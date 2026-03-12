#!/usr/bin/env python3
"""PostToolUse Hook: RLM Execution Capture.

Captures Task tool completions and stores metadata in RLM Memory
for pattern matching and workflow recommendations.
Graceful degradation: never blocks tool execution.

Hook Type: PostToolUse
Timeout: 3000ms
Exit codes: 0 (allow), 1 (block with error)
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

ALLOW = 0
BLOCK = 1

RLM_AVAILABLE = False
rlm_memory = None
try:
    hooks_utils_dir = Path(__file__).parent.parent / "utils"
    if str(hooks_utils_dir) not in sys.path:
        sys.path.insert(0, str(hooks_utils_dir))

    from rlm_memory_bridge import rlm_memory as _rlm_memory

    rlm_memory = _rlm_memory
    RLM_AVAILABLE = True
except ImportError as e:
    logger.debug(f"RLM Memory not available: {e}")


@dataclass(frozen=True)
class HookInput:
    """Parsed input from Claude Code PostToolUse event."""

    tool_name: str
    tool_input: dict[str, Any]
    tool_result: dict[str, Any]
    session_id: str

    @classmethod
    def from_stdin(cls) -> HookInput:
        """Parse JSON from stdin."""
        try:
            data = json.load(sys.stdin)
            return cls(
                tool_name=data.get("tool_name", ""),
                tool_input=data.get("tool_input", {}),
                tool_result=data.get("tool_result", {}),
                session_id=data.get("session_id", ""),
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON input: {e}")
            raise ValueError(f"Invalid JSON input: {e}") from e


@dataclass(frozen=True)
class HookResult:
    """Hook execution result."""

    exit_code: int
    message: str = ""

    def emit(self) -> None:
        """Emit result and exit."""
        if self.message:
            print(self.message, file=sys.stderr)
        sys.exit(self.exit_code)


RELEVANT_SUBAGENTS = frozenset(
    {
        "antt-reequilibrio-analyzer",
        "antt-vote-drafter",
        "voto-antt-elaborador",
        "antt-rag-intelligence",
        "claude-code-meta-orchestrator",
    }
)

ANTT_SKILL_PATTERNS = (
    "antt-",
    "vote-",
    "voto-",
    "process-orchestrator",
    "legal-analyzer",
    "technical-analyzer",
)


def is_relevant_execution(hook_input: HookInput) -> bool:
    """Check if this Task execution should be captured."""
    if hook_input.tool_name != "Task":
        return False

    subagent_type = hook_input.tool_input.get("subagent_type", "")
    if subagent_type in RELEVANT_SUBAGENTS:
        return True

    return any(pattern in subagent_type.lower() for pattern in ANTT_SKILL_PATTERNS)


def extract_execution_metadata(hook_input: HookInput) -> dict[str, Any]:
    """Extract execution metadata from hook input."""
    tool_input = hook_input.tool_input
    tool_result = hook_input.tool_result

    content_hash = hashlib.sha256(json.dumps(tool_input, sort_keys=True).encode()).hexdigest()[:12]
    execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{content_hash}"

    subagent_type = tool_input.get("subagent_type", "unknown")
    description = tool_input.get("description", "")
    prompt = tool_input.get("prompt", "")

    result_text = str(tool_result.get("result", ""))
    success = "error" not in result_text.lower()

    return {
        "execution_id": execution_id,
        "workflow": subagent_type,
        "task_description": description or prompt[:200],
        "success": success,
        "quality_score": 0.85 if success else 0.3,
        "execution_time": 0.0,
        "skills_used": [subagent_type] if subagent_type != "unknown" else [],
        "key_learnings": [],
        "session_id": hook_input.session_id,
    }


def capture_execution(hook_input: HookInput) -> bool:
    """Capture execution and store in RLM Memory."""
    if not RLM_AVAILABLE or rlm_memory is None:
        logger.debug("RLM Memory not available, skipping capture")
        return False

    try:
        metadata = extract_execution_metadata(hook_input)

        # Pass metadata directly, excluding session_id (not a store_execution param)
        store_params = {k: v for k, v in metadata.items() if k != "session_id"}
        success = rlm_memory.store_execution(**store_params, tier="project")

        if success:
            logger.info(f"[RLM] Captured execution: {metadata['execution_id']} ({metadata['workflow']})")
        return success

    except Exception as e:
        logger.warning(f"[RLM] Capture failed: {e}")
        return False


def main() -> None:
    """PostToolUse hook entry point."""
    try:
        hook_input = HookInput.from_stdin()

        if not is_relevant_execution(hook_input):
            HookResult(ALLOW).emit()
            return  # emit() calls sys.exit, but return for clarity

        captured = capture_execution(hook_input)
        if captured:
            subagent = hook_input.tool_input.get("subagent_type", "unknown")
            HookResult(ALLOW, f"[RLM] Execution captured: {subagent}").emit()
        else:
            HookResult(ALLOW).emit()

    except Exception as e:
        logger.error(f"RLM capture hook error: {e}")
        HookResult(ALLOW).emit()


if __name__ == "__main__":
    main()
