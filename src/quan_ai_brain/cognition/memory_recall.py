# -*- coding: utf-8 -*-
"""MEMORY RECALL — chế độ hồi tưởng theo THỜI GIAN cho câu hỏi meta.

(18/11/2026, yêu cầu owner: "trí nhớ này là riêng tư của cá nhân, cấu hình để
hoạt động: trí nhớ, biểu cảm, suy luận, phân tích, tư duy")

Vấn đề: CognitiveRetriever chỉ làm token LIKE-matching — câu hỏi TỔNG QUÁT
("anh đã nói gì với em 1 tháng trước", "trí nhớ của em lưu gì", "nhớ gì về
chụp hình") không có token nội dung khớp → retrieval trả về chính câu hỏi
(self-match) → GLM trả lời "em không nhớ". Dữ liệu thực tế có 3.500+ episodes
từ 19/10 đầy đủ trong brain.db.

Giải pháp: phát hiện câu hỏi META về trí nhớ → recall theo KHOẢNG THỜI GIAN
(episodes gần nhất trong khoảng được hỏi) + đếm thống kê → block có cấu trúc
đưa vào context cho GLM tóm tắt. Toàn bộ dữ liệu nằm LOCAL brain.db (riêng tư
cá nhân owner) — chỉ excerpt đi vào prompt, không có gì rời máy.

Fail-honest: lỗi recall → trả None, caller đi tiếp đường retrieval thường.
"""
from __future__ import annotations

import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# --- Patterns câu hỏi META về trí nhớ (tiếng Việt) ---
_META_PATTERNS = [
    r"\b(nhớ|ghi nhớ|ghi_nhớ)\b.*\b(gì|những gì|cái gì|điều gì)\b",
    r"\b(liệt kê|kể|cho xem|đâu)\b.*\b(trí nhớ|ghi nhớ|ký ức)\b",
    r"\b(trí nhớ|ghi nhớ|ký ức)\b.*\b(lưu|chứa|có gì|nào)\b",
    r"\b(anh|em|chị)\s+(đã\s+)?(nói|nhắn|trao đổi|hỏi|bảo)\b.*\b(trước|lúc trước|tháng trước|tuần trước|hôm qua|早|1 tháng|2 tuần)\b",
    r"\b(hôm qua|tuần trước|tháng trước|tháng [1-9]|lần trước|trước đây)\b.*\b(nói|nhắn|trao đổi|hỏi)\b",
    r"\b(chúng ta|anh và em)\b.*\b(đã)?\s*(nói chuyện|trao đổi|học|làm)\b.*\b(trước|gần đây)\b",
    r"\bnhớ\b.*\b(được|không)\b.*\b(không|gì)\b",
]

# Khoảng thời gian hỏi → (số ngày lookback, nhãn)
_TIME_SPAN_PATTERNS = [
    (r"\b1\s*tháng\s*trước\b|\btháng\s*trước\b", 45, "khoảng 1 tháng trước"),
    (r"\b2\s*tháng\s*trước\b", 75, "khoảng 2 tháng trước"),
    (r"\b\d+\s*tháng\s*trước\b", None, "n tháng trước"),  # parse riêng
    (r"\btuần\s*trước\b|\b1\s*tuần\s*trước\b", 14, "tuần trước"),
    (r"\b2\s*tuần\s*trước\b", 21, "2 tuần trước"),
    (r"\bhôm\s*qua\b", 2, "hôm qua"),
    (r"\btrước\s*đây\b|\blúc\s*trước\b|\bcách\s*đây\b", 45, "trước đây"),
    (r"\btháng\s*10\b", 45, "tháng 10"),
    (r"\btháng\s*9\b", 75, "tháng 9"),
]


def is_memory_meta_query(query: str) -> bool:
    """True nếu câu hỏi là meta về trí nhớ (hỏi về nội dung đã ghi nhớ)."""
    q = query.strip().lower()
    if len(q) < 6:
        return False
    return any(re.search(p, q) for p in _META_PATTERNS)


def _resolve_span(query: str) -> tuple[int, str, str, str] | None:
    """Trả về (days_back, label, date_from_iso, date_to_iso) hoặc None."""
    today = datetime.now(timezone.utc)
    for pat, days, label in _TIME_SPAN_PATTERNS:
        if not re.search(pat, query.strip().lower()):
            continue
        if days is None:
            m = re.search(r"(\d+)\s*tháng\s*trước", query.lower())
            days = int(m.group(1)) * 30 if m else 45
        if "tháng 10" in query.lower():
            d_from, d_to = "2026-10-01", "2026-11-01"
        elif "tháng 9" in query.lower():
            d_from, d_to = "2026-09-01", "2026-10-01"
        else:
            d_to = today.isoformat()
            d_from = (today - timedelta(days=days)).isoformat()
        return days, label, d_from, d_to
    # Không nói thời gian → mặc định 45 ngày gần nhất
    if is_memory_meta_query(query):
        d_to = today.isoformat()
        d_from = (today - timedelta(days=45)).isoformat()
        return 45, "45 ngày gần nhất", d_from, d_to
    return None




_STOPWORDS = {
    "anh", "em", "gì", "những", "gì", "cái", "điều", "đã", "nói", "nhớ", "ghi",
    "với", "cho", "xem", "kể", "lại", "trước", "đây", "tháng", "tuần", "hôm",
    "qua", "là", "của", "và", "có", "không", "được", "nào", "về", "việc",
    "chúng", "tôi", "bạn", "cherry", "liệt", "kê", "trao", "đổi", "lúc",
}


