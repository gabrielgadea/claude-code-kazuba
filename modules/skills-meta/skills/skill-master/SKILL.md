---
name: skill-master
description: |
  Meta-skill for creating and managing Claude Code skills. Reference for SKILL.md
  frontmatter, progressive disclosure tiers, skill types, naming conventions,
  and validation checklists.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["meta", "skills", "infrastructure", "reference"]
triggers:
  - "create skill"
  - "new skill"
  - "skill reference"
  - "skill template"
  - "criar skill"
  - "nova skill"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
context: main
---

# Skill Master

## Philosophy

> Skills are reusable knowledge packets. A good skill teaches Claude how to
> perform a task consistently, regardless of context window state.

## SKILL.md Frontmatter Reference

### Required Fields

```yaml
---
name: my-skill-name              # kebab-case, unique within module
description: |                   # Multi-line description
  What this skill does, when to use it, and what it produces.
---
```

### Optional Fields

```yaml
---
name: my-skill-name
description: |
  Detailed description here.
version: "1.0.0"                 # Semver
author: "Author Name"            # Creator
tags: ["category", "subcategory"] # For discovery and filtering
triggers:                        # Natural language patterns that activate this skill
  - "phrase in English"
  - "frase em Portugues"
allowed-tools: Read, Write, Edit, Bash  # Tools this skill needs
context: main                    # Context mode (main, subagent, any)
model: sonnet                    # Preferred model (opus, sonnet, haiku)
dependencies:                    # Other skills this depends on
  - other-skill-name
---
```

## Progressive Disclosure Tiers

Skills should be structured in layers so Claude can load only what it needs:

### L1: Metadata (frontmatter only)

The YAML frontmatter is always loaded. Keep it concise — name, description,
triggers, and tags. This is what Claude uses to decide whether to load the
full skill.

### L2: Definition (main body)

The markdown body after frontmatter. Contains:
- **When to Use**: Clear conditions for activation
- **Workflow**: Step-by-step procedure
- **Templates**: Code or text templates
- **Examples**: Concrete usage examples

### L3: References (external files)

For complex skills, split into:
```
skills/my-skill/
  SKILL.md           # L1 + L2 (main definition)
  references/        # L3 (loaded on demand)
    patterns.md
    examples.md
    config.yaml
```

## Skill Types

### 1. Simple Skill

Single SKILL.md file with inline instructions.
Best for: focused tasks with clear procedures.

```
skills/format-checker/
  SKILL.md           # Everything in one file
```

### 2. Reference Skill

SKILL.md with external reference files for depth.
Best for: complex domains needing extensive examples.

```
skills/api-designer/
  SKILL.md
  references/
    rest-patterns.md
    graphql-patterns.md
    openapi-template.yaml
```

### 3. Scripted Skill

Includes executable scripts as part of the skill.
Best for: skills that need validation or code generation.

```
skills/test-generator/
  SKILL.md
  scripts/
    generate_tests.py
    validate_coverage.py
```

### 4. Meta Skill

A skill that creates or manages other skills/hooks/agents.
Best for: infrastructure and framework maintenance.

```
skills/hook-master/
  SKILL.md           # Instructions for creating hooks
```

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Skill directory | kebab-case | `my-skill-name/` |
| Skill file | UPPERCASE | `SKILL.md` |
| Reference files | kebab-case | `api-patterns.md` |
| Script files | snake_case | `validate_skill.py` |
| Tags | lowercase | `["meta", "hooks"]` |
| Triggers | Natural language | `"create a new hook"` |

## Best Practices

1. **One skill, one concern**: Each skill should do one thing well.
2. **Triggers are discovery**: Write triggers as the user would type them (both EN and PT-BR).
3. **Workflow is king**: The step-by-step workflow is the most important section.
4. **Templates save tokens**: Provide copy-paste templates instead of lengthy descriptions.
5. **Examples ground understanding**: Always include at least one concrete example.
6. **Fail conditions**: Document what to do when the skill's approach does not work.
7. **Cross-references**: Link to related skills when they complement each other.
8. **Keep frontmatter lean**: Description should be 1-3 sentences, not paragraphs.

## Quick-Start Template

Use this template when creating a new skill from scratch:

```markdown
---
name: my-new-skill
description: |
  Brief description of what this skill does, when to use it,
  and what output it produces.
version: "1.0.0"
author: "Your Name"
tags: ["category"]
triggers:
  - "english trigger phrase"
  - "frase gatilho em portugues"
allowed-tools: Read, Write, Edit, Bash
context: main
---

# My New Skill

## When to Use

Activate this skill when [conditions].

## Workflow

1. **Step One** -- Description of first action.
2. **Step Two** -- Description of second action.
3. **Step Three** -- Description of third action.

## Output Format

Describe expected output format or template.

## Failure Modes

- **Condition A**: Recovery action.
- **Condition B**: Escalation path.

## Checklist

- [ ] Step 1 complete
- [ ] Step 2 complete
- [ ] Output validated
```

## Validation Checklist

Before shipping a skill, verify:

```
[ ] Frontmatter has `name` and `description` (required)
[ ] Name matches directory name (kebab-case)
[ ] Description is clear and actionable (1-3 sentences)
[ ] Triggers cover both EN and PT-BR phrases
[ ] Workflow has numbered steps (not just prose)
[ ] At least one concrete example
[ ] Tools listed in `allowed-tools` match what workflow needs
[ ] No broken cross-references
[ ] File size < 15k tokens (fits in one context load)
[ ] Tested: follow the skill yourself and verify it works
```
