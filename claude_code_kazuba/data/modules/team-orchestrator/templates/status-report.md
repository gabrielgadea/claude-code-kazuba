---
name: status-report
description: "Template for agent status reports"
---

# Status Report

## Header

- **Agent**: {agent_name}
- **Task ID**: {task_id}
- **Report Type**: progress | completion | blocker | escalation
- **Timestamp**: {timestamp}

## Progress

| Phase | Status | Notes |
|-------|--------|-------|
| {Phase 1} | DONE / IN_PROGRESS / PENDING / BLOCKED | {notes} |
| {Phase 2} | DONE / IN_PROGRESS / PENDING / BLOCKED | {notes} |
| {Phase 3} | DONE / IN_PROGRESS / PENDING / BLOCKED | {notes} |

**Overall**: {percentage}% complete

## Deliverables

- [x] {Completed deliverable 1}
- [ ] {Pending deliverable 2}
- [ ] {Pending deliverable 3}

## Blockers

| Blocker | Severity | Needed From | ETA |
|---------|----------|-------------|-----|
| {description} | high/medium/low | {who can unblock} | {when} |

## Metrics

- **Time spent**: {minutes}
- **Files modified**: {count}
- **Tests added**: {count}
- **Test coverage**: {percentage}%
- **Issues found**: {count}

## Next Steps

1. {Next action 1}
2. {Next action 2}
3. {Next action 3}

## Notes

{Any additional context, lessons learned, or recommendations.}
