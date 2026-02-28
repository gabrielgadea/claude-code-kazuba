---
name: debug-RCA
description: |
  Structured 6-step Root Cause Analysis debugging command. Guides through
  symptom capture, hypothesis generation, evidence collection, root cause
  identification, fix implementation, and regression prevention.
tags: ["debugging", "rca", "troubleshooting"]
triggers:
  - "/debug-RCA"
  - "/rca"
---

# /debug-RCA — Root Cause Analysis

## Invocation

```
/debug-RCA [error description or failing test]
```

## 6-Step Process

### Step 1: Capture Symptoms

Gather all observable symptoms before analyzing:

1. **Exact error message** (full stack trace, not summary).
2. **When it happens** (always, intermittent, after specific action).
3. **What changed** (recent commits, config changes, dependency updates).
4. **Environment** (OS, Python version, virtualenv, CI vs local).

Output: Symptom report.

### Step 2: Generate Hypotheses

List at least 3 possible causes, ranked by likelihood:

```
H1 (70%): [most likely cause based on symptoms]
H2 (20%): [alternative explanation]
H3 (10%): [unlikely but possible]
```

### Step 3: Collect Evidence

For each hypothesis, find evidence that confirms or refutes:

```bash
# Read the failing code
# Check recent git changes
git log --oneline -10
git diff HEAD~3

# Check environment
python3 --version
pip list | grep relevant-package

# Reproduce with minimal case
```

Eliminate hypotheses that contradict evidence.

### Step 4: Identify Root Cause

The root cause is NOT the error message. It is the earliest point in the
causal chain that, if changed, prevents the error.

```
Symptom: "KeyError: 'user_id'"
Proximate cause: Missing key in dictionary
Root cause: API response schema changed in v2.3, code assumes v2.2 schema
```

### Step 5: Implement Fix

1. Write a test that reproduces the root cause.
2. Implement the minimal fix that passes the test.
3. Run the full test suite to check for regressions.
4. Commit with message: `fix: [root cause description]`

### Step 6: Prevent Regression

1. Ensure the regression test stays in the suite.
2. Add defensive code if appropriate (input validation, assertions).
3. Update `tasks/lessons.md` with the pattern.
4. Consider if a hook or lint rule could catch this class of bug.

## Output Format

```markdown
## RCA Report

**Symptom**: [what was observed]
**Root Cause**: [what was actually wrong]
**Fix**: [what was changed]
**Prevention**: [how to avoid recurrence]
**Time**: [minutes spent]
**Horizon**: H0 (local) | H1 (system) | H2 (paradigm)
```
