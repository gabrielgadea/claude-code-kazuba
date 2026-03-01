---
name: agents-dev
description: |
  Development agent definitions — code review, security audit, and meta-orchestration.
  Each agent has a focused role with specific tools and model configuration.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies: []
provides:
  agents:
    - code-reviewer
    - security-auditor
    - meta-orchestrator
---

# agents-dev

Agent definitions for development workflows. Each agent is a focused specialist
with defined tool access and behavioral constraints.

## Contents

| Agent | Purpose | Model |
|-------|---------|-------|
| `code-reviewer` | Review code for bugs, security, performance, style | sonnet |
| `security-auditor` | OWASP Top 10, secrets, PII, dependency vulnerabilities | sonnet |
| `meta-orchestrator` | Create Claude Code infrastructure (hooks, skills, agents) | opus |
