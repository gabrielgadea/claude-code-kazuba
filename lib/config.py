"""Pydantic v2 configuration models for claude-code-kazuba."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 — Pydantic needs this at runtime
from typing import Any

from pydantic import BaseModel, Field


class ModuleManifest(BaseModel):
    """Manifest for a kazuba module."""

    name: str
    version: str
    description: str
    dependencies: list[str]
    hooks_file: str | None = None
    files: list[str]


class HookRegistration(BaseModel):
    """Registration entry for a hook in settings.json."""

    event: str
    matcher: str | None = None
    command: str
    timeout: int = 10


class PresetConfig(BaseModel):
    """A preset that bundles multiple modules together."""

    name: str
    description: str
    modules: list[str]


class ProjectSettings(BaseModel):
    """Claude Code settings.json model."""

    schema_: str | None = Field(default=None, alias="$schema")
    permissions: dict[str, Any] = Field(default_factory=dict)
    hooks: dict[str, Any] = Field(default_factory=dict)
    env: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class InstallerConfig(BaseModel):
    """Configuration for the module installer."""

    target_dir: Path
    preset: str | None = None
    modules: list[str] = Field(default_factory=list)
    dry_run: bool = False
    stack: str | None = None


def resolve_dependencies(
    requested: list[str],
    manifests: dict[str, ModuleManifest],
) -> list[str]:
    """Resolve module dependencies in topological order.

    Args:
        requested: List of module names to install.
        manifests: Map of module name to its manifest.

    Returns:
        Ordered list of module names (dependencies first).

    Raises:
        ValueError: If a required dependency is not found in manifests.
    """
    resolved: list[str] = []
    visited: set[str] = set()

    def _visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        manifest = manifests.get(name)
        if manifest is None:
            msg = f"Module not found: {name}"
            raise ValueError(msg)
        for dep in manifest.dependencies:
            if dep not in manifests:
                msg = f"Dependency not found: {dep} (required by {name})"
                raise ValueError(msg)
            _visit(dep)
        resolved.append(name)

    for module in requested:
        _visit(module)

    return resolved
