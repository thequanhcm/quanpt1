"""Unit test ghép cặp ẢNH ↔ LỜI MÔ TẢ trong DM (yêu cầu owner 31/10/2026).

Quy tắc owner:
- Ảnh gửi KHÔNG kèm mô tả → KHÔNG phản hồi (HOLD chờ).
- Lời mô tả gửi TRƯỚC hoặc SAU ảnh đều ghép được.
- TỔNG HỢP cả ảnh (OCR) + lời yêu cầu rồi MỚI xử lý.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.netchat_auto_responder import (  # noqa: E402
    _plan_batch,
    _prune_pending,
    PENDING_FILES_TTL_MS,
    DESC_BEFORE_WINDOW_MS,
)

NOW = 1_800_000_000_000  # mốc thời gian giả (ms)
IMG_EXT = "png"


def _img(mid, cat, fid="fIMG"):
    return {"id": mid, "message": "", "file_ids": [fid], "create_at": cat,
            "user_id": "owner", "_src": "dm", "_chan": "DM"}


def _txt(mid, body, cat):
    return {"id": mid, "message": body, "file_ids": [], "create_at": cat,
            "user_id": "owner", "_src": "dm", "_chan": "DM"}


def _fake_image_check_factory(known_image_ids: set[str]):
    """image_check giả: file_id thuộc known_image_ids là ảnh, còn lại là file thường."""
    def check(msg):
        return all(f in known_image_ids for f in (msg.get("file_ids") or []))
    return check


IMG_IDS = {"fIMG"}
ic = _fake_image_check_factory(IMG_IDS)


# ---------------------------------------------------------------------------
# 1. Ảnh đơn KHÔNG mô tả → HOLD (không phản hồi)
# ---------------------------------------------------------------------------
def test_image_without_description_holds():
    work, pending = _plan_batch([_img("m1", NOW)], [], now_ms=NOW, image_check=ic)
    assert work == [], "Ảnh không mô tả phải HOLD, không tạo việc"
    assert len(pending) == 1 and pending[0]["msg_id"] == "m1"


# ---------------------------------------------------------------------------
# 2. Mô tả gửi SAU ảnh (ảnh hold từ lượt trước) → ghép thành 1 việc
# ---------------------------------------------------------------------------
def test_description_after_image_pairs():
    held = [{"msg_id": "m1", "file_ids": ["fIMG"], "create_at": NOW - 60_000}]
    work, pending = _plan_batch([_txt("m2", "ảnh này là gì em?", NOW)],
                                held, now_ms=NOW, image_check=ic)
    assert len(work) == 1
    assert work[0]["text"] == "ảnh này là gì em?"
    assert work[0]["file_ids"] == ["fIMG"], "Ảnh đang chờ phải ghép vào việc"
    assert pending == [], "Ảnh đã ghép → hết chờ"


# ---------------------------------------------------------------------------
# 3. Mô tả gửi TRƯỚC ảnh (cùng lượt poll) → ghép ngược
# ---------------------------------------------------------------------------
def test_description_before_image_pairs():
    # (07/11/2026) CẬP NHẬT THEO THIẾT KẾ MỚI (Vision S1 0d850b8): cụm "đọc giúp
    # anh ảnh này" giờ là LỆNH hệ thống tony_analyze_image → chạy NGAY không ghép
    # ảnh (luật "lệnh hệ thống không ghép ảnh"). Dùng lời mô tả THƯỜNG để test ghép.
    msgs = [
        _txt("t1", "ảnh này chụp ở nhà anh nè", NOW - 30_000),
        _img("i1", NOW),
    ]
    work, pending = _plan_batch(msgs, [], now_ms=NOW, image_check=ic)
    assert len(work) == 1, "Mô tả trước + ảnh = 1 việc duy nhất"
    assert work[0]["text"] == "ảnh này chụp ở nhà anh nè"
    assert work[0]["file_ids"] == ["fIMG"]
    assert pending == []


def test_analyze_image_command_does_not_pair():
    # Lệnh hệ thống ("phân tích ảnh") chạy ngay — KHÔNG ghép ảnh đang chờ
    # (quy tắc: lệnh hệ thống = việc riêng, file đi kèm tin lệnh mới dùng).
    msgs = [
        _txt("t1", "phân tích ảnh", NOW - 30_000),
        _img("i1", NOW),
    ]
    work, pending = _plan_batch(msgs, [], now_ms=NOW, image_check=ic)
    assert len(work) == 1 and work[0]["text"] == "phân tích ảnh"
    assert work[0]["file_ids"] == [], "Lệnh hệ thống không được ghép ảnh ngoài"
    assert len(pending) == 1, "Ảnh vẫn HOLD chờ mô tả thường"


# ---------------------------------------------------------------------------
# 4. Ảnh kèm CHỮ ngay trong 1 tin (caption) → ghép luôn, không HOLD
# ---------------------------------------------------------------------------
def test_image_with_caption_processes_immediately():
    msgs = [{"id": "c1", "message": "báo cáo này nói gì?",
             "file_ids": ["fIMG"], "create_at": NOW,
             "user_id": "owner", "_src": "dm", "_chan": "DM"}]
    work, pending = _plan_batch(msgs, [], now_ms=NOW, image_check=ic)
    assert len(work) == 1
    assert work[0]["text"] == "báo cáo này nói gì?"
    assert work[0]["file_ids"] == ["fIMG"]
    assert pending == []


# ---------------------------------------------------------------------------
# 5. LỆNH HỆ THỐNG không bao giờ ghép ảnh đang chờ
# ---------------------------------------------------------------------------
def test_system_command_never_grabs_pending_image():
    held = [{"msg_id": "m1", "file_ids": ["fIMG"], "create_at": NOW - 60_000}]
    work, pending = _plan_batch([_txt("c1", "mở chrome lên", NOW)],
                                held, now_ms=NOW, image_check=ic)
    assert len(work) == 1 and work[0]["text"] == "mở chrome lên"
    assert work[0]["file_ids"] == [], "Lệnh phải chạy không kèm ảnh"
    assert len(pending) == 1, "Ảnh đang chờ giữ nguyên"


# ---------------------------------------------------------------------------
# 6. File KHÔNG phải ảnh (PDF) → xử lý ngay như cũ
# ---------------------------------------------------------------------------
def test_non_image_file_processes_immediately():
    work, pending = _plan_batch([_img("d1", NOW, fid="fPDF")], [],
                                now_ms=NOW, image_check=ic)
    assert len(work) == 1 and work[0]["file_ids"] == ["fPDF"]
    assert pending == []


# ---------------------------------------------------------------------------
# 7. Nhiều ảnh đang chờ + 1 mô tả → TỔNG HỢP tất cả thành 1 việc
# ---------------------------------------------------------------------------
def test_multiple_pending_images_merge_into_one_work():
    held = [
        {"msg_id": "m1", "file_ids": ["fA"], "create_at": NOW - 120_000},
        {"msg_id": "m2", "file_ids": ["fB"], "create_at": NOW - 60_000},
    ]
    work, pending = _plan_batch([_txt("t1", "tổng hợp 2 ảnh này giúp em", NOW)],
                                held, now_ms=NOW, image_check=ic)
    assert len(work) == 1
    assert sorted(work[0]["file_ids"]) == ["fA", "fB"], "Cả 2 ảnh phải vào 1 việc"
    assert pending == []


# ---------------------------------------------------------------------------
# 8. TTL: ảnh chờ quá 30 phút bị bỏ (im lặng theo yêu cầu owner)
# ---------------------------------------------------------------------------
def test_pending_ttl_prune():
    fresh = _prune_pending([{"msg_id": "old", "file_ids": ["fX"],
                             "create_at": NOW - PENDING_FILES_TTL_MS - 1}], now_ms=NOW)
    assert fresh == []
    keep = _prune_pending([{"msg_id": "new", "file_ids": ["fX"],
                            "create_at": NOW - PENDING_FILES_TTL_MS}], now_ms=NOW)
    assert len(keep) == 1


# ---------------------------------------------------------------------------
# 9. Ảnh hold từ trước + ảnh mới không mô tả → cả 2 cùng chờ
# ---------------------------------------------------------------------------
def test_two_undescribed_images_both_hold():
    held = [{"msg_id": "m1", "file_ids": ["fIMG"], "create_at": NOW - 60_000}]
    work, pending = _plan_batch([_img("m2", NOW, fid="fIMG")], held,
                                now_ms=NOW, image_check=ic)
    assert work == []
    assert {p["msg_id"] for p in pending} == {"m1", "m2"}


# ---------------------------------------------------------------------------
# 9b. Ảnh mới KHÔNG phải ảnh (PDF) + ảnh đang chờ → ảnh chờ giữ nguyên
# ---------------------------------------------------------------------------
def test_non_image_arrival_keeps_pending():
    held = [{"msg_id": "m1", "file_ids": ["fIMG"], "create_at": NOW - 60_000}]
    work, pending = _plan_batch([_img("d2", NOW, fid="fPDF")], held,
                                now_ms=NOW, image_check=ic)
    assert len(work) == 1 and work[0]["file_ids"] == ["fPDF"]
    assert len(pending) == 1 and pending[0]["msg_id"] == "m1"


# ---------------------------------------------------------------------------
# 10. Chữ TRƯỚC ảnh quá 2 phút → KHÔNG ghép (chữ thành việc AI riêng)
# ---------------------------------------------------------------------------
def test_stale_description_not_paired():
    msgs = [
        _txt("t1", "chào em, hôm nay thế nào", NOW - DESC_BEFORE_WINDOW_MS - 5),
        _img("i1", NOW),
    ]
    work, pending = _plan_batch(msgs, [], now_ms=NOW, image_check=ic)
    # ảnh HOLD; chữ quá hạn → việc AI bình thường (không kèm ảnh)
    assert len(pending) == 1 and pending[0]["msg_id"] == "i1"
    assert len(work) == 1 and work[0]["text"] == "chào em, hôm nay thế nào"
    assert work[0]["file_ids"] == []
