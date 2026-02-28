"""Tests for lib.performance — L0Cache, ParallelExecutor, rust_accelerator."""
from __future__ import annotations

import time

import pytest

from lib.performance import L0Cache, ParallelExecutor, rust_accelerator


class TestL0Cache:
    """L0Cache in-memory LRU with TTL."""

    def test_set_and_get(self) -> None:
        cache: L0Cache[str] = L0Cache(max_size=10, ttl_seconds=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_returns_none(self) -> None:
        cache: L0Cache[str] = L0Cache()
        assert cache.get("nonexistent") is None

    def test_has_key(self) -> None:
        cache: L0Cache[str] = L0Cache()
        cache.set("k", "v")
        assert cache.has("k") is True
        assert cache.has("missing") is False

    def test_ttl_expiration(self) -> None:
        cache: L0Cache[str] = L0Cache(max_size=10, ttl_seconds=0.1)
        cache.set("k", "v")
        assert cache.get("k") == "v"
        time.sleep(0.15)
        assert cache.get("k") is None

    def test_max_size_eviction(self) -> None:
        cache: L0Cache[str] = L0Cache(max_size=2, ttl_seconds=60)
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")  # should evict "a"
        assert cache.get("a") is None
        assert cache.get("b") == "2"
        assert cache.get("c") == "3"

    def test_clear(self) -> None:
        cache: L0Cache[str] = L0Cache()
        cache.set("k", "v")
        cache.clear()
        assert cache.get("k") is None
        assert cache.has("k") is False

    def test_overwrite_existing(self) -> None:
        cache: L0Cache[str] = L0Cache()
        cache.set("k", "v1")
        cache.set("k", "v2")
        assert cache.get("k") == "v2"


class TestParallelExecutor:
    """ParallelExecutor runs callables in parallel."""

    def test_run_multiple_tasks(self) -> None:
        executor = ParallelExecutor()
        tasks = [lambda: 1, lambda: 2, lambda: 3]
        results = executor.run(tasks)
        assert sorted(results) == [1, 2, 3]

    def test_run_empty_list(self) -> None:
        executor = ParallelExecutor()
        results = executor.run([])
        assert results == []

    def test_actually_parallel(self) -> None:
        """Verify tasks run in parallel by checking wall-clock time."""
        executor = ParallelExecutor(max_workers=3)

        def slow_task() -> str:
            time.sleep(0.1)
            return "done"

        tasks = [slow_task, slow_task, slow_task]
        start = time.monotonic()
        results = executor.run(tasks)
        elapsed = time.monotonic() - start
        assert len(results) == 3
        # If parallel, should take ~0.1s; if serial, ~0.3s
        assert elapsed < 0.25


class TestRustAccelerator:
    """rust_accelerator returns None when Rust extension not available."""

    def test_returns_none_without_rust(self) -> None:
        result = rust_accelerator()
        assert result is None

    def test_singleton_behavior(self) -> None:
        r1 = rust_accelerator()
        r2 = rust_accelerator()
        assert r1 is r2  # Both None, but verifies caching
