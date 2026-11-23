# -*- coding: utf-8 -*-
"""Tests ThreadAnalyzer (CHERRY VMAIL INTELLIGENCE Sprint 2, card TASK-VMAIL-S2).

Mock 100% — KHÔNG gọi SOAP thật. Bao phủ:
1. normalize_subject: RE/FW prefix, tag [Hủy cuộc họp] tách khỏi key
2. build_threads: ghép ĐÚNG gốc "Mời họp" + "[Hủy cuộc họp]" (tiêu chí P1-3)
3. analyze_thread: 10 mục §5.3 đủ + nguồn
4. Mâu thuẫn §5.3: hủy vs mời → CẢ HAI + nguồn, không kết luận hộ
5. format_thread_summary: 8 mục §5.4, dẫn nguồn
6. format_10_items: đủ 10 mục
7. Edge: rỗng, 1 mail, không deadline, mail mới nhất từ owner
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.office.thread_analyzer import (  # noqa: E402
    ThreadAnalysis,
    analyze_thread,
    build_threads,
    format_10_items,
    format_thread_summary,
    normalize_subject,
)


def _m(mid, subject, body="", date="2026-11-23 09:00", name="Nguyễn Văn A",
       addr="nva@viettel.com.vn", frag=""):
    return {"id": str(mid), "date": date, "subject": subject, "from_name": name,
            "from_addr": addr, "fragment": frag, "body_preview": body,
            "has_attachment": False}


# ---- 1. normalize_subject ----
class TestNormalizeSubject:
    def test_strips_re_prefix(self):
        key, _ = normalize_subject("RE: Mời họp dự án X")
        assert key == "mời họp dự án x".replace(" ", " ") or key == "mời họp dự án x"

    def test_strips_fw_prefix(self):
        key, _ = normalize_subject("FW: FWD: RE: Báo cáo tuần")
        assert "báo cáo tuần" in key

    def test_cancel_tag_removed_from_key(self):
        key, tags = normalize_subject("[Hủy cuộc họp] Mời họp dự án X")
        assert "họp dự án x" in key
        assert "hủy" not in key.split()  # tag đã tách
        assert "HỦY_CUỘC_HỌP" in tags

    def test_postpone_tag(self):
        _, tags = normalize_subject("Hoãn cuộc họp Sprint 5")
        assert any("HOÃN" in t or "DỜI" in t for t in tags)

    def test_plain_subject_untouched(self):
        key, tags = normalize_subject("Báo cáo tiến độ tuần 48")
        assert "báo cáo tiến độ tuần 48" in key
        assert tags == []


# ---- 2. build_threads — tiêu chí nghiệm thu P1-3 ----
class TestBuildThreads:
    def test_cancel_mail_groups_with_original(self):
        """TIÊU CHÍ NGHIỆM THU: '[Hủy cuộc họp]' ghép ĐÚNG với mail gốc."""
        msgs = [
            _m(1, "Mời họp dự án Battery AI", date="2026-11-20 09:00"),
            _m(2, "[Hủy cuộc họp] Mời họp dự án Battery AI", date="2026-11-21 10:00"),
            _m(3, "RE: Mời họp dự án Battery AI", date="2026-11-22 11:00"),
        ]
        th = build_threads(msgs)
        assert len(th) == 1, f"3 mail phải thành 1 luồng, nhận {len(th)}: {list(th)}"
        assert len(th[list(th)[0]]) == 3

    def test_different_subjects_separate(self):
        th = build_threads([_m(1, "Mời họp A"), _m(2, "Báo cáo B")])
        assert len(th) == 2

    def test_messages_sorted_oldest_first(self):
        msgs = [
            _m(3, "RE: X", date="2026-11-23 10:00"),
            _m(1, "X", date="2026-11-20 09:00"),
            _m(2, "RE: X", date="2026-11-21 10:00"),
        ]
        th = build_threads(msgs)
        key = list(th)[0]
        assert [m.id for m in th[key]] == ["1", "2", "3"]


# ---- 3+4. analyze_thread — 10 mục + mâu thuẫn ----
def _sample_thread():
    return [
        _m(101, "Mời họp rà soát Battery AI",
           body="Kính gửi anh, đề nghị anh tham dự cuộc họp rà soát Battery AI "
                "lúc 9h thứ Năm. Anh vui lòng xác nhận tham dự trước 17h hôm nay.",
           date="2026-11-20 09:00", name="Trần B", addr="trb@viettel.com.vn"),
        _m(102, "[Hủy cuộc họp] Mời họp rà soát Battery AI",
           body="Do phòng họp bị trùng, cuộc họp rà soát Battery AI được hủy. "
                "Chúng tôi sẽ thông báo lịch mới.",
           date="2026-11-21 10:00", name="Trần B", addr="trb@viettel.com.vn"),
        _m(103, "RE: Mời họp rà soát Battery AI",
           body="Em xác nhận đã nhận thông tin. Vụ này em sẽ cập nhật tiến độ "
                "trước 25/11.",
           date="2026-11-22 11:00", name="Phạm Thế Quân", addr="quanpt1@viettel.com.vn"),
    ]


class TestAnalyzeThread:
    def test_10_items_populated(self):
        th = build_threads(_sample_thread())
        a = analyze_thread(list(th.values())[0])
        assert a.initial is not None and a.initial.id == "101"
        assert len(a.replies) == 2
        assert len(a.participants) == 2
        assert a.requests, "phải bắt được 'đề nghị anh tham dự'"
        assert any("#101" in r for r in a.requests), "mỗi item phải dẫn nguồn"
        assert a.commitments, "phải bắt 'em sẽ cập nhật'"
        assert a.unresolved
        assert "mail #103" in a.status or "#103" in a.status

    def test_contradiction_cancel_vs_invite_both_sides(self):
        """§5.3: hủy vs mời → trình bày CẢ HAI + nguồn, KHÔNG kết luận hộ."""
        th = build_threads(_sample_thread())
        a = analyze_thread(list(th.values())[0])
        assert a.contradictions, "phải phát hiện mâu thuẫn hủy vs mời"
        c = a.contradictions[0]
        assert "#101" in c and "#102" in c, "phải dẫn nguồn CẢ HAI mail"
        assert "THÔNG BÁO" in c and "HỦY" in c

    def test_waiting_on_owner_when_last_mail_is_incoming(self):
        th = build_threads([_m(1, "X", body="Anh vui lòng gửi báo cáo.", name="Trần B",
                               addr="trb@viettel.com.vn")])
        a = analyze_thread(list(th.values())[0])
        assert "ANH (owner)" in a.status

    def test_single_message_thread(self):
        a = analyze_thread([ThreadAnalyzerMsg(_m(9, "Đơn lẻ"))] if False else
                           list(build_threads([_m(9, "Đơn lẻ")]).values())[0])
        assert a.initial.id == "9" and a.replies == []

    def test_no_deadline_claimed_when_absent(self):
        th = build_threads([_m(5, "Thư chúc mừng", body="Chúc mừng sinh nhật anh!")])
        a = analyze_thread(list(th.values())[0])
        assert a.requests == [] and a.decisions == []

    def test_confidence_range(self):
        th = build_threads(_sample_thread())
        a = analyze_thread(list(th.values())[0])
        assert 0.0 <= a.confidence <= 1.0


# ---- 5. format_thread_summary — 8 mục §5.4 ----
class TestFormatSummary:
    def test_8_sections_with_sources(self):
        th = build_threads(_sample_thread())
        a = analyze_thread(list(th.values())[0])
        s = format_thread_summary(a)
        for marker in ("TỔNG QUAN", "DIỄN BIẾN", "CÁC BÊN", "YÊU CẦU", "DEADLINE",
                       "QUYẾT ĐỊNH", "VẤN ĐỀ CHƯA GIẢI QUYẾT", "ĐỀ XUẤT"):
            assert marker in s, f"thiếu mục {marker}"
        assert "#101" in s  # dẫn nguồn

    def test_missing_sections_are_honest(self):
        th = build_threads([_m(5, "Thư chúc mừng", body="Chúc mừng anh!")])
        s = format_thread_summary(analyze_thread(list(th.values())[0]))
        assert "(không phát hiện yêu cầu tường minh)" in s or "(không có deadline" in s


# ---- 6. format_10_items ----
class TestFormat10Items:
    def test_all_10_sections_present(self):
        th = build_threads(_sample_thread())
        a = analyze_thread(list(th.values())[0])
        s = format_10_items(a)
        for i, marker in enumerate(
            ["Nội dung ban đầu", "Các lần phản hồi", "Người tham gia", "Các yêu cầu",
             "Các câu hỏi", "Các cam kết", "Các quyết định", "Các nội dung thay đổi",
             "Vấn đề còn tồn tại", "Trạng thái hiện tại"], 1
        ):
            assert f"{i}. {marker}" in s, f"thiếu mục {i}: {marker}"


# ---- 7. Edge cases ----
class TestEdge:
    def test_empty_raises(self):
        import pytest
        with pytest.raises(ValueError):
            analyze_thread([])

    def test_dict_conversion_roundtrip(self):
        th = build_threads(_sample_thread())
        a = analyze_thread(list(th.values())[0])
        d = a.to_dict()
        assert d["message_count"] == 3
        assert d["participants"] == a.participants
