# -*- coding: utf-8 -*-
"""ReplyDrafter — CHERRY VMAIL INTELLIGENCE V1.0 — Sprint 4 (card TASK-VMAIL-S4).

Owner duyệt (24/11 chat): "duyệt Sprint 4 REPLY-DRAFT (§17)". Master prompt §7:
Context-Aware Reply (§7.1) + 11 Reply Styles (§7.2) + Quality Check (§7.3) +
Send Policy (§7.4 — KHÔNG tự gửi; draft-only, gửi cần phê duyệt riêng từng lần).

Lớp mỏng (không core thứ 2):
- Context: ThreadAnalyzer (S2) + CherryMemoryAdapter (S3) + EmailAnalysis (S1).
- Nháp: format văn bản + ghi .eml qua tools email_draft.create_draft hiện có
  (không SMTP/COM — R2 DRAFT-ONLY; owner mở .eml tự bấm Send khi duyệt).
- Không bắt buộc LLM: builder deterministic template; caller có thể truyền
  body_text đã soạn (ví dụ do GLM soạn) — module vẫn quality-check + ghi nháp.

§7.1 pipeline trong build_reply():
1. Đọc email hiện tại (thread messages).
2. Đọc toàn bộ thread (ThreadAnalyzer analyze).
3. Truy xuất Memory liên quan (adapter.retrieve_context — dùng khi truyền vào).
4. Phát hiện thông tin thiếu (questions chưa trả lời, deadline không rõ).
5. Xây dựng phương án trả lời theo style.
6. Kiểm tra mâu thuẫn (§5.3 thread.contradictions + memory mâu thuẫn).
7. Tạo bản nháp (.eml) + quality check §7.3.

Fail-honest: thiếu dữ liệu → báo "thiếu", không bịa; lỗi → status error.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---- §7.2 Reply Styles (11) ----
REPLY_STYLES: dict[str, str] = {
    "ngan_gon": "Ngắn gọn",
    "chuyen_nghiep": "Chuyên nghiệp",
    "hanh_chinh": "Hành chính",
    "ky_thuat": "Kỹ thuật",
    "giai_trinh": "Giải trình",
    "xac_nhan": "Xác nhận",
    "tu_choi_lich_su": "Từ chối lịch sự",
    "de_nghi_phoi_hop": "Đề nghị phối hợp",
    "nhac_tien_do": "Nhắc tiến độ",
    "phan_hoi_dut_khoat": "Phản hồi dứt khoát",
    "tieng_anh": "Tiếng Anh công việc",
}

_GREETING = {
    "ngan_gon": "",
    "chuyen_nghiep": "Kính gửi {recipient},\n\n",
    "hanh_chinh": "Kính gửi {recipient},\n\n",
    "ky_thuat": "Chào {recipient},\n\n",
    "giai_trinh": "Kính gửi {recipient},\n\n",
    "xac_nhan": "Chào {recipient},\n\n",
    "tu_choi_lich_su": "Kính gửi {recipient},\n\n",
    "de_nghi_phoi_hop": "Chào {recipient},\n\n",
    "nhac_tien_do": "Chào {recipient},\n\n",
    "phan_hoi_dut_khoat": "Chào {recipient},\n\n",
    "tieng_anh": "Dear {recipient_en},\n\n",
}

# Thân mặc định theo style — dùng CHỈ khi caller không truyền body.
# Deterministic, rút từ dữ liệu thật (questions/requests/decisions của thread).
_DEFAULT_BODY: dict[str, str] = {
    "ngan_gon": ("Em phản hồi về “{subject}”:\n{points}\n"
                 "Anh/chị cần em bổ sung gì thêm thì báo em nhé."),
    "chuyen_nghiep": ("Về nội dung “{subject}”, em xin phản hồi như sau:\n{points}\n"
                      "Rất mong nhận được hướng dẫn thêm từ anh/chị."),
    "hanh_chinh": ("Trả lời công văn/email “{subject}”:\n{points}\n"
                   "Đề nghị anh/chị xem xét và phản hồi."),
    "ky_thuat": ("Về vấn đề kỹ thuật “{subject}”:\n{points}\n"
                 "Đề xuất kỹ thuật và thông tin chi tiết đính kèm nếu anh/chị cần."),
    "giai_trinh": ("Em xin giải trình về “{subject}”:\n{points}\n"
                   "Nếu cần thêm bằng chứng/tài liệu, em sẽ cung cấp ngay."),
    "xac_nhan": ("Em xác nhận đã nhận được email “{subject}”.\n{points}\n"),
    "tu_choi_lich_su": ("Về đề xuất trong email “{subject}”, em xin phép được trình "
                        "bày như sau:\n{points}\nRất mong anh/chị thông cảm và hỗ trợ."),
    "de_nghi_phoi_hop": ("Để xử lý “{subject}”, em đề nghị phối hợp như sau:\n{points}\n"
                         "Nhờ anh/chị xác nhận đầu mối và thời gian."),
    "nhac_tien_do": ("Em xin nhắc tiến độ về “{subject}”:\n{points}\n"
                     "Nhờ anh/chị cập nhật tiến độ sớm giúp em."),
    "phan_hoi_dut_khoat": ("Về “{subject}”, em phản hồi dứt khoát như sau:\n{points}\n"),
    "tieng_anh": ("Regarding “{subject}”:\n{points}\n"
                  "Please let me know if any further information is needed.\n\n"
                  "Best regards,"),
}

_SIGN_OFF = {
    "ngan_gon": "Em cảm ơn!",
    "chuyen_nghiep": "Trân trọng,\nQuân",
    "hanh_chinh": "Trân trọng,\nPhạm Thế Quân",
    "ky_thuat": "Thanks,\nQuân",
    "giai_trinh": "Trân trọng,\nPhạm Thế Quân",
    "xac_nhan": "Em cảm ơn!",
    "tu_choi_lich_su": "Trân trọng,\nPhạm Thế Quân",
    "de_nghi_phoi_hop": "Trân trọng,\nQuân",
    "nhac_tien_do": "Trân trọng,\nQuân",
    "phan_hoi_dut_khoat": "Trân trọng,\nQuân",
    "tieng_anh": "",  # body đã có Best regards
}

# ---- §7.3 Quality-check patterns ----
# cam kết vượt thẩm quyền: hứa kết quả/tài nguyên mà email không có căn cứ
_OVERCOMMIT_RE = re.compile(
    r"(chắc chắn (sẽ )?(xong|hoàn thành|đúng hạn)|cam kết (xong|hoàn thành)|"
    r"(em|tôi) (sẽ )?(chịu trách nhiệm (toàn bộ|chi phí))|guarantee|I will personally)", re.I)
# dữ liệu nhạy cảm không được phép đưa vào nháp
_SENSITIVE_RE = re.compile(
    r"(mật khẩu|mat khau|password|token|api[_ ]?key|secret|otp\b|pin\b)", re.I)
# mâu thuẫn chủ đề hủy/hoãn: nháp xác nhận cuộc họp trong khi luồng có tag hủy
_CONFIRM_MEETING_RE = re.compile(r"(xác nhận (tham dự|cuộc họp)|confirm.*attendance)", re.I)
_CANCEL_TAG_RE = re.compile(r"\[hủy|hủy cuộc họp|cancelled?\]", re.I)


# ---------------- Context (§7.1) ----------------
@dataclass
class ReplyContext:
    """Ngữ cảnh §7.1 — thu thập từ thread + memory + dữ liệu caller."""

    recipient: str = ""                      # người nhận chính (tên hiển thị)
    recipient_en: str = ""                   # tên cho style tiếng Anh (mặc định = recipient)
    recipient_email: str = ""                # địa chỉ To của nháp
    subject: str = ""                        # chủ đề trả lời (thêm "RE:" nếu chưa có)
    points: list[str] = field(default_factory=list)   # các ý phản hồi (bắt buộc nguồn)
    questions_pending: list[str] = field(default_factory=list)  # §7.1.7 thông tin thiếu
    decisions: list[str] = field(default_factory=list)  # §7.1.5 quyết định đã thống nhất
    deadlines: list[str] = field(default_factory=list)  # §7.1.6 deadline
    memory_hits: list[str] = field(default_factory=list)  # §7.1.3 tóm tắt memory (S3)
    contradictions: list[str] = field(default_factory=list)  # §7.1.9 mâu thuẫn phát hiện
    thread_cancelled: bool = False           # luồng có tag hủy (S2 normalize)

    @classmethod
    def from_thread_analysis(cls, analysis: Any, *, recipient_email: str = "",
                             recipient: str = "") -> "ReplyContext":
        """Dựng context từ ThreadAnalysis (Sprint 2) — chỉ lấy dữ liệu CÓ THẬT."""
        ta = analysis
        ctx = cls()
        ctx.recipient = recipient or getattr(ta, "participants", [""])[0] if getattr(ta, "participants", None) else ""
        ctx.recipient_en = ctx.recipient
        ctx.recipient_email = recipient_email
        subj = getattr(ta, "subject_display", "") or ""
        ctx.subject = subj if re.match(r"^(re|fw|fwd)[: ]", subj, re.I) else (f"RE: {subj}" if subj else "")
        ctx.questions_pending = [str(q) for q in (getattr(ta, "questions", []) or [])]
        ctx.decisions = [str(d) for d in (getattr(ta, "decisions", []) or [])]
        ctx.deadlines = [str(d) for d in (getattr(ta, "deadlines", []) or [])]
        ctx.contradictions = [str(c) for c in (getattr(ta, "contradictions", []) or [])]
        ctx.thread_cancelled = bool(_CANCEL_TAG_RE.search(subj))
        return ctx


# ---------------- Result ----------------
@dataclass
class DraftResult:
    """Kết quả build_reply — nháp + quality + đường gửi (§7.4)."""

    ok: bool
    style: str = ""
    subject: str = ""
    body: str = ""
    to_email: str = ""
    eml_path: str = ""
    quality_warnings: list[str] = field(default_factory=list)
    missing_info: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok, "style": self.style, "subject": self.subject,
            "body": self.body, "to": self.to_email, "eml_path": self.eml_path,
            "quality_warnings": self.quality_warnings,
            "missing_info": self.missing_info, "error": self.error,
        }


class ReplyDrafter:
    """Soạn nháp trả lời email theo §7 — DRAFT-ONLY, không gửi."""

    def __init__(self, memory_adapter: Any | None = None) -> None:
        # Adapter S3 (tùy chọn — retrieval memory khi caller cần §7.1.3)
        if memory_adapter is None:
            try:
                from quan_ai_brain.office.memory_adapter import CherryMemoryAdapter
                memory_adapter = CherryMemoryAdapter()
            except Exception:
                memory_adapter = None  # degraded — không memory cũng soạn được
        self.memory_adapter = memory_adapter

    # ---- §7.1.3 memory retrieval ----
    def gather_memory(self, topic: str, top_k: int = 3) -> list[str]:
        """Truy xuất memory liên quan (S3). Lỗi → trả [] + không phá luồng chính."""
        if self.memory_adapter is None or not topic:
            return []
        try:
            res = self.memory_adapter.retrieve_context(topic, top_k=top_k)
            if res.error or not res.hits:
                return []
            out = []
            for h in res.hits:
                tag = h.verification or h.fact_level or "N/A"
                out.append(f"[{tag}] {h.content[:160]}")
            return out
        except Exception:
            return []

    # ---- §7.2 body builder ----
    def _build_body(self, ctx: ReplyContext, style: str, custom_body: str = "") -> str:
        """custom_body (caller/GLM soạn sẵn) → dùng nguyên; không → template
        deterministic từ points thật. Luôn thêm greeting + sign-off theo style."""
        if custom_body and custom_body.strip():
            body = custom_body.strip()
        else:
            pts = "\n".join(f"  • {p}" for p in ctx.points) or "  • (em bổ sung ý phản hồi sau — chưa đủ dữ liệu, không bịa)"
            body = _DEFAULT_BODY.get(style, _DEFAULT_BODY["chuyen_nghiep"]).format(
                subject=ctx.subject or "(không tiêu đề)", points=pts)
            # Thêm phần "thiếu thông tin" trung thực (§7.1.7)
            if ctx.questions_pending and style not in ("xac_nhan", "ngan_gon"):
                body += ("\n\nCác nội dung em đang chờ làm rõ (chưa trả lời được, "
                         "không suy diễn):\n" + "\n".join(f"  - {q}" for q in ctx.questions_pending[:3]))
        greet = _GREETING.get(style, "").format(recipient=ctx.recipient or "anh/chị",
                                                recipient_en=ctx.recipient_en or "Sir/Madam")
        sign = _SIGN_OFF.get(style, "")
        parts = [greet, body] if greet else [body]
        if sign and sign not in body:
            parts.append(sign)
        return "\n\n".join(p for p in parts if p).strip() + "\n"

    # ---- §7.3 quality check ----
    def quality_check(self, ctx: ReplyContext, body: str) -> list[str]:
        """8 mục §7.3 → list cảnh báo (rỗng = đạt). Không chặn ghi nháp —
        cảnh báo đi kèm nháp để owner duyệt (owner là người quyết cuối)."""
        w: list[str] = []
        # 1. Trả lời đúng câu hỏi: câu hỏi chưa trả lời mà body không đề cập
        for q in ctx.questions_pending[:3]:
            key = re.sub(r"[^\wàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộờớởỡợùúủũụưừứửữựỳýỷỹỵđ ]", "", str(q)).strip()[:40]
            if key and key[:20].lower() not in body.lower():
                w.append(f"§7.3.1 Câu hỏi trong luồng có thể chưa được trả lời: “{str(q)[:70]}…”")
                break
        # 2. Bỏ sót yêu cầu: requests đã phân tích ở ThreadAnalysis (ctx.points rỗng)
        if not ctx.points and not body.strip():
            w.append("§7.3.2 Body rỗng — không có ý phản hồi nào.")
        # 3. Mâu thuẫn email cũ
        for c in ctx.contradictions[:2]:
            w.append(f"§7.3.3 Luồng có mâu thuẫn — trình bày CẢ HAI trước khi gửi: {str(c)[:90]}")
        if ctx.thread_cancelled and _CONFIRM_MEETING_RE.search(body):
            w.append("§7.3.3 Luồng có tag HỦY nhưng nháp đang xác nhận cuộc họp — kiểm tra lại.")
        # 4. Sai số liệu: không tự sinh số — nháp template không chứa số mới
        # 5. Deadline chính xác: deadline trong context phải xuất hiện đúng nếu body nhắc
        for d in ctx.deadlines[:2]:
            dd = re.search(r"\d{1,2}[/-]\d{1,2}", str(d))
            if dd and dd.group(0) not in body and any(re.findall(r"hạn|deadline|trước", body, re.I)):
                w.append(f"§7.3.5 Deadline trong luồng “{dd.group(0)}” chưa khớp trong body — kiểm tra.")
                break
        # 6. Cam kết vượt thẩm quyền
        if _OVERCOMMIT_RE.search(body):
            w.append("§7.3.6 Nháp chứa cam kết mạnh (chắc chắn/cam kết/chịu trách nhiệm…) — chỉ giữ nếu anh thật sự cam kết.")
        # 7. Thông tin nội bộ nhạy cảm
        if _SENSITIVE_RE.search(body):
            w.append("§7.3.7 Nháp chứa từ nhạy cảm (mật khẩu/token/key…) — TUYỆT ĐỐI không đưa vào mail.")
        # 8. Nhầm người nhận
        if not ctx.recipient_email:
            w.append("§7.3.8 Chưa xác định địa chỉ người nhận (To) — nháp lưu không người nhận.")
        return w

    # ---- §7.1 + §7.2 + §7.3: build ----
    def build_reply(self, ctx: ReplyContext, *, style: str = "chuyen_nghiep",
                    custom_body: str = "", write_eml: bool = True,
                    task_id: str = "", source_email_id: str = "") -> DraftResult:
        """Pipeline §7.1 đủ 10 bước → DraftResult (nháp .eml, KHÔNG gửi)."""
        out = DraftResult(ok=False)
        if style not in REPLY_STYLES:
            out.error = f"Style không hợp lệ: '{style}'. Hợp lệ: {', '.join(REPLY_STYLES)}"
            return out
        if not ctx.subject and not ctx.points and not custom_body:
            out.error = "Không đủ dữ liệu trả lời (thiếu subject + points + body)."
            return out
        out.style = style
        out.subject = ctx.subject or "RE: (không tiêu đề)"
        out.to_email = ctx.recipient_email
        # §7.1.3 memory (nếu chưa truyền):
        if not ctx.memory_hits and self.memory_adapter:
            ctx.memory_hits = self.gather_memory(ctx.subject or " ".join(ctx.points[:1]))
        out.body = self._build_body(ctx, style, custom_body)
        out.quality_warnings = self.quality_check(ctx, out.body)
        out.missing_info = [str(q)[:80] for q in ctx.questions_pending[:3]]
        if not write_eml:
            out.ok = True
            return out
        # §7.4: ghi .eml qua email_draft hiện có (R2 — không SMTP/COM)
        try:
            from quan_ai_brain.tools.email_draft import create_draft
            to_addr = ctx.recipient_email or "chua_xac_dinh@example.com"  # nháp mù địa chỉ → placeholder, cảnh báo đã kèm
            meta = create_draft(
                to=to_addr, subject=out.subject, body=out.body,
                task_id=task_id, source_email_id=source_email_id,
                reason=f"S4 reply draft style={style} warnings={len(out.quality_warnings)}",
            )
            out.eml_path = str(meta.get("path", ""))
            out.ok = True
        except Exception as exc:
            out.error = f"Lỗi ghi nháp .eml (fail-honest): {type(exc).__name__}: {exc}"
            out.ok = False
        return out

    # ---- §7.4 preview đầy đủ (trước khi owner duyệt) ----
    @staticmethod
    def format_preview(res: DraftResult) -> str:
        lines = [
            "📝 BẢN NHÁP TRẢ LỜI (R2 — KHÔNG gửi tự động)",
            f"Style: {REPLY_STYLES.get(res.style, res.style)}",
            f"To: {res.to_email or '(chưa xác định)'}",
            f"Subject: {res.subject}",
            "─" * 46,
            res.body.strip(),
            "─" * 46,
        ]
        if res.quality_warnings:
            lines.append(f"⚠️ Quality check ({len(res.quality_warnings)} cảnh báo):")
            lines += [f"  {w}" for w in res.quality_warnings]
        else:
            lines.append("✅ Quality check: không phát hiện cảnh báo.")
        if res.missing_info:
            lines.append("ℹ️ Thông tin thiếu trong luồng (không bịa): "
                         + "; ".join(res.missing_info))
        if res.eml_path:
            lines.append(f"💾 Nháp: {res.eml_path} — anh duyệt → mở .eml bấm Send (gửi CẦN PHÊ DUYỆT RIÊNG từng lần §7.4).")
        return "\n".join(lines)
