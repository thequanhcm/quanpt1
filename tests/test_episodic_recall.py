"""Test Episodic Time Recall — sửa lỗi CHERRY né câu "hôm qua anh hỏi gì?".

(26/11/2026) Owner feedback 12:35: CHERRY trả lời "em không có thông tin
chính xác" dù brain.db có 3.814 episodes. Gốc rễ: semantic recall không
match thời gian + DB ghi UTC trong khi owner nói giờ VN.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_BRAIN_ROOT = Path(__file__).resolve().parents[1]
if str(_BRAIN_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_BRAIN_ROOT / "src"))

from quan_ai_brain.cognition.episodic_recall import (  # noqa: E402
    looks_like_past_query,
    recall_past_chat_turns,
    render_episodic_block,
)

_VN_TZ = timezone(timedelta(hours=7))


@pytest.fixture()
def mem_db(tmp_path: Path) -> Path:
    """brain.db mini với 2 chat_turn 'hôm qua' (giờ VN) + 1 hôm nay."""
    db = tmp_path / "brain.db"
    con = sqlite3.connect(str(db))
    con.execute(
        "CREATE TABLE episodes (id TEXT PRIMARY KEY, created_at_utc TEXT, "
        "kind TEXT, summary TEXT, source_ref TEXT, status TEXT, metadata_json TEXT)"
    )
    now_vn = datetime.now(_VN_TZ)
    hom_qua = (now_vn - timedelta(days=1)).replace(hour=9, minute=30)
    hom_qua_utc = hom_qua.astimezone(timezone.utc).isoformat()
    hom_nay_utc = now_vn.astimezone(timezone.utc).isoformat()
    rows = [
        ("ep1", hom_qua_utc, "chat_turn",
         json.dumps({"user_query": "kiểm tra sức khỏe hệ thống",
                     "assistant_reply": "Mọi component ONLINE ạ"}, ensure_ascii=False)),
        ("ep2", hom_qua_utc.replace("09:30", "09:35"), "chat_turn",
         json.dumps({"user_query": "check mail da1.dieuphoi2",
                     "assistant_reply": "Có 10 mail mới, 5 quan trọng"}, ensure_ascii=False)),
        ("ep3", hom_nay_utc, "chat_turn",
         json.dumps({"user_query": "trí nhớ của em thế nào",
                     "assistant_reply": "3.273 memories"}, ensure_ascii=False)),
        # kind khác phải bị loại
        ("ep4", hom_qua_utc, "other_kind", "{}"),
    ]
    con.executemany(
        "INSERT INTO episodes VALUES (?,?,?,?,?,?,?)",
        [(r[0], r[1], r[2], r[3] + "|SUMMARY", "chat_session:t", "ACTIVE", r[3])
         for r in rows],
    )
    con.commit()
    con.close()
    return db


# ---------------------------------------------------------------------------
# Detector — thận trọng: khớp tín hiệu thời gian, bỏ qua câu thường
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("q", [
    "hôm qua anh đã hỏi em cái gì?",
    "hom qua anh noi gi",
    "hôm nay anh đã nhắn gì rồi?",
    "lần trước anh đã hỏi gì em nhớ không",
    "sáng nay chúng ta đã nói gì",
])
def test_detector_matches_past_queries(q: str) -> None:
    assert looks_like_past_query(q) is True, q


@pytest.mark.parametrize("q", [
    "trí nhớ của em bây giờ thế nào?",
    "check mail da1.dieuphoi2",
    "em tư vấn thấy hệ thống có thiếu sót gì?",
    "mở chrome giúp em",
    "",
])
def test_detector_ignores_non_time_queries(q: str) -> None:
    assert looks_like_past_query(q) is False, q


# ---------------------------------------------------------------------------
# Recall — đúng khung ngày VN→UTC, đúng metadata, đúng kind
# ---------------------------------------------------------------------------

def test_recall_hom_qua_returns_two_turns(mem_db: Path) -> None:
    data = recall_past_chat_turns(mem_db, "hôm qua anh đã hỏi em cái gì?")
    assert data is not None
    assert data["label"].startswith("NGÀY")
    assert "hôm qua" in data["label"]
    assert len(data["items"]) == 2  # ep1 + ep2, ep4 (kind khác) bị loại
    users = " ".join(i["user"] for i in data["items"])
    assert "kiểm tra sức khỏe hệ thống" in users
    assert "check mail da1.dieuphoi2" in users


def test_recall_hom_nay_returns_today_turn(mem_db: Path) -> None:
    data = recall_past_chat_turns(mem_db, "hôm nay anh đã nhắn gì rồi?")
    assert data is not None
    assert len(data["items"]) == 1
    assert "trí nhớ" in data["items"][0]["user"]


def test_recall_empty_frame_returns_honest_days(tmp_path: Path) -> None:
    """DB trống khung hôm qua → vẫn trả dict kèm ngày CÓ dữ liệu (trung thực)."""
    db = tmp_path / "empty.db"
    con = sqlite3.connect(str(db))
    con.execute(
        "CREATE TABLE episodes (id TEXT PRIMARY KEY, created_at_utc TEXT, "
        "kind TEXT, summary TEXT, source_ref TEXT, status TEXT, metadata_json TEXT)"
    )
    con.commit()
    con.close()
    data = recall_past_chat_turns(db, "hôm qua anh hỏi gì?")
    assert data is not None
    assert data["items"] == []


def test_recall_fail_open_on_missing_db(tmp_path: Path) -> None:
    assert recall_past_chat_turns(tmp_path / "khong-ton-tai.db", "hôm qua?") is None


# ---------------------------------------------------------------------------
# Render — block buộc trả lời bằng dữ liệu, cấm né
# ---------------------------------------------------------------------------

def test_render_with_items_forces_data_answer(mem_db: Path) -> None:
    data = recall_past_chat_turns(mem_db, "hôm qua anh đã hỏi em cái gì?")
    block = render_episodic_block(data)
    assert "[HỘI THOẠI" in block
    assert "TRUY XUẤT TỪ TRÍ NHỚ EPISODIC" in block
    assert "kiểm tra sức khỏe hệ thống" in block
    assert "KHÔNG nói 'không có thông tin'" in block


def test_render_empty_is_honest(tmp_path: Path) -> None:
    db = tmp_path / "e.db"
    con = sqlite3.connect(str(db))
    con.execute(
        "CREATE TABLE episodes (id TEXT PRIMARY KEY, created_at_utc TEXT, "
        "kind TEXT, summary TEXT, source_ref TEXT, status TEXT, metadata_json TEXT)"
    )
    con.commit()
    con.close()
    block = render_episodic_block(recall_past_chat_turns(db, "hôm qua?"))
    assert "không có bản ghi" in block


def test_render_none_is_empty_string() -> None:
    assert render_episodic_block(None) == ""


# ---------------------------------------------------------------------------
# Wire vào server.py
# ---------------------------------------------------------------------------

def test_server_has_episodic_recall_wire() -> None:
    srv = (_BRAIN_ROOT / "src" / "quan_ai_brain" / "web" / "server.py").read_text(
        encoding="utf-8", errors="replace")
    assert "2.54 EPISODIC TIME RECALL" in srv
    assert "looks_like_past_query(query)" in srv
    assert "recall_past_chat_turns(db_path, query)" in srv
