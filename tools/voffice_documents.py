# -*- coding: utf-8 -*-
"""Voffice Documents reader — đọc + tóm tắt VĂN BẢN Voffice nhận được.

(24/11 S3-v7, owner: "cherry có kiểm tra được các văn bản anh nhận trên Voffice
không? cấu hình cherry để có thể đọc và tóm tắt được các nội dung trong văn bản
nhận được và DM đến anh")

KHẢO SÁT THẬT 24/11 (fail-honest, không đoán):
- voffice.viettel.vn = 10.60.7.120 LAN-only: từ WiFi nhà (192.168.1.9/24) TCP/443
  TIMEOUT — KHÔNG truy cập trực tiếp được portal văn bản. Điều này chỉ đổi khi:
  (a) máy chạy trong mạng LAN công ty, hoặc (b) owner login app M-Suite ZTNA
  (tunnel vtn-msuite.viettel.vn đang OK 443 nhưng CHƯA login).
- NGUỒN GIÁN TIẾP khả dụng NGAY: văn bản Voffice về tổng trạm được CHUYỂN TIẾP
  qua mail Zimbra (subject chứa số/ký hiệu VB, "V/v", chỉ thị, kế hoạch, quyết
  định, công văn; body chứa "Kính gửi"/"Số:/Ký hiệu/Trích yếu"). Module này đọc
  nguồn đó — NÓI ĐÚNG LÀ GIÁN TIẾP, không fake "đọc portal".

R2 READONLY: chỉ Search/GetMsg SOAP. Không gửi, không xóa, không mark-read.
Fail-honest: SOAP lỗi → trả {"error"}; không có VB → nói rõ không có.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mail_reader  # noqa: E402

# Từ khóa nhận diện VĂN BẢN (khác lịch họp vofficeadmin / báo cáo ca trực):
VB_PATTERNS = [
    r"\b[Vv]/[Vv]\b",                    # "V/v" — về việc (VB chuyển tiếp chuẩn)
    r"công văn", r"quyết định", r"kế hoạch số",
    r"chỉ thị", r"thông tư", r"nghị quyết",
    r"\d+/[A-Z]{2,}-[A-Z&]{2,}",         # số/ký hiệu VB: 3176/KH-ĐT&QLTS, 1569/CT-...
    r"văn bản số", r"vbhxh",
]
RE_VB = re.compile("|".join(VB_PATTERNS), re.IGNORECASE)

# Loại TRỰC TIẾP trùng mail-alert (báo cáo ca trực/quân số — đã có cảnh báo riêng):
EXCLUDE = re.compile(r"báo cáo bàn giao ca trực|bao cao ban giao ca truc|"
                     r"báo cáo quân số|báo cáo nguồn ngày đêm|báo cáo công việc ngày", re.IGNORECASE)

RE_SO_KY_HIEU = re.compile(r"\b(\d{1,5}/[A-ZĐÀ-Ỹ0-9\-&\.]{2,20})\b", re.IGNORECASE)
RE_TRICH_YEU = re.compile(r"(?:trích\s*yếu|về việc|V/v)\s*:?\s*([^\n]{10,160})", re.IGNORECASE)
RE_NGAY_BAN_HANH = re.compile(r"ngày\s+(\d{1,2}[/.]\d{1,2}[/.]\d{2,4})", re.IGNORECASE)
RE_NOI_BAN_HANH = re.compile(r"(?:tập đoàn|tổng công ty|công ty|vtv?net|ttktdkv\d|ban [A-ZĐÀ-Ỹ]{2,})", re.IGNORECASE)


def _extract(subject: str, body: str, sender: str, date: str) -> dict[str, Any] | None:
    """Nhận diện + trích cấu trúc 1 văn bản. None = không phải VB."""
    text = f"{subject} {body}"
    if not RE_VB.search(text):
        return None
    if EXCLUDE.search(subject):
        return None  # báo cáo thường — đã có mail-alert riêng
    so = RE_SO_KY_HIEU.search(subject) or RE_SO_KY_HIEU.search(body)
    trich = RE_TRICH_YEU.search(subject) or RE_TRICH_YEU.search(body)
    ngay = RE_NGAY_BAN_HANH.search(body) or RE_NGAY_BAN_HANH.search(subject)
    noi = RE_NOI_BAN_HANH.search(subject) or RE_NOI_BAN_HANH.search(body)
    # tóm tắt nội dung: lấy phần đầu body (bỏ header forward dư):
    b = re.sub(r"From:.*?(?=Dear|Kính|Kinh|\Z)", " ", body, flags=re.S)
    b = re.sub(r"\s+", " ", b).strip()
    summary = b[:450]
    return {
        "so_ky_hieu": so.group(1) if so else "",
        "trich_yeu": (trich.group(1).strip() if trich else "")[:160],
        "ngay_ban_hanh": ngay.group(1) if ngay else "",
        "noi_ban_hanh": noi.group(0) if noi else "",
        "subject": subject,
        "sender": sender,
        "received": date,
        "summary": summary,
    }


def list_documents(query_days: str = "17/11", limit: int = 15) -> dict[str, Any]:
    """Liệt kê văn bản Voffice (gián tiếp qua mail) từ ngày DD/MM đến giờ."""
    try:
        dd, mm = query_days.split("/")[:2]
        d_us = f"{int(mm):02d}/{int(dd):02d}/{__import__('datetime').date.today().year}"
    except Exception:
        return {"error": f"định dạng ngày sai: {query_days!r} (cần DD/MM)"}
    raw = mail_reader._list_emails(
        f"in:inbox after:{d_us}", limit=max(1, min(limit, 20)), with_body=True)
    if "error" in raw:
        return raw
    docs: list[dict[str, Any]] = []
    seen_subj: set[str] = set()
    for e in raw.get("emails", []):
        item = _extract(e["subject"], e.get("body_preview") or "",
                        e.get("from_addr", ""), e.get("date", ""))
        if not item:
            continue
        key = e["subject"].lower()
        if key in seen_subj:
            continue  # bỏ trùng lặp FW/RE
        seen_subj.add(key)
        item["mid"] = e.get("uid", "")
        docs.append(item)
    return {"host": "voffice (gián tiếp qua mail Zimbra)", "window_since": query_days,
            "count": len(docs), "documents": docs}


def format_for_dm(result: dict[str, Any], max_docs: int = 8) -> str:
    if "error" in result:
        return f"⚠️ {result['error']}"
    docs = result.get("documents") or []
    if not docs:
        return (f"📭 Không có văn bản Voffice nào trong hộp thư từ "
                f"{result.get('window_since')} (nguồn gián tiếp qua mail — portal "
                f"voffice.viettel.vn LAN-only máy nhà không truy cập được).")
    lines = [f"📄 {len(docs)} VĂN BẢN VOFFICE (từ {result.get('window_since')})"
             " — nguồn gián tiếp qua mail:"]
    for i, d in enumerate(docs[:max_docs], 1):
        lines.append("")
        so = f"Số {d['so_ky_hieu']} · " if d.get("so_ky_hieu") else ""
        nb = f"· ban hành {d['ngay_ban_hanh']} " if d.get("ngay_ban_hanh") else ""
        lines.append(f"{i}. {so}{d['subject'][:110]} {nb}")
        lines.append(f"   👤 {d['sender']} · 🕐 nhận {d['received']}")
        if d.get("trich_yeu"):
            lines.append(f"   📌 Trích yếu: {d['trich_yeu'][:140]}")
        s = (d.get("summary") or "").strip()
        if s:
            lines.append(f"   💬 Tóm tắt: {s[:300]}{'…' if len(s) > 300 else ''}")
    lines.append("")
    lines.append("(Portal voffice.viettel.vn LAN-only — đọc trực tiếp cần M-Suite "
                 "tunnel: anh login app M-Suite rồi báo em.)")
    return "\n".join(lines)


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "17/11"
    print(format_for_dm(list_documents(q)))
