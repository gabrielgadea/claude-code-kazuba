#!/usr/bin/env python3
# Adapted from analise/.claude/hooks/planning/antt_workflow_tracker.py
# ADAPTATION: ANTT-specific references removed
"""
Kazuba Workflow Tracker Hook

Tracks progress through a configurable multi-phase workflow.
Auto-creates TODOs, estimates time, suggests skills, and tracks completeness.

Integrates with learning_system.py to learn execution time patterns.

Based on: auto_todo_creator.py (clean, production-ready code)
Author: Claude Code (Kazuba Project)
Date: 2025-11-06
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from os.path import dirname
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

sys.path.insert(0, dirname(dirname(__file__)))
from utils.hook_cache import HookCache

# =============================================================================
# Constants
# =============================================================================

# Generic process number pattern (not domain-specific)
PROCESS_NUMBER_PATTERN = re.compile(r"\d{5,6}\.\d{6}/\d{4}-\d{2}")

COMPLEXITY_MULTIPLIERS: dict[str, float] = {
    "high": 1.5,
    "medium": 1.0,
    "low": 0.7,
}

LEARNING_WORKFLOW_MAP: dict[str, str] = {
    "complete_process_analysis": "complete_analysis",
    "preliminary_analysis": "analysis",
    "vote_generation": "vote",
    "legal_analysis": "legal",
    "chronology_construction": "chronology",
    "technical_analysis": "technical",
}

# Module-level path setup — executed once at import, not on every SessionStart call
_SKILLS_PATH = (
    Path(__file__).parent.parent.parent / "skills" / "kazuba-skill-orchestrator" / "scripts"
)
if _SKILLS_PATH.exists() and str(_SKILLS_PATH) not in sys.path:
    sys.path.insert(0, str(_SKILLS_PATH))

try:
    from learning_system import LearningSystem as _LearningSystem  # type: ignore

    _LEARNING_AVAILABLE = True
except ImportError:
    _LEARNING_AVAILABLE = False


# =============================================================================
# Helpers
# =============================================================================


def _extract_process_number(text: str) -> str | None:
    """Extract process number from text."""
    match = PROCESS_NUMBER_PATTERN.search(text)
    return match.group(0) if match else None


def _now_utc() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(tz=UTC)


def _elapsed_seconds(start: datetime) -> float:
    """Return seconds elapsed since start."""
    return (_now_utc() - start).total_seconds()


# =============================================================================
# Anthropic-Compliant Output Format (SessionStart)
# =============================================================================


def format_session_output(result: KazubaWorkflowResult) -> str:
    """Format KazubaWorkflowResult as Anthropic-compliant SessionStart output.

    Args:
        result: The workflow tracking result

    Returns:
        JSON string in correct Anthropic schema format
    """
    context_parts = [result.message]
    if result.todo_list:
        context_parts.append(f"TODO: {len(result.todo_list)} items")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": " | ".join(context_parts),
        },
        "suppressOutput": True,
    }
    return json.dumps(output)


# =============================================================================
# PYDANTIC MODELS (Type-Safe Configuration & Results)
# =============================================================================


class KazubaPhase(BaseModel):
    """A single phase in the Kazuba workflow."""

    phase_number: int = Field(..., ge=1, le=8, description="Phase number (1-8)")
    name: str = Field(..., min_length=1, description="Phase name")
    skill: str = Field(..., min_length=1, description="Recommended skill")
    estimate_hours: float = Field(..., gt=0, description="Estimated hours")
    deliverable: str = Field(..., min_length=1, description="Expected deliverable")
    dependencies: list[int] = Field(
        default_factory=list,
        description="Phase numbers this phase depends on",
    )


class KazubaWorkflowConfig(BaseModel):
    """Configuration for Kazuba Workflow Tracker."""

    project_root: Path = Field(
        default_factory=lambda: Path.cwd(),
        description="Project root directory",
    )
    enable_learning: bool = Field(
        default=True,
        description="Enable learning system integration",
    )

    @field_validator("project_root")
    @classmethod
    def validate_project_root(cls, v: Path) -> Path:
        """Validate project root exists."""
        if not v.exists():
            msg = f"Project root does not exist: {v}"
            raise ValueError(msg)
        return v.resolve()


class KazubaWorkflowResult(BaseModel):
    """Type-safe result from workflow tracker."""

    status: Literal["allow", "warn", "block"]
    message: str
    suggestions: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    todo_list: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    execution_time_seconds: float = Field(default=0.0, ge=0.0)


# =============================================================================
# KAZUBA WORKFLOW TRACKER IMPLEMENTATION
# =============================================================================


class KazubaWorkflowTracker:
    """Tracks progress through Kazuba multi-phase workflow."""

    # Kazuba Workflow Definition
    PHASES = [
        KazubaPhase(
            phase_number=1,
            name="Processamento de Documentos (SEI)",
            skill="kazuba-document-processor",
            estimate_hours=0.5,
            deliverable="Arquivos markdown em md_[processo]/",
            dependencies=[],
        ),
        KazubaPhase(
            phase_number=2,
            name="Análise Preliminar",
            skill="kazuba-preliminary-analyzer",
            estimate_hours=1.0,
            deliverable="Metadata, partes, documentos-chave, cronologia inicial",
            dependencies=[1],
        ),
        KazubaPhase(
            phase_number=3,
            name="Construção de Cronologia",
            skill="kazuba-chronology-builder",
            estimate_hours=1.0,
            deliverable="Timeline evento-por-evento com cita\u00e7\u00f5es",
            dependencies=[1, 2],
        ),
        KazubaPhase(
            phase_number=4,
            name="Análise Técnica",
            skill="kazuba-technical-analyzer",
            estimate_hours=2.0,
            deliverable="Análise econômico-financeira, Fator D, AIR",
            dependencies=[1, 2, 3],
        ),
        KazubaPhase(
            phase_number=5,
            name="Análise Crítica (Stress-Test)",
            skill="kazuba-critical-analyzer",
            estimate_hours=1.0,
            deliverable="Vulnerabilidades, falhas lógicas, riscos TCU",
            dependencies=[2, 3, 4],
        ),
        KazubaPhase(
            phase_number=6,
            name="Análise Jurídica",
            skill="kazuba-legal-analyzer",
            estimate_hours=1.5,
            deliverable="Parecer jurídico, precedentes TCU, conformidade",
            dependencies=[2, 3, 4, 5],
        ),
        KazubaPhase(
            phase_number=7,
            name="Síntese e Integração",
            skill="kazuba-final-synthesizer",
            estimate_hours=1.0,
            deliverable="Relatório final consolidado",
            dependencies=[2, 3, 4, 5, 6],
        ),
        KazubaPhase(
            phase_number=8,
            name="Elaboração de Voto Deliberativo",
            skill="kazuba-vote-architect",
            estimate_hours=4.0,
            deliverable="Voto 60-80 páginas, legal robustness ≥99.5%",
            dependencies=[7],
        ),
    ]

    # Workflow trigger keywords
    WORKFLOW_KEYWORDS: dict[str, list[str]] = {
        "complete_analysis": [
            "análise completa",
            "complete analysis",
            "processo completo",
            "full process",
            "analisar processo",
            "analyze process",
        ],
        "partial_analysis": [
            "análise parcial",
            "partial analysis",
            "apenas fase",
            "only phase",
            "specific phase",
        ],
        "resume_analysis": [
            "retomar análise",
            "resume analysis",
            "continuar análise",
            "continue analysis",
        ],
    }

    # Complexity indicators (affect time estimates)
    COMPLEXITY_INDICATORS: dict[str, list[str]] = {
        "high": [
            "reequilíbrio",
            "termo aditivo",
            "AIR",
            "contrato",
            "concessão",
            "complex",
            "complexo",
        ],
        "medium": [
            "análise técnica",
            "technical analysis",
            "parecer",
            "opinion",
        ],
        "low": [
            "consulta",
            "query",
            "simples",
            "simple",
            "revisão",
            "review",
        ],
    }

    def __init__(self, config: KazubaWorkflowConfig | None = None):
        """Initialize workflow tracker.

        Args:
            config: Optional configuration (uses defaults if None)
        """
        self.config = config or KazubaWorkflowConfig()

        # Initialize cache for performance (TTL: 24 hours)
        cache_file = Path(".local-cache/kazuba_workflow_cache.json")
        self._cache = HookCache(cache_file=cache_file, max_entries=500)

    def _detect_workflow_intent(self, text: str) -> dict[str, Any] | None:
        """Detect if text contains workflow-related intent.

        Uses learning system for ML-based detection with keyword fallback.

        Args:
            text: User input text

        Returns:
            Dict with workflow info, or None if no intent detected
        """
        result = self._detect_via_learning_system(text)
        if result is not None:
            return result

        return self._detect_via_keywords(text)

    def _detect_via_learning_system(self, text: str) -> dict[str, Any] | None:
        """Try ML-based intent detection via the learning system.

        Args:
            text: User input text

        Returns:
            Dict with workflow info if high-confidence match found, else None
        """
        if not _LEARNING_AVAILABLE:
            return None

        try:
            learning = _LearningSystem()  # type: ignore[possibly-unbound]
            patterns = learning.find_similar_patterns(
                task_description=text,
                max_results=10,
            )

            if not patterns:
                return None

            best_match = patterns[0]
            if best_match.similarity_score < 0.85:
                return None

            workflow = best_match.workflow_name
            workflow_type = LEARNING_WORKFLOW_MAP.get(workflow, "complete_analysis")

            return {
                "workflow_type": workflow_type,
                "process_number": _extract_process_number(text),
                "detected_keyword": f"learning_system:{workflow}",
                "confidence": best_match.similarity_score,
                "detection_method": "learning_system",
            }
        except Exception:
            return None

    def _detect_via_keywords(self, text: str) -> dict[str, Any] | None:
        """Keyword-based workflow intent detection (fallback).

        Args:
            text: User input text

        Returns:
            Dict with workflow info if keyword match found, else None
        """
        text_lower = text.lower()

        for workflow_type, keywords in self.WORKFLOW_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return {
                        "workflow_type": workflow_type,
                        "process_number": _extract_process_number(text),
                        "detected_keyword": keyword,
                        "confidence": 1.0,
                        "detection_method": "keywords",
                    }

        return None

    def _determine_complexity(self, text: str) -> str:
        """Determine analysis complexity from text.

        Args:
            text: User input text

        Returns:
            Complexity level: "high", "medium", or "low"
        """
        text_lower = text.lower()

        for complexity, indicators in self.COMPLEXITY_INDICATORS.items():
            for indicator in indicators:
                if indicator in text_lower:
                    return complexity

        return "medium"

    def _create_todo_list(
        self,
        workflow_info: dict[str, Any],
        complexity: str,
    ) -> tuple[list[str], dict[str, Any]]:
        """Create TODO list for workflow.

        Args:
            workflow_info: Workflow detection info
            complexity: Complexity level

        Returns:
            Tuple of (todo_list, metrics)
        """
        multiplier = COMPLEXITY_MULTIPLIERS.get(complexity, 1.0)

        todo_list: list[str] = []
        total_hours = 0.0

        process_number = workflow_info.get("process_number", "XXXXX")
        workflow_type = workflow_info["workflow_type"]

        if workflow_type == "complete_analysis":
            header = f"📋 Análise Completa - Processo {process_number}"
            todo_list.append(header)
            todo_list.append("=" * len(header))
            todo_list.append("")

            for phase in self.PHASES:
                adjusted_hours = phase.estimate_hours * multiplier
                total_hours += adjusted_hours

                phase_todo = (
                    f"[ ] Phase {phase.phase_number}: {phase.name} ({adjusted_hours:.1f}h)"
                )
                todo_list.append(phase_todo)
                todo_list.append(f"    ↳ Skill: {phase.skill}")
                todo_list.append(f"    ↳ Deliverable: {phase.deliverable}")

                if phase.dependencies:
                    deps = ", ".join(str(d) for d in phase.dependencies)
                    todo_list.append(f"    ↳ Depends on: Phase(s) {deps}")

                todo_list.append("")

        else:
            todo_list.append(f"[ ] {workflow_info['detected_keyword'].title()}")
            total_hours = 2.0 * multiplier

        if total_hours <= 8:
            time_estimate = f"{total_hours:.1f}h"
        else:
            days = total_hours / 8
            time_estimate = f"{days:.1f}d ({total_hours:.1f}h)"

        metrics: dict[str, Any] = {
            "workflow_type": workflow_type,
            "process_number": process_number,
            "complexity": complexity,
            "total_phases": len(self.PHASES) if workflow_type == "complete_analysis" else 1,
            "estimated_time": time_estimate,
            "estimated_hours": total_hours,
            "complexity_multiplier": multiplier,
        }

        return todo_list, metrics

    def execute(self, tool: str, args: list[str]) -> KazubaWorkflowResult:
        """Execute workflow tracking.

        Args:
            tool: Tool name
            args: Tool arguments (usually contains user prompt)

        Returns:
            KazubaWorkflowResult with TODO list and recommendations
        """
        start_time = _now_utc()

        text = " ".join(args)
        cache_key = self._cache.generate_key(tool, text)

        cached_result = self._cache.get(cache_key)
        if cached_result:
            cached_result["execution_time_seconds"] = _elapsed_seconds(start_time)
            return KazubaWorkflowResult(**cached_result)

        workflow_info = self._detect_workflow_intent(text)

        if not workflow_info:
            return KazubaWorkflowResult(
                status="allow",
                message="Nenhum workflow detectado",
                suggestions=[
                    "Use 'análise completa' para workflow de 8 fases",
                    "Especifique número de processo (XXXXX.XXXXXX/YYYY-ZZ)",
                ],
                confidence=1.0,
                execution_time_seconds=_elapsed_seconds(start_time),
            )

        complexity = self._determine_complexity(text)
        todo_list, metrics = self._create_todo_list(workflow_info, complexity)

        suggestions = [
            "Siga o workflow de 8 fases do início ao fim",
            "Use o skill recomendado para cada fase",
            f"Complexidade detectada: {complexity.upper()}",
            f"Tempo estimado total: {metrics['estimated_time']}",
            "Integra com learning_system.py para estimativas adaptativas",
        ]

        execution_time = _elapsed_seconds(start_time)

        result = KazubaWorkflowResult(
            status="allow",
            message=f"✅ Workflow detectado: {workflow_info['workflow_type']}",
            suggestions=suggestions,
            metrics=metrics,
            todo_list=todo_list,
            confidence=0.95,
            execution_time_seconds=execution_time,
        )

        self._cache.set(cache_key, result.model_dump(mode="json"), ttl=86400)
        return result


# =============================================================================
# CLI INTERFACE
# =============================================================================


def main() -> None:
    """Main entry point for SessionStart hook."""
    # Read hook data from stdin (Claude Code protocol)
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        data = {}

    # For SessionStart events, tool_name is the event type
    tool_name = data.get("tool_name", "SessionStart")
    tool_input = data.get("tool_input", {})
    tool_args = [tool_input.get("file_path", "")] if tool_input.get("file_path") else []

    try:
        tracker = KazubaWorkflowTracker()
        result = tracker.execute(tool_name, tool_args)

        print(format_session_output(result))

        if result.todo_list:
            print("\n" + "\n".join(result.todo_list), file=sys.stderr)

        sys.exit(0)

    except Exception as e:
        error_result = KazubaWorkflowResult(
            status="warn",
            message=f"⚠️ Workflow tracker error: {e!s}",
            suggestions=["Check hook configuration"],
            confidence=0.0,
        )
        print(format_session_output(error_result))
        print(f"[Workflow Tracker] ERROR: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
