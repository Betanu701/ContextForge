"""Tests for InfiniteContext — context recycling, working sets, and project generation."""

from __future__ import annotations

import pytest
from typing import AsyncGenerator

from contextforge import ContextForge, InfiniteContext, InfiniteContextStats, WorkingSet
from contextforge.index import MemoryIndex
from contextforge.loader import ProactiveLoader
from contextforge.providers.base import LLMProvider
from contextforge.session import SessionStore
from contextforge.tree import KnowledgeTree


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class MockProvider(LLMProvider):
    """Mock LLM provider that echoes back or returns a canned response."""

    def __init__(self):
        self.last_messages: list[dict] = []
        self.response = "Mock response."
        self.call_count = 0

    async def chat(self, messages: list[dict], **kwargs) -> str:
        self.last_messages = messages
        self.call_count += 1
        return self.response

    async def stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        self.last_messages = messages
        self.call_count += 1
        for word in self.response.split():
            yield word + " "


@pytest.fixture
def provider():
    return MockProvider()


@pytest.fixture
def tree():
    t = KnowledgeTree(db_path=":memory:")
    t.open()
    yield t
    t.close()


@pytest.fixture
def session_store():
    s = SessionStore(db_path=":memory:")
    s.open()
    yield s
    s.close()


@pytest.fixture
def index(tree):
    idx = MemoryIndex()
    idx.build_from_tree(tree)
    return idx


@pytest.fixture
def loader(tree, index):
    return ProactiveLoader(tree=tree, index=index, max_context_tokens=4096)


@pytest.fixture
def ic(tree, session_store, index, loader):
    return InfiniteContext(
        tree=tree,
        session=session_store,
        index=index,
        loader=loader,
        max_active_tokens=100_000,
    )


@pytest.fixture
def populated_tree(tree, index):
    """A tree pre-loaded with several knowledge nodes."""
    tree.add("finance/q3", "Q3 Report", "Revenue was $10M in Q3 2024. Profit up 15%.", category="finance")
    tree.add("finance/q2", "Q2 Report", "Revenue was $8M in Q2 2024.", category="finance")
    tree.add("engineering/arch", "Architecture", "Microservices with gRPC. class UserService: pass", category="engineering")
    tree.add("engineering/api", "API Docs", "REST API uses JWT auth. def authenticate(): pass", category="engineering")
    tree.add("hr/handbook", "Handbook", "PTO is 25 days. Remote work allowed.", category="hr")
    index.build_from_tree(tree)
    return tree


# ---------------------------------------------------------------------------
# WorkingSet basics
# ---------------------------------------------------------------------------


class TestWorkingSet:
    def test_working_set_creation(self):
        ws = WorkingSet(
            content="some knowledge",
            node_paths=["a/b", "a/c"],
            total_tokens=100,
            node_ids=[1, 2],
        )
        assert ws.total_tokens == 100
        assert len(ws.node_paths) == 2

    def test_working_set_empty(self):
        ws = WorkingSet(content="", node_paths=[], total_tokens=0)
        assert ws.total_tokens == 0
        assert ws.content == ""


# ---------------------------------------------------------------------------
# KnowledgeTree — new context-window methods
# ---------------------------------------------------------------------------


class TestTreeWorkingSet:
    def test_get_working_set_by_keywords(self, populated_tree):
        ws = populated_tree.get_working_set(["revenue"], max_tokens=50_000)
        assert ws.total_tokens > 0
        assert len(ws.node_paths) > 0
        assert any("finance" in p for p in ws.node_paths)

    def test_get_working_set_respects_budget(self, populated_tree):
        # Very small budget — should limit results
        ws = populated_tree.get_working_set(["revenue", "architecture"], max_tokens=20)
        # At minimum we get 1 node (greedy allows the first even if over budget)
        assert len(ws.node_paths) >= 1

    def test_get_working_set_empty_keywords(self, populated_tree):
        ws = populated_tree.get_working_set([], max_tokens=50_000)
        assert ws.total_tokens == 0
        assert ws.content == ""

    def test_get_working_set_no_matches(self, populated_tree):
        ws = populated_tree.get_working_set(["xyznonexistent"], max_tokens=50_000)
        assert ws.total_tokens == 0


class TestTreeRecycleContext:
    def test_recycle_clears_working_set(self, populated_tree):
        ws = populated_tree.get_working_set(["revenue"], max_tokens=50_000)
        assert ws.content != ""
        populated_tree.recycle_context(ws)
        assert ws.content == ""
        assert ws.node_paths == []
        assert ws.total_tokens == 0

    def test_recycle_preserves_disk_data(self, populated_tree):
        ws = populated_tree.get_working_set(["revenue"], max_tokens=50_000)
        populated_tree.recycle_context(ws)
        # Knowledge still on disk
        node = populated_tree.get("finance/q3")
        assert node is not None
        assert "Revenue" in node.content


