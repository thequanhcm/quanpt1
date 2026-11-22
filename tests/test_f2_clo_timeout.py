# -*- coding: utf-8 -*-
"""Test F2 — enforce_stall_timeout (owner directive 22/11: timeout 48h → COMPLETED + lessons queue).

Mock 100% tmp_path — không đụng DB thật, không network.
"""
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quan_ai_brain.cognition.self_study import enforce_stall_timeout  # noqa: E402


def _make_ws(tmp_path, hours_running, clo_enabled=True):
    """Tạo workspace giả: brain.db episodes + learning_checkpoints.db session RUNNING."""
    (tmp_path / "data").mkdir(exist_ok=True)
    con = sqlite3.connect(tmp_path / "data" / "brain.db")
    con.execute("CREATE TABLE episodes(id TEXT, created_at_utc TEXT, kind TEXT, "
                "summary TEXT, source_ref TEXT, status TEXT, metadata_json TEXT)")
    con.commit()
    con.close()
    con = sqlite3.connect(tmp_path / "data" / "learning_checkpoints.db")
    con.execute("""CREATE TABLE learning_sessions (
        session_id TEXT PRIMARY KEY, cycle_number INTEGER UNIQUE NOT NULL,
        started_at TEXT NOT NULL, ended_at TEXT, status TEXT,
        learning_objectives TEXT NOT NULL, source_manifest TEXT NOT NULL,
        tasks_completed TEXT NOT NULL, tasks_failed TEXT NOT NULL,
        evidence_refs TEXT NOT NULL, knowledge_candidates TEXT NOT NULL,
        evaluation_result TEXT NOT NULL, unresolved_questions TEXT NOT NULL,
        resource_usage TEXT NOT NULL, checkpoint_ref TEXT,
        next_session_plan TEXT NOT NULL, stop_or_pause_reason TEXT)""")
    con.execute("CREATE TABLE learning_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    con.execute("INSERT INTO learning_state VALUES ('CLO_ENABLED', ?)",
                ('true' if clo_enabled else 'false',))
    con.execute("INSERT INTO learning_state VALUES ('STOP_FLAG', 'false')")
    old = (datetime.now(timezone.utc) - timedelta(hours=hours_running)).isoformat()
    con.execute("INSERT INTO learning_sessions VALUES ('sess-a', 1, ?, NULL, 'RUNNING', "
                "'[]','{}','[]','[]','[]','[]','{}','[]','{}',NULL,'{}',NULL)", (old,))
    con.commit()
    con.close()


def test_session_over_48h_completes_and_queues_lesson(tmp_path):
    _make_ws(tmp_path, hours_running=75)
    rep = enforce_stall_timeout(tmp_path)
    assert rep["triggered"] is True
    assert rep["errors"] == []
    assert rep["lesson_episode_id"] is not None
    con = sqlite3.connect(tmp_path / "data" / "learning_checkpoints.db")
    rows = con.execute("SELECT cycle_number, status FROM learning_sessions "
                       "ORDER BY cycle_number").fetchall()
    con.close()
    by_cycle = dict(rows)
    assert by_cycle[1] == "HANDOFF"  # kết thúc sạch qua state machine chuẩn
    assert by_cycle[2] == "RUNNING"  # session mới đẻ qua engine (CLO_ENABLED=true)
    con = sqlite3.connect(tmp_path / "data" / "brain.db")
    lesson = con.execute("SELECT kind, status, summary FROM episodes").fetchone()
    con.close()
    assert lesson[0] == "experience_lesson"  # lessons queue
    assert "timeout" in lesson[2]


def test_session_under_48h_noop(tmp_path):
    _make_ws(tmp_path, hours_running=30)
    rep = enforce_stall_timeout(tmp_path)
    assert rep["triggered"] is False
    assert "chưa đạt ngưỡng" in rep["note"]
    con = sqlite3.connect(tmp_path / "data" / "learning_checkpoints.db")
    st = con.execute("SELECT status FROM learning_sessions WHERE cycle_number=1").fetchone()[0]
    con.close()
    assert st == "RUNNING"  # không đụng


def test_idempotent_second_run_no_new_lesson(tmp_path):
    _make_ws(tmp_path, hours_running=75)
    rep1 = enforce_stall_timeout(tmp_path)
    rep2 = enforce_stall_timeout(tmp_path)
    assert rep1["triggered"] is True
    assert rep2["triggered"] is False  # session cũ đã HANDOFF — no-op
    con = sqlite3.connect(tmp_path / "data" / "brain.db")
    n = con.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    con.close()
    assert n == 1  # chỉ 1 lesson, không trùng


def test_no_session_noop(tmp_path):
    _make_ws(tmp_path, hours_running=75)
    con = sqlite3.connect(tmp_path / "data" / "learning_checkpoints.db")
    con.execute("DELETE FROM learning_sessions")
    con.commit()
    con.close()
    rep = enforce_stall_timeout(tmp_path)
    assert rep["triggered"] is False
    assert "không có session" in rep["note"]


def test_clo_disabled_no_next_session(tmp_path):
    _make_ws(tmp_path, hours_running=75, clo_enabled=False)
    rep = enforce_stall_timeout(tmp_path)
    assert rep["triggered"] is True
    con = sqlite3.connect(tmp_path / "data" / "learning_checkpoints.db")
    rows = con.execute("SELECT cycle_number, status FROM learning_sessions").fetchall()
    con.close()
    assert dict(rows) == {1: "HANDOFF"}  # không đẻ session mới khi CLO disabled
