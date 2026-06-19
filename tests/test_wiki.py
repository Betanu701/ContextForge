"""Tests for compiled wiki memory."""

from __future__ import annotations

import pytest
from typing import AsyncGenerator

from contextforge import ContextForge
from contextforge.index import MemoryIndex
from contextforge.loader import ProactiveLoader
from contextforge.providers.base import LLMProvider
from contextforge.tree import KnowledgeTree
from contextforge.wiki import WIKI_CATEGORY, WikiMemory


class MockProvider(LLMProvider):
    def __init__(self):
        self.last_messages: list[dict] = []
        self.response = "Mock wiki response."

    async def chat(self, messages: list[dict], **kwargs) -> str:
        self.last_messages = messages
        return self.response

    async def stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        self.last_messages = messages
        yield self.response


@pytest.fixture
def wiki_setup():
    tree = KnowledgeTree(":memory:")
    tree.open()
    index = MemoryIndex()
    loader = ProactiveLoader(tree, index, max_context_tokens=4096)
    wiki = WikiMemory(tree)
    yield tree, index, loader, wiki
    tree.close()


class TestWikiCompilation:
    def test_compile_source_creates_source_backed_pages(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        source = tree.add(
            "memory/day_42",
            "Day 42",
            "On day 42, Jamie approved the Caldwell launch. The Europe rollout was canceled.",
            category="memory",
        )
        result = wiki.compile_source_node(source)
        index.build_from_tree(tree)

        paths = tree.list_paths("wiki/")
        assert "wiki/index" in paths
        assert "wiki/log" in paths
        assert "wiki/sources/memory-day-42" in paths
        assert "wiki/entities/jamie" in paths
        assert "wiki/decisions/decision-log" in paths
        assert "wiki/facts/negative-facts" in paths
        assert "memory/day_42" in tree.get("wiki/entities/jamie").content
        assert "wiki/entities/jamie" in result.touched_pages

    def test_compile_existing_skips_wiki_nodes(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        tree.add("memory/day_1", "Day 1", "Riley confirmed the budget.", category="memory")
        compiled = wiki.compile_existing()
        assert compiled == 1
        compiled_again = wiki.compile_existing()
        assert compiled_again == 1

    def test_lint_reports_missing_index(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        issues = wiki.lint()
        assert any(issue.path == "wiki/index" for issue in issues)


class TestWikiRetrieval:
    def test_load_wiki_prefers_compiled_pages_and_evidence(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        source = tree.add(
            "memory/day_42",
            "Day 42",
            "Jamie approved the Caldwell launch. The Europe rollout was canceled.",
            category="memory",
        )
        wiki.compile_source_node(source)
        index.build_from_tree(tree)

        loaded = loader.load_wiki("What happened with the Europe rollout?")
        assert "Compiled Wiki Knowledge" in loaded.system_prefix
        assert "Supporting Raw Evidence" in loaded.system_prefix
        assert any(path.startswith("wiki/") for path in loaded.sources)
        assert "memory/day_42" in loaded.sources

    def test_load_wiki_respects_wiki_budget(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        loader.max_context_tokens = 600
        tree.add(
            "wiki/page-one",
            "Page One",
            "alpha " * 120,
            category=WIKI_CATEGORY,
        )
        tree.add(
            "wiki/page-two",
            "Page Two",
            "alpha " * 120,
            category=WIKI_CATEGORY,
        )
        index.build_from_tree(tree)

        loaded = loader.load_wiki("alpha", wiki_token_ratio=0.50, include_raw_evidence=False)

        assert loaded.total_tokens <= 300

    def test_load_wiki_stops_below_ceiling_when_evidence_is_sufficient(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        loader.max_context_tokens = 2000
        for page_number in range(1, 8):
            tree.add(
                f"wiki/page-{page_number}",
                f"Page {page_number}",
                "alpha beta " * 180,
                category=WIKI_CATEGORY,
            )
        index.build_from_tree(tree)

        loaded = loader.load_wiki("alpha beta", include_raw_evidence=False)

        assert loaded.total_tokens <= 1000


class TestContextForgeWikiAPI:
    @pytest.mark.asyncio
    async def test_ingest_wiki_text_and_chat_use_wiki(self):
        provider = MockProvider()
        forge = ContextForge(db_path=":memory:", llm_provider=provider)
        try:
            result = await forge.ingest_wiki_text(
                "Jamie approved the Caldwell launch. The Europe rollout was canceled.",
                title="Day 42",
                category="memory",
            )
            assert result.pages_created
            response = await forge.chat("What happened with the Europe rollout?", use_wiki=True)
            assert response == "Mock wiki response."
            system_message = provider.last_messages[0]["content"]
            assert "Compiled Wiki Knowledge" in system_message
            assert "Supporting Raw Evidence" in system_message
        finally:
            forge.close()
