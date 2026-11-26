"""Episodic time recall — trả lời câu hỏi về quá khứ bằng dữ liệu thật.

(26/11/2026, Sprint CHERRY-ĐA-NGHIỆP-VỤ — feedback owner 12:35: câu
"hôm qua anh đã hỏi em cái gì?" bị CHERRY né dù brain.db có dữ liệu).

Audit gốc rễ: (1) semantic recall chỉ match NGỮ NGHĨA (embedding), câu hỏi
về THỜI GIAN không có keyword trùng nội dung hội thoại cũ → 0 hit;
(2) không module nào tra bảng episodes theo khoảng thời gian; (3) giờ DB
ghi UTC, owner nói giờ VN (UTC+7) — phải đổi múi đúng.

Fail-open, chỉ-đọc: mọi lỗi → trả None, chat vẫn chạy. Không đụng R4/R5.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_VN_TZ = timezone(timedelta(hours=7))

# Từ khóa câu hỏi về quá khứ (thận trọng: chỉ inject khi có tín hiệu thời gian)
_KEYWORDS_SPECIFIC_DAY = ("hôm qua", "hom qua", "hôm kia", "hom kia", "hôm trước")
_KEYWORDS_TODAY = ("hôm nay", "sáng nay", "chiều nay", "tối nay", "lúc sáng")
_KEYWORDS_RECENT = (
    "lần trước", "lần trước đó", "trước đó", "anh đã hỏi", "anh đã nói",
    "anh đã nhắn", "anh hỏi gì", "anh nói gì", "chúng ta đã nói",
    "mình đã nói", "đã trò chuyện", "đã bàn",
)


def looks_like_past_query(text: str) -> bool:
    """Detector câu hỏi về quá khứ — thận trọng, chỉ khớp tín hiệu thời gian."""
    t = (text or "").lower()
    if not t:
        return False
    return any(
        k in t
        for k in _KEYWORDS_SPECIFIC_DAY + _KEYWORDS_TODAY + _KEYWORDS_RECENT
    )


def _resolve_window(text: str) -> tuple[str, datetime, datetime]:
    """Trả (nhãn VN, start_utc, end_utc) theo từ khóa trong câu hỏi.

    Hôm qua/hôm nay tính theo ngày VN (UTC+7) rồi đổi ra khung UTC.
    """
    t = (text or "").lower()
    now_vn = datetime.now(_VN_TZ)
    today = now_vn.date()

    if any(k in t for k in _KEYWORDS_SPECIFIC_DAY):
        d = today - timedelta(days=1)
        label = f"NGÀY {d.strftime('%d/%m/%Y')} (hôm qua)"
    elif any(k in t for k in _KEYWORDS_TODAY):
        d = today
        label = f"NGÀY {d.strftime('%d/%m/%Y')} (hôm nay)"
    else:
        d = today - timedelta(days=3)
        label = "3 NGÀY GẦN NHẤT"

    start_utc = datetime(d.year, d.month, d.day, tzinfo=_VN_TZ).astimezone(
        timezone.utc
    )
    end_utc = start_utc + timedelta(days=1 if "3 NGÀY" not in label else 3)
    return label, start_utc, end_utc


def recall_past_chat_turns(
    db_path: Path | str, query: str, max_items: int = 12
) -> dict[str, Any] | None:
    """Tra episodes kind='chat_turn' trong khung thời gian được hỏi.

    Trả dict {label, items: [{gio_vn, user, reply}], empty_days} hoặc None
    khi lỗi (fail-open). 0 item → vẫn trả (kèm các ngày CÓ dữ liệu gần
    nhất) để CHERRY trả lời trung thực thay vì né chung chung.
    """
    try:
        label, start_utc, end_utc = _resolve_window(query)
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT created_at_utc, metadata_json FROM episodes "
            "WHERE kind='chat_turn' AND created_at_utc >= ? AND created_at_utc < ? "
            "ORDER BY created_at_utc LIMIT ?",
            (start_utc.isoformat(), end_utc.isoformat(), max_items),
        ).fetchall()

        items: list[dict[str, str]] = []
        for r in rows:
            try:
                meta = json.loads(r["metadata_json"] or "{}")
            except json.JSONDecodeError:
                meta = {}
            user = str(meta.get("user_query", ""))[:160]
            reply = str(meta.get("assistant_reply", ""))[:160]
            ts = str(r["created_at_utc"])[:19]
            try:
                gio_vn = (
                    datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
                    .astimezone(_VN_TZ)
                    .strftime("%H:%M")
                )
            except ValueError:
                gio_vn = ts[11:16] if len(ts) >= 16 else "??:??"
            items.append({"gio_vn": gio_vn, "user": user, "reply": reply})

        # Các ngày CÓ dữ liệu gần nhất (khi khung rỗng → trung thực "rỗng")
        empty_days: list[str] = []
        if not items:
            empty_days = [
                f"{(row[0] or '')[:10]} ({row[1]} lượt)"
                for row in con.execute(
                    "SELECT substr(created_at_utc,1,10) d, COUNT(*) "
                    "FROM episodes WHERE kind='chat_turn' "
                    "GROUP BY d ORDER BY d DESC LIMIT 5"
                ).fetchall()
            ]
        con.close()
        return {"label": label, "items": items, "empty_days": empty_days}
    except Exception:
        return None


def render_episodic_block(data: dict[str, Any] | None) -> str:
    """Render block inject vào system_instructions (fail-open: None → '')."""
    if not data:
        return ""
    lines = [f"[HỘI THOẠI {data['label']} — TRUY XUẤT TỪ TRÍ NHỚ EPISODIC]"]
    items = data.get("items") or []
    if items:
        for it in items:
            lines.append(
                f"- {it['gio_vn']} (giờ VN) anh hỏi: \"{it['user']}\" | "
                f"em trả lời: \"{it['reply']}\""
            )
        lines.append(
            "→ Trả lời ANH BẰNG CHÍNH DỮ LIỆU TRÊN (tóm tắt đúng, trích giờ), "
            "KHÔNG nói 'không có thông tin'."
        )
    else:
        days = " ; ".join(data.get("empty_days") or []) or "không rõ"
        lines.append(
            "→ KHÔNG có bản ghi hội thoại trong khung này. Hãy nói TRUNG THỰC "
            f"khoảng đó không có bản ghi (server có thể offline), và liệt kê "
            f"các ngày CÓ dữ liệu gần nhất: {days}."
        )
    return "\n".join(lines)
