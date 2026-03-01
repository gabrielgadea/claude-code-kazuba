---
name: verify
description: |
  Pre-PR verification command that invokes the verification-loop skill.
  Quick access to the full quality gate pipeline.
tags: ["verification", "quality", "pre-PR"]
triggers:
  - "/verify"
  - "/check"
---

# /verify — Pre-PR Verification

## Invocation

```
/verify [stack]
```

Where `stack` is one of: `python` (default), `rust`, `js`, `ts`.

## Behavior

This command invokes the `verification-loop` skill and runs all 6 phases:

1. Build
2. Type Check
3. Lint
4. Test
5. Security
6. Diff Review

## Quick Reference (Python)

```bash
# Phase 1: Build
pip install -e ".[dev]"

# Phase 2: TypeCheck
pyright lib/

# Phase 3: Lint
ruff check claude_code_kazuba/ tests/ scripts/ --fix

# Phase 4: Test
pytest tests/ --cov=claude_code_kazuba --cov-report=term-missing --tb=short

# Phase 5: Security
pip audit 2>/dev/null || echo "pip-audit not installed"

# Phase 6: Diff
git diff --stat
```

## Output

Prints the verification report from verification-loop skill.
Exits with pass/fail summary.