class TestCompactedSignatures:
    def test_signatures_from_code(self, tree):
        code = (
            "import os\n"
            "from pathlib import Path\n"
            "\n"
            "class MyService:\n"
            "    def handle_request(self, req):\n"
            "        return req\n"
            "\n"
            "def helper():\n"
            "    pass\n"
        )
        node = tree.add("code/service", "Service", code, category="code")
        sigs = tree.get_compacted_signatures([node.id])
        assert "class MyService" in sigs
        assert "def handle_request" in sigs
        assert "def helper" in sigs
        assert "import os" in sigs
        # Full body should NOT be present
        assert "return req" not in sigs

    def test_signatures_from_prose(self, tree):
        prose = "This is a design document.\nIt describes the architecture.\nMore details here."
        node = tree.add("docs/design", "Design", prose, category="docs")
        sigs = tree.get_compacted_signatures([node.id])
        assert "This is a design document." in sigs

    def test_signatures_multiple_nodes(self, tree):
        n1 = tree.add("a", "A", "class Foo:\n    pass\n", category="code")
        n2 = tree.add("b", "B", "def bar():\n    pass\n", category="code")
        sigs = tree.get_compacted_signatures([n1.id, n2.id])
        assert "class Foo" in sigs
        assert "def bar" in sigs

    def test_signatures_from_content(self, tree):
        code = "class Baz:\n    async def run(self): pass\n"
        sig = tree.get_compacted_signatures_from_content("src/baz.py", code)
        assert "class Baz" in sig
        assert "src/baz.py" in sig

    def test_compacted_vs_full_is_smaller(self, tree):
        big_code = "\n".join(
            [f"def func_{i}():\n    x = {i}\n    return x * 2\n" for i in range(50)]
        )
        node = tree.add("big", "Big Module", big_code, category="code")
        sigs = tree.get_compacted_signatures([node.id])
        assert len(sigs) < len(big_code)


# ---------------------------------------------------------------------------
# InfiniteContext — core behaviour
# ---------------------------------------------------------------------------


