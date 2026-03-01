---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 13
title: "Core Governance + CILA Formal"
effort: "M"
estimated_tokens: 12000
depends_on: [11]
parallel_group: "infra"
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_13.py"
checkpoint: "checkpoints/phase_13.toon"
recovery_plan: "If governance complexity grows: split into governance_core.py and governance_ext.py"
agent_execution_spec: "general-purpose with worktree isolation"
status: "pending"
cross_refs:
  - {file: "01-phase-shared-infrastructure.md", relation: "depends_on"}
  - {file: "04-phase-agent-triggers-recovery-triggers.md", relation: "blocks"}
  - {file: "09-phase-integration-presets-migration.md", relation: "blocks"}
---

# Phase 13: Core Governance + CILA Formal

**Effort**: M | **Tokens**: ~12,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 11

**Parallel with**: Phase 12 (Rust Acceleration Layer)


## Description

Formalize the governance rules and CILA taxonomy as programmatically enforceable components. Extract CODE-FIRST cycle, ZERO-HALLUCINATION enforcement, and L0-L6 intent heuristics into reusable modules.


## Objectives

- [ ] Extract and generalize core-governance.md (remove ANTT-specific refs)
- [ ] Extract and generalize agent-teams.md for any project
- [ ] Adapt CILA taxonomy (L0-L6 heuristics) without domain specifics
- [ ] Implement governance.py with programmatic rule enforcement
- [ ] Adapt strategy_enforcer.py to integrate with cila_router.py


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `core/rules/core-governance.md` | Generalized governance rules | 200 |
| `core/rules/agent-teams.md` | Agent team coordination rules | 150 |
| `modules/hooks-routing/config/cila-taxonomy.md` | CILA L0-L6 taxonomy | 50 |
| `lib/governance.py` | Programmatic governance enforcement | 200 |
| `modules/hooks-routing/hooks/strategy_enforcer.py` | CILA strategy enforcement hook | 120 |


## Source Files (Extraction Map)

| Source Path | Target | Type | LOC | Key Classes |
|-------------|--------|------|-----|-------------|
| `analise/.claude/rules/00-core-governance.md` | `core/rules/core-governance.md` | ADAPT_IMPORTS | 233 | - |
| `analise/.claude/rules/agent-teams.md` | `core/rules/agent-teams.md` | ADAPT_IMPORTS | 184 | - |
| `analise/.claude/rules/antt/cila-taxonomy.md` | `modules/hooks-routing/config/cila-taxonomy.md` | ADAPT_IMPORTS | 54 | - |
| `(new)` | `lib/governance.py` | REIMPLEMENT | 200 | GovernanceRule, CodeFirstPhase, ValidationCriteria |
| `analise/.claude/hooks/context/strategy_enforcer.py` | `modules/hooks-routing/hooks/strategy_enforcer.py` | ADAPT_IMPORTS | 150 | - |

### Adaptation Notes

- **`core/rules/core-governance.md`**: Remove ANTT-specific refs, keep CODE-FIRST 6-step cycle
- **`core/rules/agent-teams.md`**: Generalize from analise to any project
- **`modules/hooks-routing/config/cila-taxonomy.md`**: Remove ANTT, keep L0-L6 heuristics
- **`lib/governance.py`**: Programmatic enforcement of governance rules
- **`modules/hooks-routing/hooks/strategy_enforcer.py`**: Enforce CILA level-based strategy

### External Dependencies from Sources

- `pydantic`


## Pydantic Models

### `GovernanceRule` (frozen=True)

Governance rule definition

- **Module**: `lib/governance.py`
- **Fields**:
  - `name: str = ""`
  - `level: str = "mandatory"`
  - `enforcement: str = "block"`

### `CodeFirstPhase` (frozen=True)

CODE-FIRST cycle phase

- **Module**: `lib/governance.py`
- **Fields**:
  - `phase: str = ""`
  - `completed: bool = False`
  - `evidence: str = ""`


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_13/test_governance.py` | 15 | 90% | unit |
| `tests/phase_13/test_strategy_enforcer.py` | 10 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_13/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_governance.py`
  - `test_strategy_enforcer.py`


## Acceptance Criteria

- [ ] Governance rules render in CLAUDE.md template
- [ ] lib/governance.py passes pyright strict
- [ ] strategy_enforcer.py integrates with existing cila_router.py
- [ ] CODE-FIRST 6-step cycle is enforceable programmatically


## Tools Required

- Bash, Write, Edit


## Recovery Plan

If governance complexity grows: split into governance_core.py and governance_ext.py


## Agent Execution

**Spec**: general-purpose with worktree isolation


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_13.py
```
Checkpoint saved to: `checkpoints/phase_13.toon`
