"""Tests for scripts.merge_settings — deep merge algorithm."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from scripts.merge_settings import merge_settings, merge_settings_file

if TYPE_CHECKING:
    from pathlib import Path


class TestMergePermissions:
    """Permission array merging."""

    def test_extend_allow(self) -> None:
        base: dict[str, Any] = {"permissions": {"allow": ["Read"], "deny": []}}
        overlay: dict[str, Any] = {"permissions": {"allow": ["Write", "Edit"]}}
        result = merge_settings(base, overlay)
        assert set(result["permissions"]["allow"]) == {"Read", "Write", "Edit"}

    def test_extend_deny(self) -> None:
        base: dict[str, Any] = {"permissions": {"deny": ["Bash(rm -rf /)"]}}
        overlay: dict[str, Any] = {"permissions": {"deny": ["Bash(chmod 777)"]}}
        result = merge_settings(base, overlay)
        assert "Bash(rm -rf /)" in result["permissions"]["deny"]
        assert "Bash(chmod 777)" in result["permissions"]["deny"]

    def test_no_duplicates(self) -> None:
        base: dict[str, Any] = {"permissions": {"allow": ["Read", "Write"]}}
        overlay: dict[str, Any] = {"permissions": {"allow": ["Write", "Edit"]}}
        result = merge_settings(base, overlay)
        assert result["permissions"]["allow"].count("Write") == 1

    def test_preserve_existing(self) -> None:
        base: dict[str, Any] = {"permissions": {"allow": ["Read"]}}
        overlay: dict[str, Any] = {"permissions": {"allow": ["Write"]}}
        result = merge_settings(base, overlay)
        assert result["permissions"]["allow"][0] == "Read"


class TestMergeHooks:
    """Hook configuration merging."""

    def test_merge_new_event(self) -> None:
        base: dict[str, Any] = {
            "hooks": {"PreToolUse": [{"type": "command", "command": "hook1.py"}]}
        }
        overlay: dict[str, Any] = {
            "hooks": {"PostToolUse": [{"type": "command", "command": "hook2.py"}]}
        }
        result = merge_settings(base, overlay)
        assert "PreToolUse" in result["hooks"]
        assert "PostToolUse" in result["hooks"]

    def test_append_to_existing_event(self) -> None:
        base: dict[str, Any] = {
            "hooks": {"PreToolUse": [{"type": "command", "command": "hook1.py"}]}
        }
        overlay: dict[str, Any] = {
            "hooks": {"PreToolUse": [{"type": "command", "command": "hook2.py"}]}
        }
        result = merge_settings(base, overlay)
        commands = [h["command"] for h in result["hooks"]["PreToolUse"]]
        assert "hook1.py" in commands
        assert "hook2.py" in commands

    def test_no_duplicate_hooks(self) -> None:
        hook = {"type": "command", "command": "hook.py"}
        base: dict[str, Any] = {"hooks": {"PreToolUse": [hook]}}
        overlay: dict[str, Any] = {"hooks": {"PreToolUse": [hook]}}
        result = merge_settings(base, overlay)
        assert len(result["hooks"]["PreToolUse"]) == 1

    def test_preserve_hook_order(self) -> None:
        base: dict[str, Any] = {
            "hooks": {
                "PreToolUse": [
                    {"type": "command", "command": "first.py"},
                    {"type": "command", "command": "second.py"},
                ]
            }
        }
        overlay: dict[str, Any] = {
            "hooks": {"PreToolUse": [{"type": "command", "command": "third.py"}]}
        }
        result = merge_settings(base, overlay)
        commands = [h["command"] for h in result["hooks"]["PreToolUse"]]
        assert commands == ["first.py", "second.py", "third.py"]


class TestMergeEnv:
    """Environment variable merging."""

    def test_add_new_key(self) -> None:
        base: dict[str, Any] = {"env": {"KEY1": "val1"}}
        overlay: dict[str, Any] = {"env": {"KEY2": "val2"}}
        result = merge_settings(base, overlay)
        assert result["env"]["KEY1"] == "val1"
        assert result["env"]["KEY2"] == "val2"

    def test_preserve_existing_value(self) -> None:
        base: dict[str, Any] = {"env": {"KEY": "original"}}
        overlay: dict[str, Any] = {"env": {"KEY": "override"}}
        result = merge_settings(base, overlay)
        assert result["env"]["KEY"] == "original"


class TestMergeSchema:
    """$schema field handling."""

    def test_preserve_base_schema(self) -> None:
        base: dict[str, Any] = {"$schema": "https://example.com/base.json"}
        overlay: dict[str, Any] = {"$schema": "https://example.com/overlay.json"}
        result = merge_settings(base, overlay)
        assert result["$schema"] == "https://example.com/base.json"

    def test_add_schema_from_overlay(self) -> None:
        base: dict[str, Any] = {}
        overlay: dict[str, Any] = {"$schema": "https://example.com/schema.json"}
        result = merge_settings(base, overlay)
        assert result["$schema"] == "https://example.com/schema.json"


class TestMergeComplete:
    """Full merge scenarios."""

    def test_empty_base(self) -> None:
        overlay: dict[str, Any] = {
            "$schema": "https://example.com/schema.json",
            "permissions": {"allow": ["Read"]},
            "hooks": {"PreToolUse": [{"type": "command", "command": "hook.py"}]},
            "env": {"KEY": "val"},
        }
        result = merge_settings({}, overlay)
        assert result["$schema"] == "https://example.com/schema.json"
        assert result["permissions"]["allow"] == ["Read"]
        assert len(result["hooks"]["PreToolUse"]) == 1
        assert result["env"]["KEY"] == "val"

    def test_empty_overlay(self) -> None:
        base: dict[str, Any] = {
            "$schema": "https://example.com/schema.json",
            "permissions": {"allow": ["Read"]},
        }
        result = merge_settings(base, {})
        assert result == base

    def test_no_mutation_of_inputs(self) -> None:
        base: dict[str, Any] = {"permissions": {"allow": ["Read"]}}
        overlay: dict[str, Any] = {"permissions": {"allow": ["Write"]}}
        base_copy = json.loads(json.dumps(base))
        overlay_copy = json.loads(json.dumps(overlay))
        merge_settings(base, overlay)
        assert base == base_copy
        assert overlay == overlay_copy

    def test_extra_top_level_keys(self) -> None:
        base: dict[str, Any] = {"custom": "value"}
        overlay: dict[str, Any] = {"extra": "new"}
        result = merge_settings(base, overlay)
        assert result["custom"] == "value"
        assert result["extra"] == "new"


class TestMergeSettingsFile:
    """File-based merge."""

    def test_merge_files(self, tmp_path: Path) -> None:
        base_file = tmp_path / "base.json"
        overlay_file = tmp_path / "overlay.json"

        base_file.write_text(json.dumps({"permissions": {"allow": ["Read"]}}))
        overlay_file.write_text(json.dumps({"permissions": {"allow": ["Write"]}}))

        result = merge_settings_file(base_file, overlay_file)
        assert "Read" in result["permissions"]["allow"]
        assert "Write" in result["permissions"]["allow"]

    def test_base_file_missing(self, tmp_path: Path) -> None:
        base_file = tmp_path / "missing.json"
        overlay_file = tmp_path / "overlay.json"
        overlay_file.write_text(json.dumps({"env": {"KEY": "val"}}))

        result = merge_settings_file(base_file, overlay_file)
        assert result["env"]["KEY"] == "val"

    def test_overlay_file_missing(self, tmp_path: Path) -> None:
        overlay_file = tmp_path / "missing.json"
        with pytest.raises(FileNotFoundError):
            merge_settings_file(tmp_path / "base.json", overlay_file)
