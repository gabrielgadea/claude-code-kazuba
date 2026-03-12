#!/usr/bin/env python3
"""Thin stdin wrapper for QA Loop -- PostToolUse hook.

Event: PostToolUse
Matcher: Write|Edit|MultiEdit
Purpose: Quick quality check on written Python files.

Performs a lightweight py_compile syntax check on files written/edited
by Claude Code. This avoids running the full QA loop (which uses asyncio,
learning bridge, etc.) while still catching syntax errors immediately.

Exit codes:
    0 - ALLOW (file OK or non-Python)
    1 - BLOCK (critical syntax error)
"""

from __future__ import annotations

import json
import py_compile
import sys
from pathlib import Path

ALLOW = 0
BLOCK = 1

QA_TOOLS = {"Write", "Edit", "MultiEdit"}


def check_python_syntax(file_path: str) -> tuple[bool, str]:
    """Check if a Python file has valid syntax.

    Uses py_compile to catch syntax errors without executing the file.

    Args:
        file_path: Absolute path to the Python file to check.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    try:
        py_compile.compile(file_path, doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)
    except (OSError, ValueError) as e:
        return False, str(e)


def main() -> None:
    """Entry point for PostToolUse hook.

    Reads JSON from stdin, checks if the tool wrote a Python file,
    and validates syntax. Exits with ALLOW (0) or BLOCK (1).
    """
    try:
        # Read stdin
        try:
            data = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError):
            data = {}

        tool_name = data.get("tool_name", "")
        if tool_name not in QA_TOOLS:
            sys.exit(ALLOW)

        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if not file_path or not file_path.endswith(".py"):
            sys.exit(ALLOW)

        # Check if file exists
        if not Path(file_path).exists():
            sys.exit(ALLOW)

        # Quick syntax check
        is_valid, error_msg = check_python_syntax(file_path)

        result = {
            "hook": "qa_hook_entry",
            "file_path": file_path,
            "syntax_valid": is_valid,
        }

        if not is_valid:
            result["error"] = error_msg
            json.dump(result, sys.stdout)
            print(
                f"\nQA: Syntax error in {file_path}: {error_msg}",
                file=sys.stderr,
            )
            sys.exit(BLOCK)

        json.dump(result, sys.stdout)
        sys.exit(ALLOW)

    except Exception as e:
        print(f"QA hook error (fail-open): {e}", file=sys.stderr)
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
