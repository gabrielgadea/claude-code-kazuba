---
name: hooks-kazuba-routing
description: |
  UserPromptSubmit routing via Rust binary. The hook-intent-router binary classifies
  incoming prompts using CILA (L0-L6) and injects CognitiveTechnique hints.
  Rust binary compiled in Phase 1D — this module is a placeholder scaffold.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
provides:
  hooks: []
  rust_binaries:
    - hook-intent-router
hook_events:
  - UserPromptSubmit
---

# hooks-kazuba-routing

UserPromptSubmit routing hook — Rust binary placeholder for Phase 1D.

## Contents

The `hook-intent-router` Rust binary will handle `UserPromptSubmit` events.
It classifies prompts by CILA level (L0-L6) and injects `CognitiveTechnique` hints
into the hook output.

See `hooks/README.md` for implementation details.

## Phase 1D

The Rust binary source will be added in Phase 1D of the kazuba expansion.
Until then, this module registers an empty hooks array for `UserPromptSubmit`.
