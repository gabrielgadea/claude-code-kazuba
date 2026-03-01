---
name: plan-execution
description: |
  6-phase plan execution framework with checkpoints, recovery strategies, and
  knowledge capture. Takes a plan from paper to production with structured
  quality gates at each phase.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["planning", "execution", "checkpoints", "recovery"]
triggers:
  - "execute plan"
  - "run plan"
  - "plan execution"
  - "start implementation"
  - "executar plano"
  - "rodar plano"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
context: main
---

# Plan Execution

## When to Use

- You have a validated plan (Pln1 or Pln-squared) ready for implementation
- Multi-phase projects requiring structured progress tracking
- When checkpoint/recovery is important (long-running tasks)

## 6-Phase Execution

### Phase 1: Discovery

**Goal**: Understand the current state before changing anything.

1. Read the plan file completely.
2. Identify all source files that will be modified.
3. Read each source file to understand current state.
4. Identify dependencies between plan items.
5. Note any discrepancies between plan assumptions and reality.

**Output**: Discovery report with file list, dependency map, and assumption check.

**Checkpoint**: `checkpoints/discovery_{plan_id}.toon`

### Phase 2: Context Loading

**Goal**: Load all necessary context without exceeding window limits.

1. Prioritize files by modification scope (most-changed first).
2. Load only relevant sections (use line ranges, not full files).
3. Build a mental model of the architecture.
4. Identify the critical path (longest dependency chain).

**Output**: Context summary with key structures and interfaces.

**Checkpoint**: `checkpoints/context_{plan_id}.toon`

### Phase 3: Phased Execution

**Goal**: Implement changes in small, validated increments.

For each phase in the plan:
1. Read the phase specification.
2. Write tests first (TDD).
3. Implement the minimum code to pass tests.
4. Run the verification loop (build, typecheck, lint, test).
5. Commit with a descriptive message.
6. Update the plan status.

**Execution rules**:
- One phase at a time. Never work on two phases simultaneously.
- If a phase depends on another, verify the dependency is complete.
- If a phase is too large for one context window, split it.
- `/clear` between phases to reclaim context.

**Checkpoint**: `checkpoints/phase_{plan_id}_{phase_num}.toon`

### Phase 4: QA (Quality Assurance)

**Goal**: Verify the full implementation meets all acceptance criteria.

1. Run the complete test suite.
2. Run the verification loop (all 6 phases).
3. Check each acceptance criterion from the plan.
4. Test edge cases explicitly listed in the plan.
5. Verify no regressions in existing functionality.

**Output**: QA report with pass/fail for each criterion.

**Checkpoint**: `checkpoints/qa_{plan_id}.toon`

### Phase 5: Knowledge Capture

**Goal**: Document what was learned for future reference.

1. Update documentation affected by changes.
2. Record any deviations from the original plan (and why).
3. Note any technical debt introduced (and why it was acceptable).
4. Update lessons learned (`tasks/lessons.md`).
5. Update skills if a new pattern was discovered.

**Output**: Knowledge capture document.

### Phase 6: Completion

**Goal**: Close out the task cleanly.

1. Final commit with all changes.
2. Create PR (if applicable) with summary.
3. Update task status to complete.
4. Notify stakeholders (if applicable).
5. `/clear` to free context.

## Checkpoint Schema

```python
@dataclass(frozen=True)
class Checkpoint:
    plan_id: str
    phase: str           # discovery, context, phase_N, qa, complete
    timestamp: str       # ISO 8601
    status: str          # in_progress, passed, failed, skipped
    summary: str         # Brief description of state
    files_modified: list[str]
    tests_passed: int
    tests_failed: int
    coverage: float
    notes: str
```

Serialized as msgpack (`.toon` format).

## Recovery Strategies

| Failure | Recovery |
|---------|----------|
| Test fails in Phase 3 | Fix the test or implementation. Do not skip. |
| Context overflow mid-phase | Checkpoint to file, `/clear`, reload from checkpoint. |
| Plan assumption was wrong | Update plan, re-score affected dimensions, continue. |
| Dependency not met | Go back to dependent phase, complete it first. |
| External service down | Mock the service, continue. Fix integration later. |
| Phase too large | Split into sub-phases. Each must independently pass. |
| Lost context between sessions | Load from latest checkpoint. Verify state matches. |

## Status Tracking

Update the plan file's frontmatter after each phase:

```yaml
status: in_progress
current_phase: 3
phases_completed: [1, 2]
phases_remaining: [3, 4, 5, 6]
last_checkpoint: checkpoints/phase_plan01_2.toon
```
