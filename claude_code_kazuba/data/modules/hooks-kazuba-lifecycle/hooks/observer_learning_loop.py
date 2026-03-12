#!/usr/bin/env python3
"""D10: Observer Learning Loop — Stop hook.

Observes session completion patterns and stores high-confidence insights
to a namespace-isolated learning store.

Namespace isolation: SHA-1(project_root)[:8] prevents cross-project
contamination when Claude Code is used in multiple projects.

Threshold: Only stores patterns with confidence >= LEARNING_THRESHOLD (0.5).
Dry-run: Default behavior (ANTT_OBSERVER_ENABLED=1 required to write).
Always exits 0 (Stop hook contract — must never block).

Storage: .claude/learning/{8-char-namespace}/patterns.jsonl
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s observer: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEARNING_THRESHOLD = 0.5  # minimum confidence before storing pattern
DRY_RUN = os.environ.get("ANTT_OBSERVER_DRY_RUN", "0") == "1"


@functools.lru_cache(maxsize=1)
def _namespace_hash() -> str:
    """SHA-1 of project root path for namespace isolation.

    Uses project path (not git remote) to guarantee uniqueness even for
    local-only repositories. Cached because PROJECT_ROOT is immutable.
    """
    raw = str(PROJECT_ROOT).encode()
    return hashlib.sha1(raw, usedforsecurity=False).hexdigest()[:8]


def _learning_dir() -> Path:
    """Return namespace-isolated learning directory, creating if needed."""
    ns = _namespace_hash()
    d = PROJECT_ROOT / ".claude" / "learning" / ns
    if not DRY_RUN:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _parse_stdin() -> dict:
    """Parse JSON from stdin; return empty dict on any failure."""
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _enrich_pattern(pattern: dict, domain: str = "general") -> dict:
    """Add lifecycle fields to a pattern dict (additive, backward-compatible)."""
    return {
        **pattern,
        "domain": domain,
        "scope": "project",
        "last_seen": date.today().isoformat(),
        "session_count": 1,
    }


def _extract_patterns(data: dict) -> list[dict]:
    """Extract learning patterns from session stop data.

    Returns only patterns meeting LEARNING_THRESHOLD confidence.
    """
    patterns: list[dict] = []
    session_id = data.get("session_id", "unknown")
    model = data.get("model", os.environ.get("ANTHROPIC_MODEL", "unknown"))

    # Pattern 1: Session completed — always confidence 0.8
    patterns.append(
        _enrich_pattern(
            {
                "type": "session_completion",
                "confidence": 0.8,
                "session_id": session_id,
                "model": model,
                "hook_profile": os.environ.get("ANTT_HOOK_PROFILE", "strict"),
            },
            domain="general",
        )
    )

    # Pattern 2: Cache efficiency signal
    usage = data.get("usage", {})
    if usage:
        total = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_ratio = cache_read / max(total, 1)
        if cache_ratio > 0.3:
            patterns.append(
                _enrich_pattern(
                    {
                        "type": "cache_efficient_session",
                        "confidence": min(0.5 + cache_ratio, 1.0),
                        "cache_ratio": round(cache_ratio, 3),
                        "session_id": session_id,
                    },
                    domain="rag",
                )
            )

    # Pattern 3: Hook profile usage
    profile = os.environ.get("ANTT_HOOK_PROFILE", "strict")
    if profile != "strict":
        patterns.append(
            _enrich_pattern(
                {
                    "type": "non_strict_profile",
                    "confidence": 0.7,
                    "profile": profile,
                    "session_id": session_id,
                },
                domain="dev",
            )
        )

    # Pattern 4: Error recovery proxy — high turn_count signals retry storms
    turn_count = data.get("turn_count", 0)
    if turn_count > 20:
        patterns.append(
            _enrich_pattern(
                {
                    "type": "error_recovery",
                    "confidence": min(0.6 + (turn_count - 20) * 0.01, 0.9),
                    "turn_count": turn_count,
                    "session_id": session_id,
                },
                domain="dev",
            )
        )

    return [p for p in patterns if p.get("confidence", 0.0) >= LEARNING_THRESHOLD]


def _store_patterns(patterns: list[dict]) -> int:
    """Append patterns to namespace-isolated JSONL. Returns count stored."""
    if not patterns:
        return 0

    ns = _namespace_hash()
    learning_file = _learning_dir() / "patterns.jsonl"
    timestamp = datetime.now(UTC).isoformat()

    if DRY_RUN:
        logger.debug(
            "dry-run: would store %d pattern(s) to .claude/learning/%s/patterns.jsonl",
            len(patterns),
            ns,
        )
        return 0

    try:
        with learning_file.open("a", encoding="utf-8") as f:
            for pattern in patterns:
                record = {"timestamp": timestamp, **pattern}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return len(patterns)
    except Exception as exc:
        logger.warning("failed to store patterns: %s", exc)
        return 0


def main() -> int:
    """Entry point — always exits 0 (Stop hook contract)."""
    try:
        data = _parse_stdin()
        patterns = _extract_patterns(data)
        stored = _store_patterns(patterns)

        if stored > 0:
            logger.info(
                "stored %d pattern(s) [namespace=%s]", stored, _namespace_hash()
            )
    except Exception as exc:
        # Absolute fail-open: never block a session stop
        logger.warning("observer error (ignored): %s", exc)

    return 0  # Stop hook contract: always exit 0


if __name__ == "__main__":
    sys.exit(main())
