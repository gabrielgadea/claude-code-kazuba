---
name: review
description: "Review mode — strict quality checks, comprehensive analysis, detailed responses"
---

# Context: Review Mode

## Behavior Adjustments

- **Response style**: Detailed and thorough. Explain reasoning.
- **Quality gates**: Strict — 90% coverage, zero warnings, full type check.
- **Analysis depth**: Comprehensive — check all dimensions (security, performance, style).
- **Suggestions**: Always provide specific fix code, not just problem description.
- **Documentation**: Verify docs match code. Flag any drift.

## Quality Thresholds

| Gate | Threshold |
|------|-----------|
| Test coverage | >= 90% per file |
| Type check | Zero errors AND zero warnings |
| Lint | Zero issues (no auto-fix escape) |
| Security | All severities reviewed |
| Complexity | Cyclomatic <= 10 |

## Review Checklist

- [ ] Correctness: Logic errors, edge cases, error handling
- [ ] Security: OWASP Top 10, input validation, secrets
- [ ] Performance: N+1 queries, unbounded growth, blocking calls
- [ ] Style: Naming, complexity, dead code, type annotations
- [ ] Tests: Coverage, edge cases, isolation, naming
- [ ] Docs: Synchronized with code changes

## When to Use

- Pre-merge code review
- Pull request analysis
- Quality audit of existing code
- Post-incident review
