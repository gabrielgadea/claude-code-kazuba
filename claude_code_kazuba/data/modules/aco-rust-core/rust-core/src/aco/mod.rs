//! ACO (Agentic Code Orchestrator) — Rust acceleration module.
//!
//! Provides high-performance implementations of ACO core components:
//!
//! - **models**: Domain types (enums + structs) mirroring Python Pydantic V2 frozen models
//! - **graph**: DAG operations (topological sort, critical path, parallelization) via petgraph
//! - **tracker**: 9-dimensional goal tracking with weighted scoring and drift detection
//!
//! # Architecture
//!
//! ```text
//! Python Layer (orchestrator.py, generators/)
//!     │
//!     │ PyO3 bindings
//!     ▼
//! Rust ACO Kernel (this module)
//!     ├── models   → 5 enums + 14 structs (serde + PyO3 frozen)
//!     ├── graph    → petgraph DiGraph + Kahn's + DP critical path
//!     └── tracker  → weighted composite scoring + status determination
//! ```

pub mod esaa;
pub mod graph;
pub mod models;
pub mod tracker;

// Re-exports for convenience
pub use graph::{GraphError, MutableGeneratorGraph};
pub use models::*;
pub use tracker::{
    build_report, compute_composite, determine_status, dim_from_checks, DimResult, TrackerReport,
    TrackerStatus, CRITICAL_DIMS, CRITICAL_WEIGHT, HALT_ITERATIONS, HALT_THRESHOLD, NORMAL_WEIGHT,
    VETO_THRESHOLD,
};

/// Register all ACO PyO3 classes and functions in the parent module.
#[cfg(feature = "python")]
pub fn register_aco_module(m: &pyo3::Bound<'_, pyo3::types::PyModule>) -> pyo3::PyResult<()> {
    use pyo3::prelude::*;

    // Enums
    m.add_class::<models::OperationMode>()?;
    m.add_class::<models::Complexity>()?;
    m.add_class::<models::ValidationStatus>()?;
    m.add_class::<models::DriftLevel>()?;
    m.add_class::<models::GeneratorType>()?;
    m.add_class::<models::ExecutionStatus>()?;

    // Structs — Intent/Objective
    m.add_class::<models::IntentSpec>()?;
    m.add_class::<models::SuccessCriterion>()?;
    m.add_class::<models::SystemicImpact>()?;

    // Structs — Generator
    m.add_class::<models::GeneratorOutputs>()?;
    m.add_class::<models::GeneratorContract>()?;
    m.add_class::<models::GeneratorNode>()?;
    m.add_class::<models::GeneratorGraphModel>()?;

    // Structs — Goal Tracking
    m.add_class::<models::DimensionScore>()?;
    m.add_class::<models::GoalTrackerState>()?;

    // Structs — Evolution
    m.add_class::<models::LearnedPattern>()?;
    m.add_class::<models::SystemUpgrade>()?;
    m.add_class::<models::EvolutionPackage>()?;
    m.add_class::<models::ValidationResult>()?;

    // Graph
    m.add_class::<graph::PyAcoGraph>()?;

    // Tracker
    m.add_class::<tracker::TrackerStatus>()?;
    m.add_class::<tracker::DimResult>()?;
    m.add_class::<tracker::TrackerReport>()?;
    m.add_function(wrap_pyfunction!(tracker::py_compute_composite, m)?)?;
    m.add_function(wrap_pyfunction!(tracker::py_determine_status, m)?)?;
    m.add_function(wrap_pyfunction!(tracker::py_build_report, m)?)?;

    // Constants
    m.add("VETO_THRESHOLD", VETO_THRESHOLD)?;
    m.add("HALT_THRESHOLD", HALT_THRESHOLD)?;
    m.add("HALT_ITERATIONS", HALT_ITERATIONS)?;
    m.add("CRITICAL_WEIGHT", CRITICAL_WEIGHT)?;
    m.add("NORMAL_WEIGHT", NORMAL_WEIGHT)?;

    // ESAA — Event Sourcing Agent Architecture
    m.add_class::<esaa::QueryCacheStats>()?;
    m.add_class::<esaa::EventBufferStats>()?;
    m.add_class::<esaa::EventBufferConfig>()?;
    m.add_class::<esaa::PyQueryCache>()?;
    m.add_class::<esaa::PyEventBuffer>()?;
    // D3 — Rust AST Projector
    m.add_class::<esaa::PyEventProjector>()?;
    // D4 — Rust Hash Chain Verifier
    m.add_function(wrap_pyfunction!(esaa::verify_chain_parallel, m)?)?;

    Ok(())
}
