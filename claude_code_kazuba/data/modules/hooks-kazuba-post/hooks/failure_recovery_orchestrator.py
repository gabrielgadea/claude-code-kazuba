#!/usr/bin/env python3
"""
PostToolUseFailure Hook: Recovery Orchestrator.

This hook intercepts PostToolUseFailure events to analyze failures
and suggest automatic recovery strategies based on error patterns.

Exit codes:
  0 - Recovery strategy determined
  1 - No recovery available (non-blocking)

Input (stdin): JSON with tool_name, error, tool_input
Output (stdout): JSON with recovery strategy and commands
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# ============================================================================
# EXIT CODES
# ============================================================================

ALLOW = 0
BLOCK = 1

# ============================================================================
# RECOVERY PATTERNS
# ============================================================================


@dataclass(frozen=True)
class RecoveryStrategy:
    """A strategy for recovering from a specific error pattern."""

    pattern: str
    strategy: str
    description: str
    command: str | None = None
    suggestion: str | None = None
    auto_apply: bool = False


# Recovery patterns ordered by priority
RECOVERY_PATTERNS: tuple[RecoveryStrategy, ...] = (
    # Ruff/formatting errors
    RecoveryStrategy(
        pattern=r"ruff.*error|ruff.*check",
        strategy="auto_fix",
        description="Auto-fix with ruff",
        command="ruff check --fix {file_path}",
        auto_apply=True,
    ),
    RecoveryStrategy(
        pattern=r"ruff.*format",
        strategy="auto_fix",
        description="Auto-format with ruff",
        command="ruff format {file_path}",
        auto_apply=True,
    ),
    # Import errors
    RecoveryStrategy(
        pattern=r"ModuleNotFoundError|ImportError|No module named",
        strategy="suggest",
        description="Missing module",
        suggestion="Install missing module with: uv add {module_name} or pip install {module_name}",
    ),
    # Permission errors
    RecoveryStrategy(
        pattern=r"PermissionError|EACCES|Permission denied",
        strategy="escalate",
        description="Permission denied - requires user intervention",
        suggestion="Check file permissions with: ls -la {file_path}",
    ),
    # File not found
    RecoveryStrategy(
        pattern=r"FileNotFoundError|ENOENT|No such file",
        strategy="verify_path",
        description="File not found - verify path exists",
        suggestion="Verify path with: ls -la {directory}",
    ),
    # Syntax errors
    RecoveryStrategy(
        pattern=r"SyntaxError|invalid syntax",
        strategy="analyze",
        description="Syntax error - analyze and suggest fix",
        command="python -m py_compile {file_path}",
    ),
    # Type errors
    RecoveryStrategy(
        pattern=r"TypeError|type.*error",
        strategy="type_check",
        description="Type error - run type checker",
        command="pyright {file_path}",
    ),
    RecoveryStrategy(
        pattern=r"AttributeError|has no attribute",
        strategy="type_check",
        description="Attribute error - check object type",
        command="pyright {file_path}",
    ),
    # Test failures
    RecoveryStrategy(
        pattern=r"AssertionError|FAILED.*test|pytest.*failed",
        strategy="rerun_tests",
        description="Test failure - rerun with verbose output",
        command="pytest {file_path} -v --tb=long",
    ),
    # Git errors
    RecoveryStrategy(
        pattern=r"git.*error|fatal.*git",
        strategy="git_recovery",
        description="Git error - check repository state",
        command="git status && git diff",
    ),
    # Network/timeout errors
    RecoveryStrategy(
        pattern=r"ConnectionError|TimeoutError|ETIMEDOUT",
        strategy="retry",
        description="Network error - retry after delay",
        suggestion="Wait and retry the operation",
    ),
    # Memory errors
    RecoveryStrategy(
        pattern=r"MemoryError|out of memory|OOM",
        strategy="escalate",
        description="Memory error - reduce operation scope",
        suggestion="Process data in smaller batches",
    ),
    # JSON/parsing errors
    RecoveryStrategy(
        pattern=r"JSONDecodeError|json.*error|invalid JSON",
        strategy="analyze",
        description="JSON parse error - validate JSON syntax",
        suggestion="Check JSON syntax with: python -m json.tool < {file_path}",
    ),
)


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass(frozen=True)
class HookInput:
    """Parsed input from Claude Code PostToolUseFailure event."""

    tool_name: str
    error: str
    file_path: str
    tool_input: dict[str, Any]

    @classmethod
    def from_stdin(cls) -> HookInput:
        """Parse JSON input from stdin."""
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {e}") from e

        tool_input = data.get("tool_input", {})

        return cls(
            tool_name=data.get("tool_name", ""),
            error=data.get("error", ""),
            file_path=tool_input.get("file_path", ""),
            tool_input=tool_input,
        )


@dataclass(frozen=True)
class RecoveryResult:
    """Result of recovery analysis."""

    exit_code: int
    recovery_available: bool
    strategy: str
    description: str
    command: str | None
    suggestion: str | None
    auto_apply: bool
    message: str

    def to_json(self) -> str:
        """Convert to JSON string for output."""
        return json.dumps(
            {
                "recovery_available": self.recovery_available,
                "strategy": self.strategy,
                "description": self.description,
                "command": self.command,
                "suggestion": self.suggestion,
                "auto_apply": self.auto_apply,
            }
        )

    def emit(self) -> None:
        """Emit result and exit."""
        print(self.message, file=sys.stderr)
        print(self.to_json())
        sys.exit(self.exit_code)


# ============================================================================
# RECOVERY LOGIC
# ============================================================================


def extract_module_name(error: str) -> str:
    """Extract module name from import error."""
    match = re.search(r"No module named ['\"]?(\w+)", error)
    if match:
        return match.group(1)
    return "unknown_module"


def extract_directory(file_path: str) -> str:
    """Extract directory from file path."""
    if "/" in file_path:
        return "/".join(file_path.split("/")[:-1]) or "."
    return "."


# Pre-compiled regex patterns — avoid per-call re.compile() overhead
_COMPILED_RECOVERY_RES: tuple[tuple[re.Pattern[str], RecoveryStrategy], ...] = tuple(
    (re.compile(strategy.pattern, re.IGNORECASE), strategy) for strategy in RECOVERY_PATTERNS
)


def match_recovery_pattern(error: str) -> RecoveryStrategy | None:
    """Match error message to recovery pattern."""
    for compiled_re, strategy in _COMPILED_RECOVERY_RES:
        if compiled_re.search(error):
            return strategy
    return None


def format_command(command: str | None, file_path: str, error: str) -> str | None:
    """Format recovery command with context."""
    if command is None:
        return None

    return command.format(
        file_path=file_path,
        directory=extract_directory(file_path),
        module_name=extract_module_name(error),
    )


def format_suggestion(suggestion: str | None, file_path: str, error: str) -> str | None:
    """Format recovery suggestion with context."""
    if suggestion is None:
        return None

    return suggestion.format(
        file_path=file_path,
        directory=extract_directory(file_path),
        module_name=extract_module_name(error),
    )


def analyze_failure(hook_input: HookInput) -> RecoveryResult:
    """
    Analyze a tool failure and determine recovery strategy.

    Returns RecoveryResult with appropriate strategy.
    """
    recovery = match_recovery_pattern(hook_input.error)

    if recovery:
        return RecoveryResult(
            exit_code=ALLOW,
            recovery_available=True,
            strategy=recovery.strategy,
            description=recovery.description,
            command=format_command(recovery.command, hook_input.file_path, hook_input.error),
            suggestion=format_suggestion(recovery.suggestion, hook_input.file_path, hook_input.error),
            auto_apply=recovery.auto_apply,
            message=f"Recovery strategy: {recovery.description}",
        )

    return RecoveryResult(
        exit_code=ALLOW,
        recovery_available=False,
        strategy="none",
        description="No automatic recovery available",
        command=None,
        suggestion="Manual intervention required",
        auto_apply=False,
        message="No automatic recovery available",
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main() -> None:
    """Entry point for the PostToolUseFailure hook."""
    try:
        # Parse input
        hook_input = HookInput.from_stdin()

        # Analyze failure
        result = analyze_failure(hook_input)

        # Emit result
        result.emit()

    except ValueError as e:
        # Invalid input - warn but don't block
        print(f"WARNING: Invalid input: {e}", file=sys.stderr)
        print(json.dumps({"recovery_available": False, "strategy": "none"}))
        sys.exit(ALLOW)

    except Exception as e:
        # Unexpected error
        print(f"WARNING: Recovery hook error: {e}", file=sys.stderr)
        print(json.dumps({"recovery_available": False, "strategy": "none"}))
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
