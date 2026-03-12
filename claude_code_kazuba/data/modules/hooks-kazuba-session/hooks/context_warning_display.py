#!/usr/bin/env python3
"""
Context Warning Display - SessionStart hook to display context warnings.

Event: SessionStart
Purpose: Read and display any pending context warnings from context_monitor.

Since UserPromptSubmit hooks cannot display output reliably (Claude Code bug #13912),
this SessionStart hook reads the warning file and displays it where stderr works.

Exit codes:
  0 - Allow (always)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ALLOW = 0
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
WARNING_FILE = PROJECT_DIR / ".claude" / "context_warning.txt"


def main() -> None:
    """Display any pending context warnings."""
    try:
        if WARNING_FILE.exists():
            content = WARNING_FILE.read_text().strip()
            if content:
                # Display warning via stderr (works in SessionStart)
                print(f"\n{'=' * 60}", file=sys.stderr)
                print("⚠️  CONTEXT WARNING FROM PREVIOUS SESSION", file=sys.stderr)
                print("=" * 60, file=sys.stderr)
                print(content, file=sys.stderr)
                print("=" * 60, file=sys.stderr)
                print("", file=sys.stderr)

                # Output JSON for hook system (Anthropic-compliant SessionStart schema)
                print(
                    json.dumps(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": "SessionStart",
                                "additionalContext": f"[context_warning] {content}",
                            },
                            "suppressOutput": True,
                        }
                    )
                )

    except OSError:
        pass  # Silently ignore file read errors

    sys.exit(ALLOW)


if __name__ == "__main__":
    main()
