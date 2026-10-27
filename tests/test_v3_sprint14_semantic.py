"""Tests — Sprint 14: Information Gaps schema thật + Semantic search kinh nghiệm (BGE-M3).

Tmp DB 100% + FakeEmbedding (không gọi Ollama thật trong unit test);
chỉ test smoke thật mới chạm Ollama. Không mạng ngoài, không ghi DB thật.
"""
from __future__ import annotations

import sqlite3
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.cognition.embedding import cosine_similarity
from quan_ai_brain.cognition.improvement_report import build_improvement_report
from quan_ai_brain.cognition.experience_semantic import (
    find_similar_experiences_semantic,
)
from quan_ai_brain.memory.models import MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


class FakeEmbedding:
    """Embedding giả: vector 3 chiều theo từ khoá — deterministic, không mạng."""

    model_name = "fake-bge"

    def __init__(self, available: bool = True) -> None:
        self.available = available

    def embed_text(self, text: str) -> list[float]:
        text = (text or "").lower()
        if not self.available:
            return []
        return [
            1.0 if "backup" in text else 0.0,
            1.0 if "email" in text else 0.0,
            1.0 if "python" in text else 0.0,
        ]


def _store_with_lessons(tmp_path: Path) -> MemoryStore:
    store = MemoryStore(tmp_path / "brain.db", workspace=tmp_path)
    store.store_memory(
        content="Bài học (thành công): backup 2AM chạy trước khi sync email tránh xung đột I/O",
        memory_type=MemoryType.EPISODIC,
        verification_status=VerificationStatus.VERIFIED,
        project_scope="experience",
        source_ref="task:backup_01",
        tags=["sprint11_lesson"],
    )
    store.store_memory(
        content="Ghi chú python: chạy script qua venv để đúng dependency",
        memory_type=MemoryType.PROCEDURAL,
        verification_status=VerificationStatus.UNVERIFIED,
        project_scope="experience",
        source_ref="task:venv_01",
        tags=["note"],
    )
    return store


class TestSemanticSearch:
    def test_confirmed_ranked_by_similarity(self, tmp_path):
        store = _store_with_lessons(tmp_path)
        r = find_similar_experiences_semantic(
            store, "backup email xung đột", embedding=FakeEmbedding(), limit=5
        )
        assert r["semantic_available"] is True
        assert r["model"] == "fake-bge"
        assert len(r["confirmed"]) == 1
        top = r["confirmed"][0]
        assert top["similarity"] >= 0.3
        assert top["is_confirmed"] is True
        assert top["source_ref"] == "task:backup_01"

    def test_candidate_separated_from_confirmed(self, tmp_path):
        store = _store_with_lessons(tmp_path)
        r = find_similar_experiences_semantic(
            store, "python venv dependency", embedding=FakeEmbedding(), limit=5
        )
        # note UNVERIFIED → candidates, KHÔNG lẫn vào confirmed
        assert not r["confirmed"]
        assert len(r["candidates"]) == 1
        assert r["candidates"][0]["verification_status"] == "UNVERIFIED"

    def test_ollama_offline_fail_open(self, tmp_path):
        store = _store_with_lessons(tmp_path)
        r = find_similar_experiences_semantic(
            store, "bất kỳ", embedding=FakeEmbedding(available=False), limit=5
        )
        assert r["semantic_available"] is False
        assert r["confirmed"] == [] and r["candidates"] == []

    def test_empty_query_noop(self, tmp_path):
        store = _store_with_lessons(tmp_path)
        r = find_similar_experiences_semantic(store, "  ", embedding=FakeEmbedding())
        assert r["semantic_available"] is False

    def test_below_threshold_filtered(self, tmp_path):
        store = _store_with_lessons(tmp_path)
        r = find_similar_experiences_semantic(
            store, "chủ đề hoàn toàn xa lạ", embedding=FakeEmbedding(),
            limit=5, min_similarity=0.99,
        )
        assert r["confirmed"] == [] and r["candidates"] == []
        assert r["semantic_available"] is True  # available nhưng 0 kết quả


class TestCosine:
    def test_cosine_identical_and_orthogonal(self):
        assert cosine_similarity([1, 0, 0], [1, 0, 0]) == 1.0
        assert cosine_similarity([1, 0, 0], [0, 1, 0]) == 0.0
        assert cosine_similarity([], [1.0]) == 0.0
        assert cosine_similarity([1, 0], [1, 0, 0]) == 0.0


