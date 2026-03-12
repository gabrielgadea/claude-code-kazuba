//! ACO domain models — Rust equivalents of Python Pydantic V2 frozen models.
//!
//! All structs are immutable (no `&mut self` methods).
//! Mirrors: `scripts/aco/models/core.py` (242 lines Python → ~300 lines Rust)
//!
//! # Architecture
//!
//! - 5 enums: OperationMode, Complexity, ValidationStatus, DriftLevel, GeneratorType
//! - 14 structs: Intent/Objective specs, Generator contracts, Goal tracking, Evolution
//! - All implement Serialize/Deserialize for JSON checkpoint persistence
//! - PyO3 bindings via `#[pyclass(frozen)]` for zero-cost Python interop

use std::collections::HashMap;

#[cfg(feature = "python")]
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

// --- Enums ---

/// Operation mode determines orchestration depth.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(eq, hash, frozen))]
pub enum OperationMode {
    /// Direct response, no orchestration
    Direct,
    /// Light orchestration
    Light,
    /// Complete orchestration (default for complex tasks)
    Complete,
    /// Deep orchestration with meta-generation
    Deep,
}

#[cfg(feature = "python")]
#[pymethods]
impl OperationMode {
    /// Convert to Python string representation (matches Python enum values).
    fn __str__(&self) -> &str {
        match self {
            Self::Direct => "resposta_direta",
            Self::Light => "orquestração_leve",
            Self::Complete => "orquestração_completa",
            Self::Deep => "orquestração_profunda",
        }
    }

    /// Create from Python string value.
    #[staticmethod]
    fn from_str(s: &str) -> PyResult<Self> {
        match s {
            "resposta_direta" => Ok(Self::Direct),
            "orquestração_leve" | "orquestracao_leve" => Ok(Self::Light),
            "orquestração_completa" | "orquestracao_completa" => Ok(Self::Complete),
            "orquestração_profunda" | "orquestracao_profunda" => Ok(Self::Deep),
            _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Unknown OperationMode: {s}"
            ))),
        }
    }
}

/// Task complexity classification.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(eq, hash, frozen))]
pub enum Complexity {
    Trivial,
    Moderate,
    High,
    Critical,
}

#[cfg(feature = "python")]
#[pymethods]
impl Complexity {
    fn __str__(&self) -> &str {
        match self {
            Self::Trivial => "trivial",
            Self::Moderate => "moderada",
            Self::High => "alta",
            Self::Critical => "crítica",
        }
    }

    #[staticmethod]
    fn from_str(s: &str) -> PyResult<Self> {
        match s {
            "trivial" => Ok(Self::Trivial),
            "moderada" => Ok(Self::Moderate),
            "alta" => Ok(Self::High),
            "crítica" | "critica" => Ok(Self::Critical),
            _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Unknown Complexity: {s}"
            ))),
        }
    }
}

/// Validation check result status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(eq, hash, frozen))]
pub enum ValidationStatus {
    Pass,
    Warn,
    Fail,
}

#[cfg(feature = "python")]
#[pymethods]
impl ValidationStatus {
    fn __str__(&self) -> &str {
        match self {
            Self::Pass => "pass",
            Self::Warn => "warn",
            Self::Fail => "fail",
        }
    }

    #[staticmethod]
    fn from_str(s: &str) -> PyResult<Self> {
        match s {
            "pass" => Ok(Self::Pass),
            "warn" => Ok(Self::Warn),
            "fail" => Ok(Self::Fail),
            _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Unknown ValidationStatus: {s}"
            ))),
        }
    }
}

/// Drift from objective — determines orchestrator response.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(eq, hash, frozen))]
pub enum DriftLevel {
    Ok,
    Warning,
    Critical,
    Halt,
}

#[cfg(feature = "python")]
#[pymethods]
impl DriftLevel {
    fn __str__(&self) -> &str {
        match self {
            Self::Ok => "ok",
            Self::Warning => "warning",
            Self::Critical => "critical",
            Self::Halt => "halt",
        }
    }

