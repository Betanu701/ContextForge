"""KnowledgeTree — hierarchical knowledge storage backed by SQLite."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .utils import chunk_text, extract_keywords, estimate_tokens


@dataclass
class WorkingSet:
    """A subset of the knowledge tree loaded for a single query.

    Represents the context window's dynamic portion — only what's needed
    for the current operation, freeing everything else for subsequent queries.
    """

    content: str
    """Assembled text ready for injection into the LLM prompt."""

    node_paths: list[str]
    """Paths of nodes included in this working set."""

    total_tokens: int
    """Estimated token count of the assembled content."""

    node_ids: list[int] = field(default_factory=list)
    """Internal node IDs for recycling."""


@dataclass
class KnowledgeNode:
    """A node in the knowledge tree."""

    id: int
    path: str  # e.g. "company/finance/q3_report"
    title: str
    content: str
    category: str
    parent_id: Optional[int] = None
    token_estimate: int = 0
    children: list[KnowledgeNode] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    parent_id INTEGER REFERENCES knowledge_nodes(id),
    token_estimate INTEGER DEFAULT 0,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_kn_path ON knowledge_nodes(path);
CREATE INDEX IF NOT EXISTS idx_kn_category ON knowledge_nodes(category);
CREATE INDEX IF NOT EXISTS idx_kn_parent ON knowledge_nodes(parent_id);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_estimate INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_kc_node ON knowledge_chunks(node_id);
"""


