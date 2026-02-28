"""Integration tests for the research preset."""
from __future__ import annotations

from typing import Any

import pytest

from scripts.validate_installation import validate_installation


@pytest.mark.integration
class TestResearchPreset:
    """Install research preset and verify result."""

    def test_claude_dir_created(self, install_preset: Any) -> None:
        target = install_preset("research")
        assert (target / ".claude").is_dir()

    def test_research_skills_present(self, install_preset: Any) -> None:
        target = install_preset("research")
        skills_dir = target / ".claude" / "skills"
        assert skills_dir.is_dir()
        skill_files = list(skills_dir.rglob("SKILL.md"))
        # skills-meta (3) + skills-planning (3) + skills-research (2) = 8
        assert len(skill_files) >= 5

    def test_essential_hooks_present(self, install_preset: Any) -> None:
        target = install_preset("research")
        hooks_dir = target / ".claude" / "hooks"
        assert hooks_dir.is_dir()
        assert (hooks_dir / "prompt_enhancer.py").exists()

    def test_no_quality_hooks(self, install_preset: Any) -> None:
        """Research preset should NOT have quality hooks."""
        target = install_preset("research")
        hooks_dir = target / ".claude" / "hooks"
        assert not (hooks_dir / "quality_gate.py").exists()
        assert not (hooks_dir / "secrets_scanner.py").exists()
        assert not (hooks_dir / "bash_safety.py").exists()

    def test_no_routing_hooks(self, install_preset: Any) -> None:
        """Research preset should NOT have routing hooks."""
        target = install_preset("research")
        hooks_dir = target / ".claude" / "hooks"
        assert not (hooks_dir / "cila_router.py").exists()

    def test_no_agents(self, install_preset: Any) -> None:
        """Research preset should NOT have agents."""
        target = install_preset("research")
        assert not (target / ".claude" / "agents").exists()

    def test_contexts_present(self, install_preset: Any) -> None:
        target = install_preset("research")
        contexts_dir = target / ".claude" / "contexts"
        assert contexts_dir.is_dir()

    def test_claude_md_content(self, install_preset: Any) -> None:
        target = install_preset("research")
        content = (target / ".claude" / "CLAUDE.md").read_text()
        assert "test-research" in content
        assert len(content) > 100

    def test_validation_passes(self, install_preset: Any) -> None:
        target = install_preset("research")
        results = validate_installation(target)
        assert results["directory_structure"] is True
        assert results["claude_md"] is True
        assert results["skill_files"] is True
