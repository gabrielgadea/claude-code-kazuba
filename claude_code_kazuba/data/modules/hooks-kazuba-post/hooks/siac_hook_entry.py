#!/usr/bin/env python3
"""Thin stdin wrapper for SIAC Orchestrator -- PostToolUse hook.

Event: PostToolUse
Matcher: Write|Edit|MultiEdit
Purpose: Coordinates 4 SIAC motors for code quality validation.

Protocol:
  1. Reads JSON from stdin (Claude Code hook format)
  2. Filters by tool_name and file extension
  3. Delegates to siac_orchestrator.hook_post_tool_use()
  4. Writes result JSON to stdout
  5. Exits with appropriate code

Exit codes:
    0 - ALLOW (all motors pass or non-critical failure)
    1 - BLOCK (critical motor blocks)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Exit codes (Claude Code hook protocol)
ALLOW = 0
BLOCK = 1

# Tools that trigger SIAC validation
SIAC_TOOLS = frozenset({"Write", "Edit", "MultiEdit"})

# Module-level path setup — executed once at import, not inside main().
_HOOK_DIR = Path(__file__).parent
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))


def main() -> None:
    """Entry point for PostToolUse hook."""
    try:
        # Read stdin
        try:
            data = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError, ValueError):
            data = {}

        # Early exit for non-relevant tools
        tool_name = data.get("tool_name", "")
        if tool_name not in SIAC_TOOLS:
            sys.exit(ALLOW)

        # Extract file_path from tool_input
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        # Only validate Python files
        if not file_path.endswith(".py"):
            sys.exit(ALLOW)

        # Build context for SIAC orchestrator
        context = {
            "tool_name": tool_name,
            "file_path": file_path,
            "tool_input": tool_input,
        }

        # Import SIAC orchestrator (sibling module, path set at module level)
        import siac_orchestrator

        result = siac_orchestrator.hook_post_tool_use(context)
        action = result.get("action", 0)

        # Emit result JSON to stdout
        json.dump(result, sys.stdout)

        # Map SIAC action to exit code
        # action: 0=ALLOW, 1=BLOCK, 2=WARN (treat WARN as ALLOW)
        if action == 1:
            print(
                "\nSIAC: BLOCK -- critical motor failed",
                file=sys.stderr,
            )
            sys.exit(BLOCK)
        elif action == 2:
            print(
                "\nSIAC: WARN -- non-critical issue detected",
                file=sys.stderr,
            )

        sys.exit(ALLOW)

    except ImportError as e:
        # SIAC motors not available -- fail-open
        print(f"SIAC import error (fail-open): {e}", file=sys.stderr)
        sys.exit(ALLOW)
    except Exception as e:
        # Unexpected error -- fail-open
        print(f"SIAC error (fail-open): {e}", file=sys.stderr)
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
