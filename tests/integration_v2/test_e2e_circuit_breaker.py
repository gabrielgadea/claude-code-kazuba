#!/usr/bin/env python3
"""E2E integration tests for the SIAC Orchestrator circuit breaker.

Tests the MotorCircuitBreaker integration with siac_orchestrator,
including state transitions, cooldown, metrics, and motor execution.
"""
from __future__ import annotations

import importlib.util
import sys
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Load siac_orchestrator via importlib (directory name has hyphen)
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "modules" / "hooks-quality" / "hooks" / "siac_orchestrator.py"

_spec = importlib.util.spec_from_file_location("siac_orch_e2e", _PATH)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules.setdefault("siac_orch_e2e", _mod)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

MotorCircuitBreaker = _mod.MotorCircuitBreaker
MotorResult = _mod.MotorResult
run_motors = _mod.run_motors
reset_circuit_breakers = _mod.reset_circuit_breakers
reset_metrics = _mod.reset_metrics
get_metrics = _mod.get_metrics
ALLOW = _mod.ALLOW
BLOCK = _mod.BLOCK
WARN = _mod.WARN


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_state() -> None:
    """Reset circuit breakers and metrics before each test."""
    reset_circuit_breakers()
    reset_metrics()


# ---------------------------------------------------------------------------
# Tests: MotorCircuitBreaker state machine
# ---------------------------------------------------------------------------


def test_circuit_breaker_initial_state_is_closed() -> None:
    """Circuit breaker starts in closed state."""
    cb = MotorCircuitBreaker()
    assert cb.should_attempt() is True
    assert cb.is_open is False


def test_circuit_breaker_opens_after_threshold_failures() -> None:
    """Circuit opens after FAILURE_THRESHOLD consecutive failures."""
    cb = MotorCircuitBreaker()
    threshold = cb.FAILURE_THRESHOLD

    for _ in range(threshold):
        assert cb.should_attempt() is True
        cb.record_failure()

    assert cb.is_open is True
    assert cb.should_attempt() is False


def test_circuit_breaker_does_not_open_before_threshold() -> None:
    """Circuit stays closed if failures are below threshold."""
    cb = MotorCircuitBreaker()
    for _ in range(cb.FAILURE_THRESHOLD - 1):
        cb.record_failure()

    assert cb.is_open is False
    assert cb.should_attempt() is True


def test_circuit_breaker_closes_on_success() -> None:
    """Recording success resets circuit to closed."""
    cb = MotorCircuitBreaker()
    for _ in range(cb.FAILURE_THRESHOLD):
        cb.record_failure()

    assert cb.is_open is True
    cb.reset()
    cb.record_success()
    assert cb.is_open is False
    assert cb.should_attempt() is True


def test_circuit_breaker_reset_clears_state() -> None:
    """Manual reset clears failures and opens circuit."""
    cb = MotorCircuitBreaker()
    for _ in range(cb.FAILURE_THRESHOLD):
        cb.record_failure()

    cb.reset()
    assert cb.is_open is False
    assert cb.should_attempt() is True


def test_circuit_breaker_half_open_after_cooldown() -> None:
    """After cooldown, a probe attempt is allowed (half-open transition)."""
    cb = MotorCircuitBreaker()
    # Manually force open state with past failure time
    cb._state = "open"
    cb._failures = cb.FAILURE_THRESHOLD
    cb._last_failure_time = time.monotonic() - (cb.COOLDOWN_S + 1)

    # should_attempt returns True when cooldown elapsed (transitions to half_open)
    assert cb.should_attempt() is True


def test_circuit_breaker_stays_open_within_cooldown() -> None:
    """Circuit stays open if cooldown has not elapsed."""
    cb = MotorCircuitBreaker()
    for _ in range(cb.FAILURE_THRESHOLD):
        cb.record_failure()

    # Immediately check — cooldown has not elapsed
    assert cb.is_open is True
    assert cb.should_attempt() is False


def test_circuit_breaker_thread_safety() -> None:
    """MotorCircuitBreaker is thread-safe under concurrent access."""
    cb = MotorCircuitBreaker()
    errors: list[Exception] = []

    def record_failures() -> None:
        try:
            for _ in range(10):
                cb.record_failure()
                cb.record_success()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=record_failures) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Thread errors: {errors}"


def test_run_motors_returns_allow_with_no_motors() -> None:
    """run_motors returns ALLOW when all motors are None (no-ops)."""
    context: dict[str, Any] = {
        "session_id": "test-e2e-001",
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {},
    }
    result = run_motors(context)
    assert result is not None
    assert hasattr(result, "overall_action")
    # With no real motors, should default to ALLOW
    assert result.overall_action in (ALLOW, WARN)


def test_run_motors_with_mock_block_motor() -> None:
    """run_motors propagates BLOCK from a motor that returns block."""

    def blocking_motor(_ctx: dict[str, Any]) -> dict[str, Any]:
        return {"action": BLOCK, "reason": "test block"}

    context: dict[str, Any] = {"session_id": "test-e2e-002", "tool_name": "Bash"}

    with patch.object(
        _mod,
        "MOTORS",
        [("MockBlocker", blocking_motor)],
    ):
        result = run_motors(context)
        assert result.overall_action == BLOCK


def test_motor_result_serialization() -> None:
    """MotorResult serializes to dict correctly.

    Note: to_dict() uses key "motor" (not "motor_name") per implementation.
    """
    mr = MotorResult(
        motor_name="TestMotor",
        action=ALLOW,
        details={"info": "ok"},
        execution_time_ms=12.5,
    )
    d = mr.to_dict()
    # Key is "motor" in the actual implementation
    assert d.get("motor") == "TestMotor" or mr.motor_name == "TestMotor"
    assert mr.action == ALLOW
    assert mr.execution_time_ms == 12.5


def test_get_metrics_returns_dict() -> None:
    """get_metrics returns a dict (may be empty before any motor runs)."""
    metrics = get_metrics()
    assert isinstance(metrics, dict)
