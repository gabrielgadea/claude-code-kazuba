"""Reward Calculator - Compute RL rewards from ESAA events.

Maps ESAA event outcomes to numerical rewards for Q-learning.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from claude_code_kazuba.models.esaa_types import ESAAEventEnvelope, RiskLevel


class Outcome(Enum):
    """Event outcome classification."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class RewardBreakdown:
    """Detailed reward calculation."""

    base_reward: float
    risk_multiplier: float
    time_factor: float
    complexity_bonus: float
    verification_bonus: float
    total: float


class RewardCalculator:
    """Calculate RL rewards from ESAA events."""

    # Base rewards
    BASE_SUCCESS = 1.0
    BASE_FAILURE = -1.0
    BASE_PARTIAL = 0.3
    BASE_TIMEOUT = -0.5
    BASE_BLOCKED = 0.0

    # Risk multipliers (higher risk = higher potential reward/penalty)
    RISK_MULTIPLIERS = {
        RiskLevel.LOW: 1.0,
        RiskLevel.MEDIUM: 1.5,
        RiskLevel.HIGH: 2.0,
        RiskLevel.CRITICAL: 3.0,
    }

    # CILA complexity bonuses
    CILA_BONUSES = {
        "L0": 0.0,
        "L1": 0.1,
        "L2": 0.2,
        "L3": 0.3,
        "L4": 0.5,
        "L5": 0.8,
        "L6": 1.0,
    }

    @classmethod
    def from_event(cls, event: ESAAEventEnvelope) -> float:
        """Calculate total reward for an event."""
        breakdown = cls.calculate_breakdown(event)
        return breakdown.total

    @classmethod
    def calculate_breakdown(cls, event: ESAAEventEnvelope) -> RewardBreakdown:
        """Calculate detailed reward breakdown."""
        cognitive = event.command.cognitive_state

        # Determine outcome from action
        outcome = cls._infer_outcome(event)

        # Base reward
        base = cls._base_for_outcome(outcome)

        # Risk multiplier
        risk_mult = cls.RISK_MULTIPLIERS.get(cognitive.risk_assessment, 1.0)

        # Time factor (placeholder - would use actual duration)
        time_factor = 1.0

        # Complexity bonus
        cila_str = cognitive.cila_context.value
        complexity = cls.CILA_BONUSES.get(cila_str, 0.0)

        # Verification bonus (would check if verification passed)
        verification = 0.0

        # Calculate total
        total = (base * risk_mult * time_factor) + complexity + verification

        return RewardBreakdown(
            base_reward=base,
            risk_multiplier=risk_mult,
            time_factor=time_factor,
            complexity_bonus=complexity,
            verification_bonus=verification,
            total=round(total, 4),
        )

    @classmethod
    def _infer_outcome(cls, event: ESAAEventEnvelope) -> Outcome:
        """Infer outcome from event data."""
        intention = event.command.cognitive_state.intention.lower()

        # Check for failure indicators
        if any(x in intention for x in ["fail", "error", "rejected", "timeout"]):
            if "timeout" in intention:
                return Outcome.TIMEOUT
            return Outcome.FAILURE

        # Check for success indicators
        if any(x in intention for x in ["ok", "success", "complete", "pass"]):
            return Outcome.SUCCESS

        # Default to success for completed operations
        return Outcome.SUCCESS

    @classmethod
    def _base_for_outcome(cls, outcome: Outcome) -> float:
        """Get base reward for outcome."""
        return {
            Outcome.SUCCESS: cls.BASE_SUCCESS,
            Outcome.FAILURE: cls.BASE_FAILURE,
            Outcome.PARTIAL: cls.BASE_PARTIAL,
            Outcome.TIMEOUT: cls.BASE_TIMEOUT,
            Outcome.BLOCKED: cls.BASE_BLOCKED,
        }.get(outcome, 0.0)

    @classmethod
    def from_action_result(
        cls,
        action: str,
        success: bool,
        duration_ms: float,
        risk_level: RiskLevel = RiskLevel.LOW,
    ) -> float:
        """Calculate reward from action result."""
        base = cls.BASE_SUCCESS if success else cls.BASE_FAILURE

        # Time penalty for slow operations (>5s)
        time_factor = 1.0
        if duration_ms > 5000:
            time_factor = 0.8
        elif duration_ms > 10000:
            time_factor = 0.5

        risk_mult = cls.RISK_MULTIPLIERS.get(risk_level, 1.0)

        return round(base * risk_mult * time_factor, 4)
