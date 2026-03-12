//! ESAA Projector - Deterministic state projection from events
//!
//! Pure functions: same events always produce same state.
//! Zero-copy where possible, Rayon for parallelization.

use crate::types::*;
use rayon::prelude::*;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::HashMap;

/// Project events into state - pure function
pub fn project_events(events: &[RawEventEntry]) -> ProjectedState {
    let mut state = empty_state("kazuba-esaa".to_string());

    for entry in events {
        if let Some(ref activity) = entry.activity_event {
            apply_event(&mut state, activity);
        }
    }

    // Build indexes
    state.indexes.by_status = index_counts(&state.tasks, |t| t.status.to_string());
    state.indexes.by_kind = index_counts(&state.tasks, |t| t.task_kind.clone());

    state
}

/// Compute SHA-256 hash of roadmap (excluding meta.run to avoid cycles)
pub fn compute_projection_hash(roadmap: &serde_json::Value) -> String {
    let payload = json!({
        "schema_version": roadmap.get("meta").and_then(|m| m.get("schema_version")),
        "project": roadmap.get("project"),
        "tasks": roadmap.get("tasks"),
        "indexes": roadmap.get("indexes"),
    });

    let canonical = serde_json::to_string(&payload).unwrap_or_default();
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    hex::encode(hasher.finalize())
}

/// Verify that computed hash matches stored hash
pub fn esaa_verify(
    events: &[RawEventEntry],
    roadmap: &serde_json::Value,
) -> VerifyResult {
    let projected = project_events(events);
    let computed_hash = compute_projection_hash(&serde_json::to_value(&projected).unwrap_or_default());

    let stored_hash = roadmap
        .get("meta")
        .and_then(|m| m.get("run"))
        .and_then(|r| r.get("projection_hash_sha256"))
        .and_then(|h| h.as_str())
        .unwrap_or("");

    if computed_hash == stored_hash {
        VerifyResult {
            verify_status: "ok".to_string(),
            hash: Some(computed_hash),
            expected: None,
            computed: None,
        }
    } else {
        VerifyResult {
            verify_status: "mismatch".to_string(),
            hash: None,
            expected: Some(stored_hash.to_string()),
            computed: Some(computed_hash),
        }
    }
}

/// Empty initial state
fn empty_state(project_name: String) -> ProjectedState {
    ProjectedState {
        meta: MetaState {
            schema_version: "0.4.0".to_string(),
            esaa_version: "0.4.x".to_string(),
            immutable_done: true,
            master_correlation_id: None,
            run: RunInfo {
                run_id: None,
                status: "initialized".to_string(),
                last_event_seq: 0,
                projection_hash_sha256: String::new(),
                verify_status: "unknown".to_string(),
            },
            updated_at: None,
        },
        project: ProjectInfo {
            name: project_name,
            audit_scope: ".esaa/".to_string(),
        },
        tasks: Vec::new(),
        indexes: Indexes::default(),
        _issues: HashMap::new(),
        _lessons: Vec::new(),
    }
}

/// Apply a single event to state
fn apply_event(state: &mut ProjectedState, event: &ActivityEvent) {
    match event.action.as_str() {
        "task.create" => apply_task_create(state, event),
        "verify.ok" => apply_verify_ok(state, event),
        "verify.fail" => apply_verify_fail(state, event),
        "output.rejected" => apply_output_rejected(state, event),
        _ => {} // Unknown action - ignore
    }
}

/// Handle task.create action
fn apply_task_create(state: &mut ProjectedState, event: &ActivityEvent) {
    let task = Task {
        task_id: event.task_id.clone(),
        task_kind: "checkpoint".to_string(),
        title: event
            .payload
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("Unknown")
            .to_string(),
        status: TaskStatus::Todo,
        assigned_to: "kazuba-orchestrator".to_string(),
        completed_at: None,
        fail_reason: None,
    };
    state.tasks.push(task);
}

/// Handle verify.ok action
fn apply_verify_ok(state: &mut ProjectedState, event: &ActivityEvent) {
    for task in &mut state.tasks {
        if task.task_id == event.task_id {
            task.status = TaskStatus::Done;
            if let Some(result) = event.payload.get("n0_result") {
                // Store in _issues or metadata if needed
                let _ = result;
            }
            break;
        }
    }
}

/// Handle verify.fail action
fn apply_verify_fail(state: &mut ProjectedState, event: &ActivityEvent) {
    for task in &mut state.tasks {
        if task.task_id == event.task_id {
            task.status = TaskStatus::Failed;
            task.fail_reason = event
                .payload
                .get("reason")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());
            break;
        }
    }
}

/// Handle output.rejected action
fn apply_output_rejected(state: &mut ProjectedState, event: &ActivityEvent) {
    for task in &mut state.tasks {
        if task.task_id == event.task_id {
            task.status = TaskStatus::Failed;
            task.fail_reason = event
                .payload
                .get("reason")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());
            break;
        }
    }
}

/// Count items by key extractor
fn index_counts<T, F>(items: &[T], key_fn: F) -> HashMap<String, u64>
where
    F: Fn(&T) -> String,
{
    let mut counts: HashMap<String, u64> = HashMap::new();
    for item in items {
        let key = key_fn(item);
        *counts.entry(key).or_insert(0) += 1;
    }
    counts
}

/// Parallel projection for large event sets
pub fn project_events_parallel(events: &[RawEventEntry]) -> ProjectedState {
    // For now, sequential is faster for small sets
    // Rayon benefits kick in at >1000 events
    if events.len() > 1000 {
        // Chunk and parallel process
        project_events(events) // Fallback to sequential for correctness
    } else {
        project_events(events)
    }
}

/// Replay events up to a specific sequence or event_id
pub fn replay_events_until(
    events: &[RawEventEntry],
    until_event_id: &str,
) -> ProjectedState {
    let filtered: Vec<_> = events
        .iter()
        .take_while(|e| {
            e.event_id
                .as_ref()
                .map(|id| id != until_event_id)
                .unwrap_or(true)
        })
        .cloned()
        .collect();

    let mut state = project_events(&filtered);

    // Apply the until event itself
    if let Some(until_event) = events.iter().find(|e| {
        e.event_id
            .as_ref()
            .map(|id| id == until_event_id)
            .unwrap_or(false)
    }) {
        if let Some(ref activity) = until_event.activity_event {
            apply_event(&mut state, activity);
        }
    }

    state
}

/// Replay events up to sequence number
pub fn replay_events_until_seq(events: &[RawEventEntry], seq: usize) -> ProjectedState {
    let filtered: Vec<_> = events.iter().take(seq).cloned().collect();
    project_events(&filtered)
}
