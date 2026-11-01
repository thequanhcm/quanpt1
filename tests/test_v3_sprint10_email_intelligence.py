"""Tests — Sprint 10: Email Intelligence (proposal builder, candidate task, API).

Mock/tmppath 100%: không Vmail thật, không gửi email, không đụng DB thật.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.integration.email_intake import (
    ConnectorStatus,
    EmailCategory,
    EmailIntakeStore,
    EmailMessage,
    MockEmailConnector,
    sync_intake,
)
from quan_ai_brain.integration.email_intelligence import (
    ProposalStore,
    build_proposal,
    generate_proposals_for_intake,
)
from quan_ai_brain.memory.models import MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


def _action_msg() -> EmailMessage:
    return EmailMessage(
        message_id="mock-001",
        sender="trinhvien@viettel.com.vn",
        subject="Yêu cầu báo cáo tuần nhóm AI",
        body_preview="Chào Quân, vui lòng xử lý và gửi báo cáo tuần trước 17h thứ Sáu.",
        received_at_utc="2026-10-27T00:00:00+00:00",
        source="mock",
        category=EmailCategory.ACTION_REQUIRED,
    )


def _fyi_msg() -> EmailMessage:
    return EmailMessage(
        message_id="mock-003",
        sender="hoidap@viettel.com.vn",
        subject="Thông báo bảo trì",
        body_preview="Hệ thống bảo trì 22:00. Thông báo FYI.",
        received_at_utc="2026-10-27T00:00:00+00:00",
        source="mock",
        category=EmailCategory.FYI,
    )


# ---------------------------------------------------------------------------
# (a) Proposal builder
# ---------------------------------------------------------------------------

class TestProposalBuilder:
    def test_action_required_gets_full_proposal(self, tmp_path):
        store = MemoryStore(tmp_path / "memory.db")
        p = build_proposal(_action_msg(), store)
        assert p is not None
        d = p.to_dict()
        # Đủ 11 trường §VI.3 — không cụt
        for key in (
            "goal", "basis", "conclusion", "assumptions", "recommended_action",
            "alternatives", "risks", "action_scope", "success_criteria",
            "rollback", "owner_decision_needed",
        ):
            assert d[key], f"thiếu trường {key}"
        # Giả định phải ghi rõ nguồn mock
        assert any("MOCK" in a or "mock" in a for a in d["assumptions"])

    def test_fyi_returns_none(self, tmp_path):
        """Email FYI không tạo đề xuất (không cưỡng bách)."""
        store = MemoryStore(tmp_path / "memory.db")
        assert build_proposal(_fyi_msg(), store) is None

    def test_confirmed_experience_in_basis_not_candidates(self, tmp_path):
        store = MemoryStore(tmp_path / "memory.db")
        store.store_memory(
            content="Quy trình gửi báo cáo tuần: tổng hợp số liệu trước 15h",
            memory_type=MemoryType.PROCEDURAL,
            verification_status=VerificationStatus.OBSERVED,
        )
        p = build_proposal(_action_msg(), store)
        assert any("báo cáo tuần" in b for b in p.basis)
        assert p.experience_confirmed  # có confirmed

    def test_candidate_experience_separated(self, tmp_path):
        """Kinh nghiệm chưa duyệt nằm ở candidates — không lẫn căn cứ mạnh."""
        store = MemoryStore(tmp_path / "memory.db")
        store.store_memory(
            content="Mẹo soạn báo cáo nhanh bằng template",
            memory_type=MemoryType.PROCEDURAL,
            verification_status=VerificationStatus.CANDIDATE,
        )
        p = build_proposal(_action_msg(), store)
        assert p.experience_candidates  # có candidates
        cand_contents = [c["content"] for c in p.experience_candidates]
        assert any("template" in c for c in cand_contents)


# ---------------------------------------------------------------------------
# Proposal store — idempotent theo message_id
# ---------------------------------------------------------------------------

class TestProposalStore:
    def test_save_idempotent_per_message(self, tmp_path):
        store = ProposalStore(tmp_path / "email_intake.db")
        store2 = ProposalStore(tmp_path / "email_intake.db")
        p1 = build_proposal(_action_msg(), MemoryStore(":memory:"))
        p2 = build_proposal(_action_msg(), MemoryStore(":memory:"))
        assert store.save(p1) is True
        # Cùng message_id lần 2 → False (không trùng — luật §X master prompt)
        assert store2.save(p2) is False
        assert len(store.list_proposals()) == 1

    def test_link_task_once(self, tmp_path):
        store = ProposalStore(tmp_path / "email_intake.db")
        p = build_proposal(_action_msg(), MemoryStore(":memory:"))
        store.save(p)
        assert store.link_task(p.proposal_id, "task_abc") is True
        rec = store.get(p.proposal_id)
        assert rec["linked_task_id"] == "task_abc"
        assert rec["status"] == "TASK_CREATED"
        # Gắn task khác → False (không đổi liên kết)
        assert store.link_task(p.proposal_id, "task_other") is False

    def test_get_missing_returns_none(self, tmp_path):
        store = ProposalStore(tmp_path / "email_intake.db")
        assert store.get("prop_khongco") is None


# ---------------------------------------------------------------------------
# generate_proposals_for_intake — end-to-end trên tmp DB
# ---------------------------------------------------------------------------

class TestGenerateProposals:
    def test_generate_once_and_idempotent(self, tmp_path):
        db = tmp_path / "email_intake.db"
        # Sync mock intake trước (3 email: 1 ACTION_REQUIRED, 1 NEWSLETTER, 1 FYI)
        sync_intake(MockEmailConnector(), EmailIntakeStore(db))
        mem = MemoryStore(tmp_path / "memory.db")
        r1 = generate_proposals_for_intake(db, mem)
        assert r1["created"] == 1          # chỉ email ACTION_REQUIRED
        assert r1["skipped_category"] == 2  # NEWSLETTER + FYI bị bỏ qua
        r2 = generate_proposals_for_intake(db, mem)
        assert r2["created"] == 0           # lặp lại không tạo thêm
        assert r2["already_existed"] == 1

    def test_empty_intake_no_proposals(self, tmp_path):
        db = tmp_path / "email_intake.db"
        r = generate_proposals_for_intake(db, MemoryStore(tmp_path / "memory.db"))
        assert r["created"] == 0


# ---------------------------------------------------------------------------
# (b/c) API handlers
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


class TestEmailIntelligenceAPI:
    def _make(self, tmp_path, monkeypatch, client="127.0.0.1"):
        srv = _server_mod()
        from quan_ai_brain.web.server import BrainAPIHandler

        for name in ("_handle_api_email_proposals_list", "_handle_api_email_task_create"):
            setattr(_FakeHandler, name, getattr(BrainAPIHandler, name))
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: tmp_path, raising=False)
        h = _FakeHandler()
        h.client_address = (client, 1)
        return h

    def test_proposals_remote_403(self, tmp_path, monkeypatch):
        h = self._make(tmp_path, monkeypatch, client="192.168.1.50")

        class Q(dict):
            pass

        h._handle_api_email_proposals_list(Q())
        assert h.error and h.error["code"] == 403

    def test_proposals_list_with_generated(self, tmp_path, monkeypatch):
        h = self._make(tmp_path, monkeypatch)
        # Chuẩn bị intake + sync mock
        sync_intake(MockEmailConnector(), EmailIntakeStore(tmp_path / "data" / "email_intake.db"))

        class Q(dict):
            pass

        h._handle_api_email_proposals_list(Q())
        assert h.sent and h.sent["success"] is True
        assert h.sent["vmail_status"] == "BLOCKED"
        assert len(h.sent["proposals"]) == 1
        prop = h.sent["proposals"][0]
        assert prop["payload"]["goal"]
        assert any("MOCK" in a or "mock" in a for a in prop["payload"]["assumptions"])

    def test_task_create_idempotent(self, tmp_path, monkeypatch):
        """Tạo task 2 lần cùng email → cùng task_id, lần 2 created=False."""
        h = self._make(tmp_path, monkeypatch)
        sync_intake(MockEmailConnector(), EmailIntakeStore(tmp_path / "data" / "email_intake.db"))

        class Q(dict):
            pass

        h._handle_api_email_proposals_list(Q())
        pid = h.sent["proposals"][0]["proposal_id"]

        type(h).sent = None
        type(h).error = None
        h._handle_api_email_task_create({"proposal_id": pid})
        assert h.sent and h.sent["success"] is True and h.sent["created"] is True, (
            f"sent={type(h).sent!r} error={type(h).error!r}"
        )
        task_id_1 = h.sent["task_id"]
        assert h.sent["status"] == "PENDING"
        assert h.sent["autonomy"] == "LEVEL_A"

        # Lần 2 — idempotent
        type(h).sent = None
        type(h).error = None
        h._handle_api_email_task_create({"proposal_id": pid})
        assert h.sent["created"] is False
        assert h.sent["task_id"] == task_id_1  # cùng task — không trùng

    def test_task_create_unknown_404(self, tmp_path, monkeypatch):
        h = self._make(tmp_path, monkeypatch)
        h._handle_api_email_task_create({"proposal_id": "prop_khongco"})
        assert h.error and h.error["code"] == 404

    def test_task_create_missing_param_400(self, tmp_path, monkeypatch):
        h = self._make(tmp_path, monkeypatch)
        h._handle_api_email_task_create({})
        assert h.error and h.error["code"] == 400

    def test_task_pending_never_executes(self, tmp_path, monkeypatch):
        """Task tạo ra PENDING + LEVEL_A — không có đường thực thi tự động."""
        h = self._make(tmp_path, monkeypatch)
        sync_intake(MockEmailConnector(), EmailIntakeStore(tmp_path / "data" / "email_intake.db"))

        class Q(dict):
            pass

        h._handle_api_email_proposals_list(Q())
        pid = h.sent["proposals"][0]["proposal_id"]
        type(h).sent = None
        type(h).error = None
        h._handle_api_email_task_create({"proposal_id": pid})
        # Kiểm tra trực tiếp trong tasks.db
        from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry, TaskStatus

        reg = DurableTaskRegistry(tmp_path / "data" / "tasks.db", workspace=str(tmp_path))
        task = reg.get_task(h.sent["task_id"])
        assert task.status == TaskStatus.PENDING
        assert task.autonomy_level.value == "LEVEL_A"
