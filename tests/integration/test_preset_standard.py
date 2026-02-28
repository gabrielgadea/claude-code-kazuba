"""Integration tests for the standard preset."""

from __future__ import annotations

import json
from typing import Any

import pytest

from scripts.validate_installation import validate_installation


@pytest.mark.integration
class TestStandardPreset:
    """Install standard preset and verify result."""

    def test_claude_dir_created(self, install_preset: Any) -> None:
        target = install_preset("standard")
        assert (target / ".claude").is_dir()

    def test_essential_hooks_present(self, install_preset: Any) -> None:
        target = install_preset("standard")
        hooks_dir = target / ".claude" / "hooks"
        assert hooks_dir.is_dir()
        assert (hooks_dir / "prompt_enhancer.py").exists()
        assert (hooks_dir / "status_monitor.sh").exists()
        assert (hooks_dir / "auto_compact.sh").exists()

    def test_skills_directories_created(self, install_preset: Any) -> None:
        target = install_preset("standard")
        skills_dir = target / ".claude" / "skills"
        assert skills_dir.is_dir()
        # skills-meta provides skill-master, skill-writer, hook-master
        skill_files = list(skills_dir.rglob("SKILL.md"))
        assert len(skill_files) >= 3

    def test_contexts_present(self, install_preset: Any) -> None:
        target = install_preset("standard")
        contexts_dir = target / ".claude" / "contexts"
        assert contexts_dir.is_dir()
        context_files = list(contexts_dir.glob("*.md"))
        assert len(context_files) >= 1

    def test_settings_json_has_hooks(self, install_preset: Any) -> None:
        target = install_preset("standard")
        settings = json.loads((target / ".claude" / "settings.json").read_text())
        assert "hooks" in settings
        # hooks-essential registers UserPromptSubmit, SessionStart, PreCompact
        hooks = settings["hooks"]
        assert any(event in hooks for event in ("UserPromptSubmit", "SessionStart", "PreCompact"))

    def test_no_quality_hooks(self, install_preset: Any) -> None:
        """Standard preset should NOT have quality hooks."""
        target = install_preset("standard")
        hooks_dir = target / ".claude" / "hooks"
        assert not (hooks_dir / "quality_gate.py").exists()
        assert not (hooks_dir / "secrets_scanner.py").exists()

    def test_claude_md_content(self, install_preset: Any) -> None:
        target = install_preset("standard")
        content = (target / ".claude" / "CLAUDE.md").read_text()
        assert "test-standard" in content

    def test_validation_passes(self, install_preset: Any) -> None:
        target = install_preset("standard")
        results = validate_installation(target)
        assert results["directory_structure"] is True
        assert results["claude_md"] is True
        assert results["skill_files"] is True
