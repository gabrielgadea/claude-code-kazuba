---
name: hooks-kazuba-pre
description: |
  PreToolUse hooks across 5 matchers — SIAC pre-validation, code standards enforcement,
  PGCC validation, Cipher knowledge retrieval, Serena context retrieval, PRP complexity
  routing, CODE-FIRST validation, PTC advisory, task skill routing, ACO rollback
  enforcement, and pipeline state validation.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
provides:
  hooks:
    - siac_pre_validator
    - code_standards_enforcer
    - pgcc_validator
    - cipher_knowledge_retrieval
    - serena_context_retrieval
    - prp_complexity_router
    - code_first_validator_entry
    - ptc_advisor
    - task_skill_router
    - aco_rollback_enforcer
    - code_first_pipeline_validator
hook_events:
  - PreToolUse
---

# hooks-kazuba-pre

PreToolUse hooks providing quality gates, knowledge retrieval, and validation.

## Contents

| Hook | Matcher | Async | Timeout | Purpose |
|------|---------|-------|---------|---------|
| `siac_pre_validator.py` | Write\|Edit\|MultiEdit | no | 5s | AST audit before writes |
| `code_standards_enforcer.py` | Write\|Edit\|MultiEdit | no | 5s | Enforce code standards |
| `pgcc_validator.py` | Write\|Edit\|MultiEdit | no | 3s | PGCC cache validation |
| `cipher_knowledge_retrieval.py` | Read\|Grep\|Glob | yes | 2s | Pre-fetch relevant knowledge |
| `serena_context_retrieval.py` | Serena mutations | no | 2s | Retrieve symbol context before mutations |
| `prp_complexity_router.py` | Task | yes | 2s | Route by task complexity |
| `code_first_validator_entry.py` | Task | no | 5s | Enforce CODE-FIRST cycle |
| `ptc_advisor.py` | Task | yes | 2s | PTC sequence advisory |
| `task_skill_router.py` | Task | yes | 2s | Route task to appropriate skill |
| `aco_rollback_enforcer.py` | Task | yes | 2s | Enforce ACO rollback on failure |
| `code_first_pipeline_validator.py` | Skill | no | 3s | Validate pipeline state before skills (adapted) |

## Adaptations

- `code_first_pipeline_validator.py`: Adapted from `analise/.claude/hooks/validation/code_first_pipeline_validator.py`.
  Hardcoded `"pipeline_state_*.json"` glob replaced with `_PIPELINE_STATE_GLOB` env var
  (`KAZUBA_PIPELINE_STATE_GLOB`, default: `"pipeline_state_*.json"`). ANTT skill list kept
  as-is but can be overridden by downstream configuration.
