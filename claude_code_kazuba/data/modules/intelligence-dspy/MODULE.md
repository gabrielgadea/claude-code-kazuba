---
name: intelligence-dspy
description: |
  DSPy signatures and modules for cognitive intent classification.
  Includes cognitive architecture signatures, perception modules,
  and retrieval caches for Tantivy, Serena, and GitNexus.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
provides:
  intelligence:
    - dspy_signatures
    - dspy_perception
    - dspy_retrieval_caches
---

# intelligence-dspy

DSPy signatures and modules for cognitive intent classification and retrieval.

## Contents
- `signatures/cognitive_architectures.py` — DSPy signatures for cognitive architectures
- `signatures/perception.py` — Perception signatures for intent classification
- `modules/perception_module.py` — DSPy module for cognitive intent classification
- `modules/tantivy_retriever.py` — Tantivy FTS retrieval cache module
- `modules/serena_cache.py` — Serena MCP cache module
- `modules/gitnexus_cache.py` — GitNexus graph cache module

## Excluded
- `gate_bridge.py` — Pipeline-specific bridge excluded (ANTT-only dependency)
