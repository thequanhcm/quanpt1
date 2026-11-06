"""Test TONY Vision — 'phân tích ảnh' qua DM (06/11/2026).

Phủ: routing intent, chọn nguồn ảnh (đính kèm DM → DM 24h → TONY tự chụp 24h),
OCR thật trên ảnh tạo local (PIL), tri thức vào candidate_knowledge (tmp DB),
fail-honest khi không có ảnh. Không DM thật, không đụng DB production.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

BRAIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRAIN_ROOT))
sys.path.insert(0, str(BRAIN_ROOT / "src"))

from tools import netchat_command_center as cc  # noqa: E402
from quan_ai_brain.vision import image_analyzer as va  # noqa: E402


# ---------------------------------------------------------------- routing ---
@pytest.mark.parametrize("q", [
    "phân tích ảnh vừa chụp,",       # đúng tin owner 20:58 (kèm dấu phẩy)
    "phân tích ảnh",
    "phân tích hình vừa chụp",
    "đọc chữ trong ảnh này",
    "ảnh này ghi gì",
    "xem giúp em nội dung ảnh",
])
def test_intent_analyze_image_matches(q):
    assert cc.detect_intent(q) == "tony_analyze_image"


@pytest.mark.parametrize("q", [
    "phân tích dữ liệu doanh thu giúp anh",  # không có 'ảnh' → không nuốt
    "thống kê bảng lương",
    "chụp hình",                              # vẫn là lệnh chụp
    "hôm nay thế nào",                        # chat thường
])
def test_intent_analyze_image_not_overreach(q):
    assert cc.detect_intent(q) != "tony_analyze_image"


# ------------------------------------------------------------------ helper ---
@pytest.fixture()
def vision_env(tmp_path, monkeypatch):
    """Workspace giả lập: brain.db tmp + dirs ảnh tmp; giữ production nguyên vẹn."""
    db = tmp_path / "brain.db"
    import sqlite3
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE candidate_knowledge "
                 "(id TEXT PRIMARY KEY, created_at_utc TEXT NOT NULL, "
                 "statement TEXT NOT NULL, source_ref TEXT NOT NULL, "
                 "rationale TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'quarantined', "
                 "decision_note TEXT NOT NULL DEFAULT '')")
    conn.close()
    monkeypatch.setattr(va, "BRAIN_ROOT", tmp_path)
    # image_analyzer đọc DB tại BRAIN_ROOT/data/brain.db — khớp cấu trúc thật
    (tmp_path / "data").mkdir(exist_ok=True)
    import shutil
    shutil.move(str(db), str(tmp_path / "data" / "brain.db"))
    monkeypatch.setattr(va, "PI5_MEDIA_DIR", tmp_path / "logs" / "pi5_media")
    monkeypatch.setattr(va, "NETCHAT_FILES_DIR", tmp_path / "data" / "netchat_files")
    monkeypatch.setattr(cc, "WORKSPACE", tmp_path)
    return tmp_path


def _make_image(path: Path, text: str = "TONY TEST 123", size=(640, 320)):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", size, (245, 240, 230))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, size[0] - 10, size[1] - 10], outline=(120, 60, 40), width=6)
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except Exception:
        font = ImageFont.load_default()
    d.text((40, 120), text, fill=(20, 20, 90), font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


# ------------------------------------------------------------------- happy ---
def test_analyze_image_ocr_and_facts(vision_env):
    p = _make_image(vision_env / "img1.png", "TONY TEST 123")
    out = va.analyze_image(p)
    assert "img1.png" in out
    assert "640×320" in out                     # fact đo được
    assert "TONY TEST 123" in out               # OCR đọc được chữ
    assert "candidate" in out.lower() or "chờ anh duyệt" in out  # tri thức đã ghi
    # DB tmp nhận 1 dòng chờ duyệt
    import sqlite3
    conn = sqlite3.connect(str(vision_env / "data" / "brain.db"))
    n = conn.execute("SELECT COUNT(*) FROM candidate_knowledge "
                     "WHERE source_ref LIKE 'tony_vision:%'").fetchone()[0]
    conn.close()
    assert n == 1


def test_analyze_image_no_text_is_honest(vision_env):
    # Ảnh màu phẳng, không chữ → OCR rỗng PHẢI được nói thẳng, không bịa
    from PIL import Image
    p = vision_env / "blank.png"
    Image.new("RGB", (320, 240), (200, 205, 210)).save(p)
    out = va.analyze_image(p)
    assert "không có chữ" in out
    assert "TONY TEST" not in out


def test_handler_fallback_capture_photo(vision_env, monkeypatch):
    # Không DM attach → rơi về ảnh TONY tự chụp mới nhất (trong 24h)
    cap = _make_image(vision_env / "logs" / "pi5_media" / "photo_20261106_210000.jpg",
                      "CAPTURED 42")
    import os
    old = time.time() - 60
    os.utime(cap, (old, old))  # mtime khớp "vừa chụp"
    out = cc.handle_tony_analyze_image("phân tích ảnh vừa chụp")
    assert "photo_20261106_210000.jpg" in out
    assert "CAPTURED 42" in out


def test_handler_dm_attach_priority(vision_env, monkeypatch):
    # Có file DM attach trong payload → ưu tiên file đó, không lấy ảnh chụp
    _make_image(vision_env / "logs" / "pi5_media" / "photo_20261106_205438.jpg", "CŨ")
    dm_img = _make_image(vision_env / "data" / "netchat_files" / "owner_sent.jpg", "DM MỚI")
    out = cc.handle_tony_analyze_image("phân tích ảnh", payload={"file_paths": [str(dm_img)]})
    assert "owner_sent.jpg" in out


def test_handler_no_image_fail_honest(vision_env):
    out = cc.handle_tony_analyze_image("phân tích ảnh")
    assert "⚠️" in out and "chưa thấy ảnh" in out


def test_missing_file_fail_honest(vision_env):
    out = va.analyze_image(vision_env / "không_tồn_tại.jpg")
    assert "⚠️" in out and "Không tìm thấy" in out
