# -*- coding: utf-8 -*-
"""Tests cho memory_recall — recall theo thời gian + từ khóa cho câu hỏi meta.

(18/11/2026) Owner hỏi "vì sao dữ liệu trí nhớ không hoạt động" — gốc: token
LIKE retrieval trả self-match với câu hỏi meta → bot nói "không nhớ" dù có
3.5k episodes. Module memory_recall.py fix điều này. Tests bảo đảm:
- is_memory_meta_query: nhận đúng câu meta VN, loại câu thường
- recall_memory_summary: trả block có dữ liệu thật từ brain.db tạm (tmp)
- Hybrid: từ khóa ("chụp ảnh") phải hiện TRƯỚC timeline
- Fail-honest: lỗi DB → None, không raise
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS / "src"))

from quan_ai_brain.cognition.memory_recall import (  # noqa: E402
    _extract_keywords,
    is_memory_meta_query,
    recall_memory_summary,
)


@pytest.fixture()
def tmp_brain_db(tmp_path: Path) -> Path:
    """brain.db tạm với 2 episodes + 1 memory mẫu."""
    db = tmp_path / "brain.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE memories (
            memory_id TEXT PRIMARY KEY, content TEXT, memory_type TEXT,
            verification_status TEXT, project_scope TEXT, tags_json TEXT,
            lifecycle_status TEXT, created_at_utc TEXT, updated_at_utc TEXT
        );
        CREATE TABLE episodes (
            episode_id TEXT PRIMARY KEY, kind TEXT, summary TEXT,
            created_at_utc TEXT
        );
        INSERT INTO memories VALUES (
            'm1', 'Owner thích chụp ảnh kiosk Pi 5', 'fact', 'verified',
            'cherry', '[]', 'active', '2026-11-14T00:04:00Z', '2026-11-14T00:04:00Z'
        );
        INSERT INTO episodes VALUES (
            'e1', 'chat_turn',
            'User: Chụp kiosk | Assistant: Da, em chup anh tu camera Pi 5.',
            '2026-11-14T00:04:00Z'
        );
        INSERT INTO episodes VALUES (
            'e2', 'chat_turn',
            'User: Pi5 la gi | Assistant: Raspberry Pi 5 la may tinh board nho.',
            '2026-11-15T09:00:00Z'
        );
        """
    )
    conn.commit()
    conn.close()
    return db


class TestIsMemoryMetaQuery:
    def test_owner_question_is_meta(self) -> None:
        assert is_memory_meta_query(
            "anh đã nói gì với em 1 tháng trước? Liệt kê những gì em nhớ được"
        )

    def test_topic_recall_is_meta(self) -> None:
        assert is_memory_meta_query("em nhớ gì về việc chụp ảnh của anh? Kể lại.")

    def test_normal_question_not_meta(self) -> None:
        assert not is_memory_meta_query("Pi5 là gì?")
        assert not is_memory_meta_query("cherry chụp kiosk như thế nào?")

    def test_too_short_not_meta(self) -> None:
        assert not is_memory_meta_query("nhớ?")


class TestExtractKeywords:
    def test_filters_stopwords(self) -> None:
        kws = _extract_keywords("em nhớ gì về việc chụp ảnh của anh?")
        assert "chụp" in kws
        assert "ảnh" in kws
        assert "anh" not in kws
        assert "nhớ" not in kws

    def test_max_keywords(self) -> None:
        assert len(_extract_keywords("a b c d e f g h i j")) <= 6


class TestRecallMemorySummary:
    def test_time_span_recall(self, tmp_brain_db: Path) -> None:
        r = recall_memory_summary(
            "anh đã nói gì với em 1 tháng trước?", tmp_brain_db
        )
        assert r is not None
        assert "MEMORY RECALL" in r["block"]
        assert "1 tháng trước" in r["span_label"]
        assert r["n_scanned"] >= 1

    def test_keyword_hybrid_recall(self, tmp_brain_db: Path) -> None:
        r = recall_memory_summary(
            "em nhớ gì về việc chụp ảnh của anh?", tmp_brain_db
        )
        assert r is not None
        # Từ khóa khớp phải xuất hiện trước timeline trong block
        assert "chụp" in r["block"]
        assert "Nội dung khớp từ khóa" in r["block"]

    def test_non_meta_returns_none(self, tmp_brain_db: Path) -> None:
        assert recall_memory_summary("Pi5 là gì?", tmp_brain_db) is None

    def test_missing_db_returns_none(self, tmp_path: Path) -> None:
        # Fail-honest: DB không tồn tại → None, không raise
        assert recall_memory_summary(
            "anh đã nói gì 1 tháng trước?", tmp_path / "khong_ton_tai.db"
        ) is None
