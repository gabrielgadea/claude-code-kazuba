"""Thread-safe circuit breaker with 3 states: CLOSED, OPEN, HALF_OPEN.

State machine:
    CLOSED  --(max_failures reached)--> OPEN
    OPEN    --(cooldown elapsed)------> HALF_OPEN
    HALF_OPEN --(success)-------------> CLOSED
    HALF_OPEN --(failure)-------------> OPEN

Thread-safe via threading.RLock per breaker and per registry.

Usage:
    cb = CircuitBreaker("my-service")
    result = cb.call(some_function, arg1, arg2)

    # Or manual recording:
    if not cb.is_open:
        try:
            result = do_work()
            cb.record_success()
        except Exception as e:
            cb.record_failure(e)

    # Context manager:
    with cb:
        cb.record_success()

    # Registry for shared breakers:
    registry = CircuitBreakerRegistry()
    cb = registry.get_or_create("service-a", config)
"""

from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Any

from pydantic import BaseModel


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerConfig(BaseModel, frozen=True):
    """Immutable configuration for a circuit breaker.

    Args:
        max_failures: Consecutive failures before transitioning to OPEN.
        cooldown_seconds: Seconds to wait in OPEN before trying HALF_OPEN.
        half_open_max: Max probe calls allowed in HALF_OPEN state.
    """

    max_failures: int = 5
    cooldown_seconds: float = 60.0
    half_open_max: int = 1


class CircuitBreakerOpenError(Exception):
    """Raised when a call is attempted on an OPEN circuit breaker."""

    def __init__(self, name: str) -> None:
        self.breaker_name = name
        super().__init__(f"Circuit breaker '{name}' is OPEN — call rejected")


class CircuitBreaker:
    """Thread-safe circuit breaker for protecting external calls.

    Tracks consecutive failures and transitions through three states:
    CLOSED (normal), OPEN (rejecting calls), HALF_OPEN (probing).

    Args:
        name: Identifier for this circuit breaker.
        config: Configuration parameters. Uses defaults if not provided.
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._lock = threading.RLock()

        # Mutable state
        self._state = CircuitBreakerState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._half_open_calls = 0

    @property
    def name(self) -> str:
        """Return the breaker name."""
        return self._name

    @property
    def state(self) -> CircuitBreakerState:
        """Current state, with automatic OPEN -> HALF_OPEN transition check."""
        with self._lock:
            self._maybe_transition()
            return self._state

    @property
    def is_open(self) -> bool:
        """True if circuit is OPEN (calls should be rejected).

        HALF_OPEN returns False to allow probe calls through.
        """
        return self.state == CircuitBreakerState.OPEN

    @property
    def failure_count(self) -> int:
        """Current consecutive failure count."""
        with self._lock:
            return self._consecutive_failures

    def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute func with circuit breaker protection.

        Args:
            func: Callable to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            The return value of func.

        Raises:
            CircuitBreakerOpenError: If the circuit is OPEN.
            Exception: Any exception raised by func (also recorded as failure).
        """
        with self._lock:
            self._maybe_transition()
            if self._state == CircuitBreakerState.OPEN:
                raise CircuitBreakerOpenError(self._name)

        try:
            result = func(*args, **kwargs)
        except Exception:
            self.record_failure(None)
            raise
        else:
            self.record_success()
            return result

    def record_success(self) -> None:
        """Record a successful execution.

        In HALF_OPEN state, transitions back to CLOSED.
        In CLOSED state, resets consecutive failure counter.
        """
        with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._consecutive_failures = 0
                self._half_open_calls = 0
                self._transition_to(CircuitBreakerState.CLOSED)
            elif self._state == CircuitBreakerState.CLOSED:
                self._consecutive_failures = 0

    def record_failure(self, error: Exception | None) -> None:
        """Record a failed execution.

        In HALF_OPEN state, transitions back to OPEN with fresh cooldown.
        In CLOSED state, increments counter and may transition to OPEN.

        Args:
            error: The exception that caused the failure (for diagnostics).
        """
        with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._consecutive_failures = 0
                self._half_open_calls = 0
                self._transition_to(CircuitBreakerState.OPEN)
                self._opened_at = time.monotonic()
            elif self._state == CircuitBreakerState.CLOSED:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self._config.max_failures:
                    self._transition_to(CircuitBreakerState.OPEN)
                    self._opened_at = time.monotonic()

    def reset(self) -> None:
        """Force circuit breaker back to CLOSED state, clearing all counters."""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._consecutive_failures = 0
            self._opened_at = None
            self._half_open_calls = 0

    def _maybe_transition(self) -> None:
        """Check if OPEN should transition to HALF_OPEN based on cooldown.

        Must be called with self._lock held.
        """
        if self._state == CircuitBreakerState.OPEN and self._opened_at is not None:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self._config.cooldown_seconds:
                self._transition_to(CircuitBreakerState.HALF_OPEN)
                self._half_open_calls = 0

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """Internal state transition. Must be called with self._lock held."""
        self._state = new_state

    def __enter__(self) -> CircuitBreaker:
        """Support usage as context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit context manager. Does not suppress exceptions."""


class CircuitBreakerRegistry:
    """Registry of named circuit breakers. Thread-safe.

    Provides get_or_create semantics so multiple callers can share
    the same circuit breaker instance by name.

    Usage:
        registry = CircuitBreakerRegistry()
        cb = registry.get_or_create("my-service")
        result = cb.call(external_call)
    """

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()

    def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get an existing breaker or create a new one.

        Args:
            name: Unique name for the circuit breaker.
            config: Configuration to use if creating a new breaker.

        Returns:
            The CircuitBreaker instance for the given name.
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        """Get an existing breaker by name, or None if not found.

        Args:
            name: Name of the circuit breaker.

        Returns:
            The CircuitBreaker if found, None otherwise.
        """
        with self._lock:
            return self._breakers.get(name)

    def reset_all(self) -> None:
        """Reset all registered breakers to CLOSED state."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
