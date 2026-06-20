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

    def test_compile_source_creates_temporal_status_and_thread_pages(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        source = tree.add(
            "memory/day_120",
            "Day 120",
            (
                "On 2026-05-20, Project Condor financing remained blocked because "
                "legal approval was not granted. Jamie confirmed the launch memo was unchanged."
            ),
            category="memory",
        )
        result = wiki.compile_source_node(source)

        assert "wiki/facts/temporal-state" in result.touched_pages
        assert "wiki/status/blocked" in result.touched_pages
        assert "wiki/threads/project-condor" in result.touched_pages
        temporal = tree.get("wiki/facts/temporal-state")
        blocked = tree.get("wiki/status/blocked")
        thread = tree.get("wiki/threads/project-condor")
        assert temporal is not None
        assert blocked is not None
        assert thread is not None
        assert "2026-05-20" in temporal.content
        assert "Status: blocked" in blocked.content
        assert "memory/day_120" in thread.content

    def test_compile_source_uses_structured_temporal_metadata(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        source = tree.add(
            "memory/2026-05-20",
            "Memory 2026-05-20",
            "Project Condor financing remained blocked pending legal approval.",
            category="memory",
            metadata={
                "source_date": "2026-05-20",
                "temporal_anchors": [
                    {"kind": "sequence", "unit": "day", "value": 120}
                ],
            },
        )
        result = wiki.compile_source_node(source)

        assert "wiki/timeline/2026-05-20" in result.touched_pages
        source_page = tree.get("wiki/sources/memory-2026-05-20")
        temporal = tree.get("wiki/facts/temporal-state")
        assert source_page is not None
        assert temporal is not None
        assert "2026-05-20" in source_page.content
        assert "day-120" in source_page.content
        assert "day-120" in temporal.content

    def test_compile_source_creates_user_semantic_fact_pages(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        source = tree.add(
            "memory/2026-05-21",
            "Memory 2026-05-21",
            (
                "Document completeness remained the gating item before outside adviser outreach. "
                "No disclosure exceptions were granted, and distribution stayed pending Jamie review. "
                "The ERP focus shifted from rollout tracking to post-close follow-through."
            ),
            category="memory",
            metadata={"source_date": "2026-05-21"},
        )
        result = wiki.compile_source_node(source)

        assert "wiki/facts/constraints" in result.touched_pages
        assert "wiki/facts/approvals-and-exceptions" in result.touched_pages
        assert "wiki/facts/change-log" in result.touched_pages
        assert "gating item" in tree.get("wiki/facts/constraints").content
        assert "disclosure exceptions" in tree.get("wiki/facts/approvals-and-exceptions").content
        assert "shifted from rollout tracking" in tree.get("wiki/facts/change-log").content

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

    def test_load_wiki_uses_temporal_status_and_thread_memory(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        source = tree.add(
            "memory/day_120",
            "Day 120",
            (
                "On 2026-05-20, Project Condor financing remained blocked because "
                "legal approval was not granted. Jamie confirmed the launch memo was unchanged."
            ),
            category="memory",
        )
        wiki.compile_source_node(source)
        index.build_from_tree(tree)

        loaded = loader.load_wiki("What was the status of Project Condor financing on 2026-05-20?")

        assert "wiki/timeline/2026-05-20" in loaded.sources
        assert "wiki/sources/memory-day-120" in loaded.sources
        assert "wiki/status/blocked" in loaded.sources
        assert "memory/day_120" in loaded.sources
        assert "Status: blocked" in loaded.system_prefix

    def test_load_wiki_uses_user_semantic_fact_pages(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        source = tree.add(
            "memory/2026-05-21",
            "Memory 2026-05-21",
            (
                "Document completeness remained the gating item before outside adviser outreach. "
                "No disclosure exceptions were granted, and distribution stayed pending Jamie review. "
                "The ERP focus shifted from rollout tracking to post-close follow-through."
            ),
            category="memory",
            metadata={"source_date": "2026-05-21"},
        )
        wiki.compile_source_node(source)
        index.build_from_tree(tree)

        gating = loader.load_wiki("What was the gating item before outside adviser outreach?")
        exceptions = loader.load_wiki("Were any disclosure exceptions granted?")
        shift = loader.load_wiki("How did the ERP focus shift from rollout tracking to post-close follow-through?")

        assert "wiki/facts/constraints" in gating.sources
        assert "wiki/facts/approvals-and-exceptions" in exceptions.sources
        assert "wiki/facts/change-log" in shift.sources

    def test_load_wiki_prioritizes_source_refs_from_matching_fact_lines(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        tree.add(
            "memory/2026-01-08",
            "Memory 2026-01-08",
            "Jamie kept Jordan at read-only inbox and calendar access.",
            category="memory",
        )
        tree.add(
            "memory/2026-03-01",
            "Memory 2026-03-01",
            (
                "Jamie granted Jordan send-on-behalf authority for routine logistics, "
                "but did not grant send-as authority or independent expense approval."
            ),
            category="memory",
        )
        tree.add(
            "wiki/facts/approvals-and-exceptions",
            "Approvals and Exceptions",
            (
                "# Approvals and Exceptions\n\n"
                "Type: approval-exception-facts\n\n"
                "## Sources\n"
                "- memory/2026-01-08\n"
                "- memory/2026-03-01\n\n"
                "## Facts\n"
                "- Time: 2026-01-08 | Approval/Exception: Jamie kept Jordan at read-only access. "
                "(Source: memory/2026-01-08)\n"
                "- Time: 2026-03-01 | Approval/Exception: Jamie granted send-on-behalf for "
                "routine logistics but withheld send-as and independent expense approval. "
                "(Source: memory/2026-03-01)\n"
            ),
            category=WIKI_CATEGORY,
        )
        index.build_from_tree(tree)

        loaded = loader.load_wiki(
            "After the 2026-03-01 authorization expansion, what authority was still not granted?"
        )

        assert "memory/2026-03-01" in loaded.sources
        assert loaded.sources.index("memory/2026-03-01") < loaded.sources.index("memory/2026-01-08")

    def test_load_wiki_ranks_raw_sources_by_question_match(self, wiki_setup):
        tree, index, loader, wiki = wiki_setup
        tree.add(
            "memory/2026-02-26",
            "Memory 2026-02-26",
            "Caldwell remained in active recovery mode with sponsor-review timing still pending.",
            category="memory",
        )
        tree.add(
            "memory/2026-02-27",
            "Memory 2026-02-27",
            "Caldwell service stabilized and the remediation plan was accepted for closeout.",
            category="memory",
        )
        tree.add(
            "wiki/facts/change-log",
            "Change Log",
            (
                "# Change Log\n\n"
                "Type: change-facts\n\n"
                "## Sources\n"
                "- memory/2026-02-26\n"
                "- memory/2026-02-27\n\n"
                "## Facts\n"
                "- Time: 2026-02-26 | Change: Caldwell remained in active recovery mode. "
                "(Source: memory/2026-02-26)\n"
                "- Time: 2026-02-27 | Change: Caldwell service stabilized and moved to closeout. "
                "(Source: memory/2026-02-27)\n"
            ),
            category=WIKI_CATEGORY,
        )
        index.build_from_tree(tree)

        loaded = loader.load_wiki("What changed for Caldwell on 2026-02-27?")

        assert "memory/2026-02-27" in loaded.sources
        assert loaded.sources.index("memory/2026-02-27") < loaded.sources.index("memory/2026-02-26")


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
