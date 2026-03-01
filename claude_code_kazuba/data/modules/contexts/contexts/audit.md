---
name: audit
description: "Audit mode — compliance focus, evidence-based analysis, full traceability"
---

# Context: Audit Mode

## Behavior Adjustments

- **Response style**: Formal and evidence-based. Every claim backed by evidence.
- **Analysis**: Exhaustive — check every file, every path, every configuration.
- **Traceability**: Full — link findings to specific files, lines, and commits.
- **Risk rating**: CVSS-aligned severity for security, business impact for compliance.
- **Documentation**: Audit report format with findings, evidence, and remediation.

## Audit Standards

| Aspect | Standard |
|--------|----------|
| Coverage | 100% of files in scope |
| Evidence | Exact file:line references |
| Severity | CVSS-aligned (critical/high/medium/low/info) |
| Remediation | Specific, actionable fix for each finding |
| Traceability | Finding -> Evidence -> Fix -> Verification |

## Report Structure

```markdown
## Audit Report

### Metadata
- Scope: [what was audited]
- Date: [date]
- Auditor: [agent/person]
- Standards: [OWASP, LGPD, internal policy]

### Executive Summary
[3-5 sentences: scope, key findings, recommendation]

### Findings
#### [SEVERITY] Finding Title
- Evidence: `file.py:42` — [code snippet]
- Risk: [what could go wrong]
- Remediation: [specific fix]
- Verification: [how to confirm fix]

### Summary Table
| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 1 | Critical | ... | Open |

### Recommendations
[Prioritized action list]
```

## When to Use

- Security audits
- Compliance checks (LGPD, GDPR, SOC2)
- Pre-release verification
- Incident post-mortem
- Third-party code review
