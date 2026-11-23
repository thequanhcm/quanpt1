# -*- coding: utf-8 -*-
"""Runner CLI — Thread Analyzer (TASK-VMAIL-S2). Dùng bởi netchat_command_center
subprocess (110s timeout — bài học imaplib hang) hoặc chạy tay:

    python office_thread_summary_runner.py --latest        # 3 luồng nổi bật mới nhất
    python office_thread_summary_runner.py <từ khóa>       # luồng khớp từ khóa

Đường dữ liệu: VmailConnector (SOAP READONLY R2) → list_messages inbox (20) →
group theo subject-normalize → chọn luồng (từ khóa hoặc nhiều mail nhất) →
analyze_thread 10 mục §5.3 → format §5.4 8 mục + nguồn.

Fail-honest: mọi lỗi SOAP → in ⚠️ + lỗi thật, exit 0 (responder đọc stdout).
READONLY: chỉ Search/GetMsg — không mark read/xóa/gửi.
"""
from __future__ import annotations

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
    format_thread_summary,
    normalize_subject,
)

MAX_FETCH = 20  # list_messages clamp 1-20 (connector)


def _pick_threads(threads: dict, kw: str, latest: bool) -> list[tuple[str, list]]:
    """Chọn luồng: theo từ khóa (key chứa kw) hoặc các luồng nổi bật (≥2 mail
    hoặc có mail hôm nay), sort theo mail mới nhất giảm dần, lấy tối đa 3."""
    items = list(threads.items())
    if kw:
        kwl = kw.lower()
        picked = [(k, v) for k, v in items if kwl in k or kwl in normalize_subject(v[0].subject)[0]]
        if not picked:
            picked = [(k, v) for k, v in items
                      if kwl in " ".join(m.subject.lower() for m in v)]
        return picked[:3]
    # latest: ưu tiên luồng nhiều mail, rồi mới nhất
    def rank(kv):
        msgs = kv[1]
        newest = max((m._dt for m in msgs if m._dt), default=None)
        return (len(msgs), newest or 0)
    picked = sorted(items, key=rank, reverse=True)
    # Giữ luồng ≥2 mail trước, bổ sung luồng 1 mail mới nhất nếu thiếu
    multi = [(k, v) for k, v in picked if len(v) >= 2]
    single = [(k, v) for k, v in picked if len(v) == 1]
    out = multi[:3] or (single[:1] if not multi else [])
    return out


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else "--latest"
    kw = "" if arg == "--latest" else arg

    conn = VmailConnector()
    r = conn.list_messages("inbox", MAX_FETCH)
    if r.status != "ok":
        print(f"⚠️ Không đọc được hộp thư (fail-honest): {r.error or 'lỗi không rõ'}")
        return 0
    msgs = (r.data or {}).get("messages", [])
    if not msgs:
        print("📭 Inbox trống — không có luồng nào để tóm tắt.")
        return 0

    threads = build_threads(msgs)
    picked = _pick_threads(threads, kw, latest=(arg == "--latest"))
    if not picked:
        print(f"📭 Không tìm thấy luồng nào khớp “{kw}” trong {len(msgs)} mail gần nhất.")
        return 0

    parts: list[str] = [f"🧵 TÓM TẮT LUỒNG EMAIL ({len(picked)} luồng / {len(msgs)} mail gần nhất)"]
    for k, ms in picked:
        a = analyze_thread(ms)
        parts.append("\n" + "─" * 46)
        parts.append(format_thread_summary(a))
    parts.append("\n🛡️ R2: chỉ ĐỌC — không đánh dấu đã đọc, không gửi.")
    print("\n".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
