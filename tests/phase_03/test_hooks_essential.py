"""Tests for hooks-essential module: prompt_enhancer, status_monitor, auto_compact."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

# --- Helper to import module from file path ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def _import_from_path(name: str, file_path: Path) -> ModuleType:
    """Import a Python module from an arbitrary file path."""
    # Ensure lib is on sys.path for the module's own imports
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


# Import the prompt_enhancer module
_pe_path = PROJECT_ROOT / "modules" / "hooks-essential" / "hooks" / "prompt_enhancer.py"
pe = _import_from_path("prompt_enhancer", _pe_path)


# --- Module manifest tests ---

class TestModuleManifest:
    """Test MODULE.md exists and has correct frontmatter."""

    def test_module_md_exists(self, base_dir: Path) -> None:
        module_md = base_dir / "modules" / "hooks-essential" / "MODULE.md"
        assert module_md.is_file(), "MODULE.md must exist"

    def test_module_md_has_frontmatter(self, base_dir: Path) -> None:
        module_md = base_dir / "modules" / "hooks-essential" / "MODULE.md"
        content = module_md.read_text()
        assert content.startswith("---"), "MODULE.md must start with YAML frontmatter"
        # Must have closing frontmatter
        parts = content.split("---", 2)
        assert len(parts) >= 3, "MODULE.md must have closing --- for frontmatter"

    def test_module_md_has_name(self, base_dir: Path) -> None:
        module_md = base_dir / "modules" / "hooks-essential" / "MODULE.md"
        content = module_md.read_text()
        assert "name: hooks-essential" in content

    def test_module_md_has_dependencies(self, base_dir: Path) -> None:
        module_md = base_dir / "modules" / "hooks-essential" / "MODULE.md"
        content = module_md.read_text()
        assert "core" in content, "Must depend on core"


# --- Settings JSON tests ---

class TestSettingsHooksJson:
    """Test settings.hooks.json is valid and complete."""

    def test_settings_json_exists(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "settings.hooks.json"
        assert path.is_file()

    def test_settings_json_is_valid(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "settings.hooks.json"
        data = json.loads(path.read_text())
        assert "hooks" in data
        assert isinstance(data["hooks"], dict)

    def test_settings_has_user_prompt_submit(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "settings.hooks.json"
        data = json.loads(path.read_text())
        assert "UserPromptSubmit" in data["hooks"]

    def test_settings_has_session_start(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "settings.hooks.json"
        data = json.loads(path.read_text())
        assert "SessionStart" in data["hooks"]

    def test_settings_has_pre_compact(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "settings.hooks.json"
        data = json.loads(path.read_text())
        assert "PreCompact" in data["hooks"]


# --- Shell script tests ---

class TestShellScripts:
    """Test shell scripts exist and are properly structured."""

    def test_status_monitor_exists(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "status_monitor.sh"
        assert path.is_file()

    def test_status_monitor_has_shebang(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "status_monitor.sh"
        content = path.read_text()
        assert content.startswith("#!/usr/bin/env bash")

    def test_status_monitor_has_set_euo(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "status_monitor.sh"
        content = path.read_text()
        assert "set -euo pipefail" in content

    def test_auto_compact_exists(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "auto_compact.sh"
        assert path.is_file()

    def test_auto_compact_has_shebang(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "auto_compact.sh"
        content = path.read_text()
        assert content.startswith("#!/usr/bin/env bash")

    def test_auto_compact_has_set_euo(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "auto_compact.sh"
        content = path.read_text()
        assert "set -euo pipefail" in content


# --- Prompt enhancer tests ---

class TestPromptEnhancerClassifier:
    """Test intent classification logic."""

    def test_classify_code_intent(self) -> None:
        result = pe.classify_intent("implement a new authentication module")
        assert result.intent == "code"
        assert result.confidence > 0.0

    def test_classify_debug_intent(self) -> None:
        result = pe.classify_intent("fix bug in the login handler, there's a traceback")
        assert result.intent == "debug"

    def test_classify_test_intent(self) -> None:
        result = pe.classify_intent("write unit test for the parser module with pytest")
        assert result.intent == "test"

    def test_classify_refactor_intent(self) -> None:
        result = pe.classify_intent("refactor the database connection to simplify it")
        assert result.intent == "refactor"

    def test_classify_plan_intent(self) -> None:
        result = pe.classify_intent("plan the architecture for the new microservice")
        assert result.intent == "plan"

    def test_classify_analysis_intent(self) -> None:
        result = pe.classify_intent("analyze how does the caching layer work")
        assert result.intent == "analysis"

    def test_classify_creative_intent(self) -> None:
        result = pe.classify_intent("brainstorm creative ideas for the UI")
        assert result.intent == "creative"

    def test_classify_general_fallback(self) -> None:
        result = pe.classify_intent("hello there")
        assert result.intent == "general"

    def test_classify_empty_prompt(self) -> None:
        result = pe.classify_intent("")
        assert result.intent == "general"
        assert result.confidence == 0.0

    def test_classify_portuguese_intent(self) -> None:
        result = pe.classify_intent("implementar um novo modulo de autenticacao")
        assert result.intent == "code"

    def test_classify_returns_scores(self) -> None:
        result = pe.classify_intent("implement a function")
        assert isinstance(result.scores, dict)
        assert len(result.scores) > 0

    def test_tiebreak_by_priority(self) -> None:
        """When two intents tie, higher priority (lower index) wins."""
        result = pe.classify_intent("build something")
        assert result.intent == "code"


class TestPromptEnhancerTechniques:
    """Test technique selection and composition."""

    def test_all_intents_covered(self) -> None:
        for intent in pe.INTENTS:
            techs = pe.select_techniques(intent)
            assert len(techs) >= 1, f"Intent {intent!r} must have at least 1 technique"

    def test_chain_of_thought_is_universal(self) -> None:
        """chain_of_thought should apply to all intents."""
        for intent in pe.INTENTS:
            techs = pe.select_techniques(intent)
            names = [t.name for t in techs]
            assert "chain_of_thought" in names, (
                f"chain_of_thought missing for {intent!r}"
            )

    def test_compose_context_format(self) -> None:
        techs = pe.select_techniques("code")
        ctx = pe.compose_context("code", techs)
        assert "[prompt-enhancer] Intent: code" in ctx
        assert "chain_of_thought" in ctx

    def test_compose_context_empty_techniques(self) -> None:
        ctx = pe.compose_context("general", [])
        assert "[prompt-enhancer] Intent: general" in ctx


# --- File structure tests ---

class TestFileStructure:
    """Test that all required files exist with minimum line counts."""

    def test_prompt_enhancer_exists(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "prompt_enhancer.py"
        assert path.is_file()

    def test_prompt_enhancer_min_lines(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "prompt_enhancer.py"
        lines = path.read_text().count("\n")
        assert lines >= 100, f"prompt_enhancer.py must have 100+ lines, has {lines}"

    def test_status_monitor_min_lines(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "status_monitor.sh"
        lines = path.read_text().count("\n")
        assert lines >= 40, f"status_monitor.sh must have 40+ lines, has {lines}"

    def test_auto_compact_min_lines(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "auto_compact.sh"
        lines = path.read_text().count("\n")
        assert lines >= 30, f"auto_compact.sh must have 30+ lines, has {lines}"

    def test_prompt_enhancer_has_future_annotations(self, base_dir: Path) -> None:
        path = base_dir / "modules" / "hooks-essential" / "hooks" / "prompt_enhancer.py"
        content = path.read_text()
        assert "from __future__ import annotations" in content
