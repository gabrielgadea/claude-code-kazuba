#!/usr/bin/env python3
"""SessionStart Hook: Cross-Session Guidance Injection.

Injects pending items and reminders from previous sessions into the
current session's additionalContext. Works with GuidanceManager which
is populated by stop_transcript_hook.py on session Stop.

Hook Type: SessionStart
Timeout: 5000ms
Exit: Always 0 (never blocks session start)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add hooks root to path for imports
_hooks_dir = Path(__file__).parent.parent.parent
if str(_hooks_dir) not in sys.path:
    sys.path.insert(0, str(_hooks_dir))


def _format_output(context: str = "") -> str:
    """Format SessionStart hook output per Anthropic schema."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            },
            "suppressOutput": True,
        },
        ensure_ascii=False,
    )


# Pre-computed empty output (avoids json.dumps on common no-context path)
_EMPTY_OUTPUT = json.dumps(
    {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "",
        },
        "suppressOutput": True,
    },
    ensure_ascii=False,
)

_GREETING_PROTOCOL = (
    "SessionStart hook additional context: "
    "MANDATORY FIRST ACTION — Before responding to ANY user message, "
    "you MUST greet the user and present a summary of the previous session "
    "(based on the guidance below). Ask if they want to continue where they "
    "left off, follow the suggested next steps, or work on something different. "
    "This greeting is BLOCKING — do NOT skip it even if the user's first "
    "message is a question or command. Present the summary FIRST, then address "
    "their request."
)


def main() -> None:
    """Inject guidance from previous sessions."""
    # Verificar source do evento: não reinjetar após compactação (evita context loop)
    # SessionStart dispara com source="compact" após auto-compact — pular injeção nesses casos
    try:
        raw = sys.stdin.read().strip()
        if raw:
            data = json.loads(raw)
            source = data.get("source", "startup")
            if source in ("compact", "resume"):
                print(_EMPTY_OUTPUT)
                return
    except Exception:
        pass  # Em caso de erro no parse, proceder com injeção normal

    context = ""
    try:
        from learning.guidance.guidance_manager import GuidanceManager

        manager = GuidanceManager()
        guidance_text = manager.format_for_injection()

        if guidance_text:
            count = manager.mark_all_delivered()
            manager.clear_stale()
            logger.info(f"Injected {count} guidance entries")
            context = f"{_GREETING_PROTOCOL}\n\n{guidance_text}"

    except Exception as e:
        logger.error(f"Guidance injection failed: {e}")

    if not context:
        print(_EMPTY_OUTPUT)
    else:
        print(_format_output(context))


if __name__ == "__main__":
    main()
