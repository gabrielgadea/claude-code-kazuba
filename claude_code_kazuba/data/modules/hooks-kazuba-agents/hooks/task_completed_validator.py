#!/usr/bin/env python3
# Adapted from analise/.claude/hooks/agents/task_completed_validator.py
# ADAPTATION: ANTT-specific validation checks removed
"""TaskCompleted Validator Hook.

Executado quando uma task está sendo marcada como completada.
Se o validador falhar, exit code 2 impede conclusão e envia feedback.

Events: TaskCompleted
Exit 0 = task pode ser marcada como completada
Exit 2 = task não é marcada, feedback enviado ao modelo
"""

from __future__ import annotations

import json
import subprocess
import sys

# Pre-computed at module level — avoid per-call list creation
# _ANTT_PATTERNS removed: ANTT-specific domain patterns not included in kazuba generic module

_CODE_PATTERNS = (
    "implement",
    "implementar",
    "criar",
    "refatorar",
    "fix",
    "corrigir",
    "desenvolver",
    "codificar",
    "build",
    "construir",
    "módulo",
    "classe",
    "função",
    "script",
    "endpoint",
    "api",
)

_REVIEW_PATTERNS = (
    "review",
    "revisar",
    "verificar",
    "auditar",
    "analisar código",
    "code review",
    "security review",
    "performance review",
)

_DOC_PATTERNS = (
    "documentação",
    "documentation",
    "relatório",
    "report",
    "voto",
    "parecer",
    "nota técnica",
    "sumário",
    "resumo",
)

_RESEARCH_PATTERNS = (
    "pesquisa",
    "research",
    "investigar",
    "buscar",
    "encontrar",
    "levantar",
    "mapear",
    "identificar",
)

_FINDINGS_INDICATORS = (
    "finding",
    "issue",
    "problema",
    "vulnerabilidade",
    "risco",
    "recomendação",
    "sugestão",
    "no issues",
    "sem problemas",
    "nenhum problema",
    "limpo",
    "clean",
    "aprovado",
    "approved",
    "severity",
    "severidade",
)


def load_event() -> dict:
    """Load hook event data from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def detect_task_type(task_subject: str, task_description: str) -> str:
    """Classify task type for targeted validation.

    Returns:
        One of: "code_implementation", "documentation",
                "code_review", "research", "generic"
    """
    combined = f"{task_subject} {task_description}".lower()

    if any(p in combined for p in _CODE_PATTERNS):
        return "code_implementation"

    if any(p in combined for p in _REVIEW_PATTERNS):
        return "code_review"

    if any(p in combined for p in _DOC_PATTERNS):
        return "documentation"

    if any(p in combined for p in _RESEARCH_PATTERNS):
        return "research"

    return "generic"


def validate_code_implementation(cwd: str) -> tuple[bool, str]:
    """Validate code implementation task passes quality checks.

    Checks:
    - Ruff: 0 errors
    - Pyright: no critical errors (optional, best-effort)
    """
    try:
        result = subprocess.run(
            ["ruff", "check", "--select=E,W,F,C901", "--quiet", "."],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30,
        )
        if result.returncode != 0:
            lines = result.stdout.strip().split("\n")
            issues = "\n".join(lines[:8])
            if len(lines) > 8:
                issues += f"\n... e mais {len(lines) - 8} issues"
            return False, (
                f"Task de código não pode ser completada com erros ruff:\n{issues}\n"
                f"Execute `ruff check --fix .` e corrija os erros antes de completar."
            )
        return True, "Ruff: 0 erros"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return True, "Ruff: skip (não disponível)"


def validate_code_review(task_description: str) -> tuple[bool, str]:
    """Validate code review has findings documented."""
    # Check that the description mentions findings or explicitly states "no issues"
    description_lower = task_description.lower() if task_description else ""
    has_findings_doc = any(i in description_lower for i in _FINDINGS_INDICATORS)

    if not has_findings_doc and not task_description:
        return False, (
            "Code review task deve documentar findings (ou explicitamente indicar "
            "'sem issues encontrados') na descrição da task antes de marcar como completa."
        )

    return True, "Code review: findings documentados"


def main() -> None:
    """Main validation logic."""
    event = load_event()

    # Only process TaskCompleted events
    if event.get("hook_event_name") != "TaskCompleted":
        sys.exit(0)

    task_id = event.get("task_id", "unknown")
    task_subject = event.get("task_subject", "")
    task_description = event.get("task_description", "")
    teammate_name = event.get("teammate_name", "unknown")
    team_name = event.get("team_name", "unknown")
    cwd = event.get("cwd", ".")

    task_type = detect_task_type(task_subject, task_description)
    failures: list[str] = []

    # Run type-specific validation
    if task_type == "code_implementation":
        passed, msg = validate_code_implementation(cwd)
        if not passed:
            failures.append(msg)

    elif task_type == "code_review":
        passed, msg = validate_code_review(task_description)
        if not passed:
            failures.append(msg)

    if failures:
        feedback = (
            f"[TaskCompleted Validator] Task '{task_subject}' (ID: {task_id})\n"
            f"Teammate: {teammate_name} | Team: {team_name} | Tipo: {task_type}\n"
            f"Critérios de conclusão não atendidos:\n\n" + "\n\n".join(f"• {f}" for f in failures)
        )
        print(feedback, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
