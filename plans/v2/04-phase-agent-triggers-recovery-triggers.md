---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 14
title: "Agent Triggers + Recovery Triggers"
effort: "M"
estimated_tokens: 10000
depends_on: [11, 13]
parallel_group: "triggers"
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_14.py"
checkpoint: "checkpoints/phase_14.toon"
recovery_plan: "If trigger conditions fail: simplify to string-only conditions without eval"
agent_execution_spec: "general-purpose with worktree isolation"
status: "pending"
cross_refs:
  - {file: "01-phase-shared-infrastructure.md", relation: "depends_on"}
  - {file: "03-phase-core-governance-cila-formal.md", relation: "depends_on"}
  - {file: "05-phase-hypervisor-executable.md", relation: "blocks"}
  - {file: "09-phase-integration-presets-migration.md", relation: "blocks"}
---

# Phase 14: Agent Triggers + Recovery Triggers

**Effort**: M | **Tokens**: ~10,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 11, Phase 13


## Description

Extract and formalize 14 agent triggers and 8 recovery triggers from kazuba-cargo config. Triggers define when agents auto-activate and how the system recovers from failures, with Python conditions and thinking levels.


## Objectives

- [ ] Extract 14 agent triggers from kazuba-cargo config YAML
- [ ] Extract 5 auto + 3 manual recovery triggers
- [ ] Create Pydantic v2 models for trigger validation
- [ ] Integrate trigger loading with hypervisor config module
- [ ] Validate all triggers load from YAML without errors


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `modules/config-hypervisor/config/agent_triggers.yaml` | 14 declarative agent triggers | 180 |
| `modules/config-hypervisor/config/recovery_triggers.yaml` | 8 recovery triggers (5 auto + 3 manual) | 90 |


## Source Files (Extraction Map)

| Source Path | Target | Type | LOC | Key Classes |
|-------------|--------|------|-----|-------------|
| `kazuba-cargo/.claude/config/agent_triggers.yaml` | `modules/config-hypervisor/config/agent_triggers.yaml` | ADAPT_IMPORTS | 199 | - |
| `kazuba-cargo/.claude/config/recovery_triggers.yaml` | `modules/config-hypervisor/config/recovery_triggers.yaml` | DIRECT_COPY | 95 | - |

### Adaptation Notes

- **`modules/config-hypervisor/config/agent_triggers.yaml`**: 14 triggers with Python conditions, thinking_levels, domain_keywords
- **`modules/config-hypervisor/config/recovery_triggers.yaml`**: 5 auto + 3 manual triggers


## Pydantic Models

### `AgentTrigger` (frozen=True)

Agent trigger with Python condition

- **Module**: `lib/config.py`
- **Fields**:
  - `name: str = ""`
  - `type: str = "auto"`
  - `condition: str = ""`
  - `thinking_level: str = "normal"`
  - `agent: str = ""`

### `RecoveryTrigger` (frozen=True)

Recovery trigger definition

- **Module**: `lib/config.py`
- **Fields**:
  - `name: str = ""`
  - `type: str = "auto"`
  - `on_event: str = ""`
  - `action: str = ""`
  - `max_retries: int = 3`


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_14/test_agent_triggers.py` | 14 | 90% | unit |
| `tests/phase_14/test_recovery_triggers.py` | 10 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_14/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_agent_triggers.py`
  - `test_recovery_triggers.py`


## Acceptance Criteria

- [ ] 14 agent triggers load from YAML
- [ ] 8 recovery triggers load from YAML
- [ ] Pydantic models validate all trigger configs
- [ ] Triggers integrate with hypervisor config


## Tools Required

- Bash, Write, Edit


## Recovery Plan

If trigger conditions fail: simplify to string-only conditions without eval


## Agent Execution

**Spec**: general-purpose with worktree isolation


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_14.py
```
Checkpoint saved to: `checkpoints/phase_14.toon`
