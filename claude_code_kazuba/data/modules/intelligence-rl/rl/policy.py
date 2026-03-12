"""Epsilon-Greedy Policy with decay.

Implements exploration vs exploitation tradeoff.
Uses Rust kernel for vectorized operations when available.
"""

import random
import threading
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..core.config import LearningConfig
from ..core.models import RLAction, RLState
from .action import ActionSelector

# Try to import Rust kernel
try:
    from kazuba_rust_core.learning import RustEpsilonGreedyPolicy

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False


class EpsilonGreedyPolicy:
    """Epsilon-greedy policy with exponential decay.

    Balances exploration (random actions) and exploitation
    (best known actions) with decaying exploration rate.
    """

    def __init__(
        self,
        config: LearningConfig,
        action_selector: ActionSelector | None = None,
    ) -> None:
        self._config = config
        self._action_selector = action_selector or ActionSelector()
        self._lock = threading.RLock()

        self._epsilon = config.epsilon_initial
        self._episode_count = 0

        if RUST_AVAILABLE:
            self._rust_policy = RustEpsilonGreedyPolicy(
                config.epsilon_initial,
                config.epsilon_decay,
                config.epsilon_min,
            )
            self._use_rust = True
        else:
            self._use_rust = False

    @property
    def epsilon(self) -> float:
        """Current exploration rate."""
        with self._lock:
            return self._epsilon

    def select_action(
        self,
        state: RLState,
        q_values: dict[RLAction, float],
    ) -> RLAction:
        """Select action using epsilon-greedy policy.

        Args:
            state: Current state
            q_values: Q-values for each action

        Returns:
            Selected action
        """
        with self._lock:
            valid_actions = self._action_selector.get_valid_actions(state)

            if not valid_actions:
                return RLAction.SKIP

            # Exploration: random action
            if random.random() < self._epsilon:
                return random.choice(valid_actions)

            # Exploitation: best Q-value among valid actions
            best_action = max(
                valid_actions,
                key=lambda a: q_values.get(a, 0.0),
            )

            return best_action

    def select_action_vectorized(
        self,
        state: RLState,
        q_values: NDArray[np.float32],
        action_mask: NDArray[np.bool_] | None = None,
    ) -> int:
        """Select action using vectorized Q-values.

        Args:
            state: Current state
            q_values: Q-value array (shape: [num_actions])
            action_mask: Boolean mask for valid actions

        Returns:
            Action index
        """
        with self._lock:
            if self._use_rust:
                return self._rust_policy.select_action(
                    q_values,
                    action_mask,
                    self._epsilon,
                )

            # Python fallback
            valid_indices = np.where(action_mask)[0] if action_mask is not None else np.arange(len(q_values))

            if len(valid_indices) == 0:
                return self._action_selector.get_action_index(RLAction.SKIP)

            # Exploration
            if random.random() < self._epsilon:
                return int(random.choice(valid_indices))

            # Exploitation
            valid_q_values = q_values[valid_indices]
            best_idx = valid_indices[np.argmax(valid_q_values)]

            return int(best_idx)

    def decay_epsilon(self) -> float:
        """Apply epsilon decay after episode.

        Returns:
            New epsilon value
        """
        with self._lock:
            self._episode_count += 1
            self._epsilon = max(
                self._config.epsilon_min,
                self._epsilon * self._config.epsilon_decay,
            )

            if self._use_rust:
                self._rust_policy.decay()

            return self._epsilon

    def reset(self) -> None:
        """Reset epsilon to initial value."""
        with self._lock:
            self._epsilon = self._config.epsilon_initial
            self._episode_count = 0

            if self._use_rust:
                self._rust_policy.reset()

    def get_action_probabilities(
        self,
        state: RLState,
        q_values: dict[RLAction, float],
    ) -> dict[RLAction, float]:
        """Get probability distribution over actions.

        Args:
            state: Current state
            q_values: Q-values for each action

        Returns:
            Dict mapping actions to probabilities
        """
        valid_actions = self._action_selector.get_valid_actions(state)

        if not valid_actions:
            return {RLAction.SKIP: 1.0}

        # Find greedy action
        best_action = max(valid_actions, key=lambda a: q_values.get(a, 0.0))

        # Calculate probabilities
        explore_prob = self._epsilon / len(valid_actions)
        exploit_prob = 1.0 - self._epsilon

        probs: dict[RLAction, float] = {}
        for action in valid_actions:
            if action == best_action:
                probs[action] = exploit_prob + explore_prob
            else:
                probs[action] = explore_prob

        return probs

    def stats(self) -> dict[str, Any]:
        """Get policy statistics."""
        with self._lock:
            return {
                "epsilon": self._epsilon,
                "epsilon_initial": self._config.epsilon_initial,
                "epsilon_min": self._config.epsilon_min,
                "decay_rate": self._config.epsilon_decay,
                "episode_count": self._episode_count,
                "using_rust": self._use_rust,
            }
