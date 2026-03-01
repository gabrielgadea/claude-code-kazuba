"""Tests for lib.config — Pydantic v2 configuration models."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from claude_code_kazuba.config import (
    HookRegistration,
    InstallerConfig,
    ModuleManifest,
    PresetConfig,
    ProjectSettings,
)


class TestModuleManifest:
    """ModuleManifest model validation."""

    def test_valid_manifest(self) -> None:
        m = ModuleManifest(
            name="security",
            version="1.0.0",
            description="Security hooks",
            dependencies=[],
            files=["hooks/pre_tool_use.py"],
        )
        assert m.name == "security"
        assert m.hooks_file is None

    def test_with_hooks_file(self) -> None:
        m = ModuleManifest(
            name="test",
            version="0.1.0",
            description="Test",
            dependencies=["core"],
            hooks_file="settings.hooks.json",
            files=[],
        )
        assert m.hooks_file == "settings.hooks.json"

    def test_invalid_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            ModuleManifest(name="x")  # type: ignore[call-arg]


class TestHookRegistration:
    """HookRegistration model."""

    def test_defaults(self) -> None:
        h = HookRegistration(event="PreToolUse", command="python hook.py")
        assert h.timeout == 10
        assert h.matcher is None

    def test_with_matcher(self) -> None:
        h = HookRegistration(
            event="PreToolUse",
            matcher="Bash",
            command="python bash_guard.py",
            timeout=5,
        )
        assert h.matcher == "Bash"
        assert h.timeout == 5


class TestPresetConfig:
    """PresetConfig model."""

    def test_valid_preset(self) -> None:
        p = PresetConfig(
            name="full-stack",
            description="Full stack preset",
            modules=["security", "quality", "productivity"],
        )
        assert len(p.modules) == 3


class TestProjectSettings:
    """ProjectSettings model with alias."""

    def test_valid_settings(self) -> None:
        s = ProjectSettings(
            **{
                "$schema": "https://json.schemastore.org/claude-code-settings.json",
                "permissions": {"allow": ["Bash"], "deny": []},
                "hooks": {},
                "env": {},
            }
        )
        assert s.schema_ == "https://json.schemastore.org/claude-code-settings.json"

    def test_serialization_uses_alias(self) -> None:
        s = ProjectSettings(
            **{
                "$schema": "https://example.com/schema.json",
                "permissions": {},
                "hooks": {},
                "env": {},
            }
        )
        dumped = s.model_dump(by_alias=True)
        assert "$schema" in dumped


class TestInstallerConfig:
    """InstallerConfig model."""

    def test_defaults(self) -> None:
        ic = InstallerConfig(target_dir=Path("/tmp/project"), modules=["security"])
        assert ic.dry_run is False
        assert ic.preset is None
        assert ic.stack is None

    def test_with_preset(self) -> None:
        ic = InstallerConfig(
            target_dir=Path("/tmp/project"),
            preset="full-stack",
            modules=[],
        )
        assert ic.preset == "full-stack"

    def test_invalid_target_dir_type(self) -> None:
        # Path should coerce from string
        ic = InstallerConfig(target_dir="/tmp/project", modules=[])  # type: ignore[arg-type]
        assert isinstance(ic.target_dir, Path)


class TestDependencyResolution:
    """Dependency resolution validation."""

    def test_resolve_valid_deps(self) -> None:
        from claude_code_kazuba.config import resolve_dependencies

        manifests = {
            "core": ModuleManifest(
                name="core", version="1.0", description="Core", dependencies=[], files=[]
            ),
            "security": ModuleManifest(
                name="security",
                version="1.0",
                description="Security",
                dependencies=["core"],
                files=[],
            ),
        }
        order = resolve_dependencies(["security"], manifests)
        assert order.index("core") < order.index("security")

    def test_missing_dependency_raises(self) -> None:
        from claude_code_kazuba.config import resolve_dependencies

        manifests = {
            "security": ModuleManifest(
                name="security",
                version="1.0",
                description="Sec",
                dependencies=["nonexistent"],
                files=[],
            ),
        }
        with pytest.raises(ValueError, match="nonexistent"):
            resolve_dependencies(["security"], manifests)
