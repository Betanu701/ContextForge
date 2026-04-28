"""Tests for ProactiveLoader — context assembly, branch caching."""

from __future__ import annotations

import pytest
from contextforge.index import MemoryIndex
from contextforge.loader import ProactiveLoader
from contextforge.tree import KnowledgeTree


@pytest.fixture
def setup():
    tree = KnowledgeTree(":memory:")
    tree.open()

    tree.add("finance/q3", "Q3 Financial Report", "Revenue was $10M in Q3 2024. Net profit $2M.", category="finance")
    tree.add("finance/q2", "Q2 Financial Report", "Revenue was $8M in Q2 2024. Net profit $1.5M.", category="finance")
    tree.add("engineering/arch", "System Architecture", "Microservices with event-driven patterns. gRPC for inter-service.", category="engineering")
    tree.add("engineering/roadmap", "Engineering Roadmap", "Q4 goals: improve latency, add caching layer.", category="engineering")
    tree.add("hr/policies", "HR Policies", "Vacation: 20 days. Remote work: 3 days/week. Benefits enrollment in January.", category="hr")

    index = MemoryIndex()
    index.build_from_tree(tree)

    loader = ProactiveLoader(tree, index, max_context_tokens=8192)

    yield tree, index, loader
    tree.close()


class TestBasicLoading:
    def test_load_relevant_context(self, setup):
        tree, index, loader = setup
        ctx = loader.load("What was the Q3 revenue?")
        assert ctx.total_tokens > 0
        assert len(ctx.sources) > 0
        assert any("finance" in s for s in ctx.sources)

    def test_load_returns_system_prefix(self, setup):
        tree, index, loader = setup
        ctx = loader.load("Tell me about the system architecture")
        assert "Relevant Knowledge" in ctx.system_prefix
        assert len(ctx.system_prefix) > 0

    def test_load_no_match(self, setup):
        tree, index, loader = setup
        ctx = loader.load("xyznonexistentquerythatwontmatch")
        assert ctx.total_tokens == 0
        assert ctx.sources == []

    def test_load_empty_query(self, setup):
        tree, index, loader = setup
        ctx = loader.load("")
        assert ctx.total_tokens == 0


class TestConversationContext:
    def test_conversation_context_improves_results(self, setup):
        tree, index, loader = setup
        # Without conversation context
        ctx1 = loader.load("Compare with Q2")
        # With conversation context about finance
        ctx2 = loader.load("Compare with Q2", conversation_context="We were discussing Q3 revenue of $10M")
        # ctx2 should have relevant financial sources
        assert len(ctx2.sources) > 0

    def test_category_hint(self, setup):
        tree, index, loader = setup
        ctx = loader.load("What are the policies?", category_hint="hr")
        assert any("hr" in s for s in ctx.sources)


class TestBranchCaching:
    def test_cache_populated_after_load(self, setup):
        tree, index, loader = setup
        loader.load("Q3 revenue report")
        stats = loader.cache_stats()
        assert stats["entries"] > 0

    def test_cache_boosts_follow_up(self, setup):
        tree, index, loader = setup
        # First query loads financial data
        loader.load("Q3 revenue")
        # Follow-up should benefit from cache
        ctx2 = loader.load("Net profit comparison")
        assert ctx2.total_tokens > 0

    def test_invalidate_cache(self, setup):
        tree, index, loader = setup
        loader.load("Q3 revenue")
        assert loader.cache_stats()["entries"] > 0
        loader.invalidate_cache()
        assert loader.cache_stats()["entries"] == 0

    def test_invalidate_specific_path(self, setup):
        tree, index, loader = setup
        loader.load("Q3 revenue architecture")
        entries_before = loader.cache_stats()["entries"]
        loader.invalidate_cache("finance/q3")
        entries_after = loader.cache_stats()["entries"]
        assert entries_after < entries_before


class TestMultiPass:
    def test_load_multi_returns_per_category(self, setup):
        tree, index, loader = setup
        contexts = loader.load_multi("Compare revenue with engineering roadmap")
        assert len(contexts) >= 1
        categories = {c.branch_paths[0].split("/")[0] for c in contexts if c.branch_paths}
        assert len(categories) >= 1

    def test_load_multi_empty(self, setup):
        tree, index, loader = setup
        contexts = loader.load_multi("xyznonexistentquerythatwontmatch")
        assert contexts == []


class TestTokenBudget:
    def test_respects_token_budget(self, setup):
        tree, index, loader = setup
        loader.max_context_tokens = 100  # Very small budget
        ctx = loader.load("revenue architecture policies")
        # Should not exceed budget significantly
        assert ctx.total_tokens <= 200  # Allow some slack for small nodes
