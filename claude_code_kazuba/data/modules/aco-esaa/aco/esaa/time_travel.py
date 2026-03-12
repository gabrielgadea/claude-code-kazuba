"""C3 — Time-Travel Debugger for ESAA event streams.

With the SQLite WAL backend + hash chain, any historical agent state
can be reconstructed deterministically. This module provides:

  state_at_seq(agent_id, seq)   — state after exactly N events
  state_at_time(agent_id, ts)   — state at a wall-clock moment
  diff(agent_id, seq_a, seq_b)  — field-level diff between two checkpoints
  replay_from(agent_id, seq)    — generator yielding states event-by-event

CLI::

    python -m scripts.aco.esaa.time_travel --agent-id my-agent --at-seq 100
    python -m scripts.aco.esaa.time_travel --agent-id my-agent --at-time 2026-03-10T12:00:00
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .cqrs_read_model import AgentState, _default_projector
from .sqlite_backend import SQLiteEventStore

if TYPE_CHECKING:
    from collections.abc import Generator


def _parse_iso(ts_str: str) -> float:
    """Parse an ISO 8601 datetime string to a POSIX timestamp.

    Naive datetimes (no timezone info) are treated as UTC.

    Args:
        ts_str: ISO 8601 string, e.g. "2026-03-10T12:00:00" or with offset.

    Returns:
        POSIX timestamp (float seconds since Unix epoch).
    """
    dt = datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()


class TimeTravelDebugger:
    """Reconstruct agent state at any historical point in time.

    Uses the SQLiteEventStore to replay events up to a given sequence
    number or wall-clock timestamp.

    Args:
        store: SQLite event store containing the event stream.
    """

    def __init__(self, store: SQLiteEventStore) -> None:
        self._store = store

    def state_at_seq(self, agent_id: str, seq: int) -> AgentState:
        """Reconstruct agent state after exactly ``seq`` events.

        Args:
            agent_id: Agent whose state to reconstruct.
            seq: Number of events to replay (0 = initial state).

        Returns:
            AgentState after replaying the first ``seq`` events.
        """
        events = self._store.get_stream(agent_id, since_seq=0)
        state = AgentState(agent_id=agent_id)
        for event in events[:seq]:
            state = _default_projector(state, event)
        return state

    def state_at_time(self, agent_id: str, ts: float) -> AgentState:
        """Reconstruct agent state at a given wall-clock timestamp.

        Replays all events with ``event.timestamp <= ts``.

        Args:
            agent_id: Agent whose state to reconstruct.
            ts: POSIX timestamp cutoff (inclusive).

        Returns:
            AgentState after replaying events up to ``ts``.
        """
        events = self._store.get_stream(agent_id, since_seq=0)
        state = AgentState(agent_id=agent_id)
        for event in events:
            if event.timestamp > ts:
                break
            state = _default_projector(state, event)
        return state

    def diff(self, agent_id: str, seq_a: int, seq_b: int) -> dict[str, Any]:
        """Return field-level differences between two historical states.

        Args:
            agent_id: Agent to compare.
            seq_a: First sequence number.
            seq_b: Second sequence number.

        Returns:
            Dict mapping field names to their value in state_b, for fields
            that differ between state_a and state_b.  Empty dict if identical.
        """
        state_a = self.state_at_seq(agent_id, seq_a)
        state_b = self.state_at_seq(agent_id, seq_b)
        a_dict = state_a.to_dict()
        b_dict = state_b.to_dict()
        return {
            field: b_dict[field] for field in ("status", "execution_count") if a_dict.get(field) != b_dict.get(field)
        }

    def replay_from(self, agent_id: str, seq: int) -> Generator[AgentState, None, None]:
        """Yield agent states incrementally starting from ``seq``.

        Each yielded state incorporates one additional event beyond the
        previous, allowing step-by-step inspection of the event stream.

        Args:
            agent_id: Agent to replay.
            seq: Starting sequence number (inclusive lower bound).

        Yields:
            AgentState after each successive event from ``seq`` onwards.
        """
        events = self._store.get_stream(agent_id, since_seq=0)
        state = self.state_at_seq(agent_id, seq)
        for event in events[seq:]:
            state = _default_projector(state, event)
            yield state


def _main() -> None:
    """CLI entry point for the time-travel debugger."""
    import argparse

    parser = argparse.ArgumentParser(description="ESAA Time-Travel Debugger")
    parser.add_argument("--agent-id", required=True, help="Agent ID to inspect")
    parser.add_argument("--db", default=":memory:", help="SQLite database path")

    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--at-seq", type=int, help="Reconstruct state at sequence N")
    grp.add_argument("--at-time", help="Reconstruct state at ISO timestamp")
    grp.add_argument("--diff", nargs=2, type=int, metavar=("SEQ_A", "SEQ_B"))

    args = parser.parse_args()
    store = SQLiteEventStore(args.db)
    debugger = TimeTravelDebugger(store)

    import json

    if args.at_seq is not None:
        state = debugger.state_at_seq(args.agent_id, args.at_seq)
        print(json.dumps(state.to_dict(), indent=2))
    elif args.at_time is not None:
        ts = _parse_iso(args.at_time)
        state = debugger.state_at_time(args.agent_id, ts)
        print(json.dumps(state.to_dict(), indent=2))
    elif args.diff is not None:
        diff = debugger.diff(args.agent_id, args.diff[0], args.diff[1])
        print(json.dumps(diff, indent=2))


if __name__ == "__main__":
    _main()
