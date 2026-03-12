"""KazubaCognitiveEvent — cognitive metadata envelope for ESAA DomainEvents.

Wraps a base DomainEvent with ACO cognitive context (CILA level, Q-value
estimate, intention). Provides the reward signal for Offline RL (Sprint D).

Example:
    >>> from scripts.aco.esaa.cognitive_event import CognitiveTrace, KazubaCognitiveEvent
    >>> from scripts.aco.esaa.event_buffer import DomainEvent
    >>> import time, uuid
    >>> base = DomainEvent(
    ...     event_id=str(uuid.uuid4()),
    ...     event_type="agent_executed",
    ...     agent_id="agent-1",
    ...     timestamp=time.time(),
    ...     payload={"result": "ok"},
    ... )
    >>> trace = CognitiveTrace(cila_level=2, intention="execute code")
    >>> cognitive_event = KazubaCognitiveEvent(base_event=base, cognitive_trace=trace)
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .event_buffer import DomainEvent


class CognitiveTrace(BaseModel):
    """Cognitive metadata attached to an ACO agent action.

    Attributes:
        cila_level: CILA complexity level (0=Direct … 6=Multi-Agent).
        intention: Human-readable description of the agent's goal.
        q_value_estimate: Bellman Q-value estimate for this action (Decimal
            for precision; updated by OfflineRLBuffer in Sprint D).
        confidence: Agent's confidence in this action [0.0, 1.0].
        technique: CognitiveTechnique hint injected by intent_router.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    cila_level: int
    intention: str
    q_value_estimate: Decimal = Decimal("0.0")
    confidence: float = 0.0
    technique: str = ""


class KazubaCognitiveEvent(BaseModel):
    """DomainEvent envelope with ACO cognitive metadata.

    Combines the raw DomainEvent (what happened) with CognitiveTrace
    (why it happened and how confident the agent was), enabling:
    - Offline RL training via Q-value signals (Sprint D).
    - Reproducible CILA routing analysis (Sprint C).
    - Post-mortem agent behavior inspection via Time-Travel Debugger.

    Attributes:
        base_event: The underlying domain event.
        cognitive_trace: Cognitive metadata for this action.
        schema_version: Schema version for EventUpcaster compatibility.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    base_event: DomainEvent
    cognitive_trace: CognitiveTrace
    schema_version: int = 1

    def to_dict(self) -> dict:
        """Serialize to a plain dict for persistence.

        Returns:
            Nested dict with ``base_event``, ``cognitive_trace``, and
            ``schema_version`` keys.
        """
        return {
            "base_event": self.base_event.to_dict(),
            "cognitive_trace": {
                "cila_level": self.cognitive_trace.cila_level,
                "intention": self.cognitive_trace.intention,
                "q_value_estimate": str(self.cognitive_trace.q_value_estimate),
                "confidence": self.cognitive_trace.confidence,
                "technique": self.cognitive_trace.technique,
            },
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> KazubaCognitiveEvent:
        """Deserialise from a plain dict.

        Args:
            data: Dict previously produced by ``to_dict()``.

        Returns:
            Reconstructed KazubaCognitiveEvent.
        """
        trace_data = data["cognitive_trace"]
        trace = CognitiveTrace(
            cila_level=int(trace_data["cila_level"]),
            intention=trace_data["intention"],
            q_value_estimate=Decimal(str(trace_data.get("q_value_estimate", "0.0"))),
            confidence=float(trace_data.get("confidence", 0.0)),
            technique=str(trace_data.get("technique", "")),
        )
        return cls(
            base_event=DomainEvent.from_dict(data["base_event"]),
            cognitive_trace=trace,
            schema_version=int(data.get("schema_version", 1)),
        )
