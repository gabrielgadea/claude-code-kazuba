---
name: hooks-kazuba-post
description: |
  PostToolUse hooks across 5 matchers — quality gates, knowledge capture, incremental
  indexing, SIAC post-validation, QA loop, DSPy quality gates, PGCC warming, compliance
  collection, failure recovery, ACO goal tracking, and RLM execution capture.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
  - hooks-kazuba-pre
provides:
  hooks:
    - post_quality_gate
    - cipher_knowledge_capture
    - incremental_indexer
    - siac_hook_entry
    - siac_orchestrator
    - qa_hook_entry
    - dspy_quality_gates
    - pgcc_warmer
    - compliance_collector_entry
    - failure_recovery_orchestrator
    - aco_goal_tracker_hook
    - rlm_execution_capture_post
hook_events:
  - PostToolUse
---

# hooks-kazuba-post

PostToolUse hooks providing quality assurance, knowledge persistence, and metrics.

## Contents

| Hook | Matcher | Async | Timeout | Purpose |
|------|---------|-------|---------|---------|
| `post_quality_gate.py` | Write\|Edit\|MultiEdit | yes | 20s | Run ruff/pyright quality gate |
| `cipher_knowledge_capture.py` | Write\|Edit\|MultiEdit | yes | 10s | Capture knowledge to Cipher |
| `incremental_indexer.py` | Write\|Edit\|MultiEdit | yes | 5s | Reindex changed files in Tantivy |
| `siac_hook_entry.py` | Write\|Edit\|MultiEdit | yes | 5s | SIAC post-write entry point |
| `siac_orchestrator.py` | Write\|Edit\|MultiEdit | yes | 10s | SIAC motors orchestration |
| `qa_hook_entry.py` | Write\|Edit\|MultiEdit | yes | 5s | QA loop entry point |
| `dspy_quality_gates.py` | Write\|Edit\|MultiEdit | yes | 10s | DSPy-based quality gates |
| `pgcc_warmer.py` | Write\|Edit\|MultiEdit | yes | 30s | Warm PGCC cache |
| `compliance_collector_entry.py` | Task\|Bash\|Write\|Edit | yes | 5s | Record compliance metrics |
| `failure_recovery_orchestrator.py` | Task\|Bash | yes | 10s | Orchestrate failure recovery |
| `aco_goal_tracker_hook.py` | Task\|Bash\|Skill | yes | 10s | Track ACO goal progress |
| `rlm_execution_capture_post.py` | Task | yes | 5s | Capture RLM execution metrics |
