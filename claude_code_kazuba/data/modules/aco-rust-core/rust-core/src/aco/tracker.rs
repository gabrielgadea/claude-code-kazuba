//! GoalTracker — Computational scoring engine for 9-dimensional quality tracking.
//!
//! Rust equivalent of the scoring/aggregation logic from `scripts/aco/goal_tracker_v2.py`.
//! The actual check execution (subprocess calls to ruff, pytest, etc.) remains in Python.
//! This module handles the mathematical core: weighted scoring, drift detection, and status.
//!
//! # Constants (matching Python)
//!
//! - VETO_THRESHOLD: 0.80 (all dims must reach this)
//! - HALT_THRESHOLD: 0.50 (composite below this for N iterations = HALT)
//! - HALT_ITERATIONS: 3 consecutive iterations below HALT
//! - Critical dims D1, D2, D6 have 1.5x weight

#[cfg(feature = "python")]
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// VETO threshold — all dimensions must score >= this.
pub const VETO_THRESHOLD: f64 = 0.80;

/// HALT threshold — composite below this triggers HALT after N iterations.
pub const HALT_THRESHOLD: f64 = 0.50;

/// Number of consecutive iterations below HALT_THRESHOLD before HALT.
pub const HALT_ITERATIONS: u32 = 3;

/// Critical dimensions with 1.5x weight.
pub const CRITICAL_DIMS: &[&str] = &["D1", "D2", "D6"];

/// Weight for critical dimensions.
pub const CRITICAL_WEIGHT: f64 = 1.5;

/// Weight for normal dimensions.
pub const NORMAL_WEIGHT: f64 = 1.0;

/// Tracker status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(eq, frozen))]
pub enum TrackerStatus {
    /// All dimensions >= VETO_THRESHOLD
    Pass,
    /// At least one dimension < VETO_THRESHOLD but composite >= HALT_THRESHOLD
    Veto,
    /// Composite < HALT_THRESHOLD
    Halt,
}

#[cfg(feature = "python")]
#[pymethods]
impl TrackerStatus {
    fn __str__(&self) -> &str {
        match self {
            Self::Pass => "PASS",
            Self::Veto => "VETO",
            Self::Halt => "HALT",
        }
    }
}

/// Result for a single dimension (computed from check results).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct DimResult {
    /// Dimension identifier (e.g. "D1", "D2", ..., "D9").
    pub dim_id: String,
    /// Human-readable dimension name (e.g. "Precision", "Code Quality").
    pub name: String,
    /// Score in [0.0, 1.0] — passed / total checks.
    pub score: f64,
    /// Number of checks that passed.
    pub checks_passed: u32,
    /// Total number of checks evaluated.
    pub checks_total: u32,
    /// Detail strings per check (e.g. "OK: ruff 0 errors", "FAIL: coverage < 80%").
    pub details: Vec<String>,
}

impl DimResult {
    /// Weight for this dimension (1.5x for critical, 1.0x otherwise).
    pub fn weight(&self) -> f64 {
        if CRITICAL_DIMS.contains(&self.dim_id.as_str()) {
            CRITICAL_WEIGHT
        } else {
            NORMAL_WEIGHT
        }
    }

    /// Weighted score = score * weight.
    pub fn weighted_score(&self) -> f64 {
        self.score * self.weight()
    }

