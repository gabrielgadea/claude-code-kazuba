"""
Hypervisor - Orchestrator for multi-phase plan execution.

Coordinates phase execution, manages state with checkpointing,
integrates with the hook circuit breaker infrastructure, and
implements the Airlock pattern to avoid context accumulation
between sessions.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================


class ExecutionMode(str, Enum):
    """Execution modes for the Hypervisor."""

    SEQUENTIAL = "sequential"    # Execute phases in dependency order
    PARALLEL = "parallel"        # Execute independent phases in parallel
    INTERACTIVE = "interactive"  # Wait for confirmation between phases
    DRY_RUN = "dry_run"          # Simulate execution without running phases


class PhaseStatus(str, Enum):
    """Status of a phase execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================================
# Models (Pydantic v2, frozen=True for immutability)
# ============================================================================


class HypervisorConfig(BaseModel, frozen=True):
    """Immutable configuration for the Hypervisor.

    Attributes:
        phases: Optional list of phase IDs to include in execution.
        mode: Execution mode (sequential, parallel, interactive, dry_run).
        max_workers: Maximum parallel workers when mode is parallel.
        timeout_per_phase: Seconds before a phase execution times out.
        checkpoint_dir: Directory where phase checkpoints are written.
        max_retries: Maximum retries per phase on failure.
        quality_threshold: Minimum quality score to consider a phase passing.
    """

    phases: list[str] = Field(default_factory=list)
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_workers: int = 4
    timeout_per_phase: int = 600
    checkpoint_dir: Path = Path(".claude/checkpoints")
    max_retries: int = 3
    quality_threshold: float = 70.0

    model_config = {"arbitrary_types_allowed": True}


class PhaseDefinition(BaseModel, frozen=True):
    """Immutable definition of a phase to be executed.

    Attributes:
        id: Unique numeric identifier for the phase.
        name: Human-readable phase name.
        depends_on: List of phase IDs that must complete first.
        parallel_group: Optional tag for grouping parallel-eligible phases.
        validation_script: Optional path to a validation script to run post-phase.
        prompt: Optional prompt to pass to claude CLI.
        max_turns: Maximum turns allowed for this phase.
        can_skip: If True, phase may be skipped when dependencies fail.
    """

    id: int
    name: str
    depends_on: list[int] = Field(default_factory=list)
    parallel_group: str | None = None
    validation_script: str | None = None
    prompt: str = ""
    max_turns: int = 50
    can_skip: bool = False


class ExecutionResult(BaseModel, frozen=True):
    """Immutable result of a phase or plan execution.

    Attributes:
        phase_id: Numeric phase identifier.
        status: Final status of the phase (success, failed, skipped, etc.).
        duration_ms: Wall-clock duration of the execution in milliseconds.
        checkpoint_path: Path where checkpoint was written, if any.
        error: Error message if execution failed.
        stdout: Captured standard output from the execution.
        stderr: Captured standard error from the execution.
        quality_score: Quality score returned by validation, if applicable.
    """

    phase_id: int
    status: PhaseStatus = PhaseStatus.PENDING
    duration_ms: int = 0
    checkpoint_path: Path | None = None
    error: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    quality_score: float = 0.0

    model_config = {"arbitrary_types_allowed": True}

    @property
    def success(self) -> bool:
        """Return True if status is SUCCESS or PARTIAL."""
        return self.status in (PhaseStatus.SUCCESS, PhaseStatus.PARTIAL)


# ============================================================================
# Hypervisor
# ============================================================================


