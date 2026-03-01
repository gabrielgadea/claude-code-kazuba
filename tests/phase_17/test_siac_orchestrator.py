"""Tests for siac_orchestrator — Phase 17."""

from __future__ import annotations

import importlib.util
import sys
import time
import types
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------


def _import_from_path(name: str, file_path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


_SIAC_PATH = PROJECT_ROOT / "claude_code_kazuba/data/modules" / "hooks-quality" / "hooks" / "siac_orchestrator.py"
_siac = _import_from_path("siac_orchestrator_ph17", _SIAC_PATH)

# Aliases for convenience
MotorResult = _siac.MotorResult
SIACResult = _siac.SIACResult
MotorCircuitBreaker = _siac.MotorCircuitBreaker
run_motors = _siac.run_motors
_determine_overall_action = _siac._determine_overall_action
_run_single_motor = _siac._run_single_motor
hook_post_tool_use = _siac.hook_post_tool_use
get_metrics = _siac.get_metrics
reset_metrics = _siac.reset_metrics
reset_circuit_breakers = _siac.reset_circuit_breakers
ALLOW = _siac.ALLOW
BLOCK = _siac.BLOCK
WARN = _siac.WARN


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_state() -> None:
    """Reset metrics and circuit breakers between tests."""
    reset_metrics()
    reset_circuit_breakers()


# ---------------------------------------------------------------------------
# MotorResult tests
# ---------------------------------------------------------------------------


class TestMotorResult:
    """Tests for MotorResult data model."""

    def test_to_dict_allow(self) -> None:
        """MotorResult with ALLOW action serializes correctly."""
        mr = MotorResult("M1", ALLOW, {"status": "ok"}, 10.5)
        d = mr.to_dict()
        assert d["motor"] == "M1"
        assert d["action"] == ALLOW
        assert d["action_name"] == "ALLOW"
        assert "10.5" in d["execution_time_ms"]

    def test_to_dict_block(self) -> None:
        """MotorResult with BLOCK action has correct action_name."""
        mr = MotorResult("M2", BLOCK, {"reason": "bad"}, 5.0)
        d = mr.to_dict()
        assert d["action_name"] == "BLOCK"

    def test_to_dict_warn(self) -> None:
        """MotorResult with WARN action has correct action_name."""
        mr = MotorResult("M3", WARN, {"msg": "warning"}, 3.0)
        d = mr.to_dict()
        assert d["action_name"] == "WARN"

    def test_frozen(self) -> None:
        """MotorResult is immutable (frozen=True)."""
        mr = MotorResult("M1", ALLOW, {}, 0.0)
        with pytest.raises((AttributeError, TypeError)):
            mr.action = BLOCK  # type: ignore[misc]

    def test_action_name_unknown(self) -> None:
        """MotorResult with unknown action code returns UNKNOWN string."""
        mr = MotorResult("M1", 99, {}, 0.0)
        assert "UNKNOWN" in mr.action_name()


# ---------------------------------------------------------------------------
# SIACResult tests
# ---------------------------------------------------------------------------


class TestSIACResult:
    """Tests for SIACResult aggregation."""

    def _make_result(self, actions: list[int]) -> SIACResult:
        motors = [MotorResult(f"M{i}", a, {}, 1.0) for i, a in enumerate(actions, 1)]
        overall = _determine_overall_action(motors)
        return SIACResult("test.py", motors, overall, "2025-01-01T00:00:00Z")

    def test_has_blocks_true(self) -> None:
        """SIACResult.has_blocks is True when any motor blocks."""
        r = self._make_result([ALLOW, BLOCK])
        assert r.has_blocks is True

    def test_has_blocks_false(self) -> None:
        """SIACResult.has_blocks is False with no blocking motors."""
        r = self._make_result([ALLOW, WARN])
        assert r.has_blocks is False

    def test_has_warnings_true(self) -> None:
        """SIACResult.has_warnings is True when any motor warns."""
        r = self._make_result([ALLOW, WARN])
        assert r.has_warnings is True

    def test_to_dict_summary_counts(self) -> None:
        """SIACResult.to_dict includes correct summary counts."""
        r = self._make_result([ALLOW, BLOCK, WARN])
        d = r.to_dict()
        assert d["summary"]["blocks"] == 1
        assert d["summary"]["warnings"] == 1
        assert d["summary"]["allows"] == 1
        assert d["summary"]["total_motors"] == 3


# ---------------------------------------------------------------------------
# MotorCircuitBreaker tests
# ---------------------------------------------------------------------------


class TestMotorCircuitBreaker:
    """Tests for per-motor circuit breaker state machine."""

    def test_initial_state_should_attempt(self) -> None:
        """New circuit breaker allows attempts."""
        cb = MotorCircuitBreaker()
        assert cb.should_attempt() is True

    def test_opens_after_threshold(self) -> None:
        """Circuit opens after FAILURE_THRESHOLD consecutive failures."""
        cb = MotorCircuitBreaker()
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure()
        assert cb.should_attempt() is False

    def test_resets_on_success(self) -> None:
        """Successful execution resets failure counter."""
        cb = MotorCircuitBreaker()
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.should_attempt() is True

    def test_half_open_after_cooldown(self) -> None:
        """Circuit transitions to half_open after cooldown elapses."""
        cb = MotorCircuitBreaker()
        cb.COOLDOWN_S = 0.01  # Very short for testing
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure()
        time.sleep(0.05)
        # After cooldown, should_attempt returns True (half-open)
        assert cb.should_attempt() is True

    def test_is_open_property(self) -> None:
        """is_open reflects circuit state without cooldown elapsed."""
        cb = MotorCircuitBreaker()
        assert cb.is_open is False
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure()
        assert cb.is_open is True


# ---------------------------------------------------------------------------
# _determine_overall_action tests
# ---------------------------------------------------------------------------


class TestDetermineOverallAction:
    """Tests for action aggregation logic."""

    def test_all_allow(self) -> None:
        """All ALLOW motors -> ALLOW."""
        motors = [MotorResult(f"M{i}", ALLOW, {}, 0.0) for i in range(3)]
        assert _determine_overall_action(motors) == ALLOW

    def test_one_block(self) -> None:
        """Any BLOCK motor -> BLOCK overall."""
        motors = [
            MotorResult("M1", ALLOW, {}, 0.0),
            MotorResult("M2", BLOCK, {}, 0.0),
        ]
        assert _determine_overall_action(motors) == BLOCK

    def test_block_over_warn(self) -> None:
        """BLOCK takes priority over WARN."""
        motors = [
            MotorResult("M1", WARN, {}, 0.0),
            MotorResult("M2", BLOCK, {}, 0.0),
        ]
        assert _determine_overall_action(motors) == BLOCK

    def test_warn_without_block(self) -> None:
        """WARN without BLOCK -> WARN overall."""
        motors = [
            MotorResult("M1", ALLOW, {}, 0.0),
            MotorResult("M2", WARN, {}, 0.0),
        ]
        assert _determine_overall_action(motors) == WARN

    def test_empty_list(self) -> None:
        """Empty motor list -> ALLOW."""
        assert _determine_overall_action([]) == ALLOW


# ---------------------------------------------------------------------------
# run_motors tests (with mock hooks)
# ---------------------------------------------------------------------------


def _make_hook(action: int, details: dict[str, Any] | None = None) -> Any:
    """Create a minimal motor hook returning the given action."""
    _details = details or {}

    def hook(ctx: dict[str, Any]) -> dict[str, Any]:
        return {"action": action, **_details}

    return hook


def _make_failing_hook() -> Any:
    """Create a motor hook that raises an exception."""

    def hook(ctx: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("motor_error")

    return hook


class TestRunMotors:
    """Integration tests for run_motors orchestration."""

    def test_all_none_motors_allow(self) -> None:
        """All unavailable motors -> ALLOW result."""
        # Temporarily set all MOTORS to None
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = [(f"M{i}", None) for i in range(4)]
        try:
            result = run_motors({"file_path": "/tmp/test.py"})
            assert result.overall_action == ALLOW
        finally:
            _siac.MOTORS[:] = original

    def test_single_allow_motor(self) -> None:
        """Single ALLOW motor -> ALLOW result."""
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = [("TestMotor", _make_hook(ALLOW))]
        try:
            result = run_motors({"file_path": "test.py"})
            assert result.overall_action == ALLOW
            assert len(result.motor_results) == 1
        finally:
            _siac.MOTORS[:] = original

    def test_single_block_motor(self) -> None:
        """Single BLOCK motor -> BLOCK result."""
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = [("Blocker", _make_hook(BLOCK))]
        try:
            result = run_motors({"file_path": "test.py"})
            assert result.overall_action == BLOCK
        finally:
            _siac.MOTORS[:] = original

    def test_failing_motor_becomes_warn(self) -> None:
        """Motor that throws exception is captured as WARN (not crash)."""
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = [("Failer", _make_failing_hook())]
        try:
            result = run_motors({"file_path": "test.py"})
            # A failing motor returns WARN with error in details
            assert any(r.action == WARN for r in result.motor_results)
        finally:
            _siac.MOTORS[:] = original

    def test_file_path_captured(self) -> None:
        """file_path is propagated to SIACResult."""
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = []
        try:
            result = run_motors({"file_path": "/src/app.py"})
            assert result.file_path == "/src/app.py"
        finally:
            _siac.MOTORS[:] = original

    def test_timestamp_present(self) -> None:
        """SIACResult timestamp is non-empty."""
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = []
        try:
            result = run_motors({})
            assert result.timestamp
        finally:
            _siac.MOTORS[:] = original


# ---------------------------------------------------------------------------
# hook_post_tool_use tests
# ---------------------------------------------------------------------------


class TestHookPostToolUse:
    """Tests for the PostToolUse hook entry function."""

    def test_returns_action_key(self) -> None:
        """hook_post_tool_use returns dict with 'action' key."""
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = []
        try:
            result = hook_post_tool_use({"file_path": "x.py"})
            assert "action" in result
        finally:
            _siac.MOTORS[:] = original

    def test_returns_siac_orchestrator_metadata(self) -> None:
        """hook_post_tool_use includes siac_orchestrator metadata."""
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = []
        try:
            result = hook_post_tool_use({"file_path": "x.py"})
            assert "siac_orchestrator" in result
            meta = result["siac_orchestrator"]
            assert "timestamp" in meta
            assert "file_path" in meta
            assert "summary" in meta
        finally:
            _siac.MOTORS[:] = original


# ---------------------------------------------------------------------------
# Metrics tests
# ---------------------------------------------------------------------------


class TestMetrics:
    """Tests for metrics collection."""

    def test_reset_metrics_clears_data(self) -> None:
        """reset_metrics clears accumulated metrics."""
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = [("M", _make_hook(ALLOW))]
        try:
            run_motors({})
            reset_metrics()
            assert get_metrics() == {}
        finally:
            _siac.MOTORS[:] = original

    def test_metrics_recorded_after_run(self) -> None:
        """Metrics are recorded after a successful motor run."""
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = [("MetricMotor", _make_hook(ALLOW))]
        try:
            run_motors({})
            metrics = get_metrics()
            assert "MetricMotor" in metrics
            assert metrics["MetricMotor"]["successes"] >= 1
        finally:
            _siac.MOTORS[:] = original


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerEdgeCases:
    """Additional circuit breaker edge-case coverage."""

    def test_is_open_when_open_and_within_cooldown(self) -> None:
        """is_open=True when circuit is open and cooldown has not elapsed."""
        cb = MotorCircuitBreaker()
        cb.COOLDOWN_S = 9999.0
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure()
        assert cb.is_open is True

    def test_is_open_false_when_closed(self) -> None:
        """is_open=False when circuit is closed."""
        cb = MotorCircuitBreaker()
        assert cb.is_open is False

    def test_half_open_reopens_on_failure(self) -> None:
        """Half-open circuit reopens on another failure."""
        cb = MotorCircuitBreaker()
        cb.COOLDOWN_S = 0.01
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure()
        time.sleep(0.05)
        cb.should_attempt()  # Triggers half_open transition
        cb.record_failure()  # Should reopen
        assert cb._state == "open"

    def test_should_attempt_returns_false_with_no_failure_time(self) -> None:
        """should_attempt returns False when open and no failure time recorded."""
        cb = MotorCircuitBreaker()
        cb._state = "open"
        cb._last_failure_time = None
        assert cb.should_attempt() is False

    def test_reset_clears_all_state(self) -> None:
        """reset() clears failures and restores closed state."""
        cb = MotorCircuitBreaker()
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure()
        cb.reset()
        assert cb._state == "closed"
        assert cb._failures == 0
        assert cb._last_failure_time is None


class TestMotorMetricsAdditional:
    """Tests for _MotorMetrics class."""

    def test_record_failure_increments(self) -> None:
        """record_failure increments failure count."""
        mm = _siac._MotorMetrics()
        mm.record_failure(10.0)
        d = mm.to_dict()
        assert d["failures"] == 1
        assert d["total_time_ms"] == 10.0

    def test_record_timeout_increments(self) -> None:
        """record_timeout increments timeout count."""
        mm = _siac._MotorMetrics()
        mm.record_timeout()
        d = mm.to_dict()
        assert d["timeouts"] == 1

    def test_record_success_increments(self) -> None:
        """record_success increments success count."""
        mm = _siac._MotorMetrics()
        mm.record_success(5.0)
        d = mm.to_dict()
        assert d["successes"] == 1


class TestSequentialFallback:
    """Tests for sequential motor fallback."""

    def test_sequential_run_returns_results(self) -> None:
        """_run_motors_sequential returns list of motor results."""
        motors = [("M1", _make_hook(ALLOW)), ("M2", _make_hook(WARN))]
        results = _siac._run_motors_sequential(motors, {"file_path": "x.py"})
        assert len(results) == 2
        assert results[0].action == ALLOW
        assert results[1].action == WARN

    def test_sequential_empty_motors(self) -> None:
        """_run_motors_sequential with no motors returns empty list."""
        results = _siac._run_motors_sequential([], {})
        assert results == []


class TestRunMotorsConcurrentCircuitOpen:
    """Test _run_motors_concurrent with circuit-open motor."""

    def test_circuit_open_motor_skipped(self) -> None:
        """Motor with open circuit is skipped (returns ALLOW/skipped)."""
        original = list(_siac.MOTORS)
        cb_motor_name = "CircuitOpenMotorX"
        cb = _siac._get_circuit_breaker(cb_motor_name)
        cb.COOLDOWN_S = 9999.0
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure()

        _siac.MOTORS[:] = [(cb_motor_name, _make_hook(BLOCK))]
        try:
            result = run_motors({"file_path": "test.py"})
            skipped = [
                r for r in result.motor_results if r.details.get("reason") == "circuit_open"
            ]
            assert len(skipped) >= 1
        finally:
            _siac.MOTORS[:] = original
            _siac.reset_circuit_breakers()


class TestRunMotorsSequentialFallback:
    """Test that sequential fallback path is exercised."""

    def test_sequential_fallback_on_exception(self) -> None:
        """When concurrent execution fails, sequential fallback is used."""
        original_concurrent = _siac._run_motors_concurrent

        def _raise(*args: Any, **kwargs: Any) -> list:  # type: ignore[return]
            raise RuntimeError("executor_failed")

        _siac._run_motors_concurrent = _raise  # type: ignore[assignment]
        original_motors = list(_siac.MOTORS)
        _siac.MOTORS[:] = [("FallbackMotor", _make_hook(ALLOW))]
        try:
            result = run_motors({"file_path": "fallback.py"})
            assert any(r.motor_name == "FallbackMotor" for r in result.motor_results)
        finally:
            _siac._run_motors_concurrent = original_concurrent  # type: ignore[assignment]
            _siac.MOTORS[:] = original_motors


class TestMainFunction:
    """Tests for the main() CLI entry point."""

    def test_main_invalid_json_exits_0(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() exits 0 on invalid JSON (fail-open)."""
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = []
        try:
            with pytest.raises(SystemExit) as exc_info:
                _siac.main()
            assert exc_info.value.code == 0
        finally:
            _siac.MOTORS[:] = original

    def test_main_allow_context_exits_0(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() exits 0 when all motors ALLOW."""
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO('{"file_path": "test.py"}'))
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = [("M", _make_hook(ALLOW))]
        try:
            with pytest.raises(SystemExit) as exc_info:
                _siac.main()
            assert exc_info.value.code == 0
        finally:
            _siac.MOTORS[:] = original

    def test_main_block_exits_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() exits 1 when a motor BLOCKs."""
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO('{"file_path": "test.py"}'))
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = [("B", _make_hook(BLOCK))]
        try:
            with pytest.raises(SystemExit) as exc_info:
                _siac.main()
            assert exc_info.value.code == BLOCK
        finally:
            _siac.MOTORS[:] = original

    def test_main_warn_exits_2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() exits 2 when a motor WARNs."""
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO('{"file_path": "test.py"}'))
        original = list(_siac.MOTORS)
        _siac.MOTORS[:] = [("W", _make_hook(WARN))]
        try:
            with pytest.raises(SystemExit) as exc_info:
                _siac.main()
            assert exc_info.value.code == WARN
        finally:
            _siac.MOTORS[:] = original
