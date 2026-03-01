"""Pydantic v2 models for multi-agent team orchestration.

Defines typed data structures for task delegation, agent capabilities,
routing decisions, and system status reporting.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskPriority(StrEnum):
    """Priority levels for task routing and SLA enforcement."""

    P0 = "critical"
    P1 = "high"
    P2 = "medium"
    P3 = "low"
    P4 = "informational"


class TaskStatus(StrEnum):
    """Lifecycle states for a delegated task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRole(StrEnum):
    """Recognized agent roles within the orchestration framework."""

    ORCHESTRATOR = "orchestrator"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    AUDITOR = "auditor"


class CircuitState(StrEnum):
    """Circuit breaker states (Hystrix pattern)."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class EscalationLevel(StrEnum):
    """Escalation severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Agent Models
# ---------------------------------------------------------------------------


class AgentCapability(BaseModel):
    """Describes a single capability an agent possesses."""

    name: str = Field(..., description="Capability identifier (e.g. 'code_review')")
    proficiency: float = Field(..., ge=0.0, le=1.0, description="Proficiency score 0.0-1.0")
    tools: list[str] = Field(default_factory=list, description="Tools required")
    description: str = Field(default="", description="Human-readable description")


class AgentConfig(BaseModel):
    """Configuration for a single agent in the registry."""

    name: str = Field(..., description="Agent display name")
    bot_username: str = Field(..., description="Bot username (e.g. @my_bot)")
    role: AgentRole = Field(..., description="Agent role")
    model: str = Field(default="sonnet", description="Default model to use")
    capabilities: list[AgentCapability] = Field(default_factory=list)
    max_concurrent_tasks: int = Field(default=1, ge=1)
    is_coordinator: bool = Field(default=False)
    silence_window_seconds: int = Field(default=0, ge=0, description="Cooldown between deliveries")


# ---------------------------------------------------------------------------
# Task Models
# ---------------------------------------------------------------------------


class TaskRequest(BaseModel):
    """A task to be delegated to an agent."""

    task_id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., min_length=1, description="Brief task title")
    description: str = Field(default="", description="Detailed requirements")
    priority: TaskPriority = Field(default=TaskPriority.P2)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    assigned_to: str | None = Field(default=None, description="Agent name")
    created_by: str = Field(default="orchestrator")
    created_at: datetime = Field(default_factory=datetime.now)
    deadline_seconds: int | None = Field(default=None, ge=0, description="SLA deadline in seconds")
    tags: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(
        default_factory=list, description="Task IDs that block this task"
    )
    metadata: dict[str, str] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Result returned after task completion or failure."""

    task_id: str = Field(..., description="Matches the originating TaskRequest")
    status: TaskStatus = Field(...)
    agent_name: str = Field(..., description="Agent that executed the task")
    output: str = Field(default="", description="Task output or error message")
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    duration_seconds: float | None = Field(default=None, ge=0.0)
    retries: int = Field(default=0, ge=0)
    success: bool = Field(default=True)


# ---------------------------------------------------------------------------
# Routing Models
# ---------------------------------------------------------------------------


class RoutingRule(BaseModel):
    """Declarative routing rule for the SmartRouter."""

    name: str = Field(..., description="Rule identifier")
    priority: int = Field(default=100, description="Lower = higher priority")
    condition: str = Field(..., description="Condition expression")
    action: str = Field(..., description="Action to take (route, drop, broadcast)")
    target_agents: list[str] = Field(default_factory=list, description="Target agent names")
    exclude_sender: bool = Field(default=True)
    description: str = Field(default="")


class DelegationDecision(BaseModel):
    """Result of the routing engine selecting an agent for a task."""

    task_id: str = Field(..., description="Task being delegated")
    selected_agent: str = Field(..., description="Chosen agent name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Selection confidence score")
    reasoning: str = Field(default="", description="Why this agent was chosen")
    fallback_agents: list[str] = Field(
        default_factory=list, description="Alternatives if primary fails"
    )
    matched_rule: str | None = Field(default=None, description="Routing rule that matched")


# ---------------------------------------------------------------------------
# System Status Models
# ---------------------------------------------------------------------------


class CircuitBreakerStatus(BaseModel):
    """Status of a single circuit breaker."""

    name: str = Field(..., description="Breaker identifier")
    state: CircuitState = Field(default=CircuitState.CLOSED)
    failure_count: int = Field(default=0, ge=0)
    last_failure_at: datetime | None = Field(default=None)
    recovery_timeout_seconds: int = Field(default=60, ge=0)


class SystemStatus(BaseModel):
    """Snapshot of the orchestration system state."""

    timestamp: datetime = Field(default_factory=datetime.now)
    active_agents: list[str] = Field(default_factory=list)
    pending_tasks: int = Field(default=0, ge=0)
    in_progress_tasks: int = Field(default=0, ge=0)
    completed_tasks: int = Field(default=0, ge=0)
    failed_tasks: int = Field(default=0, ge=0)
    circuit_breakers: list[CircuitBreakerStatus] = Field(default_factory=list)
    uptime_seconds: float = Field(default=0.0, ge=0.0)


class EscalationEvent(BaseModel):
    """Event raised when a task or agent requires escalation."""

    event_id: str = Field(..., description="Unique event identifier")
    level: EscalationLevel = Field(...)
    source_agent: str = Field(..., description="Agent that triggered escalation")
    task_id: str | None = Field(default=None, description="Related task if any")
    message: str = Field(..., description="Description of the issue")
    timestamp: datetime = Field(default_factory=datetime.now)
    suggested_action: str = Field(default="", description="Recommended resolution")
    auto_resolved: bool = Field(default=False)
