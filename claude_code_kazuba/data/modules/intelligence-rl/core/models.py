"""Immutable domain models using Pydantic v2.

All models use ConfigDict(frozen=True) for immutability.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskType(StrEnum):
    """Types of ANTT analysis tasks."""

    COMPLETE_ANALYSIS = "complete_analysis"
    PRELIMINARY = "preliminary"
    PRELIMINARY_ANALYSIS = "preliminary"  # Alias for compatibility
    CHRONOLOGY = "chronology"
    TECHNICAL = "technical"
    TECHNICAL_ANALYSIS = "technical"  # Alias for compatibility
    CRITICAL = "critical"
    CRITICAL_ANALYSIS = "critical"  # Alias for compatibility
    LEGAL = "legal"
    LEGAL_ANALYSIS = "legal"  # Alias for compatibility
    SYNTHESIS = "synthesis"
    VOTE = "vote"
    VOTE_GENERATION = "vote"  # Alias for compatibility
    TRIP = "trip"
    HABILITACAO = "habilitacao"
    DOCUMENT_PROCESSING = "document_processing"
    NARRATIVE = "narrative"
    RAG_QUERY = "rag_query"
    UNKNOWN = "unknown"


class ProcessType(StrEnum):
    """Types of ANTT processes."""

    REEQUILIBRIO = "reequilibrio"
    TERMO_ADITIVO = "termo_aditivo"
    AIR = "air"
    FISCALIZACAO = "fiscalizacao"
    HABILITACAO = "habilitacao"
    TRIP = "trip"
    UNKNOWN = "unknown"


class LessonCategory(StrEnum):
    """Categories for lessons learned."""

    SUCCESS_PATTERN = "success_pattern"
    FAILURE_PATTERN = "failure_pattern"
    BEST_PRACTICE = "best_practice"
    GOTCHA = "gotcha"
    OPTIMIZATION = "optimization"


class LessonImpact(StrEnum):
    """Impact level of lessons."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RLAction(StrEnum):
    """Actions available in the RL system."""

    USE_LOCAL_CACHE = "use_local_cache"
    QUERY_CIPHER_MCP = "query_cipher_mcp"
    ACTIVATE_SKILL = "activate_skill"
    APPLY_PATTERN = "apply_pattern"
    STORE_LESSON = "store_lesson"
    CONSOLIDATE_PATTERNS = "consolidate_patterns"
    SKIP = "skip"

    # Skill-specific actions
    ANTT_PRELIMINARY = "antt_preliminary"
    ANTT_CHRONOLOGY = "antt_chronology"
    ANTT_TECHNICAL = "antt_technical"
    ANTT_CRITICAL = "antt_critical"
    ANTT_LEGAL = "antt_legal"
    ANTT_SYNTHESIS = "antt_synthesis"
    ANTT_VOTE = "antt_vote"
    ANTT_DOCUMENT = "antt_document"
    ANTT_ORCHESTRATOR = "antt_orchestrator"

    @classmethod
    def from_skill_name(cls, skill_name: str) -> "RLAction | None":
        """Create RLAction from skill name.

        Args:
            skill_name: Skill name (e.g., 'antt-preliminary-analyzer')

        Returns:
            Corresponding RLAction or None if not mapped
        """
        skill_map = {
            "antt-preliminary-analyzer": cls.ANTT_PRELIMINARY,
            "antt-chronology-builder": cls.ANTT_CHRONOLOGY,
            "antt-technical-analyzer": cls.ANTT_TECHNICAL,
            "antt-critical-analyzer": cls.ANTT_CRITICAL,
            "antt-legal-analyzer": cls.ANTT_LEGAL,
            "antt-final-synthesizer": cls.ANTT_SYNTHESIS,
            "antt-vote-architect": cls.ANTT_VOTE,
            "antt-document-processor": cls.ANTT_DOCUMENT,
            "process-analysis-maestria": cls.ANTT_ORCHESTRATOR,
        }
        return skill_map.get(skill_name)


class MutationStrategy(StrEnum):
    """Strategies for generating capability mutations."""

    PARAMETER_TWEAK = "parameter_tweak"
    SKILL_REORDER = "skill_reorder"
    THRESHOLD_ADJUST = "threshold_adjust"


class MutationStatus(StrEnum):
    """Lifecycle status of a mutation."""

    PENDING = "pending"
    TESTING = "testing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class DriftStatus(StrEnum):
    """Status of concept drift detection."""

    NO_DRIFT = "no_drift"
    WARNING = "warning"
    DRIFT_DETECTED = "drift_detected"


