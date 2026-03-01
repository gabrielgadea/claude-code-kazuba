"""
Hypervisor Bridge — Reinforcement Learning and Metrics integration.

Provides bidirectional integration between the Hypervisor and downstream
learning systems (RLM, metrics collectors, external event stores). Captures
phase lifecycle events as LearningEvents and exports them as JSONL for
offline analysis or online training.

Architecture:
    Hypervisor  →  HypervisorBridge  →  LearningEvent store
                                     →  JSONL export
                                     →  External RL/metrics systems
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Models (Pydantic v2, frozen=True)
# ============================================================================


class LearningEvent(BaseModel, frozen=True):
    """Immutable record of a single phase lifecycle event.

    Attributes:
        event_type: Category of the event (e.g. "phase_start", "phase_end").
        phase_id: Numeric identifier of the phase that generated the event.
        duration_ms: Duration of the phase in milliseconds (0 for start events).
        success: True if the phase completed successfully.
        metadata: Arbitrary key-value pairs for additional context.
        timestamp: ISO 8601 timestamp when this event was created.
    """

    event_type: str
    phase_id: int
    duration_ms: int = 0
    success: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable dictionary representation."""
        return {
            "event_type": self.event_type,
            "phase_id": self.phase_id,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


# ============================================================================
# HypervisorBridge
# ============================================================================


class HypervisorBridge:
    """Bridge between Hypervisor and learning/metrics systems.

    Captures phase lifecycle events, stores them in memory, and provides
    export utilities for downstream consumption. When disabled, all methods
    are no-ops so the hypervisor incurs no overhead.

    Args:
        enabled: If False, all recording methods become no-ops.
    """

    def __init__(self, enabled: bool = True) -> None:
        """Initialise the bridge.

        Args:
            enabled: Whether event recording is active. Defaults to True.
        """
        self._enabled = enabled
        self._history: list[LearningEvent] = []
        self._phase_start_times: dict[int, datetime] = {}

        if enabled:
            logger.debug("HypervisorBridge initialised (recording ON)")
        else:
            logger.debug("HypervisorBridge initialised (recording OFF)")

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        """Return True if event recording is active."""
        return self._enabled

    # -------------------------------------------------------------------------
    # Public recording API
    # -------------------------------------------------------------------------

    def record_phase_start(self, phase_id: int) -> None:
        """Record that a phase has begun execution.

        Stores the start timestamp so that duration can be calculated
        when record_phase_end is called.

        Args:
            phase_id: Numeric identifier of the phase that started.
        """
        if not self._enabled:
            return

        self._phase_start_times[phase_id] = datetime.now(UTC)
        event = self._make_event(
            event_type="phase_start",
            phase_id=phase_id,
            success=False,
            duration_ms=0,
        )
        self._history.append(event)
        logger.debug("Bridge: phase_start recorded for phase %d", phase_id)

    def record_phase_end(self, phase_id: int, result: Any) -> None:
        """Record that a phase has completed.

        Calculates duration from the stored start time and appends a
        phase_end (or phase_failed) event depending on result status.

        Args:
            phase_id: Numeric identifier of the completed phase.
            result: ExecutionResult or any object with .success and
                    .duration_ms attributes. Also accepts a dict with
                    those keys.
        """
        if not self._enabled:
            return

        # Resolve success and duration from various result types
        if hasattr(result, "success"):
            is_success = bool(result.success)
            duration_ms = getattr(result, "duration_ms", 0)
        elif isinstance(result, dict):
            is_success = bool(result.get("success", False))
            duration_ms = int(result.get("duration_ms", 0))
        else:
            is_success = False
            duration_ms = 0

        # Fallback: calculate from stored start time
        if duration_ms == 0 and phase_id in self._phase_start_times:
            start = self._phase_start_times[phase_id]
            elapsed = (datetime.now(UTC) - start).total_seconds()
            duration_ms = int(elapsed * 1000)

        event_type = "phase_end" if is_success else "phase_failed"
        event = self._make_event(
            event_type=event_type,
            phase_id=phase_id,
            success=is_success,
            duration_ms=duration_ms,
        )
        self._history.append(event)
        # Clean up start time
        self._phase_start_times.pop(phase_id, None)

        logger.debug(
            "Bridge: %s recorded for phase %d (duration=%dms)",
            event_type,
            phase_id,
            duration_ms,
        )

    # -------------------------------------------------------------------------
    # Query API
    # -------------------------------------------------------------------------

    def get_history(self) -> list[LearningEvent]:
        """Return a copy of all recorded learning events.

        Returns:
            List of LearningEvents in chronological order.
        """
        return list(self._history)

    def get_events_for_phase(self, phase_id: int) -> list[LearningEvent]:
        """Return all events associated with a specific phase.

        Args:
            phase_id: Phase to filter by.

        Returns:
            Filtered list of LearningEvents.
        """
        return [e for e in self._history if e.phase_id == phase_id]

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics across all recorded events.

        Returns:
            Dict with keys: total_events, phases_started, phases_succeeded,
            phases_failed.
        """
        started = sum(1 for e in self._history if e.event_type == "phase_start")
        succeeded = sum(1 for e in self._history if e.event_type == "phase_end")
        failed = sum(1 for e in self._history if e.event_type == "phase_failed")
        return {
            "total_events": len(self._history),
            "phases_started": started,
            "phases_succeeded": succeeded,
            "phases_failed": failed,
        }

    # -------------------------------------------------------------------------
    # Export API
    # -------------------------------------------------------------------------

    def export_jsonl(self, path: Path) -> int:
        """Export all recorded events to a JSONL file.

        Each line in the output file is a valid JSON object representing one
        LearningEvent. If there are no events, an empty file is created.

        Args:
            path: Destination file path. Parent directories are created
                  automatically.

        Returns:
            Number of events written to the file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with path.open("w", encoding="utf-8") as fh:
            for event in self._history:
                fh.write(json.dumps(event.to_dict()) + "\n")
                count += 1

        logger.info("Bridge: exported %d events to %s", count, path)
        return count

    def clear(self) -> None:
        """Clear all recorded events and start times."""
        self._history.clear()
        self._phase_start_times.clear()
        logger.debug("Bridge: history cleared")

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _make_event(
        self,
        event_type: str,
        phase_id: int,
        success: bool = False,
        duration_ms: int = 0,
        **kwargs: Any,
    ) -> LearningEvent:
        """Construct a LearningEvent with the current UTC timestamp.

        Args:
            event_type: Category string for the event.
            phase_id: Phase identifier.
            success: Whether the associated operation succeeded.
            duration_ms: Duration in milliseconds.
            **kwargs: Additional fields merged into the metadata dict.

        Returns:
            A frozen LearningEvent instance.
        """
        metadata: dict[str, Any] = {k: v for k, v in kwargs.items()}
        return LearningEvent(
            event_type=event_type,
            phase_id=phase_id,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata,
        )
