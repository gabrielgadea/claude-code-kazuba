---
name: hooks-kazuba-session
description: |
  Session lifecycle hooks for Claude Code — Rust accelerator setup, learning system
  initialization, guidance injection, context monitoring, index warmup, and workflow
  tracking. These hooks fire at SessionStart to establish the operational environment.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
provides:
  hooks:
    - rust_accelerator_setup
    - learning_system_session_startup
    - guidance_injection_hook
    - context_monitor
    - context_warning_display
    - warmup_index
    - lexcore_workflow_tracker
hook_events:
  - SessionStart
---

# hooks-kazuba-session

Session initialization hooks that establish the cognitive runtime environment.

## Contents

| Hook | Event | Async | Timeout | Purpose |
|------|-------|-------|---------|---------|
| `rust_accelerator_setup.py` | SessionStart | yes | 15s | Initialize Rust accelerator bindings (PyO3) |
| `learning_system_session_startup.py` | SessionStart | yes | 10s | Bootstrap learning system |
| `guidance_injection_hook.py` | SessionStart | no | 5s | Inject guidance rules |
| `context_monitor.py` | SessionStart | yes | 15s | Monitor context window utilization |
| `context_warning_display.py` | SessionStart | yes | 3s | Display context budget warnings |
| `warmup_index.py` | SessionStart | yes | 15s | Warm up Tantivy search index |
| `lexcore_workflow_tracker.py` | SessionStart | yes | 10s | Track workflow state (adapted, generic) |

## Adaptations

- `lexcore_workflow_tracker.py`: Adapted from `analise/.claude/hooks/planning/antt_workflow_tracker.py`.
  ANTT-specific process numbers (50500/50505), skill names, and phase definitions replaced with
  generic Kazuba equivalents. Process number pattern generalized to `\d{5,6}\.\d{6}/\d{4}-\d{2}`.
