---
name: hooks-routing
description: |
  Routing, knowledge management, and compliance tracking hooks for Claude Code.
  CILA intent classification routes prompts by complexity (L0-L6), knowledge
  manager provides 3-tier context, and compliance tracker audits tool usage.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
  - hooks-essential
provides:
  hooks:
    - cila_router
    - knowledge_manager
    - compliance_tracker
hook_events:
  - UserPromptSubmit
  - PreToolUse
  - PostToolUse
---

# hooks-routing

Routing, knowledge, and compliance hooks for intelligent session management.

## Contents

| Hook | Event | Purpose |
|------|-------|---------|
| `cila_router.py` | UserPromptSubmit | CILA L0-L6 complexity classification and routing |
| `knowledge_manager.py` | PreToolUse | 3-tier knowledge injection (cache, project, external) |
| `compliance_tracker.py` | PostToolUse | Tool usage tracking and audit logging |

## Configuration

All hooks use `lib.performance.L0Cache` for fast classification caching
and `lib.hook_base.fail_open` for fail-open behavior.

### cila_router

CILA (Complexity-Informed Layered Architecture) classifies prompts into
7 complexity levels:

| Level | Name | Processing |
|-------|------|------------|
| L0 | Trivial | Direct answer, no tools needed |
| L1 | Simple | Single tool call |
| L2 | Standard | Multi-step with single tool type |
| L3 | Complex | Multi-tool coordination |
| L4 | Advanced | Planning + multi-tool + validation |
| L5 | Expert | Agent delegation recommended |
| L6 | Extreme | Full agent team orchestration |

### knowledge_manager

3-tier knowledge lookup:
1. Local cache (L0Cache, instant)
2. Project docs (CLAUDE.md, README, etc.)
3. External search (deferred to tools)

### compliance_tracker

Logs tool usage decisions for audit trail. Tracks:
- Tool invocation counts
- Block/allow ratios
- Compliance score over time
