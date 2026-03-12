"""saga_orchestrator.py — ESAA Saga Pattern Implementation.

Manages long-running transactions with compensation support.

The Saga pattern ensures data consistency across distributed services
by breaking transactions into steps that can be compensated (undone)
if any step fails.

Example:
    steps = [
        SagaStep(name="create_agent", action=create_fn, compensation=delete_fn),
        SagaStep(name="validate_agent", action=validate_fn),
    ]
    saga = SagaOrchestrator("agent_creation", steps)
    result = saga.execute()

    if result.status == "completed":
        print("Success!")
    elif result.status == "compensated":
        print(f"Failed at step {result.steps_failed}, compensated {result.steps_compensated}")
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SagaStep:
    """Single step in a saga.

    Attributes:
        name: Human-readable step name
        action: Function to execute (returns result dict)
        compensation: Optional function to undo action
        max_retries: Number of retries on failure
    """

    name: str
    action: Callable[[], dict[str, Any]]
    compensation: Callable[[], dict[str, Any]] | None = None
    max_retries: int = 0


@dataclass
class SagaResult:
    """Result of saga execution.

    Attributes:
        status: 'completed', 'failed', or 'compensated'
        steps_completed: Number of steps that succeeded
        steps_failed: Number of steps that failed
        steps_compensated: Number of steps that were rolled back
        results: Output from each step
        errors: Error messages
        saga_id: Identifier of the saga
    """

    status: str
    steps_completed: int = 0
    steps_failed: int = 0
    steps_compensated: int = 0
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    saga_id: str = ""


class SagaOrchestrator:
    """Orchestrates saga execution with compensation.

    Usage:
        steps = [
            SagaStep(name="create_agent", action=create_fn, compensation=delete_fn),
            SagaStep(name="validate_agent", action=validate_fn),
        ]
        saga = SagaOrchestrator("agent_creation", steps)
        result = saga.execute()
    """

    def __init__(self, saga_id: str, steps: list[SagaStep]) -> None:
        """Initialize saga.

        Args:
            saga_id: Unique saga identifier
            steps: Ordered list of saga steps
        """
        self._saga_id = saga_id
        self._steps = steps
        self._completed_steps: list[int] = []

    def execute(self) -> SagaResult:
        """Execute saga with compensation on failure.

        Returns:
            SagaResult with execution status
        """
        logger.info("Starting saga: %s (%d steps)", self._saga_id, len(self._steps))

        self._completed_steps = []
        result = SagaResult(status="completed", saga_id=self._saga_id)

        for i, step in enumerate(self._steps):
            logger.info("Executing step %d: %s", i, step.name)

            # Execute with retries
            step_result = self._execute_with_retries(step, result)

            if step_result is None:
                # Step failed after all retries
                result.steps_failed += 1
                result.errors.append(f"Step '{step.name}' failed after retries")

                # Trigger compensation
                self._compensate(i)
                result.steps_compensated = len(self._completed_steps)
                result.status = "compensated"
                return result

            result.results[step.name] = step_result
            result.steps_completed += 1
            self._completed_steps.append(i)

        logger.info("Saga completed successfully: %s", self._saga_id)
        return result

    def _execute_with_retries(self, step: SagaStep, result: SagaResult) -> dict[str, Any] | None:
        """Execute a step with retry logic.

        Args:
            step: Saga step to execute
            result: Current saga result for context

        Returns:
            Step result dict or None if all retries failed
        """
        for attempt in range(step.max_retries + 1):
            try:
                step_result = step.action()

                # Check if step reported failure
                if step_result.get("status") == "failure":
                    raise RuntimeError(f"Step {step.name} returned failure status")

                return step_result

            except Exception as e:
                if attempt < step.max_retries:
                    logger.warning(
                        "Step %s failed (attempt %d/%d): %s",
                        step.name,
                        attempt + 1,
                        step.max_retries + 1,
                        e,
                    )
                else:
                    logger.error(
                        "Step %s failed after %d attempts: %s",
                        step.name,
                        step.max_retries + 1,
                        e,
                    )
                    result.errors.append(f"{step.name}: {e}")

        return None

    def _compensate(self, failed_step_index: int) -> None:
        """Run compensation for completed steps in reverse order.

        Args:
            failed_step_index: Index of the step that failed
        """
        logger.warning(
            "Compensating saga %s after step %d failure",
            self._saga_id,
            failed_step_index,
        )

        for i in reversed(self._completed_steps):
            step = self._steps[i]
            if step.compensation:
                try:
                    logger.info("Compensating step %d: %s", i, step.name)
                    step.compensation()
                except Exception as e:
                    logger.error(
                        "Compensation failed for step %d (%s): %s",
                        i,
                        step.name,
                        e,
                    )
                    # Continue with other compensations
            else:
                logger.warning("No compensation for step %d: %s", i, step.name)

    def get_status(self) -> dict[str, Any]:
        """Get current saga status.

        Returns:
            Dictionary with saga status information
        """
        return {
            "saga_id": self._saga_id,
            "total_steps": len(self._steps),
            "completed_steps": len(self._completed_steps),
            "remaining_steps": len(self._steps) - len(self._completed_steps),
            "step_names": [step.name for step in self._steps],
            "completed_step_names": [self._steps[i].name for i in self._completed_steps],
        }


class SagaBuilder:
    """Builder for constructing sagas fluently.

    Example:
        saga = (
            SagaBuilder("my_saga")
            .step("create", create_fn, compensate=delete_fn)
            .step("validate", validate_fn)
            .step("save", save_fn, compensate=delete_save)
            .build()
        )
        result = saga.execute()
    """

    def __init__(self, saga_id: str) -> None:
        """Initialize builder.

        Args:
            saga_id: Unique saga identifier
        """
        self._saga_id = saga_id
        self._steps: list[SagaStep] = []

    def step(
        self,
        name: str,
        action: Callable[[], dict[str, Any]],
        compensate: Callable[[], dict[str, Any]] | None = None,
        max_retries: int = 0,
    ) -> SagaBuilder:
        """Add a step to the saga.

        Args:
            name: Step name
            action: Function to execute
            compensate: Optional compensation function
            max_retries: Number of retries on failure

        Returns:
            Self for method chaining
        """
        self._steps.append(
            SagaStep(
                name=name,
                action=action,
                compensation=compensate,
                max_retries=max_retries,
            )
        )
        return self

    def build(self) -> SagaOrchestrator:
        """Build the saga orchestrator.

        Returns:
            Configured SagaOrchestrator
        """
        return SagaOrchestrator(self._saga_id, self._steps)


if __name__ == "__main__":
    # Demo usage
    import tempfile
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)

    created_files: list[Path] = []

    def create_file() -> dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            tmp = Path(f.name)
        created_files.append(tmp)
        return {"status": "success", "file": str(tmp)}

    def delete_file() -> dict[str, Any]:
        if created_files:
            tmp = created_files.pop()
            if tmp.exists():
                tmp.unlink()
        return {"status": "success"}

    def validate_file() -> dict[str, Any]:
        return {"status": "success", "valid": True}

    # Build and execute saga
    saga = (
        SagaBuilder("file_processing")
        .step("create", create_file, compensate=delete_file)
        .step("validate", validate_file)
        .build()
    )

    result = saga.execute()
    print(f"\nSaga result: {result.status}")
    print(f"Completed: {result.steps_completed}, Failed: {result.steps_failed}")

    # Cleanup
    for f in created_files:
        if f.exists():
            f.unlink()
