---
name: hooks-kazuba-subagent
description: |
  Sub-agent lifecycle hooks — skill injection at subagent start, and knowledge/execution
  capture at subagent stop. Ensures sub-agents inherit appropriate skills and their outputs
  are captured for learning.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
provides:
  hooks:
    - subagent_skill_injector
    - cipher_agent_output_capture
    - rlm_execution_capture
hook_events:
  - SubagentStart
  - SubagentStop
---

# hooks-kazuba-subagent

Sub-agent lifecycle hooks for skill injection and output capture.

## Contents

| Hook | Event | Async | Timeout | Purpose |
|------|-------|-------|---------|---------|
| `subagent_skill_injector.py` | SubagentStart | no | 5s | Inject relevant skills into sub-agent context |
| `cipher_agent_output_capture.py` | SubagentStop | yes | 10s | Capture sub-agent output to Cipher knowledge base |
| `rlm_execution_capture.py` | SubagentStop | yes | 5s | Capture execution metrics for RLM learning |
