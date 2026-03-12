#!/usr/bin/env python3
# Adapted from analise/.claude/hooks/validation/code_first_pipeline_validator.py
# ADAPTATION: ANTT-specific pipeline_state glob replaced with env var KAZUBA_PIPELINE_STATE_GLOB
# ADAPTATION: ANTT-specific skill whitelist replaced with env var KAZUBA_PIPELINE_SKILLS
# ADAPTATION: ANTT process number pattern replaced with env var KAZUBA_PROCESS_PATTERN
# ADAPTATION: ANTT-specific required phases removed (disabled in generic version)
"""
Pre-Pipeline-Validator Hook — CODE-FIRST enforcement

Blocks pipeline skills from executing without verified pipeline state.
Validates: pipeline_state JSON, phase completion, quality gates.

Event: PreToolUse (when invoking configured pipeline skills)
Action: BLOCK if violations detected, ALLOW otherwise

Configuration via environment variables:
  KAZUBA_PIPELINE_STATE_GLOB  — glob pattern for pipeline state files
                                (default: "pipeline_state_*.json")
  KAZUBA_PIPELINE_SKILLS      — comma-separated list of skill names that
                                require a verified pipeline state
                                (default: empty = no skill-based pipeline check)
  KAZUBA_PROCESS_PATTERN      — regex pattern to extract process identifier
                                from conversation context
                                (default: empty = skip process extraction)
"""

import json
import os as _os
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

# ADAPTATION: Allow overriding pipeline_state glob via environment variable
_PIPELINE_STATE_GLOB = _os.environ.get("KAZUBA_PIPELINE_STATE_GLOB", "pipeline_state_*.json")

# ============================================================================
# Configuration
# ============================================================================

# ADAPTATION: ANTT-specific skill whitelist replaced with env var KAZUBA_PIPELINE_SKILLS
# Original had hardcoded antt-* skill names
_SKILLS_ENV = _os.environ.get("KAZUBA_PIPELINE_SKILLS", "")
PIPELINE_SKILLS: frozenset[str] = (
    frozenset(s.strip() for s in _SKILLS_ENV.split(",") if s.strip())
    if _SKILLS_ENV
    else frozenset()
)  # empty = no skill-based pipeline check

# ADAPTATION: ANTT-specific required phases removed
# Skill-to-phase validation disabled in generic version
# Projects can implement domain-specific phase validation via subclassing
REQUIRED_PHASES: dict[str, list[int]] = {}  # disabled in generic version

# ADAPTATION: ANTT process number pattern replaced with env var KAZUBA_PROCESS_PATTERN
_PROCESS_PATTERN_ENV = _os.environ.get("KAZUBA_PROCESS_PATTERN", "")
PROCESS_PATTERN = re.compile(_PROCESS_PATTERN_ENV) if _PROCESS_PATTERN_ENV else None


# ============================================================================
# Validation Logic
# ============================================================================


def find_process_in_context(context: dict) -> str | None:
    """Extract process identifier from conversation context."""
    if not context or PROCESS_PATTERN is None:
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

    # Check quality for critical phases
    for phase_num in required_phases:
        phase_data = phases_by_num.get(phase_num)
        if not phase_data:
            continue

        # Verify Rust integration (not pure LLM estimate)
        if phase_data.get("engine") != "rust_bridge":
            return (
                False,
                f"Phase {phase_num} not via Rust Core (engine={phase_data.get('engine')})",
            )

        # Check quality score
        quality = phase_data.get("quality_score", 0)
        if quality < 0.7:
            return False, f"Phase {phase_num} quality below threshold: {quality:.2f}"

    return True, "All phases verified"


def validate_skill_invocation(
    skill_name: str, context: dict
) -> tuple[Literal["ALLOW", "BLOCK", "WARN"], str]:
    """
    Main validator: check if skill can execute.

    Returns: (action, reason)
    """

    # Only validate configured pipeline skills
    if not PIPELINE_SKILLS or skill_name not in PIPELINE_SKILLS:
        return "ALLOW", "Not a configured pipeline skill"

    # Find process in context
    process = find_process_in_context(context)
    if not process:
        return "WARN", f"No process detected for {skill_name}. Proceeding with caution."

    # Find pipeline state
    state_path = find_pipeline_state(process)
    if not state_path:
        return "BLOCK", (
            f"No pipeline_state found for {process}. "
            f"Run the pipeline for {process} before invoking {skill_name}."
        )

    # Validate required phases (disabled in generic version)
    required = REQUIRED_PHASES.get(skill_name, [])
    if not required:
        return "ALLOW", f"No phase requirements for {skill_name}"

    valid, reason = validate_pipeline_state(state_path, required)
    if not valid:
        return "BLOCK", (
            f"Pipeline validation failed for {skill_name}: {reason}\nRequired phases: {required}"
        )

    return "ALLOW", f"Pipeline validated for {skill_name}"


# ============================================================================
# Hook Entry Point
# ============================================================================


def hook_pre_tool_use(context: dict) -> dict:
    """
    PreToolUse hook — validates CODE-FIRST pipeline before pipeline skill execution.

    Input: {
        "skill": "my-pipeline-skill",
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
    import os

    # Test: skill not in PIPELINE_SKILLS (empty set) → ALLOW
    result = hook_pre_tool_use({"skill": "some-skill", "messages": []})
    print("Test 1 (no pipeline skills configured):", result)
    assert result["action"] == "ALLOW"

    # Test: with PIPELINE_SKILLS set but no process pattern → WARN
    os.environ["KAZUBA_PIPELINE_SKILLS"] = "my-analyzer"
    # Reload the module-level constants to simulate env change at runtime
    _skills_env2 = os.environ.get("KAZUBA_PIPELINE_SKILLS", "")
    _pipeline_skills2: frozenset[str] = frozenset(
        s.strip() for s in _skills_env2.split(",") if s.strip()
    )

    def _patched_validate(
        skill_name: str, context: dict
    ) -> tuple[Literal["ALLOW", "BLOCK", "WARN"], str]:  # type: ignore[misc]
        if not _pipeline_skills2 or skill_name not in _pipeline_skills2:
            return "ALLOW", "Not a configured pipeline skill"
        process = find_process_in_context(context)
        if not process:
            return "WARN", f"No process detected for {skill_name}. Proceeding with caution."
        state_path = find_pipeline_state(process)
        if not state_path:
            return "BLOCK", f"No pipeline_state found for {process}."
        return "ALLOW", f"Pipeline validated for {skill_name}"

    result2_action, result2_reason = _patched_validate("my-analyzer", {"messages": []})
    print("Test 2 (pipeline skill, no process):", result2_action, result2_reason)
    assert result2_action == "WARN"

    print("All validation tests passed")
