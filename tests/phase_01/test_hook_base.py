"""Tests for lib.hook_base — core hook infrastructure."""
from __future__ import annotations

import json
import sys
from typing import Any
from unittest.mock import patch

import pytest

from lib.hook_base import (
    ALLOW,
    BLOCK,
    DENY,
    HookConfig,
    HookInput,
    HookResult,
    fail_open,
)


class TestExitCodes:
    """Exit code constants."""

    def test_allow_is_zero(self) -> None:
        assert ALLOW == 0

    def test_block_is_one(self) -> None:
        assert BLOCK == 1

    def test_deny_is_two(self) -> None:
        assert DENY == 2


class TestHookConfig:
    """HookConfig frozen dataclass."""

    def test_defaults(self) -> None:
        cfg = HookConfig()
        assert cfg.enabled is True
        assert cfg.timeout_ms == 10_000

    def test_custom_values(self) -> None:
        cfg = HookConfig(enabled=False, timeout_ms=5000)
        assert cfg.enabled is False
        assert cfg.timeout_ms == 5000

    def test_frozen(self) -> None:
        cfg = HookConfig()
        with pytest.raises(AttributeError):
            cfg.enabled = False  # type: ignore[misc]


class TestHookInput:
    """HookInput parsing and immutability."""

    def test_from_dict(self, sample_hook_input: dict[str, Any]) -> None:
        hi = HookInput.from_dict(sample_hook_input)
        assert hi.tool_name == "Write"
        assert hi.session_id == "test-session-001"
        assert hi.cwd == "/tmp/test-project"
        assert hi.hook_event_name == "PreToolUse"
        assert isinstance(hi.tool_input, dict)

    def test_from_dict_minimal(self) -> None:
        data: dict[str, Any] = {
            "session_id": "s1",
            "cwd": "/tmp",
            "hook_event_name": "PreToolUse",
        }
        hi = HookInput.from_dict(data)
        assert hi.tool_name is None
        assert hi.tool_input is None

    def test_from_stdin(self, sample_hook_input: dict[str, Any]) -> None:
        json_str = json.dumps(sample_hook_input)
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = json_str
            hi = HookInput.from_stdin()
        assert hi.tool_name == "Write"
        assert hi.session_id == "test-session-001"

    def test_frozen(self, sample_hook_input: dict[str, Any]) -> None:
        hi = HookInput.from_dict(sample_hook_input)
        with pytest.raises(AttributeError):
            hi.tool_name = "Bash"  # type: ignore[misc]


class TestHookResult:
    """HookResult construction and emit."""

    def test_construction(self) -> None:
        r = HookResult(exit_code=ALLOW, message="ok")
        assert r.exit_code == 0
        assert r.message == "ok"
        assert r.output_json is None

    def test_with_output_json(self) -> None:
        out = {"decision": "block", "reason": "unsafe"}
        r = HookResult(exit_code=BLOCK, message="blocked", output_json=out)
        assert r.output_json == out

    def test_emit_exits_with_code(self) -> None:
        r = HookResult(exit_code=DENY, message="denied")
        with pytest.raises(SystemExit) as exc_info:
            r.emit()
        assert exc_info.value.code == DENY

    def test_emit_prints_message_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        r = HookResult(exit_code=ALLOW, message="all good")
        with pytest.raises(SystemExit):
            r.emit()
        captured = capsys.readouterr()
        assert "all good" in captured.err

    def test_emit_prints_json_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        out = {"hookSpecificOutput": {"decision": "allow"}}
        r = HookResult(exit_code=ALLOW, message="ok", output_json=out)
        with pytest.raises(SystemExit):
            r.emit()
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["hookSpecificOutput"]["decision"] == "allow"

    def test_frozen(self) -> None:
        r = HookResult(exit_code=ALLOW, message="ok")
        with pytest.raises(AttributeError):
            r.exit_code = 1  # type: ignore[misc]


class TestFailOpen:
    """fail_open decorator catches all exceptions and exits 0."""

    def test_normal_function_runs(self) -> None:
        @fail_open
        def good() -> str:
            return "ok"

        assert good() == "ok"

    def test_exception_exits_zero(self) -> None:
        @fail_open
        def bad() -> str:
            msg = "boom"
            raise RuntimeError(msg)

        with pytest.raises(SystemExit) as exc_info:
            bad()
        assert exc_info.value.code == 0

    def test_exception_prints_error_to_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        @fail_open
        def bad() -> str:
            msg = "something broke"
            raise ValueError(msg)

        with pytest.raises(SystemExit):
            bad()
        captured = capsys.readouterr()
        assert "something broke" in captured.err
