"""Tests for UnifiedMemorySystem (UMS) — 5-layer CQRS facade."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_ROOT = Path(__file__).resolve().parent.parent / "claude_code_kazuba" / "data" / "modules" / "intelligence-ums"


def _load_ums_module():
    import sys

    ums_path = MODULE_ROOT / "ums.py"
    assert ums_path.exists(), f"ums.py not found at {ums_path}"
    mod_name = "intelligence_ums_test_module"
    spec = importlib.util.spec_from_file_location(mod_name, ums_path)
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules so frozen dataclass __module__ lookup works
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ums_mod():
    return _load_ums_module()


@pytest.fixture
def ums(tmp_path, ums_mod):
    system = ums_mod.UnifiedMemorySystem(data_path=tmp_path)
    yield system
    system.close()


class TestUnifiedMemorySystem:
    def test_initialization_creates_data_dir(self, tmp_path, ums_mod):
        data_dir = tmp_path / "ums_data"
        assert not data_dir.exists()
        system = ums_mod.UnifiedMemorySystem(data_path=data_dir)
        assert data_dir.exists()
        system.close()

    def test_is_initialized_true_after_creation(self, ums):
        assert ums.is_initialized is True

    def test_data_path_property(self, tmp_path, ums):
        assert ums.data_path == tmp_path

    def test_store_and_recall_basic(self, ums):
        ums.store("mykey", "hello world content")
        results = ums.recall("hello world")
        assert len(results) >= 1
        assert results[0].content == "hello world content"
        assert results[0].source == "L0"

    def test_recall_returns_empty_for_nonexistent(self, ums):
        results = ums.recall("xyzzy_nonexistent_query_abc")
        assert results == []

    def test_store_key_in_metadata(self, ums):
        ums.store("mykey", "some content here")
        results = ums.recall("some content")
        assert len(results) >= 1
        assert results[0].metadata.get("key") == "mykey"

    def test_lru_eviction_with_small_cache(self, tmp_path, ums_mod):
        """Store 5 items with max_size=3, verify oldest are evicted."""

        mod = ums_mod
        config = mod.UMSConfig(data_path=tmp_path, l0_max_size=3)
        system = mod.UnifiedMemorySystem(data_path=tmp_path, config=config)
        try:
            for i in range(5):
                system.store(f"key{i}", f"content for item {i}")
            # Cache should hold at most 3 items
            assert len(system._l0_cache) == 3
            # First 2 items should be evicted
            assert "key0" not in system._l0_cache
            assert "key1" not in system._l0_cache
            # Last 3 should be present
            assert "key2" in system._l0_cache
            assert "key3" in system._l0_cache
            assert "key4" in system._l0_cache
        finally:
            system.close()

    def test_get_stats_returns_expected_keys(self, ums):
        stats = ums.get_stats()
        expected_keys = {
            "l0_size",
            "l0_max_size",
            "l1_db_exists",
            "l2_index_exists",
            "l3_available",
            "l4_available",
            "data_path",
        }
        assert expected_keys.issubset(set(stats.keys()))

    def test_get_stats_l0_size_reflects_stores(self, ums):
        ums.store("a", "alpha content")
        ums.store("b", "beta content")
        stats = ums.get_stats()
        assert stats["l0_size"] == 2

    def test_recall_top_k_limits_results(self, ums):
        for i in range(10):
            ums.store(f"key{i}", f"matching query content item {i}")
        results = ums.recall("matching query content", top_k=3)
        assert len(results) <= 3

    def test_recall_without_l1_db_does_not_crash(self, ums):
        """L1 query should gracefully skip if events.db does not exist."""
        results = ums.recall("anything")
        assert isinstance(results, list)

    def test_recall_sorted_by_score_descending(self, ums):
        ums.store("k1", "test query alpha")
        ums.store("k2", "test query beta")
        results = ums.recall("test query")
        if len(results) > 1:
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_store_overwrites_existing_key(self, ums):
        ums.store("dupkey", "original content")
        ums.store("dupkey", "updated content")
        results = ums.recall("updated content")
        assert len(results) >= 1
        assert results[0].content == "updated content"

    def test_ums_files_exist(self):
        assert (MODULE_ROOT / "ums.py").exists()
        assert (MODULE_ROOT / "MODULE.md").exists()
        assert (MODULE_ROOT / "settings.hooks.json").exists()
