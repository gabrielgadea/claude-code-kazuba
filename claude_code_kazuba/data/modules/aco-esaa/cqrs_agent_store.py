"""cqrs_agent_store.py — CQRS Pattern for Agent State Management.

Command Query Responsibility Segregation: Separate read and write models
for optimal performance and scalability.

The CQRS pattern separates:
- CommandSide: Handles all state mutations (writes)
- QuerySide: Optimized for fast reads with potential caching

This allows independent optimization of read and write paths.

Example:
    # Write side - commands
    commands = CommandSide()
    agent_id = commands.create_agent(spec)
    commands.update_status(agent_id, "executing")

    # Read side - queries
    queries = QuerySide()
    state = queries.get_agent(agent_id)
    all_agents = queries.list_agents(status="executing")
    stats = queries.get_agent_stats()
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Project root resolution for imports
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.aco.models.agent_spec import AgentCategory, AgentSpec

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Read model for agent state.

    Optimized for queries with denormalized fields.

    Attributes:
        agent_id: Unique agent identifier
        name: Agent name
        version: Agent version
        status: Current status (created/executing/validated/failed/rolled_back)
        created_at: ISO8601 timestamp of creation
        updated_at: ISO8601 timestamp of last update
        execution_count: Number of times agent was executed
        last_execution: ISO8601 timestamp of last execution
        last_result: Result of last execution
        error_count: Number of errors encountered
        metadata: Additional metadata
    """

    agent_id: str
    name: str
    version: str
    status: str  # created, executing, validated, failed, rolled_back
    created_at: str
    updated_at: str
    execution_count: int = 0
    last_execution: str | None = None
    last_result: dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class CommandSide:
    """Write model for agent state (commands).

    Handles all state mutations. Events are persisted to EventStore.
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize command side.

        Args:
            storage_path: Directory for state storage
        """
        self._storage_path = storage_path or Path(".claude/esaa/agents")
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def create_agent(self, spec: AgentSpec) -> str:
        """Create new agent.

        Args:
            spec: Agent specification

        Returns:
            Agent ID
        """
        agent_id = f"{spec.name}-{spec.version}"
        state_path = self._storage_path / f"{agent_id}.json"

        now = datetime.now(UTC).isoformat()

        state = {
            "agent_id": agent_id,
            "name": spec.name,
            "version": spec.version,
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "execution_count": 0,
            "error_count": 0,
            "spec": spec.to_frontmatter(),
        }

        state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Created agent: %s", agent_id)
        return agent_id

    def update_status(
        self,
        agent_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update agent status.

        Args:
            agent_id: Agent identifier
            status: New status
            metadata: Optional metadata to merge
        """
        state_path = self._storage_path / f"{agent_id}.json"

        if not state_path.exists():
            raise ValueError(f"Agent not found: {agent_id}")

        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["status"] = status
        state["updated_at"] = datetime.now(UTC).isoformat()

        if metadata:
            state.setdefault("metadata", {}).update(metadata)

        state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug("Updated agent %s status to %s", agent_id, status)

    def increment_execution_count(self, agent_id: str, result: dict[str, Any]) -> None:
        """Record agent execution.

        Args:
            agent_id: Agent identifier
            result: Execution result
        """
        state_path = self._storage_path / f"{agent_id}.json"

        if not state_path.exists():
            raise ValueError(f"Agent not found: {agent_id}")

        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["execution_count"] = state.get("execution_count", 0) + 1
        state["last_execution"] = datetime.now(UTC).isoformat()
        state["last_result"] = result
        state["updated_at"] = state["last_execution"]

        if result.get("status") == "failure":
            state["error_count"] = state.get("error_count", 0) + 1

        state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if deleted, False if not found
        """
        state_path = self._storage_path / f"{agent_id}.json"

        if not state_path.exists():
            return False

        state_path.unlink()
        logger.info("Deleted agent: %s", agent_id)
        return True


class QuerySide:
    """Read model for agent state (queries).

    Optimized for fast reads with potential caching.
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize query side.

        Args:
            storage_path: Directory for state storage
        """
        self._storage_path = storage_path or Path(".claude/esaa/agents")

    def get_agent(self, agent_id: str) -> AgentState | None:
        """Get agent state by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent state or None if not found
        """
        state_path = self._storage_path / f"{agent_id}.json"

        if not state_path.exists():
            return None

        data = json.loads(state_path.read_text(encoding="utf-8"))
        return self._deserialize_state(data)

    def list_agents(self, status: str | None = None) -> list[AgentState]:
        """List all agents, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of agent states
        """
        agents = []

        for state_file in self._storage_path.glob("*.json"):
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))

                if status and data.get("status") != status:
                    continue

                agents.append(self._deserialize_state(data))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to parse agent state %s: %s", state_file, e)

        return agents

    def get_agent_stats(self) -> dict[str, Any]:
        """Get aggregate statistics.

        Returns:
            Statistics dictionary
        """
        agents = self.list_agents()

        if not agents:
            return {
                "total": 0,
                "by_status": {},
                "total_executions": 0,
                "total_errors": 0,
            }

        by_status: dict[str, int] = {}
        for agent in agents:
            by_status[agent.status] = by_status.get(agent.status, 0) + 1

        total_executions = sum(a.execution_count for a in agents)
        return {
            "total": len(agents),
            "by_status": by_status,
            "total_executions": total_executions,
            "total_errors": sum(a.error_count for a in agents),
            "avg_executions": total_executions / len(agents),
        }

    def search_agents(self, name_pattern: str) -> list[AgentState]:
        """Search agents by name pattern.

        Args:
            name_pattern: Pattern to match in agent names

        Returns:
            List of matching agent states
        """
        agents = self.list_agents()
        return [a for a in agents if name_pattern.lower() in a.name.lower()]

    def _deserialize_state(self, data: dict[str, Any]) -> AgentState:
        """Deserialize state dictionary to AgentState.

        Args:
            data: State dictionary

        Returns:
            AgentState instance
        """
        return AgentState(
            agent_id=data["agent_id"],
            name=data["name"],
            version=data["version"],
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            execution_count=data.get("execution_count", 0),
            last_execution=data.get("last_execution"),
            last_result=data.get("last_result", {}),
            error_count=data.get("error_count", 0),
            metadata=data.get("metadata", {}),
        )


