# ESAA-Kazuba ACO Engine: Complete Architectural Overview

This document formally details the exponential upgrade applied to the Kazuba architecture, fusing the **Claude Code Local CLI** with the strict, fail-closed principles of the **Event Sourcing Autonomous Agents (ESAA)** blueprint.

The result is the **Agentic Code Orchestrator (ACO) Engine**, moving from a theoretical AI developer tool to a production-ready, highly parallelized infrastructure.

![ACO Engine Top-Down Diagram](/home/gabrielgadea/.gemini/antigravity/brain/5bd90554-40b6-4c66-bf2a-3f943fe169ee/aco_architecture_diagram_1772576408246.png)

## Core Philosophy

Traditional AI Assistants operate linearly: they modify the codebase immediately based on LLM predictions. 
The ESAA-Kazuba ACO Engine operates **generation-first**. It refuses to directly modify files. Instead, it delegates generation tasks to an isolated environment, meta-validates the resulting structure, and executes it securely before merging.

## The 3-Tier Layered Architecture

### N2: The Master MCTS Orchestrator (`n2_mcts_orchestrator.py`)
- **Role:** The strategic mind of the system.
- **Function:** Receives logical directives from Claude Code (via `.claude/hooks/prompt_enhancer.py` and `team-orchestrator` constraints). 
- **Parallelism:** Implements Monte Carlo Tree Search (MCTS) branches via Python's `ThreadPoolExecutor`. Instead of creating one script synchronously, the N2 spawns parallel tasks to generate and evaluate multiple `N0` shadow directories simultaneously.

### N1: The Generator Engine & Quality Gates (`meta/`)
- **Role:** The isolated logic fabricators.
- **Function:** Transforms N2 instructions into Python executable triads (`execute.py`, `validate.py`, `rollback.py`).
- **Pydantic V2 Safety Shield (`esaa_contracts.py`):** Uses strict models and regex validations to ensure no hallucinated parameters exist before code generation.
- **AST Security Scanner (`quality_gates.py`):** Before allowing any triad to proceed, an `ast.NodeVisitor` deep-scans the payload to reject any destructive primitives (`os.system()`, `open()`, `eval()`). Generators must use explicit ESAA/FFI mutations.

### N0: Physical Executors (`n0_executor.py`)
- **Role:** The ephemeral workers.
- **Function:** Placed in isolated shadow directories (e.g., `AST_PATCH_XXX`), they run the exact triad produced by N1.
- **Fail-Fast Protocol:** They run `execute.py`. If successful, they run `validate.py`. If ANY step fails or assertions break, they immediately trigger `rollback.py` to restore the state space. They operate invisibly.

## Closed-Loop Auditing (RLM)

Once the MCTS rollouts conclude at the `N0` level, the `ACOOrchestrator` leverages the **EventStore** (`event_store.py`) to log the activity trail in `database/activity.jsonl`.
This log dictates Reinforcement Learning Memory (RLM):
- Identifies paths that succeeded.
- Records hash-level context of failed mutations.
- The Tantivy indexer will eventually consume this database so Claude Code avoids repeating catastrophic prompt structures.

## Usage & Execution

Because the Claude Code `/home/gabrielgadea/.claude/hooks/prompt_enhancer.py` injects rigid *Constitutional Constraints* during user interactions, Claude automatically defers to `n2_mcts_orchestrator.py` when complex refactorings are needed.

To trigger an orchestration rollout manually:
```bash
export PYTHONPATH="/home/gabrielgadea/projects/claude-code-kazuba/generated:$PYTHONPATH"
python3 /home/gabrielgadea/projects/claude-code-kazuba/generated/n2_mcts_orchestrator.py
```
