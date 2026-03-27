"""
Event Store — Black box that records all AI agent decisions.

Uses SQLite to store events in chronological order,
allowing later retrieval of all events for a given session to reconstruct the timeline.
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Event:
    """An event representing a single decision/action made by an agent."""
    timestamp: str          # when
    event_type: str         # what kind (llm_call, tool_call, decision, error)
    agent_id: str           # which agent
    action: str             # what it did
    input_data: dict        # what input it received
    output_data: dict       # what result it produced
    reasoning: str          # why it made this decision
    session_id: str = ""    # which session it belongs to
    event_id: str = ""      # unique event ID


class EventStore:
    """Store that saves and queries events in SQLite."""

    def __init__(self, db_path: str = "forensics.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        """Create table if it does not exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                action TEXT NOT NULL,
                input_data TEXT NOT NULL,
                output_data TEXT NOT NULL,
                reasoning TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session
            ON events(session_id, timestamp)
        """)
        self.conn.commit()

    def save(self, event: Event) -> str:
        """Save a single event. Returns the event_id."""
        if not event.event_id:
            event.event_id = str(uuid.uuid4())
        if not event.session_id:
            event.session_id = "default"

        self.conn.execute(
            """
            INSERT INTO events
            (event_id, session_id, timestamp, event_type, agent_id,
             action, input_data, output_data, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.session_id,
                event.timestamp,
                event.event_type,
                event.agent_id,
                event.action,
                json.dumps(event.input_data, ensure_ascii=False),
                json.dumps(event.output_data, ensure_ascii=False),
                event.reasoning,
            ),
        )
        self.conn.commit()
        return event.event_id

    def get_session_events(self, session_id: str) -> list[Event]:
        """Return all events for a given session in chronological order."""
        rows = self.conn.execute(
            """
            SELECT event_id, session_id, timestamp, event_type,
                   agent_id, action, input_data, output_data, reasoning
            FROM events
            WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,),
        ).fetchall()

        return [
            Event(
                event_id=row[0],
                session_id=row[1],
                timestamp=row[2],
                event_type=row[3],
                agent_id=row[4],
                action=row[5],
                input_data=json.loads(row[6]),
                output_data=json.loads(row[7]),
                reasoning=row[8],
            )
            for row in rows
        ]

    def get_all_sessions(self) -> list[str]:
        """Return a list of all stored session IDs."""
        rows = self.conn.execute(
            "SELECT DISTINCT session_id FROM events ORDER BY session_id"
        ).fetchall()
        return [row[0] for row in rows]


def now() -> str:
    """Return the current time as an ISO format string."""
    return datetime.now(timezone.utc).isoformat()
