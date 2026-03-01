---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 21
title: "Documentation + CI Update"
effort: "M"
estimated_tokens: 10000
depends_on: [19]
parallel_group: "finalize"
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_21.py"
checkpoint: "checkpoints/phase_21.toon"
recovery_plan: "If doc cross-references break: generate link index programmatically"
agent_execution_spec: "general-purpose"
status: "pending"
cross_refs:
  - {file: "09-phase-integration-presets-migration.md", relation: "depends_on"}
  - {file: "12-phase-release-v0.2.0.md", relation: "blocks"}
---

# Phase 21: Documentation + CI Update

**Effort**: M | **Tokens**: ~10,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 19

**Parallel with**: Phase 20 (Benchmarks + Self-Hosting)


## Description

Update all documentation to reflect v0.2.0 components. Add optional rust-check CI job. Validate all doc cross-references.


## Objectives

- [ ] Update docs/ARCHITECTURE.md with new components
- [ ] Update docs/HOOKS_REFERENCE.md with new hooks
- [ ] Update docs/MODULES_CATALOG.md with RLM, governance, hypervisor
- [ ] Create docs/CREATING_MODULES.md extensibility guide update
- [ ] Create docs/MIGRATION.md for v0.1.0 -> v0.2.0
- [ ] Update README.md with v0.2.0 capabilities
- [ ] Add optional rust-check CI job


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `docs/MIGRATION.md` | v0.1.0 to v0.2.0 migration guide | 80 |


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_21/test_doc_links.py` | 10 | 90% | unit |
| `tests/phase_21/test_doc_completeness.py` | 8 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_21/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_doc_links.py`
  - `test_doc_completeness.py`


## Acceptance Criteria

- [ ] All 5 docs updated with new components
- [ ] README reflects v0.2.0 capabilities
- [ ] CI has optional rust-check job
- [ ] All doc cross-references valid


## Tools Required

- Write, Edit, Bash


## Recovery Plan

If doc cross-references break: generate link index programmatically


## Agent Execution

**Spec**: general-purpose


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_21.py
```
Checkpoint saved to: `checkpoints/phase_21.toon`
