"""Tests for modules/rlm/src/q_table.py — QTable."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from modules.rlm.src.q_table import QTable, _decode, _encode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_table(**kwargs: object) -> QTable:
    defaults: dict[str, object] = {
        "learning_rate": 0.1,
        "discount_factor": 0.95,
        "lambda_trace": 0.8,
        "max_size": 100,
    }
    defaults.update(kwargs)
    return QTable(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_unseen_returns_zero() -> None:
    table = make_table()
    assert table.get("s1", "a1") == 0.0


def test_set_and_get() -> None:
    table = make_table()
    table.set("s1", "a1", 3.14)
    assert table.get("s1", "a1") == pytest.approx(3.14)


def test_update_increases_q_value_with_positive_reward() -> None:
    table = make_table()
    result = table.update("s1", "a1", reward=1.0, next_state="s2")
    assert result["new_q_value"] > 0.0
    assert result["td_error"] > 0.0
    assert result["states_updated"] >= 1


def test_update_decreases_q_value_with_negative_reward() -> None:
    table = make_table()
    # First set a positive Q-value
    table.set("s1", "a1", 1.0)
    result = table.update("s1", "a1", reward=-1.0, next_state="terminal")
    # After negative reward update, td_error should be negative
    assert result["td_error"] < 0.0


def test_update_returns_correct_keys() -> None:
    table = make_table()
    result = table.update("s1", "a1", reward=0.5, next_state="s2")
    assert "new_q_value" in result
    assert "td_error" in result
    assert "states_updated" in result


def test_multiple_updates_converge() -> None:
    table = make_table(learning_rate=0.5)
    for _ in range(20):
        table.update("s1", "a1", reward=1.0, next_state="terminal")
    q = table.get("s1", "a1")
    assert q > 0.5, "Q-value should converge toward positive territory"


def test_best_action_returns_highest_q() -> None:
    table = make_table()
    table.set("s1", "a1", 0.1)
    table.set("s1", "a2", 0.9)
    table.set("s1", "a3", 0.5)
    assert table.best_action("s1") == "a2"


def test_best_action_returns_none_for_unknown_state() -> None:
    table = make_table()
    assert table.best_action("unknown") is None


def test_max_q_returns_zero_for_unknown_state() -> None:
    table = make_table()
    assert table.max_q("unknown") == 0.0


def test_max_q_returns_correct_value() -> None:
    table = make_table()
    table.set("s1", "a1", 0.3)
    table.set("s1", "a2", 0.8)
    assert table.max_q("s1") == pytest.approx(0.8)


def test_actions_for_state() -> None:
    table = make_table()
    table.set("s1", "a1", 0.5)
    table.set("s1", "a2", 0.3)
    actions = table.actions_for_state("s1")
    assert set(actions) == {"a1", "a2"}


def test_reset_traces() -> None:
    table = make_table()
    table.update("s1", "a1", reward=1.0, next_state="s2")
    # After reset traces, next update should only update current pair
    table.reset_traces()
    result = table.update("s2", "a1", reward=0.5, next_state="terminal")
    assert result["states_updated"] >= 1


def test_export_and_import_roundtrip() -> None:
    table = make_table()
    table.set("s1", "a1", 0.7)
    table.set("s2", "a2", 0.3)

    exported = table.export()
    assert "s1|a1" in exported
    assert "s2|a2" in exported

    new_table = make_table()
    new_table.import_data(exported)
    assert new_table.get("s1", "a1") == pytest.approx(0.7)
    assert new_table.get("s2", "a2") == pytest.approx(0.3)


def test_persistence_save_and_load() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "q_table.json"
        table = make_table()
        table.set("s1", "a1", 1.23)
        saved_path = table.save(path)
        assert saved_path == path
        assert path.exists()

        loaded = make_table()
        loaded.load(path)
        assert loaded.get("s1", "a1") == pytest.approx(1.23)


def test_size_tracks_entries() -> None:
    table = make_table()
    assert table.size() == 0
    table.set("s1", "a1", 0.5)
    assert table.size() == 1
    table.set("s1", "a2", 0.3)
    assert table.size() == 2


def test_update_count_increments() -> None:
    table = make_table()
    assert table.update_count() == 0
    table.update("s1", "a1", reward=1.0, next_state="s2")
    assert table.update_count() == 1
    table.update("s2", "a2", reward=0.5, next_state="terminal")
    assert table.update_count() == 2


def test_max_size_enforcement() -> None:
    table = QTable(max_size=3)
    for i in range(10):
        table.set(f"s{i}", "a1", float(i))
    assert table.size() <= 3


def test_sarsa_update_with_next_action() -> None:
    table = make_table()
    table.set("s2", "a_next", 0.5)
    result = table.update("s1", "a1", reward=1.0, next_state="s2", next_action="a_next")
    # td_error = 1.0 + 0.95 * 0.5 - 0.0 = 1.475
    assert result["td_error"] == pytest.approx(1.475, abs=1e-3)


def test_encode_decode_roundtrip() -> None:
    key = _encode("state:foo/bar", "action:baz")
    s, a = _decode(key)
    assert s == "state:foo/bar"
    assert a == "action:baz"
