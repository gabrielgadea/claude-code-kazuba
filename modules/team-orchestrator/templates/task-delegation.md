---
name: task-delegation
description: "Template for delegating tasks to agents"
---

# Task Delegation

## Task

- **ID**: {task_id}
- **Type**: feature | bugfix | refactor | security | review
- **Priority**: P0 | P1 | P2 | P3 | P4
- **Assigned to**: {agent_name}
- **Delegated by**: {delegator}
- **Timestamp**: {timestamp}

## Context

{Brief description of the task and its importance.}

### Relevant Files

- `{file_path_1}` — {description}
- `{file_path_2}` — {description}

### Related Issues

- {issue_ref} — {description}

## Requirements

1. {Specific requirement 1}
2. {Specific requirement 2}
3. {Specific requirement 3}

## Constraints

- **Time**: {deadline or time budget}
- **Scope**: {what is in/out of scope}
- **Dependencies**: {other tasks that must complete first}
- **Model**: {opus | sonnet | haiku}

## Acceptance Criteria

- [ ] {Criterion 1 — measurable and binary}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

## Escalation

- If blocked for > {timeout}: escalate to {escalation_target}
- If scope unclear: ask {delegator} before proceeding
- If security concern: escalate immediately to security-auditor

## Reporting

Report progress to {delegator} at:
- 25% — confirm understanding and approach
- 50% — interim status
- 100% — completion report with acceptance criteria status
