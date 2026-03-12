#!/usr/bin/env python3
"""Incremental Indexer — PostToolUse hook for search index updates.

Event: PostToolUse
Purpose: Re-index files in .claude/ when they are written or edited.

Exit codes:
    0 - Allow (success)
    1 - Block (with error message to stderr)

Input (stdin): JSON with tool_name, tool_input, etc.
Output (stdout): JSON with indexing result.
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

# Module-level optional imports — done once at hook startup, not on every PostToolUse call.
# Graceful degradation: if these packages are absent the indexer skips silently.
try:
    from search_api import SearchIndexer as _SearchIndexer  # type: ignore[import]

    _SEARCH_API_AVAILABLE = True
except ImportError:
    _SearchIndexer = None  # type: ignore[assignment]
    _SEARCH_API_AVAILABLE = False

try:
    from index_event_bus import IndexEventBus as _IndexEventBus  # type: ignore[import]

    _INDEX_EVENT_BUS_AVAILABLE = True
except ImportError:
    _IndexEventBus = None  # type: ignore[assignment]
    _INDEX_EVENT_BUS_AVAILABLE = False

# Tools that modify files — frozenset for O(1) lookup
FILE_MODIFY_TOOLS = frozenset({"Write", "Edit", "MultiEdit"})

# Default paths
DEFAULT_INDEX_DIR = Path(".claude/data/search_index")
DEFAULT_CLAUDE_ROOT = Path(".claude")


def _is_in_indexed_root(file_path: Path, project_root: Path) -> bool:
    """Check whether file_path resides under any of the INDEX_ROOTS.

    Args:
        file_path: Absolute or relative path to the file.
        project_root: Root of the project (parent of .claude/).

    Returns:
        True if file_path is under a root covered by INDEX_ROOTS.
    """
    try:
        from search_api import INDEX_ROOTS  # type: ignore[import]

        abs_file = file_path.resolve()
        abs_project = project_root.resolve()
        for root_rel, _exts, _skip in INDEX_ROOTS:
            root_abs = (abs_project / root_rel).resolve()
            try:
                abs_file.relative_to(root_abs)
                return True
            except ValueError:
                continue
    except Exception:
        pass
    return False


def process_tool_event(
    event: dict[str, Any],
    index_dir: Path | None = None,
    claude_root: Path | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Process a PostToolUse event and update index if needed.

    Supports multi-root indexing: files in scripts/, packages/, backend/,
    frontend/, and .claude/ are all eligible for incremental re-indexing.

    Args:
        event: Tool event dict with tool_name and tool_input.
        index_dir: Directory for the Tantivy index.
        claude_root: Root of the .claude/ directory.
        project_root: Project root (parent of .claude/). Used for multi-root
            INDEX_ROOTS lookup. Defaults to claude_root.parent if available,
            otherwise cwd.

    Returns:
        Dict with action ('indexed' or 'skipped') and details.
    """
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    # Skip irrelevant tools
    if tool_name not in FILE_MODIFY_TOOLS:
        return {"action": "skipped", "reason": f"tool {tool_name} not tracked"}

    # Get file path from tool input
    file_path_str = tool_input.get("file_path", "")
    if not file_path_str:
        return {"action": "skipped", "reason": "no file_path in tool_input"}

    file_path = Path(file_path_str)
    root = claude_root or DEFAULT_CLAUDE_ROOT

    # Resolve project root (used for multi-root check and rel_path computation)
    proj_root = project_root or root.parent

    # Check 1: file is inside .claude/
    in_claude = False
    try:
        file_path.relative_to(root)
        in_claude = True
    except ValueError:
        try:
            abs_root = root.resolve()
            abs_file = file_path.resolve()
            abs_file.relative_to(abs_root)
            in_claude = True
        except (ValueError, OSError):
            pass

    # Check 2: file is under any indexed root (scripts/, packages/, etc.)
    in_indexed_root = in_claude or _is_in_indexed_root(file_path, proj_root)

    if not in_indexed_root:
        return {
            "action": "skipped",
            "reason": f"{file_path} not in any indexed root",
        }

    # Compute relative path for indexer (relative to project root)
    try:
        rel_path = str(file_path.relative_to(proj_root))
    except ValueError:
        try:
            abs_proj = proj_root.resolve()
            abs_file = file_path.resolve()
            rel_path = str(abs_file.relative_to(abs_proj))
        except (ValueError, OSError):
            return {
                "action": "skipped",
                "reason": f"cannot compute relative path for {file_path}",
            }

    # Perform incremental update
    idx_dir = index_dir or DEFAULT_INDEX_DIR

    if _SearchIndexer is None:
        return {"action": "skipped", "reason": "search_api not available"}

    indexer = _SearchIndexer(index_dir=idx_dir)
    indexer._claude_root = root

    updated = indexer.incremental_update(rel_path)
    logger.info("Incremental index update: %s", rel_path)

    # Emit IndexUpdated event (graceful degradation if bus unavailable)
    if _IndexEventBus is not None:
        try:
            bus = _IndexEventBus.get_instance()
            bus.emit(
                "IndexUpdated",
                {"path": rel_path, "action": "update" if updated else "skip"},
            )
        except Exception as exc:
            logger.debug("IndexEventBus unavailable — skipping event emit: %s", exc)

    return {"action": "indexed", "path": rel_path}


def main() -> None:
    """Entry point for PostToolUse hook."""
    try:
        # Read stdin
        try:
            event = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError):
            event = {}

        result = process_tool_event(event)

        # Output result as JSON
        json.dump(
            {"hook": "incremental_indexer", **result},
            sys.stdout,
        )
        sys.exit(ALLOW)

    except Exception as exc:
        print(f"Incremental indexer error: {exc}", file=sys.stderr)
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
