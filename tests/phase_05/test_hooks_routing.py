"""Tests for hooks-routing module: cila_router, knowledge_manager, compliance_tracker."""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

# --- Helper to import module from file path ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _import_from_path(name: str, file_path: Path) -> ModuleType:
    """Import a Python module from an arbitrary file path."""
    lib_parent = str(PROJECT_ROOT)
    if lib_parent not in sys.path:
        sys.path.insert(0, lib_parent)
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    assert spec is not None, f"Cannot load spec for {file_path}"
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_hooks_dir = PROJECT_ROOT / "modules" / "hooks-routing" / "hooks"
cr = _import_from_path("cila_router", _hooks_dir / "cila_router.py")
km = _import_from_path("knowledge_manager", _hooks_dir / "knowledge_manager.py")
ct = _import_from_path("compliance_tracker", _hooks_dir / "compliance_tracker.py")


# --- Module manifest tests ---

class TestModuleManifest:
    """Test MODULE.md exists and has correct structure."""

    def test_module_md_exists(self, base_dir: Path) -> None:
        module_md = base_dir / "modules" / "hooks-routing" / "MODULE.md"
        assert module_md.is_file()

    def test_module_md_has_name(self, base_dir: Path) -> None:
        content = (base_dir / "modules" / "hooks-routing" / "MODULE.md").read_text()
        assert "name: hooks-routing" in content

    def test_module_md_has_dependencies(self, base_dir: Path) -> None:
        content = (base_dir / "modules" / "hooks-routing" / "MODULE.md").read_text()
        assert "core" in content
        assert "hooks-essential" in content


# --- Settings JSON tests ---

