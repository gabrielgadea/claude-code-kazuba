#!/usr/bin/env python3
"""Auto Permission Resolver — PreToolUse hook for auto-approving safe operations.

Event: PreToolUse (all tools)
Purpose: Auto-approve known-safe operations to reduce user interruption.
         Blocks or denies only on clearly dangerous patterns.

Exit codes:
    0 - Allow (auto-approved or safe operation)
    1 - Block (dangerous operation detected — hard stop)
    2 - Deny  (requires explicit user approval)

Fail-open: any unhandled exception exits 0 (never block Claude on hook error).
"""

from __future__ import annotations

import contextlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
ALLOW: int = 0
BLOCK: int = 1
DENY: int = 2


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PermissionConfig:
    """Immutable configuration for the permission resolver.

    All tuple fields use tuple (not list) to satisfy frozen=True.
    """

    enabled: bool = True
    timeout_ms: int = 5000
    auto_approve_safe_reads: bool = True
    auto_approve_safe_writes: bool = True
    auto_approve_safe_bash: bool = True

    # Paths where writes are considered safe
    safe_write_paths: tuple[str, ...] = (
        ".claude/",
        "tests/",
        "scripts/",
        "modules/",
        "lib/",
        "__pycache__/",
        ".venv/",
        "node_modules/",
        "dist/",
        "build/",
        "/tmp/",
    )

    # Glob-like extensions that are safe to read
    safe_read_extensions: tuple[str, ...] = (
        ".py",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".txt",
        ".ts",
        ".js",
        ".html",
        ".css",
        ".rst",
        ".cfg",
        ".ini",
    )

    # Path fragments that are always dangerous (write/read)
    dangerous_path_patterns: tuple[str, ...] = (
        ".env",
        "credentials",
        "secrets",
        ".ssh/",
        ".gnupg/",
        "/etc/",
        "/var/log/",
        "/usr/",
        "/root/",
        "private_key",
        "id_rsa",
    )

    # Commands whose first token is considered safe
    safe_bash_commands: tuple[str, ...] = (
        "git",
        "pytest",
        "ruff",
        "python",
        "python3",
        "pip",
        "pip3",
        "npm",
        "node",
        "ls",
        "cat",
        "head",
        "tail",
        "grep",
        "find",
        "echo",
        "pwd",
        "which",
        "make",
        "cargo",
        "curl",
        "wget",
        "uv",
        "uvicorn",
        "black",
        "mypy",
        "pyright",
        "coverage",
    )

    # Regex patterns for dangerous bash commands
    dangerous_bash_patterns: tuple[str, ...] = (
        r"rm\s+-rf\s+/",
        r"sudo\s+rm",
        r"curl\s+.*\|\s*sh",
        r"wget\s+.*\|\s*sh",
        r"dd\s+if=",
        r"mkfs\.",
        r">\s*/dev/",
        r"chmod\s+777",
        r"sudo\s+chmod",
        r":\s*\(\)\s*\{",  # fork bomb pattern
    )