def _extract_keywords(query: str, max_kw: int = 6) -> list[str]:
    """Lấy token có nghĩa (>2 ký tự, không stopword) từ query."""
    tokens = re.findall(r"[a-zA-Zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]{2,}", query.lower())
    seen: list[str] = []
    for t in tokens:
        if t in _STOPWORDS or t in seen:
            continue
        seen.append(t)
        if len(seen) >= max_kw:
            break
    return seen


def recall_memory_summary(
    query: str,
    db_path: Path | str,
    *,
    max_episodes: int = 40,
    max_chars: int = 3500,
) -> dict[str, Any] | None:
    """Hồi tưởng trí nhớ theo thời gian từ brain.db (LOCAL — riêng tư owner).

    Returns: {"block": str, "n_scanned": int, "span_label": str} hoặc None
    nếu không phải câu hỏi meta / không có dữ liệu / lỗi (fail-honest).
    """
    try:
        span = _resolve_span(query)
        if span is None:
            return None
        days, label, d_from, d_to = span

        conn = sqlite3.connect(str(db_path), timeout=5.0)
        try:
            cur = conn.cursor()
            # 1. Thống kê tổng
            total_mem = cur.execute(
                "SELECT COUNT(*) FROM memories WHERE lifecycle_status='active'"
            ).fetchone()[0]
            total_ep = cur.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            oldest = cur.execute(
                "SELECT MIN(created_at_utc) FROM episodes"
            ).fetchone()[0]
            # 2. Episodes trong khoảng thời gian hỏi
            rows = cur.execute(
                "SELECT created_at_utc, kind, summary FROM episodes "
                "WHERE created_at_utc >= ? AND created_at_utc <= ? "
                "ORDER BY created_at_utc DESC LIMIT ?",
                (d_from[:10], d_to[:10] + "Z", max_episodes * 4),
            ).fetchall()

            # 2.5 HYBRID: nếu query có từ khóa nội dung ("chụp ảnh", "Pi5", "họp") →
            # search LIKE theo token trong episodes + memories (bỏ qua span) —
            # recall thuần thời gian không đủ cho câu "em nhớ gì về X".
            kw_lines: list[str] = []
            keywords = _extract_keywords(query)
            if keywords:
                like_clauses = " OR ".join(["summary LIKE ?"] * len(keywords))
                try:
                    kw_rows = cur.execute(
                        f"SELECT created_at_utc, kind, summary FROM episodes "
                        f"WHERE ({like_clauses}) ORDER BY created_at_utc DESC LIMIT ?",
                        (*[f"%{kw}%" for kw in keywords], max_episodes),
                    ).fetchall()
                except sqlite3.Error:
                    kw_rows = []
                for ts, kind, summary in kw_rows[:12]:
                    day = str(ts)[:16].replace("T", " ")
                    text = (summary or "").strip().replace("\n", " ")[:200]
                    if text:
                        kw_lines.append(f"- {day} | {text}")
                try:
                    mem_rows = cur.execute(
                        f"SELECT created_at_utc, content FROM memories "
                        f"WHERE lifecycle_status='active' AND "
                        f"({like_clauses.replace('summary', 'content')}) "
                        f"ORDER BY created_at_utc DESC LIMIT 8",
                        (*[f"%{kw}%" for kw in keywords],),
                    ).fetchall()
                except sqlite3.Error:
                    mem_rows = []
                for ts, content in mem_rows[:8]:
                    day = str(ts)[:16].replace("T", " ")
                    text = (content or "").strip().replace("\n", " ")[:200]
                    if text:
                        kw_lines.append(f"- {day} | [memory] {text}")
        finally:
            conn.close()

        if not rows and total_ep == 0:
            return None

        # 3. Build block có cấu trúc (excerpt ngắn, không tràn prompt)
        lines: list[str] = []
        lines.append(
            f"[MEMORY RECALL — dữ liệu riêng tư LOCAL của owner (brain.db), "
            f"tổng {total_mem} trí nhớ active + {total_ep} episodes, "
            f"ghi nhớ từ {str(oldest)[:10]}]"
        )
        # Ưu tiên 1: nội dung khớp từ khóa câu hỏi (liên quan trực tiếp nhất)
        if kw_lines:
            lines.append(f"Nội dung khớp từ khóa ({', '.join(keywords)}):")
            lines.extend(kw_lines[:14])
        # Ưu tiên 2: timeline gần đây trong span
        lines.append(f"Khoảng anh hỏi: {label} → tìm thấy {len(rows)} ghi chép:")
        picked = 0
        for ts, kind, summary in rows:
            if picked >= max_episodes:
                break
            day = str(ts)[:16].replace("T", " ")
            text = (summary or "").strip().replace("\n", " ")[:220]
            if not text:
                continue
            lines.append(f"- {day} | {text}")
            picked += 1
        if picked == 0 and not kw_lines:
            lines.append("(không có ghi chép chi tiết trong khoảng này — báo thật với anh)")
        block = "\n".join(lines)
        if len(block) > max_chars:
            block = block[:max_chars] + " …]"
        return {"block": block, "n_scanned": len(rows), "span_label": label}
    except Exception:
        return None  # fail-honest — caller đi tiếp retrieval thường
