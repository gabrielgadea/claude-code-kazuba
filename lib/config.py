"""Pydantic v2 configuration models for claude-code-kazuba."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 — Pydantic needs this at runtime
from typing import Any

from pydantic import BaseModel, Field


class ModuleManifest(BaseModel):
    """Manifest for a kazuba module."""

    name: str
    version: str
    description: str
    dependencies: list[str]
    hooks_file: str | None = None
    files: list[str]


class HookRegistration(BaseModel):
    """Registration entry for a hook in settings.json."""

    event: str
    matcher: str | None = None
    command: str
    timeout: int = 10


class PresetConfig(BaseModel):
    """A preset that bundles multiple modules together."""

    name: str
    description: str
    modules: list[str]


class ProjectSettings(BaseModel):
    """Claude Code settings.json model."""

    schema_: str | None = Field(default=None, alias="$schema")
    permissions: dict[str, Any] = Field(default_factory=dict)
    hooks: dict[str, Any] = Field(default_factory=dict)
    env: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class InstallerConfig(BaseModel):
    """Configuration for the module installer."""

    target_dir: Path
    preset: str | None = None
    modules: list[str] = Field(default_factory=list)
    dry_run: bool = False
    stack: str | None = None


class AgentTrigger(BaseModel, frozen=True):
    """Agent trigger with condition string for auto-activation.

    Conditions are matched using keyword-based evaluation (no eval()).
    Recovery plan: string-only conditions without code evaluation.
    """

    name: str = ""
    type: str = "auto"
    condition: str = ""
    thinking_level: str = "normal"
    agent: str = ""
    model: str = "sonnet"
    priority: int = 50
    background: bool = False
    max_retries: int = 3
    description: str = ""
    skill_attachments: list[str] = Field(default_factory=list)

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Evaluate trigger condition against context using safe string matching.

        Supports simple conditions like:
          - "task_type == 'exploration'"
          - "'search' in task"
          - "complexity == 'high'"

        Args:
            context: Dict with task, complexity, domain, task_type, etc.

        Returns:
            True if trigger condition matches the context.
        """
        if not self.condition:
            return False
        condition = self.condition.lower()
        # Check each context key for simple equality or membership conditions
        for key, value in context.items():
            val_str = str(value).lower() if value is not None else ""
            # Match "key == 'value'" pattern
            if f"{key} ==" in condition and f"'{val_str}'" in condition:
                return True
            # Match "'keyword' in key" or "keyword in key" pattern
            if f"in {key}" in condition:
                for token in condition.split():
                    token = token.strip("'\"")
                    if token and token in val_str:
                        return True
        return False


class RecoveryTrigger(BaseModel, frozen=True):
    """Recovery trigger definition for automatic failure handling."""

    name: str = ""
    type: str = "auto"
    on_event: str = ""
    action: str = ""
    max_retries: int = 3
    cooldown_seconds: float = 30.0
    description: str = ""
    conditions: dict[str, Any] = Field(default_factory=dict)


class TriggerRegistry(BaseModel):
    """Registry for loading and querying triggers from YAML config."""

    agent_triggers: list[AgentTrigger] = Field(default_factory=list)  # type: ignore[assignment]
    recovery_triggers: list[RecoveryTrigger] = Field(default_factory=list)  # type: ignore[assignment]

    @classmethod
    def from_yaml(cls, agent_path: Path, recovery_path: Path) -> TriggerRegistry:
        """Load triggers from YAML files.

        Args:
            agent_path: Path to agent_triggers.yaml.
            recovery_path: Path to recovery_triggers.yaml.

        Returns:
            Populated TriggerRegistry.
        """
        import yaml  # noqa: PLC0415

        agent_triggers: list[AgentTrigger] = []
        if agent_path.exists():
            data = yaml.safe_load(agent_path.read_text()) or {}  # type: ignore[assignment]
            for tname, cfg in (data.get("agent_triggers") or {}).items():  # type: ignore[union-attr]
                safe_cfg = {k: v for k, v in cfg.items() if k != "name"}  # type: ignore[union-attr]
                agent_triggers.append(AgentTrigger(name=tname, **safe_cfg))  # type: ignore[arg-type]

        recovery_triggers: list[RecoveryTrigger] = []
        if recovery_path.exists():
            data: dict[str, Any] = yaml.safe_load(recovery_path.read_text()) or {}  # type: ignore[assignment]
            # Support both flat "recovery_triggers" and nested "recovery.{auto,manual}_triggers"
            flat: dict[str, Any] = data.get("recovery_triggers") or {}  # type: ignore[assignment]
            nested: dict[str, Any] = data.get("recovery") or {}  # type: ignore[assignment]
            auto_triggers: dict[str, Any] = nested.get("automatic_triggers") or {}  # type: ignore[assignment]
            manual_triggers: dict[str, Any] = nested.get("manual_triggers") or {}  # type: ignore[assignment]
            all_triggers: dict[str, Any] = {**flat, **auto_triggers, **manual_triggers}
            for tname, cfg in all_triggers.items():
                if not isinstance(cfg, dict):
                    continue
                safe_cfg: dict[str, Any] = {k: v for k, v in cfg.items() if k != "name"}  # type: ignore[misc]
                # Map nested YAML fields to RecoveryTrigger fields
                # Prefer explicit on_event, then condition, then trigger, then name
                on_event: str | None = (
                    safe_cfg.pop("on_event", None)  # type: ignore[misc]
                    or safe_cfg.pop("condition", None)  # type: ignore[misc]
                    or safe_cfg.pop("trigger", tname)  # type: ignore[misc]
                )
                recovery_triggers.append(
                    RecoveryTrigger(
                        name=str(tname),
                        on_event=str(on_event) if on_event else str(tname),
                        **{  # type: ignore[arg-type]
                            k: v
                            for k, v in safe_cfg.items()
                            if k
                            in {
                                "type",
                                "action",
                                "max_retries",
                                "cooldown_seconds",
                                "description",
                                "conditions",
                            }
                        },
                    )
                )

        return cls(agent_triggers=agent_triggers, recovery_triggers=recovery_triggers)

    def match_agent_triggers(self, context: dict[str, Any]) -> list[AgentTrigger]:
        """Return all agent triggers that match the given context.

        Args:
            context: Execution context dict.

        Returns:
            List of matching triggers sorted by priority descending.
        """
        matched = [t for t in self.agent_triggers if t.evaluate(context)]
        return sorted(matched, key=lambda t: t.priority, reverse=True)

    def get_recovery_trigger(self, event: str) -> RecoveryTrigger | None:
        """Find the first recovery trigger matching an event.

        Args:
            event: Event name to match against on_event field.

        Returns:
            Matching trigger or None.
        """
        for trigger in self.recovery_triggers:
            if trigger.on_event == event:
                return trigger
        return None


def resolve_dependencies(
    requested: list[str],
    manifests: dict[str, ModuleManifest],
) -> list[str]:
    """Resolve module dependencies in topological order.

    Args:
        requested: List of module names to install.
        manifests: Map of module name to its manifest.

    Returns:
        Ordered list of module names (dependencies first).

    Raises:
        ValueError: If a required dependency is not found in manifests.
    """
    resolved: list[str] = []
    visited: set[str] = set()

    def _visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        manifest = manifests.get(name)
        if manifest is None:
            msg = f"Module not found: {name}"
            raise ValueError(msg)
        for dep in manifest.dependencies:
            if dep not in manifests:
                msg = f"Dependency not found: {dep} (required by {name})"
                raise ValueError(msg)
            _visit(dep)
        resolved.append(name)

    for module in requested:
        _visit(module)

    return resolved
