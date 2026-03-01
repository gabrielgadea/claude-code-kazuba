"""Tests for lib.governance — Phase 13 Core Governance + CILA Formal."""

from __future__ import annotations

import pytest

from claude_code_kazuba.governance import (
    CILA_LEVELS,
    CODE_FIRST_PHASES,
    GOVERNANCE_RULES,
    VALIDATION_CRITERIA,
    CILALevel,
    CILARouter,
    CodeFirstCycle,
    CodeFirstPhase,
    GovernanceEnforcer,
    GovernanceRule,
    ValidationCriteria,
    check_governance_rule,
    enforce_code_first,
    get_cila_level,
)


class TestGovernanceRule:
    """Tests for GovernanceRule Pydantic model."""

    def test_governance_rule_creation(self) -> None:
        """GovernanceRule creates with provided values."""
        rule = GovernanceRule(
            name="TEST_RULE",
            level="mandatory",
            enforcement="block",
            description="Test rule",
        )
        assert rule.name == "TEST_RULE"
        assert rule.level == "mandatory"
        assert rule.enforcement == "block"
        assert rule.description == "Test rule"

    def test_governance_rule_frozen(self) -> None:
        """GovernanceRule is immutable (frozen=True)."""
        rule = GovernanceRule(name="FROZEN_RULE")
        with pytest.raises((TypeError, AttributeError, Exception)):
            rule.name = "CHANGED"  # type: ignore[misc]

    def test_governance_rule_defaults(self) -> None:
        """GovernanceRule has correct defaults."""
        rule = GovernanceRule()
        assert rule.name == ""
        assert rule.level == "mandatory"
        assert rule.enforcement == "block"
        assert rule.description == ""

    def test_governance_rule_advisory_level(self) -> None:
        """GovernanceRule supports advisory level."""
        rule = GovernanceRule(name="ADVISORY", level="advisory", enforcement="warn")
        assert rule.level == "advisory"
        assert rule.enforcement == "warn"

    def test_governance_rules_constant_non_empty(self) -> None:
        """GOVERNANCE_RULES constant has entries."""
        assert len(GOVERNANCE_RULES) > 0
        for rule in GOVERNANCE_RULES:
            assert isinstance(rule, GovernanceRule)
            assert rule.name != ""


class TestCodeFirstPhase:
    """Tests for CodeFirstPhase Pydantic model."""

    def test_code_first_phase_creation(self) -> None:
        """CodeFirstPhase creates with provided values."""
        phase = CodeFirstPhase(phase="DISCOVER", completed=True, evidence="found_script.py")
        assert phase.phase == "DISCOVER"
        assert phase.completed is True
        assert phase.evidence == "found_script.py"

    def test_code_first_phase_defaults(self) -> None:
        """CodeFirstPhase has correct defaults."""
        phase = CodeFirstPhase()
        assert phase.phase == ""
        assert phase.completed is False
        assert phase.evidence == ""

    def test_code_first_phase_completion(self) -> None:
        """CodeFirstPhase can represent completed state."""
        phase = CodeFirstPhase(phase="EXECUTE", completed=True, evidence="output.json")
        assert phase.completed is True
        assert phase.evidence == "output.json"

    def test_code_first_phase_frozen(self) -> None:
        """CodeFirstPhase is immutable."""
        phase = CodeFirstPhase(phase="CREATE")
        with pytest.raises((TypeError, AttributeError, Exception)):
            phase.completed = True  # type: ignore[misc]

    def test_code_first_phases_constant(self) -> None:
        """CODE_FIRST_PHASES has the 6 expected phases."""
        expected = {"DISCOVER", "CREATE", "EXECUTE", "EVALUATE", "REFINE", "PERSIST"}
        assert set(CODE_FIRST_PHASES) == expected
        assert len(CODE_FIRST_PHASES) == 6


class TestValidationCriteria:
    """Tests for ValidationCriteria Pydantic model."""

    def test_validation_criteria_creation(self) -> None:
        """ValidationCriteria creates with provided values."""
        criteria = ValidationCriteria(name="FUNCTIONAL", required=True, gate="functional")
        assert criteria.name == "FUNCTIONAL"
        assert criteria.required is True
        assert criteria.gate == "functional"

    def test_validation_criteria_frozen(self) -> None:
        """ValidationCriteria is immutable."""
        criteria = ValidationCriteria(name="TESTED")
        with pytest.raises((TypeError, AttributeError, Exception)):
            criteria.required = False  # type: ignore[misc]

    def test_validation_criteria_defaults(self) -> None:
        """ValidationCriteria has correct defaults."""
        criteria = ValidationCriteria()
        assert criteria.name == ""
        assert criteria.required is True
        assert criteria.gate == "functional"

    def test_validation_criteria_constant_non_empty(self) -> None:
        """VALIDATION_CRITERIA constant has entries."""
        assert len(VALIDATION_CRITERIA) > 0
        for crit in VALIDATION_CRITERIA:
            assert isinstance(crit, ValidationCriteria)