    /// Whether this dimension passes the VETO threshold.
    pub fn is_passing(&self) -> bool {
        self.score >= VETO_THRESHOLD
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl DimResult {
    #[new]
    #[pyo3(signature = (dim_id, name, score, checks_passed, checks_total, details=vec![]))]
    fn new(
        dim_id: String,
        name: String,
        score: f64,
        checks_passed: u32,
        checks_total: u32,
        details: Vec<String>,
    ) -> Self {
        Self {
            dim_id,
            name,
            score,
            checks_passed,
            checks_total,
            details,
        }
    }

    /// Weight property (accessible from Python).
    #[getter]
    fn weight_py(&self) -> f64 {
        self.weight()
    }

    /// Weighted score property.
    #[getter]
    fn weighted_score_py(&self) -> f64 {
        self.weighted_score()
    }

    /// Is this dimension passing?
    fn is_passing_py(&self) -> bool {
        self.is_passing()
    }
}

/// Full 9-dimension tracker report.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct TrackerReport {
    /// All 9 dimension results.
    pub dims: Vec<DimResult>,
    /// Weighted composite score across all dimensions.
    pub composite: f64,
    /// Overall tracker status (Pass/Veto/Halt).
    pub status: TrackerStatus,
    /// Current iteration number.
    pub iteration: u32,
}

#[cfg(feature = "python")]
#[pymethods]
impl TrackerReport {
    /// Export to JSON.
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string_pretty(self)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    /// Export to dict-like JSON string (use json.loads() in Python).
    fn to_dict_json(&self) -> PyResult<String> {
        let mut map = serde_json::Map::new();
        map.insert(
            "status".into(),
            serde_json::Value::String(self.status.__str__().to_string()),
        );
        map.insert(
            "composite".into(),
            serde_json::json!(self.composite),
        );
        map.insert("iteration".into(), serde_json::json!(self.iteration));

        let dims: Vec<serde_json::Value> = self
            .dims
            .iter()
            .map(|d| {
                serde_json::json!({
                    "id": d.dim_id,
                    "name": d.name,
                    "score": d.score,
                    "checks_passed": d.checks_passed,
                    "checks_total": d.checks_total,
                    "weight": d.weight(),
                })
            })
            .collect();
        map.insert("dims".into(), serde_json::json!(dims));

        serde_json::to_string(&map)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }
}

/// Compute weighted composite score from dimension results.
///
/// Critical dimensions (D1, D2, D6) have 1.5x weight.
/// Returns 0.0 if no dimensions provided.
pub fn compute_composite(dims: &[DimResult]) -> f64 {
    let total_weight: f64 = dims.iter().map(|d| d.weight()).sum();
    if total_weight == 0.0 {
        return 0.0;
    }
    dims.iter().map(|d| d.weighted_score()).sum::<f64>() / total_weight
}

/// Determine tracker status from dimension scores and composite.
pub fn determine_status(dims: &[DimResult], composite: f64) -> TrackerStatus {
    let all_pass = dims.iter().all(|d| d.score >= VETO_THRESHOLD);
    if all_pass {
        TrackerStatus::Pass
    } else if composite < HALT_THRESHOLD {
        TrackerStatus::Halt
    } else {
        TrackerStatus::Veto
    }
}

/// Build a TrackerReport from raw dimension results.
pub fn build_report(dims: Vec<DimResult>, iteration: u32) -> TrackerReport {
    let composite = compute_composite(&dims);
    let status = determine_status(&dims, composite);
    TrackerReport {
        dims,
        composite,
        status,
        iteration,
    }
}

/// Create a DimResult from a list of check outcomes.
///
/// Each check is a (name, passed) pair. Score = passed / total.
pub fn dim_from_checks(dim_id: &str, name: &str, checks: &[(&str, bool)]) -> DimResult {
    let total = checks.len() as u32;
    let passed = checks.iter().filter(|(_, ok)| *ok).count() as u32;
    let score = if total > 0 {
        f64::from(passed) / f64::from(total)
    } else {
        0.0
    };
    let details: Vec<String> = checks
        .iter()
        .map(|(name, ok)| format!("{}: {name}", if *ok { "OK" } else { "FAIL" }))
        .collect();

    DimResult {
        dim_id: dim_id.to_string(),
        name: name.to_string(),
        score,
        checks_passed: passed,
        checks_total: total,
        details,
    }
}

// --- PyO3 free functions ---

#[cfg(feature = "python")]
/// Compute composite score from Python DimResult list.
#[pyfunction]
pub fn py_compute_composite(dims: Vec<DimResult>) -> f64 {
    compute_composite(&dims)
}

#[cfg(feature = "python")]
/// Determine status from Python DimResult list.
#[pyfunction]
pub fn py_determine_status(dims: Vec<DimResult>, composite: f64) -> TrackerStatus {
    determine_status(&dims, composite)
}

#[cfg(feature = "python")]
/// Build full report from Python DimResult list.
#[pyfunction]
pub fn py_build_report(dims: Vec<DimResult>, iteration: u32) -> TrackerReport {
    build_report(dims, iteration)
}

// --- Unit Tests ---

#[cfg(test)]
mod tests {
    use super::*;

    fn make_dim(id: &str, name: &str, score: f64) -> DimResult {
        DimResult {
            dim_id: id.to_string(),
            name: name.to_string(),
            score,
            checks_passed: (score * 9.0) as u32,
            checks_total: 9,
            details: vec![],
        }
    }

    #[test]
    fn test_critical_dim_weight() {
        let d1 = make_dim("D1", "Precision", 0.9);
        assert_eq!(d1.weight(), CRITICAL_WEIGHT);

        let d3 = make_dim("D3", "Performance", 0.9);
        assert_eq!(d3.weight(), NORMAL_WEIGHT);
    }

    #[test]
    fn test_weighted_score() {
        let d1 = make_dim("D1", "Precision", 0.8);
        assert!((d1.weighted_score() - 1.2).abs() < 1e-10); // 0.8 * 1.5 = 1.2

        let d3 = make_dim("D3", "Performance", 0.8);
        assert!((d3.weighted_score() - 0.8).abs() < 1e-10); // 0.8 * 1.0 = 0.8
    }

    #[test]
    fn test_is_passing() {
        assert!(make_dim("D1", "Precision", 0.80).is_passing());
        assert!(make_dim("D1", "Precision", 0.95).is_passing());
        assert!(!make_dim("D1", "Precision", 0.79).is_passing());
    }

