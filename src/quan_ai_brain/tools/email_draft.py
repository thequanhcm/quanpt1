"""Sprint 8 (b): Email DRAFT tool — CHỈ tạo nháp .eml, KHÔNG gửi.

R2 cẩn trọng: tuyệt đối không SMTP, không COM Outlook, không API gửi.
Nháp lưu data/email_drafts/YYYYMMDD_HHMMSS_*.eml + trả path cho card duyệt.
Owner duyệt → mở file .eml bằng trình mail mặc định (anh tự bấm Send).
"""
from __future__ import annotations

import re
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path
from typing import Any

# Sprint 8 (b): nháp nằm trong WORKSPACE/data/email_drafts (src/ là code, không chứa data).
# parents[2] từ src/quan_ai_brain/tools/ = src/ — sai; đi 3 cấp lên = workspace root.
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DRAFT_DIR = WORKSPACE_ROOT / "data" / "email_drafts"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailDraftError(ValueError):
    """Fail-closed: thiếu subject/nội dung hoặc địa chỉ sai định dạng."""


def validate_address(addr: str) -> str:
    addr = (addr or "").strip()
    if not _EMAIL_RE.match(addr):
        raise EmailDraftError(f"Địa chỉ email không hợp lệ: '{addr[:50]}'")
    return addr


def create_draft(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    draft_dir: str | Path = DRAFT_DIR,
) -> dict[str, Any]:
    """Tạo nháp .eml. Trả về {path, to, subject}. KHÔNG gửi."""
    to = validate_address(to)
    if not subject or not subject.strip():
        raise EmailDraftError("Thiếu tiêu đề (subject) — nháp phải có subject")
    if not body or not body.strip():
        raise EmailDraftError("Thiếu nội dung (body) — nháp phải có nội dung")

    msg = EmailMessage()
    msg["From"] = "quanpt1@viettel.com.vn"
    msg["To"] = to
    msg["Subject"] = subject.strip()
    msg["Date"] = formatdate(localtime=True)
    if cc.strip():
        msg["Cc"] = ", ".join(
            validate_address(a) for a in cc.split(";") if a.strip()
        )
    msg.set_content(body.strip(), charset="utf-8")

    out_dir = Path(draft_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_subj = re.sub(r"[^\w\- ]", "", subject.strip())[:40].replace(" ", "_") or "draft"
    path = out_dir / f"{stamp}_{safe_subj}.eml"
    path.write_bytes(msg.as_bytes())

    return {"path": str(path), "to": to, "subject": subject.strip(), "created": True}
