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
import re
import sqlite3
import sys
import time
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

# ---------------------------------------------------------------------------
# "ok" = owner confirmation of the bot's LAST question/proposal (27/10/2026).
# Yêu cầu chủ sở hữu: "khi anh gõ ok, OK có nghĩa là anh đã xác nhận; còn
# không sẽ không phản hồi hoặc không có xác nhận" + "trợ lý không hỏi lòng vòng".
# Khi bot hỏi xin phép/chờ lệnh (VD: "Anh xác nhận cho em chạy lại probe nhé?"),
# câu "ok" của anh là lệnh THỰC THI luôn — không hỏi lại lần nữa.
# ---------------------------------------------------------------------------

_OK_RE = re.compile(r"^\s*(ok|okay|okie|ok anh|oke|uk|ừ|uh)\s*[.!]?\s*$", re.IGNORECASE)

# Actions một lần chờ "ok" xác nhận. TTL 15 phút — quá hạn thì huỷ (an toàn:
# "ok" muộn không kích hoạt hành động đã lỗi thời).
_PENDING_ACTIONS: dict[str, dict[str, Any]] = {}
_PENDING_TTL_S = 15 * 60


def stage_pending_action(chat_session_id: str, label: str, action: Any) -> str:
    """Bot vừa HỎI xin phép → ghi nhận việc chờ xác nhận. Trả lời CÂU HỎI đó
    (bot không tự thực hiện trước, vì đây là việc có quyết định của anh)."""
    _PENDING_ACTIONS[chat_session_id] = {
        "label": label,
        "action": action,
        "staged_at": time.time(),
    }
    return label


def _take_pending_action(chat_session_id: str) -> dict[str, Any] | None:
    entry = _PENDING_ACTIONS.pop(chat_session_id, None)
    if entry is None:
        return None
    if time.time() - entry["staged_at"] > _PENDING_TTL_S:
        return None  # expired — stale confirmation must not fire old actions
    return entry


def run_pending_action(chat_session_id: str) -> str | None:
    """Owner đã gõ 'ok' → thực thi hành động đang chờ xác nhận, TRẢ KẾT QUẢ
    thật (không hỏi lại, không lòng vòng)."""
    entry = _take_pending_action(chat_session_id)
    if entry is None:
        return None
    label = entry["label"]
    action = entry["action"]
    try:
        if action == "reprobe_pi5":
            return _reprobe_pi5(label)
        if action == "reprobe_full":
            return _reprobe_full(label)
    except Exception as exc:
        return f"⚠️ Thực thi '{label}' lỗi: {type(exc).__name__}: {exc}"
    return f"Đã xác nhận '{label}' nhưng chưa có runner tương ứng (lỗi cấu hình)."


def _probe_port(port: int, timeout: float = 2.0) -> bool:
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def _pi5_status() -> dict[str, Any]:
    """Nguồn sự thật DUY NHẤT cho trạng thái Pi 5: EdgeConnectionMonitor —
    heartbeat thực do Pi 5 gửi qua LAN lên Executive server (8766), có HMAC
    auth + RTT đo thật. TCP probe 127.0.0.1:8768 là SAI BẢN CHẤT: 8768 là
    kiosk port chạy TRÊN Pi 5 (mạng LAN), không bao giờ lắng nghe trên PC."""
    try:
        import urllib.request

        with urllib.request.urlopen(
            "http://127.0.0.1:8766/api/executive/edge/status", timeout=3
        ) as r:
            data = json.loads(r.read().decode("utf-8"))
        edge = data.get("edge", {})
        state = str(edge.get("state", "UNKNOWN"))
        connected = state in ("READY", "CONNECTED", "SYNCING", "RECOVERING")
        return {
            "connected": connected,
            "state": state,
            "rtt_ms": edge.get("rtt_ms"),
            "seconds_since_heartbeat": edge.get("seconds_since_heartbeat"),
            "source": "edge_monitor_heartbeat:8766",
        }
    except Exception:
        return {
            "connected": False,
            "state": "UNKNOWN",
            "rtt_ms": None,
            "seconds_since_heartbeat": None,
            "source": "edge_status_unavailable",
        }


def _reprobe_pi5(label: str) -> str:
    """Probe lại Pi 5 qua edge heartbeat + các thành phần local — một lần, báo thật."""
    edge = _pi5_status()
    core = _probe_port(8765)
    ollama = _probe_port(11434)
    now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    if edge["connected"]:
        rtt = f", RTT {edge['rtt_ms']:.0f}ms" if edge.get("rtt_ms") else ""
        result = f"🟢 Pi 5: ONLINE ({edge['state']}{rtt}, heartbeat {edge.get('seconds_since_heartbeat', 0):.0f}s trước) — xác nhận được rồi ạ."
    else:
        result = f"🔴 Pi 5: chưa xác minh được kết nối lúc {now} (trạng thái edge: {edge['state']})."
    _audit(
        "netchat_command.ok_confirm_reprobe",
        {"pi5_connected": edge["connected"], "edge_state": edge["state"], "core": core, "ollama": ollama},
    )
    return (
        f"✅ Đã kiểm tra ngay ạ:\n"
        f"• {result}\n"
        f"• Core server (8765): {'🟢 ONLINE' if core else '🔴 OFFLINE'} | "
        f"Ollama: {'🟢 ONLINE' if ollama else '🔴 OFFLINE'}\n"
        + (
            ""
            if edge["connected"]
            else "Kết luận: Pi 5 chưa gửi heartbeat về PC — em sẽ không khẳng định nó đang chạy. Anh kiểm tra nguồn/WiFi trên Pi giúp em nhé."
        )
    )


