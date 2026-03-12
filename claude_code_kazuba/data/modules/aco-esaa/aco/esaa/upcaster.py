"""EventUpcaster — schema evolution for ESAA DomainEvents.

Enables zero-downtime migration of persisted event streams when field names
or structures change. Each registered upcaster transforms a raw event dict
from one schema version to the next, allowing historical events to be
replayed transparently through updated models.

Example:
    >>> from scripts.aco.esaa.upcaster import EventUpcaster
    >>> caster = EventUpcaster()
    >>> # Register v1 → v2 migration for AgentExecuted events
    >>> def v1_to_v2(raw: dict) -> dict:
    ...     raw["schema_version"] = 2
    ...     raw["payload"]["duration_ms"] = raw["payload"].pop("duration", 0)
    ...     return raw
    >>> caster.register("AgentExecuted", from_version=1, fn=v1_to_v2)
    >>> upgraded = caster.upcast({"event_type": "AgentExecuted", "schema_version": 1, ...})
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

UpcasterFn = Callable[[dict[str, Any]], dict[str, Any]]


class EventUpcaster:
    """Transforms raw event dicts through a chain of version migrations.

    Each registered ``UpcasterFn`` accepts a raw dict at version N and
    returns a dict at version N+1 (or higher). Migrations are applied
    sequentially until no further upcaster is found for the current version.

    Thread-safe: registrations happen at startup before concurrent reads.
    """

    def __init__(self) -> None:
        self._chain: dict[tuple[str, int], UpcasterFn] = {}

    def register(
        self, event_type: str, from_version: int, fn: UpcasterFn
    ) -> None:
        """Register a migration function for a specific event type and version.

        Args:
            event_type: The ``event_type`` field value to match (e.g. "AgentExecuted").
            from_version: Schema version the function upgrades FROM.
            fn: Callable that accepts raw dict and returns upgraded dict.
                Must set ``raw["schema_version"]`` to the new version.

        Raises:
            ValueError: If a migration for (event_type, from_version) already exists.
        """
        key = (event_type, from_version)
        if key in self._chain:
            raise ValueError(
                f"Upcaster for ({event_type!r}, v{from_version}) already registered"
            )
        self._chain[key] = fn

    def upcast(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Apply all applicable migrations to a raw event dict.

        Walks the registered migration chain starting from the event's
        current ``schema_version`` until no further migration is found.

        Args:
            raw: Raw event dictionary (may be mutated by migration functions).

        Returns:
            Upgraded event dict at the latest registered schema version.
        """
        event_type: str = raw.get("event_type", "")
        version: int = int(raw.get("schema_version", 1))

        while (event_type, version) in self._chain:
            fn = self._chain[(event_type, version)]
            raw = fn(raw)
            new_version: int = int(raw.get("schema_version", version + 1))
            if new_version <= version:
                break
            version = new_version

        return raw

    def registered_migrations(self) -> list[tuple[str, int]]:
        """Return a sorted list of registered (event_type, from_version) keys.

        Returns:
            Sorted list of (event_type, from_version) tuples.
        """
        return sorted(self._chain.keys())
