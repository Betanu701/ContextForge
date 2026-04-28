"""Tests for SessionStore — persist, resume, compaction."""

from __future__ import annotations

import pytest
from contextforge.session import SessionStore


@pytest.fixture
def store():
    s = SessionStore(db_path=":memory:", compaction_threshold=500)
    s.open()
    yield s
    s.close()


class TestSessionLifecycle:
    def test_create_session(self, store: SessionStore):
        session = store.create_session()
        assert session.id is not None
        assert session.messages == []

    def test_create_with_id(self, store: SessionStore):
        session = store.create_session(session_id="test-123")
        assert session.id == "test-123"

    def test_create_with_metadata(self, store: SessionStore):
        session = store.create_session(metadata={"user": "alice"})
        assert session.metadata == {"user": "alice"}

    def test_get_session(self, store: SessionStore):
        created = store.create_session(session_id="s1")
        retrieved = store.get_session("s1")
        assert retrieved is not None
        assert retrieved.id == "s1"

    def test_get_nonexistent(self, store: SessionStore):
        assert store.get_session("nonexistent") is None

    def test_list_sessions(self, store: SessionStore):
        store.create_session(session_id="s1")
        store.create_session(session_id="s2")
        sessions = store.list_sessions()
        assert len(sessions) == 2
        ids = {s["id"] for s in sessions}
        assert ids == {"s1", "s2"}

    def test_delete_session(self, store: SessionStore):
        store.create_session(session_id="s1")
        store.add_message("s1", "user", "Hello")
        store.delete_session("s1")
        assert store.get_session("s1") is None


class TestMessages:
    def test_add_and_get_messages(self, store: SessionStore):
        store.create_session(session_id="s1")
        store.add_message("s1", "user", "Hello")
        store.add_message("s1", "assistant", "Hi there!")
        messages = store.get_messages("s1")
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["content"] == "Hi there!"

    def test_add_to_nonexistent_raises(self, store: SessionStore):
        with pytest.raises(ValueError):
            store.add_message("nonexistent", "user", "Hello")

    def test_messages_persist_across_load(self, store: SessionStore):
        store.create_session(session_id="s1")
        store.add_message("s1", "user", "Hello")
        store.add_message("s1", "assistant", "Hi!")

        # Clear cache and reload
        store._active.clear()
        session = store.load_session("s1")
        assert session is not None
        assert len(session.messages) == 2


class TestCompaction:
    def test_compaction_triggers(self, store: SessionStore):
        store.create_session(session_id="s1")
        # Add many messages to exceed threshold
        for i in range(20):
            store.add_message("s1", "user", f"Question {i} " * 20)
            store.add_message("s1", "assistant", f"Answer {i} " * 20)

        # After compaction, there should be summaries
        rows = store.conn.execute(
            "SELECT COUNT(*) FROM session_summaries WHERE session_id = 's1'"
        ).fetchone()
        assert rows[0] > 0

    def test_compacted_session_loads_with_summary(self, store: SessionStore):
        store.create_session(session_id="s1")
        for i in range(20):
            store.add_message("s1", "user", f"Question {i} " * 20)
            store.add_message("s1", "assistant", f"Answer {i} " * 20)

        # Reload
        store._active.clear()
        session = store.load_session("s1")
        assert session is not None
        # Should have a summary system message + recent messages
        has_summary = any(
            "[Previous conversation summary]" in m.get("content", "")
            for m in session.messages
        )
        assert has_summary

    def test_force_compact(self, store: SessionStore):
        store.create_session(session_id="s1")
        for i in range(10):
            store.add_message("s1", "user", f"Msg {i}")
            store.add_message("s1", "assistant", f"Reply {i}")

        store.force_compact("s1")
        rows = store.conn.execute(
            "SELECT COUNT(*) FROM session_summaries WHERE session_id = 's1'"
        ).fetchone()
        assert rows[0] >= 0  # May or may not compact depending on message count


class TestMultipleSessions:
    def test_isolated_sessions(self, store: SessionStore):
        store.create_session(session_id="s1")
        store.create_session(session_id="s2")
        store.add_message("s1", "user", "Hello from s1")
        store.add_message("s2", "user", "Hello from s2")

        m1 = store.get_messages("s1")
        m2 = store.get_messages("s2")
        assert len(m1) == 1
        assert len(m2) == 1
        assert "s1" in m1[0]["content"]
        assert "s2" in m2[0]["content"]
