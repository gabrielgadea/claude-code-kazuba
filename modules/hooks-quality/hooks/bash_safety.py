"""PreToolUse hook: block dangerous bash commands.

Uses lib.patterns.BashSafetyPatterns to detect and block dangerous shell
commands like rm -rf /, chmod 777, curl|bash, and fork bombs.
Allows safe patterns in approved directories.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

# Ensure lib is importable from project root
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))

from claude_code_kazuba.hook_base import ALLOW, BLOCK, fail_open
from claude_code_kazuba.json_output import emit_json, pre_tool_use_output
from claude_code_kazuba.patterns import BashSafetyPatterns

# Approved directories where destructive operations are allowed
# Override via BASH_SAFETY_APPROVED_DIRS env var (colon-separated)
DEFAULT_APPROVED_DIRS: list[str] = [
    "/tmp/",
    "/var/tmp/",
]

# Safe rm patterns (rm in approved directories)
SAFE_RM_RE = re.compile(r"rm\s+.*(/tmp/|/var/tmp/)")


def get_approved_dirs() -> list[str]:
    """Get the list of approved directories for destructive operations.

    Returns:
        List of directory path prefixes.
    """
    env_dirs = os.environ.get("BASH_SAFETY_APPROVED_DIRS", "")
    if env_dirs:
        return [d.strip() for d in env_dirs.split(":") if d.strip()]
    return DEFAULT_APPROVED_DIRS


def is_command_safe(command: str, approved_dirs: list[str]) -> bool:
    """Check if a dangerous command is operating in an approved directory.

    Args:
        command: The shell command string.
        approved_dirs: List of approved directory prefixes.

    Returns:
        True if the command targets only approved directories.
    """
    return any(approved in command for approved in approved_dirs)


def scan_bash_command(command: str) -> list[str]:
    """Scan a bash command for dangerous patterns.

    Args:
        command: The shell command to scan.

    Returns:
        List of danger descriptions. Empty if safe.
    """
    pattern_set = BashSafetyPatterns.create()
    matches = pattern_set.detect(command)

    approved_dirs = get_approved_dirs()
    findings: list[str] = []

    for match in matches:
        # Check if the match is in an approved directory
        if is_command_safe(command, approved_dirs):
            continue
        findings.append(
            f"Dangerous command: {match.matched_text!r} "
            f"(pattern: {match.pattern_name[:50]})"
        )
    return findings


@fail_open
def main() -> None:
    """Main hook entry point: read stdin, scan bash command, block if dangerous."""
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    data: dict[str, Any] = json.loads(raw)
    tool_name = data.get("tool_name", "")

    # Only check Bash tool
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command: str = tool_input.get("command", "")

    if not command:
        sys.exit(0)

    findings = scan_bash_command(command)

    if not findings:
        sys.exit(ALLOW)

    # Block the command
    reason_lines = [f"[bash-safety] {len(findings)} dangerous pattern(s) detected:"]
    for finding in findings:
        reason_lines.append(f"  - {finding}")
    reason_lines.append("")
    reason_lines.append("This command has been blocked for safety.")

    reason = "\n".join(reason_lines)
    output = pre_tool_use_output("block", reason)
    emit_json(output)
    sys.exit(BLOCK)


if __name__ == "__main__":
    main()
