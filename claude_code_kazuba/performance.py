"""Performance utilities: caching, parallel execution, and Rust acceleration."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

# Singleton cache for rust_accelerator
_rust_accel_cache: dict[str, Any] = {}
_RUST_KEY = "_instance"


class L0Cache[T]:
    """Generic in-memory LRU cache with TTL.

    A simple cache that evicts the oldest entries when max_size is reached
    and automatically expires entries older than ttl_seconds.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 300.0) -> None:
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._data: dict[str, tuple[T, float]] = {}

    def get(self, key: str) -> T | None:
        """Get a value by key, returning None if missing or expired."""
        entry = self._data.get(key)
        if entry is None:
            return None
        value, timestamp = entry
        if time.monotonic() - timestamp > self._ttl_seconds:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: T) -> None:
        """Set a key-value pair, evicting oldest if at capacity."""
        # Remove existing key first (to update position in insertion order)
        if key in self._data:
            del self._data[key]
        # Evict oldest if at capacity
        while len(self._data) >= self._max_size:
            oldest_key = next(iter(self._data))
            del self._data[oldest_key]
        self._data[key] = (value, time.monotonic())

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None

    def clear(self) -> None:
        """Remove all entries."""
        self._data.clear()


class ParallelExecutor:
    """Wrapper around ThreadPoolExecutor for parallel task execution."""

    def __init__(self, max_workers: int | None = None) -> None:
        self._max_workers = max_workers

    def run(self, tasks: list[Any]) -> list[Any]:
        """Run all callables in parallel and return results.

        Args:
            tasks: List of callables to execute.

        Returns:
            List of results in submission order.
        """
        if not tasks:
            return []
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = [executor.submit(task) for task in tasks]
            return [f.result() for f in futures]


def rust_accelerator() -> Any | None:
    """Singleton accessor for the Rust acceleration extension.

    Tries to import the RustAccelerator module. Returns the cached instance
    on subsequent calls, or None if the extension is unavailable.
    """
    if _RUST_KEY in _rust_accel_cache:
        return _rust_accel_cache[_RUST_KEY]
    instance: Any | None = None
    try:
        from claude_code_kazuba._rust_accel import (  # pyright: ignore[reportMissingImports]
            RustAccelerator,  # type: ignore[import-not-found]
        )

        instance = cast("Any", RustAccelerator())  # pyright: ignore[reportUnknownVariableType]
    except (ImportError, ModuleNotFoundError):
        pass
    _rust_accel_cache[_RUST_KEY] = instance
    return instance
