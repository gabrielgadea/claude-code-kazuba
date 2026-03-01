---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 20
title: "Benchmarks + Self-Hosting"
effort: "S"
estimated_tokens: 8000
depends_on: [19]
parallel_group: "finalize"
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_20.py"
checkpoint: "checkpoints/phase_20.toon"
recovery_plan: "If benchmarks are flaky: increase warm-up iterations and use median"
agent_execution_spec: "general-purpose"
status: "pending"
cross_refs:
  - {file: "09-phase-integration-presets-migration.md", relation: "depends_on"}
  - {file: "12-phase-release-v0.2.0.md", relation: "blocks"}
---

# Phase 20: Benchmarks + Self-Hosting

**Effort**: S | **Tokens**: ~8,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 19

**Parallel with**: Phase 21 (Documentation + CI Update)


## Description

Create benchmark suite for all hooks with P50/P95/P99 metrics. Self-host the framework: kazuba project uses its own hooks.


## Objectives

- [ ] Create benchmark suite for all hooks (P50/P95/P99)
- [ ] Self-host: configure .claude/hooks/ to use framework hooks
- [ ] Add benchmark regression check to CI


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `scripts/benchmark_hooks.py` | Hook benchmark suite with percentile metrics | 200 |
| `.claude/hooks/self_host_config.py` | Self-hosting hook configuration | 50 |


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_20/test_benchmark_runner.py` | 10 | 90% | unit |
| `tests/phase_20/test_self_hosting.py` | 10 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_20/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_benchmark_runner.py`
  - `test_self_hosting.py`


## Acceptance Criteria

- [ ] Benchmark suite runs all hooks with P50/P95/P99 metrics
- [ ] Self-hosting: kazuba project uses its own hooks
- [ ] CI includes benchmark regression check


## Tools Required

- Bash, Write, Edit


## Recovery Plan

If benchmarks are flaky: increase warm-up iterations and use median


## Agent Execution

**Spec**: general-purpose


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_20.py
```
Checkpoint saved to: `checkpoints/phase_20.toon`
