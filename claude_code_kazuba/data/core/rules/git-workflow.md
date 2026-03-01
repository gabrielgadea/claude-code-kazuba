# Git Workflow Rules

Git is the safety net. Use it deliberately and consistently.
Every commit is a checkpoint you can recover from.

---

## Branch Naming Conventions

Use prefixes that describe the type of work:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feat/` | New feature | `feat/user-authentication` |
| `fix/` | Bug fix | `fix/login-timeout` |
| `refactor/` | Code restructuring | `refactor/extract-payment-module` |
| `docs/` | Documentation only | `docs/api-reference` |
| `test/` | Adding or fixing tests | `test/auth-edge-cases` |
| `chore/` | Tooling, CI, dependencies | `chore/upgrade-pytest-8` |
| `hotfix/` | Urgent production fix | `hotfix/security-patch-cve-2024` |

- Use kebab-case: `feat/my-feature`, not `feat/myFeature` or `feat/my_feature`.
- Keep branch names under 50 characters.
- Include ticket/issue number when applicable: `fix/123-login-timeout`.

---

## Commit Message Format

Follow Conventional Commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

- **type**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`, `style`.
- **scope**: Module or area affected (e.g., `auth`, `api`, `core`).
- **description**: Imperative mood, lowercase, no period. Under 72 characters.
  - Good: `feat(auth): add JWT refresh token rotation`
  - Bad: `Added JWT refresh tokens.`
- **body**: Explain the WHY, not the WHAT. Wrap at 72 characters.
- **footer**: `Closes #123`, `BREAKING CHANGE: ...`, `Co-Authored-By: ...`.

---

## Small, Atomic Commits

- **One logical change per commit.** Do not mix feature + refactor + fix in one commit.
- **Commit early, commit often.** Small commits are easier to review, revert, and bisect.
- **Commit BEFORE risky changes.** `git checkout` is instant recovery.
- **Each commit should leave the project in a working state.** Tests pass, builds succeed.
- **Avoid WIP commits** on shared branches. Use `--fixup` and interactive rebase locally.

---

## Pull Request Workflow

- **One PR per feature or fix.** Keep PRs focused and reviewable.
- **Small PRs preferred.** Under 400 lines of diff. Split large changes into a stack.
- **PR description**: What changed, why, and how to test.
- **Self-review before requesting review.** Read your own diff first.
- **Address all review comments.** Do not merge with unresolved threads.
- **Squash merge** for feature branches (clean main history).
- **Rebase merge** for long-lived branches (preserve commit history).

---

## Force Push Policy

- **NEVER force-push to main/master.** This is a hard rule.
- **NEVER force-push to shared branches** without explicit team approval.
- **Force-push to personal feature branches** only when:
  - Rebasing onto latest main.
  - Squashing fixup commits.
  - Amending the last commit (before review).
- **Use `--force-with-lease`** instead of `--force` to prevent overwriting others' work.

---

## Branch Protection

- **main/master is always deployable.** Never commit directly.
- **Require PR reviews** before merging (minimum 1 approval).
- **Require CI passing** before merge.
- **Delete branches after merge.** Keep the branch list clean.
- **Use tags for releases.** Semantic versioning: `v1.2.3`.

---

## Git Hygiene

- **Write meaningful messages.** "fix" and "update" are not meaningful.
- **Do not commit generated files** (build artifacts, compiled code, lock files vary by ecosystem).
- **Do not commit secrets.** Use `.gitignore` and pre-commit hooks.
- **Review `git diff` before every commit.** Know exactly what you are committing.
- **Use `.gitignore` aggressively.** IDE files, OS files, build directories, temp files.
