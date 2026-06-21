"""MemoryIndex — hyper-dense local memory index with SQ8 semantic retrieval."""

from __future__ import annotations

import math
import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .hyperdense import (
    HyperDenseMemoryConfig,
    SQ8VectorIndex,
    normalize_temporal_metadata,
)
from .utils import extract_keywords


@dataclass
class IndexEntry:
    """A single entry in the compatibility keyword index."""

    node_id: int
    path: str
    title: str
    category: str
    term_frequency: float = 0.0
    timestamp: float = 0.0
    turn_sequence: int = 0
    state_anchors: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class SearchResult:
    """A scored semantic search result with strict temporal metadata."""

    node_id: int
    path: str
    title: str
    category: str
    score: float
    matched_terms: list[str] = field(default_factory=list)
    timestamp: float = 0.0
    turn_sequence: int = 0
    state_anchors: tuple[str, ...] = field(default_factory=tuple)


class MemoryIndex:
    """In-memory SQ8 semantic index built from KnowledgeTree nodes.

    Provides quantized semantic top-k retrieval with a small keyword
    compatibility layer for direct lookup and lexical tie-breaking.
    Rebuilt from the database on startup; no persistence of its own.
    """

    def __init__(self, config: Optional[HyperDenseMemoryConfig] = None) -> None:
        self.config = config or HyperDenseMemoryConfig()
        self._semantic = SQ8VectorIndex(self.config)
        # term → list of IndexEntry
        self._index: dict[str, list[IndexEntry]] = defaultdict(list)
        # node_id → set of terms
        self._node_terms: dict[int, set[str]] = defaultdict(set)
        # node_id → document length (term count)
        self._doc_lengths: dict[int, int] = {}
        # Total documents
        self._num_docs: int = 0
        # Average document length
        self._avg_dl: float = 0.0
        # BM25 parameters
        self._k1: float = 1.5
        self._b: float = 0.75
        # node_id → document payload for SQ8 rebuilds
        self._documents: dict[int, tuple[str, str, str, str, float, int, tuple[str, ...]]] = {}

    @property
    def num_docs(self) -> int:
        return self._num_docs

    @property
    def num_terms(self) -> int:
        return len(self._index)

    @property
    def quantized_bytes(self) -> int:
        """RAM used by the SQ8 vector matrix."""
        return self._semantic.byte_size

    def add_document(
        self,
        node_id: int,
        path: str,
        title: str,
        category: str,
        content: str,
        metadata: Optional[dict] = None,
        timestamp: Optional[float] = None,
        turn_sequence: Optional[int] = None,
    ) -> None:
        """Index a document's content."""
        temporal = normalize_temporal_metadata(
            metadata,
            timestamp=timestamp,
            turn_sequence=turn_sequence,
            fallback_sequence=node_id,
            content=content,
            path=path,
        )
        self.remove_document(node_id)
        self._documents[node_id] = (
            path,
            title,
            category,
            content,
            temporal.timestamp,
            temporal.turn_sequence,
            temporal.state_anchors,
        )

        keywords = extract_keywords(content, top_k=50)
        title_keywords = extract_keywords(title, top_k=10)
        all_terms = set(keywords) | set(title_keywords) | {category.lower()}

        # Count term frequencies
        content_lower = content.lower()
        term_counts: dict[str, int] = {}
        for term in all_terms:
            count = content_lower.count(term)
            # Boost title matches
            if term in set(title_keywords):
                count += 5
            term_counts[term] = max(count, 1)

        doc_length = sum(term_counts.values())
        self._doc_lengths[node_id] = doc_length
        self._node_terms[node_id] = all_terms

        for term, count in term_counts.items():
            entry = IndexEntry(
                node_id=node_id,
                path=path,
                title=title,
                category=category,
                term_frequency=count / doc_length if doc_length > 0 else 0,
                timestamp=temporal.timestamp,
                turn_sequence=temporal.turn_sequence,
                state_anchors=temporal.state_anchors,
            )
            self._index[term].append(entry)

        self._num_docs += 1
        total_length = sum(self._doc_lengths.values())
        self._avg_dl = total_length / self._num_docs if self._num_docs > 0 else 0
        self._rebuild_semantic()

    def remove_document(self, node_id: int) -> None:
        """Remove a document from the index."""
        existed = node_id in self._documents or node_id in self._node_terms
        terms = self._node_terms.pop(node_id, set())
        for term in terms:
            self._index[term] = [e for e in self._index[term] if e.node_id != node_id]
            if not self._index[term]:
                del self._index[term]
        self._doc_lengths.pop(node_id, None)
        self._documents.pop(node_id, None)
        if existed:
            self._num_docs = max(0, self._num_docs - 1)
        if self._num_docs > 0:
            self._avg_dl = sum(self._doc_lengths.values()) / self._num_docs
        else:
            self._avg_dl = 0
        self._rebuild_semantic()

    def search(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search the SQ8 semantic index with lexical tie-breaking.

        Returns top-k candidates sorted by semantic relevance. Callers that
        assemble context should then run a chronological pass.
        """
        terms = extract_keywords(query, top_k=15)
        if not query.strip() or not self._documents:
            return []

        scores, matched, entry_info = self._keyword_scores(terms, category)
        if terms and not scores:
            return []

        semantic_limit = max(top_k, top_k * self.config.search_multiplier)
        semantic_hits = self._semantic.search(query, top_k=semantic_limit)
        if not semantic_hits and not scores:
            return []

        combined: dict[int, float] = defaultdict(float)
        for raw_id, semantic_score in semantic_hits:
            node_id = int(raw_id)
            doc = self._documents.get(node_id)
            if not doc:
                continue
            if category and doc[2] != category:
                continue
            combined[node_id] += semantic_score * 10.0

        for node_id, keyword_score in scores.items():
            combined[node_id] += keyword_score

        if not combined:
            return []

        results: list[SearchResult] = []
        for node_id, score in sorted(combined.items(), key=lambda x: -x[1])[:top_k]:
            doc = self._documents.get(node_id)
            if not doc:
                continue
            path, title, doc_category, _content, timestamp, turn_sequence, anchors = doc
            info = entry_info.get(node_id)
            results.append(
                SearchResult(
                    node_id=node_id,
                    path=info.path if info else path,
                    title=info.title if info else title,
                    category=info.category if info else doc_category,
                    score=score,
                    matched_terms=matched.get(node_id, []),
                    timestamp=timestamp,
                    turn_sequence=turn_sequence,
                    state_anchors=anchors,
                )
            )

        return results

    def _keyword_scores(
        self,
        terms: list[str],
        category: Optional[str],
    ) -> tuple[dict[int, float], dict[int, list[str]], dict[int, IndexEntry]]:
        scores: dict[int, float] = defaultdict(float)
        matched: dict[int, list[str]] = defaultdict(list)
        entry_info: dict[int, IndexEntry] = {}
        if not terms:
            return scores, matched, entry_info

        for term in terms:
            entries = self._index.get(term, [])
            if not entries:
                continue

            # IDF component
            df = len(entries)
            idf = math.log((self._num_docs - df + 0.5) / (df + 0.5) + 1.0)

            for entry in entries:
                if category and entry.category != category:
                    continue

                # BM25 TF component
                dl = self._doc_lengths.get(entry.node_id, 1)
                tf = entry.term_frequency * dl  # recover raw count
                tf_norm = (tf * (self._k1 + 1)) / (
                    tf + self._k1 * (1 - self._b + self._b * dl / max(self._avg_dl, 1))
                )

                scores[entry.node_id] += idf * tf_norm
                matched[entry.node_id].append(term)
                entry_info[entry.node_id] = entry

        return scores, matched, entry_info

    def lookup(self, term: str) -> list[IndexEntry]:
        """Direct O(1) lookup of a single term."""
        return self._index.get(term.lower(), [])

    def build_from_tree(self, tree) -> int:
        """Rebuild the entire index from a KnowledgeTree instance.

        Returns the number of documents indexed.
        """
        self.clear()
        rows = tree.conn.execute(
            "SELECT id, path, title, content, category, metadata_json FROM knowledge_nodes ORDER BY id"
        ).fetchall()
        for row in rows:
            try:
                metadata = json.loads(row[5] or "{}")
            except json.JSONDecodeError:
                metadata = {}
            self.add_document(
                node_id=row[0],
                path=row[1],
                title=row[2],
                category=row[4],
                content=row[3],
                metadata=metadata,
            )
        return len(rows)

    def clear(self) -> None:
        """Reset the index to empty."""
        self._index.clear()
        self._node_terms.clear()
        self._doc_lengths.clear()
        self._documents.clear()
        self._num_docs = 0
        self._avg_dl = 0.0
        self._semantic.clear()

    def _rebuild_semantic(self) -> None:
        documents = [
            (node_id, f"{path}\n{title}\n{category}\n{content}")
            for node_id, (path, title, category, content, *_rest) in self._documents.items()
        ]
        self._semantic.build(documents)
