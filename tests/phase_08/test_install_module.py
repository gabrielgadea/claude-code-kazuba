"""Tests for scripts.install_module — single module installation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from claude_code_kazuba.installer.install_module import install_module

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def source_dir(base_dir: Path) -> Path:
    """Return the project source directory (contains core/ and modules/)."""
    return base_dir


@pytest.fixture
def target_project(tmp_path: Path) -> Path:
    """Create a clean target project directory."""
    project = tmp_path / "target"
    project.mkdir()
    return project


class TestInstallCore:
    """Core module installation."""

    def test_install_creates_claude_dir(self, source_dir: Path, target_project: Path) -> None:
        install_module("core", source_dir, target_project, {"project_name": "Test"})
        assert (target_project / ".claude").is_dir()

    def test_install_renders_claude_md(self, source_dir: Path, target_project: Path) -> None:
        result = install_module(
            "core",
            source_dir,
            target_project,
            {"project_name": "My Project", "stack": "Python 3.12"},
        )
        claude_md = target_project / ".claude" / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "My Project" in content
        assert str(claude_md) in result["rendered"]

    def test_install_renders_settings_json(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("core", source_dir, target_project, {})
        settings = target_project / ".claude" / "settings.json"
        assert settings.exists()
        assert str(settings) in result["rendered"]

    def test_install_copies_rules(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("core", source_dir, target_project, {})
        rules_dir = target_project / ".claude" / "rules"
        assert rules_dir.is_dir()
        assert any("rules" in f for f in result["copied"])

    def test_install_returns_result_dict(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("core", source_dir, target_project, {})
        assert "copied" in result
        assert "merged" in result
        assert "rendered" in result
        assert isinstance(result["copied"], list)
        assert isinstance(result["merged"], list)
        assert isinstance(result["rendered"], list)


class TestInstallHooksModule:
    """Hooks module installation."""

    def test_install_hooks_essential(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("hooks-essential", source_dir, target_project, {})
        hooks_dir = target_project / ".claude" / "hooks"
        assert hooks_dir.is_dir()
        assert len(result["copied"]) > 0

    def test_hooks_files_copied(self, source_dir: Path, target_project: Path) -> None:
        install_module("hooks-essential", source_dir, target_project, {})
        hooks_dir = target_project / ".claude" / "hooks"
        # Should have prompt_enhancer.py, status_monitor.sh, auto_compact.sh
        assert (hooks_dir / "prompt_enhancer.py").exists()
        assert (hooks_dir / "status_monitor.sh").exists()
        assert (hooks_dir / "auto_compact.sh").exists()

    def test_settings_hooks_merged(self, source_dir: Path, target_project: Path) -> None:
        # First install core to create settings.json
        install_module("core", source_dir, target_project, {})
        # Then install hooks
        result = install_module("hooks-essential", source_dir, target_project, {})
        assert len(result["merged"]) > 0

        # Verify hooks are in settings.json
        settings = json.loads((target_project / ".claude" / "settings.json").read_text())
        assert "hooks" in settings

    def test_install_hooks_quality(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("hooks-quality", source_dir, target_project, {})
        hooks_dir = target_project / ".claude" / "hooks"
        assert (hooks_dir / "quality_gate.py").exists()
        assert (hooks_dir / "secrets_scanner.py").exists()
        assert len(result["merged"]) > 0


class TestInstallSkillsModule:
    """Skills module installation."""

    def test_install_skills_meta(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("skills-meta", source_dir, target_project, {})
        skills_dir = target_project / ".claude" / "skills"
        assert skills_dir.is_dir()
        assert len(result["copied"]) > 0

    def test_skill_md_files_present(self, source_dir: Path, target_project: Path) -> None:
        install_module("skills-meta", source_dir, target_project, {})
        skills_dir = target_project / ".claude" / "skills"
        skill_files = list(skills_dir.rglob("SKILL.md"))
        assert len(skill_files) > 0


class TestInstallModuleErrors:
    """Error handling."""

    def test_missing_module_raises(self, source_dir: Path, target_project: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            install_module("nonexistent-module", source_dir, target_project, {})

    def test_no_pyc_copied(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("hooks-essential", source_dir, target_project, {})
        for f in result["copied"]:
            assert not f.endswith(".pyc")
            assert "__pycache__" not in f


class TestInstallOtherModules:
    """Test other module types."""

    def test_install_agents(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("agents-dev", source_dir, target_project, {})
        agents_dir = target_project / ".claude" / "agents"
        assert agents_dir.is_dir()
        assert len(result["copied"]) > 0

    def test_install_commands(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("commands-dev", source_dir, target_project, {})
        commands_dir = target_project / ".claude" / "commands"
        assert commands_dir.is_dir()
        assert len(result["copied"]) > 0

    def test_install_contexts(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("contexts", source_dir, target_project, {})
        contexts_dir = target_project / ".claude" / "contexts"
        assert contexts_dir.is_dir()
        assert len(result["copied"]) > 0

    def test_install_config_hypervisor(self, source_dir: Path, target_project: Path) -> None:
        result = install_module("config-hypervisor", source_dir, target_project, {})
        config_dir = target_project / ".claude" / "config"
        assert config_dir.is_dir()
        assert len(result["copied"]) > 0
