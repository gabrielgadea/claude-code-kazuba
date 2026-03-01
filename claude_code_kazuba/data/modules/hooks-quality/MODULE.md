---
name: hooks-quality
description: |
  Quality and security gate hooks for Claude Code — prevents bad code,
  exposed secrets, PII leaks, and dangerous shell commands from entering
  the codebase. Forms the defensive layer of the hook pipeline.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
  - hooks-essential
provides:
  hooks:
    - quality_gate
    - secrets_scanner
    - pii_scanner
    - bash_safety
hook_events:
  - PreToolUse
---

# hooks-quality

Defensive hooks that enforce code quality and security standards.

## Contents

| Hook | Event | Tool Filter | Purpose |
|------|-------|-------------|---------|
| `quality_gate.py` | PreToolUse | Write, Edit | File size, debug code, docstring checks |
| `secrets_scanner.py` | PreToolUse | Write, Edit | API keys, tokens, credentials detection |
| `pii_scanner.py` | PreToolUse | Write, Edit | CPF, CNPJ, SSN, email, phone detection |
| `bash_safety.py` | PreToolUse | Bash | Dangerous command blocking |

## Configuration

All hooks use `lib.patterns` for pattern matching and `lib.hook_base.fail_open`
for fail-open behavior.

### quality_gate
- Max line count: 500 (configurable)
- Blocks debug code in production files (print, console.log, debugger)
- Warns about missing docstrings in public functions

### secrets_scanner
- Detects: API keys, AWS keys, GitHub tokens, OpenAI keys, private keys, passwords
- Whitelists: test files, .example files, placeholder values

### pii_scanner
- Country-configurable (BR default): CPF, CNPJ
- Also supports US (SSN) and EU (email, phone)
- Warns but does not block (exit 0)

### bash_safety
- Blocks: rm -rf /, chmod 777, curl|bash, dd to devices, fork bombs
- Allows safe patterns in approved directories
