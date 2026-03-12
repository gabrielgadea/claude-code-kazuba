#!/usr/bin/env python3
"""
Context Monitor - Automatic context utilization monitoring.

Events: SessionStart, UserPromptSubmit (dual-event hook)
Purpose: Monitor context utilization and trigger automatic state capture.

Rationale for dual-event design:
  - SessionStart: Critical for detecting high context after resume/restore
    (user hasn't sent a prompt yet, but context may already be elevated)
  - UserPromptSubmit: Continuous monitoring during session

Exit codes:
  0 - Allow (continue normally)
  1 - Block (with error message)

Thresholds (aligned with global CONTEXT_THRESHOLD=95):
  80% - WARNING: Background capture initiated
  90% - CRITICAL: Sync capture + strong warning
  95% - COMPACT: Sync capture + "Run /compact NOW!"
  97% - EMERGENCY: Immediate action required

Part of Plan: tranquil-booping-planet (Phase 1: Core Foundation)

Uses: token_usage_detector.py for accurate context detection
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("context_monitor")

# Exit codes
ALLOW = 0
BLOCK = 1

# Configuration
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))


class MonitorAction(StrEnum):
    """Actions the context monitor can take."""

    NORMAL = "normal"
    WARNING = "warning"  # 85% - background capture
    CRITICAL = "critical"  # 92% - sync capture + strong warning
    EMERGENCY = "emergency"  # 97% - immediate action required
    FORCE_TRANSITION = "force_transition"  # Legacy alias for CRITICAL


class AlertLevel(StrEnum):
    """Alert level for output messages."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass(frozen=True)
class MonitorConfig:
    """Configuration for context monitoring."""

    warning_threshold: float = 0.80  # 80%
    critical_threshold: float = 0.90  # 90%
    compact_threshold: float = 0.95  # 95% - aligned with global CONTEXT_THRESHOLD
    emergency_threshold: float = 0.97  # 97%
    enable_background_capture: bool = True
    emit_warnings: bool = True
    timeout_seconds: int = 5


@dataclass(frozen=True)
class MonitorResult:
    """Result from context monitoring check."""

    action: MonitorAction
    context_utilization: float
    tokens_used: int
    tokens_available: int
    message: str
    exit_code: int = ALLOW
    background_capture_started: bool = False
    # Detection metadata
    detection_method: str = "unknown"
    detection_confidence: str = "none"
    alert_level: str = "info"
    # Auto-compact recommendation
    tokens_remaining: int = 0
    estimated_prompts_remaining: int = 0
    should_compact: bool = False
    should_compact_immediately: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "action": self.action.value,
            "level": self.alert_level,
            "usage_percent": round(self.context_utilization * 100, 1),
            "tokens_used": self.tokens_used,
            "tokens_available": self.tokens_available,
            "tokens_remaining": self.tokens_remaining,
            "estimated_prompts_remaining": self.estimated_prompts_remaining,
            "should_compact": self.should_compact,
            "should_compact_immediately": self.should_compact_immediately,
            "detection_method": self.detection_method,
            "detection_confidence": self.detection_confidence,
            "background_capture_started": self.background_capture_started,
            "message": self.message,
        }


