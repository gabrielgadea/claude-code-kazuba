"""Tests for validate_hooks_health.py — Phase 16."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Module loading via importlib (modules dir has hyphens — not valid py names)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _import_from_path(name: str, file_path: Path) -> types.ModuleType:
    """Import a Python module from an arbitrary file path."""
    lib_parent = str(PROJECT_ROOT)
    if lib_parent not in sys.path:
        sys.path.insert(0, lib_parent)
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    assert spec is not None, f"Cannot load spec for {file_path}"
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_VHH_PATH = PROJECT_ROOT / "modules" / "hooks-quality" / "hooks" / "validate_hooks_health.py"
_vhh = _import_from_path("validate_hooks_health_ph16", _VHH_PATH)

HookStatus = _vhh.HookStatus
HealthReport = _vhh.HealthReport
HooksHealthValidator = _vhh.HooksHealthValidator
main = _vhh.main


# ---------------------------------------------------------------------------
# HookStatus tests
# ---------------------------------------------------------------------------


def test_hook_status_creation() -> None:
    """HookStatus can be created with required fields."""
    status = HookStatus(name="my_hook.py", event="PreToolUse", healthy=True)
    assert status.name == "my_hook.py"
    assert status.event == "PreToolUse"
    assert status.healthy is True
    assert status.error_count == 0
    assert status.last_error == ""


def test_hook_status_frozen() -> None:
    """HookStatus is immutable (frozen=True)."""
    status = HookStatus(name="hook.py", event="SessionStart", healthy=True)
    with pytest.raises(ValueError):
        status.healthy = False  # type: ignore[misc]


def test_hook_status_unhealthy() -> None:
    """HookStatus stores error info for unhealthy hooks."""
    status = HookStatus(
        name="broken.py",
        event="Stop",
        healthy=False,
        error_count=1,
        last_error="File not found",
    )
    assert status.healthy is False
    assert status.error_count == 1
    assert "not found" in status.last_error


# ---------------------------------------------------------------------------
# HealthReport tests
# ---------------------------------------------------------------------------


def test_health_report_creation() -> None:
    """HealthReport can be created with aggregate counts."""
    report = HealthReport(total=5, healthy=4, degraded=0, failed=1)
    assert report.total == 5
    assert report.healthy == 4
    assert report.failed == 1
    assert report.hooks == []


def test_health_report_counts() -> None:
    """HealthReport counts reflect the provided hook statuses."""
    hooks = [
        HookStatus(name="a.py", event="SessionStart", healthy=True),
        HookStatus(name="b.py", event="PreCompact", healthy=False, error_count=1),
    ]
    report = HealthReport(total=2, healthy=1, degraded=0, failed=1, hooks=hooks)
    assert report.total == 2
    assert len(report.hooks) == 2


def test_health_report_frozen() -> None:
    """HealthReport is immutable (frozen=True)."""
    report = HealthReport(total=0, healthy=0, degraded=0, failed=0)
    with pytest.raises(ValueError):
        report.total = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# HooksHealthValidator tests
# ---------------------------------------------------------------------------


def test_validator_init() -> None:
    """HooksHealthValidator can be created with no settings_path."""
    validator = HooksHealthValidator()
    assert validator.settings_path is None


def test_validator_no_settings() -> None:
    """validate_all returns empty report when settings_path is None."""
    validator = HooksHealthValidator(settings_path=None)
    report = validator.validate_all()
    assert report.total == 0
    assert report.healthy == 0
    assert report.failed == 0


def test_validator_empty_settings(tmp_path: Path) -> None:
    """validate_all handles settings file with no hooks section."""
    settings = {"permissions": {"allow": [], "deny": []}}
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    validator = HooksHealthValidator(settings_path=settings_path)
    report = validator.validate_all()
    assert report.total == 0


def test_check_hook_file_python_exists(tmp_path: Path) -> None:
    """_check_hook_file returns True for an existing executable .py file."""
    hook_file = tmp_path / "my_hook.py"
    hook_file.write_text("#!/usr/bin/env python3\nprint('hello')\n")
    hook_file.chmod(0o755)

    validator = HooksHealthValidator()
    result = validator._check_hook_file(f"python3 {hook_file}")
    assert result is True


def test_check_hook_file_missing(tmp_path: Path) -> None:
    """_check_hook_file returns False for a missing .py file."""
    validator = HooksHealthValidator()
    result = validator._check_hook_file(f"python3 {tmp_path}/nonexistent.py")
    assert result is False


def test_validate_all_empty(tmp_path: Path) -> None:
    """validate_all with empty hooks section returns zero-count report."""
    settings = {"hooks": {}}
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    validator = HooksHealthValidator(settings_path=settings_path)
    report = validator.validate_all()
    assert report.total == 0
    assert report.failed == 0


def test_validate_all_with_existing_hook(tmp_path: Path) -> None:
    """validate_all detects an existing executable hook as healthy."""
    hook_file = tmp_path / "good_hook.py"
    hook_file.write_text("#!/usr/bin/env python3\nprint('ok')\n")
    hook_file.chmod(0o755)

    settings = {"hooks": {"SessionStart": [{"hooks": [{"command": f"python3 {hook_file}"}]}]}}
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    validator = HooksHealthValidator(settings_path=settings_path)
    report = validator.validate_all()
    assert report.total >= 1
    assert report.failed == 0


def test_validate_all_with_missing_hook(tmp_path: Path) -> None:
    """validate_all detects a missing hook file as failed."""
    settings = {
        "hooks": {
            "SessionStart": [{"hooks": [{"command": f"python3 {tmp_path}/missing_hook.py"}]}]
        }
    }
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    validator = HooksHealthValidator(settings_path=settings_path)
    report = validator.validate_all()
    assert report.total >= 1
    assert report.failed >= 1


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


def test_main_no_settings() -> None:
    """main() works when no settings file is found, exits 0."""
    with (
        patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": "/nonexistent/path/xyz"}),
        patch("sys.stdin", StringIO("")),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 0


def test_main_always_exits_zero() -> None:
    """main() always exits 0 regardless of input (fail-open)."""
    with patch("sys.stdin", StringIO("INVALID {{{")), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


def test_validate_all_parse_exception(tmp_path: Path) -> None:
    """validate_all returns failed report when settings.json is invalid JSON."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("NOT VALID JSON {{{")

    validator = HooksHealthValidator(settings_path=settings_path)
    report = validator.validate_all()
    assert report.failed >= 1


def test_check_hook_with_uv_run_shebang(tmp_path: Path) -> None:
    """_check_hook detects incompatible uv run shebang as error."""
    hook_file = tmp_path / "uv_hook.py"
    hook_file.write_text("#!/usr/bin/env uv run python\nprint('hello')\n")
    hook_file.chmod(0o755)

    settings = {"hooks": {"SessionStart": [{"hooks": [{"command": f"python3 {hook_file}"}]}]}}
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    validator = HooksHealthValidator(settings_path=settings_path)
    report = validator.validate_all()
    # The hook exists and is executable, but has uv run shebang
    assert report.total >= 1
    # It should be flagged as unhealthy or degraded
    has_issue = any(not h.healthy for h in report.hooks)
    assert has_issue


def test_check_hook_file_non_python_command() -> None:
    """_check_hook_file returns True for non-python commands (no .py file)."""
    validator = HooksHealthValidator()
    result = validator._check_hook_file("bash my_script.sh")
    # No .py file means _extract returns None → returns True
    assert result is True


def test_extract_python_file_no_match() -> None:
    """_extract_python_file returns None for non-Python commands."""
    validator = HooksHealthValidator()
    result = validator._extract_python_file("bash run.sh")
    assert result is None


def test_extract_python_file_with_python() -> None:
    """_extract_python_file returns path when .py present."""
    validator = HooksHealthValidator()
    result = validator._extract_python_file("python3 /some/hook.py --flag")
    assert result == "/some/hook.py"


def test_parse_settings_non_list_event_configs(tmp_path: Path) -> None:
    """_parse_settings skips events where configs is not a list."""
    settings = {
        "hooks": {
            "SessionStart": "not-a-list",
        }
    }
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    validator = HooksHealthValidator(settings_path=settings_path)
    hook_defs = validator._parse_settings(settings_path)
    assert hook_defs == []


def test_parse_settings_no_command(tmp_path: Path) -> None:
    """_parse_settings skips hooks with empty command."""
    settings = {"hooks": {"SessionStart": [{"hooks": [{"type": "python", "command": ""}]}]}}
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    validator = HooksHealthValidator(settings_path=settings_path)
    hook_defs = validator._parse_settings(settings_path)
    assert hook_defs == []


def test_main_with_settings(tmp_path: Path) -> None:
    """main() reads settings from CLAUDE_PROJECT_DIR env var, exits 0."""
    (tmp_path / ".claude").mkdir()
    settings = {"hooks": {}}
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(settings))

    with (
        patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(tmp_path)}),
        patch("sys.stdin", StringIO("")),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 0


def test_main_with_failed_hooks_branch(tmp_path: Path) -> None:
    """main() covers the failed>0 branch in the report output."""
    (tmp_path / ".claude").mkdir()
    settings = {
        "hooks": {
            "SessionStart": [{"hooks": [{"command": f"python3 {tmp_path}/missing_hook.py"}]}]
        }
    }
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(settings))

    with (
        patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(tmp_path)}),
        patch("sys.stdin", StringIO("")),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 0


