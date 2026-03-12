---
name: aco-rust-core
description: |
  Rust computational core for ACO: EventProjector (ESAA), GoalTracker, dependency
  graph, frozen models. Compiled via maturin as a Python wheel, or via
  `kazuba build-rust` CLI command.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - aco-esaa
provides:
  rust:
    - event_projector
    - goal_tracker_native
    - dependency_graph
    - frozen_models
---

# aco-rust-core

Rust computational core for ACO: EventProjector (ESAA), GoalTracker, dependency graph,
frozen models. Compiled via `maturin build --features python --release` as a Python wheel,
or via `kazuba build-rust` CLI command.

## Dependencies

- `aco-esaa` -- Python ESAA layer (Rust core accelerates this)

## Files

- `rust-core/Cargo.toml` -- Rust workspace configuration
- `rust-core/src/aco/esaa.rs` -- EventProjector (load_events, project_agent_state, verify_hash_chain, replay_since, verify_chain_parallel)
- `rust-core/src/aco/models.rs` -- Frozen Pydantic-equivalent models
- `rust-core/src/aco/graph.rs` -- Kahn+DP dependency graph solver
- `rust-core/src/aco/tracker.rs` -- GoalTracker 9x9=81 checks
- `rust-core/src/aco/mod.rs` -- Module declarations

## Build

```bash
cd <target>/.claude/rust-core
maturin build --features python --release
pip install --user --force-reinstall --break-system-packages target/wheels/*.whl
```
