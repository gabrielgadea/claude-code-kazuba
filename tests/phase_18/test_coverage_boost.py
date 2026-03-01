"""Additional tests to boost coverage for config, models, session_manager, and lib/rlm."""

from __future__ import annotations

from pathlib import Path

import pytest

from claude_code_kazuba.rlm import RLMFacade, RLMFacadeConfig
from claude_code_kazuba.data.modules.rlm.src.config import RLMConfig
from claude_code_kazuba.data.modules.rlm.src.models import Episode, LearningRecord, MemoryEntry, SessionMeta
from claude_code_kazuba.data.modules.rlm.src.session_manager import SessionManager

# ===========================================================================
# Config coverage
# ===========================================================================


def test_config_from_yaml_loads_defaults() -> None:
    """RLMConfig.from_yaml reads the bundled rlm.yaml correctly."""
    yaml_path = Path(__file__).parents[2] / "claude_code_kazuba/data/modules/rlm/config/rlm.yaml"
    cfg = RLMConfig.from_yaml(yaml_path)
    assert cfg.learning_rate == pytest.approx(0.1)
    assert cfg.discount_factor == pytest.approx(0.95)
    assert cfg.epsilon == pytest.approx(0.1)


def test_config_from_yaml_with_persist_path(tmp_path: Path) -> None:
    """from_yaml coerces string persist_path to Path."""
    yaml_content = f"persist_path: {tmp_path / 'q.json'}\n"
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)
    cfg = RLMConfig.from_yaml(yaml_file)
    assert cfg.persist_path is not None
    assert isinstance(cfg.persist_path, Path)


def test_config_persist_path_coercion() -> None:
    """String persist_path is coerced to Path via validator."""
    cfg = RLMConfig(persist_path="/tmp/test.json")
    assert isinstance(cfg.persist_path, Path)


def test_config_session_checkpoint_dir_coercion() -> None:
    """String session_checkpoint_dir is coerced to Path."""
    cfg = RLMConfig(session_checkpoint_dir="/tmp/sessions")
    assert isinstance(cfg.session_checkpoint_dir, Path)


def test_config_invalid_reward_clip_raises() -> None:
    """reward_clip_min >= reward_clip_max should raise."""
    with pytest.raises(ValueError, match="reward_clip_min"):
        RLMConfig(reward_clip_min=1.0, reward_clip_max=0.5)


def test_config_to_dict_with_paths(tmp_path: Path) -> None:
    """to_dict converts Path objects to strings."""
    cfg = RLMConfig(
        persist_path=tmp_path / "q.json",
        session_checkpoint_dir=tmp_path / "sessions",
    )
    data = cfg.to_dict()
    assert isinstance(data["persist_path"], str)
    assert isinstance(data["session_checkpoint_dir"], str)


def test_config_to_dict_null_paths() -> None:
    """to_dict handles None paths gracefully."""
    cfg = RLMConfig()
    data = cfg.to_dict()
    assert data["persist_path"] is None
    assert data["session_checkpoint_dir"] is None


def test_config_defaults_factory() -> None:
    """RLMConfig.defaults() returns a valid config."""
    cfg = RLMConfig.defaults()
    assert cfg.learning_rate == pytest.approx(0.1)


# ===========================================================================
# Models coverage
# ===========================================================================


def test_learning_record_invalid_reward_raises() -> None:
    """NaN reward should raise ValueError."""
    with pytest.raises(ValueError):
        LearningRecord(state="s", action="a", reward=float("nan"))


def test_learning_record_inf_reward_raises() -> None:
    """Infinite reward should raise ValueError."""
    with pytest.raises(ValueError):
        LearningRecord(state="s", action="a", reward=float("inf"))


def test_learning_record_from_dict() -> None:
    """from_dict reconstructs a LearningRecord."""
    rec = LearningRecord(state="s1", action="a1", reward=0.5)
    data = rec.to_dict()
    restored = LearningRecord.from_dict(data)
    assert restored.state == "s1"
    assert restored.reward == pytest.approx(0.5)


def test_memory_entry_from_dict_converts_tags() -> None:
    """from_dict should convert list tags to tuple."""
    data = {
        "id": "eid",
        "content": "test",
        "importance": 0.5,
        "tags": ["a", "b"],
        "created_at": 0.0,
        "accessed_at": 0.0,
        "access_count": 0,
    }
    entry = MemoryEntry.from_dict(data)
    assert isinstance(entry.tags, tuple)
    assert "a" in entry.tags


def test_episode_duration_when_running() -> None:
    """duration is 0.0 when episode is still running."""
    ep = Episode()
    assert ep.duration == 0.0


def test_episode_duration_when_closed() -> None:
    """duration is positive after closing."""
    import time

    ep = Episode()
    time.sleep(0.01)
    closed = ep.close()
    assert closed.duration > 0.0


def test_session_meta_duration_when_running() -> None:
    """SessionMeta.duration is 0.0 when still running."""
    meta = SessionMeta()
    assert meta.duration == 0.0


def test_session_meta_duration_when_closed() -> None:
    """SessionMeta.duration is positive after closing."""
    import time

    meta = SessionMeta()
    time.sleep(0.01)
    closed = meta.close()
    assert closed.duration > 0.0


