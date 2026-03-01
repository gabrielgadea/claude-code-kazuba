#!/usr/bin/env python3
"""CILA Strategy Enforcer — PreToolUse Policy Enforcement Point.

Event: PreToolUse (Task tool only)
Purpose: Verifies that CILA level requirements are met before tool execution.

Policy checks:
  - L2+ (Tool-Augmented): DISCOVER must be run before spawning sub-tasks
  - L3+ (Pipelines): Requires precondition state to exist
  - L4+ (Agent Loops): Planning and state verification required
  - L5+ (Self-Modifying): Explicit user approval required
  - L6 (Multi-Agent): Full team orchestration sequence required

This hook is ADVISORY — it warns but never blocks (fail-open).
Enforcement is via additionalContext warnings that guide Claude's behavior.

Protocol:
  1. Reads JSON from stdin (tool_name, tool_input)
  2. Classifies intent via CILA level detection
  3. Checks strategy requirements using GovernanceEnforcer + CILARouter
  4. Outputs additionalContext JSON with warnings
  5. Always exits 0 (advisory, never blocks on normal violations)
  6. Exits 2 ONLY for hard security violations

Exit codes:
  0 - Allow (advisory warnings via additionalContext)
  2 - Block (hard security violations only)
"""

from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ensure lib/ is importable when run directly as a hook script
_HOOK_DIR = Path(__file__).resolve().parent
_MODULE_DIR = _HOOK_DIR.parent.parent.parent  # modules/hooks-routing/hooks → project root
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

try:
    from lib.governance import CILARouter, GovernanceEnforcer
    _GOVERNANCE_AVAILABLE = True
except ImportError:
    _GOVERNANCE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Exit codes
ALLOW = 0
BLOCK = 2  # Hard violations only (fail-open = default exit 0)

# CILA keyword patterns for fast classification
_L6_PATTERN = re.compile(
    r"\b(swarm|multi.?agent|orchestrate.?agents|agent.?team|TeamCreate)\b", re.IGNORECASE
)
_L5_PATTERN = re.compile(
    r"\b(self.?evolv|mutate|drift.?detect|capability.?evolver)\b", re.IGNORECASE
)
_L4_PATTERN = re.compile(
    r"\b(ReAct|auto.?correct|iteration.?loop|max.?iteration|agent.?loop)\b", re.IGNORECASE
)
_L3_PATTERN = re.compile(
    r"\b(pipeline.?state|pipeline.?runner|multi.?phase|phase.?F\d+)\b", re.IGNORECASE
)
_L2_PATTERN = re.compile(
    r"\b(Bash|tool.?use|Read|Write|file.?operation|web.?search|MCP)\b", re.IGNORECASE
)
_L1_PATTERN = re.compile(r"\b(calculate|format|convert)\b", re.IGNORECASE)


@dataclass(frozen=True)
class EnforcementResult:
    """Immutable result of strategy enforcement.

    Attributes:
        action: "allow" or "warn" — this hook is always advisory.
        cila_level: Detected CILA level (0-6).
        warnings: Non-blocking guidance messages.
        violations: Advisory violation notices (still exits 0).
    """

    action: str = "allow"
    cila_level: int = 0
    warnings: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)


def classify_cila_level(prompt: str) -> int:
    """Classify prompt into CILA level using keyword heuristics.

    Uses the same classification heuristics as the CILA taxonomy:
    - L6: swarm, multi-agent, agent team keywords
    - L5: self-evolution, mutation, drift detection
    - L4: ReAct, auto-correction, iteration loops
    - L3: pipeline_state, pipeline_runner, multi-phase
    - L2: Bash, Read/Write, tool_use, file operations
    - L1: calculate, format, convert
    - L0: default (no code indicators)

    Args:
        prompt: The task prompt to classify.

    Returns:
        Integer CILA level (0-6).
    """
    if _L6_PATTERN.search(prompt):
        return 6
    if _L5_PATTERN.search(prompt):
        return 5
    if _L4_PATTERN.search(prompt):
        return 4
    if _L3_PATTERN.search(prompt):
        return 3
    if _L2_PATTERN.search(prompt):
        return 2
    if _L1_PATTERN.search(prompt):
        return 1
    return 0


