#!/usr/bin/env python3
"""
Hook: PGCC Validator
Event: PreToolUse (SYNC, ≤3s budget)
Purpose: Detect drift between warm cache symbols and file about to be written.

Exit codes:
  0 - Allow (ALWAYS — fail-open pattern, never blocks writes)

Input (stdin):  JSON with tool_name, tool_input {file_path, content/old_string/new_string}
Output (stderr): Warning if significant symbol drift detected (informational only)
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PGCC_DIR = Path(__file__).parent
if str(_PGCC_DIR) not in sys.path:
    sys.path.insert(0, str(_PGCC_DIR))

import contextlib  # noqa: E402

import pgcc_cache  # noqa: E402

ALLOW = 0
WRITE_TOOLS: frozenset[str] = frozenset({"Write", "Edit", "MultiEdit"})

# Module-level cache singleton — avoids opening SQLite on every PreToolUse call.
# Fail-open: if construction raises, _PGCC_CACHE stays None and callers fall back.
_PGCC_CACHE: pgcc_cache.PGCCCache | None = None
with contextlib.suppress(Exception):
    _PGCC_CACHE = pgcc_cache.PGCCCache()

# Drift detection tuning
DRIFT_THRESHOLD: float = 0.40  # warn if overlap_rate < this (>60% symbols removed)
MIN_SYMBOLS_FOR_WARN: int = 2  # minimum cached symbols before drift check applies


# ─────────────────────────────────────────────────────────────────
# Result model
# ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ValidationResult:
    """Immutable result of a PGCC drift validation.

    Args:
        ok: Always True (validator never blocks).
        message: Warning message for stderr, or "" if no drift.
        drift_rate: Fraction of cached symbols removed (0.0–1.0).
        removed_symbols: Sorted tuple of symbol names that were removed.
    """

    ok: bool
    message: str = ""
    drift_rate: float = 0.0
    removed_symbols: tuple[str, ...] = field(default_factory=tuple)


# ─────────────────────────────────────────────────────────────────
# Symbol extraction
# ─────────────────────────────────────────────────────────────────


def _parse_symbols_from_content(content: str) -> list[str]:
    """Extract function/class names from Python source. Returns [] on parse error."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    symbols: list[str] = [
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    ]
    return symbols


# ─────────────────────────────────────────────────────────────────
# Validation logic
# ─────────────────────────────────────────────────────────────────


def validate_write(
    file_path: str,
    content: str,
    session_id: str,
) -> ValidationResult:
    """Validate a Write operation against warm cache symbols.

    Args:
        file_path: Absolute path to file being written.
        content: Full new file content.
        session_id: Claude Code session identifier.

    Returns:
        ValidationResult — ok is always True.
    """
    try:
        cache = _PGCC_CACHE if _PGCC_CACHE is not None else pgcc_cache.PGCCCache()
        cached_entry = cache.get(file_path)

        if cached_entry is None or len(cached_entry.symbols) < MIN_SYMBOLS_FOR_WARN:
            return ValidationResult(ok=True)

        new_symbols = set(_parse_symbols_from_content(content))
        if not new_symbols:
            return ValidationResult(ok=True)

        cached_symbols = set(cached_entry.symbols)
        overlap = cached_symbols & new_symbols
        removed = cached_symbols - new_symbols
        overlap_rate = len(overlap) / len(cached_symbols)

        if overlap_rate < DRIFT_THRESHOLD and removed:
            drift_rate = 1.0 - overlap_rate
            removed_sorted = tuple(sorted(removed))
            sample = ", ".join(removed_sorted[:3])
            ellipsis = "..." if len(removed) > 3 else ""
            msg = (
                f"[PGCC] Drift detected in {Path(file_path).name}: "
                f"{len(removed)} symbol(s) removed — {sample}{ellipsis}"
            )
            return ValidationResult(
                ok=True,
                message=msg,
                drift_rate=drift_rate,
                removed_symbols=removed_sorted,
            )

        return ValidationResult(ok=True)

    except Exception:
        return ValidationResult(ok=True)


def validate_edit(
    file_path: str,
    old_string: str,
    new_string: str,
    session_id: str,
) -> ValidationResult:
    """Validate an Edit operation — detect cached symbols being removed.

    Args:
        file_path: Absolute path to file being edited.
        old_string: Text being replaced.
        new_string: Replacement text.
        session_id: Claude Code session identifier.

    Returns:
        ValidationResult — ok is always True.
    """
    try:
        cache = _PGCC_CACHE if _PGCC_CACHE is not None else pgcc_cache.PGCCCache()
        cached_entry = cache.get(file_path)

        if cached_entry is None or len(cached_entry.symbols) < MIN_SYMBOLS_FOR_WARN:
            return ValidationResult(ok=True)

        removed_from_old = set(_parse_symbols_from_content(old_string))
        added_in_new = set(_parse_symbols_from_content(new_string))
        net_removed = removed_from_old - added_in_new

        cached_symbols = set(cached_entry.symbols)
        cache_symbols_removed = cached_symbols & net_removed

        if len(cache_symbols_removed) >= MIN_SYMBOLS_FOR_WARN:
            drift_rate = len(cache_symbols_removed) / len(cached_symbols)
            if drift_rate >= (1.0 - DRIFT_THRESHOLD):
                removed_sorted = tuple(sorted(cache_symbols_removed))
                sample = ", ".join(removed_sorted[:3])
                msg = f"[PGCC] Edit removes cached symbols in {Path(file_path).name}: {sample}"
                return ValidationResult(
                    ok=True,
                    message=msg,
                    drift_rate=drift_rate,
                    removed_symbols=removed_sorted,
                )

        return ValidationResult(ok=True)

    except Exception:
        return ValidationResult(ok=True)


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point — ALWAYS exits 0. Emits warnings to stderr (informational only)."""
    try:
        data: dict[str, Any] = json.load(sys.stdin)
        tool_name: str = data.get("tool_name", "")
        tool_input: dict[str, Any] = data.get("tool_input", {})
        session_id: str = data.get("session_id", "")

        if tool_name not in WRITE_TOOLS:
            sys.exit(ALLOW)

        file_path: str = tool_input.get("file_path", "")
        if not file_path or not file_path.endswith(".py"):
            sys.exit(ALLOW)

        result: ValidationResult
        if tool_name == "Write":
            content = tool_input.get("content", "")
            result = validate_write(file_path, content, session_id)
        else:
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")
            result = validate_edit(file_path, old_string, new_string, session_id)

        if result.message:
            print(result.message, file=sys.stderr)

    except Exception:
        pass

    sys.exit(ALLOW)


if __name__ == "__main__":
    main()