class Hypervisor:
    """Orchestrator for multi-phase plan execution.

    Coordinates the execution of multiple PhaseDefinitions according to the
    configured ExecutionMode. Supports dry-run, checkpointing, circuit
    breaker integration, and topological dependency ordering.

    Example:
        config = HypervisorConfig(mode=ExecutionMode.DRY_RUN)
        hypervisor = Hypervisor(config)
        phases = [
            PhaseDefinition(id=1, name="setup"),
            PhaseDefinition(id=2, name="build", depends_on=[1]),
        ]
        results = hypervisor.execute_all(phases)
    """

    def __init__(self, config: HypervisorConfig | None = None) -> None:
        """Initialize the Hypervisor with optional configuration.

        Args:
            config: HypervisorConfig instance. Uses defaults if None.
        """
        self._config = config or HypervisorConfig()
        self._circuit_breaker: Any = None
        self._completed_phases: set[int] = set()
        self._execution_log: list[dict[str, Any]] = []

        # Lazily import circuit breaker from lib
        try:
            from lib.circuit_breaker import CircuitBreaker  # type: ignore[import]
            self._circuit_breaker = CircuitBreaker("hypervisor")
        except ImportError:
            logger.debug("CircuitBreaker not available; proceeding without it")

    @property
    def config(self) -> HypervisorConfig:
        """Return the current hypervisor configuration."""
        return self._config

    @property
    def circuit_breaker(self) -> Any:
        """Return circuit breaker instance, or None if unavailable."""
        return self._circuit_breaker

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def execute_phase(self, phase: PhaseDefinition) -> ExecutionResult:
        """Execute a single phase and return its result.

        In DRY_RUN mode, the phase is simulated without any real execution.
        Otherwise, the phase prompt is sent to the Claude CLI subprocess.

        Args:
            phase: PhaseDefinition describing what to execute.

        Returns:
            ExecutionResult with status, duration, and checkpoint path.
        """
        start = datetime.now()

        if self._config.mode == ExecutionMode.DRY_RUN:
            return self._dry_run_phase(phase, start)

        try:
            cli_result = self._run_cli(phase)
        except subprocess.TimeoutExpired:
            duration_ms = self._elapsed_ms(start)
            error = f"Timeout after {self._config.timeout_per_phase}s"
            logger.warning("Phase %d timed out: %s", phase.id, error)
            return ExecutionResult(
                phase_id=phase.id,
                status=PhaseStatus.FAILED,
                duration_ms=duration_ms,
                error=error,
            )
        except Exception as exc:
            duration_ms = self._elapsed_ms(start)
            error = str(exc)
            logger.error("Phase %d error: %s", phase.id, error)
            return ExecutionResult(
                phase_id=phase.id,
                status=PhaseStatus.FAILED,
                duration_ms=duration_ms,
                error=error,
            )

        duration_ms = self._elapsed_ms(start)
        status = PhaseStatus.SUCCESS if cli_result["exit_code"] == 0 else PhaseStatus.FAILED
        cp = self._save_checkpoint(phase, cli_result, duration_ms)

        self._log_result(phase.id, status, duration_ms)
        self._completed_phases.add(phase.id)

        return ExecutionResult(
            phase_id=phase.id,
            status=status,
            duration_ms=duration_ms,
            checkpoint_path=cp,
            stdout=cli_result.get("stdout"),
            stderr=cli_result.get("stderr"),
        )

    def execute_all(self, phases: list[PhaseDefinition]) -> list[ExecutionResult]:
        """Execute all phases, respecting dependency order.

        Phases are topologically sorted by their `depends_on` lists before
        execution. If a phase fails and its dependents cannot be skipped,
        execution stops.

        Args:
            phases: List of PhaseDefinitions to execute.

        Returns:
            List of ExecutionResults in execution order.
        """
        ordered = self._topological_sort(phases)
        results: list[ExecutionResult] = []

        for phase in ordered:
            if not self._deps_satisfied(phase):
                if phase.can_skip:
                    logger.warning("Skipping phase %d — deps not met", phase.id)
                    results.append(
                        ExecutionResult(
                            phase_id=phase.id,
                            status=PhaseStatus.SKIPPED,
                        )
                    )
                    continue
                # Fail fast
                results.append(
                    ExecutionResult(
                        phase_id=phase.id,
                        status=PhaseStatus.FAILED,
                        error="Dependencies not satisfied",
                    )
                )
                break

            result = self.execute_phase(phase)
            results.append(result)

            if not result.success:
                logger.error("Phase %d failed — stopping execution", phase.id)
                break

        return results

    def run_dry(self, phases: list[PhaseDefinition]) -> list[str]:
        """List phase names without executing them.

        Performs topological sorting and returns the names in execution order,
        useful for previewing what would be executed.

        Args:
            phases: List of PhaseDefinitions to preview.

        Returns:
            Ordered list of phase names.
        """
        ordered = self._topological_sort(phases)
        return [p.name for p in ordered]

    def load_checkpoint(self, phase_id: int) -> dict[str, Any]:
        """Load checkpoint data for a completed phase.

        Args:
            phase_id: Numeric phase identifier.

        Returns:
            Dictionary with checkpoint data, or empty dict if not found.
        """
        cp_dir = self._config.checkpoint_dir
        cp_file = cp_dir / f"phase_{phase_id}.json"

        if not cp_file.exists():
            logger.debug("No checkpoint found for phase %d", phase_id)
            return {}

        try:
            return json.loads(cp_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load checkpoint %s: %s", cp_file, exc)
            return {}

    def get_execution_log(self) -> list[dict[str, Any]]:
        """Return a copy of the execution log."""
        return list(self._execution_log)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _dry_run_phase(
        self, phase: PhaseDefinition, start: datetime
    ) -> ExecutionResult:
        """Simulate phase execution without running any subprocess."""
        logger.info("[DRY_RUN] Phase %d: %s", phase.id, phase.name)
        duration_ms = self._elapsed_ms(start)
        self._completed_phases.add(phase.id)
        self._log_result(phase.id, PhaseStatus.SUCCESS, duration_ms)
        return ExecutionResult(
            phase_id=phase.id,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
        )

    def _run_cli(self, phase: PhaseDefinition) -> dict[str, Any]:
        """Run claude CLI for a phase and capture output."""
        cmd = [
            "claude",
            "-p",
            phase.prompt or f"Execute phase {phase.id}: {phase.name}",
            "--output-format", "json",
            "--max-turns", str(phase.max_turns),
        ]
        logger.debug("Running CLI for phase %d", phase.id)
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=self._config.timeout_per_phase,
            check=False,
        )
        return {
            "stdout": proc.stdout.decode("utf-8", errors="replace"),
            "stderr": proc.stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode,
        }

    def _save_checkpoint(
        self,
        phase: PhaseDefinition,
        cli_result: dict[str, Any],
        duration_ms: int,
    ) -> Path | None:
        """Save a JSON checkpoint for the phase."""
        cp_dir = self._config.checkpoint_dir
        try:
            cp_dir.mkdir(parents=True, exist_ok=True)
            cp_file = cp_dir / f"phase_{phase.id}.json"
            data = {
                "phase_id": phase.id,
                "phase_name": phase.name,
                "duration_ms": duration_ms,
                "exit_code": cli_result.get("exit_code"),
                "timestamp": datetime.now().isoformat(),
            }
            cp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return cp_file
        except OSError as exc:
            logger.warning("Failed to write checkpoint: %s", exc)
            return None

    def _topological_sort(
        self, phases: list[PhaseDefinition]
    ) -> list[PhaseDefinition]:
        """Return phases sorted by dependency order (topological sort).

        Args:
            phases: Unsorted list of PhaseDefinitions.

        Returns:
            Sorted list where each phase appears after its dependencies.

        Raises:
            ValueError: If a dependency cycle is detected.
        """
        id_map = {p.id: p for p in phases}
        sorted_phases: list[PhaseDefinition] = []
        remaining = list(phases)
        completed: set[int] = set(self._completed_phases)

        max_iterations = len(phases) * 2 + 1
        iterations = 0

        while remaining and iterations < max_iterations:
            iterations += 1
            progress = False
            for phase in list(remaining):
                if all(dep in completed for dep in phase.depends_on):
                    sorted_phases.append(phase)
                    completed.add(phase.id)
                    remaining.remove(phase)
                    progress = True

            if not progress and remaining:
                unresolved = [p.id for p in remaining]
                raise ValueError(
                    f"Dependency cycle or missing dependency for phases: {unresolved}"
                )

        return sorted_phases

    def _deps_satisfied(self, phase: PhaseDefinition) -> bool:
        """Check if all dependencies for a phase are in completed set."""
        return all(dep in self._completed_phases for dep in phase.depends_on)

    @staticmethod
    def _elapsed_ms(start: datetime) -> int:
        """Return elapsed milliseconds since start."""
        return int((datetime.now() - start).total_seconds() * 1000)

    def _log_result(
        self, phase_id: int, status: PhaseStatus, duration_ms: int
    ) -> None:
        """Append an entry to the execution log."""
        self._execution_log.append(
            {
                "phase_id": phase_id,
                "status": status.value,
                "duration_ms": duration_ms,
            }
        )
