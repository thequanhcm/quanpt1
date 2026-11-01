"""Tests — Sprint 11: Experience Memory (consolidation, promote, API, hook).

Mock/tmppath 100%: không đụng brain.db thật, không gọi server thật.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.memory.experience_consolidation import (
    extract_candidate_lesson,
    list_lessons,
    promote_lesson,
)
from quan_ai_brain.memory.experience_retrieval import find_similar_experiences
from quan_ai_brain.memory.models import LifecycleStatus, MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


@pytest.fixture()
def store(tmp_path):
    return MemoryStore(tmp_path / "memory.db")


# ---------------------------------------------------------------------------
# (a) extract_candidate_lesson
# ---------------------------------------------------------------------------

class TestExtractCandidateLesson:
    def test_completed_creates_candidate(self, store):
        r = extract_candidate_lesson(store, "task_001", "backup DB mỗi tuần", "COMPLETED", result_summary="Đã backup 4 DB")
        assert r.created is True
        rec = store.get_memory(r.lesson["id"])
        assert rec.memory_type == MemoryType.EPISODIC.value
        assert rec.verification_status == VerificationStatus.UNVERIFIED.value
        assert rec.lifecycle_status == LifecycleStatus.QUARANTINED.value
        assert "thành công" in rec.content

    def test_failed_creates_candidate(self, store):
        r = extract_candidate_lesson(store, "task_002", "sync email", "FAILED", result_summary="SSO lỗi")
        assert r.created is True
        assert "thất bại" in r.lesson["content"]

    def test_invalid_outcome_rejected(self, store):
        r = extract_candidate_lesson(store, "task_003", "goal", "IN_PROGRESS")
        assert r.created is False
        assert "không hợp lệ" in r.reason

    def test_idempotent_same_task(self, store):
        r1 = extract_candidate_lesson(store, "task_004", "goal A", "COMPLETED")
        r2 = extract_candidate_lesson(store, "task_004", "goal A", "COMPLETED")
        assert r1.created is True
        assert r2.created is False
        assert r2.existing_lesson_id == r1.lesson["id"]

    def test_episode_recorded(self, store):
        extract_candidate_lesson(store, "task_005", "goal", "COMPLETED")
        eps = store.list_episodes(limit=10)
        assert any(e["kind"] == "experience_lesson" for e in eps)


# ---------------------------------------------------------------------------
# promote_lesson — chỉ owner duyệt
# ---------------------------------------------------------------------------

class TestPromoteLesson:
    def test_promote_without_approval_blocked(self, store):
        r = extract_candidate_lesson(store, "task_006", "goal", "COMPLETED")
        with pytest.raises(PermissionError):
            promote_lesson(store, r.lesson["id"], approval_verified=False)

    def test_promote_with_approval_verifies(self, store):
        r = extract_candidate_lesson(store, "task_007", "goal backup", "COMPLETED")
        out = promote_lesson(store, r.lesson["id"], approval_verified=True)
        assert out["promoted"] is True
        new_rec = store.get_memory(out["memory"]["id"])
        assert new_rec.verification_status == VerificationStatus.VERIFIED.value
        assert new_rec.lifecycle_status == LifecycleStatus.ACTIVE.value

    def test_promote_idempotent(self, store):
        r = extract_candidate_lesson(store, "task_008", "goal", "COMPLETED")
        out1 = promote_lesson(store, r.lesson["id"], approval_verified=True)
        assert out1["promoted"] is True
        # Promote BẢN MỚI (VERIFIED + active) lần nữa → no-op không lỗi
        new_id = out1["memory"]["id"]
        out2 = promote_lesson(store, new_id, approval_verified=True)
        assert out2["promoted"] is False
        assert "idempotent" in out2["reason"]

    def test_promote_old_superseded_raises(self, store):
        r = extract_candidate_lesson(store, "task_009", "goal", "COMPLETED")
        out = promote_lesson(store, r.lesson["id"], approval_verified=True)
        # Promote lại BẢN CŨ (đã superseded) → lỗi 409
        with pytest.raises(ValueError):
            promote_lesson(store, r.lesson["id"], approval_verified=True)
        _ = out

    def test_promote_non_lesson_rejected(self, store):
        rec = store.store_memory("ghi chú thường", MemoryType.EPISODIC)
        with pytest.raises(ValueError):
            promote_lesson(store, rec.id, approval_verified=True)

    def test_promote_unknown_404(self, store):
        with pytest.raises(KeyError):
            promote_lesson(store, "mem_khongco", approval_verified=True)


# ---------------------------------------------------------------------------
# list_lessons + tích hợp retrieval (Sprint 9 D)
# ---------------------------------------------------------------------------

class TestListAndRetrieval:
    def test_list_separates_candidates_confirmed(self, store):
        r1 = extract_candidate_lesson(store, "task_010", "goal A", "COMPLETED")
        promote_lesson(store, r1.lesson["id"], approval_verified=True)
        extract_candidate_lesson(store, "task_011", "goal B", "FAILED")
        data = list_lessons(store)
        assert len(data["confirmed"]) == 1
        assert len(data["candidates"]) == 1

    def test_candidate_not_in_retrieval_until_promoted(self, store):
        """Lesson CHƯA duyệt (quarantined) KHÔNG xuất hiện trong retrieval —
        an toàn hơn yêu cầu tối thiểu §VII.2 (chỉ active được tra cứu)."""
        extract_candidate_lesson(store, "task_012", "cần restart daemon và backup DB", "COMPLETED")
        found = find_similar_experiences(store, "cần restart daemon và backup DB trong sprint này")
        assert found["confirmed"] == []
        assert found["candidates"] == []  # quarantined không rò vào retrieval

    def test_promoted_lesson_enters_confirmed_retrieval(self, store):
        """Sau khi owner duyệt → lesson thành căn cứ mạnh trong retrieval."""
        r = extract_candidate_lesson(store, "task_013", "quy trình restart daemon backup", "COMPLETED")
        promote_lesson(store, r.lesson["id"], approval_verified=True)
        found = find_similar_experiences(store, "quy trình restart daemon backup")
        assert any("task_013" in c["content"] for c in found["confirmed"])


# ---------------------------------------------------------------------------
# (b) API handlers
# ---------------------------------------------------------------------------

def _server_mod():
    import quan_ai_brain.web.server as srv

    return srv


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


class TestExperienceAPI:
    def _patch(self, tmp_path, monkeypatch):
        srv = _server_mod()
        from quan_ai_brain.web.server import BrainAPIHandler

        for name in (
            "_handle_api_experience_lessons_list",
            "_handle_api_experience_consolidate",
            "_handle_api_experience_lessons_promote",
        ):
            setattr(_FakeHandler, name, getattr(BrainAPIHandler, name))
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: tmp_path, raising=False)

    def _remote_handler(self):
        h = _FakeHandler()
        h.client_address = ("192.168.1.50", 1)
        return h

    def test_lessons_remote_403(self, tmp_path, monkeypatch):
        self._patch(tmp_path, monkeypatch)

        class Q(dict):
            pass

        self._remote_handler()._handle_api_experience_lessons_list(Q())
        assert _FakeHandler.error and _FakeHandler.error["code"] == 403

    def test_consolidate_remote_403(self, tmp_path, monkeypatch):
        self._patch(tmp_path, monkeypatch)
        self._remote_handler()._handle_api_experience_consolidate({"task_id": "t", "outcome": "COMPLETED"})
        assert _FakeHandler.error and _FakeHandler.error["code"] == 403

    def test_lessons_list_empty(self, tmp_path, monkeypatch):
        self._patch(tmp_path, monkeypatch)

        class Q(dict):
            pass

        _FakeHandler()._handle_api_experience_lessons_list(Q())
        assert _FakeHandler.sent["success"] is True
        assert _FakeHandler.sent["counts"] == {"candidates": 0, "confirmed": 0}

    def test_consolidate_creates_and_idempotent(self, tmp_path, monkeypatch):
        self._patch(tmp_path, monkeypatch)
        # Tạo task thật trong tmp tasks.db để handler đọc goal
        from quan_ai_brain.orchestration.models import AutonomyLevel
        from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

        reg = DurableTaskRegistry(tmp_path / "data" / "tasks.db", workspace=tmp_path)
        t = reg.register_task(
            goal="backup DB hàng tuần",
            autonomy_level=AutonomyLevel.LEVEL_A,
        )

        class Q(dict):
            pass

        h = _FakeHandler()
        h._handle_api_experience_consolidate({"task_id": t.task_id, "outcome": "COMPLETED", "result_summary": "backup OK"})
        assert _FakeHandler.sent and _FakeHandler.sent["created"] is True

        # Lần 2 — idempotent
        h._handle_api_experience_consolidate({"task_id": t.task_id, "outcome": "COMPLETED"})
        assert _FakeHandler.sent["created"] is False
        assert _FakeHandler.sent["existing_lesson_id"] is not None

    def test_consolidate_invalid_outcome_400(self, tmp_path, monkeypatch):
        self._patch(tmp_path, monkeypatch)
        _FakeHandler()._handle_api_experience_consolidate({"task_id": "t1", "outcome": "KHONGLA"})
        # outcome không hợp lệ → success với created=False + reason (không crash)
        assert _FakeHandler.sent and _FakeHandler.sent["created"] is False

    def test_consolidate_missing_params_400(self, tmp_path, monkeypatch):
        self._patch(tmp_path, monkeypatch)
        _FakeHandler()._handle_api_experience_consolidate({"task_id": "t1"})
        assert _FakeHandler.error and _FakeHandler.error["code"] == 400

    def test_promote_requires_owner_confirm(self, tmp_path, monkeypatch):
        self._patch(tmp_path, monkeypatch)
        _FakeHandler()._handle_api_experience_lessons_promote({"memory_id": "abc"})
        assert _FakeHandler.error and _FakeHandler.error["code"] == 403
        assert "owner_confirm" in _FakeHandler.error["error"]

    def test_promote_full_flow_via_api(self, tmp_path, monkeypatch):
        self._patch(tmp_path, monkeypatch)
        store = MemoryStore(tmp_path / "data" / "brain.db", workspace=tmp_path)
        r = extract_candidate_lesson(store, "task_api1", "goal API", "COMPLETED")

        class Q(dict):
            pass

        h = _FakeHandler()
        h._handle_api_experience_lessons_promote({"memory_id": r.lesson["id"], "owner_confirm": "DUYET"})
        assert _FakeHandler.sent["success"] is True
        assert _FakeHandler.sent["promoted"] is True

        # List — giờ có 1 confirmed
        h._handle_api_experience_lessons_list(Q())
        assert _FakeHandler.sent["counts"]["confirmed"] == 1

    def test_promote_wrong_confirm_403(self, tmp_path, monkeypatch):
        self._patch(tmp_path, monkeypatch)
        store = MemoryStore(tmp_path / "data" / "brain.db", workspace=tmp_path)
        r = extract_candidate_lesson(store, "task_api2", "goal", "FAILED")
        _FakeHandler()._handle_api_experience_lessons_promote({"memory_id": r.lesson["id"], "owner_confirm": "OK"})
        assert _FakeHandler.error and _FakeHandler.error["code"] == 403

    def test_promote_unknown_404(self, tmp_path, monkeypatch):
        self._patch(tmp_path, monkeypatch)
        _FakeHandler()._handle_api_experience_lessons_promote({"memory_id": "mem_x", "owner_confirm": "DUYET"})
        assert _FakeHandler.error and _FakeHandler.error["code"] == 404
