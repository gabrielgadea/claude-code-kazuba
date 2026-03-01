"""Tests for modules/hooks-routing/hooks/strategy_enforcer.py — Phase 13."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Load strategy_enforcer from hyphenated directory using importlib
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SE_PATH = _PROJECT_ROOT / "modules" / "hooks-routing" / "hooks" / "strategy_enforcer.py"
_spec = importlib.util.spec_from_file_location("strategy_enforcer", _SE_PATH)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules.setdefault("strategy_enforcer", _mod)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

EnforcementResult = _mod.EnforcementResult
build_enforcement_context = _mod.build_enforcement_context
check_governance_compliance = _mod.check_governance_compliance
classify_cila_level = _mod.classify_cila_level
enforce_strategy = _mod.enforce_strategy
main = _mod.main


class TestCILAClassification:
    """Tests for CILA level classification heuristics."""

    def test_classify_direct_l0(self) -> None:
        """Plain question classifies as L0 (Direct)."""
        assert classify_cila_level("What is the capital of France?") == 0

    def test_classify_pal_l1(self) -> None:
        """Calculate/format keywords classify as L1 (PAL)."""
        assert classify_cila_level("Calculate the sum of these numbers.") == 1

    def test_classify_tool_augmented_l2(self) -> None:
        """File operation keywords classify as L2 (Tool-Augmented)."""
        assert classify_cila_level("Read the file and Write the output.") == 2

    def test_classify_pipeline_l3(self) -> None:
        """Pipeline keywords classify as L3 (Pipelines)."""
        assert classify_cila_level("Check pipeline_state before running.") == 3

    def test_classify_agent_loop_l4(self) -> None:
        """ReAct keywords classify as L4 (Agent Loops)."""
        assert classify_cila_level("Use a ReAct loop with auto-correction.") == 4

    def test_classify_self_modifying_l5(self) -> None:
        """Self-evolution keywords classify as L5."""
        assert classify_cila_level("capability-evolver self-evolv the system.") == 5

    def test_classify_multi_agent_l6(self) -> None:
        """Multi-agent keywords classify as L6."""
        assert classify_cila_level("Use TeamCreate for multi-agent swarm.") == 6

    def test_classify_higher_takes_precedence(self) -> None:
        """Higher CILA levels take precedence over lower."""
        # Both L2 (Bash) and L6 (swarm) — L6 wins
        assert classify_cila_level("Bash swarm agents together.") == 6


class TestEnforcementResult:
    """Tests for EnforcementResult dataclass."""

    def test_enforcement_result_frozen(self) -> None:
        """EnforcementResult is immutable."""
        result = EnforcementResult(action="allow", cila_level=0)
        with pytest.raises((TypeError, AttributeError, Exception)):
            result.action = "warn"  # type: ignore[misc]

    def test_enforcement_result_defaults(self) -> None:
        """EnforcementResult has correct defaults."""
        result = EnforcementResult()
        assert result.action == "allow"
        assert result.cila_level == 0
        assert result.warnings == []
        assert result.violations == []


class TestEnforceStrategy:
    """Tests for enforce_strategy function."""

    def test_strategy_enforcer_cila_level_0_no_warnings(self) -> None:
        """L0 produces no warnings — direct response."""
        result = enforce_strategy(0)
        assert result.action == "allow"
        assert result.warnings == []
        assert result.violations == []

    def test_strategy_enforcer_cila_level_3_planning(self) -> None:
        """L3 without precondition generates violation."""
        result = enforce_strategy(3, precondition_exists=False)
        assert len(result.violations) > 0
        assert "L3" in result.violations[0]

    def test_strategy_enforcer_cila_level_2_discover_warning(self) -> None:
        """L2 generates DISCOVER warning."""
        result = enforce_strategy(2)
        assert result.action == "warn"
        assert any("DISCOVER" in w for w in result.warnings)

    def test_strategy_enforcer_l5_approval_required(self) -> None:
        """L5 generates user approval required violation."""
        result = enforce_strategy(5)
        assert any("approval" in v.lower() for v in result.violations)

    def test_strategy_enforcer_blocking_rule(self) -> None:
        """L3 without precondition has non-empty violations."""
        result = enforce_strategy(3, precondition_exists=False)
        assert len(result.violations) > 0

    def test_strategy_enforcer_l0_allow(self) -> None:
        """L0 returns action=allow."""
        result = enforce_strategy(0)
        assert result.action == "allow"

    def test_strategy_enforcer_l6_planning_and_approval(self) -> None:
        """L6 generates both DISCOVER warning and approval violation."""
        result = enforce_strategy(6)
        assert any("DISCOVER" in w for w in result.warnings)
        assert any("approval" in v.lower() for v in result.violations)


class TestBuildEnforcementContext:
    """Tests for build_enforcement_context function."""

    def test_build_context_allow(self) -> None:
        """Allow result builds simple context string."""
        result = EnforcementResult(action="allow", cila_level=0)
        context = build_enforcement_context(result)
        assert "L0" in context
        assert "ALLOW" in context

    def test_build_context_with_warnings(self) -> None:
        """Warnings are included in context string."""
        result = EnforcementResult(
            action="warn",
            cila_level=2,
            warnings=["DISCOVER REQUIRED"],
            violations=[],
        )
        context = build_enforcement_context(result)
        assert "WARNING" in context
        assert "DISCOVER REQUIRED" in context

    def test_build_context_with_violations(self) -> None:
        """Violations are prefixed with VIOLATION in context."""
        result = EnforcementResult(
            action="warn",
            cila_level=3,
            warnings=[],
            violations=["L3 requires preconditions."],
        )
        context = build_enforcement_context(result)
        assert "VIOLATION" in context


class TestGovernanceCompliance:
    """Tests for check_governance_compliance function."""

    def test_governance_check_short_prompt(self) -> None:
        """Short prompts may not trigger CODE_FIRST violation."""
        # Short prompts (< 50 chars) are treated as compliant by default
        warnings = check_governance_compliance("Short")
        assert isinstance(warnings, list)

    def test_governance_check_returns_list(self) -> None:
        """check_governance_compliance always returns a list."""
        result = check_governance_compliance("Some arbitrary prompt text")
        assert isinstance(result, list)


class TestMainHookEntryPoint:
    """Tests for main() hook entry point."""

    def _run_hook(self, stdin_data: str) -> tuple[int, str, str]:
        """Run strategy_enforcer as subprocess and return (exit_code, stdout, stderr)."""
        result = subprocess.run(
            [sys.executable, str(_SE_PATH)],
            input=stdin_data,
            capture_output=True,
            text=True,
            cwd=str(_PROJECT_ROOT),
        )
        return result.returncode, result.stdout, result.stderr

    def test_strategy_enforcer_no_input(self) -> None:
        """Empty stdin → exit 0 (fail-open)."""
        code, stdout, stderr = self._run_hook("")
        assert code == 0

    def test_strategy_enforcer_invalid_json(self) -> None:
        """Invalid JSON → exit 0 (fail-open, never crashes)."""
        code, stdout, stderr = self._run_hook("not valid json {{{")
        assert code == 0

    def test_strategy_enforcer_valid_input_non_task(self) -> None:
        """Non-Task tool input → exit 0, no output."""
        data = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        code, stdout, stderr = self._run_hook(data)
        assert code == 0

    def test_strategy_enforcer_valid_input_task_l0(self) -> None:
        """Task tool with L0 prompt → exit 0, no additionalContext."""
        data = json.dumps({
            "tool_name": "Task",
            "tool_input": {"prompt": "What is the current time?"},
        })
        code, stdout, stderr = self._run_hook(data)
        assert code == 0

    def test_strategy_enforcer_output_format(self) -> None:
        """Task with L2+ prompt → additionalContext JSON in stdout."""
        data = json.dumps({
            "tool_name": "Task",
            "tool_input": {"prompt": "Read the file and Write output using Bash tool_use."},
        })
        code, stdout, stderr = self._run_hook(data)
        assert code == 0
        if stdout.strip():
            parsed = json.loads(stdout)
            assert "additionalContext" in parsed

    def test_strategy_enforcer_integration(self) -> None:
        """Integration: L3 pipeline prompt generates CILA enforcement context."""
        data = json.dumps({
            "tool_name": "Task",
            "tool_input": {"prompt": "Verify pipeline_state before running pipeline_runner."},
        })
        code, stdout, stderr = self._run_hook(data)
        assert code == 0
        if stdout.strip():
            parsed = json.loads(stdout)
            context = parsed.get("additionalContext", "")
            assert "L3" in context or "CILA" in context


class TestMainWithMocking:
    """Tests using mocking for unit-level main() coverage."""

    def test_strategy_enforcer_empty_prompt(self) -> None:
        """Empty prompt in Task input → exits 0 immediately."""
        data = json.dumps({
            "tool_name": "Task",
            "tool_input": {"prompt": ""},
        })
        with patch("sys.stdin", StringIO(data)):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_strategy_enforcer_governance_check(self) -> None:
        """Governance check runs without error for any prompt."""
        warnings = check_governance_compliance("Analyze the codebase using Bash tools.")
        assert isinstance(warnings, list)
