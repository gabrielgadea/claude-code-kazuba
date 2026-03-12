"""Query Cache: LRU-based caching for agent state queries.

Provides configurable cache with size limits and TTL support.
Complements CachedQuerySide with additional caching strategies.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")
K = TypeVar("K")


@dataclass
class CacheEntry[T]:
    """Single cache entry with metadata.

    Attributes:
        value: Cached value.
        created_at: Timestamp when entry was created.
        accessed_at: Timestamp of last access.
        access_count: Number of times entry was accessed.
    """

    value: T
    created_at: float
    accessed_at: float
    access_count: int = 0


@dataclass
class QueryCacheStats:
    """Statistics for query cache.

    Attributes:
        hits: Number of cache hits.
        misses: Number of cache misses.
        evictions: Number of entries evicted.
        expired: Number of entries expired (TTL).
        current_size: Current cache size.
        max_size: Maximum cache size.
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired: int = 0
    current_size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


class LRUQueryCache[K, T]:
    """LRU (Least Recently Used) cache for query results.

    Provides O(1) get/put operations with automatic eviction
    when capacity is reached. Thread-safe with RLock.

    Example:
        >>> cache = LRUQueryCache[str, AgentState](max_size=100)
        >>> cache.put("agent-1", agent_state)
        >>> state = cache.get("agent-1")  # Cache hit
        >>> stats = cache.get_stats()
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: float | None = None,
    ) -> None:
        """Initialize LRU cache.

        Args:
            max_size: Maximum number of cached entries.
            ttl_seconds: Optional TTL for cache entries.
        """
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache: OrderedDict[K, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = QueryCacheStats(max_size=max_size)

    def get(self, key: K) -> T | None:
        """Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found/expired.
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            # Check TTL
            if self._ttl_seconds:
                age = time.monotonic() - entry.created_at
                if age > self._ttl_seconds:
                    del self._cache[key]
                    self._stats.expired += 1
                    self._stats.misses += 1
                    return None

            # Update access metadata
            entry.accessed_at = time.monotonic()
            entry.access_count += 1

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats.hits += 1

            return entry.value

    def put(self, key: K, value: T) -> None:
        """Store value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
        """
        with self._lock:
            # Evict LRU if inserting a new key at capacity
            if key not in self._cache and len(self._cache) >= self._max_size:
                self._evict_lru()

            now = time.monotonic()
            self._cache[key] = CacheEntry(
                value=value,
                created_at=now,
                accessed_at=now,
                access_count=0,
            )
            self._cache.move_to_end(key)

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._cache:
            # OrderedDict maintains insertion order
            # First item is oldest (LRU)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._stats.evictions += 1

    def invalidate(self, key: K) -> bool:
        """Remove specific key from cache.

        Args:
            key: Cache key to invalidate.

        Returns:
            True if key existed, False otherwise.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern.

        Args:
            pattern: Substring to match in keys (str keys only).

        Returns:
            Number of entries invalidated.
        """
        with self._lock:
            to_remove = [k for k in self._cache.keys() if isinstance(k, str) and pattern in k]
            for key in to_remove:
                del self._cache[key]
            return len(to_remove)

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_stats(self) -> QueryCacheStats:
        """Get cache statistics."""
        with self._lock:
            return QueryCacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                expired=self._stats.expired,
                current_size=len(self._cache),
                max_size=self._max_size,
            )

    def get_size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def contains(self, key: K) -> bool:
        """Check if key exists in cache (without updating access time).

        Args:
            key: Cache key to check.

        Returns:
            True if key exists and not expired.
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False

            if self._ttl_seconds:
                age = time.monotonic() - entry.created_at
                if age > self._ttl_seconds:
                    del self._cache[key]
                    self._stats.expired += 1
                    return False

            return True


class TieredQueryCache[K, T]:
    """Two-tier cache: L1 (in-memory) + L2 (optional external).

    L1: Fast LRU cache in local memory
    L2: External cache (e.g., Redis, shared memory)

    Example:
        >>> cache = TieredQueryCache[str, AgentState](
        ...     l1_size=100,
        ...     l2_get=redis_get,
        ...     l2_set=redis_set,
        ... )
    """

    def __init__(
        self,
        l1_size: int = 1000,
        l2_get: Callable[[K], T | None] | None = None,
        l2_set: Callable[[K, T], None] | None = None,
    ) -> None:
        """Initialize tiered cache.

        Args:
            l1_size: Size of L1 cache.
            l2_get: Optional L2 cache get function.
            l2_set: Optional L2 cache set function.
        """
        self._l1 = LRUQueryCache[K, T](max_size=l1_size)
        self._l2_get = l2_get
        self._l2_set = l2_set
        self._lock = threading.RLock()
        self._l2_hits = 0
        self._l2_misses = 0

    def get(self, key: K) -> T | None:
        """Get value from cache (L1 -> L2 -> None).

        Args:
            key: Cache key.

        Returns:
            Cached value or None.
        """
        # Try L1 first
        value = self._l1.get(key)
        if value is not None:
            return value

        # Try L2
        if self._l2_get:
            value = self._l2_get(key)
            if value is not None:
                with self._lock:
                    self._l2_hits += 1
                # Promote to L1
                self._l1.put(key, value)
                return value
            with self._lock:
                self._l2_misses += 1

        return None

    def put(self, key: K, value: T, l2: bool = False) -> None:
        """Store value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            l2: If True, also store in L2 cache.
        """
        self._l1.put(key, value)

        if l2 and self._l2_set:
            self._l2_set(key, value)

    def invalidate(self, key: K) -> bool:
        """Invalidate key from L1 cache.

        Args:
            key: Cache key.

        Returns:
            True if key existed in L1.
        """
        return self._l1.invalidate(key)

    def get_stats(self) -> dict[str, Any]:
        """Get combined cache statistics."""
        l1_stats = self._l1.get_stats()
        with self._lock:
            l2_hits = self._l2_hits
            l2_misses = self._l2_misses
        total = l2_hits + l2_misses
        return {
            "l1": {
                "hits": l1_stats.hits,
                "misses": l1_stats.misses,
                "hit_rate": l1_stats.hit_rate,
                "size": l1_stats.current_size,
            },
            "l2": {
                "hits": l2_hits,
                "misses": l2_misses,
                "hit_rate": l2_hits / total if total > 0 else 0.0,
            },
        }


def create_default_query_cache() -> LRUQueryCache[str, Any]:
    """Factory for default query cache configuration.

    Returns:
        Configured LRU cache for agent queries.
    """
    return LRUQueryCache[str, Any](
        max_size=10000,
        ttl_seconds=300.0,  # 5 minute TTL
    )
