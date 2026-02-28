---
name: code-first-planner
description: |
  Generate implementation plans programmatically using Python instead of writing
  markdown manually. Produces consistent phase files with YAML frontmatter,
  cross-references, validation scripts, and checkpoint support (.toon format).
  Use when creating any multi-phase plan, project scaffold, or structured documentation.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["planning", "code-first", "meta", "generator", "validation"]
triggers:
  - "create plan"
  - "generate plan"
  - "plan for"
  - "implementation plan"
  - "multi-phase"
  - "plano de implementação"
  - "gerar plano"
  - "criar plano"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
context: main
---

# Code-First Planner

## Philosophy

> **Plans are data, not documents.**
> A plan written as code is consistent, validated, reproducible, and evolvable.
> A plan written as markdown is prone to drift, inconsistency, and staleness.

The **meta-code-first** principle: instead of writing plan files manually, define
the plan as structured data (Python dataclasses/Pydantic models) and generate
all artifacts programmatically.

## When to Use

- ANY plan with 3+ phases or deliverables
- ANY project scaffold (directory structure + boilerplate)
- ANY structured documentation set (APIs, modules, configs)
- ANY repetitive file generation (test files, configs, migrations)

## What Gets Generated

```
plans/
├── 00-index.md                    # Master index with DAG visualization
├── NN-phase-{slug}.md             # One file per phase (max ~15k tokens)
├── validation/
│   ├── validate_phase_NN.py       # Per-phase validation + checkpoint
│   └── validate_all.py            # Pipeline runner
```

Each phase file includes:
- **YAML frontmatter**: plan, version, phase, title, effort, depends_on, parallel_group,
  validation_script, checkpoint, status, cross_refs
- **Objectives**: Checkable list
- **Files to Create**: Table with path, description, min lines
- **Source Files**: Where to extract code from
- **TDD Specification**: Test descriptions BEFORE implementation
- **Implementation Notes**: Key design decisions
- **Testing**: test_dir, min_coverage, test_files
- **Acceptance Criteria**: Measurable pass/fail conditions
- **Checkpoint**: Command to run validation

## Workflow

### Step 1: Define Data Models

```python
@dataclass(frozen=True)
class Phase:
    id: int
    title: str
    effort: str  # S, M, L, XL
    estimated_tokens: int
    depends_on: list[int]
    parallel_group: str | None  # Phases in same group run in parallel
    objectives: list[str]
    files_to_create: list[PhaseFile]
    tests: PhaseTest | None
    acceptance_criteria: list[str]
    source_files: list[str]  # Where to extract from
    tdd_spec: str  # Tests BEFORE code
    implementation_notes: str
```

### Step 2: Populate Phase Definitions

Define all phases as a `PHASES: list[Phase]` with complete data.
Each phase should:
- Fit in 1 context window (~180k tokens)
- Have explicit dependencies (DAG)
- Include TDD specs (tests before code)
- Reference source files with exact paths

### Step 3: Generate Artifacts

```bash
python scripts/generate_plan.py --validate
```

This produces:
- Phase files with standardized frontmatter
- Validation scripts with checkpoint (.toon) support
- Cross-references automatically computed from dependency graph
- Master index with DAG visualization

### Step 4: Execute Phases

Each phase is self-contained and executed in a dedicated context window:
1. Read the phase file for specs
2. Run TDD: write tests first
3. Implement to make tests pass
4. Run validation: `python plans/validation/validate_phase_NN.py`
5. Checkpoint saved automatically in .toon format
6. `/clear` before next phase

## Applying to Other Activities

### 1. Test Suite Generation
Instead of writing test files manually, define test specs as data and generate:
```python
@dataclass
class TestSpec:
    module: str
    function: str
    cases: list[TestCase]  # input, expected, description
```

### 2. API Scaffold Generation
Define endpoints as data, generate routes + models + tests:
```python
@dataclass
class Endpoint:
    method: str  # GET, POST, PUT, DELETE
    path: str
    request_model: str
    response_model: str
    auth_required: bool
```

### 3. Configuration Generation
Define configs as typed models, generate YAML/JSON with validation:
```python
class HookConfig(BaseModel):
    event: HookEvent
    matcher: str | None
    command: str
    timeout: int = 10
```

### 4. Documentation Generation
Define documentation structure as data, generate consistent docs:
```python
@dataclass
class DocSection:
    title: str
    level: int  # h1-h6
    content_template: str
    examples: list[str]
```

### 5. Migration Scripts
Define schema changes as data, generate up/down migrations:
```python
@dataclass
class Migration:
    version: str
    up: list[SQLStatement]
    down: list[SQLStatement]
    validation: str  # SQL query to verify
```

## Benefits Over Manual Plans

| Aspect | Manual Markdown | Code-First |
|--------|----------------|------------|
| Consistency | Drift between files | Guaranteed by templates |
| Validation | Manual review | Automated (`--validate`) |
| Cross-refs | Manual, error-prone | Auto-computed from DAG |
| Evolution | Edit every file | Change data, regenerate |
| Reproducibility | None | `python generate.py` |
| Testing | Afterthought | Built-in per phase |
| Checkpoints | Manual saves | Automatic .toon format |

## Anti-patterns

- **Don't over-engineer the generator**: Keep it simple. The generator is a tool,
  not a framework. If it takes longer to build than the manual approach, simplify.
- **Don't generate everything**: Some files need human judgment (CLAUDE.md content,
  skill descriptions, architectural decisions). Generate structure, not wisdom.
- **Don't skip validation**: Always run `--validate` after generation.
