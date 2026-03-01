#!/usr/bin/env python3
"""Validate Hooks Health — SessionStart hook to verify hook registry integrity.

Event: SessionStart
Purpose: At session start, scan the registered hooks from settings.json and
         verify each hook file exists, is executable, and has a valid shebang.
         Reports issues but never blocks the session (fail-open).

Exit codes:
  0 - Allow (always — hooks must be fail-open)

Protocol: stdin JSON -> validate hooks -> stderr report -> exit 0
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class HookStatus(BaseModel, frozen=True):
    """Status of a single registered hook.

    Args:
        name: Hook name or command basename.
        event: The Claude Code event this hook listens to.
        healthy: Whether the hook is considered healthy.
        error_count: Number of issues detected for this hook.
        last_error: Description of the last error found (empty if healthy).
    """

    name: str
    event: str
    healthy: bool
    error_count: int = 0
    last_error: str = ""


class HealthReport(BaseModel, frozen=True):
    """Aggregate health report for all registered hooks.

    Args:
        total: Total number of hooks inspected.
        healthy: Number of hooks without issues.
        degraded: Number of hooks with warnings.
        failed: Number of hooks with critical issues.
        hooks: Detailed status for each hook.
    """

    total: int
    healthy: int
    degraded: int
    failed: int
    hooks: list[HookStatus] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# HooksHealthValidator
# ---------------------------------------------------------------------------


class HooksHealthValidator:
    """Validates health of hooks registered in a Claude Code settings.json.

    Checks each hook's command for:
    - File existence
    - Execute permission
    - Valid Python shebang (no uv run)
    """

    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = settings_path

    def validate_all(self) -> HealthReport:
        """Validate all hooks found in the settings file.

        Returns:
            HealthReport with aggregate counts and per-hook status.
        """
        if self.settings_path is None or not self.settings_path.exists():
            return HealthReport(total=0, healthy=0, degraded=0, failed=0, hooks=[])

        try:
            hook_defs = self._parse_settings(self.settings_path)
        except Exception as exc:
            return HealthReport(
                total=0,
                healthy=0,
                degraded=0,
                failed=1,
                hooks=[
                    HookStatus(
                        name="settings.json",
                        event="unknown",
                        healthy=False,
                        error_count=1,
                        last_error=f"Failed to parse settings: {exc}",
                    )
                ],
            )

        statuses: list[HookStatus] = []
        for hook_def in hook_defs:
            status = self._check_hook(hook_def)
            statuses.append(status)

        total = len(statuses)
        healthy = sum(1 for s in statuses if s.healthy and s.error_count == 0)
        degraded = sum(1 for s in statuses if s.healthy and s.error_count > 0)
        failed = sum(1 for s in statuses if not s.healthy)

        return HealthReport(
            total=total,
            healthy=healthy,
            degraded=degraded,
            failed=failed,
            hooks=statuses,
        )

    def _check_hook(self, hook_def: dict[str, Any]) -> HookStatus:
        """Check a single hook definition for health issues.

        Args:
            hook_def: Dict with 'command' and 'event' keys.

        Returns:
            HookStatus for this hook.
        """
        command = hook_def.get("command", "")
        event = hook_def.get("event", "unknown")
        name = Path(command.split()[-1]).name if command.split() else command

        errors: list[str] = []

        py_path = self._extract_python_file(command)
        if py_path is not None:
            if not self._check_hook_file(command):
                errors.append(f"File not found or not executable: {py_path}")
            else:
                # Check for incompatible shebang
                try:
                    path = Path(py_path)
                    first_line = path.read_text(encoding="utf-8").splitlines()[0]
                    if "uv run" in first_line:
                        errors.append(f"Incompatible shebang (uv run): {py_path}")
                except (OSError, IndexError):
                    pass

        return HookStatus(
            name=name,
            event=event,
            healthy=len(errors) == 0,
            error_count=len(errors),
            last_error=errors[-1] if errors else "",
        )

    def _check_hook_file(self, command: str) -> bool:
        """Check if the Python file referenced in a hook command is valid.

        Looks for a .py file reference in the command string and verifies
        it exists and is executable.

        Args:
            command: Full hook command string.

        Returns:
            True if the file exists and is executable, False otherwise.
        """
        py_path = self._extract_python_file(command)
        if py_path is None:
            # Not a Python-based command — assume OK
            return True

        path = Path(py_path)
        if not path.exists():
            return False
        return os.access(path, os.X_OK)

    def _extract_python_file(self, command: str) -> str | None:
        """Extract the .py file path from a hook command string.

        Args:
            command: Hook command string.

        Returns:
            The .py file path string, or None if not found.
        """
        if "python" not in command and ".py" not in command:
            return None

        parts = command.split()
        for part in parts:
            if part.endswith(".py"):
                return part

        return None

    def _parse_settings(self, path: Path) -> list[dict[str, Any]]:
        """Parse a Claude Code settings.json and extract hook definitions.

        Args:
            path: Path to settings.json file.

        Returns:
            List of hook definition dicts with 'command' and 'event'.
        """
        content = path.read_text(encoding="utf-8")
        settings: dict[str, Any] = json.loads(content)

        hook_defs: list[dict[str, Any]] = []
        hooks_section = settings.get("hooks", {})

        if isinstance(hooks_section, dict):
            for event_name, event_configs in hooks_section.items():
                if not isinstance(event_configs, list):
                    continue
                for config in event_configs:
                    if not isinstance(config, dict):
                        continue
                    inner_hooks = config.get("hooks", [])
                    if not isinstance(inner_hooks, list):
                        continue
                    for hook in inner_hooks:
                        if not isinstance(hook, dict):
                            continue
                        command = hook.get("command", "")
                        if command:
                            hook_defs.append({"command": command, "event": event_name})

        return hook_defs


# ---------------------------------------------------------------------------
# Hook entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """SessionStart hook entry point.

    Loads settings.json from the Claude project directory, validates all
    registered hooks, and reports results to stderr. Always exits 0.
    """
    try:
        # Read stdin (may be empty or hook event JSON)
        raw = sys.stdin.read().strip()
        hook_data: dict[str, Any] = {}
        if raw:
            with contextlib.suppress(json.JSONDecodeError):
                hook_data = json.loads(raw)

        # Determine settings path
        project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", str(Path.cwd())))

        # Try both settings files
        candidates = [
            project_dir / ".claude" / "settings.local.json",
            project_dir / ".claude" / "settings.json",
        ]
        settings_path: Path | None = None
        for candidate in candidates:
            if candidate.exists():
                settings_path = candidate
                break

        validator = HooksHealthValidator(settings_path=settings_path)
        report = validator.validate_all()

        if report.total == 0:
            print(
                "HooksHealthValidator: No hooks found to validate.",
                file=sys.stderr,
            )
        elif report.failed > 0:
            print(
                f"HooksHealthValidator: {report.failed}/{report.total} hooks have issues.",
                file=sys.stderr,
            )
            for hook in report.hooks:
                if not hook.healthy:
                    print(
                        f"  [ISSUE] {hook.event}/{hook.name}: {hook.last_error}", file=sys.stderr
                    )
        else:
            print(
                f"HooksHealthValidator: {report.healthy}/{report.total} hooks healthy.",
                file=sys.stderr,
            )

        _ = hook_data  # hook_data consumed but not needed for this hook

    except Exception as exc:
        # Fail-open: never block session start
        print(
            f"validate_hooks_health hook error (non-blocking): {exc}",
            file=sys.stderr,
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
