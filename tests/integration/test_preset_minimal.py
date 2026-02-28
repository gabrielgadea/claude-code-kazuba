"""Integration tests for the minimal preset."""
from __future__ import annotations

import json
from typing import Any

import pytest

from scripts.validate_installation import validate_installation


@pytest.mark.integration
class TestMinimalPreset:
    """Install minimal preset and verify result."""

    def test_claude_dir_created(self, install_preset: Any) -> None:
        target = install_preset("minimal")
        assert (target / ".claude").is_dir()

    def test_claude_md_exists(self, install_preset: Any) -> None:
        target = install_preset("minimal")
        claude_md = target / ".claude" / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "test-minimal" in content

    def test_settings_json_valid(self, install_preset: Any) -> None:
        target = install_preset("minimal")
        settings_path = target / ".claude" / "settings.json"
        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        assert isinstance(data, dict)

    def test_gitignore_created(self, install_preset: Any) -> None:
        target = install_preset("minimal")
        gitignore = target / ".claude" / ".gitignore"
        assert gitignore.exists()

    def test_rules_copied(self, install_preset: Any) -> None:
        target = install_preset("minimal")
        rules_dir = target / ".claude" / "rules"
        assert rules_dir.is_dir()
        assert (rules_dir / "code-style.md").exists()
        assert (rules_dir / "security.md").exists()
        assert (rules_dir / "testing.md").exists()
        assert (rules_dir / "git-workflow.md").exists()

    def test_no_hooks_dir(self, install_preset: Any) -> None:
        target = install_preset("minimal")
        # Minimal preset has only core — no hooks directory
        hooks_dir = target / ".claude" / "hooks"
        assert not hooks_dir.exists()

    def test_no_skills_dir(self, install_preset: Any) -> None:
        target = install_preset("minimal")
        skills_dir = target / ".claude" / "skills"
        assert not skills_dir.exists()

    def test_validation_passes(self, install_preset: Any) -> None:
        target = install_preset("minimal")
        results = validate_installation(target)
        assert results["directory_structure"] is True
        assert results["claude_md"] is True
