---
name: aco-generators
description: |
  ACO N1 Generator system: library (auto-discover, catalog, quality scoring),
  learning (JSONL outcomes, effectiveness scoring, pattern extraction),
  and starter generators for common patterns (Rust/PyO3, pytest, FastAPI).
version: "1.0.0"
author: "Gabriel Gadea"
dependencies: []
provides:
  aco:
    - generator_library
    - generator_learning
    - gen_rust_module
    - gen_test_suite
    - gen_api_endpoint
---

# aco-generators

ACO N1 Generator system: library (auto-discover, catalog, quality scoring),
learning (JSONL outcomes, effectiveness scoring, pattern extraction),
and starter generators for common patterns.

## Files

- `src/aco/generators/library.py` -- Generator catalog and discovery
- `src/aco/generators/learning.py` -- Generator effectiveness tracking
- `src/aco/generators/gen_rust_module.py` -- Starter: Rust/PyO3 module skeleton
- `src/aco/generators/gen_test_suite.py` -- Starter: pytest test suite
- `src/aco/generators/gen_api_endpoint.py` -- Starter: FastAPI endpoint
