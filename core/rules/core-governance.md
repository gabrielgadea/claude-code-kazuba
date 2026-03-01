# Core Governance Rules

> Priority: 100 — Mandatory for all agents and sub-agents
> Scope: Universal — applies to every interaction, regardless of domain

---

## Overview

These governance rules define the operational contract between the LLM and the deterministic world.
They apply to the main agent AND to every sub-agent spawned via Task tool.

**Fundamental Principle**:

- **LLM = stochastic predictor**: outputs are probabilistic, never guaranteed.
- **Code = deterministic executor**: the output of a script is always more reliable than any LLM inference.
- Every task must produce, execute, and evaluate code — not just narrative.

---

## CODE-FIRST CYCLE (Mandatory — Priority 100)

For ANY task received, follow this 6-step cycle:

### Step 1 — DISCOVER

Before doing anything, search for existing code for the task **across the entire codebase**:

```
Search strategy (in order):
1. Grep: "keyword_of_task" across entire codebase (no path filter)
2. Glob: lib/**/*.py       — core library modules
3. Glob: modules/**/*.py   — modular hooks, skills, agents
4. Glob: scripts/**/*.py   — utilities and automation
5. Glob: tests/**/*.py     — test utilities and fixtures
```

**Codebase map** — where each type of code lives:

| Area          | Path                      | Content                                    |
|---------------|---------------------------|--------------------------------------------|
| Core Library  | `lib/`                    | Shared modules: hook_base, config, patterns|
| Modules       | `modules/`                | Hooks, skills, agents, commands            |
| Core Rules    | `core/rules/`             | Governance, coding standards, docs         |
| Scripts       | `scripts/`                | Utilities, generators, validators          |
| Tests         | `tests/`                  | Phase tests, integration tests             |
| Plans         | `plans/`                  | Phase plans, validation scripts            |
| Presets       | `presets/`                | Bundled configurations                     |

If existing code found → go to Step 3 (Execute).
If NOT found → go to Step 2 (Create).

**Objective**: Each successful DISCOVER builds a mental map of "where things live". This knowledge
accumulates over time, accelerating future searches.

---

### Step 2 — CREATE

If no script exists, CREATE before analyzing manually:

1. **Consult the codebase as reference**:
   - Search for **similar modules** across the entire codebase (Grep by functionality)
   - Identify **import patterns, logging, error handling** used in neighboring modules
   - For core logic → reference `lib/` (hook_base, config, patterns)
   - For hook automation → reference `modules/*/hooks/` (PreToolUse/PostToolUse patterns)
   - For config/rules → reference `core/rules/` and `modules/*/config/`

2. **Generate the script in the appropriate location**:
   - `lib/` → if reusable core logic (models, utilities, shared infrastructure)
   - `modules/<module>/hooks/` → if it is Claude Code hook automation
   - `modules/<module>/config/` → if it is configuration or taxonomy
   - `core/rules/` → if it is governance or standard documentation
   - `scripts/` → if it is a one-off utility or generator

3. **Validate syntax**: `ruff check` + `ruff format` before any execution.

The script MUST:
- Follow codebase patterns (see `core/rules/code-style.md`)
- Reuse existing modules when possible
- Have `if __name__ == "__main__":` for standalone execution
- Produce structured output (JSON when possible)
- Include proper logging

---

### Step 3 — EXECUTE

Run the script and capture full output:

```bash
python <script>.py [args] 2>&1
```

The execution result is the FACTUAL BASE. LLM analysis is complementary.

---

### Step 4 — EVALUATE

Evaluate BOTH dimensions — not just one:

**4A. Code quality** (if created in Step 2):
- `ruff check`: 0 errors?
- `pytest`: tests pass?
- Complexity <= 10 per function?
- Codebase patterns followed?
- If insufficient → REFINE (back to Step 2 with improvements)

**4B. Output/content quality**:
- Output is complete for the requested task?
- Data is verifiable?
- Format is consumable (JSON, markdown, etc.)?
- If insufficient → REFINE (adjust parameters, improve logic, re-execute)

---

### Step 5 — REFINE

If any dimension in Step 4 is insufficient:
- Adjust the code based on results
- Re-execute (Step 3)
- Re-evaluate (Step 4)
- Maximum 3 iterations before reporting to user

---

### Step 6 — PERSIST

After success, ensure the script and its context are available for future reuse:

**6A. Persist the script**:
- Save in the appropriate location per the Codebase Map (Step 1)
- If reusable core logic → integrate into `lib/` as module
- If utility → save in `scripts/` with descriptive name

**6B. Index the relationship** (incremental codebase map):
- Document WHICH existing modules the new script uses
- Document WHAT problem it solves
- Document WHERE it fits in the map
- This registration lives in the script's docstring AND in task context

**6C. Growing knowledge base**:
- Each task resolved via code-first ADDS a reusable script to the codebase
- Next similar task, Step 1 (DISCOVER) finds that script
- Over time, the codebase self-indexes

### Cycle Summary

```
DISCOVER → code exists?
  ├─ YES → EXECUTE → EVALUATE → (REFINE?) → PERSIST
  └─ NO  → CREATE (codebase ref) → EXECUTE → EVALUATE → (REFINE?) → PERSIST
```

---

## Supplementary Rules

1. **VERIFY before ASSERTING**: `ls` before "file exists". `pytest` before "tests pass". `wc -l` before "has ~300 lines".
2. **CALCULATE before ESTIMATING**: Never "~85% coverage" — run `pytest --cov`.
3. **SUB-AGENTS INCLUDED**: Every sub-agent spawned via Task tool MUST follow the same 6-step cycle.
4. **Type hints**: Use modern syntax `list[T]`, `T | None`. Never `List[T]`, `Optional[T]`.
5. **frozen=True**: All dataclasses and Pydantic BaseModel must use `frozen=True`.
6. **from __future__ import annotations**: First line of every `.py` file.

