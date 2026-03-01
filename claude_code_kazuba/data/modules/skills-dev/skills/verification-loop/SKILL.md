---
name: verification-loop
description: |
  6-phase pre-PR verification loop: build, typecheck, lint, test, security, diff.
  Runs all quality gates before code is committed or submitted for review.
  Supports Python, Rust, and JS/TS stacks.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["quality", "verification", "ci", "pre-commit"]
triggers:
  - "verify before PR"
  - "run verification"
  - "pre-PR check"
  - "quality gates"
  - "verificar antes do PR"
  - "rodar verificacao"
allowed-tools: Read, Bash, Glob, Grep
context: main
---

# Verification Loop

## When to Use

- Before creating a PR or merge request
- Before marking a task as complete
- After any L3+ refactoring
- When `/verify` command is invoked

## 6-Phase Verification

### Phase 1: Build

Verify the project compiles/installs without errors.

| Stack | Command |
|-------|---------|
| Python | `pip install -e ".[dev]" 2>&1` |
| Rust | `cargo build 2>&1` |
| JS/TS | `npm ci && npm run build 2>&1` |

**Pass criteria**: Exit code 0, no error output.

### Phase 2: Type Check

Static type analysis catches type mismatches before runtime.

| Stack | Command |
|-------|---------|
| Python | `pyright lib/ src/` |
| Rust | `cargo check` (included in build) |
| JS/TS | `npx tsc --noEmit` |

**Pass criteria**: Zero errors. Warnings are logged but do not block.

### Phase 3: Lint

Code style and common bug patterns.

| Stack | Command |
|-------|---------|
| Python | `ruff check lib/ tests/ scripts/ --fix` |
| Rust | `cargo clippy -- -D warnings` |
| JS/TS | `npx eslint . --fix` |

**Pass criteria**: Zero errors after auto-fix. Report any remaining issues.

### Phase 4: Test

Run the full test suite with coverage.

| Stack | Command |
|-------|---------|
| Python | `pytest tests/ --cov=claude_code_kazuba --cov-report=term-missing --tb=short` |
| Rust | `cargo test -- --test-threads=1` |
| JS/TS | `npm test -- --coverage` |

**Pass criteria**: All tests pass. Coverage meets minimum threshold (90% for Python).

### Phase 5: Security

Scan for known vulnerabilities and secret exposure.

| Stack | Command |
|-------|---------|
| Python | `pip audit` or `safety check` |
| Rust | `cargo audit` |
| JS/TS | `npm audit --production` |
| All | `git diff --cached -- '*.env' '*.key' '*.pem'` (must be empty) |

**Pass criteria**: No high/critical vulnerabilities. No secrets in diff.

### Phase 6: Diff Review

Final human-readable review of what will be committed.

```bash
git diff --stat
git diff --cached --stat
git log --oneline -5
```

**Pass criteria**: Changes are scoped to the task. No unrelated modifications.

## Workflow

1. Run phases 1-5 sequentially (each depends on previous passing).
2. On any failure: STOP, report the phase and error, fix before retrying.
3. After all pass: run Phase 6 (diff review) and present summary.
4. Output a verification report:

```
VERIFICATION REPORT
===================
Phase 1 (Build):     PASS
Phase 2 (TypeCheck): PASS
Phase 3 (Lint):      PASS (2 auto-fixed)
Phase 4 (Test):      PASS (47/47, 94% coverage)
Phase 5 (Security):  PASS
Phase 6 (Diff):      12 files changed, +340, -89

RESULT: ALL GATES PASSED — Ready for PR
```

## Failure Recovery

| Phase | Common Fix |
|-------|-----------|
| Build | Check imports, missing deps, Python version |
| TypeCheck | Add type annotations, fix `Any` escapes |
| Lint | Run auto-fix, then fix remaining manually |
| Test | Read failure output, fix logic or update test |
| Security | Update vulnerable dep, remove exposed secret |
| Diff | `git checkout` unrelated files, squash commits |
