"""SQLite WAL-mode event store for ESAA — durable, indexed, ACID-compliant.

Supersedes the JSONL-based BatchedEventStore (Sprint A2) with true ACID
guarantees via SQLite Write-Ahead Logging. Supports hash chain verification,
snapshots for O(1) replay, and chronological queries.

Pattern sourced from: scripts/aco/generators/gen_swarm_coordinator.py (~200)

Example:
    >>> from scripts.aco.esaa.sqlite_backend import SQLiteEventStore
    >>> store = SQLiteEventStore(":memory:")
    >>> store.append_events([event1, event2])
    >>> events = store.get_stream("agent-1")
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from .event_buffer import DomainEvent
from .hash_chain import (
    GENESIS_HASH,
    canonical_payload,
    compute_event_hash,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

logger = logging.getLogger(__name__)

_CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id       TEXT UNIQUE NOT NULL,
    agent_id       TEXT NOT NULL,
    event_type     TEXT NOT NULL,
    timestamp      REAL NOT NULL,
    payload        TEXT NOT NULL,
    prev_hash      TEXT NOT NULL,
    event_hash     TEXT NOT NULL,
    correlation_id TEXT,
    causation_id   TEXT
)
"""

_CREATE_SNAPSHOTS_TABLE = """
CREATE TABLE IF NOT EXISTS snapshots (
    agent_id     TEXT PRIMARY KEY,
    seq          INTEGER NOT NULL,
    state_json   TEXT NOT NULL,
    snapshot_at  REAL NOT NULL
)
"""

_CREATE_AGENT_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_events_agent_id ON events(agent_id, seq)"
)
_CREATE_TS_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)"
)


class SQLiteEventStore:
    """Durable SQLite WAL-mode event store with hash chain and snapshots.

    Thread-safe: each file-based operation opens a fresh connection with
    WAL mode enabled. In-memory mode uses a single persistent connection.

    Args:
        db_path: Path to the SQLite database (``":memory:"`` for tests).
        snapshot_every: Auto-snapshot after this many appended events.
    """

    def __init__(
        self,
        db_path: str | Path = ":memory:",
        snapshot_every: int = 100,
    ) -> None:
        self._db_path = str(db_path)
        self._snapshot_every = snapshot_every
        self._appended_since_snapshot: int = 0
        self._mem_conn: sqlite3.Connection | None = None
        if self._db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
            self._mem_conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    # ------------------------------------------------------------------
    # Context manager for connection handling
    # ------------------------------------------------------------------

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a database connection (persistent for :memory:, fresh for file)."""
        if self._mem_conn is not None:
            yield self._mem_conn
        else:
            conn = sqlite3.connect(self._db_path, timeout=10, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._conn() as conn:
            conn.execute(_CREATE_EVENTS_TABLE)
            conn.execute(_CREATE_SNAPSHOTS_TABLE)
            conn.execute(_CREATE_AGENT_IDX)
            conn.execute(_CREATE_TS_IDX)
            if self._mem_conn is not None:
                conn.commit()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def append_events(self, events: list[DomainEvent]) -> None:
        """Persist a list of events in a single atomic transaction.

        Automatically computes ``prev_hash`` / ``event_hash`` for events
        that have not yet been hashed (``event_hash == ""``).

        Args:
            events: Events to persist (ordered, oldest first).
        """
        if not events:
            return
        rows = self._build_rows(events)
        with self._conn() as conn:
            conn.executemany(
                """INSERT OR IGNORE INTO events
                   (event_id, agent_id, event_type, timestamp, payload,
                    prev_hash, event_hash, correlation_id, causation_id)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            if self._mem_conn is not None:
                conn.commit()
        self._appended_since_snapshot += len(events)

    def _build_rows(self, events: list[DomainEvent]) -> list[tuple[Any, ...]]:
        """Build INSERT tuples, chaining hashes for unhashed events."""
        rows: list[tuple[Any, ...]] = []
        prev = GENESIS_HASH
        for event in events:
            if event.event_hash:
                hashed = event
                prev = event.event_hash
            else:
                from dataclasses import replace as dc_replace

                canon = canonical_payload(dict(event.payload))
                h = compute_event_hash(prev, event.event_id, canon)
                hashed = dc_replace(event, prev_hash=prev, event_hash=h)
                prev = h
            rows.append((
                hashed.event_id,
                hashed.agent_id,
                hashed.event_type,
                hashed.timestamp,
                json.dumps(dict(hashed.payload)),
                hashed.prev_hash,
                hashed.event_hash,
                hashed.correlation_id,
                hashed.causation_id,
            ))
        return rows

    def save_snapshot(self, agent_id: str, seq: int, state: dict) -> None:
        """Persist an agent state snapshot at the given sequence number.

        Args:
            agent_id: Agent identifier.
            seq: Sequence number of the last event included in snapshot.
            state: Dictionary representation of agent state.
        """
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO snapshots
                   (agent_id, seq, state_json, snapshot_at) VALUES (?,?,?,?)""",
                (agent_id, seq, json.dumps(state), time.time()),
            )
            if self._mem_conn is not None:
                conn.commit()
        self._appended_since_snapshot = 0

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_stream(
        self, agent_id: str, since_seq: int = 0
    ) -> list[DomainEvent]:
        """Load events for an agent from the database.

        Args:
            agent_id: Agent to query.
            since_seq: Return only events with seq > this value (0 = all).

        Returns:
            Ordered list of DomainEvent objects (oldest first).
        """
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT event_id, agent_id, event_type, timestamp, payload,
                          prev_hash, event_hash, correlation_id, causation_id
                   FROM events
                   WHERE agent_id = ? AND seq > ?
                   ORDER BY seq ASC""",
                (agent_id, since_seq),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_latest_snapshot(
        self, agent_id: str
    ) -> tuple[int, dict] | None:
        """Return the most recent snapshot for an agent.

        Args:
            agent_id: Agent to query.

        Returns:
            Tuple of (seq, state_dict) or None if no snapshot exists.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT seq, state_json FROM snapshots WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        return int(row["seq"]), json.loads(row["state_json"])

    def get_latest_seq(self, agent_id: str) -> int:
        """Return the highest sequence number for an agent's events.

        Args:
            agent_id: Agent to query.

        Returns:
            Maximum ``seq`` value, or 0 if no events exist.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT MAX(seq) FROM events WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        val = row[0] if row else None
        return int(val) if val is not None else 0

    @property
    def should_snapshot(self) -> bool:
        """True when appended-since-last-snapshot reaches the threshold.

        Resets to False automatically when ``save_snapshot()`` is called.
        """
        return self._appended_since_snapshot >= self._snapshot_every

    def verify_chain(self, agent_id: str) -> bool:
        """Verify the SHA-256 hash chain for all events of an agent.

        Args:
            agent_id: Agent whose event stream to verify.

        Returns:
            True if the chain is intact.

        Raises:
            ValueError: If any tampered or broken-link event is found.
        """
        events = self.get_stream(agent_id)
        from .hash_chain import verify_chain as _verify

        return _verify(events)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> DomainEvent:
        """Convert a database row to a DomainEvent."""
        return DomainEvent(
            event_id=row["event_id"],
            event_type=row["event_type"],
            agent_id=row["agent_id"],
            timestamp=float(row["timestamp"]),
            payload=json.loads(row["payload"]),
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            prev_hash=row["prev_hash"],
            event_hash=row["event_hash"],
        )
