---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 16
title: "Advanced Hooks Batch 1"
effort: "M"
estimated_tokens: 12000
depends_on: [11]
parallel_group: "hooks"
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_16.py"
checkpoint: "checkpoints/phase_16.toon"
recovery_plan: "If session state is too large for TOON: implement incremental delta checkpoints"
agent_execution_spec: "general-purpose with worktree isolation"
status: "pending"
cross_refs:
  - {file: "01-phase-shared-infrastructure.md", relation: "depends_on"}
  - {file: "07-phase-advanced-hooks-batch-2.md", relation: "blocks"}
  - {file: "09-phase-integration-presets-migration.md", relation: "blocks"}
---

# Phase 16: Advanced Hooks Batch 1

**Effort**: M | **Tokens**: ~12,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 11

**Parallel with**: Phase 17 (Advanced Hooks Batch 2)


## Description

Extract lifecycle and governance hooks: session state manager for checkpoint before compaction, post-compact rule reinjector, and hooks health validator. These form the self-healing layer.


## Objectives

- [ ] Adapt session_state_manager.py (use lib/checkpoint.py for TOON)
- [ ] Adapt post_compact_reinjector.py (configurable rules injection)
- [ ] Reimplement validate_hooks_health.py (framework settings schema)
- [ ] All hooks follow fail-open pattern (exit 0 on error)


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `modules/hooks-essential/hooks/session_state_manager.py` | State checkpoint before compaction | 200 |
| `modules/hooks-essential/hooks/post_compact_reinjector.py` | Rule reinjection after compaction | 80 |
| `modules/hooks-quality/hooks/validate_hooks_health.py` | Hook health validator on session start | 120 |


## Source Files (Extraction Map)

| Source Path | Target | Type | LOC | Key Classes |
|-------------|--------|------|-----|-------------|
| `analise/.claude/hooks/lifecycle/session_state_manager.py` | `modules/hooks-essential/hooks/session_state_manager.py` | ADAPT_IMPORTS | 250 | SessionStateConfig, CaptureResult, SessionStateManager |
| `analise/.claude/hooks/lifecycle/post_compact_reinjector.py` | `modules/hooks-essential/hooks/post_compact_reinjector.py` | ADAPT_IMPORTS | 96 | - |
| `analise/.claude/hooks/governance/validate_hooks_health.py` | `modules/hooks-quality/hooks/validate_hooks_health.py` | REIMPLEMENT | 150 | - |

### Adaptation Notes

- **`modules/hooks-essential/hooks/session_state_manager.py`**: Remove StateBus/WAL deps, use lib/checkpoint.py for TOON
- **`modules/hooks-essential/hooks/post_compact_reinjector.py`**: Inject critical rules as additionalContext post-compaction
- **`modules/hooks-quality/hooks/validate_hooks_health.py`**: Rewrite to use framework settings schema instead of settings.local.json


## Hook Specifications

| Hook | Event | Module | Exit Codes | P99 Target |
|------|-------|--------|------------|------------|
| `session_state_manager` | PreCompact | hooks-essential | 0 | 200ms |
| `post_compact_reinjector` | PreCompact | hooks-essential | 0 | 100ms |
| `validate_hooks_health` | SessionStart | hooks-quality | 0 | 500ms |

### `session_state_manager`

Checkpoint state before context compaction

**Integration points**:
- `lib/checkpoint.py`
- `lib/circuit_breaker.py`

### `post_compact_reinjector`

Reinject critical rules after compaction

**Integration points**:
- `core/rules/`

### `validate_hooks_health`

Health check all registered hooks

**Integration points**:
- `lib/circuit_breaker.py`


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_16/test_session_state_manager.py` | 15 | 90% | unit |
| `tests/phase_16/test_post_compact_reinjector.py` | 10 | 90% | unit |
| `tests/phase_16/test_validate_hooks_health.py` | 12 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_16/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_session_state_manager.py`
  - `test_post_compact_reinjector.py`
  - `test_validate_hooks_health.py`


## Acceptance Criteria

- [ ] session_state_manager creates valid TOON checkpoints
- [ ] post_compact_reinjector reinjects rules via additionalContext
- [ ] validate_hooks_health checks all hooks and reports status
- [ ] All hooks exit 0 on error (fail-open)
- [ ] 90%+ coverage per file


## Tools Required

- Bash, Write, Edit


## Recovery Plan

If session state is too large for TOON: implement incremental delta checkpoints


## Agent Execution

**Spec**: general-purpose with worktree isolation


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_16.py
```
Checkpoint saved to: `checkpoints/phase_16.toon`
