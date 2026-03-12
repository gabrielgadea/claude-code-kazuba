#!/usr/bin/env python3
"""PTC Advisor — PreToolUse hook that suggests Programmatic Tool Calling sequences.

Event: PreToolUse (Task tool, L2+ only)
Purpose: Generates PTC program suggestion and injects as additionalContext.

The advisor is NON-BLOCKING — it suggests but never blocks.
Claude decides whether to follow the PTC suggestion or use conversational approach.

Protocol:
  1. Reads JSON from stdin (tool_name, tool_input)
  2. Classifies intent via CILA patterns
  3. If L2+, synthesizes PTC program
  4. Outputs additionalContext JSON with PTC advisory
  5. Always exits 0
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ALLOW = 0

# Minimum CILA level for PTC suggestions
MIN_PTC_LEVEL = 2

# Module-level path setup — executed once at import, not on every hook call
_ROUTING_DIR = Path(__file__).parent.parent / "routing"
_SYNTHESIS_DIR = Path(__file__).parent

for _dir in (_ROUTING_DIR, _SYNTHESIS_DIR):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

try:
    from intent_patterns import classify_intent  # type: ignore[import-untyped]
    from program_synthesizer import (  # type: ignore[import-untyped]
        format_program_advisory,
        synthesize_program,
    )

    _PTC_AVAILABLE = True
except ImportError:
    _PTC_AVAILABLE = False


def main() -> None:
    """PreToolUse hook entry point."""
    try:
        # Parse stdin
        try:
            data = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError, ValueError):
            sys.exit(ALLOW)

        tool_name = data.get("tool_name", "")

        # Only advise on Task tool calls
        if tool_name != "Task":
            sys.exit(ALLOW)

        tool_input = data.get("tool_input", {})
        prompt = tool_input.get("prompt", "")

        if not prompt.strip():
            sys.exit(ALLOW)

        # Module-level imports — no path manipulation needed here
        if not _PTC_AVAILABLE:
            sys.exit(ALLOW)

        classification: Any = classify_intent(prompt)  # type: ignore[possibly-unbound]

        # Only suggest PTC for L2+
        if classification.level < MIN_PTC_LEVEL:
            sys.exit(ALLOW)

        # Synthesize PTC program
        program = synthesize_program(  # type: ignore[possibly-unbound]
            cila_level=classification.level,
            strategy=classification.routing_strategy,
        )

        advisory = format_program_advisory(program)  # type: ignore[possibly-unbound]
        if advisory:
            json.dump({"additionalContext": advisory}, sys.stdout)

        sys.exit(ALLOW)

    except Exception as e:
        # Fail-open: PTC advice is optional
        print(f"PTC advisor error (fail-open): {e}", file=sys.stderr)
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
