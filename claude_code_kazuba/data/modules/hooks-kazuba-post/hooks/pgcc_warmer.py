#!/usr/bin/env python3
"""
Hook: PGCC Warmer
Event: PostToolUse (async, 30s budget)
Purpose: Warms PGCC cache when Python files are written or edited.

Exit codes:
  0 - Allow (ALWAYS — fail-open pattern, never blocks user operations)

Input (stdin): JSON with tool_name, tool_input.file_path, session_id
Output: None (async, side-effect only)
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Add pgcc dir to path for module imports (hook runs as standalone script)
_PGCC_DIR = Path(__file__).parent
if str(_PGCC_DIR) not in sys.path:
    sys.path.insert(0, str(_PGCC_DIR))

import contextlib  # noqa: E402

import lifecycle_bridge as lb  # noqa: E402
import models  # noqa: E402
import pgcc_cache  # noqa: E402
import tantivy_bridge as tb  # noqa: E402

logger = logging.getLogger(__name__)

ALLOW = 0
WRITE_TOOLS: frozenset[str] = frozenset({"Write", "Edit"})
L0_TTL_S: float = 60.0  # skip re-warm if same hash seen within 60s


# ─────────────────────────────────────────────────────────────────
# Core logic
# ─────────────────────────────────────────────────────────────────


def _compute_hash(file_path: str) -> str:
    """Compute SHA256[:16] of file content. Returns "" on I/O error."""
    try:
        content = Path(file_path).read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]
    except OSError:
        return ""


def warm_file(file_path: str, session_id: str) -> None:
    """Warm cache for a single Python file.

    Args:
        file_path: Absolute path to the Python file.
        session_id: Claude Code session identifier.
    """
    if not file_path:
        return

    file_hash = _compute_hash(file_path)
    if not file_hash:
        return  # file unreadable — skip silently

    # L0 check: skip if same hash seen recently (within L0_TTL_S)
    cache = pgcc_cache.PGCCCache()
    existing = cache.get(file_path)
    if existing and existing.file_hash == file_hash and not existing.is_stale(ttl_s=L0_TTL_S):
        return  # L0 cache hit — no re-warm needed

    # Extract AST symbols
    symbols_data = _extract_safe(file_path)
    raw_symbols = symbols_data.get("functions", []) + symbols_data.get("classes", [])
    raw_imports = symbols_data.get("imports", [])

    # Apply PII filter
    filtered_data, was_filtered = _apply_pii(raw_symbols, raw_imports)
    clean_symbols = tuple(filtered_data.get("symbols", raw_symbols))
    clean_imports = tuple(filtered_data.get("imports", raw_imports))

    # Build and persist cache entry
    entry = models.WarmCacheEntry(
        file_path=file_path,
        file_hash=file_hash,
        symbols=clean_symbols,
        imports=clean_imports,
        pii_filtered=was_filtered,
    )
    cache.set(entry)

    # WAL log (non-blocking, fail-open)
    _log_wal(file_path, session_id, file_hash)

    # Notify IndexEventBus — EC4: hasattr check inside tb
    _emit_event(file_path)


def _extract_safe(file_path: str) -> dict[str, list[str]]:
    """Extract AST symbols — fail-open, returns empty on error."""
    try:
        import ast_extractor

        return ast_extractor.extract_symbols(file_path)
    except Exception:
        return {"functions": [], "classes": [], "imports": []}


def _apply_pii(symbols: list[str], imports: list[str]) -> tuple[dict[str, Any], bool]:
    """Apply PII filter — returns (data, was_filtered). Fail-open."""
    try:
        return lb.filter_pii({"symbols": symbols, "imports": imports})
    except Exception:
        return {"symbols": symbols, "imports": imports}, False


def _log_wal(file_path: str, session_id: str, file_hash: str) -> None:
    """Log warm event to WAL. Fail-open."""
    with contextlib.suppress(Exception):
        lb.log_wal(
            "PGCC_WARM",
            {"file_path": file_path, "session_id": session_id, "hash": file_hash},
        )


def _emit_event(file_path: str) -> None:
    """Emit IndexUpdated event. Fail-open — EC4 compliance."""
    with contextlib.suppress(Exception):
        tb.emit_cache_update(file_path, "update")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point — ALWAYS exits 0 (fail-open). Never blocks user operations."""
    try:
        data: dict[str, Any] = json.load(sys.stdin)
        tool_name: str = data.get("tool_name", "")
        tool_input: dict[str, Any] = data.get("tool_input", {})
        file_path: str = tool_input.get("file_path", "")
        session_id: str = data.get("session_id", "")

        if tool_name not in WRITE_TOOLS:
            sys.exit(ALLOW)

        if not file_path or not file_path.endswith(".py"):
            sys.exit(ALLOW)

        warm_file(file_path, session_id)

    except Exception:
        pass

    sys.exit(ALLOW)


