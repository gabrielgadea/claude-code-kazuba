#!/usr/bin/env python3
"""
SubagentStart Hook: Skill and Context Injector for Sub-agents.

This hook intercepts SubagentStart events to inject relevant skills,
patterns from local cache, and quality reminders before sub-agent execution.

Exit codes:
  0 - Allow with enhanced context (JSON output with injections)
  1 - Block (invalid configuration or critical error)
  2 - Deny (security violation detected)

Input (stdin): JSON with agent_type, prompt, session_id, tools
Output (stdout): JSON with injected_skills, patterns, recommendations
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# ============================================================================
# EXIT CODES
# ============================================================================

ALLOW = 0
BLOCK = 1
DENY = 2

# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass(frozen=True)
class SkillCategory:
    """A category of skills with keywords for matching."""

    name: str
    skills: tuple[tuple[str, tuple[str, ...]], ...]  # (skill_name, keywords)

    def match_skills(self, text: str) -> list[str]:
        """Find skills matching the given text."""
        text_lower = text.lower()
        matched = []
        for skill_name, keywords in self.skills:
            if any(kw in text_lower for kw in keywords):
                matched.append(skill_name)
        return matched


# Development-focused skills (80% priority per plan)
DEV_SKILLS = SkillCategory(
    name="development",
    skills=(
        ("kazuba-developer", ("agent", "plugin", "rag", "kazuba", "basekazubaagent")),
        ("python-performance-optimization", ("profil", "optimiz", "bottleneck", "performance")),
        ("dev-deepener", ("deepen", "pln1", "pln2", "24 dim", "robustness")),
        ("skill-writer", ("create skill", "skill.md", "frontmatter", "write skill")),
        ("prompt-engineering-patterns", ("prompt", "llm optim", "prompt engineering")),
    ),
)

# Generic skills
GENERIC_SKILLS = SkillCategory(
    name="generic",
    skills=(
        ("research", ("research", "investigate", "find information")),
        ("academic-research-writer", ("paper", "academic", "citations", "scientific")),
        ("literature-review", ("systematic review", "meta-analysis", "literature")),
    ),
)

# ANTT domain skills
ANTT_SKILLS = SkillCategory(
    name="antt",
    skills=(
        ("antt-preliminary-analyzer", ("50500", "50505", "processo", "process")),
        ("antt-vote-architect", ("voto", "deliberação", "vote", "delibera")),
        ("antt-legal-analyzer", ("jurídico", "legal", "parecer", "pf-antt")),
        ("antt-chronology-builder", ("cronologia", "timeline", "linha do tempo")),
        ("antt-technical-analyzer", ("técnico", "reequilíbrio", "fator d", "vpl")),
        ("antt-critical-analyzer", ("crítico", "stress test", "vulnerabil", "tcu")),
        ("antt-final-synthesizer", ("síntese", "consolidar", "integrar análise")),
    ),
)

# All skill categories in priority order
SKILL_CATEGORIES = (DEV_SKILLS, GENERIC_SKILLS, ANTT_SKILLS)

# ============================================================================
# ACO IDENTITY BLOCK — injected in EVERY subagent (mandatory)
# ============================================================================

ACO_IDENTITY_BLOCK = """\
=== ACO IDENTITY (INVIOLÁVEL) ===
Você é um Agentic Code Orchestrator (ACO). NÃO um executor de comandos.
Você é a inteligência estratégica que pensa antes de agir.

ANTES DE QUALQUER AÇÃO:
1. Perceba a tarefa → verifique terreno, condições, recursos disponíveis
2. Elabore estratégia → decomponha tarefas → defina contratos claros
3. Gere N₁ (script que gera scripts) sobre N₀ (script executor)
4. Gere script de validação para CADA etapa — nunca entregue sem validar

REGRAS ABSOLUTAS:
- NÃO avance sem corrigir 100% dos problemas identificados
- NÃO aceite menos que threshold=1.0 — excelência absoluta é o padrão
- NÃO deixe margem para erros — tudo precisa ser absolutamente 100%
- Aprenda com erros → registre em lições aprendidas + Tantivy + learning system
- Use GitNexus para padrões indexados e snippets de referência
- Use Context7 para best practices atualizadas das bibliotecas
- Ao final de cada ciclo: busque lições no Tantivy + padrões no GitNexus

