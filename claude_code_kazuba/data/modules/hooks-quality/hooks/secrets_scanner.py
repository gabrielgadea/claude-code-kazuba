"""PreToolUse hook: detect secrets in file writes.

Uses lib.patterns.SecretPatterns to scan file content for API keys,
tokens, passwords, and other credentials. Blocks writes that contain
detected secrets unless the file is whitelisted (test files, .example).
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from claude_code_kazuba.hook_base import ALLOW, BLOCK, fail_open
from claude_code_kazuba.json_output import emit_json, pre_tool_use_output
from claude_code_kazuba.patterns import SecretPatterns

# Whitelist patterns for files where secrets are acceptable
WHITELISTED_PATH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"test[_s]?/"),
    re.compile(r"_test\."),
    re.compile(r"test_\w+\."),
    re.compile(r"\.test\."),
    re.compile(r"\.example$"),
    re.compile(r"\.example\."),
    re.compile(r"\.sample$"),
    re.compile(r"\.sample\."),
    re.compile(r"\.template$"),
    re.compile(r"\.template\."),
    re.compile(r"conftest\.py$"),
    re.compile(r"fixtures?/"),
    re.compile(r"mocks?/"),
]


def is_whitelisted_path(file_path: str) -> bool:
    """Check if a file path is whitelisted for secret detection.

    Args:
        file_path: The file path to check.

    Returns:
        True if the file is whitelisted (secrets are expected).
    """
    return any(p.search(file_path) for p in WHITELISTED_PATH_PATTERNS)


def scan_for_secrets(content: str, file_path: str) -> list[str]:
    """Scan file content for secrets.

    Args:
        content: The file content to scan.
        file_path: Path of the file being written (for whitelist check).

    Returns:
        List of detected secret descriptions. Empty if clean or whitelisted.
    """
    if is_whitelisted_path(file_path):
        return []

    pattern_set = SecretPatterns.create()
    matches = pattern_set.detect(content)

    findings: list[str] = []
    for match in matches:
        # Redact the actual matched text for safety
        redacted = match.matched_text[:8] + "..." if len(match.matched_text) > 8 else "***"
        findings.append(
            f"Secret detected at position {match.start}: {redacted} "
            f"(pattern: {match.pattern_name[:40]})"
        )
    return findings


@fail_open
def main() -> None:
    """Main hook entry point: read stdin, scan for secrets, emit result."""
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    data: dict[str, Any] = json.loads(raw)
    tool_name = data.get("tool_name", "")

    # Only check Write and Edit tools
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path: str = tool_input.get("file_path", "")
    content: str = tool_input.get("content", tool_input.get("new_string", ""))

    if not file_path or not content:
        sys.exit(0)

    findings = scan_for_secrets(content, file_path)

    if not findings:
        sys.exit(ALLOW)

    # Block the write
    reason_lines = [f"[secrets-scanner] {len(findings)} secret(s) detected in {file_path}:"]
    for finding in findings:
        reason_lines.append(f"  - {finding}")
    reason_lines.append("")
    reason_lines.append("Remove secrets before writing. Use environment variables instead.")

    reason = "\n".join(reason_lines)
    output = pre_tool_use_output("block", reason)
    emit_json(output)
    sys.exit(BLOCK)


if __name__ == "__main__":
    main()
