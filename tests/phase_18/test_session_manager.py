"""Tests for modules/rlm/src/session_manager.py — SessionManager."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from claude_code_kazuba.data.modules.rlm.src.session_manager import SessionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_manager(with_checkpoint: bool = False) -> tuple[SessionManager, Path | None]:
    if with_checkpoint:
        tmpdir = tempfile.mkdtemp()
        ckpt_dir = Path(tmpdir)
        return SessionManager(checkpoint_dir=ckpt_dir), ckpt_dir
    return SessionManager(), None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_start_session_returns_id() -> None:
    mgr, _ = make_manager()
    sid = mgr.start("test-session")
    assert sid == "test-session"
    assert mgr.is_active


def test_start_auto_generates_id() -> None:
    mgr, _ = make_manager()
    sid = mgr.start()
    assert isinstance(sid, str)
    assert len(sid) > 0


def test_double_start_raises() -> None:
    mgr, _ = make_manager()
    mgr.start("first")
    with pytest.raises(RuntimeError):
        mgr.start("second")


def test_end_session_returns_meta() -> None:
    mgr, _ = make_manager()
    mgr.start("sess")
    meta = mgr.end()
    assert meta.id == "sess"
    assert meta.ended_at is not None
    assert not mgr.is_active


def test_end_without_start_raises() -> None:
    mgr, _ = make_manager()
    with pytest.raises(RuntimeError):
        mgr.end()


def test_start_episode_and_end() -> None:
    mgr, _ = make_manager()
    mgr.start("s1")
    ep_id = mgr.start_episode()
    assert isinstance(ep_id, str)
    episode = mgr.end_episode(ep_id)
    assert episode.is_complete


def test_record_step_creates_record() -> None:
    mgr, _ = make_manager()
    mgr.start("s1")
    ep_id = mgr.start_episode()
    rec = mgr.record_step(ep_id, state="s1", action="a1", reward=0.5)
    assert rec.state == "s1"
    assert rec.action == "a1"
    assert rec.reward == pytest.approx(0.5)


def test_record_to_closed_episode_raises() -> None:
    mgr, _ = make_manager()
    mgr.start("s1")
    ep_id = mgr.start_episode()
    mgr.end_episode(ep_id)
    with pytest.raises(RuntimeError):
        mgr.record_step(ep_id, state="s", action="a", reward=0.1)


def test_stats_returns_session_info() -> None:
    mgr, _ = make_manager()
    mgr.start("s1")
    ep_id = mgr.start_episode()
    mgr.record_step(ep_id, state="s", action="a", reward=1.0)
    mgr.end_episode(ep_id)
    stats = mgr.stats()
    assert stats["active"] is True
    assert stats["episode_count"] == 1
    assert stats["total_steps"] == 1


def test_checkpoint_saved_on_end() -> None:
    mgr, ckpt_dir = make_manager(with_checkpoint=True)
    assert ckpt_dir is not None
    mgr.start("chk-test")
    ep_id = mgr.start_episode()
    mgr.record_step(ep_id, state="s", action="a", reward=0.3)
    mgr.end_episode(ep_id)
    mgr.end()
    toon_files = list(ckpt_dir.glob("*.toon"))
    assert len(toon_files) >= 1


def test_load_checkpoint_reads_toon() -> None:
    mgr, ckpt_dir = make_manager(with_checkpoint=True)
    assert ckpt_dir is not None
    mgr.start("load-test")
    mgr.end()
    toon_files = list(ckpt_dir.glob("*.toon"))
    assert len(toon_files) >= 1
    data = mgr.load_checkpoint(toon_files[0])
    assert "session" in data
