"""JSON output builders for Claude Code hook contract."""

from __future__ import annotations

import json
from typing import Any


def pre_tool_use_output(decision: str, reason: str) -> dict[str, Any]:
    """Build PreToolUse hookSpecificOutput.

    Args:
        decision: "allow", "block", or "deny"
        reason: Human-readable explanation

    Returns:
        Properly structured dict per Claude Code hook contract.
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "decision": decision,
            "reason": reason,
        }
    }


def user_prompt_output(additional_context: str) -> dict[str, Any]:
    """Build UserPromptSubmit hookSpecificOutput.

    Args:
        additional_context: Context to inject into the prompt.

    Returns:
        Properly structured dict.
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    }


def session_start_output(additional_context: str) -> dict[str, Any]:
    """Build SessionStart hookSpecificOutput.

    Args:
        additional_context: Context to inject at session start.

    Returns:
        Properly structured dict.
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }
    }


def stop_output(decision: str, reason: str) -> dict[str, Any]:
    """Build Stop hookSpecificOutput.

    Args:
        decision: "stop" or "continue"
        reason: Human-readable explanation

    Returns:
        Properly structured dict.
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "decision": decision,
            "reason": reason,
        }
    }


def pre_compact_output(rules: str) -> dict[str, Any]:
    """Build PreCompact additionalContext.

    Args:
        rules: Rules/context to preserve during compaction.

    Returns:
        Properly structured dict.
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext": rules,
        }
    }


def emit_json(data: dict[str, Any]) -> None:
    """Print JSON to stdout.

    Args:
        data: Dictionary to serialize and print.
    """
    print(json.dumps(data))
