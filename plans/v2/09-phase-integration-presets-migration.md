---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 19
title: "Integration + Presets + Migration"
effort: "M"
estimated_tokens: 12000
depends_on: [11, 12, 13, 14, 15, 16, 17, 18]
parallel_group: null
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_19.py"
checkpoint: "checkpoints/phase_19.toon"
recovery_plan: "If regression tests fail: git bisect to find breaking change, revert and fix in isolation"
agent_execution_spec: "general-purpose with full test suite access"
status: "pending"
cross_refs:
  - {file: "01-phase-shared-infrastructure.md", relation: "depends_on"}
  - {file: "02-phase-rust-acceleration-layer.md", relation: "depends_on"}
  - {file: "03-phase-core-governance-cila-formal.md", relation: "depends_on"}
  - {file: "04-phase-agent-triggers-recovery-triggers.md", relation: "depends_on"}
  - {file: "05-phase-hypervisor-executable.md", relation: "depends_on"}
  - {file: "06-phase-advanced-hooks-batch-1.md", relation: "depends_on"}
  - {file: "07-phase-advanced-hooks-batch-2.md", relation: "depends_on"}
  - {file: "08-phase-rlm-learning-memory.md", relation: "depends_on"}
  - {file: "10-phase-benchmarks-self-hosting.md", relation: "blocks"}
  - {file: "11-phase-documentation-ci-update.md", relation: "blocks"}
---

# Phase 19: Integration + Presets + Migration

**Effort**: M | **Tokens**: ~12,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 11, Phase 12, Phase 13, Phase 14, Phase 15, Phase 16, Phase 17, Phase 18


## Description

Integration phase: wire all new components together, update presets with new modules, create migration script for v0.1.0 installs, and run full regression to ensure nothing is broken.


## Objectives

- [ ] Update all 5 presets with new v2 modules
- [ ] Add --with-rust flag to install.sh
- [ ] Create scripts/migrate_v01_v02.py migration tool
- [ ] Run ALL existing 723 tests (regression)
- [ ] Create integration E2E tests for new components


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `scripts/migrate_v01_v02.py` | v0.1.0 to v0.2.0 migration | 150 |


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/integration_v2/test_e2e_circuit_breaker.py` | 10 | 90% | unit |
| `tests/integration_v2/test_e2e_governance.py` | 10 | 90% | unit |
| `tests/integration_v2/test_e2e_hypervisor.py` | 10 | 90% | unit |
| `tests/integration_v2/test_e2e_rlm.py` | 10 | 90% | unit |
| `tests/integration_v2/test_regression_723.py` | 5 | 90% | regression |


## Testing

- **Test directory**: `tests/integration_v2/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_e2e_circuit_breaker.py`
  - `test_e2e_governance.py`
  - `test_e2e_hypervisor.py`
  - `test_e2e_rlm.py`
  - `test_regression_723.py`


## Acceptance Criteria

- [ ] All presets updated with new modules
- [ ] install.sh supports --with-rust flag
- [ ] scripts/migrate_v01_v02.py works on v0.1.0 installs
- [ ] ALL existing 723 tests still pass
- [ ] New integration E2E tests pass


## Tools Required

- Bash, Write, Edit, Agent(general-purpose)


## Recovery Plan

If regression tests fail: git bisect to find breaking change, revert and fix in isolation


## Agent Execution

**Spec**: general-purpose with full test suite access


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_19.py
```
Checkpoint saved to: `checkpoints/phase_19.toon`
