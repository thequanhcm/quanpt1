# -*- coding: utf-8 -*-
"""Runner CLI — Reply Draft (TASK-VMAIL-S4). Dùng bởi netchat_command_center
subprocess (110s timeout — bài học imaplib hang) hoặc chạy tay:

    python office_reply_draft_runner.py <từ khóa> [style]

Đường dữ liệu: VmailConnector (SOAP READONLY R2) → list_messages inbox →
build_threads → chọn luồng theo từ khóa → ThreadAnalyzer (S2) → ReplyContext →
ReplyDrafter.build_reply (S4, §7.1-7.3) → .eml (R2 DRAFT-ONLY §7.4) + preview.

Địa chỉ To: trích từ mail cuối/người gửi đầu của luồng (dữ liệu thật). Không
tìm thấy → nháp placeholder + cảnh báo §7.3.8. KHÔNG GỬI — owner duyệt .eml.
Fail-honest: mọi lỗi SOAP → in ⚠️ + lỗi thật, exit 0 (responder đọc stdout).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
for p in (WORKSPACE / "src", WORKSPACE / "tools", WORKSPACE / "user, pass, token"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from quan_ai_brain.office.vmail_connector import VmailConnector  # noqa: E402
from quan_ai_brain.office.thread_analyzer import (  # noqa: E402
    analyze_thread,
    build_threads,
    normalize_subject,
)
from quan_ai_brain.office.reply_drafter import (  # noqa: E402
    REPLY_STYLES,
    ReplyContext,
    ReplyDrafter,
)

MAX_FETCH = 20  # list_messages clamp 1-20 (connector)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def _pick_thread(threads: dict, kw: str) -> tuple[str, list] | None:
    """Chọn 1 luồng khớp từ khóa (nhiều mail nhất khi nhiều khớp)."""
    kwl = (kw or "").lower()
    hits = [(k, v) for k, v in threads.items() if kwl in k]
    if not hits:
        hits = [(k, v) for k, v in threads.items()
                if kwl in " ".join(m.subject.lower() for m in v)]
    if not hits:
        return None
    hits.sort(key=lambda kv: len(kv[1]), reverse=True)
    return hits[0]


def _extract_recipient(msgs: list) -> tuple[str, str]:
    """Người nhận của nháp = người GỬI mail đầu tiên trong luồng (trừ owner).
    ThreadMessage (S2) có from_name + from_addr."""
    owner = "quanpt1"
    for m in msgs:  # msgs sắp theo thời gian tăng (S2)
        addr = (getattr(m, "from_addr", "") or "").strip()
        name = (getattr(m, "from_name", "") or "").strip()
        if not addr and not name:
            continue
        if owner in (addr + " " + name).lower():
            continue
        clean_name = re.sub(r"\s*<.*>", "", name).strip() or addr
        em = _EMAIL_RE.search(addr) or _EMAIL_RE.search(name)
        return (clean_name, em.group(0) if em else "")
    return ("", "")


def main() -> int:
    args = sys.argv[1:]
    kw = args[0] if args else ""
    style = args[1] if len(args) > 1 else "chuyen_nghiep"
    if style not in REPLY_STYLES:
        print(f"⚠️ Style '{style}' không hợp lệ. Hợp lệ: {', '.join(REPLY_STYLES)}")
        return 0

    conn = VmailConnector()
    r = conn.list_messages("inbox", MAX_FETCH)
    if r.status != "ok":
        print(f"⚠️ Không đọc được hộp thư (fail-honest): {r.error or 'lỗi không rõ'}")
        return 0
    msgs = (r.data or {}).get("messages", [])
    if not msgs:
        print("📭 Inbox trống — không có luồng nào để soạn trả lời.")
        return 0
    if not kw:
        print("⚠️ Cần từ khóa luồng: 'soạn trả lời email <từ khóa> [style]'. "
              "Styles: " + ", ".join(REPLY_STYLES))
        return 0

    threads = build_threads(msgs)
    picked = _pick_thread(threads, kw)
    if not picked:
        print(f"📭 Không tìm thấy luồng nào khớp “{kw}” trong {len(msgs)} mail gần nhất.")
        return 0

    key, tmsgs = picked
    analysis = analyze_thread(tmsgs)
    recipient_name, recipient_email = _extract_recipient(tmsgs)
    source_email_id = str(getattr(tmsgs[-1], "id", "") or "")

    ctx = ReplyContext.from_thread_analysis(
        analysis, recipient_email=recipient_email, recipient=recipient_name)
    # Điểm phản hồi lấy từ dữ liệu thật: quyết định + cam kết + thay đổi trong luồng
    ctx.points = (ctx.decisions + analysis.commitments[:1] + ctx.deadlines[:1])[:4]

    drafter = ReplyDrafter()
    res = drafter.build_reply(ctx, style=style, source_email_id=source_email_id)
    if not res.ok:
        print(f"⚠️ Soạn nháp thất bại (fail-honest): {res.error}")
        return 0
    print(ReplyDrafter.format_preview(res))
    print("\n🛡️ R2: CHỈ SOẠN NHÁP — không gửi tự động; gửi cần anh phê duyệt riêng từng lần (§7.4).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
