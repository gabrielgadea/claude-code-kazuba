#!/usr/bin/env python3
"""Thin stdin wrapper for CODE-FIRST pipeline validator — PreToolUse hook.

Event: PreToolUse
Matcher: Task
Purpose: Validates CODE-FIRST pipeline state before ANTT skill invocation.

Protocol:
  1. Reads JSON from stdin (Claude Code hook format)
  2. Filters by tool_name (only "Task")
  3. Delegates to code_first_pipeline_validator.hook_pre_tool_use()
  4. Writes result JSON to stdout
  5. Exits with appropriate code

Exit codes:
    0 - ALLOW (validation passed or non-relevant tool)
    1 - BLOCK (pipeline validation failed)

stdin: {"tool_name": "Task", "tool_input": {"prompt": "..."}}
stdout: {"decision": "allow"} or {"decision": "block", "reason": "..."}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Exit codes (Claude Code hook protocol)
ALLOW = 0
BLOCK = 1

# Only validate Task tool calls (skill invocations)
VALIDATED_TOOLS = frozenset({"Task"})

# Module-level path setup — executed once at import, not inside delegate_validation.
_HOOK_DIR = Path(__file__).parent
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))


def parse_stdin() -> dict:
    """Parse JSON from stdin. Returns empty dict on failure (fail-open)."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        return {}


def should_validate(tool_name: str) -> bool:
    """Check if tool_name should trigger CODE-FIRST validation."""
    return tool_name in VALIDATED_TOOLS


def delegate_validation(context: dict) -> dict:
    """Delegate to code_first_pipeline_validator.hook_pre_tool_use().

    Returns validation result dict with 'action' key.
    """
    import code_first_pipeline_validator

    return code_first_pipeline_validator.hook_pre_tool_use(context)


def map_exit_code(action: str) -> int:
    """Map validator action to exit code. BLOCK=1, everything else=0."""
    if action == "BLOCK":
        return BLOCK
    return ALLOW


def main() -> None:
    """Entry point for PreToolUse hook."""
    try:
        # ANTT_HOOK_PROFILE guard (fail-open)
        try:
            _aco_dir = str(Path(__file__).resolve().parents[3] / "scripts" / "aco")
            if _aco_dir not in sys.path:
                sys.path.insert(0, _aco_dir)
            from hook_profile_manager import is_hook_enabled  # type: ignore[import-not-found]

            if not is_hook_enabled("code_first_validator"):
                sys.exit(ALLOW)
        except Exception:
            pass  # fail-open: if manager unavailable, proceed normally

        data = parse_stdin()

        # Early exit for non-relevant tools
        tool_name = data.get("tool_name", "")
        if not should_validate(tool_name):
            sys.exit(ALLOW)

        # Extract prompt context for validator
        tool_input = data.get("tool_input", {})
        prompt = tool_input.get("prompt", "")

        # Build context for pipeline validator
        # Detect skill name from prompt (heuristic: first antt-* word)
        skill_name = ""
        for word in prompt.lower().split():
            if word.startswith("antt-"):
                skill_name = word
                break

        context = {
            "skill": skill_name,
            "messages": [{"content": prompt}] if prompt else [],
        }

        result = delegate_validation(context)
        action = result.get("action", "ALLOW")

        # Emit result to stdout
        decision = "block" if action == "BLOCK" else "allow"
        output = {"decision": decision}
        if action == "BLOCK":
            output["reason"] = result.get("reason", "Pipeline validation failed")

        json.dump(output, sys.stdout)

        # Map to exit code
        exit_code = map_exit_code(action)
        if exit_code == BLOCK:
            print(
                f"\nCODE-FIRST: BLOCK -- {result.get('reason', '')}",
                file=sys.stderr,
            )

        sys.exit(exit_code)

    except ImportError as e:
        # Validator not available — fail-open
        print(f"CODE-FIRST validator import error (fail-open): {e}", file=sys.stderr)
        sys.exit(ALLOW)
    except Exception as e:
        # Unexpected error — fail-open
        print(f"CODE-FIRST validator error (fail-open): {e}", file=sys.stderr)
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
