# Hooks Reference

Complete reference for all 18 Claude Code hook events supported by the framework.

## Hook Contract

All hooks follow the same contract:

- **Input**: JSON on stdin
- **Output**: JSON on stdout (optional, event-specific)
- **Diagnostic**: Messages on stderr (for logging, not parsed by Claude Code)
- **Exit codes**:
  - `0` = allow / continue (hook approves the action)
  - `1` = block (hook rejects the action, provides reason)
  - `2` = deny (hard block, cannot be overridden)
- **Timeout**: Default 10,000ms (configurable per hook)
- **Fail-open**: Hooks MUST catch all exceptions and exit 0. Use `lib.hook_base.fail_open`.

## Common Input Fields

Every hook receives at minimum:

```json
{
  "session_id": "uuid-string",
  "cwd": "/path/to/project",
  "hook_event_name": "EventName"
}
```

## Events

### 1. PreToolUse

**When**: Before Claude Code executes any tool (Write, Edit, Bash, Read, etc.)

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/project/src/main.py",
    "content": "print('hello')\n"
  }
}
```

**Output** (to block):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "decision": "block",
    "reason": "File contains exposed API key"
  }
}
```

**Decisions**: `"allow"`, `"block"`, `"deny"`

**Framework hooks on this event**:
- `quality_gate.py` — File size limits, debug code detection
- `secrets_scanner.py` — API key and credential detection
- `pii_scanner.py` — CPF, CNPJ, SSN, email, phone detection
- `bash_safety.py` — Dangerous command blocking (rm -rf /, chmod 777, etc.)
- `knowledge_manager.py` — Context injection based on tool usage
- `siac_orchestrator.py` — Quality gates with circuit breaker integration [v0.2.0]
- `auto_permission_resolver.py` — CILA-aware automatic permission resolution [v0.2.0]

**Example implementation**:
```python
#!/usr/bin/env python3
from claude_code_kazuba.hook_base import HookInput, HookResult, fail_open, ALLOW, BLOCK
from claude_code_kazuba.json_output import pre_tool_use_output, emit_json

@fail_open
def main() -> None:
    hook_input = HookInput.from_stdin()
    if hook_input.tool_name == "Bash":
        command = (hook_input.tool_input or {}).get("command", "")
        if "rm -rf /" in command:
            emit_json(pre_tool_use_output("block", "Dangerous command detected"))
            raise SystemExit(BLOCK)
    raise SystemExit(ALLOW)

if __name__ == "__main__":
    main()
```

---

### 2. PostToolUse

**When**: After a tool execution completes.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PostToolUse",
  "tool_name": "Bash",
  "tool_input": {"command": "pytest tests/"},
  "tool_result": {"stdout": "5 passed", "exit_code": 0}
}
```

**Output**: No hookSpecificOutput required. Exit 0 to continue.

**Framework hooks**: `compliance_tracker.py` — Logs tool usage for audit trail.

---

### 3. UserPromptSubmit

**When**: After the user submits a prompt, before Claude processes it.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "Fix the authentication bug in login.py"
}
```

**Output** (to inject context):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Apply chain-of-thought reasoning. Check error handling paths."
  }
}
```

**Framework hooks**:
- `prompt_enhancer.py` — Intent classification + cognitive technique injection
- `cila_router.py` — CILA L0-L6 complexity classification and routing
- `ptc_advisor.py` — PTC program advisor with CILA L0-L6 classification [v0.2.0]

---

### 4. Stop

**When**: When Claude Code is about to stop (end of turn, task complete, etc.)

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "Stop",
  "stop_reason": "end_turn"
}
```

**Output**:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "decision": "stop",
    "reason": "Task complete"
  }
}
```

**Decisions**: `"stop"` (allow stop) or `"continue"` (force continuation).

---

### 5. PreCompact

**When**: Before Claude Code compacts the conversation context.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PreCompact"
}
```

**Output** (preserve context):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreCompact",
    "additionalContext": "Critical: remember to run tests after each change."
  }
}
```

**Framework hooks**:
- `auto_compact.sh` — Saves checkpoint before compaction.
- `post_compact_reinjector.py` — Re-injects critical context after compaction [v0.2.0]

---

### 6. SessionStart

**When**: At the beginning of a new Claude Code session.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "SessionStart"
}
```