    #[staticmethod]
    fn from_str(s: &str) -> PyResult<Self> {
        match s {
            "ok" => Ok(Self::Ok),
            "warning" => Ok(Self::Warning),
            "critical" => Ok(Self::Critical),
            "halt" => Ok(Self::Halt),
            _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Unknown DriftLevel: {s}"
            ))),
        }
    }
}

/// Generator classification by function.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(eq, hash, frozen))]
pub enum GeneratorType {
    Template,
    Transformer,
    Composer,
    Validator,
}

#[cfg(feature = "python")]
#[pymethods]
impl GeneratorType {
    fn __str__(&self) -> &str {
        match self {
            Self::Template => "template",
            Self::Transformer => "transformer",
            Self::Composer => "composer",
            Self::Validator => "validator",
        }
    }

    #[staticmethod]
    fn from_str(s: &str) -> PyResult<Self> {
        match s {
            "template" => Ok(Self::Template),
            "transformer" => Ok(Self::Transformer),
            "composer" => Ok(Self::Composer),
            "validator" => Ok(Self::Validator),
            _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Unknown GeneratorType: {s}"
            ))),
        }
    }
}

/// Status of a generator execution.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(eq, hash, frozen))]
pub enum ExecutionStatus {
    Success,
    ValidationFailed,
    ExecutionFailed,
    PreconditionFailed,
    RollbackExecuted,
    RollbackFailed,
}

#[cfg(feature = "python")]
#[pymethods]
impl ExecutionStatus {
    fn __str__(&self) -> &str {
        match self {
            Self::Success => "success",
            Self::ValidationFailed => "validation_failed",
            Self::ExecutionFailed => "execution_failed",
            Self::PreconditionFailed => "precondition_failed",
            Self::RollbackExecuted => "rollback_executed",
            Self::RollbackFailed => "rollback_failed",
        }
    }
}

// --- N2: Intent & Objective Structs ---

/// Parsed user intent with gap analysis and risk assessment.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct IntentSpec {
    /// Raw user prompt before parsing
    pub raw_prompt: String,
    /// Extracted real need after gap analysis
    pub real_need: String,
    /// Description of gap between prompt and real need
    pub gap_analysis: String,
    /// Orchestration depth for this intent
    pub operation_mode: OperationMode,
    /// Identified risks before execution
    pub preliminary_risks: Vec<String>,
    /// Known anti-patterns to monitor during execution
    pub anti_patterns_to_watch: Vec<String>,
    /// SHA256 of real_need — immutable during cycle
    pub objective_hash: String,
}

#[cfg(feature = "python")]
#[pymethods]
impl IntentSpec {
    #[new]
    #[pyo3(signature = (raw_prompt, real_need, gap_analysis, operation_mode, preliminary_risks, anti_patterns_to_watch, objective_hash))]
    fn new(
        raw_prompt: String,
        real_need: String,
        gap_analysis: String,
        operation_mode: OperationMode,
        preliminary_risks: Vec<String>,
        anti_patterns_to_watch: Vec<String>,
        objective_hash: String,
    ) -> Self {
        Self {
            raw_prompt,
            real_need,
            gap_analysis,
            operation_mode,
            preliminary_risks,
            anti_patterns_to_watch,
            objective_hash,
        }
    }

    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(self)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }
}

/// Single measurable success criterion with threshold.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct SuccessCriterion {
    /// Human-readable criterion description
    pub criterion: String,
    /// Metric name used for measurement
    pub metric: String,
    /// Minimum value to consider criterion met
    pub threshold: f64,
    /// Latest measured value for this criterion
    pub current_value: f64,
}

#[cfg(feature = "python")]
#[pymethods]
impl SuccessCriterion {
    #[new]
    #[pyo3(signature = (criterion, metric, threshold, current_value=0.0))]
    fn new(criterion: String, metric: String, threshold: f64, current_value: f64) -> Self {
        Self {
            criterion,
            metric,
            threshold,
            current_value,
        }
    }

