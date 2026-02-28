# Migration Guide

For users who already have an existing `.claude/` configuration and want to
adopt claude-code-kazuba.

## Overview

If you already have a `.claude/` directory with custom `CLAUDE.md`, `settings.json`,
hooks, skills, or agents, this guide helps you migrate to the framework while
preserving your customizations.

## Step 1: Backup Existing Config

Before any changes, create a complete backup:

```bash
# Create timestamped backup
cp -r .claude/ .claude.backup-$(date +%Y%m%d-%H%M%S)/

# Verify backup
diff -r .claude/ .claude.backup-*/
```

Keep this backup until migration is fully validated.

## Step 2: Detect Current Setup

Inventory your existing configuration:

```bash
# List all files in .claude/
find .claude/ -type f | sort

# Check for custom hooks
ls .claude/hooks/ 2>/dev/null

# Check for custom skills
ls .claude/skills/ 2>/dev/null

# Check for custom agents
ls .claude/agents/ 2>/dev/null

# Check for custom commands
ls .claude/commands/ 2>/dev/null

# Review current settings.json
cat .claude/settings.json 2>/dev/null

# Review current CLAUDE.md
head -50 .claude/CLAUDE.md 2>/dev/null
```

Take note of:
- Custom hooks and their registered events
- Custom skills, agents, and commands
- Any `settings.json` customizations (permissions, env vars)
- Custom rules or instructions in CLAUDE.md

## Step 3: Select and Install a Preset

Choose the preset that best matches your needs:

| Preset | What you get |
|--------|-------------|
| `minimal` | Core only (CLAUDE.md template, settings, rules) |
| `standard` | Core + essential hooks + planning skills + meta skills + contexts |

```bash
# Clone the framework (if not already done)
git clone https://github.com/gabrielgadea/claude-code-kazuba.git
cd claude-code-kazuba

# Install with your chosen preset
python scripts/install.py --preset standard --target /path/to/your/project
```

The installer will:
- Resolve module dependencies
- Render templates with your project variables
- Create a new `.claude/` directory structure
- Register hooks in `settings.json`

## Step 4: Merge Custom Rules and Hooks

### Custom CLAUDE.md Rules

If you had custom rules in CLAUDE.md, add them to the generated file:

```bash
# Compare your backup with the generated file
diff .claude.backup-*/CLAUDE.md .claude/CLAUDE.md

# Add your custom rules to the appropriate section
# The generated CLAUDE.md has clearly marked sections for custom additions
```

### Custom Hooks

For each custom hook from your backup:

1. Copy the hook script to `.claude/hooks/`
2. Add the hook registration to `settings.json`

```bash
# Copy custom hook
cp .claude.backup-*/hooks/my_custom_hook.py .claude/hooks/

# Add to settings.json hooks section (merge manually or use jq)
# Example: add to PreToolUse array
```

Or better: create a custom module for your hooks (see `docs/CREATING_MODULES.md`).

### Custom Skills, Agents, Commands

Copy directly — the framework does not modify these directories:

```bash
cp -r .claude.backup-*/skills/my-custom-skill/ .claude/skills/
cp -r .claude.backup-*/agents/my-custom-agent.md .claude/agents/
cp -r .claude.backup-*/commands/my-command.md .claude/commands/
```

### Custom settings.json Overrides

For personal overrides that should not be committed, use `settings.local.json`:

```json
{
  "permissions": {
    "allow": ["my-custom-tool"]
  },
  "env": {
    "MY_CUSTOM_VAR": "value"
  }
}
```

## Step 5: Validate Installation

Run the validation suite:

```bash
# Check that all expected files exist
ls -la .claude/CLAUDE.md .claude/settings.json

# Check that hooks are registered
python3 -c "
import json
with open('.claude/settings.json') as f:
    settings = json.load(f)
print('Registered hook events:', list(settings.get('hooks', {}).keys()))
"

# Test hooks (if installed)
echo '{"session_id":"test","cwd":".","hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"test.py","content":"x=1"}}' | python3 .claude/hooks/quality_gate.py

# Start a Claude Code session and verify
claude
```

## Common Migration Scenarios

### Scenario A: Clean start (no existing .claude/)

Simply install a preset. No migration needed:

```bash
python scripts/install.py --preset standard --target .
```

### Scenario B: Only CLAUDE.md customizations

1. Install the `minimal` preset
2. Merge your custom rules into the generated CLAUDE.md
3. Your existing hooks/skills/agents remain untouched

### Scenario C: Custom hooks that overlap with framework hooks

1. Install `standard` preset (which includes hooks-essential)
2. Compare your hooks with framework hooks
3. If functionality overlaps, prefer the framework hook (it is tested and maintained)
4. If your hook adds unique functionality, keep it alongside framework hooks
5. Register both in `settings.json` — hooks are executed in array order

### Scenario D: Team with shared .claude/ configuration

1. Install the framework in the project repository
2. Each team member uses `settings.local.json` for personal overrides
3. Commit `.claude/` to version control (except `settings.local.json`)
4. Add `settings.local.json` to `.gitignore`

### Scenario E: Multiple projects, same configuration

1. Fork claude-code-kazuba and customize modules
2. Use the same preset across all projects
3. Project-specific overrides go in `settings.local.json`

## Rollback

If the migration does not work as expected:

```bash
# Remove the generated config
rm -rf .claude/

# Restore from backup
cp -r .claude.backup-*/ .claude/
```

Your backup directory preserves the exact state before migration.
