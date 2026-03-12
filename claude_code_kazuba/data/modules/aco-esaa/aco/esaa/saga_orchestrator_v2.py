"""Optimized Saga Orchestrator v2: Deferred Event Persistence.

Implements the Saga pattern with deferred event persistence.
Execute all steps in memory first, then batch-write events only
on successful completion.

Expected improvement: Saga overhead < 0.01ms per step.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .event_buffer import DomainEvent

logger = logging.getLogger(__name__)


class SagaStatus(str, Enum):
    """Status of a saga execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


class StepStatus(str, Enum):
    """Status of a saga step."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    COMPENSATED = "compensated"


@dataclass(frozen=True)
class SagaResult:
    """Result of saga execution.

    Attributes:
        saga_id: Unique saga identifier.
        status: Final saga status.
        steps_completed: Number of steps completed.
        steps_total: Total number of steps.
        duration_ms: Execution duration in milliseconds.
        events: List of events generated (if successful).
        error: Error message if failed.
    """

    saga_id: str
    status: SagaStatus
    steps_completed: int
    steps_total: int
    duration_ms: float
    events: tuple[DomainEvent, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class SagaStepResult:
    """Result of a single saga step.

    Attributes:
        step_index: Index of the step.
        step_name: Name of the step.
        status: Step execution status.
        result: Step output data.
        error: Error if step failed.
    """

    step_index: int
    step_name: str
    status: StepStatus
    result: Any = None
    error: str | None = None


@dataclass
class SagaStep:
    """Single step in a saga.

    Attributes:
        name: Step name for logging/debugging.
        action: Function to execute the step.
        compensation: Optional function to compensate the step.
    """

    name: str
    action: Callable[..., Any]
    compensation: Callable[..., Any] | None = None


def _build_saga_events(
    saga_id: str,
    steps: list[SagaStep],
    step_results: list[SagaStepResult],
    correlation_id: str | None,
) -> list[DomainEvent]:
    """Build domain events from a completed saga execution.

    Shared by both sync and async saga implementations.

    Args:
        saga_id: Saga identifier.
        steps: Original saga steps.
        step_results: Results of each executed step.
        correlation_id: Optional correlation ID for event tracing.

    Returns:
        List of domain events including per-step and completion events.
    """
    from .event_buffer import DomainEvent

    base_time = time.time()

    events = [
        DomainEvent(
            event_id=f"{saga_id}-step-{i}",
            event_type="saga_step_completed",
            agent_id="saga_orchestrator",
            timestamp=base_time + (i * 0.001),
            payload={
                "saga_id": saga_id,
                "step_index": i,
                "step_name": step_result.step_name,
                "step_result": str(step_result.result),
            },
            correlation_id=correlation_id,
        )
        for i, step_result in enumerate(step_results)
    ]

    events.append(
        DomainEvent(
            event_id=f"{saga_id}-completed",
            event_type="saga_completed",
            agent_id="saga_orchestrator",
            timestamp=base_time + len(step_results) * 0.001,
            payload={
                "saga_id": saga_id,
                "steps_total": len(steps),
                "status": "success",
            },
            correlation_id=correlation_id,
        )
    )

    return events


@dataclass
class OptimizedSaga:
    """Optimized Saga with deferred event persistence.

    Executes all steps in memory first, collecting events.
    Only persists events to disk on successful completion.
    If any step fails, compensates in-memory and no events
    are persisted.

    Example:
        >>> saga = OptimizedSaga(
        ...     saga_id="transfer-123",
        ...     steps=[
        ...         SagaStep(name="debit", action=debit_account),
        ...         SagaStep(name="credit", action=credit_account),
        ...     ],
        ... )
        >>> result = saga.execute()
        >>> if result.status == SagaStatus.SUCCESS:
        ...     events = result.events  # Batch-written to disk
    """

    saga_id: str
    steps: list[SagaStep]
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        self._step_results: list[SagaStepResult] = []
        self._events: list[DomainEvent] = []

    def execute(self) -> SagaResult:
        """Execute the saga with deferred persistence.

        Returns:
            SagaResult with status and events (if successful).
        """
        start_time = time.perf_counter()
        self._step_results = []
        self._events = []

        logger.debug("Starting saga %s with %d steps", self.saga_id, len(self.steps))

        for i, step in enumerate(self.steps):
            result = self._execute_step(i, step)
            self._step_results.append(result)

            if result.status == StepStatus.FAILED:
                self._compensate_in_memory(i)
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.warning(
                    "Saga %s failed at step %d (%s)",
                    self.saga_id,
                    i,
                    step.name,
                )
                return SagaResult(
                    saga_id=self.saga_id,
                    status=SagaStatus.COMPENSATED,
                    steps_completed=i,
                    steps_total=len(self.steps),
                    duration_ms=duration_ms,
                    error=result.error,
                )

        self._events = _build_saga_events(
            self.saga_id,
            self.steps,
            self._step_results,
            self.correlation_id,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(
            "Saga %s completed successfully in %.3fms",
            self.saga_id,
            duration_ms,
        )
        return SagaResult(
            saga_id=self.saga_id,
            status=SagaStatus.SUCCESS,
            steps_completed=len(self.steps),
            steps_total=len(self.steps),
            duration_ms=duration_ms,
            events=tuple(self._events),
        )

    def _execute_step(self, index: int, step: SagaStep) -> SagaStepResult:
        """Execute a single step."""
        try:
            logger.debug("Executing step %d: %s", index, step.name)
            result = step.action()

            return SagaStepResult(
                step_index=index,
                step_name=step.name,
                status=StepStatus.SUCCESS,
                result=result,
            )
        except Exception as e:
            logger.exception("Step %d (%s) failed", index, step.name)
            return SagaStepResult(
                step_index=index,
                step_name=step.name,
                status=StepStatus.FAILED,
                error=str(e),
            )

    def _compensate_in_memory(self, failed_index: int) -> None:
        """Compensate completed steps in reverse order."""
        for i in range(failed_index - 1, -1, -1):
            step = self.steps[i]
            result = self._step_results[i]

            if result.status == StepStatus.SUCCESS and step.compensation:
                try:
                    logger.debug("Compensating step %d: %s", i, step.name)
                    step.compensation(result.result)
                    self._step_results[i] = SagaStepResult(
                        step_index=i,
                        step_name=step.name,
                        status=StepStatus.COMPENSATED,
                        result=result.result,
                    )
                except Exception:
                    logger.exception(
                        "Compensation failed for step %d (%s)",
                        i,
                        step.name,
                    )

    def get_step_results(self) -> list[SagaStepResult]:
        """Get results of all executed steps."""
        return self._step_results.copy()


@dataclass
class AsyncOptimizedSaga:
    """Async version of OptimizedSaga for async step actions."""

    saga_id: str
    steps: list[SagaStep]
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        self._step_results: list[SagaStepResult] = []
        self._events: list[DomainEvent] = []

    async def execute(self) -> SagaResult:
        """Execute async saga with deferred persistence."""
        start_time = time.perf_counter()
        self._step_results = []
        self._events = []

        logger.debug(
            "Starting async saga %s with %d steps",
            self.saga_id,
            len(self.steps),
        )

        for i, step in enumerate(self.steps):
            result = await self._execute_step(i, step)
            self._step_results.append(result)

            if result.status == StepStatus.FAILED:
                await self._compensate_in_memory(i)
                duration_ms = (time.perf_counter() - start_time) * 1000
                return SagaResult(
                    saga_id=self.saga_id,
                    status=SagaStatus.COMPENSATED,
                    steps_completed=i,
                    steps_total=len(self.steps),
                    duration_ms=duration_ms,
                    error=result.error,
                )

        self._events = _build_saga_events(
            self.saga_id,
            self.steps,
            self._step_results,
            self.correlation_id,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000
        return SagaResult(
            saga_id=self.saga_id,
            status=SagaStatus.SUCCESS,
            steps_completed=len(self.steps),
            steps_total=len(self.steps),
            duration_ms=duration_ms,
            events=tuple(self._events),
        )

    async def _execute_step(self, index: int, step: SagaStep) -> SagaStepResult:
        """Execute a single async step."""
        import asyncio

        try:
            logger.debug("Executing async step %d: %s", index, step.name)

            result = step.action()
            if asyncio.iscoroutine(result):
                result = await result

            return SagaStepResult(
                step_index=index,
                step_name=step.name,
                status=StepStatus.SUCCESS,
                result=result,
            )
        except Exception as e:
            logger.exception("Async step %d (%s) failed", index, step.name)
            return SagaStepResult(
                step_index=index,
                step_name=step.name,
                status=StepStatus.FAILED,
                error=str(e),
            )

    async def _compensate_in_memory(self, failed_index: int) -> None:
        """Compensate async steps in reverse order."""
        for i in range(failed_index - 1, -1, -1):
            step = self.steps[i]
            result = self._step_results[i]

            if result.status == StepStatus.SUCCESS and step.compensation:
                try:
                    comp_result = step.compensation(result.result)
                    if hasattr(comp_result, "__await__"):
                        await comp_result

                    self._step_results[i] = SagaStepResult(
                        step_index=i,
                        step_name=step.name,
                        status=StepStatus.COMPENSATED,
                        result=result.result,
                    )
                except Exception:
                    logger.exception(
                        "Async compensation failed for step %d (%s)",
                        i,
                        step.name,
                    )


class SagaOrchestratorV2:
    """Orchestrator for managing multiple optimized sagas."""

    def __init__(self, max_history: int = 1000) -> None:
        """Initialize the saga orchestrator.

        Args:
            max_history: Maximum number of completed saga results to keep
                in memory. Oldest entries are evicted first (FIFO).
        """
        self._active_sagas: dict[str, OptimizedSaga | AsyncOptimizedSaga] = {}
        self._completed_sagas: dict[str, SagaResult] = {}
        self._saga_count = 0
        self._max_history = max_history

    def _next_saga_id(self, prefix: str) -> str:
        """Generate the next unique saga ID.

        Args:
            prefix: ID prefix (e.g., "saga" or "saga-async").

        Returns:
            Unique saga ID string. Uses uuid4 suffix to prevent collisions
            in fast loops where int(time.time()) would repeat within the same
            second (e.g., when creating 1000+ sagas in unit tests).
        """
        import uuid

        self._saga_count += 1
        return f"{prefix}-{self._saga_count}-{uuid.uuid4().hex[:8]}"

    def create_saga(
        self,
        steps: list[SagaStep],
        correlation_id: str | None = None,
    ) -> OptimizedSaga:
        """Create a new saga instance.

        Args:
            steps: List of saga steps.
            correlation_id: Optional correlation ID.

        Returns:
            Configured OptimizedSaga instance.
        """
        saga = OptimizedSaga(
            saga_id=self._next_saga_id("saga"),
            steps=steps,
            correlation_id=correlation_id,
        )
        self._active_sagas[saga.saga_id] = saga
        return saga

    def create_async_saga(
        self,
        steps: list[SagaStep],
        correlation_id: str | None = None,
    ) -> AsyncOptimizedSaga:
        """Create a new async saga instance.

        Args:
            steps: List of saga steps.
            correlation_id: Optional correlation ID.

        Returns:
            Configured AsyncOptimizedSaga instance.
        """
        saga = AsyncOptimizedSaga(
            saga_id=self._next_saga_id("saga-async"),
            steps=steps,
            correlation_id=correlation_id,
        )
        self._active_sagas[saga.saga_id] = saga
        return saga

    def complete_saga(self, saga_id: str, result: SagaResult) -> None:
        """Mark a saga as completed.

        Evicts the oldest entry (FIFO) when the history limit is reached to
        prevent unbounded memory growth in long-running orchestrators.

        Args:
            saga_id: ID of completed saga.
            result: Saga execution result.
        """
        self._completed_sagas[saga_id] = result
        self._active_sagas.pop(saga_id, None)
        if len(self._completed_sagas) > self._max_history:
            oldest_key = next(iter(self._completed_sagas))
            del self._completed_sagas[oldest_key]

    def get_saga_result(self, saga_id: str) -> SagaResult | None:
        """Get result of a completed saga.

        Args:
            saga_id: Saga ID to look up.

        Returns:
            SagaResult if completed, None otherwise.
        """
        return self._completed_sagas.get(saga_id)

    def get_stats(self) -> dict[str, int]:
        """Get orchestrator statistics."""
        return {
            "active_sagas": len(self._active_sagas),
            "completed_sagas": len(self._completed_sagas),
            "total_created": self._saga_count,
        }
