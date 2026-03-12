#!/usr/bin/env python3
"""Thin stdin wrapper for Compliance Metrics Collector -- PostToolUse hook.

Event: PostToolUse
Matcher: Task|Bash|Write|Edit
Purpose: Collects compliance metrics per tool execution.

Protocol:
    1. Reads JSON from stdin (Claude Code hook format)
    2. Filters by tool_name relevance
    3. Delegates to compliance_collector.build_metric + persist_metric
    4. Exits 0 always (collector NEVER blocks)

Exit codes:
    0 - Always (collector is observational, never blocks)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Tools that are relevant for compliance tracking
_RELEVANT_TOOLS = frozenset({"Task", "Bash", "Write", "Edit"})

# Pre-computed paths — avoid per-call Path resolution
_HOOK_DIR = str(Path(__file__).parent)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ACO_DIR = str(_PROJECT_ROOT / "scripts" / "aco")


def main() -> None:
    """Entry point for PostToolUse compliance collection hook."""
    try:
        # ANTT_HOOK_PROFILE guard (fail-open)
        try:
            if _ACO_DIR not in sys.path:
                sys.path.insert(0, _ACO_DIR)
            from hook_profile_manager import is_hook_enabled

            if not is_hook_enabled("compliance_collector"):
                sys.exit(0)
        except Exception:
            pass  # fail-open: if manager unavailable, proceed normally

        # Read stdin
        try:
            data = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError, ValueError):
            sys.exit(0)

        # Early exit for irrelevant tools
        tool_name = data.get("tool_name", "")
        if tool_name not in _RELEVANT_TOOLS:
            sys.exit(0)

        # Import collector (sibling module)
        hook_dir = Path(__file__).parent
        if str(hook_dir) not in sys.path:
            sys.path.insert(0, str(hook_dir))

        import compliance_collector

        metric = compliance_collector.build_metric(data)
        compliance_collector.persist_metric(metric)

    except Exception:
        pass  # Collector NEVER blocks

    sys.exit(0)


if __name__ == "__main__":
    main()
