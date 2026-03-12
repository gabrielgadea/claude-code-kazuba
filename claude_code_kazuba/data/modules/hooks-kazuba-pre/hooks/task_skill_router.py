#!/usr/bin/env python3
"""
PreToolUse Hook for Task: Skill Auto-Router.

This hook intercepts Task tool calls to automatically route them
to the most appropriate skills based on content analysis.
Development skills are prioritized (80% target).

Exit codes:
  0 - Allow with skill suggestions
  1 - Block (invalid configuration)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass

# ============================================================================
# EXIT CODES
# ============================================================================

ALLOW = 0
BLOCK = 1

# ============================================================================
# SKILL DEFINITIONS
# ============================================================================


@dataclass(frozen=True)
class SkillDefinition:
    """Definition of a skill with routing keywords."""

    name: str
    category: str  # "development", "generic", "antt"
    priority: int  # 1-10, higher = more preferred
    keywords: tuple[str, ...]
    description: str


# Development skills (80% priority per plan)
DEVELOPMENT_SKILLS: tuple[SkillDefinition, ...] = (
    SkillDefinition(
        name="kazuba-developer",
        category="development",
        priority=10,
        keywords=("agent", "plugin", "rag", "kazuba", "basekazubaagent", "monorepo"),
        description="Agent and plugin development for Kazuba ecosystem",
    ),
    SkillDefinition(
        name="python-performance-optimization",
        category="development",
        priority=9,
        keywords=("profile", "optimize", "bottleneck", "performance", "cprofile", "memory"),
        description="Python code profiling and optimization",
    ),
    SkillDefinition(
        name="dev-deepener",
        category="development",
        priority=9,
        keywords=("deepen", "pln1", "pln2", "24 dim", "robustness", "development plan"),
        description="Development plan deepening (24 dimensions)",
    ),
    SkillDefinition(
        name="skill-writer",
        category="development",
        priority=8,
        keywords=("skill.md", "frontmatter", "write skill", "create skill"),
        description="Custom skill creation for Claude Code",
    ),
    SkillDefinition(
        name="prompt-engineering-patterns",
        category="development",
        priority=8,
        keywords=("prompt engineering", "llm optim", "chain of thought", "few-shot"),
        description="Advanced prompt engineering techniques",
    ),
    SkillDefinition(
        name="plan-amplifier",
        category="development",
        priority=8,
        keywords=("amplify", "exponential", "pln2", "32 dim", "multi-dimensional"),
        description="Exponential plan amplification",
    ),
)

# Generic skills
GENERIC_SKILLS: tuple[SkillDefinition, ...] = (
    SkillDefinition(
        name="research",
        category="generic",
        priority=7,
        keywords=("research", "investigate", "find information", "search"),
        description="Multi-source comprehensive research",
    ),
    SkillDefinition(
        name="academic-research-writer",
        category="generic",
        priority=7,
        keywords=("paper", "academic", "citations", "scientific", "ieee"),
        description="Academic research document writing",
    ),
    SkillDefinition(
        name="literature-review",
        category="generic",
        priority=7,
        keywords=("systematic review", "meta-analysis", "literature"),
        description="Systematic literature reviews",
    ),
)

# ANTT domain skills
ANTT_SKILLS: tuple[SkillDefinition, ...] = (
    SkillDefinition(
        name="antt-preliminary-analyzer",
        category="antt",
        priority=9,
        keywords=("50500", "50505", "processo", "process", "sei"),
        description="ANTT process preliminary analysis",
    ),
    SkillDefinition(
        name="antt-vote-architect",
        category="antt",
        priority=10,
        keywords=("voto", "deliberação", "vote", "relator"),
        description="Deliberative vote drafting",
    ),
    SkillDefinition(
        name="antt-legal-analyzer",
        category="antt",
        priority=9,
        keywords=("jurídico", "legal", "parecer", "pf-antt"),
        description="Legal analysis and opinions",
    ),
    SkillDefinition(
        name="antt-technical-analyzer",
        category="antt",
        priority=8,
        keywords=("técnico", "reequilíbrio", "fator d", "vpl", "wacc"),
        description="Technical economic-financial analysis",
    ),
    SkillDefinition(
        name="antt-chronology-builder",
        category="antt",
        priority=7,
        keywords=("cronologia", "timeline", "linha do tempo", "eventos"),
        description="Process chronology construction",
    ),
)

ALL_SKILLS = DEVELOPMENT_SKILLS + GENERIC_SKILLS + ANTT_SKILLS


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass(frozen=True)
class HookInput:
    """Parsed input from Claude Code PreToolUse(Task) event."""

    tool_name: str
    prompt: str
    agent_type: str

    @classmethod
    def from_stdin(cls) -> HookInput:
        """Parse JSON input from stdin."""
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {e}") from e

        tool_input = data.get("tool_input", {})

        return cls(
            tool_name=data.get("tool_name", ""),
            prompt=tool_input.get("prompt", ""),
            agent_type=tool_input.get("subagent_type", "general-purpose"),
        )


@dataclass(frozen=True)
class SkillMatch:
    """A matched skill with score."""

    skill: SkillDefinition
    score: float
    matched_keywords: tuple[str, ...]


@dataclass(frozen=True)
class RoutingResult:
    """Result of skill routing."""

    exit_code: int
    suggested_skills: tuple[str, ...]
    skill_scores: dict[str, float]
    dev_skill_ratio: float
    message: str

    def to_json(self) -> str:
        """Convert to JSON string for output."""
        return json.dumps(
            {
                "suggested_skills": list(self.suggested_skills),
                "skill_scores": self.skill_scores,
                "dev_skill_ratio": self.dev_skill_ratio,
            }
        )

    def emit(self) -> None:
        """Emit result and exit."""
        print(self.message, file=sys.stderr)
        print(self.to_json())
        sys.exit(self.exit_code)


# ============================================================================
# ROUTING LOGIC
# ============================================================================


def calculate_skill_score(skill: SkillDefinition, prompt: str) -> SkillMatch:
    """
    Calculate how well a skill matches the given prompt.

    Returns SkillMatch with score and matched keywords.
    """
    prompt_lower = prompt.lower()
    matched = [keyword for keyword in skill.keywords if keyword.lower() in prompt_lower]

    if not matched:
        return SkillMatch(skill=skill, score=0.0, matched_keywords=())

    # Base score from keyword matches
    keyword_score = len(matched) / len(skill.keywords)

    # Bonus for skill priority
    priority_bonus = skill.priority / 10.0 * 0.3

    # Bonus for development skills (80% priority)
    dev_bonus = 0.2 if skill.category == "development" else 0.0

    total_score = min(keyword_score + priority_bonus + dev_bonus, 1.0)

    return SkillMatch(
        skill=skill,
        score=total_score,
        matched_keywords=tuple(matched),
    )


def route_to_skills(prompt: str, max_skills: int = 5) -> list[SkillMatch]:
    """
    Route a prompt to the most appropriate skills.

    Returns list of SkillMatch sorted by score.
    """
    matches = []

    for skill in ALL_SKILLS:
        match = calculate_skill_score(skill, prompt)
        if match.score > 0:
            matches.append(match)

    # Sort by score descending
    matches.sort(key=lambda m: m.score, reverse=True)

    return matches[:max_skills]


def calculate_dev_ratio(skills: list[SkillMatch]) -> float:
    """Calculate ratio of development skills in matches."""
    if not skills:
        return 0.0

    dev_count = sum(1 for s in skills if s.skill.category == "development")
    return dev_count / len(skills)


def process_routing(hook_input: HookInput) -> RoutingResult:
    """
    Process skill routing for a Task tool call.

    Returns RoutingResult with suggested skills.
    """
    # Skip if not a Task tool
    if hook_input.tool_name != "Task":
        return RoutingResult(
            exit_code=ALLOW,
            suggested_skills=(),
            skill_scores={},
            dev_skill_ratio=0.0,
            message="Not a Task tool call",
        )

    # Route to skills
    matches = route_to_skills(hook_input.prompt)

    # Calculate dev ratio
    dev_ratio = calculate_dev_ratio(matches)

    # Build result
    suggested = tuple(m.skill.name for m in matches)
    scores = {m.skill.name: m.score for m in matches}

    return RoutingResult(
        exit_code=ALLOW,
        suggested_skills=suggested,
        skill_scores=scores,
        dev_skill_ratio=dev_ratio,
        message=f"Routed to {len(matches)} skills, dev_ratio={dev_ratio:.2f}",
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main() -> None:
    """Entry point for the Task skill router hook."""
    try:
        # Parse input
        hook_input = HookInput.from_stdin()

        # Process routing
        result = process_routing(hook_input)

        # Emit result
        result.emit()

    except ValueError as e:
        # Invalid input - warn but allow
        print(f"WARNING: Invalid input: {e}", file=sys.stderr)
        print(json.dumps({"suggested_skills": [], "skill_scores": {}, "dev_skill_ratio": 0.0}))
        sys.exit(ALLOW)

    except Exception as e:
        # Unexpected error - allow to prevent blocking
        print(f"WARNING: Router hook error: {e}", file=sys.stderr)
        print(json.dumps({"suggested_skills": [], "skill_scores": {}, "dev_skill_ratio": 0.0}))
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
