---
name: orchestrate
description: |
  Multi-agent orchestration command with modes for feature development, bugfix,
  refactoring, and security audits. Coordinates specialized agents.
tags: ["orchestration", "multi-agent", "workflow"]
triggers:
  - "/orchestrate"
  - "/orch"
---

# /orchestrate — Multi-Agent Orchestration

## Invocation

```
/orchestrate <mode> [description]
```

### Modes

| Mode | Agents Involved | Workflow |
|------|----------------|----------|
| `feature` | meta-orchestrator, code-reviewer | Plan, implement, review |
| `bugfix` | code-reviewer, security-auditor | Diagnose, fix, audit |
| `refactor` | code-reviewer | Analyze, restructure, verify |
| `security` | security-auditor, code-reviewer | Audit, remediate, verify |

## Mode: feature

1. **Plan**: Analyze the requirement. Create implementation plan.
2. **Implement**: Execute plan phases with TDD.
3. **Review**: code-reviewer agent scans for bugs, style, performance.
4. **Fix**: Address review findings.
5. **Verify**: Run verification-loop.
6. **Complete**: Smart-commit and report.

## Mode: bugfix

1. **Diagnose**: Run debug-RCA to identify root cause.
2. **Fix**: Implement minimal fix with regression test.
3. **Audit**: security-auditor checks the fix does not introduce vulnerabilities.
4. **Verify**: Run verification-loop.
5. **Complete**: Smart-commit and report.

## Mode: refactor

1. **Analyze**: Read current code, identify improvement opportunities.
2. **Plan**: Define refactoring scope and safety criteria.
3. **Implement**: Restructure in small, tested increments.
4. **Review**: code-reviewer verifies behavior preservation.
5. **Verify**: Full test suite must pass with no regressions.
6. **Complete**: Smart-commit and report.

## Mode: security

1. **Audit**: security-auditor performs full scan.
2. **Triage**: Prioritize findings by severity.
3. **Remediate**: Fix critical and high issues.
4. **Review**: code-reviewer verifies fixes.
5. **Re-audit**: Confirm issues are resolved.
6. **Report**: Produce security audit report.

## Output

Each orchestration produces:

```markdown
## Orchestration Report

**Mode**: feature | bugfix | refactor | security
**Description**: [what was done]
**Agents Used**: [list]
**Phases Completed**: [N/N]
**Findings**: [summary]
**Commits**: [list of commit hashes]
**Status**: COMPLETE | INCOMPLETE (reason)
```
