---
name: hooks-essential
description: |
  Essential hook infrastructure for Claude Code sessions — prompt enhancement,
  session status monitoring, and context preservation during compaction.
  These hooks form the nervous system of context management.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
provides:
  hooks:
    - prompt_enhancer
    - status_monitor
    - auto_compact
hook_events:
  - UserPromptSubmit
  - SessionStart
  - PreCompact
---

# hooks-essential

Core hooks that enhance, monitor, and preserve Claude Code sessions.

## Contents

| Hook | Event | Purpose |
|------|-------|---------|
| `prompt_enhancer.py` | UserPromptSubmit | Classifies intent and injects cognitive techniques |
| `status_monitor.sh` | SessionStart | Reports session info, git branch, pending TODOs |
| `auto_compact.sh` | PreCompact | Saves context checkpoint before compaction |

## Configuration

All hooks follow the fail-open pattern: internal errors never block Claude Code.

### prompt_enhancer

Classifies user prompts into 8 intent categories and injects relevant
cognitive techniques (chain_of_thought, structured_output, etc.) as
`additionalContext`.

### status_monitor

Reports session environment at startup: Python version, git branch,
project name, and pending TODO count.

### auto_compact

Preserves critical context state before compaction by writing a
checkpoint file that can be reloaded after compaction completes.
