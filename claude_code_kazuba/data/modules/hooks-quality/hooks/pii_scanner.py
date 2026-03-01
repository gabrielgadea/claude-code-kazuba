"""PreToolUse hook: detect PII (Personally Identifiable Information) in file writes.

Uses lib.patterns.PIIPatterns with country-configurable detection.
Default country: BR (CPF, CNPJ). Warns but does NOT block (exit 0).
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from claude_code_kazuba.hook_base import ALLOW, fail_open
from claude_code_kazuba.patterns import PIIPatterns

# Default country for PII detection — override via PII_COUNTRY env var
DEFAULT_COUNTRY: str = "BR"


def get_country() -> str:
    """Get the configured country code for PII detection.

    Returns:
        Country code string (e.g., "BR", "US", "EU").
    """
    return os.environ.get("PII_COUNTRY", DEFAULT_COUNTRY).upper()


def scan_for_pii(content: str, country: str) -> list[str]:
    """Scan file content for PII patterns.

    Args:
        content: The file content to scan.
        country: Country code for pattern selection.

    Returns:
        List of PII detection descriptions. Empty if clean.
    """
    pattern_set = PIIPatterns.for_country(country)
    matches = pattern_set.detect(content)

    findings: list[str] = []
    for match in matches:
        # Partially redact the matched text
        text = match.matched_text
        redacted = text[:3] + "***" + text[-2:] if len(text) > 6 else "***"
        findings.append(
            f"PII ({country}) at position {match.start}: {redacted}"
        )
    return findings


@fail_open
def main() -> None:
    """Main hook entry point: read stdin, scan for PII, warn if found."""
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

    country = get_country()
    findings = scan_for_pii(content, country)

    if not findings:
        sys.exit(ALLOW)

    # Warn but do NOT block
    warning_lines = [f"[pii-scanner] {len(findings)} PII pattern(s) detected in {file_path}:"]
    for finding in findings:
        warning_lines.append(f"  - {finding}")
    warning_lines.append("")
    warning_lines.append("Consider removing or redacting PII before committing.")

    warning = "\n".join(warning_lines)
    print(warning, file=sys.stderr)

    # Exit 0 — warn only, do not block
    sys.exit(ALLOW)


if __name__ == "__main__":
    main()
