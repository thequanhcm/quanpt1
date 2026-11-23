# -*- coding: utf-8 -*-
"""Sprint 1a EMAIL-INTAKE-REAL — test mock 100% (không gọi SOAP thật, không mạng).

Card TASK-OFFICE-S1 (đã APPROVED + consumed 23/11/2026).
Chỉ tạo file dưới tmp_path. mail_reader KHÔNG được gọi mạng trong test.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BRAIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN_ROOT / "src"))

from quan_ai_brain.integration.email_intake import (  # noqa: E402
    ConnectorStatus,
    EmailIntakeStore,
    EmailMessage,
)
from quan_ai_brain.office.email_connector import (  # noqa: E402
    EmailCategory10,
    EmailAnalysis,
    SOAPMailConnector,
    analyze_email,
    format_summary_ab,
    sync_and_analyze,
)


def _msg(mid: str, subject: str, body: str, sender: str = "a@viettel.com.vn") -> EmailMessage:
    return EmailMessage(
        message_id=mid,
        sender=sender,
        subject=subject,
        body_preview=body[:500],
        received_at_utc="2026-11-23T10:00:00+07:00",
        source="mock",
    )


class MockConnector:
    """Connector mock đúng interface — KHÔNG đụng hộp thư thật."""

    def __init__(self, messages: list[EmailMessage], status: ConnectorStatus = ConnectorStatus.CONNECTED):
        self._messages = messages
        self._status = status

    def status(self) -> ConnectorStatus:
        return self._status

    def fetch_recent(self, limit: int = 20) -> list[EmailMessage]:
        if self._status != ConnectorStatus.CONNECTED:
            return []
        return self._messages[:limit]


# ---------------------------------------------------------------------------
# Phân loại 10 nhóm
# ---------------------------------------------------------------------------

class TestClassify10:
    def test_urgent(self):
        a = analyze_email(_msg("m1", "GẤP: UPS trạm PDL cần xử lý", "Cần anh xác nhận ngay lập tức"))
        assert a.category == EmailCategory10.URGENT
        assert a.urgency_score >= 50

    def test_action_required(self):
        a = analyze_email(_msg("m2", "Đề nghị cung cấp số liệu quý 3", "Vui lòng gửi lại số liệu"))
        assert a.category == EmailCategory10.ACTION_REQUIRED

    def test_need_reply(self):
        a = analyze_email(_msg("m3", "Hỏi về tiến độ công việc", "Cho em biết tình trạng hiện tại"))
        assert a.category == EmailCategory10.NEED_REPLY

    def test_approval(self):
        a = analyze_email(_msg("m4", "Tờ trình kính trình ký", "Đề nghị anh phê duyệt hồ sơ"))
        assert a.category == EmailCategory10.APPROVAL

    def test_meeting(self):
        a = analyze_email(_msg("m5", "[Voffice] Lịch họp định kỳ", "Cuộc họp chủ trì bởi Giám đốc"))
        assert a.category == EmailCategory10.MEETING

    def test_information_fallback(self):
        a = analyze_email(_msg("m6", "Ảnh sự kiện team building", "Xem hình đẹp lắm"))
        assert a.category == EmailCategory10.INFORMATION

    def test_low_priority_newsletter(self):
        a = analyze_email(_msg("m7", "Khuyến mãi tháng 11", "Giảm giá 50%, unsubscribe tại đây"))
        assert a.category == EmailCategory10.LOW_PRIORITY

    def test_reference(self):
        a = analyze_email(_msg("m8", "Hướng dẫn sử dụng hệ thống", "Tài liệu tham khảo cho anh"))
        assert a.category == EmailCategory10.REFERENCE


# ---------------------------------------------------------------------------
# Deadline — explicit vs suggested (master prompt: không suy diễn khi không nêu rõ)
# ---------------------------------------------------------------------------

class TestDeadline:
    def test_deadline_explicit_time(self):
        a = analyze_email(_msg("d1", "Báo cáo tuần", "Vui lòng gửi báo cáo trước 17h thứ Sáu"))
        assert a.deadline != ""
        assert a.deadline_is_suggested is False

    def test_deadline_explicit_date(self):
        a = analyze_email(_msg("d2", "Đăng ký đào tạo", "Hoàn thành đăng ký trước 25/11"))
        assert "25/11" in a.deadline or "25-11" in a.deadline
        assert a.deadline_is_suggested is False

    def test_deadline_suggested_marked(self):
        a = analyze_email(_msg("d3", "Kế hoạch tháng", "Anh xem và phản hồi sớm nhất có thể"))
        assert a.deadline_is_suggested is True

    def test_no_deadline_no_invention(self):
        a = analyze_email(_msg("d4", "Ảnh họp", "Gửi anh bộ ảnh họp hôm qua"))
        # Không nêu thời hạn → KHÔNG được suy diễn deadline
        assert a.deadline == ""

    def test_deadline_goes_to_urgency(self):
        a1 = analyze_email(_msg("d5", "Việc gấp", "Cần xử lý trước 17h"))
        a2 = analyze_email(_msg("d6", "Việc gấp", "Cần xử lý khi tiện"))
        assert a1.urgency_score > a2.urgency_score


# ---------------------------------------------------------------------------
# Score + EmailAnalysis shape (master prompt §II.2 fields)
# ---------------------------------------------------------------------------

class TestScores:
    def test_score_range(self):
        for mid, sub, body in [
            ("s1", "GẤP", "xử lý ngay"),
            ("s2", "FYI", "tham khảo"),
            ("s3", "Họp", "lịch họp"),
        ]:
            a = analyze_email(_msg(mid, sub, body))
            assert 0 <= a.priority_score <= 100
            assert 0 <= a.urgency_score <= 100
            assert 0 <= a.confidence <= 1

    def test_to_dict_has_all_fields(self):
        a = analyze_email(_msg("s4", "Đề nghị", "vui lòng xử lý"))
        d = a.to_dict()
        for key in ("category10", "priority_score", "urgency_score", "action_required",
                    "deadline", "deadline_is_suggested", "suggested_next_action",
                    "confidence", "related_project"):
            assert key in d, f"missing {key}"


# ---------------------------------------------------------------------------
# sync_and_analyze + store integration (mock connector, tmp_path DB)
# ---------------------------------------------------------------------------

class TestSyncAndAnalyze:
    def test_sync_new_and_dedupe(self, tmp_path):
        store = EmailIntakeStore(tmp_path / "intake.db")
        conn = MockConnector([
            _msg("x1", "GẤP xử lý", "cần ngay"),
            _msg("x2", "Lịch họp", "cuộc họp"),
        ])
        result, analyses = sync_and_analyze(conn, store)
        assert result.new == 2
        assert result.duplicates == 0
        assert len(analyses) == 2
        # sync lại → dedupe
        result2, analyses2 = sync_and_analyze(conn, store)
        assert result2.new == 0
        assert result2.duplicates == 2
        assert len(analyses2) == 0
        assert store.count() == 2

    def test_sync_disconnected_fail_honest(self, tmp_path):
        store = EmailIntakeStore(tmp_path / "intake2.db")
        conn = MockConnector([], status=ConnectorStatus.BLOCKED)
        result, analyses = sync_and_analyze(conn, store)
        assert result.connector_status == ConnectorStatus.BLOCKED
        assert result.error != ""  # báo lỗi trung thực, không fake
        assert analyses == []

    def test_sync_connector_exception(self, tmp_path):
        store = EmailIntakeStore(tmp_path / "intake3.db")

        class BoomConnector:
            def status(self):
                return ConnectorStatus.CONNECTED

            def fetch_recent(self, limit=20):
                raise RuntimeError("SOAP lỗi mạng")

        result, analyses = sync_and_analyze(BoomConnector(), store)
        assert analyses == []
        assert result.connector_status == ConnectorStatus.UNKNOWN
        assert "SOAP" in result.error or "lỗi" in result.error.lower()


# ---------------------------------------------------------------------------
# format_summary_ab — format A/B master prompt §II.3
# ---------------------------------------------------------------------------

class TestFormatSummary:
    def test_summary_contains_a_and_b(self, tmp_path):
        store = EmailIntakeStore(tmp_path / "intake4.db")
        conn = MockConnector([
            _msg("f1", "GẤP: ký hồ sơ", "phê duyệt trước 17h"),
            _msg("f2", "Hỏi số liệu", "cho em biết tiến độ"),
        ])
        result, analyses = sync_and_analyze(conn, store)
        text = format_summary_ab(result, analyses)
        assert "A. TỔNG QUAN" in text
        assert "B. EMAIL QUAN TRỌNG" in text
        assert "Priority" in text
        assert "17h" in text  # deadline explicit hiển thị

    def test_summary_empty(self):
        from quan_ai_brain.integration.email_intake import IntakeResult
        result = IntakeResult(connector_status=ConnectorStatus.CONNECTED, new=0)
        text = format_summary_ab(result, [])
        assert "A. TỔNG QUAN" in text
        assert "Không có email mới" in text


# ---------------------------------------------------------------------------
# SOAPMailConnector — status check KHÔNG gọi mạng (chỉ kiểm secret tồn tại)
# ---------------------------------------------------------------------------

class TestSOAPConnector:
    def test_status_not_configured_when_no_secret(self, monkeypatch):
        # Giả lập thiếu secret → NOT_CONFIGURED (không gọi mạng)
        import types
        fake_mr = types.ModuleType("mail_reader")
        def boom():
            raise RuntimeError("Chưa có thông tin đăng nhập")
        fake_mr._creds = boom
        import quan_ai_brain.office.email_connector as ec
        monkeypatch.setitem(sys.modules, "mail_reader", fake_mr)
        c = SOAPMailConnector()
        assert c.status() == ConnectorStatus.NOT_CONFIGURED

    def test_status_connected_when_creds_ok(self, monkeypatch):
        import types
        fake_mr = types.ModuleType("mail_reader")
        fake_mr._creds = lambda: ("user@viettel.com.vn", "dummy")
        monkeypatch.setitem(sys.modules, "mail_reader", fake_mr)
        c = SOAPMailConnector()
        assert c.status() == ConnectorStatus.CONNECTED

    def test_fetch_recent_maps_fields(self, monkeypatch):
        import types
        fake_mr = types.ModuleType("mail_reader")
        fake_mr.read_latest = lambda n: {
            "emails": [
                {"id": "123", "subject": "GẤP thử nghiệm", "from_addr": "x@y.vn",
                 "date": "2026-11-23 10:00", "fragment": "mảnh",
                 "body_preview": "nội dung thử", "has_attachment": False, "read": True},
            ]
        }
        monkeypatch.setitem(sys.modules, "mail_reader", fake_mr)
        c = SOAPMailConnector()
        msgs = c.fetch_recent(5)
        assert len(msgs) == 1
        m = msgs[0]
        assert m.message_id == "vmail-123"
        assert m.source == "vmail_soap"
        assert m.sender == "x@y.vn"

    def test_fetch_recent_error_raises(self, monkeypatch):
        import types
        fake_mr = types.ModuleType("mail_reader")
        fake_mr.read_latest = lambda n: {"error": "Không kết nối được"}
        monkeypatch.setitem(sys.modules, "mail_reader", fake_mr)
        c = SOAPMailConnector()
        with pytest.raises(RuntimeError):
            c.fetch_recent(5)
