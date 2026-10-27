"""Tests — Sprint 13: Continuous Improvement (self-assessment report, export, API).

Tmp DBs 100%: không đụng DB thật, không tự chạy pytest, không mạng.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.cognition.improvement_report import (
    build_improvement_report,
    export_report_markdown,
)


@pytest.fixture()
def ws(tmp_path):
    """Workspace giả lập với DB thật schema."""
    data = tmp_path / "data"
    data.mkdir()

    # tasks.db
    conn = sqlite3.connect(data / "tasks.db")
    conn.execute(
        "CREATE TABLE durable_tasks (task_id TEXT PRIMARY KEY, status TEXT, created_at_utc TEXT, updated_at_utc TEXT, completed_at_utc TEXT, error_message TEXT, checkpoint_data_json TEXT, result_payload_json TEXT, evidence_refs_json TEXT)"
    )
    for i, st in enumerate(["COMPLETED", "COMPLETED", "FAILED", "PENDING"]):
        conn.execute("INSERT INTO durable_tasks VALUES (?,?, '2026-10-27', '2026-10-27', NULL, '', '{}', '{}', '[]')", (f"t{i}", st))
    conn.commit(); conn.close()

    # governance.db
    conn = sqlite3.connect(data / "governance.db")
    conn.execute("CREATE TABLE approval_cards (card_id TEXT PRIMARY KEY, task_code TEXT, status TEXT, created_at_utc TEXT)")
    for i, st in enumerate(["APPROVED", "APPROVED", "REJECTED"]):
        conn.execute("INSERT INTO approval_cards VALUES (?,?,?, '2026-10-27')", (f"c{i}", f"TASK-{i}", st))
    conn.commit(); conn.close()

    # brain.db (lesson schema tối thiểu)
    conn = sqlite3.connect(data / "brain.db")
    conn.execute(
        "CREATE TABLE memories (id TEXT PRIMARY KEY, memory_type TEXT, content TEXT, source_ref TEXT, verification_status TEXT, confidence_score REAL, project_scope TEXT, tags_json TEXT, lifecycle_status TEXT, version INTEGER, superseded_by TEXT, created_at_utc TEXT, updated_at_utc TEXT, metadata_json TEXT)"
    )
    conn.execute(
        "INSERT INTO memories VALUES ('l1','EPISODIC','Bài học (thành công) — task t0','task:t0','UNVERIFIED',0.5,'experience','[\"sprint11_lesson\",\"completed\"]','quarantined',1,NULL,'2026-10-27','2026-10-27','{}')"
    )
    conn.execute(
        "INSERT INTO memories VALUES ('l2','EPISODIC','Bài học (thất bại) — task t2','task:t2','VERIFIED',1.0,'experience','[\"sprint11_lesson\",\"failed\",\"reviewed\"]','active',2,NULL,'2026-10-27','2026-10-27','{}')"
    )
    conn.execute("CREATE TABLE candidate_knowledge (id TEXT PRIMARY KEY, created_at_utc TEXT, statement TEXT, source_ref TEXT, rationale TEXT, status TEXT, decision_note TEXT)")
    conn.execute("CREATE TABLE semantic_memory (id TEXT PRIMARY KEY, created_at_utc TEXT, statement TEXT, source_ref TEXT, approved_by TEXT, regression_passed INTEGER)")
    conn.commit(); conn.close()

    # email_intake.db
    conn = sqlite3.connect(data / "email_intake.db")
    conn.execute("CREATE TABLE intake_emails (message_id TEXT PRIMARY KEY, sender TEXT, subject TEXT, body_preview TEXT, received_at_utc TEXT, category TEXT, related_task_id TEXT, source TEXT, synced_at_utc TEXT)")
    conn.execute("CREATE TABLE email_proposals (proposal_id TEXT PRIMARY KEY, message_id TEXT, subject TEXT, sender TEXT, goal TEXT, payload_json TEXT, status TEXT, linked_task_id TEXT, created_at_utc TEXT)")
    conn.execute("INSERT INTO intake_emails VALUES ('m1','a@b','s','p','2026','ACTION_REQUIRED','','mock','2026')")
    conn.execute("INSERT INTO email_proposals VALUES ('p1','m1','s','a@b','g','{}','TASK_CREATED','t0','2026')")
    conn.commit(); conn.close()

    # information_gaps.db — schema thật của Sprint 3/4: dùng OPEN status? Nếu schema khác → chưa xác minh là hành vi đúng. Tạo đúng bảng common:
    conn = sqlite3.connect(data / "information_gaps.db")
    conn.execute("CREATE TABLE information_gaps (gap_id TEXT PRIMARY KEY, group_code TEXT, question TEXT, status TEXT, created_at_utc TEXT, updated_at_utc TEXT, answer TEXT, answered_by TEXT)")
    conn.execute("INSERT INTO information_gaps VALUES ('g1','A','?','OPEN','2026','2026','','')")
    conn.commit(); conn.close()

    # báo cáo test gần nhất
    rep_dir = tmp_path / "bao cao xay dung he thong"
    rep_dir.mkdir()
    (rep_dir / "BAO_CAO_V3_SPRINT12_20261027.md").write_text("Full regression: 893 passed / 0 fail / 1 skipped", encoding="utf-8")

    return tmp_path


class TestBuildReport:
    def test_tasks_section_real_numbers(self, ws):
        r = build_improvement_report(ws)
        t = r["sections"]["tasks"]
        assert t["status"] == "Đã có và hoạt động"
        assert t["total"] == 4 and t["completed"] == 2 and t["failed"] == 1
        assert t["success_rate_pct"] == 66.7

    def test_approvals_section(self, ws):
        r = build_improvement_report(ws)
        a = r["sections"]["approvals"]
        assert a["cards_total"] == 3 and a["approved"] == 2 and a["rejected"] == 1
        assert a["decision_rate_pct"] == 33.3

    def test_experience_lessons(self, ws):
        r = build_improvement_report(ws)
        e = r["sections"]["experience"]
        assert e["lessons_total"] == 2 and e["lessons_confirmed"] == 1
        assert e["lessons_pending"] == 1

    def test_email_vmail_blocked_honest(self, ws):
        r = build_improvement_report(ws)
        e = r["sections"]["email_intelligence"]
        assert e["vmail_real"] == "Bị chặn"
        assert e["proposals_linked_task"] == 1

    def test_matrix_5_levels_only(self, ws):
        r = build_improvement_report(ws)
        valid = {"Đã có và hoạt động", "Có một phần", "Chưa có", "Chưa xác minh", "Bị chặn"}
        assert r["matrix"] and all(m["level"] in valid for m in r["matrix"])
        assert all(m["evidence"] for m in r["matrix"])

    def test_corrupt_db_unverified_not_zero(self, tmp_path):
        """DB hỏng → CHƯA XÁC MINH, không 0 giả (nguyên tắc workbench overview)."""
        data = tmp_path / "data"
        data.mkdir()
        (data / "tasks.db").write_bytes(b"khong phai sqlite")
        r = build_improvement_report(tmp_path)
        assert r["sections"]["tasks"]["status"] == "Chưa xác minh"

    def test_missing_db_unverified(self, tmp_path):
        r = build_improvement_report(tmp_path)
        assert r["sections"]["tasks"]["status"] == "Chưa xác minh"
        assert r["sections"]["approvals"]["status"] == "Chưa xác minh"

    def test_regression_from_report_file(self, ws):
        r = build_improvement_report(ws)
        t = r["sections"]["regression_tests"]
        assert t["status"] == "Đã có và hoạt động"
        assert "893 passed" in t["evidence"]

    def test_suggested_improvements_data_driven(self, ws):
        r = build_improvement_report(ws)
        joined = " ".join(r["suggested_improvements"])
        assert "1 bài học đang chờ" in joined          # lessons_pending = 1
        assert "BLOCKED" in joined                      # vmail
        assert "1 thông tin thiếu" in joined            # gaps


class TestExport:
    def test_export_writes_md(self, ws):
        r = build_improvement_report(ws)
        path = export_report_markdown(r, ws)
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "Ma trận năng lực" in text
        assert "893 passed" in text
        assert path.parent.name == "bao cao xay dung he thong"


class TestAPI:
    def _patch(self, monkeypatch):
        import quan_ai_brain.web.server as srv
        from quan_ai_brain.web.server import BrainAPIHandler

        for name in ("_handle_api_improvement_report", "_handle_api_improvement_export"):
            setattr(_FakeHandler, name, getattr(BrainAPIHandler, name))
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: Path("."), raising=False)

    def test_remote_403(self, monkeypatch):
        self._patch(monkeypatch)
        h = _FakeHandler()
        h.client_address = ("192.168.1.50", 1)
        h._handle_api_improvement_report("")
        assert _FakeHandler.error and _FakeHandler.error["code"] == 403

    def test_report_local_ok(self, monkeypatch, tmp_path):
        import quan_ai_brain.web.server as srv

        monkeypatch.setattr(srv, "_find_workspace_root", lambda: tmp_path, raising=False)
        from quan_ai_brain.web.server import BrainAPIHandler

        _FakeHandler._handle_api_improvement_report = BrainAPIHandler._handle_api_improvement_report
        _FakeHandler.sent = None
        _FakeHandler.error = None
        _FakeHandler()._handle_api_improvement_report("")
        assert _FakeHandler.sent and _FakeHandler.sent["success"] is True
        assert len(_FakeHandler.sent["report"]["matrix"]) >= 6


class _FakeHandler:
    sent = None
    error = None
    client_address = ("127.0.0.1", 1)

    @staticmethod
    def _send_json(payload, code=200):
        _FakeHandler.sent = payload
        _FakeHandler.error = None

    @staticmethod
    def _send_error_json(msg, code=400):
        _FakeHandler.error = {"error": msg, "code": code}
        _FakeHandler.sent = None
