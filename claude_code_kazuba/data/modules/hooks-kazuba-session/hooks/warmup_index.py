#!/usr/bin/env python3
"""Warmup Index — SessionStart hook for search index initialization.

Event: SessionStart
Purpose: Full reindex of .claude/ directory on session start.

Exit codes:
    0 - Allow (success, index warmed up)
    1 - Block (with error message to stderr)

Input (stdin): JSON with session_id, etc.
Output (stdout): JSON with reindex stats.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Exit codes
ALLOW = 0
BLOCK = 1

# Default paths
DEFAULT_INDEX_DIR = Path(".claude/data/search_index")
DEFAULT_CLAUDE_ROOT = Path(".claude")

# Module-level optional import — graceful degradation if tantivy is not installed.
# ModuleNotFoundError is a subclass of ImportError, so this catches missing tantivy too.
try:
    from search_api import SearchIndexer as _SearchIndexer  # type: ignore[import]

    _SEARCH_API_AVAILABLE = True
except ImportError:
    _SearchIndexer = None  # type: ignore[assignment]
    _SEARCH_API_AVAILABLE = False


def run_warmup(
    index_dir: Path | None = None,
    claude_root: Path | None = None,
) -> dict[str, Any]:
    """Run full reindex of .claude/ directory.

    Args:
        index_dir: Directory for the Tantivy index.
        claude_root: Root of the .claude/ directory.

    Returns:
        Dict with reindex stats (indexed, skipped, errors).
        Returns zeros with a reason key when search_api is unavailable.
    """
    if _SearchIndexer is None:
        return {
            "indexed": 0,
            "skipped": 0,
            "errors": 0,
            "reason": "tantivy not installed — pip install tantivy to enable",
        }

    idx_dir = index_dir or DEFAULT_INDEX_DIR
    root = claude_root or DEFAULT_CLAUDE_ROOT

    indexer = _SearchIndexer(index_dir=idx_dir)
    indexer._claude_root = root

    stats = indexer.full_reindex()
    logger.info(
        "Warmup complete: indexed=%d, skipped=%d, errors=%d",
        stats["indexed"],
        stats["skipped"],
        stats["errors"],
    )
    return stats


def main() -> None:
    """Entry point for SessionStart hook."""
    try:
        # Read stdin (SessionStart event) — content unused, just drain stdin
        try:
            json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError):
            pass

        stats = run_warmup()

        # Output stats as JSON — "skipped" when tantivy unavailable, never BLOCK
        status = "ok" if _SEARCH_API_AVAILABLE else "skipped"
        json.dump(
            {"hook": "warmup_index", "status": status, **stats},
            sys.stdout,
        )
        sys.exit(ALLOW)

    except Exception as exc:
        print(f"Warmup error: {exc}", file=sys.stderr)
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
