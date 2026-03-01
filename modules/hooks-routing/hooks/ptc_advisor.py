#!/usr/bin/env python3
"""PTC Advisor — PreToolUse hook that suggests Programmatic Tool Calling sequences.

Event: PreToolUse (Task tool, L2+ CILA level only)
Purpose: Generates PTC program suggestion and injects as additionalContext.

The advisor is NON-BLOCKING — it suggests but never blocks.
Claude decides whether to follow the PTC suggestion or use conversational approach.

Protocol:
    1. Read JSON from stdin (tool_name, tool_input).
    2. Classify intent via CILA patterns.
    3. If CILA L2+, synthesise a PTC program.
    4. Output {additionalContext: <advisory>} to stdout.
    5. Always exit 0 (fail-open).

CILA Levels:
    L0 — Direct response (no code needed)
    L1 — PAL: generate simple calculation/formatting code
    L2 — Tool-Augmented: DISCOVER → existing script → EXECUTE → SYNTHESIZE
    L3 — Pipelines: verify state/deps then run pipeline
    L4 — Agent Loops: ReAct cycle with self-correction
    L5 — Self-Modifying: capability evolution
    L6 — Multi-Agent: TeamCreate → parallel agents
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Any

ALLOW: int = 0

# Minimum CILA level for PTC suggestions
MIN_PTC_LEVEL: int = 2


# ---------------------------------------------------------------------------
# CILA Classification
# ---------------------------------------------------------------------------

# Keyword maps: CILA level -> (exclusive_keywords, shared_keywords)
_CILA_KEYWORDS: dict[int, tuple[list[str], list[str]]] = {
    6: (
        ["multi-agent", "agent team", "teamcreate", "parallel agents"],
        ["team", "parallel", "concurrent agents"],
    ),
    5: (
        ["self-modifying", "capability evolver", "self-improve"],
        ["evolve", "self-update", "modify skill"],
    ),
    4: (
        ["react cycle", "agent loop", "self-correction", "retry loop"],
        ["loop", "iterate", "agent"],
    ),
    3: (
        ["pipeline", "pipeline_state", "f1-f9", "phase runner"],
        ["pipeline", "orchestrate", "phase"],
    ),
    2: (
        ["discover", "existing script", "tool-augmented", "execute script"],
        ["search codebase", "find existing", "run script", "tool call"],
    ),
    1: (
        ["generate code", "write function", "calculate", "format output"],
        ["code", "function", "script", "calculate"],
    ),
}

_DEFAULT_CILA_LEVEL: int = 0


@dataclass(frozen=True)
class CILAClassification:
    """Result of CILA intent classification."""

    level: int
    confidence: float
    routing_strategy: str
    matched_keywords: list[str]

    def is_ptc_eligible(self) -> bool:
        """True if this classification should receive a PTC suggestion."""
        return self.level >= MIN_PTC_LEVEL


def _extract_keywords(text: str) -> list[str]:
    """Extract lowercase words from text for keyword matching."""
    return re.findall(r"[a-z0-9_/-]+", text.lower())


def classify_intent(prompt: str) -> CILAClassification:
    """Classify prompt into a CILA level using weighted keyword scoring.

    Higher CILA levels are checked first (exclusive match wins immediately).
    Shared keywords contribute a score of 1.0; exclusive keywords score 2.0.
    The level with the highest score (>= 1.0) is returned.

    Args:
        prompt: The task description text.

    Returns:
        CILAClassification with level, confidence, routing_strategy, and
        matched keywords.
    """
    if not prompt or not prompt.strip():
        return CILAClassification(
            level=0,
            confidence=1.0,
            routing_strategy="direct_response",
            matched_keywords=[],
        )

    prompt_lower = prompt.lower()
    best_level = _DEFAULT_CILA_LEVEL
    best_score = 0.0
    best_matches: list[str] = []

    # Check levels from highest to lowest
    for level in sorted(_CILA_KEYWORDS.keys(), reverse=True):
        exclusive_kws, shared_kws = _CILA_KEYWORDS[level]
        score = 0.0
        matches: list[str] = []

        for kw in exclusive_kws:
            if kw in prompt_lower:
                score += 2.0
                matches.append(kw)

        for kw in shared_kws:
            if kw in prompt_lower:
                score += 1.0
                matches.append(kw)

        if score > best_score:
            best_score = score
            best_level = level
            best_matches = matches

    strategy = _routing_strategy(best_level)
    confidence = min(1.0, best_score / 2.0) if best_score > 0 else 1.0

    return CILAClassification(
        level=best_level,
        confidence=confidence,
        routing_strategy=strategy,
        matched_keywords=best_matches,
    )


def _routing_strategy(level: int) -> str:
    """Map CILA level to a canonical routing strategy name."""
    strategies: dict[int, str] = {
        0: "direct_response",
        1: "pal_code_generation",
        2: "tool_augmented",
        3: "pipeline_execution",
        4: "agent_loop",
        5: "self_modifying",
        6: "multi_agent",
    }
    return strategies.get(level, "direct_response")


# ---------------------------------------------------------------------------
# PTC Program Synthesis
# ---------------------------------------------------------------------------

# Templates per CILA level: list of steps in the PTC sequence
_PTC_TEMPLATES: dict[int, list[str]] = {
    2: ["DISCOVER", "CHECK_EXISTING", "EXECUTE", "SYNTHESIZE"],
    3: ["CHECK_PIPELINE_STATE", "EXECUTE_PIPELINE", "EVALUATE_OUTPUT", "SYNTHESIZE"],
    4: [
        "DISCOVER",
        "PLAN",
        "EXECUTE",
        "OBSERVE",
        "SELF_CORRECT",
        "VALIDATE",
        "SYNTHESIZE",
    ],
    5: ["DISCOVER_CAPABILITIES", "DESIGN_EXTENSION", "IMPLEMENT", "TEST", "PERSIST"],
    6: [
        "TEAM_CREATE",
        "TASK_DEFINE",
        "SPAWN_AGENTS",
        "MONITOR",
        "SYNTHESIZE",
        "TEAM_DELETE",
    ],
}


@dataclass(frozen=True)
class PTCProgram:
    """A synthesised PTC program for a given CILA level."""

    cila_level: int
    strategy: str
    steps: list[str]
    estimated_token_savings_pct: int

    def format_sequence(self) -> str:
        """Return steps formatted as a readable sequence string."""
        return " → ".join(self.steps)


def synthesize_program(cila_level: int, strategy: str) -> PTCProgram:
    """Build a PTC program for the given CILA level and routing strategy.

    Args:
        cila_level: CILA classification level (2-6 for PTC-eligible tasks).
        strategy: Routing strategy name.

    Returns:
        PTCProgram with the recommended step sequence.
    """
    steps = _PTC_TEMPLATES.get(
        cila_level, _PTC_TEMPLATES.get(2, ["DISCOVER", "EXECUTE", "SYNTHESIZE"])
    )
    # Token savings estimate: higher CILA levels benefit more from PTC structure
    savings = min(50, 20 + (cila_level - 2) * 8)
    return PTCProgram(
        cila_level=cila_level,
        strategy=strategy,
        steps=list(steps),
        estimated_token_savings_pct=savings,
    )


def format_program_advisory(program: PTCProgram) -> str:
    """Render a PTC program as a human-readable advisory string.

    Args:
        program: The synthesised PTC program.

    Returns:
        Multi-line string suitable for injection as additionalContext.
    """
    lines = [
        f"PTC Advisory — CILA L{program.cila_level} ({program.strategy.upper()})",
        f"Recommended sequence: {program.format_sequence()}",
        f"Estimated token savings: ~{program.estimated_token_savings_pct}%",
        "",
        "Steps:",
    ]
    for i, step in enumerate(program.steps, 1):
        lines.append(f"  {i}. {step}")
    lines += [
        "",
        "This is a suggestion only — adapt as needed for the task.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hook entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """PreToolUse hook entry point.

    Reads stdin, classifies intent, and optionally injects PTC advisory.
    Always exits 0 (fail-open).
    """
    try:
        try:
            data: dict[str, Any] = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError, ValueError):
            sys.exit(ALLOW)

        tool_name = data.get("tool_name", "")

        # Only advise on Task tool invocations
        if tool_name != "Task":
            sys.exit(ALLOW)

        tool_input = data.get("tool_input", {})
        prompt: str = tool_input.get("prompt", "")

        if not prompt.strip():
            sys.exit(ALLOW)

        classification = classify_intent(prompt)

        # Only suggest PTC for L2+
        if not classification.is_ptc_eligible():
            sys.exit(ALLOW)

        program = synthesize_program(
            cila_level=classification.level,
            strategy=classification.routing_strategy,
        )
        advisory = format_program_advisory(program)

        if advisory:
            json.dump({"additionalContext": advisory}, sys.stdout)

        sys.exit(ALLOW)

    except Exception as exc:
        # Fail-open: PTC advice is optional, never block Claude Code
        print(f"[ptc_advisor] fail-open: {exc}", file=sys.stderr)
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
