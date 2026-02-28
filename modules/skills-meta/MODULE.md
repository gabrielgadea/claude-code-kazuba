---
name: skills-meta
description: |
  Meta-skills for creating and managing hooks, skills, and other Claude Code
  configuration artifacts. Use these skills to bootstrap new skills, debug hooks,
  and maintain the framework itself.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies: []
provides:
  skills:
    - hook-master
    - skill-master
    - skill-writer
---

# skills-meta

Meta-skills that operate on Claude Code infrastructure itself. These are the
skills you use to create, validate, and maintain other skills and hooks.

## Contents

| Skill | Purpose |
|-------|---------|
| `hook-master` | Create, validate, test, and debug Claude Code hooks |
| `skill-master` | Create and manage skills with proper frontmatter and structure |
| `skill-writer` | Concise 10-step skill creation workflow |
