"""C1 — CILA Router as Saga Manager.

Routes a prompt through CILA L0-L6 as a compensable Saga, with
every routing decision persisted as a DomainEvent for replay and audit.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .event_buffer import DomainEvent, new_event_id
from .saga_orchestrator_v2 import OptimizedSaga, SagaResult, SagaStep

if TYPE_CHECKING:
    from .sqlite_backend import SQLiteEventStore

# DEFAULT_CILA_KEYWORDS — full L0-L6 coverage, domain-independent
DEFAULT_CILA_KEYWORDS: dict[int, list[str]] = {
    6: ["team", "swarm", "orchestrat", "multi-agent"],
    5: ["evolve", "self-modif", "meta"],
    4: ["agent", "loop", "cycle"],
    3: ["pipeline", "process"],  # "antt" removed — was hardcoded domain keyword
    2: ["search", "retriev", "query"],
    1: ["compute", "calculat", "run"],
    0: [],
}

# Module-level default used by _classify_prompt (set by build_cila_router or default)
_CILA_KEYWORDS: list[tuple[int, list[str]]] = [
    (level, words)
    for level, words in sorted(
        DEFAULT_CILA_KEYWORDS.items(),
        reverse=True,
    )
    if words
]


def build_cila_router(
    domain_keywords: dict[int, list[str]] | None = None,
) -> _CILARouterConfig:
    """Build a CILARouter config with merged domain keywords.

    Merges domain_keywords onto DEFAULT_CILA_KEYWORDS (additive, not replace).
    Domain keywords are ADDED to existing level lists.

    Args:
        domain_keywords: Optional dict mapping CILA level (0-6) to keyword lists.
            These are ADDED to the default keywords for each level.

    Returns:
        A _CILARouterConfig instance.

    Example:
        >>> router = build_cila_router({3: ["lexcore", "convert"]})
        >>> # L3 now has ["pipeline", "process", "lexcore", "convert"]
        >>> # L4 default ["agent", "loop", "cycle"] is untouched
    """
    keywords = {k: list(v) for k, v in DEFAULT_CILA_KEYWORDS.items()}
    if domain_keywords:
        for level, words in domain_keywords.items():
            keywords[level] = keywords.get(level, []) + words
    return _CILARouterConfig(keywords=keywords)


class _CILARouterConfig:
    """Internal config holder for parametrized CILA routing.

    Attributes:
        keywords: Merged keyword dict (level -> word list).
    """

    def __init__(self, keywords: dict[int, list[str]]) -> None:
        self.keywords = keywords
        self._sorted_keywords: list[tuple[int, list[str]]] = [
            (level, words)
            for level, words in sorted(
                keywords.items(),
                reverse=True,
            )
            if words
        ]

    def classify_prompt(self, prompt: str) -> int:
        """Classify a prompt into a CILA level using this config's keywords.

        Args:
            prompt: Raw user prompt string.

        Returns:
            Integer CILA level (0-6).
        """
        lower = prompt.lower()
        for level, kws in self._sorted_keywords:
            if any(kw in lower for kw in kws):
                return level
        return 0


_LEVEL_TECHNIQUE: dict[int, str] = {
    0: "direct_response",
    1: "compute_first",
    2: "tool_augmented",
    3: "pipeline_check",
    4: "aco_identity",
    5: "self_modifying",
    6: "team_coordination",
}


def _classify_prompt(prompt: str) -> int:
    """Classify a prompt into a CILA level (0-6).

    Args:
        prompt: Raw user prompt string.

    Returns:
        Integer CILA level where 0=direct response, 6=multi-agent.
    """
    lower = prompt.lower()
    for level, keywords in _CILA_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return level
    return 0


@dataclass
class RouteContext:
    """Mutable routing context shared across saga steps.

    Attributes:
        prompt: Original prompt text.
        cila_level: Classified CILA level (0-6).
        technique: Cognitive technique name for the level.
        route_event_id: ID of the emitted routing event.
    """

    prompt: str
    cila_level: int = 0
    technique: str = ""
    route_event_id: str = ""


def _make_classify_step(ctx: RouteContext) -> SagaStep:
    """Build the classify_intent SagaStep (zero-arity action)."""

    def _execute() -> dict[str, Any]:
        ctx.cila_level = _classify_prompt(ctx.prompt)
        return {"cila_level": ctx.cila_level}

    def _compensate(_result: Any = None) -> None:
        ctx.cila_level = 0

    return SagaStep(name="classify_intent", action=_execute, compensation=_compensate)


def _make_inject_step(ctx: RouteContext) -> SagaStep:
    """Build the inject_technique SagaStep."""

    def _execute() -> dict[str, Any]:
        ctx.technique = _LEVEL_TECHNIQUE.get(ctx.cila_level, "direct_response")
        return {"technique": ctx.technique}

    def _compensate(_result: Any = None) -> None:
        ctx.technique = ""

    return SagaStep(name="inject_technique", action=_execute, compensation=_compensate)


def _make_emit_step(ctx: RouteContext) -> SagaStep:
    """Build the emit_route_event SagaStep."""

    def _execute() -> dict[str, Any]:
        ctx.route_event_id = new_event_id()
        return {"route_event_id": ctx.route_event_id}

    def _compensate(_result: Any = None) -> None:
        ctx.route_event_id = ""

    return SagaStep(name="emit_route_event", action=_execute, compensation=_compensate)


@dataclass
class CILARouteSaga:
    """Routes a prompt through CILA L0-L6 as a compensable saga.

    Attributes:
        prompt: The prompt to classify and route.
    """

    prompt: str

    def __post_init__(self) -> None:
        self.context = RouteContext(prompt=self.prompt)
        self._saga = OptimizedSaga(
            saga_id=f"cila-route-{uuid.uuid4().hex[:8]}",
            steps=[
                _make_classify_step(self.context),
                _make_inject_step(self.context),
                _make_emit_step(self.context),
            ],
        )

    def execute(self) -> SagaResult:
        """Execute the routing saga.

        Returns:
            SagaResult with SUCCESS or COMPENSATED status.
        """
        return self._saga.execute()


class CILARouterEventStore:
    """Routes prompts and persists every decision as a DomainEvent.

    Wraps CILARouteSaga with event sourcing, enabling full replay of
    all historical routing classifications for debugging and audit.

    Args:
        store: SQLite event store for durable persistence.
    """

    def __init__(self, store: SQLiteEventStore) -> None:
        self._store = store

    def route(self, prompt: str) -> dict[str, Any]:
        """Route a prompt and persist the classification decision.

        Args:
            prompt: User prompt to classify.

        Returns:
            Dict with keys: cila_level, technique, event_id, saga_status.
        """
        saga = CILARouteSaga(prompt)
        result = saga.execute()
        ctx = saga.context

        event = DomainEvent(
            event_id=ctx.route_event_id or new_event_id(),
            event_type="prompt_routed",
            agent_id="cila_router",
            timestamp=time.time(),
            payload={
                "prompt": prompt[:200],
                "cila_level": ctx.cila_level,
                "technique": ctx.technique,
            },
        )
        self._store.append_events([event])

        return {
            "cila_level": ctx.cila_level,
            "technique": ctx.technique,
            "event_id": event.event_id,
            "saga_status": result.status.value,
        }

    def get_route_events(self) -> list[DomainEvent]:
        """Return all persisted routing events.

        Returns:
            List of DomainEvents with event_type='prompt_routed'.
        """
        return self._store.get_stream("cila_router")

    def replay_classifications(self) -> list[int]:
        """Replay all routing decisions, returning CILA levels in order.

        Returns:
            List of integer CILA levels in chronological order.
        """
        return [int(e.payload.get("cila_level", 0)) for e in self.get_route_events()]
