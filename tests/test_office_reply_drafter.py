# -*- coding: utf-8 -*-
"""Sprint 4 REPLY-DRAFT — tests (card TASK-VMAIL-S4).

Mock 100% (không SOAP, không network, .eml ghi vào tmp_path). Kiểm tra:
- §7.2: đủ 11 style; greeting/sign-off đúng; style sai → lỗi rõ.
- §7.1: ReplyContext.from_thread_analysis lấy questions/decisions/deadlines/
  contradictions CÓ THẬT từ ThreadAnalysis; subject thêm RE: đúng.
- §7.3: 8 mục quality check — câu hỏi chưa trả lời, mâu thuẫn, hủy vs xác nhận,
  cam kết vượt thẩm quyền, nhạy cảm, thiếu người nhận; không cảnh báo khi sạch.
- §7.4: build_reply ghi .eml qua email_draft (mock dir), KHÔNG có đường send;
  thiếu dữ liệu → fail-honest; custom_body được dùng nguyên.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quan_ai_brain.office.reply_drafter import (  # noqa: E402
    REPLY_STYLES, DraftResult, ReplyContext, ReplyDrafter,
)


@dataclass
class FakeAnalysis:
    """ThreadAnalysis tối giản của Sprint 2."""
    key: str = "k"
    subject_display: str = "Re: Yêu cầu báo cáo tuần"
    participants: list[str] = field(default_factory=lambda: ["linhtq3", "Z78_1"])
    questions: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    deadlines: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    commitments: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)


@pytest.fixture()
def drafter(tmp_path):
    """Drafter với memory adapter mock + draft dir tạm."""
    from quan_ai_brain.office import reply_drafter as rd
    mem = type("FakeAdapter", (), {"retrieve_context": staticmethod(
        lambda q, top_k=3: type("R", (), {"error": "", "hits": []})())})()
    d = ReplyDrafter(memory_adapter=mem)
    return d


# ---------- §7.2 styles ----------
class TestStyles:
    def test_11_styles_complete(self):
        assert len(REPLY_STYLES) == 11
        assert set(REPLY_STYLES) == {
            "ngan_gon", "chuyen_nghiep", "hanh_chinh", "ky_thuat", "giai_trinh",
            "xac_nhan", "tu_choi_lich_su", "de_nghi_phoi_hop", "nhac_tien_do",
            "phan_hoi_dut_khoat", "tieng_anh"}

    def test_invalid_style_rejected(self, drafter):
        ctx = ReplyContext(subject="RE: test", points=["ý 1"])
        res = drafter.build_reply(ctx, style="khong_co", write_eml=False)
        assert not res.ok and "Style không hợp lệ" in res.error

    def test_each_style_produces_body(self, drafter):
        ctx = ReplyContext(subject="RE: báo cáo", points=["ý A"],
                           recipient="Linh", recipient_email="l@viettel.com.vn")
        for style in REPLY_STYLES:
            res = drafter.build_reply(ctx, style=style, write_eml=False)
            assert res.ok, f"style {style} fail: {res.error}"
            assert res.body.strip(), f"style {style} body rỗng"

    def test_greeting_and_signoff(self, drafter):
        ctx = ReplyContext(subject="RE: test", points=["ý"], recipient="Linh")
        res = drafter.build_reply(ctx, style="chuyen_nghiep", write_eml=False)
        assert "Kính gửi Linh" in res.body
        assert "Trân trọng" in res.body

    def test_english_style(self, drafter):
        ctx = ReplyContext(subject="RE: report", points=["point A"],
                           recipient="Linh", recipient_en="Mr. Linh")
        res = drafter.build_reply(ctx, style="tieng_anh", write_eml=False)
        assert "Dear Mr. Linh" in res.body


# ---------- §7.1 context ----------
class TestReplyContext:
    def test_from_thread_analysis(self):
        ana = FakeAnalysis(
            subject_display="Re: Yêu cầu báo cáo tuần",
            questions=["Số liệu quý IV lấy từ nguồn nào?"],
            decisions=["Chốt format bảng Excel"],
            deadlines=["Trước 25/11"],
            contradictions=["mâu thuẫn A ⇄ B"])
        ctx = ReplyContext.from_thread_analysis(ana, recipient_email="l@viettel.com.vn")
        assert ctx.subject == "Re: Yêu cầu báo cáo tuần"  # đã có RE: — không nhân đôi
        assert ctx.recipient == "linhtq3"
        assert ctx.questions_pending == ["Số liệu quý IV lấy từ nguồn nào?"]
        assert ctx.decisions and ctx.deadlines and ctx.contradictions

    def test_subject_prefix_re_added(self):
        ana = FakeAnalysis(subject_display="Họp sprint")
        ctx = ReplyContext.from_thread_analysis(ana)
        assert ctx.subject == "RE: Họp sprint"

    def test_cancelled_thread_detected(self):
        ana = FakeAnalysis(subject_display="[Hủy cuộc họp] Họp sprint 25/11")
        ctx = ReplyContext.from_thread_analysis(ana)
        assert ctx.thread_cancelled is True


# ---------- §7.3 quality check ----------
class TestQualityCheck:
    def test_unanswered_question_warned(self, drafter):
        # Style xac_nhan KHÔNG in phần câu hỏi chờ → body không đề cập → warn.
        ctx = ReplyContext(subject="RE: test", points=["ý"],
                           questions_pending=["Số liệu quý IV lấy nguồn nào?"])
        body = drafter._build_body(ctx, "xac_nhan")
        w = drafter.quality_check(ctx, body)
        assert any("§7.3.1" in x for x in w)

    def test_contradiction_warned(self, drafter):
        ctx = ReplyContext(subject="RE: test", points=["ý"],
                           contradictions=["hạn 25/11 ⇄ hạn 30/11"])
        w = drafter.quality_check(ctx, "Nội dung bình thường.")
        assert any("§7.3.3" in x for x in w)

    def test_cancel_vs_confirm_warned(self, drafter):
        ctx = ReplyContext(subject="RE: test", points=["ý"], thread_cancelled=True)
        w = drafter.quality_check(ctx, "Em xác nhận tham dự cuộc họp nhé.")
        assert any("§7.3.3" in x and "HỦY" in x for x in w)

    def test_overcommit_warned(self, drafter):
        ctx = ReplyContext(subject="RE: test", points=["ý"], recipient_email="a@b.vn")
        w = drafter.quality_check(ctx, "Em chắc chắn sẽ xong trước 25/11.")
        assert any("§7.3.6" in x for x in w)

    def test_sensitive_warned(self, drafter):
        ctx = ReplyContext(subject="RE: test", points=["ý"], recipient_email="a@b.vn")
        w = drafter.quality_check(ctx, "Mật khẩu hệ thống là abc.")
        assert any("§7.3.7" in x for x in w)

    def test_missing_recipient_warned(self, drafter):
        ctx = ReplyContext(subject="RE: test", points=["ý"])
        w = drafter.quality_check(ctx, "Nội dung sạch.")
        assert any("§7.3.8" in x for x in w)

    def test_clean_body_no_warnings(self, drafter):
        ctx = ReplyContext(subject="RE: test", points=["ý"],
                           recipient_email="a@b.vn")
        w = drafter.quality_check(ctx, "Đã nhận được email. Em sẽ phản hồi chi tiết sau.")
        assert w == []


# ---------- §7.1/§7.4 build + eml ----------
class TestBuildReply:
    def test_missing_data_fail_honest(self, drafter):
        res = drafter.build_reply(ReplyContext(), write_eml=False)
        assert not res.ok and "Không đủ dữ liệu" in res.error

    def test_template_uses_real_points(self, drafter):
        ctx = ReplyContext(subject="RE: báo cáo", points=["Đã gửi báo cáo 24/11"])
        res = drafter.build_reply(ctx, write_eml=False)
        assert "Đã gửi báo cáo 24/11" in res.body

    def test_no_points_honest_placeholder(self, drafter):
        ctx = ReplyContext(subject="RE: báo cáo")
        res = drafter.build_reply(ctx, write_eml=False)
        assert "không bịa" in res.body

    def test_custom_body_used_verbatim(self, drafter):
        ctx = ReplyContext(subject="RE: test", recipient="Linh",
                           recipient_email="l@viettel.com.vn")
        res = drafter.build_reply(ctx, custom_body="Nội dung do GLM soạn sẵn.",
                                  write_eml=False)
        assert "Nội dung do GLM soạn sẵn." in res.body

    def test_writes_eml(self, drafter, tmp_path, monkeypatch):
        from quan_ai_brain.tools import email_draft as ed
        monkeypatch.setattr(ed, "DRAFT_DIR", tmp_path)
        ctx = ReplyContext(subject="RE: báo cáo tuần", points=["Đã gửi"],
                           recipient="Linh", recipient_email="linhtq3@viettel.com.vn")
        res = drafter.build_reply(ctx, style="chuyen_nghiep",
                                  task_id="T-1", source_email_id="39012")
        assert res.ok and res.eml_path
        p = Path(res.eml_path)
        assert p.exists() and p.suffix == ".eml"
        raw = p.read_text(encoding="utf-8", errors="replace")
        assert "Subject: RE: báo cáo tuần" in raw or "RE: báo cáo" in raw
        assert "X-QAB-Task-Id: T-1" in raw
        assert "X-QAB-Source-Email-Id: 39012" in raw
        assert "Kính gửi Linh" in raw

    def test_no_send_path(self, drafter):
        """§7.4 bất biến: ReplyDrafter KHÔNG có method gửi."""
        assert not hasattr(drafter, "send")
        assert not hasattr(drafter, "send_message")
        assert not hasattr(drafter, "smtp")

    def test_preview_format(self, drafter):
        ctx = ReplyContext(subject="RE: test", points=["ý"],
                           recipient_email="a@b.vn")
        res = drafter.build_reply(ctx, write_eml=False)
        text = ReplyDrafter.format_preview(res)
        assert "BẢN NHÁP" in text and "R2" in text and "Style:" in text

    def test_memory_gathered(self, tmp_path):
        """§7.1.3: memory hits từ adapter S3 được lấy trong build_reply."""
        from quan_ai_brain.office import reply_drafter as rd
        hit = type("H", (), {"content": "quyết định chốt format",
                             "verification": "OBSERVED", "fact_level": "OBSERVED"})()
        mem = type("FakeAdapter", (), {"retrieve_context": staticmethod(
            lambda q, top_k=3: type("R", (), {"error": "", "hits": [hit]})())})()
        d = ReplyDrafter(memory_adapter=mem)
        ctx = ReplyContext(subject="RE: format báo cáo", points=["ý"])
        res = d.build_reply(ctx, write_eml=False)
        assert res.ok
        assert ctx.memory_hits and "OBSERVED" in ctx.memory_hits[0]

    def test_memory_error_degraded(self, tmp_path):
        """Memory lỗi → draft vẫn soạn được (degraded, không crash)."""
        mem = type("BadAdapter", (), {"retrieve_context": staticmethod(
            lambda q, top_k=3: (_ for _ in ()).throw(RuntimeError("db")))} )()
        d = ReplyDrafter(memory_adapter=mem)
        ctx = ReplyContext(subject="RE: test", points=["ý"])
        res = d.build_reply(ctx, write_eml=False)
        assert res.ok and res.body
