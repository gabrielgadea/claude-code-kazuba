---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 22
title: "Release v0.2.0"
effort: "S"
estimated_tokens: 5000
depends_on: [20, 21]
parallel_group: null
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_22.py"
checkpoint: "checkpoints/phase_22.toon"
recovery_plan: "If CI fails on release: fix in hotfix branch, re-tag"
agent_execution_spec: "general-purpose"
status: "pending"
cross_refs:
  - {file: "10-phase-benchmarks-self-hosting.md", relation: "depends_on"}
  - {file: "11-phase-documentation-ci-update.md", relation: "depends_on"}
---

# Phase 22: Release v0.2.0

**Effort**: S | **Tokens**: ~5,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 20, Phase 21


## Description

Final release: tag v0.2.0, generate release notes, verify CI green on all jobs, include migration guide.


## Objectives

- [ ] Verify CI green on all jobs (lint, test, coverage, optional rust)
- [ ] Create v0.2.0 git tag
- [ ] Generate release notes documenting all changes from v0.1.0
- [ ] Include migration guide in release


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_22/test_release_checklist.py` | 8 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_22/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_release_checklist.py`


## Acceptance Criteria

- [ ] CI green on all jobs
- [ ] v0.2.0 tag created
- [ ] Release notes document all changes from v0.1.0
- [ ] Migration guide included


## Tools Required

- Bash


## Recovery Plan

If CI fails on release: fix in hotfix branch, re-tag


## Agent Execution

**Spec**: general-purpose


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_22.py
```
Checkpoint saved to: `checkpoints/phase_22.toon`
