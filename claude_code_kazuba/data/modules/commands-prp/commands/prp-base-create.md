---
name: prp-base-create
description: |
  PRP (Product Requirements Prompt) creation command. Researches the problem
  space, generates structured requirements, applies ultrathink for depth,
  and outputs a complete PRP document.
tags: ["prp", "requirements", "planning"]
triggers:
  - "/prp-create"
  - "/prp-new"
---

# /prp-base-create — Create Product Requirements Prompt

## Invocation

```
/prp-base-create [product/feature description]
```

## 4-Phase Workflow

### Phase 1: Research

1. Understand the problem domain.
2. Identify existing solutions and their limitations.
3. Define target users and their needs.
4. Identify technical constraints.
5. Document assumptions.

### Phase 2: Generate

Produce the PRP document with these sections:

```markdown
# PRP: [Product/Feature Name]

## Problem Statement
[What problem are we solving? Why does it matter?]

## Target Users
[Who benefits? What are their workflows?]

## Requirements

### Functional Requirements
- FR1: [requirement]
- FR2: [requirement]

### Non-Functional Requirements
- NFR1: Performance — [target]
- NFR2: Security — [constraint]
- NFR3: Usability — [standard]

## Technical Constraints
- [Stack, compatibility, infrastructure limits]

## Acceptance Criteria
- AC1: [measurable criterion]
- AC2: [measurable criterion]

## Out of Scope
- [Explicitly excluded features]

## Dependencies
- [External systems, APIs, data sources]

## Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| [risk] | H/M/L | H/M/L | [plan] |
```

### Phase 3: Ultrathink

Apply deep analysis to the generated PRP:
- Challenge each requirement: Is it necessary? Is it sufficient?
- Identify hidden requirements (error handling, edge cases, migration).
- Check for contradictions between requirements.
- Verify acceptance criteria are testable.
- Ensure non-functional requirements have specific targets.

### Phase 4: Output

Produce the final PRP file:
```bash
# Save to plans/ directory
plans/prp-{slug}-{date}.md
```

## Quality Checklist

- [ ] Problem statement is clear and specific
- [ ] All functional requirements are testable
- [ ] Non-functional requirements have numeric targets
- [ ] Acceptance criteria are binary (pass/fail)
- [ ] Out of scope is explicit (prevents scope creep)
- [ ] Risks have mitigations
- [ ] No undefined terms or acronyms
