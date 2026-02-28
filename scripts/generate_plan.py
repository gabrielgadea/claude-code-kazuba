#!/usr/bin/env python3
"""
Pln2 Generator — Code-First Plan Generation for claude-code-kazuba.

Generates all plan phase files with standardized frontmatter,
cross-references, and validation scripts programmatically.

Usage:
    python scripts/generate_plan.py [--output-dir plans/] [--validate]
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

try:
    import msgpack
except ImportError:
    msgpack = None  # type: ignore[assignment]


# =============================================================================
# Data Models
# =============================================================================


@dataclass(frozen=True)
class CrossRef:
    """Cross-reference between plan files."""

    file: str
    relation: str  # depends_on | blocks | related


@dataclass(frozen=True)
class PhaseFile:
    """Expected file to be created during a phase."""

    path: str
    description: str
    min_lines: int = 10


@dataclass(frozen=True)
class PhaseTest:
    """Test specification for a phase."""

    test_dir: str
    min_coverage: int = 90
    test_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentSpec:
    """Agent specification for parallel execution."""

    name: str
    subagent_type: str
    model: str = "sonnet"
    isolation: str = "worktree"
    task: str = ""


@dataclass(frozen=True)
class Phase:
    """A single phase of the Pln2 plan."""

    id: int
    title: str
    effort: str  # S, M, L, XL
    estimated_tokens: int
    depends_on: list[int] = field(default_factory=list)
    parallel_group: str | None = None  # Phases in same group run in parallel
    description: str = ""
    objectives: list[str] = field(default_factory=list)
    files_to_create: list[PhaseFile] = field(default_factory=list)
    tests: PhaseTest | None = None
    agents: list[AgentSpec] = field(default_factory=list)
    tdd_spec: str = ""
    context_budget: str = "1 context window (~180k tokens)"
    tools_required: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    implementation_notes: str = ""


# =============================================================================
# Phase Definitions — The Pln2 Data
# =============================================================================

PHASES: list[Phase] = [
    Phase(
        id=0,
        title="Bootstrap & Scaffolding",
        effort="S",
        estimated_tokens=8000,
        description=(
            "Initialize the repository with complete project structure, "
            "dependency management, git configuration, and foundational files. "
            "This phase establishes the skeleton that all subsequent phases build upon."
        ),
        objectives=[
            "Create complete directory tree for all 20+ modules",
            "Initialize git repo with .gitignore and LICENSE (MIT)",
            "Create pyproject.toml with all dependencies pinned",
            "Create .venv with Python 3.12+",
            "Initialize .claude/ config for the project itself (self-hosting)",
            "Create CLAUDE.md for the framework project",
        ],
        files_to_create=[
            PhaseFile("pyproject.toml", "Project metadata, dependencies, tool configs", 40),
            PhaseFile(".gitignore", "Git ignore patterns", 20),
            PhaseFile("LICENSE", "MIT License", 20),
            PhaseFile("README.md", "Project overview, quick start, badges", 50),
            PhaseFile("lib/__init__.py", "Package init with version", 5),
            PhaseFile("tests/__init__.py", "Test package init", 1),
            PhaseFile("tests/conftest.py", "Shared fixtures for all tests", 20),
            PhaseFile(".claude/CLAUDE.md", "Self-hosting config for framework dev", 30),
            PhaseFile(".claude/settings.json", "Project settings with hooks stubs", 20),
        ],
        tests=PhaseTest(
            test_dir="tests/phase_00/",
            min_coverage=100,
            test_files=["test_structure.py"],
        ),
        acceptance_criteria=[
            "All directories exist per layout spec",
            "pyproject.toml valid (pip install -e . succeeds)",
            ".venv created with Python 3.12+",
            "git init with initial commit",
            "validate_phase_00.py passes all checks",
        ],
        tools_required=["Bash", "Write", "Edit"],
        implementation_notes=textwrap.dedent("""\
            ## Implementation Strategy

            1. Create all directories in single `mkdir -p` command
            2. Write pyproject.toml with:
               - `[project]` metadata (name, version, description, requires-python>=3.12)
               - `[project.dependencies]`: pydantic>=2.10, msgpack>=1.1, pyyaml>=6.0, jinja2>=3.1
               - `[project.optional-dependencies.dev]`: pytest>=8.3, pytest-cov>=6.0, ruff>=0.8, pyright>=1.1.390
               - `[tool.ruff]`: line-length=99, target-version="py312"
               - `[tool.pyright]`: pythonVersion="3.12", typeCheckingMode="strict"
               - `[tool.pytest.ini_options]`: testpaths=["tests"], addopts="--strict-markers -v"
            3. Write .gitignore (Python + .claude/settings.local.json + .venv + checkpoints/*.toon)
            4. git init && git add && git commit -m "feat: bootstrap project structure"
        """),
    ),
    Phase(
        id=1,
        title="Shared Library (lib/)",
        effort="M",
        estimated_tokens=15000,
        depends_on=[0],
        description=(
            "Build the shared Python library that all hooks depend on. "
            "This is the foundation layer providing standardized dataclasses, "
            "patterns, performance utilities, and JSON output helpers."
        ),
        objectives=[
            "Create hook_base.py with frozen dataclasses (HookConfig, HookInput, HookResult)",
            "Create patterns.py with configurable regex patterns (secrets, PII by country)",
            "Create performance.py with L0 cache, parallel executor, Rust accelerator singleton",
            "Create json_output.py with factory functions per hook event",
            "Create config.py with Pydantic v2 models for all config validation",
            "Create checkpoint.py with .toon save/load using msgpack",
            "Achieve 90%+ coverage per file with TDD approach",
        ],
        files_to_create=[
            PhaseFile("lib/hook_base.py", "Core hook dataclasses and exit code contracts", 120),
            PhaseFile("lib/patterns.py", "Reusable regex patterns (secrets, PII, safety)", 150),
            PhaseFile("lib/performance.py", "L0 cache, ParallelExecutor, RustAccelerator", 100),
            PhaseFile("lib/json_output.py", "Standardized JSON output builders per event", 80),
            PhaseFile("lib/config.py", "Pydantic v2 models for settings, hooks, modules", 200),
            PhaseFile("lib/checkpoint.py", "Checkpoint save/load in .toon (msgpack) format", 80),
            PhaseFile(
                "lib/template_engine.py", "Jinja2-based template renderer for CLAUDE.md etc", 60
            ),
        ],
        tests=PhaseTest(
            test_dir="tests/phase_01/",
            min_coverage=90,
            test_files=[
                "test_hook_base.py",
                "test_patterns.py",
                "test_performance.py",
                "test_json_output.py",
                "test_config.py",
                "test_checkpoint.py",
                "test_template_engine.py",
            ],
        ),
        tdd_spec=textwrap.dedent("""\
            ## TDD Specification

            Write tests BEFORE implementation for each file:

            ### test_hook_base.py
            - test_hook_input_from_dict: valid JSON → HookInput
            - test_hook_input_from_stdin_invalid: bad JSON → exit BLOCK
            - test_hook_result_emit_allow: exit 0, no stderr
            - test_hook_result_emit_deny: exit 2, stderr message
            - test_hook_config_frozen: cannot mutate after creation
            - test_exit_codes_constants: ALLOW=0, BLOCK=1, DENY=2

            ### test_patterns.py
            - test_secret_patterns_detect_api_key: match API key formats
            - test_secret_patterns_no_false_positive: safe strings pass
            - test_pii_patterns_brazil_cpf: detect CPF format
            - test_pii_patterns_configurable_country: switch country, different patterns
            - test_whitelist_patterns_env_vars: process.env.* not flagged

            ### test_performance.py
            - test_l0_cache_hit: cached result returns without computation
            - test_l0_cache_miss: uncached triggers computation
            - test_l0_cache_ttl_expiry: expired entry triggers recomputation
            - test_parallel_executor_runs_parallel: verify concurrent execution
            - test_rust_accelerator_fallback: when unavailable, returns None

            ### test_checkpoint.py
            - test_save_toon: save dict → .toon file exists
            - test_load_toon: load .toon → same dict
            - test_roundtrip: save → load → equal
            - test_checkpoint_metadata: includes timestamp, phase_id, version
        """),
        source_files=[
            "~/.claude/hooks/prompt_enhancer.py (hook_base patterns)",
            "analise/.claude/hooks/security/antt_pii_detector.py (L0 cache, PII patterns)",
            "kazuba-cargo/.claude/hooks/security/secrets_detector.py (secret patterns)",
            "analise/.claude/hooks/quality/post_quality_gate.py (parallel executor)",
        ],
        acceptance_criteria=[
            "All 7 lib/ files created and importable",
            "pytest tests/phase_01/ passes with 90%+ coverage per file",
            "pyright --strict lib/ passes with 0 errors",
            "ruff check lib/ passes with 0 errors",
            "Checkpoint .toon roundtrip verified",
        ],
        tools_required=["Bash", "Write", "Edit", "Agent(general-purpose)"],
        mcp_servers=["context7"],
        implementation_notes=textwrap.dedent("""\
            ## Key Design Decisions

            - All dataclasses use `frozen=True` for immutability
            - Type hints use modern syntax: `list[T]`, `T | None` (not `List[T]`, `Optional[T]`)
            - `from __future__ import annotations` in every file
            - PII patterns configurable via country code: `PIIPatterns.for_country("BR")`
            - L0 cache uses SHA-256 hash key with configurable TTL (default 300s)
            - .toon format: msgpack header (4 bytes magic + version) + msgpack payload
            - Template engine wraps Jinja2 with custom filters for CLAUDE.md rendering
        """),
    ),
    Phase(
        id=2,
        title="Core Module",
        effort="M",
        estimated_tokens=12000,
        depends_on=[1],
        description=(
            "Create the core module that is always installed. Contains CLAUDE.md template, "
            "settings.json template, and universal rules extracted from all 4 source configs."
        ),
        objectives=[
            "Create CLAUDE.md.template with CRC cycle, circuit breakers, validation gate",
            "Create settings.json.template with $schema, hooks stubs, env vars",
            "Create settings.local.json.template (gitignored, personal preferences)",
            "Create .gitignore.template for .claude/ directory",
            "Extract and generalize rules from kazuba-cargo/.claude/rules/",
            "Create MODULE.md manifest with metadata and dependencies",
        ],
        files_to_create=[
            PhaseFile("core/CLAUDE.md.template", "Master template with Jinja2 vars", 150),
            PhaseFile("core/settings.json.template", "Base settings with $schema", 60),
            PhaseFile("core/settings.local.json.template", "Local overrides template", 20),
            PhaseFile("core/.gitignore.template", "Gitignore for .claude/", 15),
            PhaseFile("core/MODULE.md", "Core module manifest", 30),
            PhaseFile("core/rules/code-style.md", "Universal code style rules", 50),
            PhaseFile("core/rules/security.md", "Security rules (OWASP, secrets, PII)", 60),
            PhaseFile("core/rules/testing.md", "Testing rules (TDD, coverage, pyramid)", 40),
            PhaseFile("core/rules/git-workflow.md", "Git workflow rules (branches, commits)", 40),
        ],
        tests=PhaseTest(
            test_dir="tests/phase_02/",
            min_coverage=90,
            test_files=[
                "test_core_templates.py",
                "test_rules_content.py",
            ],
        ),
        source_files=[
            "~/.claude/CLAUDE.md (CRC cycle, circuit breakers, validation gate, L1-L5 taxonomy)",
            "kazuba-cargo/.claude/rules/ (code-style, security, testing, git-workflow)",
            "analise/.claude/rules/00-core-governance.md (CODE-FIRST, ZERO-HALLUCINATION)",
            "kazuba-cargo/.claude/CLAUDE.md (compact style, context optimization)",
        ],
        acceptance_criteria=[
            "CLAUDE.md.template renders with sample vars without error",
            "settings.json.template is valid JSON after rendering",
            "All rules files have actionable content (not placeholder)",
            "Templates contain {{PROJECT_NAME}}, {{LANGUAGE}}, {{STACK}} variables",
            "pytest tests/phase_02/ passes",
        ],
        tools_required=["Write", "Edit", "Bash"],
    ),
    Phase(
        id=3,
        title="Hooks Essential Module",
        effort="L",
        estimated_tokens=15000,
        depends_on=[1],
        parallel_group="hooks",
        description=(
            "Extract and generalize the 5 fundamental hooks that form the context management "
            "nervous system. These hooks work together to monitor, warn, preserve, and enhance."
        ),
        objectives=[
            "Generalize prompt_enhancer.py (remove ANTT-specific, parametrize)",
            "Parametrize status_monitor.sh (configurable thresholds)",
            "Extract check_context.sh + auto_compact.sh coordination pattern",
            "Generalize compact_reinjector.py (configurable rules)",
            "Create settings.hooks.json fragment for module registration",
            "Validate with 46 golden prompts (EN + PT-BR)",
        ],
        files_to_create=[
            PhaseFile("modules/hooks-essential/MODULE.md", "Module manifest", 30),
            PhaseFile(
                "modules/hooks-essential/hooks/prompt_enhancer.py",
                "Intent classifier + technique injector",
                400,
            ),
            PhaseFile(
                "modules/hooks-essential/hooks/prompt_enhancer_config.yaml",
                "Templates and technique map",
                80,
            ),
            PhaseFile(
                "modules/hooks-essential/hooks/status_monitor.sh", "StatusLine context bar", 60
            ),
            PhaseFile(
                "modules/hooks-essential/hooks/check_context.sh", "PostToolUse context warning", 25
            ),
            PhaseFile(
                "modules/hooks-essential/hooks/auto_compact.sh", "Stop auto-compaction trigger", 30
            ),
            PhaseFile(
                "modules/hooks-essential/hooks/compact_reinjector.py",
                "PreCompact rules preservation",
                50,
            ),
            PhaseFile(
                "modules/hooks-essential/settings.hooks.json", "Hook registration fragment", 30
            ),
        ],
        tests=PhaseTest(
            test_dir="tests/phase_03/",
            min_coverage=90,
            test_files=[
                "test_prompt_enhancer.py",
                "test_compact_reinjector.py",
                "test_golden_prompts.py",
            ],
        ),
        source_files=[
            "~/.claude/hooks/prompt_enhancer.py (938 lines, 100% accuracy, P99<50ms)",
            "~/.claude/hooks/prompt_enhancer_config.yaml",
            "~/.claude/hooks/status_monitor.sh",
            "~/.claude/hooks/check_context.sh",
            "~/.claude/hooks/auto_compact.sh",
            "analise/.claude/hooks/lifecycle/post_compact_reinjector.py",
        ],
        acceptance_criteria=[
            "prompt_enhancer.py classifies 46/46 golden prompts correctly",
            "status_monitor.sh shows colored progress bar with configurable threshold",
            "auto_compact + check_context coordinate via flag file pattern",
            "compact_reinjector preserves configurable rules through compaction",
            "All hooks follow fail-open pattern (exit 0 on error)",
            "pytest with 90%+ coverage per file",
        ],
        tools_required=["Bash", "Write", "Edit", "Agent(general-purpose)"],
    ),
    Phase(
        id=4,
        title="Hooks Quality + Security",
        effort="L",
        estimated_tokens=15000,
        depends_on=[1],
        parallel_group="hooks",
        description=(
            "Extract quality gate pipeline and security hooks. These hooks form the "
            "defensive layer that prevents bad code and secrets from entering the codebase."
        ),
        objectives=[
            "Generalize post_quality_gate.py (6-stage parallel pipeline)",
            "Generalize code_standards_enforcer.py (auto-fix before block)",
            "Generalize stop_validator.py (block if tasks incomplete)",
            "Generalize secrets_detector.py (pattern-based)",
            "Create pii_detector.py (country-configurable via lib/patterns.py)",
            "Create bash_safety.py (block dangerous commands)",
        ],
        files_to_create=[
            PhaseFile("modules/hooks-quality/MODULE.md", "Module manifest", 30),
            PhaseFile(
                "modules/hooks-quality/hooks/post_quality_gate.py", "6-stage parallel QA", 200
            ),
            PhaseFile(
                "modules/hooks-quality/hooks/code_standards_enforcer.py", "Auto-fix or block", 150
            ),
            PhaseFile("modules/hooks-quality/hooks/stop_validator.py", "Block if incomplete", 80),
            PhaseFile("modules/hooks-quality/settings.hooks.json", "Hook registration", 25),
            PhaseFile("modules/hooks-security/MODULE.md", "Module manifest", 30),
            PhaseFile(
                "modules/hooks-security/hooks/secrets_detector.py",
                "Secret/credential detection",
                120,
            ),
            PhaseFile(
                "modules/hooks-security/hooks/pii_detector.py",
                "PII detection (configurable country)",
                100,
            ),
            PhaseFile(
                "modules/hooks-security/hooks/bash_safety.py", "Block dangerous bash commands", 60
            ),
            PhaseFile("modules/hooks-security/settings.hooks.json", "Hook registration", 25),
        ],
        tests=PhaseTest(
            test_dir="tests/phase_04/",
            min_coverage=90,
            test_files=[
                "test_quality_gate.py",
                "test_standards_enforcer.py",
                "test_stop_validator.py",
                "test_secrets_detector.py",
                "test_pii_detector.py",
                "test_bash_safety.py",
            ],
        ),
        source_files=[
            "analise/.claude/hooks/quality/post_quality_gate.py (6-stage, ThreadPoolExecutor)",
            "kazuba-cargo/.claude/hooks/quality/code_standards_enforcer.py (auto-fix)",
            "kazuba-cargo/.claude/hooks/lifecycle/stop_validator.py (transcript parsing)",
            "kazuba-cargo/.claude/hooks/security/secrets_detector.py",
            "analise/.claude/hooks/security/antt_pii_detector.py (L0 cache)",
            "analise/.claude/hooks/security/bash_safety_validator.py",
        ],
        acceptance_criteria=[
            "post_quality_gate runs 6 stages in parallel (ThreadPoolExecutor)",
            "code_standards_enforcer attempts auto-fix before blocking",
            "secrets_detector catches all patterns from lib/patterns.py",
            "pii_detector works with BR (CPF/CNPJ) and is extensible to other countries",
            "bash_safety blocks rm -rf /, chmod 777, curl | bash patterns",
            "All hooks use lib/hook_base.py dataclasses",
            "90%+ coverage per file",
        ],
        tools_required=["Bash", "Write", "Edit"],
    ),
    Phase(
        id=5,
        title="Hooks Routing + Knowledge + Metrics",
        effort="M",
        estimated_tokens=14000,
        depends_on=[1],
        parallel_group="hooks",
        description=(
            "Extract intent classification (CILA), knowledge management (3-tier), "
            "and compliance metrics hooks."
        ),
        objectives=[
            "Generalize CILA intent_router.py (remove ANTT L3 patterns, keep L0-L6 framework)",
            "Generalize intent_patterns.py (configurable pattern registry)",
            "Create strategy_enforcer.py (inject DISCOVER warnings for L2+)",
            "Create knowledge_retrieval.py (local cache → MCP → fallback)",
            "Create knowledge_capture.py (PostToolUse pattern capture)",
            "Create compliance_collector.py + compliance_dashboard.py",
        ],
        files_to_create=[
            PhaseFile("modules/hooks-routing/MODULE.md", "Module manifest", 30),
            PhaseFile(
                "modules/hooks-routing/hooks/intent_router.py", "CILA L0-L6 classifier", 120
            ),
            PhaseFile(
                "modules/hooks-routing/hooks/intent_patterns.py", "Configurable regex patterns", 80
            ),
            PhaseFile(
                "modules/hooks-routing/hooks/strategy_enforcer.py",
                "DISCOVER warning injection",
                60,
            ),
            PhaseFile("modules/hooks-routing/settings.hooks.json", "Hook registration", 20),
            PhaseFile("modules/hooks-knowledge/MODULE.md", "Module manifest", 30),
            PhaseFile(
                "modules/hooks-knowledge/hooks/knowledge_retrieval.py",
                "3-tier knowledge lookup",
                100,
            ),
            PhaseFile(
                "modules/hooks-knowledge/hooks/knowledge_capture.py",
                "Pattern capture PostToolUse",
                80,
            ),
            PhaseFile(
                "modules/hooks-knowledge/hooks/session_context.py",
                "SessionStart context loader",
                60,
            ),
            PhaseFile("modules/hooks-knowledge/settings.hooks.json", "Hook registration", 20),
            PhaseFile("modules/hooks-metrics/MODULE.md", "Module manifest", 30),
            PhaseFile(
                "modules/hooks-metrics/hooks/compliance_collector.py",
                "Enforcement score recorder",
                80,
            ),
            PhaseFile(
                "modules/hooks-metrics/hooks/compliance_dashboard.py",
                "Rich/JSON/MD dashboard",
                100,
            ),
            PhaseFile("modules/hooks-metrics/settings.hooks.json", "Hook registration", 20),
        ],
        tests=PhaseTest(
            test_dir="tests/phase_05/",
            min_coverage=90,
            test_files=[
                "test_intent_router.py",
                "test_intent_patterns.py",
                "test_knowledge_retrieval.py",
                "test_compliance.py",
            ],
        ),
        source_files=[
            "analise/.claude/hooks/routing/intent_router.py (CILA <1ms)",
            "analise/.claude/hooks/routing/intent_patterns.py",
            "analise/.claude/hooks/routing/strategy_enforcer.py",
            "analise/.claude/hooks/knowledge/cipher_knowledge_retrieval.py",
            "analise/.claude/hooks/knowledge/cipher_knowledge_capture.py",
            "analise/.claude/hooks/metrics/compliance_collector.py",
            "analise/.claude/hooks/metrics/compliance_dashboard.py",
        ],
        acceptance_criteria=[
            "CILA classifier works for L0-L6 without domain-specific patterns",
            "Intent patterns are configurable via YAML or Python dict",
            "Knowledge retrieval follows 3-tier: local → MCP → fallback",
            "Compliance dashboard outputs rich, JSON, and markdown formats",
            "90%+ coverage per file",
        ],
        tools_required=["Bash", "Write", "Edit"],
    ),
    Phase(
        id=6,
        title="Skills + Agents + Commands",
        effort="L",
        estimated_tokens=15000,
        depends_on=[0],
        parallel_group="content",
        description=(
            "Extract and generalize reusable skills, agent definitions, and slash commands "
            "from all 4 source configurations."
        ),
        objectives=[
            "Extract meta-skills: hook-master, skill-master, skill-writer",
            "Extract dev skills: verification-loop, supreme-problem-solver, eval-harness",
            "Extract planning skills: plan-amplifier, plan-execution",
            "Extract research skills: academic-research-writer, literature-review, scientific-writing",
            "Create dev agents: code-reviewer, performance-analyzer, security-auditor, meta-orchestrator",
            "Extract commands: debug-RCA, smart-commit, orchestrate, verify",
            "Extract PRP system with shared YAML patterns",
        ],
        files_to_create=[
            PhaseFile("modules/skills-meta/MODULE.md", "Module manifest", 20),
            PhaseFile(
                "modules/skills-meta/skills/hook-master/SKILL.md", "Meta-skill for hooks", 200
            ),
            PhaseFile(
                "modules/skills-meta/skills/skill-master/SKILL.md", "Meta-skill for skills", 200
            ),
            PhaseFile(
                "modules/skills-meta/skills/skill-writer/SKILL.md", "Guide for skill creation", 100
            ),
            PhaseFile("modules/skills-dev/MODULE.md", "Module manifest", 20),
            PhaseFile(
                "modules/skills-dev/skills/verification-loop/SKILL.md", "6-phase pre-PR", 100
            ),
            PhaseFile(
                "modules/skills-dev/skills/supreme-problem-solver/SKILL.md",
                "H0/H1/H2 escalation",
                120,
            ),
            PhaseFile("modules/skills-dev/skills/eval-harness/SKILL.md", "Eval-driven dev", 80),
            PhaseFile("modules/skills-planning/MODULE.md", "Module manifest", 20),
            PhaseFile(
                "modules/skills-planning/skills/plan-amplifier/SKILL.md",
                "8-dim amplification",
                150,
            ),
            PhaseFile(
                "modules/skills-planning/skills/plan-execution/SKILL.md",
                "Checkpoint execution",
                120,
            ),
            PhaseFile("modules/skills-research/MODULE.md", "Module manifest", 20),
            PhaseFile(
                "modules/skills-research/skills/academic-research-writer/SKILL.md",
                "Academic writing",
                100,
            ),
            PhaseFile(
                "modules/skills-research/skills/literature-review/SKILL.md",
                "Literature review",
                80,
            ),
            PhaseFile("modules/agents-dev/MODULE.md", "Module manifest", 20),
            PhaseFile("modules/agents-dev/agents/code-reviewer.md", "Code review agent", 60),
            PhaseFile("modules/agents-dev/agents/security-auditor.md", "Security audit agent", 60),
            PhaseFile(
                "modules/agents-dev/agents/meta-orchestrator.md", "Meta-orchestrator agent", 80
            ),
            PhaseFile("modules/commands-dev/MODULE.md", "Module manifest", 20),
            PhaseFile("modules/commands-dev/commands/debug-RCA.md", "Structured RCA", 60),
            PhaseFile("modules/commands-dev/commands/smart-commit.md", "Intelligent commits", 40),
            PhaseFile(
                "modules/commands-dev/commands/orchestrate.md", "Multi-agent orchestration", 60
            ),
            PhaseFile("modules/commands-dev/commands/verify.md", "Pre-PR verification", 40),
            PhaseFile("modules/commands-prp/MODULE.md", "Module manifest", 20),
            PhaseFile("modules/commands-prp/commands/prp-base-create.md", "PRP creation", 60),
            PhaseFile("modules/commands-prp/commands/prp-base-execute.md", "PRP execution", 60),
            PhaseFile(
                "modules/commands-prp/commands/shared/quality-patterns.yml", "Quality YAML", 30
            ),
            PhaseFile(
                "modules/commands-prp/commands/shared/security-patterns.yml", "Security YAML", 30
            ),
        ],
        tests=PhaseTest(
            test_dir="tests/phase_06/",
            min_coverage=90,
            test_files=[
                "test_skill_frontmatter.py",
                "test_agent_frontmatter.py",
                "test_command_structure.py",
            ],
        ),
        source_files=[
            "kazuba-cargo/.claude/skills/hook-master/SKILL.md",
            "kazuba-cargo/.claude/skills/skill-master/SKILL.md",
            "kazuba-cargo/.claude/skills/supreme-problem-solver/SKILL.md",
            "kazuba-cargo/.claude/skills/verification-loop/SKILL.md",
            "kazuba-cargo/.claude/skills/eval-harness/SKILL.md",
            "~/.claude/skills/plan-amplifier/SKILL.md",
            "~/.claude/skills/plan-execution/SKILL.md",
            "~/.claude/skills/academic-research-writer/SKILL.md",
            "kazuba-cargo/.claude/agents/claude-code-meta-orchestrator.md",
            "transferegov/.claude/commands/development/debug-RCA.md",
            "transferegov/.claude/commands/development/smart-commit.md",
            "transferegov/.claude/commands/PRPs/prp-base-create.md",
        ],
        acceptance_criteria=[
            "All SKILL.md files have valid YAML frontmatter",
            "All agent .md files have valid frontmatter with required fields",
            "All commands follow Claude Code command format",
            "Shared YAML patterns are valid YAML",
            "No domain-specific (ANTT/TIR) content in generalized files",
        ],
        tools_required=["Write", "Edit", "Bash", "Agent(general-purpose)"],
    ),
    Phase(
        id=7,
        title="Config + Contexts + Team Orchestrator",
        effort="M",
        estimated_tokens=12000,
        depends_on=[0],
        parallel_group="content",
        description=(
            "Extract centralized automation configs, context modifiers, "
            "and the team orchestrator framework."
        ),
        objectives=[
            "Extract and generalize hypervisor.yaml (circuit breakers, SLA, thinking levels)",
            "Extract agent_triggers.yaml (declarative agent auto-selection)",
            "Extract event_mesh.yaml (event bus architecture)",
            "Create 4 context modifiers (dev, review, research, audit)",
            "Extract team orchestrator with Pydantic models and config YAML",
        ],
        files_to_create=[
            PhaseFile("modules/config-hypervisor/MODULE.md", "Module manifest", 20),
            PhaseFile("modules/config-hypervisor/config/hypervisor.yaml", "Automation config", 80),
            PhaseFile(
                "modules/config-hypervisor/config/agent_triggers.yaml", "Agent triggers", 60
            ),
            PhaseFile("modules/config-hypervisor/config/event_mesh.yaml", "Event bus config", 50),
            PhaseFile("modules/contexts/MODULE.md", "Module manifest", 20),
            PhaseFile("modules/contexts/contexts/dev.md", "Dev mode (relaxed)", 30),
            PhaseFile("modules/contexts/contexts/review.md", "Review mode (strict)", 30),
            PhaseFile("modules/contexts/contexts/research.md", "Research mode (deep)", 30),
            PhaseFile("modules/contexts/contexts/audit.md", "Audit mode (thorough)", 30),
            PhaseFile("modules/team-orchestrator/MODULE.md", "Module manifest", 20),
            PhaseFile("modules/team-orchestrator/config/agents.yaml", "Agent registry", 40),
            PhaseFile("modules/team-orchestrator/config/routing_rules.yaml", "Routing rules", 40),
            PhaseFile("modules/team-orchestrator/config/sla.yaml", "SLA targets", 30),
            PhaseFile("modules/team-orchestrator/src/models.py", "Pydantic v2 models", 150),
            PhaseFile(
                "modules/team-orchestrator/templates/task-delegation.md", "Delegation template", 20
            ),
            PhaseFile(
                "modules/team-orchestrator/templates/status-report.md", "Status template", 20
            ),
        ],
        tests=PhaseTest(
            test_dir="tests/phase_07/",
            min_coverage=90,
            test_files=[
                "test_yaml_configs.py",
                "test_orchestrator_models.py",
                "test_contexts.py",
            ],
        ),
        source_files=[
            "kazuba-cargo/.claude/config/hypervisor.yaml",
            "kazuba-cargo/.claude/config/agent_triggers.yaml",
            "kazuba-cargo/.claude/config/event_mesh.yaml",
            "kazuba-cargo/.claude/contexts/ (dev, review, research, tir-audit)",
            "~/.claude/skills/team-orchestrator/ (config, src, templates)",
        ],
        acceptance_criteria=[
            "All YAML files pass yaml.safe_load() validation",
            "Pydantic models validate sample data without errors",
            "Contexts modify behavior descriptors appropriately",
            "hypervisor.yaml has circuit_breakers, sla, thinking sections",
        ],
        tools_required=["Write", "Edit", "Bash"],
    ),
    Phase(
        id=8,
        title="Installer CLI",
        effort="L",
        estimated_tokens=15000,
        depends_on=[1, 2, 3, 4, 5, 6, 7],
        description=(
            "Build the interactive installer CLI that detects project stack, "
            "offers presets, and installs selected modules with intelligent merging."
        ),
        objectives=[
            "Create install.sh with argument parser (--preset, --modules, --target, --dry-run)",
            "Implement stack detection (Python/Rust/JS/TS/Go/Java via manifest files)",
            "Implement preset system (minimal/standard/professional/enterprise/research)",
            "Implement module selection with dependency resolution",
            "Implement settings.json merge algorithm (append hooks, don't overwrite)",
            "Implement template variable substitution",
            "Create validate_installation.py post-install health check",
            "Support remote install via curl | bash",
        ],
        files_to_create=[
            PhaseFile("install.sh", "Main installer CLI script", 300),
            PhaseFile("scripts/install_module.py", "Python module installer helper", 150),
            PhaseFile("scripts/merge_settings.py", "Settings.json merge algorithm", 100),
            PhaseFile("scripts/detect_stack.py", "Project stack auto-detection", 60),
            PhaseFile("scripts/resolve_deps.py", "Module dependency DAG resolver", 80),
            PhaseFile("scripts/validate_installation.py", "Post-install health check", 80),
            PhaseFile("presets/minimal.txt", "Core only", 5),
            PhaseFile("presets/standard.txt", "Core + essential hooks + meta skills", 10),
            PhaseFile("presets/professional.txt", "Standard + quality + security + agents", 15),
            PhaseFile("presets/enterprise.txt", "Professional + team + hypervisor", 18),
            PhaseFile("presets/research.txt", "Standard + research + planning skills", 12),
        ],
        tests=PhaseTest(
            test_dir="tests/phase_08/",
            min_coverage=90,
            test_files=[
                "test_installer.py",
                "test_merge_settings.py",
                "test_detect_stack.py",
                "test_resolve_deps.py",
                "test_validate_installation.py",
            ],
        ),
        acceptance_criteria=[
            "install.sh --preset minimal --target /tmp/test works E2E",
            "install.sh --dry-run shows plan without writing files",
            "Stack detection identifies Python, Rust, JS, TS, Go",
            "Settings merge appends hooks without overwriting user config",
            "Dependency resolver detects cycles and reports errors",
            "validate_installation.py reports all checks green",
            "90%+ coverage per script file",
        ],
        tools_required=["Bash", "Write", "Edit"],
    ),
    Phase(
        id=9,
        title="Presets + Integration Tests",
        effort="M",
        estimated_tokens=12000,
        depends_on=[8],
        description=(
            "Define all 5 presets with exact module lists, run integration tests "
            "that install each preset and validate the result."
        ),
        objectives=[
            "Define module lists for all 5 presets",
            "Create integration test that installs each preset to temp dir",
            "Verify all hooks fire correctly in mock Claude Code session",
            "Verify settings.json is valid after each preset install",
            "Create E2E test script",
        ],
        files_to_create=[
            PhaseFile("tests/integration/test_preset_minimal.py", "Minimal preset E2E", 40),
            PhaseFile("tests/integration/test_preset_standard.py", "Standard preset E2E", 50),
            PhaseFile(
                "tests/integration/test_preset_professional.py", "Professional preset E2E", 50
            ),
            PhaseFile("tests/integration/test_preset_enterprise.py", "Enterprise preset E2E", 60),
            PhaseFile("tests/integration/test_preset_research.py", "Research preset E2E", 40),
            PhaseFile("tests/integration/conftest.py", "Shared integration fixtures", 40),
        ],
        tests=PhaseTest(
            test_dir="tests/integration/",
            min_coverage=90,
            test_files=[
                "test_preset_minimal.py",
                "test_preset_standard.py",
                "test_preset_professional.py",
                "test_preset_enterprise.py",
                "test_preset_research.py",
            ],
        ),
        acceptance_criteria=[
            "All 5 preset installations succeed in clean temp directories",
            "Installed settings.json passes JSON Schema validation",
            "All hook scripts are executable and exit 0 on empty input",
            "All SKILL.md files have valid YAML frontmatter",
            "validate_installation.py passes for each preset",
        ],
        tools_required=["Bash", "Write", "Edit"],
    ),
    Phase(
        id=10,
        title="GitHub + CI + Documentation",
        effort="S",
        estimated_tokens=10000,
        depends_on=[9],
        description=(
            "Create GitHub repository, CI pipeline, comprehensive documentation, "
            "and release automation."
        ),
        objectives=[
            "Create GitHub repo gabrielgadea/claude-code-kazuba",
            "Create GitHub Actions CI (lint, test, coverage badge)",
            "Write comprehensive README.md with quick start and module catalog",
            "Write ARCHITECTURE.md with design decisions",
            "Write HOOKS_REFERENCE.md with all 18 events + JSON schemas",
            "Write MODULES_CATALOG.md with descriptions and dependencies",
            "Write CREATING_MODULES.md for extensibility",
            "Write MIGRATION.md for existing .claude/ users",
            "Create initial release tag v0.1.0",
        ],
        files_to_create=[
            PhaseFile(".github/workflows/ci.yml", "CI pipeline (lint+test+coverage)", 50),
            PhaseFile("docs/ARCHITECTURE.md", "Framework architecture", 100),
            PhaseFile("docs/HOOKS_REFERENCE.md", "All 18 hook events + schemas", 150),
            PhaseFile("docs/MODULES_CATALOG.md", "Module descriptions", 80),
            PhaseFile("docs/CREATING_MODULES.md", "Extensibility guide", 60),
            PhaseFile("docs/MIGRATION.md", "Migration guide", 40),
        ],
        acceptance_criteria=[
            "GitHub repo created and accessible",
            "CI pipeline passes on push",
            "README.md has quick start that works",
            "All docs are comprehensive and accurate",
            "Release v0.1.0 tagged",
        ],
        tools_required=["Bash", "Write", "Edit"],
    ),
]


# =============================================================================
# Plan File Generators
# =============================================================================


def generate_frontmatter(phase: Phase) -> str:
    """Generate YAML frontmatter for a phase file."""
    cross_refs = []
    for dep_id in phase.depends_on:
        dep_phase = next(p for p in PHASES if p.id == dep_id)
        cross_refs.append(
            f'  - {{file: "{dep_id:02d}-phase-{_slug(dep_phase.title)}.md", relation: "depends_on"}}'
        )

    # Find phases that depend on this one
    for p in PHASES:
        if phase.id in p.depends_on:
            cross_refs.append(
                f'  - {{file: "{p.id:02d}-phase-{_slug(p.title)}.md", relation: "blocks"}}'
            )

    refs_str = "\n".join(cross_refs) if cross_refs else "  []"

    return textwrap.dedent(f"""\
        ---
        plan: claude-code-kazuba
        version: "2.0"
        phase: {phase.id}
        title: "{phase.title}"
        effort: "{phase.effort}"
        estimated_tokens: {phase.estimated_tokens}
        depends_on: {json.dumps(phase.depends_on)}
        parallel_group: {json.dumps(phase.parallel_group)}
        context_budget: "{phase.context_budget}"
        validation_script: "validation/validate_phase_{phase.id:02d}.py"
        checkpoint: "checkpoints/phase_{phase.id:02d}.toon"
        status: "pending"
        cross_refs:
        {refs_str}
        ---
    """)


def generate_phase_content(phase: Phase) -> str:
    """Generate the full markdown content for a phase file."""
    sections = [generate_frontmatter(phase)]

    sections.append(f"# Phase {phase.id}: {phase.title}\n")
    sections.append(
        f"**Effort**: {phase.effort} | **Tokens**: ~{phase.estimated_tokens:,} | "
        f"**Context**: {phase.context_budget}\n"
    )

    if phase.depends_on:
        deps = ", ".join(f"Phase {d}" for d in phase.depends_on)
        sections.append(f"**Dependencies**: {deps}\n")

    if phase.parallel_group:
        parallel_peers = [
            p for p in PHASES if p.parallel_group == phase.parallel_group and p.id != phase.id
        ]
        if parallel_peers:
            peers = ", ".join(f"Phase {p.id} ({p.title})" for p in parallel_peers)
            sections.append(f"**Parallel with**: {peers}\n")

    sections.append(f"\n## Description\n\n{phase.description}\n")

    sections.append("\n## Objectives\n")
    for obj in phase.objectives:
        sections.append(f"- [ ] {obj}")
    sections.append("")

    if phase.files_to_create:
        sections.append("\n## Files to Create\n")
        sections.append("| Path | Description | Min Lines |")
        sections.append("|------|-------------|-----------|")
        for f in phase.files_to_create:
            sections.append(f"| `{f.path}` | {f.description} | {f.min_lines} |")
        sections.append("")

    if phase.source_files:
        sections.append("\n## Source Files (extract from)\n")
        for sf in phase.source_files:
            sections.append(f"- `{sf}`")
        sections.append("")

    if phase.tdd_spec:
        sections.append(f"\n{phase.tdd_spec}")

    if phase.implementation_notes:
        sections.append(f"\n{phase.implementation_notes}")

    if phase.tests:
        sections.append("\n## Testing\n")
        sections.append(f"- **Test directory**: `{phase.tests.test_dir}`")
        sections.append(f"- **Min coverage per file**: {phase.tests.min_coverage}%")
        sections.append("- **Test files**:")
        for tf in phase.tests.test_files:
            sections.append(f"  - `{tf}`")
        sections.append("")

    sections.append("\n## Acceptance Criteria\n")
    for ac in phase.acceptance_criteria:
        sections.append(f"- [ ] {ac}")
    sections.append("")

    if phase.tools_required:
        sections.append("\n## Tools Required\n")
        sections.append(f"- {', '.join(phase.tools_required)}")
        if phase.mcp_servers:
            sections.append(f"- MCP: {', '.join(phase.mcp_servers)}")
        if phase.plugins:
            sections.append(f"- Plugins: {', '.join(phase.plugins)}")
        sections.append("")

    if phase.risks:
        sections.append("\n## Risks\n")
        for r in phase.risks:
            sections.append(f"- {r}")
        sections.append("")

    sections.append("\n## Checkpoint\n")
    sections.append("After completing this phase, run:")
    sections.append("```bash")
    sections.append(f"python plans/validation/validate_phase_{phase.id:02d}.py")
    sections.append("```")
    sections.append(f"Checkpoint saved to: `checkpoints/phase_{phase.id:02d}.toon`\n")

    return "\n".join(sections)


def generate_index() -> str:
    """Generate the master index file with DAG visualization."""
    lines = [
        textwrap.dedent("""\
        ---
        plan: claude-code-kazuba
        version: "2.0"
        type: index
        total_phases: 11
        total_estimated_tokens: 143000
        generated: "{now}"
        ---

        # Claude Code Kazuba — Pln2 Master Index

        ## Overview

        Framework de configuração de excelência para Claude Code.
        Pln2 = (Pln1)² — amplificado em 9 dimensões.

        ## Dependency Graph (DAG)

        ```
        Phase 0 (Bootstrap)
            ├── Phase 1 (Shared Lib)
            │   ├── Phase 3 (Hooks Essential)  ─┐
            │   ├── Phase 4 (Hooks Quality)     ├─ PARALLEL (hooks)
            │   └── Phase 5 (Hooks Routing)    ─┘
            └── Phase 2 (Core Module)
        Phase 0
            ├── Phase 6 (Skills/Agents)  ─┐
            └── Phase 7 (Config/Contexts) ┘─ PARALLEL (content)

        Phase 2,3,4,5,6,7 → Phase 8 (Installer CLI)
        Phase 8 → Phase 9 (Integration Tests)
        Phase 9 → Phase 10 (GitHub + CI + Docs)
        ```

        **Critical Path**: 0 → 1 → 3 → 8 → 9 → 10 (6 sequential phases)
        **With parallelism**: ~8 context windows instead of 11

        ## Phase Summary

        | # | Title | Effort | Tokens | Group | Status |
        |---|-------|--------|--------|-------|--------|
    """).format(now=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    ]

    for phase in PHASES:
        group = phase.parallel_group or "sequential"
        lines.append(
            f"| {phase.id} | [{phase.title}]({phase.id:02d}-phase-{_slug(phase.title)}.md) "
            f"| {phase.effort} | ~{phase.estimated_tokens:,} | {group} | pending |"
        )

    lines.append("")
    lines.append("\n## Execution Strategy\n")
    lines.append("### Sequential Phases (must be in order)")
    lines.append("- Phase 0 → Phase 1 → Phase 2 (foundation)")
    lines.append("- Phase 8 → Phase 9 → Phase 10 (integration & delivery)")
    lines.append("")
    lines.append("### Parallel Groups")
    lines.append(
        "- **hooks** (after Phase 1): Phases 3, 4, 5 via Agent Team (3 agents, worktree isolation)"
    )
    lines.append(
        "- **content** (after Phase 0): Phases 6, 7 via Agent Team (2 agents, worktree isolation)"
    )
    lines.append("")
    lines.append("### Swarm Configuration")
    lines.append("```yaml")
    lines.append("team: claude-code-kazuba-build")
    lines.append("parallel_groups:")
    lines.append("  hooks:")
    lines.append("    phases: [3, 4, 5]")
    lines.append("    agents: 3")
    lines.append("    isolation: worktree")
    lines.append("    merge_strategy: git merge --no-ff")
    lines.append("  content:")
    lines.append("    phases: [6, 7]")
    lines.append("    agents: 2")
    lines.append("    isolation: worktree")
    lines.append("    merge_strategy: git merge --no-ff")
    lines.append("```")
    lines.append("")
    lines.append("## Validation\n")
    lines.append("Each phase has a validation script in `validation/validate_phase_NN.py`.")
    lines.append("Run all validations: `python plans/validation/validate_all.py`")
    lines.append("")
    lines.append("## Checkpoints\n")
    lines.append("Checkpoints saved in `.toon` format (msgpack) at `checkpoints/phase_NN.toon`.")
    lines.append("Recovery: load last .toon checkpoint to resume from any phase.\n")

    return "\n".join(lines)


def generate_validation_script(phase: Phase) -> str:
    """Generate validation script for a phase."""
    expected_files_str = ",\n        ".join(f'"{f.path}"' for f in phase.files_to_create)
    min_lines_map = ", ".join(f'"{f.path}": {f.min_lines}' for f in phase.files_to_create)

    test_dir = phase.tests.test_dir if phase.tests else f"tests/phase_{phase.id:02d}/"
    min_cov = phase.tests.min_coverage if phase.tests else 90

    return textwrap.dedent(f'''\
        #!/usr/bin/env python3
        """
        Validation Script — Phase {phase.id}: {phase.title}

        Verifies all deliverables, runs tests, checks coverage, saves checkpoint.
        Exit 0 = PASS, Exit 1 = FAIL
        """
        from __future__ import annotations

        import json
        import subprocess
        import sys
        import time
        from pathlib import Path

        try:
            import msgpack
        except ImportError:
            msgpack = None  # type: ignore[assignment]

        PHASE_ID = {phase.id}
        PHASE_TITLE = "{phase.title}"
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        CHECKPOINT_DIR = BASE_DIR / "checkpoints"
        CHECKPOINT_DIR.mkdir(exist_ok=True)

        EXPECTED_FILES = [
            {expected_files_str}
        ]
        MIN_LINES = {{{min_lines_map}}}
        TEST_DIR = "{test_dir}"
        MIN_COVERAGE = {min_cov}


        def check_files_exist() -> list[str]:
            """Verify all expected files exist and meet minimum line counts."""
            errors: list[str] = []
            for fpath in EXPECTED_FILES:
                full = BASE_DIR / fpath
                if not full.exists():
                    errors.append(f"MISSING: {{fpath}}")
                    continue
                lines = len(full.read_text().splitlines())
                min_l = MIN_LINES.get(fpath, 1)
                if lines < min_l:
                    errors.append(f"TOO_SHORT: {{fpath}} ({{lines}} < {{min_l}} lines)")
            return errors


        def run_tests() -> dict:
            """Run pytest with coverage for this phase."""
            test_path = BASE_DIR / TEST_DIR
            if not test_path.exists():
                return {{"status": "SKIP", "reason": f"Test dir {{TEST_DIR}} not found"}}

            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest", str(test_path),
                    "--tb=short", "-q",
                    f"--cov={{BASE_DIR / 'lib'}}",
                    "--cov-report=json:coverage.json",
                    f"--cov-fail-under={{MIN_COVERAGE}}",
                ],
                capture_output=True, text=True, cwd=str(BASE_DIR),
            )

            cov_data = {{}}
            cov_file = BASE_DIR / "coverage.json"
            if cov_file.exists():
                cov_data = json.loads(cov_file.read_text())
                cov_file.unlink()

            return {{
                "status": "PASS" if result.returncode == 0 else "FAIL",
                "returncode": result.returncode,
                "stdout": result.stdout[-500:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else "",
                "coverage": cov_data.get("totals", {{}}).get("percent_covered", 0),
            }}


        def run_lint() -> dict:
            """Run ruff check on lib/ directory."""
            result = subprocess.run(
                [sys.executable, "-m", "ruff", "check", str(BASE_DIR / "lib"), "--quiet"],
                capture_output=True, text=True, cwd=str(BASE_DIR),
            )
            return {{
                "status": "PASS" if result.returncode == 0 else "FAIL",
                "errors": result.stdout.strip() if result.stdout else "",
            }}


        def run_typecheck() -> dict:
            """Run pyright on lib/ directory."""
            result = subprocess.run(
                [sys.executable, "-m", "pyright", str(BASE_DIR / "lib"), "--outputjson"],
                capture_output=True, text=True, cwd=str(BASE_DIR),
            )
            return {{
                "status": "PASS" if result.returncode == 0 else "FAIL",
                "output": result.stdout[-300:] if result.stdout else "",
            }}


        def save_checkpoint(results: dict) -> Path:
            """Save checkpoint in .toon format (msgpack)."""
            checkpoint = {{
                "phase_id": PHASE_ID,
                "phase_title": PHASE_TITLE,
                "timestamp": time.time(),
                "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "results": results,
                "version": "2.0",
            }}

            path = CHECKPOINT_DIR / f"phase_{{PHASE_ID:02d}}.toon"
            if msgpack is not None:
                path.write_bytes(msgpack.packb(checkpoint, use_bin_type=True))
            else:
                # Fallback: JSON with .toon extension
                path.write_text(json.dumps(checkpoint, indent=2, default=str))

            return path


        def main() -> int:
            print(f"\\n{"=" * 60}")
            print(f"  Phase {{PHASE_ID}} Validation: {{PHASE_TITLE}}")
            print(f"{"=" * 60}\\n")

            results: dict = {{"phase": PHASE_ID, "checks": {{}}}}
            all_pass = True

            # Check 1: Files exist
            file_errors = check_files_exist()
            results["checks"]["files"] = {{
                "status": "PASS" if not file_errors else "FAIL",
                "total": len(EXPECTED_FILES),
                "missing": len(file_errors),
                "errors": file_errors,
            }}
            if file_errors:
                all_pass = False
                for e in file_errors:
                    print(f"  [FAIL] {{e}}")
            else:
                print(f"  [PASS] All {{len(EXPECTED_FILES)}} files present")

            # Check 2: Tests
            test_results = run_tests()
            results["checks"]["tests"] = test_results
            if test_results["status"] == "FAIL":
                all_pass = False
                print(f"  [FAIL] Tests failed (coverage: {{test_results.get('coverage', 'N/A')}}%)")
            elif test_results["status"] == "SKIP":
                print(f"  [SKIP] {{test_results['reason']}}")
            else:
                print(f"  [PASS] Tests passed (coverage: {{test_results.get('coverage', 'N/A')}}%)")

            # Check 3: Lint
            lint_results = run_lint()
            results["checks"]["lint"] = lint_results
            if lint_results["status"] == "FAIL":
                all_pass = False
                print(f"  [FAIL] Lint errors found")
            else:
                print(f"  [PASS] Lint clean")

            # Check 4: Type check
            type_results = run_typecheck()
            results["checks"]["typecheck"] = type_results
            if type_results["status"] == "FAIL":
                print(f"  [WARN] Type check issues (non-blocking)")
            else:
                print(f"  [PASS] Type check clean")

            # Save checkpoint
            results["overall"] = "PASS" if all_pass else "FAIL"
            cp_path = save_checkpoint(results)
            print(f"\\n  Checkpoint: {{cp_path}}")

            print(f"\\n  Overall: {{results['overall']}}")
            print(f"{"=" * 60}\\n")

            return 0 if all_pass else 1


        if __name__ == "__main__":
            sys.exit(main())
    ''')


def generate_validate_all() -> str:
    """Generate the validate_all.py runner."""
    phase_ids = [p.id for p in PHASES]
    return textwrap.dedent(f'''\
        #!/usr/bin/env python3
        """Run all phase validation scripts sequentially."""
        from __future__ import annotations

        import importlib.util
        import sys
        from pathlib import Path

        PHASE_IDS = {phase_ids}


        def main() -> int:
            validation_dir = Path(__file__).parent
            failed: list[int] = []

            for phase_id in PHASE_IDS:
                script = validation_dir / f"validate_phase_{{phase_id:02d}}.py"
                if not script.exists():
                    print(f"[SKIP] Phase {{phase_id}}: validation script not found")
                    continue

                spec = importlib.util.spec_from_file_location(f"validate_{{phase_id}}", script)
                if spec is None or spec.loader is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                result = mod.main()
                if result != 0:
                    failed.append(phase_id)

            print(f"\\n{"=" * 60}")
            if failed:
                print(f"  FAILED phases: {{failed}}")
                return 1
            print(f"  ALL PHASES PASSED")
            print(f"{"=" * 60}")
            return 0


        if __name__ == "__main__":
            sys.exit(main())
    ''')


# =============================================================================
# Utilities
# =============================================================================


def _slug(title: str) -> str:
    """Convert title to filename slug."""
    return (
        title.lower()
        .replace(" + ", "-")
        .replace(" ", "-")
        .replace("/", "-")
        .replace("(", "")
        .replace(")", "")
    )


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Pln2 plan files")
    parser.add_argument("--output-dir", default="plans", help="Output directory for plan files")
    parser.add_argument("--validate", action="store_true", help="Validate generated files")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    output = base / args.output_dir
    validation = output / "validation"
    output.mkdir(parents=True, exist_ok=True)
    validation.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []

    # Generate index
    index_path = output / "00-index.md"
    index_path.write_text(generate_index())
    generated.append(str(index_path.relative_to(base)))
    print(f"  [GEN] {index_path.relative_to(base)}")

    # Generate phase files
    for phase in PHASES:
        slug = _slug(phase.title)
        fname = f"{phase.id + 1:02d}-phase-{slug}.md"
        fpath = output / fname
        fpath.write_text(generate_phase_content(phase))
        generated.append(str(fpath.relative_to(base)))
        print(f"  [GEN] {fpath.relative_to(base)}")

    # Generate validation scripts
    for phase in PHASES:
        vpath = validation / f"validate_phase_{phase.id:02d}.py"
        vpath.write_text(generate_validation_script(phase))
        vpath.chmod(0o755)
        generated.append(str(vpath.relative_to(base)))
        print(f"  [GEN] {vpath.relative_to(base)}")

    # Generate validate_all
    va_path = validation / "validate_all.py"
    va_path.write_text(generate_validate_all())
    va_path.chmod(0o755)
    generated.append(str(va_path.relative_to(base)))
    print(f"  [GEN] {va_path.relative_to(base)}")

    print(f"\n  Total: {len(generated)} files generated")

    if args.validate:
        print("\n  Validating generated files...")
        errors = 0
        for g in generated:
            p = base / g
            if not p.exists():
                print(f"  [FAIL] {g} does not exist")
                errors += 1
            elif p.stat().st_size == 0:
                print(f"  [FAIL] {g} is empty")
                errors += 1
        if errors:
            print(f"\n  {errors} validation errors!")
            return 1
        print("  All files validated OK")

    return 0


if __name__ == "__main__":
    sys.exit(main())
