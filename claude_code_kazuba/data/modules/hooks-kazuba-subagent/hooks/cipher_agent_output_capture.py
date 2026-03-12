#!/usr/bin/env python3
"""SubagentStop Hook: Cipher Agent Output Capture.

Captures Task tool (sub-agent) output for knowledge storage in Cipher MCP
and local cache.

Hook Type: SubagentStop
Execution: After each Task tool execution
Timeout: 5000ms
Integration: Cipher MCP + Local storage

Architecture:
- TIER 1: Store in local cache (.cipher/agent_outputs/)
- TIER 2: Store in Cipher MCP (if available)
- TIER 3: Graceful degradation (local-only mode)

Context7 Best Practices Applied:
- Modern type hints (Path | None, dict[str, Any])
- Dataclasses for structured data
- Graceful error handling
- Structured logging
- FIFO cache with max 100 agent outputs

Use Cases:
- Track sub-agent performance
- Learn from agent execution patterns
- Build knowledge base from agent insights
- Enable cross-agent knowledge sharing

Output Format (Anthropic-Compliant Schema):
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStop",
    "additionalContext": "Agent output captured: task_20251106_152000"
  },
  "suppressOutput": true
}
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


# ============================================================================
# Anthropic-Compliant Output Format (SubagentStop)
# ============================================================================


def format_subagent_output(context: str = "", suppress: bool = True) -> str:
    """Format output for SubagentStop hooks according to Anthropic schema.

    Args:
        context: Additional context for Claude
        suppress: Whether to suppress output in transcript

    Returns:
        JSON string with correct Anthropic schema format
    """
    output = {
        "hookSpecificOutput": {"hookEventName": "SubagentStop", "additionalContext": context},
        "suppressOutput": suppress,
    }
    return json.dumps(output, ensure_ascii=False)


# ============================================================================
# Data Models (Context7 Best Practice: Dataclasses)
# ============================================================================


@dataclass
class AgentOutput:
    """Captured output from a sub-agent execution.

    Attributes:
        agent_id: Unique agent execution identifier
        agent_type: Type of agent (Explore, Plan, code-reviewer, etc.)
        timestamp: ISO format timestamp
        execution_time_seconds: Execution time in seconds
        success: Whether agent execution succeeded
        output_text: Agent output text (first 1000 chars)
        insights: List of extracted insights
        error: Error message if failed
    """

    agent_id: str
    agent_type: str
    timestamp: str
    execution_time_seconds: float
    success: bool
    output_text: str = ""
    insights: list[str] = field(default_factory=list)
    error: str | None = None


# ============================================================================
# Agent Output Capture
# ============================================================================


# Pre-computed at module level — avoid per-call list creation
_INSIGHT_KEYWORDS = ("Found", "Discovered", "Identified", "Located")


class AgentOutputCapture:
    """Capture and store sub-agent outputs.

    Implements 3-Tier hybrid architecture:
    - TIER 1: Local cache (instant, 0 tokens)
    - TIER 2: Cipher MCP (semantic storage, ~300 tokens)
    - TIER 3: Graceful degradation (always works)
    """

    def __init__(self) -> None:
        """Initialize agent output capture."""
        self.cache_dir = Path.cwd() / ".cipher" / "agent_outputs"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.cache_dir / "agent_outputs.json"
        self.max_entries = 100  # FIFO cache limit

        self.logger = logging.getLogger(__name__)

    def capture(
        self,
        agent_type: str,
        agent_output: str,
        execution_time: float,
        success: bool = True,
        error: str | None = None,
    ) -> AgentOutput:
        """Capture agent output.

        Args:
            agent_type: Type of agent
            agent_output: Agent output text
            execution_time: Execution time in seconds
            success: Whether execution succeeded
            error: Error message if failed

        Returns:
            AgentOutput object
        """
        try:
            # Generate agent ID
            agent_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Extract insights (simple pattern matching)
            insights = self._extract_insights(agent_output)

            # Create agent output object
            output = AgentOutput(
                agent_id=agent_id,
                agent_type=agent_type,
                timestamp=datetime.now().isoformat(),
                execution_time_seconds=execution_time,
                success=success,
                output_text=agent_output[:1000],  # Limit to 1000 chars
                insights=insights,
                error=error,
            )

            # TIER 1: Store in local cache
            self._store_local(output)

            # TIER 2: Store in Cipher MCP (if available)
            # Note: MCP tools not available in subprocess context
            self.logger.debug(f"Cipher MCP storage available at orchestrator level for agent {agent_id}")

            return output

        except Exception as e:
            self.logger.error(f"Error capturing agent output: {e}", exc_info=True)
            # TIER 3: Return empty output on error
            return AgentOutput(
                agent_id="error",
                agent_type=agent_type,
                timestamp=datetime.now().isoformat(),
                execution_time_seconds=execution_time,
                success=False,
                error=str(e),
            )

    def _extract_insights(self, output_text: str) -> list[str]:
        """Extract insights from agent output.

        Args:
            output_text: Agent output text

        Returns:
            List of extracted insights
        """
        insights = []

        try:
            lines = output_text.split("\n")

            # Pattern 1: Lines starting with "✅"
            insights.extend(line.strip() for line in lines if line.strip().startswith("✅"))

            # Pattern 2: Lines with insight keywords (module-level tuple)
            insights.extend(line.strip() for line in lines if any(keyword in line for keyword in _INSIGHT_KEYWORDS))

            # Limit to 10 insights
            return insights[:10]

        except Exception as e:
            self.logger.debug(f"Error extracting insights: {e}")
            return []

    def _store_local(self, output: AgentOutput) -> bool:
        """Store agent output in local cache.

        Args:
            output: AgentOutput object

        Returns:
            True if stored successfully
        """
        try:
            # Load existing outputs
            outputs: list[dict[str, Any]] = []
            if self.cache_file.exists():
                with open(self.cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                    outputs = data.get("agent_outputs", [])

            # Add new output
            outputs.append(asdict(output))

            # Keep only last N entries (FIFO)
            if len(outputs) > self.max_entries:
                outputs = sorted(
                    outputs,
                    key=lambda x: x.get("timestamp", ""),
                    reverse=True,
                )[: self.max_entries]

            # Save back to file
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"agent_outputs": outputs},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            self.logger.debug(f"Stored agent output: {output.agent_id}")
            return True

        except Exception as e:
            self.logger.warning(f"Error storing agent output locally: {e}")
            return False


# ============================================================================
# Hook Entry Point
# ============================================================================


def main() -> None:
    """SubagentStop hook entry point.

    Captures agent output and outputs results in hook format.
    """
    try:
        # Read hook data from stdin (Claude Code protocol)
        # SubagentStop stdin: {subagent_type, output, execution_time_seconds, success}
        try:
            data = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError):
            data = {}

        agent_type = data.get("subagent_type", "unknown")
        execution_time = float(data.get("execution_time_seconds", 0.0))
        success = bool(data.get("success", True))
        # output is provided directly in stdin (not via file)
        agent_output = str(data.get("output", ""))

        # Capture output
        capture = AgentOutputCapture()
        output = capture.capture(
            agent_type=agent_type,
            agent_output=agent_output,
            execution_time=execution_time,
            success=success,
        )

        # Build output message
        message_parts = ["Agent output captured"]

        if output.insights:
            message_parts.append(f"({len(output.insights)} insights)")

        if not success:
            message_parts.append("(execution failed)")

        # Output hook result in Anthropic-compliant format
        context = " - ".join(message_parts) + f" ({output.agent_type}: {output.agent_id})"
        print(format_subagent_output(context))

    except Exception as e:
        # TIER 3: Graceful degradation - always allow
        logger.error(f"Agent output capture hook failed: {e}", exc_info=True)
        context = f"Agent output capture hook failed (continuing): {e}"
        print(format_subagent_output(context))


if __name__ == "__main__":
    main()
