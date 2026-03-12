"""Multi-objective reward function for RL.

Balances multiple objectives:
- Task success
- Token efficiency
- User satisfaction
- Quality score
"""

from dataclasses import dataclass

from ..core.models import ExecutionOutcome, RLAction


@dataclass(frozen=True)
class RewardComponents:
    """Components of the reward signal."""

    success_reward: float
    quality_reward: float
    efficiency_reward: float
    feedback_reward: float
    penalty: float
    total: float


class RewardCalculator:
    """Multi-objective reward calculator.

    Combines multiple reward signals with configurable weights.
    """

    def __init__(
        self,
        success_weight: float = 0.4,
        quality_weight: float = 0.3,
        efficiency_weight: float = 0.2,
        feedback_weight: float = 0.1,
    ) -> None:
        self._success_weight = success_weight
        self._quality_weight = quality_weight
        self._efficiency_weight = efficiency_weight
        self._feedback_weight = feedback_weight

        # Token costs for efficiency calculation
        self._action_token_costs = {
            RLAction.USE_LOCAL_CACHE: 0,
            RLAction.QUERY_CIPHER_MCP: 800,
            RLAction.ACTIVATE_SKILL: 500,
            RLAction.APPLY_PATTERN: 100,
            RLAction.STORE_LESSON: 200,
            RLAction.CONSOLIDATE_PATTERNS: 300,
            RLAction.SKIP: 0,
        }

    def calculate(
        self,
        outcome: ExecutionOutcome,
        action: RLAction,
        tokens_used: int = 0,
    ) -> RewardComponents:
        """Calculate reward for action outcome.

        Args:
            outcome: Execution outcome
            action: Action taken
            tokens_used: Actual tokens used (if known)

        Returns:
            RewardComponents with breakdown and total
        """
        # Success reward: 1.0 for success, -0.5 for failure
        success_reward = 1.0 if outcome.success else -0.5

        # Quality reward: 0-1 based on quality score
        quality_reward = outcome.quality_score or 0.5

        # Efficiency reward: Penalize high token usage
        base_cost = self._action_token_costs.get(action, 500)
        actual_cost = tokens_used or base_cost
        efficiency_reward = self._calculate_efficiency(actual_cost)

        # Feedback reward: -1, 0, or 1 based on user feedback
        feedback_reward = float(outcome.user_feedback)

        # Penalties
        penalty = 0.0
        if outcome.had_errors:
            penalty -= 0.2
        if outcome.exceeded_timeout:
            penalty -= 0.3

        # Calculate weighted total
        total = (
            self._success_weight * success_reward
            + self._quality_weight * quality_reward
            + self._efficiency_weight * efficiency_reward
            + self._feedback_weight * feedback_reward
            + penalty
        )

        # Clip to [-1, 1]
        total = max(-1.0, min(1.0, total))

        return RewardComponents(
            success_reward=success_reward,
            quality_reward=quality_reward,
            efficiency_reward=efficiency_reward,
            feedback_reward=feedback_reward,
            penalty=penalty,
            total=total,
        )

    def _calculate_efficiency(self, tokens: int) -> float:
        """Calculate efficiency reward based on token usage.

        Args:
            tokens: Tokens used

        Returns:
            Efficiency reward (0-1)
        """
        # Target: 0 tokens = 1.0, 1000+ tokens = 0.0
        if tokens <= 0:
            return 1.0
        if tokens >= 1000:
            return 0.0

        return 1.0 - (tokens / 1000.0)

    def calculate_simple(
        self,
        success: bool,
        tokens_used: int = 0,
    ) -> float:
        """Calculate simple reward for quick evaluations.

        Args:
            success: Whether action succeeded
            tokens_used: Tokens consumed

        Returns:
            Simple reward value
        """
        base = 1.0 if success else -0.5
        efficiency_bonus = self._calculate_efficiency(tokens_used) * 0.2

        return base + efficiency_bonus

    def get_optimal_action_bias(self, action: RLAction) -> float:
        """Get bias toward token-efficient actions.

        Used to encourage exploration of efficient actions.

        Args:
            action: Action to evaluate

        Returns:
            Bias value (higher = more encouraged)
        """
        # Encourage local cache usage (0 tokens)
        if action == RLAction.USE_LOCAL_CACHE:
            return 0.1
        if action == RLAction.SKIP:
            return 0.0
        if action == RLAction.QUERY_CIPHER_MCP:
            return -0.05  # Slight penalty for token usage

        return 0.0
