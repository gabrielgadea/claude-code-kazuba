"""Tests for scripts.validate_installation — post-install health checks."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from claude_code_kazuba.installer.validate_installation import validate_installation

if TYPE_CHECKING:
    from pathlib import Path


class TestValidateDirectoryStructure:
    """Verify .claude/ directory checks."""

    def test_missing_claude_dir(self, tmp_path: Path) -> None:
        result = validate_installation(tmp_path)
        assert result["directory_structure"] is False

    def test_claude_dir_exists(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        result = validate_installation(tmp_path)
        assert result["directory_structure"] is True


class TestValidateSettingsJson:
    """Verify settings.json validation."""

    def test_valid_settings(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings = {
            "$schema": "https://json.schemastore.org/claude-code-settings.json",
            "permissions": {},
            "hooks": {},
        }
        (claude_dir / "settings.json").write_text(json.dumps(settings))
        result = validate_installation(tmp_path)
        assert result["settings_json"] is True

    def test_missing_settings(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        result = validate_installation(tmp_path)
        assert result["settings_json"] is False

    def test_invalid_json(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("not json {{{")
        result = validate_installation(tmp_path)
        assert result["settings_json"] is False

    def test_missing_schema(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text(json.dumps({"permissions": {}}))
        result = validate_installation(tmp_path)
        assert result["settings_json"] is False


class TestValidateHookScripts:
    """Verify hook script checks."""

    def test_no_hooks_dir_passes(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        result = validate_installation(tmp_path)
        assert result["hook_scripts"] is True

    def test_hooks_present(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        hooks_dir = claude_dir / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "test.py").write_text("# hook")

        settings = {
            "$schema": "https://json.schemastore.org/claude-code-settings.json",
            "hooks": {"PreToolUse": [{"type": "command", "command": "python hooks/test.py"}]},
        }
        (claude_dir / "settings.json").write_text(json.dumps(settings))

        result = validate_installation(tmp_path)
        assert result["hook_scripts"] is True

    def test_missing_hook_script(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "hooks").mkdir()

        settings = {
            "$schema": "https://json.schemastore.org/claude-code-settings.json",
            "hooks": {"PreToolUse": [{"type": "command", "command": "python hooks/missing.py"}]},
        }
        (claude_dir / "settings.json").write_text(json.dumps(settings))

        result = validate_installation(tmp_path)
        assert result["hook_scripts"] is False


class TestValidateSkillFiles:
    """Verify SKILL.md validation."""

    def test_no_skills_dir_passes(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        result = validate_installation(tmp_path)
        assert result["skill_files"] is True

    def test_valid_skill_md(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        skills_dir = claude_dir / "skills" / "test-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("---\nname: test\n---\n# Test\n")

        result = validate_installation(tmp_path)
        assert result["skill_files"] is True

    def test_invalid_skill_md(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        skills_dir = claude_dir / "skills" / "bad-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("# No frontmatter here\n")

        result = validate_installation(tmp_path)
        assert result["skill_files"] is False


class TestValidateClaudeMd:
    """Verify CLAUDE.md checks."""

    def test_claude_md_present(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(
            "# Project\n\nThis is a valid CLAUDE.md file with enough content.\n"
        )
        result = validate_installation(tmp_path)
        assert result["claude_md"] is True

    def test_claude_md_missing(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        result = validate_installation(tmp_path)
        assert result["claude_md"] is False

    def test_claude_md_too_short(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text("# X\n")
        result = validate_installation(tmp_path)
        assert result["claude_md"] is False


class TestValidateOverall:
    """Overall validation result."""

    def test_all_passed_true(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text(
            json.dumps({"$schema": "https://example.com/s.json"})
        )
        (claude_dir / "CLAUDE.md").write_text(
            "# Project\n\nFull CLAUDE.md content with enough text to pass the check.\n"
        )
        result = validate_installation(tmp_path)
        assert result["all_passed"] is True

    def test_all_passed_false_when_any_fails(self, tmp_path: Path) -> None:
        # No .claude/ dir
        result = validate_installation(tmp_path)
        assert result["all_passed"] is False

    def test_messages_present(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        result = validate_installation(tmp_path)
        assert "_messages" in result
        assert isinstance(result["_messages"], list)
        assert len(result["_messages"]) > 0
