#!/usr/bin/env python3
# Adapted from analise/.claude/hooks/validation/code_first_pipeline_validator.py
# ADAPTATION: ANTT-specific pipeline_state glob replaced with env var KAZUBA_PIPELINE_STATE_GLOB
"""
Pre-Pipeline-Validator Hook — CODE-FIRST enforcement

Blocks ANTT skills from executing without verified pipeline state.
Validates: pipeline_state JSON, phase completion, LNA quality gates.

Event: PreToolUse (when invoking antt-* skills)
Action: BLOCK if violations detected, ALLOW otherwise
"""

import json
import os as _os
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

# ADAPTATION: Allow overriding pipeline_state glob via environment variable
_PIPELINE_STATE_GLOB = _os.environ.get(
    "KAZUBA_PIPELINE_STATE_GLOB",
    "pipeline_state_*.json"
)

# ============================================================================
# Configuration
# ============================================================================

ANTT_SKILLS = frozenset(
    {
        "antt-preliminary-analyzer",
        "antt-chronology-builder",
        "antt-technical-analyzer",
        "antt-critical-analyzer",
        "antt-legal-analyzer",
        "antt-final-synthesizer",
        "antt-vote-architect",
        "process-analysis-maestria",
        "antt-cognitive-orchestrator",
        "antt-deliberation-analyzer",
        "antt-citation-validator",
        "antt-narrative-architect",
        "antt-document-processor",
        "antt-habilitacao-analyzer",
        "antt-trip-analyzer",
        "antt-document-analyzer",
    }
)

REQUIRED_PHASES = {
    "antt-preliminary-analyzer": [1, 2, 3],
    "antt-chronology-builder": [1, 2, 3],
    "antt-technical-analyzer": [1, 2, 3, 4],
    "antt-critical-analyzer": [1, 2, 3, 5],
    "antt-legal-analyzer": [1, 2, 3, 6],
    "antt-final-synthesizer": [1, 2, 3, 7],
    "antt-vote-architect": [1, 2, 3, 8],
    "process-analysis-maestria": [1, 2, 3],
    "antt-cognitive-orchestrator": [1, 2, 3],
    "antt-deliberation-analyzer": [1, 2, 3],
    "antt-citation-validator": [1, 2, 3, 15],
    "antt-narrative-architect": [1, 2, 3, 7],
    "antt-document-processor": [1, 2, 3],
    "antt-habilitacao-analyzer": [1, 2, 3, 4],
    "antt-trip-analyzer": [1, 2, 3, 4],
    "antt-document-analyzer": [1, 2, 3],
}

PROCESS_PATTERN = re.compile(r"50500\.\d{6}-\d{4}-\d{2}|50505\.\d{6}-\d{4}-\d{2}")


# ============================================================================
# Validation Logic
# ============================================================================


def find_process_in_context(context: dict) -> str | None:
    """Extract process number from conversation context."""
    if not context:
        return None

    messages = context.get("messages", [])
    for msg in messages:
        if isinstance(msg, dict) and "content" in msg:
            content = str(msg["content"])
            match = PROCESS_PATTERN.search(content)
            if match:
                return match.group(0)

    return None


def find_pipeline_state(process: str) -> Path | None:
    """Locate pipeline_state JSON for given process."""
    analise_path = Path("analise/relatoria")
    if not analise_path.exists():
        return None

    # Normalize: 50500.123456-2026-01 → directory name
    proc_dir = analise_path / process
    if proc_dir.exists():
        state_files = list(proc_dir.glob(_PIPELINE_STATE_GLOB))
        if state_files:
            return state_files[0]

    return None


def validate_pipeline_state(state_path: Path, required_phases: list[int]) -> tuple[bool, str]:
    """Check if pipeline has completed required phases with quality gates."""
    try:
        with open(state_path) as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Invalid pipeline_state JSON: {e}"

    # Build O(1) phase lookup dict — avoids O(N²) linear scan in quality check loop
    phases_by_num: dict[int, dict] = {p["phase"]: p for p in state.get("phases", [])}

    # Check phase completion
    completed_phases = {num for num, p in phases_by_num.items() if p.get("status") == "completed"}
    missing = set(required_phases) - completed_phases

    if missing:
        return False, f"Missing phases: {sorted(missing)}"

    # Check LNA quality for critical phases
    for phase_num in required_phases:
        phase_data = phases_by_num.get(phase_num)
        if not phase_data:
            continue

        # Verify Rust integration (not pure Claude estimate)
        if phase_data.get("engine") != "rust_bridge":
            return False, f"Phase {phase_num} not via Rust Core (engine={phase_data.get('engine')})"

        # Check quality score
        quality = phase_data.get("quality_score", 0)
        if quality < 0.7:
            return False, f"Phase {phase_num} quality below threshold: {quality:.2f}"

    return True, "All phases verified"


def validate_skill_invocation(skill_name: str, context: dict) -> tuple[Literal["ALLOW", "BLOCK", "WARN"], str]:
    """
    Main validator: check if skill can execute.

    Returns: (action, reason)
    """

    # Only validate ANTT skills
    if skill_name not in ANTT_SKILLS:
        return "ALLOW", "Not an ANTT skill"

    # Find process in context
    process = find_process_in_context(context)
    if not process:
        return "WARN", f"No process detected for {skill_name}. Proceeding with caution."

    # Find pipeline state
    state_path = find_pipeline_state(process)
    if not state_path:
        return "BLOCK", (
            f"No pipeline_state found for {process}. "
            f"Run: python -m scripts.process_analysis.pipeline_runner --dir analise/relatoria/{process}/"
        )

    # Validate required phases
    required = REQUIRED_PHASES.get(skill_name, [])
    if not required:
        return "ALLOW", f"No phase requirements for {skill_name}"

    valid, reason = validate_pipeline_state(state_path, required)
    if not valid:
        return "BLOCK", (
            f"Pipeline validation failed for {skill_name}: {reason}\n"
            f"Required phases: {required}\n"
            f"Run: python -m scripts.process_analysis.pipeline_runner "
            f"--dir analise/relatoria/{process}/ --phases {','.join(map(str, required))}"
        )

    return "ALLOW", f"Pipeline validated for {skill_name}"


# ============================================================================
# Hook Entry Point
# ============================================================================


def hook_pre_tool_use(context: dict) -> dict:
    """
    PreToolUse hook — validates CODE-FIRST pipeline before ANTT skill execution.

    Input: {
        "skill": "antt-preliminary-analyzer",
        "messages": [...]
    }

    Output: {
        "action": "ALLOW" | "WARN" | "BLOCK",
        "reason": str,
        "skill": str
    }
    """
    skill_name = context.get("skill", "")

    action, reason = validate_skill_invocation(skill_name, context)

    return {
        "action": action,
        "reason": reason,
        "skill": skill_name,
        "timestamp": datetime.now().isoformat(),
        "validator": "code_first_pipeline_validator",
    }


# ============================================================================
# Testing
# ============================================================================


if __name__ == "__main__":
    # Test without process
    result = hook_pre_tool_use({"skill": "antt-preliminary-analyzer", "messages": []})
    print("Test 1 (no process):", result)
    assert result["action"] == "WARN"

    # Test with process but no pipeline
    result = hook_pre_tool_use(
        {
            "skill": "antt-preliminary-analyzer",
            "messages": [{"content": "Process 50500.123456-2026-01 analysis"}],
        }
    )
    print("Test 2 (no pipeline):", result)
    assert result["action"] == "BLOCK"

    print("✅ All validation tests passed")
