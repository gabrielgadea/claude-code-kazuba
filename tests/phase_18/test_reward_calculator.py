"""Tests for modules/rlm/src/reward_calculator.py — RewardCalculator."""

from __future__ import annotations

import pytest

from claude_code_kazuba.data.modules.rlm.src.reward_calculator import RewardCalculator, RewardComponent

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_empty_calculator_returns_zero() -> None:
    calc = RewardCalculator()
    assert calc.compute({"any_metric": 1.0}) == 0.0


def test_single_component_at_target_returns_positive() -> None:
    comp = RewardComponent(metric_key="accuracy", weight=1.0, target=1.0, scale=0.1)
    calc = RewardCalculator(components=[comp])
    reward = calc.compute({"accuracy": 1.0})
    assert reward > 0.0


def test_negative_weight_component() -> None:
    comp = RewardComponent(metric_key="latency", weight=-1.0, target=10.0, scale=5.0)
    calc = RewardCalculator(components=[comp])
    # High latency = bad
    reward = calc.compute({"latency": 100.0})
    assert reward < 0.0


def test_missing_metric_contributes_zero() -> None:
    comp = RewardComponent(metric_key="missing_key", weight=1.0, target=1.0, scale=0.1)
    calc = RewardCalculator(components=[comp])
    reward = calc.compute({"other_key": 0.5})
    assert reward == pytest.approx(0.0)


def test_reward_clipping_max() -> None:
    comp = RewardComponent(metric_key="m", weight=100.0, target=1.0, scale=0.001)
    calc = RewardCalculator(components=[comp], clip_max=1.0)
    reward = calc.compute({"m": 1.0})
    assert reward <= 1.0


def test_reward_clipping_min() -> None:
    comp = RewardComponent(metric_key="m", weight=-100.0, target=0.0, scale=0.001)
    calc = RewardCalculator(components=[comp], clip_min=-1.0)
    reward = calc.compute({"m": 0.0})
    assert reward >= -1.0


def test_breakdown_contains_expected_keys() -> None:
    comp = RewardComponent(metric_key="acc", weight=1.0, target=1.0, scale=0.2)
    calc = RewardCalculator(components=[comp])
    breakdown = calc.compute_breakdown({"acc": 0.9})
    assert "total" in breakdown
    assert "raw_total" in breakdown
    assert "components" in breakdown
    assert len(breakdown["components"]) == 1


def test_add_component_at_runtime() -> None:
    calc = RewardCalculator()
    calc.add_component(RewardComponent(metric_key="speed", weight=1.0, target=100.0, scale=10.0))
    assert len(calc.components) == 1


def test_remove_component() -> None:
    comp = RewardComponent(metric_key="speed", weight=1.0, target=100.0, scale=10.0)
    calc = RewardCalculator(components=[comp])
    removed = calc.remove_component("speed")
    assert removed is True
    assert len(calc.components) == 0


def test_serialization_roundtrip() -> None:
    comp = RewardComponent(metric_key="acc", weight=0.8, target=1.0, scale=0.1)
    calc = RewardCalculator(components=[comp], clip_min=-0.5, clip_max=0.5)
    data = calc.to_dict()
    restored = RewardCalculator.from_dict(data)
    assert len(restored.components) == 1
    assert restored.clip_range == (-0.5, 0.5)


def test_invalid_clip_range_raises() -> None:
    with pytest.raises(ValueError):
        RewardCalculator(clip_min=1.0, clip_max=0.0)