class CircuitState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class LessonContext(BaseModel):
    """Context information for a lesson learned."""

    model_config = ConfigDict(frozen=True)

    task_type: TaskType | None = None
    workflow: str | None = None
    process_number: str | None = None
    process_type: ProcessType = ProcessType.UNKNOWN
    phase: int | None = None  # Analysis phase (1-8)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionOutcome(BaseModel):
    """Outcome of a skill/workflow execution."""

    model_config = ConfigDict(frozen=True)

    execution_id: str
    task_type: TaskType | None = None
    workflow_name: str
    success: bool
    quality_score: float | None = None
    execution_time: float = 0.0  # seconds (legacy name)
    duration_seconds: float = 0.0  # seconds (new name for compatibility)
    user_feedback: int = Field(default=0, ge=-1, le=1)  # -1, 0, 1
    had_errors: bool = False
    error_message: str | None = None  # Error details if failed
    exceeded_timeout: bool = False
    process_number: str | None = None
    process_type: ProcessType = ProcessType.UNKNOWN
    lessons_learned: tuple[str, ...] = ()  # IDs of lessons from this execution
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PatternMatch(BaseModel):
    """A matched pattern from memory."""

    model_config = ConfigDict(frozen=True)

    pattern_id: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    source: str  # "working", "short_term", "long_term", "cipher_mcp"
    content: dict[str, Any] = Field(default_factory=dict)
    workflow_name: str | None = None  # Associated workflow
    quality_score: float | None = None  # Historical quality
    created_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0
    task_type: TaskType | None = None


class LessonLearned(BaseModel):
    """A lesson learned from experience."""

    model_config = ConfigDict(frozen=True)

    lesson_id: str
    category: LessonCategory
    title: str
    description: str
    context: LessonContext  # Context for the lesson
    impact: LessonImpact
    tags: tuple[str, ...] = ()
    source_execution_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    validated: bool = False
    validation_count: int = 0
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)


class EmergentPattern(BaseModel):
    """Pattern emergente detectado por clustering."""

    model_config = ConfigDict(frozen=True)

    pattern_id: str
    centroid: tuple[float, ...]
    member_ids: tuple[str, ...]
    cluster_size: int
    density: float
    created_at: datetime
    confidence: float = Field(ge=0.0, le=1.0)


class Mutation(BaseModel):
    """A capability mutation hypothesis to be tested."""

    model_config = ConfigDict(frozen=True)

    mutation_id: str
    parent_pattern_id: str
    generation: int = 1
    strategy: MutationStrategy
    hypothesis: str
    config_delta: dict[str, Any] = Field(default_factory=dict)
    status: MutationStatus = MutationStatus.PENDING
    baseline_scores: tuple[float, ...] = ()
    mutation_scores: tuple[float, ...] = ()
    p_value: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MutationResult(BaseModel):
    """Result of evaluating a mutation via A/B test."""

    model_config = ConfigDict(frozen=True)

    mutation_id: str
    accepted: bool
    p_value: float
    baseline_mean: float
    mutation_mean: float
    improvement_pct: float
    sample_size: int


class RLState(BaseModel):
    """State representation for RL."""

    model_config = ConfigDict(frozen=True)

    # Core task identification
    task_type: str  # TaskType value or string
    process_type: ProcessType = ProcessType.UNKNOWN

    # Complexity and context
    complexity_level: int = Field(ge=0, le=10, default=5)
    complexity: float = Field(ge=0.0, le=1.0, default=0.5)  # Normalized complexity

    # Document/process availability
    has_local_cache: bool = False
    has_process: bool = False  # Has process number/context
    has_documents: bool = False  # Has associated documents
    cipher_available: bool = True

    # Performance tracking
    recent_success_rate: float = Field(ge=0.0, le=1.0, default=0.5)
    success_rate: float = Field(ge=0.0, le=1.0, default=0.5)  # Alias

    # Temporal and sequence context
    time_of_day_bucket: int = Field(ge=0, le=5, default=0)  # 0-5 (4h buckets)
    previous_skill: str | None = None  # Last skill used

    # Evolution tracking
    evolution_generation: int = 0
    active_mutation_id: str | None = None


class QTableEntry(BaseModel):
    """Entry in the Q-table."""

    model_config = ConfigDict(frozen=True)

    state_hash: str
    action: RLAction
    q_value: float = 0.0
    eligibility_trace: float = 0.0
    update_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
