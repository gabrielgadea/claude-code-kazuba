#!/usr/bin/env python3
"""Hook: Transcript Analysis on Session Stop.

Event: Stop
Purpose: Analyze session transcript to extract pending items, user corrections,
         and tool patterns. Saves pending items as guidance for next session.

Exit codes:
  0 - Allow (always allows, this is informational)

Input (stdin): JSON with session_id, transcript_path, etc.
Output (stderr): Summary of what was captured.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Exit codes
ALLOW = 0

logger = logging.getLogger(__name__)

# Project root (4 levels up from this file)
PROJECT_ROOT = Path(__file__).parents[4]

# Add .claude directory to path so "hooks.learning..." imports work
# Note: directory is ".claude" (with dot), not importable as "claude"
_CLAUDE_DIR = PROJECT_ROOT / ".claude"
sys.path.insert(0, str(_CLAUDE_DIR))


def main() -> None:
    """Entry point for Stop hook."""
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        data = {}

    transcript_path = data.get("transcript_path", "")
    session_id = data.get("session_id", "")

    if not transcript_path or not Path(transcript_path).exists():
        # No transcript available, silently exit
        sys.exit(ALLOW)

    try:
        from hooks.learning.guidance.guidance_manager import (
            GuidanceManager,
        )
        from hooks.learning.transcript.transcript_analyzer import (
            TranscriptAnalyzer,
        )

        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze(transcript_path)

        # Save pending items as guidance for next session
        guidance = GuidanceManager(project_dir=PROJECT_ROOT)

        for item in result.pending_items[:5]:  # Top 5 pending items
            priority = "high" if item.source == "tool_error" else "normal"
            guidance.add(
                message=item.description,
                priority=priority,
                category="pending_work",
                source_session=session_id,
            )

        # Save user corrections as preference guidance
        for correction in result.user_corrections[:3]:
            guidance.add(
                message=f"User preference: {correction.user_message}",
                priority="normal",
                category="preference",
                source_session=session_id,
            )

        # Generate session slug
        from hooks.learning.transcript.transcript_analyzer import (
            generate_session_slug,
        )

        slug = generate_session_slug(result)
        print(f"[transcript] Session slug: {slug}", file=sys.stderr)

        # Keep last N session summaries (preserve history, evict oldest)
        MAX_SESSION_SUMMARIES = 5
        all_entries = guidance.get_all()
        old_summaries = sorted(
            [e for e in all_entries if e.category == "session_summary"],
            key=lambda e: e.created_at,
            reverse=True,
        )
        # Remove excess summaries (keep MAX-1 to make room for the new one)
        for old_entry in old_summaries[MAX_SESSION_SUMMARIES - 1 :]:
            guidance.remove(old_entry.id)

        # Also remove old pending_work and preference entries (delivered)
        for old_entry in all_entries:
            if old_entry.delivered and old_entry.category in (
                "pending_work",
                "preference",
            ):
                guidance.remove(old_entry.id)

        # Build rich session summary for next session greeting
        summary_parts = [f"Sessão anterior ({slug}):"]
        if result.pending_items:
            summary_parts.append("Itens pendentes:")
            summary_parts.extend(f"  - {item.description[:200]}" for item in result.pending_items[:5])
        if result.user_corrections:
            summary_parts.append("Correções do usuário:")
            summary_parts.extend(f"  - {c.user_message[:200]}" for c in result.user_corrections[:3])
        top_tools = sorted(
            result.tool_patterns.items(),
            key=lambda x: x[1].call_count,
            reverse=True,
        )[:5]
        if top_tools:
            tool_summary = ", ".join(f"{name}({s.call_count}x)" for name, s in top_tools)
            summary_parts.append(f"Ferramentas mais usadas: {tool_summary}")
        summary_parts.append(f"Total: {result.total_messages} mensagens, {result.total_tool_calls} tool calls")

        guidance.add(
            message="\n".join(summary_parts),
            priority="high",
            category="session_summary",
            source_session=session_id,
        )

        # Summary to stderr
        parts = []
        if result.pending_items:
            parts.append(f"{len(result.pending_items)} pending items")
        if result.user_corrections:
            parts.append(f"{len(result.user_corrections)} corrections")
        if result.tool_patterns:
            error_tools = [name for name, stats in result.tool_patterns.items() if stats.error_rate > 0.5]
            if error_tools:
                parts.append(f"high-error tools: {', '.join(error_tools)}")

        if parts:
            print(
                f"Transcript analysis: {' | '.join(parts)}",
                file=sys.stderr,
            )

    except ImportError as e:
        # Dependencies not available - log to file for diagnosis
        _log_to_file(f"Transcript hook skipped (import error): {e}")
    except Exception as e:
        # Never block session end - but log for diagnosis
        _log_to_file(f"Transcript hook error: {e}")

    sys.exit(ALLOW)


def _log_to_file(message: str) -> None:
    """Log errors to file for cross-session diagnosis."""
    try:
        log_dir = PROJECT_ROOT / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "transcript_hook_errors.log"
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Truly last resort - cannot even log


if __name__ == "__main__":
    main()
