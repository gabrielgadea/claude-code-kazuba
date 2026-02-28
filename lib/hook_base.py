"""Core hook infrastructure for Claude Code hooks."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from collections.abc import Callable

# Exit code constants per Claude Code hook contract
ALLOW: int = 0
BLOCK: int = 1
DENY: int = 2


@dataclass(frozen=True)
class HookConfig:
    """Configuration for a hook module."""

    enabled: bool = True
    timeout_ms: int = 10_000


@dataclass(frozen=True)
class HookInput:
    """Parsed hook input from Claude Code.

    Represents the JSON payload received via stdin when a hook is triggered.
    """

    session_id: str
    cwd: str
    hook_event_name: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HookInput:
        """Create HookInput from a dictionary."""
        return cls(
            session_id=data.get("session_id", ""),
            cwd=data.get("cwd", ""),
            hook_event_name=data.get("hook_event_name", ""),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input"),
        )

    @classmethod
    def from_stdin(cls) -> HookInput:
        """Read and parse hook input from stdin."""
        raw = sys.stdin.read()
        data: dict[str, Any] = json.loads(raw)
        return cls.from_dict(data)


@dataclass(frozen=True)
class HookResult:
    """Result to emit back to Claude Code.

    The emit() method handles the hook contract:
    - Message printed to stderr (diagnostic)
    - JSON output printed to stdout (hook-specific output)
    - Process exits with the appropriate exit code
    """

    exit_code: int
    message: str
    output_json: dict[str, Any] | None = None

    def emit(self) -> NoReturn:
        """Print result and exit with the appropriate code.

        Writes message to stderr and output_json to stdout,
        then exits with self.exit_code.
        """
        print(self.message, file=sys.stderr)
        if self.output_json is not None:
            json.dump(self.output_json, sys.stdout)
        sys.exit(self.exit_code)


def fail_open(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that catches all exceptions and exits 0 (fail-open).

    Ensures hooks never block Claude Code operation due to internal errors.
    Prints the exception to stderr for diagnostic purposes.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except SystemExit:
            raise
        except Exception as exc:
            print(f"[fail-open] {exc}", file=sys.stderr)
            sys.exit(0)

    return wrapper