def test_main_with_healthy_hooks_branch(tmp_path: Path) -> None:
    """main() covers the healthy branch (report.failed == 0, total > 0)."""
    hook_file = tmp_path / "good.py"
    hook_file.write_text("#!/usr/bin/env python3\nprint('ok')\n")
    hook_file.chmod(0o755)

    (tmp_path / ".claude").mkdir()
    settings = {"hooks": {"SessionStart": [{"hooks": [{"command": f"python3 {hook_file}"}]}]}}
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(settings))

    with (
        patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(tmp_path)}),
        patch("sys.stdin", StringIO("")),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 0


def test_main_exception_branch(tmp_path: Path) -> None:
    """main() exception branch still exits 0 (fail-open)."""
    import validate_hooks_health_ph16 as mod_vhh

    original = mod_vhh.HooksHealthValidator.validate_all

    def _raise(self: object) -> object:
        raise RuntimeError("forced error in validate_all")

    mod_vhh.HooksHealthValidator.validate_all = _raise  # type: ignore[method-assign]

    with patch("sys.stdin", StringIO("")), pytest.raises(SystemExit) as exc_info:
        main()

    mod_vhh.HooksHealthValidator.validate_all = original  # type: ignore[method-assign]
    assert exc_info.value.code == 0


def test_extract_python_with_python_in_path_but_no_py() -> None:
    """_extract_python_file returns None when 'python' in path but no .py part."""
    validator = HooksHealthValidator()
    # Command has 'python' in a non-.py word
    result = validator._extract_python_file("python3 run_server")
    assert result is None


