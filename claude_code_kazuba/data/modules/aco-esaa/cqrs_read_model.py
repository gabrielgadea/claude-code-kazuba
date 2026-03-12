"""Cached CQRS Read Model for ESAA.

Implements in-memory read model with automatic cache invalidation.
Based on Rust CQRS pattern: HashMap + Mutex for thread-safe caching.

Expected improvement: Query latency ~0.08ms -> ~0.001ms (80x)
"""

from __future__ import annotations

import copy
import json
import logging
import threading
import time as _time
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentState:
    """Immutable agent state for CQRS read model.

    Attributes:
        agent_id: Unique agent identifier.
        status: Current agent status (e.g., "active", "idle", "error").
        execution_count: Number of times agent has executed.
        last_execution: Timestamp of last execution.
        metadata: Additional agent metadata.
        created_at: Timestamp when agent was created.
        updated_at: Timestamp of last update.
    """

    agent_id: str
    status: str = "created"
    execution_count: int = 0
    last_execution: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time.time)
    updated_at: float = field(default_factory=_time.time)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(self.metadata))

    def with_status(self, status: str) -> AgentState:
        """Return new state with updated status."""
        return AgentState(
            agent_id=self.agent_id,
            status=status,
            execution_count=self.execution_count,
            last_execution=self.last_execution,
            metadata=copy.deepcopy(dict(self.metadata)),
            created_at=self.created_at,
            updated_at=_time.time(),
        )

    def with_execution(self) -> AgentState:
        """Return new state with incremented execution count."""
        now = _time.time()
        return AgentState(
            agent_id=self.agent_id,
            status=self.status,
            execution_count=self.execution_count + 1,
            last_execution=now,
            metadata=copy.deepcopy(dict(self.metadata)),
            created_at=self.created_at,
            updated_at=now,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict for snapshot storage.

        Returns:
            Dict with all AgentState fields, suitable for JSON serialization.
        """
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentState:
        """Reconstruct from a plain dict (e.g., loaded from snapshot storage).

        Args:
            data: Dict previously produced by ``to_dict()``.

        Returns:
            Reconstructed AgentState.
        """
        return cls(
            agent_id=data["agent_id"],
            status=data.get("status", "created"),
            execution_count=data.get("execution_count", 0),
            last_execution=data.get("last_execution"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", _time.time()),
            updated_at=data.get("updated_at", _time.time()),
        )


@dataclass
class CacheStats:
    """Statistics for cached query operations.

    Attributes:
        hits: Number of cache hits.
        misses: Number of cache misses.
        invalidations: Number of explicit invalidations.
        size: Current cache size.
    """

    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    size: int = 0


def _parse_agent_file(agent_file: Path) -> AgentState | None:
    """Parse a JSON agent file into an AgentState.

    Args:
        agent_file: Path to the agent JSON file.

    Returns:
        AgentState if successfully parsed, None otherwise.
    """
    if not agent_file.exists():
        return None

    try:
        data = json.loads(agent_file.read_text())
        return AgentState(
            agent_id=data["agent_id"],
            status=data["status"],
            execution_count=data.get("execution_count", 0),
            last_execution=data.get("last_execution"),
            metadata=data.get("metadata", {}),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.warning("Failed to parse %s: %s", agent_file, e)
        return None


class CachedQuerySide:
    """CQRS QuerySide with in-memory read model caching.

    Provides fast read operations through an in-memory cache
    with automatic invalidation on writes.

    Thread-safe: Uses RLock for concurrent access.

    Example:
        >>> query = CachedQuerySide(storage_path="/tmp/agents")
        >>> agent = query.get_agent("agent-1")
        >>> agents = query.list_agents(status="active")
        >>> stats = query.get_cache_stats()
    """

    def __init__(self, storage_path: Path | str | None = None) -> None:
        """Initialize the cached query side.

        Args:
            storage_path: Optional path to load persisted states.
        """
        self._storage_path = Path(storage_path) if storage_path else None
        self._cache: dict[str, AgentState] = {}
        self._index_by_status: dict[str, set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self._stats = CacheStats()

        if self._storage_path:
            self._load_from_disk()

    def get_agent(self, agent_id: str) -> AgentState | None:
        """Get agent state from cache or disk.

        Args:
            agent_id: The agent ID to query.

        Returns:
            AgentState if found, None otherwise.
        """
        with self._lock:
            if agent_id in self._cache:
                self._stats.hits += 1
                return self._cache[agent_id]
            self._stats.misses += 1

        # Load from disk outside lock (I/O must not hold the lock)
        state = self._load_agent_from_disk(agent_id)

        with self._lock:
            # Double-check: another thread may have populated the cache
            # while we were loading from disk — prefer the more recent version.
            if agent_id in self._cache:
                return self._cache[agent_id]
            if state:
                self._cache[agent_id] = state
                self._index_by_status[state.status].add(agent_id)
        return state

    def list_agents(
        self,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentState]:
        """List agents with optional status filter.

        Args:
            status: Optional status filter.
            limit: Maximum number of results.

        Returns:
            List of agent states.
        """
        with self._lock:
            if status:
                agent_ids = list(self._index_by_status.get(status, set()))
            else:
                agent_ids = list(self._cache.keys())

            if limit:
                agent_ids = agent_ids[:limit]

            return [self._cache[aid] for aid in agent_ids if aid in self._cache]

    def search_agents(
        self,
        predicate: Callable[[AgentState], bool],
        limit: int | None = None,
    ) -> list[AgentState]:
        """Search agents by custom predicate.

        Args:
            predicate: Function to filter agents.
            limit: Maximum number of results.

        Returns:
            List of matching agent states.
        """
        with self._lock:
            results = [state for state in self._cache.values() if predicate(state)]

            if limit:
                results = results[:limit]

            return results

    def get_agent_stats(self, agent_id: str) -> dict[str, Any] | None:
        """Get statistics for a specific agent.

        Args:
            agent_id: The agent ID to query.

        Returns:
            Dictionary with agent statistics or None.
        """
        state = self.get_agent(agent_id)
        if not state:
            return None

        return {
            "agent_id": state.agent_id,
            "status": state.status,
            "execution_count": state.execution_count,
            "last_execution": state.last_execution,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "metadata_keys": list(state.metadata.keys()),
        }

    def invalidate(self, agent_id: str) -> bool:
        """Invalidate cache entry for an agent.

        Called synchronously on all writes to ensure cache consistency.

        Args:
            agent_id: The agent ID to invalidate.

        Returns:
            True if entry was in cache, False otherwise.
        """
        with self._lock:
            if agent_id in self._cache:
                old_status = self._cache[agent_id].status
                self._index_by_status[old_status].discard(agent_id)
                del self._cache[agent_id]
                self._stats.invalidations += 1
                return True
            return False

    def update(self, state: AgentState) -> None:
        """Update cache with new agent state.

        Args:
            state: The new agent state.
        """
        with self._lock:
            if state.agent_id in self._cache:
                old_status = self._cache[state.agent_id].status
                self._index_by_status[old_status].discard(state.agent_id)

            self._cache[state.agent_id] = state
            self._index_by_status[state.status].add(state.agent_id)

    def _load_agent_from_disk(self, agent_id: str) -> AgentState | None:
        """Load agent state from disk (called outside lock)."""
        if not self._storage_path:
            return None

        agent_file = self._storage_path / f"{agent_id}.json"
        return _parse_agent_file(agent_file)

    def _load_from_disk(self) -> None:
        """Load all agent states from disk."""
        if not self._storage_path:
            return

        for agent_file in self._storage_path.glob("*.json"):
            state = _parse_agent_file(agent_file)
            if state:
                self._cache[state.agent_id] = state
                self._index_by_status[state.status].add(state.agent_id)

    def get_cache_stats(self) -> CacheStats:
        """Get current cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                invalidations=self._stats.invalidations,
                size=len(self._cache),
            )

    def clear_cache(self) -> int:
        """Clear all cached entries.

        Returns:
            Number of entries cleared.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._index_by_status.clear()
            return count


class CachedCommandSide:
    """CQRS CommandSide with cache invalidation.

        Wraps write operations with automatic cache invalidation
    to ensure read model consistency.
    """

    def __init__(
        self,
        storage_path: Path | str,
        query_side: CachedQuerySide | None = None,
    ) -> None:
        """Initialize the cached command side.

        Args:
            storage_path: Path to persist agent states.
            query_side: Optional query side for cache invalidation.
        """
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._query_side = query_side
        self._lock = threading.RLock()

    def create_agent(
        self,
        agent_id: str,
        initial_status: str = "created",
        metadata: dict[str, Any] | None = None,
    ) -> AgentState:
        """Create a new agent.

        Args:
            agent_id: Unique agent identifier.
            initial_status: Initial agent status.
            metadata: Optional initial metadata.

        Returns:
            Created agent state.
        """
        import time

        state = AgentState(
            agent_id=agent_id,
            status=initial_status,
            metadata=metadata or {},
            created_at=time.time(),
            updated_at=time.time(),
        )

        self._persist_state(state)

        if self._query_side:
            self._query_side.update(state)

        logger.debug("Created agent %s with status %s", agent_id, initial_status)
        return state

    def _resolve_and_update(self, agent_id: str, transform: Callable[[AgentState], AgentState]) -> AgentState | None:
        """Resolve current agent state, apply a transform, persist, and sync cache.

        Args:
            agent_id: The agent ID to update.
            transform: Function that takes current state and returns new state.

        Returns:
            Updated state or None if agent not found.
        """
        current = None
        if self._query_side:
            current = self._query_side.get_agent(agent_id)
        if not current:
            current = self._load_from_disk(agent_id)
        if not current:
            return None

        new_state = transform(current)
        self._persist_state(new_state)

        if self._query_side:
            self._query_side.invalidate(agent_id)
            self._query_side.update(new_state)

        return new_state

    def update_status(self, agent_id: str, status: str) -> AgentState | None:
        """Update agent status.

        Args:
            agent_id: The agent ID to update.
            status: New status value.

        Returns:
            Updated state or None if agent not found.
        """
        result = self._resolve_and_update(agent_id, lambda s: s.with_status(status))
        if result:
            logger.debug("Updated agent %s status to %s", agent_id, status)
        return result

    def increment_execution(self, agent_id: str) -> AgentState | None:
        """Increment agent execution count.

        Args:
            agent_id: The agent ID to update.

        Returns:
            Updated state or None if agent not found.
        """
        result = self._resolve_and_update(agent_id, lambda s: s.with_execution())
        if result:
            logger.debug("Incremented execution count for agent %s", agent_id)
        return result

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent.

        Args:
            agent_id: The agent ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        agent_file = self._storage_path / f"{agent_id}.json"

        with self._lock:
            if not agent_file.exists():
                return False

            try:
                agent_file.unlink()
            except OSError as e:
                logger.error("Failed to delete agent %s: %s", agent_id, e)
                return False

        if self._query_side:
            self._query_side.invalidate(agent_id)

        logger.debug("Deleted agent %s", agent_id)
        return True

    def _persist_state(self, state: AgentState) -> None:
        """Persist state to disk."""

        agent_file = self._storage_path / f"{state.agent_id}.json"

        with self._lock:
            agent_file.write_text(
                json.dumps(
                    {
                        "agent_id": state.agent_id,
                        "status": state.status,
                        "execution_count": state.execution_count,
                        "last_execution": state.last_execution,
                        "metadata": dict(state.metadata),
                        "created_at": state.created_at,
                        "updated_at": state.updated_at,
                    },
                    indent=2,
                )
            )

    def _load_from_disk(self, agent_id: str) -> AgentState | None:
        """Load agent state from disk."""
        return _parse_agent_file(self._storage_path / f"{agent_id}.json")


# ---------------------------------------------------------------------------
# B3 — Event sourcing replayer (snapshot + delta)
# ---------------------------------------------------------------------------

ProjectorFn = Callable[[AgentState, Any], AgentState]
"""Type alias for a state projector: (current_state, event) → new_state."""


def _default_projector(state: AgentState, event: Any) -> AgentState:
    """Default event to AgentState projection.

    Handles ``agent_executed`` and ``agent_status_changed``; all other event
    types are treated as idempotent (state is returned unchanged).

    Args:
        state: Current agent state.
        event: DomainEvent-like object with ``event_type`` and ``payload``.

    Returns:
        Updated agent state.
    """
    if event.event_type == "agent_executed":
        return state.with_execution()
    if event.event_type == "agent_status_changed":
        return state.with_status(str(event.payload.get("status", state.status)))
    return state


class EventSourcingReplayer:
    """Rebuilds AgentState from an event store using snapshot + delta replay.

    With snapshots taken every N events, at most N events are replayed on
    recovery — achieving O(1) amortized startup cost.

    Args:
        store: Object implementing ``get_latest_snapshot(agent_id)`` and
            ``get_stream(agent_id, since_seq=N)``.  Duck-typed to avoid a
            circular import with ``sqlite_backend``.
        projector: Optional custom projector function.  Defaults to
            ``_default_projector``.

    Example:
        >>> replayer = EventSourcingReplayer(store)
        >>> state = replayer.build_state("agent-1")
    """

    def __init__(
        self,
        store: Any,
        projector: Callable[..., AgentState] | None = None,
    ) -> None:
        self._store = store
        self._projector: Callable[..., AgentState] = projector or _default_projector

    def build_state(self, agent_id: str) -> AgentState | None:
        """Reconstruct the latest agent state.

        Uses the most recent snapshot as the base, then replays only the
        delta events that occurred after it.

        Args:
            agent_id: Agent to reconstruct.

        Returns:
            Reconstructed AgentState, or None if no events exist.
        """
        snapshot = self._store.get_latest_snapshot(agent_id)
        since_seq = 0
        initial: AgentState | None = None
        if snapshot is not None:
            since_seq, state_dict = snapshot
            initial = AgentState.from_dict(state_dict)
        events = self._store.get_stream(agent_id, since_seq=since_seq)
        if not events and initial is None:
            return None
        current: AgentState = (
            initial if initial is not None else AgentState(agent_id=agent_id)
        )
        for event in events:
            current = self._projector(current, event)
        return current

    def replay_count(self, agent_id: str) -> int:
        """Return how many delta events would be replayed.

        With snapshots in place, this is at most ``snapshot_every`` events.

        Args:
            agent_id: Agent to query.

        Returns:
            Number of events that ``build_state`` would process.
        """
        snapshot = self._store.get_latest_snapshot(agent_id)
        since_seq = snapshot[0] if snapshot is not None else 0
        return len(self._store.get_stream(agent_id, since_seq=since_seq))
