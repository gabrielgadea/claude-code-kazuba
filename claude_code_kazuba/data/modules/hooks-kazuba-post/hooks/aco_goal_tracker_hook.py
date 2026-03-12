#!/usr/bin/env python3
"""ACO Goal Tracker — PostToolUse hook.

Event: PostToolUse
Purpose: After Task/Agent tool calls, checks the most recent ACO goal tracker
checkpoint. If overall_score is below threshold, emits a warning to stderr.
Advisory only — never blocks.

Protocol:
  1. Reads JSON from stdin (tool_name, tool_input, tool_response, session_id)
  2. Filters: only processes Task and Agent tools
  3. Searches for latest aco_goal_tracker_*.json checkpoint
  4. If found and overall_score < 0.6: emits warning to stderr
  5. Always exits 0 (advisory, never blocks)

Input (stdin): {"tool_name": "...", "tool_input": {...}, "tool_response": {...}, "session_id": "..."}
Output (stderr): Warning message if score is low
"""

from __future__ import annotations

import glob
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Exit codes
ALLOW = 0

# Only process these tools
_RELEVANT_TOOLS: frozenset[str] = frozenset({"Task", "Agent"})

# Score threshold for warning
_SCORE_THRESHOLD = 0.6

# Checkpoint directory — .claude/checkpoints/ (3 levels up from validation/)
_CHECKPOINT_DIR = Path(__file__).resolve().parent.parent.parent / "checkpoints"


@dataclass(frozen=True)
class HookInput:
    """Parsed input from Claude Code PostToolUse event."""

    tool_name: str
    tool_input: dict[str, Any]
    tool_response: dict[str, Any]
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
                tool_response=data.get("tool_response", {}),
                session_id=data.get("session_id", ""),
            )
        except (json.JSONDecodeError, EOFError, ValueError):
            sys.exit(ALLOW)
            return cls(  # unreachable, for type checker
                tool_name="",
                tool_input={},
                tool_response={},
                session_id="",
            )


@dataclass(frozen=True)
class HookResult:
    """Hook execution result."""

    exit_code: int
    message: str = ""

    def emit(self) -> None:
        """Emit result to stderr and exit."""
        if self.message:
            print(self.message, file=sys.stderr)
        sys.exit(self.exit_code)


def find_latest_checkpoint() -> Path | None:
    """Find the most recent ACO goal tracker checkpoint.

    Returns:
        Path to the latest checkpoint, or None if not found.
    """
    pattern = str(_CHECKPOINT_DIR / "aco_goal_tracker_*.json")
    matches = glob.glob(pattern)
    if not matches:
        return None
    # Sort by filename (contains timestamp) — latest is last
    matches.sort()
    return Path(matches[-1])


def read_overall_score(checkpoint_path: Path) -> float | None:
    """Read overall_score from checkpoint JSON.

    Args:
        checkpoint_path: Path to checkpoint file.

    Returns:
        The overall_score value, or None if not found/parseable.
    """
    try:
        data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        score = data.get("overall_score")
        if score is not None:
            return float(score)
    except (json.JSONDecodeError, ValueError, OSError):
        pass
    return None


def process(hook_input: HookInput) -> HookResult:
    """Check ACO goal tracker state after Task/Agent execution.

    Args:
        hook_input: Parsed input from Claude Code.

    Returns:
        HookResult with warning if score is low.
    """
    # Fast path: skip irrelevant tools
    if hook_input.tool_name not in _RELEVANT_TOOLS:
        return HookResult(exit_code=ALLOW)

    # Find latest checkpoint
    checkpoint = find_latest_checkpoint()
    if checkpoint is None:
        return HookResult(exit_code=ALLOW)

    # Read score
    score = read_overall_score(checkpoint)
    if score is None:
        return HookResult(exit_code=ALLOW)

    # Warn if below threshold
    if score < _SCORE_THRESHOLD:
        return HookResult(
            exit_code=ALLOW,
            message=(
                f"ACO GOAL TRACKER WARNING: overall_score={score:.2f} "
                f"(threshold={_SCORE_THRESHOLD}). "
                f"Consider reviewing objective alignment before proceeding. "
                f"Checkpoint: {checkpoint.name}"
            ),
        )

    return HookResult(exit_code=ALLOW)


def main() -> None:
    """Entry point for PostToolUse hook."""
    try:
        hook_input = HookInput.from_stdin()
        result = process(hook_input)
        result.emit()
    except Exception:
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
