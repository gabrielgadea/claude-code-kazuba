//! ESAA FFI - Python bindings for ESAA core
//!
//! Exports:
//! - project_events(events_json: str) -> str (JSON result)
//! - compute_sha256(state_json: str) -> str
//! - esaa_verify(events_json: str, roadmap_json: str) -> str
//! - validate_event(event_json: str) -> bool

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

pub mod projector;
pub mod types;

use crate::projector::*;
use crate::types::*;

/// Project ESAA events into state
///
/// Args:
///     events_json: JSON string with array of event entries
///
/// Returns:
///     JSON string with ProjectedState
#[pyfunction]
fn project_events(events_json: &str) -> PyResult<String> {
    let events: Vec<RawEventEntry> = serde_json::from_str(events_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid events JSON: {}", e)))?;

    let state = projector::project_events(&events);

    serde_json::to_string(&state)
        .map_err(|e| PyValueError::new_err(format!("Serialization error: {}", e)))
}

/// Compute SHA-256 hash of roadmap state
///
/// Args:
///     state_json: JSON string with roadmap/state
///
/// Returns:
///     Hex string of SHA-256 hash
#[pyfunction]
fn compute_sha256(state_json: &str) -> PyResult<String> {
    let state: serde_json::Value = serde_json::from_str(state_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid state JSON: {}", e)))?;

    Ok(projector::compute_projection_hash(&state))
}

/// Verify ESAA events against roadmap
///
/// Args:
///     events_json: JSON string with events array
///     roadmap_json: JSON string with roadmap
///
/// Returns:
///     JSON string with VerifyResult { verify_status, hash, expected, computed }
#[pyfunction]
fn esaa_verify(events_json: &str, roadmap_json: &str) -> PyResult<String> {
    let events: Vec<RawEventEntry> = serde_json::from_str(events_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid events JSON: {}", e)))?;

    let roadmap: serde_json::Value = serde_json::from_str(roadmap_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid roadmap JSON: {}", e)))?;

    let result = projector::esaa_verify(&events, &roadmap);

    serde_json::to_string(&result)
        .map_err(|e| PyValueError::new_err(format!("Serialization error: {}", e)))
}

/// Validate a single ESAA event
///
/// Args:
///     event_json: JSON string with ESAAEventEnvelope
///
/// Returns:
///     true if valid, raises ValueError if invalid
#[pyfunction]
fn validate_event(event_json: &str) -> PyResult<bool> {
    let event: ESAAEventEnvelope = serde_json::from_str(event_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid event JSON: {}", e)))?;

    // Validate schema version
    if event.schema_version != "0.4.0" {
        return Err(PyValueError::new_err(
            format!("Unsupported schema version: {}", event.schema_version)
        ));
    }

    // Validate event_id format
    if !event.event_id.starts_with("EV-") {
        return Err(PyValueError::new_err(
            format!("Invalid event_id format: {}", event.event_id)
        ));
    }

    // Validate hash
    if !event.verify_hash() {
        return Err(PyValueError::new_err("Event hash verification failed"));
    }

    Ok(true)
}

/// Replay events until specific event_id
///
/// Args:
///     events_json: JSON string with events array
///     until_event_id: Event ID to replay until (inclusive)
///
/// Returns:
///     JSON string with ProjectedState at that point
#[pyfunction]
fn replay_events_until(events_json: &str, until_event_id: &str) -> PyResult<String> {
    let events: Vec<RawEventEntry> = serde_json::from_str(events_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid events JSON: {}", e)))?;

    let state = projector::replay_events_until(&events, until_event_id);

    serde_json::to_string(&state)
        .map_err(|e| PyValueError::new_err(format!("Serialization error: {}", e)))
}

/// Check if Rust extension is available
#[pyfunction]
fn is_available() -> bool {
    true
}

/// Get version info
#[pyfunction]
fn version() -> String {
    "0.4.0".to_string()
}

/// ESAA FFI Python module
#[pymodule]
fn esaa_ffi(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(project_events, m)?)?;
    m.add_function(wrap_pyfunction!(compute_sha256, m)?)?;
    m.add_function(wrap_pyfunction!(esaa_verify, m)?)?;
    m.add_function(wrap_pyfunction!(validate_event, m)?)?;
    m.add_function(wrap_pyfunction!(replay_events_until, m)?)?;
    m.add_function(wrap_pyfunction!(is_available, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;

    m.add("__version__", "0.4.0")?;

    Ok(())
}