**Output**:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Python 3.12.3 | branch: main | 3 pending TODOs"
  }
}
```

**Framework hooks**:
- `status_monitor.sh` — Reports session environment info.
- `session_state_manager.py` — Persists and restores session state across compactions [v0.2.0]

---

### 7. SessionStop

**When**: When a Claude Code session ends (user exits, timeout, etc.)

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "SessionStop"
}
```

**Output**: No hookSpecificOutput required. Use for cleanup (save state, close connections).

---

### 8. SubagentToolUse

**When**: Before a subagent executes a tool (analogous to PreToolUse for subagents).

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "SubagentToolUse",
  "tool_name": "Bash",
  "tool_input": {"command": "npm test"},
  "subagent_id": "subagent-001"
}
```

**Output**: Same format as PreToolUse. Decisions: `"allow"`, `"block"`, `"deny"`.

---

### 9. PostSubagentToolUse

**When**: After a subagent tool execution completes.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PostSubagentToolUse",
  "tool_name": "Bash",
  "tool_result": {"stdout": "tests passed", "exit_code": 0},
  "subagent_id": "subagent-001"
}
```

**Output**: No hookSpecificOutput required.

---

### 10. PreAssistantTurn

**When**: Before Claude begins generating a response turn.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PreAssistantTurn"
}
```

**Output**: Can inject `additionalContext` for turn-level guidance.

---

### 11. PostAssistantTurn

**When**: After Claude completes a response turn.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PostAssistantTurn"
}
```

**Output**: No hookSpecificOutput required. Use for turn-level logging or metrics.

---

### 12. PreApproval

**When**: Before an approval prompt is shown to the user (e.g., for destructive operations).

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PreApproval",
  "tool_name": "Bash",
  "tool_input": {"command": "git push --force"}
}
```

**Output**: Can auto-approve or auto-deny. Decisions: `"allow"`, `"block"`, `"deny"`.

---

### 13. PostApproval

**When**: After the user responds to an approval prompt.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PostApproval",
  "approved": true,
  "tool_name": "Bash"
}
```

**Output**: No hookSpecificOutput required. Use for audit logging.

---

### 14. PrePlanModeApproval

**When**: Before a plan mode approval prompt is shown.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PrePlanModeApproval",
  "plan": "1. Read files\n2. Edit code\n3. Run tests"
}
```

**Output**: Can auto-approve or modify the plan.

---

### 15. PostPlanModeApproval

**When**: After the user approves or rejects a plan.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PostPlanModeApproval",
  "approved": true
}
```

**Output**: No hookSpecificOutput required.

---

### 16. PreNotification

**When**: Before a notification is shown to the user.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PreNotification",
  "notification": {
    "type": "info",
    "message": "Task completed successfully"
  }
}
```

**Output**: Can suppress or modify notifications. Decision: `"allow"` or `"block"`.

---

### 17. PostNotification

**When**: After a notification has been shown.

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "PostNotification",
  "notification": {
    "type": "info",
    "message": "Task completed successfully"
  }
}
```

**Output**: No hookSpecificOutput required. Use for notification logging.

---

### 18. Heartbeat

**When**: Periodically during long-running operations (configurable interval).

**Input**:
```json
{
  "session_id": "...",
  "cwd": "/project",
  "hook_event_name": "Heartbeat",
  "uptime_seconds": 3600
}
```

**Output**: No hookSpecificOutput required. Use for health checks, watchdog timers,
or periodic state saves.

**Framework hooks**: `validate_hooks_health.py` — Periodic health check for all registered hooks [v0.2.0]

---

## Exit Code Summary

| Exit Code | Meaning | Use When |
|-----------|---------|----------|
| 0 | Allow / Continue | Hook approves the action or has no opinion |
| 1 | Block | Hook rejects the action (soft block, user can override) |
| 2 | Deny | Hook hard-blocks the action (cannot be overridden) |

## Hook Registration

Hooks are registered in `.claude/settings.json` under the `hooks` key:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "python3 .claude/hooks/quality_gate.py",
        "timeout": 10000
      }
    ],
    "UserPromptSubmit": [
      {
        "command": "python3 .claude/hooks/prompt_enhancer.py",
        "timeout": 15000
      }
    ]
  }
}
```

Each event key maps to an array of hook registrations with:
- `matcher` (optional): Regex to match tool names (only for tool-related events)
- `command`: Shell command to execute the hook
- `timeout`: Maximum execution time in milliseconds
