#!/usr/bin/env python3
"""
Pln2 v2 Generator — Source Integration Plan for claude-code-kazuba v0.2.0.

Generates amplified plan files (phases 11-22) with source extraction maps,
Pydantic model specs, hook specifications, and validation scripts.

Usage:
    python scripts/generate_plan_v2.py [--output-dir plans/v2] [--validate]
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
# Data Models — v1 (preserved)
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


# =============================================================================
# Data Models — v2 (amplified)
# =============================================================================


@dataclass(frozen=True)
class SourceFile:
    """Source file to extract from another project."""

    path: str
    target: str
    extraction_type: str  # DIRECT_COPY | ADAPT_IMPORTS | REIMPLEMENT
    loc: int
    key_classes: tuple[str, ...] = ()
    key_methods: tuple[str, ...] = ()
    external_deps: tuple[str, ...] = ()
    adaptation_notes: str = ""


@dataclass(frozen=True)
class PydanticModelSpec:
    """Pydantic v2 model to be created."""

    name: str
    module: str
    fields: tuple[tuple[str, str, str], ...] = ()  # (name, type, default)
    frozen: bool = True
    description: str = ""


@dataclass(frozen=True)
class HookSpec:
    """Hook specification with performance targets."""

    name: str
    event: str
    module: str  # hooks-essential, hooks-quality, etc.
    exit_codes: tuple[int, ...] = (0,)
    latency_target_ms: int = 500
    integration_points: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class TestFileSpec:
    """Test file specification with coverage target."""

    path: str
    min_tests: int = 10
    coverage_target: int = 90
    test_categories: tuple[str, ...] = ("unit",)


# =============================================================================
# Amplified Phase dataclass
# =============================================================================


@dataclass(frozen=True)
class Phase:
    """A single phase of the Pln2 v2 plan (amplified)."""

    id: int
    title: str
    effort: str  # S, M, L, XL
    estimated_tokens: int
    depends_on: list[int] = field(default_factory=list)
    parallel_group: str | None = None
    description: str = ""
    objectives: list[str] = field(default_factory=list)
    files_to_create: list[PhaseFile] = field(default_factory=list)
    source_files: list[SourceFile] = field(default_factory=list)
    pydantic_models: list[PydanticModelSpec] = field(default_factory=list)
    hook_specs: list[HookSpec] = field(default_factory=list)
    test_specs: list[TestFileSpec] = field(default_factory=list)
    tests: PhaseTest | None = None
    agents: list[AgentSpec] = field(default_factory=list)
    tdd_spec: str = ""
    context_budget: str = "1 context window (~180k tokens)"
    tools_required: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recovery_plan: str = ""
    implementation_notes: str = ""
    agent_execution_spec: str = ""


# =============================================================================
# Phase Definitions — Pln2 v2 (IDs 11-22)
# =============================================================================

PHASES: list[Phase] = [
    # =========================================================================
    # Phase 11: Shared Infrastructure (Foundation)
    # =========================================================================
    Phase(
        id=11,
        title="Shared Infrastructure",
        effort="M",
        estimated_tokens=12000,
        depends_on=[],
        parallel_group=None,
        description=(
            "Build the shared infrastructure layer that all v2 components depend on. "
            "Circuit breaker, trace manager, hook logger, and event bus form the "
            "foundation for reliability, observability, and decoupled communication."
        ),
        objectives=[
            "Extract and adapt circuit breaker from analise hooks (thread-safe, Pydantic v2 config)",
            "Extract and adapt trace manager (pure Python, no Rust dependency)",
            "Extract and adapt hook logger (JSON-structured output)",
            "Implement event bus based on hypervisor_v2.py event mesh pattern",
            "Achieve 90%+ coverage per file with TDD approach",
        ],
        source_files=[
            SourceFile(
                path="analise/.claude/hooks/common/hook_circuit_breaker_v2.py",
                target="lib/circuit_breaker.py",
                extraction_type="ADAPT_IMPORTS",
                loc=150,
                key_classes=(
                    "HookCircuitBreaker",
                    "CircuitBreakerConfig",
                    "CircuitBreakerRegistry",
                ),
                key_methods=("record_success", "record_failure", "is_open"),
                external_deps=("threading",),
                adaptation_notes=("Remove kazuba_rust_core import, use Pydantic v2 config"),
            ),
            SourceFile(
                path="analise/.claude/hooks/common/trace_manager.py",
                target="lib/trace_manager.py",
                extraction_type="ADAPT_IMPORTS",
                loc=80,
                key_classes=("TraceManager",),
                key_methods=("get", "start_session", "record_file_read", "record_search"),
                external_deps=(),
                adaptation_notes=("Remove kazuba_rust_core.TraceSession dep, pure Python"),
            ),
            SourceFile(
                path="analise/.claude/hooks/common/hook_logger.py",
                target="lib/hook_logger.py",
                extraction_type="ADAPT_IMPORTS",
                loc=80,
                key_classes=("HookLogger", "LogLevel"),
                key_methods=("_write_log", "info", "error"),
                external_deps=(),
                adaptation_notes="Use json_output.py for formatting",
            ),
            SourceFile(
                path="(new)",
                target="lib/event_bus.py",
                extraction_type="REIMPLEMENT",
                loc=120,
                key_classes=("EventBus",),
                key_methods=("subscribe", "publish", "unsubscribe"),
                external_deps=(),
                adaptation_notes=("Based on event mesh pattern from hypervisor_v2.py"),
            ),
        ],
        pydantic_models=[
            PydanticModelSpec(
                "CircuitBreakerConfig",
                "lib/circuit_breaker.py",
                (
                    ("max_failures", "int", "5"),
                    ("cooldown_seconds", "float", "60.0"),
                    ("half_open_max", "int", "1"),
                ),
                True,
                "Thread-safe circuit breaker config",
            ),
            PydanticModelSpec(
                "TraceNode",
                "lib/trace_manager.py",
                (
                    ("name", "str", '""'),
                    ("start_time", "float", "0.0"),
                    ("children", "list[TraceNode]", "[]"),
                ),
                True,
                "Trace tree node",
            ),
        ],
        files_to_create=[
            PhaseFile(
                "lib/circuit_breaker.py", "Thread-safe circuit breaker with Pydantic config", 200
            ),
            PhaseFile("lib/trace_manager.py", "Trace tree for hook execution", 80),
            PhaseFile("lib/hook_logger.py", "Structured JSON hook logger", 80),
            PhaseFile("lib/event_bus.py", "Pub/sub event bus for decoupled communication", 100),
        ],
        test_specs=[
            TestFileSpec("tests/phase_11/test_circuit_breaker.py", 20, 90),
            TestFileSpec("tests/phase_11/test_trace_manager.py", 15, 90),
            TestFileSpec("tests/phase_11/test_hook_logger.py", 10, 90),
            TestFileSpec("tests/phase_11/test_event_bus.py", 15, 90),
        ],
        tests=PhaseTest(
            "tests/phase_11/",
            90,
            [
                "test_circuit_breaker.py",
                "test_trace_manager.py",
                "test_hook_logger.py",
                "test_event_bus.py",
            ],
        ),
        acceptance_criteria=[
            "All 4 lib files importable and pyright clean",
            "Circuit breaker transitions CLOSED->OPEN->HALF_OPEN correctly",
            "Event bus pub/sub works with multiple subscribers",
            "90%+ coverage per file",
            "723 existing tests still pass (regression)",
        ],
        recovery_plan=(
            "If circuit breaker threading issues: simplify to single-threaded with asyncio.Lock"
        ),
        agent_execution_spec="general-purpose with worktree isolation",
        tools_required=["Bash", "Write", "Edit", "Agent(general-purpose)"],
    ),
    # =========================================================================
    # Phase 12: Rust Acceleration Layer (Optional)
    # =========================================================================
    Phase(
        id=12,
        title="Rust Acceleration Layer",
        effort="L",
        estimated_tokens=15000,
        depends_on=[11],
        parallel_group="infra",
        description=(
            "Integrate the Rust acceleration crate for high-performance pattern matching, "
            "secrets detection, and code quality validation. This phase is OPTIONAL: "
            "the Python fallback must always work without Rust installed."
        ),
        objectives=[
            "Copy kazuba-hooks Rust crate and verify cargo check passes",
            "Create Python facade (lib/rust_bridge.py) with try/except fallback",
            "Benchmark Rust vs Python performance (target: 5x speedup)",
            "Add optional [rust] dependency group to pyproject.toml",
            "Ensure all code paths work WITHOUT Rust installed",
        ],
        source_files=[
            SourceFile(
                path="kazuba-cargo/.claude/rust/kazuba-hooks/",
                target="rust/kazuba-hooks/",
                extraction_type="DIRECT_COPY",
                loc=7000,
                key_classes=(
                    "SecretsDetector",
                    "BashSafetyValidator",
                    "CodeQualityValidator",
                    "SkillMatcher",
                ),
                key_methods=(
                    "py_detect_secrets",
                    "py_validate_code",
                    "py_skill_match",
                ),
                external_deps=(
                    "aho-corasick",
                    "regex",
                    "rayon",
                    "pyo3",
                    "serde",
                ),
                adaptation_notes="Copy entire crate, verify cargo check passes",
            ),
            SourceFile(
                path="(new)",
                target="lib/rust_bridge.py",
                extraction_type="REIMPLEMENT",
                loc=150,
                key_classes=("RustBridge",),
                key_methods=("scan_secrets", "check_bash_safety", "match_patterns"),
                external_deps=(),
                adaptation_notes=(
                    "Python facade with try/except import fallback to lib/patterns.py"
                ),
            ),
        ],
        files_to_create=[
            PhaseFile("rust/kazuba-hooks/Cargo.toml", "Rust crate manifest", 50),
            PhaseFile("rust/kazuba-hooks/src/lib.rs", "Rust crate entry point with PyO3", 800),
            PhaseFile("lib/rust_bridge.py", "Python facade with Rust fallback", 150),
        ],
        test_specs=[
            TestFileSpec(
                "tests/phase_12/test_rust_bridge.py",
                20,
                90,
                ("unit", "integration"),
            ),
            TestFileSpec("tests/phase_12/test_rust_fallback.py", 15, 90),
        ],
        tests=PhaseTest(
            "tests/phase_12/",
            90,
            ["test_rust_bridge.py", "test_rust_fallback.py"],
        ),
        acceptance_criteria=[
            "cargo check passes in rust/kazuba-hooks/",
            "lib/rust_bridge.py works WITH Rust installed (if available)",
            "lib/rust_bridge.py gracefully falls back to Python WITHOUT Rust",
            "Benchmark: Rust >=5x faster than Python for pattern matching",
            "pyproject.toml has optional [rust] dep group",
        ],
        risks=[
            "Rust toolchain not available on all machines -- fallback must work",
            "PyO3 version mismatch -- pin to 0.28.2",
        ],
        recovery_plan=(
            "If Rust compilation fails: mark phase as OPTIONAL, Python-only fallback is sufficient"
        ),
        agent_execution_spec="general-purpose with Rust toolchain",
        tools_required=["Bash", "Write", "Edit"],
    ),
    # =========================================================================
    # Phase 13: Core Governance + CILA Formal
    # =========================================================================
    Phase(
        id=13,
        title="Core Governance + CILA Formal",
        effort="M",
        estimated_tokens=12000,
        depends_on=[11],
        parallel_group="infra",
        description=(
            "Formalize the governance rules and CILA taxonomy as programmatically "
            "enforceable components. Extract CODE-FIRST cycle, ZERO-HALLUCINATION "
            "enforcement, and L0-L6 intent heuristics into reusable modules."
        ),
        objectives=[
            "Extract and generalize core-governance.md (remove ANTT-specific refs)",
            "Extract and generalize agent-teams.md for any project",
            "Adapt CILA taxonomy (L0-L6 heuristics) without domain specifics",
            "Implement governance.py with programmatic rule enforcement",
            "Adapt strategy_enforcer.py to integrate with cila_router.py",
        ],
        source_files=[
            SourceFile(
                path="analise/.claude/rules/00-core-governance.md",
                target="core/rules/core-governance.md",
                extraction_type="ADAPT_IMPORTS",
                loc=233,
                adaptation_notes=("Remove ANTT-specific refs, keep CODE-FIRST 6-step cycle"),
            ),
            SourceFile(
                path="analise/.claude/rules/agent-teams.md",
                target="core/rules/agent-teams.md",
                extraction_type="ADAPT_IMPORTS",
                loc=184,
                adaptation_notes="Generalize from analise to any project",
            ),
            SourceFile(
                path="analise/.claude/rules/antt/cila-taxonomy.md",
                target="modules/hooks-routing/config/cila-taxonomy.md",
                extraction_type="ADAPT_IMPORTS",
                loc=54,
                adaptation_notes="Remove ANTT, keep L0-L6 heuristics",
            ),
            SourceFile(
                path="(new)",
                target="lib/governance.py",
                extraction_type="REIMPLEMENT",
                loc=200,
                key_classes=(
                    "GovernanceRule",
                    "CodeFirstPhase",
                    "ValidationCriteria",
                ),
                key_methods=(
                    "validate_code_first_cycle",
                    "check_hallucination_risk",
                    "enforce_local_cache_first",
                ),
                external_deps=("pydantic",),
                adaptation_notes=("Programmatic enforcement of governance rules"),
            ),
            SourceFile(
                path="analise/.claude/hooks/context/strategy_enforcer.py",
                target="modules/hooks-routing/hooks/strategy_enforcer.py",
                extraction_type="ADAPT_IMPORTS",
                loc=150,
                adaptation_notes="Enforce CILA level-based strategy",
            ),
        ],
        pydantic_models=[
            PydanticModelSpec(
                "GovernanceRule",
                "lib/governance.py",
                (
                    ("name", "str", '""'),
                    ("level", "str", '"mandatory"'),
                    ("enforcement", "str", '"block"'),
                ),
                True,
                "Governance rule definition",
            ),
            PydanticModelSpec(
                "CodeFirstPhase",
                "lib/governance.py",
                (
                    ("phase", "str", '""'),
                    ("completed", "bool", "False"),
                    ("evidence", "str", '""'),
                ),
                True,
                "CODE-FIRST cycle phase",
            ),
        ],
        files_to_create=[
            PhaseFile("core/rules/core-governance.md", "Generalized governance rules", 200),
            PhaseFile("core/rules/agent-teams.md", "Agent team coordination rules", 150),
            PhaseFile(
                "modules/hooks-routing/config/cila-taxonomy.md",
                "CILA L0-L6 taxonomy",
                50,
            ),
            PhaseFile(
                "lib/governance.py",
                "Programmatic governance enforcement",
                200,
            ),
            PhaseFile(
                "modules/hooks-routing/hooks/strategy_enforcer.py",
                "CILA strategy enforcement hook",
                120,
            ),
        ],
        tests=PhaseTest(
            "tests/phase_13/",
            90,
            ["test_governance.py", "test_strategy_enforcer.py"],
        ),
        test_specs=[
            TestFileSpec("tests/phase_13/test_governance.py", 15, 90),
            TestFileSpec("tests/phase_13/test_strategy_enforcer.py", 10, 90),
        ],
        acceptance_criteria=[
            "Governance rules render in CLAUDE.md template",
            "lib/governance.py passes pyright strict",
            "strategy_enforcer.py integrates with existing cila_router.py",
            "CODE-FIRST 6-step cycle is enforceable programmatically",
        ],
        recovery_plan="If governance complexity grows: split into governance_core.py and governance_ext.py",
        agent_execution_spec="general-purpose with worktree isolation",
        tools_required=["Bash", "Write", "Edit"],
    ),
    # =========================================================================
    # Phase 14: Agent Triggers + Recovery Triggers
    # =========================================================================
    Phase(
        id=14,
        title="Agent Triggers + Recovery Triggers",
        effort="M",
        estimated_tokens=10000,
        depends_on=[11, 13],
        parallel_group="triggers",
        description=(
            "Extract and formalize 14 agent triggers and 8 recovery triggers from "
            "kazuba-cargo config. Triggers define when agents auto-activate and how "
            "the system recovers from failures, with Python conditions and thinking levels."
        ),
        objectives=[
            "Extract 14 agent triggers from kazuba-cargo config YAML",
            "Extract 5 auto + 3 manual recovery triggers",
            "Create Pydantic v2 models for trigger validation",
            "Integrate trigger loading with hypervisor config module",
            "Validate all triggers load from YAML without errors",
        ],
        source_files=[
            SourceFile(
                path="kazuba-cargo/.claude/config/agent_triggers.yaml",
                target="modules/config-hypervisor/config/agent_triggers.yaml",
                extraction_type="ADAPT_IMPORTS",
                loc=199,
                adaptation_notes=(
                    "14 triggers with Python conditions, thinking_levels, domain_keywords"
                ),
            ),
            SourceFile(
                path="kazuba-cargo/.claude/config/recovery_triggers.yaml",
                target="modules/config-hypervisor/config/recovery_triggers.yaml",
                extraction_type="DIRECT_COPY",
                loc=95,
                adaptation_notes="5 auto + 3 manual triggers",
            ),
        ],
        pydantic_models=[
            PydanticModelSpec(
                "AgentTrigger",
                "lib/config.py",
                (
                    ("name", "str", '""'),
                    ("type", "str", '"auto"'),
                    ("condition", "str", '""'),
                    ("thinking_level", "str", '"normal"'),
                    ("agent", "str", '""'),
                ),
                True,
                "Agent trigger with Python condition",
            ),
            PydanticModelSpec(
                "RecoveryTrigger",
                "lib/config.py",
                (
                    ("name", "str", '""'),
                    ("type", "str", '"auto"'),
                    ("on_event", "str", '""'),
                    ("action", "str", '""'),
                    ("max_retries", "int", "3"),
                ),
                True,
                "Recovery trigger definition",
            ),
        ],
        files_to_create=[
            PhaseFile(
                "modules/config-hypervisor/config/agent_triggers.yaml",
                "14 declarative agent triggers",
                180,
            ),
            PhaseFile(
                "modules/config-hypervisor/config/recovery_triggers.yaml",
                "8 recovery triggers (5 auto + 3 manual)",
                90,
            ),
        ],
        tests=PhaseTest(
            "tests/phase_14/",
            90,
            ["test_agent_triggers.py", "test_recovery_triggers.py"],
        ),
        test_specs=[
            TestFileSpec("tests/phase_14/test_agent_triggers.py", 14, 90),
            TestFileSpec("tests/phase_14/test_recovery_triggers.py", 10, 90),
        ],
        acceptance_criteria=[
            "14 agent triggers load from YAML",
            "8 recovery triggers load from YAML",
            "Pydantic models validate all trigger configs",
            "Triggers integrate with hypervisor config",
        ],
        recovery_plan="If trigger conditions fail: simplify to string-only conditions without eval",
        agent_execution_spec="general-purpose with worktree isolation",
        tools_required=["Bash", "Write", "Edit"],
    ),
    # =========================================================================
    # Phase 15: Hypervisor Executable
    # =========================================================================
    Phase(
        id=15,
        title="Hypervisor Executable",
        effort="L",
        estimated_tokens=15000,
        depends_on=[11, 14],
        parallel_group=None,
        description=(
            "Build the executable hypervisor that orchestrates phase execution "
            "with support for sequential, parallel, interactive, and dry-run modes. "
            "Integrates circuit breaker for failed phases and checkpoint recovery."
        ),
        objectives=[
            "Adapt hypervisor.py with lib.* imports (remove kazuba-cargo-specific code)",
            "Adapt hypervisor_v2.py abstract interfaces (EventMesh, GPUSkillRouter, etc.)",
            "Adapt hypervisor_bridge.py for learning/RLM system integration",
            "Implement ExecutionMode enum (sequential, parallel, interactive, dry_run)",
            "Implement checkpoint recovery from .toon files",
            "Integrate circuit breaker for phase failure handling",
        ],
        source_files=[
            SourceFile(
                path="kazuba-cargo/.claude/orchestration/kazuba_hypervisor.py",
                target="modules/config-hypervisor/src/hypervisor.py",
                extraction_type="ADAPT_IMPORTS",
                loc=200,
                key_classes=(
                    "HypervisorConfig",
                    "PhaseDefinition",
                    "ExecutionResult",
                ),
                key_methods=("execute_phase", "run_sequential", "run_parallel"),
                adaptation_notes=("Refactor imports to lib.*, remove kazuba-cargo-specific code"),
            ),
            SourceFile(
                path="kazuba-cargo/.claude/orchestration/hypervisor_v2.py",
                target="modules/config-hypervisor/src/hypervisor_v2.py",
                extraction_type="ADAPT_IMPORTS",
                loc=150,
                key_classes=(
                    "HypervisorConfig",
                    "HypervisorState",
                    "HookType",
                ),
                adaptation_notes=(
                    "Abstract interfaces for EventMesh, GPUSkillRouter, "
                    "UnifiedMemoryManager, AgentDelegationEngine"
                ),
            ),
            SourceFile(
                path="kazuba-cargo/.claude/orchestration/learning/hypervisor_bridge.py",
                target="modules/config-hypervisor/src/hypervisor_bridge.py",
                extraction_type="ADAPT_IMPORTS",
                loc=150,
                key_classes=("LearningEvent",),
                key_methods=("record_learning_event", "calculate_reward"),
                adaptation_notes=("Bridge between hypervisor and learning/RLM system"),
            ),
        ],
        files_to_create=[
            PhaseFile(
                "modules/config-hypervisor/src/hypervisor.py",
                "Phase execution engine with 4 modes",
                180,
            ),
            PhaseFile(
                "modules/config-hypervisor/src/hypervisor_v2.py",
                "V2 abstract interfaces for extensibility",
                140,
            ),
            PhaseFile(
                "modules/config-hypervisor/src/hypervisor_bridge.py",
                "Bridge to RLM learning system",
                130,
            ),
        ],
        tests=PhaseTest(
            "tests/phase_15/",
            90,
            [
                "test_hypervisor.py",
                "test_hypervisor_v2.py",
                "test_hypervisor_bridge.py",
            ],
        ),
        test_specs=[
            TestFileSpec("tests/phase_15/test_hypervisor.py", 15, 90),
            TestFileSpec("tests/phase_15/test_hypervisor_v2.py", 10, 90),
            TestFileSpec("tests/phase_15/test_hypervisor_bridge.py", 10, 90),
        ],
        acceptance_criteria=[
            "Hypervisor executes phases in dry-run mode",
            "ExecutionMode enum works (sequential, parallel, interactive, dry_run)",
            "Checkpoint recovery from .toon files works",
            "Circuit breaker integration for failed phases",
        ],
        recovery_plan=(
            "If parallel execution deadlocks: fall back to sequential mode with circuit breaker"
        ),
        agent_execution_spec="general-purpose with worktree isolation",
        tools_required=["Bash", "Write", "Edit", "Agent(general-purpose)"],
    ),
    # =========================================================================
    # Phase 16: Advanced Hooks Batch 1 (Lifecycle + Governance)
    # =========================================================================
    Phase(
        id=16,
        title="Advanced Hooks Batch 1",
        effort="M",
        estimated_tokens=12000,
        depends_on=[11],
        parallel_group="hooks",
        description=(
            "Extract lifecycle and governance hooks: session state manager for "
            "checkpoint before compaction, post-compact rule reinjector, and "
            "hooks health validator. These form the self-healing layer."
        ),
        objectives=[
            "Adapt session_state_manager.py (use lib/checkpoint.py for TOON)",
            "Adapt post_compact_reinjector.py (configurable rules injection)",
            "Reimplement validate_hooks_health.py (framework settings schema)",
            "All hooks follow fail-open pattern (exit 0 on error)",
        ],
        source_files=[
            SourceFile(
                path="analise/.claude/hooks/lifecycle/session_state_manager.py",
                target="modules/hooks-essential/hooks/session_state_manager.py",
                extraction_type="ADAPT_IMPORTS",
                loc=250,
                key_classes=(
                    "SessionStateConfig",
                    "CaptureResult",
                    "SessionStateManager",
                ),
                key_methods=("capture_state", "restore_state", "mark_checkpoint"),
                adaptation_notes=("Remove StateBus/WAL deps, use lib/checkpoint.py for TOON"),
            ),
            SourceFile(
                path="analise/.claude/hooks/lifecycle/post_compact_reinjector.py",
                target="modules/hooks-essential/hooks/post_compact_reinjector.py",
                extraction_type="ADAPT_IMPORTS",
                loc=96,
                adaptation_notes=("Inject critical rules as additionalContext post-compaction"),
            ),
            SourceFile(
                path="analise/.claude/hooks/governance/validate_hooks_health.py",
                target="modules/hooks-quality/hooks/validate_hooks_health.py",
                extraction_type="REIMPLEMENT",
                loc=150,
                adaptation_notes=(
                    "Rewrite to use framework settings schema instead of settings.local.json"
                ),
            ),
        ],
        hook_specs=[
            HookSpec(
                "session_state_manager",
                "PreCompact",
                "hooks-essential",
                (0,),
                200,
                ("lib/checkpoint.py", "lib/circuit_breaker.py"),
                "Checkpoint state before context compaction",
            ),
            HookSpec(
                "post_compact_reinjector",
                "PreCompact",
                "hooks-essential",
                (0,),
                100,
                ("core/rules/",),
                "Reinject critical rules after compaction",
            ),
            HookSpec(
                "validate_hooks_health",
                "SessionStart",
                "hooks-quality",
                (0,),
                500,
                ("lib/circuit_breaker.py",),
                "Health check all registered hooks",
            ),
        ],
        files_to_create=[
            PhaseFile(
                "modules/hooks-essential/hooks/session_state_manager.py",
                "State checkpoint before compaction",
                200,
            ),
            PhaseFile(
                "modules/hooks-essential/hooks/post_compact_reinjector.py",
                "Rule reinjection after compaction",
                80,
            ),
            PhaseFile(
                "modules/hooks-quality/hooks/validate_hooks_health.py",
                "Hook health validator on session start",
                120,
            ),
        ],
        tests=PhaseTest(
            "tests/phase_16/",
            90,
            [
                "test_session_state_manager.py",
                "test_post_compact_reinjector.py",
                "test_validate_hooks_health.py",
            ],
        ),
        test_specs=[
            TestFileSpec("tests/phase_16/test_session_state_manager.py", 15, 90),
            TestFileSpec("tests/phase_16/test_post_compact_reinjector.py", 10, 90),
            TestFileSpec("tests/phase_16/test_validate_hooks_health.py", 12, 90),
        ],
        acceptance_criteria=[
            "session_state_manager creates valid TOON checkpoints",
            "post_compact_reinjector reinjects rules via additionalContext",
            "validate_hooks_health checks all hooks and reports status",
            "All hooks exit 0 on error (fail-open)",
            "90%+ coverage per file",
        ],
        recovery_plan="If session state is too large for TOON: implement incremental delta checkpoints",
        agent_execution_spec="general-purpose with worktree isolation",
        tools_required=["Bash", "Write", "Edit"],
    ),
    # =========================================================================
    # Phase 17: Advanced Hooks Batch 2 (Validation + Permissions + Synthesis)
    # =========================================================================
    Phase(
        id=17,
        title="Advanced Hooks Batch 2",
        effort="L",
        estimated_tokens=14000,
        depends_on=[11, 16],
        parallel_group="hooks",
        description=(
            "Extract validation orchestrator (SIAC with 4 concurrent motors), "
            "auto permission resolver, and programmatic tool calling advisor. "
            "These hooks provide the quality and efficiency layer."
        ),
        objectives=[
            "Adapt siac_orchestrator_v2.py (refactor motors to plugin registry pattern)",
            "Adapt auto_permission_resolver.py (externalize safe paths to YAML config)",
            "Adapt ptc_advisor.py (detect repetitive tool calls, suggest automation)",
            "All hooks follow fail-open pattern (exit 0 on error)",
        ],
        source_files=[
            SourceFile(
                path="analise/.claude/hooks/validation/siac_orchestrator_v2.py",
                target="modules/hooks-quality/hooks/siac_orchestrator.py",
                extraction_type="ADAPT_IMPORTS",
                loc=200,
                key_classes=("MotorResult", "SIACResult"),
                external_deps=("concurrent.futures",),
                adaptation_notes="Refactor motors to plugin registry pattern",
            ),
            SourceFile(
                path="analise/.claude/hooks/permissions/auto_permission_resolver.py",
                target="modules/hooks-routing/hooks/auto_permission_resolver.py",
                extraction_type="ADAPT_IMPORTS",
                loc=80,
                key_classes=("PermissionConfig",),
                adaptation_notes="Externalize safe paths to YAML config",
            ),
            SourceFile(
                path="analise/.claude/hooks/synthesis/ptc_advisor.py",
                target="modules/hooks-routing/hooks/ptc_advisor.py",
                extraction_type="ADAPT_IMPORTS",
                loc=200,
                adaptation_notes=("Detect repetitive tool calls, suggest automation"),
            ),
        ],
        hook_specs=[
            HookSpec(
                "siac_orchestrator",
                "PreToolUse",
                "hooks-quality",
                (0, 1),
                1500,
                ("lib/performance.py",),
                "4 concurrent validation motors",
            ),
            HookSpec(
                "auto_permission_resolver",
                "PreToolUse",
                "hooks-routing",
                (0, 2),
                100,
                (),
                "Auto-approve safe operations",
            ),
            HookSpec(
                "ptc_advisor",
                "PostToolUse",
                "hooks-routing",
                (0,),
                200,
                (),
                "Suggest programmatic tool calling patterns",
            ),
        ],
        files_to_create=[
            PhaseFile(
                "modules/hooks-quality/hooks/siac_orchestrator.py",
                "4-motor concurrent validation orchestrator",
                180,
            ),
            PhaseFile(
                "modules/hooks-routing/hooks/auto_permission_resolver.py",
                "Auto-approve safe file operations",
                100,
            ),
            PhaseFile(
                "modules/hooks-routing/hooks/ptc_advisor.py",
                "Programmatic tool calling advisor",
                150,
            ),
        ],
        tests=PhaseTest(
            "tests/phase_17/",
            90,
            [
                "test_siac_orchestrator.py",
                "test_auto_permission_resolver.py",
                "test_ptc_advisor.py",
            ],
        ),
        test_specs=[
            TestFileSpec("tests/phase_17/test_siac_orchestrator.py", 15, 90),
            TestFileSpec("tests/phase_17/test_auto_permission_resolver.py", 12, 90),
            TestFileSpec("tests/phase_17/test_ptc_advisor.py", 10, 90),
        ],
        acceptance_criteria=[
            "SIAC orchestrator runs 4 motors concurrently under P99 1500ms",
            "auto_permission_resolver auto-approves configured safe paths",
            "ptc_advisor detects 3+ repetitive tool calls and suggests batch",
            "All hooks exit 0 on error (fail-open)",
            "90%+ coverage per file",
        ],
        recovery_plan=(
            "If ThreadPoolExecutor hangs: add per-motor timeout with "
            "concurrent.futures.wait(timeout=2)"
        ),
        agent_execution_spec="general-purpose with worktree isolation",
        tools_required=["Bash", "Write", "Edit"],
    ),
    # =========================================================================
    # Phase 18: RLM (Learning Memory)
    # =========================================================================
    Phase(
        id=18,
        title="RLM Learning Memory",
        effort="L",
        estimated_tokens=15000,
        depends_on=[11, 15],
        parallel_group=None,
        description=(
            "Implement the Reinforcement Learning Memory system in pure Python. "
            "Q-learning with persistent Q-table, working memory with configurable "
            "capacity, and session management with TOON checkpoint integration."
        ),
        objectives=[
            "Reimplement reasoning patterns (CoT, GoT, ToT) from Rust in Python",
            "Reimplement TD-learner and Q-table in pure Python (no NumPy required)",
            "Create working memory with configurable capacity and eviction",
            "Create session manager with TOON checkpoint save/restore",
            "Create reward calculator for hook/agent performance",
            "Create RLM facade (lib/rlm.py) for integration with auto_compact",
        ],
        source_files=[
            SourceFile(
                path="kazuba-cargo/.claude/rust/kazuba-hooks/src/rlm_reasoning.rs",
                target="(reference only)",
                extraction_type="REIMPLEMENT",
                loc=200,
                key_classes=("ChainOfThought", "GraphOfThought", "TreeOfThought"),
                adaptation_notes=("Reimplement reasoning patterns in Python"),
            ),
            SourceFile(
                path="kazuba-cargo/.claude/rust/kazuba-hooks/src/learning.rs",
                target="(reference only)",
                extraction_type="REIMPLEMENT",
                loc=600,
                key_classes=("TDLearner", "ClusterEngine", "WorkingMemory"),
                adaptation_notes=("Reimplement Q-learning in pure Python (no numpy required)"),
            ),
            SourceFile(
                path="kazuba-cargo/.claude/orchestration/rlm/",
                target="modules/rlm/src/",
                extraction_type="ADAPT_IMPORTS",
                loc=300,
                adaptation_notes=("Python orchestration for RLM context management and recursion"),
            ),
        ],
        pydantic_models=[
            PydanticModelSpec(
                "RLMConfig",
                "modules/rlm/src/config.py",
                (
                    ("learning_rate", "float", "0.1"),
                    ("discount_factor", "float", "0.95"),
                    ("epsilon", "float", "0.1"),
                    ("max_history", "int", "1000"),
                ),
                True,
                "RLM hyperparameters",
            ),
            PydanticModelSpec(
                "LearningRecord",
                "modules/rlm/src/models.py",
                (
                    ("state", "str", '""'),
                    ("action", "str", '""'),
                    ("reward", "float", "0.0"),
                    ("timestamp", "float", "0.0"),
                ),
                True,
                "Single learning record",
            ),
        ],
        files_to_create=[
            PhaseFile("modules/rlm/MODULE.md", "RLM module manifest", 40),
            PhaseFile("modules/rlm/src/__init__.py", "RLM package init", 5),
            PhaseFile("modules/rlm/src/config.py", "RLM Pydantic config", 50),
            PhaseFile("modules/rlm/src/models.py", "RLM data models", 80),
            PhaseFile("modules/rlm/src/q_table.py", "Persistent Q-table", 150),
            PhaseFile("modules/rlm/src/working_memory.py", "Configurable working memory", 100),
            PhaseFile("modules/rlm/src/session_manager.py", "Session checkpoint manager", 120),
            PhaseFile("modules/rlm/src/reward_calculator.py", "Performance reward calculator", 80),
            PhaseFile("modules/rlm/config/rlm.yaml", "RLM default config", 40),
            PhaseFile("lib/rlm.py", "RLM facade for hook integration", 150),
        ],
        tests=PhaseTest(
            "tests/phase_18/",
            90,
            [
                "test_q_table.py",
                "test_working_memory.py",
                "test_session_manager.py",
                "test_reward_calculator.py",
                "test_rlm_facade.py",
            ],
        ),
        test_specs=[
            TestFileSpec("tests/phase_18/test_q_table.py", 15, 90),
            TestFileSpec("tests/phase_18/test_working_memory.py", 12, 90),
            TestFileSpec("tests/phase_18/test_session_manager.py", 10, 90),
            TestFileSpec("tests/phase_18/test_reward_calculator.py", 10, 90),
            TestFileSpec("tests/phase_18/test_rlm_facade.py", 10, 90),
        ],
        acceptance_criteria=[
            "Q-table persists between simulated sessions",
            "Working memory has configurable capacity",
            "Session compact/restore works with TOON format",
            "RLM facade integrates with auto_compact hook",
            "Pure Python -- no NumPy required (optional perf boost)",
        ],
        recovery_plan=(
            "If Q-table grows unbounded: implement LRU eviction with configurable max_entries"
        ),
        agent_execution_spec="general-purpose with worktree isolation",
        tools_required=["Bash", "Write", "Edit", "Agent(general-purpose)"],
    ),
    # =========================================================================
    # Phase 19: Integration + Presets + Migration
    # =========================================================================
    Phase(
        id=19,
        title="Integration + Presets + Migration",
        effort="M",
        estimated_tokens=12000,
        depends_on=[11, 12, 13, 14, 15, 16, 17, 18],
        parallel_group=None,
        description=(
            "Integration phase: wire all new components together, update presets "
            "with new modules, create migration script for v0.1.0 installs, and "
            "run full regression to ensure nothing is broken."
        ),
        objectives=[
            "Update all 5 presets with new v2 modules",
            "Add --with-rust flag to install.sh",
            "Create scripts/migrate_v01_v02.py migration tool",
            "Run ALL existing 723 tests (regression)",
            "Create integration E2E tests for new components",
        ],
        files_to_create=[
            PhaseFile("scripts/migrate_v01_v02.py", "v0.1.0 to v0.2.0 migration", 150),
        ],
        tests=PhaseTest(
            "tests/integration_v2/",
            90,
            [
                "test_e2e_circuit_breaker.py",
                "test_e2e_governance.py",
                "test_e2e_hypervisor.py",
                "test_e2e_rlm.py",
                "test_regression_723.py",
            ],
        ),
        test_specs=[
            TestFileSpec("tests/integration_v2/test_e2e_circuit_breaker.py", 10, 90),
            TestFileSpec("tests/integration_v2/test_e2e_governance.py", 10, 90),
            TestFileSpec("tests/integration_v2/test_e2e_hypervisor.py", 10, 90),
            TestFileSpec("tests/integration_v2/test_e2e_rlm.py", 10, 90),
            TestFileSpec(
                "tests/integration_v2/test_regression_723.py",
                5,
                90,
                ("regression",),
            ),
        ],
        acceptance_criteria=[
            "All presets updated with new modules",
            "install.sh supports --with-rust flag",
            "scripts/migrate_v01_v02.py works on v0.1.0 installs",
            "ALL existing 723 tests still pass",
            "New integration E2E tests pass",
        ],
        recovery_plan=(
            "If regression tests fail: git bisect to find breaking change, "
            "revert and fix in isolation"
        ),
        agent_execution_spec="general-purpose with full test suite access",
        tools_required=["Bash", "Write", "Edit", "Agent(general-purpose)"],
    ),
    # =========================================================================
    # Phase 20: Benchmarks + Self-Hosting
    # =========================================================================
    Phase(
        id=20,
        title="Benchmarks + Self-Hosting",
        effort="S",
        estimated_tokens=8000,
        depends_on=[19],
        parallel_group="finalize",
        description=(
            "Create benchmark suite for all hooks with P50/P95/P99 metrics. "
            "Self-host the framework: kazuba project uses its own hooks."
        ),
        objectives=[
            "Create benchmark suite for all hooks (P50/P95/P99)",
            "Self-host: configure .claude/hooks/ to use framework hooks",
            "Add benchmark regression check to CI",
        ],
        files_to_create=[
            PhaseFile(
                "scripts/benchmark_hooks.py", "Hook benchmark suite with percentile metrics", 200
            ),
            PhaseFile(".claude/hooks/self_host_config.py", "Self-hosting hook configuration", 50),
        ],
        tests=PhaseTest(
            "tests/phase_20/",
            90,
            ["test_benchmark_runner.py", "test_self_hosting.py"],
        ),
        test_specs=[
            TestFileSpec("tests/phase_20/test_benchmark_runner.py", 10, 90),
            TestFileSpec("tests/phase_20/test_self_hosting.py", 10, 90),
        ],
        acceptance_criteria=[
            "Benchmark suite runs all hooks with P50/P95/P99 metrics",
            "Self-hosting: kazuba project uses its own hooks",
            "CI includes benchmark regression check",
        ],
        recovery_plan="If benchmarks are flaky: increase warm-up iterations and use median",
        agent_execution_spec="general-purpose",
        tools_required=["Bash", "Write", "Edit"],
    ),
    # =========================================================================
    # Phase 21: Documentation + CI Update
    # =========================================================================
    Phase(
        id=21,
        title="Documentation + CI Update",
        effort="M",
        estimated_tokens=10000,
        depends_on=[19],
        parallel_group="finalize",
        description=(
            "Update all documentation to reflect v0.2.0 components. "
            "Add optional rust-check CI job. Validate all doc cross-references."
        ),
        objectives=[
            "Update docs/ARCHITECTURE.md with new components",
            "Update docs/HOOKS_REFERENCE.md with new hooks",
            "Update docs/MODULES_CATALOG.md with RLM, governance, hypervisor",
            "Create docs/CREATING_MODULES.md extensibility guide update",
            "Create docs/MIGRATION.md for v0.1.0 -> v0.2.0",
            "Update README.md with v0.2.0 capabilities",
            "Add optional rust-check CI job",
        ],
        files_to_create=[
            PhaseFile("docs/MIGRATION.md", "v0.1.0 to v0.2.0 migration guide", 80),
        ],
        tests=PhaseTest(
            "tests/phase_21/",
            90,
            ["test_doc_links.py", "test_doc_completeness.py"],
        ),
        test_specs=[
            TestFileSpec("tests/phase_21/test_doc_links.py", 10, 90),
            TestFileSpec("tests/phase_21/test_doc_completeness.py", 8, 90),
        ],
        acceptance_criteria=[
            "All 5 docs updated with new components",
            "README reflects v0.2.0 capabilities",
            "CI has optional rust-check job",
            "All doc cross-references valid",
        ],
        recovery_plan="If doc cross-references break: generate link index programmatically",
        agent_execution_spec="general-purpose",
        tools_required=["Write", "Edit", "Bash"],
    ),
    # =========================================================================
    # Phase 22: Release v0.2.0
    # =========================================================================
    Phase(
        id=22,
        title="Release v0.2.0",
        effort="S",
        estimated_tokens=5000,
        depends_on=[20, 21],
        parallel_group=None,
        description=(
            "Final release: tag v0.2.0, generate release notes, "
            "verify CI green on all jobs, include migration guide."
        ),
        objectives=[
            "Verify CI green on all jobs (lint, test, coverage, optional rust)",
            "Create v0.2.0 git tag",
            "Generate release notes documenting all changes from v0.1.0",
            "Include migration guide in release",
        ],
        files_to_create=[],
        tests=PhaseTest(
            "tests/phase_22/",
            90,
            ["test_release_checklist.py"],
        ),
        test_specs=[
            TestFileSpec("tests/phase_22/test_release_checklist.py", 8, 90),
        ],
        acceptance_criteria=[
            "CI green on all jobs",
            "v0.2.0 tag created",
            "Release notes document all changes from v0.1.0",
            "Migration guide included",
        ],
        recovery_plan="If CI fails on release: fix in hotfix branch, re-tag",
        agent_execution_spec="general-purpose",
        tools_required=["Bash"],
    ),
]


# =============================================================================
# Plan File Generators
# =============================================================================


def generate_frontmatter(phase: Phase) -> str:
    """Generate YAML frontmatter for a phase file."""
    cross_refs: list[str] = []
    for dep_id in phase.depends_on:
        dep_phase = next(p for p in PHASES if p.id == dep_id)
        slug = _slug(dep_phase.title)
        file_idx = dep_phase.id - 11 + 1
        cross_refs.append(
            f'  - {{file: "{file_idx:02d}-phase-{slug}.md", relation: "depends_on"}}'
        )

    for p in PHASES:
        if phase.id in p.depends_on:
            slug = _slug(p.title)
            file_idx = p.id - 11 + 1
            cross_refs.append(
                f'  - {{file: "{file_idx:02d}-phase-{slug}.md", relation: "blocks"}}'
            )

    refs_str = "\n".join(cross_refs) if cross_refs else "  []"

    lines: list[str] = [
        "---",
        "plan: claude-code-kazuba-v2",
        'version: "3.0"',
        f"phase: {phase.id}",
        f'title: "{phase.title}"',
        f'effort: "{phase.effort}"',
        f"estimated_tokens: {phase.estimated_tokens}",
        f"depends_on: {json.dumps(phase.depends_on)}",
        f"parallel_group: {json.dumps(phase.parallel_group)}",
        f'context_budget: "{phase.context_budget}"',
        f'validation_script: "validation/validate_phase_{phase.id}.py"',
        f'checkpoint: "checkpoints/phase_{phase.id}.toon"',
        f"recovery_plan: {json.dumps(phase.recovery_plan)}",
        f"agent_execution_spec: {json.dumps(phase.agent_execution_spec)}",
        'status: "pending"',
        "cross_refs:",
        refs_str,
        "---",
        "",
    ]
    return "\n".join(lines)


def generate_phase_content(phase: Phase) -> str:
    """Generate the full markdown content for a phase file."""
    sections: list[str] = [generate_frontmatter(phase)]

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

    # Objectives
    sections.append("\n## Objectives\n")
    for obj in phase.objectives:
        sections.append(f"- [ ] {obj}")
    sections.append("")

    # Files to Create
    if phase.files_to_create:
        sections.append("\n## Files to Create\n")
        sections.append("| Path | Description | Min Lines |")
        sections.append("|------|-------------|-----------|")
        for f in phase.files_to_create:
            sections.append(f"| `{f.path}` | {f.description} | {f.min_lines} |")
        sections.append("")

    # Source Files (Extraction Map) — AMPLIFIED
    if phase.source_files:
        sections.append("\n## Source Files (Extraction Map)\n")
        sections.append("| Source Path | Target | Type | LOC | Key Classes |")
        sections.append("|-------------|--------|------|-----|-------------|")
        for sf in phase.source_files:
            classes = ", ".join(sf.key_classes) if sf.key_classes else "-"
            sections.append(
                f"| `{sf.path}` | `{sf.target}` | {sf.extraction_type} | {sf.loc} | {classes} |"
            )
        sections.append("")

        # Detailed adaptation notes
        has_notes = any(sf.adaptation_notes for sf in phase.source_files)
        if has_notes:
            sections.append("### Adaptation Notes\n")
            for sf in phase.source_files:
                if sf.adaptation_notes:
                    sections.append(f"- **`{sf.target}`**: {sf.adaptation_notes}")
            sections.append("")

        # External dependencies from source files
        all_ext_deps: list[str] = []
        for sf in phase.source_files:
            all_ext_deps.extend(sf.external_deps)
        if all_ext_deps:
            unique_deps = sorted(set(all_ext_deps))
            sections.append("### External Dependencies from Sources\n")
            for dep in unique_deps:
                sections.append(f"- `{dep}`")
            sections.append("")

    # Pydantic Models — NEW
    if phase.pydantic_models:
        sections.append("\n## Pydantic Models\n")
        for model in phase.pydantic_models:
            frozen_str = "frozen=True" if model.frozen else "frozen=False"
            sections.append(f"### `{model.name}` ({frozen_str})\n")
            if model.description:
                sections.append(f"{model.description}\n")
            sections.append(f"- **Module**: `{model.module}`")
            if model.fields:
                sections.append("- **Fields**:")
                for fname, ftype, fdefault in model.fields:
                    sections.append(f"  - `{fname}: {ftype} = {fdefault}`")
            sections.append("")

    # Hook Specifications — NEW
    if phase.hook_specs:
        sections.append("\n## Hook Specifications\n")
        sections.append("| Hook | Event | Module | Exit Codes | P99 Target |")
        sections.append("|------|-------|--------|------------|------------|")
        for hs in phase.hook_specs:
            codes = ", ".join(str(c) for c in hs.exit_codes)
            sections.append(
                f"| `{hs.name}` | {hs.event} | {hs.module} | {codes} | {hs.latency_target_ms}ms |"
            )
        sections.append("")

        # Hook details
        for hs in phase.hook_specs:
            if hs.description or hs.integration_points:
                sections.append(f"### `{hs.name}`\n")
                if hs.description:
                    sections.append(f"{hs.description}\n")
                if hs.integration_points:
                    sections.append("**Integration points**:")
                    for ip in hs.integration_points:
                        sections.append(f"- `{ip}`")
                    sections.append("")

    # Test Specifications — NEW
    if phase.test_specs:
        sections.append("\n## Test Specifications\n")
        sections.append("| Test File | Min Tests | Coverage | Categories |")
        sections.append("|-----------|-----------|----------|------------|")
        for ts in phase.test_specs:
            cats = ", ".join(ts.test_categories)
            sections.append(f"| `{ts.path}` | {ts.min_tests} | {ts.coverage_target}% | {cats} |")
        sections.append("")

    # TDD spec
    if phase.tdd_spec:
        sections.append(f"\n{phase.tdd_spec}")

    # Implementation notes
    if phase.implementation_notes:
        sections.append(f"\n{phase.implementation_notes}")

    # Testing (legacy format for compatibility)
    if phase.tests:
        sections.append("\n## Testing\n")
        sections.append(f"- **Test directory**: `{phase.tests.test_dir}`")
        sections.append(f"- **Min coverage per file**: {phase.tests.min_coverage}%")
        sections.append("- **Test files**:")
        for tf in phase.tests.test_files:
            sections.append(f"  - `{tf}`")
        sections.append("")

    # Acceptance Criteria
    sections.append("\n## Acceptance Criteria\n")
    for ac in phase.acceptance_criteria:
        sections.append(f"- [ ] {ac}")
    sections.append("")

    # Tools Required
    if phase.tools_required:
        sections.append("\n## Tools Required\n")
        sections.append(f"- {', '.join(phase.tools_required)}")
        if phase.mcp_servers:
            sections.append(f"- MCP: {', '.join(phase.mcp_servers)}")
        if phase.plugins:
            sections.append(f"- Plugins: {', '.join(phase.plugins)}")
        sections.append("")

    # Risks
    if phase.risks:
        sections.append("\n## Risks\n")
        for r in phase.risks:
            sections.append(f"- {r}")
        sections.append("")

    # Recovery Plan — NEW
    if phase.recovery_plan:
        sections.append("\n## Recovery Plan\n")
        sections.append(f"{phase.recovery_plan}\n")

    # Agent Execution — NEW
    if phase.agent_execution_spec:
        sections.append("\n## Agent Execution\n")
        sections.append(f"**Spec**: {phase.agent_execution_spec}\n")

    # Checkpoint
    sections.append("\n## Checkpoint\n")
    sections.append("After completing this phase, run:")
    sections.append("```bash")
    sections.append(f"python plans/v2/validation/validate_phase_{phase.id}.py")
    sections.append("```")
    sections.append(f"Checkpoint saved to: `checkpoints/phase_{phase.id}.toon`\n")

    return "\n".join(sections)


def generate_index() -> str:
    """Generate the master index file with DAG visualization."""
    total_tokens = sum(p.estimated_tokens for p in PHASES)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        textwrap.dedent(f"""\
        ---
        plan: claude-code-kazuba-v2
        version: "3.0"
        type: index
        total_phases: {len(PHASES)}
        total_estimated_tokens: {total_tokens}
        generated: "{now}"
        ---

        # Claude Code Kazuba v0.2.0 — Source Integration Master Index

        ## Overview

        Pln2 v2: Source integration plan for claude-code-kazuba v0.2.0.
        Phases 11-22 build on the v0.1.0 foundation (phases 0-10).
        Amplified in 9 dimensions: source extraction, Pydantic models, hook specs,
        test specs, recovery plans, agent execution specs, and more.

        ## Dependency Graph (DAG)

        ```
        Phase 11 (Shared Infrastructure) [FOUNDATION]
            |-- Phase 12 (Rust Acceleration)  --+-- PARALLEL (infra)
            |-- Phase 13 (Core Governance)    --+
            |       |
            |       +-- Phase 14 (Agent Triggers) -- PARALLEL (triggers)
            |               |
            |               +-- Phase 15 (Hypervisor) [SEQUENTIAL]
            |                       |
            |                       +-- Phase 18 (RLM Learning) [SEQUENTIAL]
            |
            |-- Phase 16 (Hooks Batch 1)      --+-- PARALLEL (hooks)
            |       |                           |
            +-------+-- Phase 17 (Hooks Batch 2) --+
            |
            +-- Phase 12, 13, 14, 15, 16, 17, 18 --> Phase 19 (Integration)
                                                          |
                                                  +-------+-------+
                                                  |               |
                                          Phase 20 (Bench)  Phase 21 (Docs)
                                                  |               |
                                                  +-------+-------+
                                                          |
                                                  Phase 22 (Release v0.2.0)
        ```

        **Critical Path**: 11 -> 14 -> 15 -> 18 -> 19 -> 22 (6 sequential phases)
        **With parallelism**: ~7 context windows instead of 12

        ## Phase Summary

        | # | Title | Effort | Tokens | Group | Deps | Status |
        |---|-------|--------|--------|-------|------|--------|
        """)
    ]

    for phase in PHASES:
        group = phase.parallel_group or "sequential"
        slug = _slug(phase.title)
        file_idx = phase.id - 11 + 1
        deps_str = ", ".join(str(d) for d in phase.depends_on) or "-"
        lines.append(
            f"| {phase.id} | [{phase.title}]"
            f"({file_idx:02d}-phase-{slug}.md) "
            f"| {phase.effort} | ~{phase.estimated_tokens:,} "
            f"| {group} | {deps_str} | pending |"
        )

    lines.append("")

    # Source extraction summary
    total_source_loc = sum(sf.loc for p in PHASES for sf in p.source_files)
    total_source_files = sum(len(p.source_files) for p in PHASES)
    total_pydantic = sum(len(p.pydantic_models) for p in PHASES)
    total_hooks = sum(len(p.hook_specs) for p in PHASES)
    total_test_specs = sum(len(p.test_specs) for p in PHASES)

    lines.append("\n## Amplification Metrics\n")
    lines.append(f"- **Total source files to extract**: {total_source_files}")
    lines.append(f"- **Total source LOC**: ~{total_source_loc:,}")
    lines.append(f"- **Pydantic models to create**: {total_pydantic}")
    lines.append(f"- **Hook specs defined**: {total_hooks}")
    lines.append(f"- **Test file specs**: {total_test_specs}")
    lines.append(f"- **Total estimated tokens**: ~{total_tokens:,}")
    lines.append("")

    # Execution strategy
    lines.append("\n## Execution Strategy\n")
    lines.append("### Sequential Phases (must be in order)")
    lines.append("- Phase 11 (foundation, no deps)")
    lines.append("- Phase 14 -> Phase 15 -> Phase 18 (triggers -> hypervisor -> RLM)")
    lines.append("- Phase 19 (integration hub, waits for all)")
    lines.append("- Phase 22 (release, waits for 20+21)")
    lines.append("")
    lines.append("### Parallel Groups")
    lines.append("- **infra** (after Phase 11): Phases 12, 13 (Rust + Governance)")
    lines.append("- **triggers** (after Phases 11, 13): Phase 14")
    lines.append("- **hooks** (after Phase 11): Phases 16, 17 (Advanced hooks batches)")
    lines.append("- **finalize** (after Phase 19): Phases 20, 21 (Bench + Docs)")
    lines.append("")

    lines.append("### Swarm Configuration\n")
    lines.append("```yaml")
    lines.append("team: claude-code-kazuba-v2-build")
    lines.append("parallel_groups:")
    lines.append("  infra:")
    lines.append("    phases: [12, 13]")
    lines.append("    agents: 2")
    lines.append("    isolation: worktree")
    lines.append("    merge_strategy: git merge --no-ff")
    lines.append("  hooks:")
    lines.append("    phases: [16, 17]")
    lines.append("    agents: 2")
    lines.append("    isolation: worktree")
    lines.append("    merge_strategy: git merge --no-ff")
    lines.append("  finalize:")
    lines.append("    phases: [20, 21]")
    lines.append("    agents: 2")
    lines.append("    isolation: worktree")
    lines.append("    merge_strategy: git merge --no-ff")
    lines.append("```")
    lines.append("")

    lines.append("## Validation\n")
    lines.append("Each phase has a validation script in `validation/validate_phase_NN.py`.")
    lines.append("Run all validations: `python plans/v2/validation/validate_all.py`")
    lines.append("")
    lines.append("## Checkpoints\n")
    lines.append("Checkpoints saved in `.toon` format (msgpack) at `checkpoints/phase_NN.toon`.")
    lines.append("Recovery: load last .toon checkpoint to resume from any phase.\n")

    return "\n".join(lines)


def generate_validation_script(phase: Phase) -> str:
    """Generate validation script for a phase.

    Builds the script as a list of lines to avoid textwrap.dedent issues
    with embedded multi-line interpolations.
    """
    lines: list[str] = []
    _a = lines.append  # shorthand

    expected_files_str = ",\n    ".join(f'"{f.path}"' for f in phase.files_to_create)
    min_lines_map = ", ".join(f'"{f.path}": {f.min_lines}' for f in phase.files_to_create)

    test_dir = phase.tests.test_dir if phase.tests else f"tests/phase_{phase.id}/"
    min_cov = phase.tests.min_coverage if phase.tests else 90

    # --- Header ---
    _a("#!/usr/bin/env python3")
    _a('"""')
    _a(f"Validation Script — Phase {phase.id}: {phase.title}")
    _a("")
    _a("Verifies all deliverables, runs tests, checks coverage, lint, typecheck,")
    _a("regression, and saves checkpoint.")
    _a("Exit 0 = PASS, Exit 1 = FAIL")
    _a('"""')
    _a("from __future__ import annotations")
    _a("")
    _a("import json")
    _a("import subprocess")
    _a("import sys")
    _a("import time")
    _a("from pathlib import Path")
    _a("")
    _a("try:")
    _a("    import msgpack")
    _a("except ImportError:")
    _a("    msgpack = None  # type: ignore[assignment]")
    _a("")
    _a(f"PHASE_ID = {phase.id}")
    _a(f'PHASE_TITLE = "{phase.title}"')
    _a("BASE_DIR = Path(__file__).resolve().parent.parent.parent")
    _a('CHECKPOINT_DIR = BASE_DIR / "checkpoints"')
    _a("CHECKPOINT_DIR.mkdir(exist_ok=True)")
    _a("")
    _a("EXPECTED_FILES = [")
    _a(f"    {expected_files_str}")
    _a("]")
    _a(f"MIN_LINES = {{{min_lines_map}}}")
    _a(f'TEST_DIR = "{test_dir}"')
    _a(f"MIN_COVERAGE = {min_cov}")
    _a("")
    _a("")

    # --- check_files_exist ---
    _a("def check_files_exist() -> list[str]:")
    _a('    """Verify all expected files exist and meet minimum line counts."""')
    _a("    errors: list[str] = []")
    _a("    for fpath in EXPECTED_FILES:")
    _a("        full = BASE_DIR / fpath")
    _a("        if not full.exists():")
    _a('            errors.append(f"MISSING: {fpath}")')
    _a("            continue")
    _a("        lines = len(full.read_text().splitlines())")
    _a("        min_l = MIN_LINES.get(fpath, 1)")
    _a("        if lines < min_l:")
    _a('            errors.append(f"TOO_SHORT: {fpath} ({lines} < {min_l} lines)")')
    _a("    return errors")
    _a("")
    _a("")

    # --- run_tests ---
    _a("def run_tests() -> dict:")
    _a('    """Run pytest with coverage for this phase."""')
    _a("    test_path = BASE_DIR / TEST_DIR")
    _a("    if not test_path.exists():")
    _a('        return {"status": "SKIP", "reason": f"Test dir {TEST_DIR} not found"}')
    _a("")
    _a("    result = subprocess.run(")
    _a("        [")
    _a('            sys.executable, "-m", "pytest", str(test_path),')
    _a('            "--tb=short", "-q",')
    _a("            f\"--cov={BASE_DIR / 'lib'}\",")
    _a('            "--cov-report=json:coverage.json",')
    _a('            f"--cov-fail-under={MIN_COVERAGE}",')
    _a("        ],")
    _a("        capture_output=True, text=True, cwd=str(BASE_DIR),")
    _a("    )")
    _a("")
    _a("    cov_data = {}")
    _a('    cov_file = BASE_DIR / "coverage.json"')
    _a("    if cov_file.exists():")
    _a("        cov_data = json.loads(cov_file.read_text())")
    _a("        cov_file.unlink()")
    _a("")
    _a("    return {")
    _a('        "status": "PASS" if result.returncode == 0 else "FAIL",')
    _a('        "returncode": result.returncode,')
    _a('        "stdout": result.stdout[-500:] if result.stdout else "",')
    _a('        "stderr": result.stderr[-500:] if result.stderr else "",')
    _a('        "coverage": cov_data.get("totals", {}).get("percent_covered", 0),')
    _a("    }")
    _a("")
    _a("")

    # --- run_lint ---
    _a("def run_lint() -> dict:")
    _a('    """Run ruff check on lib/ directory."""')
    _a("    result = subprocess.run(")
    _a('        [sys.executable, "-m", "ruff", "check", str(BASE_DIR / "lib"), "--quiet"],')
    _a("        capture_output=True, text=True, cwd=str(BASE_DIR),")
    _a("    )")
    _a("    return {")
    _a('        "status": "PASS" if result.returncode == 0 else "FAIL",')
    _a('        "errors": result.stdout.strip() if result.stdout else "",')
    _a("    }")
    _a("")
    _a("")

    # --- run_typecheck ---
    _a("def run_typecheck() -> dict:")
    _a('    """Run pyright on lib/ directory."""')
    _a("    result = subprocess.run(")
    _a('        [sys.executable, "-m", "pyright", str(BASE_DIR / "lib"), "--outputjson"],')
    _a("        capture_output=True, text=True, cwd=str(BASE_DIR),")
    _a("    )")
    _a("    return {")
    _a('        "status": "PASS" if result.returncode == 0 else "FAIL",')
    _a('        "output": result.stdout[-300:] if result.stdout else "",')
    _a("    }")
    _a("")
    _a("")

    # --- run_regression ---
    _a("def run_regression() -> dict:")
    _a('    """Run existing test suite to check for regressions."""')
    _a('    existing_tests = BASE_DIR / "tests"')
    _a("    if not existing_tests.exists():")
    _a('        return {"status": "SKIP", "reason": "No existing tests dir"}')
    _a("")
    _a("    result = subprocess.run(")
    _a("        [")
    _a('            sys.executable, "-m", "pytest", str(existing_tests),')
    _a('            "--tb=short", "-q", "--ignore=tests/phase_11",')
    _a('            "--ignore=tests/phase_12", "--ignore=tests/phase_13",')
    _a('            "--ignore=tests/phase_14", "--ignore=tests/phase_15",')
    _a('            "--ignore=tests/phase_16", "--ignore=tests/phase_17",')
    _a('            "--ignore=tests/phase_18", "--ignore=tests/phase_19",')
    _a('            "--ignore=tests/phase_20", "--ignore=tests/phase_21",')
    _a('            "--ignore=tests/phase_22", "--ignore=tests/integration_v2",')
    _a("        ],")
    _a("        capture_output=True, text=True, cwd=str(BASE_DIR),")
    _a("    )")
    _a("    return {")
    _a('        "status": "PASS" if result.returncode == 0 else "FAIL",')
    _a('        "returncode": result.returncode,')
    _a('        "stdout": result.stdout[-500:] if result.stdout else "",')
    _a("    }")
    _a("")
    _a("")

    # --- check_test_specs (conditional) ---
    if phase.test_specs:
        _a("TEST_SPECS = [")
        for ts in phase.test_specs:
            _a(f'    ("{ts.path}", {ts.min_tests}, {ts.coverage_target}),')
        _a("]")
        _a("")
        _a("")
        _a("def check_test_specs() -> list[str]:")
        _a('    """Verify test files meet minimum test count."""')
        _a("    errors: list[str] = []")
        _a("    for tpath, min_tests, _cov_target in TEST_SPECS:")
        _a("        full = BASE_DIR / tpath")
        _a("        if not full.exists():")
        _a('            errors.append(f"MISSING_TEST: {tpath}")')
        _a("            continue")
        _a("        content = full.read_text()")
        _a('        test_count = content.count("def test_")')
        _a("        if test_count < min_tests:")
        _a("            errors.append(")
        _a('                f"TOO_FEW_TESTS: {tpath} ({test_count} < {min_tests})"')
        _a("            )")
        _a("    return errors")
        _a("")
        _a("")

    # --- save_checkpoint ---
    _a("def save_checkpoint(results: dict) -> Path:")
    _a('    """Save checkpoint in .toon format (msgpack)."""')
    _a("    checkpoint = {")
    _a('        "phase_id": PHASE_ID,')
    _a('        "phase_title": PHASE_TITLE,')
    _a('        "timestamp": time.time(),')
    _a('        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),')
    _a('        "results": results,')
    _a('        "version": "3.0",')
    _a("    }")
    _a("")
    _a('    path = CHECKPOINT_DIR / f"phase_{PHASE_ID}.toon"')
    _a("    if msgpack is not None:")
    _a("        path.write_bytes(msgpack.packb(checkpoint, use_bin_type=True))")
    _a("    else:")
    _a("        # Fallback: JSON with .toon extension")
    _a("        path.write_text(json.dumps(checkpoint, indent=2, default=str))")
    _a("")
    _a("    return path")
    _a("")
    _a("")

    # --- main ---
    _a("def main() -> int:")
    _a('    print(f"\\n{"=" * 60}")')
    _a('    print(f"  Phase {PHASE_ID} Validation: {PHASE_TITLE}")')
    _a('    print(f"{"=" * 60}\\n")')
    _a("")
    _a('    results: dict = {"phase": PHASE_ID, "checks": {}}')
    _a("    all_pass = True")
    _a("")
    _a("    # Check 1: Files exist")
    _a("    file_errors = check_files_exist()")
    _a('    results["checks"]["files"] = {')
    _a('        "status": "PASS" if not file_errors else "FAIL",')
    _a('        "total": len(EXPECTED_FILES),')
    _a('        "missing": len(file_errors),')
    _a('        "errors": file_errors,')
    _a("    }")
    _a("    if file_errors:")
    _a("        all_pass = False")
    _a("        for e in file_errors:")
    _a('            print(f"  [FAIL] {e}")')
    _a("    else:")
    _a('        print(f"  [PASS] All {len(EXPECTED_FILES)} files present")')
    _a("")
    _a("    # Check 2: Tests")
    _a("    test_results = run_tests()")
    _a('    results["checks"]["tests"] = test_results')
    _a('    if test_results["status"] == "FAIL":')
    _a("        all_pass = False")
    _a(
        "        print(f\"  [FAIL] Tests failed (coverage: {test_results.get('coverage', 'N/A')}%)\")"
    )
    _a('    elif test_results["status"] == "SKIP":')
    _a("        print(f\"  [SKIP] {test_results['reason']}\")")
    _a("    else:")
    _a(
        "        print(f\"  [PASS] Tests passed (coverage: {test_results.get('coverage', 'N/A')}%)\")"
    )
    _a("")
    _a("    # Check 3: Lint")
    _a("    lint_results = run_lint()")
    _a('    results["checks"]["lint"] = lint_results')
    _a('    if lint_results["status"] == "FAIL":')
    _a("        all_pass = False")
    _a('        print("  [FAIL] Lint errors found")')
    _a("    else:")
    _a('        print("  [PASS] Lint clean")')
    _a("")
    _a("    # Check 4: Type check")
    _a("    type_results = run_typecheck()")
    _a('    results["checks"]["typecheck"] = type_results')
    _a('    if type_results["status"] == "FAIL":')
    _a('        print("  [WARN] Type check issues (non-blocking)")')
    _a("    else:")
    _a('        print("  [PASS] Type check clean")')
    _a("")

    # Check 5: Test specs (conditional)
    if phase.test_specs:
        _a("    # Check 5: Test specifications")
        _a("    ts_errors = check_test_specs()")
        _a('    results["checks"]["test_specs"] = {')
        _a('        "status": "PASS" if not ts_errors else "FAIL",')
        _a('        "errors": ts_errors,')
        _a("    }")
        _a("    if ts_errors:")
        _a("        all_pass = False")
        _a("        for e in ts_errors:")
        _a('            print(f"  [FAIL] {e}")')
        _a("    else:")
        _a('        print("  [PASS] All test specs met")')
        _a("")

    # Check 6: Regression
    _a("    # Check 6: Regression (existing tests)")
    _a("    reg_results = run_regression()")
    _a('    results["checks"]["regression"] = reg_results')
    _a('    if reg_results["status"] == "FAIL":')
    _a("        all_pass = False")
    _a('        print("  [FAIL] Regression: existing tests broken")')
    _a('    elif reg_results["status"] == "SKIP":')
    _a("        print(f\"  [SKIP] {reg_results['reason']}\")")
    _a("    else:")
    _a('        print("  [PASS] Regression: existing tests still green")')
    _a("")

    # Save checkpoint and return
    _a("    # Save checkpoint")
    _a('    results["overall"] = "PASS" if all_pass else "FAIL"')
    _a("    cp_path = save_checkpoint(results)")
    _a('    print(f"\\n  Checkpoint: {cp_path}")')
    _a("")
    _a("    print(f\"\\n  Overall: {results['overall']}\")")
    _a('    print(f"{"=" * 60}\\n")')
    _a("")
    _a("    return 0 if all_pass else 1")
    _a("")
    _a("")
    _a('if __name__ == "__main__":')
    _a("    sys.exit(main())")
    _a("")

    return "\n".join(lines)


