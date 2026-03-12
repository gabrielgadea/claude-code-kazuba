"""ESAA Core Types - Pydantic models for Event Sourcing.

Mirrors Rust structs with full type safety and validation.
All models are frozen (immutable) for determinism.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskLevel(str, Enum):
    """Risk assessment levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CilaLevel(str, Enum):
    """CILA complexity levels."""

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"


class OperationType(str, Enum):
    """ESAA operation types."""

    AST_PATCH = "AstPatch"
    FILE_WRITE = "FileWrite"
    SHELL_EXEC = "ShellExec"
    HOOK_EVENT = "HookEvent"


class TaskStatus(str, Enum):
    """Task status in projection."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class GeneratorType(str, Enum):
    """Generator specification types."""

    TEMPLATE = "template"
    TRANSFORMER = "transformer"
    COMPOSER = "composer"
    VALIDATOR = "validator"


class CognitiveTrace(BaseModel):
    """Metadados de rastreamento cognitivo - tracks agent decision context.

    Attributes:
        q_value: Q-value from RL (-1.0 to 1.0)
        intention: Intention description
        risk_assessment: Risk level assessment
        cila_context: CILA complexity level
        agent_id: Agent identifier
        timestamp: Event timestamp
        correlation_id: Optional saga correlation ID
    """

    model_config = ConfigDict(frozen=True, strict=True)

    q_value: float = Field(ge=-1.0, le=1.0, default=0.0)
    intention: str = Field(min_length=1)
    risk_assessment: RiskLevel = RiskLevel.LOW
    cila_context: CilaLevel = CilaLevel.L1
    agent_id: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str | None = None


class CommandPayload(BaseModel):
    """Payload de comando ESAA - the core action unit.

    Attributes:
        operation_type: Type of operation
        target_node: Target file/node (optional)
        delta_payload: Serialized delta (base64 msgpack)
        cognitive_state: Cognitive context
        parent_hash: Parent hash for chain
    """

    model_config = ConfigDict(frozen=True, strict=True)

    operation_type: OperationType
    target_node: str | None = None
    delta_payload: str = Field(min_length=0)
    cognitive_state: CognitiveTrace
    parent_hash: str | None = None


class ESAAEventEnvelope(BaseModel):
    """Envelope de evento ESAA - immutable event record.

    Attributes:
        event_id: Event identifier (EV-00000000 format)
        timestamp: Event timestamp
        command: Command payload
        cryptographic_hash: SHA-256 hash
        schema_version: Schema version
    """

    model_config = ConfigDict(frozen=True, strict=True)

    event_id: str = Field(pattern=r"^EV-\d{8}$")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    command: CommandPayload
    cryptographic_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_version: Literal["0.4.0"] = "0.4.0"

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validate event_id format."""
        if not v.startswith("EV-"):
            raise ValueError("event_id must start with EV-")
        parts = v.split("-")
        if len(parts) != 2 or not parts[1].isdigit():
            raise ValueError("event_id must be EV-XXXXXXXX format")
        return v


class Task(BaseModel):
    """Task state in projection."""

    model_config = ConfigDict(frozen=True, strict=True)

    task_id: str
    task_kind: str = "checkpoint"
    title: str
    status: TaskStatus = TaskStatus.TODO
    assigned_to: str
    completed_at: datetime | None = None
    fail_reason: str | None = None


class RunInfo(BaseModel):
    """Run information in metadata."""

    model_config = ConfigDict(frozen=True, strict=True)

    run_id: str | None = None
    status: str = "initialized"
    last_event_seq: int = 0
    projection_hash_sha256: str = ""
    verify_status: str = "unknown"


class MetaState(BaseModel):
    """Metadata state."""

    model_config = ConfigDict(frozen=True, strict=True)

    schema_version: str = "0.4.0"
    esaa_version: str = "0.4.x"
    immutable_done: bool = True
    master_correlation_id: str | None = None
    run: RunInfo = Field(default_factory=RunInfo)
    updated_at: datetime | None = None


class ProjectInfo(BaseModel):
    """Project information."""

    model_config = ConfigDict(frozen=True, strict=True)

    name: str
    audit_scope: str = ".esaa/"


class Indexes(BaseModel):
    """Indexes for fast queries."""

    model_config = ConfigDict(frozen=True, strict=True)

    by_status: dict[str, int] = Field(default_factory=dict)
    by_kind: dict[str, int] = Field(default_factory=dict)


class ProjectedState(BaseModel):
    """Projected state - result of applying events.

    Attributes:
        meta: Metadata state
        project: Project info
        tasks: List of tasks
        indexes: Computed indexes
    """

    model_config = ConfigDict(frozen=True, strict=True)

    meta: MetaState = Field(default_factory=MetaState)
    project: ProjectInfo = Field(default_factory=lambda: ProjectInfo(name="esaa"))
    tasks: list[Task] = Field(default_factory=list)
    indexes: Indexes = Field(default_factory=Indexes)


class GeneratorSpec(BaseModel):
    """Generator specification - N1 contract.

    Attributes:
        generator_id: Unique ID (UPPER_SNAKE_hex format)
        description: Human-readable description
        generator_type: Type of generator
        inputs: Input parameters
        constraints: Required constraints
        preconditions: Required preconditions
        postconditions: Expected postconditions
        invariants: Maintained invariants
    """

    model_config = ConfigDict(frozen=True, strict=True)

    generator_id: str = Field(pattern=r"^[A-Z_]+_[a-f0-9\-]+$")
    description: str = Field(min_length=10, max_length=200)
    generator_type: GeneratorType
    inputs: dict[str, Any]
    constraints: list[str] = Field(min_length=1)
    preconditions: list[str] = Field(min_length=1)
    postconditions: list[str] = Field(min_length=1)
    invariants: list[str] = Field(min_length=1)

    @field_validator("generator_id")
    @classmethod
    def validate_generator_id(cls, v: str) -> str:
        """Validate generator_id format."""
        parts = v.rsplit("_", 1)
        if len(parts) != 2:
            raise ValueError("generator_id must be PREFIX_hex format")
        prefix, _hex = parts
        if not prefix.isupper():
            raise ValueError("generator_id prefix must be UPPERCASE")
        return v


class TriadOutput(BaseModel):
    """Output validado do motor N1 - execute/validate/rollback.

    Attributes:
        execute_script: Script to execute
        validate_script: Script to validate
        rollback_script: Script to rollback
        execution_hash: SHA-256 hash of execution
    """

    model_config = ConfigDict(frozen=True, strict=True)

    execute_script: str = Field(min_length=50)
    validate_script: str = Field(min_length=50)
    rollback_script: str = Field(min_length=50)
    execution_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class VerifyResult(BaseModel):
    """Verification result."""

    model_config = ConfigDict(frozen=True, strict=True)

    verify_status: str
    hash: str | None = None
    expected: str | None = None
    computed: str | None = None


class ActivityEvent(BaseModel):
    """Activity event payload from activity.jsonl."""

    model_config = ConfigDict(frozen=True, strict=True)

    action: str
    task_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RawEventEntry(BaseModel):
    """Raw event entry from activity.jsonl."""

    model_config = ConfigDict(frozen=True, strict=True)

    event_id: str | None = None
    activity_event: ActivityEvent | None = None


# Type aliases for common patterns
EventStream = list[ESAAEventEnvelope]
TaskList = list[Task]
