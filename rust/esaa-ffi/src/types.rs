//! ESAA Core Types - Rust implementation of ESAA schemas
//!
//! Mirrors Python Pydantic models with Serde for serialization.
//! All structs are immutable (no mutation after construction).

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Cognitive trace metadata - tracks agent decision context
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CognitiveTrace {
    /// Q-value from RL (-1.0 to 1.0)
    pub q_value: f64,
    /// Intention description
    pub intention: String,
    /// Risk assessment level
    pub risk_assessment: RiskLevel,
    /// CILA context level
    pub cila_context: CilaLevel,
    /// Agent identifier
    pub agent_id: String,
    /// Event timestamp
    pub timestamp: DateTime<Utc>,
    /// Correlation ID for saga tracking
    pub correlation_id: Option<String>,
}

/// Risk assessment levels
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

/// CILA complexity levels
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CilaLevel {
    #[serde(rename = "L0")]
    L0,
    #[serde(rename = "L1")]
    L1,
    #[serde(rename = "L2")]
    L2,
    #[serde(rename = "L3")]
    L3,
    #[serde(rename = "L4")]
    L4,
    #[serde(rename = "L5")]
    L5,
    #[serde(rename = "L6")]
    L6,
}

/// ESAA operation types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "PascalCase")]
pub enum OperationType {
    AstPatch,
    FileWrite,
    ShellExec,
    HookEvent,
}

/// Command payload - the core ESAA action unit
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CommandPayload {
    /// Type of operation
    pub operation_type: OperationType,
    /// Target file/node (optional)
    pub target_node: Option<String>,
    /// Serialized delta (msgpack bytes as base64 string)
    pub delta_payload: String,
    /// Cognitive context
    pub cognitive_state: CognitiveTrace,
    /// Parent hash for chain
    pub parent_hash: Option<String>,
}

/// ESAA Event Envelope - immutable event record
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ESAAEventEnvelope {
    /// Event identifier (EV-00000000 format)
    pub event_id: String,
    /// Event timestamp
    pub timestamp: DateTime<Utc>,
    /// Command payload
    pub command: CommandPayload,
    /// SHA-256 cryptographic hash
    pub cryptographic_hash: String,
    /// Schema version
    pub schema_version: String,
}

impl ESAAEventEnvelope {
    /// Compute SHA-256 hash of the event (excluding the hash field itself)
    pub fn compute_hash(&self) -> String {
        use sha2::{Digest, Sha256};

        let payload = serde_json::json!({
            "event_id": &self.event_id,
            "timestamp": self.timestamp.to_rfc3339(),
            "command": &self.command,
            "schema_version": &self.schema_version,
        });

        let canonical = serde_json::to_string(&payload).unwrap_or_default();
        let mut hasher = Sha256::new();
        hasher.update(canonical.as_bytes());
        hex::encode(hasher.finalize())
    }

    /// Verify that the stored hash matches computed hash
    pub fn verify_hash(&self) -> bool {
        self.cryptographic_hash == self.compute_hash()
    }
}

/// Task state in projection
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Task {
    pub task_id: String,
    pub task_kind: String,
    pub title: String,
    pub status: TaskStatus,
    pub assigned_to: String,
    pub completed_at: Option<DateTime<Utc>>,
    pub fail_reason: Option<String>,
}

/// Task status enum
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum TaskStatus {
    Todo,
    InProgress,
    Done,
    Failed,
}

/// Projected state - the result of applying events
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ProjectedState {
    pub meta: MetaState,
    pub project: ProjectInfo,
    pub tasks: Vec<Task>,
    pub indexes: Indexes,
    #[serde(skip)]
    pub _issues: HashMap<String, serde_json::Value>,
    #[serde(skip)]
    pub _lessons: Vec<serde_json::Value>,
}

/// Metadata state
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MetaState {
    pub schema_version: String,
    pub esaa_version: String,
    pub immutable_done: bool,
    pub master_correlation_id: Option<String>,
    pub run: RunInfo,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub updated_at: Option<DateTime<Utc>>,
}

/// Run information
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RunInfo {
    pub run_id: Option<String>,
    pub status: String,
    pub last_event_seq: u64,
    pub projection_hash_sha256: String,
    pub verify_status: String,
}

/// Project information
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ProjectInfo {
    pub name: String,
    pub audit_scope: String,
}

/// Indexes for fast queries
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Indexes {
    pub by_status: HashMap<String, u64>,
    pub by_kind: HashMap<String, u64>,
}

/// Generator specification - N1 contract
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GeneratorSpec {
    pub generator_id: String,
    pub description: String,
    pub generator_type: GeneratorType,
    pub inputs: HashMap<String, serde_json::Value>,
    pub constraints: Vec<String>,
    pub preconditions: Vec<String>,
    pub postconditions: Vec<String>,
    pub invariants: Vec<String>,
}

/// Generator types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum GeneratorType {
    Template,
    Transformer,
    Composer,
    Validator,
}

/// Triad output - execute/validate/rollback scripts
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TriadOutput {
    pub execute_script: String,
    pub validate_script: String,
    pub rollback_script: String,
    pub execution_hash: String,
}

/// Verification result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifyResult {
    pub verify_status: String,
    pub hash: Option<String>,
    pub expected: Option<String>,
    pub computed: Option<String>,
}

/// Event action types for projection
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EventAction {
    TaskCreate,
    VerifyOk,
    VerifyFail,
    OutputRejected,
}

/// Activity event payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActivityEvent {
    pub action: String,
    pub task_id: String,
    pub payload: serde_json::Value,
}

/// Raw event entry from activity.jsonl
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawEventEntry {
    #[serde(rename = "event_id", skip_serializing_if = "Option::is_none")]
    pub event_id: Option<String>,
    #[serde(rename = "activity_event", skip_serializing_if = "Option::is_none")]
    pub activity_event: Option<ActivityEvent>,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}
