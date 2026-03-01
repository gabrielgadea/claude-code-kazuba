---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 17
title: "Advanced Hooks Batch 2"
effort: "L"
estimated_tokens: 14000
depends_on: [11, 16]
parallel_group: "hooks"
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_17.py"
checkpoint: "checkpoints/phase_17.toon"
recovery_plan: "If ThreadPoolExecutor hangs: add per-motor timeout with concurrent.futures.wait(timeout=2)"
agent_execution_spec: "general-purpose with worktree isolation"
status: "pending"
cross_refs:
  - {file: "01-phase-shared-infrastructure.md", relation: "depends_on"}
  - {file: "06-phase-advanced-hooks-batch-1.md", relation: "depends_on"}
  - {file: "09-phase-integration-presets-migration.md", relation: "blocks"}
---

# Phase 17: Advanced Hooks Batch 2

**Effort**: L | **Tokens**: ~14,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 11, Phase 16

**Parallel with**: Phase 16 (Advanced Hooks Batch 1)


## Description

Extract validation orchestrator (SIAC with 4 concurrent motors), auto permission resolver, and programmatic tool calling advisor. These hooks provide the quality and efficiency layer.


## Objectives

- [ ] Adapt siac_orchestrator_v2.py (refactor motors to plugin registry pattern)
- [ ] Adapt auto_permission_resolver.py (externalize safe paths to YAML config)
- [ ] Adapt ptc_advisor.py (detect repetitive tool calls, suggest automation)
- [ ] All hooks follow fail-open pattern (exit 0 on error)


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `modules/hooks-quality/hooks/siac_orchestrator.py` | 4-motor concurrent validation orchestrator | 180 |
| `modules/hooks-routing/hooks/auto_permission_resolver.py` | Auto-approve safe file operations | 100 |
| `modules/hooks-routing/hooks/ptc_advisor.py` | Programmatic tool calling advisor | 150 |


## Source Files (Extraction Map)

| Source Path | Target | Type | LOC | Key Classes |
|-------------|--------|------|-----|-------------|
| `analise/.claude/hooks/validation/siac_orchestrator_v2.py` | `modules/hooks-quality/hooks/siac_orchestrator.py` | ADAPT_IMPORTS | 200 | MotorResult, SIACResult |
| `analise/.claude/hooks/permissions/auto_permission_resolver.py` | `modules/hooks-routing/hooks/auto_permission_resolver.py` | ADAPT_IMPORTS | 80 | PermissionConfig |
| `analise/.claude/hooks/synthesis/ptc_advisor.py` | `modules/hooks-routing/hooks/ptc_advisor.py` | ADAPT_IMPORTS | 200 | - |

### Adaptation Notes

- **`modules/hooks-quality/hooks/siac_orchestrator.py`**: Refactor motors to plugin registry pattern
- **`modules/hooks-routing/hooks/auto_permission_resolver.py`**: Externalize safe paths to YAML config
- **`modules/hooks-routing/hooks/ptc_advisor.py`**: Detect repetitive tool calls, suggest automation

### External Dependencies from Sources

- `concurrent.futures`


## Hook Specifications

| Hook | Event | Module | Exit Codes | P99 Target |
|------|-------|--------|------------|------------|
| `siac_orchestrator` | PreToolUse | hooks-quality | 0, 1 | 1500ms |
| `auto_permission_resolver` | PreToolUse | hooks-routing | 0, 2 | 100ms |
| `ptc_advisor` | PostToolUse | hooks-routing | 0 | 200ms |

### `siac_orchestrator`

4 concurrent validation motors

**Integration points**:
- `lib/performance.py`

### `auto_permission_resolver`

Auto-approve safe operations

### `ptc_advisor`

Suggest programmatic tool calling patterns


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_17/test_siac_orchestrator.py` | 15 | 90% | unit |
| `tests/phase_17/test_auto_permission_resolver.py` | 12 | 90% | unit |
| `tests/phase_17/test_ptc_advisor.py` | 10 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_17/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_siac_orchestrator.py`
  - `test_auto_permission_resolver.py`
  - `test_ptc_advisor.py`


## Acceptance Criteria

- [ ] SIAC orchestrator runs 4 motors concurrently under P99 1500ms
- [ ] auto_permission_resolver auto-approves configured safe paths
- [ ] ptc_advisor detects 3+ repetitive tool calls and suggests batch
- [ ] All hooks exit 0 on error (fail-open)
- [ ] 90%+ coverage per file


## Tools Required

- Bash, Write, Edit


## Recovery Plan

If ThreadPoolExecutor hangs: add per-motor timeout with concurrent.futures.wait(timeout=2)


## Agent Execution

**Spec**: general-purpose with worktree isolation


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_17.py
```
Checkpoint saved to: `checkpoints/phase_17.toon`
