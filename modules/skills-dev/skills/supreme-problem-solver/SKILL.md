---
name: supreme-problem-solver
description: |
  Last-resort problem solver with H0/H1/H2 escalation horizons. Forces scope
  amplification before giving up. Use when standard debugging has failed 3+ times.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["debugging", "problem-solving", "escalation", "last-resort"]
triggers:
  - "I'm stuck"
  - "nothing works"
  - "tried everything"
  - "last resort"
  - "supreme solver"
  - "estou travado"
  - "nada funciona"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
context: main
---

# Supreme Problem Solver

## When to Use

- Standard debugging has failed 3+ times on the same issue
- Circuit breaker "loop detection" has fired
- You suspect the problem is not where you are looking
- The fix keeps breaking something else

## Core Principle

> When you cannot solve a problem, you are looking at the wrong scope.
> Expand the scope until the problem dissolves.

## Escalation Horizons

### H0: Current Scope (5 min)

Confirm you understand the actual problem, not a symptom.

1. **State the problem** in one sentence. If you cannot, you do not understand it.
2. **Reproduce** the exact failure with a minimal case.
3. **Read the error** — the full error, not just the last line.
4. **Check assumptions**: Is the code you think is running actually running?
   - `which python3`, `git branch`, `git status`, `ls -la`
5. **Binary search**: Comment out half the code. Does the error persist?

If solved: done. If not: escalate to H1.

### H1: Expanded Scope (15 min)

The problem is not in your function — it is in the system.

1. **Trace the full call chain**: From entry point to error site.
2. **Check dependencies**: Version conflicts, stale caches, wrong env.
   ```bash
   pip list | grep suspect-package
   pip cache purge
   ```
3. **Check state**: Is the data what you think it is? Add assertions.
4. **Check timing**: Race conditions, async ordering, event loop state.
5. **Read upstream code**: The bug may be in a library you call.
6. **Git bisect**: Find the exact commit that introduced the regression.
   ```bash
   git bisect start HEAD last-known-good
   git bisect run pytest tests/failing_test.py
   ```

If solved: done. If not: escalate to H2.

### H2: Paradigm Shift (30 min)

The approach itself is wrong. Do not fix the code — replace the approach.

1. **Question the requirement**: Is this actually necessary? Can we avoid the problem entirely?
2. **List 3 alternative approaches**: Different library, different algorithm, different architecture.
3. **Prototype the simplest alternative**: 20 lines max, test if the core idea works.
4. **Cost analysis**: Is switching cheaper than continuing to debug?
5. **Consult external knowledge**: Search docs, issues, Stack Overflow for the exact error.
6. **Spike and discard**: Build a throwaway prototype to validate the new approach.

## Decision Matrix

| Signal | Horizon | Action |
|--------|---------|--------|
| Error message is clear | H0 | Fix the specific issue |
| Error is intermittent | H1 | Trace timing/state |
| Error changes with each fix | H1 | Check assumptions |
| 3+ failed fix attempts | H2 | Question the approach |
| Fix breaks other things | H2 | Architecture mismatch |
| No error, wrong output | H1 | Add assertions, trace data |
| Works locally, fails in CI | H1 | Environment diff |

## Anti-Patterns

- **Shotgun debugging**: Changing random things hoping something works. STOP. Think.
- **Ignoring the error**: "It works if I catch the exception." No. Fix the cause.
- **Tunnel vision**: Staring at the same 10 lines for 30 minutes. Zoom out.
- **Sunk cost**: "I've spent so long on this approach." Irrelevant. Switch if switching is cheaper.

## Output Format

After resolving, document:

```
PROBLEM: [one sentence]
HORIZON: H0 | H1 | H2
ROOT CAUSE: [what was actually wrong]
FIX: [what was done]
LESSON: [what to do differently next time]
TIME SPENT: [minutes]
```
