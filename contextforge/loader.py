"""ProactiveLoader — automatic context assembly from the knowledge tree."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .index import MemoryIndex, SearchResult
from .tree import KnowledgeTree
from .utils import estimate_tokens, extract_keywords


@dataclass
class LoadedContext:
    """The assembled context ready to inject into the LLM prompt."""

    system_prefix: str
    """Knowledge context formatted for the system message."""

    sources: list[str]
    """Paths of knowledge nodes used."""

    total_tokens: int
    """Estimated token count of the assembled context."""

    branch_paths: list[str]
    """Full branch paths that were loaded."""


@dataclass
class _CacheEntry:
    """Cached branch content to avoid re-reading on follow-up turns."""

    path: str
    content: str
    tokens: int
    hits: int = 0


class ProactiveLoader:
    """Assembles relevant knowledge context for each user query.

    Strategy:
    1. Extract keywords from user query + recent conversation
    2. Search the inverted index for matching nodes
    3. Load the best-matching branches from the tree
    4. Assemble into a context block that fits within the token budget
    5. Cache loaded branches for follow-up questions
    """

    def __init__(
        self,
        tree: KnowledgeTree,
        index: MemoryIndex,
        max_context_tokens: int = 4096,
    ) -> None:
        self._tree = tree
        self._index = index
        self._max_tokens = max_context_tokens
        self._cache: dict[str, _CacheEntry] = {}
        self._last_categories: list[str] = []

    @property
    def max_context_tokens(self) -> int:
        return self._max_tokens

    @max_context_tokens.setter
    def max_context_tokens(self, value: int) -> None:
        self._max_tokens = value

    def load(
        self,
        query: str,
        conversation_context: str = "",
        category_hint: Optional[str] = None,
    ) -> LoadedContext:
        """Proactively load relevant knowledge for a query.

        Args:
            query: The current user message.
            conversation_context: Recent conversation turns for better matching.
            category_hint: Optional category to prioritize.

        Returns:
            LoadedContext with assembled knowledge and metadata.
        """
        # Combine query with conversation for richer keyword extraction
        combined = f"{query} {conversation_context}".strip()
        keywords = extract_keywords(combined, top_k=15)

        if not keywords and not category_hint:
            return LoadedContext(
                system_prefix="",
                sources=[],
                total_tokens=0,
                branch_paths=[],
            )

        # Search the index
        results = self._index.search(
            query=combined,
            top_k=20,
            category=category_hint,
        )

        if not results:
            return LoadedContext(
                system_prefix="",
                sources=[],
                total_tokens=0,
                branch_paths=[],
            )

        # Select nodes within token budget, preferring cached branches
        selected = self._select_nodes(results)

        # Track categories for follow-up context
        self._last_categories = list({r.category for r in selected})

        # Assemble the context
        return self._assemble(selected)

    def load_multi(
        self,
        query: str,
        conversation_context: str = "",
    ) -> list[LoadedContext]:
        """Multi-pass loading for cross-domain analysis.

        Loads context from each matching category separately,
        useful for synthesizing across knowledge domains.
        """
        combined = f"{query} {conversation_context}".strip()
        results = self._index.search(query=combined, top_k=30)

        if not results:
            return []

        # Group by category
        by_category: dict[str, list[SearchResult]] = {}
        for r in results:
            by_category.setdefault(r.category, []).append(r)

        contexts = []
        for category, cat_results in by_category.items():
            selected = self._select_nodes(cat_results)
            if selected:
                ctx = self._assemble(selected, label=category)
                contexts.append(ctx)

        return contexts

    def _select_nodes(self, results: list[SearchResult]) -> list[SearchResult]:
        """Select nodes within the token budget, boosting cached branches."""
        budget = self._max_tokens
        selected: list[SearchResult] = []

        # Boost cached entries
        scored = []
        for r in results:
            boost = 1.0
            if r.path in self._cache:
                boost = 1.5
                self._cache[r.path].hits += 1
            scored.append((r, r.score * boost))

        scored.sort(key=lambda x: -x[1])

        for r, _ in scored:
            node = self._tree.get(r.path)
            if not node:
                continue
            if budget - node.token_estimate < 0 and selected:
                continue
            budget -= node.token_estimate
            selected.append(r)

            # Cache this branch
            if r.path not in self._cache:
                self._cache[r.path] = _CacheEntry(
                    path=r.path,
                    content=node.content,
                    tokens=node.token_estimate,
                )

        return selected

    def _assemble(
        self,
        results: list[SearchResult],
        label: Optional[str] = None,
    ) -> LoadedContext:
        """Assemble selected nodes into a formatted context string."""
        parts: list[str] = []
        sources: list[str] = []
        total_tokens = 0

        header = "## Relevant Knowledge"
        if label:
            header += f" ({label})"
        parts.append(header)

        for r in results:
            # Prefer cached content
            cached = self._cache.get(r.path)
            if cached:
                content = cached.content
                tokens = cached.tokens
            else:
                node = self._tree.get(r.path)
                if not node:
                    continue
                content = node.content
                tokens = node.token_estimate

            parts.append(f"\n### {r.title} [{r.path}]")
            parts.append(content)
            sources.append(r.path)
            total_tokens += tokens

        system_prefix = "\n".join(parts) if len(parts) > 1 else ""

        return LoadedContext(
            system_prefix=system_prefix,
            sources=sources,
            total_tokens=total_tokens,
            branch_paths=[r.path for r in results],
        )

    def invalidate_cache(self, path: Optional[str] = None) -> None:
        """Clear the branch cache, optionally for a specific path."""
        if path:
            self._cache.pop(path, None)
        else:
            self._cache.clear()

    def cache_stats(self) -> dict:
        """Return cache statistics."""
        return {
            "entries": len(self._cache),
            "total_tokens": sum(e.tokens for e in self._cache.values()),
            "total_hits": sum(e.hits for e in self._cache.values()),
        }
