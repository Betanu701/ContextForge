"""ProactiveLoader — automatic context assembly from the knowledge tree."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .index import MemoryIndex, SearchResult
from .tree import KnowledgeTree
from .utils import estimate_tokens, extract_keywords
from .wiki import WIKI_CATEGORY, WikiMemory


_WIKI_AUTO_BUDGET_RATIOS = (0.50, 0.75, 1.0)
_DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
_DAY_RE = re.compile(r"\bday[-_\s]*(\d{1,4})\b", re.IGNORECASE)
_ENTITY_RE = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2}\b")
_STATUS_TERMS = {
    "approved", "approval", "confirmed", "accepted", "granted", "blocked",
    "pending", "waiting", "cancelled", "canceled", "deferred", "delayed",
    "postponed", "rejected", "declined", "denied", "superseded", "changed",
    "latest", "current", "status", "remained", "still",
}
_CONSTRAINT_TERMS = {
    "constraint", "constraints", "gating", "gate", "blocked", "pending", "waiting",
    "dependency", "dependencies", "requires", "required", "prerequisite", "before",
    "until", "unless", "permission", "permissions", "hold", "holds", "cannot",
    "without",
}
_APPROVAL_EXCEPTION_TERMS = {
    "approved", "approval", "authorized", "authorization", "granted", "denied",
    "declined", "exception", "exceptions", "disclosure", "external", "circulate",
    "circulation", "distribution", "distributed", "send", "sent", "share", "shared",
    "review", "permission", "permissions",
}
_CHANGE_TERMS = {
    "changed", "change", "shifted", "shift", "moved", "became", "converted",
    "transitioned", "from", "to", "before", "after", "by", "latest", "prior",
    "earlier", "remained", "still", "no longer", "superseded", "replaced",
    "follow-through",
}


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

    def load_wiki(
        self,
        query: str,
        conversation_context: str = "",
        wiki_token_ratio: float = 0.30,
        include_raw_evidence: bool = True,
    ) -> LoadedContext:
        """Load compiled wiki pages first, then source-backed raw evidence.

        This keeps query-time context structured around durable synthesized pages
        while preserving access to raw source nodes for grounding.
        """
        combined = f"{query} {conversation_context}".strip()
        if not combined:
            return LoadedContext(system_prefix="", sources=[], total_tokens=0, branch_paths=[])

        wiki_results = self._index.search(combined, top_k=20, category=WIKI_CATEGORY)
        wiki_results = self._prioritize_wiki_results(combined, wiki_results)
        best_loaded = LoadedContext(system_prefix="", sources=[], total_tokens=0, branch_paths=[])
        ceiling = max(1, self._max_tokens)

        for ratio in _WIKI_AUTO_BUDGET_RATIOS:
            total_budget = max(1, min(ceiling, int(ceiling * ratio)))
            loaded = self._load_wiki_with_budget(
                combined,
                wiki_results,
                total_budget,
                wiki_token_ratio,
                include_raw_evidence,
            )
            best_loaded = loaded
            if ratio >= 1.0 or self._wiki_context_is_sufficient(
                combined,
                wiki_results,
                loaded,
                total_budget,
            ):
                break

        return best_loaded

    def _load_wiki_with_budget(
        self,
        combined: str,
        wiki_results: list[SearchResult],
        total_budget: int,
        wiki_token_ratio: float,
        include_raw_evidence: bool,
    ) -> LoadedContext:
        wiki_budget = max(1, int(total_budget * max(0.05, min(wiki_token_ratio, 0.90))))
        raw_budget = max(0, total_budget - wiki_budget)

        selected_wiki = self._select_results_with_budget(wiki_results, wiki_budget)
        selected_wiki = self._expand_wiki_neighbors(selected_wiki, wiki_budget)

        raw_paths: list[str] = []
        if include_raw_evidence:
            for result in selected_wiki:
                node = self._tree.get(result.path)
                if not node:
                    continue
                for source_path in self._query_relevant_source_refs(combined, node.content):
                    if source_path not in raw_paths:
                        raw_paths.append(source_path)

            for result in self._index.search(combined, top_k=30):
                if result.category == WIKI_CATEGORY:
                    continue
                if result.path not in raw_paths:
                    raw_paths.append(result.path)

            raw_paths = self._rank_raw_paths(combined, raw_paths)

        return self._assemble_wiki_context(selected_wiki, raw_paths, wiki_budget, raw_budget)

    def _query_relevant_source_refs(self, query: str, wiki_content: str) -> list[str]:
        """Return source refs from the wiki lines that best match the user's question."""
        query_lower = query.lower()
        query_terms = set(extract_keywords(query, top_k=20))
        dates = set(_DATE_RE.findall(query))
        dates.update(f"day-{int(value)}" for value in _DAY_RE.findall(query))
        entities = {entity.lower() for entity in _ENTITY_RE.findall(query)}

        scored_refs: list[tuple[float, int, str]] = []
        fallback_refs: list[str] = []

        for line_index, line in enumerate(wiki_content.splitlines()):
            refs = WikiMemory.extract_source_refs(line)
            if not refs:
                continue
            for source_ref in refs:
                if source_ref not in fallback_refs:
                    fallback_refs.append(source_ref)

            line_lower = line.lower()
            line_terms = set(extract_keywords(line, top_k=30))
            score = float(len(query_terms & line_terms))
            if dates and any(date.lower() in line_lower for date in dates):
                score += 8.0
            if entities:
                score += sum(1 for entity in entities if entity in line_lower) * 3.0
            if any(term in line_lower for term in _STATUS_TERMS & set(query_lower.split())):
                score += 2.0
            if any(term in line_lower for term in _CONSTRAINT_TERMS & set(query_lower.split())):
                score += 2.0
            if any(term in line_lower for term in _APPROVAL_EXCEPTION_TERMS & set(query_lower.split())):
                score += 2.0
            if any(term in line_lower for term in _CHANGE_TERMS & set(query_lower.split())):
                score += 2.0

            if score <= 0:
                continue
            for source_ref in refs:
                scored_refs.append((score, line_index, source_ref))

        if not scored_refs:
            return fallback_refs

        refs_by_best_score: dict[str, tuple[float, int]] = {}
        for score, line_index, source_ref in scored_refs:
            current = refs_by_best_score.get(source_ref)
            if current is None or score > current[0] or (score == current[0] and line_index > current[1]):
                refs_by_best_score[source_ref] = (score, line_index)

        return [
            source_ref for source_ref, _ in sorted(
                refs_by_best_score.items(),
                key=lambda item: (-item[1][0], -item[1][1], item[0]),
            )
        ]

    def _rank_raw_paths(self, query: str, raw_paths: list[str]) -> list[str]:
        """Rank raw source paths by how well their content matches the question."""
        query_terms = set(extract_keywords(query, top_k=20))
        dates = set(_DATE_RE.findall(query))
        dates.update(f"day-{int(value)}" for value in _DAY_RE.findall(query))
        entities = {entity.lower() for entity in _ENTITY_RE.findall(query)}

        ranked: list[tuple[float, int, str]] = []
        for path_index, path in enumerate(raw_paths):
            node = self._tree.get(path)
            if not node:
                continue
            haystack = f"{node.path} {node.title} {node.content}".lower()
            node_terms = set(extract_keywords(f"{node.title} {node.content}", top_k=40))
            score = float(len(query_terms & node_terms))
            if dates and any(date.lower() in haystack for date in dates):
                score += 10.0
            if entities:
                score += sum(1 for entity in entities if entity in haystack) * 3.0
            ranked.append((score, path_index, path))

        return [path for _, _, path in sorted(ranked, key=lambda item: (-item[0], item[1]))]

    def _prioritize_wiki_results(
        self,
        query: str,
        wiki_results: list[SearchResult],
    ) -> list[SearchResult]:
        """Boost source-backed wiki pages using generic temporal/entity/status signals."""
        query_lower = query.lower()
        dates = set(_DATE_RE.findall(query))
        dates.update(f"day-{int(value)}" for value in _DAY_RE.findall(query))
        entities = {entity.lower() for entity in _ENTITY_RE.findall(query)}
        statuses = {term for term in _STATUS_TERMS if term in query_lower}
        constraints = {term for term in _CONSTRAINT_TERMS if term in query_lower}
        approvals = {term for term in _APPROVAL_EXCEPTION_TERMS if term in query_lower}
        changes = {term for term in _CHANGE_TERMS if term in query_lower}
        terms = set(extract_keywords(query, top_k=20))

        by_path: dict[str, SearchResult] = {result.path: result for result in wiki_results}
        scored_paths: dict[str, float] = {result.path: result.score for result in wiki_results}

        if dates or entities or statuses or constraints or approvals or changes:
            for path in self._tree.list_paths(WIKI_CATEGORY + "/"):
                node = self._tree.get(path)
                if not node:
                    continue
                haystack = f"{path} {node.title} {node.content}".lower()
                score = 0.0

                if dates and any(date.lower() in haystack for date in dates):
                    score += 40.0
                if entities:
                    entity_hits = sum(1 for entity in entities if entity in haystack)
                    score += entity_hits * 3.0
                if statuses:
                    status_hits = sum(1 for status in statuses if status in haystack)
                    score += status_hits * 2.0
                if constraints:
                    constraint_hits = sum(1 for term in constraints if term in haystack)
                    score += constraint_hits * 2.0
                if approvals:
                    approval_hits = sum(1 for term in approvals if term in haystack)
                    score += approval_hits * 2.0
                if changes:
                    change_hits = sum(1 for term in changes if term in haystack)
                    score += change_hits * 1.5

                if path.startswith("wiki/timeline/") and dates:
                    score += 20.0
                if path.startswith("wiki/sources/") and dates:
                    score += 10.0
                if path.startswith("wiki/status/") and statuses:
                    score += 2.0
                if path.startswith("wiki/threads/") and (entities or terms):
                    score += 1.5
                if path.startswith("wiki/facts/temporal") and (dates or statuses):
                    score += 1.5
                if path == "wiki/facts/constraints" and constraints:
                    score += 6.0
                if path == "wiki/facts/approvals-and-exceptions" and approvals:
                    score += 6.0
                if path == "wiki/facts/change-log" and (changes or len(dates) >= 2):
                    score += 6.0

                score += len(terms & set(extract_keywords(f"{node.title} {node.content}", top_k=30))) * 0.25
                if score <= 0:
                    continue

                if path in scored_paths:
                    scored_paths[path] += score
                    by_path[path].score = scored_paths[path]
                    continue

                by_path[path] = SearchResult(
                    node_id=node.id,
                    path=node.path,
                    title=node.title,
                    category=node.category,
                    score=score,
                    matched_terms=sorted(terms & set(extract_keywords(node.content, top_k=30))),
                )
                scored_paths[path] = score

        return sorted(by_path.values(), key=lambda result: -result.score)[:30]

    def _wiki_context_is_sufficient(
        self,
        combined: str,
        wiki_results: list[SearchResult],
        loaded: LoadedContext,
        budget: int,
    ) -> bool:
        """Decide whether to stop before spending the full wiki ceiling."""
        if not loaded.sources:
            return False

        # If the current rung was not filled, the available evidence fit already.
        if loaded.total_tokens < int(budget * 0.85):
            return True

        query_terms = set(extract_keywords(combined, top_k=15))
        if not query_terms:
            return True

        selected_wiki_paths = set(path for path in loaded.sources if path.startswith("wiki/"))
        selected_results = [result for result in wiki_results if result.path in selected_wiki_paths]
        if not selected_results:
            return False

        matched_terms = set()
        for result in selected_results:
            matched_terms.update(result.matched_terms)
        coverage = len(matched_terms & query_terms) / max(len(query_terms), 1)

        if coverage >= 0.55 and len(selected_results) >= 2:
            return True
        if coverage >= 0.70 and any(not path.startswith("wiki/") for path in loaded.sources):
            return True
        return False

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

    def _select_results_with_budget(
        self,
        results: list[SearchResult],
        budget: int,
    ) -> list[SearchResult]:
        """Select search results without mutating the general branch cache."""
        selected: list[SearchResult] = []
        remaining = budget
        for result in results:
            node = self._tree.get(result.path)
            if not node:
                continue
            tokens = node.token_estimate or estimate_tokens(node.content)
            if selected and remaining - tokens < 0:
                continue
            selected.append(result)
            remaining -= tokens
        return selected

    def _expand_wiki_neighbors(
        self,
        selected: list[SearchResult],
        budget: int,
    ) -> list[SearchResult]:
        """Add directly linked wiki pages when they fit the wiki budget."""
        selected_paths = {result.path for result in selected}
        total_tokens = 0
        for result in selected:
            node = self._tree.get(result.path)
            if node:
                total_tokens += node.token_estimate or estimate_tokens(node.content)

        expanded = list(selected)
        for result in selected:
            node = self._tree.get(result.path)
            if not node:
                continue
            for ref in WikiMemory.extract_wiki_refs(node.content):
                if ref in selected_paths:
                    continue
                ref_node = self._tree.get(ref)
                if not ref_node:
                    continue
                tokens = ref_node.token_estimate or estimate_tokens(ref_node.content)
                if expanded and total_tokens + tokens > budget:
                    continue
                expanded.append(
                    SearchResult(
                        node_id=ref_node.id,
                        path=ref_node.path,
                        title=ref_node.title,
                        category=ref_node.category,
                        score=result.score * 0.5,
                        matched_terms=list(result.matched_terms),
                    ),
                )
                selected_paths.add(ref)
                total_tokens += tokens
        return expanded

    def _assemble_wiki_context(
        self,
        wiki_results: list[SearchResult],
        raw_paths: list[str],
        wiki_budget: int,
        raw_budget: int,
    ) -> LoadedContext:
        parts: list[str] = []
        sources: list[str] = []
        total_tokens = 0

        if wiki_results:
            parts.append("## Compiled Wiki Knowledge")
            wiki_tokens = 0
            for result in wiki_results:
                node = self._tree.get(result.path)
                if not node:
                    continue
                tokens = node.token_estimate or estimate_tokens(node.content)
                if wiki_tokens + tokens > wiki_budget:
                    continue
                parts.append(f"\n### {node.title} [{node.path}]")
                parts.append(node.content)
                sources.append(node.path)
                total_tokens += tokens
                wiki_tokens += tokens

        raw_tokens = 0
        raw_parts: list[str] = []
        for path in raw_paths:
            node = self._tree.get(path)
            if not node:
                continue
            tokens = node.token_estimate or estimate_tokens(node.content)
            if raw_parts and raw_tokens + tokens > raw_budget:
                continue
            raw_parts.append(f"\n### {node.title} [{node.path}]")
            raw_parts.append(node.content)
            if node.path not in sources:
                sources.append(node.path)
            raw_tokens += tokens

        if raw_parts:
            parts.append("\n## Supporting Raw Evidence")
            parts.extend(raw_parts)
            total_tokens += raw_tokens

        return LoadedContext(
            system_prefix="\n".join(parts) if parts else "",
            sources=sources,
            total_tokens=total_tokens,
            branch_paths=sources,
        )

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
