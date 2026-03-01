---
name: plan-amplifier
description: |
  8-dimension plan amplification that transforms a basic plan (Pln1) into a
  comprehensive plan (Pln-squared). Evaluates Architecture, Security, Performance,
  Quality, Libraries, UI/UX, Data/ML, and PR Context dimensions.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["planning", "amplification", "architecture", "review"]
triggers:
  - "amplify plan"
  - "plan amplification"
  - "Pln squared"
  - "deep plan review"
  - "amplificar plano"
  - "plano amplificado"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
context: main
---

# Plan Amplifier

## When to Use

- You have a basic plan (Pln1) and need to ensure completeness
- Before starting L3+ implementations
- When the plan will be executed by someone else (clarity matters)
- When the plan involves multiple subsystems

## Core Principle

> A plan is only as good as its worst-reviewed dimension.
> Amplification forces you to consider what you missed.

## 8 Dimensions

### D1: Architecture

- Component boundaries and interfaces
- Data flow between components
- Dependency direction (who depends on whom)
- Extension points and plugin architecture
- Migration path from current state

**Key question**: Can each component be tested, deployed, and evolved independently?

### D2: Security

- Authentication and authorization model
- Input validation boundaries
- Secret management (no hardcoded secrets)
- Dependency vulnerability scan
- Principle of least privilege

**Key question**: What is the worst thing an attacker could do at each boundary?

### D3: Performance

- Expected load (requests/sec, data volume)
- Bottleneck identification (I/O, CPU, memory)
- Caching strategy
- Async vs sync decisions
- Resource limits and backpressure

**Key question**: What happens at 10x the expected load?

### D4: Quality

- Test strategy (unit, integration, e2e)
- Coverage targets per component
- Error handling and recovery
- Logging and observability
- Code review checklist

**Key question**: How will you know when something breaks in production?

### D5: Libraries

- Third-party dependency evaluation
- License compatibility
- Maintenance status (last commit, open issues)
- Alternative options considered
- Version pinning strategy

**Key question**: What happens if this library is abandoned tomorrow?

### D6: UI/UX

- User workflow mapping
- Error states and empty states
- Loading states and feedback
- Accessibility considerations
- Progressive disclosure of complexity

**Key question**: Can a new user complete the primary task without reading docs?

### D7: Data/ML

- Data schema and validation
- Migration strategy
- Backup and recovery
- Privacy and compliance (LGPD/GDPR)
- Model versioning and rollback

**Key question**: Can you restore to a known-good state within the SLA?

### D8: PR Context

- Commit strategy (atomic, squash, conventional)
- PR size management (< 400 lines per PR)
- Reviewer assignment and load balancing
- CI/CD pipeline requirements
- Release notes and changelog

**Key question**: Can the reviewer understand the "why" from the PR description alone?

## Scoring Matrix

Rate each dimension 0-5:

| Score | Meaning |
|-------|---------|
| 0 | Not addressed |
| 1 | Mentioned but no detail |
| 2 | Basic coverage, gaps visible |
| 3 | Adequate for the task |
| 4 | Thorough, edge cases considered |
| 5 | Production-grade, battle-tested |

### Amplification Thresholds

| Total Score (out of 40) | Grade | Action |
|--------------------------|-------|--------|
| 0-15 | F | Rewrite plan from scratch |
| 16-23 | C | Major gaps — amplify weak dimensions |
| 24-31 | B | Minor gaps — targeted improvements |
| 32-37 | A | Ready for execution |
| 38-40 | A+ | Over-engineered? Check for YAGNI |

## Workflow

1. **Score Pln1**: Rate each dimension 0-5 with brief justification.
2. **Identify gaps**: Any dimension < 3 must be amplified.
3. **Amplify**: For each gap, add specific details addressing the key question.
4. **Re-score**: Verify all dimensions >= 3.
5. **Output Pln-squared**: The amplified plan with scores and justifications.

## Output Format

```markdown
# Plan Amplification Report

## Scores
| Dimension | Pln1 | Pln2 | Delta | Notes |
|-----------|------|------|-------|-------|
| Architecture | 2 | 4 | +2 | Added component diagram |
| Security | 1 | 3 | +2 | Added auth model |
| ... | ... | ... | ... | ... |
| **Total** | **18** | **30** | **+12** | |

## Amplified Sections
[Details for each dimension that was amplified]
```
