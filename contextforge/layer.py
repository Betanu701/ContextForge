"""ContextForge — the main entry point for the SDK.

One import, one class, infinite memory for any LLM.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncGenerator, Optional, Union

from .index import MemoryIndex
from .infinite_context import InfiniteContext, InfiniteContextStats
from .loader import LoadedContext, ProactiveLoader
from .providers import LLMProvider, get_provider
from .session import Session, SessionStore
from .tree import KnowledgeTree
from .utils import estimate_tokens


class ContextForge:
    """Give any LLM unlimited, persistent, hierarchical memory.

    Usage::

        layer = ContextForge(provider="openai", api_key="sk-...")
        await layer.ingest("./docs/")
        response = await layer.chat("What was the Q3 revenue?")

    Args:
        provider: LLM backend — ``"openai"``, ``"anthropic"``, or ``"local"``.
        api_key: API key for cloud providers.
        model: Model name override.
        base_url: Endpoint URL (required for ``"local"`` provider).
        knowledge_dir: Directory to auto-ingest on init.
        db_path: SQLite database path for knowledge + sessions.
        max_context_tokens: Token budget for proactive knowledge loading.
        system_prompt: Base system prompt prepended to every request.
        llm_provider: Pre-built LLMProvider instance (overrides ``provider``).
    """

    def __init__(
        self,
        provider: str = "openai",
        api_key: str = "",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        knowledge_dir: Optional[str] = None,
        db_path: str = "./contextforge.db",
        max_context_tokens: int = 4096,
        system_prompt: str = "You are a helpful assistant with access to a knowledge base.",
        llm_provider: Optional[LLMProvider] = None,
    ) -> None:
        # -- LLM provider --
        if llm_provider:
            self._provider = llm_provider
        else:
            self._provider = get_provider(
                provider, api_key=api_key, model=model, base_url=base_url,
            )

        self._system_prompt = system_prompt

        # -- Knowledge tree + index --
        self._tree = KnowledgeTree(db_path=db_path)
        self._tree.open()

        self._index = MemoryIndex()
        self._index.build_from_tree(self._tree)

        # -- Proactive loader --
        self._loader = ProactiveLoader(
            tree=self._tree,
            index=self._index,
            max_context_tokens=max_context_tokens,
        )

        # -- Session store (shares the same DB) --
        self._sessions = SessionStore(db_path=db_path)
        self._sessions.open()
        self._current_session: Optional[Session] = None

        # -- Infinite context engine --
        self._infinite = InfiniteContext(
            tree=self._tree,
            session=self._sessions,
            index=self._index,
            loader=self._loader,
            max_active_tokens=max_context_tokens * 160,  # scale from per-query to full window
        )

        # -- Auto-ingest --
        if knowledge_dir and os.path.isdir(knowledge_dir):
            self.ingest_sync(knowledge_dir)

    # -- knowledge ingestion ----------------------------------------------

    async def ingest(
        self,
        path: str,
        category: str = "general",
        extensions: Optional[set[str]] = None,
    ) -> int:
        """Ingest a directory of files into the knowledge tree.

        Returns the number of files ingested.
        """
        return self.ingest_sync(path, category=category, extensions=extensions)

    def ingest_sync(
        self,
        path: str,
        category: str = "general",
        extensions: Optional[set[str]] = None,
    ) -> int:
        """Synchronous ingestion (called by __init__ for auto-ingest)."""
        count = self._tree.ingest_directory(path, category=category, extensions=extensions)
        self._index.build_from_tree(self._tree)
        self._loader.invalidate_cache()
        return count

    async def ingest_text(
        self,
        text: str,
        title: str = "untitled",
        category: str = "general",
        path: Optional[str] = None,
    ) -> None:
        """Ingest a single text document."""
        node_path = path or f"{category}/{title.lower().replace(' ', '_')}"
        self._tree.add(path=node_path, title=title, content=text, category=category)
        self._index.build_from_tree(self._tree)

    async def ingest_code(
        self,
        directory: str,
        project: str = "code",
    ) -> int:
        """Ingest source code files from a project directory."""
        code_extensions = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
            ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
            ".kt", ".scala", ".r", ".sql", ".sh", ".bash", ".yaml", ".yml",
            ".json", ".toml", ".xml", ".html", ".css", ".md", ".txt",
        }
        return await self.ingest(directory, category=project, extensions=code_extensions)

    # -- chat interface ---------------------------------------------------

    async def chat(self, message: str, **kwargs) -> str:
        """Send a message and get a complete response.

        Proactively loads relevant knowledge, maintains session context,
        and returns the LLM's response.
        """
        self._ensure_session()
        assert self._current_session is not None

        # Build conversation context from recent messages
        conv_context = self._recent_context()

        # Proactive knowledge loading
        loaded = self._loader.load(message, conversation_context=conv_context)

        # Assemble messages
        messages = self._build_messages(message, loaded)

        # Call LLM
        response = await self._provider.chat(messages, **kwargs)

        # Store in session
        self._sessions.add_message(self._current_session.id, "user", message)
        self._sessions.add_message(self._current_session.id, "assistant", response)

        return response

    async def stream(self, message: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream a response token by token.

        Same proactive loading as ``chat``, but yields tokens incrementally.
        """
        self._ensure_session()
        assert self._current_session is not None

        conv_context = self._recent_context()
        loaded = self._loader.load(message, conversation_context=conv_context)
        messages = self._build_messages(message, loaded)

        full_response: list[str] = []
        async for token in self._provider.stream(messages, **kwargs):
            full_response.append(token)
            yield token

        # Store in session
        self._sessions.add_message(self._current_session.id, "user", message)
        self._sessions.add_message(
            self._current_session.id, "assistant", "".join(full_response),
        )

    async def analyze(self, query: str, **kwargs) -> str:
        """Multi-pass analysis across knowledge domains.

        Loads context from each matching category, sends separate queries,
        and then synthesizes a final answer.
        """
        self._ensure_session()
        assert self._current_session is not None

        conv_context = self._recent_context()
        contexts = self._loader.load_multi(query, conversation_context=conv_context)

        if not contexts:
            return await self.chat(query, **kwargs)

        if len(contexts) == 1:
            return await self.chat(query, **kwargs)

        # Multi-pass: get per-domain responses
        domain_responses: list[str] = []
        for ctx in contexts:
            domain_messages = self._build_messages(query, ctx)
            resp = await self._provider.chat(domain_messages, **kwargs)
            domain_responses.append(resp)

        # Synthesis pass
        synthesis_prompt = (
            f"You were asked: {query}\n\n"
            f"Here are analyses from {len(domain_responses)} knowledge domains:\n\n"
        )
        for i, resp in enumerate(domain_responses, 1):
            synthesis_prompt += f"--- Domain {i} ---\n{resp}\n\n"
        synthesis_prompt += (
            "Please synthesize these into a single, comprehensive answer. "
            "Identify agreements, contradictions, and gaps."
        )

        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": synthesis_prompt},
        ]
        response = await self._provider.chat(messages, **kwargs)

        self._sessions.add_message(self._current_session.id, "user", query)
        self._sessions.add_message(self._current_session.id, "assistant", response)

        return response

    # -- session management -----------------------------------------------

    def new_session(self, session_id: Optional[str] = None, metadata: Optional[dict] = None) -> str:
        """Start a new conversation session. Returns the session ID."""
        session = self._sessions.create_session(session_id=session_id, metadata=metadata)
        self._current_session = session
        return session.id

    def resume_session(self, session_id: str) -> bool:
        """Resume a previous session. Returns True if found."""
        session = self._sessions.load_session(session_id)
        if session:
            self._current_session = session
            return True
        return False

    def save_session(self) -> Optional[str]:
        """Persist the current session. Returns the session ID."""
        if self._current_session:
            return self._current_session.id
        return None

    def list_sessions(self) -> list[dict]:
        """List all stored sessions."""
        return self._sessions.list_sessions()

    # -- accessors --------------------------------------------------------

    @property
    def tree(self) -> KnowledgeTree:
        """Access the underlying knowledge tree."""
        return self._tree

    @property
    def index(self) -> MemoryIndex:
        """Access the memory index."""
        return self._index

    @property
    def session(self) -> Optional[Session]:
        """The current active session."""
        return self._current_session

    @property
    def infinite(self) -> InfiniteContext:
        """Access the infinite context engine."""
        return self._infinite

    async def set_permanent_context(self, text: str) -> None:
        """Set permanent context that persists across all queries.

        This content (personality, contracts, safety rules) is cached once and
        reused via KV-cache prefix caching — costing 0 recomputation tokens
        after the first request.
        """
        await self._infinite.set_permanent_context(text)

    @property
    def stats(self) -> dict:
        """Return current statistics."""
        ic_stats = self._infinite.get_stats()
        return {
            "knowledge_nodes": self._tree.total_nodes(),
            "index_terms": self._index.num_terms,
            "index_docs": self._index.num_docs,
            "sessions": len(self._sessions.list_sessions()),
            "cache": self._loader.cache_stats(),
            "infinite_context": {
                "active_tokens": ic_stats.active_tokens,
                "disk_tokens": ic_stats.disk_tokens,
                "permanent_tokens": ic_stats.permanent_tokens,
                "compression_ratio": ic_stats.compression_ratio,
                "recycles": ic_stats.recycles,
                "peak_active": ic_stats.peak_active,
            },
        }

    # -- cleanup ----------------------------------------------------------

    def close(self) -> None:
        """Close all database connections."""
        self._tree.close()
        self._sessions.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # -- internals --------------------------------------------------------

    def _ensure_session(self) -> None:
        """Create a session if none exists."""
        if self._current_session is None:
            self.new_session()

    def _recent_context(self, max_turns: int = 6) -> str:
        """Build a string of recent conversation for keyword extraction."""
        if not self._current_session:
            return ""
        recent = self._current_session.messages[-max_turns:]
        parts = [m.get("content", "") for m in recent if m.get("role") != "system"]
        return " ".join(parts)

    def _build_messages(self, user_message: str, loaded: LoadedContext) -> list[dict]:
        """Assemble the final message list for the LLM."""
        messages: list[dict] = []

        # System prompt with knowledge context
        system = self._system_prompt
        if loaded.system_prefix:
            system += f"\n\n{loaded.system_prefix}"
        messages.append({"role": "system", "content": system})

        # Session history (skip system messages — we already have our own)
        if self._current_session:
            for msg in self._current_session.messages:
                if msg.get("role") != "system":
                    messages.append(msg)

        # Current user message
        messages.append({"role": "user", "content": user_message})

        return messages