class TestSettingsJson:
    """Test settings.hooks.json is valid."""

    def test_settings_exists(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-routing" / "settings.hooks.json"
        assert path.is_file()

    def test_settings_valid_json(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-routing" / "settings.hooks.json"
        data = json.loads(path.read_text())
        assert "hooks" in data

    def test_settings_has_all_events(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-routing" / "settings.hooks.json"
        data = json.loads(path.read_text())
        assert "UserPromptSubmit" in data["hooks"]
        assert "PreToolUse" in data["hooks"]
        assert "PostToolUse" in data["hooks"]


# --- CILA router tests ---

class TestCILARouter:
    """Test CILA complexity classification."""

    def test_trivial_prompt_l0(self) -> None:
        result = cr.classify_complexity("yes")
        assert result.level == 0

    def test_simple_prompt_l1(self) -> None:
        result = cr.classify_complexity("read main.py")
        assert result.level <= 1

    def test_standard_prompt_l2(self) -> None:
        result = cr.classify_complexity("update the config and then add a new setting to the module")
        assert result.level >= 2

    def test_complex_prompt_l3(self) -> None:
        result = cr.classify_complexity("refactor all the modules to use the new pattern")
        assert result.level >= 3

    def test_advanced_prompt_l4(self) -> None:
        result = cr.classify_complexity("design a new architecture for the migration system")
        assert result.level >= 4

    def test_expert_prompt_l5(self) -> None:
        result = cr.classify_complexity(
            "research different approaches and compare evaluation options and alternatives"
        )
        assert result.level >= 5

    def test_extreme_prompt_l6(self) -> None:
        result = cr.classify_complexity(
            "use a team of parallel agents for a full rewrite from scratch"
        )
        assert result.level >= 5  # L5 or L6

    def test_cila_levels_defined(self) -> None:
        assert len(cr.CILA_LEVELS) == 7
        for i in range(7):
            assert i in cr.CILA_LEVELS

    def test_cila_routing_defined(self) -> None:
        assert len(cr.CILA_ROUTING) == 7
        for i in range(7):
            assert i in cr.CILA_ROUTING

    def test_classification_returns_result(self) -> None:
        result = cr.classify_complexity("hello")
        assert isinstance(result, cr.CILAResult)
        assert isinstance(result.level, int)
        assert 0 <= result.level <= 6

    def test_format_routing_context(self) -> None:
        result = cr.CILAResult(
            level=3, level_name="complex", routing_hint="Plan before executing."
        )
        ctx = cr.format_routing_context(result)
        assert "[cila-router]" in ctx
        assert "L3" in ctx
        assert "complex" in ctx

    def test_word_count_boost(self) -> None:
        """Long prompts should get a complexity boost."""
        short = cr.classify_complexity("fix the bug")
        long_prompt = "fix the bug " + "with additional context about the problem " * 30
        long_result = cr.classify_complexity(long_prompt)
        assert long_result.level >= short.level

    def test_caching_works(self) -> None:
        """Second classification of same prompt should use cache."""
        prompt = "show the files in the directory"
        r1 = cr.classify_complexity(prompt)
        r2 = cr.classify_complexity(prompt)
        assert r1.level == r2.level


# --- Knowledge manager tests ---

class TestKnowledgeManager:
    """Test 3-tier knowledge injection."""

    def test_tier1_cache_miss(self) -> None:
        result = km.tier1_cache_lookup("Read", "/nonexistent/path.py")
        assert result is None

    def test_tier2_project_docs(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Test Project\nSome docs.")
        entries = km.tier2_project_docs(str(tmp_path))
        assert len(entries) >= 1
        assert entries[0].tier == 2
        assert entries[0].source == "CLAUDE.md"

    def test_tier2_no_docs(self, tmp_path: Path) -> None:
        entries = km.tier2_project_docs(str(tmp_path))
        assert len(entries) == 0

    def test_tier3_external_hint(self) -> None:
        hint = km.tier3_external_hint("WebSearch")
        assert "[knowledge-manager]" in hint
        assert "WebSearch" in hint

    def test_build_knowledge_context_with_docs(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Project")
        ctx = km.build_knowledge_context("Read", "main.py", str(tmp_path))
        assert ctx is not None
        assert "[knowledge-manager]" in ctx

    def test_build_knowledge_context_no_match(self, tmp_path: Path) -> None:
        ctx = km.build_knowledge_context("SomeUnknownTool", "", str(tmp_path))
        assert ctx is None

    def test_knowledge_entry_dataclass(self) -> None:
        entry = km.KnowledgeEntry(tier=1, source="cache", content="test")
        assert entry.tier == 1
        assert entry.source == "cache"


# --- Compliance tracker tests ---

class TestComplianceTracker:
    """Test compliance tracking and audit logging."""

    def test_compliance_event_creation(self) -> None:
        event = ct.ComplianceEvent(
            timestamp=time.time(),
            session_id="test-001",
            tool_name="Write",
            hook_event="PostToolUse",
            decision="allow",
        )
        assert event.tool_name == "Write"
        assert event.decision == "allow"

    def test_compliance_stats_record(self) -> None:
        stats = ct.ComplianceStats()
        event = ct.ComplianceEvent(
            timestamp=time.time(),
            session_id="test",
            tool_name="Write",
            hook_event="PostToolUse",
            decision="allow",
        )
        stats.record(event)
        assert stats.total_events == 1
        assert stats.allow_count == 1
        assert stats.tool_counts["Write"] == 1

    def test_compliance_stats_block(self) -> None:
        stats = ct.ComplianceStats()
        event = ct.ComplianceEvent(
            timestamp=time.time(),
            session_id="test",
            tool_name="Bash",
            hook_event="PostToolUse",
            decision="block",
        )
        stats.record(event)
        assert stats.block_count == 1

    def test_compliance_score_perfect(self) -> None:
        stats = ct.ComplianceStats()
        for _ in range(5):
            stats.record(ct.ComplianceEvent(
                timestamp=time.time(),
                session_id="test",
                tool_name="Read",
                hook_event="PostToolUse",
                decision="allow",
            ))
        assert stats.compliance_score == 1.0

    def test_compliance_score_mixed(self) -> None:
        stats = ct.ComplianceStats()
        stats.record(ct.ComplianceEvent(
            timestamp=time.time(), session_id="t", tool_name="A",
            hook_event="PostToolUse", decision="allow",
        ))
        stats.record(ct.ComplianceEvent(
            timestamp=time.time(), session_id="t", tool_name="B",
            hook_event="PostToolUse", decision="block",
        ))
        assert stats.compliance_score == 0.5

    def test_compliance_score_empty(self) -> None:
        stats = ct.ComplianceStats()
        assert stats.compliance_score == 1.0

    def test_create_event_from_dict(self) -> None:
        data = {
            "session_id": "sess-001",
            "tool_name": "Write",
            "hook_event_name": "PostToolUse",
            "tool_input": {"file_path": "/tmp/test.py"},
            "tool_result": {"exit_code": 0},
        }
        event = ct.create_event(data)
        assert event.tool_name == "Write"
        assert event.session_id == "sess-001"
        assert event.file_path == "/tmp/test.py"

    def test_log_event_writes_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COMPLIANCE_LOG_DIR", str(tmp_path))
        event = ct.ComplianceEvent(
            timestamp=time.time(),
            session_id="test",
            tool_name="Read",
            hook_event="PostToolUse",
            decision="allow",
        )
        ct.log_event(event)
        log_file = tmp_path / "audit.jsonl"
        assert log_file.is_file()
        line = log_file.read_text().strip()
        data = json.loads(line)
        assert data["tool_name"] == "Read"


# --- File structure tests ---

class TestFileStructure:
    """Test all required files exist with minimum line counts."""

    @pytest.mark.parametrize(
        "hook_file",
        ["cila_router.py", "knowledge_manager.py", "compliance_tracker.py"],
    )
    def test_hook_files_exist(self, base_dir: Path, hook_file: str) -> None:
        path = base_dir / "modules" / "hooks-routing" / "hooks" / hook_file
        assert path.is_file()

    def test_cila_router_min_lines(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-routing" / "hooks" / "cila_router.py"
        lines = path.read_text().count("\n")
        assert lines >= 80, f"cila_router.py must have 80+ lines, has {lines}"

    def test_knowledge_manager_min_lines(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-routing" / "hooks" / "knowledge_manager.py"
        lines = path.read_text().count("\n")
        assert lines >= 60, f"knowledge_manager.py must have 60+ lines, has {lines}"

    def test_compliance_tracker_min_lines(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-routing" / "hooks" / "compliance_tracker.py"
        lines = path.read_text().count("\n")
        assert lines >= 50, f"compliance_tracker.py must have 50+ lines, has {lines}"

    @pytest.mark.parametrize(
        "hook_file",
        ["cila_router.py", "knowledge_manager.py", "compliance_tracker.py"],
    )
    def test_future_annotations(self, base_dir: Path, hook_file: str) -> None:
        path = base_dir / "modules" / "hooks-routing" / "hooks" / hook_file
        content = path.read_text()
        assert "from __future__ import annotations" in content
