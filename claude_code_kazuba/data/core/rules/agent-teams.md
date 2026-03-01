# Agent Teams — Rules and Governance

> Priority: 90 (below CODE-FIRST Priority 100)
> Status: EXPERIMENTAL — activate via CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
> CILA Level: L6 (Multi-Agent)

---

## When to Use Agent Teams

Agent teams are **MANDATORY** for:

| Task                              | Why use a team                                       |
|-----------------------------------|------------------------------------------------------|
| Multi-phase analysis (F1-F16)     | Real parallelism between independent phases          |
| Multi-perspective code review     | Security + Performance + Quality simultaneously      |
| Investigation with competing hyp. | Adversarial debug converges faster                   |
| Vote with multi-disciplinary work | Independent technical + review streams               |
| Sprint with independent modules   | Parallel implementation without conflict             |

Agent teams are **PROHIBITED** when:

- Tasks are sequential (B necessarily depends on A)
- Multiple teammates would edit the same file
- Task is simple (subagent or single session is sufficient)
- There is no real parallelism in the task

---

## Mandatory Rules (L6)

### R1 — Explicit Context in Spawn

```
MANDATORY: Include in spawn prompt:
- Objective and scope of the task
- Exclusive files assigned to this teammate
- Completion criterion (what "done" looks like)
- Dependencies on other teammates (if any)

PROHIBITED: Assuming teammate inherits context from lead.
Each teammate starts with ZERO context history.
```

### R2 — File Partition without Conflict

```
MANDATORY: Each teammate has an EXCLUSIVE set of files.
PROHIBITED: Two teammates editing the same file simultaneously.

Partition patterns:
- By package: teammate-a → lib/, teammate-b → modules/
- By section: teammate-a → core/rules/, teammate-b → tests/
- By phase: teammate-a → phase_12, teammate-b → phase_13
- By concern: teammate-a → implementation, teammate-b → tests
```

### R3 — State Verification Before Team

```
MANDATORY: For tasks requiring prior state, verify before creating team.
Lead verifies preconditions before spawning teammates.

VIOLATION: Creating analysis team without verified preconditions.
```

### R4 — Quality Gates via Hooks

```
ACTIVE: TeammateIdle hook → validates teammate output quality
ACTIVE: TaskCompleted hook → validates by task type (code, review, docs)

Teammates pass through automatic quality gate:
- TeammateIdle: ruff check, checkpoint verify, output verify
- TaskCompleted: validation by task type
```

### R5 — Mandatory Cleanup

```
MANDATORY: Lead performs cleanup after team conclusion.
PROHIBITED: Teammate executing TeamDelete (team context may be wrong).
PROHIBITED: Leaving orphan teams in ~/.claude/teams/
```

### R6 — One Team per Session

```
Lead can manage only one team at a time.
For new team: cleanup current FIRST.
```

---

## L6 Execution Sequence

```
1. TeamCreate (lead) → define name, objective
2. TaskCreate × N (lead) → create tasks with correct blockedBy
3. Spawn teammates with explicit context (R1 — full context required)
4. Monitor (lead) → verify progress, redirect if necessary
5. Synthesis (lead) → consolidate results after tasks complete
6. Shutdown teammates → SendMessage shutdown_request to each one
7. TeamDelete → resource cleanup
```

---

## Recommended Models by Role

| Role                   | Model       | Justification                              |
|------------------------|-------------|--------------------------------------------|
| Orchestrator lead      | Sonnet 4.6  | Good coordination capacity, moderate cost  |
| Complex analysis       | Opus 4.6    | Complex reasoning tasks                    |
| Technical analysis     | Sonnet 4.6  | Balance of capability/cost                 |
| QA/validation          | Haiku 4.5   | Mechanical task, low cost                  |
| Code review            | Sonnet 4.6  | Good for code analysis                     |
| Research               | Sonnet 4.6  | Synthesis capability                       |

---

## Communication Between Teammates

```python
# Direct message (preferred)
SendMessage(type="message", recipient="reviewer",
    content="Implementation complete. Module X is ready for review. Check lib/governance.py.",
    summary="Implementation ready for review")

# Broadcast (use sparingly — expensive)
SendMessage(type="broadcast",
    content="CRITICAL: Shared dependency changed. All pause until resolution.",
    summary="Dependency conflict - pause work")

# Shutdown approval
SendMessage(type="shutdown_response", request_id="...", approve=True)
```

---

## Compliance and Enforcement Score

L6 tasks contribute to enforcement_score:

```python
# Positive contributions (+)
+ team_created = True          # +0.3
+ tasks_defined = True         # +0.2
+ context_provided = True      # +0.2
+ cleanup_done = True          # +0.1
+ no_file_conflicts = True     # +0.2

# Negative contributions (-)
- no_preconditions = -0.5      # L3+ tasks without verified state
- file_conflicts = -0.3        # File conflict detected
- no_cleanup = -0.2            # Team not cleaned up at end
```

---

## Troubleshooting

```bash
# Teammate not responding
Navigate to teammate → check output directly

# Stuck task
TaskUpdate({taskId: "X", status: "completed"})  # manually if truly done

# Orphan tmux session
tmux ls && tmux kill-session -t <session>

# Team not cleaned up
TeamDelete()  # via lead, after shutdown of all teammates
```

---

## Integration with CILA Router

The CILA router (`modules/hooks-routing/hooks/cila_router.py`) classifies tasks by level.
L6 tasks trigger multi-agent orchestration:

```python
# CILA classification triggers team creation
if cila_level == 6:
    # TeamCreate → TaskCreate → Spawn → Monitor → Synthesis → Cleanup
    pass
```

Routing heuristics for L6:
- Mentions `swarm`, `team`, `multi-agent`, `orchestrate agents`
- Mentions parallel execution with independent outputs
- Requires multiple specialized reviewers simultaneously

---

## Error Handling in Teams

```
Teammate error → Lead receives notification
Lead decides:
  - Retry teammate with adjusted prompt
  - Reassign task to different model
  - Mark task as failed and handle gracefully
  - Escalate to user if unrecoverable

NEVER: Let error propagate silently across team
ALWAYS: Lead maintains error log per teammate
```

---

## Anti-patterns to Avoid

| Anti-pattern                      | Problem                                    | Solution                        |
|-----------------------------------|--------------------------------------------|---------------------------------|
| Teammate delegating tasks         | Violates hierarchy (only lead delegates)   | Lead handles all delegation     |
| Shared mutable state              | Race conditions, conflicts                 | Strict file partitioning (R2)   |
| Implicit context inheritance      | Teammate makes wrong assumptions           | Explicit context in spawn (R1)  |
| No cleanup after team             | Orphan resources, state pollution          | Always TeamDelete at end (R5)   |
| Sequential tasks in parallel team | Blocking dependencies, deadlocks           | Model with blockedBy correctly  |
| Excessive broadcasts              | High token cost, noise                     | Use direct messages (preferred) |

---

## References

- Core governance: `core/rules/core-governance.md`
- CILA taxonomy: `modules/hooks-routing/config/cila-taxonomy.md`
- Strategy enforcer: `modules/hooks-routing/hooks/strategy_enforcer.py`
- Hook base: `lib/hook_base.py`
- Official documentation: https://code.claude.com/docs/en/agent-teams
