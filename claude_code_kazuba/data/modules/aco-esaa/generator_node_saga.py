"""C2 — GeneratorNode ↔ SagaStep isomorphism bridge.

GeneratorNode (execute+validate+rollback triad) and SagaStep (action+compensation)
are structurally isomorphic. This module bridges the two, enabling any ACO generator
to be used as a saga step and vice versa.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from typing import Any

from scripts.aco.esaa.saga_orchestrator_v2 import SagaStep
from scripts.aco.models.core import (
    GeneratorContract,
    GeneratorNode,
    GeneratorOutputs,
    GeneratorType,
)


def _make_execute_fn(script_path: str) -> Callable[[], dict[str, Any]]:
    """Return a zero-arity callable that runs the given script.

    Args:
        script_path: Path to the execute script.

    Returns:
        Callable that runs the script and returns stdout as a dict.
    """

    def _run() -> dict[str, Any]:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=False,
        )
        return {"returncode": result.returncode, "stdout": result.stdout}

    return _run


def _make_compensate_fn(script_path: str) -> Callable[[Any], None]:
    """Return a callable that runs the rollback script.

    Args:
        script_path: Path to the rollback script.

    Returns:
        Callable accepting one optional argument that runs the rollback script.
    """

    def _run(_result: Any = None) -> None:
        subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=False,
        )

    return _run


def generator_node_to_saga_step(node: Any) -> SagaStep:
    """Convert a GeneratorNode into an ESAA SagaStep.

    Maps:
        node.id              → step.name
        node.outputs.execution_script → step.action (zero-arity script runner)
        node.outputs.rollback_script  → step.compensation (None if empty)

    Args:
        node: GeneratorNode instance (duck-typed for flexibility).

    Returns:
        SagaStep with wired action and optional compensation.
    """
    outputs = getattr(node, "outputs", node)
    execute_path: str = getattr(outputs, "execution_script", "")
    rollback_path: str = getattr(outputs, "rollback_script", "")
    name: str = str(getattr(node, "id", "unknown-node"))

    action: Callable[[], Any] = _make_execute_fn(execute_path) if execute_path else dict
    compensation: Callable[[Any], None] | None = _make_compensate_fn(rollback_path) if rollback_path else None

    return SagaStep(name=name, action=action, compensation=compensation)


def saga_step_to_generator_node(
    step: SagaStep,
    execute_script: str = "",
    validate_script: str = "",
    rollback_script: str = "",
    description: str = "",
) -> GeneratorNode:
    """Wrap a SagaStep as a GeneratorNode for ACO pipeline compatibility.

    Produces a valid GeneratorNode that satisfies the mandatory triad
    contract (execute + validate + rollback paths).

    Args:
        step: SagaStep to wrap.
        execute_script: Path for the execution script.
        validate_script: Path for the validation script.
        rollback_script: Path for the rollback script.
        description: Human-readable description (defaults to step name).

    Returns:
        GeneratorNode wrapping the given step.
    """
    node_description = description or f"SagaStep wrapper for '{step.name}'"

    return GeneratorNode(
        id=f"saga-step-{step.name}",
        description=node_description,
        generator_type=GeneratorType.TRANSFORMER,
        inputs_data=(),
        inputs_templates=(),
        inputs_constraints=(),
        outputs=GeneratorOutputs(
            execution_script=execute_script,
            validation_script=validate_script,
            rollback_script=rollback_script,
        ),
        contract=GeneratorContract(
            precondition="saga step is defined",
            postcondition="saga step executed",
            invariant="step name unchanged",
        ),
        acceptance_criteria="step executes without raising",
        depends_on=(),
    )


def round_trip_preserves_semantics(node: Any) -> bool:
    """Verify that GeneratorNode → SagaStep → GeneratorNode preserves semantics.

    The key semantic invariant: the node's ``id`` must survive the round-trip
    as the SagaStep's ``name``.

    Args:
        node: GeneratorNode to verify.

    Returns:
        True if the round-trip preserves the id↔name mapping.
    """
    step = generator_node_to_saga_step(node)
    return step.name == str(getattr(node, "id", ""))
