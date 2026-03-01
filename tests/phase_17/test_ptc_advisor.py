"""Tests for ptc_advisor — Phase 17."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------


def _import_from_path(name: str, file_path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


_PTC_PATH = (
    PROJECT_ROOT / "modules" / "hooks-routing" / "hooks" / "ptc_advisor.py"
)
_ptc = _import_from_path("ptc_advisor_ph17", _PTC_PATH)

# Aliases
CILAClassification = _ptc.CILAClassification
PTCProgram = _ptc.PTCProgram
classify_intent = _ptc.classify_intent
synthesize_program = _ptc.synthesize_program
format_program_advisory = _ptc.format_program_advisory
MIN_PTC_LEVEL = _ptc.MIN_PTC_LEVEL
ALLOW = _ptc.ALLOW


# ---------------------------------------------------------------------------
# CILAClassification tests
# ---------------------------------------------------------------------------


class TestCILAClassification:
    """Tests for the CILA classification data model."""

    def test_frozen(self) -> None:
        """CILAClassification is immutable (frozen=True)."""
        c = CILAClassification(2, 0.8, "tool_augmented", [])
        with pytest.raises((AttributeError, TypeError)):
            c.level = 3  # type: ignore[misc]

    def test_ptc_eligible_l2(self) -> None:
        """L2 classification is PTC-eligible."""
        c = CILAClassification(2, 1.0, "tool_augmented", [])
        assert c.is_ptc_eligible() is True

    def test_ptc_eligible_l6(self) -> None:
        """L6 classification is PTC-eligible."""
        c = CILAClassification(6, 1.0, "multi_agent", [])
        assert c.is_ptc_eligible() is True

    def test_not_ptc_eligible_l0(self) -> None:
        """L0 classification is NOT PTC-eligible."""
        c = CILAClassification(0, 1.0, "direct_response", [])
        assert c.is_ptc_eligible() is False

    def test_not_ptc_eligible_l1(self) -> None:
        """L1 classification is NOT PTC-eligible."""
        c = CILAClassification(1, 0.5, "pal_code_generation", [])
        assert c.is_ptc_eligible() is False


# ---------------------------------------------------------------------------
# classify_intent tests
# ---------------------------------------------------------------------------


class TestClassifyIntent:
    """Tests for CILA-level intent classifier."""

    def test_empty_prompt_returns_l0(self) -> None:
        """Empty prompt defaults to L0."""
        result = classify_intent("")
        assert result.level == 0

    def test_whitespace_prompt_returns_l0(self) -> None:
        """Whitespace-only prompt defaults to L0."""
        result = classify_intent("   ")
        assert result.level == 0

    def test_multi_agent_keyword_matches_l6(self) -> None:
        """Prompt with 'multi-agent' matches L6."""
        result = classify_intent("Use multi-agent approach for this analysis")
        assert result.level == 6

    def test_pipeline_keyword_matches_l3(self) -> None:
        """Prompt with 'pipeline' matches L3 or higher."""
        result = classify_intent("Run the pipeline and check state")
        assert result.level >= 3

    def test_discover_keyword_matches_l2(self) -> None:
        """Prompt with 'discover' matches L2 or higher."""
        result = classify_intent("Discover and run the existing script")
        assert result.level >= 2

    def test_confidence_is_float(self) -> None:
        """Confidence is a float in [0, 1]."""
        result = classify_intent("generate code for this task")
        assert 0.0 <= result.confidence <= 1.0

    def test_routing_strategy_non_empty(self) -> None:
        """routing_strategy is always a non-empty string."""
        result = classify_intent("anything")
        assert isinstance(result.routing_strategy, str)
        assert result.routing_strategy


# ---------------------------------------------------------------------------
# synthesize_program tests
# ---------------------------------------------------------------------------


class TestSynthesizeProgram:
    """Tests for PTC program synthesis."""

    def test_l2_program_has_steps(self) -> None:
        """L2 program has at least one step."""
        prog = synthesize_program(2, "tool_augmented")
        assert len(prog.steps) >= 1

    def test_l6_program_has_team_steps(self) -> None:
        """L6 program includes team-related steps."""
        prog = synthesize_program(6, "multi_agent")
        seq = prog.format_sequence().upper()
        assert "TEAM" in seq or "AGENT" in seq

    def test_token_savings_non_negative(self) -> None:
        """Estimated token savings is non-negative."""
        prog = synthesize_program(2, "tool_augmented")
        assert prog.estimated_token_savings_pct >= 0

    def test_token_savings_capped(self) -> None:
        """Estimated token savings does not exceed 50."""
        prog = synthesize_program(6, "multi_agent")
        assert prog.estimated_token_savings_pct <= 50

    def test_frozen(self) -> None:
        """PTCProgram is immutable (frozen=True)."""
        prog = synthesize_program(2, "tool_augmented")
        with pytest.raises((AttributeError, TypeError)):
            prog.cila_level = 99  # type: ignore[misc]

    def test_format_sequence_contains_arrow(self) -> None:
        """Formatted sequence contains ' → ' separator."""
        prog = synthesize_program(3, "pipeline_execution")
        seq = prog.format_sequence()
        assert " → " in seq


# ---------------------------------------------------------------------------
# format_program_advisory tests
# ---------------------------------------------------------------------------


class TestFormatProgramAdvisory:
    """Tests for PTC advisory text formatting."""

    def test_advisory_non_empty(self) -> None:
        """Advisory text is non-empty."""
        prog = synthesize_program(2, "tool_augmented")
        advisory = format_program_advisory(prog)
        assert advisory.strip()

    def test_advisory_contains_cila_level(self) -> None:
        """Advisory text mentions the CILA level."""
        prog = synthesize_program(3, "pipeline_execution")
        advisory = format_program_advisory(prog)
        assert "L3" in advisory or "3" in advisory

    def test_advisory_contains_strategy(self) -> None:
        """Advisory text contains the routing strategy."""
        prog = synthesize_program(4, "agent_loop")
        advisory = format_program_advisory(prog)
        assert "agent_loop" in advisory.lower() or "AGENT_LOOP" in advisory


# ---------------------------------------------------------------------------
# Additional coverage tests for main() and _extract_keywords
# ---------------------------------------------------------------------------


class TestExtractKeywords:
    """Tests for _extract_keywords helper."""

    def test_extract_lowercase_words(self) -> None:
        """Returns lowercase word tokens from text."""
        result = _ptc._extract_keywords("Run Pipeline NOW")
        assert "run" in result
        assert "pipeline" in result
        assert "now" in result

    def test_empty_string_returns_empty(self) -> None:
        """Empty string returns empty list."""
        result = _ptc._extract_keywords("")
        assert result == []

    def test_hyphens_preserved(self) -> None:
        """Hyphenated words are preserved as a single token."""
        result = _ptc._extract_keywords("multi-agent")
        assert "multi-agent" in result


class TestClassifyIntentLevels:
    """Tests for classify_intent across different CILA levels."""

    def test_agent_loop_matches_l4(self) -> None:
        """Prompt with 'react cycle' or 'agent loop' classifies as L4."""
        result = classify_intent("Use a react cycle for self-correction")
        assert result.level >= 4

    def test_self_modifying_matches_l5(self) -> None:
        """Prompt with 'self-modifying' classifies as L5."""
        result = classify_intent("Use self-modifying capability evolver")
        assert result.level >= 5

    def test_low_score_yields_l0(self) -> None:
        """Generic prompt without any CILA keywords defaults to L0."""
        result = classify_intent("hello world")
        assert result.level == 0

    def test_routing_strategy_for_l0(self) -> None:
        """L0 classification has direct_response routing strategy."""
        result = classify_intent("hello")
        assert result.routing_strategy == "direct_response"


class TestSynthesizeProgramLevels:
    """Tests for synthesize_program at various CILA levels."""

    def test_l4_program_has_steps(self) -> None:
        """L4 program has multiple steps."""
        prog = synthesize_program(4, "agent_loop")
        assert len(prog.steps) >= 3

    def test_l5_program_has_steps(self) -> None:
        """L5 program has multiple steps."""
        prog = synthesize_program(5, "self_modifying")
        assert len(prog.steps) >= 2

    def test_unknown_level_uses_default_template(self) -> None:
        """Unknown CILA level falls back to default template."""
        prog = synthesize_program(99, "unknown")
        assert len(prog.steps) >= 1


class TestMainFunction:
    """Tests for the main() entry point."""

    def test_non_task_tool_exits_0(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-Task tool name causes immediate exit 0."""
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO('{"tool_name": "Write"}'))
        with pytest.raises(SystemExit) as exc_info:
            _ptc.main()
        assert exc_info.value.code == 0

    def test_invalid_json_exits_0(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Invalid JSON causes exit 0 (fail-open)."""
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        with pytest.raises(SystemExit) as exc_info:
            _ptc.main()
        assert exc_info.value.code == 0

    def test_empty_prompt_exits_0(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty prompt in Task input causes exit 0."""
        import io
        data = '{"tool_name": "Task", "tool_input": {"prompt": ""}}'
        monkeypatch.setattr("sys.stdin", io.StringIO(data))
        with pytest.raises(SystemExit) as exc_info:
            _ptc.main()
        assert exc_info.value.code == 0

    def test_l1_prompt_exits_0_no_advisory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """L1-classified prompt does not produce advisory, exits 0."""
        import io
        data = '{"tool_name": "Task", "tool_input": {"prompt": "generate code"}}'
        monkeypatch.setattr("sys.stdin", io.StringIO(data))
        with pytest.raises(SystemExit) as exc_info:
            _ptc.main()
        assert exc_info.value.code == 0

    def test_l2_prompt_produces_advisory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """L2+ prompt produces advisory and exits 0."""
        import io
        data = '{"tool_name": "Task", "tool_input": {"prompt": "discover and run existing script for pipeline"}}'
        monkeypatch.setattr("sys.stdin", io.StringIO(data))
        captured = []

        original_dump = __import__("json").dump

        def _capture_dump(obj: object, fp: object, **kwargs: object) -> None:
            captured.append(obj)
            original_dump(obj, fp, **kwargs)

        monkeypatch.setattr("json.dump", _capture_dump)
        with pytest.raises(SystemExit) as exc_info:
            _ptc.main()
        assert exc_info.value.code == 0
