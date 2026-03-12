---
name: hooks-kazuba-agents
description: |
  Agent team lifecycle hooks — TeammateIdle quality gate blocks incomplete teammates,
  TaskCompleted validator enforces completion criteria (code quality, ruff compliance,
  documentation). ANTT-specific checks removed; generic quality validation retained.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
provides:
  hooks:
    - teammate_idle_quality_gate
    - task_completed_validator
hook_events:
  - TeammateIdle
  - TaskCompleted
---

# hooks-kazuba-agents

Agent team lifecycle hooks for quality enforcement on teammates and task completion.

## Contents

| Hook | Event | Async | Timeout | Purpose |
|------|-------|-------|---------|---------|
| `teammate_idle_quality_gate.py` | TeammateIdle | no | 10s | Block idle teammates failing quality checks |
| `task_completed_validator.py` | TaskCompleted | no | 10s | Validate task completion criteria (adapted) |

## Adaptations

- `task_completed_validator.py`: Adapted from `analise/.claude/hooks/agents/task_completed_validator.py`.
  ANTT-specific validation removed: `_ANTT_PATTERNS` tuple, `validate_antt_analysis()` function,
  and `antt_analysis` task type branch in `main()`. Generic checks retained: code quality (ruff),
  code review findings documentation, research and documentation validation.
