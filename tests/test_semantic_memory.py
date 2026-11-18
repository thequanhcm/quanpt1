# -*- coding: utf-8 -*-
"""Tests cho semantic_memory — ChromaDB ONNX MiniLM (local, không Ollama).

Sprint 18/11 TASK-SEMANTIC-MEMORY-M6: ingest idempotent, search ngữ nghĩa
tiếng Việt, fail-honest khi lỗi, stats trả về thông tin thật.
"""
from __future__ import annotations

import sqlite3
import shutil
import tempfile
from pathlib import Path

import pytest

from quan_ai_brain.cognition.semantic_memory import SemanticMemoryEngine


@pytest.fixture()
def tmp_workspace() -> Path:
    """Workspace tạm với brain.db mẫu (memories + episodes + lessons)."""
    tmp = Path(tempfile.mkdtemp())
    db = tmp / "brain.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE memories (
            id TEXT PRIMARY KEY, memory_type TEXT, content TEXT, source_ref TEXT,
            verification_status TEXT, confidence_score REAL, project_scope TEXT,
            tags_json TEXT, lifecycle_status TEXT, version INTEGER,
            superseded_by TEXT, created_at_utc TEXT, updated_at_utc TEXT,
            metadata_json TEXT
        );
        CREATE TABLE episodes (
            id TEXT PRIMARY KEY, created_at_utc TEXT, kind TEXT, summary TEXT,
            source_ref TEXT, status TEXT, metadata_json TEXT
        );
        INSERT INTO memories VALUES (
            'm1', 'SEMANTIC', 'Anh Quan thich chup anh kiosk tren Pi 5 bang camera IMX708',
            NULL, 'VERIFIED', 1.0, 'cherry', '[]', 'active', 1, NULL,
            '2026-11-14T00:04:00Z', '2026-11-14T00:04:00Z', NULL
        );
        INSERT INTO memories VALUES (
            'm2', 'PROCEDURAL', 'Quy trinh backup database truoc khi nang cap he thong',
            NULL, 'VERIFIED', 1.0, 'cherry', '[]', 'active', 1, NULL,
            '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', NULL
        );
        INSERT INTO episodes VALUES (
            'e1', '2026-11-14T00:04:00Z', 'chat_turn',
            'User: Chup kiosk | Assistant: Da, em chup anh tu camera kiosk Pi 5 ngay day a.',
            NULL, 'OPEN', NULL
        );
        INSERT INTO episodes VALUES (
            'e2', '2026-11-12T09:00:00Z', 'experience_lesson',
            'Camera IMX708 tra anh 0 byte khi 2 tien trinh chup cung luc - can lock.',
            NULL, 'RESOLVED', NULL
        );
        """
    )
    conn.commit()
    conn.close()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


class TestSemanticMemoryEngine:
    def test_stats_no_chunks(self, tmp_workspace: Path) -> None:
        engine = SemanticMemoryEngine(tmp_workspace / "vdb", tmp_workspace / "brain.db")
        s = engine.stats()
        assert s["n_chunks"] == 0
        # Embedding local ONNX MiniLM — chuỗi khẳng định KHÔNG cần Ollama (fail-honest)
        assert "ONNX MiniLM" in s["embedding"]
        assert "không cần Ollama" in s["embedding"]

    def test_ingest_idempotent(self, tmp_workspace: Path) -> None:
        engine = SemanticMemoryEngine(tmp_workspace / "vdb", tmp_workspace / "brain.db")
        r1 = engine.ingest(limit_per_table=100)
        assert r1["added"] >= 4
        assert r1["total_in_collection"] >= 4
        # Chạy lần 2 → 0 added
        r2 = engine.ingest(limit_per_table=100)
        assert r2["added"] == 0
        assert r2["skipped_existing"] == r1["added"]
        assert r2["total_in_collection"] == r1["total_in_collection"]

    def test_search_hits_related_semantically(self, tmp_workspace: Path) -> None:
        engine = SemanticMemoryEngine(tmp_workspace / "vdb", tmp_workspace / "brain.db")
        engine.ingest(limit_per_table=100)
        # Query có dấu khớp doc không dấu → semantic thật
        hits = engine.search("nhiep anh kiosk", top_k=3)
        assert len(hits) >= 1
        assert any("chup" in h["text"].lower() or "kiosk" in h["text"].lower()
                   for h in hits)

    def test_search_empty_query_returns_empty(self, tmp_workspace: Path) -> None:
        engine = SemanticMemoryEngine(tmp_workspace / "vdb", tmp_workspace / "brain.db")
        engine.ingest(limit_per_table=100)
        assert engine.search("", top_k=5) == []
        assert engine.search("   ", top_k=5) == []

    def test_search_filter_distance(self, tmp_workspace: Path) -> None:
        engine = SemanticMemoryEngine(tmp_workspace / "vdb", tmp_workspace / "brain.db")
        engine.ingest(limit_per_table=100)
        # distance quá nhỏ → 0 hit (chỉ lọc rất gần)
        very_close = engine.search("chup anh kiosk", top_k=5, min_distance=0.0)
        # distance lớn → nhiều hit
        loose = engine.search("chup anh kiosk", top_k=5, min_distance=2.5)
        assert len(loose) >= len(very_close)

    def test_missing_db_returns_empty(self, tmp_workspace: Path) -> None:
        # DB không tồn tại → fail-honest: stats vẫn trả (count=0), search []
        engine = SemanticMemoryEngine(tmp_workspace / "vdb", tmp_workspace / "khong.db")
        assert engine.stats()["n_chunks"] == 0
        assert engine.search("test", top_k=5) == []

    def test_hits_have_metadata(self, tmp_workspace: Path) -> None:
        engine = SemanticMemoryEngine(tmp_workspace / "vdb", tmp_workspace / "brain.db")
        engine.ingest(limit_per_table=100)
        hits = engine.search("camera", top_k=2)
        assert hits
        for h in hits:
            assert "source" in h
            assert "verification" in h
            assert "distance" in h
            assert "text" in h
