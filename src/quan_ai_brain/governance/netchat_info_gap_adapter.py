"""V3 Sprint 3 — NetChat integration cho Information Gap Awareness.

Gửi yêu cầu bổ sung thông tin qua kênh hiện có (KHÔNG tạo bot mới) và
tiếp nhận câu trả lời của chủ nhân, phân loại đúng 3 loại giao tiếp (V3 §10):
- Information Request  → module này (format [CẦN ANH QUANPT1 BỔ SUNG THÔNG TIN])
- Approval Request     → ApprovalOrchestrator hiện có (KHÔNG đụng)
- Progress Report      → kênh thường

Điểm nối vào command center: route_message() bước 0.5 — trước system commands,
sau "ok"/approval. Owner trả lời câu hỏi (có "TASK-xxxx" trong tin + không khớp
lệnh duyệt) → map về câu hỏi đang OPEN của task → record_owner_reply.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from quan_ai_brain.cognition.information_gap_analyzer import (
    InformationGapAnalyzer,
    ReadinessStatus,
)

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent

_NETCHAT_BOT = (
    r"C:\Users\DELL\AppData\Local\netmind_desktop\skills\bot-netchat\netchat_bot.py"
)
_AGENT_PY = (
    r"C:\Users\DELL\AppData\Local\netmind_desktop\netmind-agent\venv\Scripts\python.exe"
)

CHANNEL_ID = "4phc9b1mx78qjq3grxcw89u94a"

# Mã nhiệm vụ trong tin nhắn: TASK-xxxx (chữ/số)
_TASK_RE = re.compile(r"TASK[-_]?([A-Za-z0-9]{3,12})", re.IGNORECASE)


def has_waiting_task(task_code: str) -> bool:
    """True khi task_code đang chờ trong information gap DB (V3 §8).

    Dùng bởi netchat_approval_adapter để phân biệt: tin có mã TASK không khớp
    lệnh duyệt + task đang chờ thông tin → route sang info-gap handler.
    """
    if not task_code:
        return False
    code = task_code.upper().replace("_", "-")
    try:
        analyzer = get_analyzer()
    except Exception:
        return False
    for row in analyzer.list_waiting():
        wid = row["task_id"].upper().replace("_", "-")
        if wid == code or wid.endswith(code.replace("TASK-", "-")) or code in wid:
            return True
    return False


def get_analyzer() -> InformationGapAnalyzer:
    return InformationGapAnalyzer(workspace=WORKSPACE)


def send_info_request(analysis: Any, *, message_id_capture: bool = True) -> dict[str, Any]:
    """Gửi tin [CẦN ANH QUANPT1 BỔ SUNG THÔNG TIN] qua kênh NetChat hiện có.

    Dùng đúng 2 bước của skill bot-netchat: send → CONFIRM-REQUIRED hash →
    resend --confirmed. KHÔNG tạo bot mới. Trả về {sent, message_hint, error}.
    """
    text = get_analyzer().render_info_request(analysis)
    if not text:
        return {"sent": False, "error": "nothing_to_send"}
    try:
        first = subprocess.run(
            [_AGENT_PY, _NETCHAT_BOT, "send", CHANNEL_ID, "--to-bot", text],
            capture_output=True, text=True, timeout=30,
        )
        out = (first.stdout or "") + (first.stderr or "")
        if first.returncode == 0 and "CONFIRM-REQUIRED" not in out:
            return {"sent": True, "raw": out[:300]}
        # 2 bước: hash xác nhận
        import re as _re

        m = _re.search(r"CONFIRM-REQUIRED:\s*([0-9a-f]{8,64})", out)
        if not m:
            return {"sent": False, "error": f"no_confirm_hash: {out[:200]}"}
        second = subprocess.run(
            [_AGENT_PY, _NETCHAT_BOT, "send", CHANNEL_ID, "--to-bot", text,
             "--confirmed", m.group(1)],
            capture_output=True, text=True, timeout=30,
        )
        ok = second.returncode == 0
        return {"sent": ok, "raw": ((second.stdout or "") + (second.stderr or ""))[:300]}
    except Exception as exc:
        return {"sent": False, "error": str(exc)[:200]}


def handle_owner_info_reply(
    text: str,
    *,
    sender_user_id: str = "",
) -> str | None:
    """Owner trả lời câu hỏi bổ sung thông tin → cập nhật trạng thái chờ.

    V3 §8.1: xác định task, lưu nguồn = phản hồi chủ nhân, phân tích lại
    khoảng trống, hỏi tiếp phần còn thiếu hoặc báo đã đủ. Trả lời KHÔNG
    PHẢI phê duyệt — approval vẫn thuộc ApprovalOrchestrator.

    Return None khi tin không phải trả lời thông tin (caller fallback tiếp).
    """
    if not text:
        return None
    t = text.strip()

    # Chỉ xử lý tin có mã nhiệm vụ — tránh bắt nhầm chat thường.
    m = _TASK_RE.search(t)
    if not m:
        return None

    analyzer = get_analyzer()
    task_code = f"TASK-{m.group(1)}"

    # Task đang chờ nào khớp mã (mã trong analyzer có dạng TASK-xxxxxxxx)?
    candidates = [
        row for row in analyzer.list_waiting()
        if row["task_id"].upper() == task_code.upper()
        or row["task_id"].upper().replace("_", "-").endswith(task_code.upper().replace("TASK-", ""))
    ]
    if not candidates:
        return None  # không phải trả lời cho info-gap → fallback lệnh khác

    row = candidates[0]
    spec_json = row["spec_json"]

    # Tìm câu hỏi OPEN khớp nội dung tin nhắn (ưu tiên khớp question_id nếu
    # owner reply kèm mã câu hỏi; nếu không, map câu hỏi OPEN đầu tiên còn thiếu).
    import json as _json

    spec = _json.loads(spec_json)
    open_questions = [q for q in spec.get("questions", []) if q.get("status") == "OPEN"]
    if not open_questions:
        return None

    matched_qid = ""
    for q in open_questions:
        if q["question_id"].lower() in t.lower():
            matched_qid = q["question_id"]
            break
    if not matched_qid:
        matched_qid = open_questions[0]["question_id"]

    result = analyzer.record_owner_reply(
        row["task_id"], matched_qid, t,
        source=f"netchat:owner {sender_user_id or 'quanpt1'}",
    )
    if not result.get("ok"):
        return None

    if result.get("all_answered"):
        return (
            f"✅ Đã nhận đủ thông tin cho {row['task_id']}. Em cập nhật vào nhiệm vụ "
            "và tiếp tục các bước được phép (phân tích/lập kế hoạch). "
            "Lưu ý trung thực: việc anh cung cấp thông tin KHÔNG PHẢI phê duyệt "
            "hành động — nếu bước tiếp theo cần phê duyệt, em sẽ lập hồ sơ riêng "
            "qua Approval Card."
        )
    remaining = result.get("still_missing", [])
    return (
        f"✅ Đã nhận phần trả lời cho {row['task_id']} — em ghi nhận nguồn là "
        f"phản hồi của anh. Còn thiếu {len(remaining)} thông tin, anh trả lời tiếp "
        f"các câu còn lại giúp em (câu hỏi: {', '.join(remaining)}). "
        "Trạng thái: VẪN ĐANG CHỜ — CHƯA THỰC HIỆN HÀNH ĐỘNG NGHIỆP VỤ."
    )
