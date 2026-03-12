#!/usr/bin/env python3
"""TeammateIdle Quality Gate Hook.

Executado quando um teammate de agent team está prestes a ficar idle.
Se o quality gate falhar, exit code 2 impede o idle e envia feedback.

Events: TeammateIdle
Exit 0 = teammate pode ficar idle
Exit 2 = teammate recebe feedback e continua trabalhando
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

# Pre-computed at module level — avoid per-call set creation
_ANTT_ANALYSIS_TEAMMATES = frozenset({"atlas", "themis", "praetor", "argus", "regularis"})
_CODE_TEAMMATES = frozenset({"implementer", "developer", "coder", "refactorer", "fixer"})
_DOC_TEAMMATES = frozenset({"narrator", "synthesizer", "vote-architect", "technical"})


def load_event() -> dict:
    """Load hook event data from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def check_ruff(cwd: str) -> tuple[bool, str]:
    """Run ruff check on modified Python files.

    Returns:
        (passed, message) tuple.
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
            # Limit to first 5 issues for readability
            issues = "\n".join(lines[:5])
            if len(lines) > 5:
                issues += f"\n... e mais {len(lines) - 5} issues"
            return False, f"Ruff detectou problemas:\n{issues}"
        return True, "Ruff: OK"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return True, "Ruff: skip (não disponível)"


def check_checkpoint_exists(cwd: str, teammate_name: str) -> tuple[bool, str]:
    """Verify that a checkpoint was saved for long-running analysis tasks.

    Only required for ANTT analysis teammates (atlas, themis, praetor, argus).
    """
    if teammate_name not in _ANTT_ANALYSIS_TEAMMATES:
        return True, "Checkpoint: não requerido para este teammate"

    checkpoints_dir = Path(cwd) / ".claude" / "checkpoints"
    if not checkpoints_dir.exists():
        return True, "Checkpoint: diretório não existe, skip"

    # Check for recent checkpoint (created in last 2 hours)
    cutoff = time.time() - 7200  # 2 hours
    recent_checkpoints = [f for f in checkpoints_dir.glob("*.json") if f.stat().st_mtime > cutoff]

    if not recent_checkpoints:
        return False, (
            "Nenhum checkpoint recente encontrado para análise ANTT. "
            "Salve um checkpoint em .claude/checkpoints/ antes de concluir. "
            "Formato: {descricao}_YYYYMMDD.json"
        )
    return True, f"Checkpoint: OK ({len(recent_checkpoints)} recente(s))"


def check_output_files(cwd: str, teammate_name: str) -> tuple[bool, str]:
    """For document-producing teammates, verify output files exist."""
    # Only check if teammate name suggests it should produce docs
    produces_docs = any(t in teammate_name.lower() for t in _DOC_TEAMMATES)
    if not produces_docs:
        return True, "Output: não verificado para este teammate"

    # Check analise directory for recent output
    analise_dir = Path(cwd) / "analise"
    if not analise_dir.exists():
        return True, "Output: diretório analise não existe, skip"

    cutoff = time.time() - 3600  # 1 hour
    recent_outputs = [f for f in analise_dir.rglob("*.md") if f.stat().st_mtime > cutoff]

    if not recent_outputs:
        return False, (
            f"Teammate {teammate_name} esperado para produzir documentação "
            f"mas nenhum arquivo .md foi criado/modificado na última hora em analise/. "
            f"Verifique se o trabalho foi concluído."
        )
    return True, f"Output: {len(recent_outputs)} arquivo(s) recente(s) em analise/"


def main() -> None:
    """Main quality gate logic."""
    event = load_event()

    teammate_name = event.get("teammate_name", "unknown")
    team_name = event.get("team_name", "unknown")
    cwd = event.get("cwd", ".")

    # Only process TeammateIdle events
    if event.get("hook_event_name") != "TeammateIdle":
        sys.exit(0)

    failures: list[str] = []

    # Gate 1: Ruff check (for code-producing teammates)
    if any(t in teammate_name.lower() for t in _CODE_TEAMMATES):
        passed, msg = check_ruff(cwd)
        if not passed:
            failures.append(msg)

    # Gate 2: Checkpoint verification (for ANTT analysis teammates)
    passed, msg = check_checkpoint_exists(cwd, teammate_name)
    if not passed:
        failures.append(msg)

    # Gate 3: Output files verification (for document teammates)
    passed, msg = check_output_files(cwd, teammate_name)
    if not passed:
        failures.append(msg)

    if failures:
        feedback = (
            f"[TeammateIdle Quality Gate] Teammate '{teammate_name}' (team: {team_name})\n"
            f"Quality gates falharam — corrija antes de concluir:\n\n" + "\n\n".join(f"• {f}" for f in failures)
        )
        print(feedback, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
