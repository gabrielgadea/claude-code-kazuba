"""Shared fixtures for integration tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from claude_code_kazuba.installer.install_module import install_module
from claude_code_kazuba.installer.resolve_deps import resolve_dependencies


@pytest.fixture
def installer_source() -> Path:
    """Return the project root directory (source of modules)."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def install_preset(
    installer_source: Path,
    tmp_path: Path,
) -> Any:
    """Factory fixture: install a preset to a temp directory.

    Returns a callable that accepts a preset name and returns the
    target directory with the installation.
    """

    def _install(preset_name: str) -> Path:
        target = tmp_path / f"project-{preset_name}"
        target.mkdir(parents=True, exist_ok=True)

        # Read preset file
        preset_file = (
            installer_source / "claude_code_kazuba" / "data" / "presets" / f"{preset_name}.txt"
        )
        assert preset_file.exists(), f"Preset file not found: {preset_file}"

        module_names: list[str] = []
        for line in preset_file.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                module_names.append(stripped)

        # Resolve dependencies
        modules_dir = installer_source / "claude_code_kazuba/data/modules"
        core_dir = installer_source / "claude_code_kazuba" / "data" / "core"
        ordered = resolve_dependencies(module_names, modules_dir, core_dir=core_dir)

        # Install each module in order
        variables: dict[str, Any] = {
            "project_name": f"test-{preset_name}",
            "stack": "Python 3.12 (test)",
            "language": "python",
            "version": "3.12",
        }

        data_dir = installer_source / "claude_code_kazuba" / "data"
        for module_name in ordered:
            install_module(module_name, data_dir, target, variables)

        return target

    return _install
