"""InfiniteContext — practically unlimited knowledge through context recycling.

VRAM holds ~680K active tokens at any moment.
Disk holds unlimited tokens as tree nodes.
Each operation loads what it needs, works, frees context.
The 1000th query costs the same VRAM as the 1st.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .index import MemoryIndex
from .loader import ProactiveLoader
from .providers.base import LLMProvider
from .session import SessionStore
from .tree import KnowledgeTree, WorkingSet
from .utils import estimate_tokens, extract_keywords


@dataclass
class InfiniteContextStats:
    """Snapshot of infinite context memory usage."""

    active_tokens: int = 0
    """Tokens currently loaded in the working set."""

    disk_tokens: int = 0
    """Total tokens stored on disk across all tree nodes."""

    permanent_tokens: int = 0
    """Tokens in permanent residual context (personality, contracts)."""

    compression_ratio: float = 0.0
    """Ratio of active tokens to total tokens (lower = more compressed)."""

    recycles: int = 0
    """Number of times context has been recycled since creation."""

    peak_active: int = 0
    """Maximum active tokens observed during the session."""


_COMPACT_PROMPT = (
    "Summarize the following conversation concisely, preserving all key facts, "
    "decisions, and action items. Omit pleasantries and filler:\n\n"
)

_HISTORY_COMPACT_THRESHOLD = 3000
"""When compacted history exceeds this many tokens, re-compact."""


class InfiniteContext:
    """Manages practically infinite knowledge through context recycling.

    The core idea: VRAM is a *window* over disk-backed knowledge. Each query
    loads only the branches it needs, generates a response, then recycles the
    branches so the next query can load different ones. Permanent context
    (personality, contracts, safety rules) is cached once and reused as a
    residual prefix — costing zero tokens after the first request.

    Usage::

        ic = InfiniteContext(tree, session_store, index, loader)
        await ic.set_permanent_context("You are a helpful assistant.")
        response = await ic.query("What was Q3 revenue?", provider)
    """

    def __init__(
        self,
        tree: KnowledgeTree,
        session: SessionStore,
        index: MemoryIndex,
        loader: ProactiveLoader,
        *,
        max_active_tokens: int = 680_000,
    ) -> None:
        self.tree = tree
        self.session = session
        self.index = index
        self.loader = loader

        self._max_active_tokens = max_active_tokens
        self._permanent_prefix: str = ""
        self._permanent_tokens: int = 0
        self._active_branches: dict[str, int] = {}  # path → token count
        self._compacted_history: str = ""
        self._compacted_history_tokens: int = 0

        # Tracking
        self._recycles: int = 0
        self._peak_active: int = 0

    # -- permanent context ------------------------------------------------

    async def set_permanent_context(self, text: str) -> None:
        """Set permanent context (contract, personality, safety rules).

        This content is prepended to every request and benefits from KV-cache
        prefix caching — after the first request it costs effectively 0 tokens
        of recomputation. With KV-free residual storage the memory footprint
        is ~48% smaller than full KV pairs.
        """
        self._permanent_prefix = text
        self._permanent_tokens = estimate_tokens(text)

    # -- query interface --------------------------------------------------

    async def query(
        self,
        message: str,
        provider: LLMProvider,
        *,
        session_id: Optional[str] = None,
        max_knowledge_tokens: Optional[int] = None,
    ) -> str:
        """Smart query with infinite context recycling.

        Steps:
        1. Extract keywords from message
        2. Search tree index (<1ms)
        3. Load relevant branches (2–10K tokens, not everything)
        4. Add compacted history (rolling summary, ~1K tokens)
        5. Generate response
        6. Save response to session
        7. Compact history if it's getting long
        8. Recycle branches not needed for next turn
        """
        budget = max_knowledge_tokens or self._dynamic_budget()

        # 1–3: Load a working set via the tree
        keywords = extract_keywords(message, top_k=15)
        working_set = self.tree.get_working_set(keywords, max_tokens=budget)
        self._track_branches(working_set)

        # 4: Build messages
        messages = self._build_messages(message, working_set.content)

        # 5: Generate
        response = await provider.chat(messages)

        # 6: Save to session
        if session_id:
            self.session.add_message(session_id, "user", message)
            self.session.add_message(session_id, "assistant", response)

        # 7: Compact history if needed
        self._append_to_history(message, response)
        if self._compacted_history_tokens > _HISTORY_COMPACT_THRESHOLD:
            await self._compact_history(provider)

        # 8: Recycle
        self.tree.recycle_context(working_set)
        self._recycles += 1

        return response

    # -- file / project generation ----------------------------------------

    async def generate_file(
        self,
        file_spec: str,
        contract: str,
        previous_signatures: str,
        provider: LLMProvider,
    ) -> str:
        """Generate a single file with infinite context recycling.

        Context layout:
        1. Permanent: contract (cached, 0 tokens after first request)
        2. Dynamic: relevant spec section from tree (~2K tokens)
        3. Dynamic: compacted signatures of previous files (~500 tokens/file)
        4. Generate file content
        5. Recycle spec section

        File 1 and file 1000 use the same VRAM.
        """
        budget = self._dynamic_budget()

        # Load spec context
        keywords = extract_keywords(file_spec, top_k=15)
        working_set = self.tree.get_working_set(keywords, max_tokens=budget)
        self._track_branches(working_set)

        # Build generation prompt
        parts: list[str] = []
        if contract:
            parts.append(f"## Contract\n{contract}")
        if working_set.content:
            parts.append(f"## Specification\n{working_set.content}")
        if previous_signatures:
            parts.append(f"## Previously Generated (signatures only)\n{previous_signatures}")
        parts.append(f"## Task\nGenerate the following file:\n{file_spec}")

        messages = [
            {"role": "system", "content": self._permanent_prefix or "You are a code generator."},
            {"role": "user", "content": "\n\n".join(parts)},
        ]

        response = await provider.chat(messages)

        # Recycle
        self.tree.recycle_context(working_set)
        self._recycles += 1

        return response

    async def generate_project(
        self,
        spec: str,
        files: list[str],
        provider: LLMProvider,
        *,
        contract: str = "",
    ) -> dict[str, str]:
        """Generate an entire project with infinite context recycling.

        Each file is generated independently. After generation its full content
        is compacted to signatures (~500 tokens instead of ~5000) and carried
        forward as context for subsequent files. No context limit regardless of
        project size.

        Returns:
            Dict mapping file path → generated content.
        """
        # Ingest the spec into the tree for per-file retrieval
        self.tree.add(
            path="_project_spec",
            title="Project Specification",
            content=spec,
            category="_generation",
        )
        self.index.build_from_tree(self.tree)

        results: dict[str, str] = {}
        accumulated_signatures: list[str] = []

        for file_path in files:
            sigs_text = "\n".join(accumulated_signatures) if accumulated_signatures else ""
            content = await self.generate_file(
                file_spec=file_path,
                contract=contract,
                previous_signatures=sigs_text,
                provider=provider,
            )
            results[file_path] = content

            # Compact to signatures for next file
            sig = self.tree.get_compacted_signatures_from_content(
                file_path, content,
            )
            accumulated_signatures.append(sig)

        # Clean up temp spec node
        self.tree.remove("_project_spec")
        self.index.build_from_tree(self.tree)

        return results

    # -- stats ------------------------------------------------------------

    def get_stats(self) -> InfiniteContextStats:
        """Snapshot of current memory usage."""
        active = self._current_active_tokens()
        disk = self._total_disk_tokens()
        total = disk if disk > 0 else 1

        return InfiniteContextStats(
            active_tokens=active,
            disk_tokens=disk,
            permanent_tokens=self._permanent_tokens,
            compression_ratio=active / total,
            recycles=self._recycles,
            peak_active=self._peak_active,
        )

    # -- internals --------------------------------------------------------

    def _dynamic_budget(self) -> int:
        """Calculate available token budget for knowledge context."""
        overhead = self._permanent_tokens + self._compacted_history_tokens + 500
        return max(1024, self._max_active_tokens - overhead)

    def _build_messages(self, user_message: str, knowledge_content: str) -> list[dict]:
        """Assemble messages for the LLM with permanent + dynamic context."""
        messages: list[dict] = []

        # System: permanent prefix + knowledge
        system_parts: list[str] = []
        if self._permanent_prefix:
            system_parts.append(self._permanent_prefix)
        if knowledge_content:
            system_parts.append(f"## Relevant Knowledge\n{knowledge_content}")
        if self._compacted_history:
            system_parts.append(f"## Conversation History (compacted)\n{self._compacted_history}")

        messages.append({
            "role": "system",
            "content": "\n\n".join(system_parts) if system_parts else "You are a helpful assistant.",
        })
        messages.append({"role": "user", "content": user_message})

        return messages

    def _track_branches(self, working_set: WorkingSet) -> None:
        """Update active branch tracking and peak stats."""
        for path in working_set.node_paths:
            self._active_branches[path] = working_set.total_tokens
        active = self._current_active_tokens()
        if active > self._peak_active:
            self._peak_active = active

    def _current_active_tokens(self) -> int:
        """Total tokens currently loaded."""
        return (
            self._permanent_tokens
            + self._compacted_history_tokens
            + sum(self._active_branches.values())
        )

    def _total_disk_tokens(self) -> int:
        """Total tokens stored on disk."""
        row = self.tree.conn.execute(
            "SELECT COALESCE(SUM(token_estimate), 0) FROM knowledge_nodes"
        ).fetchone()
        return row[0] if row else 0

    def _append_to_history(self, user_msg: str, assistant_msg: str) -> None:
        """Append an exchange to the rolling compacted history."""
        entry = f"User: {user_msg}\nAssistant: {assistant_msg}\n"
        self._compacted_history += entry
        self._compacted_history_tokens = estimate_tokens(self._compacted_history)

    async def _compact_history(self, provider: LLMProvider) -> None:
        """Use the LLM to compress conversation history into a summary."""
        messages = [
            {"role": "system", "content": "You are a summarization assistant."},
            {"role": "user", "content": _COMPACT_PROMPT + self._compacted_history},
        ]
        summary = await provider.chat(messages)
        self._compacted_history = summary
        self._compacted_history_tokens = estimate_tokens(summary)
