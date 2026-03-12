#!/usr/bin/env python3
"""ACO Rollback Enforcer — PreToolUse hook (matcher: Task).

Event: PreToolUse
Purpose: When a Task tool call contains ACO-related content, checks if the
prompt mentions rollback strategy. If not, injects a reminder as
additionalContext. Advisory only — never blocks.

Protocol:
  1. Reads JSON from stdin (tool_name, tool_input, session_id)
  2. Checks if tool_input prompt contains ACO/generator keywords
  3. If ACO-related and no rollback mention: injects reminder
  4. Always exits 0 (advisory, never blocks)

Input (stdin): {"tool_name": "Task", "tool_input": {"prompt": "..."}, "session_id": "..."}
Output (stdout): {"additionalContext": "..."} if rollback reminder needed
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Any

# Exit codes
ALLOW = 0

# Patterns to detect ACO-related task content (case-insensitive)
_ACO_KEYWORDS: re.Pattern[str] = re.compile(
    r"\baco\b|\bgenerator\b|\borchestrat",
    re.IGNORECASE,
)

# Patterns to detect rollback mentions (case-insensitive)
_ROLLBACK_KEYWORDS: re.Pattern[str] = re.compile(
    r"\brollback\b|\brevert\b|\bundo\b|\brecovery\b|\bfallback\b|\bcheckpoint\b",
    re.IGNORECASE,
)

# Reminder message
_ROLLBACK_REMINDER = (
    "ACO ROLLBACK REMINDER: Este Task ACO não menciona estratégia de "
    "rollback. Considere: (1) Criar checkpoint ANTES de executar mudanças "
    "destrutivas, (2) Validar artefatos intermediários, (3) Definir "
    "critério de rollback se score < threshold. "
    "Padrão: git stash/commit antes de L3+ changes."
)


@dataclass(frozen=True)
class HookInput:
    """Parsed input from Claude Code PreToolUse event."""

    tool_name: str
    tool_input: dict[str, Any]
    session_id: str

    @classmethod
    def from_stdin(cls) -> HookInput:
        """Parse JSON from stdin.

        Returns:
            HookInput with tool metadata.
            On parse error, exits with ALLOW (never blocks).
        """
        try:
            data: dict[str, Any] = json.load(sys.stdin)
            return cls(
                tool_name=data.get("tool_name", ""),
                tool_input=data.get("tool_input", {}),
                session_id=data.get("session_id", ""),
            )
        except (json.JSONDecodeError, EOFError, ValueError):
            sys.exit(ALLOW)
            return cls(  # unreachable, for type checker
                tool_name="",
                tool_input={},
                session_id="",
            )


@dataclass(frozen=True)
class HookResult:
    """Hook execution result."""

    exit_code: int
    additional_context: str = ""

    def emit(self) -> None:
        """Emit result to stdout and exit."""
        if self.additional_context:
            json.dump(
                {"additionalContext": self.additional_context},
                sys.stdout,
            )
        sys.exit(self.exit_code)


def is_aco_related(prompt: str) -> bool:
    """Check if task prompt is ACO-related.

    Args:
        prompt: Task prompt text.

    Returns:
        True if ACO keywords found.
    """
    return bool(_ACO_KEYWORDS.search(prompt))


def mentions_rollback(prompt: str) -> bool:
    """Check if task prompt mentions rollback strategy.

    Args:
        prompt: Task prompt text.

    Returns:
        True if rollback-related keywords found.
    """
    return bool(_ROLLBACK_KEYWORDS.search(prompt))


def process(hook_input: HookInput) -> HookResult:
    """Check ACO task for rollback strategy mention.

    Args:
        hook_input: Parsed input from Claude Code.

    Returns:
        HookResult with rollback reminder if needed.
    """
    # Extract prompt from tool_input
    prompt = hook_input.tool_input.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        return HookResult(exit_code=ALLOW)

    # Check if ACO-related
    if not is_aco_related(prompt):
        return HookResult(exit_code=ALLOW)

    # Check if rollback is mentioned
    if mentions_rollback(prompt):
        return HookResult(exit_code=ALLOW)

    # Inject rollback reminder
    return HookResult(
        exit_code=ALLOW,
        additional_context=_ROLLBACK_REMINDER,
    )


def main() -> None:
    """Entry point for PreToolUse hook."""
    try:
        hook_input = HookInput.from_stdin()
        result = process(hook_input)
        result.emit()
    except Exception:
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