    /// Check if criterion is met.
    fn is_met(&self) -> bool {
        self.current_value >= self.threshold
    }
}

/// Impact analysis across system boundaries.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct SystemicImpact {
    /// Components that feed into the affected area
    pub upstream: Vec<String>,
    /// Components that depend on the affected area
    pub downstream: Vec<String>,
    /// Sibling components with shared dependencies
    pub lateral: Vec<String>,
    /// Future capabilities enabled by this change
    pub future_enablement: Vec<String>,
}

#[cfg(feature = "python")]
#[pymethods]
impl SystemicImpact {
    #[new]
    fn new(
        upstream: Vec<String>,
        downstream: Vec<String>,
        lateral: Vec<String>,
        future_enablement: Vec<String>,
    ) -> Self {
        Self {
            upstream,
            downstream,
            lateral,
            future_enablement,
        }
    }
}

// --- N1: Generator Contracts ---

/// Triad of scripts produced by a generator.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct GeneratorOutputs {
    /// Path or content of the main execution script
    pub execution_script: String,
    /// Path or content of the validation script
    pub validation_script: String,
    /// Path or content of the rollback script
    pub rollback_script: String,
}

#[cfg(feature = "python")]
#[pymethods]
impl GeneratorOutputs {
    #[new]
    fn new(execution_script: String, validation_script: String, rollback_script: String) -> Self {
        Self {
            execution_script,
            validation_script,
            rollback_script,
        }
    }

    /// Check if all three scripts are defined (non-empty).
    fn is_complete(&self) -> bool {
        !self.execution_script.is_empty()
            && !self.validation_script.is_empty()
            && !self.rollback_script.is_empty()
    }
}

/// Design-by-contract specification for a generator node.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct GeneratorContract {
    /// Condition that must hold before generator execution
    pub precondition: String,
    /// Condition that must hold after generator execution
    pub postcondition: String,
    /// Condition that must hold throughout execution
    pub invariant: String,
}

#[cfg(feature = "python")]
#[pymethods]
impl GeneratorContract {
    #[new]
    fn new(precondition: String, postcondition: String, invariant: String) -> Self {
        Self {
            precondition,
            postcondition,
            invariant,
        }
    }

    /// Check if all contract fields are defined.
    fn is_complete(&self) -> bool {
        !self.precondition.is_empty()
            && !self.postcondition.is_empty()
            && !self.invariant.is_empty()
    }
}

/// Single generator in the DAG — produces a triad of scripts.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct GeneratorNode {
    /// Unique identifier within the DAG (e.g., "G0", "G1")
    pub id: String,
    /// Human-readable description of what this generator produces
    pub description: String,
    /// Classification of generator function
    pub generator_type: GeneratorType,
    /// Input data file paths or references
    pub inputs_data: Vec<String>,
    /// Template file paths used for code generation
    pub inputs_templates: Vec<String>,
    /// Constraint definitions that bound generation
    pub inputs_constraints: Vec<String>,
    /// Triad of scripts produced by this generator
    pub outputs: GeneratorOutputs,
    /// Design-by-contract specification
    pub contract: GeneratorContract,
    /// Criteria that must pass for acceptance
    pub acceptance_criteria: String,
    /// IDs of generators that must complete before this one
    pub depends_on: Vec<String>,
}

#[cfg(feature = "python")]
#[pymethods]
impl GeneratorNode {
    #[new]
    #[pyo3(signature = (id, description, generator_type, inputs_data, inputs_templates, inputs_constraints, outputs, contract, acceptance_criteria, depends_on))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        id: String,
        description: String,
        generator_type: GeneratorType,
        inputs_data: Vec<String>,
        inputs_templates: Vec<String>,
        inputs_constraints: Vec<String>,
        outputs: GeneratorOutputs,
        contract: GeneratorContract,
        acceptance_criteria: String,
        depends_on: Vec<String>,
    ) -> Self {
        Self {
            id,
            description,
            generator_type,
            inputs_data,
            inputs_templates,
            inputs_constraints,
            outputs,
            contract,
            acceptance_criteria,
            depends_on,
        }
    }

    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(self)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }
}

