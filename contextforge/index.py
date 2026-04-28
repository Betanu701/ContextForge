"""MemoryIndex — in-memory inverted index for O(1) keyword → node lookup."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .utils import extract_keywords


@dataclass
class IndexEntry:
    """A single entry in the inverted index."""

    node_id: int
    path: str
    title: str
    category: str
    term_frequency: float = 0.0


@dataclass
class SearchResult:
    """A scored search result."""

    node_id: int
    path: str
    title: str
    category: str
    score: float
    matched_terms: list[str] = field(default_factory=list)


class MemoryIndex:
    """In-memory inverted index built from KnowledgeTree nodes.

    Provides BM25-scored keyword search with O(1) term lookup.
    Rebuilt from the database on startup; no persistence of its own.
    """

    def __init__(self) -> None:
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

    @property
    def num_docs(self) -> int:
        return self._num_docs

    @property
    def num_terms(self) -> int:
        return len(self._index)

    def add_document(
        self,
        node_id: int,
        path: str,
        title: str,
        category: str,
        content: str,
    ) -> None:
        """Index a document's content."""
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
            )
            self._index[term].append(entry)

        self._num_docs += 1
        total_length = sum(self._doc_lengths.values())
        self._avg_dl = total_length / self._num_docs if self._num_docs > 0 else 0

    def remove_document(self, node_id: int) -> None:
        """Remove a document from the index."""
        terms = self._node_terms.pop(node_id, set())
        for term in terms:
            self._index[term] = [e for e in self._index[term] if e.node_id != node_id]
            if not self._index[term]:
                del self._index[term]
        self._doc_lengths.pop(node_id, None)
        self._num_docs = max(0, self._num_docs - 1)
        if self._num_docs > 0:
            self._avg_dl = sum(self._doc_lengths.values()) / self._num_docs
        else:
            self._avg_dl = 0

    def search(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search the index using BM25 scoring.

        Returns the top-k results sorted by relevance score.
        """
        terms = extract_keywords(query, top_k=15)
        if not terms:
            return []

        scores: dict[int, float] = defaultdict(float)
        matched: dict[int, list[str]] = defaultdict(list)
        entry_info: dict[int, IndexEntry] = {}

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

        results = []
        for node_id, score in sorted(scores.items(), key=lambda x: -x[1])[:top_k]:
            info = entry_info[node_id]
            results.append(
                SearchResult(
                    node_id=node_id,
                    path=info.path,
                    title=info.title,
                    category=info.category,
                    score=score,
                    matched_terms=matched[node_id],
                )
            )

        return results

    def lookup(self, term: str) -> list[IndexEntry]:
        """Direct O(1) lookup of a single term."""
        return self._index.get(term.lower(), [])

    def build_from_tree(self, tree) -> int:
        """Rebuild the entire index from a KnowledgeTree instance.

        Returns the number of documents indexed.
        """
        self.clear()
        rows = tree.conn.execute(
            "SELECT id, path, title, content, category FROM knowledge_nodes"
        ).fetchall()
        for row in rows:
            self.add_document(
                node_id=row[0],
                path=row[1],
                title=row[2],
                category=row[4],
                content=row[3],
            )
        return len(rows)

    def clear(self) -> None:
        """Reset the index to empty."""
        self._index.clear()
        self._node_terms.clear()
        self._doc_lengths.clear()
        self._num_docs = 0
        self._avg_dl = 0.0
