---
name: aco-orchestrator
description: |
  ACO N2 Orchestrator: coordinates N1 generators, tracks goals (9x9=81 checks),
  bridges Python/Rust execution paths.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - aco-esaa
  - aco-generators
provides:
  aco:
    - orchestrator
    - goal_tracker
    - rust_bridge
---

# aco-orchestrator

ACO N2 Orchestrator: coordinates N1 generators, tracks goals (9x9=81 checks),
bridges Python/Rust execution paths.

## Dependencies

- `aco-esaa` -- Event-Sourced Agent Architecture (foundation layer)
- `aco-generators` -- N1 generators coordinated by the orchestrator

## Files

- `src/aco/orchestrator.py` -- N2 coordinator
- `src/aco/goal_tracker.py` -- 9x9=81 dimensional goal tracking
- `src/aco/rust_bridge.py` -- try Rust -> fallback Python (8 functions)
