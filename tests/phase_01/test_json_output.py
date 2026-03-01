"""Tests for lib.json_output — JSON output builders for hook contract."""

from __future__ import annotations

import json

import pytest

from claude_code_kazuba.json_output import (
    emit_json,
    pre_compact_output,
    pre_tool_use_output,
    session_start_output,
    stop_output,
    user_prompt_output,
)


class TestPreToolUseOutput:
    """pre_tool_use_output builds correct structure."""

    def test_allow_decision(self) -> None:
        result = pre_tool_use_output("allow", "safe tool")
        assert result["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert result["hookSpecificOutput"]["decision"] == "allow"
        assert result["hookSpecificOutput"]["reason"] == "safe tool"

    def test_block_decision(self) -> None:
        result = pre_tool_use_output("block", "dangerous")
        assert result["hookSpecificOutput"]["decision"] == "block"


class TestUserPromptOutput:
    """user_prompt_output builds correct structure."""

    def test_structure(self) -> None:
        result = user_prompt_output("Think step by step")
        out = result["hookSpecificOutput"]
        assert out["hookEventName"] == "UserPromptSubmit"
        assert out["additionalContext"] == "Think step by step"


class TestSessionStartOutput:
    """session_start_output builds correct structure."""

    def test_structure(self) -> None:
        result = session_start_output("Welcome context")
        out = result["hookSpecificOutput"]
        assert out["hookEventName"] == "SessionStart"
        assert out["additionalContext"] == "Welcome context"


class TestStopOutput:
    """stop_output builds correct structure."""

    def test_structure(self) -> None:
        result = stop_output("stop", "task complete")
        out = result["hookSpecificOutput"]
        assert out["hookEventName"] == "Stop"
        assert out["decision"] == "stop"
        assert out["reason"] == "task complete"


class TestPreCompactOutput:
    """pre_compact_output builds correct structure."""

    def test_structure(self) -> None:
        result = pre_compact_output("Preserve these rules")
        out = result["hookSpecificOutput"]
        assert out["hookEventName"] == "PreCompact"
        assert out["additionalContext"] == "Preserve these rules"


class TestEmitJson:
    """emit_json prints JSON to stdout."""

    def test_emits_valid_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = {"key": "value", "num": 42}
        emit_json(data)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed == data

    def test_emits_compact_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = {"a": 1}
        emit_json(data)
        captured = capsys.readouterr()
        # Compact = no extra spaces
        assert captured.out.strip() == '{"a": 1}'
