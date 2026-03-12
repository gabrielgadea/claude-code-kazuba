#!/usr/bin/env python3
"""Post-Compaction Rules Reinjector — preserves critical rules across compaction.

Injects ultra-compact essential rules (~200 tokens) as additionalContext
so they survive context compaction. Runs as a pre_compact hook to ensure
rules are part of the compacted context.

Protocol: stdin JSON → stdout JSON with additionalContext → exit 0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ============================================================================
# Compact rules (<=200 tokens target)
# ============================================================================

# These rules are the absolute minimum that must survive compaction.
# They represent the most critical invariants of the system.
_COMPACT_RULES = """\
CODE-FIRST: DISCOVER→EXECUTE→SYNTHESIZE (never analyze without script).
CILA: Check intent level before tool selection (L0=direct, L2=tools, L3+=pipeline).
PIPELINE: For 50500/50505 processes, verify pipeline_state BEFORE activating skills.
ZERO-HALLUCINATION: Never invent numbers, citations, or TCU/ANTT references. Read sources first.
LOCAL-CACHE-FIRST: Check .local-cache/knowledge.json before Cipher MCP (saves ~800 tokens/call).
QUALITY: Ruff 0 errors, coverage >=80%, complexity <=10/fn.
"""

# Path to optional custom rules file (overrides built-in if exists)
_CUSTOM_RULES_PATH = Path(".claude/hooks/lifecycle/compact_rules.json")


def load_compact_rules() -> str:
    """Load compact rules from custom file or use built-in.

    Returns:
        Rules text to inject as additionalContext.
    """
    if _CUSTOM_RULES_PATH.exists():
        try:
            data = json.loads(_CUSTOM_RULES_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "rules" in data:
                return str(data["rules"])
        except (json.JSONDecodeError, OSError):
            pass  # Fall through to built-in
    return _COMPACT_RULES


def build_reinjection_context(rules: str) -> dict[str, str]:
    """Build the additionalContext dict for reinjection.

    Args:
        rules: Rules text to inject.

    Returns:
        Dict with additionalContext key.
    """
    return {
        "additionalContext": (f"[CRITICAL RULES — preserved across compaction]\n{rules.strip()}\n[END CRITICAL RULES]"),
    }


def main() -> None:
    """Pre-compact hook entry point.

    Reads stdin (compaction event), outputs additionalContext with rules.
    Always exits 0 (never blocks compaction).
    """
    try:
        # Drain stdin (required by hook protocol, but data is unused)
        sys.stdin.read()

        rules = load_compact_rules()
        output = build_reinjection_context(rules)
        sys.stdout.write(json.dumps(output))
        sys.exit(0)

    except Exception:
        # Fail-open: never block compaction
        sys.exit(0)


if __name__ == "__main__":
    main()