class ContextMonitor:
    """Monitor context utilization and trigger state capture.

    Integrated as UserPromptSubmit hook to check context
    before each user prompt is processed.

    Uses TokenUsageDetector for accurate context detection.
    """

    def __init__(
        self,
        config: MonitorConfig | None = None,
        project_dir: Path | None = None,
    ) -> None:
        self.config = config or MonitorConfig()
        self.project_dir = project_dir or PROJECT_DIR

    def _get_detector(self) -> Any:
        """Get TokenUsageDetector instance.

        Lazy import to avoid circular dependencies.
        """
        try:
            # Try importing from context module
            sys.path.insert(0, str(self.project_dir / ".claude" / "hooks" / "context"))
            from token_usage_detector import TokenUsageDetector

            return TokenUsageDetector(project_dir=self.project_dir)
        except ImportError:
            logger.warning("TokenUsageDetector not found, using fallback")
            return None

    def _detect_event_type(self, hook_input: dict[str, Any]) -> str:
        """Detect which event triggered this hook.

        Returns:
            "session_start" if SessionStart event, "user_prompt" otherwise.
        """
        if "type" in hook_input and hook_input["type"] in ("startup", "resume"):
            return "session_start"
        if hook_input.get("event_type") in ("startup", "resume", "SessionStart"):
            return "session_start"
        if "prompt" in hook_input:
            return "user_prompt"
        return "user_prompt"

    def check_context(self, hook_input: dict[str, Any]) -> MonitorResult:
        """Check current context utilization and determine action.

        Args:
            hook_input: Input from SessionStart or UserPromptSubmit hook.

        Returns:
            MonitorResult with action to take.
        """
        event_type = self._detect_event_type(hook_input)
        is_resume = hook_input.get("type") == "resume"

        # Detect token usage
        detector = self._get_detector()
        if detector:
            detection_result = detector.detect(hook_input)
            utilization = detection_result.utilization
            tokens_used = detection_result.tokens_used
            tokens_available = detection_result.tokens_available
            detection_method = detection_result.method.value
            detection_confidence = detection_result.confidence.value
        else:
            # Fallback if detector not available
            utilization = hook_input.get("context_utilization", 0.0)
            tokens_used = hook_input.get("tokens_used", 0)
            tokens_available = hook_input.get("tokens_available", 200000)
            detection_method = "hook_input"
            detection_confidence = "low"

        # Log event context for debugging
        if event_type == "session_start":
            logger.info(
                f"SessionStart monitor: event={hook_input.get('type', 'unknown')}, "
                f"utilization={utilization:.1%}, method={detection_method}"
            )

        # Determine action based on thresholds
        # On resume, be more aggressive with warnings
        effective_warning = self.config.warning_threshold
        if is_resume:
            effective_warning = min(0.75, self.config.warning_threshold)

        # Emergency threshold (97%)
        if utilization >= self.config.emergency_threshold:
            return self._handle_emergency(
                utilization,
                tokens_used,
                tokens_available,
                detection_method,
                detection_confidence,
            )

        # Compact threshold (95%) - aligned with global CONTEXT_THRESHOLD
        if utilization >= self.config.compact_threshold:
            return self._handle_compact(
                utilization,
                tokens_used,
                tokens_available,
                detection_method,
                detection_confidence,
            )

        # Critical threshold (90%)
        if utilization >= self.config.critical_threshold:
            return self._handle_critical(
                utilization,
                tokens_used,
                tokens_available,
                detection_method,
                detection_confidence,
            )

        # Warning threshold (80%)
        if utilization >= effective_warning:
            return self._handle_warning(
                utilization,
                tokens_used,
                tokens_available,
                detection_method,
                detection_confidence,
            )

        # Normal operation
        tokens_remaining = max(0, tokens_available - tokens_used)
        prompts_remaining = max(0, tokens_remaining // 3000)
        return MonitorResult(
            action=MonitorAction.NORMAL,
            context_utilization=utilization,
            tokens_used=tokens_used,
            tokens_available=tokens_available,
            message="",
            exit_code=ALLOW,
            detection_method=detection_method,
            detection_confidence=detection_confidence,
            alert_level=AlertLevel.INFO.value,
            tokens_remaining=tokens_remaining,
            estimated_prompts_remaining=prompts_remaining,
            should_compact=False,
            should_compact_immediately=False,
        )

    def _handle_warning(
        self,
        utilization: float,
        tokens_used: int,
        tokens_available: int,
        detection_method: str,
        detection_confidence: str,
    ) -> MonitorResult:
        """Handle warning threshold (85-92%)."""
        tokens_remaining = max(0, tokens_available - tokens_used)
        prompts_remaining = max(0, tokens_remaining // 3000)

        message = f"⚠️ Context at {utilization:.0%} - State capture in progress"

        background_started = False
        if self.config.enable_background_capture:
            background_started = self._trigger_background_capture()

        return MonitorResult(
            action=MonitorAction.WARNING,
            context_utilization=utilization,
            tokens_used=tokens_used,
            tokens_available=tokens_available,
            message=message,
            exit_code=ALLOW,
            background_capture_started=background_started,
            detection_method=detection_method,
            detection_confidence=detection_confidence,
            alert_level=AlertLevel.WARNING.value,
            tokens_remaining=tokens_remaining,
            estimated_prompts_remaining=prompts_remaining,
            should_compact=False,
            should_compact_immediately=False,
        )

    def _handle_compact(
        self,
        utilization: float,
        tokens_used: int,
        tokens_available: int,
        detection_method: str,
        detection_confidence: str,
    ) -> MonitorResult:
        """Handle compact threshold (95-97%) - aligned with global CONTEXT_THRESHOLD."""
        tokens_remaining = max(0, tokens_available - tokens_used)
        prompts_remaining = max(0, tokens_remaining // 3000)
        self._trigger_sync_capture(utilization)

        message = (
            f"🔴 Context at {utilization:.0%} (~{prompts_remaining} prompts left) - "
            "Session state captured. Run /compact NOW!"
        )

        return MonitorResult(
            action=MonitorAction.CRITICAL,
            context_utilization=utilization,
            tokens_used=tokens_used,
            tokens_available=tokens_available,
            message=message,
            exit_code=ALLOW,
            detection_method=detection_method,
            detection_confidence=detection_confidence,
            alert_level=AlertLevel.CRITICAL.value,
            tokens_remaining=tokens_remaining,
            estimated_prompts_remaining=prompts_remaining,
            should_compact=True,
            should_compact_immediately=True,
        )

    def _handle_critical(
        self,
        utilization: float,
        tokens_used: int,
        tokens_available: int,
        detection_method: str,
        detection_confidence: str,
    ) -> MonitorResult:
        """Handle critical threshold (90-95%)."""
        tokens_remaining = max(0, tokens_available - tokens_used)
        prompts_remaining = max(0, tokens_remaining // 3000)
        capture_success = self._trigger_sync_capture(utilization)

        if capture_success:
            message = (
                f"🔴 Context at {utilization:.0%} (~{prompts_remaining} prompts left) - "
                "Session state captured. Run /compact soon!"
            )
        else:
            message = (
                f"🔴 Context at {utilization:.0%} (~{prompts_remaining} prompts left) - "
                "Approaching limit. Run /compact soon!"
            )

        return MonitorResult(
            action=MonitorAction.CRITICAL,
            context_utilization=utilization,
            tokens_used=tokens_used,
            tokens_available=tokens_available,
            message=message,
            exit_code=ALLOW,
            detection_method=detection_method,
            detection_confidence=detection_confidence,
            alert_level=AlertLevel.CRITICAL.value,
            tokens_remaining=tokens_remaining,
            estimated_prompts_remaining=prompts_remaining,
            should_compact=True,
            should_compact_immediately=False,
        )

    def _handle_emergency(
        self,
        utilization: float,
        tokens_used: int,
        tokens_available: int,
        detection_method: str,
        detection_confidence: str,
    ) -> MonitorResult:
        """Handle emergency threshold (97%+).

        This is the auto-compact trigger point. Outputs strong recommendation
        and structured JSON for potential automation.
        """
        tokens_remaining = max(0, tokens_available - tokens_used)
        prompts_remaining = max(0, tokens_remaining // 3000)
        self._trigger_sync_capture(utilization)

        # Generate urgent message with countdown
        if prompts_remaining <= 1:
            urgency = "THIS MAY BE YOUR LAST PROMPT!"
        elif prompts_remaining <= 3:
            urgency = f"Only ~{prompts_remaining} prompts left!"
        else:
            urgency = f"~{prompts_remaining} prompts remaining."

        message = (
            f"🚨 EMERGENCY: Context at {utilization:.0%}! {urgency}\n"
            "╔══════════════════════════════════════════════════╗\n"
            "║  AUTO-COMPACT RECOMMENDED - Run /compact NOW!   ║\n"
            "║  Or /clear to start fresh (loses context)       ║\n"
            "╚══════════════════════════════════════════════════╝"
        )

        return MonitorResult(
            action=MonitorAction.EMERGENCY,
            context_utilization=utilization,
            tokens_used=tokens_used,
            tokens_available=tokens_available,
            message=message,
            exit_code=ALLOW,  # Don't block, but emit strong warning
            detection_method=detection_method,
            detection_confidence=detection_confidence,
            alert_level=AlertLevel.EMERGENCY.value,
            tokens_remaining=tokens_remaining,
            estimated_prompts_remaining=prompts_remaining,
            should_compact=True,
            should_compact_immediately=True,
        )

    def _trigger_background_capture(self) -> bool:
        """Trigger background state capture."""
        manager_path = self.project_dir / ".claude" / "hooks" / "lifecycle" / "session_state_manager.py"
        if not manager_path.exists():
            return False

        try:
            subprocess.Popen(
                [sys.executable, str(manager_path), "--capture"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logger.info("Background state capture triggered")
            return True

        except OSError as e:
            logger.warning(f"Failed to trigger background capture: {e}")
            return False

    def _trigger_sync_capture(self, utilization: float = 0.90) -> bool:
        """Trigger synchronous state capture.

        Args:
            utilization: Actual context utilization (0.0-1.0).
        """
        try:
            manager_path = self.project_dir / ".claude" / "hooks" / "lifecycle"
            sys.path.insert(0, str(manager_path))
            from session_state_manager import (  # type: ignore[import-not-found]
                SessionStateManager,
            )

            manager = SessionStateManager(project_dir=self.project_dir)
            result = manager.capture_state(
                session_id=os.environ.get("CLAUDE_SESSION_ID", "unknown"),
                context_utilization=utilization,
                source_hook="context_monitor",
            )
            return result.success

        except Exception as e:
            logger.error(f"Sync capture failed: {e}")
            return False


def read_hook_input() -> dict[str, Any]:
    """Read JSON input from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def emit_result(exit_code: int, message: str = "") -> None:
    """Emit hook result and exit."""
    if message:
        print(message, file=sys.stderr)
    sys.exit(exit_code)


def main() -> None:
    """Entry point for UserPromptSubmit hook.

    WORKAROUND: Due to Claude Code bugs (issues #10964, #4084, #13912):
    - UserPromptSubmit hooks cannot use stdout (causes hook error)
    - stderr is not reliably displayed to users

    Solution: Write warnings to a visible log file that Claude can read.
    The log file is checked at session start and on demand.
    """
    try:
        hook_input = read_hook_input()
        monitor = ContextMonitor()
        result = monitor.check_context(hook_input)

        # Only process non-normal actions (warnings/critical/emergency)
        if result.action != MonitorAction.NORMAL and result.message:
            compact_msg = (
                f"Context at {result.context_utilization:.0%} (~{result.estimated_prompts_remaining} prompts left)"
            )

            if result.should_compact_immediately:
                compact_msg += " - 🚨 EMERGENCY: Run /compact NOW!"
            elif result.should_compact:
                compact_msg += " - 🔴 Run /compact soon!"

            # Write to context warning file (workaround for stdout bug)
            # Claude can be configured to check this file
            warning_file = PROJECT_DIR / ".claude" / "context_warning.txt"
            with contextlib.suppress(OSError):
                warning_file.write_text(
                    f"[{result.alert_level.upper()}] {compact_msg}\n"
                    f"Tokens: {result.tokens_used:,} / {result.tokens_available:,}\n"
                    f"Detection: {result.detection_method} ({result.detection_confidence})\n"
                )

            # Log for debugging
            logger.info(f"Context {result.alert_level}: {result.context_utilization:.1%}")

        else:
            # Clear warning file when context is normal
            warning_file = PROJECT_DIR / ".claude" / "context_warning.txt"
            if warning_file.exists():
                with contextlib.suppress(OSError):
                    warning_file.unlink()

        # Exit with success - no stdout output to avoid hook error
        sys.exit(result.exit_code)

    except Exception:
        logger.exception("Unexpected error in context_monitor")
        sys.exit(ALLOW)  # Don't fail the hook, just log the error


if __name__ == "__main__":
    main()
