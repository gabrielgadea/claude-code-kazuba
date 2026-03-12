"""D2 — Ghost Projections for parallel hypothesis evaluation (MCTS-inspired).

Runs N async hypothesis functions concurrently against ephemeral in-memory
event stores, scores each resulting AgentState, and returns the
highest-scoring (index, state) pair — with zero side effects on the real store.

Design:
    Each hypothesis is a zero-argument async callable returning an AgentState.
    Hypotheses bind their own isolated context (ghost store) via closures.
    The GhostProjector caps evaluation at ``max_simulations`` to bound cost.

Usage::

    projector = GhostProjector(real_store)
    idx, best_state = await projector.project(hypothesis_list, scorer)
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from scripts.aco.esaa.cqrs_read_model import AgentState
from scripts.aco.esaa.sqlite_backend import SQLiteEventStore

# Type aliases for readability
HypothesisFn = Callable[[], Coroutine[Any, Any, AgentState]]
ScorerFn = Callable[[AgentState], float]


async def _safe_run(h: HypothesisFn) -> AgentState:
    """Run a hypothesis, returning a fallback state on any exception.

    Args:
        h: Zero-arg async callable returning AgentState.

    Returns:
        AgentState from the hypothesis, or a ghost-failed fallback.
    """
    try:
        return await h()
    except Exception:
        return AgentState(agent_id="ghost-failed")


class GhostProjector:
    """Parallel Monte-Carlo hypothesis evaluator with isolated ghost stores.

    Each hypothesis executes in its own context with no side effects on
    the primary store. Useful for evaluating competing generator strategies
    before committing to a code change.

    Args:
        store: Primary event store (read-only reference; never written to).
        max_simulations: Hard cap on the number of hypotheses evaluated.
    """

    def __init__(
        self,
        store: SQLiteEventStore,
        max_simulations: int = 50,
    ) -> None:
        self._store = store
        self._max_simulations = max_simulations

    async def project(
        self,
        hypotheses: list[HypothesisFn],
        scorer: ScorerFn,
    ) -> tuple[int, AgentState]:
        """Evaluate hypotheses in parallel and return the best.

        Args:
            hypotheses: List of zero-arg async callables returning AgentState.
            scorer: Function mapping AgentState → float (higher = better).

        Returns:
            Tuple ``(index, AgentState)`` of the highest-scoring hypothesis.

        Raises:
            ValueError: If ``hypotheses`` is empty.
        """
        if not hypotheses:
            raise ValueError("hypotheses list must not be empty")
        limited = hypotheses[: self._max_simulations]
        results = await self._run_parallel(limited)
        return self._select_best(results, scorer)

    async def _run_parallel(
        self,
        hypotheses: list[HypothesisFn],
    ) -> list[AgentState]:
        """Run all hypotheses concurrently and collect their states.

        Args:
            hypotheses: Bounded list of hypothesis callables.

        Returns:
            List of AgentState results in hypothesis order.
        """
        return list(await asyncio.gather(*(_safe_run(h) for h in hypotheses)))

    def _select_best(
        self,
        results: list[AgentState],
        scorer: ScorerFn,
    ) -> tuple[int, AgentState]:
        """Pick the highest-scoring result from a list of states.

        Args:
            results: Ordered list of AgentState outcomes.
            scorer: Scoring function.

        Returns:
            ``(best_index, best_state)`` pair.
        """
        scores = [scorer(r) for r in results]
        best_idx = max(range(len(scores)), key=lambda i: scores[i])
        return best_idx, results[best_idx]
