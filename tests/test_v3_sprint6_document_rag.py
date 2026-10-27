"""Tests — Sprint 6-GOP hạng mục (1): Document RAG (embedding mock 100%)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.cognition.document_rag import (  # noqa: E402
    Chunk,
    DocumentRAG,
)


class FakeEmbedding:
    """Mock BGE service: vector 3-chiều theo hash chữ đầu."""

    def get_embedding(self, text: str) -> list[float]:
        t = text.lower()
        # vector đơn giản: [có 'alert', có 'quy trình', có 'sla']
        return [
            1.0 if "alert" in t else 0.0,
            1.0 if "quy trình" in t or "quy trinh" in t else 0.0,
            1.0 if "sla" in t else 0.0,
        ]


@pytest.fixture()
def rag(tmp_path):
    return DocumentRAG(workspace=tmp_path, embedding_service=FakeEmbedding())


@pytest.fixture()
def kho_tai_lieu(tmp_path):
    k = tmp_path / "kho_tai_lieu"
    k.mkdir()
    (k / "so_tay_alarm.md").write_text(
        "# Xử lý alarm mất đồng bộ\n\nKhi site báo alarm mất đồng bộ, "
        "kiểm tra quy trình: 1) kiểm tra nguồn điện. 2) kiểm tra link quang. "
        "3) escalation nếu 30 phút không hồi phục.\n\n"
        "# SLA xử lý alarm\n\nAlarm nghiêm trọng phải xử lý trong 4 giờ theo SLA.",
        encoding="utf-8",
    )
    (k / "huong_dan_bao_mat.md").write_text(
        "# Quy trình đổi mật khẩu\n\nĐổi mật khẩu định kỳ 90 ngày. "
        "Không chia sẻ tài khoản.",
        encoding="utf-8",
    )
    return k


def test_ingest_creates_chunks(rag, kho_tai_lieu):
    n = rag.ingest_document(kho_tai_lieu / "so_tay_alarm.md", version="2024")
    assert n >= 2  # 2 section → ít nhất 2 chunk
    assert rag.count_chunks() == n


def test_ingest_folder_all_docs(rag, kho_tai_lieu):
    res = rag.ingest_folder(kho_tai_lieu)
    assert set(res.keys()) == {"so_tay_alarm.md", "huong_dan_bao_mat.md"}
    assert all(v > 0 for v in res.values())


def test_ingest_forbidden_file_rejected(rag, tmp_path):
    env = tmp_path / ".env"
    env.write_text("SECRET=1", encoding="utf-8")
    with pytest.raises(ValueError):
        rag.ingest_document(env)


def test_retrieve_direct_hit(rag, kho_tai_lieu):
    rag.ingest_document(kho_tai_lieu / "so_tay_alarm.md")
    r = rag.retrieve("quy trình xử lý alarm mất đồng bộ")
    assert r.has_evidence
    assert any("alarm" in c.content.lower() for c in r.chunks)
    assert r.chunks[0].doc_title == "so_tay_alarm"


def test_retrieve_paraphrase_hit_via_dense(rag, kho_tai_lieu):
    rag.ingest_document(kho_tai_lieu / "so_tay_alarm.md")
    # paraphrase không chứa từ 'alarm' nhưng chứa 'quy trình' → dense match
    r = rag.retrieve("quy trình khi thiết bị báo mất kết nối")
    assert r.has_evidence


def test_retrieve_no_answer_returns_empty(rag, kho_tai_lieu):
    rag.ingest_document(kho_tai_lieu / "huong_dan_bao_mat.md")
    r = rag.retrieve("cách nấu phở bò")  # ngoài phạm vi
    assert not r.has_evidence
    assert r.render_evidence_block() == ""
    assert "chưa tìm thấy căn cứ" in rag.answer_not_found_message()


def test_evidence_block_has_citation(rag, kho_tai_lieu):
    rag.ingest_document(kho_tai_lieu / "so_tay_alarm.md", version="2024")
    r = rag.retrieve("SLA xử lý alarm")
    assert r.has_evidence
    block = r.render_evidence_block()
    assert "[so_tay_alarm §" in block
    assert "v2024" in block
    assert "chưa tìm thấy căn cứ" in block  # hướng dẫn fail-closed trong prompt


def test_retrieve_empty_index_empty_result(rag):
    r = rag.retrieve("bất kỳ câu gì")
    assert not r.has_evidence


def test_reingest_same_doc_is_idempotent(rag, kho_tai_lieu):
    rag.ingest_document(kho_tai_lieu / "so_tay_alarm.md")
    n1 = rag.count_chunks()
    rag.ingest_document(kho_tai_lieu / "so_tay_alarm.md")
    assert rag.count_chunks() == n1  # không nhân đôi chunk


def test_keyword_fallback_when_no_embedding(tmp_path, kho_tai_lieu):
    rag = DocumentRAG(workspace=tmp_path, embedding_service=None)
    rag.ingest_document(kho_tai_lieu / "so_tay_alarm.md")
    r = rag.retrieve("quy trình xử lý alarm")
    assert r.has_evidence  # keyword-only vẫn tìm được direct hit
    assert "keyword-only" in r.chunks[0].score_reason
