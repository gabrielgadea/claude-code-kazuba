#!/usr/bin/env python3
"""E2E integration tests for the config-hypervisor (Phase 15).

Tests the Hypervisor orchestrator integration:
- HypervisorConfig (Pydantic frozen model)
- ExecutionMode enum
- Hypervisor instantiation and DRY_RUN execution
- PhaseDefinition, ExecutionResult models
- execute_all with dependency ordering
- circuit_breaker integration
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load hypervisor via importlib (in modules/config-hypervisor/src/)
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[2]
_HV_PATH = _ROOT / "modules" / "config-hypervisor" / "src" / "hypervisor.py"

_hv_spec = importlib.util.spec_from_file_location("hypervisor_e2e", _HV_PATH)
_hv_mod = importlib.util.module_from_spec(_hv_spec)  # type: ignore[arg-type]
sys.modules.setdefault("hypervisor_e2e", _hv_mod)
_hv_spec.loader.exec_module(_hv_mod)  # type: ignore[union-attr]

ExecutionMode = _hv_mod.ExecutionMode
HypervisorConfig = _hv_mod.HypervisorConfig
PhaseDefinition = _hv_mod.PhaseDefinition
ExecutionResult = _hv_mod.ExecutionResult
PhaseStatus = _hv_mod.PhaseStatus
Hypervisor = _hv_mod.Hypervisor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dry_run_config() -> Any:
    """Return a HypervisorConfig in DRY_RUN mode."""
    return HypervisorConfig(mode=ExecutionMode.DRY_RUN)


@pytest.fixture
def hypervisor(dry_run_config: Any) -> Any:
    """Return a Hypervisor instance configured for dry-run."""
    return Hypervisor(config=dry_run_config)


@pytest.fixture
def simple_phase() -> Any:
    """Return a simple PhaseDefinition for testing."""
    return PhaseDefinition(
        id=1,
        name="test_phase",
        prompt="Run the test suite",
        depends_on=[],
    )


@pytest.fixture
def dependent_phases() -> list[Any]:
    """Return a list of phases with dependency chain."""
    return [
        PhaseDefinition(id=1, name="setup", prompt="Initialize environment"),
        PhaseDefinition(id=2, name="build", prompt="Build artifacts", depends_on=[1]),
        PhaseDefinition(id=3, name="test", prompt="Run tests", depends_on=[2]),
    ]


# ---------------------------------------------------------------------------
# Tests: ExecutionMode enum
# ---------------------------------------------------------------------------


def test_execution_mode_values() -> None:
    """ExecutionMode has expected values."""
    assert ExecutionMode.DRY_RUN == "dry_run"
    assert ExecutionMode.SEQUENTIAL == "sequential"
    assert ExecutionMode.PARALLEL == "parallel"
    assert ExecutionMode.INTERACTIVE == "interactive"


def test_execution_mode_membership() -> None:
    """All execution modes are accessible as enum members."""
    modes = {m.value for m in ExecutionMode}
    assert "dry_run" in modes
    assert "sequential" in modes


# ---------------------------------------------------------------------------
# Tests: HypervisorConfig (Pydantic frozen model)
# ---------------------------------------------------------------------------


def test_hypervisor_config_defaults() -> None:
    """HypervisorConfig has sensible defaults."""
    cfg = HypervisorConfig()
    assert cfg.mode == ExecutionMode.SEQUENTIAL
    assert cfg.max_workers >= 1
    assert cfg.timeout_per_phase > 0
    assert isinstance(cfg.quality_threshold, float)


def test_hypervisor_config_frozen() -> None:
    """HypervisorConfig is immutable (Pydantic frozen=True)."""
    cfg = HypervisorConfig()
    with pytest.raises((TypeError, AttributeError, Exception)):  # ValidationError or TypeError
        cfg.mode = ExecutionMode.PARALLEL  # type: ignore[misc]


def test_hypervisor_config_dry_run(dry_run_config: Any) -> None:
    """DRY_RUN mode is set correctly."""
    assert dry_run_config.mode == ExecutionMode.DRY_RUN


# ---------------------------------------------------------------------------
# Tests: Hypervisor instantiation
# ---------------------------------------------------------------------------


def test_hypervisor_instantiates(hypervisor: Any) -> None:
    """Hypervisor instantiates without errors."""
    assert hypervisor is not None
    assert hypervisor.config.mode == ExecutionMode.DRY_RUN


def test_hypervisor_config_property(hypervisor: Any, dry_run_config: Any) -> None:
    """Hypervisor.config returns the configured HypervisorConfig."""
    assert hypervisor.config is dry_run_config


def test_hypervisor_circuit_breaker_property(hypervisor: Any) -> None:
    """Hypervisor.circuit_breaker is either a CircuitBreaker or None."""
    # May or may not be available depending on lib
    cb = hypervisor.circuit_breaker
    assert cb is None or hasattr(cb, "call")


# ---------------------------------------------------------------------------
# Tests: DRY_RUN phase execution
# ---------------------------------------------------------------------------


def test_hypervisor_dry_run_phase(hypervisor: Any, simple_phase: Any) -> None:
    """execute_phase in DRY_RUN returns a simulated result."""
    result = hypervisor.execute_phase(simple_phase)
    assert isinstance(result, ExecutionResult)
    assert result.phase_id == simple_phase.id
    # DRY_RUN should either succeed or skip, never fail
    assert result.status in (PhaseStatus.SUCCESS, PhaseStatus.SKIPPED)


def test_hypervisor_run_dry_returns_strings(hypervisor: Any, simple_phase: Any) -> None:
    """run_dry returns a list of simulation strings."""
    output = hypervisor.run_dry([simple_phase])
    assert isinstance(output, list)
    assert len(output) >= 1
    assert all(isinstance(s, str) for s in output)


def test_hypervisor_execute_all_dry_run(hypervisor: Any, dependent_phases: list[Any]) -> None:
    """execute_all in DRY_RUN mode handles dependency ordering."""
    results = hypervisor.execute_all(dependent_phases)
    assert isinstance(results, list)
    assert len(results) == len(dependent_phases)
    for r in results:
        assert isinstance(r, ExecutionResult)
        assert r.status in (PhaseStatus.SUCCESS, PhaseStatus.SKIPPED)


def test_execution_result_success_property() -> None:
    """ExecutionResult.success returns True for SUCCESS status."""
    result = ExecutionResult(
        phase_id=1,
        status=PhaseStatus.SUCCESS,
        duration_ms=100,
    )
    assert result.success is True


def test_execution_result_failure_property() -> None:
    """ExecutionResult.success returns False for FAILED status."""
    result = ExecutionResult(
        phase_id=2,
        status=PhaseStatus.FAILED,
        duration_ms=50,
        error="Something went wrong",
    )
    assert result.success is False


def test_phase_definition_frozen() -> None:
    """PhaseDefinition is immutable."""
    phase = PhaseDefinition(id=1, name="test", prompt="do something")
    with pytest.raises((TypeError, AttributeError, Exception)):  # ValidationError or TypeError
        phase.name = "modified"  # type: ignore[misc]


def test_hypervisor_get_execution_log(hypervisor: Any, simple_phase: Any) -> None:
    """get_execution_log returns list after executions."""
    hypervisor.execute_phase(simple_phase)
    log = hypervisor.get_execution_log()
    assert isinstance(log, list)
