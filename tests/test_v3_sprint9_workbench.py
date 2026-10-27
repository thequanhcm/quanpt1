"""Tests — Sprint 9: Workbench overview/tasks API, Email intake (mock), Experience retrieval.

Mock/tmppath 100%: không đụng DB thật, không đọc Vmail, không gửi email.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))


# ---------------------------------------------------------------------------
# (C) Email intake — connector mock, dedupe, phân loại, Vmail BLOCKED
# ---------------------------------------------------------------------------

from quan_ai_brain.integration.email_intake import (
    ConnectorStatus,
    EmailCategory,
    EmailIntakeStore,
    EmailMessage,
    MockEmailConnector,
    VmailConnector,
    classify_email,
    sync_intake,
)


class TestEmailIntake:
    def _store(self, tmp_path):
        return EmailIntakeStore(tmp_path / "email_intake.db")

    def test_vmail_blocked(self):
        """§IX: Vmail phải BLOCKED — không đọc hộp thư thật."""
        v = VmailConnector()
        assert v.status() == ConnectorStatus.BLOCKED
        assert v.fetch_recent() == []

    def test_sync_new_then_dedupe(self, tmp_path):
        """Cùng email không xử lý 2 lần (luật §X.9)."""
        store = self._store(tmp_path)
        r1 = sync_intake(MockEmailConnector(), store)
        assert r1.connector_status == ConnectorStatus.CONNECTED
        assert r1.fetched == 3
        assert r1.new == 3
        assert r1.duplicates == 0
        r2 = sync_intake(MockEmailConnector(), store)
        assert r2.fetched == 3
        assert r2.new == 0
        assert r2.duplicates == 3
        assert store.count() == 3  # không tăng

    def test_classify_categories(self, tmp_path):
        store = self._store(tmp_path)
        sync_intake(MockEmailConnector(), store)
        cats = {e["subject"]: e["category"] for e in store.list_emails()}
        assert cats["Yêu cầu báo cáo tuần nhóm AI"] == EmailCategory.ACTION_REQUIRED.value
        assert cats["Khuyến mãi nội bộ tháng 11"] == EmailCategory.NEWSLETTER.value
        assert cats["Thông báo bảo trì hệ thống M-Suite"] == EmailCategory.FYI.value

    def test_connector_disconnected_no_fake_read(self, tmp_path):
        """Connector lỗi → không giả vờ đã đọc (luật §X.10)."""
        store = self._store(tmp_path)
        conn = MockEmailConnector()
        conn.set_status(ConnectorStatus.DISCONNECTED)
        r = sync_intake(conn, store)
        assert r.fetched == 0
        assert r.new == 0
        assert r.connector_status == ConnectorStatus.DISCONNECTED
        assert store.count() == 0

    def test_source_is_mock(self, tmp_path):
        """Mọi email mock phải ghi nguồn="mock" — không tự nhận là mail thật."""
        store = self._store(tmp_path)
        sync_intake(MockEmailConnector(), store)
        for e in store.list_emails():
            assert e["source"] == "mock"

    def test_save_duplicate_returns_false(self, tmp_path):
        store = self._store(tmp_path)
        msg = EmailMessage(
            message_id="dup-1", sender="a@b.vn", subject="S", body_preview="x",
            received_at_utc="2026-10-27T00:00:00+00:00", source="mock",
        )
        assert store.save(msg, EmailCategory.FYI) is True
        assert store.save(msg, EmailCategory.FYI) is False  # trùng


# ---------------------------------------------------------------------------
# (C2) Email draft với metadata nhiệm vụ — vẫn DRAFT ONLY
# ---------------------------------------------------------------------------

from quan_ai_brain.tools.email_draft import create_draft


class TestEmailDraftSprint9:
    def test_draft_with_task_metadata(self, tmp_path):
        result = create_draft(
            to="a@viettel.com.vn", subject="Báo cáo", body="Nội dung",
            draft_dir=tmp_path, task_id="TASK-123",
            source_email_id="mock-001", reason="Trả lời yêu cầu báo cáo tuần",
        )
        import email as email_lib

        msg = email_lib.message_from_bytes(Path(result["path"]).read_bytes(), policy=email_lib.policy.default)
        assert msg["X-QAB-Task-Id"] == "TASK-123"
        assert msg["X-QAB-Source-Email-Id"] == "mock-001"
        assert "Trả lời yêu cầu" in msg["X-QAB-Draft-Reason"]
        assert result["created"] is True  # tạo file, KHÔNG gửi

    def test_draft_without_metadata_backward_compatible(self, tmp_path):
        """API cũ (không metadata) vẫn hoạt động — backward-compat §XI.23."""
        result = create_draft(
            to="a@viettel.com.vn", subject="S", body="B", draft_dir=tmp_path
        )
        assert result["created"] is True
        assert result["task_id"] == ""


# ---------------------------------------------------------------------------
# (D) Experience retrieval — confirmed vs candidates
# ---------------------------------------------------------------------------

from quan_ai_brain.memory.experience_retrieval import find_similar_experiences
from quan_ai_brain.memory.models import MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


class TestExperienceRetrieval:
    def _store(self, tmp_path):
        return MemoryStore(tmp_path / "memory.db")

    def test_confirmed_and_candidates_separated(self, tmp_path):
        store = self._store(tmp_path)
        # Kinh nghiệm đã xác nhận (OBSERVED = hệ thống quan sát thật)
        store.store_memory(
            content="Cách restart daemon an toàn: dùng watchdog start_daemon, cap 5 lần/giờ",
            memory_type=MemoryType.PROCEDURAL,
            verification_status=VerificationStatus.OBSERVED,
            project_scope="QUAN AI BRAIN",
        )
        # Bài học ứng viên CHƯA duyệt (CANDIDATE)
        store.store_memory(
            content="Quy trình backup DB nên chạy trước dedup lớn",
            memory_type=MemoryType.PROCEDURAL,
            verification_status=VerificationStatus.CANDIDATE,
            project_scope="QUAN AI BRAIN",
        )
        result = find_similar_experiences(store, "cần restart daemon và backup DB trong sprint này")
        assert len(result["confirmed"]) == 1
        assert "daemon" in result["confirmed"][0]["content"]
        assert result["confirmed"][0]["is_confirmed"] is True
        # CANDIDATE phải vào candidates, KHÔNG lẫn vào confirmed (luật §X.15)
        cand_contents = [c["content"] for c in result["candidates"]]
        assert any("backup" in c for c in cand_contents)
        assert result["candidates"][0]["is_confirmed"] is False

    def test_no_match_returns_empty(self, tmp_path):
        store = self._store(tmp_path)
        result = find_similar_experiences(store, "xyzabc123 không liên quan gì")
        assert result["confirmed"] == []
        assert result["candidates"] == []

    def test_superseded_excluded(self, tmp_path):
        """Kinh nghiệm lỗi thời (superseded) không được trả về là active (§VII.2)."""
        store = self._store(tmp_path)
        rec = store.store_memory(
            content="Deploy bằng cách copy tay DLL",
            memory_type=MemoryType.PROCEDURAL,
            verification_status=VerificationStatus.VERIFIED,
        )
        store.supersede_memory(rec.id, "Deploy bằng pip install -e .")
        result = find_similar_experiences(store, "deploy DLL bằng pip")
        contents = [c["content"] for c in result["confirmed"]]
        assert not any("copy tay" in c for c in contents)


# ---------------------------------------------------------------------------
# (A/B) Workbench API handlers — overview fail-honest + tasks list
# ---------------------------------------------------------------------------

def _server_mod():
    sys.path.insert(0, str(WORKSPACE / "src"))
    import quan_ai_brain.web.server as srv

    return srv


class _FakeHandler:
    sent = None
    error = None

    def _send_json(self, payload, code=200):
        type(self).sent = payload
        type(self).code = code

    def _send_error_json(self, msg, code=400):
        type(self).error = {"error": msg, "code": code}


class TestWorkbenchAPI:
    def _make(self, client="127.0.0.1"):
        srv = _server_mod()
        from quan_ai_brain.web.server import BrainAPIHandler

        # Gắn method THẬT từ BrainAPIHandler vào fake handler
        for name in (
            "_handle_api_workbench_overview",
            "_handle_api_workbench_tasks",
            "_handle_api_email_intake_sync",
            "_handle_api_email_intake_list",
        ):
            setattr(_FakeHandler, name, getattr(BrainAPIHandler, name))
        h = _FakeHandler()
        h.client_address = (client, 12345)
        return h, srv

    def test_overview_all_blocks_present(self, tmp_path, monkeypatch):
        """Overview trả đủ các khối; mỗi khối OK hoặc CHƯA XÁC MINH — không cụt."""
        h, srv = self._make()
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: tmp_path, raising=False)
        # Tạo DB tối thiểu để khối tasks OK
        from quan_ai_brain.orchestration.models import AutonomyLevel
        from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

        reg = DurableTaskRegistry(tmp_path / "data" / "tasks.db", workspace=str(tmp_path))
        reg.register_task(
            goal="Nhiệm vụ kiểm thử workbench",
            risk_level="R2",
            autonomy_level=AutonomyLevel.LEVEL_A,
            acceptance_criteria=["x"],
            approved_scope=["read-only"],
        )
        h._handle_api_workbench_overview()
        assert h.sent and h.sent["success"] is True
        assert h.sent["tasks"]["status"] == "OK"
        assert h.sent["tasks"]["total"] == 1
        # Các khối khác tồn tại (dù CHƯA XÁC MINH hay OK) — không bị cụt
        for key in ("information_gaps", "approvals", "todos"):
            assert key in h.sent
            assert h.sent[key].get("status") in ("OK", "CHƯA XÁC MINH")
        # services là map tên→trạng thái (không có khối "status")
        assert isinstance(h.sent["services"], dict)
        assert all(v in ("CONNECTED", "DISCONNECTED") for v in h.sent["services"].values())

    def test_overview_corrupt_db_is_honest(self, tmp_path, monkeypatch):
        """DB hỏng → CHƯA XÁC MINH, không điền 0 (luật §X.2)."""
        h, srv = self._make()
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: tmp_path, raising=False)
        (tmp_path / "data").mkdir(exist_ok=True)
        (tmp_path / "data" / "tasks.db").write_bytes(b"khong phai sqlite")
        h._handle_api_workbench_overview()
        assert h.sent["tasks"]["status"] == "CHƯA XÁC MINH"
        assert "error" in h.sent["tasks"]

    def test_tasks_list_from_registry(self, tmp_path, monkeypatch):
        h, srv = self._make()
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: tmp_path, raising=False)
        from quan_ai_brain.orchestration.models import AutonomyLevel
        from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

        reg = DurableTaskRegistry(tmp_path / "data" / "tasks.db", workspace=str(tmp_path))
        reg.register_task(
            goal="Task lọc theo trạng thái",
            risk_level="R2",
            autonomy_level=AutonomyLevel.LEVEL_A,
            acceptance_criteria=["x"],
            approved_scope=["read-only"],
        )

        class Q(dict):
            def get(self, k, d=None):
                return super().get(k, d)

        q = Q({"limit": ["10"]})
        h._handle_api_workbench_tasks(q)
        assert h.sent["success"] is True
        assert h.sent["count"] == 1
        assert h.sent["tasks"][0]["status"] in ("PENDING", "IN_PROGRESS", "WAITING_APPROVAL")

    def test_email_intake_sync_localhost_only(self, tmp_path, monkeypatch):
        h, srv = self._make(client="192.168.1.50")
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: tmp_path, raising=False)
        h._handle_api_email_intake_sync({})
        assert h.error and h.error["code"] == 403

    def test_email_intake_sync_runs_mock(self, tmp_path, monkeypatch):
        """Sync qua API thật trả result với nguồn mock + Vmail BLOCKED."""
        h, srv = self._make()
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: tmp_path, raising=False)
        h._handle_api_email_intake_sync({})
        assert h.sent and h.sent["success"] is True
        assert h.sent["vmail_status"] == "BLOCKED"
        assert h.sent["result"]["new"] == 3
        assert all(e["source"] == "mock" for e in h.sent["emails"])


# ---------------------------------------------------------------------------
# Regression nhanh: các route Sprint 8 vẫn tồn tại (backward-compat)
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    def test_sprint8_routes_still_bound(self):
        srv = _server_mod()
        from quan_ai_brain.web.server import BrainAPIHandler

        for m in (
            "_handle_api_todos_list",
            "_handle_api_todos_add",
            "_handle_api_todos_done",
            "_handle_api_approvals_list",
            "_handle_api_approvals_decide",
        ):
            assert hasattr(BrainAPIHandler, m), f"missing Sprint 8 route handler: {m}"

    def test_sprint9_routes_bound(self):
        from quan_ai_brain.web.server import BrainAPIHandler

        for m in (
            "_handle_api_workbench_overview",
            "_handle_api_workbench_tasks",
            "_handle_api_email_intake_sync",
            "_handle_api_email_intake_list",
        ):
            assert hasattr(BrainAPIHandler, m), f"missing Sprint 9 route handler: {m}"
