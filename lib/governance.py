"""Governance enforcement module for claude-code-kazuba.

Provides programmatic enforcement of:
- Core governance rules (CODE-FIRST cycle)
- CILA levels (L0-L6 classification and routing)
- Quality gates and compliance tracking

All models use frozen=True for immutability.
All public functions are pure (no side effects).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Models (frozen=True)
# ---------------------------------------------------------------------------


class GovernanceRule(BaseModel, frozen=True):
    """A single governance rule definition.

    Attributes:
        name: Rule identifier (e.g. "CODE_FIRST", "ZERO_HALLUCINATION").
        level: Enforcement level ("mandatory" or "advisory").
        enforcement: Action on violation ("block", "warn", or "log").
        description: Human-readable description of the rule.
    """

    name: str = ""
    level: str = "mandatory"
    enforcement: str = "block"
    description: str = ""


class CodeFirstPhase(BaseModel, frozen=True):
    """Represents one phase of the CODE-FIRST 6-step cycle.

    Attributes:
        phase: Phase name (DISCOVER, CREATE, EXECUTE, EVALUATE, REFINE, PERSIST).
        completed: Whether this phase has been completed.
        evidence: Proof of completion (e.g. script path, test output).
    """

    phase: str = ""
    completed: bool = False
    evidence: str = ""


class ValidationCriteria(BaseModel, frozen=True):
    """A single validation criterion for the delivery checklist.

    Attributes:
        name: Criterion name (e.g. "FUNCTIONAL", "TESTED", "ROBUST").
        required: Whether this criterion must pass (True) or is optional.
        gate: Which gate this belongs to ("functional", "quality", "security").
    """

    name: str = ""
    required: bool = True
    gate: str = "functional"


class CILALevel(BaseModel, frozen=True):
    """Descriptor for a CILA classification level.

    Attributes:
        level: Integer level (0-6).
        name: Short name (e.g. "Direct", "PAL", "Tool-Augmented").
        description: What tasks belong to this level.
        planning_required: Whether upfront planning is mandatory.
        coverage_target: Minimum test coverage percentage.
        quality_gate_required: Whether quality gate must pass.
    """

    level: int = 0
    name: str = ""
    description: str = ""
    planning_required: bool = False
    coverage_target: int = 0
    quality_gate_required: bool = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GOVERNANCE_RULES: list[GovernanceRule] = [
    GovernanceRule(
        name="CODE_FIRST",
        level="mandatory",
        enforcement="block",
        description="Every task must follow DISCOVER→CREATE→EXECUTE→EVALUATE→REFINE→PERSIST cycle.",
    ),
    GovernanceRule(
        name="ZERO_HALLUCINATION",
        level="mandatory",
        enforcement="block",
        description="Never invent file paths, API methods, or test results without verification.",
    ),
    GovernanceRule(
        name="FROZEN_MODELS",
        level="mandatory",
        enforcement="block",
        description="All dataclasses and BaseModel must use frozen=True.",
    ),
    GovernanceRule(
        name="FUTURE_ANNOTATIONS",
        level="mandatory",
        enforcement="block",
        description="All Python files must start with 'from __future__ import annotations'.",
    ),
    GovernanceRule(
        name="FAIL_OPEN",
        level="mandatory",
        enforcement="block",
        description="Hooks must always exit 0 on internal error (fail-open). Only exit 2 to block.",
    ),
    GovernanceRule(
        name="COVERAGE_90",
        level="mandatory",
        enforcement="warn",
        description="Minimum 90% test coverage per file.",
    ),
    GovernanceRule(
        name="COMPLEXITY_10",
        level="mandatory",
        enforcement="warn",
        description="Maximum cyclomatic complexity of 10 per function.",
    ),
    GovernanceRule(
        name="HOOKS_INVIOLABLE",
        level="mandatory",
        enforcement="block",
        description="Never ignore, disable, or bypass hooks.",
    ),
]

CILA_LEVELS: list[CILALevel] = [
    CILALevel(
        level=0,
        name="Direct",
        description="Direct textual response — no code, no pipeline.",
        planning_required=False,
        coverage_target=0,
        quality_gate_required=False,
    ),
    CILALevel(
        level=1,
        name="PAL",
        description="Program-Aided Language — generates simple code (calc/format/convert).",
        planning_required=False,
        coverage_target=0,
        quality_gate_required=False,
    ),
    CILALevel(
        level=2,
        name="Tool-Augmented",
        description="Uses external tools (Bash, Read/Write, search). DISCOVER required.",
        planning_required=False,
        coverage_target=80,
        quality_gate_required=False,
    ),
    CILALevel(
        level=3,
        name="Pipelines",
        description="Multi-phase pipelines with state verification required.",
        planning_required=True,
        coverage_target=90,
        quality_gate_required=True,
    ),
    CILALevel(
        level=4,
        name="Agent Loops",
        description="ReAct loops with self-correction (max 3 iterations).",
        planning_required=True,
        coverage_target=90,
        quality_gate_required=True,
    ),
    CILALevel(
        level=5,
        name="Self-Modifying",
        description="Modifies own behavior — requires explicit user approval.",
        planning_required=True,
        coverage_target=95,
        quality_gate_required=True,
    ),
    CILALevel(
        level=6,
        name="Multi-Agent",
        description="Orchestrates multiple agents (swarm/team). Full team sequence required.",
        planning_required=True,
        coverage_target=95,
        quality_gate_required=True,
    ),
]

CODE_FIRST_PHASES: list[str] = [
    "DISCOVER",
    "CREATE",
    "EXECUTE",
    "EVALUATE",
    "REFINE",
    "PERSIST",
]

VALIDATION_CRITERIA: list[ValidationCriteria] = [
    ValidationCriteria(name="FUNCTIONAL", required=True, gate="functional"),
    ValidationCriteria(name="TESTED", required=True, gate="functional"),
    ValidationCriteria(name="ROBUST", required=True, gate="quality"),
    ValidationCriteria(name="READABLE", required=True, gate="quality"),
    ValidationCriteria(name="DOCUMENTED", required=True, gate="quality"),
    ValidationCriteria(name="NO_REGRESS", required=True, gate="functional"),
    ValidationCriteria(name="NO_HALLUC", required=True, gate="security"),
    ValidationCriteria(name="DELIVERABLE", required=True, gate="functional"),
]


# ---------------------------------------------------------------------------
# Pure Functions
# ---------------------------------------------------------------------------


def check_governance_rule(rule_name: str) -> GovernanceRule | None:
    """Look up a governance rule by name.

    Args:
        rule_name: The rule identifier (case-insensitive).

    Returns:
        The GovernanceRule if found, None otherwise.
    """
    name_upper = rule_name.upper()
    for rule in GOVERNANCE_RULES:
        if rule.name == name_upper:
            return rule
    return None


def get_cila_level(level: int) -> CILALevel | None:
    """Look up a CILA level descriptor by integer level.

    Args:
        level: Integer level 0-6.

    Returns:
        The CILALevel if valid, None otherwise.
    """
    if level < 0 or level > 6:
        return None
    for cila in CILA_LEVELS:
        if cila.level == level:
            return cila
    return None


def enforce_code_first(phases: list[CodeFirstPhase]) -> list[str]:
    """Check CODE-FIRST cycle compliance and return violations.

    Args:
        phases: List of CodeFirstPhase objects representing cycle state.

    Returns:
        List of violation messages (empty = compliant).
    """
    violations: list[str] = []
    completed_names = {p.phase for p in phases if p.completed}

    for phase_name in CODE_FIRST_PHASES:
        if phase_name not in completed_names:
            violations.append(f"Phase {phase_name} not completed.")

    return violations


# ---------------------------------------------------------------------------
# Enforcement Classes
# ---------------------------------------------------------------------------


class GovernanceEnforcer:
    """Applies governance rules to check compliance.

    All rules are checked against the canonical GOVERNANCE_RULES list.
    Results are deterministic for given inputs.
    """

    def __init__(self) -> None:
        """Initialize with the canonical rule set."""
        self._rules: dict[str, GovernanceRule] = {r.name: r for r in GOVERNANCE_RULES}

    @property
    def rules(self) -> list[GovernanceRule]:
        """Return all registered governance rules."""
        return list(self._rules.values())

    def check_rule(self, rule_name: str) -> GovernanceRule | None:
        """Check a governance rule by name.

        Args:
            rule_name: The rule identifier (case-insensitive).

        Returns:
            The GovernanceRule if found, None otherwise.
        """
        return self._rules.get(rule_name.upper())

    def check_violation(self, rule_name: str, condition: bool) -> str | None:
        """Check if a governance rule is violated.

        Args:
            rule_name: The rule identifier.
            condition: True if the rule condition is MET (no violation).

        Returns:
            Violation message if violated, None if compliant.
        """
        if condition:
            return None
        rule = self.check_rule(rule_name)
        if rule is None:
            return f"Unknown rule: {rule_name}"
        return f"VIOLATION [{rule.enforcement.upper()}] {rule.name}: {rule.description}"

    def validate_all(self, conditions: dict[str, bool]) -> list[str]:
        """Validate multiple rules at once.

        Args:
            conditions: Mapping of rule_name → condition_met (True = compliant).

        Returns:
            List of violation messages for failed conditions.
        """
        violations: list[str] = []
        for rule_name, condition in conditions.items():
            msg = self.check_violation(rule_name, condition)
            if msg is not None:
                violations.append(msg)
        return violations


class CodeFirstCycle:
    """Manages the 6-phase CODE-FIRST cycle.

    Tracks which phases have been completed and provides
    validation of cycle compliance.
    """

    def __init__(self) -> None:
        """Initialize cycle with all phases incomplete."""
        self._phases: dict[str, CodeFirstPhase] = {
            name: CodeFirstPhase(phase=name, completed=False, evidence="")
            for name in CODE_FIRST_PHASES
        }
        self._current_index: int = 0

    @property
    def phases(self) -> list[CodeFirstPhase]:
        """Return all phases in order."""
        return [self._phases[name] for name in CODE_FIRST_PHASES]

    @property
    def current_phase(self) -> str | None:
        """Return the name of the current active phase."""
        if self._current_index >= len(CODE_FIRST_PHASES):
            return None
        return CODE_FIRST_PHASES[self._current_index]

    @property
    def is_complete(self) -> bool:
        """Check if all required phases have been completed."""
        return all(p.completed for p in self._phases.values() if p.phase != "REFINE")

    def advance(self, evidence: str = "") -> bool:
        """Mark current phase complete and advance to next.

        Args:
            evidence: Proof of completion (script path, output, etc.).

        Returns:
            True if advanced successfully, False if already at end.
        """
        if self._current_index >= len(CODE_FIRST_PHASES):
            return False

        phase_name = CODE_FIRST_PHASES[self._current_index]
        self._phases[phase_name] = CodeFirstPhase(
            phase=phase_name, completed=True, evidence=evidence
        )
        self._current_index += 1
        return True

    def complete_phase(self, phase_name: str, evidence: str = "") -> bool:
        """Mark a specific phase as complete.

        Args:
            phase_name: Name of phase to complete.
            evidence: Proof of completion.

        Returns:
            True if phase found and marked complete, False otherwise.
        """
        phase_name_upper = phase_name.upper()
        if phase_name_upper not in self._phases:
            return False
        self._phases[phase_name_upper] = CodeFirstPhase(
            phase=phase_name_upper, completed=True, evidence=evidence
        )
        return True

    def get_violations(self) -> list[str]:
        """Get list of incomplete required phases.

        Returns:
            List of phase names that are required but not completed.
            REFINE is optional, so it is excluded from violations.
        """
        required_phases = [p for p in CODE_FIRST_PHASES if p != "REFINE"]
        return [
            f"Phase {name} not completed."
            for name in required_phases
            if not self._phases[name].completed
        ]

    def summary(self) -> dict[str, Any]:
        """Return cycle state as a dictionary.

        Returns:
            Dict with phase names as keys and completion status as values.
        """
        return {
            p.phase: {"completed": p.completed, "evidence": p.evidence}
            for p in self.phases
        }


class CILARouter:
    """Routes tasks based on CILA level classification.

    Determines required workflow behavior for each CILA level
    and generates enforcement recommendations.
    """

    def __init__(self) -> None:
        """Initialize with canonical CILA level definitions."""
        self._levels: dict[int, CILALevel] = {c.level: c for c in CILA_LEVELS}

    @property
    def levels(self) -> list[CILALevel]:
        """Return all CILA levels in order."""
        return [self._levels[i] for i in sorted(self._levels)]

    def get_level(self, level: int) -> CILALevel | None:
        """Get CILA level descriptor by integer.

        Args:
            level: Integer 0-6.

        Returns:
            CILALevel if valid, None otherwise.
        """
        return self._levels.get(level)

    def route(self, level: int) -> dict[str, Any]:
        """Determine routing strategy for a given CILA level.

        Args:
            level: Integer CILA level 0-6.

        Returns:
            Dict with routing recommendations:
                - level: int
                - name: str
                - planning_required: bool
                - discover_required: bool (True for L2+)
                - quality_gate_required: bool
                - coverage_target: int
                - warnings: list[str]
        """
        cila = self._levels.get(level)
        if cila is None:
            return {
                "level": level,
                "name": "Unknown",
                "planning_required": True,
                "discover_required": True,
                "quality_gate_required": True,
                "coverage_target": 90,
                "warnings": [f"Unknown CILA level {level} — defaulting to strict enforcement."],
            }

        warnings: list[str] = []
        discover_required = level >= 2

        if discover_required:
            warnings.append(
                f"DISCOVER REQUIRED (L{level}): Search for existing scripts before creating new ones."
            )

        if cila.planning_required:
            warnings.append(
                f"PLANNING REQUIRED (L{level}): Document approach before implementation."
            )

        if level >= 5:
            warnings.append(
                f"USER APPROVAL REQUIRED (L{level}): This level requires explicit user consent."
            )

        return {
            "level": level,
            "name": cila.name,
            "planning_required": cila.planning_required,
            "discover_required": discover_required,
            "quality_gate_required": cila.quality_gate_required,
            "coverage_target": cila.coverage_target,
            "warnings": warnings,
        }

    def planning_required(self, level: int) -> bool:
        """Check if planning is required for this CILA level.

        Args:
            level: Integer CILA level 0-6.

        Returns:
            True if planning is mandatory for this level.
        """
        cila = self._levels.get(level)
        if cila is None:
            return True  # Unknown levels require planning by default
        return cila.planning_required
