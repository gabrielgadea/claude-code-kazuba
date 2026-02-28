---
name: prp-base-execute
description: |
  PRP execution command. Loads an existing PRP document, creates an
  implementation plan, executes it phase by phase, and verifies against
  acceptance criteria.
tags: ["prp", "execution", "implementation"]
triggers:
  - "/prp-execute"
  - "/prp-run"
---

# /prp-base-execute — Execute Product Requirements Prompt

## Invocation

```
/prp-base-execute <path-to-prp.md>
```

## 4-Phase Workflow

### Phase 1: Load PRP

1. Read the PRP document.
2. Extract all requirements (FR, NFR).
3. Extract acceptance criteria.
4. Extract constraints and dependencies.
5. Validate PRP completeness (run quality checklist).

### Phase 2: Plan

1. Decompose requirements into implementation tasks.
2. Order tasks by dependency.
3. Estimate effort per task (S/M/L/XL).
4. Create the implementation plan using code-first-planner.
5. Apply plan-amplifier for L3+ tasks.

### Phase 3: Implement

For each phase in the plan:
1. Load phase specification.
2. Write tests first (TDD from acceptance criteria).
3. Implement minimum code to pass.
4. Run verification-loop.
5. Commit phase.
6. `/clear` between phases.

### Phase 4: Verify

1. Run full test suite.
2. Check each acceptance criterion:
   ```
   AC1: [criterion] — PASS | FAIL
   AC2: [criterion] — PASS | FAIL
   ```
3. Check non-functional requirements:
   ```
   NFR1: Performance p95 < 100ms — MEASURED: 82ms — PASS
   NFR2: Coverage > 90% — MEASURED: 94% — PASS
   ```
4. Produce execution report.

## Output

```markdown
## PRP Execution Report

**PRP**: [name]
**Date**: [date]
**Phases**: [completed/total]

### Acceptance Criteria
| AC | Description | Status |
|----|------------|--------|
| AC1 | ... | PASS |
| AC2 | ... | PASS |

### Non-Functional Requirements
| NFR | Target | Measured | Status |
|-----|--------|----------|--------|
| NFR1 | <100ms | 82ms | PASS |

### Summary
- All AC passed: YES/NO
- All NFR met: YES/NO
- Test coverage: X%
- Total commits: N
```