/// Immutable DAG of generator nodes with execution metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct GeneratorGraphModel {
    /// All generator nodes in the DAG
    pub nodes: Vec<GeneratorNode>,
    /// Ordered node IDs forming the longest dependency chain
    pub critical_path: Vec<String>,
    /// Groups of node IDs that can execute concurrently
    pub parallelizable: Vec<Vec<String>>,
    /// SHA256 linking this graph to its originating objective
    pub objective_hash: String,
}

// --- N2: Goal Tracking ---

/// Score for one of the 9 quality dimensions.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct DimensionScore {
    /// Dimension name (e.g., "D1", "correctness")
    pub name: String,
    /// Aggregated score for this dimension (0.0..1.0)
    pub score: f64,
    /// Individual check scores within this dimension
    pub sub_scores: HashMap<String, f64>,
    /// Minimum score to consider this dimension passing
    pub threshold: f64,
    /// Current drift classification for this dimension
    pub drift_level: DriftLevel,
}

#[cfg(feature = "python")]
#[pymethods]
impl DimensionScore {
    #[new]
    #[pyo3(signature = (name, score, sub_scores, threshold=0.8, drift_level=DriftLevel::Ok))]
    fn new(
        name: String,
        score: f64,
        sub_scores: HashMap<String, f64>,
        threshold: f64,
        drift_level: DriftLevel,
    ) -> Self {
        Self {
            name,
            score,
            sub_scores,
            threshold,
            drift_level,
        }
    }

    /// Check if dimension passes its threshold.
    fn is_passing(&self) -> bool {
        self.score >= self.threshold
    }
}

/// Snapshot of goal tracking state — serializable for checkpoints.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct GoalTrackerState {
    /// SHA256 linking this state to its originating objective
    pub objective_hash: String,
    /// Current orchestration phase name
    pub phase: String,
    /// Scores for each of the 9 quality dimensions
    pub dimension_scores: Vec<DimensionScore>,
    /// Weighted composite score across all dimensions
    pub overall_score: f64,
    /// Aggregate drift level for the entire state
    pub drift_level: DriftLevel,
    /// Diagnostic messages from the tracker
    pub messages: Vec<String>,
    /// Current CRC iteration number
    pub iteration: u32,
}

// --- N3: Evolution & Learning ---

/// Reusable pattern extracted from a successful orchestration cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct LearnedPattern {
    /// Unique identifier for this pattern
    pub pattern_id: String,
    /// Human-readable description of the pattern
    pub description: String,
    /// Template source used when applying this pattern
    pub generator_template: String,
    /// Domain where this pattern applies (e.g., "antt", "rag")
    pub domain: String,
    /// Searchable tags for pattern retrieval
    pub tags: Vec<String>,
}

/// Proposed system improvement based on execution evidence.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct SystemUpgrade {
    /// Target component to upgrade
    pub component: String,
    /// Description of the proposed change
    pub change: String,
    /// Evidence-based justification for the upgrade
    pub rationale: String,
}

/// Post-execution learning package for N3 meta-orchestrator.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct EvolutionPackage {
    /// Unique session identifier for traceability
    pub session_id: String,
    /// SHA256 linking this package to its originating objective
    pub objective_hash: String,
    /// JSON string of execution report (serde_json::Value not PyO3-compatible).
    pub execution_report_json: String,
    /// Reusable patterns extracted from this session
    pub learned_patterns: Vec<LearnedPattern>,
    /// Anti-patterns identified during execution
    pub anti_patterns_discovered: Vec<String>,
    /// Proposed system improvements based on evidence
    pub system_upgrades: Vec<SystemUpgrade>,
    /// Key-value quality metrics (e.g., "composite" -> 0.95)
    pub quality_metrics: HashMap<String, f64>,
    /// Actions to persist knowledge (e.g., "write to KB")
    pub persistence_actions: Vec<String>,
}

