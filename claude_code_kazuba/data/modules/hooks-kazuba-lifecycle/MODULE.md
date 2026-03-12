---
name: hooks-kazuba-lifecycle
description: |
  Session teardown and compaction hooks — transcript analysis, session finalization,
  ACO evolution, generator learning, DSPy optimization, cost tracking, observer loop,
  and post-compact reinjection of critical rules.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
  - hooks-kazuba-session
provides:
  hooks:
    - stop_transcript_hook
    - session_finalizer
    - aco_evolution_hook
    - generator_learning_hook
    - dspy_session_optimizer
    - cost_tracker
    - observer_learning_loop
    - post_compact_reinjector
hook_events:
  - Stop
  - PreCompact
---

# hooks-kazuba-lifecycle

Session teardown and compaction lifecycle hooks.

## Contents

| Hook | Event | Async | Timeout | Purpose |
|------|-------|-------|---------|---------|
| `stop_transcript_hook.py` | Stop | yes | 15s | Analyze session transcript for learning |
| `session_finalizer.py` | Stop | yes | 10s | Finalize session state |
| `aco_evolution_hook.py` | Stop | yes | 10s | Persist ACO evolution checkpoint |
| `generator_learning_hook.py` | Stop | yes | 10s | Capture generator outcomes for learning |
| `dspy_session_optimizer.py` | Stop | yes | 10s | Optimize DSPy session parameters |
| `cost_tracker.py` | Stop | yes | 10s | Track session token/cost metrics |
| `observer_learning_loop.py` | Stop | yes | 10s | Run observer learning cycle |
| `post_compact_reinjector.py` | PreCompact | no | 10s | Reinject CODE-FIRST + CILA rules after compaction |
