"""event_store.py — ESAA Event Store (append-only).

Event Sourcing Agent Architecture: Event Store implementation
with append-only semantics and replay capability.

This module provides immutable event storage with:
- Append-only writes (events never modified or deleted)
- Stream-based organization (one stream per agent)
- Replay capability for state reconstruction
- Correlation and causation tracking

Example:
    store = EventStore(storage_path=Path(".claude/esaa/events"))
    event = create_event(
        EventType.AGENT_EXECUTED,
        agent_id="my-agent-1.0.0",
        payload={"result": "success"},
    )
    store.append(event)

    # Replay to reconstruct state
    events = store.get_stream("my-agent-1.0.0")
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of domain events."""

    AGENT_CREATED = "agent_created"
    AGENT_EXECUTED = "agent_executed"
    AGENT_VALIDATED = "agent_validated"
    AGENT_ROLLED_BACK = "agent_rolled_back"
    CHECKPOINT_CREATED = "checkpoint_created"
    CHECKPOINT_RESTORED = "checkpoint_restored"
    GENERATION_STARTED = "generation_started"
    GENERATION_COMPLETED = "generation_completed"
    GENERATION_FAILED = "generation_failed"


@dataclass(frozen=True)
class DomainEvent:
    """Immutable domain event.

    Attributes:
        event_id: Unique event identifier (UUID)
        event_type: Type of event
        agent_id: Identifier of the agent that generated the event
        timestamp: ISO8601 timestamp
        payload: Event-specific data
        correlation_id: Optional correlation ID for distributed tracing
        causation_id: Optional ID of the event that caused this one
    """

    event_id: str
    event_type: EventType
    agent_id: str
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None


class EventStore:
    """Append-only event store.

    All events are immutable and append-only. Events can be queried
    by stream (agent_id) and replayed to reconstruct state.

    Attributes:
        storage_path: Directory for event storage
    """

    def __init__(
        self,
        storage_path: Path | None = None,
        max_events_per_stream: int = 10_000,
    ) -> None:
        """Initialize event store.

        Args:
            storage_path: Directory for event storage (default: .claude/esaa/events/)
            max_events_per_stream: Maximum in-memory events per stream (oldest trimmed).
        """
        self._storage_path = storage_path or Path(".claude/esaa/events")
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._streams: dict[str, list[DomainEvent]] = {}
        self._max_events_per_stream = max_events_per_stream
        self._load_all_streams()

    def append(self, event: DomainEvent) -> None:
        """Append event to store (immutable operation).

        Args:
            event: Event to append
        """
        # Append to memory, trimming oldest events if cap exceeded
        stream = self._streams.setdefault(event.agent_id, [])
        stream.append(event)
        if len(stream) > self._max_events_per_stream:
            del stream[: len(stream) - self._max_events_per_stream]

        # Persist to disk
        stream_path = self._storage_path / f"{event.agent_id}.jsonl"
        with open(stream_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type.value,
                        "agent_id": event.agent_id,
                        "timestamp": event.timestamp,
                        "payload": event.payload,
                        "correlation_id": event.correlation_id,
                        "causation_id": event.causation_id,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        logger.debug(
            "Appended event %s to stream %s", event.event_id, event.agent_id
        )

    def get_stream(self, agent_id: str) -> list[DomainEvent]:
        """Get all events for an agent stream.

        Args:
            agent_id: Agent identifier

        Returns:
            List of events in chronological order
        """
        return list(self._streams.get(agent_id, []))

    def replay(
        self,
        agent_id: str,
        projector: Callable[[Any, DomainEvent], Any],
        initial_state: Any = None,
    ) -> Any:
        """Replay events to reconstruct state.

        Args:
            agent_id: Agent identifier
            projector: Function that applies events to state
            initial_state: Starting state

        Returns:
            Final state after all events applied
        """
        state = initial_state
        for event in self.get_stream(agent_id):
            state = projector(state, event)
        return state

    def get_events_by_type(self, event_type: EventType) -> list[DomainEvent]:
        """Get all events of a specific type across all streams.

        Args:
            event_type: Type of events to retrieve

        Returns:
            List of matching events
        """
        return [
            event
            for stream in self._streams.values()
            for event in stream
            if event.event_type == event_type
        ]

    def get_correlated_events(self, correlation_id: str) -> list[DomainEvent]:
        """Get all events with a specific correlation ID.

        Args:
            correlation_id: Correlation identifier to search for

        Returns:
            List of matching events
        """
        return [
            event
            for stream in self._streams.values()
            for event in stream
            if event.correlation_id == correlation_id
        ]

    def get_latest_event(self, agent_id: str) -> DomainEvent | None:
        """Get the most recent event for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Latest event or None if stream is empty
        """
        stream = self._streams.get(agent_id, [])
        return stream[-1] if stream else None

    def get_stream_count(self) -> int:
        """Get total number of streams (agents)."""
        return len(self._streams)

    def get_event_count(self) -> int:
        """Get total number of events across all streams."""
        return sum(len(stream) for stream in self._streams.values())

    def _load_all_streams(self) -> None:
        """Load all streams from disk."""
        if not self._storage_path.exists():
            return

        for stream_file in self._storage_path.glob("*.jsonl"):
            agent_id = stream_file.stem
            self._streams[agent_id] = []

            with open(stream_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        self._streams[agent_id].append(
                            DomainEvent(
                                event_id=data["event_id"],
                                event_type=EventType(data["event_type"]),
                                agent_id=data["agent_id"],
                                timestamp=data["timestamp"],
                                payload=data.get("payload", {}),
                                correlation_id=data.get("correlation_id"),
                                causation_id=data.get("causation_id"),
                            )
                        )
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(
                            "Failed to parse event in %s: %s", stream_file, e
                        )


def create_event(
    event_type: EventType,
    agent_id: str,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
) -> DomainEvent:
    """Factory function for creating events.

    Args:
        event_type: Type of event
        agent_id: Agent identifier
        payload: Event data
        correlation_id: Optional correlation ID
        causation_id: Optional causation ID

    Returns:
        New domain event
    """
    return DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        agent_id=agent_id,
        timestamp=datetime.now(UTC).isoformat(),
        payload=payload or {},
        correlation_id=correlation_id,
        causation_id=causation_id,
    )


def create_correlation_id() -> str:
    """Generate a new correlation ID for distributed tracing."""
    return str(uuid.uuid4())


if __name__ == "__main__":
    # Demo usage
    import tempfile

    logging.basicConfig(level=logging.INFO)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(Path(tmpdir))

        # Create some events
        corr_id = create_correlation_id()
        event1 = create_event(
            EventType.AGENT_CREATED,
            "test-agent-1.0.0",
            {"spec": {"name": "test-agent"}},
            correlation_id=corr_id,
        )
        store.append(event1)

        event2 = create_event(
            EventType.AGENT_EXECUTED,
            "test-agent-1.0.0",
            {"result": "success"},
            correlation_id=corr_id,
            causation_id=event1.event_id,
        )
        store.append(event2)

        print(f"Streams: {store.get_stream_count()}")
        print(f"Total events: {store.get_event_count()}")

        stream = store.get_stream("test-agent-1.0.0")
        print(f"Events for test-agent: {len(stream)}")

        for ev in stream:
            print(f"  - {ev.event_type.value}: {ev.timestamp}")