class AgentStore:
    """Combined CQRS agent store.

    Provides unified interface for both command and query operations.

    Example:
        store = AgentStore()

        # Create agent
        agent_id = store.commands.create_agent(spec)

        # Query agent
        state = store.queries.get_agent(agent_id)

        # Update and record execution
        store.commands.increment_execution_count(agent_id, result)
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize agent store.

        Args:
            storage_path: Base directory for storage
        """
        base_path = storage_path or Path(".claude/esaa")
        self.commands = CommandSide(base_path / "agents")
        self.queries = QuerySide(base_path / "agents")


# Alias for compatibility with external references
CQRSAgentStore = AgentStore


if __name__ == "__main__":
    # Demo usage
    import tempfile

    logging.basicConfig(level=logging.INFO)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = AgentStore(Path(tmpdir))

        # Create a spec
        spec = AgentSpec(
            name="demo-agent",
            version="1.0.0",
            description="A demo agent for testing CQRS store with sufficient chars.",
            category=AgentCategory.GENERIC,
        )

        # Create agent
        agent_id = store.commands.create_agent(spec)
        print(f"Created: {agent_id}")

        # Update status
        store.commands.update_status(agent_id, "executing")

        # Record execution
        store.commands.increment_execution_count(agent_id, {"status": "success", "output": "Hello"})

        # Query
        state = store.queries.get_agent(agent_id)
        if state:
            print(f"State: {state.status}, Executions: {state.execution_count}")
        else:
            print("State: not found")

        # Stats
        stats = store.queries.get_agent_stats()
        print(f"Stats: {stats}")
