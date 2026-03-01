---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 18
title: "RLM Learning Memory"
effort: "L"
estimated_tokens: 15000
depends_on: [11, 15]
parallel_group: null
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_18.py"
checkpoint: "checkpoints/phase_18.toon"
recovery_plan: "If Q-table grows unbounded: implement LRU eviction with configurable max_entries"
agent_execution_spec: "general-purpose with worktree isolation"
status: "pending"
cross_refs:
  - {file: "01-phase-shared-infrastructure.md", relation: "depends_on"}
  - {file: "05-phase-hypervisor-executable.md", relation: "depends_on"}
  - {file: "09-phase-integration-presets-migration.md", relation: "blocks"}
---

# Phase 18: RLM Learning Memory

**Effort**: L | **Tokens**: ~15,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 11, Phase 15


## Description

Implement the Reinforcement Learning Memory system in pure Python. Q-learning with persistent Q-table, working memory with configurable capacity, and session management with TOON checkpoint integration.


## Objectives

- [ ] Reimplement reasoning patterns (CoT, GoT, ToT) from Rust in Python
- [ ] Reimplement TD-learner and Q-table in pure Python (no NumPy required)
- [ ] Create working memory with configurable capacity and eviction
- [ ] Create session manager with TOON checkpoint save/restore
- [ ] Create reward calculator for hook/agent performance
- [ ] Create RLM facade (lib/rlm.py) for integration with auto_compact


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `modules/rlm/MODULE.md` | RLM module manifest | 40 |
| `modules/rlm/src/__init__.py` | RLM package init | 5 |
| `modules/rlm/src/config.py` | RLM Pydantic config | 50 |
| `modules/rlm/src/models.py` | RLM data models | 80 |
| `modules/rlm/src/q_table.py` | Persistent Q-table | 150 |
| `modules/rlm/src/working_memory.py` | Configurable working memory | 100 |
| `modules/rlm/src/session_manager.py` | Session checkpoint manager | 120 |
| `modules/rlm/src/reward_calculator.py` | Performance reward calculator | 80 |
| `modules/rlm/config/rlm.yaml` | RLM default config | 40 |
| `lib/rlm.py` | RLM facade for hook integration | 150 |


## Source Files (Extraction Map)

| Source Path | Target | Type | LOC | Key Classes |
|-------------|--------|------|-----|-------------|
| `kazuba-cargo/.claude/rust/kazuba-hooks/src/rlm_reasoning.rs` | `(reference only)` | REIMPLEMENT | 200 | ChainOfThought, GraphOfThought, TreeOfThought |
| `kazuba-cargo/.claude/rust/kazuba-hooks/src/learning.rs` | `(reference only)` | REIMPLEMENT | 600 | TDLearner, ClusterEngine, WorkingMemory |
| `kazuba-cargo/.claude/orchestration/rlm/` | `modules/rlm/src/` | ADAPT_IMPORTS | 300 | - |

### Adaptation Notes

- **`(reference only)`**: Reimplement reasoning patterns in Python
- **`(reference only)`**: Reimplement Q-learning in pure Python (no numpy required)
- **`modules/rlm/src/`**: Python orchestration for RLM context management and recursion


## Pydantic Models

### `RLMConfig` (frozen=True)

RLM hyperparameters

- **Module**: `modules/rlm/src/config.py`
- **Fields**:
  - `learning_rate: float = 0.1`
  - `discount_factor: float = 0.95`
  - `epsilon: float = 0.1`
  - `max_history: int = 1000`

### `LearningRecord` (frozen=True)

Single learning record

- **Module**: `modules/rlm/src/models.py`
- **Fields**:
  - `state: str = ""`
  - `action: str = ""`
  - `reward: float = 0.0`
  - `timestamp: float = 0.0`


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_18/test_q_table.py` | 15 | 90% | unit |
| `tests/phase_18/test_working_memory.py` | 12 | 90% | unit |
| `tests/phase_18/test_session_manager.py` | 10 | 90% | unit |
| `tests/phase_18/test_reward_calculator.py` | 10 | 90% | unit |
| `tests/phase_18/test_rlm_facade.py` | 10 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_18/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_q_table.py`
  - `test_working_memory.py`
  - `test_session_manager.py`
  - `test_reward_calculator.py`
  - `test_rlm_facade.py`


## Acceptance Criteria

- [ ] Q-table persists between simulated sessions
- [ ] Working memory has configurable capacity
- [ ] Session compact/restore works with TOON format
- [ ] RLM facade integrates with auto_compact hook
- [ ] Pure Python -- no NumPy required (optional perf boost)


## Tools Required

- Bash, Write, Edit, Agent(general-purpose)


## Recovery Plan

If Q-table grows unbounded: implement LRU eviction with configurable max_entries


## Agent Execution

**Spec**: general-purpose with worktree isolation


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_18.py
```
Checkpoint saved to: `checkpoints/phase_18.toon`
