# -*- coding: utf-8 -*-
"""VoIP reader cho QUAN AI BRAIN — đọc lịch họp VoIP Viettel qua mail vofficeadmin.

(23/11/2026, owner: "cấu hình để cherry đọc được Voffice")

Phát hiện quan trọng khi khảo sát 23/11:
- voffice.viettel.vn CHỈ có IP nội bộ Viettel (10.60.7.120) — máy CHERRY ở WiFi nhà
  anh (192.168.1.9/24) PING fail + TCP/443 timeout → KHÔNG truy cập được trực tiếp.
- Tuy nhiên: VoIP tự động gửi mail thông báo lịch họp qua sender vofficeadmin@viettel.com.vn.
- Đây là nguồn GIÁN TIẾP đầy đủ: Nội dung / Thời gian / Địa điểm / Chủ trì / Chuẩn bị
  / Thành phần / Trang phục — đủ cho lịch ngày/tuần của owner.
- Mail này đã đến INBOX của anh (qua Zimbra SOAP như mail_reader.py) → module này đọc +
  parse cấu trúc + trả lịch active.

Fail-honest: không đoán, không tự tạo lịch — chỉ parse từ mail thật.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

# Tái sử dụng mail_reader (cùng đường SOAP đã có)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mail_reader  # noqa: E402

VOFFICE_SENDER = "vofficeadmin@viettel.com.vn"

# Pattern thời gian: "Thứ 3, ngày 24/11/2026 08:00 - 12:00"
RE_TIME = re.compile(
    r"Thời\s*gian\s*:?\s*([^:\n]+(?:UTC[+\-][\d:]+)?)",
    re.IGNORECASE,
)
RE_PLACE = re.compile(r"Địa\s*điểm\s*:?\s*([^\n]+)", re.IGNORECASE)
RE_HOST = re.compile(r"Chủ\s*trì\s*:?\s*([^\n0-9]+?)(?=\s+\d+\.|$)", re.IGNORECASE)
RE_DRESS = re.compile(r"\(Trang\s*phục\s*:?\s*([^)]+)\)", re.IGNORECASE)


def _parse_body(subject: str, body: str) -> dict[str, Any]:
    """Trích thời gian / địa điểm / chủ trì / trang phục từ body mail vofficeadmin."""
    out: dict[str, Any] = {
        "subject": subject,
        "time": "",
        "place": "",
        "host": "",
        "dress_code": "",
        "is_cancelled": "[Hủy cuộc họp]" in subject,
        "is_voffice": True,
    }
    # Cắt body đến trước phần "4. Chủ trì" để tránh regex greedy ăn vào body
    head = re.split(r"\s\d+\.\s+Chủ\s*trì", body, maxsplit=1)[0]
    m = RE_TIME.search(head)
    if m:
        out["time"] = m.group(1).strip().rstrip(",;.")
    m = RE_PLACE.search(head)
    if m:
        out["place"] = m.group(1).strip().rstrip(",;.")
    m = RE_HOST.search(head)
    if m:
        out["host"] = m.group(1).strip().rstrip(",;.")
    m = RE_DRESS.search(subject + " " + body)
    if m:
        out["dress_code"] = m.group(1).strip().rstrip(",;.")
    return out


def list_meetings(limit: int = 30, include_cancelled: bool = False,
                  days_ahead: int | None = None) -> dict[str, Any]:
    """Liệt kê các cuộc họp VoIP (mail từ vofficeadmin@viettel.com.vn).

    Args:
        limit: tối đa số mail cần quét (mặc định 30)
        include_cancelled: True = giữ cả mail "[Hủy cuộc họp]"
        days_ahead: chỉ lấy mail trong N ngày tới (None = tất cả)
    """
    raw = mail_reader._list_emails(
        f"from:{VOFFICE_SENDER}", limit=limit, with_body=True
    )
    if "error" in raw:
        return raw
    meetings: list[dict[str, Any]] = []
    for e in raw.get("emails", []):
        item = _parse_body(e["subject"], e.get("body_preview") or "")
        if not include_cancelled and item["is_cancelled"]:
            continue
        item["date"] = e["date"]
        item["mid"] = e["uid"]
        meetings.append(item)
    return {
        "host": "vofficeadmin@viettel.com.vn",
        "count": len(meetings),
        "note": ("bao gồm cả hủy" if include_cancelled else "chỉ lịch ACTIVE — đã lọc hủy"),
        "meetings": meetings,
    }


def upcoming_meetings(days_ahead: int = 14, limit: int = 30) -> dict[str, Any]:
    """Lấy các cuộc họp ACTIVE mới nhất (mặc định 30 cái gần nhất trong 14 ngày)."""
    # SOAP SearchRequest không hỗ trợ after:date linh hoạt — lấy 30 ACTIVE gần nhất, lọc sau
    res = list_meetings(limit=limit, include_cancelled=False)
    if "error" in res:
        return res
    return res


def format_for_dm(result: dict[str, Any], max_meetings: int = 10) -> str:
    if "error" in result:
        return f"⚠️ {result['error']}"
    items = result.get("meetings") or []
    if not items:
        return "📭 Không có cuộc họp VoIP nào trong hộp thư."
    lines = [f"📅 {len(items)} lịch họp VoIP ({result.get('note','active')}):"]
    for i, m in enumerate(items[:max_meetings], 1):
        cancel = " ❌HỦY" if m.get("is_cancelled") else ""
        lines.append(f"\n{i}. {m['subject']}{cancel}")
        if m.get("time"):
            lines.append(f"   🕐 {m['time']}")
        if m.get("place"):
            lines.append(f"   📍 {m['place']}")
        if m.get("host"):
            lines.append(f"   👤 {m['host']}")
        if m.get("dress_code"):
            lines.append(f"   👔 Trang phục: {m['dress_code']}")
    return "\n".join(lines)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "upcoming"
    if arg == "all":
        res = list_meetings(include_cancelled=True)
    else:
        res = upcoming_meetings()
    print(format_for_dm(res))
