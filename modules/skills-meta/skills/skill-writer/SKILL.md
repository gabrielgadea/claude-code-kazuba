---
name: skill-writer
description: |
  Concise 10-step workflow for creating Claude Code skills. Quick-reference
  guide that gets you from idea to validated skill in minimal steps.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["meta", "skills", "workflow", "quick-start"]
triggers:
  - "write skill"
  - "quick skill"
  - "skill workflow"
  - "escrever skill"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
context: main
---

# Skill Writer — 10-Step Workflow

## Steps

### 1. Name It

Choose a kebab-case name that describes the action: `verb-noun` or `noun-modifier`.
Good: `code-reviewer`, `plan-amplifier`, `hook-master`.
Bad: `my-tool`, `utils`, `helper`.

### 2. Create Directory

```bash
mkdir -p modules/{module-name}/skills/{skill-name}
```

### 3. Write Frontmatter

```yaml
---
name: {skill-name}
description: |
  One sentence: what it does.
  One sentence: when to use it.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["category"]
triggers:
  - "english trigger phrase"
  - "frase gatilho portugues"
allowed-tools: Read, Write, Edit, Bash
context: main
---
```

### 4. Define "When to Use"

Write 3-5 bullet points. Be specific about conditions, not vague.

### 5. Write the Workflow

Numbered steps, each with a clear action and expected output.
This is the core of the skill — make it unambiguous.

### 6. Add Templates

Provide copy-paste code/text blocks. Templates save tokens and ensure consistency.

### 7. Add Examples

At least one concrete before/after example showing the skill in action.

### 8. Document Failure Modes

What to do when it does not work. Escalation paths.

### 9. Validate

Run through the checklist:
- Frontmatter has `name` + `description`
- Triggers cover EN + PT-BR
- Workflow has numbered steps
- At least one example
- File size < 15k tokens

### 10. Test It

Follow your own skill as if you were Claude encountering it for the first time.
If any step is ambiguous, rewrite it.
