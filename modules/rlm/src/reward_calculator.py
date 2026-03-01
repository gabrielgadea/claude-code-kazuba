"""Performance-based reward calculator for RLM."""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, Field


class RewardComponent(BaseModel, frozen=True):
    """A single weighted metric contributing to the composite reward."""

    metric_key: str = Field(description="Key name in the metrics dict")
    weight: float = Field(default=1.0, description="Contribution weight (can be negative)")
    target: float = Field(default=1.0, description="Ideal value (reward peaks at this)")
    scale: float = Field(
        default=1.0,
        gt=0.0,
        description="Width of the Gaussian reward curve around target",
    )

    def compute(self, metrics: dict[str, float]) -> float:
        """Compute this component's contribution from the metrics dict.

        Uses a Gaussian (bell-curve) similarity centered at ``target``:
            component = weight * exp(-(value - target)^2 / (2 * scale^2))

        Missing metrics contribute 0.0 to this component.

        Args:
            metrics: Dict of metric names to observed values.

        Returns:
            Weighted scalar contribution.
        """
        value = metrics.get(self.metric_key)
        if value is None:
            return 0.0
        if not math.isfinite(value):
            return 0.0
        diff = value - self.target
        gaussian = math.exp(-(diff**2) / (2.0 * self.scale**2))
        return self.weight * gaussian


class RewardCalculator:
    """Compute composite scalar rewards from performance metrics.

    Supports arbitrary weighted components with optional clipping.

    Example::

        calc = RewardCalculator(
            components=[
                RewardComponent(metric_key="latency_ms", weight=-0.5, target=50, scale=20),
                RewardComponent(metric_key="accuracy", weight=1.0, target=1.0, scale=0.1),
            ],
            clip_min=-1.0,
            clip_max=1.0,
        )
        reward = calc.compute({"latency_ms": 60.0, "accuracy": 0.95})

    Args:
        components: List of ``RewardComponent`` objects (empty = always 0.0).
        clip_min: Minimum clipped reward value.
        clip_max: Maximum clipped reward value.
    """

    def __init__(
        self,
        components: list[RewardComponent] | None = None,
        clip_min: float = -1.0,
        clip_max: float = 1.0,
    ) -> None:
        if clip_min >= clip_max:
            msg = f"clip_min ({clip_min}) must be < clip_max ({clip_max})"
            raise ValueError(msg)
        self._components = list(components or [])
        self._clip_min = clip_min
        self._clip_max = clip_max

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def compute(self, metrics: dict[str, float]) -> float:
        """Compute the composite reward for the given metrics.

        Sums all component contributions and clips to [clip_min, clip_max].

        Args:
            metrics: Dict of metric name -> observed float value.

        Returns:
            Clipped composite reward in [clip_min, clip_max].
        """
        if not self._components:
            return 0.0

        total = sum(c.compute(metrics) for c in self._components)

        # Normalize if total weight > 1.0 to keep in reasonable range
        total_weight = sum(abs(c.weight) for c in self._components)
        if total_weight > 0.0:
            total = total / total_weight

        return max(self._clip_min, min(self._clip_max, total))

    def compute_breakdown(self, metrics: dict[str, float]) -> dict[str, Any]:
        """Compute reward and return per-component breakdown.

        Args:
            metrics: Dict of metric name -> observed float value.

        Returns:
            Dict with keys:
                - ``total``: Final clipped reward.
                - ``raw_total``: Sum before normalization and clipping.
                - ``components``: List of per-component dicts.
        """
        contributions: list[dict[str, Any]] = []
        raw_total = 0.0

        for comp in self._components:
            value = metrics.get(comp.metric_key)
            contribution = comp.compute(metrics)
            raw_total += contribution
            contributions.append(
                {
                    "metric": comp.metric_key,
                    "observed": value,
                    "weight": comp.weight,
                    "contribution": round(contribution, 6),
                }
            )

        total_weight = sum(abs(c.weight) for c in self._components)
        normalized = raw_total / total_weight if total_weight > 0.0 else 0.0
        clipped = max(self._clip_min, min(self._clip_max, normalized))

        return {
            "total": round(clipped, 6),
            "raw_total": round(raw_total, 6),
            "normalized": round(normalized, 6),
            "components": contributions,
        }

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def add_component(self, component: RewardComponent) -> None:
        """Add a new component to the calculator.

        Args:
            component: The ``RewardComponent`` to append.
        """
        self._components.append(component)

    def remove_component(self, metric_key: str) -> bool:
        """Remove all components matching the given metric key.

        Args:
            metric_key: The key to remove.

        Returns:
            True if at least one component was removed.
        """
        before = len(self._components)
        self._components = [c for c in self._components if c.metric_key != metric_key]
        return len(self._components) < before

    @property
    def components(self) -> list[RewardComponent]:
        """Return current list of reward components (read-only copy)."""
        return list(self._components)

    @property
    def clip_range(self) -> tuple[float, float]:
        """Return (clip_min, clip_max)."""
        return (self._clip_min, self._clip_max)

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def simple(cls, metric_key: str, weight: float = 1.0) -> RewardCalculator:
        """Create a single-metric linear calculator.

        The reward equals ``weight * metrics[metric_key]``, clipped.

        Args:
            metric_key: Metric to use.
            weight: Scalar multiplier.

        Returns:
            A ``RewardCalculator`` with one linear component.
        """
        # Use very large scale so Gaussian ≈ linear for typical metric values
        comp = RewardComponent(metric_key=metric_key, weight=weight, target=1.0, scale=1e6)
        return cls(components=[comp])

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "clip_min": self._clip_min,
            "clip_max": self._clip_max,
            "components": [c.model_dump() for c in self._components],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RewardCalculator:
        """Deserialize from plain dict."""
        components = [RewardComponent(**c) for c in data.get("components", [])]
        return cls(
            components=components,
            clip_min=data.get("clip_min", -1.0),
            clip_max=data.get("clip_max", 1.0),
        )
