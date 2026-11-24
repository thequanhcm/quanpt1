# -*- coding: utf-8 -*-
"""CHERRY Office Intelligence — Sprint 1a EMAIL-INTAKE-REAL (card TASK-OFFICE-S1).

Owner master prompt (23/11/2026): CHERRY OFFICE INTELLIGENCE V1.0 §II — Module 1
Email Intelligence. Audit: docs/CHERRY_OFFICE_INTELLIGENCE/ARCHITECTURE_AUDIT.md.

Lớp mỏng TRÊN nền hiện có (không tạo bộ não thứ 2):
- Nguồn mail thật = tools/mail_reader.py (Zimbra SOAP — LIVE 23/11, READONLY).
- Pipeline lưu/dedupe = integration/email_intake.EmailIntakeStore (dùng lại nguyên si).
- Phân loại: mở rộng 5 nhóm cũ → 10 nhóm master prompt §II.2 (hằng string
  EmailCategory10; KHÔNG đụng enum cũ để không phá Sprint 9).
- Priority/Urgency score + deadline detect: CHỈ khi email nêu rõ (explicit);
  suy luận ngữ cảnh → bắt buộc gắn nhãn "đề xuất" (master prompt §II.2 middle).

R2 bất biến: CHỈ ĐỌC — không đánh dấu đã đọc, không xóa, không gửi. Credentials
đi qua vault loader như mail_reader; KHÔNG log/echo secret.
Fail-honest: SOAP lỗi → IntakeResult(connector_status=...), không fake số liệu.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_BRAIN_SRC = Path(__file__).resolve().parents[2]
if str(_BRAIN_SRC) not in sys.path:
    sys.path.insert(0, str(_BRAIN_SRC))

from quan_ai_brain.integration.email_intake import (  # noqa: E402
    ConnectorStatus,
    EmailIntakeStore,
    EmailMessage,
    IntakeResult,
)

# tools/ import mail_reader (SOAP thật)
_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))


class EmailCategory10:
    """10 nhóm phân loại master prompt §II.2 — string constants (không phá enum cũ)."""

    URGENT = "URGENT"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    NEED_REPLY = "NEED_REPLY"
    INFORMATION = "INFORMATION"
    APPROVAL = "APPROVAL"
    MEETING = "MEETING"
    DEADLINE = "DEADLINE"
    FOLLOW_UP = "FOLLOW_UP"
    REFERENCE = "REFERENCE"
    LOW_PRIORITY = "LOW_PRIORITY"


@dataclass
class EmailAnalysis:
    """Kết quả phân tích 1 email theo master prompt §II.2 (priority/urgency/...)."""

    message: EmailMessage
    category: str
    priority_score: int          # 0-100
    urgency_score: int           # 0-100
    action_required: str         # mô tả việc cần làm ("" = không có)
    deadline: str                # deadline EXPLICIT từ email ("" = không nêu)
    deadline_is_suggested: bool  # True = deadline suy luận từ ngữ cảnh (KHÔNG phải khẳng định)
    suggested_next_action: str   # đề xuất bước tiếp theo
    confidence: float            # 0-1 độ tin cậy phân loại
    related_project: str = ""    # tên dự án nếu nhận ra

    def to_dict(self) -> dict[str, Any]:
        d = self.message.to_dict()
        d.update({
            "category10": self.category,
            "priority_score": self.priority_score,
            "urgency_score": self.urgency_score,
            "action_required": self.action_required,
            "deadline": self.deadline,
            "deadline_is_suggested": self.deadline_is_suggested,
            "suggested_next_action": self.suggested_next_action,
            "confidence": self.confidence,
            "related_project": self.related_project,
        })
        return d


# ---- Từ khóa phân loại (deterministic, không LLM trong sprint này) ----
_KW_URGENT = ("gấp", "gap", "khẩn", "khan", "urgent", "asap", "ngay lập tức",
              "cần ngay", "trước 8h", "trước 9h", "hôm nay trước", "hom nay truoc")
_KW_ACTION = ("đề nghị", "de nghi", "yêu cầu", "yeu cau", "vui lòng", "vui long",
              "cần anh", "can anh", "cần chị", "can chi", "xử lý", "xu ly",
              "thực hiện", "thuc hien", "gửi lại", "gui lai", "hoàn thành",
              "hoan thanh", "điền", "dien", "đăng ký", "dang ky")
_KW_REPLY = ("phản hồi", "phan hoi", "trả lời", "tra loi", "reply", "cho em biết",
             "cho anh biết", "cho e biet", "cho a biet", "xin ý kiến", "xin y kien",
             "ý kiến của anh", "y kien cua anh")
_KW_APPROVAL = ("phê duyệt", "phe duyet", "duyệt giúp", "duyet giup",
                "xin duyệt", "xin duyet", "chờ duyệt", "cho duyet", "phê chuẩn", "phe chuan",
                "ký duyệt", "ky duyet", "trình ký", "trinh ky", "trình duyệt", "trinh duyet")
_KW_MEETING = ("họp", "cuộc họp", "cuoc hop", "meeting", "lịch họp", "lich hop",
               "họp online", "hop online", "họp trực tuyến", "hop truc tuyen",
               "voffice", "chủ trì", "chu tri", "thành phần tham dự", "thanh phan tham du")
_KW_FOLLOWUP = ("nhắc lại", "nhac lai", "theo dõi", "theo doi", "follow up", "follow-up",
                "đã gửi trước", "da gui truoc", "tiến độ", "tien do", "đến bao giờ",
                "den bao gio", "tình trạng", "tinh trang")
_KW_REFERENCE = ("tham khảo", "tham khao", "reference", "fyi", "thông tin thêm",
                 "thong tin them", "hướng dẫn", "huong dan", "tài liệu", "tai lieu",
                 "sổ tay", "so tay", "kinh nghiệm", "kinh nghiem")
_KW_LOW = ("khuyến mãi", "khuyen mai", "sale", "giảm giá", "giam gia", "quảng cáo",
           "quang cao", "newsletter", "unsubscribe", "hủy đăng ký", "huy dang ky",
           "chúc mừng sinh nhật", "chuc mung sinh nhat")

# deadline EXPLICIT: ngày tháng/cụm thời gian NÓI RÕ trong email
_DEADLINE_PATTERNS = [
    re.compile(r"trước\s+(?:\d{1,2}[h:]\d{0,2}|\d{1,2}\s*giờ)\s*(?:thứ\s*\w+|ngày\s*\d{1,2})?", re.I),
    re.compile(r"(?:hạn|deadline|hoàn thành|hoan thanh|gửi về|gui ve|báo cáo|bao cao)[^.;\n]{0,40}?(?:trước|vào|đến|den)?\s*(?:\d{1,2}[/:]\d{1,2}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)", re.I),
    re.compile(r"(?:trước|vào)\s*(?:ngày)?\s*\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?", re.I),
    re.compile(r"trước\s+(?:\d{1,2})\s*(?:h|giờ)\s*(?:chiều|sáng)?", re.I),
    re.compile(r"trong\s+(?:hôm\s+nay|ngày\s+hôm\s+nay|tuần\s+này|tuan\s+nay)", re.I),
]
_DEADLINE_SUGGEST_WORDS = ("sớm nhất", "som nhat", "tháng này", "thang nay",
                           "cuối tuần", "cuoi tuan", "trong tuần", "trong tuan")


def _score_text(text_lower: str, kws: tuple[str, ...]) -> int:
    return sum(1 for k in kws if k in text_lower)


def analyze_email(msg: EmailMessage) -> EmailAnalysis:
    """Phân loại 10 nhóm + score + deadline (explicit mới ghi, còn lại = đề xuất)."""
    text = f"{msg.subject}\n{msg.body_preview}".lower()

    scores: dict[str, int] = {
        EmailCategory10.URGENT: _score_text(text, _KW_URGENT) * 3,
        EmailCategory10.ACTION_REQUIRED: _score_text(text, _KW_ACTION) * 2,
        EmailCategory10.NEED_REPLY: _score_text(text, _KW_REPLY) * 4,
        EmailCategory10.APPROVAL: _score_text(text, _KW_APPROVAL) * 3,
        EmailCategory10.MEETING: _score_text(text, _KW_MEETING) * 2,
        EmailCategory10.FOLLOW_UP: _score_text(text, _KW_FOLLOWUP) * 2,
        EmailCategory10.REFERENCE: _score_text(text, _KW_REFERENCE),
        EmailCategory10.LOW_PRIORITY: _score_text(text, _KW_LOW) * 3,
    }
    total_kw = sum(scores.values())
    if total_kw == 0:
        category = EmailCategory10.INFORMATION
        confidence = 0.4
    else:
        best = max(scores, key=lambda k: scores[k])  # type: ignore[arg-type]
        if scores[EmailCategory10.LOW_PRIORITY] >= 3:
            best = EmailCategory10.LOW_PRIORITY
        category = best
        confidence = min(0.9, 0.4 + total_kw * 0.1)

    # Deadline: explicit pattern → ghi; chỉ có từ mờ → đề xuất (suggested)
    deadline = ""
    deadline_suggested = False
    for pat in _DEADLINE_PATTERNS:
        m = pat.search(text)
        if m:
            deadline = m.group(0).strip()
            break
    if not deadline and any(w in text for w in _DEADLINE_SUGGEST_WORDS):
        for w in _DEADLINE_SUGGEST_WORDS:
            if w in text:
                deadline = w
                deadline_suggested = True
                break

    # Priority/Urgency 0-100 (deterministic)
    urgency = min(100, scores[EmailCategory10.URGENT] * 25
                  + (40 if deadline and not deadline_suggested else 0)
                  + (20 if ("hôm nay" in text or "hom nay" in text) else 0))
    priority = int(min(100, urgency * 0.6
                       + scores[EmailCategory10.ACTION_REQUIRED] * 12
                       + scores[EmailCategory10.APPROVAL] * 15))

    action_required = ""
    next_action = ""
    if category == EmailCategory10.URGENT:
        action_required = "Xử lý ngay trong ngày"
        next_action = "Đọc và xử lý ngay"
    elif category == EmailCategory10.ACTION_REQUIRED:
        action_required = "Thực hiện yêu cầu trong email"
        next_action = "Lên kế hoạch thực hiện"
    elif category == EmailCategory10.NEED_REPLY:
        action_required = "Soạn phản hồi (nháp — chờ duyệt)"
        next_action = "Soạn bản nháp trả lời"
    elif category == EmailCategory10.APPROVAL:
        action_required = "Xem xét phê duyệt"
        next_action = "Đọc hồ sơ chờ duyệt"
    elif category == EmailCategory10.MEETING:
        action_required = "Xem lịch + chuẩn bị họp"
        next_action = "Kiểm tra lịch và tài liệu họp"
    elif category == EmailCategory10.FOLLOW_UP:
        action_required = "Theo dõi tiến độ"
        next_action = "Đưa vào danh sách follow-up"
    elif category == EmailCategory10.LOW_PRIORITY:
        next_action = "Bỏ qua hoặc đọc lúc rảnh"

    return EmailAnalysis(
        message=msg, category=category, priority_score=priority,
        urgency_score=urgency, action_required=action_required,
        deadline=deadline, deadline_is_suggested=deadline_suggested,
        suggested_next_action=next_action, confidence=round(confidence, 2),
    )


class SOAPMailConnector:
    """Connector mail THẬT qua tools/mail_reader.py (Zimbra SOAP) — R2 READONLY.

    Interface trùng EmailConnector: status() + fetch_recent(). Mỗi EmailMessage
    ghi nguồn="vmail_soap". Không đánh dấu đã đọc, không xóa, không gửi.
    """

    def __init__(self, *, with_body: bool = True) -> None:
        self._with_body = with_body

    def status(self) -> ConnectorStatus:
        try:
            import mail_reader as _mr
            try:
                _mr._creds()  # chỉ kiểm tra secret tồn tại — không gọi mạng
            except Exception:
                return ConnectorStatus.NOT_CONFIGURED
            return ConnectorStatus.CONNECTED
        except Exception:
            return ConnectorStatus.UNKNOWN

    def fetch_recent(self, limit: int = 20) -> list[EmailMessage]:
        import mail_reader as _mr
        res = _mr.read_latest(max(1, min(limit, 20)))
        if "error" in res:
            raise RuntimeError(res["error"])
        out: list[EmailMessage] = []
        for it in res.get("emails", []):
            out.append(EmailMessage(
                message_id=f"vmail-{it['id']}",
                sender=it.get("from_addr", ""),
                subject=it.get("subject", ""),
                body_preview=(it.get("body_preview") or it.get("fragment") or "")[:500],
                received_at_utc=it.get("date", ""),
                source="vmail_soap",
            ))
        return out

    def fetch_since(self, date_ddmm: str, limit: int = 20) -> list[EmailMessage]:
        """Mail từ ngày DD/MM (năm nay) — 'check mail từ ngày 22/11' (S3-24/11)."""
        import mail_reader as _mr
        res = _mr.read_since(date_ddmm, limit=max(1, min(limit, 20)))
        if "error" in res:
            raise RuntimeError(res["error"])
        out: list[EmailMessage] = []
        for it in res.get("emails", []):
            out.append(EmailMessage(
                message_id=f"vmail-{it['id']}",
                sender=it.get("from_addr", ""),
                subject=it.get("subject", ""),
                body_preview=(it.get("body_preview") or it.get("fragment") or "")[:500],
                received_at_utc=it.get("date", ""),
                source="vmail_soap",
            ))
        return out

    def fetch_since_direct_only(self, date_ddmm: str, limit: int = 20) -> list[EmailMessage]:
        """(24/11 S3-v5, owner: 'lọc đúng, chỉ gửi đến cá nhân anh') — CHỈ mail
        gửi trực tiếp đến owner (TO chỉ owner, không CC khác). Vẫn READONLY."""
        import mail_reader as _mr
        res = _mr.read_since_direct_only(date_ddmm, limit=max(1, min(limit, 20)))
        if "error" in res:
            raise RuntimeError(res["error"])
        out: list[EmailMessage] = []
        for it in res.get("emails", []):
            out.append(EmailMessage(
                message_id=f"vmail-{it['id']}",
                sender=it.get("from_addr", ""),
                subject=it.get("subject", ""),
                body_preview=(it.get("body_preview") or it.get("fragment") or "")[:500],
                received_at_utc=it.get("date", ""),
                source="vmail_soap",
            ))
        return out


def sync_and_analyze(
    connector: Any,
    store: EmailIntakeStore,
    *,
    limit: int = 20,
) -> tuple[IntakeResult, list[EmailAnalysis]]:
    """Fetch 1 LẦN → dedupe → classify (tương thích nền) → phân tích 10 nhóm.

    Khác sync_intake: chỉ fetch_recent MỘT lần (SOAP đắt), rồi tự chạy pipeline
    để analyses khớp đúng tập email MỚI đã lưu. Fail-honest giữ nguyên.
    Trả (IntakeResult, list[EmailAnalysis]) — analyses chỉ gồm email MỚI.
    """
    from quan_ai_brain.integration.email_intake import classify_email

    try:
        st = connector.status()
        if st != ConnectorStatus.CONNECTED:
            return (IntakeResult(connector_status=st,
                                 error="connector không ở trạng thái CONNECTED — không đọc gì"), [])
        messages = connector.fetch_recent(limit=limit)
    except Exception as exc:
        return (IntakeResult(connector_status=ConnectorStatus.UNKNOWN,
                             error=f"{type(exc).__name__}: {exc}"), [])

    result = IntakeResult(connector_status=ConnectorStatus.CONNECTED, fetched=len(messages))
    analyses: list[EmailAnalysis] = []
    for msg in messages:
        if store.already_seen(msg.message_id):
            result.duplicates += 1
            continue
        if store.save(msg, classify_email(msg)):
            result.new += 1
            a = analyze_email(msg)
            analyses.append(a)
            result.by_category[a.category] = result.by_category.get(a.category, 0) + 1
    return result, analyses


def format_summary_ab(
    result: IntakeResult,
    analyses: list[EmailAnalysis],
    *,
    top_n: int = 5,
) -> str:
    """Format A.Tổng quan / B.Email quan trọng — master prompt §II.3.

    Trung thực: bảng C (tổng hợp công việc vào task pipeline) thuộc Sprint 5,
    chưa có trong sprint này — không fake.
    """
    lines: list[str] = []
    by10: dict[str, int] = {}
    for a in analyses:
        by10[a.category] = by10.get(a.category, 0) + 1
    important = [a for a in analyses if a.category in (
        EmailCategory10.URGENT, EmailCategory10.ACTION_REQUIRED,
        EmailCategory10.NEED_REPLY, EmailCategory10.APPROVAL)]
    need_reply = [a for a in analyses if a.category == EmailCategory10.NEED_REPLY]

    lines.append("A. TỔNG QUAN")
    lines.append(f"- Email mới: {result.new}")
    lines.append(f"- Email quan trọng: {len(important)}")
    lines.append(f"- Cần phản hồi: {len(need_reply)}")
    if by10:
        cats = ", ".join(f"{k}: {v}" for k, v in sorted(by10.items(), key=lambda x: -x[1]))
        lines.append(f"- Phân loại: {cats}")
    if result.error:
        lines.append(f"- ⚠️ {result.error}")

    if not analyses:
        lines.append("")
        lines.append("B. Không có email mới nào để phân tích.")
        return "\n".join(lines)

    analyses_sorted = sorted(analyses, key=lambda a: (-a.priority_score, -a.urgency_score))
    lines.append("")
    lines.append(f"B. EMAIL QUAN TRỌNG (top {min(top_n, len(analyses_sorted))} theo priority)")
    for i, a in enumerate(analyses_sorted[:top_n], 1):
        m = a.message
        lines.append("")
        lines.append(f"{i}. [{a.category}] {m.subject}")
        lines.append(f"   👤 {m.sender} · 🕐 {m.received_at_utc}")
        lines.append(f"   🎯 Priority {a.priority_score}/100 · Urgency {a.urgency_score}/100")
        if a.action_required:
            lines.append(f"   ✅ Việc cần làm: {a.action_required}")
        if a.deadline:
            tag = " (đề xuất — email không nêu rõ)" if a.deadline_is_suggested else ""
            lines.append(f"   ⏰ Thời hạn: {a.deadline}{tag}")
        if a.suggested_next_action:
            lines.append(f"   💡 Đề xuất: {a.suggested_next_action}")
        preview = (m.body_preview or "").strip()
        if preview:
            lines.append(f"   💬 {preview[:200]}{'…' if len(preview) > 200 else ''}")
    return "\n".join(lines)
