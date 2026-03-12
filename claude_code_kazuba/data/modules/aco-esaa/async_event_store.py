"""AsyncEventStore: Asynchronous I/O wrapper for EventStore.

This module provides async wrappers around the synchronous EventStore,
enabling non-blocking event persistence with batching support.

Uses kazuba_shared.async_utils for running sync operations in thread pool.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .event_buffer import BatchedEventStore, BufferConfig, DomainEvent

logger = logging.getLogger(__name__)


@dataclass
class AsyncStoreStats:
    """Statistics for async event store operations.

    Attributes:
        pending_operations: Number of operations in flight.
        completed_operations: Total completed operations.
        failed_operations: Total failed operations.
        cache_hits: Number of in-memory cache hits.
        cache_misses: Number of cache misses requiring disk read.
    """

    pending_operations: int = 0
    completed_operations: int = 0
    failed_operations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


class AsyncEventStore:
    """Asynchronous wrapper for BatchedEventStore.

    Provides async methods for event persistence while maintaining
    the performance benefits of batched writes.

    All write operations are non-blocking and execute in a thread pool.
    Read operations use an in-memory cache to avoid disk I/O.

    Example:
        >>> store = AsyncEventStore("/tmp/events")
        >>> event = DomainEvent(
        ...     event_id="uuid-123",
        ...     event_type="agent_created",
        ...     agent_id="agent-1",
        ...     timestamp=time.time(),
        ...     payload={"status": "active"},
        ... )
        >>> await store.append(event)
        >>> events = await store.get_stream("agent-1")
    """

    def __init__(
        self,
        storage_path: Path | str,
        buffer_config: BufferConfig | None = None,
        max_workers: int | None = None,
    ) -> None:
        """Initialize the async event store.

        Args:
            storage_path: Path to store event streams.
            buffer_config: Optional buffer configuration.
            max_workers: Max thread pool workers (None = default).
        """
        self._storage_path = Path(storage_path)
        self._buffer_config = buffer_config
        self._max_workers = max_workers

        self._store: BatchedEventStore | None = None
        self._store_lock = asyncio.Lock()
        self._cache: dict[str, list[DomainEvent]] = {}
        self._stats = AsyncStoreStats()

    async def _get_store(self) -> BatchedEventStore:
        """Lazy initialization of underlying store (double-check lock pattern)."""
        if self._store is not None:
            return self._store
        async with self._store_lock:
            if self._store is None:
                from .event_buffer import BatchedEventStore

                loop = asyncio.get_running_loop()
                self._store = await loop.run_in_executor(
                    None,
                    lambda: BatchedEventStore(
                        storage_path=self._storage_path,
                        buffer_config=self._buffer_config,
                    ),
                )
        assert self._store is not None
        return self._store

    async def append(self, event: DomainEvent) -> None:
        """Append an event asynchronously.

        The event is added to the in-memory buffer immediately.
        Disk persistence happens asynchronously in batches.

        Args:
            event: The domain event to append.
        """
        store = await self._get_store()
        loop = asyncio.get_running_loop()

        self._stats.pending_operations += 1
        try:
            await loop.run_in_executor(None, store.append, event)
            self._stats.completed_operations += 1
        except Exception as e:
            self._stats.failed_operations += 1
            logger.exception("Failed to append event: %s", event.event_id)
            raise RuntimeError(f"Event append failed: {e}") from e
        finally:
            self._stats.pending_operations -= 1

    async def append_batch(self, events: list[DomainEvent]) -> None:
        """Append multiple events in a single batch.

        More efficient than multiple append() calls as it reduces
        lock contention and amortizes overhead.

        Args:
            events: List of domain events to append.
        """
        store = await self._get_store()
        loop = asyncio.get_running_loop()

        self._stats.pending_operations += 1
        try:
            # Use gather for concurrent appends; return_exceptions=True means we
            # must inspect results — exceptions are returned as values, not raised.
            results = await asyncio.gather(
                *[loop.run_in_executor(None, store.append, e) for e in events],
                return_exceptions=True,
            )
            failures = [r for r in results if isinstance(r, BaseException)]
            if failures:
                self._stats.failed_operations += len(failures)
                logger.warning(
                    "Failed to append %d of %d events in batch",
                    len(failures),
                    len(events),
                )
            self._stats.completed_operations += len(events) - len(failures)
        except Exception as e:
            self._stats.failed_operations += 1
            logger.exception("Failed to append batch of %d events", len(events))
            raise RuntimeError(f"Batch append failed: {e}") from e
        finally:
            self._stats.pending_operations -= 1

    async def get_stream(self, agent_id: str) -> list[DomainEvent]:
        """Get all events for an agent (async with caching).

        Checks in-memory cache first, then loads from disk if needed.

        Args:
            agent_id: The agent ID to query.

        Returns:
            List of events for the agent.
        """
        # Check cache first
        if agent_id in self._cache:
            self._stats.cache_hits += 1
            return self._cache[agent_id].copy()

        self._stats.cache_misses += 1

        # Async load from disk
        store = await self._get_store()
        loop = asyncio.get_running_loop()

        events = await loop.run_in_executor(None, store.get_stream, agent_id)
        self._cache[agent_id] = events
        return events

    async def get_stream_async(
        self,
        agent_id: str,
        use_cache: bool = True,
    ) -> list[DomainEvent]:
        """Async stream retrieval with optional cache bypass.

        Args:
            agent_id: The agent ID to query.
            use_cache: If False, always read from disk.

        Returns:
            List of events for the agent.
        """
        if use_cache and agent_id in self._cache:
            self._stats.cache_hits += 1
            return self._cache[agent_id].copy()

        return await self.get_stream(agent_id)

    async def replay(
        self,
        agent_id: str,
        handler: Callable[[DomainEvent], Any],
    ) -> int:
        """Replay all events for an agent through an async handler.

        Args:
            agent_id: The agent ID to replay.
            handler: Async callback function for each event.

        Returns:
            Number of events replayed.
        """
        events = await self.get_stream(agent_id)

        # Call handler for each event
        for event in events:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result

        return len(events)

    async def get_events_by_type(self, event_type: str) -> list[DomainEvent]:
        """Get all events of a specific type.

        Args:
            event_type: The event type to filter by.

        Returns:
            List of matching events.
        """
        store = await self._get_store()
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            None,
            store.get_events_by_type,
            event_type,
        )

    async def get_correlated_events(self, correlation_id: str) -> list[DomainEvent]:
        """Get all events with a specific correlation ID.

        Args:
            correlation_id: The correlation ID to search for.

        Returns:
            List of correlated events.
        """
        store = await self._get_store()
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            None,
            store.get_correlated_events,
            correlation_id,
        )

    async def flush(self) -> list[DomainEvent]:
        """Force flush all pending events to disk.

        Returns:
            List of events that were flushed.
        """
        store = await self._get_store()
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(None, store.flush)

    async def shutdown(self, flush_remaining: bool = True) -> None:
        """Shutdown the store gracefully.

        Args:
            flush_remaining: If True, flush all pending events.
        """
        if self._store:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                self._store.shutdown,
                flush_remaining,
            )
            self._store = None

        logger.info("AsyncEventStore shutdown complete")

    def invalidate_cache(self, agent_id: str | None = None) -> None:
        """Invalidate the in-memory cache.

        Args:
            agent_id: If provided, invalidate only that agent's cache.
                     If None, invalidate entire cache.
        """
        if agent_id:
            self._cache.pop(agent_id, None)
        else:
            self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get store and cache statistics.

        Returns:
            Dictionary with store and async operation stats.
        """
        stats: dict[str, Any] = {
            "async": {
                "pending_ops": self._stats.pending_operations,
                "completed_ops": self._stats.completed_operations,
                "failed_ops": self._stats.failed_operations,
                "cache_hits": self._stats.cache_hits,
                "cache_misses": self._stats.cache_misses,
                "cache_size": len(self._cache),
            }
        }

        if self._store:
            stats["store"] = self._store.get_stats()

        return stats

    async def __aenter__(self) -> AsyncEventStore:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Async context manager exit with automatic shutdown."""
        await self.shutdown(flush_remaining=True)
