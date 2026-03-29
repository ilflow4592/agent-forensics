"""Tests for EventStore — save/retrieve, session isolation, thread safety."""

import threading
import uuid

import pytest

from agent_forensics.store import EventStore, Event, now


class TestEventSaveAndRetrieve:
    """Event를 저장하고 올바르게 조회하는지 검증."""

    def test_save_returns_event_id(self, store, sample_event):
        event = sample_event()
        eid = store.save(event)
        assert eid
        assert isinstance(eid, str)

    def test_save_assigns_event_id_when_empty(self, store, sample_event):
        event = sample_event()
        assert event.event_id == ""
        store.save(event)
        assert event.event_id != ""

    def test_save_preserves_explicit_event_id(self, store, sample_event):
        event = sample_event()
        event.event_id = "my-custom-id"
        eid = store.save(event)
        assert eid == "my-custom-id"

    def test_save_assigns_default_session_when_empty(self, store, sample_event):
        event = sample_event(session_id="")
        store.save(event)
        assert event.session_id == "default"

    def test_retrieve_saved_event(self, store, sample_event):
        event = sample_event(action="search", reasoning="find products")
        store.save(event)

        events = store.get_session_events("test-session")
        assert len(events) == 1
        assert events[0].action == "search"
        assert events[0].reasoning == "find products"
        assert events[0].agent_id == "test-agent"

    def test_input_output_json_roundtrip(self, store, sample_event):
        event = sample_event(
            input_data={"query": "wireless mouse", "filters": [1, 2]},
            output_data={"results": [{"name": "Mouse A", "price": 29.99}]},
        )
        store.save(event)

        retrieved = store.get_session_events("test-session")[0]
        assert retrieved.input_data == {"query": "wireless mouse", "filters": [1, 2]}
        assert retrieved.output_data["results"][0]["price"] == 29.99

    def test_unicode_data_preserved(self, store, sample_event):
        event = sample_event(
            action="검색",
            reasoning="한국어 테스트",
            input_data={"query": "무선 마우스"},
        )
        store.save(event)

        retrieved = store.get_session_events("test-session")[0]
        assert retrieved.action == "검색"
        assert retrieved.input_data["query"] == "무선 마우스"

    def test_multiple_events_chronological_order(self, store, sample_event):
        for i in range(5):
            store.save(sample_event(action=f"step_{i}"))

        events = store.get_session_events("test-session")
        assert len(events) == 5
        for i, e in enumerate(events):
            assert e.action == f"step_{i}"

    def test_empty_session_returns_empty_list(self, store):
        events = store.get_session_events("nonexistent")
        assert events == []


class TestSessionIsolation:
    """서로 다른 session_id의 이벤트가 격리되는지 검증."""

    def test_events_isolated_by_session(self, store, sample_event):
        store.save(sample_event(session_id="session-a", action="action_a"))
        store.save(sample_event(session_id="session-b", action="action_b"))

        events_a = store.get_session_events("session-a")
        events_b = store.get_session_events("session-b")

        assert len(events_a) == 1
        assert events_a[0].action == "action_a"
        assert len(events_b) == 1
        assert events_b[0].action == "action_b"

    def test_get_all_sessions(self, store, sample_event):
        store.save(sample_event(session_id="alpha"))
        store.save(sample_event(session_id="beta"))
        store.save(sample_event(session_id="alpha"))  # duplicate session

        sessions = store.get_all_sessions()
        assert set(sessions) == {"alpha", "beta"}

    def test_get_all_sessions_empty_db(self, store):
        assert store.get_all_sessions() == []


class TestThreadSafety:
    """멀티스레드 환경에서 EventStore가 안전하게 동작하는지 검증."""

    def test_concurrent_writes_separate_connections(self, tmp_db):
        """Each thread uses its own EventStore (separate SQLite connection)."""
        errors = []

        def write_events(thread_id):
            try:
                thread_store = EventStore(tmp_db)
                for i in range(20):
                    thread_store.save(Event(
                        timestamp=now(),
                        event_type="decision",
                        agent_id=f"agent-{thread_id}",
                        action=f"action-{thread_id}-{i}",
                        input_data={},
                        output_data={},
                        reasoning="concurrent test",
                        session_id=f"session-{thread_id}",
                    ))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_events, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent write errors: {errors}"

        # Verify all events were saved
        reader = EventStore(tmp_db)
        total = sum(
            len(reader.get_session_events(f"session-{t}"))
            for t in range(5)
        )
        assert total == 100  # 5 threads * 20 events


class TestEventStoreInit:
    """DB 초기화 관련 테스트."""

    def test_creates_db_file(self, tmp_path):
        db_path = str(tmp_path / "new.db")
        EventStore(db_path)
        assert (tmp_path / "new.db").exists()

    def test_reopen_existing_db(self, tmp_db, sample_event):
        store1 = EventStore(tmp_db)
        store1.save(sample_event(session_id="persist"))

        store2 = EventStore(tmp_db)
        events = store2.get_session_events("persist")
        assert len(events) == 1
