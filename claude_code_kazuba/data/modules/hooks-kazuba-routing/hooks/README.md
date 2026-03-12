# hooks-kazuba-routing Rust Binary Placeholder

The `hook-intent-router` Rust binary handles UserPromptSubmit events.
It will be compiled and registered in Phase 1D.

## Planned behavior

1. Read hook event JSON from stdin
2. Classify prompt via CILA (L0-L6): Direct / PAL / Tool-Augmented / Pipelines / Agent Loops / Self-Modifying / Multi-Agent
3. Inject `CognitiveTechnique` hint into `hookSpecificOutput`
4. Exit 0 (ALLOW) — routing is advisory, never blocking

## Source location (Phase 1D)

The Rust source will live in `src/hooks/intent_router/` within the kazuba-rust-core crate.
PyO3 bindings are not needed — the binary reads stdin/stdout directly per Claude Code hook protocol.
