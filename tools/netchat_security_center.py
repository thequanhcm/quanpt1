"""SEC-S1 (d): Trung tâm lệnh An ninh qua DM — wire vào netchat_command_center + watchdog.

Lệnh owner (tiếng Việt, không dấu vẫn khớp):
- "an ninh"                      → trạng thái: hợp đồng ACTIVE + vi phạm gần đây
- "giữ <pid>" / "giữ pid 1234"   → TẠM GIỮ (suspend, giữ dữ liệu, thả được)
- "thả <pid>"                    → cho tiến trình bị treo chạy lại
- "hạ <pid>"                     → HẠ GỤC vĩnh viễn (taskkill /F)
- "giao nhiệm vụ cho <tên>: <mục tiêu> | phạm vi: <paths> | miền: <domains> |
   hạn: <N> phút | tự giữ"       → tạo hợp đồng nhiệm vụ (fail-honest)

An toàn: mọi giữ/thả/hạ đi qua actions.protected_reason() — whitelist cứng
hệ thống + TONY/netMind refuse fail-closed. Watchdog gọi security_watchdog_cycle()
mỗi chu kỳ; DM alert qua bridge chuẩn (ID DM bot_tony ↔ quanpt1).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent

_PID_RE = r"(?:pid\s*)?(?P<pid>\d{1,7})"

_SEC_STATUS_RE = re.compile(r"^\s*(?:an\s*ninh|an ninh he thong|trang thai an ninh|giam sat ai|bao ve he thong)\s*[!.?]?\s*$", re.IGNORECASE)
_HOLD_RE = re.compile(rf"^\s*(?:giữ|giu|suspend|hold)\s+{_PID_RE}\s*[!.]?\s*$", re.IGNORECASE)
_RELEASE_RE = re.compile(rf"^\s*(?:thả|tha|resume|release|cho chay lại|cho chay lai)\s+{_PID_RE}\s*[!.]?\s*$", re.IGNORECASE)
_KILL_RE = re.compile(rf"^\s*(?:hạ|ha|kill|hạ gục|ha guc|dit)\s+{_PID_RE}\s*[!.]?\s*$", re.IGNORECASE)


def _dm_send(text: str) -> None:
    """DM alert cho owner qua bridge chuẩn (fire-and-forget, fail-honest)."""
    try:
        from quan_ai_brain.integration.netchat_bridge import send_message
        send_message("mwp3nk3ciprjjr4hdmcoqgk6jr", text)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Handlers cho route_message
# ---------------------------------------------------------------------------
def route_security_command(text: str) -> tuple[str, str] | None:
    """Khớp lệnh an ninh. Trả (intent, response) hoặc None để đi tiếp luồng khác."""
    t = (text or "").strip()

    if _SEC_STATUS_RE.match(t):
        return "an_ninh", handle_security_status()

    m = _HOLD_RE.match(t)
    if m:
        return "sec_hold", _do_action("suspend", int(m.group("pid")))

    m = _RELEASE_RE.match(t)
    if m:
        return "sec_release", _do_action("resume", int(m.group("pid")))

    m = _KILL_RE.match(t)
    if m:
        return "sec_kill", _do_action("kill", int(m.group("pid")))

    # "giao nhiệm vụ cho ..." — delegate sang parser của task_contracts
    if re.match(r"^\s*giao\s+nhiệm\s+vụ\s+cho\b", t, re.IGNORECASE):
        return "sec_contract", _create_contract_from_dm(t)

    return None


def handle_security_status() -> str:
    from quan_ai_brain.security.task_contracts import TaskContractStore
    from quan_ai_brain.security.watcher import SecurityEventStore

    contracts = TaskContractStore(WORKSPACE / "data" / "security_contracts.db")
    events = SecurityEventStore(WORKSPACE / "data" / "security_events.db")

    active = contracts.active_contracts()
    pending = events.recent(limit=10, unhandled_only=True)
    lines = ["🛡️ **AN NINH HỆ THỐNG**",
             f"• Hợp đồng nhiệm vụ ACTIVE: **{len(active)}**"]
    for c in active[:5]:
        expired_note = " (QUÁ HẠN)" if c.is_expired() else ""
        lines.append(
            f"   — `{c.contract_id[-8:]}` {c.subject}: {c.goal[:60]} | "
            f"hạn: {c.expires_at or 'không'}{expired_note} | tự giữ: {'có' if c.auto_contain else 'không'}")
    lines.append(f"• Vi phạm CHƯA xử lý: **{len(pending)}**")
    for e in pending[:5]:
        lines.append(f"   — [{e['violation']}] PID {e['pid']} ({e['process_name']}): "
                     f"{(e['cmdline'] or '')[:70]}")
    if not active and not pending:
        lines.append("• (chưa có hợp đồng nào được đăng ký — nhắn "
                     "'giao nhiệm vụ cho <tên AI>: <mục tiêu>...' để bắt đầu giám sát)")
    lines.append("\nLệnh: `giữ <pid>` · `thả <pid>` · `hạ <pid>` · "
                 "`giao nhiệm vụ cho <tên AI>: <mục tiêu> | phạm vi: ... | hạn: N phút`")
    return "\n".join(lines)


def _do_action(action: str, pid: int) -> str:
    from quan_ai_brain.security.actions import kill_process, resume_process, suspend_process
    from quan_ai_brain.security.watcher import SecurityEventStore

    fn = {"suspend": suspend_process, "resume": resume_process, "kill": kill_process}[action]
    result = fn(pid)
    if result.get("success"):
        # audit hành động tay của owner
        try:
            store = SecurityEventStore(WORKSPACE / "data" / "security_events.db")
            store.record(
                violation="OWNER_ACTION", pid=pid,
                process_name=str(result.get("name", "?")), cmdline="",
                evidence={"action": action, "by": "owner_dm"},
                handled="HANDLED", action_taken=action)
        except Exception:
            pass
        return f"✅ PID {pid}: {result.get('reason', 'ok')}"
    return (f"⛔ PID {pid}: từ chối — {result.get('reason', 'lỗi không rõ')}\n"
            f"(whitelist cứng bảo vệ hệ thống + chính TONY)") \
        if "whitelist" in str(result.get("reason", "")) or "hệ thống" in str(result.get("reason", "")) \
        else f"⚠️ PID {pid}: {result.get('reason', 'thất bại')}"


def _create_contract_from_dm(text: str) -> str:
    from quan_ai_brain.security.task_contracts import TaskContractStore, parse_dm_contract
    try:
        spec = parse_dm_contract(text)
        store = TaskContractStore(WORKSPACE / "data" / "security_contracts.db")
        c = store.create_contract(**spec)
        scope = ", ".join(c.allowed_paths) or "toàn bộ (không giới hạn đường dẫn)"
        domains = ", ".join(c.allowed_domains) or "không giới hạn miền"
        return (
            f"🛡️ Đã lập **hợp đồng nhiệm vụ** `{c.contract_id[-8:]}` cho **{c.subject}**\n"
            f"• Nhiệm vụ: {c.goal}\n"
            f"• Phạm vi đường dẫn: {scope}\n"
            f"• Miền được gọi: {domains}\n"
            f"• Hạn: {c.expires_at or 'không (dài hạn)'} · Tự giữ khi vi phạm: "
            f"{'CÓ — em tạm giữ ngay rồi báo anh' if c.auto_contain else 'không (em chỉ cảnh báo)'}\n"
            f"Vệ sĩ bắt đầu giám sát tiến trình '{c.subject}' từ chu kỳ quét tới."
        )
    except ValueError as exc:
        return f"🤔 {exc}"


# ---------------------------------------------------------------------------
# Chu kỳ watchdog: quét + auto-contain + DM alert (1 tin/cycle có vi phạm mới)
# ---------------------------------------------------------------------------
def security_watchdog_cycle() -> int:
    """Trả số vi phạm MỚI phát hiện trong cycle này. Không raise ra ngoài."""
    from quan_ai_brain.security.actions import suspend_process
    from quan_ai_brain.security.task_contracts import TaskContractStore
    from quan_ai_brain.security.watcher import SecurityEventStore, SecurityWatcher

    contracts = TaskContractStore(WORKSPACE / "data" / "security_contracts.db")
    if not contracts.subject_family_keywords():
        return 0  # chưa đăng ký hợp đồng nào → không tốn tài nguyên

    watcher = SecurityWatcher(contracts, SecurityEventStore(WORKSPACE / "data" / "security_events.db"))
    violations = watcher.detect_violations(deep=True)
    if not violations:
        return 0

    auto_contained: list[str] = []
    pending_names = []
    for v in violations:
        # auto-contain: hợp đồng ACTIVE có auto_contain=True → TẠM GIỮ ngay
        contract = contracts.match_process(str(v.get("evidence", {}).get("cmdline", "")))
        if contract is None:
            contract = next((c for c in contracts.active_contracts()
                             if c.subject.lower() in v.get("process_name", "").lower()), None)
        if contract is not None and contract.auto_contain:
            r = suspend_process(v["pid"])
            if r.get("success"):
                auto_contained.append(f"PID {v['pid']} ({v['process_name']})")
                watcher.events.mark_handled_by_pid(v["pid"], f"auto_suspend:{contract.contract_id[-8:]}")
            else:
                pending_names.append(f"PID {v['pid']} — giữ THẤT BẠI: {r.get('reason', '?')}")
        else:
            pending_names.append(f"PID {v['pid']} ({v['process_name']}) — {v['violation']}")

    # 1 tin DM tổng hợp cho cycle (anti-spam: mỗi cycle tối đa 1 tin)
    msg = ["🚨 **CẢNH BÁO AN NINH** — phát hiện hành vi vượt thẩm quyền:"]
    if auto_contained:
        msg.append(f"⛔ ĐÃ TẠM GIỮ tự động: {', '.join(auto_contained)}")
    for line in pending_names[:6]:
        msg.append(f"• {line}")
    if pending_names:
        msg.append("→ Anh nhắn `an ninh` để xem bằng chứng, `giữ <pid>`/`thả <pid>`/`hạ <pid>` để xử lý.")
    _dm_send("\n".join(msg))
    return len(violations)
