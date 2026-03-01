---
plan: claude-code-kazuba-v2
version: "3.0"
type: index
total_phases: 12
total_estimated_tokens: 140000
generated: "2026-02-28T22:13:48Z"
---

# Claude Code Kazuba v0.2.0 — Source Integration Master Index

## Overview

Pln2 v2: Source integration plan for claude-code-kazuba v0.2.0.
Phases 11-22 build on the v0.1.0 foundation (phases 0-10).
Amplified in 9 dimensions: source extraction, Pydantic models, hook specs,
test specs, recovery plans, agent execution specs, and more.

## Dependency Graph (DAG)

```
Phase 11 (Shared Infrastructure) [FOUNDATION]
    |-- Phase 12 (Rust Acceleration)  --+-- PARALLEL (infra)
    |-- Phase 13 (Core Governance)    --+
    |       |
    |       +-- Phase 14 (Agent Triggers) -- PARALLEL (triggers)
    |               |
    |               +-- Phase 15 (Hypervisor) [SEQUENTIAL]
    |                       |
    |                       +-- Phase 18 (RLM Learning) [SEQUENTIAL]
    |
    |-- Phase 16 (Hooks Batch 1)      --+-- PARALLEL (hooks)
    |       |                           |
    +-------+-- Phase 17 (Hooks Batch 2) --+
    |
    +-- Phase 12, 13, 14, 15, 16, 17, 18 --> Phase 19 (Integration)
                                                  |
                                          +-------+-------+
                                          |               |
                                  Phase 20 (Bench)  Phase 21 (Docs)
                                          |               |
                                          +-------+-------+
                                                  |
                                          Phase 22 (Release v0.2.0)
```

**Critical Path**: 11 -> 14 -> 15 -> 18 -> 19 -> 22 (6 sequential phases)
**With parallelism**: ~7 context windows instead of 12

## Phase Summary

| # | Title | Effort | Tokens | Group | Deps | Status |
|---|-------|--------|--------|-------|------|--------|

| 11 | [Shared Infrastructure](01-phase-shared-infrastructure.md) | M | ~12,000 | sequential | - | pending |
| 12 | [Rust Acceleration Layer](02-phase-rust-acceleration-layer.md) | L | ~15,000 | infra | 11 | pending |
| 13 | [Core Governance + CILA Formal](03-phase-core-governance-cila-formal.md) | M | ~12,000 | infra | 11 | pending |
| 14 | [Agent Triggers + Recovery Triggers](04-phase-agent-triggers-recovery-triggers.md) | M | ~10,000 | triggers | 11, 13 | pending |
| 15 | [Hypervisor Executable](05-phase-hypervisor-executable.md) | L | ~15,000 | sequential | 11, 14 | pending |
| 16 | [Advanced Hooks Batch 1](06-phase-advanced-hooks-batch-1.md) | M | ~12,000 | hooks | 11 | pending |
| 17 | [Advanced Hooks Batch 2](07-phase-advanced-hooks-batch-2.md) | L | ~14,000 | hooks | 11, 16 | pending |
| 18 | [RLM Learning Memory](08-phase-rlm-learning-memory.md) | L | ~15,000 | sequential | 11, 15 | pending |
| 19 | [Integration + Presets + Migration](09-phase-integration-presets-migration.md) | M | ~12,000 | sequential | 11, 12, 13, 14, 15, 16, 17, 18 | pending |
| 20 | [Benchmarks + Self-Hosting](10-phase-benchmarks-self-hosting.md) | S | ~8,000 | finalize | 19 | pending |
| 21 | [Documentation + CI Update](11-phase-documentation-ci-update.md) | M | ~10,000 | finalize | 19 | pending |
| 22 | [Release v0.2.0](12-phase-release-v0.2.0.md) | S | ~5,000 | sequential | 20, 21 | pending |


## Amplification Metrics

- **Total source files to extract**: 25
- **Total source LOC**: ~11,271
- **Pydantic models to create**: 8
- **Hook specs defined**: 6
- **Test file specs**: 34
- **Total estimated tokens**: ~140,000


## Execution Strategy

### Sequential Phases (must be in order)
- Phase 11 (foundation, no deps)
- Phase 14 -> Phase 15 -> Phase 18 (triggers -> hypervisor -> RLM)
- Phase 19 (integration hub, waits for all)
- Phase 22 (release, waits for 20+21)

### Parallel Groups
- **infra** (after Phase 11): Phases 12, 13 (Rust + Governance)
- **triggers** (after Phases 11, 13): Phase 14
- **hooks** (after Phase 11): Phases 16, 17 (Advanced hooks batches)
- **finalize** (after Phase 19): Phases 20, 21 (Bench + Docs)

### Swarm Configuration

```yaml
team: claude-code-kazuba-v2-build
parallel_groups:
  infra:
    phases: [12, 13]
    agents: 2
    isolation: worktree
    merge_strategy: git merge --no-ff
  hooks:
    phases: [16, 17]
    agents: 2
    isolation: worktree
    merge_strategy: git merge --no-ff
  finalize:
    phases: [20, 21]
    agents: 2
    isolation: worktree
    merge_strategy: git merge --no-ff
```

## Validation

Each phase has a validation script in `validation/validate_phase_NN.py`.
Run all validations: `python plans/v2/validation/validate_all.py`

## Checkpoints

Checkpoints saved in `.toon` format (msgpack) at `checkpoints/phase_NN.toon`.
Recovery: load last .toon checkpoint to resume from any phase.
