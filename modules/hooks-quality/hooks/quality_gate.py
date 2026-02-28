"""PreToolUse hook: quality gate for Write/Edit operations.

Validates files before they are written or edited:
- Checks file does not exceed max line count
- Detects debug code (print, console.log, etc.) in production files
- Warns about missing docstrings in public functions
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Any

# Ensure lib is importable from project root
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))

from lib.hook_base import ALLOW, BLOCK, fail_open
from lib.json_output import emit_json, pre_tool_use_output

# --- Configuration ---
MAX_LINE_COUNT: int = 500
DEBUG_ONLY_FILE_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java"}
)
TEST_PATH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"test[_s]?/"),
    re.compile(r"_test\."),
    re.compile(r"test_\w+\."),
    re.compile(r"\.test\."),
    re.compile(r"spec[_s]?/"),
    re.compile(r"\.spec\."),
    re.compile(r"conftest\.py"),
]

# Debug code patterns per language
DEBUG_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    ".py": [
        re.compile(r"^\s*print\s*\(", re.MULTILINE),
        re.compile(r"^\s*breakpoint\s*\(", re.MULTILINE),
        re.compile(r"^\s*import\s+pdb", re.MULTILINE),
        re.compile(r"^\s*pdb\.set_trace\s*\(", re.MULTILINE),
    ],
    ".js": [
        re.compile(r"^\s*console\.\w+\s*\(", re.MULTILINE),
        re.compile(r"^\s*debugger\s*;?\s*$", re.MULTILINE),
    ],
    ".ts": [
        re.compile(r"^\s*console\.\w+\s*\(", re.MULTILINE),
        re.compile(r"^\s*debugger\s*;?\s*$", re.MULTILINE),
    ],
    ".tsx": [
        re.compile(r"^\s*console\.\w+\s*\(", re.MULTILINE),
        re.compile(r"^\s*debugger\s*;?\s*$", re.MULTILINE),
    ],
    ".jsx": [
        re.compile(r"^\s*console\.\w+\s*\(", re.MULTILINE),
        re.compile(r"^\s*debugger\s*;?\s*$", re.MULTILINE),
    ],
}

# Docstring detection for Python
PY_PUBLIC_FUNC_RE = re.compile(
    r'^(def\s+(?!_)\w+\s*\([^)]*\).*?:)\s*\n((?!\s*"""|\s*\'\'\'))',
    re.MULTILINE,
)


@dataclass(frozen=True)
class QualityIssue:
    """A detected quality issue."""

    severity: str  # "error" or "warning"
    message: str


def is_test_file(file_path: str) -> bool:
    """Check if a file path belongs to a test file.

    Args:
        file_path: The path to check.

    Returns:
        True if the file is a test file.
    """
    return any(p.search(file_path) for p in TEST_PATH_PATTERNS)


def get_file_extension(file_path: str) -> str:
    """Extract file extension from path.

    Args:
        file_path: The file path.

    Returns:
        The file extension including the dot (e.g., ".py").
    """
    dot_idx = file_path.rfind(".")
    if dot_idx == -1:
        return ""
    return file_path[dot_idx:]


def check_line_count(content: str, max_lines: int = MAX_LINE_COUNT) -> QualityIssue | None:
    """Check if content exceeds the maximum line count.

    Args:
        content: File content to check.
        max_lines: Maximum allowed line count.

    Returns:
        QualityIssue if exceeded, None otherwise.
    """
    line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    if line_count > max_lines:
        return QualityIssue(
            severity="error",
            message=f"File has {line_count} lines (max: {max_lines}). Consider splitting.",
        )
    return None


def check_debug_code(
    content: str,
    file_path: str,
) -> list[QualityIssue]:
    """Check for debug code in production files.

    Args:
        content: File content to check.
        file_path: Path to determine language and test status.

    Returns:
        List of QualityIssue for each debug pattern found.
    """
    if is_test_file(file_path):
        return []

    ext = get_file_extension(file_path)
    if ext not in DEBUG_ONLY_FILE_EXTENSIONS:
        return []

    patterns = DEBUG_PATTERNS.get(ext, [])
    issues: list[QualityIssue] = []
    for pattern in patterns:
        matches = pattern.findall(content)
        if matches:
            issues.append(
                QualityIssue(
                    severity="warning",
                    message=f"Debug code detected: {matches[0].strip()!r} in {file_path}",
                )
            )
    return issues


def check_docstrings(content: str, file_path: str) -> list[QualityIssue]:
    """Check for missing docstrings in public Python functions.

    Args:
        content: File content to check.
        file_path: Path to determine if Python file.

    Returns:
        List of QualityIssue for each public function without docstring.
    """
    if not file_path.endswith(".py") or is_test_file(file_path):
        return []

    issues: list[QualityIssue] = []
    for match in PY_PUBLIC_FUNC_RE.finditer(content):
        func_def = match.group(1).strip()
        issues.append(
            QualityIssue(
                severity="warning",
                message=f"Missing docstring: {func_def}",
            )
        )
    return issues


def run_quality_gate(
    content: str,
    file_path: str,
    max_lines: int = MAX_LINE_COUNT,
) -> tuple[list[QualityIssue], bool]:
    """Run all quality checks on file content.

    Args:
        content: File content to check.
        file_path: Path of the file being written.
        max_lines: Maximum allowed line count.

    Returns:
        Tuple of (issues list, should_block boolean).
    """
    issues: list[QualityIssue] = []

    # Check line count
    line_issue = check_line_count(content, max_lines)
    if line_issue is not None:
        issues.append(line_issue)

    # Check debug code
    issues.extend(check_debug_code(content, file_path))

    # Check docstrings
    issues.extend(check_docstrings(content, file_path))

    # Block only on errors, not warnings
    should_block = any(issue.severity == "error" for issue in issues)
    return issues, should_block


@fail_open
def main() -> None:
    """Main hook entry point: read stdin, validate, emit result."""
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

    issues, should_block = run_quality_gate(content, file_path)

    if not issues:
        sys.exit(0)

    # Format message
    msg_lines = ["[quality-gate] Issues detected:"]
    for issue in issues:
        prefix = "ERROR" if issue.severity == "error" else "WARN"
        msg_lines.append(f"  [{prefix}] {issue.message}")

    reason = "\n".join(msg_lines)

    if should_block:
        output = pre_tool_use_output("block", reason)
        emit_json(output)
        sys.exit(BLOCK)
    else:
        # Warn but allow
        print(reason, file=sys.stderr)
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
