"""Test Sprint CHERRY-CÓ-TƯ-DUY — health_snapshot + rule 14 (26/11/2026).

Owner: "cherry chưa có quan điểm, suy nghĩ. hãy xây dựng để cherry có tư duy".
Đảm bảo: detector đúng câu hỏi thật của owner (image_92b084), snapshot probe
không bao giờ raise, render block có đủ phần yêu cầu quan điểm, rule 14 vào
system prompt, và các câu hỏi/lệnh thường KHÔNG bị kích hoạt oan.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BRAIN_ROOT = Path(__file__).resolve().parents[1]
if str(_BRAIN_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_BRAIN_ROOT / "src"))

from quan_ai_brain.tools.health_snapshot import (  # noqa: E402
    collect_health_snapshot,
    looks_like_analysis_query,
    render_health_snapshot_block,
)


# ---------------------------------------------------------------------------
# Detector — câu hỏi thật của owner (ảnh image_92b084 09:47)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query", [
    "em tư vấn thấy hệ thống của em có thiếu sót gì?",   # câu owner thật
    "em thấy hệ thống của em có thiếu sót gì?",           # biến thể không dấu tư vấn? (giữ 'thiếu sót')
    "đánh giá giúp em hệ thống hiện tại",
    "anh thấy em nên cải thiện gì",
    "bot có vấn đề gì không anh",
    "cherry suy nghĩ xem em còn hạn chế ở đâu",
])
def test_detector_positive_owner_style(query: str) -> None:
    assert looks_like_analysis_query(query) is True, query


@pytest.mark.parametrize("query", [
    "trạng thái",                      # lệnh hệ thống — phải vào router, không phải AI
    "mở chrome",                       # lệnh điều khiển
    "bật bài hát Tàu Anh Qua Núi",     # phát nhạc
    "chụp màn hình",                   # lệnh PC
    "help",                            # menu
    "hi",                              # chào
    "Ai là chủ tịch Việt Nam",         # tri thức chung (chứa 'việt nam')
    "thời tiết hôm nay thế nào",       # tri thức chung
    "em sinh ngày nào",                # về bản thân nhưng không phải phân tích
    "",                                # rỗng
])
def test_detector_negative_no_false_positive(query: str) -> None:
    assert looks_like_analysis_query(query) is False, query


# ---------------------------------------------------------------------------
# Snapshot — probe thật, fail-open tuyệt đối
# ---------------------------------------------------------------------------

def test_collect_health_snapshot_never_raises_and_has_keys() -> None:
    snap = collect_health_snapshot(current_model="zai-org/GLM-5.3-Flash")
    assert isinstance(snap, dict)
    assert "generated_at_utc" in snap
    # Các key chuẩn dù probe có lỗi gì đi nữa
    for key in ("components", "disk_e", "responder_heartbeat_age_s",
                "recent_errors", "self_improve_pending"):
        assert key in snap, key


def test_snapshot_disk_shape_when_available() -> None:
    snap = collect_health_snapshot()
    disk = snap.get("disk_e") or {}
    if disk:  # ổ E: tồn tại trên máy thật — luôn có 3 trường
        assert {"free_gb", "total_gb", "used_pct"} <= set(disk.keys())


def test_render_block_contains_opinion_directive() -> None:
    snap = collect_health_snapshot()
    block = render_health_snapshot_block(snap)
    assert "[SNAPSHOT SỨC KHỎE HỆ THỐNG" in block
    assert "YÊU CẦU TƯ DUY" in block          # bắt buộc đưa quan điểm
    assert "KHÔNG né" in block                 # cấm né kiểu "chưa đủ dữ kiện"
    assert "điểm đang TỐT" in block            # nêu cả 2 mặt


def test_render_block_with_empty_snapshot_does_not_crash() -> None:
    block = render_health_snapshot_block({
        "generated_at_utc": "2026-11-26T00:00:00+00:00",
        "components": {},
        "pi5": {},
        "disk_e": {},
        "responder_heartbeat_age_s": None,
        "recent_errors": [],
        "self_improve_pending": 0,
    })
    assert "KHÔNG THẤY" in block               # heartbeat không thấy → điểm nghi trọng
    assert "không thấy lỗi nổi bật" in block


# ---------------------------------------------------------------------------
# Rule 14 — tư duy phản biện trong DEFAULT_SYSTEM_INSTRUCTIONS
# ---------------------------------------------------------------------------

def test_system_prompt_has_rule14_critical_thinking() -> None:
    from quan_ai_brain.cognition.context_builder import DEFAULT_SYSTEM_INSTRUCTIONS
    assert "CÓ QUAN ĐIỂM — TƯ DUY PHẢN BIỆN" in DEFAULT_SYSTEM_INSTRUCTIONS
    assert "26/11" in DEFAULT_SYSTEM_INSTRUCTIONS
    # Luật cũ phải còn nguyên — không phá governance
    for must in ("R0-R5", "KHÔNG HỎI LÒNG VÒNG", "TIẾNG VIỆT"):
        assert must in DEFAULT_SYSTEM_INSTRUCTIONS, must


def test_context_builder_still_imports_and_builds() -> None:
    from quan_ai_brain.cognition.context_builder import PromptContextBuilder
    builder = PromptContextBuilder()
    ctx = builder.build(user_query="test rule 14")
    assert "CÓ QUAN ĐIỂM" in (ctx.system_instructions or "")