# ===========================================================================
# SessionManager coverage
# ===========================================================================


def test_session_id_property_with_active_session() -> None:
    mgr = SessionManager()
    mgr.start("id-test")
    assert mgr.session_id == "id-test"
    mgr.end()


def test_session_id_property_without_session() -> None:
    mgr = SessionManager()
    assert mgr.session_id is None


def test_current_session_returns_meta() -> None:
    mgr = SessionManager()
    assert mgr.current_session() is None
    mgr.start("s1")
    assert mgr.current_session() is not None
    mgr.end()


def test_start_episode_no_session_raises() -> None:
    mgr = SessionManager()
    with pytest.raises(RuntimeError):
        mgr.start_episode()


def test_end_episode_no_session_raises() -> None:
    mgr = SessionManager()
    with pytest.raises(RuntimeError):
        mgr.end_episode("ghost")


def test_end_episode_unknown_id_raises() -> None:
    mgr = SessionManager()
    mgr.start("s1")
    with pytest.raises(KeyError):
        mgr.end_episode("nonexistent")
    mgr.end()


def test_get_episode_returns_none_for_unknown() -> None:
    mgr = SessionManager()
    mgr.start("s1")
    assert mgr.get_episode("ghost") is None
    mgr.end()


def test_all_episodes_returns_list() -> None:
    mgr = SessionManager()
    mgr.start("s1")
    ep1 = mgr.start_episode()
    mgr.end_episode(ep1)
    ep2 = mgr.start_episode()
    mgr.end_episode(ep2)
    episodes = mgr.all_episodes()
    assert len(episodes) == 2
    mgr.end()


def test_active_episode_id_property() -> None:
    mgr = SessionManager()
    mgr.start("s1")
    ep_id = mgr.start_episode()
    assert mgr.active_episode_id == ep_id
    mgr.end_episode(ep_id)
    assert mgr.active_episode_id is None
    mgr.end()


def test_record_step_unknown_episode_raises() -> None:
    mgr = SessionManager()
    mgr.start("s1")
    with pytest.raises(KeyError):
        mgr.record_step("ghost", state="s", action="a", reward=0.1)
    mgr.end()


def test_stats_no_session() -> None:
    mgr = SessionManager()
    stats = mgr.stats()
    assert stats["active"] is False


def test_end_with_open_episode_auto_closes() -> None:
    """end() auto-closes any open episode."""
    mgr = SessionManager()
    mgr.start("s1")
    mgr.start_episode()  # open but not closed
    # Should auto-close without raising
    meta = mgr.end()
    assert meta.ended_at is not None


# ===========================================================================
# lib/rlm.py coverage
# ===========================================================================


def test_facade_from_yaml() -> None:
    yaml_path = Path(__file__).parents[2] / "claude_code_kazuba/data/modules/rlm/config/rlm.yaml"
    cfg = RLMFacadeConfig.from_yaml(yaml_path)
    assert cfg.rlm.learning_rate == pytest.approx(0.1)


def test_facade_invalid_reward_component_skipped() -> None:
    """Invalid reward component dicts are skipped gracefully."""
    cfg = RLMFacadeConfig(
        reward_components=[
            {"metric_key": "valid", "weight": 1.0, "target": 1.0, "scale": 0.1},
            {"invalid_field": True},  # will fail RewardComponent(**data)
        ]
    )
    rlm = RLMFacade(config=cfg)
    # Only the valid component should be loaded
    assert len(rlm._reward.components) == 1


def test_facade_end_session_no_session() -> None:
    """end_session without start_session returns error dict."""
    rlm = RLMFacade()
    result = rlm.end_session()
    assert "error" in result


def test_facade_top_memories() -> None:
    rlm = RLMFacade()
    rlm.remember("A", importance=0.9)
    rlm.remember("B", importance=0.3)
    top = rlm.top_memories(1)
    assert len(top) == 1
    assert top[0].content == "A"


def test_facade_compute_reward_breakdown() -> None:

    rlm = RLMFacade()
    rlm.add_reward_component("acc", weight=1.0, target=1.0, scale=0.2)
    bd = rlm.compute_reward_breakdown({"acc": 0.8})
    assert "total" in bd
    assert "components" in bd


def test_facade_repr() -> None:
    rlm = RLMFacade()
    r = repr(rlm)
    assert "RLMFacade" in r


def test_facade_best_action_epsilon_greedy_explore() -> None:
    """With epsilon=1.0 and actions list, should always explore."""
    cfg = RLMFacadeConfig(rlm=RLMConfig(epsilon=1.0))
    rlm = RLMFacade(config=cfg)
    result = rlm.best_action("s1", actions=["a1", "a2"])
    assert result in ("a1", "a2")


def test_facade_best_action_explore_no_actions() -> None:
    """With epsilon=1.0 and no actions list, returns None during exploration."""
    cfg = RLMFacadeConfig(rlm=RLMConfig(epsilon=1.0))
    rlm = RLMFacade(config=cfg)
    result = rlm.best_action("unknown_state")
    assert result is None


def test_facade_record_step_without_session() -> None:
    """record_step works even without an active session."""
    rlm = RLMFacade()
    # No session started — should not raise, just skip session recording
    result = rlm.record_step("s1", "a1", 0.5)
    assert "new_q_value" in result
