# Creating Modules

Guide for creating custom modules for the claude-code-kazuba framework.

## MODULE.md Format

Every module must have a `MODULE.md` file in its root directory. The file uses
YAML frontmatter for machine-readable metadata, followed by Markdown documentation.

### Required Frontmatter Fields

```yaml
---
name: my-module           # Unique module identifier (kebab-case)
version: "1.0.0"          # Semantic version
description: |            # Multi-line description
  What this module does and why you would install it.
dependencies: []          # List of module names this depends on
provides:                 # What this module provides (at least one category)
  hooks:
    - hook_name
  skills:
    - skill-name
  agents:
    - agent-name
  commands:
    - command-name
  config:
    - config-file.yaml
  contexts:
    - context-name
  templates:
    - template-name
  rules:
    - rule-name
---
```

### Optional Frontmatter Fields

```yaml
author: "Your Name"       # Module author
hook_events:              # Hook events this module handles
  - PreToolUse
  - UserPromptSubmit
```

## Directory Structure

Modules live under `modules/<module-name>/` and follow this convention:

```
modules/my-module/
├── MODULE.md              # Manifest (required)
├── hooks/                 # Hook scripts
│   ├── my_hook.py
│   └── another_hook.sh
├── skills/                # Skill definitions
│   └── my-skill/
│       └── SKILL.md
├── agents/                # Agent definitions
│   └── my-agent.md
├── commands/              # Slash command definitions
│   └── my-command.md
├── config/                # Configuration files
│   └── settings.yaml
├── contexts/              # Context definitions
│   └── my-context.md
├── rules/                 # Rule files
│   └── my-rules.md
├── templates/             # Jinja2 templates
│   └── output.md.template
└── settings.hooks.json    # Hook registration fragment
```

Only include directories for what your module provides. A skills-only module
does not need a `hooks/` directory.

## settings.hooks.json Format

If your module provides hooks, create a `settings.hooks.json` file that defines
how hooks are registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "python3 .claude/hooks/my_hook.py",
        "timeout": 10000
      }
    ],
    "UserPromptSubmit": [
      {
        "command": "python3 .claude/hooks/my_enhancer.py",
        "timeout": 15000
      }
    ]
  }
}
```

The installer merges this into the project's settings.json during installation.

## Template Variables

When using Jinja2 templates, these variables are available during rendering:

| Variable | Type | Description |
|----------|------|-------------|
| `project_name` | str | Name of the target project |
| `project_description` | str | Project description |
| `author` | str | Project author name |
| `stack` | str | Tech stack identifier (python, node, rust, etc.) |
| `modules` | list[str] | List of installed module names |
| `hooks` | list[dict] | Merged hook registrations |
| `rules` | list[str] | Concatenated rule content |

### Custom Filters

| Filter | Purpose | Example |
|--------|---------|---------|
| `slug` | Convert to kebab-case | `{{ name \| slug }}` |
| `upper_first` | Capitalize first char | `{{ desc \| upper_first }}` |
| `indent_block` | Indent text block | `{{ content \| indent_block(4) }}` |

## How to Test Modules

### 1. Validate the manifest

```python
import yaml
from pathlib import Path

module_dir = Path("modules/my-module")
content = module_dir.joinpath("MODULE.md").read_text()
# Extract YAML frontmatter between --- markers
frontmatter = content.split("---")[1]
manifest = yaml.safe_load(frontmatter)

assert manifest["name"] == "my-module"
assert isinstance(manifest["dependencies"], list)
assert "provides" in manifest
```

### 2. Test hooks independently

```python
import json
import subprocess

hook_input = {
    "session_id": "test-001",
    "cwd": "/tmp/test",
    "hook_event_name": "PreToolUse",
    "tool_name": "Write",
    "tool_input": {"file_path": "/tmp/test/main.py", "content": "x = 1\n"},
}

result = subprocess.run(
    ["python3", "modules/my-module/hooks/my_hook.py"],
    input=json.dumps(hook_input),
    capture_output=True,
    text=True,
    timeout=10,
)
assert result.returncode == 0  # Should allow
```

### 3. Test dependency resolution

```python
from claude_code_kazuba.config import resolve_dependencies, ModuleManifest

manifests = {
    "core": ModuleManifest(name="core", version="1.0.0", description="", dependencies=[], files=[]),
    "my-module": ModuleManifest(
        name="my-module", version="1.0.0", description="",
        dependencies=["core"], files=[],
    ),
}
order = resolve_dependencies(["my-module"], manifests)
assert order == ["core", "my-module"]
```

## How to Add to Presets

Edit a preset file in `presets/` and add your module name on a new line:

```
# presets/standard.txt
core
hooks-essential
skills-meta
skills-planning
contexts
my-module
```

Modules are installed in the order listed, after dependency resolution.

## Example: Creating a Simple Hook Module

Let us create a module that warns when files exceed 200 lines.

### Step 1: Create the directory

```bash
mkdir -p modules/hooks-linecount/hooks
```

### Step 2: Write MODULE.md

```markdown
---
name: hooks-linecount
version: "1.0.0"
description: "Warns when files exceed a configurable line count."
dependencies:
  - core
provides:
  hooks:
    - line_count_checker
hook_events:
  - PreToolUse
---

# hooks-linecount

Checks file line count before writes and warns if too long.
```

### Step 3: Write the hook

```python
#!/usr/bin/env python3
"""Line count checker hook — warns when files are too long."""
from __future__ import annotations
from claude_code_kazuba.hook_base import HookInput, fail_open, ALLOW
from claude_code_kazuba.json_output import pre_tool_use_output, emit_json
import sys

MAX_LINES = 200

@fail_open
def main() -> None:
    hook_input = HookInput.from_stdin()
    if hook_input.tool_name not in ("Write", "Edit"):
        sys.exit(ALLOW)
    content = (hook_input.tool_input or {}).get("content", "")
    line_count = content.count("\n") + 1
    if line_count > MAX_LINES:
        print(f"Warning: file has {line_count} lines (max {MAX_LINES})", file=sys.stderr)
    sys.exit(ALLOW)

if __name__ == "__main__":
    main()
```

### Step 4: Write settings.hooks.json

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "python3 .claude/hooks/line_count_checker.py",
        "timeout": 5000
      }
    ]
  }
}
```

### Step 5: Write a test

```python
def test_line_count_module_manifest():
    from pathlib import Path
    import yaml
    content = Path("modules/hooks-linecount/MODULE.md").read_text()
    manifest = yaml.safe_load(content.split("---")[1])
    assert manifest["name"] == "hooks-linecount"
    assert "core" in manifest["dependencies"]
```

### Step 6: Add to a preset (optional)

```bash
echo "hooks-linecount" >> presets/standard.txt
```