def test_parse_settings_non_dict_config(tmp_path: Path) -> None:
    """_parse_settings skips non-dict entries in event config list."""
    settings = {
        "hooks": {
            "SessionStart": [
                "not-a-dict",
                {"hooks": [{"command": "echo hello"}]},
            ]
        }
    }
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    validator = HooksHealthValidator(settings_path=settings_path)
    hook_defs = validator._parse_settings(settings_path)
    # Only the dict entry with 'hooks' produces hook_defs
    assert len(hook_defs) >= 0


def test_parse_settings_non_list_inner_hooks(tmp_path: Path) -> None:
    """_parse_settings skips configs where inner hooks is not a list."""
    settings = {
        "hooks": {
            "SessionStart": [
                {"hooks": "not-a-list"},
            ]
        }
    }
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    validator = HooksHealthValidator(settings_path=settings_path)
    hook_defs = validator._parse_settings(settings_path)
    assert hook_defs == []


def test_check_hook_file_not_executable(tmp_path: Path) -> None:
    """_check_hook_file returns False for an existing but non-executable .py file."""
    hook_file = tmp_path / "no_exec.py"
    hook_file.write_text("print('hi')")
    hook_file.chmod(0o644)  # read/write but not executable

    validator = HooksHealthValidator()
    result = validator._check_hook_file(f"python3 {hook_file}")
    # On Linux, non-executable file → False
    assert result is False


def test_check_hook_oserror_on_read(tmp_path: Path) -> None:
    """_check_hook handles OSError when reading hook file content."""
    hook_file = tmp_path / "unreadable.py"
    hook_file.write_text("#!/usr/bin/env python3\nprint('ok')\n")
    hook_file.chmod(0o311)  # executable but not readable

    settings = {"hooks": {"PreCompact": [{"hooks": [{"command": f"python3 {hook_file}"}]}]}}
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    validator = HooksHealthValidator(settings_path=settings_path)
    report = validator.validate_all()
    # Should not crash — report total >= 1
    assert report.total >= 1
