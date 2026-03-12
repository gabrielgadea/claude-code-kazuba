#!/usr/bin/env python3
"""PRP Complexity Router Hook.

Routes PRP (Planning/Research/Production) tasks to appropriate phase count
based on complexity analysis. This hook is triggered for Task tool calls
with PRP-related patterns.

Hook Type: PreToolUse
Matcher: Task.*PRP.*|Task.*plan.*|Task.*spec.*
Input: JSON via stdin with tool_input containing task description
Output: JSON with routing decision and phase recommendation

Exit Codes:
    0 - Success, continue with routing decision
    1 - Error during processing
    2 - Block (not used for routing, only for blocking)

Usage:
    Configured in .claude/settings.local.json as PreToolUse hook.
    Receives task description and outputs recommended phase count.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add project root to path for imports — consolidated single insert
_project_root = Path(__file__).parent.parent.parent.parent
_hooks_dir = str(_project_root / ".claude" / "hooks")
_planning_dir = str(_project_root / ".claude" / "hooks" / "planning")
if _planning_dir not in sys.path:
    sys.path.insert(0, _planning_dir)
if _hooks_dir not in sys.path:
    sys.path.insert(0, _hooks_dir)

logger = logging.getLogger(__name__)


@dataclass
class RouterConfig:
    """Configuration for PRP complexity routing."""

    simple_threshold: int = 20
    standard_threshold: int = 50
    enable_rust_acceleration: bool = True
    log_level: str = "INFO"


@dataclass
class RoutingResult:
    """Result of complexity routing analysis."""

    task_description: str
    complexity_score: float
    complexity_level: str
    recommended_phases: int
    confidence: float
    factors: dict[str, Any]
    routing_decision: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "task_description": self.task_description[:100] + "..."
            if len(self.task_description) > 100
            else self.task_description,
            "complexity_score": self.complexity_score,
            "complexity_level": self.complexity_level,
            "recommended_phases": self.recommended_phases,
            "confidence": self.confidence,
            "factors": self.factors,
            "routing_decision": self.routing_decision,
        }


class PRPComplexityRouter:
    """Routes PRP tasks based on complexity analysis.

    Integrates with ComplexityScorer for scoring and provides
    routing decisions for the task orchestration system.
    """

    def __init__(self, config: RouterConfig | None = None) -> None:
        """Initialize router with optional configuration."""
        self._config = config or RouterConfig()
        self._scorer: Any = None
        self._initialize_scorer()

    def _initialize_scorer(self) -> None:
        """Initialize ComplexityScorer if available."""
        try:
            # Try direct import first (when running from hooks directory)
            from complexity_scorer import ComplexityScorer

            self._scorer = ComplexityScorer()
            logger.info("PRPComplexityRouter: ComplexityScorer initialized")
        except ImportError:
            try:
                # Try with planning prefix
                from planning.complexity_scorer import ComplexityScorer

                self._scorer = ComplexityScorer()
                logger.info("PRPComplexityRouter: ComplexityScorer initialized (planning.)")
            except ImportError:
                logger.warning("PRPComplexityRouter: ComplexityScorer not available, using fallback")
                self._scorer = None

    def route(self, task_description: str) -> RoutingResult:
        """Analyze task and determine routing.

        Args:
            task_description: Description of the task to analyze

        Returns:
            RoutingResult with complexity analysis and routing decision
        """
        if self._scorer is not None:
            try:
                result = self._scorer.calculate(
                    task_description=task_description,
                    files_affected=self._estimate_files(task_description),
                    lines_estimate=self._estimate_lines(task_description),
                    external_dependencies=self._estimate_deps(task_description),
                )
                return RoutingResult(
                    task_description=task_description,
                    complexity_score=result.score,
                    complexity_level=result.level,
                    recommended_phases=result.recommended_phases,
                    confidence=result.confidence,
                    factors=result.breakdown,
                    routing_decision=self._determine_routing(result.level),
                )
            except Exception as e:
                logger.warning(f"ComplexityScorer error: {e}, using fallback")

        # Fallback scoring
        return self._fallback_route(task_description)

    def _fallback_route(self, task_description: str) -> RoutingResult:
        """Fallback routing when ComplexityScorer unavailable."""
        description_lower = task_description.lower()

        # Simple keyword-based scoring
        score = 0.0
        factors: dict[str, Any] = {}

        # Check complexity indicators
        high_indicators = [
            "architecture",
            "refactor",
            "migration",
            "integration",
            "full pipeline",
            "complex",
            "8 phases",
        ]
        medium_indicators = [
            "feature",
            "enhance",
            "extend",
            "optimize",
            "implement",
            "add",
        ]
        low_indicators = ["fix", "bug", "typo", "minor", "simple", "quick", "document"]

        for indicator in high_indicators:
            if indicator in description_lower:
                score += 15
                factors[indicator] = 15

        for indicator in medium_indicators:
            if indicator in description_lower:
                score += 7
                factors[indicator] = 7

        for indicator in low_indicators:
            if indicator in description_lower:
                score += 2
                factors[indicator] = 2

        # Determine level and phases
        if score < self._config.simple_threshold:
            level = "simple"
            phases = 3
        elif score < self._config.standard_threshold:
            level = "standard"
            phases = 5
        else:
            level = "complex"
            phases = 8

        return RoutingResult(
            task_description=task_description,
            complexity_score=score,
            complexity_level=level,
            recommended_phases=phases,
            confidence=0.6,  # Lower confidence for fallback
            factors=factors,
            routing_decision=self._determine_routing(level),
        )

    def _determine_routing(self, level: str) -> str:
        """Determine routing decision based on complexity level."""
        routing_map = {
            "simple": "quick_spec",
            "standard": "standard_prp",
            "complex": "full_prp_pipeline",
        }
        return routing_map.get(level, "standard_prp")

    def _estimate_files(self, description: str) -> int:
        """Estimate files affected from description."""
        description_lower = description.lower()
        if any(word in description_lower for word in ["all", "entire", "full", "codebase"]):
            return 10
        if any(word in description_lower for word in ["multiple", "several", "many"]):
            return 5
        if any(word in description_lower for word in ["single", "one", "this"]):
            return 1
        return 3  # Default moderate estimate

    def _estimate_lines(self, description: str) -> int:
        """Estimate lines of code from description."""
        description_lower = description.lower()
        if any(word in description_lower for word in ["major", "large", "extensive", "complete"]):
            return 500
        if any(word in description_lower for word in ["minor", "small", "quick", "simple"]):
            return 50
        return 200  # Default moderate estimate

    def _estimate_deps(self, description: str) -> int:
        """Estimate external dependencies from description."""
        description_lower = description.lower()
        dep_keywords = [
            "api",
            "external",
            "integration",
            "third-party",
            "mcp",
            "database",
            "service",
        ]
        count = sum(1 for kw in dep_keywords if kw in description_lower)
        return min(count, 5)


def process_hook_input() -> dict[str, Any]:
    """Process JSON input from stdin.

    Returns:
        Parsed JSON dictionary from stdin
    """
    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            return {}
        return json.loads(input_data)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON input: {e}")
        return {}


def main() -> int:
    """Main entry point for hook execution.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    try:
        # Read input from stdin
        input_data = process_hook_input()

        # Extract task description from tool input
        tool_input = input_data.get("tool_input", {})
        prompt = tool_input.get("prompt", "")
        description = tool_input.get("description", prompt)
        subagent_type = tool_input.get("subagent_type", "")

        # Combine available information
        task_description = f"{description} {subagent_type}".strip()

        if not task_description:
            # No task description, pass through
            output = {
                "continue": True,
                "message": "PRP Router: No task description provided",
            }
            print(json.dumps(output))
            return 0

        # Route the task
        router = PRPComplexityRouter()
        result = router.route(task_description)

        # Output routing decision
        output = {
            "continue": True,
            "routing": result.to_dict(),
            "message": (
                f"PRP Router: {result.complexity_level} task "
                f"({result.recommended_phases} phases, "
                f"score={result.complexity_score:.1f})"
            ),
        }
        print(json.dumps(output, indent=2))
        return 0

    except Exception as e:
        logger.error(f"PRP Router error: {e}")
        error_output = {
            "continue": True,  # Don't block on router errors
            "error": str(e),
            "message": f"PRP Router: Error during routing - {e}",
        }
        print(json.dumps(error_output))
        return 1


if __name__ == "__main__":
    sys.exit(main())