# ---------------------------------------------------------------------------
# Input / Output models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HookInput:
    """Parsed hook payload from Claude Code (stdin JSON)."""

    tool_name: str
    tool_input: dict[str, Any]
    session_id: str

    @classmethod
    def from_stdin(cls) -> HookInput:
        """Parse JSON from stdin and return HookInput."""
        data: dict[str, Any] = json.load(sys.stdin)
        return cls(
            tool_name=data.get("tool_name", ""),
            tool_input=data.get("tool_input", {}),
            session_id=data.get("session_id", ""),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HookInput:
        """Create from a plain dict (useful for testing)."""
        return cls(
            tool_name=data.get("tool_name", ""),
            tool_input=data.get("tool_input", {}),
            session_id=data.get("session_id", ""),
        )


@dataclass(frozen=True)
class PermissionResult:
    """Resolution outcome — emits to stdout/stderr and exits."""

    exit_code: int
    message: str = ""
    reason: str = ""
    auto_approved: bool = False

    def emit(self) -> None:
        """Write result JSON to stdout and exit with exit_code."""
        payload: dict[str, Any] = {
            "exit_code": self.exit_code,
            "reason": self.reason,
            "auto_approved": self.auto_approved,
        }
        if self.message:
            print(self.message, file=sys.stderr)
        json.dump(payload, sys.stdout)
        sys.exit(self.exit_code)


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


def load_config(config_path: Path | None = None) -> PermissionConfig:
    """Load PermissionConfig from an optional JSON config file.

    Args:
        config_path: Path to a JSON config file. If None, uses a default
                     sibling hooks.json relative to this file.

    Returns:
        PermissionConfig (defaults if file is absent or unreadable).
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "settings.hooks.json"
    if config_path.exists():
        with contextlib.suppress(OSError):
            config_path.read_text()  # Validate readable; parsed if needed later
    return PermissionConfig()


# ---------------------------------------------------------------------------
# Permission checks
# ---------------------------------------------------------------------------


def _path_is_dangerous(file_path: str, config: PermissionConfig) -> bool:
    """Return True if file_path matches any dangerous pattern."""
    lower = file_path.lower()
    return any(p in lower for p in config.dangerous_path_patterns)


def is_safe_read(tool_input: dict[str, Any], config: PermissionConfig) -> bool:
    """Return True when a Read operation is considered safe.

    A read is safe when:
        - The file has a recognised safe extension, OR
        - The path does not contain any dangerous pattern.

    Args:
        tool_input: The "tool_input" dict from the hook payload.
        config: Active PermissionConfig.

    Returns:
        True if the read can be auto-approved.
    """
    file_path: str = tool_input.get("file_path", "")
    if not file_path:
        return False
    if _path_is_dangerous(file_path, config):
        return False
    ext = Path(file_path).suffix.lower()
    if ext in config.safe_read_extensions:
        return True
    # Permit reads of files without extension (e.g. Makefile, Dockerfile)
    return not ext or ext not in (".key", ".pem", ".p12", ".pfx", ".cer")


def is_safe_write(tool_input: dict[str, Any], config: PermissionConfig) -> bool:
    """Return True when a write operation is considered safe.

    A write is safe when the file_path starts with (or contains) a safe
    write path AND does not contain any dangerous pattern.

    Args:
        tool_input: The "tool_input" dict from the hook payload.
        config: Active PermissionConfig.

    Returns:
        True if the write can be auto-approved.
    """
    file_path: str = tool_input.get("file_path", "")
    if not file_path:
        return False
    if _path_is_dangerous(file_path, config):
        return False
    return any(safe in file_path for safe in config.safe_write_paths)


def is_safe_bash(tool_input: dict[str, Any], config: PermissionConfig) -> bool:
    """Return True when a Bash command is considered safe.

    A command is safe when:
        - Its first token is in safe_bash_commands, AND
        - It does not match any dangerous_bash_patterns.

    Args:
        tool_input: The "tool_input" dict from the hook payload.
        config: Active PermissionConfig.

    Returns:
        True if the command can be auto-approved.
    """
    command: str = tool_input.get("command", "")
    if not command:
        return False
    # Reject dangerous patterns first (highest priority)
    for pattern in config.dangerous_bash_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return False
    tokens = command.strip().split()
    if not tokens:
        return False
    first_token = tokens[0]
    return first_token in config.safe_bash_commands


# ---------------------------------------------------------------------------
# Main resolution logic
# ---------------------------------------------------------------------------


def resolve_permission(
    hook_input: HookInput,
    config: PermissionConfig,
) -> PermissionResult:
    """Determine the permission decision for a given tool invocation.

    Decision table:
        Read  — auto-approve if safe, else allow with review flag
        Write/Edit/MultiEdit — auto-approve if safe path; deny if dangerous;
                               else allow with review flag
        Bash  — auto-approve if safe command; block if dangerous pattern;
                else allow with review flag
        Task  — always allow (sub-agent delegation)
        *     — default allow with review flag

    Args:
        hook_input: Parsed hook payload.
        config: Active PermissionConfig.

    Returns:
        PermissionResult encoding the decision.
    """
    tool_name = hook_input.tool_name
    tool_input = hook_input.tool_input

    # Read -------------------------------------------------------------------
    if tool_name == "Read":
        if config.auto_approve_safe_reads and is_safe_read(tool_input, config):
            return PermissionResult(
                exit_code=ALLOW,
                reason="safe_read_extension",
                auto_approved=True,
            )
        return PermissionResult(
            exit_code=ALLOW,
            reason="read_requires_review",
            auto_approved=False,
        )

    # Write / Edit / MultiEdit -----------------------------------------------
    if tool_name in ("Write", "Edit", "MultiEdit"):
        file_path = tool_input.get("file_path", "")
        if _path_is_dangerous(file_path, config):
            return PermissionResult(
                exit_code=DENY,
                message=f"Dangerous write target blocked: {file_path}",
                reason="dangerous_path_detected",
                auto_approved=False,
            )
        if config.auto_approve_safe_writes and is_safe_write(tool_input, config):
            return PermissionResult(
                exit_code=ALLOW,
                reason="safe_write_path",
                auto_approved=True,
            )
        return PermissionResult(
            exit_code=ALLOW,
            reason="write_requires_review",
            auto_approved=False,
        )

    # Bash -------------------------------------------------------------------
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        for pattern in config.dangerous_bash_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return PermissionResult(
                    exit_code=BLOCK,
                    message=f"Dangerous bash pattern blocked: {pattern}",
                    reason="dangerous_bash_pattern",
                    auto_approved=False,
                )
        if config.auto_approve_safe_bash and is_safe_bash(tool_input, config):
            return PermissionResult(
                exit_code=ALLOW,
                reason="safe_bash_command",
                auto_approved=True,
            )
        return PermissionResult(
            exit_code=ALLOW,
            reason="bash_requires_review",
            auto_approved=False,
        )

    # Task (sub-agent delegation) — always allow
    if tool_name == "Task":
        return PermissionResult(
            exit_code=ALLOW,
            reason="task_delegation_allowed",
            auto_approved=True,
        )

    # Default ----------------------------------------------------------------
    return PermissionResult(
        exit_code=ALLOW,
        reason="default_allow",
        auto_approved=False,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Hook entry point — reads stdin JSON, emits decision, exits."""
    try:
        config = load_config()
        if not config.enabled:
            PermissionResult(ALLOW, reason="hook_disabled").emit()
            return  # unreachable after emit(), kept for clarity

        hook_input = HookInput.from_stdin()
        result = resolve_permission(hook_input, config)
        result.emit()

    except json.JSONDecodeError as exc:
        # Fail-open on malformed input
        PermissionResult(
            ALLOW,
            message=f"[auto_permission_resolver] JSON parse error (fail-open): {exc}",
            reason="json_decode_error",
        ).emit()
    except Exception as exc:
        # Fail-open on any unexpected error
        PermissionResult(
            ALLOW,
            message=f"[auto_permission_resolver] Unexpected error (fail-open): {exc}",
            reason="unexpected_error",
        ).emit()


if __name__ == "__main__":
    main()