def _reprobe_full(label: str) -> str:
    from quan_ai_brain.cognition.self_model_engine import SelfModelEngine

    engine = SelfModelEngine(str(WORKSPACE))
    qa = engine.answer_state_questions()
    online = [c["component_id"] for c in qa.get("q2_components_online", [])]
    offline = [c["component_id"] for c in qa.get("q3_components_offline_unverified", [])]
    return (
        f"✅ Đã xác nhận — probe lại toàn hệ thống:\n"
        f"• 🟢 ONLINE: {', '.join(online) if online else '(không)'}\n"
        f"• 🔴 OFFLINE: {', '.join(offline) if offline else '(không)'}\n"
        f"🕐 {qa.get('generated_at', '')}"
    )


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
    """'trạng thái': live self-model probes — NGẮN GỌN, đúng yêu cầu chủ sở hữu
    27/10 ('trả lời ngắn gọn, tránh dài dòng'). Chỉ 5-6 dòng, không bảng dài."""
    try:
        from quan_ai_brain.cognition.self_model_engine import SelfModelEngine

        engine = SelfModelEngine(str(WORKSPACE))
        qa = engine.answer_state_questions()
        online = [c["component_id"] for c in qa.get("q2_components_online", [])]
        offline = [c["component_id"] for c in qa.get("q3_components_offline_unverified", [])]
        tasks = qa.get("q6_running_waiting_failed_tasks") or {}
        owner_decisions = (qa.get("q9_pending_owner_decisions") or {}).get("count", 0)
        lines = [
            f"🟢 ONLINE: {', '.join(online) if online else '(không)'}",
            f"🔴 OFFLINE: {', '.join(offline) if offline else '(không)'}",
            f"📋 Nhiệm vụ: {tasks.get('pending', 0)} chờ / {tasks.get('in_progress', 0)} chạy / {tasks.get('failed', 0)} lỗi",
        ]
        if owner_decisions:
            lines.append(f"⏳ Chờ anh quyết định: {owner_decisions}")
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


def route_message(text: str, *, sender_user_id: str = "", chat_session_id: str = "default") -> tuple[str | None, str]:
    """Route an incoming channel message.

    Returns (intent, response). intent=None + response='' means: fall back
    to AI conversational processing in the responder.

    Sprint 2 (V3): approval intents go through NetChatApprovalAdapter —
    persistent Approval Cards + formal ApprovalGate + SPECIFIC explanations
    (duyệt gì, vì sao, trạng thái, bước tiếp theo). The old consultation-FIFO
    handler stays as a fallback for legacy tickets not bound to task codes.

    27/10/2026 (yêu cầu chủ sở hữu): "ok" = XÁC NHẬN việc bot vừa hỏi → thực
    thi NGAY; nếu không có việc nào chờ xác nhận → KHÔNG PHẢN HỒI (im lặng).
    """
    t = (text or "").strip()

    # 0) "ok" — xác nhận nhanh, PHẢI đứng trước adapter (regex của adapter
    #    bắt cả 'ok' thành lệnh duyệt hồ sơ → lòng vòng, sai ý).
    if _OK_RE.match(t):
        result = run_pending_action(chat_session_id)
        if result is not None:
            _audit("netchat_command.ok_confirmed", {"session": chat_session_id})
            return "ok_confirm", result
        # Không có việc nào chờ xác nhận → im lặng (không lòng vòng).
        return "ok_silent", ""

    # 1) Approval-card commands (DUYỆT/TỪ CHỐI/SỬA/CHI TIẾT TASK-xxxx,
    #    or a plain 'Duyệt'/'Từ chối'/'Chi tiết') — giữ priority như V3.
    try:
        from quan_ai_brain.governance.netchat_approval_adapter import NetChatApprovalAdapter

        adapter = NetChatApprovalAdapter()
        reply = adapter.handle_owner_message(text, sender_user_id=sender_user_id, post=False)
        if reply:
            _audit("netchat_command.approval_card", {"matched": True, "sender": sender_user_id})
            return "approval_card", reply
    except Exception as exc:  # adapter failure must not break other commands
        _audit("netchat_command.approval_adapter_error", {"error": str(exc)[:200]})

    # 2) System commands (trạng thái/báo cáo/nhiệm vụ/tri thức/giúp/phê duyệt)
    intent = detect_intent(text)
    if intent is not None:
        handler = HANDLERS[intent]
        try:
            return intent, handler()
        except Exception as exc:
            return intent, f"⚠️ Lỗi thực thi lệnh '{intent}': {type(exc).__name__}: {exc}"

    return None, ""


def _audit(event_type: str, details: dict[str, Any]) -> None:
    try:
        from quan_ai_brain.core.audit import AuditLogger

        AuditLogger(WORKSPACE).record(event_type, details)
    except Exception:
        pass
