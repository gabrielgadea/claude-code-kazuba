#!/usr/bin/env python3
"""SIAC PreToolUse Validator — Motor 1 AST audit before file write.

Event: PreToolUse
Matcher: Write, Edit
Purpose: Validates Python code via AST analysis BEFORE it reaches disk.

This hook intercepts Write/Edit tool calls, extracts the Python content
from tool_input, and runs Motor 1 (AST Audit) against it. Violations
are caught before the file is written, implementing the Self-Healing
pattern from Monografia II.A (REPL Autonomo).

Protocol:
  1. Reads JSON from stdin (Claude Code PreToolUse format)
  2. Filters: only Write/Edit on *.py files
  3. Extracts content from tool_input.content (Write) or tool_input.new_string (Edit)
  4. Runs Motor 1 audit_content() against the extracted code
  5. Writes result JSON to stdout
  6. Exit code: 0=ALLOW, 1=BLOCK (errors found)

Design decisions:
  - Errors (mutable_default, bare_except, etc.) -> BLOCK (exit 1)
  - Warnings (missing_type_hints, deep_nesting) -> ALLOW (exit 0)
  - Fail-open: ImportError or unexpected errors -> ALLOW (exit 0)
  - Edit tool: validates new_string only (partial content, may not parse as full module)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Exit codes (Claude Code hook protocol)
ALLOW = 0
BLOCK = 1

# Tools that trigger PreToolUse AST validation
VALIDATED_TOOLS = frozenset({"Write", "Edit"})

# Module-level path setup — executed once at import, not on every tool call.
_HOOK_DIR = Path(__file__).parent
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))


def run_motor1_audit(content: str, file_path: str) -> dict:
    """Run Motor 1 AST audit on content string.

    Imports motor1_ast_audit as sibling module and calls audit_content().

    Args:
        content: Python source code to validate.
        file_path: Virtual file path for error context.

    Returns:
        Dict with action (0/1/2), violations list, and summary.

    Raises:
        ImportError: If motor1_ast_audit is not available.
    """
    import motor1_ast_audit

    result = motor1_ast_audit.audit_content(content, file_path)

    # Map result to action code
    action = 0  # ALLOW
    if result.has_errors:
        action = 1  # BLOCK
    elif result.has_warnings:
        action = 2  # WARN

    return {
        "action": action,
        "motor": "Motor1_AST_PreToolUse",
        "file_path": file_path,
        "violations": [v.to_dict() for v in result.violations],
        "summary": result.to_dict()["summary"],
    }


def main() -> None:
    """PreToolUse hook entry point."""
    try:
        # Parse stdin
        try:
            data = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError, ValueError):
            data = {}

        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})

        # Early exit: not a Write/Edit tool
        if tool_name not in VALIDATED_TOOLS:
            sys.exit(ALLOW)

        # Extract file path
        file_path = tool_input.get("file_path", "")

        # Early exit: not a Python file
        if not file_path.endswith(".py"):
            sys.exit(ALLOW)

        # Extract content to validate
        # Write: tool_input.content
        # Edit: tool_input.new_string (partial — may not parse as full module)
        content = tool_input.get("content", "") or tool_input.get("new_string", "")

        if not content.strip():
            sys.exit(ALLOW)

        # Run Motor 1 AST audit on content
        result = run_motor1_audit(content, file_path)
        action = result.get("action", 0)

        # Emit result JSON
        json.dump(result, sys.stdout)

        # BLOCK only on errors, WARN is informational (ALLOW)
        if action == 1:
            print(
                f"\nSIAC PreToolUse: BLOCK — AST violations in {file_path}",
                file=sys.stderr,
            )
            sys.exit(BLOCK)
        elif action == 2:
            print(
                f"\nSIAC PreToolUse: WARN — non-critical issues in {file_path}",
                file=sys.stderr,
            )

        sys.exit(ALLOW)

    except ImportError as e:
        # Motor 1 not available — fail-open
        print(f"SIAC PreToolUse import error (fail-open): {e}", file=sys.stderr)
        sys.exit(ALLOW)
    except Exception as e:
        # Unexpected error — fail-open
        print(f"SIAC PreToolUse error (fail-open): {e}", file=sys.stderr)
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
