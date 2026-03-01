"""Tests for modules/config-hypervisor/src/hypervisor_v2.py — Phase 15."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Load hypervisor_v2 from hyphenated directory using importlib
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_HV2_PATH = _PROJECT_ROOT / "claude_code_kazuba/data/modules" / "config-hypervisor" / "src" / "hypervisor_v2.py"
_spec = importlib.util.spec_from_file_location("hypervisor_v2", _HV2_PATH)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules.setdefault("hypervisor_v2", _mod)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

AgentDelegationEngine = _mod.AgentDelegationEngine
BaseEventMesh = _mod.BaseEventMesh
EventMesh = _mod.EventMesh
GPUSkillRouter = _mod.GPUSkillRouter
HookType = _mod.HookType
HypervisorPlugin = _mod.HypervisorPlugin
HypervisorState = _mod.HypervisorState
InMemoryMemoryManager = _mod.InMemoryMemoryManager
SimpleDelegationEngine = _mod.SimpleDelegationEngine
SimpleSkillRouter = _mod.SimpleSkillRouter
UnifiedMemoryManager = _mod.UnifiedMemoryManager


# ---------------------------------------------------------------------------
# HypervisorState
# ---------------------------------------------------------------------------


def test_hypervisor_state_creation():
    """HypervisorState must be constructable with defaults."""
    state = HypervisorState()
    assert state.phase_id == 0
    assert state.active_workers == 0
    assert state.memory_mb == 0.0


def test_hypervisor_state_custom():
    """HypervisorState must accept custom values."""
    state = HypervisorState(phase_id=5, mode="parallel", active_workers=4, memory_mb=256.0)
    assert state.phase_id == 5
    assert state.mode == "parallel"
    assert state.active_workers == 4
    assert state.memory_mb == 256.0


def test_hypervisor_state_frozen():
    """HypervisorState must be immutable (frozen=True)."""
    state = HypervisorState(phase_id=1)
    with pytest.raises((TypeError, AttributeError, Exception)):
        state.phase_id = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# HookType enum
# ---------------------------------------------------------------------------


def test_hook_type_enum_values():
    """HookType must have all four required values."""
    assert HookType.PRE_PHASE.value == "pre_phase"
    assert HookType.POST_PHASE.value == "post_phase"
    assert HookType.ON_FAILURE.value == "on_failure"
    assert HookType.ON_SUCCESS.value == "on_success"


# ---------------------------------------------------------------------------
# EventMesh ABC
# ---------------------------------------------------------------------------


def test_event_mesh_abc():
    """EventMesh must be abstract and not directly instantiatable."""
    with pytest.raises(TypeError):
        EventMesh()  # type: ignore[abstract]


def test_concrete_event_mesh_implementation():
    """BaseEventMesh must implement the full EventMesh interface."""
    mesh = BaseEventMesh()
    mesh.subscribe("topic-a")
    mesh.publish("event-1")
    mesh.publish("event-2")
    mesh.unsubscribe("topic-a")

    assert "event-1" in mesh.events
    assert "event-2" in mesh.events
    assert "topic-a" not in mesh.subscriptions


# ---------------------------------------------------------------------------
# GPUSkillRouter ABC
# ---------------------------------------------------------------------------


def test_gpu_skill_router_abc():
    """GPUSkillRouter must be abstract and not directly instantiatable."""
    with pytest.raises(TypeError):
        GPUSkillRouter()  # type: ignore[abstract]


def test_concrete_skill_router():
    """SimpleSkillRouter must route tasks to registered skills."""
    router = SimpleSkillRouter(default_skill="general")
    router.register("python", "python-skill")
    router.register("rust", "rust-skill")

    assert router.route("write a python script") == "python-skill"
    assert router.route("implement rust binary") == "rust-skill"
    assert router.route("unknown task") == "general"


# ---------------------------------------------------------------------------
# UnifiedMemoryManager ABC
# ---------------------------------------------------------------------------


def test_unified_memory_manager_abc():
    """UnifiedMemoryManager must be abstract and not directly instantiatable."""
    with pytest.raises(TypeError):
        UnifiedMemoryManager()  # type: ignore[abstract]


def test_in_memory_manager_allocate_and_free():
    """InMemoryMemoryManager must track allocations and frees correctly."""
    mgr = InMemoryMemoryManager()
    assert mgr.used_mb() == 0.0

    mgr.allocate(128.0)
    assert mgr.used_mb() == 128.0

    mgr.free(64.0)
    assert mgr.used_mb() == 64.0

    # Floor at 0 — never negative
    mgr.free(200.0)
    assert mgr.used_mb() == 0.0


# ---------------------------------------------------------------------------
# AgentDelegationEngine ABC
# ---------------------------------------------------------------------------


def test_agent_delegation_engine_abc():
    """AgentDelegationEngine must be abstract and not directly instantiatable."""
    with pytest.raises(TypeError):
        AgentDelegationEngine()  # type: ignore[abstract]


def test_concrete_delegation_engine():
    """SimpleDelegationEngine must return unique task IDs."""
    engine = SimpleDelegationEngine()
    id1 = engine.delegate("write tests", "test-agent")
    id2 = engine.delegate("write docs", "docs-agent")

    assert "test-agent" in id1
    assert "docs-agent" in id2
    assert id1 != id2


# ---------------------------------------------------------------------------
# HypervisorPlugin ABC
# ---------------------------------------------------------------------------


def test_hypervisor_plugin_abc():
    """HypervisorPlugin must be abstract and not directly instantiatable."""
    with pytest.raises(TypeError):
        HypervisorPlugin()  # type: ignore[abstract]


def test_concrete_plugin_implementation():
    """A concrete HypervisorPlugin must be callable via on_hook."""

    class _RecordingPlugin(HypervisorPlugin):
        def __init__(self):
            self.calls: list[tuple[HookType, HypervisorState]] = []

        def on_hook(self, hook_type: HookType, state: HypervisorState) -> None:
            self.calls.append((hook_type, state))

    plugin = _RecordingPlugin()
    state = HypervisorState(phase_id=3)

    plugin.on_hook(HookType.PRE_PHASE, state)
    plugin.on_hook(HookType.POST_PHASE, state)

    assert len(plugin.calls) == 2
    assert plugin.calls[0][0] == HookType.PRE_PHASE
    assert plugin.calls[1][0] == HookType.POST_PHASE
