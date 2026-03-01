"""UserPromptSubmit hook: classify intent and inject cognitive techniques.

Reads prompt from stdin JSON, classifies the intent into one of 8 categories,
selects appropriate reasoning techniques, and outputs additionalContext.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any

from claude_code_kazuba.hook_base import fail_open
from claude_code_kazuba.json_output import emit_json, user_prompt_output

# --- Intent categories ---
INTENTS: list[str] = [
    "code",
    "debug",
    "test",
    "refactor",
    "plan",
    "analysis",
    "creative",
    "general",
]

# Priority order for tiebreaking (lower index = higher priority)
INTENT_PRIORITY: dict[str, int] = {name: i for i, name in enumerate(INTENTS)}


# --- Keyword scoring ---
# exclusive=2.0 (unique to one intent), shared=1.0 (appears in multiple)
@dataclass(frozen=True)
class ScoredKeyword:
    """A keyword with its scoring weight."""

    word: str
    weight: float = 1.0


# Default keyword registry per intent
_DEFAULT_KEYWORDS: dict[str, list[ScoredKeyword]] = {
    "code": [
        ScoredKeyword("implement", 2.0),
        ScoredKeyword("create function", 2.0),
        ScoredKeyword("write code", 2.0),
        ScoredKeyword("add feature", 2.0),
        ScoredKeyword("build", 1.0),
        ScoredKeyword("develop", 1.0),
        ScoredKeyword("code", 1.0),
        ScoredKeyword("function", 1.0),
        ScoredKeyword("class", 1.0),
        ScoredKeyword("module", 1.0),
        ScoredKeyword("criar", 2.0),
        ScoredKeyword("implementar", 2.0),
        ScoredKeyword("escrever", 1.0),
    ],
    "debug": [
        ScoredKeyword("debug", 2.0),
        ScoredKeyword("fix bug", 2.0),
        ScoredKeyword("error", 2.0),
        ScoredKeyword("traceback", 2.0),
        ScoredKeyword("exception", 2.0),
        ScoredKeyword("stack trace", 2.0),
        ScoredKeyword("failing", 1.0),
        ScoredKeyword("broken", 1.0),
        ScoredKeyword("crash", 1.0),
        ScoredKeyword("bug", 1.0),
        ScoredKeyword("corrigir", 2.0),
        ScoredKeyword("erro", 2.0),
        ScoredKeyword("falha", 1.0),
    ],
    "test": [
        ScoredKeyword("write test", 2.0),
        ScoredKeyword("test case", 2.0),
        ScoredKeyword("unit test", 2.0),
        ScoredKeyword("pytest", 2.0),
        ScoredKeyword("coverage", 2.0),
        ScoredKeyword("assert", 1.0),
        ScoredKeyword("test", 1.0),
        ScoredKeyword("mock", 1.0),
        ScoredKeyword("fixture", 2.0),
        ScoredKeyword("teste", 2.0),
        ScoredKeyword("testar", 2.0),
    ],
    "refactor": [
        ScoredKeyword("refactor", 2.0),
        ScoredKeyword("clean up", 2.0),
        ScoredKeyword("simplify", 2.0),
        ScoredKeyword("extract method", 2.0),
        ScoredKeyword("rename", 1.0),
        ScoredKeyword("restructure", 2.0),
        ScoredKeyword("reorganize", 2.0),
        ScoredKeyword("deduplicate", 2.0),
        ScoredKeyword("refatorar", 2.0),
        ScoredKeyword("simplificar", 2.0),
        ScoredKeyword("limpar", 1.0),
    ],
    "plan": [
        ScoredKeyword("plan", 2.0),
        ScoredKeyword("design", 1.0),
        ScoredKeyword("architecture", 2.0),
        ScoredKeyword("roadmap", 2.0),
        ScoredKeyword("strategy", 2.0),
        ScoredKeyword("approach", 1.0),
        ScoredKeyword("how should", 1.0),
        ScoredKeyword("planejar", 2.0),
        ScoredKeyword("arquitetura", 2.0),
        ScoredKeyword("estrategia", 2.0),
    ],
    "analysis": [
        ScoredKeyword("analyze", 2.0),
        ScoredKeyword("explain", 2.0),
        ScoredKeyword("how does", 2.0),
        ScoredKeyword("what is", 1.0),
        ScoredKeyword("understand", 1.0),
        ScoredKeyword("investigate", 2.0),
        ScoredKeyword("trace", 1.0),
        ScoredKeyword("analisar", 2.0),
        ScoredKeyword("explicar", 2.0),
        ScoredKeyword("investigar", 2.0),
    ],
    "creative": [
        ScoredKeyword("generate", 1.0),
        ScoredKeyword("brainstorm", 2.0),
        ScoredKeyword("suggest", 1.0),
        ScoredKeyword("idea", 2.0),
        ScoredKeyword("creative", 2.0),
        ScoredKeyword("invent", 2.0),
        ScoredKeyword("imagine", 2.0),
        ScoredKeyword("gerar", 1.0),
        ScoredKeyword("ideia", 2.0),
        ScoredKeyword("criativo", 2.0),
    ],
    "general": [
        ScoredKeyword("help", 1.0),
        ScoredKeyword("show", 1.0),
        ScoredKeyword("list", 1.0),
        ScoredKeyword("check", 1.0),
        ScoredKeyword("ajuda", 1.0),
        ScoredKeyword("mostrar", 1.0),
    ],
}


# --- Technique definitions ---
@dataclass(frozen=True)
class Technique:
    """A cognitive technique with its applicable categories."""

    name: str
    categories: frozenset[str]
    template: str


# Technique registry
TECHNIQUES: list[Technique] = [
    Technique(
        name="chain_of_thought",
        categories=frozenset(INTENTS),
        template="Think step-by-step. Break down the problem before solving.",
    ),
    Technique(
        name="structured_output",
        categories=frozenset(["code", "test", "analysis", "plan"]),
        template="Structure your response with clear sections and code blocks.",
    ),
    Technique(
        name="constitutional_constraints",
        categories=frozenset(["code", "debug", "refactor", "test"]),
        template="Follow project coding standards. Validate before delivering.",
    ),
    Technique(
        name="few_shot_reasoning",
        categories=frozenset(["debug", "test", "creative"]),
        template="Consider multiple approaches. Evaluate trade-offs explicitly.",
    ),
    Technique(
        name="self_validation",
        categories=frozenset(["debug", "refactor", "plan"]),
        template="After each step, verify: Does this match the requirement?",
    ),
    Technique(
        name="precision_hints",
        categories=frozenset(
            ["code", "refactor", "analysis", "creative", "plan", "general"]
        ),
        template="Be precise and concise. Avoid unnecessary elaboration.",
    ),
]


@dataclass(frozen=True)
class ClassificationResult:
    """Result of intent classification."""

    intent: str
    confidence: float
    scores: dict[str, float] = field(default_factory=dict)


def classify_intent(
    prompt: str,
    keywords: dict[str, list[ScoredKeyword]] | None = None,
) -> ClassificationResult:
    """Classify user prompt into an intent category.

    Uses weighted keyword scoring with tiebreak by priority.

    Args:
        prompt: The user's prompt text.
        keywords: Optional custom keyword registry. Defaults to built-in.

    Returns:
        ClassificationResult with intent, confidence, and per-intent scores.
    """
    if keywords is None:
        keywords = _DEFAULT_KEYWORDS

    prompt_lower = prompt.lower()
    scores: dict[str, float] = {}

    for intent, kw_list in keywords.items():
        score = 0.0
        for kw in kw_list:
            if kw.word.lower() in prompt_lower:
                score += kw.weight
        scores[intent] = score

    # Find max score
    max_score = max(scores.values()) if scores else 0.0

    if max_score == 0.0:
        return ClassificationResult(intent="general", confidence=0.0, scores=scores)

    # Tiebreak by priority (lower index wins)
    candidates = [
        intent for intent, score in scores.items() if score == max_score
    ]
    best = min(candidates, key=lambda i: INTENT_PRIORITY.get(i, 999))

    # Normalize confidence to 0-1 range (cap at 1.0)
    confidence = min(max_score / 5.0, 1.0)

    return ClassificationResult(intent=best, confidence=confidence, scores=scores)


def select_techniques(intent: str) -> list[Technique]:
    """Select applicable techniques for the classified intent.

    Args:
        intent: The classified intent category.

    Returns:
        List of techniques applicable to this intent.
    """
    return [t for t in TECHNIQUES if intent in t.categories]


def compose_context(intent: str, techniques: list[Technique]) -> str:
    """Compose additionalContext string from intent and techniques.

    Args:
        intent: The classified intent category.
        techniques: List of selected techniques.

    Returns:
        Formatted context string for injection.
    """
    lines: list[str] = [
        f"[prompt-enhancer] Intent: {intent}",
        "",
    ]
    for tech in techniques:
        lines.append(f"- [{tech.name}] {tech.template}")

    return "\n".join(lines)


@fail_open
def main() -> None:
    """Main hook entry point: read stdin, classify, emit context."""
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    data: dict[str, Any] = json.loads(raw)
    prompt: str = data.get("prompt", "")

    if not prompt.strip():
        sys.exit(0)

    # Classify intent
    result = classify_intent(prompt)

    # Select techniques
    techniques = select_techniques(result.intent)

    # Compose and emit
    context = compose_context(result.intent, techniques)
    output = user_prompt_output(context)
    emit_json(output)


if __name__ == "__main__":
    main()
