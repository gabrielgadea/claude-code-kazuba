#!/usr/bin/env python3
"""PreToolUse hook for Serena operations - PLN2 with HookLogger.

This hook runs BEFORE Serena symbolic operations to:
1. Retrieve symbol context for the target file
2. Log operation metadata for observability
3. Provide context hints to Claude

Matcher: mcp__plugin_serena_serena__(replace_symbol_body|insert_after_symbol|...)
Decision: Always 'allow' (informational hook, never blocks)
Timeout: 5s

Exit Codes:
    0: Success
    1: Error (still outputs valid JSON with allow decision)

Environment Variables:
    CLAUDE_PROJECT_DIR: Project root directory
    CLAUDE_TOOL_NAME: Name of tool being called
    CLAUDE_TOOL_INPUT: JSON string of tool parameters
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger(__name__)

# Add hooks directory to path for imports
PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", ".")
sys.path.insert(0, str(Path(PROJECT_DIR) / ".claude" / "hooks"))

# ─── L0 PRE-IMPORT CACHE (stdlib-only, ~2ms) ──────────────────────────────
import contextlib  # noqa: E402
import hashlib as _hlib_scr  # noqa: E402

_scr_stdin: dict = {}
try:
    import sys as _sys_scr

    _scr_stdin = __import__("json").loads(_sys_scr.stdin.read())
except Exception:
    pass

_scr_tool: str = _scr_stdin.get("tool_name", "")
_scr_ti: dict = _scr_stdin.get("tool_input", {})
_scr_rpath: str = _scr_ti.get("relative_path", "")

# Determine cache TTL and key
_SERENA_FILE_OPS_L0 = frozenset(
    {
        "mcp__plugin_serena_serena__replace_symbol_body",
        "mcp__plugin_serena_serena__insert_after_symbol",
        "mcp__plugin_serena_serena__insert_before_symbol",
        "mcp__plugin_serena_serena__rename_symbol",
        "mcp__plugin_serena_serena__create_text_file",
        "mcp__plugin_serena_serena__replace_content",
    }
)

if _scr_tool not in _SERENA_FILE_OPS_L0:
    # Non-Serena tool: fast path with 300s TTL
    _scr_ck = _hlib_scr.sha256(_scr_tool.encode()).hexdigest()[:16]
    _scr_ttl = 300
else:
    # Serena file op: cache on tool+path with 60s TTL (symbol context changes)
    _scr_ck = _hlib_scr.sha256(f"{_scr_tool}|{_scr_rpath}".encode()).hexdigest()[:16]
    _scr_ttl = 60

_scr_cp = __import__("pathlib").Path(f"/tmp/antt-scr-allow-{_scr_ck}.json")
if _scr_cp.exists():
    import time as _tm_scr

    if (_tm_scr.time() - _scr_cp.stat().st_mtime) < _scr_ttl:
        _cached_scr = _scr_cp.read_text().strip()
        if _cached_scr:
            import sys as _sys_scr2

            _sys_scr2.stdout.write(_cached_scr + "\n")
            _sys_scr2.exit(0)  # L0 cache hit — saves ~65ms (serena import)
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    """Main hook entry point."""
    start_time = time.perf_counter()

    # stdin already consumed at module level by L0 pre-import cache
    data = _scr_stdin

    tool_name = data.get("tool_name", "")

    # Define which Serena tools trigger this hook
    # Reuse module-level set from L0 cache section

    # Skip if not a relevant Serena tool
    if tool_name not in _SERENA_FILE_OPS_L0:
        _output_result("allow", "Not a Serena file operation")
        return

    try:
        # Import SerenaIntegrationService
        from serena.serena_bridge import SerenaIntegrationService

        # Parse tool input from stdin data
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("relative_path", "")

        if file_path:
            # Get symbol context for the file
            service = SerenaIntegrationService()
            context = service.get_symbol_context(file_path)

            classes = context.get_classes()
            functions = context.get_functions()

            message = (
                f"[Serena] Context retrieved: {context.symbol_count} symbols | "
                f"{len(classes)} classes | {len(functions)} functions"
            )

            # Log operation for observability
            _log_operation(
                "serena_context_retrieval",
                "allow",
                {
                    "file": file_path,
                    "symbols": context.symbol_count,
                    "classes": len(classes),
                    "functions": len(functions),
                    "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
                    "cache_hit_rate": (round(service._cache.metrics.hit_rate, 4) if service._cache else 0),
                },
            )

            _output_result("allow", message)
        else:
            _output_result("allow", "No file path provided")

    except ImportError as e:
        # Serena module not available - graceful fallback
        _output_result("allow", f"[Serena] Module unavailable: {e}")
        logger.debug(f"Import error: {e}")

    except json.JSONDecodeError as e:
        # Invalid JSON in tool input
        _output_result("allow", f"[Serena] JSON parse error: {e}")
        logger.debug(f"JSON error: {e}")

    except Exception as e:
        # Any other error - graceful fallback
        _output_result("allow", f"[Serena] Fallback: {e}")
        logger.debug(f"Unexpected error: {e}")


def _output_result(decision: str = "allow", reason: str = "", suppress: bool = True) -> None:
    """Output JSON result to stdout in Anthropic schema format.

    Args:
        decision: Permission decision ("allow", "deny", "ask")
        reason: Explanation for the decision
        suppress: Whether to suppress output in transcript
    """
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        },
        "suppressOutput": suppress,
    }
    out_str = json.dumps(output)
    print(out_str)

    # Cache ALLOW results for L0 fast path on next invocation
    if decision == "allow":
        with contextlib.suppress(Exception):
            _scr_cp.write_text(out_str)


def _log_operation(hook_name: str, decision: str, metadata: dict[str, Any]) -> None:
    """Log operation to JSONL file for observability.

    Args:
        hook_name: Name of the hook
        decision: Hook decision (allow/warn/block)
        metadata: Additional metadata to log
    """
    try:
        log_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "hook": hook_name,
            "decision": decision,
            **metadata,
        }

        with open(log_dir / "serena_hooks.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    except Exception as e:
        # Logging failure should not affect hook execution
        logger.debug(f"Logging failed: {e}")


if __name__ == "__main__":
    main()
