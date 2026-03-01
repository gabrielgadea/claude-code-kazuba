"""Tests for lib/rlm.py — RLMFacade."""

from __future__ import annotations

import tempfile
from pathlib import Path

from lib.rlm import RLMFacade, RLMFacadeConfig
from modules.rlm.src.config import RLMConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_facade(**kwargs: object) -> RLMFacade:
    return RLMFacade(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_facade_creates_without_config() -> None:
    rlm = make_facade()
    assert rlm is not None
    assert not rlm.is_session_active


def test_start_and_end_session() -> None:
    rlm = make_facade()
    sid = rlm.start_session("sess-1")
    assert sid == "sess-1"
    assert rlm.is_session_active
    summary = rlm.end_session()
    assert isinstance(summary, dict)
    assert not rlm.is_session_active


def test_record_step_updates_q_table() -> None:
    rlm = make_facade()
    rlm.start_session()
    result = rlm.record_step(state="s1", action="a1", reward=1.0)
    assert "td_error" in result
    assert "new_q_value" in result
    assert result["new_q_value"] > 0.0
    rlm.end_session()


def test_record_step_with_metrics() -> None:
    cfg = RLMFacadeConfig(
        rlm=RLMConfig(epsilon=0.0),
        reward_components=[
            {"metric_key": "accuracy", "weight": 1.0, "target": 1.0, "scale": 0.2}
        ],
    )
    rlm = RLMFacade(config=cfg)
    rlm.start_session()
    result = rlm.record_step(
        state="s1", action="a1", reward=0.0, metrics={"accuracy": 1.0}
    )
    assert result["effective_reward"] > 0.0
    rlm.end_session()


def test_best_action_after_learning() -> None:
    cfg = RLMFacadeConfig(rlm=RLMConfig(epsilon=0.0))
    rlm = RLMFacade(config=cfg)
    rlm.start_session()
    # Teach that (s1, a1) is best
    for _ in range(5):
        rlm.record_step(state="s1", action="a1", reward=1.0)
    rlm.record_step(state="s1", action="a2", reward=-1.0)
    rlm.end_session()

    best = rlm.best_action("s1")
    assert best == "a1"


def test_remember_and_recall() -> None:
    rlm = make_facade()
    eid = rlm.remember("Python snippet", importance=0.8, tags=["python"])
    entry = rlm.recall(eid)
    assert entry is not None
    assert entry.content == "Python snippet"
    assert "python" in entry.tags


def test_recall_by_tag() -> None:
    rlm = make_facade()
    rlm.remember("Rust code", tags=["rust"])
    rlm.remember("More Rust", tags=["rust"])
    rlm.remember("Python code", tags=["python"])
    results = rlm.recall_by_tag("rust")
    assert len(results) == 2


def test_forget_removes_entry() -> None:
    rlm = make_facade()
    eid = rlm.remember("temp entry")
    removed = rlm.forget(eid)
    assert removed is True
    assert rlm.recall(eid) is None


def test_compute_reward_from_metrics() -> None:
    rlm = make_facade()
    rlm.add_reward_component("speed", weight=1.0, target=100.0, scale=10.0)
    reward = rlm.compute_reward({"speed": 100.0})
    assert reward > 0.0


def test_stats_returns_comprehensive_dict() -> None:
    rlm = make_facade()
    rlm.start_session()
    rlm.record_step("s1", "a1", 0.5)
    rlm.remember("fact")
    stats = rlm.stats()
    assert "q_table_size" in stats
    assert "memory_size" in stats
    assert "session_stats" in stats
    rlm.end_session()


def test_save_and_load_q_table() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "q.json"
        rlm = make_facade()
        rlm.start_session()
        rlm.record_step("s1", "a1", 1.0)
        rlm.end_session()
        saved = rlm.save_q_table(path)
        assert saved == path
        assert path.exists()

        rlm2 = make_facade()
        rlm2.load_q_table(path)
        assert rlm2.get_q_value("s1", "a1") > 0.0
