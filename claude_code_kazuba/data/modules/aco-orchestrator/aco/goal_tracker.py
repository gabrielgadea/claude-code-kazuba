"""GoalTracker — N2 convergence monitoring with 9x9 = 81 quality checks.

Monitors drift from ObjectiveSpec across 9 Pln2 dimensions,
each with 9 sub-dimensions for fine-grained measurement.
Can trigger HALT and GoalKeeper veto via exit codes.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from .models import (
    DimensionScore,
    DriftLevel,
    GoalTrackerState,
    ObjectiveSpec,
    ValidationResult,
    ValidationStatus,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# 9 dimensions x 9 sub-dimensions = 81 checks
DIMENSIONS: dict[str, list[str]] = {
    "precision": [
        "zero_hallucination",
        "source_traceability",
        "edge_cases_covered",
        "type_safety",
        "contract_adherence",
        "citation_validation",
        "data_provenance",
        "confidence_tagged",
        "deterministic_output",
    ],
    "scalability": [
        "horizontal_scale",
        "vertical_scale",
        "load_tested",
        "stateless_design",
        "async_ready",
        "partitionable",
        "cache_friendly",
        "db_indexed",
        "bounded_complexity",
    ],
    "performance": [
        "profiled",
        "benchmarked",
        "baseline_established",
        "p95_within_target",
        "memory_bounded",
        "no_n_plus_1",
        "early_exit",
        "lazy_evaluation",
        "batching_capable",
    ],
    "applicability": [
        "generalized",
        "domain_agnostic",
        "api_documented",
        "variant_tested",
        "edge_input_handled",
        "composable",
        "exportable",
        "versioned",
        "backward_compatible",
    ],
    "code_quality": [
        "ruff_zero",
        "pyright_strict",
        "coverage_90",
        "complexity_le10",
        "solid_applied",
        "dry_applied",
        "no_magic_numbers",
        "google_docstrings",
        "typed_signatures",
    ],
    "specification": [
        "preconditions_defined",
        "postconditions_defined",
        "invariants_defined",
        "contract_tested",
        "formal_schema",
        "acceptance_criteria",
        "boundary_conditions",
        "error_contracts",
        "rollback_defined",
    ],
    "systemic_integration": [
        "imports_valid",
        "no_circular_deps",
        "hooks_registered",
        "backward_compat",
        "integration_tested",
        "dependency_graph",
        "no_file_conflicts",
        "discovery_indexed",
        "co_evolution_done",
    ],
    "dependencies": [
        "latest_stable",
        "security_audited",
        "lock_file_updated",
        "no_yanked_versions",
        "minimal_deps",
        "dev_prod_separated",
        "transitive_checked",
        "license_compatible",
        "pinned_versions",
    ],
    "potentiation": [
        "future_enabled",
        "tech_debt_reduced",
        "template_library_updated",
        "patterns_persisted",
        "anti_patterns_documented",
        "evolution_package",
        "knowledge_indexed",
        "reusable_generators",
        "meta_level_improved",
    ],
}

# Drift thresholds — score below threshold triggers that level
DRIFT_THRESHOLDS: dict[DriftLevel, float] = {
    DriftLevel.OK: 0.8,
    DriftLevel.WARNING: 0.6,
    DriftLevel.CRITICAL: 0.4,
}

# Dimensions with elevated weight (1.5x) in composite scoring
CRITICAL_DIMS: frozenset[str] = frozenset({"precision", "code_quality", "specification"})

# Type alias for check functions: () -> float (0.0 to 1.0)
CheckFunction = Callable[[], float]


def _classify_drift(score: float, threshold: float) -> DriftLevel:
    """Classify drift level based on score relative to threshold.

    Args:
        score: Current score (0.0 to 1.0).
        threshold: Target threshold for OK status.

    Returns:
        DriftLevel classification.
    """
    if score >= threshold:
        return DriftLevel.OK
    ratio = score / threshold if threshold > 0 else 0.0
    if ratio >= 0.75:
        return DriftLevel.WARNING
    if ratio >= 0.50:
        return DriftLevel.CRITICAL
    return DriftLevel.HALT


class GoalTracker:
    """Monitors convergence toward objective across 9 quality dimensions.

    Each dimension has 9 sub-dimensions for 81 total quality checks.
    Tracks drift from objective and can trigger HALT when invariant
    is violated or quality drops below critical threshold.
    """

    def __init__(
        self,
        objective: ObjectiveSpec,
        phase: str = "initial",
        iteration: int = 0,
    ) -> None:
        """Initialize GoalTracker with objective specification.

        Args:
            objective: The target objective specification.
            phase: Current orchestration phase name.
            iteration: Current refinement iteration (0-based).
        """
        self._objective = objective
        self._phase = phase
        self._iteration = iteration
        self._dimension_scores: dict[str, DimensionScore] = {}
        self._messages: list[str] = []

    @property
    def objective(self) -> ObjectiveSpec:
        """The target objective specification."""
        return self._objective

    @property
    def phase(self) -> str:
        """Current orchestration phase."""
        return self._phase

    @phase.setter
    def phase(self, value: str) -> None:
        self._phase = value

    @property
    def iteration(self) -> int:
        """Current refinement iteration."""
        return self._iteration

    def advance_iteration(self) -> None:
        """Increment the iteration counter."""
        self._iteration += 1

    def assess_dimension(
        self,
        dim_name: str,
        check_fn_map: dict[str, CheckFunction],
    ) -> DimensionScore:
        """Assess one dimension using provided check functions.

        Args:
            dim_name: Name of the dimension (must be in DIMENSIONS).
            check_fn_map: Map of sub-dimension name to check function.
                Each function returns 0.0-1.0. Missing checks score 0.0.

        Returns:
            DimensionScore with computed sub-scores and drift level.

        Raises:
            ValueError: If dim_name is not a valid dimension.
        """
        if dim_name not in DIMENSIONS:
            msg = f"Unknown dimension: {dim_name}. Valid: {list(DIMENSIONS)}"
            raise ValueError(msg)

        sub_dims = DIMENSIONS[dim_name]
        sub_scores: dict[str, float] = {}

        for sub_dim in sub_dims:
            check_fn = check_fn_map.get(sub_dim)
            if check_fn is not None:
                try:
                    raw = check_fn()
                    sub_scores[sub_dim] = max(0.0, min(1.0, raw))
                except Exception:
                    logger.exception("Check %s.%s failed", dim_name, sub_dim)
                    sub_scores[sub_dim] = 0.0
                    self._messages.append(f"EXCEPTION in {dim_name}.{sub_dim}")
            else:
                sub_scores[sub_dim] = 0.0

        # Aggregate: simple mean of sub-scores
        total = sum(sub_scores.values())
        count = len(sub_scores)
        avg_score = total / count if count > 0 else 0.0

        threshold = DRIFT_THRESHOLDS[DriftLevel.OK]
        drift = _classify_drift(avg_score, threshold)

        dim_score = DimensionScore(
            name=dim_name,
            score=round(avg_score, 4),
            sub_scores={k: round(v, 4) for k, v in sub_scores.items()},
            threshold=threshold,
            drift_level=drift,
        )
        self._dimension_scores[dim_name] = dim_score
        return dim_score

    def compute_overall(self) -> GoalTrackerState:
        """Aggregate all assessed dimensions into overall state.

        Returns:
            GoalTrackerState snapshot with overall score and drift.
        """
        scores = tuple(self._dimension_scores.values())

        if not scores:
            return GoalTrackerState(
                objective_hash=self._compute_objective_hash(),
                phase=self._phase,
                dimension_scores=(),
                overall_score=0.0,
                drift_level=DriftLevel.HALT,
                messages=("No dimensions assessed",),
                iteration=self._iteration,
            )

        # Weighted aggregation: critical dimensions get 1.5x weight
        weighted_sum = 0.0
        weight_total = 0.0

        for ds in scores:
            weight = 1.5 if ds.name in CRITICAL_DIMS else 1.0
            weighted_sum += ds.score * weight
            weight_total += weight

        overall = weighted_sum / weight_total if weight_total > 0 else 0.0
        overall = round(overall, 4)

        drift = self._detect_drift_from_scores(scores, overall)

        return GoalTrackerState(
            objective_hash=self._compute_objective_hash(),
            phase=self._phase,
            dimension_scores=scores,
            overall_score=overall,
            drift_level=drift,
            messages=tuple(self._messages),
            iteration=self._iteration,
        )

    def detect_drift(self) -> DriftLevel:
        """Compute current drift level from assessed dimensions.

        Returns:
            Current DriftLevel based on dimension scores.
        """
        state = self.compute_overall()
        return state.drift_level

    def should_halt(self) -> bool:
        """Determine if orchestration should halt.

        Returns True if:
        - DriftLevel is HALT
        - Any critical dimension is in HALT state
        - Overall score is below 0.3

        Returns:
            True if HALT condition is met.
        """
        state = self.compute_overall()

        if state.drift_level == DriftLevel.HALT:
            return True

        # Check critical dimensions individually
        for ds in state.dimension_scores:
            if ds.name in CRITICAL_DIMS and ds.drift_level == DriftLevel.HALT:
                self._messages.append(f"HALT: critical dimension {ds.name} in HALT state (score={ds.score})")
                return True

        if state.overall_score < 0.3:
            self._messages.append(f"HALT: overall score {state.overall_score} < 0.3")
            return True

        return False

    def add_message(self, message: str) -> None:
        """Add a tracking message to the state.

        Args:
            message: Message to record.
        """
        self._messages.append(message)

    def get_failing_dimensions(self) -> list[DimensionScore]:
        """Get dimensions that are below their threshold.

        Returns:
            List of DimensionScores with drift_level != OK.
        """
        return [ds for ds in self._dimension_scores.values() if ds.drift_level != DriftLevel.OK]

    def get_failing_checks(self) -> list[tuple[str, str, float]]:
        """Get individual sub-dimension checks scoring below threshold.

        Returns:
            List of (dimension, sub_dimension, score) tuples.
        """
        failing: list[tuple[str, str, float]] = []
        threshold = DRIFT_THRESHOLDS[DriftLevel.OK]
        for dim_name, ds in self._dimension_scores.items():
            for sub_name, sub_score in ds.sub_scores.items():
                if sub_score < threshold:
                    failing.append((dim_name, sub_name, sub_score))
        return failing

    def validate_results(self) -> list[ValidationResult]:
        """Generate ValidationResult for each assessed dimension.

        Returns:
            List of ValidationResult objects for reporting.
        """
        results: list[ValidationResult] = []
        for ds in self._dimension_scores.values():
            if ds.drift_level == DriftLevel.OK:
                status = ValidationStatus.PASS
            elif ds.drift_level == DriftLevel.WARNING:
                status = ValidationStatus.WARN
            else:
                status = ValidationStatus.FAIL

            results.append(
                ValidationResult(
                    phase=self._phase,
                    check_name=f"dimension_{ds.name}",
                    status=status,
                    expected=ds.threshold,
                    actual=ds.score,
                    message=(f"{ds.name}: score={ds.score:.4f}, drift={ds.drift_level.value}"),
                    remediation=(
                        f"Improve sub-dimensions: {[k for k, v in ds.sub_scores.items() if v < ds.threshold]}"
                        if status != ValidationStatus.PASS
                        else None
                    ),
                )
            )
        return results

    def to_json(self) -> str:
        """Serialize current state to JSON string.

        Returns:
            JSON string of the GoalTrackerState.
        """
        state = self.compute_overall()
        return state.model_dump_json(indent=2)

    def save(self, path: Path) -> None:
        """Save current state to a JSON file.

        Args:
            path: File path for the checkpoint.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        logger.info("GoalTracker state saved to %s", path)

    @staticmethod
    def from_file(path: Path) -> GoalTrackerState:
        """Load a GoalTrackerState from a JSON checkpoint file.

        Args:
            path: Path to the JSON checkpoint.

        Returns:
            Deserialized GoalTrackerState.

        Raises:
            FileNotFoundError: If path does not exist.
            ValueError: If JSON is invalid or schema mismatch.
        """
        if not path.exists():
            msg = f"Checkpoint not found: {path}"
            raise FileNotFoundError(msg)

        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return GoalTrackerState.model_validate(data)

    def _compute_objective_hash(self) -> str:
        """Compute a stable hash from the objective statement.

        Returns:
            First 16 chars of SHA256 hex digest.
        """
        import hashlib

        content = self._objective.statement + self._objective.invariant
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _detect_drift_from_scores(
        self,
        scores: tuple[DimensionScore, ...],
        overall: float,
    ) -> DriftLevel:
        """Determine drift level from dimension scores and overall.

        Args:
            scores: Tuple of dimension scores.
            overall: Computed overall score.

        Returns:
            Worst-case DriftLevel across all dimensions.
        """
        drift_severity = {
            DriftLevel.OK: 0,
            DriftLevel.WARNING: 1,
            DriftLevel.CRITICAL: 2,
            DriftLevel.HALT: 3,
        }
        overall_drift = _classify_drift(overall, DRIFT_THRESHOLDS[DriftLevel.OK])
        all_drifts = [overall_drift, *(ds.drift_level for ds in scores)]
        return max(all_drifts, key=lambda d: drift_severity[d])