def enforce_strategy(
    cila_level: int,
    *,
    precondition_exists: bool = True,
    has_code_first_context: bool = True,
) -> EnforcementResult:
    """Check strategy requirements for a classified CILA level.

    Uses GovernanceEnforcer and CILARouter from lib.governance when available,
    falls back to built-in logic otherwise.

    Args:
        cila_level: Detected CILA level (0-6).
        precondition_exists: Whether required state/preconditions exist.
        has_code_first_context: Whether CODE-FIRST context is active.

    Returns:
        EnforcementResult with action, warnings, and violations.
    """
    warnings: list[str] = []
    violations: list[str] = []

    if _GOVERNANCE_AVAILABLE:
        router = CILARouter()
        routing = router.route(cila_level)

        if routing["discover_required"]:
            warnings.append(
                f"DISCOVER REQUIRED (L{cila_level}): "
                "Search for existing scripts before creating new ones."
            )

        if routing["planning_required"] and not has_code_first_context:
            warnings.append(
                f"PLANNING REQUIRED (L{cila_level}): "
                "Document approach before implementation (CODE-FIRST cycle)."
            )

        # Additional warnings from router
        for warn in routing.get("warnings", []):
            if warn not in warnings:
                warnings.append(warn)

    else:
        # Fallback: built-in enforcement logic
        if cila_level >= 2:
            warnings.append(
                f"DISCOVER REQUIRED (L{cila_level}): "
                "Search for existing scripts before creating new ones."
            )

        if cila_level >= 3 and not has_code_first_context:
            warnings.append(
                f"PLANNING REQUIRED (L{cila_level}): "
                "Document approach before implementation."
            )

    # L3+: requires precondition state
    if cila_level >= 3 and not precondition_exists:
        violations.append(
            f"L{cila_level} requires verified preconditions. "
            "Check pipeline state or required artifacts before proceeding."
        )

    # L5+: requires explicit user approval
    if cila_level >= 5:
        violations.append(
            f"L{cila_level} (Self-Modifying/Multi-Agent) requires explicit user approval. "
            "Confirm intent before proceeding."
        )

    # L1+ should follow CODE-FIRST
    if cila_level >= 1 and not has_code_first_context:
        warnings.append(
            f"L{cila_level} should follow CODE-FIRST workflow: "
            "DISCOVER→CREATE→EXECUTE→EVALUATE→REFINE→PERSIST."
        )

    action = "warn" if (warnings or violations) else "allow"

    return EnforcementResult(
        action=action,
        cila_level=cila_level,
        warnings=warnings,
        violations=violations,
    )


def build_enforcement_context(result: EnforcementResult) -> str:
    """Build additionalContext string from enforcement result.

    Args:
        result: Enforcement result with warnings/violations.

    Returns:
        Compact context string for injection into Claude's context.
    """
    parts: list[str] = [f"CILA-Enforcer L{result.cila_level}: {result.action.upper()}"]

    for violation in result.violations:
        parts.append(f"VIOLATION: {violation}")

    for warning in result.warnings:
        parts.append(f"WARNING: {warning}")

    return ". ".join(parts) + "."


def check_governance_compliance(prompt: str) -> list[str]:
    """Run governance compliance checks on a prompt.

    Uses GovernanceEnforcer from lib.governance when available.

    Args:
        prompt: The task prompt to check.

    Returns:
        List of compliance warning messages (empty = fully compliant).
    """
    if not _GOVERNANCE_AVAILABLE:
        return []

    enforcer = GovernanceEnforcer()
    warnings: list[str] = []

    # Check CODE_FIRST compliance indicator
    has_code_first = any(
        kw in prompt.lower()
        for kw in ["discover", "execute", "evaluate", "persist", "code-first"]
    )

    result = enforcer.check_violation("CODE_FIRST", has_code_first or len(prompt) < 50)
    if result:
        warnings.append(result)

    return warnings


def main() -> None:
    """PreToolUse hook entry point.

    Reads JSON from stdin, classifies CILA level, enforces strategy,
    and emits additionalContext warnings. Always exits 0 (fail-open).
    """
    try:
        # Parse stdin
        try:
            raw = sys.stdin.read()
            if not raw.strip():
                sys.exit(ALLOW)
            data: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, EOFError, ValueError):
            sys.exit(ALLOW)

        tool_name: str = data.get("tool_name", "")

        # Only enforce on Task tool calls
        if tool_name != "Task":
            sys.exit(ALLOW)

        tool_input: dict[str, Any] = data.get("tool_input", {})
        prompt: str = tool_input.get("prompt", "")

        if not prompt.strip():
            sys.exit(ALLOW)

        # Classify CILA level
        cila_level = classify_cila_level(prompt)

        # Enforce strategy
        result = enforce_strategy(
            cila_level,
            precondition_exists=True,  # Optimistic — no filesystem check by default
            has_code_first_context=True,  # Advisory only
        )

        # Check governance compliance
        gov_warnings = check_governance_compliance(prompt)

        # Emit additionalContext if there are warnings/violations or governance issues
        all_warnings = list(result.warnings) + gov_warnings
        has_output = result.action == "warn" or result.violations or gov_warnings

        if has_output:
            context_parts = [f"CILA-Enforcer L{cila_level}: {result.action.upper()}"]
            for violation in result.violations:
                context_parts.append(f"VIOLATION: {violation}")
            for warning in all_warnings:
                if warning not in context_parts:
                    context_parts.append(f"WARNING: {warning}")
            context_msg = ". ".join(context_parts) + "."
            json.dump({"additionalContext": context_msg}, sys.stdout)

        sys.exit(ALLOW)

    except Exception as exc:
        # Fail-open: enforcement is advisory, never block on internal error
        logger.debug("Strategy enforcer error (fail-open): %s", exc)
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
