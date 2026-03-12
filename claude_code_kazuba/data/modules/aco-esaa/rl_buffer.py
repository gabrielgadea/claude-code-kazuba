"""D1 — Offline RL Buffer for ACO cognitive event streams.

Accumulates KazubaCognitiveEvent instances in a bounded deque and applies
Bellman Q-table updates offline, enabling agents to improve decision quality
across sessions without requiring an online interaction loop.

State-action key: ``"{cila_level}:{technique}"`` — compact identifier derived
from each event's CognitiveTrace.

Q-update rule (Bellman):
    Q(s,a) ← Q(s,a) + α * (r + γ * max_Q(s') - Q(s,a))

where:
    - r = float(q_value_estimate) from CognitiveTrace
    - γ = discount factor (configurable, default 0.95)
    - α = learning rate (module constant 0.1)
    - max_Q(s') = best known Q for the next state (defaults to 1.0 if unknown)

CLI::

    python -m scripts.aco.esaa.rl_buffer --help
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any

from scripts.aco.esaa.cognitive_event import KazubaCognitiveEvent

_ALPHA: float = 0.1  # learning rate
_MAX_Q_DEFAULT: float = 1.0  # optimistic bootstrap for unknown next states


def _state_key(event: KazubaCognitiveEvent) -> str:
    """Derive a compact state-action key from a cognitive event.

    Args:
        event: KazubaCognitiveEvent to derive the key from.

    Returns:
        String key in format ``"{cila_level}:{technique}"``.
    """
    trace = event.cognitive_trace
    return f"{trace.cila_level}:{trace.technique}"


def _reward(event: KazubaCognitiveEvent) -> float:
    """Extract the scalar reward signal from a cognitive event.

    Args:
        event: KazubaCognitiveEvent whose Q-value estimate is the reward.

    Returns:
        Float reward (converted from Decimal for arithmetic).
    """
    return float(event.cognitive_trace.q_value_estimate)


class OfflineRLBuffer:
    """Bounded offline RL buffer with Bellman Q-table updates.

    Args:
        capacity: Maximum events to retain (FIFO eviction when full).
        gamma: Discount factor γ for future rewards [0.0, 1.0].
    """

    def __init__(self, capacity: int = 10_000, gamma: float = 0.95) -> None:
        self._buffer: deque[KazubaCognitiveEvent] = deque(maxlen=capacity)
        self._gamma = gamma
        self._q_table: dict[str, float] = {}

    def add(self, event: KazubaCognitiveEvent) -> None:
        """Append an event to the buffer (FIFO eviction at capacity).

        Args:
            event: Cognitive event to record.
        """
        self._buffer.append(event)

    def sample(self, batch_size: int) -> list[KazubaCognitiveEvent]:
        """Random sample without replacement (capped at buffer size).

        Args:
            batch_size: Desired sample count.

        Returns:
            List of at most ``min(batch_size, len(buffer))`` events.
        """
        buf = list(self._buffer)
        k = min(batch_size, len(buf))
        return random.sample(buf, k) if k > 0 else []

    def update_q_table(self) -> dict[str, float]:
        """Apply Bellman updates over the entire buffer.

        Iterates all consecutive (t, t+1) pairs and updates Q(s,a) via the
        Bellman equation with learning rate _ALPHA.

        Returns:
            Copy of the Q-table after updates.
        """
        events = list(self._buffer)
        for i, ev in enumerate(events):
            nxt = events[i + 1] if i + 1 < len(events) else None
            self._apply_bellman(ev, nxt)
        return dict(self._q_table)

    def _apply_bellman(
        self,
        current: KazubaCognitiveEvent,
        nxt: KazubaCognitiveEvent | None,
    ) -> None:
        """Single Bellman update for a (s, a, r, s') tuple.

        Args:
            current: Current event (defines state-action key and reward).
            nxt: Next event (defines next state; None at end of stream).
        """
        key = _state_key(current)
        r = _reward(current)
        q_cur = self._q_table.get(key, 0.0)
        max_q_next = self._best_q(_state_key(nxt)) if nxt is not None else 0.0
        self._q_table[key] = q_cur + _ALPHA * (r + self._gamma * max_q_next - q_cur)

    def _best_q(self, key: str) -> float:
        """Best known Q-value for a state-action key.

        Args:
            key: State-action key.

        Returns:
            Known Q-value or optimistic default (_MAX_Q_DEFAULT).
        """
        return self._q_table.get(key, _MAX_Q_DEFAULT)

    def export_policy(self) -> dict[str, Any]:
        """Export Q-table and buffer statistics for persistence.

        Returns:
            Dict with ``q_table``, ``buffer_size``, and ``gamma``.
        """
        return {
            "q_table": dict(self._q_table),
            "buffer_size": len(self._buffer),
            "gamma": self._gamma,
        }