class TestCILALevel:
    """Tests for CILALevel Pydantic model."""

    def test_cila_level_creation(self) -> None:
        """CILALevel creates with provided values."""
        cila = CILALevel(
            level=3,
            name="Pipelines",
            description="Multi-phase pipelines.",
            planning_required=True,
            coverage_target=90,
            quality_gate_required=True,
        )
        assert cila.level == 3
        assert cila.name == "Pipelines"
        assert cila.planning_required is True
        assert cila.coverage_target == 90
        assert cila.quality_gate_required is True

    def test_cila_level_frozen(self) -> None:
        """CILALevel is immutable."""
        cila = CILALevel(level=2)
        with pytest.raises((TypeError, AttributeError, Exception)):
            cila.level = 5  # type: ignore[misc]

    def test_cila_level_defaults(self) -> None:
        """CILALevel has correct defaults."""
        cila = CILALevel()
        assert cila.level == 0
        assert cila.name == ""
        assert cila.planning_required is False
        assert cila.coverage_target == 0
        assert cila.quality_gate_required is False

    def test_cila_levels_constant_complete(self) -> None:
        """CILA_LEVELS constant covers L0-L6."""
        levels = {c.level for c in CILA_LEVELS}
        assert levels == {0, 1, 2, 3, 4, 5, 6}


class TestGovernanceEnforcer:
    """Tests for GovernanceEnforcer class."""

    def test_governance_enforcer_init(self) -> None:
        """GovernanceEnforcer initializes with rules."""
        enforcer = GovernanceEnforcer()
        assert len(enforcer.rules) > 0

    def test_governance_enforcer_check_rule(self) -> None:
        """GovernanceEnforcer finds rules by name."""
        enforcer = GovernanceEnforcer()
        rule = enforcer.check_rule("CODE_FIRST")
        assert rule is not None
        assert rule.name == "CODE_FIRST"

    def test_governance_enforcer_check_rule_case_insensitive(self) -> None:
        """GovernanceEnforcer is case-insensitive for rule lookup."""
        enforcer = GovernanceEnforcer()
        rule = enforcer.check_rule("code_first")
        assert rule is not None

    def test_governance_enforcer_check_rule_missing(self) -> None:
        """GovernanceEnforcer returns None for unknown rule."""
        enforcer = GovernanceEnforcer()
        rule = enforcer.check_rule("NONEXISTENT_RULE")
        assert rule is None

    def test_governance_enforcer_check_violation_compliant(self) -> None:
        """GovernanceEnforcer returns None when condition is met."""
        enforcer = GovernanceEnforcer()
        result = enforcer.check_violation("CODE_FIRST", condition=True)
        assert result is None

    def test_governance_enforcer_check_violation_violated(self) -> None:
        """GovernanceEnforcer returns message when rule violated."""
        enforcer = GovernanceEnforcer()
        result = enforcer.check_violation("CODE_FIRST", condition=False)
        assert result is not None
        assert "CODE_FIRST" in result

    def test_governance_enforcer_validate_all(self) -> None:
        """GovernanceEnforcer.validate_all returns violations list."""
        enforcer = GovernanceEnforcer()
        violations = enforcer.validate_all({"CODE_FIRST": False, "ZERO_HALLUCINATION": True})
        assert len(violations) == 1
        assert "CODE_FIRST" in violations[0]

    def test_governance_enforcer_validate_all_compliant(self) -> None:
        """GovernanceEnforcer.validate_all returns empty for all compliant."""
        enforcer = GovernanceEnforcer()
        violations = enforcer.validate_all({"CODE_FIRST": True})
        assert violations == []


