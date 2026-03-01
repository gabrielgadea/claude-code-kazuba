"""Tests for AgentTrigger and TriggerRegistry — Phase 14."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from claude_code_kazuba.config import AgentTrigger, TriggerRegistry

FIXTURES_DIR = Path(__file__).parent


# --- AgentTrigger creation and defaults ---


def test_agent_trigger_default_creation() -> None:
    t = AgentTrigger()
    assert t.name == ""
    assert t.type == "auto"
    assert t.condition == ""
    assert t.thinking_level == "normal"
    assert t.agent == ""
    assert t.model == "sonnet"
    assert t.priority == 50
    assert t.background is False
    assert t.max_retries == 3
    assert t.skill_attachments == []


def test_agent_trigger_custom_creation() -> None:
    t = AgentTrigger(
        name="explore",
        type="auto",
        condition="task_type == 'exploration'",
        thinking_level="fast",
        agent="explore",
        model="haiku",
        priority=80,
    )
    assert t.name == "explore"
    assert t.model == "haiku"
    assert t.priority == 80


def test_agent_trigger_is_frozen() -> None:
    t = AgentTrigger(name="test")
    with pytest.raises((TypeError, AttributeError, Exception)):
        t.name = "changed"  # type: ignore[misc]


def test_agent_trigger_skill_attachments() -> None:
    t = AgentTrigger(name="test", skill_attachments=["skill1", "skill2"])
    assert "skill1" in t.skill_attachments


# --- AgentTrigger.evaluate ---


def test_evaluate_empty_condition_returns_false() -> None:
    t = AgentTrigger(name="t", condition="")
    assert t.evaluate({"task_type": "exploration"}) is False


def test_evaluate_equality_match() -> None:
    t = AgentTrigger(name="t", condition="task_type == 'exploration'")
    assert t.evaluate({"task_type": "exploration"}) is True


def test_evaluate_equality_no_match() -> None:
    t = AgentTrigger(name="t", condition="task_type == 'architecture'")
    assert t.evaluate({"task_type": "exploration"}) is False


def test_evaluate_in_condition_match() -> None:
    t = AgentTrigger(name="t", condition="'search' in task")
    assert t.evaluate({"task": "search for files", "task_type": None}) is True


def test_evaluate_in_condition_no_match() -> None:
    t = AgentTrigger(name="t", condition="'security' in task")
    assert t.evaluate({"task": "refactor code", "task_type": None}) is False


def test_evaluate_complexity_high() -> None:
    t = AgentTrigger(name="t", condition="complexity == 'high'")
    assert t.evaluate({"complexity": "high"}) is True
    assert t.evaluate({"complexity": "low"}) is False


def test_evaluate_with_empty_context() -> None:
    t = AgentTrigger(name="t", condition="task_type == 'exploration'")
    assert t.evaluate({}) is False


def test_evaluate_domain_match() -> None:
    t = AgentTrigger(name="t", condition="domain == 'python'")
    assert t.evaluate({"domain": "python"}) is True


def test_evaluate_priority_sorting() -> None:
    t1 = AgentTrigger(name="low", condition="domain == 'python'", priority=30)
    t2 = AgentTrigger(name="high", condition="domain == 'python'", priority=80)
    registry = TriggerRegistry(agent_triggers=[t1, t2])
    matched = registry.match_agent_triggers({"domain": "python"})
    assert matched[0].name == "high"
    assert matched[1].name == "low"


# --- TriggerRegistry ---


def test_trigger_registry_empty() -> None:
    reg = TriggerRegistry()
    assert reg.agent_triggers == []
    assert reg.recovery_triggers == []


def test_trigger_registry_match_no_triggers() -> None:
    reg = TriggerRegistry()
    result = reg.match_agent_triggers({"task_type": "exploration"})
    assert result == []


def test_trigger_registry_from_yaml(tmp_path: Path) -> None:
    agent_yaml = tmp_path / "agent_triggers.yaml"
    agent_yaml.write_text(
        yaml.dump(
            {
                "agent_triggers": {
                    "explore": {
                        "condition": "task_type == 'exploration'",
                        "agent_type": "explore",
                        "model": "haiku",
                        "priority": 60,
                        "background": False,
                        "max_retries": 2,
                        "description": "Fast search",
                        "skill_attachments": [],
                    }
                }
            }
        )
    )
    recovery_yaml = tmp_path / "recovery_triggers.yaml"
    recovery_yaml.write_text(yaml.dump({"recovery_triggers": {}}))

    reg = TriggerRegistry.from_yaml(agent_yaml, recovery_yaml)
    assert len(reg.agent_triggers) == 1
    assert reg.agent_triggers[0].name == "explore"


def test_trigger_registry_from_yaml_missing_files(tmp_path: Path) -> None:
    reg = TriggerRegistry.from_yaml(tmp_path / "missing.yaml", tmp_path / "missing2.yaml")
    assert reg.agent_triggers == []
    assert reg.recovery_triggers == []


def test_trigger_registry_from_real_yaml() -> None:
    base = Path(__file__).resolve().parent.parent.parent
    agent_path = (
        base / "claude_code_kazuba/data/modules/config-hypervisor/config/agent_triggers.yaml"
    )
    recovery_path = (
        base / "claude_code_kazuba/data/modules/config-hypervisor/config/recovery_triggers.yaml"
    )

    if agent_path.exists() and recovery_path.exists():
        reg = TriggerRegistry.from_yaml(agent_path, recovery_path)
        assert len(reg.agent_triggers) >= 1
        assert len(reg.recovery_triggers) >= 1


def test_trigger_registry_match_multiple() -> None:
    t1 = AgentTrigger(name="a", condition="task_type == 'exploration'", priority=60)
    t2 = AgentTrigger(name="b", condition="complexity == 'high'", priority=80)
    reg = TriggerRegistry(agent_triggers=[t1, t2])
    ctx = {"task_type": "exploration", "complexity": "high"}
    matched = reg.match_agent_triggers(ctx)
    assert len(matched) >= 1