def generate_validate_all() -> str:
    """Generate the validate_all.py runner for phases 11-22."""
    phase_ids = [p.id for p in PHASES]
    return textwrap.dedent(f'''\
        #!/usr/bin/env python3
        """Run all v2 phase validation scripts sequentially (phases 11-22)."""
        from __future__ import annotations

        import importlib.util
        import sys
        from pathlib import Path

        PHASE_IDS = {phase_ids}


        def main() -> int:
            validation_dir = Path(__file__).parent
            failed: list[int] = []

            for phase_id in PHASE_IDS:
                script = validation_dir / f"validate_phase_{{phase_id}}.py"
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
            print(f"  ALL V2 PHASES PASSED (11-22)")
            print(f"{"=" * 60}")
            return 0


        if __name__ == "__main__":
            sys.exit(main())
    ''')


def generate_amplification_report() -> str:
    """Generate amplification-report.md comparing Pln1 vs Pln2 across 9 dimensions."""
    total_source_files = sum(len(p.source_files) for p in PHASES)
    total_source_loc = sum(sf.loc for p in PHASES for sf in p.source_files)
    total_pydantic = sum(len(p.pydantic_models) for p in PHASES)
    total_hooks = sum(len(p.hook_specs) for p in PHASES)
    total_test_specs = sum(len(p.test_specs) for p in PHASES)
    total_files = sum(len(p.files_to_create) for p in PHASES)
    total_tokens = sum(p.estimated_tokens for p in PHASES)
    total_acceptance = sum(len(p.acceptance_criteria) for p in PHASES)

    direct_count = sum(
        1 for p in PHASES for sf in p.source_files if sf.extraction_type == "DIRECT_COPY"
    )
    adapt_count = sum(
        1 for p in PHASES for sf in p.source_files if sf.extraction_type == "ADAPT_IMPORTS"
    )
    reimplement_count = sum(
        1 for p in PHASES for sf in p.source_files if sf.extraction_type == "REIMPLEMENT"
    )

    phases_with_recovery = sum(1 for p in PHASES if p.recovery_plan)
    phases_with_agent_spec = sum(1 for p in PHASES if p.agent_execution_spec)

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    return textwrap.dedent(f"""\
        ---
        plan: claude-code-kazuba-v2
        type: amplification-report
        generated: "{now}"
        ---

        # Amplification Report: Pln1 vs Pln2

        ## Overview

        Pln2 = (Pln1)^2 -- amplified across 9 dimensions to integrate source
        components from 3 projects (analise, kazuba-cargo, inter-agent-relay)
        into the claude-code-kazuba framework.

        ## Dimension Comparison

        | Dimension | Pln1 (v0.1.0) | Pln2 (v0.2.0) | Amplification |
        |-----------|---------------|---------------|---------------|
        | Phases | 11 (0-10) | 12 (11-22) | 1.1x |
        | Source files mapped | 0 (string refs) | {total_source_files} (structured) | {total_source_files}x |
        | Source LOC tracked | ~0 | ~{total_source_loc:,} | -- |
        | Pydantic models defined | 0 | {total_pydantic} | {total_pydantic}x |
        | Hook specs with SLA | 0 | {total_hooks} | {total_hooks}x |
        | Test file specs | 0 | {total_test_specs} | {total_test_specs}x |
        | Recovery plans | 0 | {phases_with_recovery} | {phases_with_recovery}x |
        | Agent execution specs | 0 | {phases_with_agent_spec} | {phases_with_agent_spec}x |
        | Files to create | ~85 | {total_files} | -- |

        ## Source Extraction Analysis

        | Extraction Type | Count | Description |
        |----------------|-------|-------------|
        | DIRECT_COPY | {direct_count} | Copy as-is, minimal changes |
        | ADAPT_IMPORTS | {adapt_count} | Refactor imports, remove domain-specific code |
        | REIMPLEMENT | {reimplement_count} | Rewrite from scratch using reference |
        | **Total** | **{total_source_files}** | |

        ### Source Projects

        | Project | Files | LOC | Primary Extractions |
        |---------|-------|-----|---------------------|
        | analise | ~10 | ~1,500 | Hooks (lifecycle, governance, validation) |
        | kazuba-cargo | ~8 | ~8,500 | Rust crate, hypervisor, RLM, triggers |
        | (new) | ~4 | ~620 | Event bus, governance, rust bridge |

        ## Estimated Effort

        | Metric | Value |
        |--------|-------|
        | Total estimated tokens | ~{total_tokens:,} |
        | Total files to create | {total_files} |
        | Total acceptance criteria | {total_acceptance} |
        | Total test specs | {total_test_specs} |
        | Critical path length | 6 phases |
        | Parallelizable groups | 4 (infra, triggers, hooks, finalize) |
        | Estimated context windows | ~7 (with parallelism) |

        ## Risk Assessment

        | Risk | Probability | Impact | Mitigation |
        |------|-------------|--------|------------|
        | Rust toolchain unavailable | Medium | Low | Python fallback always works |
        | Threading issues in CB | Low | Medium | Simplify to asyncio.Lock |
        | Regression in 723 tests | Low | High | Run regression after each phase |
        | Q-table unbounded growth | Medium | Medium | LRU eviction with max_entries |
        | Doc cross-ref breakage | Low | Low | Generate link index programmatically |

        ## Key Differences from Pln1

        1. **Structured source files**: Each source has `SourceFile` with path, target,
           extraction type, LOC, key classes, and adaptation notes
        2. **Pydantic model specs**: Models defined upfront with fields, types, and defaults
        3. **Hook specs with SLA**: Each hook has event, exit codes, and P99 latency target
        4. **Test specs per file**: Minimum test count and coverage target per test file
        5. **Recovery plans**: Every phase has a fallback strategy
        6. **Agent execution specs**: Which agent type to use for each phase
        7. **Validation scripts**: Include regression check and test spec verification
        8. **Extraction types**: DIRECT_COPY, ADAPT_IMPORTS, REIMPLEMENT classification
        9. **Parallel groups**: 4 groups (infra, triggers, hooks, finalize) for efficiency
    """)


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
    """Generate all v2 plan files and optionally validate them."""
    parser = argparse.ArgumentParser(description="Generate Pln2 v2 plan files (phases 11-22)")
    parser.add_argument(
        "--output-dir",
        default="plans/v2",
        help="Output directory for plan files (default: plans/v2)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate generated files after creation",
    )
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
        file_idx = phase.id - 11 + 1
        fname = f"{file_idx:02d}-phase-{slug}.md"
        fpath = output / fname
        fpath.write_text(generate_phase_content(phase))
        generated.append(str(fpath.relative_to(base)))
        print(f"  [GEN] {fpath.relative_to(base)}")

    # Generate amplification report
    report_path = output / "amplification-report.md"
    report_path.write_text(generate_amplification_report())
    generated.append(str(report_path.relative_to(base)))
    print(f"  [GEN] {report_path.relative_to(base)}")

    # Generate validation scripts
    for phase in PHASES:
        vpath = validation / f"validate_phase_{phase.id}.py"
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
