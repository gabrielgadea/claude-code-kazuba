---
name: hook-master
description: |
  Meta-skill for creating, validating, testing, and debugging Claude Code hooks.
  Comprehensive reference for all 18 hook events, exit code contracts, JSON schemas,
  and templates for both Python and shell hooks.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["meta", "hooks", "infrastructure", "debugging"]
triggers:
  - "create hook"
  - "new hook"
  - "debug hook"
  - "hook template"
  - "criar hook"
  - "novo hook"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
context: main
---

# Hook Master

## Philosophy

> Hooks are the nervous system of Claude Code. They intercept events, enforce
> policies, and inject context — silently, reliably, and fail-safe.

## Hook Event Reference (18 events)

| # | Event | Trigger | Input Fields | Use Cases |
|---|-------|---------|-------------|-----------|
| 1 | `SessionStart` | Session begins | `session_id`, `cwd` | Init logging, load context |
| 2 | `UserPromptSubmit` | User sends prompt | `session_id`, `cwd`, `prompt` | Enhance prompt, inject context |
| 3 | `PreToolUse` | Before tool execution | `session_id`, `cwd`, `tool_name`, `tool_input` | Block dangerous ops, validate paths |
| 4 | `PermissionRequest` | Permission dialog shown | `session_id`, `cwd`, `tool_name`, `tool_input` | Auto-approve safe patterns |
| 5 | `PostToolUse` | After tool execution | `session_id`, `cwd`, `tool_name`, `tool_input`, `tool_output` | Log results, audit trail |
| 6 | `PostToolUseFailure` | Tool execution failed | `session_id`, `cwd`, `tool_name`, `tool_input`, `error` | Error tracking, recovery hints |
| 7 | `Notification` | Notification shown | `session_id`, `cwd`, `message` | External alerts, logging |
| 8 | `SubagentStart` | Subagent spawned | `session_id`, `cwd`, `subagent_id` | Track subagent lifecycle |
| 9 | `SubagentStop` | Subagent completed | `session_id`, `cwd`, `subagent_id`, `result` | Collect subagent results |
| 10 | `Stop` | Claude stops responding | `session_id`, `cwd`, `reason` | Audit stop reasons |
| 11 | `TeammateIdle` | Teammate becomes idle | `session_id`, `cwd`, `teammate_id` | Load balancing |
| 12 | `TaskCompleted` | Task marked complete | `session_id`, `cwd`, `task_id` | Notifications, metrics |
| 13 | `ConfigChange` | Config file modified | `session_id`, `cwd`, `config_path` | Reload settings, validate |
| 14 | `PreCompact` | Before context compaction | `session_id`, `cwd` | Save state, checkpoint |
| 15 | `WorktreeCreate` | Worktree created | `session_id`, `cwd`, `worktree_path` | Setup worktree environment |
| 16 | `WorktreeRemove` | Worktree removed | `session_id`, `cwd`, `worktree_path` | Cleanup resources |
| 17 | `SessionEnd` | Session ending | `session_id`, `cwd` | Cleanup, final logging |
| 18 | `Setup` | Initial setup | `session_id`, `cwd` | One-time initialization |

## Exit Code Contract

| Code | Meaning | Effect |
|------|---------|--------|
| `0` | ALLOW | Operation proceeds normally. Hook output (if any) is processed. |
| `1` | BLOCK (user-visible) | Operation blocked. Stderr shown to the **user** as an error message. |
| `2` | DENY (Claude-visible) | Operation blocked. Stderr shown to **Claude** as context (Claude sees the reason). |

**Critical rule**: Hooks MUST fail-open. If your hook crashes or times out, the
exit code should be `0` (allow). Never let a broken hook block the user's workflow.

## JSON Output Schemas

### UserPromptSubmit Output

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Injected context string visible to Claude"
  }
}
```

### PreToolUse Output (allow)

```json
{}
```

### PreToolUse Output (block with reason for Claude)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "decision": "block",
    "reason": "Writing to protected path /etc/passwd"
  }
}
```

