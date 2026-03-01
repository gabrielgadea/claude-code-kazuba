"""Tests for RecoveryTrigger and TriggerRegistry recovery logic — Phase 14."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lib.config import RecoveryTrigger, TriggerRegistry


# --- RecoveryTrigger creation and defaults ---

def test_recovery_trigger_defaults() -> None:
    t = RecoveryTrigger()
    assert t.name == ""
    assert t.type == "auto"
    assert t.on_event == ""
    assert t.action == ""
    assert t.max_retries == 3
    assert t.cooldown_seconds == 30.0
    assert t.description == ""
    assert t.conditions == {}


def test_recovery_trigger_custom_creation() -> None:
    t = RecoveryTrigger(
        name="circuit_open",
        type="auto",
        on_event="circuit_breaker_open",
        action="use_fallback",
        max_retries=5,
        cooldown_seconds=60.0,
    )
    assert t.name == "circuit_open"
    assert t.on_event == "circuit_breaker_open"
    assert t.action == "use_fallback"
    assert t.max_retries == 5
    assert t.cooldown_seconds == 60.0


def test_recovery_trigger_is_frozen() -> None:
    t = RecoveryTrigger(name="test")
    with pytest.raises(Exception):
        t.name = "changed"  # type: ignore[misc]


def test_recovery_trigger_conditions_dict() -> None:
    t = RecoveryTrigger(name="t", conditions={"consecutive_failures": 3})
    assert t.conditions.get("consecutive_failures") == 3


def test_recovery_trigger_type_manual() -> None:
    t = RecoveryTrigger(name="manual", type="manual")
    assert t.type == "manual"


# --- TriggerRegistry recovery methods ---

def test_registry_get_recovery_trigger_found() -> None:
    t = RecoveryTrigger(name="test", on_event="hook_failure", action="retry")
    reg = TriggerRegistry(recovery_triggers=[t])
    found = reg.get_recovery_trigger("hook_failure")
    assert found is not None
    assert found.name == "test"
    assert found.action == "retry"


def test_registry_get_recovery_trigger_not_found() -> None:
    reg = TriggerRegistry()
    found = reg.get_recovery_trigger("nonexistent_event")
    assert found is None


def test_registry_get_recovery_trigger_multiple() -> None:
    t1 = RecoveryTrigger(name="first", on_event="error", action="retry")
    t2 = RecoveryTrigger(name="second", on_event="timeout", action="skip")
    reg = TriggerRegistry(recovery_triggers=[t1, t2])
    assert reg.get_recovery_trigger("error") is not None
    assert reg.get_recovery_trigger("error").name == "first"  # type: ignore[union-attr]
    assert reg.get_recovery_trigger("timeout") is not None


def test_registry_from_yaml_recovery_triggers(tmp_path: Path) -> None:
    recovery_yaml = tmp_path / "recovery_triggers.yaml"
    recovery_yaml.write_text(yaml.dump({
        "recovery_triggers": {
            "auto_retry": {
                "type": "auto",
                "on_event": "hook_timeout",
                "action": "retry_with_backoff",
                "max_retries": 3,
                "cooldown_seconds": 30.0,
                "description": "Auto retry on hook timeout",
                "conditions": {},
            }
        }
    }))
    agent_yaml = tmp_path / "agent_triggers.yaml"
    agent_yaml.write_text(yaml.dump({"agent_triggers": {}}))

    reg = TriggerRegistry.from_yaml(agent_yaml, recovery_yaml)
    assert len(reg.recovery_triggers) == 1
    found = reg.get_recovery_trigger("hook_timeout")
    assert found is not None
    assert found.name == "auto_retry"


def test_registry_from_real_recovery_yaml() -> None:
    base = Path(__file__).resolve().parent.parent.parent
    recovery_path = base / "modules/config-hypervisor/config/recovery_triggers.yaml"
    agent_path = base / "modules/config-hypervisor/config/agent_triggers.yaml"

    if recovery_path.exists() and agent_path.exists():
        reg = TriggerRegistry.from_yaml(agent_path, recovery_path)
        assert len(reg.recovery_triggers) >= 1


def test_recovery_trigger_max_retries_zero() -> None:
    t = RecoveryTrigger(name="no_retry", max_retries=0)
    assert t.max_retries == 0


def test_recovery_trigger_cooldown_zero() -> None:
    t = RecoveryTrigger(name="immediate", cooldown_seconds=0.0)
    assert t.cooldown_seconds == 0.0


def test_from_yaml_with_non_dict_entry(tmp_path: Path) -> None:
    """Line 161: non-dict entries in recovery YAML should be skipped."""
    recovery_yaml = tmp_path / "recovery_triggers.yaml"
    recovery_yaml.write_text(
        "recovery_triggers:\n"
        "  valid:\n"
        "    on_event: hook_failure\n"
        "    action: retry\n"
        "  _comment: 'this is not a dict trigger'\n"
    )
    agent_yaml = tmp_path / "agent_triggers.yaml"
    agent_yaml.write_text("agent_triggers: {}")
    reg = TriggerRegistry.from_yaml(agent_yaml, recovery_yaml)
    assert len(reg.recovery_triggers) == 1
    assert reg.recovery_triggers[0].name == "valid"


def test_resolve_dependencies_basic() -> None:
    from lib.config import ModuleManifest, resolve_dependencies

    manifests = {
        "a": ModuleManifest(name="a", version="1.0", description="", dependencies=[], hooks_file=None, files=[]),
        "b": ModuleManifest(name="b", version="1.0", description="", dependencies=["a"], hooks_file=None, files=[]),
    }
    result = resolve_dependencies(["b"], manifests)
    assert result == ["a", "b"]


def test_resolve_dependencies_missing_raises() -> None:
    from lib.config import ModuleManifest, resolve_dependencies
    import pytest

    manifests = {
        "a": ModuleManifest(name="a", version="1.0", description="", dependencies=["missing"], hooks_file=None, files=[]),
    }
    with pytest.raises(ValueError, match="Dependency not found"):
        resolve_dependencies(["a"], manifests)


def test_resolve_dependencies_module_not_found() -> None:
    from lib.config import resolve_dependencies
    import pytest

    with pytest.raises(ValueError, match="Module not found"):
        resolve_dependencies(["nonexistent"], {})


def test_resolve_dependencies_no_duplicates() -> None:
    from lib.config import ModuleManifest, resolve_dependencies

    manifests = {
        "a": ModuleManifest(name="a", version="1.0", description="", dependencies=[], hooks_file=None, files=[]),
        "b": ModuleManifest(name="b", version="1.0", description="", dependencies=["a"], hooks_file=None, files=[]),
        "c": ModuleManifest(name="c", version="1.0", description="", dependencies=["a"], hooks_file=None, files=[]),
    }
    result = resolve_dependencies(["b", "c"], manifests)
    assert result.count("a") == 1
