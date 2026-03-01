#!/usr/bin/env python3
"""Self-hosting configuration — kazuba uses its own hooks.

This module defines the hook registrations that the claude-code-kazuba
project applies to itself, demonstrating the framework by being its own
first user (dogfooding / self-hosting).

Usage::

    from .claude.hooks.self_host_config import load_config, generate_settings_fragment

    config = load_config()
    fragment = generate_settings_fragment(config)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HookRegistration:
    """A single hook event registration."""

    event: str
    script: str
    timeout: int = 5000
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to settings.json hook entry format."""
        entry: dict[str, Any] = {
            "hooks": [{"type": "command", "command": self.script}],
        }
        if self.timeout != 5000:
            entry["timeout"] = self.timeout
        return entry


@dataclass(frozen=True)
class SelfHostConfig:
    """Immutable configuration for self-hosted hook registrations."""

    project_root: Path
    hooks: tuple[HookRegistration, ...]
    enabled: bool = True
    version: str = "0.2.0"

    @property
    def hooks_dir(self) -> Path:
        """Absolute path to the hooks directory."""
        return self.project_root / "modules"

    def get_hooks_for_event(self, event: str) -> list[HookRegistration]:
        """Return all hooks registered for a given event type."""
        return [h for h in self.hooks if h.event == event]


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def get_default_hooks(project_root: Path | None = None) -> list[HookRegistration]:
    """Return the default set of self-hosted hook registrations.

    Args:
        project_root: Path to the project root; defaults to cwd.

    Returns:
        List of HookRegistration objects for core hooks.
    """
    root = project_root or Path.cwd()
    hooks_base = root / "modules"

    return [
        HookRegistration(
            event="PreToolUse",
            script=f"python {hooks_base / 'hooks-routing' / 'hooks' / 'auto_permission_resolver.py'}",
            timeout=5000,
            description="Auto-approve safe operations",
        ),
        HookRegistration(
            event="PreToolUse",
            script=f"python {hooks_base / 'hooks-quality' / 'hooks' / 'siac_orchestrator.py'}",
            timeout=8000,
            description="SIAC quality gate",
        ),
        HookRegistration(
            event="PreToolUse",
            script=f"python {hooks_base / 'hooks-routing' / 'hooks' / 'ptc_advisor.py'}",
            timeout=3000,
            description="PTC program advisor",
        ),
    ]


def load_config(
    project_root: Path | None = None,
    config_path: Path | None = None,
) -> SelfHostConfig:
    """Load or construct the self-host configuration.

    Args:
        project_root: Path to the project root.
        config_path: Optional JSON config file to load overrides from.

    Returns:
        SelfHostConfig with the active hook registrations.
    """
    root = project_root or Path(__file__).resolve().parents[2]
    hooks = get_default_hooks(root)

    # Allow JSON override of hook list
    if config_path is not None and config_path.exists():
        try:
            data = json.loads(config_path.read_text())
            overrides = data.get("hooks", [])
            if overrides:
                hooks = [
                    HookRegistration(
                        event=h["event"],
                        script=h["script"],
                        timeout=h.get("timeout", 5000),
                        description=h.get("description", ""),
                    )
                    for h in overrides
                ]
        except (json.JSONDecodeError, KeyError):
            pass  # Fall back to defaults on malformed config

    return SelfHostConfig(
        project_root=root,
        hooks=tuple(hooks),
    )


def validate_config(config: SelfHostConfig) -> list[str]:
    """Validate a SelfHostConfig and return a list of error messages.

    Args:
        config: Configuration to validate.

    Returns:
        Empty list if valid; list of human-readable error strings otherwise.
    """
    errors: list[str] = []

    if not config.hooks:
        errors.append("No hooks registered — at least one hook is required")

    for reg in config.hooks:
        if not reg.event:
            errors.append(f"Hook '{reg.script}' has an empty event name")
        if not reg.script:
            errors.append(f"Hook for event '{reg.event}' has an empty script")
        if reg.timeout < 0:
            errors.append(
                f"Hook '{reg.script}' has negative timeout: {reg.timeout}"
            )
        valid_events = {
            "PreToolUse",
            "PostToolUse",
            "UserPromptSubmit",
            "Notification",
            "Stop",
        }
        if reg.event not in valid_events:
            errors.append(
                f"Hook '{reg.script}' has unknown event '{reg.event}'. "
                f"Valid events: {', '.join(sorted(valid_events))}"
            )

    return errors


def generate_settings_fragment(config: SelfHostConfig) -> dict[str, Any]:
    """Generate the `hooks` section fragment for settings.json.

    Args:
        config: Active self-host configuration.

    Returns:
        Dict suitable for merging into settings.json["hooks"].
    """
    fragment: dict[str, list[dict[str, Any]]] = {}

    for reg in config.hooks:
        entry = {"type": "command", "command": reg.script}
        if reg.timeout != 5000:
            entry["timeout"] = str(reg.timeout)
        fragment.setdefault(reg.event, []).append(entry)

    return {"hooks": fragment}


def main() -> None:
    """Print the generated settings fragment to stdout."""
    config = load_config()
    errors = validate_config(config)

    if errors:
        for err in errors:
            print(f"[ERROR] {err}")
        import sys
        sys.exit(1)

    fragment = generate_settings_fragment(config)
    print(json.dumps(fragment, indent=2))


if __name__ == "__main__":
    main()
