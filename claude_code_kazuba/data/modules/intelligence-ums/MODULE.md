---
name: intelligence-ums
description: |
  Unified Memory System (UMS) — 5-layer CQRS memory cascade.
  L0 Working (in-process LRU), L1 SQLite, L2 Tantivy, L3 FAISS (optional),
  L4 Cipher MCP. Read-side facade for ESAA event-sourced architecture.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
provides:
  intelligence:
    - unified_memory_system
---

# intelligence-ums

Unified Memory System — single API for 5-layer memory cascade.