---

## Hooks Are Inviolable

- NEVER ignore, disable, or bypass hooks
- ALWAYS respect results: allow / warn / block
- FIX 100% of identified problems
- Exit codes: 0 = allow, 1 = warn, 2 = block

**Fail-open rule**: Hooks ALWAYS exit 0 on internal error (fail-open). Only exit 2 to intentionally block.

---

## ZERO-HALLUCINATION Protocol

- NEVER invent file paths that have not been verified
- NEVER fabricate API methods without checking documentation
- NEVER claim a test passes without running it
- NEVER estimate line counts without `wc -l`
- ALWAYS verify citations in source documents
- Tag confidence: HIGH (>90%), MEDIUM (70-90%), LOW (<70%)

---

## CILA Routing Integration

Every task must be classified via CILA (Code-Integration Levels for AI) before execution:

| Level | Name            | Required Behavior                                    |
|-------|-----------------|------------------------------------------------------|
| L0    | Direct          | Textual response — no pipeline, no CODE-FIRST        |
| L1    | PAL             | Generate simple code (calc/format/convert)           |
| L2    | Tool-Augmented  | DISCOVER → existing script? → EXECUTE → SYNTHESIZE   |
| L3    | Pipelines       | Verify state/deps BEFORE executing                   |
| L4    | Agent Loops     | ReAct cycle with self-correction (max 3 iterations)  |
| L5    | Self-Modifying  | Requires explicit user approval                      |
| L6    | Multi-Agent     | TeamCreate → TaskCreate → parallel agents            |

L3+: Missing precondition → strategy_enforcer returns `action="warn"`.
Never activate pipelines without verifying required states.

---

## Checkpoint Storage (Mandatory)

- **ONLY location**: `checkpoints/`
- **Format**: `.toon` (msgpack) with JSON fallback
- **Structure**: JSON with standardized fields (phase_id, timestamp, results)

**DO NOT use other locations for checkpoints:**
- ❌ Temporary files without phase tracking
- ❌ Inline in source code
- ❌ Plans directory (only `.md` documentation)

---

## Continuous Refinement Cycle (CRC)

Within each execution, apply this inner loop:

```
EXECUTE → OBSERVE → DIAGNOSE → DECIDE → ACT → VALIDATE
                                                   ↓
                               if validation fails → restart from EXECUTE
```

### Diagnose — Classify the Gap

| Priority | Category                        | Action                           |
|----------|---------------------------------|----------------------------------|
| P0       | Correction — wrong output       | FIX NOW                          |
| P0       | Security — vulnerability        | FIX NOW                          |
| P1       | Robustness — edge cases fail    | FIX before moving forward        |
| P2       | Clarity — incomprehensible code | ASSESS cost/benefit              |
| P3       | Performance — unacceptably slow | ASSESS cost/benefit              |
| P4       | Elegance — can be simplified    | ASSESS cost/benefit              |

### ACT — The Co-evolution Triad

Every material change triggers: **Code + Docs + Skill** (updated together).

Materiality = alters behavior, interface, architecture, dependencies, or contracts.

---

## Success Criteria

- Hooks: ALLOW (not WARN, not BLOCK)
- Quality gate: PASS (all 6 stages)
- Ruff: 0 errors, 0 warnings
- Pyright: 0 errors
- Complexity: <= 10 per function
- Coverage: >= 90% per file

---

## Violations

- **VIOLATION** = narrative analysis when a script could compute the result
- **VIOLATION** = NOT searching existing scripts before analyzing manually (skip Step 1)
- **VIOLATION** = asserting without verifying (e.g. "file has 300 lines" without `wc -l`)
- **VIOLATION** = delivering code without validating (`ruff check`, tests)
- **VIOLATION** = sub-agent producing narrative when computational script exists
- **VIOLATION** = resolving same problem twice without persisting script (skip Step 6)
- **VIOLATION** = hook that crashes instead of failing open
- **VIOLATION** = dataclass or BaseModel without `frozen=True`
- **VIOLATION** = missing `from __future__ import annotations` in Python file

---

## Delivery Checklist

Before declaring any task complete, verify ALL:

- [ ] FUNCTIONAL  — Code executes, output correct
- [ ] TESTED      — Happy path + key edge cases covered (>= 90% per file)
- [ ] ROBUST      — Error handling present, inputs validated
- [ ] READABLE    — Clear names, obvious flow, justified complexity
- [ ] DOCUMENTED  — Docstrings for all public interfaces
- [ ] NO REGRESS  — Existing test suite still green
- [ ] NO HALLUC   — All external references verified by execution
- [ ] DELIVERABLE — User can use result immediately

---

## Self-Monitoring — Circuit Breakers

| Signal              | Indicator                            | Action                           |
|---------------------|--------------------------------------|----------------------------------|
| Context overflow    | Responses shorter/vaguer             | `/clear` + reload checkpoint     |
| Loop detection      | Same error 3+ times after "fixes"    | STOP. Re-diagnose from scratch   |
| Scope creep         | Task growing beyond original request | STOP. Return to original spec    |
| Hallucination risk  | Claiming without verification        | STOP. Execute to verify          |
| Yak shaving         | Fixing deps of deps                  | STOP. Assess rabbit hole depth   |
| Diminishing returns | Marginal improvements only           | STOP. Ask user if good enough    |

**Protocol**: `CIRCUIT BREAKER: [signal] | State: [desc] | Options: [A] [B] [C] | Recommendation: [reasoning]`
