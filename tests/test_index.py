"""Tests for MemoryIndex — keyword lookup, extraction, scoring."""

from __future__ import annotations

import pytest
from contextforge.index import MemoryIndex
from contextforge.tree import KnowledgeTree


@pytest.fixture
def index():
    return MemoryIndex()


@pytest.fixture
def populated_index(index: MemoryIndex):
    index.add_document(1, "finance/q3", "Q3 Report", "finance",
                       "Revenue was $10 million in Q3 2024. Operating costs decreased.")
    index.add_document(2, "finance/q2", "Q2 Report", "finance",
                       "Revenue was $8 million in Q2 2024. Growth was steady.")
    index.add_document(3, "engineering/arch", "Architecture", "engineering",
                       "Microservices architecture with event-driven communication.")
    index.add_document(4, "hr/handbook", "Employee Handbook", "hr",
                       "Vacation policy is 20 days per year. Remote work allowed.")
    return index


class TestAddRemove:
    def test_add_document(self, index: MemoryIndex):
        index.add_document(1, "test/doc", "Test Doc", "test", "Hello world test content")
        assert index.num_docs == 1
        assert index.num_terms > 0

    def test_remove_document(self, index: MemoryIndex):
        index.add_document(1, "test/doc", "Test Doc", "test", "Hello world test content")
        index.remove_document(1)
        assert index.num_docs == 0

    def test_clear(self, populated_index: MemoryIndex):
        assert populated_index.num_docs == 4
        populated_index.clear()
        assert populated_index.num_docs == 0
        assert populated_index.num_terms == 0


class TestLookup:
    def test_direct_lookup(self, populated_index: MemoryIndex):
        entries = populated_index.lookup("revenue")
        assert len(entries) >= 2
        paths = {e.path for e in entries}
        assert "finance/q3" in paths
        assert "finance/q2" in paths

    def test_lookup_missing(self, populated_index: MemoryIndex):
        entries = populated_index.lookup("xyznonexistent")
        assert entries == []


class TestSearch:
    def test_search_basic(self, populated_index: MemoryIndex):
        results = populated_index.search("revenue Q3")
        assert len(results) > 0
        paths = {r.path for r in results}
        assert "finance/q3" in paths

    def test_search_ranking(self, populated_index: MemoryIndex):
        results = populated_index.search("revenue million")
        assert len(results) >= 2
        # Q3 should rank high since it has both terms
        paths = [r.path for r in results]
        assert "finance/q3" in paths

    def test_search_category_filter(self, populated_index: MemoryIndex):
        results = populated_index.search("policy", category="hr")
        assert len(results) == 1
        assert results[0].category == "hr"

    def test_search_no_results(self, populated_index: MemoryIndex):
        results = populated_index.search("xyznonexistentquery")
        assert results == []

    def test_search_matched_terms(self, populated_index: MemoryIndex):
        results = populated_index.search("architecture microservices")
        assert len(results) > 0
        assert len(results[0].matched_terms) > 0

    def test_search_empty_query(self, populated_index: MemoryIndex):
        results = populated_index.search("")
        assert results == []

    def test_search_top_k(self, populated_index: MemoryIndex):
        results = populated_index.search("revenue", top_k=1)
        assert len(results) == 1


class TestBuildFromTree:
    def test_build_from_tree(self):
        tree = KnowledgeTree(":memory:")
        tree.open()
        tree.add("a", "Doc A", "Machine learning algorithms for classification")
        tree.add("b", "Doc B", "Database optimization and query performance")

        index = MemoryIndex()
        count = index.build_from_tree(tree)
        assert count == 2
        assert index.num_docs == 2

        results = index.search("machine learning")
        assert len(results) > 0
        assert results[0].path == "a"

        tree.close()