class TestCodeFirstCycle:
    """Tests for CodeFirstCycle class."""

    def test_code_first_cycle_init(self) -> None:
        """CodeFirstCycle initializes with all phases incomplete."""
        cycle = CodeFirstCycle()
        assert len(cycle.phases) == 6
        assert all(not p.completed for p in cycle.phases)

    def test_code_first_cycle_current_phase(self) -> None:
        """CodeFirstCycle.current_phase returns DISCOVER initially."""
        cycle = CodeFirstCycle()
        assert cycle.current_phase == "DISCOVER"

    def test_code_first_cycle_advance(self) -> None:
        """CodeFirstCycle.advance marks current phase complete and moves forward."""
        cycle = CodeFirstCycle()
        result = cycle.advance(evidence="existing_script.py")
        assert result is True
        assert cycle.current_phase == "CREATE"
        discover_phase = next(p for p in cycle.phases if p.phase == "DISCOVER")
        assert discover_phase.completed is True
        assert discover_phase.evidence == "existing_script.py"

    def test_code_first_cycle_complete_phase(self) -> None:
        """CodeFirstCycle.complete_phase marks a specific phase done."""
        cycle = CodeFirstCycle()
        success = cycle.complete_phase("EXECUTE", evidence="output.json")
        assert success is True
        execute_phase = next(p for p in cycle.phases if p.phase == "EXECUTE")
        assert execute_phase.completed is True

    def test_code_first_cycle_complete_phase_unknown(self) -> None:
        """CodeFirstCycle.complete_phase returns False for unknown phase."""
        cycle = CodeFirstCycle()
        result = cycle.complete_phase("UNKNOWN_PHASE")
        assert result is False

    def test_code_first_cycle_complete(self) -> None:
        """CodeFirstCycle.is_complete is True when required phases done."""
        cycle = CodeFirstCycle()
        required = [p for p in CODE_FIRST_PHASES if p != "REFINE"]
        for phase in required:
            cycle.complete_phase(phase)
        assert cycle.is_complete is True

    def test_code_first_cycle_not_complete(self) -> None:
        """CodeFirstCycle.is_complete is False when phases remain."""
        cycle = CodeFirstCycle()
        cycle.complete_phase("DISCOVER")
        assert cycle.is_complete is False

    def test_code_first_cycle_violations(self) -> None:
        """CodeFirstCycle.get_violations returns incomplete required phases."""
        cycle = CodeFirstCycle()
        violations = cycle.get_violations()
        # All required phases incomplete initially
        assert len(violations) >= 4  # DISCOVER, CREATE, EXECUTE, EVALUATE, PERSIST

    def test_code_first_cycle_summary(self) -> None:
        """CodeFirstCycle.summary returns dict with all phases."""
        cycle = CodeFirstCycle()
        summary = cycle.summary()
        assert set(summary.keys()) == set(CODE_FIRST_PHASES)


class TestCILARouter:
    """Tests for CILARouter class."""

    def test_cila_router_init(self) -> None:
        """CILARouter initializes with all 7 levels."""
        router = CILARouter()
        assert len(router.levels) == 7

    def test_cila_router_get_level(self) -> None:
        """CILARouter.get_level returns correct descriptor."""
        router = CILARouter()
        level = router.get_level(3)
        assert level is not None
        assert level.level == 3
        assert level.name == "Pipelines"

    def test_cila_router_get_level_invalid(self) -> None:
        """CILARouter.get_level returns None for invalid level."""
        router = CILARouter()
        level = router.get_level(99)
        assert level is None

    def test_cila_router_route(self) -> None:
        """CILARouter.route returns routing dict for valid level."""
        router = CILARouter()
        routing = router.route(2)
        assert routing["level"] == 2
        assert routing["name"] == "Tool-Augmented"
        assert isinstance(routing["warnings"], list)

    def test_cila_router_route_l0_no_warnings(self) -> None:
        """CILARouter.route L0 has no warnings (direct response)."""
        router = CILARouter()
        routing = router.route(0)
        assert routing["planning_required"] is False
        assert routing["discover_required"] is False

    def test_cila_router_route_l2_discover_required(self) -> None:
        """CILARouter.route L2+ requires DISCOVER."""
        router = CILARouter()
        routing = router.route(2)
        assert routing["discover_required"] is True

    def test_cila_router_planning_required(self) -> None:
        """CILARouter.planning_required returns correct value per level."""
        router = CILARouter()
        assert router.planning_required(0) is False
        assert router.planning_required(1) is False
        assert router.planning_required(3) is True
        assert router.planning_required(6) is True

    def test_cila_router_planning_required_unknown(self) -> None:
        """CILARouter.planning_required returns True for unknown level."""
        router = CILARouter()
        assert router.planning_required(99) is True


class TestPureFunctions:
    """Tests for module-level pure functions."""

    def test_check_governance_rule_found(self) -> None:
        """check_governance_rule returns rule when found."""
        rule = check_governance_rule("CODE_FIRST")
        assert rule is not None
        assert rule.name == "CODE_FIRST"

    def test_check_governance_rule_not_found(self) -> None:
        """check_governance_rule returns None when not found."""
        rule = check_governance_rule("NONEXISTENT")
        assert rule is None

    def test_get_cila_level_valid(self) -> None:
        """get_cila_level returns descriptor for valid level."""
        cila = get_cila_level(4)
        assert cila is not None
        assert cila.level == 4
        assert cila.name == "Agent Loops"

    def test_get_cila_level_invalid(self) -> None:
        """get_cila_level returns None for out-of-range level."""
        assert get_cila_level(-1) is None
        assert get_cila_level(7) is None

    def test_enforce_code_first_all_complete(self) -> None:
        """enforce_code_first returns empty list when all phases done."""
        phases = [CodeFirstPhase(phase=name, completed=True) for name in CODE_FIRST_PHASES]
        violations = enforce_code_first(phases)
        assert violations == []

    def test_enforce_code_first_missing_phases(self) -> None:
        """enforce_code_first reports incomplete phases."""
        phases = [CodeFirstPhase(phase="DISCOVER", completed=True)]
        violations = enforce_code_first(phases)
        assert len(violations) > 0
        assert any("PERSIST" in v for v in violations)
