"""
Hypervisor V2 — Abstract interfaces for pluggable orchestration components.

Defines the abstract base classes for the event mesh, GPU skill router,
unified memory manager, agent delegation engine, and hypervisor plugin
system. Concrete implementations are injected at runtime.

This module intentionally contains NO business logic — it is a contracts
layer used by the Hypervisor and by tests that verify interface compliance.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================


class HookType(StrEnum):
    """Types of hook events emitted by the hypervisor lifecycle.

    Attributes:
        PRE_PHASE: Fired immediately before a phase begins.
        POST_PHASE: Fired immediately after a phase completes successfully.
        ON_FAILURE: Fired when a phase fails.
        ON_SUCCESS: Fired when the full plan completes.
    """

    PRE_PHASE = "pre_phase"
    POST_PHASE = "post_phase"
    ON_FAILURE = "on_failure"
    ON_SUCCESS = "on_success"


# ============================================================================
# Models (Pydantic v2, frozen=True)
# ============================================================================


class HypervisorState(BaseModel, frozen=True):
    """Immutable snapshot of the current hypervisor runtime state.

    Attributes:
        phase_id: ID of the phase currently being executed (0 = idle).
        mode: String name of the active ExecutionMode.
        active_workers: Number of currently active worker threads/processes.
        memory_mb: Estimated memory usage in megabytes.
    """

    phase_id: int = 0
    mode: str = "sequential"
    active_workers: int = 0
    memory_mb: float = 0.0


class PluginConfig(BaseModel, frozen=True):
    """Configuration passed to a HypervisorPlugin on registration.

    Attributes:
        name: Plugin identifier.
        enabled: Whether the plugin should be active.
        settings: Arbitrary key-value settings for the plugin.
    """

    name: str
    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Abstract Interfaces
# ============================================================================


class EventMesh(ABC):
    """Abstract event mesh for pub/sub communication between components.

    Provides a decoupled communication channel. Publishers post events
    to named topics; subscribers register handlers for those topics.
    """

    @abstractmethod
    def publish(self, event: str) -> None:
        """Publish an event to the mesh.

        Args:
            event: Serialized event payload (e.g. JSON string or topic name).
        """

    @abstractmethod
    def subscribe(self, topic: str) -> None:
        """Subscribe to a topic on the mesh.

        Args:
            topic: Topic identifier to subscribe to.
        """

    @abstractmethod
    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic on the mesh.

        Args:
            topic: Topic identifier to unsubscribe from.
        """


class GPUSkillRouter(ABC):
    """Abstract router that matches tasks to skills using GPU acceleration.

    Implementations may use embedding similarity, keyword matching, or
    other techniques to determine the best skill for a given task.
    """

    @abstractmethod
    def route(self, task: str) -> str:
        """Route a task to the most appropriate skill.

        Args:
            task: Natural language description of the task.

        Returns:
            Name of the skill or handler best suited for the task.
        """


class UnifiedMemoryManager(ABC):
    """Abstract manager for a unified, tiered memory system.

    Manages allocation and deallocation of memory across tiers
    (e.g. L1 hot cache, L2 warm, L3 cold/disk).
    """

    @abstractmethod
    def allocate(self, mb: float) -> None:
        """Allocate memory.

        Args:
            mb: Megabytes to allocate.
        """

    @abstractmethod
    def free(self, mb: float) -> None:
        """Free previously allocated memory.

        Args:
            mb: Megabytes to release.
        """

    @abstractmethod
    def used_mb(self) -> float:
        """Return the total allocated memory in megabytes."""


class AgentDelegationEngine(ABC):
    """Abstract engine for delegating tasks to specialized sub-agents.

    Analyses task descriptions and routes them to the most appropriate
    specialised agent type. Returns a task identifier for tracking.
    """

    @abstractmethod
    def delegate(self, task: str, agent_type: str) -> str:
        """Delegate a task to an agent of the given type.

        Args:
            task: Natural language task description.
            agent_type: Type of agent to delegate to (e.g. "code", "docs").

        Returns:
            Unique task identifier for tracking delegation status.
        """


class HypervisorPlugin(ABC):
    """Abstract plugin that reacts to hypervisor lifecycle hooks.

    Plugins receive hook callbacks at key points in the phase execution
    lifecycle. They should be lightweight and fail-safe (never raise).
    """

    @abstractmethod
    def on_hook(self, hook_type: HookType, state: HypervisorState) -> None:
        """Handle a lifecycle hook event.

        Implementations MUST NOT raise exceptions — they should log and
        return gracefully on any error to preserve fail-open semantics.

        Args:
            hook_type: The type of hook being fired.
            state: Current immutable snapshot of the hypervisor state.
        """


# ============================================================================
# Concrete Mixins / Base Helpers (not abstract)
# ============================================================================


class BaseEventMesh(EventMesh):
    """Minimal in-memory EventMesh implementation for testing and fallback.

    Stores published events in a list and tracks subscriptions by topic.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[str]] = {}
        self._events: list[str] = []

    def publish(self, event: str) -> None:
        """Record the event."""
        self._events.append(event)

    def subscribe(self, topic: str) -> None:
        """Register subscription to topic."""
        self._subscriptions.setdefault(topic, [])

    def unsubscribe(self, topic: str) -> None:
        """Remove subscription from topic."""
        self._subscriptions.pop(topic, None)

    @property
    def events(self) -> list[str]:
        """Return a copy of all published events."""
        return list(self._events)

    @property
    def subscriptions(self) -> dict[str, list[str]]:
        """Return a copy of all topic subscriptions."""
        return dict(self._subscriptions)


class InMemoryMemoryManager(UnifiedMemoryManager):
    """Simple in-memory memory manager for testing.

    Tracks allocated MB via a running total. Does not perform actual
    system memory allocation.
    """

    def __init__(self) -> None:
        self._used: float = 0.0

    def allocate(self, mb: float) -> None:
        """Increment tracked usage."""
        self._used += mb

    def free(self, mb: float) -> None:
        """Decrement tracked usage, floor at 0."""
        self._used = max(0.0, self._used - mb)

    def used_mb(self) -> float:
        """Return total tracked allocation."""
        return self._used


class SimpleSkillRouter(GPUSkillRouter):
    """Simple keyword-based skill router for testing.

    Routes tasks by matching keywords in the task string to registered
    skills. Falls back to a default skill when no match is found.
    """

    def __init__(self, default_skill: str = "general") -> None:
        self._routes: dict[str, str] = {}
        self._default = default_skill

    def register(self, keyword: str, skill: str) -> None:
        """Register a keyword → skill mapping."""
        self._routes[keyword] = skill

    def route(self, task: str) -> str:
        """Match task against registered keywords."""
        task_lower = task.lower()
        for keyword, skill in self._routes.items():
            if keyword in task_lower:
                return skill
        return self._default


class SimpleDelegationEngine(AgentDelegationEngine):
    """Simple delegation engine that returns a task ID for testing."""

    def __init__(self) -> None:
        self._counter = 0

    def delegate(self, task: str, agent_type: str) -> str:
        """Create a deterministic task ID from agent_type and counter."""
        self._counter += 1
        return f"{agent_type}-task-{self._counter}"
