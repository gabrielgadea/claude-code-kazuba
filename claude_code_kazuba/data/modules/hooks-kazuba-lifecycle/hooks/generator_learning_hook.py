#!/usr/bin/env python3
"""Generator Learning Hook — Stop event hook.

Event: Stop
Purpose: At session end, scans execution log for generator invocations
and records outcomes to the generator learning JSONL. Standalone — no
project module imports.

Protocol:
  1. Reads JSON from stdin (session_id, transcript_path)
  2. Scans recent .claude/metrics/compliance.jsonl for generator tool calls
  3. Appends GeneratorOutcome records to .claude/metrics/generator_learning.jsonl
  4. Always exits 0 (never blocks session shutdown)

Input (stdin): {"session_id": "...", "transcript_path": "..."}
Output: Appends to .claude/metrics/generator_learning.jsonl
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Exit codes
ALLOW = 0

# Paths (relative to project root, 3 levels up from lifecycle/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_COMPLIANCE_JSONL = _PROJECT_ROOT / ".claude" / "metrics" / "compliance.jsonl"
_LEARNING_JSONL = _PROJECT_ROOT / ".claude" / "metrics" / "generator_learning.jsonl"

# Pattern to detect generator script execution
_GEN_PATTERN = re.compile(r"gen_\w+\.py")


def _read_stdin() -> dict[str, Any]:
    """Read JSON from stdin, fail-open."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        return {}


def _scan_compliance_for_generators(session_id: str) -> list[dict[str, Any]]:
    """Scan compliance JSONL for generator-related entries in this session.

    Args:
        session_id: Current session ID to filter by.

    Returns:
        List of compliance entries that reference generator scripts.
    """
    if not _COMPLIANCE_JSONL.exists():
        return []

    results: list[dict[str, Any]] = []
    try:
        for line in _COMPLIANCE_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if entry.get("session_id") != session_id:
                    continue
                tool_input = entry.get("tool_input", "")
                if isinstance(tool_input, str) and _GEN_PATTERN.search(tool_input):
                    results.append(entry)
                elif isinstance(tool_input, dict):
                    cmd = tool_input.get("command", "")
                    if isinstance(cmd, str) and _GEN_PATTERN.search(cmd):
                        results.append(entry)
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return results


def _build_outcome(
    entry: dict[str, Any],
    session_id: str,
) -> dict[str, Any]:
    """Build a GeneratorOutcome dict from a compliance entry.

    Args:
        entry: Compliance JSONL entry.
        session_id: Current session ID.

    Returns:
        Dict matching GeneratorOutcome schema.
    """
    now = datetime.now(tz=UTC).isoformat()

    # Extract generator name from tool input
    tool_input = entry.get("tool_input", "")
    gen_name = "unknown"
    if isinstance(tool_input, str):
        match = _GEN_PATTERN.search(tool_input)
        if match:
            gen_name = match.group(0).replace(".py", "")
    elif isinstance(tool_input, dict):
        cmd = tool_input.get("command", "")
        if isinstance(cmd, str):
            match = _GEN_PATTERN.search(cmd)
            if match:
                gen_name = match.group(0).replace(".py", "")

    hook_decision = entry.get("hook_decision", "allow")
    success = hook_decision == "allow"

    return {
        "timestamp": now,
        "session_id": session_id,
        "generator_name": gen_name,
        "generator_path": f"scripts/aco/generators/{gen_name}.py",
        "action": "generate",
        "success": success,
        "duration_seconds": 0.0,
        "output_loc": 0,
        "validation_passed": None,
        "error_type": None,
        "error_message": None if success else f"hook_decision={hook_decision}",
        "context": {"source": "generator_learning_hook", "auto_captured": "true"},
    }


def _record_outcomes(outcomes: list[dict[str, Any]]) -> int:
    """Append outcomes to learning JSONL.

    Args:
        outcomes: List of outcome dicts.

    Returns:
        Number of outcomes recorded.
    """
    if not outcomes:
        return 0

    try:
        _LEARNING_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with _LEARNING_JSONL.open("a", encoding="utf-8") as f:
            for outcome in outcomes:
                f.write(json.dumps(outcome, ensure_ascii=False) + "\n")
        return len(outcomes)
    except OSError:
        return 0


def main() -> None:
    """Entry point for Stop hook."""
    try:
        data = _read_stdin()
        session_id = data.get("session_id", "")
        if not session_id:
            sys.exit(ALLOW)

        gen_entries = _scan_compliance_for_generators(session_id)
        if gen_entries:
            outcomes = [_build_outcome(e, session_id) for e in gen_entries]
            count = _record_outcomes(outcomes)
            if count > 0:
                print(
                    f"Generator learning: recorded {count} outcomes",
                    file=sys.stderr,
                )
    except Exception:
        pass  # fail-open: never block shutdown
    sys.exit(ALLOW)


if __name__ == "__main__":
    main()
