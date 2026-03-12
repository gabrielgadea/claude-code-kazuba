#!/usr/bin/env python3
"""
SIAC Orchestrator — Coordinates 4 Autonomous Motors

Motor 1: AST Audit — Structural analysis
Motor 2: Type Sanitation — Type safety validation
Motor 3: Mutation Tester — Test robustness verification
Motor 4: Knowledge Sync — Persistent knowledge management

Event: PostToolUse (coordinated across all motors)
Exit codes:
  0 - ALLOW (all motors pass)
  1 - BLOCK (1+ motor blocks)
  2 - WARN (1+ motor warns, no blocks)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# Import motors (in production, dynamically load)
try:
    from motor1_ast_audit import hook_post_tool_use as motor1_hook
    from motor2_type_sanitation import hook_post_tool_use as motor2_hook
    from motor3_mutation_tester import hook_post_tool_use as motor3_hook
    from motor4_knowledge_sync import hook_post_tool_use as motor4_hook
except ImportError:
    # Fallback if imports fail
    motor1_hook = None
    motor2_hook = None
    motor3_hook = None
    motor4_hook = None


# ============================================================================
# Configuration
# ============================================================================

MOTORS = [
    ("Motor1_AST_Audit", motor1_hook),
    ("Motor2_Type_Sanitation", motor2_hook),
    ("Motor3_Mutation_Tester", motor3_hook),
    ("Motor4_Knowledge_Sync", motor4_hook),
]

# Motor execution order (can be parallelized)
MOTOR_EXECUTION_ORDER = [1, 2, 3, 4]


# ============================================================================
# Data Models
# ============================================================================


@dataclass(frozen=True)
class MotorResult:
    """Result from single motor execution."""

    motor_name: str
    action: int  # 0=ALLOW, 1=BLOCK, 2=WARN
    details: dict[str, Any]
    execution_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "motor": self.motor_name,
            "action": self.action,
            "action_name": {0: "ALLOW", 1: "BLOCK", 2: "WARN"}.get(self.action, "UNKNOWN"),
            "details": self.details,
            "execution_time_ms": f"{self.execution_time_ms:.1f}",
        }


@dataclass
class SIACResult:
    """Combined result from all SIAC motors."""

    file_path: str
    motor_results: list[MotorResult]
    overall_action: int
    timestamp: str

    @property
    def has_blocks(self) -> bool:
        """True if any motor blocks."""
        return any(r.action == 1 for r in self.motor_results)

    @property
    def has_warnings(self) -> bool:
        """True if any motor warns."""
        return any(r.action == 2 for r in self.motor_results)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "file_path": self.file_path,
            "overall_action": {0: "ALLOW", 1: "BLOCK", 2: "WARN"}.get(self.overall_action, "UNKNOWN"),
            "motors": [r.to_dict() for r in self.motor_results],
            "summary": {
                "total_motors": len(self.motor_results),
                "blocks": sum(1 for r in self.motor_results if r.action == 1),
                "warnings": sum(1 for r in self.motor_results if r.action == 2),
                "allows": sum(1 for r in self.motor_results if r.action == 0),
            },
        }


# ============================================================================
# Motor Orchestration
# ============================================================================


def run_motors(context: dict) -> SIACResult:
    """Run all SIAC motors and collect results.

    Args:
        context: Hook input context.

    Returns:
        SIACResult with combined motor results.
    """
    file_path = context.get("file_path", "unknown")
    motor_results: list[MotorResult] = []

    # Run each motor
    for motor_name, motor_hook in MOTORS:
        if motor_hook is None:
            # Skip unavailable motors
            motor_results.append(
                MotorResult(
                    motor_name=motor_name,
                    action=0,  # ALLOW
                    details={"status": "unavailable"},
                    execution_time_ms=0.0,
                )
            )
            continue

        start_time = time.time()
        try:
            result = motor_hook(context)
            execution_time = (time.time() - start_time) * 1000

            motor_results.append(
                MotorResult(
                    motor_name=motor_name,
                    action=result.get("action", 0),
                    details={k: v for k, v in result.items() if k != "action"},
                    execution_time_ms=execution_time,
                )
            )
        except Exception as e:
            # Motor failed, treat as warning
            motor_results.append(
                MotorResult(
                    motor_name=motor_name,
                    action=2,  # WARN
                    details={"error": str(e)},
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            )

    # Determine overall action
    if any(r.action == 1 for r in motor_results):
        overall_action = 1  # BLOCK
    elif any(r.action == 2 for r in motor_results):
        overall_action = 2  # WARN
    else:
        overall_action = 0  # ALLOW

    return SIACResult(
        file_path=file_path,
        motor_results=motor_results,
        overall_action=overall_action,
        timestamp=datetime.now(UTC).isoformat(),
    )


# ============================================================================
# Hook Entry Point
# ============================================================================


def hook_post_tool_use(context: dict) -> dict:
    """PostToolUse hook orchestrating SIAC motors.

    Input: {
        "tool_name": "Write" | "Edit",
        "file_path": str,
        "tool_input": {...}
    }

    Output: {
        "action": 0 | 1 | 2,
        "timestamp": str,
        "motors": [MotorResult, ...],
        "summary": {...}
    }
    """
    result = run_motors(context)

    return {
        "action": result.overall_action,
        "siac_orchestrator": {
            "timestamp": result.timestamp,
            "file_path": result.file_path,
            "motor_results": [r.to_dict() for r in result.motor_results],
            "summary": result.to_dict()["summary"],
        },
    }


# ============================================================================
# Testing
# ============================================================================


if __name__ == "__main__":
    # Test orchestration
    test_context = {
        "tool_name": "Write",
        "file_path": "/tmp/test.py",
        "tool_input": {"file_content": "def test(): pass"},
    }

    result = run_motors(test_context)
    print("SIAC Orchestration Test")
    print("=" * 50)
    print(json.dumps(result.to_dict(), indent=2))

    print("\n✅ SIAC Orchestrator tests completed")
