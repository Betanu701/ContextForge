"""Tests for ContextForge — full integration test with mock provider."""

from __future__ import annotations

import pytest
from typing import AsyncGenerator

from contextforge import ContextForge
from contextforge.providers.base import LLMProvider


class MockProvider(LLMProvider):
    """A mock LLM provider for testing."""

    def __init__(self):
        self.last_messages: list[dict] = []
        self.response = "This is a mock response."

    async def chat(self, messages: list[dict], **kwargs) -> str:
        self.last_messages = messages
        return self.response

    async def stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        self.last_messages = messages
        for word in self.response.split():
            yield word + " "


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def layer(mock_provider):
    cl = ContextForge(
        db_path=":memory:",
        llm_provider=mock_provider,
        system_prompt="You are a test assistant.",
    )
    yield cl
    cl.close()


class TestInit:
    def test_creates_with_mock_provider(self, layer: ContextForge):
        assert layer is not None
        assert layer.tree is not None
        assert layer.index is not None

    def test_stats_empty(self, layer: ContextForge):
        stats = layer.stats
        assert stats["knowledge_nodes"] == 0
        assert stats["index_terms"] == 0

    def test_context_manager(self, mock_provider):
        with ContextForge(db_path=":memory:", llm_provider=mock_provider) as layer:
            assert layer is not None


class TestIngestion:
    @pytest.mark.asyncio
    async def test_ingest_text(self, layer: ContextForge):
        await layer.ingest_text("Q3 revenue was $10M", title="Q3 Report", category="finance")
        assert layer.stats["knowledge_nodes"] == 1
        assert layer.stats["index_docs"] == 1

    @pytest.mark.asyncio
    async def test_ingest_multiple(self, layer: ContextForge):
        await layer.ingest_text("Q3 revenue $10M", title="Q3", category="finance")
        await layer.ingest_text("Architecture uses microservices", title="Arch", category="engineering")
        assert layer.stats["knowledge_nodes"] == 2


class TestChat:
    @pytest.mark.asyncio
    async def test_basic_chat(self, layer: ContextForge):
        response = await layer.chat("Hello!")
        assert response == "This is a mock response."

    @pytest.mark.asyncio
    async def test_chat_creates_session(self, layer: ContextForge):
        await layer.chat("Hello!")
        assert layer.session is not None

    @pytest.mark.asyncio
    async def test_chat_with_knowledge(self, layer: ContextForge, mock_provider: MockProvider):
        await layer.ingest_text("Revenue was $10M in Q3 2024.", title="Q3 Report", category="finance")
        await layer.chat("What was the Q3 revenue?")

        # Verify the system message includes knowledge
        system_msg = mock_provider.last_messages[0]
        assert system_msg["role"] == "system"
        assert "Relevant Knowledge" in system_msg["content"]

    @pytest.mark.asyncio
    async def test_multi_turn_context(self, layer: ContextForge, mock_provider: MockProvider):
        await layer.chat("Hello!")
        await layer.chat("How are you?")

        # Second call should include history
        messages = mock_provider.last_messages
        # system + first user + first assistant + second user
        assert len(messages) >= 3


class TestStream:
    @pytest.mark.asyncio
    async def test_stream(self, layer: ContextForge):
        chunks = []
        async for chunk in layer.stream("Hello!"):
            chunks.append(chunk)
        assert len(chunks) > 0
        assert "".join(chunks).strip() == "This is a mock response."

    @pytest.mark.asyncio
    async def test_stream_persists_session(self, layer: ContextForge):
        async for _ in layer.stream("Hello!"):
            pass
        messages = layer.session.messages
        assert len(messages) == 2


class TestAnalyze:
    @pytest.mark.asyncio
    async def test_analyze_single_domain(self, layer: ContextForge):
        await layer.ingest_text("Revenue was $10M", title="Finance", category="finance")
        response = await layer.analyze("What was the revenue?")
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_analyze_multi_domain(self, layer: ContextForge, mock_provider: MockProvider):
        await layer.ingest_text("Revenue $10M", title="Finance", category="finance")
        await layer.ingest_text("Microservices arch", title="Engineering", category="engineering")
        mock_provider.response = "Synthesized analysis."
        response = await layer.analyze("Compare finance and engineering")
        assert isinstance(response, str)


class TestSessions:
    @pytest.mark.asyncio
    async def test_new_session(self, layer: ContextForge):
        sid = layer.new_session(session_id="test-session")
        assert sid == "test-session"

    @pytest.mark.asyncio
    async def test_resume_session(self, layer: ContextForge):
        layer.new_session(session_id="s1")
        await layer.chat("Hello!")

        # Start a new session
        layer.new_session(session_id="s2")
        await layer.chat("Different conversation")

        # Resume first session
        assert layer.resume_session("s1") is True
        assert layer.session.id == "s1"

    @pytest.mark.asyncio
    async def test_resume_nonexistent(self, layer: ContextForge):
        assert layer.resume_session("nope") is False

    @pytest.mark.asyncio
    async def test_list_sessions(self, layer: ContextForge):
        layer.new_session(session_id="s1")
        layer.new_session(session_id="s2")
        sessions = layer.list_sessions()
        assert len(sessions) >= 2

    @pytest.mark.asyncio
    async def test_save_session(self, layer: ContextForge):
        layer.new_session(session_id="s1")
        sid = layer.save_session()
        assert sid == "s1"
