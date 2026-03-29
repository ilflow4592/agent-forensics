"""Shared fixtures for agent-forensics tests."""

import os
import pytest

from agent_forensics.store import EventStore, Event, now
from agent_forensics.core import Forensics


@pytest.fixture
def tmp_db(tmp_path):
    """Return a path to a temporary SQLite database."""
    return str(tmp_path / "test.db")


@pytest.fixture
def store(tmp_db):
    """Return a fresh EventStore backed by a temp file."""
    return EventStore(tmp_db)


@pytest.fixture
def forensics(tmp_db):
    """Return a Forensics instance backed by a temp DB."""
    return Forensics(session="test-session", agent="test-agent", db_path=tmp_db)


@pytest.fixture
def sample_event():
    """Return a factory for creating test events."""
    def _make(
        event_type="decision",
        action="test_action",
        session_id="test-session",
        agent_id="test-agent",
        input_data=None,
        output_data=None,
        reasoning="test reasoning",
    ):
        return Event(
            timestamp=now(),
            event_type=event_type,
            agent_id=agent_id,
            action=action,
            input_data=input_data or {},
            output_data=output_data or {},
            reasoning=reasoning,
            session_id=session_id,
        )
    return _make
