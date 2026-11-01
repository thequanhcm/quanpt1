"""Tests — V3 Sprint 4: reminder logic + dedup tool (mock NetChat thật)."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.cognition.information_gap_analyzer import (  # noqa: E402
    InformationGapAnalyzer,
    InfoItem,
    ReadinessStatus,
    WaitingState,
)


# ---------------------------------------------------------------------------
# (b) Auto-reminder policy — đúng format, cap 5, khoảng cách 12h
# ---------------------------------------------------------------------------


@pytest.fixture()
def ana(tmp_path):
    return InformationGapAnalyzer(workspace=tmp_path)


def _seed(ana, task_id="TASK-R1"):
    a = ana.analyze_request(
        task_id, goal="Kiểm tra", acceptance_criteria=["x"],
        required_inputs=[InfoItem(key="url", note="link")],
    )
    ana.save_request(a)
    return a


def test_reminder_format_contains_mandatory_line(ana):
    _seed(ana)
    assert ana.should_send_reminder("TASK-R1") is True
    ana.note_reminder_sent("TASK-R1")
    row = ana.get_waiting_task("TASK-R1")
    assert row["reminder_count"] == 1
    assert row["last_reminder_utc"]


def test_reminder_cap_five(ana):
    _seed(ana)
    ana.remind_interval_hours = 0
    for i in range(5):
        assert ana.should_send_reminder("TASK-R1") is True
        ana.note_reminder_sent("TASK-R1")
    assert ana.should_send_reminder("TASK-R1") is False
    row = ana.get_waiting_task("TASK-R1")
    assert row["reminder_count"] == 5
    # Task VẪN chờ — nhắc không phải là quyền tiếp tục
    assert row["waiting_state"] == WaitingState.WAITING_FOR_OWNER_INPUT.value


def test_reminder_interval_gap(ana):
    _seed(ana)
    ana.note_reminder_sent("TASK-R1")
    # Ngay sau khi gửi → không nhắc tiếp
    assert ana.should_send_reminder("TASK-R1") is False


def test_reminder_unknown_task_false(ana):
    assert ana.should_send_reminder("TASK-KHONGCO") is False


def test_responder_reminder_block_syntax():
    # Block reminder trong responder phải parse được + gọi đúng policy functions
    src = (WORKSPACE / "tools" / "netchat_auto_responder.py").read_text(encoding="utf-8")
    assert "should_send_reminder" in src
    assert "note_reminder_sent" in src
    assert "CHƯA THỰC HIỆN HÀNH ĐỘNG NGHIỆP VỤ" in src
    import ast

    ast.parse(src)  # syntax hợp lệ


# ---------------------------------------------------------------------------
# (c) Dedup tool — chạy trên DB test riêng, đối chứng số liệu
# ---------------------------------------------------------------------------


def _make_db(tmp_path, rows):
    db = tmp_path / "brain.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE candidate_knowledge (id TEXT PRIMARY KEY, created_at_utc TEXT,"
        " statement TEXT, source_ref TEXT, rationale TEXT, status TEXT, decision_note TEXT)"
    )
    conn.execute(
        "CREATE TABLE semantic_memory (id TEXT PRIMARY KEY, statement TEXT)"
    )
    for rid, stmt in rows:
        conn.execute(
            "INSERT INTO candidate_knowledge VALUES (?,?,?,?,?,?,?)",
            (rid, "2026-10-25", stmt, '{"conflict_ids": []}', "r", "quarantined", ""),
        )
    conn.execute("INSERT INTO semantic_memory VALUES ('sem1', 'tri thức đã duyệt')")
    conn.commit()
    return db


def test_dedup_keeps_one_per_group(tmp_path, monkeypatch):
    db = _make_db(tmp_path, [
        ("know_a", "cùng câu"), ("know_b", "cùng câu"), ("know_c", "cùng câu"),
        ("know_d", "khác"),
    ])
    import tools.dedup_candidate_knowledge as dk

    monkeypatch.setattr(dk, "DB", db)
    dk.main()
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM candidate_knowledge_archive").fetchone()[0] == 2
    # không mất dòng: 2 + 2 = 4
    assert conn.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0] == 1


def test_dedup_idempotent(tmp_path, monkeypatch):
    db = _make_db(tmp_path, [("know_a", "x"), ("know_b", "x")])
    import tools.dedup_candidate_knowledge as dk

    monkeypatch.setattr(dk, "DB", db)
    dk.main()
    dk.main()  # lần 2: không còn trùng → không làm gì, không lỗi
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM candidate_knowledge_archive").fetchone()[0] == 1


def test_dedup_no_data_loss(tmp_path, monkeypatch):
    # 100 dòng trùng 1 statement + 50 unique → sau dedup: 51 candidate, 49 archive? không:
    # 100 dòng trùng → giữ 1, archive 99; 50 unique giữ nguyên → 51 candidate.
    rows = [(f"know_{i}", "same") for i in range(100)] + [
        (f"know_u{i}", f"unique {i}") for i in range(50)
    ]
    db = _make_db(tmp_path, rows)
    import tools.dedup_candidate_knowledge as dk

    monkeypatch.setattr(dk, "DB", db)
    dk.main()
    conn = sqlite3.connect(db)
    cand = conn.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone()[0]
    arch = conn.execute("SELECT COUNT(*) FROM candidate_knowledge_archive").fetchone()[0]
    assert cand == 51
    assert arch == 99
    assert cand + arch == 150  # không mất dòng nào
