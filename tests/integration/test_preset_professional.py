"""Integration tests for the professional preset."""
from __future__ import annotations

import json
from typing import Any

import pytest

from scripts.validate_installation import validate_installation


@pytest.mark.integration
class TestProfessionalPreset:
    """Install professional preset and verify result."""

    def test_all_hook_types_present(self, install_preset: Any) -> None:
        target = install_preset("professional")
        hooks_dir = target / ".claude" / "hooks"
        assert hooks_dir.is_dir()

        # Essential hooks
        assert (hooks_dir / "prompt_enhancer.py").exists()
        assert (hooks_dir / "status_monitor.sh").exists()

        # Quality hooks
        assert (hooks_dir / "quality_gate.py").exists()
        assert (hooks_dir / "secrets_scanner.py").exists()
        assert (hooks_dir / "pii_scanner.py").exists()
        assert (hooks_dir / "bash_safety.py").exists()

        # Routing hooks
        assert (hooks_dir / "cila_router.py").exists()
        assert (hooks_dir / "knowledge_manager.py").exists()
        assert (hooks_dir / "compliance_tracker.py").exists()

    def test_agents_present(self, install_preset: Any) -> None:
        target = install_preset("professional")
        agents_dir = target / ".claude" / "agents"
        assert agents_dir.is_dir()
        agent_files = list(agents_dir.glob("*.md"))
        assert len(agent_files) >= 1

    def test_commands_present(self, install_preset: Any) -> None:
        target = install_preset("professional")
        commands_dir = target / ".claude" / "commands"
        assert commands_dir.is_dir()
        command_files = list(commands_dir.glob("*.md"))
        assert len(command_files) >= 1

    def test_settings_hooks_merged(self, install_preset: Any) -> None:
        target = install_preset("professional")
        settings = json.loads((target / ".claude" / "settings.json").read_text())
        hooks = settings.get("hooks", {})

        # Should have hooks from essential, quality, and routing modules
        assert "UserPromptSubmit" in hooks
        assert "PreToolUse" in hooks

    def test_skills_present(self, install_preset: Any) -> None:
        target = install_preset("professional")
        skills_dir = target / ".claude" / "skills"
        assert skills_dir.is_dir()
        skill_files = list(skills_dir.rglob("SKILL.md"))
        # skills-meta (3) + skills-planning (3) + skills-dev (3) = 9
        assert len(skill_files) >= 6

    def test_contexts_present(self, install_preset: Any) -> None:
        target = install_preset("professional")
        contexts_dir = target / ".claude" / "contexts"
        assert contexts_dir.is_dir()

    def test_validation_passes(self, install_preset: Any) -> None:
        target = install_preset("professional")
        results = validate_installation(target)
        assert results["directory_structure"] is True
        assert results["claude_md"] is True
        assert results["skill_files"] is True
