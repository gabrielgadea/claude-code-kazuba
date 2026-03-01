"""Runtime data directory locator for claude-code-kazuba."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

_DATA_PKG = "claude_code_kazuba.data"


def get_data_dir() -> Path:
    """Return the absolute path to the kazuba data directory."""
    return Path(str(files(_DATA_PKG)))


def get_modules_dir() -> Path:
    """Return path to the modules directory."""
    return get_data_dir() / "modules"


def get_core_dir() -> Path:
    """Return path to the core templates directory."""
    return get_data_dir() / "core"


def get_presets_dir() -> Path:
    """Return path to the presets directory."""
    return get_data_dir() / "presets"
