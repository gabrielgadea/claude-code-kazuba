---
name: smart-commit
description: |
  Intelligent commit command that reads the diff, generates a conventional
  commit message, and creates the commit. Supports conventional commits format.
tags: ["git", "commit", "automation"]
triggers:
  - "/smart-commit"
  - "/commit"
---

# /smart-commit — Intelligent Commit

## Invocation

```
/smart-commit [optional: additional context]
```

## Workflow

### 1. Analyze Changes

```bash
git status
git diff --staged
git diff  # unstaged changes
```

If nothing is staged, stage all tracked modified files:
```bash
git add -u
```

### 2. Classify Change Type

| Type | When |
|------|------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring, no behavior change |
| `test` | Adding or modifying tests |
| `docs` | Documentation only |
| `chore` | Build, CI, tooling changes |
| `perf` | Performance improvement |
| `style` | Formatting, no logic change |

### 3. Generate Message

Format: `type(scope): description`

Rules:
- Type is lowercase from the table above.
- Scope is the primary module/file affected (optional).
- Description is imperative mood, lowercase, no period.
- Max 72 characters for the subject line.
- Body (optional) explains WHY, not WHAT.

### 4. Create Commit

```bash
git commit -m "$(cat <<'EOF'
type(scope): brief description

Longer explanation of why this change was needed.
Details about the approach chosen.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### 5. Verify

```bash
git log --oneline -1
git show --stat HEAD
```

## Examples

```
feat(hooks): add PreToolUse path validation hook
fix(relay): correct webhook payload format for zeroclaw
refactor(core): extract checkpoint logic into separate module
test(skills): add frontmatter validation tests for Phase 6
docs(readme): update installation instructions
chore(ci): add pyright to GitHub Actions workflow
```

## Rules

- Never commit `.env`, credentials, or large binary files.
- Always verify the diff before committing.
- If changes span multiple concerns, split into multiple commits.
- Include `Co-Authored-By` when Claude participated in the work.
