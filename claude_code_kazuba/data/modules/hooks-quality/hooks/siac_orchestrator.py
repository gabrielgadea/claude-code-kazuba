#!/usr/bin/env python3
"""SIAC Orchestrator — Concurrent Motor Execution with Circuit Breaker.

Orchestrates multiple quality-checking motors concurrently using
ThreadPoolExecutor with per-motor timeout, circuit breaker, and metrics.

Motors:
    Motor1: AST Audit — Structural analysis
    Motor2: Type Sanitation — Type safety validation
    Motor3: Mutation Tester — Test robustness verification
    Motor4: Knowledge Sync — Persistent knowledge management

Event: PostToolUse (coordinated across all motors)
Exit codes:
    0 - ALLOW (all motors pass or unavailable)
    1 - BLOCK (1+ motor blocks)
    2 - WARN  (1+ motor warns, no blocks)

Fail-open: any unhandled exception exits 0.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
ALLOW: int = 0
BLOCK: int = 1
WARN: int = 2

# ---------------------------------------------------------------------------
# Motor registry — populated at import time (fail-open on ImportError)
# ---------------------------------------------------------------------------
# Each entry: (motor_name, callable | None)
# Motor callables must accept a dict context and return dict with "action" key.

motor1_hook: Any | None = None
motor2_hook: Any | None = None
motor3_hook: Any | None = None
motor4_hook: Any | None = None

MOTORS: list[tuple[str, Any]] = [
    ("Motor1_AST_Audit", motor1_hook),
    ("Motor2_Type_Sanitation", motor2_hook),
    ("Motor3_Mutation_Tester", motor3_hook),
    ("Motor4_Knowledge_Sync", motor4_hook),
]

# Per-motor execution timeout in seconds
MOTOR_TIMEOUT_S: float = 1.5


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MotorResult:
    """Immutable result from a single motor execution."""

    motor_name: str
    action: int  # 0=ALLOW, 1=BLOCK, 2=WARN
    details: dict[str, Any]
    execution_time_ms: float

    _ACTION_NAMES: dict[int, str] = field(
        default_factory=lambda: {0: "ALLOW", 1: "BLOCK", 2: "WARN"},
        compare=False,
        repr=False,
    )

    def action_name(self) -> str:
        """Human-readable action name."""
        return {0: "ALLOW", 1: "BLOCK", 2: "WARN"}.get(self.action, "UNKNOWN")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "motor": self.motor_name,
            "action": self.action,
            "action_name": self.action_name(),
            "details": self.details,
            "execution_time_ms": f"{self.execution_time_ms:.1f}",
        }


@dataclass
class SIACResult:
    """Combined result from all SIAC motors."""

    file_path: str
    motor_results: list[MotorResult]
    overall_action: int
    timestamp: str

    @property
    def has_blocks(self) -> bool:
        """True if any motor blocked."""
        return any(r.action == BLOCK for r in self.motor_results)

    @property
    def has_warnings(self) -> bool:
        """True if any motor warned."""
        return any(r.action == WARN for r in self.motor_results)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        action_name = {0: "ALLOW", 1: "BLOCK", 2: "WARN"}.get(
            self.overall_action, "UNKNOWN"
        )
        return {
            "timestamp": self.timestamp,
            "file_path": self.file_path,
            "overall_action": action_name,
            "motors": [r.to_dict() for r in self.motor_results],
            "summary": {
                "total_motors": len(self.motor_results),
                "blocks": sum(1 for r in self.motor_results if r.action == BLOCK),
                "warnings": sum(1 for r in self.motor_results if r.action == WARN),
                "allows": sum(1 for r in self.motor_results if r.action == ALLOW),
            },
        }


# ---------------------------------------------------------------------------
# Circuit Breaker (per-motor, thread-safe)
# ---------------------------------------------------------------------------


class MotorCircuitBreaker:
    """Per-motor circuit breaker: CLOSED -> OPEN (3 fails) -> HALF_OPEN (30s).

    States:
        closed    — normal operation
        open      — motor skipped (too many failures)
        half_open — probe call allowed after cooldown
    """

    FAILURE_THRESHOLD: int = 3
    COOLDOWN_S: float = 30.0

    def __init__(self) -> None:
        self._state: str = "closed"
        self._failures: int = 0
        self._last_failure_time: float | None = None
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        """True if circuit is open and cooldown has not elapsed."""
        with self._lock:
            if self._state != "open":
                return False
            if self._last_failure_time is not None:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.COOLDOWN_S:
                    return False  # Ready for half-open probe
            return True

    def should_attempt(self) -> bool:
        """True when a motor execution should be attempted.

        Returns True when circuit is closed or when open-but-cooled-down
        (transitioning to half_open).
        """
        with self._lock:
            if self._state in ("closed", "half_open"):
                return True
            # State is "open" — check cooldown
            if self._last_failure_time is not None:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.COOLDOWN_S:
                    self._state = "half_open"
                    logger.info("circuit_breaker_half_open (cooldown elapsed)")
                    return True
            return False

    def record_success(self) -> None:
        """Record a successful execution — resets circuit to closed."""
        with self._lock:
            self._state = "closed"
            self._failures = 0
            self._last_failure_time = None

    def record_failure(self) -> None:
        """Record a failure — opens circuit after threshold."""
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.monotonic()
            if self._failures >= self.FAILURE_THRESHOLD:
                self._state = "open"
                logger.warning("circuit_breaker_open failures=%d", self._failures)
            elif self._state == "half_open":
                self._state = "open"
                logger.warning("circuit_breaker_reopened (half_open failure)")

    def reset(self) -> None:
        """Force circuit back to closed (for testing / manual recovery)."""
        with self._lock:
            self._state = "closed"
            self._failures = 0
            self._last_failure_time = None


# Module-level registry of circuit breakers, persisted across calls
_circuit_breakers: dict[str, MotorCircuitBreaker] = {}
_cb_lock = threading.Lock()


def _get_circuit_breaker(motor_name: str) -> MotorCircuitBreaker:
    """Get or create a circuit breaker for a motor (thread-safe)."""
    with _cb_lock:
        if motor_name not in _circuit_breakers:
            _circuit_breakers[motor_name] = MotorCircuitBreaker()
        return _circuit_breakers[motor_name]


# ---------------------------------------------------------------------------
# Metrics Collection
# ---------------------------------------------------------------------------


@dataclass
class _MotorMetrics:
    """Accumulated per-motor metrics (thread-safe)."""

    successes: int = 0
    failures: int = 0
    timeouts: int = 0
    total_time_ms: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record_success(self, time_ms: float) -> None:
        """Record a successful execution with timing."""
        with self.lock:
            self.successes += 1
            self.total_time_ms += time_ms

    def record_failure(self, time_ms: float) -> None:
        """Record a failed execution with timing."""
        with self.lock:
            self.failures += 1
            self.total_time_ms += time_ms

    def record_timeout(self) -> None:
        """Record a timeout (duration = MOTOR_TIMEOUT_S)."""
        with self.lock:
            self.timeouts += 1
            self.total_time_ms += MOTOR_TIMEOUT_S * 1000

    def to_dict(self) -> dict[str, Any]:
        """Thread-safe snapshot as dict."""
        with self.lock:
            return {
                "successes": self.successes,
                "failures": self.failures,
                "timeouts": self.timeouts,
                "total_time_ms": self.total_time_ms,
            }


_metrics: dict[str, _MotorMetrics] = {}
_metrics_lock = threading.Lock()


def _get_motor_metrics(motor_name: str) -> _MotorMetrics:
    """Get or create metrics for a motor (thread-safe)."""
    with _metrics_lock:
        if motor_name not in _metrics:
            _metrics[motor_name] = _MotorMetrics()
        return _metrics[motor_name]


def get_metrics() -> dict[str, dict[str, Any]]:
    """Return a snapshot of all motor metrics.

    Returns:
        Mapping of motor_name -> {successes, failures, timeouts, total_time_ms}.
    """
    with _metrics_lock:
        return {name: m.to_dict() for name, m in _metrics.items()}


def reset_metrics() -> None:
    """Reset all accumulated metrics (useful for testing)."""
    with _metrics_lock:
        _metrics.clear()


def reset_circuit_breakers() -> None:
    """Reset all circuit breakers to closed state (useful for testing)."""
    with _cb_lock:
        for cb in _circuit_breakers.values():
            cb.reset()
        _circuit_breakers.clear()


# ---------------------------------------------------------------------------
# Single motor execution (runs inside a thread)
# ---------------------------------------------------------------------------


def _run_single_motor(
    motor_name: str,
    motor_hook: Any,
    context: dict[str, Any],
) -> MotorResult:
    """Execute one motor hook and return a MotorResult.

    All exceptions are caught and converted to WARN results so that a single
    motor failure never crashes the orchestrator.

    Args:
        motor_name: Identifier for the motor.
        motor_hook: Callable accepting a dict context, returning dict with "action".
        context: Hook input context.

    Returns:
        MotorResult capturing the motor's outcome and timing.
    """
    start_time = time.monotonic()
    try:
        result = motor_hook(context)
        execution_time = (time.monotonic() - start_time) * 1000
        return MotorResult(
            motor_name=motor_name,
            action=result.get("action", ALLOW),
            details={k: v for k, v in result.items() if k != "action"},
            execution_time_ms=execution_time,
        )
    except Exception as exc:
        execution_time = (time.monotonic() - start_time) * 1000
        return MotorResult(
            motor_name=motor_name,
            action=WARN,
            details={"error": str(exc)},
            execution_time_ms=execution_time,
        )


# ---------------------------------------------------------------------------
# Motor orchestration
# ---------------------------------------------------------------------------


def _determine_overall_action(motor_results: list[MotorResult]) -> int:
    """Compute aggregate action from all motor results.

    Priority: BLOCK > WARN > ALLOW.

    Args:
        motor_results: List of individual motor results.

    Returns:
        0 (ALLOW), 1 (BLOCK), or 2 (WARN).
    """
    if any(r.action == BLOCK for r in motor_results):
        return BLOCK
    if any(r.action == WARN for r in motor_results):
        return WARN
    return ALLOW


def _run_motors_concurrent(
    motors: list[tuple[str, Any]],
    context: dict[str, Any],
) -> list[MotorResult]:
    """Run available motors concurrently with timeout and circuit breaker.

    Args:
        motors: List of (motor_name, motor_hook) tuples.
        context: Hook input context.

    Returns:
        List of MotorResult objects.
    """
    if not motors:
        return []

    results: list[MotorResult] = []
    futures: dict[str, Future[MotorResult]] = {}

    executor = ThreadPoolExecutor(max_workers=len(motors))
    try:
        for motor_name, motor_hook in motors:
            cb = _get_circuit_breaker(motor_name)
            if not cb.should_attempt():
                results.append(
                    MotorResult(
                        motor_name=motor_name,
                        action=ALLOW,
                        details={"status": "skipped", "reason": "circuit_open"},
                        execution_time_ms=0.0,
                    )
                )
                continue
            futures[motor_name] = executor.submit(
                _run_single_motor, motor_name, motor_hook, context
            )

        for motor_name, future in futures.items():
            cb = _get_circuit_breaker(motor_name)
            mm = _get_motor_metrics(motor_name)
            try:
                result = future.result(timeout=MOTOR_TIMEOUT_S)
                if result.action == WARN and "error" in result.details:
                    cb.record_failure()
                    mm.record_failure(result.execution_time_ms)
                else:
                    cb.record_success()
                    mm.record_success(result.execution_time_ms)
                results.append(result)
            except FuturesTimeout:
                cb.record_failure()
                mm.record_timeout()
                logger.warning(
                    "motor_timeout motor=%s timeout_s=%.1f",
                    motor_name,
                    MOTOR_TIMEOUT_S,
                )
                results.append(
                    MotorResult(
                        motor_name=motor_name,
                        action=WARN,
                        details={"error": "timeout", "timeout_s": MOTOR_TIMEOUT_S},
                        execution_time_ms=MOTOR_TIMEOUT_S * 1000,
                    )
                )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return results


def _run_motors_sequential(
    motors: list[tuple[str, Any]],
    context: dict[str, Any],
) -> list[MotorResult]:
    """Sequential fallback when executor fails.

    Args:
        motors: List of (motor_name, motor_hook) tuples.
        context: Hook input context.

    Returns:
        List of MotorResult objects.
    """
    return [_run_single_motor(name, hook, context) for name, hook in motors]


def run_motors(context: dict[str, Any]) -> SIACResult:
    """Orchestrate all SIAC motors and return combined result.

    Unavailable motors (hook is None) are recorded as ALLOW/unavailable.
    Available motors run concurrently; falls back to sequential if executor fails.

    Args:
        context: Hook input dict, expected to contain at least "file_path".

    Returns:
        SIACResult with per-motor results and overall action.
    """
    file_path: str = context.get("file_path", "unknown")
    motor_results: list[MotorResult] = []
    available_motors: list[tuple[str, Any]] = []

    for motor_name, motor_hook in MOTORS:
        if motor_hook is None:
            motor_results.append(
                MotorResult(
                    motor_name=motor_name,
                    action=ALLOW,
                    details={"status": "unavailable"},
                    execution_time_ms=0.0,
                )
            )
        else:
            available_motors.append((motor_name, motor_hook))

    try:
        concurrent_results = _run_motors_concurrent(available_motors, context)
        motor_results.extend(concurrent_results)
    except Exception:
        logger.warning("executor_failed fallback=sequential")
        sequential_results = _run_motors_sequential(available_motors, context)
        motor_results.extend(sequential_results)

    return SIACResult(
        file_path=file_path,
        motor_results=motor_results,
        overall_action=_determine_overall_action(motor_results),
        timestamp=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Hook entry point
# ---------------------------------------------------------------------------


def hook_post_tool_use(context: dict[str, Any]) -> dict[str, Any]:
    """PostToolUse hook orchestrating all SIAC motors.

    Input context keys:
        tool_name (str): "Write" | "Edit" | etc.
        file_path (str): Path of the file being modified.
        tool_input (dict): Raw tool input.

    Returns:
        Dict with "action" (int) and "siac_orchestrator" metadata.
    """
    result = run_motors(context)
    return {
        "action": result.overall_action,
        "siac_orchestrator": {
            "timestamp": result.timestamp,
            "file_path": result.file_path,
            "motor_results": [r.to_dict() for r in result.motor_results],
            "summary": result.to_dict()["summary"],
        },
    }


def main() -> None:
    """Standalone CLI entry point for the SIAC orchestrator hook."""
    try:
        try:
            data = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError, ValueError):
            sys.exit(ALLOW)

        result = run_motors(data)
        if result.overall_action == BLOCK:
            summary = result.to_dict()
            print(json.dumps(summary, indent=2), file=sys.stderr)
            sys.exit(BLOCK)
        if result.overall_action == WARN:
            summary = result.to_dict()
            print(json.dumps(summary, indent=2), file=sys.stderr)
            sys.exit(WARN)

        sys.exit(ALLOW)
    except Exception as exc:
        logger.error("siac_orchestrator unhandled exception: %s", exc)
        sys.exit(ALLOW)  # Fail-open


if __name__ == "__main__":
    main()
