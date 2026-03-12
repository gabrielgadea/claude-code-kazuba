"""Verify upcaster handles event migration."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "claude_code_kazuba" / "data" / "modules" / "aco-esaa" / "upcaster.py"
)


def _load_upcaster():
    """Load upcaster module dynamically."""
    spec = importlib.util.spec_from_file_location("upcaster", MODULE_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["upcaster"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture
def upcaster_mod():
    """Provide loaded upcaster module."""
    return _load_upcaster()


class TestUpcasterStructure:
    """Verify upcaster.py has expected structure."""

    def test_file_exists(self) -> None:
        assert MODULE_PATH.exists()

    def test_compiles(self) -> None:
        import ast

        source = MODULE_PATH.read_text()
        ast.parse(source, filename="upcaster.py")

    def test_has_event_upcaster_class(self) -> None:
        import ast

        source = MODULE_PATH.read_text()
        tree = ast.parse(source)
        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert "EventUpcaster" in class_names


class TestUpcasterFunctionality:
    """Verify upcaster can register and apply migrations."""

    def test_register_and_upcast(self, upcaster_mod) -> None:
        caster = upcaster_mod.EventUpcaster()

        def v1_to_v2(raw: dict) -> dict:
            raw["schema_version"] = 2
            raw.setdefault("payload", {})["duration_ms"] = raw.get("payload", {}).pop("duration", 0)
            return raw

        caster.register("AgentExecuted", from_version=1, fn=v1_to_v2)

        event = {
            "event_type": "AgentExecuted",
            "schema_version": 1,
            "payload": {"duration": 42},
        }
        upgraded = caster.upcast(event)
        assert upgraded["schema_version"] == 2
        assert upgraded["payload"]["duration_ms"] == 42
        assert "duration" not in upgraded["payload"]

    def test_no_migration_passthrough(self, upcaster_mod) -> None:
        caster = upcaster_mod.EventUpcaster()
        event = {"event_type": "SomeEvent", "schema_version": 1, "payload": {"data": "unchanged"}}
        result = caster.upcast(event)
        assert result["payload"]["data"] == "unchanged"

    def test_upcaster_fn_type_alias(self, upcaster_mod) -> None:
        assert hasattr(upcaster_mod, "UpcasterFn")
