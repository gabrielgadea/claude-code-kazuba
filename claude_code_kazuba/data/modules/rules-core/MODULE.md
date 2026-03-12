# Module: rules-core

**Version:** 1.0.0
**Description:** Core governance rules for the Cognitive Code Orchestrator — CODE-FIRST cycle, DISCOVER protocol, PLAN-AS-CODE auditing, and zero-hallucination constraints.

## Dependencies

None (foundation module — install first)

## Hook Events

None (rules only — no hooks registered)

## Included Rules

| File | Purpose |
|------|---------|
| `rules/core/00-core-governance.md` | CODE-FIRST cycle (P100) — DISCOVER→CREATE→EXECUTE→EVALUATE→REFINE→PERSIST |
| `rules/core/plan-as-code.md` | PLAN-AS-CODE (P98) — mandatory symbol auditing before writing any spec |

## Usage

These rules are automatically loaded by Claude Code via the `rules/` directory.
They establish the foundational operating principles for any project using the kazuba framework.

## Notes

- `00-core-governance.md` is domain-generic. Domain-specific rules (e.g. LexCore, ANTT) extend it.
- `plan-as-code.md` mandates DISCOVER before writing any spec referencing external symbols.
