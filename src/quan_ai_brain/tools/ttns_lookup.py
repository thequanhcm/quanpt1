"""TTNS Lookup tool — Sprint 6-GOP hạng mục (4).

Bọc skill ttns-meeting-lookup (read-only, proxy nội bộ) thành tool cho chat
pipeline: trả câu trả lời JSON của dịch vụ hoặc None (fail-closed).

Nguyên tắc:
- CHỈ TRA CỨU: không đặt/sửa/hủy lịch, không đặt phòng (skill cấm sẵn).
- Dữ liệu nhân sự KHÔNG cache vào DB, KHÔNG log nội dung; chỉ trả về cho LLM
  tổng hợp trong phiên chat hiện tại.
- Script skill trả exit != 0 hoặc JSON lỗi → None → chat nói "chưa tra cứu được".
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

_SKILL_SCRIPT = Path(
    r"C:/Users/DELL/AppData/Local/netmind_desktop/skills/"
    r"ttns-meeting-lookup/scripts/ttns-meeting-lookup.py"
)
_SKILL_PY = Path(
    r"C:/Users/DELL/AppData/Local/netmind_desktop/netmind-agent/venv/Scripts/python.exe"
)
_TIMEOUT_S = 35


def ttns_lookup(question: str) -> dict[str, Any] | None:
    """Gọi skill TTNS với câu hỏi tự do tiếng Việt.

    Returns:
        dict với keys 'answer' (text) + 'conversationId' khi thành công;
        None khi: question rỗng, script thiếu, timeout, JSON lỗi.
    """
    if not question or not question.strip():
        return None
    if not _SKILL_SCRIPT.exists() or not _SKILL_PY.exists():
        return None
    try:
        r = subprocess.run(
            [str(_SKILL_PY), str(_SKILL_SCRIPT), question.strip()[:500]],
            capture_output=True, text=True, timeout=_TIMEOUT_S, encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    out = (r.stdout or "").strip()
    if not out:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "answer" not in data:
        return None
    return data


# Intent đơn giản để nhắc tool trong chat pipeline (an toàn: sai → không gọi,
# chỉ tốn 1 check string; không dùng LLM cho routing)
_KEYWORDS = (
    "lịch họp", "họp gì", "meeting", "cuộc họp", "phòng họp",
    "là ai", "nhân viên", "sđt", "số điện thoại", "email",
    "ttns", "thông tin nhân sự", "lịch của", "họp hôm nay", "họp ngày mai",
    "họp tuần", "còn trống không", "bận những khung",
)


def looks_like_ttns_query(text: str) -> bool:
    """True nếu văn bản có dấu hiệu tra cứu nhân sự/lịch họp nội bộ."""
    if not text:
        return False
    low = text.lower()
    return any(k in low for k in _KEYWORDS)
