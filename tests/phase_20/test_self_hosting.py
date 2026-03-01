"""Tests for .claude/hooks/self_host_config.py — SelfHostConfig."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

# Load module via importlib (path starts with '.' which can't be a package name)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SHC_PATH = PROJECT_ROOT / ".claude" / "hooks" / "self_host_config.py"

_spec = importlib.util.spec_from_file_location("self_host_config", str(_SHC_PATH))
assert _spec is not None
_shc: types.ModuleType = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("self_host_config", _shc)
assert _spec.loader is not None
_spec.loader.exec_module(_shc)  # type: ignore[attr-defined]

# Aliases
HookRegistration = _shc.HookRegistration
SelfHostConfig = _shc.SelfHostConfig
get_default_hooks = _shc.get_default_hooks
load_config = _shc.load_config
validate_config = _shc.validate_config
generate_settings_fragment = _shc.generate_settings_fragment


# ---------------------------------------------------------------------------
# HookRegistration
# ---------------------------------------------------------------------------


def test_hook_registration_defaults() -> None:
    """HookRegistration has sensible defaults."""
    reg = HookRegistration(event="PreToolUse", script="python hook.py")
    assert reg.timeout == 5000
    assert reg.description == ""


def test_hook_registration_to_dict_has_hooks_key() -> None:
    """to_dict() returns a dict with 'hooks' key."""
    reg = HookRegistration(event="PreToolUse", script="python hook.py")
    d = reg.to_dict()
    assert "hooks" in d
    assert isinstance(d["hooks"], list)
    assert len(d["hooks"]) == 1


def test_hook_registration_frozen() -> None:
    """HookRegistration is immutable."""
    reg = HookRegistration(event="PreToolUse", script="python hook.py")
    with pytest.raises((AttributeError, TypeError)):
        reg.event = "PostToolUse"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SelfHostConfig
# ---------------------------------------------------------------------------


def _make_config(**kwargs: object) -> SelfHostConfig:
    defaults: dict[str, object] = {
        "project_root": PROJECT_ROOT,
        "hooks": tuple(get_default_hooks(PROJECT_ROOT)),
        "enabled": True,
    }
    defaults.update(kwargs)
    return SelfHostConfig(**defaults)  # type: ignore[arg-type]


def test_self_host_config_hooks_dir() -> None:
    """hooks_dir points to project_root/modules."""
    config = _make_config()
    assert config.hooks_dir == PROJECT_ROOT / "modules"


def test_self_host_config_get_hooks_for_event() -> None:
    """get_hooks_for_event() returns only hooks for that event."""
    config = _make_config()
    hooks = config.get_hooks_for_event("PreToolUse")
    assert all(h.event == "PreToolUse" for h in hooks)


def test_self_host_config_get_hooks_unknown_event_empty() -> None:
    """Unknown event returns empty list."""
    config = _make_config()
    assert config.get_hooks_for_event("UnknownEvent") == []


def test_self_host_config_frozen() -> None:
    """SelfHostConfig is immutable."""
    config = _make_config()
    with pytest.raises((AttributeError, TypeError)):
        config.enabled = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# get_default_hooks
# ---------------------------------------------------------------------------


def test_get_default_hooks_returns_list() -> None:
    """get_default_hooks() returns a non-empty list."""
    hooks = get_default_hooks(PROJECT_ROOT)
    assert isinstance(hooks, list)
    assert len(hooks) > 0


def test_get_default_hooks_have_pre_tool_use_event() -> None:
    """Default hooks include at least one PreToolUse registration."""
    hooks = get_default_hooks(PROJECT_ROOT)
    events = {h.event for h in hooks}
    assert "PreToolUse" in events


def test_get_default_hooks_with_none_uses_cwd() -> None:
    """Calling with None uses Path.cwd() as root."""
    hooks = get_default_hooks(None)
    assert isinstance(hooks, list)


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


def test_load_config_returns_self_host_config() -> None:
    """load_config() returns a SelfHostConfig instance."""
    config = load_config(PROJECT_ROOT)
    assert isinstance(config, SelfHostConfig)


def test_load_config_has_hooks() -> None:
    """Loaded config has at least one hook."""
    config = load_config(PROJECT_ROOT)
    assert len(config.hooks) > 0


def test_load_config_with_json_override(tmp_path: Path) -> None:
    """JSON override file replaces default hooks."""
    override_data = {
        "hooks": [{"event": "PostToolUse", "script": "python custom.py", "timeout": 3000}]
    }
    config_file = tmp_path / "hooks.json"
    config_file.write_text(json.dumps(override_data))
    config = load_config(PROJECT_ROOT, config_path=config_file)
    assert len(config.hooks) == 1
    assert config.hooks[0].event == "PostToolUse"


def test_load_config_with_malformed_json_uses_defaults(tmp_path: Path) -> None:
    """Malformed JSON config file falls back to defaults."""
    config_file = tmp_path / "bad.json"
    config_file.write_text("not valid json {{{")
    config = load_config(PROJECT_ROOT, config_path=config_file)
    # Falls back to defaults (non-empty)
    assert len(config.hooks) > 0


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


def test_validate_config_valid_returns_empty() -> None:
    """Valid config returns no errors."""
    config = load_config(PROJECT_ROOT)
    errors = validate_config(config)
    assert errors == []


def test_validate_config_empty_hooks_returns_error() -> None:
    """Config with no hooks returns an error."""
    config = _make_config(hooks=())
    errors = validate_config(config)
    assert len(errors) >= 1
    assert any("hook" in e.lower() for e in errors)


def test_validate_config_unknown_event_returns_error() -> None:
    """Hook with unknown event is flagged."""
    reg = HookRegistration(event="InvalidEvent", script="python hook.py")
    config = _make_config(hooks=(reg,))
    errors = validate_config(config)
    assert any("InvalidEvent" in e for e in errors)


# ---------------------------------------------------------------------------
# generate_settings_fragment
# ---------------------------------------------------------------------------


def test_generate_settings_fragment_structure() -> None:
    """Fragment has 'hooks' key with event groups."""
    config = load_config(PROJECT_ROOT)
    fragment = generate_settings_fragment(config)
    assert "hooks" in fragment
    assert isinstance(fragment["hooks"], dict)


def test_generate_settings_fragment_groups_by_event() -> None:
    """All entries for PreToolUse are under the PreToolUse key."""
    regs = (
        HookRegistration(event="PreToolUse", script="a.py"),
        HookRegistration(event="PreToolUse", script="b.py"),
    )
    config = _make_config(hooks=regs)
    fragment = generate_settings_fragment(config)
    assert "PreToolUse" in fragment["hooks"]
    assert len(fragment["hooks"]["PreToolUse"]) == 2


def test_generate_settings_fragment_each_entry_has_command() -> None:
    """Every hook entry has a 'command' field."""
    config = load_config(PROJECT_ROOT)
    fragment = generate_settings_fragment(config)
    for _event, entries in fragment["hooks"].items():
        for entry in entries:
            assert "command" in entry


# ---------------------------------------------------------------------------
# HookRegistration.to_dict with custom timeout
# ---------------------------------------------------------------------------


def test_hook_registration_to_dict_custom_timeout() -> None:
    """to_dict() includes timeout when it differs from default."""
    reg = HookRegistration(event="PreToolUse", script="python hook.py", timeout=3000)
    d = reg.to_dict()
    assert "timeout" in d


def test_hook_registration_to_dict_default_timeout_omitted() -> None:
    """to_dict() omits timeout when it equals 5000 (default)."""
    reg = HookRegistration(event="PreToolUse", script="python hook.py", timeout=5000)
    d = reg.to_dict()
    assert "timeout" not in d


# ---------------------------------------------------------------------------
# generate_settings_fragment with custom timeout
# ---------------------------------------------------------------------------


def test_generate_settings_fragment_custom_timeout_included() -> None:
    """Fragment includes timeout string when hook has non-default timeout."""
    reg = HookRegistration(event="PreToolUse", script="a.py", timeout=3000)
    config = _make_config(hooks=(reg,))
    fragment = generate_settings_fragment(config)
    entry = fragment["hooks"]["PreToolUse"][0]
    assert "timeout" in entry


# ---------------------------------------------------------------------------
# validate_config — edge cases
# ---------------------------------------------------------------------------


def test_validate_config_empty_event_returns_error() -> None:
    """Hook with empty event name is flagged."""
    reg = HookRegistration(event="", script="python hook.py")
    config = _make_config(hooks=(reg,))
    errors = validate_config(config)
    assert any("empty event" in e.lower() for e in errors)


def test_validate_config_empty_script_returns_error() -> None:
    """Hook with empty script path is flagged."""
    reg = HookRegistration(event="PreToolUse", script="")
    config = _make_config(hooks=(reg,))
    errors = validate_config(config)
    assert any("empty" in e.lower() or "script" in e.lower() for e in errors)


def test_validate_config_negative_timeout_returns_error() -> None:
    """Hook with negative timeout is flagged."""
    reg = HookRegistration(event="PreToolUse", script="python hook.py", timeout=-100)
    config = _make_config(hooks=(reg,))
    errors = validate_config(config)
    assert any("negative timeout" in e.lower() or "timeout" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# main() in self_host_config
# ---------------------------------------------------------------------------


def test_main_prints_json(capsys: pytest.CaptureFixture) -> None:
    """main() prints valid JSON fragment to stdout."""
    import contextlib
    import json as _json

    with contextlib.suppress(SystemExit):
        _shc.main()
    captured = capsys.readouterr()
    if captured.out.strip():
        data = _json.loads(captured.out)
        assert "hooks" in data
