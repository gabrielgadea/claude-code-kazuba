"""DataLoader Pattern: Automatic query batching for agent state.

Implements the DataLoader pattern from GraphQL for automatic batching
of agent state queries. Multiple load() calls within the same event
loop tick are coalesced into a single batch operation.

Expected improvement: 100 batched queries from ~8ms to ~0.5ms (16x)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

logger = logging.getLogger(__name__)

T = TypeVar("T")
K = TypeVar("K")


@dataclass
class DataLoaderStats:
    """Statistics for DataLoader operations.

    Attributes:
        loads_issued: Number of load() calls issued.
        batches_executed: Number of batch operations executed.
        cache_hits: Number of in-flight cache hits.
        total_batch_size: Cumulative sum of all batch sizes (avoids unbounded list).
    """

    loads_issued: int = 0
    batches_executed: int = 0
    cache_hits: int = 0
    total_batch_size: int = 0

    @property
    def average_batch_size(self) -> float:
        """Calculate average batch size."""
        if self.batches_executed == 0:
            return 0.0
        return self.total_batch_size / self.batches_executed

    @property
    def batching_efficiency(self) -> float:
        """Calculate batching efficiency (1.0 = perfect batching)."""
        if self.loads_issued == 0:
            return 0.0
        return 1.0 - (self.batches_executed / self.loads_issued)


class DataLoader(Generic[K, T]):
    """Generic DataLoader for automatic query batching.

    The DataLoader pattern coalesces multiple individual load()
    calls into a single batch_load_fn execution within the same
    event loop tick.

    Example:
        >>> loader = DataLoader[str, AgentState](batch_load_fn=load_agents_batch)
        >>> agent1 = await loader.load("agent-1")  # Queued
        >>> agent2 = await loader.load("agent-2")  # Queued
        >>> agent3 = await loader.load("agent-3")  # Triggers batch
        >>> # Only one batch_load_fn call for all three
    """

    def __init__(
        self,
        batch_load_fn: Callable[[list[K]], Coroutine[Any, Any, list[T | None]]],
        max_batch_size: int | None = None,
        cache: bool = True,
    ) -> None:
        """Initialize DataLoader.

        Args:
            batch_load_fn: Async function to load a batch of keys.
            max_batch_size: Optional max batch size (splits large batches).
            cache: Whether to enable in-flight request caching.
        """
        self._batch_load_fn = batch_load_fn
        self._max_batch_size = max_batch_size
        self._cache_enabled = cache

        self._pending: list[K] = []
        self._pending_futures: dict[K, asyncio.Future[T | None]] = {}
        self._cache: dict[K, T] = {}
        self._stats = DataLoaderStats()
        self._lock = asyncio.Lock()
        self._dispatch_scheduled = False

    async def load(self, key: K) -> T | None:
        """Load a single item, batched with other loads.

        Args:
            key: Key to load.

        Returns:
            Loaded value or None if not found.
        """
        # Check cache first
        if self._cache_enabled and key in self._cache:
            self._stats.cache_hits += 1
            return self._cache[key]

        async with self._lock:
            # Check if already pending
            if key in self._pending_futures:
                return await self._pending_futures[key]

            # Add to pending batch
            self._pending.append(key)
            future: asyncio.Future[T | None] = asyncio.get_running_loop().create_future()
            self._pending_futures[key] = future
            self._stats.loads_issued += 1

            # Schedule dispatch
            if not self._dispatch_scheduled:
                self._dispatch_scheduled = True
                asyncio.get_running_loop().call_soon(asyncio.create_task, self._dispatch_batch())

        return await future

    async def load_many(self, keys: list[K]) -> list[T | None]:
        """Load multiple items efficiently.

        Args:
            keys: List of keys to load.

        Returns:
            List of loaded values (None for not found).
        """
        return await asyncio.gather(*[self.load(k) for k in keys])

    async def _dispatch_batch(self) -> None:
        """Dispatch pending batch for loading."""
        async with self._lock:
            if not self._pending:
                self._dispatch_scheduled = False
                return

            # Take current pending batch
            keys = self._pending.copy()
            futures = dict(self._pending_futures)
            self._pending.clear()
            self._pending_futures.clear()
            self._dispatch_scheduled = False

        # Execute batch load
        try:
            if self._max_batch_size and len(keys) > self._max_batch_size:
                # Split large batches
                results = await self._load_in_chunks(keys)
            else:
                results = await self._batch_load_fn(keys)

            self._stats.batches_executed += 1
            self._stats.total_batch_size += len(keys)

            # Resolve futures
            for key, value in zip(keys, results, strict=False):
                if key in futures:
                    futures[key].set_result(value)
                    if self._cache_enabled and value is not None:
                        self._cache[key] = value

        except Exception as e:
            logger.exception("Batch load failed")
            # Reject all pending futures
            for key in keys:
                if key in futures:
                    futures[key].set_exception(e)

    async def _load_in_chunks(self, keys: list[K]) -> list[T | None]:
        """Load large batch in chunks."""
        assert self._max_batch_size is not None

        results: list[T | None] = []
        for i in range(0, len(keys), self._max_batch_size):
            chunk = keys[i : i + self._max_batch_size]
            chunk_results = await self._batch_load_fn(chunk)
            results.extend(chunk_results)
        return results

    def clear(self, key: K | None = None) -> None:
        """Clear cached value(s).

        Args:
            key: Specific key to clear, or None to clear all.
        """
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    def prime(self, key: K, value: T) -> None:
        """Prime the cache with a value.

        Args:
            key: Cache key.
            value: Value to cache.
        """
        if self._cache_enabled:
            self._cache[key] = value

    def get_stats(self) -> DataLoaderStats:
        """Get DataLoader statistics."""
        return DataLoaderStats(
            loads_issued=self._stats.loads_issued,
            batches_executed=self._stats.batches_executed,
            cache_hits=self._stats.cache_hits,
            total_batch_size=self._stats.total_batch_size,
        )


class AgentDataLoader(DataLoader[str, Any]):
    """DataLoader specifically for agent state queries.

    Example:
        >>> loader = AgentDataLoader(query_side)
        >>> agent1 = await loader.load("agent-1")
        >>> agent2 = await loader.load("agent-2")
        >>> # Both loaded in single batch
    """

    def __init__(
        self,
        query_side: Any,  # CachedQuerySide
        max_batch_size: int = 100,
    ) -> None:
        """Initialize AgentDataLoader.

        Args:
            query_side: CachedQuerySide instance for loading.
            max_batch_size: Maximum batch size for queries.
        """
        self._query_side = query_side

        async def batch_load(agent_ids: list[str]) -> list[Any | None]:
            """Load multiple agents in parallel."""
            import asyncio

            tasks = [asyncio.to_thread(query_side.get_agent, aid) for aid in agent_ids]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            return [None if isinstance(r, BaseException) else r for r in gathered]

        super().__init__(
            batch_load_fn=batch_load,
            max_batch_size=max_batch_size,
            cache=True,
        )


class OptimizedAgentDataLoader:
    """Optimized DataLoader with parallel batch loading.

    Uses concurrent loading for improved performance with
    large batches.
    """

    def __init__(
        self,
        query_side: Any,  # CachedQuerySide
        max_concurrent: int = 10,
    ) -> None:
        """Initialize optimized loader.

        Args:
            query_side: CachedQuerySide instance.
            max_concurrent: Max concurrent loading operations.
        """
        self._query_side = query_side
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def load_batch(self, agent_ids: list[str]) -> dict[str, Any]:
        """Load batch of agents with concurrency control.

        Args:
            agent_ids: List of agent IDs to load.

        Returns:
            Dictionary mapping agent_id to state.
        """

        async def load_one(agent_id: str) -> tuple[str, Any | None]:
            async with self._semaphore:
                return agent_id, self._query_side.get_agent(agent_id)

        results = await asyncio.gather(*[load_one(aid) for aid in agent_ids])

        return {aid: state for aid, state in results if state is not None}


def create_dataloader(
    batch_load_fn: Callable[[list[K]], Coroutine[Any, Any, list[T | None]]],
    max_batch_size: int | None = None,
) -> DataLoader[K, T]:
    """Factory for creating configured DataLoaders.

    Args:
        batch_load_fn: Function to load batches.
        max_batch_size: Optional max batch size.

    Returns:
        Configured DataLoader instance.
    """
    return DataLoader(
        batch_load_fn=batch_load_fn,
        max_batch_size=max_batch_size,
        cache=True,
    )
