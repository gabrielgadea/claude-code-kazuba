---
name: dev
description: "Development mode — fast iteration, relaxed quality gates, terse responses"
---

# Context: Dev Mode

## Behavior Adjustments

- **Response style**: Terse and action-oriented. Skip explanations unless asked.
- **Quality gates**: Relaxed — 80% coverage sufficient, warnings are informational.
- **Commit frequency**: High — commit after each logical change.
- **Error handling**: Log and continue. Do not block on non-critical errors.
- **Testing**: Focus on happy path. Edge cases are secondary.
- **Documentation**: Minimal — code comments only. No formal docs.

## Quality Thresholds

| Gate | Threshold |
|------|-----------|
| Test coverage | >= 80% |
| Type check | Errors only (ignore warnings) |
| Lint | Auto-fix, ignore remaining |
| Security | Critical only |

## When to Use

- Rapid prototyping and exploration
- Local development iteration
- Proof-of-concept work
- Early-stage feature development

## When NOT to Use

- Code going to production
- Security-sensitive features
- Public API changes
- Anything that will be reviewed by others