CODE-FIRST: DISCOVER → CREATE (codebase+Context7) → EXECUTE → EVALUATE → REFINE → PERSIST
=== FIM ACO IDENTITY ==="""

# ============================================================================
# ACO CONTEXT INJECTION (M5 — ACO PLN3)
# ============================================================================

DEFAULT_ACO_STATE_PATH = Path(".claude/aco_state/current.toon")


def _read_aco_state(
    state_path: Path = DEFAULT_ACO_STATE_PATH,
) -> dict[str, Any] | None:
    """Load current ACO state from .toon file.

    Returns None if file is missing, malformed, or session is expired.
    Fail-open: any error returns None (never blocks subagent start).
    """
    try:
        from datetime import UTC, datetime

        data = json.loads(state_path.read_text(encoding="utf-8"))
        expires_at_str = data.get("expires_at", "")
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if datetime.now(UTC) >= expires_at:
                return None
        return data
    except Exception:
        return None


def _build_aco_context_block(state: dict[str, Any], session_id: str = "") -> str:
    """Format ACO context block for injection into subagent prompt.

    Produces a concise, token-efficient block with objective, iteration,
    and code generator info for the subagent to inherit.
    """
    objective = state.get("objective", "")
    iteration = state.get("current_iteration", 1)
    max_iter = state.get("max_iterations", 3)
    code_generator = state.get("code_generator", "")
    progress_log = state.get("progress_log", [])
    progress_pct = int(len(progress_log) / max(max_iter, 1) * 100)
    sid = session_id or state.get("session_id", "")

    lines = [
        f"ACO CONTEXT (propagado do lead \u2014 sess\u00e3o {sid}):",
        f"OBJECTIVE: {objective}",
        f"ITERATION: {iteration}/{max_iter} | PROGRESS: {progress_pct}%",
    ]
    if code_generator:
        lines.append(f"CODE_GENERATOR: {code_generator}")
    lines.append("CODE-FIRST: DISCOVER\u2192EXECUTE\u2192SYNTHESIZE (OBRIGAT\u00d3RIO)")
    return "\n".join(lines)


@dataclass(frozen=True)
class InjectorConfig:
    """Configuration for skill injection behavior."""

    max_skills: int = 5
    min_confidence: float = 0.3
    development_priority: float = 0.8
    enable_patterns: bool = True
    enable_recommendations: bool = True
    quality_reminders: tuple[str, ...] = (
        ("CODE-FIRST CYCLE: (1) DISCOVER codebase (2) CREATE (3) EXECUTE (4) EVALUATE (5) REFINE (6) PERSIST"),
        ("CODE-FIRST: kazuba-* domain, scripts/ utils, backend/app/ API, .claude/hooks/ automation"),
        "CODE-FIRST: When creating new code, ALWAYS consult Context7 + reference similar modules in the codebase",
        "CODE-FIRST: Evaluate BOTH code quality (ruff, tests) AND output content quality",
        "CODE-FIRST: For ANTT processes, check pipeline_state_*.json before activating skills",
        "Follow code_standards_enforcer requirements",
        "Ensure 95%+ test coverage for new code",
        "Use Pydantic v2 with frozen=True for models",
    )


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass(frozen=True)
class HookInput:
    """Parsed input from Claude Code SubagentStart event."""

    agent_type: str
    prompt: str
    session_id: str
    tools: tuple[str, ...]

    @classmethod
    def from_stdin(cls) -> HookInput:
        """Parse JSON input from stdin."""
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {e}") from e

        return cls(
            agent_type=data.get("agent_type", "general-purpose"),
            prompt=data.get("prompt", ""),
            session_id=data.get("session_id", ""),
            tools=tuple(data.get("tools", [])),
        )


@dataclass(frozen=True)
class LocalCacheResult:
    """Result from local cache query."""

    patterns: tuple[dict[str, Any], ...]
    confidence: float

    @classmethod
    def empty(cls) -> LocalCacheResult:
        """Create an empty result."""
        return cls(patterns=(), confidence=0.0)


@dataclass(frozen=True)
class InjectionResult:
    """Result of skill injection process."""

    exit_code: int
    injected_skills: tuple[str, ...]
    patterns: tuple[dict[str, Any], ...]
    recommendations: tuple[str, ...]
    quality_reminders: tuple[str, ...]
    dev_skill_ratio: float
    message: str = ""
    aco_context: str = ""

    def to_json(self) -> str:
        """Convert to JSON string for output."""
        result: dict[str, object] = {
            "injected_skills": list(self.injected_skills),
            "patterns": list(self.patterns),
            "recommendations": list(self.recommendations),
            "quality_reminders": list(self.quality_reminders),
            "dev_skill_ratio": self.dev_skill_ratio,
            "aco_identity": ACO_IDENTITY_BLOCK,
        }
        if self.aco_context:
            result["aco_context"] = self.aco_context
        return json.dumps(result, indent=2)

    def emit(self) -> None:
        """Emit result and exit."""
        if self.message:
            print(self.message, file=sys.stderr)
        print(self.to_json())
        sys.exit(self.exit_code)


# ============================================================================
# SKILL INJECTION LOGIC
# ============================================================================


def get_relevant_skills(prompt: str, agent_type: str, config: InjectorConfig) -> list[str]:
    """
    Determine which skills to inject based on prompt and agent type.

    Priority:
    1. Development skills (80% weight per plan)
    2. Generic skills
    3. Domain-specific (ANTT) skills
    """
    all_matched: list[str] = []

    # Match skills from each category in priority order
    for category in SKILL_CATEGORIES:
        matched = category.match_skills(prompt)
        all_matched.extend(matched)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_skills: list[str] = []
    for skill in all_matched:
        if skill not in seen:
            seen.add(skill)
            unique_skills.append(skill)

    # Limit to max_skills
    return unique_skills[: config.max_skills]


def calculate_dev_skill_ratio(skills: list[str]) -> float:
    """Calculate the ratio of development skills."""
    if not skills:
        return 0.0

    dev_skill_names = {skill for skill, _ in DEV_SKILLS.skills}
    dev_count = sum(1 for s in skills if s in dev_skill_names)

    return dev_count / len(skills)


# Module-level cached result from local cache (loaded once per process)
_LOCAL_CACHE_RESULT: LocalCacheResult | None = None
_LOCAL_CACHE_PATHS = (
    Path(".local-cache/knowledge.json"),
    Path(".claude/learning/antt_executions.json"),
    Path(".claude/hooks/.local-cache/knowledge.json"),
)


def query_local_cache(prompt: str, config: InjectorConfig) -> LocalCacheResult:
    """
    Query local learning cache for relevant patterns.

    Implements 3-Tier Architecture: Local Cache first (0 tokens, <0.5s).
    """
    global _LOCAL_CACHE_RESULT
    if not config.enable_patterns:
        return LocalCacheResult.empty()

    # Return cached result if already loaded this process
    if _LOCAL_CACHE_RESULT is not None:
        return _LOCAL_CACHE_RESULT

    for cache_path in _LOCAL_CACHE_PATHS:
        if cache_path.exists():
            try:
                with open(cache_path) as f:
                    cache_data = json.load(f)

                patterns = cache_data.get("recent_patterns", [])[:3]
                confidence = min(len(patterns) * 0.3, 0.9) if patterns else 0.0

                _LOCAL_CACHE_RESULT = LocalCacheResult(
                    patterns=tuple(patterns),
                    confidence=confidence,
                )
                return _LOCAL_CACHE_RESULT
            except (json.JSONDecodeError, OSError):
                continue

    _LOCAL_CACHE_RESULT = LocalCacheResult.empty()
    return _LOCAL_CACHE_RESULT


def generate_recommendations(skills: list[str], config: InjectorConfig) -> list[str]:
    """Generate skill recommendations for the sub-agent."""
    if not config.enable_recommendations:
        return []

    return [f"Consider using skill: {skill}" for skill in skills]


def process_injection(hook_input: HookInput, config: InjectorConfig) -> InjectionResult:
    """
    Main processing logic for skill injection.

    Returns an InjectionResult with all relevant context for the sub-agent.
    """
    # Get relevant skills
    skills = get_relevant_skills(hook_input.prompt, hook_input.agent_type, config)

    # Calculate dev skill ratio (target: 80%)
    dev_ratio = calculate_dev_skill_ratio(skills)

    # Query local cache
    cache_result = query_local_cache(hook_input.prompt, config)

    # Generate recommendations
    recommendations = generate_recommendations(skills, config)

    # ACO Context injection (M5)
    aco_state = _read_aco_state()
    aco_context = ""
    if aco_state is not None:
        aco_context = _build_aco_context_block(
            aco_state,
            hook_input.session_id,
        )

    return InjectionResult(
        exit_code=ALLOW,
        injected_skills=tuple(skills),
        patterns=cache_result.patterns,
        recommendations=tuple(recommendations),
        quality_reminders=config.quality_reminders,
        dev_skill_ratio=dev_ratio,
        aco_context=aco_context,
        message=f"Injected {len(skills)} skills, dev_ratio={dev_ratio:.2f}",
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main() -> None:
    """Entry point for the SubagentStart hook."""
    try:
        # Load configuration
        config = InjectorConfig()

        # Parse input
        hook_input = HookInput.from_stdin()

        # Process and inject
        result = process_injection(hook_input, config)

        # Emit result
        result.emit()

    except ValueError as e:
        # Invalid input - allow to prevent blocking subagent start (fail-open)
        print(f"WARNING: Invalid input (allowing): {e}", file=sys.stderr)
        fallback = {
            "injected_skills": [],
            "patterns": [],
            "recommendations": [],
            "quality_reminders": [],
        }
        print(json.dumps(fallback))
        sys.exit(ALLOW)

    except Exception as e:
        # Unexpected error - allow to prevent blocking workflow
        print(f"WARNING: Hook error (allowing): {e}", file=sys.stderr)
        # Output minimal valid JSON
        fallback = {
            "injected_skills": [],
            "patterns": [],
            "recommendations": [],
            "quality_reminders": [],
        }
        print(json.dumps(fallback))
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