class TestInfiniteContextQuery:
    async def test_basic_query(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        response = await ic.query("What was Q3 revenue?", provider)
        assert response == "Mock response."
        assert provider.call_count == 1

    async def test_query_loads_relevant_context(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        await ic.query("What was Q3 revenue?", provider)
        system_msg = provider.last_messages[0]["content"]
        assert "revenue" in system_msg.lower() or "knowledge" in system_msg.lower()

    async def test_query_recycles_after_each_call(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        await ic.query("Q3 revenue?", provider)
        stats_after_1 = ic.get_stats()
        await ic.query("Architecture details?", provider)
        stats_after_2 = ic.get_stats()
        assert stats_after_2.recycles == 2

    async def test_query_saves_to_session(self, ic, populated_tree, index, provider, session_store):
        index.build_from_tree(populated_tree)
        sess = session_store.create_session(session_id="test-s")
        await ic.query("Hello?", provider, session_id="test-s")
        messages = session_store.get_messages("test-s")
        assert len(messages) >= 2  # user + assistant


class TestInfiniteContextPermanent:
    async def test_permanent_context_included(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        await ic.set_permanent_context("You are ContextForge, a helpful AI assistant.")
        await ic.query("Hello!", provider)
        system_msg = provider.last_messages[0]["content"]
        assert "ContextForge" in system_msg

    async def test_permanent_tokens_tracked(self, ic):
        await ic.set_permanent_context("Contract text here.")
        stats = ic.get_stats()
        assert stats.permanent_tokens > 0

    async def test_permanent_context_persists_across_queries(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        await ic.set_permanent_context("PERMANENT_MARKER")
        await ic.query("First query", provider)
        assert "PERMANENT_MARKER" in provider.last_messages[0]["content"]
        await ic.query("Second query", provider)
        assert "PERMANENT_MARKER" in provider.last_messages[0]["content"]


class TestHistoryCompaction:
    async def test_history_accumulates(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        await ic.query("First question", provider)
        await ic.query("Second question", provider)
        assert ic._compacted_history_tokens > 0

    async def test_history_compacts_when_long(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        # Make the compaction threshold very low
        import contextforge.infinite_context as ic_mod
        original = ic_mod._HISTORY_COMPACT_THRESHOLD
        ic_mod._HISTORY_COMPACT_THRESHOLD = 50  # force compaction quickly
        try:
            for i in range(10):
                provider.response = f"Response {i} with some detail to push token count up beyond threshold."
                await ic.query(f"Question {i} about various topics and details?", provider)
            # After many queries, compaction should have run (provider called for summary)
            assert provider.call_count > 10  # extra calls for compaction
        finally:
            ic_mod._HISTORY_COMPACT_THRESHOLD = original


# ---------------------------------------------------------------------------
# InfiniteContext — file / project generation
# ---------------------------------------------------------------------------


class TestFileGeneration:
    async def test_generate_single_file(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        provider.response = "class UserService:\n    def get_user(self): pass\n"
        content = await ic.generate_file(
            file_spec="src/user_service.py",
            contract="Generate clean Python code.",
            previous_signatures="",
            provider=provider,
        )
        assert "class UserService" in content
        stats = ic.get_stats()
        assert stats.recycles >= 1

    async def test_generate_file_includes_contract(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        provider.response = "# generated"
        await ic.generate_file(
            file_spec="src/app.py",
            contract="MUST_USE_TYPING",
            previous_signatures="",
            provider=provider,
        )
        user_msg = provider.last_messages[-1]["content"]
        assert "MUST_USE_TYPING" in user_msg

    async def test_generate_file_includes_previous_sigs(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        provider.response = "# generated"
        await ic.generate_file(
            file_spec="src/b.py",
            contract="",
            previous_signatures="class A:\n    def foo(): pass",
            provider=provider,
        )
        user_msg = provider.last_messages[-1]["content"]
        assert "class A" in user_msg


class TestProjectGeneration:
    async def test_generate_project_returns_all_files(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        provider.response = "class Generated:\n    pass\n"
        files = ["src/a.py", "src/b.py", "src/c.py"]
        results = await ic.generate_project(
            spec="Build a microservice with three modules.",
            files=files,
            provider=provider,
        )
        assert set(results.keys()) == set(files)
        for path, content in results.items():
            assert len(content) > 0

    async def test_project_gen_recycles_per_file(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        provider.response = "def func(): pass\n"
        files = [f"src/mod_{i}.py" for i in range(10)]
        await ic.generate_project(
            spec="Generate 10 modules.",
            files=files,
            provider=provider,
        )
        stats = ic.get_stats()
        assert stats.recycles >= 10

    async def test_project_gen_100_files(self, ic, populated_tree, index, provider):
        """Simulate a large project — 100 files. VRAM stays constant."""
        index.build_from_tree(populated_tree)
        provider.response = "def generated_func(): return True\n"
        files = [f"src/module_{i:03d}.py" for i in range(100)]
        results = await ic.generate_project(
            spec="A large project with 100 modules.",
            files=files,
            provider=provider,
        )
        assert len(results) == 100
        stats = ic.get_stats()
        assert stats.recycles >= 100

    async def test_project_gen_cleans_up_spec_node(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        provider.response = "# code"
        await ic.generate_project(
            spec="Spec text.",
            files=["a.py"],
            provider=provider,
        )
        assert populated_tree.get("_project_spec") is None


# ---------------------------------------------------------------------------
# Stats tracking
# ---------------------------------------------------------------------------


class TestStats:
    def test_initial_stats_zeroed(self, ic):
        stats = ic.get_stats()
        assert stats.active_tokens == 0
        assert stats.recycles == 0
        assert stats.peak_active == 0

    async def test_stats_after_query(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        await ic.query("revenue?", provider)
        stats = ic.get_stats()
        assert stats.recycles == 1
        assert stats.disk_tokens > 0

    async def test_peak_active_tracked(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        await ic.query("revenue architecture handbook?", provider)
        stats = ic.get_stats()
        assert stats.peak_active > 0

    async def test_compression_ratio(self, ic, populated_tree, index, provider):
        index.build_from_tree(populated_tree)
        await ic.query("something?", provider)
        stats = ic.get_stats()
        assert 0 <= stats.compression_ratio <= 1.0 or stats.disk_tokens == 0

    async def test_permanent_tokens_in_stats(self, ic):
        await ic.set_permanent_context("Permanent knowledge block.")
        stats = ic.get_stats()
        assert stats.permanent_tokens > 0

    def test_stats_dataclass_fields(self):
        s = InfiniteContextStats()
        assert s.active_tokens == 0
        assert s.disk_tokens == 0
        assert s.permanent_tokens == 0
        assert s.compression_ratio == 0.0
        assert s.recycles == 0
        assert s.peak_active == 0


# ---------------------------------------------------------------------------
# Integration with ContextForge layer
# ---------------------------------------------------------------------------


class TestLayerIntegration:
    def test_layer_has_infinite_property(self, provider):
        with ContextForge(db_path=":memory:", llm_provider=provider) as layer:
            assert layer.infinite is not None
            assert isinstance(layer.infinite, InfiniteContext)

    def test_layer_stats_include_infinite(self, provider):
        with ContextForge(db_path=":memory:", llm_provider=provider) as layer:
            stats = layer.stats
            assert "infinite_context" in stats
            assert "active_tokens" in stats["infinite_context"]
            assert "recycles" in stats["infinite_context"]

    async def test_layer_set_permanent_context(self, provider):
        layer = ContextForge(db_path=":memory:", llm_provider=provider)
        try:
            await layer.set_permanent_context("You are ContextForge.")
            stats = layer.stats
            assert stats["infinite_context"]["permanent_tokens"] > 0
        finally:
            layer.close()

    async def test_existing_chat_still_works(self, provider):
        layer = ContextForge(db_path=":memory:", llm_provider=provider)
        try:
            await layer.ingest_text("Revenue was $10M", title="Finance", category="finance")
            response = await layer.chat("What was revenue?")
            assert response == "Mock response."
        finally:
            layer.close()
