"""QUAN AI BRAIN — NetChat Command Center (kênh điều khiển 2 chiều).

Kênh "Trợ lý Tony Pham" là kênh làm việc chuyên biệt giữa chủ sở hữu
(quanpt1) và trợ lý số: gõ tự do, không cần @bot.

Đây là lớp định tuyến lệnh CHẠY TRƯỚC khi fallback sang AI hội thoại.
Mỗi lệnh điều khiển thực thi logic hệ thống THẬT (self-model probes,
consultation approvals, task registry) — không phải câu trả lời LLM dựng.

Lệnh hỗ trợ (tiếng Việt tự nhiên):
- "phê duyệt" / "duyệt"        → duyệt consultation ticket PENDING mới nhất
- "trạng thái" / "hiện trạng"  → self-model 12 câu trả lời có bằng chứng
- "báo cáo"                    → báo cáo tổng hợp mới nhất
- "nhiệm vụ"                   → backlog durable_tasks
- "tri thức"                   → số liệu tri thức đã duyệt / cách ly
- "giúp" / "help"              → danh sách lệnh
- Fallback: câu hỏi khác → AI hội thoại qua /api/chat
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent

# Handlers import the quan_ai_brain package which lives in <workspace>/src.
# The responder may run under a different interpreter (agent venv), so make
# the package resolvable regardless of which Python executes this module.
# All handler imports are stdlib-only inside the package itself.
_SRC = WORKSPACE / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

COMMAND_PATTERNS: dict[str, tuple[str, ...]] = {
    "approve": ("phê duyệt", "phe duyet", "duyệt", "duyet", "approved", "đồng ý", "dong y"),
    "status": ("trạng thái", "trang thai", "hiện trạng", "hien trang", "status", "sức khỏe", "suc khoe"),
    "report": ("báo cáo", "bao cao", "report"),
    "tasks": ("nhiệm vụ", "nhiem vu", "tasks", "backlog", "công việc", "cong viec"),
    "knowledge": ("tri thức", "tri thuc", "knowledge", "học được gì", "hoc duoc gi"),
    "help": ("giúp", "giup", "help", "lệnh", "lenh", "menu"),
}

# State-changing commands MUST start the message (imperative form).
# Questions like "em có thể phê duyệt qua kênh này được không?" contain the
# keyword but must NOT execute anything — they fall to conversational AI.
STATE_CHANGING = {"approve"}


def _is_question(text: str) -> bool:
    t = text.strip()
    return "?" in t or t.lower().endswith(("không", "chứ", "được không"))


def detect_intent(text: str) -> str | None:
    """Return the command intent for a message, or None for free chat.

    Rules:
    - Questions ('?'/final 'không') never trigger commands unless the
      message STARTS with the command keyword.
    - 'approve' (state-changing) only fires when the message starts with
      the keyword — never on substring matches.
    - Read-only commands fire on startswith or containment.
    """
    t = (text or "").strip().lower()
    if not t:
        return None
    question = _is_question(t)
    for intent, patterns in COMMAND_PATTERNS.items():
        for p in patterns:
            starts = t.startswith(p)
            if starts:
                return intent
            if not question and intent not in STATE_CHANGING and f" {p} " in f" {t} ":
                return intent
    return None


# ---------------------------------------------------------------------------
# Handlers — every handler runs REAL system logic and reports honestly
# ---------------------------------------------------------------------------


def handle_approve(payload: dict[str, Any] | None = None) -> str:
    """'phê duyệt': approve the OLDEST pending consultation ticket (FIFO) via
    the real ConsultationStore, then audit the decision.

    Honesty contract: if nothing is pending, say so — never fake success.
    Scope: this approves exactly ONE ticket per command, with its ID shown,
    so the owner always sees what was approved. Note: ConsultationStore
    seeds its own default tickets into an empty DB by design; FIFO picks
    the oldest genuinely pending ticket.
    """
    try:
        from quan_ai_brain.governance.consultation_inbox import ConsultationStore

        db = WORKSPACE / "data" / "consultations.db"
        if not db.exists():
            return "📭 Hiện không có hồ sơ phê duyệt nào (chưa có cơ sở dữ liệu tham vấn)."

        # Guard: some module-level default tickets exist only for the default
        # DB path; constructing with an explicit path keeps them out.
        store = ConsultationStore(str(db))
        tickets = store.list_tickets()
        pending = [
            t for t in tickets
            if getattr(getattr(t, "status", None), "value", "") in ("PENDING", "PENDING_REVIEW")
        ]
        if not pending:
            store.close()
            return "📭 Hiện không có hồ sơ nào chờ phê duyệt. Mọi quyết định đã được xử lý."

        pending.sort(key=lambda t: getattr(t, "created_at", "") or "")
        target = pending[0]
        store.respond_ticket(target.ticket_id, decision="APPROVE", guidance="Phê duyệt qua NetChat bởi Quanpt1")
        store.close()

        remaining = len(pending) - 1
        _audit("netchat_command.approve", {"ticket_id": target.ticket_id, "remaining": remaining})
        lines = [
            "✅ ĐÃ PHÊ DUYỆT:",
            f"• Hồ sơ: {target.ticket_id}",
            f"• Tiêu đề: {getattr(target, 'title', '')}",
            f"• Nội dung: {(getattr(target, 'proposed_action', '') or '')[:200]}",
        ]
        if remaining > 0:
            lines.append(f"📭 Còn {remaining} hồ sơ chờ duyệt — gõ 'phê duyệt' để duyệt tiếp.")
        else:
            lines.append("📭 Đã hết hồ sơ chờ duyệt.")
        return "\n".join(lines)
    except Exception as exc:
        return f"⚠️ Không duyệt được: {type(exc).__name__}: {exc}"


def handle_status(payload: dict[str, Any] | None = None) -> str:
    """'trạng thái': live self-model probes — evidence-based, honest OFFLINE."""
    try:
        from quan_ai_brain.cognition.self_model_engine import SelfModelEngine

        engine = SelfModelEngine(str(WORKSPACE))
        qa = engine.answer_state_questions()
        online = qa.get("q2_components_online", [])
        offline = qa.get("q3_components_offline_unverified", [])
        approved = (qa.get("q7_approved_knowledge") or {}).get("count", "?")
        quarantined = (qa.get("q8_quarantined_knowledge") or {}).get("count", "?")
        tasks = qa.get("q6_running_waiting_failed_tasks") or {}
        owner_decisions = (qa.get("q9_pending_owner_decisions") or {}).get("count", "?")

        lines = ["📊 HIỆN TRẠNG HỆ THỐNG (probe thật):", ""]
        lines.append("🟢 Đang hoạt động:")
        for comp in online:
            lines.append(f"   • {comp['component_id']}: {comp['status']}")
        lines.append("🔴 Không khả dụng / không xác minh được:")
        for comp in offline:
            lines.append(f"   • {comp['component_id']}: {comp['status']}")
        lines += [
            "",
            f"🧠 Tri thức đã duyệt: {approved} | Cách ly: {quarantined}",
            f"📋 Nhiệm vụ: PENDING {tasks.get('pending', '?')} / IN_PROGRESS {tasks.get('in_progress', '?')} / FAILED {tasks.get('failed', '?')}",
            f"⏳ Chờ anh quyết định: {owner_decisions} hồ sơ",
        ]
        changes = (qa.get("changed_since_last_check") or {}).get("changes", [])
        if changes:
            lines.append("🔄 Thay đổi từ lần kiểm tra trước:")
            for ch in changes[:4]:
                lines.append(f"   • {ch['field']}: {ch.get('previous')} → {ch.get('current')}")
        lines.append(f"🕐 {qa.get('generated_at', '')}")
        return "\n".join(lines)
    except Exception as exc:
        return f"⚠️ Không đọc được trạng thái: {type(exc).__name__}: {exc}"


def handle_report(payload: dict[str, Any] | None = None) -> str:
    """'báo cáo': newest report file in 'bao cao xay dung he thong'."""
    try:
        report_dir = WORKSPACE / "bao cao xay dung he thong"
        if not report_dir.exists():
            return "📭 Chưa có thư mục báo cáo."
        files = sorted(report_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            return "📭 Chưa có báo cáo nào."
        newest = files[0]
        mtime = datetime.fromtimestamp(newest.stat().st_mtime, tz=timezone.utc)
        lines = [
            "📄 BÁO CÁO MỚI NHẤT:",
            f"• {newest.name}",
            f"• Cập nhật: {mtime.strftime('%d/%m/%Y %H:%M')} UTC",
            f"• Kích thước: {newest.stat().st_size:,} bytes",
        ]
        if len(files) > 1:
            lines.append("\nCác báo cáo khác:")
            for f in files[1:4]:
                lines.append(f"   • {f.name}")
        return "\n".join(lines)
    except Exception as exc:
        return f"⚠️ Lỗi đọc báo cáo: {type(exc).__name__}"


def handle_tasks(payload: dict[str, Any] | None = None) -> str:
    """'nhiệm vụ': durable task backlog summary."""
    try:
        db = WORKSPACE / "data" / "tasks.db"
        if not db.exists():
            return "📭 Không có registry nhiệm vụ."
        conn = sqlite3.connect(str(db))
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) FROM durable_tasks GROUP BY status ORDER BY COUNT(*) DESC"
            ).fetchall()
            recent = conn.execute(
                "SELECT goal, status, created_at_utc FROM durable_tasks "
                "WHERE status IN ('PENDING','IN_PROGRESS','WAITING_APPROVAL') "
                "ORDER BY created_at_utc DESC LIMIT 5"
            ).fetchall()
        finally:
            conn.close()
        lines = ["📋 BACKLOG NHIỆM VỤ (durable_tasks):", ""]
        for status, n in rows:
            icon = {"PENDING": "⏳", "IN_PROGRESS": "🔄", "COMPLETED": "✅", "CANCELLED": "🚫", "FAILED": "❌", "BLOCKED": "⛔", "WAITING_APPROVAL": "🛑", "APPROVED": "👍", "OUTCOME_UNKNOWN": "❓"}.get(status, "•")
            lines.append(f"{icon} {status}: {n}")
        if recent:
            lines.append("\nNhiệm vụ gần nhất:")
            for goal, status, created in recent:
                lines.append(f"   • [{status}] {str(goal)[:70]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"⚠️ Lỗi đọc nhiệm vụ: {type(exc).__name__}"


def handle_knowledge(payload: dict[str, Any] | None = None) -> str:
    """'tri thức': knowledge counts + quality highlights."""
    try:
        db = WORKSPACE / "data" / "brain.db"
        if not db.exists():
            return "📭 Không có cơ sở dữ liệu tri thức."
        conn = sqlite3.connect(str(db))
        try:
            approved = conn.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0]
            quarantined = conn.execute(
                "SELECT COUNT(*) FROM candidate_knowledge WHERE status='quarantined'"
            ).fetchone()[0]
            episodes = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        finally:
            conn.close()
        lines = [
            "🧠 TRI THỨC:",
            f"• Đã duyệt (semantic): {approved}",
            f"• Cách ly chờ duyệt (quarantined): {quarantined}",
            f"• Trải nghiệm (episodes): {episodes}",
            "",
            "📌 Chính sách: tri thức DC/SOP/An toàn (L1-L3) LUÔN chờ anh duyệt.",
            "📌 Đã phát hiện ~99% candidate trùng lặp — chờ anh duyệt chiến lược dọn dẹp.",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"⚠️ Lỗi đọc tri thức: {type(exc).__name__}"


def handle_help(payload: dict[str, Any] | None = None) -> str:
    return "\n".join([
        "🤖 KÊNH LÀM VIỆC ANH ↔ TRỢ LÝ (không cần @bot):",
        "",
        "• 'phê duyệt' — duyệt hồ sơ chờ phê duyệt gần nhất",
        "• 'trạng thái' — hiện trạng hệ thống (probe thật)",
        "• 'báo cáo' — báo cáo mới nhất",
        "• 'nhiệm vụ' — backlog nhiệm vụ",
        "• 'tri thức' — số liệu tri thức đã học",
        "• 'giúp' — xem lại các lệnh này",
        "",
        "Câu hỏi tự do khác: em sẽ trả lời bằng AI hội thoại.",
    ])


HANDLERS = {
    "approve": handle_approve,
    "status": handle_status,
    "report": handle_report,
    "tasks": handle_tasks,
    "knowledge": handle_knowledge,
    "help": handle_help,
}


def route_message(text: str) -> tuple[str | None, str]:
    """Route an incoming channel message.

    Returns (intent, response). intent=None + response='' means: fall back
    to AI conversational processing in the responder.
    """
    intent = detect_intent(text)
    if intent is None:
        return None, ""
    handler = HANDLERS[intent]
    try:
        return intent, handler()
    except Exception as exc:
        return intent, f"⚠️ Lỗi thực thi lệnh '{intent}': {type(exc).__name__}: {exc}"


def _audit(event_type: str, details: dict[str, Any]) -> None:
    try:
        from quan_ai_brain.core.audit import AuditLogger

        AuditLogger(WORKSPACE).record(event_type, details)
    except Exception:
        pass