/// Result of a single validation check.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct ValidationResult {
    /// Orchestration phase where this check ran
    pub phase: String,
    /// Name of the specific validation check
    pub check_name: String,
    /// Pass/Warn/Fail status of this check
    pub status: ValidationStatus,
    /// Expected value or condition
    pub expected: String,
    /// Actual observed value or condition
    pub actual: String,
    /// Human-readable result message
    pub message: String,
    /// Suggested fix if status is not Pass
    pub remediation: Option<String>,
}

#[cfg(feature = "python")]
#[pymethods]
impl ValidationResult {
    #[new]
    #[pyo3(signature = (phase, check_name, status, expected, actual, message, remediation=None))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        phase: String,
        check_name: String,
        status: ValidationStatus,
        expected: String,
        actual: String,
        message: String,
        remediation: Option<String>,
    ) -> Self {
        Self {
            phase,
            check_name,
            status,
            expected,
            actual,
            message,
            remediation,
        }
    }

    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(self)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }
}

// --- Unit Tests ---

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_operation_mode_serialization() {
        let mode = OperationMode::Complete;
        let json = serde_json::to_string(&mode).unwrap();
        assert_eq!(json, "\"Complete\"");
        let back: OperationMode = serde_json::from_str(&json).unwrap();
        assert_eq!(back, mode);
    }

    #[test]
    fn test_all_enums_roundtrip() {
        // ValidationStatus
        for status in [
            ValidationStatus::Pass,
            ValidationStatus::Warn,
            ValidationStatus::Fail,
        ] {
            let json = serde_json::to_string(&status).unwrap();
            let back: ValidationStatus = serde_json::from_str(&json).unwrap();
            assert_eq!(back, status);
        }

        // DriftLevel
        for drift in [
            DriftLevel::Ok,
            DriftLevel::Warning,
            DriftLevel::Critical,
            DriftLevel::Halt,
        ] {
            let json = serde_json::to_string(&drift).unwrap();
            let back: DriftLevel = serde_json::from_str(&json).unwrap();
            assert_eq!(back, drift);
        }

        // GeneratorType
        for gt in [
            GeneratorType::Template,
            GeneratorType::Transformer,
            GeneratorType::Composer,
            GeneratorType::Validator,
        ] {
            let json = serde_json::to_string(&gt).unwrap();
            let back: GeneratorType = serde_json::from_str(&json).unwrap();
            assert_eq!(back, gt);
        }

        // ExecutionStatus
        for es in [
            ExecutionStatus::Success,
            ExecutionStatus::ValidationFailed,
            ExecutionStatus::ExecutionFailed,
            ExecutionStatus::PreconditionFailed,
            ExecutionStatus::RollbackExecuted,
            ExecutionStatus::RollbackFailed,
        ] {
            let json = serde_json::to_string(&es).unwrap();
            let back: ExecutionStatus = serde_json::from_str(&json).unwrap();
            assert_eq!(back, es);
        }
    }

    #[test]
    fn test_intent_spec_serialization() {
        let spec = IntentSpec {
            raw_prompt: "analyze process".into(),
            real_need: "extract metrics".into(),
            gap_analysis: "no existing script".into(),
            operation_mode: OperationMode::Complete,
            preliminary_risks: vec!["timeout".into()],
            anti_patterns_to_watch: vec!["hardcoded paths".into()],
            objective_hash: "abc123".into(),
        };
        let json = serde_json::to_string(&spec).unwrap();
        let back: IntentSpec = serde_json::from_str(&json).unwrap();
        assert_eq!(back.raw_prompt, "analyze process");
        assert_eq!(back.objective_hash, "abc123");
    }

    #[test]
    fn test_success_criterion_is_met() {
        let met = SuccessCriterion {
            criterion: "coverage".into(),
            metric: "percent".into(),
            threshold: 0.8,
            current_value: 0.95,
        };
        assert!(met.current_value >= met.threshold);

        let not_met = SuccessCriterion {
            criterion: "coverage".into(),
            metric: "percent".into(),
            threshold: 0.8,
            current_value: 0.5,
        };
        assert!(not_met.current_value < not_met.threshold);
    }

    #[test]
    fn test_generator_outputs_completeness() {
        let complete = GeneratorOutputs {
            execution_script: "exec.py".into(),
            validation_script: "val.py".into(),
            rollback_script: "rb.py".into(),
        };
        assert!(complete.is_complete());

        let incomplete = GeneratorOutputs {
            execution_script: "exec.py".into(),
            validation_script: "".into(),
            rollback_script: "rb.py".into(),
        };
        assert!(!incomplete.is_complete());
    }

    #[test]
    fn test_generator_contract_completeness() {
        let complete = GeneratorContract {
            precondition: "files exist".into(),
            postcondition: "output valid".into(),
            invariant: "no side effects".into(),
        };
        assert!(complete.is_complete());

        let incomplete = GeneratorContract {
            precondition: "".into(),
            postcondition: "output valid".into(),
            invariant: "no side effects".into(),
        };
        assert!(!incomplete.is_complete());
    }

    #[test]
    fn test_generator_node_serialization() {
        let node = GeneratorNode {
            id: "G0".into(),
            description: "test gen".into(),
            generator_type: GeneratorType::Template,
            inputs_data: vec!["data.json".into()],
            inputs_templates: vec!["tmpl.py".into()],
            inputs_constraints: vec![],
            outputs: GeneratorOutputs {
                execution_script: "exec.py".into(),
                validation_script: "val.py".into(),
                rollback_script: "rb.py".into(),
            },
            contract: GeneratorContract {
                precondition: "pre".into(),
                postcondition: "post".into(),
                invariant: "inv".into(),
            },
            acceptance_criteria: "tests pass".into(),
            depends_on: vec![],
        };
        let json = serde_json::to_string(&node).unwrap();
        let back: GeneratorNode = serde_json::from_str(&json).unwrap();
        assert_eq!(back.id, "G0");
        assert_eq!(back.depends_on.len(), 0);
    }

    #[test]
    fn test_dimension_score() {
        let dim = DimensionScore {
            name: "D1".into(),
            score: 0.85,
            sub_scores: HashMap::from([("ruff".into(), 1.0), ("pyright".into(), 0.7)]),
            threshold: 0.8,
            drift_level: DriftLevel::Ok,
        };
        assert!(dim.score >= dim.threshold);
        assert_eq!(dim.sub_scores.len(), 2);
    }

    #[test]
    fn test_validation_result_serialization() {
        let result = ValidationResult {
            phase: "execution".into(),
            check_name: "test_check".into(),
            status: ValidationStatus::Pass,
            expected: "exit_code=0".into(),
            actual: "exit_code=0".into(),
            message: "OK".into(),
            remediation: None,
        };
        let json = serde_json::to_string(&result).unwrap();
        let back: ValidationResult = serde_json::from_str(&json).unwrap();
        assert_eq!(back.status, ValidationStatus::Pass);
        assert!(back.remediation.is_none());
    }

    #[test]
    fn test_evolution_package_serialization() {
        let pkg = EvolutionPackage {
            session_id: "sess_001".into(),
            objective_hash: "hash123".into(),
            execution_report_json: "{}".into(),
            learned_patterns: vec![],
            anti_patterns_discovered: vec!["copy-paste".into()],
            system_upgrades: vec![],
            quality_metrics: HashMap::from([("composite".into(), 0.95)]),
            persistence_actions: vec![],
        };
        let json = serde_json::to_string(&pkg).unwrap();
        assert!(json.contains("sess_001"));
        let back: EvolutionPackage = serde_json::from_str(&json).unwrap();
        assert_eq!(back.anti_patterns_discovered.len(), 1);
    }
}
