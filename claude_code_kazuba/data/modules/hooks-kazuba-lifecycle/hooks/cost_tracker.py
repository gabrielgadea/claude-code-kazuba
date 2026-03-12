#!/usr/bin/env python3
"""Stop hook: session cost tracker (D7 ECC absorption).

Event: Stop
Purpose: Records per-session token usage and estimated cost to costs.jsonl.

Model pricing (claude-sonnet-4-6, 2026-03):
  Input:       $3.00 / 1M tokens
  Output:      $15.00 / 1M tokens
  Cache write: $3.75 / 1M tokens
  Cache read:  $0.30 / 1M tokens

JSONL record schema:
  {
    "session_id": "...",
    "timestamp": "2026-03-06T...",
    "model": "claude-sonnet-4-6",
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_tokens": 0,
    "cache_read_tokens": 0,
    "estimated_cost_usd": 0.0,
    "hook_profile": "strict",
    "compliance_score": null
  }

Exit codes:
  0 — Always (Stop hooks must never block)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
COSTS_FILE = PROJECT_ROOT / ".claude" / "metrics" / "costs.jsonl"
COMPLIANCE_FILE = PROJECT_ROOT / ".claude" / "metrics" / "compliance.jsonl"

# Pricing per 1M tokens (claude-sonnet-4-6 as of 2026-03)
_PRICING: dict[str, float] = {
    "input": 3.00,
    "output": 15.00,
    "cache_write": 3.75,
    "cache_read": 0.30,
}


def _estimate_cost(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
) -> float:
    """Compute estimated USD cost from token counts.

    Args:
        input_tokens: Regular input token count.
        output_tokens: Output token count.
        cache_creation_tokens: Cache write tokens (higher cost).
        cache_read_tokens: Cache read tokens (lower cost).

    Returns:
        Estimated cost in USD, rounded to 6 decimal places.
    """
    cost = (
        input_tokens * _PRICING["input"]
        + output_tokens * _PRICING["output"]
        + cache_creation_tokens * _PRICING["cache_write"]
        + cache_read_tokens * _PRICING["cache_read"]
    ) / 1_000_000
    return round(cost, 6)


def _read_latest_compliance() -> float | None:
    """Read the most recent compliance_score from compliance.jsonl.

    Returns:
        Latest score or None if unavailable.
    """
    if not COMPLIANCE_FILE.exists():
        return None
    try:
        lines = COMPLIANCE_FILE.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            score = record.get("enforcement_score") or record.get("compliance_score")
            if score is not None:
                return float(score)
    except Exception:
        pass
    return None


def _build_record(data: dict) -> dict:
    """Build JSONL cost record from Stop hook input.

    Args:
        data: Raw JSON from stdin.

    Returns:
        Structured cost record.
    """
    usage = data.get("usage") or {}
    input_tokens = int(usage.get("input_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    cache_creation = int(usage.get("cache_creation_input_tokens", 0))
    cache_read = int(usage.get("cache_read_input_tokens", 0))

    cost = _estimate_cost(input_tokens, output_tokens, cache_creation, cache_read)

    return {
        "session_id": data.get("session_id", "unknown"),
        "timestamp": datetime.now(UTC).isoformat(),
        "model": data.get("model", os.environ.get("ANTHROPIC_MODEL", "unknown")),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_tokens": cache_creation,
        "cache_read_tokens": cache_read,
        "estimated_cost_usd": cost,
        "hook_profile": os.environ.get("ANTT_HOOK_PROFILE", "strict"),
        "compliance_score": _read_latest_compliance(),
    }


def _append_record(record: dict) -> None:
    """Append JSON record to JSONL file (creates file if missing)."""
    COSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with COSTS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def main() -> None:
    """Stop hook entry point. Never blocks (exit 0 always)."""
    try:
        try:
            data = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError, ValueError):
            data = {}

        record = _build_record(data)
        _append_record(record)

    except Exception:
        pass  # Stop hooks must NEVER fail loudly

    sys.exit(0)


if __name__ == "__main__":
    main()
