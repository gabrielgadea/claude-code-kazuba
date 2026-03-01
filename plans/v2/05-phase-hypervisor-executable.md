---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 15
title: "Hypervisor Executable"
effort: "L"
estimated_tokens: 15000
depends_on: [11, 14]
parallel_group: null
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_15.py"
checkpoint: "checkpoints/phase_15.toon"
recovery_plan: "If parallel execution deadlocks: fall back to sequential mode with circuit breaker"
agent_execution_spec: "general-purpose with worktree isolation"
status: "pending"
cross_refs:
  - {file: "01-phase-shared-infrastructure.md", relation: "depends_on"}
  - {file: "04-phase-agent-triggers-recovery-triggers.md", relation: "depends_on"}
  - {file: "08-phase-rlm-learning-memory.md", relation: "blocks"}
  - {file: "09-phase-integration-presets-migration.md", relation: "blocks"}
---

# Phase 15: Hypervisor Executable

**Effort**: L | **Tokens**: ~15,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 11, Phase 14


## Description

Build the executable hypervisor that orchestrates phase execution with support for sequential, parallel, interactive, and dry-run modes. Integrates circuit breaker for failed phases and checkpoint recovery.


## Objectives

- [ ] Adapt hypervisor.py with lib.* imports (remove kazuba-cargo-specific code)
- [ ] Adapt hypervisor_v2.py abstract interfaces (EventMesh, GPUSkillRouter, etc.)
- [ ] Adapt hypervisor_bridge.py for learning/RLM system integration
- [ ] Implement ExecutionMode enum (sequential, parallel, interactive, dry_run)
- [ ] Implement checkpoint recovery from .toon files
- [ ] Integrate circuit breaker for phase failure handling


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `modules/config-hypervisor/src/hypervisor.py` | Phase execution engine with 4 modes | 180 |
| `modules/config-hypervisor/src/hypervisor_v2.py` | V2 abstract interfaces for extensibility | 140 |
| `modules/config-hypervisor/src/hypervisor_bridge.py` | Bridge to RLM learning system | 130 |


## Source Files (Extraction Map)

| Source Path | Target | Type | LOC | Key Classes |
|-------------|--------|------|-----|-------------|
| `kazuba-cargo/.claude/orchestration/kazuba_hypervisor.py` | `modules/config-hypervisor/src/hypervisor.py` | ADAPT_IMPORTS | 200 | HypervisorConfig, PhaseDefinition, ExecutionResult |
| `kazuba-cargo/.claude/orchestration/hypervisor_v2.py` | `modules/config-hypervisor/src/hypervisor_v2.py` | ADAPT_IMPORTS | 150 | HypervisorConfig, HypervisorState, HookType |
| `kazuba-cargo/.claude/orchestration/learning/hypervisor_bridge.py` | `modules/config-hypervisor/src/hypervisor_bridge.py` | ADAPT_IMPORTS | 150 | LearningEvent |

### Adaptation Notes

- **`modules/config-hypervisor/src/hypervisor.py`**: Refactor imports to lib.*, remove kazuba-cargo-specific code
- **`modules/config-hypervisor/src/hypervisor_v2.py`**: Abstract interfaces for EventMesh, GPUSkillRouter, UnifiedMemoryManager, AgentDelegationEngine
- **`modules/config-hypervisor/src/hypervisor_bridge.py`**: Bridge between hypervisor and learning/RLM system


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_15/test_hypervisor.py` | 15 | 90% | unit |
| `tests/phase_15/test_hypervisor_v2.py` | 10 | 90% | unit |
| `tests/phase_15/test_hypervisor_bridge.py` | 10 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_15/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_hypervisor.py`
  - `test_hypervisor_v2.py`
  - `test_hypervisor_bridge.py`


## Acceptance Criteria

- [ ] Hypervisor executes phases in dry-run mode
- [ ] ExecutionMode enum works (sequential, parallel, interactive, dry_run)
- [ ] Checkpoint recovery from .toon files works
- [ ] Circuit breaker integration for failed phases


## Tools Required

- Bash, Write, Edit, Agent(general-purpose)


## Recovery Plan

If parallel execution deadlocks: fall back to sequential mode with circuit breaker


## Agent Execution

**Spec**: general-purpose with worktree isolation


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_15.py
```
Checkpoint saved to: `checkpoints/phase_15.toon`