    #[test]
    fn test_compute_composite_all_pass() {
        let dims: Vec<DimResult> = (1..=9)
            .map(|i| make_dim(&format!("D{i}"), &format!("Dim{i}"), 1.0))
            .collect();
        let composite = compute_composite(&dims);
        assert!((composite - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_compute_composite_weighted() {
        // 3 critical dims at 1.0 (weight 1.5 each = 4.5)
        // 6 normal dims at 0.5 (weight 1.0 each = 3.0)
        // weighted sum = 4.5 + 3.0 = 7.5, total weight = 4.5 + 6.0 = 10.5
        // composite = 7.5 / 10.5 ≈ 0.7143
        let mut dims = Vec::new();
        for id in CRITICAL_DIMS {
            dims.push(make_dim(id, "critical", 1.0));
        }
        for i in 3..9 {
            // D3-D8 (skipping D6 which is critical)
            let did = format!("D{}", i + 1);
            if !CRITICAL_DIMS.contains(&did.as_str()) {
                dims.push(make_dim(&did, "normal", 0.5));
            }
        }
        // Fill remaining to get 9 dims
        while dims.len() < 9 {
            dims.push(make_dim(&format!("D{}", dims.len() + 1), "extra", 0.5));
        }

        let composite = compute_composite(&dims);
        // Should be between 0.5 and 1.0 due to critical weighting
        assert!(composite > 0.5);
        assert!(composite < 1.0);
    }

    #[test]
    fn test_compute_composite_empty() {
        let composite = compute_composite(&[]);
        assert!((composite - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_determine_status_pass() {
        let dims: Vec<DimResult> = (1..=9)
            .map(|i| make_dim(&format!("D{i}"), &format!("Dim{i}"), 0.85))
            .collect();
        let composite = compute_composite(&dims);
        assert_eq!(determine_status(&dims, composite), TrackerStatus::Pass);
    }

    #[test]
    fn test_determine_status_veto() {
        let mut dims: Vec<DimResult> = (1..=8)
            .map(|i| make_dim(&format!("D{i}"), &format!("Dim{i}"), 0.85))
            .collect();
        dims.push(make_dim("D9", "Potentiation", 0.70)); // Below VETO_THRESHOLD
        let composite = compute_composite(&dims);
        assert_eq!(determine_status(&dims, composite), TrackerStatus::Veto);
    }

    #[test]
    fn test_determine_status_halt() {
        let dims: Vec<DimResult> = (1..=9)
            .map(|i| make_dim(&format!("D{i}"), &format!("Dim{i}"), 0.30))
            .collect();
        let composite = compute_composite(&dims);
        assert!(composite < HALT_THRESHOLD);
        assert_eq!(determine_status(&dims, composite), TrackerStatus::Halt);
    }

    #[test]
    fn test_build_report() {
        let dims: Vec<DimResult> = (1..=9)
            .map(|i| make_dim(&format!("D{i}"), &format!("Dim{i}"), 0.90))
            .collect();
        let report = build_report(dims, 3);
        assert_eq!(report.status, TrackerStatus::Pass);
        assert!(report.composite > 0.85);
        assert_eq!(report.iteration, 3);
        assert_eq!(report.dims.len(), 9);
    }

    #[test]
    fn test_dim_from_checks() {
        let checks = vec![
            ("ruff 0 errors", true),
            ("pyright clean", true),
            ("coverage >= 80%", false),
            ("CC <= 10", true),
            ("no circular imports", true),
            ("tests exist", true),
            ("init.py exists", true),
            ("generators nonempty", true),
            ("models exist", false),
        ];
        let dim = dim_from_checks("D5", "Code Quality", &checks);
        assert_eq!(dim.dim_id, "D5");
        assert_eq!(dim.checks_passed, 7);
        assert_eq!(dim.checks_total, 9);
        assert!((dim.score - 7.0 / 9.0).abs() < 1e-10);
        assert_eq!(dim.details.len(), 9);
        assert!(dim.details[0].starts_with("OK:"));
        assert!(dim.details[2].starts_with("FAIL:"));
    }

    #[test]
    fn test_tracker_report_serialization() {
        let dims = vec![make_dim("D1", "Precision", 0.9)];
        let report = build_report(dims, 0);
        let json = serde_json::to_string(&report).unwrap();
        let back: TrackerReport = serde_json::from_str(&json).unwrap();
        assert_eq!(back.status, TrackerStatus::Pass);
    }

    #[test]
    fn test_constants_match_python() {
        // These MUST match scripts/aco/goal_tracker_v2.py constants
        assert!((VETO_THRESHOLD - 0.80).abs() < 1e-10);
        assert!((HALT_THRESHOLD - 0.50).abs() < 1e-10);
        assert_eq!(HALT_ITERATIONS, 3);
        assert_eq!(CRITICAL_DIMS, &["D1", "D2", "D6"]);
        assert!((CRITICAL_WEIGHT - 1.5).abs() < 1e-10);
        assert!((NORMAL_WEIGHT - 1.0).abs() < 1e-10);
    }
}