if __name__ == "__main__":
    main()


# ─────────────────────────────────────────────────────────────────
# S8 Evolution features [R69, R74, R75]
# ─────────────────────────────────────────────────────────────────

#: Sessions with hit_rate below this trigger self-healing rebuild [R74]
SELF_HEAL_HIT_RATE_THRESHOLD: float = 0.30
#: Consecutive low-hit-rate sessions before triggering rebuild [R74]
SELF_HEAL_CONSECUTIVE_SESSIONS: int = 3
#: Fraction of injections skipped for A/B comparison [R75]
AB_SKIP_RATE: float = 0.10


def get_teammate_context(role: str) -> dict[str, object]:
    """Export PGCC context for Agent Teams teammate [R69].

    Returns relevant cache metrics and configuration for a teammate
    to understand the current PGCC state.

    Args:
        role: Teammate role (e.g. "atlas", "themis", "praetor").

    Returns:
        Dict with cache_size, role, hit_rate_threshold, and hints.
    """
    try:
        cache = pgcc_cache.PGCCCache()
        size = cache.size()
        return {
            "role": role,
            "cache_size": size,
            "hit_rate_threshold": SELF_HEAL_HIT_RATE_THRESHOLD,
            "ab_skip_rate": AB_SKIP_RATE,
            "hints": [
                f"PGCC has {size} warmed files in cache",
                "Use warmed symbols for faster context injection",
                f"Self-heal triggers after {SELF_HEAL_CONSECUTIVE_SESSIONS} sessions with hit_rate < 30%",
            ],
        }
    except Exception:
        return {"role": role, "cache_size": 0, "hints": []}


def should_trigger_self_heal(session_hit_rates: list[float]) -> bool:
    """Determine if PGCC self-healing rebuild is needed [R74].

    Self-healing triggers when the last N consecutive sessions all had
    hit_rate < SELF_HEAL_HIT_RATE_THRESHOLD.

    Args:
        session_hit_rates: List of hit rates from recent sessions (most recent last).

    Returns:
        True if full cache rebuild should be triggered.
    """
    if len(session_hit_rates) < SELF_HEAL_CONSECUTIVE_SESSIONS:
        return False
    recent = session_hit_rates[-SELF_HEAL_CONSECUTIVE_SESSIONS:]
    return all(r < SELF_HEAL_HIT_RATE_THRESHOLD for r in recent)


def should_skip_ab(session_id: str, skip_rate: float = AB_SKIP_RATE) -> bool:
    """Determine if this session should be in A/B skip group [R75].

    Uses deterministic hash of session_id for reproducibility.
    Approximately `skip_rate` fraction of sessions will skip injection.

    Args:
        session_id: Claude Code session identifier.
        skip_rate: Fraction of sessions to skip (default 10%).

    Returns:
        True if injection should be skipped for this session.
    """
    if not session_id:
        return False
    bucket = hash(session_id) % 100
    return bucket < round(skip_rate * 100)
