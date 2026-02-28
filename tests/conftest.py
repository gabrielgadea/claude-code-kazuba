"""Shared test fixtures for claude-code-kazuba."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def base_dir() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with basic structure."""
    project = tmp_path / "test-project"
    project.mkdir()
    (project / ".claude").mkdir()
    return project


@pytest.fixture
def sample_hook_input() -> dict[str, Any]:
    """Return a sample PreToolUse hook input."""
    return {
        "session_id": "test-session-001",
        "cwd": "/tmp/test-project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "/tmp/test-project/src/main.py",
            "content": 'print("hello")\n',
        },
    }


@pytest.fixture
def sample_prompt_input() -> dict[str, Any]:
    """Return a sample UserPromptSubmit hook input."""
    return {
        "session_id": "test-session-001",
        "cwd": "/tmp/test-project",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Fix the authentication bug in the login handler",
    }


@pytest.fixture
def tmp_settings(tmp_project: Path) -> Path:
    """Create a temporary settings.json file."""
    settings: dict[str, Any] = {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "permissions": {"allow": [], "deny": []},
        "hooks": {},
        "env": {},
    }
    settings_path = tmp_project / ".claude" / "settings.json"
    settings_path.write_text(json.dumps(settings, indent=2))
    return settings_path


@pytest.fixture
def checkpoint_dir(tmp_path: Path) -> Path:
    """Create a temporary checkpoint directory."""
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()
    return cp_dir
