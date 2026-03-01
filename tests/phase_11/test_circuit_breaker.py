"""Tests for lib.circuit_breaker — Phase 11 shared infrastructure."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from lib.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
    CircuitBreakerState,
)


class TestCircuitBreakerState:
    """Tests for the CircuitBreakerState enum."""

    def test_states_exist(self) -> None:
        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig Pydantic model."""

    def test_config_defaults(self) -> None:
        config = CircuitBreakerConfig()
        assert config.max_failures == 5
        assert config.cooldown_seconds == 60.0
        assert config.half_open_max == 1

    def test_config_custom_values(self) -> None:
        config = CircuitBreakerConfig(
            max_failures=10, cooldown_seconds=30.0, half_open_max=3
        )
        assert config.max_failures == 10
        assert config.cooldown_seconds == 30.0
        assert config.half_open_max == 3

    def test_config_is_frozen(self) -> None:
        config = CircuitBreakerConfig()
        with pytest.raises(Exception):
            config.max_failures = 10  # type: ignore[misc]


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class."""

    def test_initial_state_is_closed(self) -> None:
        cb = CircuitBreaker("test")
        assert cb.state == CircuitBreakerState.CLOSED

    def test_successful_call_stays_closed(self) -> None:
        cb = CircuitBreaker("test")
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == CircuitBreakerState.CLOSED

    def test_failure_increments_count(self) -> None:
        cb = CircuitBreaker("test", CircuitBreakerConfig(max_failures=5))

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            cb.call(failing)
        assert cb.failure_count == 1

    def test_max_failures_opens_circuit(self) -> None:
        config = CircuitBreakerConfig(max_failures=3)
        cb = CircuitBreaker("test", config)

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(failing)

        assert cb.state == CircuitBreakerState.OPEN

    def test_open_circuit_rejects_calls(self) -> None:
        config = CircuitBreakerConfig(max_failures=2)
        cb = CircuitBreaker("test", config)

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(failing)

        assert cb.is_open
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: 42)

    def test_cooldown_transitions_to_half_open(self) -> None:
        config = CircuitBreakerConfig(max_failures=1, cooldown_seconds=0.05)
        cb = CircuitBreaker("test", config)

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            cb.call(failing)
        assert cb.state == CircuitBreakerState.OPEN

        time.sleep(0.06)
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_success_closes_circuit(self) -> None:
        config = CircuitBreakerConfig(max_failures=1, cooldown_seconds=0.05)
        cb = CircuitBreaker("test", config)

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            cb.call(failing)
        time.sleep(0.06)

        assert cb.state == CircuitBreakerState.HALF_OPEN
        result = cb.call(lambda: "ok")
        assert result == "ok"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_half_open_failure_reopens_circuit(self) -> None:
        config = CircuitBreakerConfig(max_failures=1, cooldown_seconds=0.05)
        cb = CircuitBreaker("test", config)

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            cb.call(failing)
        time.sleep(0.06)

        assert cb.state == CircuitBreakerState.HALF_OPEN
        with pytest.raises(ValueError):
            cb.call(failing)
        assert cb.state == CircuitBreakerState.OPEN

    def test_reset_clears_state(self) -> None:
        config = CircuitBreakerConfig(max_failures=1)
        cb = CircuitBreaker("test", config)

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            cb.call(failing)
        assert cb.state == CircuitBreakerState.OPEN

        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_call_with_args_and_kwargs(self) -> None:
        cb = CircuitBreaker("test")

        def add(a: int, b: int, extra: int = 0) -> int:
            return a + b + extra

        result = cb.call(add, 1, 2, extra=3)
        assert result == 6

    def test_failure_count_property(self) -> None:
        cb = CircuitBreaker("test", CircuitBreakerConfig(max_failures=10))

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(failing)
        assert cb.failure_count == 3

    def test_is_open_property(self) -> None:
        cb = CircuitBreaker("test")
        assert cb.is_open is False

        config = CircuitBreakerConfig(max_failures=1)
        cb2 = CircuitBreaker("test2", config)

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            cb2.call(failing)
        assert cb2.is_open is True

    def test_context_manager(self) -> None:
        cb = CircuitBreaker("test")
        with cb:
            cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_context_manager_with_failure(self) -> None:
        config = CircuitBreakerConfig(max_failures=1)
        cb = CircuitBreaker("test", config)
        with cb:
            cb.record_failure(ValueError("boom"))
        assert cb.state == CircuitBreakerState.OPEN

    def test_thread_safety(self) -> None:
        config = CircuitBreakerConfig(max_failures=100)
        cb = CircuitBreaker("test", config)
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(50):
                    cb.call(lambda: 1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cb.state == CircuitBreakerState.CLOSED

    def test_record_success_resets_failures(self) -> None:
        config = CircuitBreakerConfig(max_failures=5)
        cb = CircuitBreaker("test", config)

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(failing)
        assert cb.failure_count == 3

        cb.record_success()
        assert cb.failure_count == 0

    def test_record_failure_with_error(self) -> None:
        config = CircuitBreakerConfig(max_failures=5)
        cb = CircuitBreaker("test", config)
        err = RuntimeError("test error")
        cb.record_failure(err)
        assert cb.failure_count == 1

    def test_name_property(self) -> None:
        cb = CircuitBreaker("my-breaker")
        assert cb.name == "my-breaker"


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""

    def test_registry_get_or_create(self) -> None:
        registry = CircuitBreakerRegistry()
        cb = registry.get_or_create("test")
        assert isinstance(cb, CircuitBreaker)
        assert cb.name == "test"

    def test_registry_get_existing(self) -> None:
        registry = CircuitBreakerRegistry()
        cb1 = registry.get_or_create("test")
        cb2 = registry.get_or_create("test")
        assert cb1 is cb2

    def test_registry_get_nonexistent_returns_none(self) -> None:
        registry = CircuitBreakerRegistry()
        assert registry.get("nonexistent") is None

    def test_registry_get_after_create(self) -> None:
        registry = CircuitBreakerRegistry()
        registry.get_or_create("test")
        cb = registry.get("test")
        assert cb is not None
        assert cb.name == "test"

    def test_registry_reset_all(self) -> None:
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(max_failures=1)
        cb = registry.get_or_create("test", config)

        def failing() -> None:
            msg = "boom"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            cb.call(failing)
        assert cb.state == CircuitBreakerState.OPEN

        registry.reset_all()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_registry_with_custom_config(self) -> None:
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(max_failures=10, cooldown_seconds=120.0)
        cb = registry.get_or_create("custom", config)
        assert isinstance(cb, CircuitBreaker)
