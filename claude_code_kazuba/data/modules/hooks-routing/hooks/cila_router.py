"""UserPromptSubmit hook: CILA complexity classification and routing.

Classifies user prompts into complexity levels L0-L6 and injects routing
hints as additionalContext. Uses L0Cache for classification caching.

CILA = Complexity-Informed Layered Architecture
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

from claude_code_kazuba.hook_base import fail_open
from claude_code_kazuba.json_output import emit_json, user_prompt_output
from claude_code_kazuba.performance import L0Cache

# --- CILA Level Definitions ---
CILA_LEVELS: dict[int, str] = {
    0: "trivial",
    1: "simple",
    2: "standard",
    3: "complex",
    4: "advanced",
    5: "expert",
    6: "extreme",
}

CILA_ROUTING: dict[int, str] = {
    0: "Direct answer. No tools needed.",
    1: "Single tool call. Straightforward execution.",
    2: "Multi-step with single tool type. Sequential execution.",
    3: "Multi-tool coordination. Plan before executing.",
    4: "Planning + multi-tool + validation. Enter plan mode.",
    5: "Agent delegation recommended. Consider subagent.",
    6: "Full agent team orchestration. Use TeamCreate.",
}


@dataclass(frozen=True)
class CILASignal:
    """A signal pattern that contributes to complexity classification."""

    pattern: re.Pattern[str]
    level_contribution: int
    weight: float = 1.0


# Signal patterns for complexity detection
COMPLEXITY_SIGNALS: list[CILASignal] = [
    # L0 signals — trivial requests
    CILASignal(re.compile(r"^(what|when|where|who|which)\s", re.IGNORECASE), 0, 2.0),
    CILASignal(re.compile(r"^(show|list|print|display)\s", re.IGNORECASE), 0, 1.5),
    CILASignal(re.compile(r"^(yes|no|ok|sure|thanks)", re.IGNORECASE), 0, 3.0),
    # L1 signals — single tool
    CILASignal(re.compile(r"\b(read|open|check)\s+\w+\.\w+\b", re.IGNORECASE), 1, 1.5),
    CILASignal(re.compile(r"\b(run|execute)\s+(the\s+)?test", re.IGNORECASE), 1, 1.5),
    CILASignal(re.compile(r"\bfix\s+(the|this|a)\s+\w+", re.IGNORECASE), 1, 1.0),
    # L2 signals — multi-step
    CILASignal(re.compile(r"\b(and|then|also|after that)\b", re.IGNORECASE), 2, 0.5),
    CILASignal(re.compile(r"\b(update|modify|change)\s+\w+", re.IGNORECASE), 2, 1.0),
    CILASignal(re.compile(r"\b(add|create)\s+\w+\s+(to|in|for)\b", re.IGNORECASE), 2, 1.0),
    # L3 signals — complex multi-tool
    CILASignal(re.compile(r"\b(refactor|restructure|reorganize)\b", re.IGNORECASE), 3, 2.0),
    CILASignal(re.compile(r"\b(multiple|several|all)\s+(files?|modules?)\b", re.IGNORECASE), 3, 1.5),
    CILASignal(re.compile(r"\b(test|lint|format)\s+(and|then)\s+(test|lint|format)\b", re.IGNORECASE), 3, 1.0),
    # L4 signals — advanced planning
    CILASignal(re.compile(r"\b(architect|design|plan)\s+(a|the|new)\b", re.IGNORECASE), 4, 2.0),
    CILASignal(re.compile(r"\b(migration|migrate|upgrade)\b", re.IGNORECASE), 4, 2.0),
    CILASignal(re.compile(r"\b(integrate|integration)\b", re.IGNORECASE), 4, 1.5),
    # L5 signals — agent delegation
    CILASignal(re.compile(r"\b(research|investigate|explore)\s+\w+\s+and\b", re.IGNORECASE), 5, 2.0),
    CILASignal(re.compile(r"\b(compare|evaluate)\s+\w+\s+(options|alternatives|approaches)\b", re.IGNORECASE), 5, 2.0),
    CILASignal(re.compile(r"\bsubagent\b", re.IGNORECASE), 5, 3.0),
    # L6 signals — team orchestration
    CILASignal(re.compile(r"\b(team|swarm|parallel\s+agents?)\b", re.IGNORECASE), 6, 3.0),
    CILASignal(re.compile(r"\b(full\s+)?rewrite\b", re.IGNORECASE), 6, 2.0),
    CILASignal(re.compile(r"\b(greenfield|from\s+scratch)\b", re.IGNORECASE), 6, 2.5),
]

# Word count thresholds for complexity boost
WORD_COUNT_THRESHOLDS: list[tuple[int, int]] = [
    (100, 1),  # 100+ words → +1 level
    (200, 2),  # 200+ words → +2 levels
    (500, 3),  # 500+ words → +3 levels
]

# Cache for classification results
_classification_cache: L0Cache[int] = L0Cache(max_size=500, ttl_seconds=120.0)


@dataclass(frozen=True)
class CILAResult:
    """Result of CILA complexity classification."""

    level: int
    level_name: str
    routing_hint: str
    signal_scores: dict[int, float] = field(default_factory=dict)


def classify_complexity(prompt: str) -> CILAResult:
    """Classify prompt complexity using CILA framework.

    Args:
        prompt: The user's prompt text.

    Returns:
        CILAResult with level, name, routing hint, and per-level scores.
    """
    # Check cache first
    cache_key = prompt.strip().lower()[:200]
    cached = _classification_cache.get(cache_key)
    if cached is not None:
        level = cached
        return CILAResult(
            level=level,
            level_name=CILA_LEVELS.get(level, "unknown"),
            routing_hint=CILA_ROUTING.get(level, ""),
        )

    # Score each complexity level
    level_scores: dict[int, float] = {i: 0.0 for i in range(7)}

    for signal in COMPLEXITY_SIGNALS:
        matches = signal.pattern.findall(prompt)
        if matches:
            level_scores[signal.level_contribution] += len(matches) * signal.weight

    # Word count boost
    word_count = len(prompt.split())
    for threshold, boost in WORD_COUNT_THRESHOLDS:
        if word_count >= threshold:
            # Add boost to the highest non-zero level
            for lvl in range(6, -1, -1):
                if level_scores[lvl] > 0:
                    level_scores[lvl] += boost
                    break

    # Determine winning level: highest level with score > 0
    # Default to L1 if any tools would be needed, L0 if trivial
    winning_level = 0
    for lvl in range(6, -1, -1):
        if level_scores[lvl] > 0:
            winning_level = lvl
            break

    # If no signals matched but prompt is non-trivial, default to L1
    if winning_level == 0 and word_count > 10:
        winning_level = 1

    # Cache the result
    _classification_cache.set(cache_key, winning_level)

    return CILAResult(
        level=winning_level,
        level_name=CILA_LEVELS.get(winning_level, "unknown"),
        routing_hint=CILA_ROUTING.get(winning_level, ""),
        signal_scores=level_scores,
    )


def format_routing_context(result: CILAResult) -> str:
    """Format CILA result as additionalContext string.

    Args:
        result: The CILA classification result.

    Returns:
        Formatted context string.
    """
    lines: list[str] = [
        f"[cila-router] Complexity: L{result.level} ({result.level_name})",
        f"Routing: {result.routing_hint}",
    ]
    return "\n".join(lines)


@fail_open
def main() -> None:
    """Main hook entry point: read stdin, classify complexity, emit routing."""
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    data: dict[str, Any] = json.loads(raw)
    prompt: str = data.get("prompt", "")

    if not prompt.strip():
        sys.exit(0)

    # Classify complexity
    result = classify_complexity(prompt)

    # Emit routing context
    context = format_routing_context(result)
    output = user_prompt_output(context)
    emit_json(output)


if __name__ == "__main__":
    main()
