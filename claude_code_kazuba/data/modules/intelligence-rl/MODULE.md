---
name: intelligence-rl
description: |
  Reinforcement Learning system for Claude Code session optimization.
  TD-learning with Q-table, policy selection, reward computation,
  and tiered memory (working + short-term).
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
provides:
  intelligence:
    - rl_td_learning
    - rl_policy
    - rl_memory
---

# intelligence-rl

Reinforcement Learning modules for adaptive session optimization.

## Key Change from Source
- `ANTTTaskType` renamed to `TaskType` for domain independence
- All enum values preserved (backward-compatible serialization)