### PostToolUse Output

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "suppressOutput": false
  }
}
```

## Python Hook Template

```python
#!/usr/bin/env python3
"""Hook: [EVENT_NAME] — [brief description].

Exit codes: 0=ALLOW, 1=BLOCK(user), 2=DENY(Claude)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field


@dataclass(frozen=True)
class HookConfig:
    """Static configuration for this hook."""
    enabled: bool = True
    timeout_seconds: int = 10
    # Add hook-specific config here


@dataclass(frozen=True)
class HookInput:
    """Parsed stdin from Claude Code."""
    session_id: str
    cwd: str
    hook_event_name: str
    # Add event-specific fields here

    @classmethod
    def from_stdin(cls) -> HookInput:
        raw = json.loads(sys.stdin.read())
        return cls(
            session_id=raw.get("session_id", ""),
            cwd=raw.get("cwd", ""),
            hook_event_name=raw.get("hook_event_name", ""),
        )


@dataclass(frozen=True)
class HookResult:
    """Output to stdout for Claude Code."""
    exit_code: int = 0
    output: dict | None = None
    error: str = ""

    def emit(self) -> None:
        if self.output:
            json.dump(self.output, sys.stdout)
        if self.error:
            print(self.error, file=sys.stderr)
        sys.exit(self.exit_code)


def main() -> None:
    config = HookConfig()
    if not config.enabled:
        sys.exit(0)

    try:
        hook_input = HookInput.from_stdin()
        # --- Hook logic here ---
        result = HookResult(exit_code=0)
        result.emit()
    except Exception:
        # FAIL-OPEN: never block on hook errors
        sys.exit(0)


if __name__ == "__main__":
    main()
```

## Shell Hook Template

```bash
#!/usr/bin/env bash
# Hook: [EVENT_NAME] — [brief description]
# Exit codes: 0=ALLOW, 1=BLOCK(user), 2=DENY(Claude)
set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))")

# --- Hook logic here ---
# Example: block Write to /etc/
if [[ "$TOOL_NAME" == "Write" ]]; then
    FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")
    if [[ "$FILE_PATH" == /etc/* ]]; then
        echo "Blocked: cannot write to /etc/" >&2
        exit 2
    fi
fi

# ALLOW by default
exit 0
```

## Testing Methodology

### 1. Unit Test: stdin mock

```bash
# Test with mock input
echo '{"session_id":"test","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"/etc/passwd"}}' \
  | python3 hooks/my_hook.py
echo "Exit code: $?"
```

### 2. Exit Code Verification

```python
import subprocess
import json

def test_hook_blocks_etc():
    inp = json.dumps({
        "session_id": "test",
        "cwd": "/tmp",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/etc/passwd"},
    })
    result = subprocess.run(
        ["python3", "hooks/my_hook.py"],
        input=inp, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "Blocked" in result.stderr
```

### 3. Integration Test

Register the hook in `settings.json`, then trigger the event manually:
```bash
# Add to .claude/settings.json hooks section
# Run claude with a prompt that triggers the hook event
# Verify behavior via logs or output
```

## Common Pitfalls

| Pitfall | Consequence | Fix |
|---------|------------|-----|
| Not reading all of stdin | Hook hangs (broken pipe) | Always `sys.stdin.read()` even if unused |
| Printing to stdout without JSON | Claude Code parsing error | Only `json.dump()` to stdout |
| Exit 1 on error (not 0) | User sees cryptic error, workflow blocked | Wrap in try/except, exit 0 on error |
| No timeout handling | Hook hangs forever | Use `signal.alarm()` or hook timeout config |
| Importing heavy libs at top | Slow hook startup (adds latency) | Lazy imports inside function |
| Modifying files in hook | Race condition with Claude | Hooks should be read-only observers |
| Not testing with real stdin | Works locally, fails in Claude Code | Always test with piped JSON |

## Debugging Tips

1. **Log to stderr**: Stderr is captured but does not affect hook behavior (unless exit != 0).
2. **Temp file logging**: Write debug info to `/tmp/hook_debug.log` during development.
3. **Dry run mode**: Add `--dry-run` flag that prints what the hook would do without acting.
4. **Check hook registration**: `cat .claude/settings.json | python3 -m json.tool | grep hooks`
5. **Verify event fires**: Add a simple echo hook first to confirm the event triggers.