class TestGapSchema:
    def _ws(self, tmp_path: Path, *, corrupt: bool = False) -> Path:
        data = tmp_path / "data"
        data.mkdir(exist_ok=True)
        if corrupt:
            (data / "information_gaps.db").write_bytes(b"khong phai sqlite")
        else:
            conn = sqlite3.connect(data / "information_gaps.db")
            conn.execute("CREATE TABLE info_gap_tasks (task_id TEXT PRIMARY KEY, spec_json TEXT NOT NULL, readiness TEXT NOT NULL, waiting_state TEXT NOT NULL, request_text TEXT, created_at_utc TEXT, updated_at_utc TEXT, netchat_message_id TEXT, reminder_count INTEGER, last_reminder_utc TEXT)")
            conn.execute("CREATE TABLE info_gap_events (event_id TEXT PRIMARY KEY, task_id TEXT, event_type TEXT, detail_json TEXT, created_at_utc TEXT)")
            conn.execute("INSERT INTO info_gap_tasks VALUES ('g1','{}','NEED_MORE_INFO','WAITING_OWNER','?','2026','2026','',0,NULL)")
            conn.execute("INSERT INTO info_gap_tasks VALUES ('g2','{}','READY','RESOLVED','?','2026','2026','',0,NULL)")
            conn.commit(); conn.close()
        return tmp_path

    def test_real_schema_counted(self, tmp_path):
        r = build_improvement_report(self._ws(tmp_path))
        g = r["sections"]["information_gaps"]
        assert g["status"] == "Đã có và hoạt động"
        assert g["open_gaps"] == 1 and g["resolved_gaps"] == 1 and g["events"] == 0

    def test_corrupt_db_still_unverified(self, tmp_path):
        """DB hỏng → CHƯA XÁC MINH (giữ nguyên tắc fail-honest Sprint 13)."""
        r = build_improvement_report(self._ws(tmp_path, corrupt=True))
        g = r["sections"]["information_gaps"]
        assert g["status"] == "Chưa xác minh"


class TestAPI:
    def _patch(self, monkeypatch, tmp_path):
        import quan_ai_brain.web.server as srv
        from quan_ai_brain.web.server import BrainAPIHandler

        _FakeHandler._handle_api_experience_search = BrainAPIHandler._handle_api_experience_search
        _FakeHandler.sent = None
        _FakeHandler.error = None
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: tmp_path, raising=False)

    def test_missing_q_400(self, monkeypatch, tmp_path):
        self._patch(monkeypatch, tmp_path)
        _FakeHandler()._handle_api_experience_search("")
        assert _FakeHandler.error and _FakeHandler.error["code"] == 400

    def test_remote_403(self, monkeypatch, tmp_path):
        self._patch(monkeypatch, tmp_path)
        h = _FakeHandler()
        h.client_address = ("10.0.0.9", 1)
        qs = urllib.parse.urlencode({"q": "backup"})
        h._handle_api_experience_search(qs)
        assert _FakeHandler.error and _FakeHandler.error["code"] == 403

    def test_offline_semantic_flag_honest(self, monkeypatch, tmp_path):
        """Ollama offline → semantic_available=False + rỗng, KHÔNG lỗi 500."""
        self._patch(monkeypatch, tmp_path)
        import quan_ai_brain.cognition.experience_semantic as sem

        class _FakeSrv:
            model_name = "fake-bge"

            def embed_text(self, text: str) -> list[float]:
                return []

        monkeypatch.setattr(sem, "BGEEmbeddingService", _FakeSrv, raising=False)
        store = _store_with_lessons(tmp_path / "brain_data" if False else tmp_path)
        store.close()
        qs = urllib.parse.urlencode({"q": "backup"})
        _FakeHandler()._handle_api_experience_search(qs)
        assert _FakeHandler.sent and _FakeHandler.sent["success"] is True
        assert _FakeHandler.sent["semantic_available"] is False


class _FakeHandler:
    sent: Any = None
    error: Any = None
    client_address = ("127.0.0.1", 1)

    @staticmethod
    def _send_json(payload, code=200):
        _FakeHandler.sent = payload
        _FakeHandler.error = None

    @staticmethod
    def _send_error_json(msg, code=400):
        _FakeHandler.error = {"error": msg, "code": code}
        _FakeHandler.sent = None
