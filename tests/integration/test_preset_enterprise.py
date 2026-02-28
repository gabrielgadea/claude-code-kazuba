"""Integration tests for the enterprise preset."""

from __future__ import annotations

import json
from typing import Any

import pytest

from scripts.validate_installation import validate_installation


@pytest.mark.integration
class TestEnterprisePreset:
    """Install enterprise preset and verify result."""

    def test_all_modules_installed(self, install_preset: Any) -> None:
        target = install_preset("enterprise")
        claude_dir = target / ".claude"
        assert claude_dir.is_dir()

        # Core artifacts
        assert (claude_dir / "CLAUDE.md").exists()
        assert (claude_dir / "settings.json").exists()
        assert (claude_dir / "rules").is_dir()

        # Hooks
        assert (claude_dir / "hooks").is_dir()

        # Skills
        assert (claude_dir / "skills").is_dir()

        # Agents
        assert (claude_dir / "agents").is_dir()

        # Commands
        assert (claude_dir / "commands").is_dir()

        # Contexts
        assert (claude_dir / "contexts").is_dir()

    def test_team_orchestrator_present(self, install_preset: Any) -> None:
        target = install_preset("enterprise")
        claude_dir = target / ".claude"

        # team-orchestrator provides config/, templates/, src/
        config_dir = claude_dir / "config"
        assert config_dir.is_dir()

        # Should have agents.yaml, routing_rules.yaml, sla.yaml from team-orchestrator
        # AND agent_triggers.yaml, event_mesh.yaml, hypervisor.yaml from config-hypervisor
        config_files = list(config_dir.glob("*.yaml"))
        assert len(config_files) >= 3

    def test_hypervisor_config_present(self, install_preset: Any) -> None:
        target = install_preset("enterprise")
        config_dir = target / ".claude" / "config"
        assert config_dir.is_dir()
        yaml_files = {f.name for f in config_dir.glob("*.yaml")}
        assert "hypervisor.yaml" in yaml_files

    def test_research_skills_present(self, install_preset: Any) -> None:
        target = install_preset("enterprise")
        skills_dir = target / ".claude" / "skills"
        skill_files = list(skills_dir.rglob("SKILL.md"))
        # Should have many skills from meta + planning + dev + research
        assert len(skill_files) >= 8

    def test_prp_commands_present(self, install_preset: Any) -> None:
        target = install_preset("enterprise")
        commands_dir = target / ".claude" / "commands"
        command_files = list(commands_dir.rglob("*.md"))
        # commands-dev + commands-prp
        assert len(command_files) >= 4

    def test_settings_json_has_all_hooks(self, install_preset: Any) -> None:
        target = install_preset("enterprise")
        settings = json.loads((target / ".claude" / "settings.json").read_text())
        hooks = settings.get("hooks", {})

        # Should have hooks from essential + quality + routing
        assert "UserPromptSubmit" in hooks
        assert "PreToolUse" in hooks
        assert "PostToolUse" in hooks

        # Should have multiple hooks per event
        pre_tool_hooks = hooks.get("PreToolUse", [])
        assert len(pre_tool_hooks) >= 3  # quality_gate, secrets, pii, bash + routing

    def test_template_files_present(self, install_preset: Any) -> None:
        target = install_preset("enterprise")
        templates_dir = target / ".claude" / "templates"
        assert templates_dir.is_dir()
        template_files = list(templates_dir.glob("*.md"))
        assert len(template_files) >= 1

    def test_validation_passes(self, install_preset: Any) -> None:
        target = install_preset("enterprise")
        results = validate_installation(target)
        assert results["directory_structure"] is True
        assert results["claude_md"] is True
        assert results["skill_files"] is True

    def test_settings_json_is_valid_json(self, install_preset: Any) -> None:
        target = install_preset("enterprise")
        settings_path = target / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text())
        assert isinstance(data, dict)
