#!/usr/bin/env python3
"""Regression tests — Issue #723.

Verifies that core modules remain importable and functional after Phase 19
changes. Guards against regressions introduced by the migration script or
integration tests.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Tests: Core module imports
# ---------------------------------------------------------------------------


def test_lib_rlm_imports() -> None:
    """lib.rlm module imports without error."""
    mod = importlib.import_module("lib.rlm")
    assert hasattr(mod, "RLMFacade")
    assert hasattr(mod, "RLMFacadeConfig")


def test_lib_config_imports() -> None:
    """lib.config module imports without error."""
    mod = importlib.import_module("lib.config")
    assert mod is not None


def test_lib_circuit_breaker_imports() -> None:
    """lib.circuit_breaker module imports without error."""
    mod = importlib.import_module("lib.circuit_breaker")
    assert mod is not None


def test_lib_governance_imports() -> None:
    """lib.governance module imports without error."""
    mod = importlib.import_module("lib.governance")
    assert mod is not None


# ---------------------------------------------------------------------------
# Tests: Migration script importable
# ---------------------------------------------------------------------------


def test_migration_script_importable() -> None:
    """migrate_v01_v02 script can be imported and has expected symbols."""
    import importlib.util
    import sys

    module_name = "migrate_v01_v02_reg_test"
    script_path = _ROOT / "scripts" / "migrate_v01_v02.py"
    assert script_path.exists(), f"Migration script not found: {script_path}"

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    # Must register in sys.modules BEFORE exec_module so dataclasses work correctly
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        sys.modules.pop(module_name, None)

    assert hasattr(mod, "MigrationConfig")
    assert hasattr(mod, "MigrationResult")
    assert hasattr(mod, "detect_v1_installation")
    assert hasattr(mod, "run_migration")
    assert hasattr(mod, "main")


# ---------------------------------------------------------------------------
# Tests: Conftest fixtures are accessible
# ---------------------------------------------------------------------------


def test_conftest_base_dir_fixture(base_dir: Path) -> None:
    """base_dir fixture from conftest resolves to project root."""
    assert base_dir.exists()
    assert (base_dir / "lib").exists()


def test_conftest_tmp_settings_fixture(tmp_settings: Path) -> None:
    """tmp_settings fixture creates a valid settings.json."""
    assert tmp_settings.exists()
    data = json.loads(tmp_settings.read_text())
    assert "hooks" in data


def test_conftest_checkpoint_dir_fixture(checkpoint_dir: Path) -> None:
    """checkpoint_dir fixture creates a writable directory."""
    assert checkpoint_dir.exists()
    test_file = checkpoint_dir / "regression_test.txt"
    test_file.write_text("ok")
    assert test_file.read_text() == "ok"


# ---------------------------------------------------------------------------
# Tests: Phase 19 files exist on disk
# ---------------------------------------------------------------------------


def test_migration_script_exists() -> None:
    """scripts/migrate_v01_v02.py exists."""
    path = _ROOT / "scripts" / "migrate_v01_v02.py"
    assert path.exists(), f"Missing: {path}"


def test_integration_v2_test_dir_exists() -> None:
    """tests/integration_v2/ directory exists."""
    path = _ROOT / "tests" / "integration_v2"
    assert path.exists() and path.is_dir()


def test_migration_script_minimum_lines() -> None:
    """Migration script has at least 150 lines."""
    path = _ROOT / "scripts" / "migrate_v01_v02.py"
    lines = len(path.read_text().splitlines())
    assert lines >= 150, f"migrate_v01_v02.py has only {lines} lines (need 150+)"