class KnowledgeTree:
    """Hierarchical knowledge storage with disk-backed SQLite and in-memory tree."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # -- lifecycle --------------------------------------------------------

    def open(self) -> None:
        """Open (or create) the database and ensure schema exists."""
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

    # -- CRUD -------------------------------------------------------------

    def add(
        self,
        path: str,
        title: str,
        content: str,
        category: str = "general",
        parent_path: Optional[str] = None,
        metadata: Optional[dict] = None,
        chunk_size: int = 512,
    ) -> KnowledgeNode:
        """Insert a knowledge node (and its chunks) into the tree.

        If the path already exists, updates the content.
        """
        import json

        parent_id = None
        if parent_path:
            row = self.conn.execute(
                "SELECT id FROM knowledge_nodes WHERE path = ?", (parent_path,)
            ).fetchone()
            if row:
                parent_id = row[0]

        meta_json = json.dumps(metadata or {})
        tok_est = estimate_tokens(content)

        existing = self.conn.execute(
            "SELECT id FROM knowledge_nodes WHERE path = ?", (path,)
        ).fetchone()

        if existing:
            node_id = existing[0]
            self.conn.execute(
                """UPDATE knowledge_nodes
                   SET title=?, content=?, category=?, parent_id=?,
                       token_estimate=?, metadata_json=?,
                       updated_at=datetime('now')
                   WHERE id=?""",
                (title, content, category, parent_id, tok_est, meta_json, node_id),
            )
            self.conn.execute("DELETE FROM knowledge_chunks WHERE node_id=?", (node_id,))
        else:
            cur = self.conn.execute(
                """INSERT INTO knowledge_nodes
                   (path, title, content, category, parent_id, token_estimate, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (path, title, content, category, parent_id, tok_est, meta_json),
            )
            node_id = cur.lastrowid

        # Chunk content for granular retrieval
        chunks = chunk_text(content, max_tokens=chunk_size)
        for idx, chunk in enumerate(chunks):
            self.conn.execute(
                """INSERT INTO knowledge_chunks (node_id, chunk_index, content, token_estimate)
                   VALUES (?, ?, ?, ?)""",
                (node_id, idx, chunk, estimate_tokens(chunk)),
            )

        self.conn.commit()

        return KnowledgeNode(
            id=node_id,
            path=path,
            title=title,
            content=content,
            category=category,
            parent_id=parent_id,
            token_estimate=tok_est,
        )

    def get(self, path: str) -> Optional[KnowledgeNode]:
        """Retrieve a single node by path."""
        row = self.conn.execute(
            "SELECT id, path, title, content, category, parent_id, token_estimate "
            "FROM knowledge_nodes WHERE path = ?",
            (path,),
        ).fetchone()
        if not row:
            return None
        return KnowledgeNode(
            id=row[0],
            path=row[1],
            title=row[2],
            content=row[3],
            category=row[4],
            parent_id=row[5],
            token_estimate=row[6],
        )

    def remove(self, path: str) -> bool:
        """Delete a node and its chunks. Returns True if found."""
        node = self.get(path)
        if not node:
            return False
        self.conn.execute("DELETE FROM knowledge_chunks WHERE node_id=?", (node.id,))
        self.conn.execute("DELETE FROM knowledge_nodes WHERE id=?", (node.id,))
        self.conn.commit()
        return True

    def list_paths(self, prefix: str = "") -> list[str]:
        """List all node paths, optionally filtered by prefix."""
        rows = self.conn.execute(
            "SELECT path FROM knowledge_nodes WHERE path LIKE ? ORDER BY path",
            (prefix + "%",),
        ).fetchall()
        return [r[0] for r in rows]

    def list_categories(self) -> list[str]:
        """Return distinct categories."""
        rows = self.conn.execute(
            "SELECT DISTINCT category FROM knowledge_nodes ORDER BY category"
        ).fetchall()
        return [r[0] for r in rows]

    def get_children(self, path: str) -> list[KnowledgeNode]:
        """Get direct children of a node."""
        parent = self.get(path)
        if not parent:
            return []
        rows = self.conn.execute(
            "SELECT id, path, title, content, category, parent_id, token_estimate "
            "FROM knowledge_nodes WHERE parent_id = ? ORDER BY path",
            (parent.id,),
        ).fetchall()
        return [
            KnowledgeNode(
                id=r[0], path=r[1], title=r[2], content=r[3],
                category=r[4], parent_id=r[5], token_estimate=r[6],
            )
            for r in rows
        ]

    def get_branch(self, path: str) -> list[KnowledgeNode]:
        """Get a node and all its descendants (breadth-first)."""
        root = self.get(path)
        if not root:
            return []
        result = [root]
        queue = [root.id]
        while queue:
            pid = queue.pop(0)
            rows = self.conn.execute(
                "SELECT id, path, title, content, category, parent_id, token_estimate "
                "FROM knowledge_nodes WHERE parent_id = ? ORDER BY path",
                (pid,),
            ).fetchall()
            for r in rows:
                node = KnowledgeNode(
                    id=r[0], path=r[1], title=r[2], content=r[3],
                    category=r[4], parent_id=r[5], token_estimate=r[6],
                )
                result.append(node)
                queue.append(node.id)
        return result

    def get_chunks(self, node_id: int) -> list[str]:
        """Get all chunks for a node, ordered by index."""
        rows = self.conn.execute(
            "SELECT content FROM knowledge_chunks WHERE node_id=? ORDER BY chunk_index",
            (node_id,),
        ).fetchall()
        return [r[0] for r in rows]

    def search(self, category: Optional[str] = None, keyword: Optional[str] = None) -> list[KnowledgeNode]:
        """Simple search by category and/or keyword substring match."""
        conditions = []
        params: list = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if keyword:
            conditions.append("(content LIKE ? OR title LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw])

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = self.conn.execute(
            f"SELECT id, path, title, content, category, parent_id, token_estimate "
            f"FROM knowledge_nodes WHERE {where} ORDER BY path",
            params,
        ).fetchall()
        return [
            KnowledgeNode(
                id=r[0], path=r[1], title=r[2], content=r[3],
                category=r[4], parent_id=r[5], token_estimate=r[6],
            )
            for r in rows
        ]

    def total_nodes(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()
        return row[0] if row else 0

    # -- bulk ingestion ---------------------------------------------------

    def ingest_directory(
        self,
        directory: str,
        category: str = "general",
        extensions: Optional[set[str]] = None,
    ) -> int:
        """Recursively ingest files from a directory into the tree.

        Returns the number of files ingested.
        """
        if extensions is None:
            extensions = {".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
                          ".html", ".css", ".rst", ".csv", ".xml", ".toml", ".cfg", ".ini"}

        root = Path(directory).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory}")

        count = 0
        for fpath in sorted(root.rglob("*")):
            if not fpath.is_file():
                continue
            if fpath.suffix.lower() not in extensions:
                continue

            rel = fpath.relative_to(root)
            node_path = f"{category}/{str(rel).replace(os.sep, '/')}"
            title = fpath.stem.replace("_", " ").replace("-", " ").title()

            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Determine parent path
            parent_parts = list(rel.parts[:-1])
            parent_path = None
            if parent_parts:
                parent_path = f"{category}/{'/'.join(parent_parts)}"
                # Ensure parent node exists
                if not self.get(parent_path):
                    self.add(
                        path=parent_path,
                        title=parent_parts[-1].replace("_", " ").title(),
                        content=f"Directory: {'/'.join(parent_parts)}",
                        category=category,
                    )

            self.add(
                path=node_path,
                title=title,
                content=content,
                category=category,
                parent_path=parent_path,
            )
            count += 1

        return count

    # -- context window management ----------------------------------------

    def get_working_set(
        self,
        keywords: list[str],
        max_tokens: Optional[int] = None,
    ) -> WorkingSet:
        """Load ONLY what's needed for this query. Everything else stays on disk.

        Searches for nodes matching *keywords*, then greedily packs them into a
        working set that fits within *max_tokens*.  Returns a ``WorkingSet``
        ready for injection into the LLM context.
        """
        budget = max_tokens or 8192

        if not keywords:
            return WorkingSet(content="", node_paths=[], total_tokens=0, node_ids=[])

        # Search by keyword substring (simple, fast, works on any SQLite)
        conditions = " OR ".join(
            ["(content LIKE ? OR title LIKE ?)"] * len(keywords)
        )
        params: list[str] = []
        for kw in keywords:
            like = f"%{kw}%"
            params.extend([like, like])

        rows = self.conn.execute(
            f"SELECT id, path, title, content, token_estimate "
            f"FROM knowledge_nodes WHERE {conditions} "
            f"ORDER BY token_estimate ASC",
            params,
        ).fetchall()

        # Greedy packing within budget
        selected_parts: list[str] = []
        selected_paths: list[str] = []
        selected_ids: list[int] = []
        used = 0

        for row in rows:
            nid, path, title, content, tok_est = row
            if used + tok_est > budget and selected_parts:
                break
            selected_parts.append(f"### {title} [{path}]\n{content}")
            selected_paths.append(path)
            selected_ids.append(nid)
            used += tok_est

        return WorkingSet(
            content="\n\n".join(selected_parts),
            node_paths=selected_paths,
            total_tokens=used,
            node_ids=selected_ids,
        )

    def recycle_context(self, working_set: WorkingSet) -> None:
        """Free the working set after generation.

        The knowledge remains on disk — only the in-memory reference is
        released so the next query can use the token budget for different
        branches.  This is a no-op at the storage layer (SQLite doesn't
        hold anything in memory per-query), but the explicit call resets
        the working set's content to signal that it should not be reused.
        """
        working_set.content = ""
        working_set.node_paths = []
        working_set.node_ids = []
        working_set.total_tokens = 0

    def get_compacted_signatures(self, node_ids: list[int]) -> str:
        """Return compact signatures for nodes — names only, not full content.

        For code nodes this extracts ``class`` / ``def`` / ``import`` lines.
        For prose nodes it keeps the first line.  The result is typically
        ~500 tokens per file instead of ~5000.
        """
        parts: list[str] = []
        for nid in node_ids:
            row = self.conn.execute(
                "SELECT path, title, content FROM knowledge_nodes WHERE id = ?",
                (nid,),
            ).fetchone()
            if not row:
                continue
            path, title, content = row
            sig = self._extract_signatures(content)
            parts.append(f"# {title} [{path}]\n{sig}")
        return "\n\n".join(parts)

    def get_compacted_signatures_from_content(
        self, file_path: str, content: str,
    ) -> str:
        """Generate a compact signature string from raw content.

        Used during project generation to summarise a freshly generated file
        without requiring it to be stored in the tree first.
        """
        sig = self._extract_signatures(content)
        return f"# {file_path}\n{sig}"

    @staticmethod
    def _extract_signatures(content: str) -> str:
        """Extract class/function/import signatures from content."""
        import re

        sig_lines: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if re.match(
                r"^(class |def |async def |import |from |export |function |const |let |var |type |interface |struct |fn |pub fn |impl )",
                stripped,
            ):
                sig_lines.append(stripped)

        if sig_lines:
            return "\n".join(sig_lines)

        # Fallback: first line for prose documents
        first_line = content.strip().split("\n", 1)[0]
        return first_line[:200] if first_line else "(empty)"
