# -*- coding: utf-8 -*-
"""Mail Alert — tự động đọc mail định kỳ, mail quan trọng → DM tóm tắt cho owner.

(24/11 S3-v6, owner: "cấu hình cho cherry tự động đọc mail 4h/lần, nếu có mail
quan trọng, highlight, gấp... gửi đến anh cần xử lý thì hãy DM trực tiếp.
khi DM hãy tóm tắt nội dung mail đó")

Thiết kế an toàn:
- READONLY R2: chỉ đọc qua SOAPMailConnector (fetch_since) + analyze. KHÔNG
  mark-read, KHÔNG xóa, KHÔNG gửi mail trả lời.
- DM duy nhất qua responder daemon (send_message NetChat) — 1 mail chỉ DM 1 lần
  (dm_sent_ids persist). Restart KHÔNG re-DM.
- Fail-honest: SOAP lỗi → trả error, log thật, thử chu kỳ sau. Không fake.
- Config runtime: data/mail_alert/config.json (enabled, interval_seconds 14400=4h,
  min_priority, categories). State: data/mail_alert/state.json (last_check, dm_sent_ids).
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
import time
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE / "src") not in sys.path:
    sys.path.insert(0, str(WORKSPACE / "src"))
if str(WORKSPACE / "tools") not in sys.path:
    sys.path.insert(0, str(WORKSPACE / "tools"))

ALERT_DIR = WORKSPACE / "data" / "mail_alert"
CONFIG_PATH = ALERT_DIR / "config.json"
STATE_PATH = ALERT_DIR / "state.json"

_DEFAULT_CONFIG = {
    "enabled": True,
    "interval_seconds": 14400,  # 4 giờ/lần (owner 24/11)
    "min_priority": 60,         # ngưỡng priority coi là quan trọng
    "categories": ["ACTION_REQUIRED", "URGENT", "NEED_REPLY"],
    "max_dm_per_cycle": 5,      # chống spam: tối đa 5 mail/chu kỳ
}


def _ensure_dir() -> None:
    ALERT_DIR.mkdir(parents=True, exist_ok=True)


def read_config() -> dict[str, Any]:
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(cfg, dict):
            merged = dict(_DEFAULT_CONFIG)
            merged.update(cfg)
            return merged
    except Exception:
        pass
    return dict(_DEFAULT_CONFIG)


def write_config(cfg: dict[str, Any]) -> dict[str, Any]:
    _ensure_dir()
    merged = dict(_DEFAULT_CONFIG)
    merged.update(cfg or {})
    CONFIG_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    return merged


def _read_state() -> dict[str, Any]:
    try:
        st = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(st, dict):
            st.setdefault("last_check_iso", "")
            st.setdefault("dm_sent_ids", [])
            return st
    except Exception:
        pass
    return {"last_check_iso": "", "dm_sent_ids": []}


def _write_state(st: dict[str, Any]) -> None:
    _ensure_dir()
    STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def is_important(analysis: Any, cfg: dict[str, Any]) -> bool:
    """Mail quan trọng = category cần xử lý HOẶC priority >= ngưỡng config."""
    cat = str(getattr(analysis, "category", "")).split(".")[-1]
    if cat in (cfg.get("categories") or []):
        return True
    try:
        if float(getattr(analysis, "priority", 0) or 0) >= float(cfg.get("min_priority", 60)):
            return True
    except Exception:
        pass
    return False


def run_check(*, mark_checked: bool = True, limit: int = 20) -> dict[str, Any]:
    """Đọc mail từ lần check trước → lọc quan trọng → trả report (chưa DM).

    mark_checked=False → chạy thử (không đổi last_check) — dùng cho lệnh
    'cảnh báo mail ngay' (không ảnh hưởng chu kỳ 4h).
    """
    cfg = read_config()
    st = _read_state()
    now = _dt.datetime.now()
    since_iso = st.get("last_check_iso") or ""
    try:
        if since_iso:
            since_dt = _dt.datetime.fromisoformat(since_iso)
        else:
            since_dt = now - _dt.timedelta(hours=4)
    except Exception:
        since_dt = now - _dt.timedelta(hours=4)
    # không lùi quá 7 ngày (chống quét lại cả hộp thư)
    if (now - since_dt).total_seconds() > 7 * 86400:
        since_dt = now - _dt.timedelta(days=7)
    since_ddmm = f"{since_dt.day:02d}/{since_dt.month:02d}"
    checked_at = now.strftime("%Y-%m-%dT%H:%M:%S")
    # (24/11 fix E2E) Zimbra 'after:' KHÔNG bao gồm chính ngày đó (strict greater)
    # → mail hôm nay bị bỏ sót khi since=hôm nay. Dùng 'date:' cho hôm nay,
    # 'after:(ngày trước since)' cho các ngày trước rồi lọc client-side >= since.
    try:
        from quan_ai_brain.office.email_connector import SOAPMailConnector, analyze_email
        connector = SOAPMailConnector()
        if since_ddmm == f"{now.day:02d}/{now.month:02d}":
            raw = connector.fetch_since(since_ddmm, limit=limit)  # date: qua read path? — dùng fetch_today-like
        else:
            prev = since_dt - _dt.timedelta(days=1)
            raw = connector.fetch_since(f"{prev.day:02d}/{prev.month:02d}", limit=limit)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "checked_at": checked_at, "fail_honest": True}
    # lọc client-side: chỉ giữ mail >= since_dt (theo ngày để tránh lệch giờ):
    def _pdt(s):
        try:
            return _dt.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
        except Exception:
            return None
    _cutoff_day = since_dt.date()
    raw = [m for m in raw
           if (_pdt(m.received_at_utc) or _dt.datetime.min).date() >= _cutoff_day]
    important = []
    for msg in raw:
        try:
            a = analyze_email(msg)
        except Exception:
            continue
        if not is_important(a, cfg):
            continue
        if msg.message_id in set(st.get("dm_sent_ids") or []):
            continue  # đã DM rồi — không re-DM
        preview = (msg.body_preview or "").strip()
        important.append({
            "message_id": msg.message_id,
            "subject": msg.subject,
            "sender": msg.sender,
            "received_at_utc": msg.received_at_utc,
            "category": str(getattr(a, "category", "")).split(".")[-1],
            "priority": getattr(a, "priority", None),
            "urgency": getattr(a, "urgency", None),
            "todo": getattr(a, "todo", "") or "",
            "deadline": getattr(a, "deadline", "") or "",
            "summary": preview[:400],
        })
    report = {"ok": True, "checked_at": checked_at, "window_since": since_ddmm,
              "fetched": len(raw), "important": important}
    if mark_checked:
        st["last_check_iso"] = checked_at
        _write_state(st)
    return report


def mark_dm_sent(message_ids: list[str]) -> None:
    st = _read_state()
    ids = set(st.get("dm_sent_ids") or [])
    ids.update(message_ids)
    st["dm_sent_ids"] = sorted(ids)[-200:]  # giữ tối đa 200 id gần nhất
    _write_state(st)


def check_documents(mark_checked: bool = True) -> dict[str, Any]:
    """(24/11 S3-v7, owner: 'đọc và tóm tắt văn bản Voffice... DM đến anh')
    Kiểm tra VĂN BẢN Voffice mới (gián tiếp qua mail) từ lần check trước.

    Dùng cùng state last_check_iso với mail alert. Trả report.documents mới
    (lọc theo vb_docs_sent_ids để không re-DM).
    """
    cfg = read_config()
    st = _read_state()
    now = _dt.datetime.now()
    since_iso = st.get("last_check_iso") or ""
    try:
        since_dt = _dt.datetime.fromisoformat(since_iso) if since_iso else now - _dt.timedelta(hours=4)
    except Exception:
        since_dt = now - _dt.timedelta(hours=4)
    if (now - since_dt).total_seconds() > 7 * 86400:
        since_dt = now - _dt.timedelta(days=7)
    checked_at = now.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        from tools.voffice_documents import list_documents
        res = list_documents(f"{since_dt.day:02d}/{since_dt.month:02d}", limit=20)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "checked_at": checked_at}
    if "error" in res:
        return {"ok": False, "error": res["error"], "checked_at": checked_at}
    sent = set(st.get("vb_docs_sent_ids") or [])
    new_docs = []
    for d in res.get("documents", []):
        key = d.get("mid") or d.get("subject", "").lower()
        if key in sent:
            continue
        d["doc_key"] = key
        new_docs.append(d)
    report = {"ok": True, "checked_at": checked_at, "documents": new_docs,
              "total_docs": res.get("count", 0)}
    if mark_checked and new_docs:
        # chỉ update vb_docs_sent_ids (last_check do mail alert quản)
        st["vb_docs_sent_ids"] = sorted(set(st.get("vb_docs_sent_ids") or []) |
                                        {d["doc_key"] for d in new_docs})[-100:]
        _write_state(st)
    return report


def format_documents_dm(report: dict[str, Any]) -> str | None:
    """DM cảnh báo văn bản mới. None = không có."""
    docs = report.get("documents") or []
    if not docs:
        return None
    lines = [f"📄 VĂN BẢN VOFFICE MỚI — {len(docs)} văn bản (nguồn gián tiếp qua mail):"]
    for i, d in enumerate(docs[:5], 1):
        lines.append("")
        so = f"Số {d['so_ky_hieu']} · " if d.get("so_ky_hieu") else ""
        lines.append(f"{i}. {so}{d['subject'][:100]}")
        lines.append(f"   👤 {d['sender']} · 🕐 {d['received']}")
        s = (d.get("summary") or "").strip()
        if s:
            lines.append(f"   💬 Tóm tắt: {s[:280]}{'…' if len(s) > 280 else ''}")
    lines.append("")
    lines.append("(Tự động kiểm tra 4h/lần — R2 chỉ đọc. Portal Voffice LAN-only, "
                 "đọc trực tiếp cần anh login M-Suite.)")
    return "\n".join(lines)


def format_dm(report: dict[str, Any]) -> str | None:
    """Format DM cảnh báo — tóm tắt nội dung từng mail quan trọng. None = không có gì."""
    items = report.get("important") or []
    if not items:
        return None
    lines = [f"🔔 CẢNH BÁO MAIL — {len(items)} mail quan trọng cần anh xử lý:"]
    for i, it in enumerate(items[:5], 1):
        lines.append("")
        lines.append(f"{i}. [{it['category']}] {it['subject']}")
        lines.append(f"   👤 {it['sender']} · 🕐 {it['received_at_utc']}")
        if it.get("deadline"):
            lines.append(f"   ⏰ Thời hạn: {it['deadline']}")
        if it.get("todo"):
            lines.append(f"   ✅ Việc cần làm: {it['todo']}")
        s = (it.get("summary") or "").strip()
        if s:
            lines.append(f"   💬 Tóm tắt: {s[:300]}{'…' if len(s) > 300 else ''}")
    lines.append("")
    lines.append("(Tự động đọc 4h/lần — R2 chỉ đọc. Anh xem mail để xử lý chi tiết.)")
    return "\n".join(lines)


if __name__ == "__main__":
    # CLI chạy thử: python mail_alert.py check
    rep = run_check(mark_checked=False)
    print(format_dm(rep) or "Không có mail quan trọng mới.")
