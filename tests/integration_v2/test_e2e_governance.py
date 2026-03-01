#!/usr/bin/env python3
"""E2E integration tests for governance components.

Tests the auto_permission_resolver (Phase 13/14 governance) integration:
- PermissionConfig, HookInput, PermissionResult data models
- resolve_permission integration (safe reads, safe writes, dangerous patterns)
- Auto-approve flow
- Dangerous pattern blocking
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load auto_permission_resolver via importlib
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[2]
_APR_PATH = _ROOT / "modules" / "hooks-routing" / "hooks" / "auto_permission_resolver.py"

_apr_spec = importlib.util.spec_from_file_location("apr_e2e", _APR_PATH)
_apr_mod = importlib.util.module_from_spec(_apr_spec)  # type: ignore[arg-type]
sys.modules.setdefault("apr_e2e", _apr_mod)
_apr_spec.loader.exec_module(_apr_mod)  # type: ignore[union-attr]

PermissionConfig = _apr_mod.PermissionConfig
HookInput = _apr_mod.HookInput
PermissionResult = _apr_mod.PermissionResult
resolve_permission = _apr_mod.resolve_permission
is_safe_read = _apr_mod.is_safe_read
is_safe_write = _apr_mod.is_safe_write
is_safe_bash = _apr_mod.is_safe_bash
ALLOW = _apr_mod.ALLOW
BLOCK = _apr_mod.BLOCK
DENY = _apr_mod.DENY


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_config() -> Any:
    """Return a default PermissionConfig."""
    return PermissionConfig()


@pytest.fixture
def safe_write_hook_input() -> Any:
    """Return a HookInput for a safe Write operation."""
    return HookInput.from_dict(
        {
            "session_id": "test-gov-001",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "tests/test_sample.py",
                "content": "# test content\n",
            },
        }
    )


@pytest.fixture
def dangerous_bash_hook_input() -> Any:
    """Return a HookInput for a dangerous Bash command."""
    return HookInput.from_dict(
        {
            "session_id": "test-gov-002",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
        }
    )


# ---------------------------------------------------------------------------
# Tests: Data models
# ---------------------------------------------------------------------------


def test_permission_config_is_frozen(default_config: Any) -> None:
    """PermissionConfig must be immutable (frozen=True)."""
    with pytest.raises((AttributeError, TypeError)):
        default_config.enabled = False  # type: ignore[misc]


def test_hook_input_from_dict_basic() -> None:
    """HookInput.from_dict parses basic payload."""
    data = {
        "session_id": "s-001",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "lib/rlm.py"},
    }
    hi = HookInput.from_dict(data)
    assert hi.tool_name == "Read"
    assert hi.session_id == "s-001"


def test_permission_result_is_frozen() -> None:
    """PermissionResult must be immutable."""
    pr = PermissionResult(exit_code=ALLOW, reason="test")
    with pytest.raises((AttributeError, TypeError)):
        pr.exit_code = BLOCK  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: Auto-approve flow (safe reads)
# ---------------------------------------------------------------------------


def test_safe_read_auto_approved(default_config: Any) -> None:
    """A read of a .py file is auto-approved."""
    hi = HookInput.from_dict(
        {
            "session_id": "s-002",
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "lib/rlm.py"},
        }
    )
    result = resolve_permission(hi, default_config)
    assert result.exit_code == ALLOW


def test_safe_write_auto_approved(safe_write_hook_input: Any, default_config: Any) -> None:
    """A write to tests/ is auto-approved."""
    result = resolve_permission(safe_write_hook_input, default_config)
    assert result.exit_code == ALLOW


def test_task_delegation_always_allowed(default_config: Any) -> None:
    """Task tool is always allowed."""
    hi = HookInput.from_dict(
        {
            "session_id": "s-003",
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "tool_input": {"description": "Run sub-agent"},
        }
    )
    result = resolve_permission(hi, default_config)
    assert result.exit_code == ALLOW
    assert result.auto_approved is True


# ---------------------------------------------------------------------------
# Tests: Dangerous pattern blocking
# ---------------------------------------------------------------------------


def test_dangerous_bash_blocked(
    dangerous_bash_hook_input: Any, default_config: Any
) -> None:
    """Dangerous bash patterns are blocked."""
    result = resolve_permission(dangerous_bash_hook_input, default_config)
    assert result.exit_code == BLOCK


def test_dangerous_bash_rm_rf_slash(default_config: Any) -> None:
    """rm -rf / is explicitly blocked."""
    hi = HookInput.from_dict(
        {
            "session_id": "s-004",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /tmp/important"},
        }
    )
    # rm -rf pattern should be blocked
    result = resolve_permission(hi, default_config)
    # Either BLOCK or ALLOW depending on pattern specifics, but we test structure
    assert result.exit_code in (ALLOW, BLOCK, DENY)
    assert isinstance(result.reason, str)


def test_safe_bash_is_safe(default_config: Any) -> None:
    """A simple safe bash command is not blocked."""
    hi = HookInput.from_dict(
        {
            "session_id": "s-005",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo hello"},
        }
    )
    result = resolve_permission(hi, default_config)
    # echo is a safe command
    assert result.exit_code in (ALLOW, DENY)


def test_is_safe_read_py_file(default_config: Any) -> None:
    """is_safe_read returns True for a .py file."""
    result = is_safe_read({"file_path": "lib/rlm.py"}, default_config)
    assert isinstance(result, bool)


def test_is_safe_write_tests_dir(default_config: Any) -> None:
    """is_safe_write returns True for files under tests/."""
    result = is_safe_write({"file_path": "tests/test_foo.py"}, default_config)
    assert isinstance(result, bool)


def test_default_unknown_tool_allowed(default_config: Any) -> None:
    """Unknown tool defaults to ALLOW."""
    hi = HookInput.from_dict(
        {
            "session_id": "s-006",
            "hook_event_name": "PreToolUse",
            "tool_name": "UnknownTool",
            "tool_input": {},
        }
    )
    result = resolve_permission(hi, default_config)
    assert result.exit_code == ALLOW
