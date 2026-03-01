#!/usr/bin/env python3
"""Post-Compact Rules Reinjector — preserves critical rules across compaction.

Event: PreCompact
Purpose: Inject critical rules as additionalContext so they survive context
         compaction and remain active in the next conversation window.

Exit codes:
  0 - Allow (always — hooks must be fail-open)

Protocol: stdin JSON -> stdout JSON with additionalContext -> exit 0
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Default built-in rules injected when no rules_dir is found
# ---------------------------------------------------------------------------
_BUILTIN_RULES: list[str] = [
    "CODE-FIRST: DISCOVER→EXECUTE→SYNTHESIZE (never analyze without running code).",
    "FAIL-OPEN: All hooks exit 0 on error — never block compaction or tool execution.",
    "FROZEN MODELS: All Pydantic models use frozen=True for immutability.",
    "TYPE HINTS: Use modern syntax — list[T], T | None (not List[T], Optional[T]).",
    "TDD: Write tests before implementation. 90% coverage per file.",
    "HOOKS: Always exit 0 on error (fail-open). Exit 2 only for intentional block.",
]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ReinjectorConfig(BaseModel, frozen=True):
    """Immutable configuration for the PostCompact reinjector.

    Args:
        rules_dir: Directory containing .txt or .md files with critical rules.
        max_rules: Maximum number of rules to inject per compaction.
    """

    rules_dir: Path = Field(default=Path(".claude") / "hooks" / "rules")
    max_rules: int = Field(default=20, ge=1)


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def load_critical_rules(rules_dir: Path) -> list[str]:
    """Load critical rules from a directory of text files.

    Reads all .txt and .md files in rules_dir, treating each non-empty line
    as a rule. Falls back to built-in rules if the directory does not exist.

    Args:
        rules_dir: Directory containing rule files.

    Returns:
        List of rule strings.
    """
    if not rules_dir.exists() or not rules_dir.is_dir():
        return list(_BUILTIN_RULES)

    rules: list[str] = []
    patterns = ["*.txt", "*.md"]

    for pattern in patterns:
        for rule_file in sorted(rules_dir.glob(pattern)):
            try:
                content = rule_file.read_text(encoding="utf-8")
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        rules.append(stripped)
            except OSError:
                pass

    if not rules:
        return list(_BUILTIN_RULES)

    return rules


def format_additional_context(rules: list[str]) -> str:
    """Format a list of rules as an additionalContext string.

    Args:
        rules: List of rule strings to inject.

    Returns:
        Formatted context string.
    """
    if not rules:
        return "[CRITICAL RULES — no rules loaded]\n[END CRITICAL RULES]"

    body = "\n".join(f"- {rule}" for rule in rules)
    return (
        "[CRITICAL RULES — preserved across compaction]\n"
        f"{body}\n"
        "[END CRITICAL RULES]"
    )


# ---------------------------------------------------------------------------
# Hook entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """PreCompact hook entry point.

    Reads stdin (compaction event), loads critical rules, outputs
    additionalContext JSON. Always exits 0 (never blocks compaction).
    """
    try:
        raw = sys.stdin.read().strip()
        hook_data: dict[str, Any] = {}
        if raw:
            with contextlib.suppress(json.JSONDecodeError):
                hook_data = json.loads(raw)

        _ = hook_data  # consumed but not needed

        config = ReinjectorConfig()
        rules = load_critical_rules(config.rules_dir)
        rules = rules[: config.max_rules]
        context = format_additional_context(rules)

        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreCompact",
                "additionalContext": context,
            }
        }

        sys.stdout.write(json.dumps(output))
        sys.stdout.flush()

    except Exception:
        # Fail-open: never block compaction — silent failure
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
