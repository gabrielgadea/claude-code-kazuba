"""PreToolUse hook: 3-tier knowledge injection.

Provides relevant context based on the tool being used:
- Tier 1: Local cache (L0Cache, instant lookup)
- Tier 2: Project docs (CLAUDE.md, README, etc.)
- Tier 3: External search (deferred hint to use search tools)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from claude_code_kazuba.hook_base import fail_open
from claude_code_kazuba.json_output import emit_json, pre_tool_use_output
from claude_code_kazuba.performance import L0Cache

# Knowledge cache (Tier 1)
_knowledge_cache: L0Cache[str] = L0Cache(max_size=200, ttl_seconds=300.0)

# Project doc filenames to scan (Tier 2)
PROJECT_DOC_FILES: list[str] = [
    "CLAUDE.md",
    ".claude/CLAUDE.md",
    "README.md",
    "CONTRIBUTING.md",
    "docs/ARCHITECTURE.md",
]

# Max bytes to read from project docs
MAX_DOC_BYTES: int = 2000


@dataclass(frozen=True)
class KnowledgeEntry:
    """A piece of knowledge from any tier."""

    tier: int
    source: str
    content: str


def tier1_cache_lookup(tool_name: str, file_path: str) -> str | None:
    """Tier 1: Check local cache for relevant knowledge.

    Args:
        tool_name: The tool being used.
        file_path: Target file path (if applicable).

    Returns:
        Cached knowledge string or None.
    """
    cache_key = f"{tool_name}:{file_path}"
    return _knowledge_cache.get(cache_key)


def tier2_project_docs(cwd: str) -> list[KnowledgeEntry]:
    """Tier 2: Read project documentation files.

    Args:
        cwd: Current working directory.

    Returns:
        List of KnowledgeEntry from project docs.
    """
    entries: list[KnowledgeEntry] = []
    cwd_path = Path(cwd)

    for doc_name in PROJECT_DOC_FILES:
        doc_path = cwd_path / doc_name
        if doc_path.is_file():
            try:
                content = doc_path.read_text(encoding="utf-8")[:MAX_DOC_BYTES]
                entries.append(
                    KnowledgeEntry(
                        tier=2,
                        source=doc_name,
                        content=content,
                    )
                )
            except (OSError, UnicodeDecodeError):
                continue
    return entries


def tier3_external_hint(tool_name: str) -> str:
    """Tier 3: Provide a hint to use external search tools.

    Args:
        tool_name: The tool being used.

    Returns:
        A hint string suggesting external knowledge lookup.
    """
    return (
        f"[knowledge-manager] No cached knowledge for {tool_name}. "
        "Consider using WebSearch or Context7 for external documentation."
    )


def build_knowledge_context(
    tool_name: str,
    file_path: str,
    cwd: str,
) -> str | None:
    """Build knowledge context from all 3 tiers.

    Args:
        tool_name: The tool being invoked.
        file_path: Target file path (if applicable).
        cwd: Current working directory.

    Returns:
        Knowledge context string, or None if nothing relevant found.
    """
    # Tier 1: Cache
    cached = tier1_cache_lookup(tool_name, file_path)
    if cached is not None:
        return f"[knowledge-manager] (cached) {cached}"

    # Tier 2: Project docs — only inject for Read/Write/Edit tools
    if tool_name in ("Read", "Write", "Edit", "Grep", "Glob"):
        docs = tier2_project_docs(cwd)
        if docs:
            # Cache for next time
            summary = f"Project has {len(docs)} doc(s): {', '.join(d.source for d in docs)}"
            cache_key = f"{tool_name}:{file_path}"
            _knowledge_cache.set(cache_key, summary)
            return f"[knowledge-manager] {summary}"

    # Tier 3: External hint — only for complex tools
    if tool_name in ("WebSearch", "WebFetch"):
        return tier3_external_hint(tool_name)

    return None


@fail_open
def main() -> None:
    """Main hook entry point: read stdin, inject knowledge context."""
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    data: dict[str, Any] = json.loads(raw)
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    cwd = data.get("cwd", os.getcwd())

    file_path: str = tool_input.get("file_path", "")

    context = build_knowledge_context(tool_name, file_path, cwd)

    if context is None:
        sys.exit(0)

    # Output as informational (allow, with context in reason)
    output = pre_tool_use_output("allow", context)
    emit_json(output)


if __name__ == "__main__":
    main()
