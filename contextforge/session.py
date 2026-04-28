"""SessionStore — conversation persistence and compaction backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .utils import estimate_tokens


@dataclass
class Session:
    """An active conversation session."""

    id: str
    messages: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    total_tokens: int = 0


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS session_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    token_estimate INTEGER DEFAULT 0,
    is_compacted INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sm_session ON session_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_sm_turn ON session_messages(session_id, turn_index);

CREATE TABLE IF NOT EXISTS session_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    covers_turns_start INTEGER NOT NULL,
    covers_turns_end INTEGER NOT NULL,
    token_estimate INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ss_session ON session_summaries(session_id);
"""


class SessionStore:
    """Persistent conversation storage with automatic compaction.

    Conversations are stored in SQLite and can be resumed across restarts.
    When conversations grow long, older turns are compacted into summaries
    to keep the active context window manageable.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        max_active_tokens: int = 8192,
        compaction_threshold: int = 6144,
    ) -> None:
        self._db_path = db_path
        self._max_active_tokens = max_active_tokens
        self._compaction_threshold = compaction_threshold
        self._conn: Optional[sqlite3.Connection] = None
        self._active: dict[str, Session] = {}

    def open(self) -> None:
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.open()
        assert self._conn is not None
        return self._conn

    # -- session lifecycle ------------------------------------------------

    def create_session(self, session_id: Optional[str] = None, metadata: Optional[dict] = None) -> Session:
        """Create a new session."""
        sid = session_id or str(uuid.uuid4())
        meta = metadata or {}
        self.conn.execute(
            "INSERT INTO sessions (id, metadata_json) VALUES (?, ?)",
            (sid, json.dumps(meta)),
        )
        self.conn.commit()
        session = Session(id=sid, metadata=meta)
        self._active[sid] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session, loading from DB if not in memory."""
        if session_id in self._active:
            return self._active[session_id]
        return self.load_session(session_id)

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session from the database."""
        row = self.conn.execute(
            "SELECT id, metadata_json FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None

        meta = json.loads(row[1]) if row[1] else {}

        # Load summaries first (for compacted history)
        summaries = self.conn.execute(
            "SELECT summary FROM session_summaries WHERE session_id = ? ORDER BY covers_turns_start",
            (session_id,),
        ).fetchall()

        # Load non-compacted messages
        messages_rows = self.conn.execute(
            "SELECT role, content, token_estimate FROM session_messages "
            "WHERE session_id = ? AND is_compacted = 0 ORDER BY turn_index",
            (session_id,),
        ).fetchall()

        messages: list[dict] = []

        # Inject summaries as a system context message
        if summaries:
            summary_text = "\n\n".join(s[0] for s in summaries)
            messages.append({
                "role": "system",
                "content": f"[Previous conversation summary]\n{summary_text}",
            })

        for r in messages_rows:
            messages.append({"role": r[0], "content": r[1]})

        total_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
        session = Session(id=session_id, messages=messages, metadata=meta, total_tokens=total_tokens)
        self._active[session_id] = session
        return session

    def list_sessions(self) -> list[dict]:
        """List all sessions with metadata."""
        rows = self.conn.execute(
            "SELECT id, created_at, updated_at, metadata_json FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        return [
            {"id": r[0], "created_at": r[1], "updated_at": r[2], "metadata": json.loads(r[3] or "{}")}
            for r in rows
        ]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        self.conn.execute("DELETE FROM session_summaries WHERE session_id = ?", (session_id,))
        self.conn.execute("DELETE FROM session_messages WHERE session_id = ?", (session_id,))
        self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()
        self._active.pop(session_id, None)
        return True

    # -- message management -----------------------------------------------

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to a session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Determine turn index
        row = self.conn.execute(
            "SELECT COALESCE(MAX(turn_index), -1) FROM session_messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        turn_index = (row[0] if row else -1) + 1

        tok_est = estimate_tokens(content)
        self.conn.execute(
            "INSERT INTO session_messages (session_id, role, content, turn_index, token_estimate) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, turn_index, tok_est),
        )
        self.conn.execute(
            "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )
        self.conn.commit()

        session.messages.append({"role": role, "content": content})
        session.total_tokens += tok_est

        # Check if compaction is needed
        if session.total_tokens > self._compaction_threshold:
            self._compact(session_id)

    def get_messages(self, session_id: str) -> list[dict]:
        """Get the active messages for a session (post-compaction)."""
        session = self.get_session(session_id)
        return session.messages if session else []

    # -- compaction -------------------------------------------------------

    def _compact(self, session_id: str) -> None:
        """Compact older messages into a summary to free token budget.

        Keeps the most recent messages and summarizes everything else.
        """
        rows = self.conn.execute(
            "SELECT id, role, content, turn_index, token_estimate "
            "FROM session_messages WHERE session_id = ? AND is_compacted = 0 "
            "ORDER BY turn_index",
            (session_id,),
        ).fetchall()

        if len(rows) < 6:
            return

        # Keep the last 4 messages, compact the rest
        to_compact = rows[:-4]
        to_keep = rows[-4:]

        # Build a simple extractive summary
        summary_parts: list[str] = []
        for r in to_compact:
            role, content = r[1], r[2]
            # Truncate very long messages in the summary
            if len(content) > 300:
                content = content[:300] + "..."
            summary_parts.append(f"{role}: {content}")

        summary = "\n".join(summary_parts)
        tok_est = estimate_tokens(summary)

        start_turn = to_compact[0][3]
        end_turn = to_compact[-1][3]

        # Save summary
        self.conn.execute(
            "INSERT INTO session_summaries (session_id, summary, covers_turns_start, covers_turns_end, token_estimate) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, summary, start_turn, end_turn, tok_est),
        )

        # Mark messages as compacted
        ids = [r[0] for r in to_compact]
        placeholders = ",".join("?" * len(ids))
        self.conn.execute(
            f"UPDATE session_messages SET is_compacted = 1 WHERE id IN ({placeholders})",
            ids,
        )
        self.conn.commit()

        # Refresh in-memory session
        self._active.pop(session_id, None)
        self.load_session(session_id)

    def force_compact(self, session_id: str) -> None:
        """Force compaction regardless of token threshold."""
        self._compact(session_id)
