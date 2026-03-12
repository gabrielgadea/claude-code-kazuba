"""AcoOrchestrator — Top-level coordinator for ACO phases 0 through 6.

Coordinates the full ACO pipeline:
Phase 0: Intent extraction
Phase 1: Objective perception
Phase 2: Decomposition into generator DAG
Phase 3: Generator engine execution (dry-run by default)
Phase 4: Goal tracking and drift detection
Phase 5: Refinement (on failure)
Phase 6: Consolidation and evolution package
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from scripts.aco.generator_engine import (
    ExecutionResult,
    ExecutionStatus,
    GeneratorEngine,
)
from scripts.aco.generator_graph import MutableGeneratorGraph
from scripts.aco.goal_tracker import GoalTracker
from scripts.aco.models import (
    EvolutionPackage,
    IntentSpec,
    ObjectiveSpec,
)
from scripts.aco.phases.phase0_intention import extract_intent
from scripts.aco.phases.phase1_perception import build_objective
from scripts.aco.phases.phase2_decomposition import decompose
from scripts.aco.phases.phase5_refinement import refine
from scripts.aco.phases.phase6_consolidation import consolidate

logger = logging.getLogger(__name__)

# Checkpoint directory
_CHECKPOINT_DIR = Path(".claude/checkpoints")

# Maximum refinement iterations before giving up
_MAX_REFINEMENT_ITERATIONS = 3


class AcoOrchestrator:
    """Top-level ACO pipeline orchestrator.

    Coordinates phases 0 through 6, saving checkpoints at each
    phase boundary and handling refinement loops on failure.

    Attributes:
        project_dir: Root directory of the project.
    """

    def __init__(self, project_dir: Path = Path(".")) -> None:
        """Initialize the orchestrator.

        Args:
            project_dir: Root directory of the project.
        """
        self._project_dir = project_dir
        self._session_results: list[dict[str, str]] = []
        self._patterns_found: list[str] = []

    @property
    def project_dir(self) -> Path:
        """Root directory of the project."""
        return self._project_dir

    def orchestrate(self, raw_prompt: str) -> EvolutionPackage:
        """Run the full ACO pipeline from raw prompt to evolution package.

        Sequence: Phase 0 -> 1 -> 2 -> 3 (execute) -> 4 (track) ->
        5 (refine if needed) -> 6 (consolidate).

        Args:
            raw_prompt: Raw user prompt text.

        Returns:
            EvolutionPackage with session results and learned patterns.
        """
        self._session_results = []
        self._patterns_found = []
        intent = self._run_phase0(raw_prompt)
        objective = self._run_phase1(intent)
        graph = self._run_phase2(objective)
        execution_results = self._run_phase3(graph)
        self._run_phase4(objective, execution_results)
        self._run_phase5_if_needed(graph, execution_results)
        return self._run_phase6()

    def _run_phase0(self, raw_prompt: str) -> IntentSpec:
        """Execute Phase 0: Intent extraction.

        Args:
            raw_prompt: Raw user prompt.

        Returns:
            IntentSpec object.
        """
        logger.info("Phase 0: Extracting intent")
        intent = extract_intent(raw_prompt)
        self._save_checkpoint("phase0_intent", intent.model_dump(mode="json"))
        self._session_results.append(
            {
                "phase": "phase0",
                "status": "success",
                "objective_hash": intent.objective_hash,
            }
        )
        return intent

    def _run_phase1(self, intent: IntentSpec) -> ObjectiveSpec:
        """Execute Phase 1: Objective perception.

        Args:
            intent: IntentSpec from Phase 0.

        Returns:
            ObjectiveSpec object.
        """
        logger.info("Phase 1: Building objective")
        objective = build_objective(intent)
        self._save_checkpoint("phase1_objective", objective.model_dump(mode="json"))
        self._session_results.append({"phase": "phase1", "status": "success"})
        return objective

    def _run_phase2(self, objective: ObjectiveSpec) -> MutableGeneratorGraph:
        """Execute Phase 2: Decomposition.

        Args:
            objective: ObjectiveSpec from Phase 1.

        Returns:
            MutableGeneratorGraph object.
        """
        logger.info("Phase 2: Decomposing objective")
        graph = decompose(objective)
        frozen = graph.freeze(objective_hash="decomposition")
        self._save_checkpoint("phase2_graph", frozen.model_dump(mode="json"))
        self._session_results.append({"phase": "phase2", "status": "success"})
        return graph

    def _run_phase3(
        self,
        graph: MutableGeneratorGraph,
    ) -> list[ExecutionResult]:
        """Execute Phase 3: Generator engine execution.

        Args:
            graph: MutableGeneratorGraph from Phase 2.

        Returns:
            List of ExecutionResult objects.
        """
        logger.info("Phase 3: Executing generators (dry-run)")
        engine = GeneratorEngine(project_root=self._project_dir, dry_run=True)
        order = graph.topological_sort()
        results = engine.execute_graph(order, graph.nodes)
        self._record_phase3_results(results)
        return results

    def _record_phase3_results(self, results: list[ExecutionResult]) -> None:
        """Record Phase 3 execution results.

        Args:
            results: List of ExecutionResult objects.
        """
        for r in results:
            status_str = "success" if r.status == ExecutionStatus.SUCCESS else "failed"
            self._session_results.append(
                {
                    "phase": "phase3",
                    "node_id": r.node_id,
                    "status": status_str,
                }
            )

    def _run_phase4(
        self,
        objective: ObjectiveSpec,
        execution_results: list[ExecutionResult],
    ) -> None:
        """Execute Phase 4: Goal tracking.

        Args:
            objective: ObjectiveSpec for tracking.
            execution_results: Results from Phase 3.
        """
        logger.info("Phase 4: Goal tracking")
        tracker = GoalTracker(objective, phase="phase4")

        success_count = sum(1 for r in execution_results if r.status == ExecutionStatus.SUCCESS)
        total = len(execution_results) if execution_results else 1

        tracker.assess_dimension(
            "precision",
            {"zero_hallucination": lambda: success_count / total},
        )
        state = tracker.compute_overall()
        self._save_checkpoint(
            "phase4_tracking",
            json.loads(state.model_dump_json()),
        )
        self._session_results.append({"phase": "phase4", "status": "success"})

    def _run_phase5_if_needed(
        self,
        graph: MutableGeneratorGraph,
        execution_results: list[ExecutionResult],
    ) -> None:
        """Execute Phase 5: Refinement if any phase3 node failed.

        Args:
            graph: MutableGeneratorGraph for refinement context.
            execution_results: Results from Phase 3.
        """
        failures = [r for r in execution_results if r.status != ExecutionStatus.SUCCESS]
        if not failures:
            self._patterns_found.append("zero_failures_in_execution")
            return

        logger.info("Phase 5: Refining %d failed nodes", len(failures))
        for failure in failures[:_MAX_REFINEMENT_ITERATIONS]:
            plan = refine(failure.node_id, failure.stderr, graph)
            self._session_results.append(
                {
                    "phase": "phase5",
                    "node_id": failure.node_id,
                    "status": "refined",
                    "layer": plan["layer"],
                }
            )

    def _run_phase6(self) -> EvolutionPackage:
        """Execute Phase 6: Consolidation.

        Returns:
            EvolutionPackage with all session data.
        """
        logger.info("Phase 6: Consolidating")
        return consolidate(self._session_results, self._patterns_found)

    def _save_checkpoint(self, name: str, data: Any) -> None:
        """Save a checkpoint file for a phase.

        Args:
            name: Checkpoint name (used in filename).
            data: JSON-serializable data to persist.
        """
        path = _CHECKPOINT_DIR / f"aco_{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug("Checkpoint saved: %s", path)
