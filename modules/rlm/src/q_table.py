"""Persistent Q-table with TD(λ) eligibility traces."""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Separator used to encode (state, action) key pairs as a single string
_KEY_SEP = "\x00"
_TRACE_THRESHOLD = 1e-4


class QTable:
    """Q-table with persistence, eligibility traces, and bounded size.

    Implements TD(λ) updates (SARSA-style or Q-learning):

        δ = r + γ * Q(s', a') - Q(s, a)
        e(s, a) = 1   (replacing traces)
        Q(s, a) += α * δ * e(s, a)  for all (s, a) with e > threshold
        e(s, a) *= γλ

    Thread-safe via a reentrant lock.

    Args:
        learning_rate: Alpha (α) — step size for Q-value updates.
        discount_factor: Gamma (γ) — future reward discount.
        lambda_trace: Lambda (λ) — eligibility trace decay.
        max_size: Maximum number of (state, action) entries to retain.
        persist_path: Optional path for JSON persistence.
        auto_save_interval: Persist every N updates (0 = disabled).
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        lambda_trace: float = 0.8,
        max_size: int = 10_000,
        persist_path: Path | None = None,
        auto_save_interval: int = 100,
    ) -> None:
        self._alpha = float(learning_rate)
        self._gamma = float(discount_factor)
        self._lambda = float(lambda_trace)
        self._max_size = max_size
        self._persist_path = persist_path
        self._auto_save_interval = auto_save_interval

        # Core data structures
        self._q: dict[str, float] = {}
        self._traces: dict[str, float] = {}
        self._update_count: int = 0

        self._lock = threading.RLock()

        # Load from disk if path provided
        if persist_path is not None and persist_path.exists():
            self._load(persist_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, state: str, action: str) -> float:
        """Return Q-value for (state, action); 0.0 if unseen."""
        key = _encode(state, action)
        with self._lock:
            return self._q.get(key, 0.0)

    def set(self, state: str, action: str, value: float) -> None:
        """Directly set a Q-value without TD update logic."""
        key = _encode(state, action)
        with self._lock:
            self._q[key] = value
            self._enforce_max_size()

    def update(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        next_action: str | None = None,
    ) -> dict[str, float]:
        """Perform a TD(λ) update step.

        Args:
            state: Current state identifier.
            action: Action taken.
            reward: Observed reward.
            next_state: State transitioned to.
            next_action: If provided, use SARSA update; else greedy (Q-learning).

        Returns:
            Dict with keys: new_q_value, td_error, states_updated.
        """
        with self._lock:
            current_key = _encode(state, action)
            current_q = self._q.get(current_key, 0.0)

            # Next Q-value: SARSA or greedy
            if next_action is not None:
                next_q = self._q.get(_encode(next_state, next_action), 0.0)
            else:
                next_q = self._max_q(next_state)

            # TD error
            td_error = reward + self._gamma * next_q - current_q

            # Replacing trace for current pair
            self._traces[current_key] = 1.0

            # Update all entries with active traces
            active = [k for k, v in self._traces.items() if v > _TRACE_THRESHOLD]
            states_updated = 0
            for key in active:
                trace_val = self._traces[key]
                self._q[key] = self._q.get(key, 0.0) + self._alpha * td_error * trace_val
                states_updated += 1

            # Decay traces
            for key in list(self._traces.keys()):
                self._traces[key] *= self._gamma * self._lambda

            # Prune tiny traces
            self._traces = {k: v for k, v in self._traces.items() if v > _TRACE_THRESHOLD}

            self._enforce_max_size()
            self._update_count += 1

            new_q = self._q.get(current_key, 0.0)

            # Auto-save
            if (
                self._auto_save_interval > 0
                and self._update_count % self._auto_save_interval == 0
                and self._persist_path is not None
            ):
                try:
                    self._save(self._persist_path)
                except Exception:  # noqa: BLE001
                    logger.warning("Auto-save failed", exc_info=True)

            return {
                "new_q_value": new_q,
                "td_error": td_error,
                "states_updated": float(states_updated),
            }

    def reset_traces(self) -> None:
        """Clear eligibility traces (call at episode boundary)."""
        with self._lock:
            self._traces.clear()

    def best_action(self, state: str) -> str | None:
        """Return the greedy best action for a state (highest Q-value).

        Returns:
            Action string, or None if no actions known for the state.
        """
        with self._lock:
            prefix = state + _KEY_SEP
            best_key: str | None = None
            best_val = float("-inf")
            for key, val in self._q.items():
                if key.startswith(prefix) and val > best_val:
                    best_val = val
                    best_key = key
            if best_key is None:
                return None
            _, action = _decode(best_key)
            return action

    def max_q(self, state: str) -> float:
        """Return the maximum Q-value for a state (0.0 if unknown)."""
        with self._lock:
            return self._max_q(state)

    def actions_for_state(self, state: str) -> list[str]:
        """Return all known actions for a state."""
        with self._lock:
            prefix = state + _KEY_SEP
            return [_decode(k)[1] for k in self._q if k.startswith(prefix)]

    def size(self) -> int:
        """Number of (state, action) entries in the table."""
        with self._lock:
            return len(self._q)

    def update_count(self) -> int:
        """Total number of TD updates applied since creation."""
        with self._lock:
            return self._update_count

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path | None = None) -> Path | None:
        """Save Q-table to JSON.

        Args:
            path: Target file path. Falls back to ``persist_path`` if None.

        Returns:
            The path written to, or None if no path configured.
        """
        target = path or self._persist_path
        if target is None:
            return None
        with self._lock:
            self._save(target)
        return target

    def load(self, path: Path) -> None:
        """Load Q-table from JSON.

        Args:
            path: Source JSON file.

        Raises:
            FileNotFoundError: If path does not exist.
        """
        with self._lock:
            self._load(path)

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export(self) -> dict[str, float]:
        """Export Q-table as a flat dict keyed by ``state|action`` strings."""
        with self._lock:
            result: dict[str, float] = {}
            for key, val in self._q.items():
                state, action = _decode(key)
                result[f"{state}|{action}"] = val
            return result

    def import_data(self, data: dict[str, float]) -> None:
        """Import Q-values from a flat dict keyed by ``state|action`` strings.

        Merges with existing data; duplicate keys are overwritten.
        """
        with self._lock:
            for compound_key, value in data.items():
                parts = compound_key.split("|", 1)
                if len(parts) == 2:
                    key = _encode(parts[0], parts[1])
                    self._q[key] = value
            self._enforce_max_size()

    def to_dict(self) -> dict[str, Any]:
        """Serialize full table state for checkpointing."""
        with self._lock:
            return {
                "q_table": {k: v for k, v in self._q.items()},
                "alpha": self._alpha,
                "gamma": self._gamma,
                "lambda": self._lambda,
                "max_size": self._max_size,
                "update_count": self._update_count,
                "saved_at": time.time(),
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QTable:
        """Reconstruct QTable from a serialized dict."""
        table = cls(
            learning_rate=data.get("alpha", 0.1),
            discount_factor=data.get("gamma", 0.95),
            lambda_trace=data.get("lambda", 0.8),
            max_size=data.get("max_size", 10_000),
        )
        table._q = dict(data.get("q_table", {}))
        table._update_count = data.get("update_count", 0)
        return table

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _max_q(self, state: str) -> float:
        """Return max Q(state, *) without lock (caller must hold lock)."""
        prefix = state + _KEY_SEP
        values = [v for k, v in self._q.items() if k.startswith(prefix)]
        return max(values, default=0.0)

    def _enforce_max_size(self) -> None:
        """Evict lowest-value entries when Q-table exceeds max_size."""
        excess = len(self._q) - self._max_size
        if excess <= 0:
            return
        # Sort by absolute value ascending (low-magnitude = less useful)
        sorted_keys = sorted(self._q.keys(), key=lambda k: abs(self._q[k]))
        for key in sorted_keys[:excess]:
            del self._q[key]

    def _save(self, path: Path) -> None:
        """Serialize Q-table to JSON (must be called under lock)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Q-table saved to %s (%d entries)", path, len(self._q))

    def _load(self, path: Path) -> None:
        """Deserialize Q-table from JSON (must be called under lock)."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._q = dict(raw.get("q_table", {}))
        if "alpha" in raw:
            self._alpha = raw["alpha"]
        if "gamma" in raw:
            self._gamma = raw["gamma"]
        if "lambda" in raw:
            self._lambda = raw["lambda"]
        self._update_count = raw.get("update_count", 0)
        logger.debug("Q-table loaded from %s (%d entries)", path, len(self._q))


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _encode(state: str, action: str) -> str:
    """Encode (state, action) pair as a single string key."""
    return state + _KEY_SEP + action


def _decode(key: str) -> tuple[str, str]:
    """Decode a compound key back to (state, action)."""
    parts = key.split(_KEY_SEP, 1)
    if len(parts) != 2:
        return key, ""
    return parts[0], parts[1]
