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




from pathlib import Path
import re

# (12/11/2026) Loader secret tập trung
import sys as _sys
_SECRET_DIR = Path('E:/BRAIN/user, pass, token')
if str(_SECRET_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SECRET_DIR))
from loader import get_secret as _get_secret
WORKSPACE = Path(__file__).resolve().parent.parent

_PID_RE = r"(?:pid\s*)?(?P<pid>\d{1,7})"

_SEC_STATUS_RE = re.compile(r"^\s*(?:an\s*ninh|an ninh he thong|trang thai an ninh|giam sat ai|bao ve he thong)\s*[!.?]?\s*$", re.IGNORECASE)
_FED_STATUS_RE = re.compile(r"^\s*(?:liên bang|lien bang|federation|các nút|cac nut)\s*[!.?]?\s*$", re.IGNORECASE)
_SCAN_RE = re.compile(r"^\s*(?:quét mạng|quet mang|scan lan|quét lan|quet lan)\s*[!.]?\s*$", re.IGNORECASE)
_HOLD_RE = re.compile(rf"^\s*(?:giữ|giu|suspend|hold)\s+{_PID_RE}\s*[!.]?\s*$", re.IGNORECASE)
_RELEASE_RE = re.compile(rf"^\s*(?:thả|tha|resume|release|cho chay lại|cho chay lai)\s+{_PID_RE}\s*[!.]?\s*$", re.IGNORECASE)
_KILL_RE = re.compile(rf"^\s*(?:hạ|ha|kill|hạ gục|ha guc|dit)\s+{_PID_RE}\s*[!.]?\s*$", re.IGNORECASE)
_REG_NODE_RE = re.compile(
    r"^\s*(?:đăng ký|dang ky)\s+nút\s+(edge|pc)\s+(?P<host>\d{1,3}(?:\.\d{1,3}){3})"
    r"(?:\s+(?P<label>.+))?\s*$", re.IGNORECASE)
_REG_CONN_RE = re.compile(
    r"^\s*(?:đăng ký|dang ky)\s+đầu nối\s+(?P<domain>[a-z0-9.-]+\.[a-z]{2,})"
    r"(?:.*?hạn ngạch\s*:?\s*(?P<cap>\d+))?\s*$", re.IGNORECASE)
_SENTINEL_RE = re.compile(r"^\s*sentinel\s*[!.]?\s*$", re.IGNORECASE)
_SENTINEL_AGENT_RE = re.compile(
    r"^\s*sentinel\s+agent\s+(?P<q>.+?)\s*[!.]?\s*$", re.IGNORECASE)
_SENTINEL_LEVEL_RE = re.compile(
    r"^\s*sentinel\s+mức\s+(?P<lv>L[0-4])\s*$", re.IGNORECASE)


def _dm_send(text: str) -> None:
    """DM alert cho owner qua bridge chuẩn (fire-and-forget, fail-honest)."""
    try:
        from quan_ai_brain.integration.netchat_bridge import send_message
        send_message(_get_secret("netchat_channel_owner", "mwp3nk3ciprjjr4hdmcoqgk6jr"), text)  # (12/11) đọc từ loader
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

    if _FED_STATUS_RE.match(t):
        return "lien_bang", handle_federation_status()

    if _SCAN_RE.match(t):
        return "quet_mang", handle_lan_scan()

    m = _REG_NODE_RE.match(t)
    if m:
        return "dang_ky_nut", _register_edge_node(m.group("host"), m.group("label") or "")

    m = _REG_CONN_RE.match(t)
    if m:
        cap = int(m.group("cap")) if m.group("cap") else 100
        return "dang_ky_dau_noi", _register_connector(m.group("domain"), cap)

    if _SENTINEL_RE.match(t):
        return "sentinel", handle_sentinel_dashboard()

    m = _SENTINEL_AGENT_RE.match(t)
    if m:
        return "sentinel_agent", handle_sentinel_agent(m.group("q"))

    m = _SENTINEL_LEVEL_RE.match(t)
    if m:
        return "sentinel_level", handle_sentinel_level(m.group("lv"))

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


def _register_edge_node(host: str, label: str) -> str:
    from quan_ai_brain.federation.node_registry import NodeRegistry

    registry = NodeRegistry(WORKSPACE / "data" / "federation_nodes.db")
    node = registry.register("EDGE", host, label=label or f"Edge node {host}",
                             capabilities=["kiosk", "audio", "camera", "sensor"])
    probe = registry.probe_node(node.node_id)
    status = probe.get("status", "UNKNOWN")
    emoji = "🟢" if status == "REACHABLE" else "🔴"
    return (
        f"{emoji} Đã đăng ký nút **{node.node_id}** → {host} : **{status}**\n"
        f"• Watchdog sẽ probe mỗi chu kỳ — mất kết nối em báo anh ngay\n"
        f"• Khi SSH mở (anh chạy script pi5_deploy/tony_pi5_all_in_one.sh trên Pi), "
        f"nút này trở thành tay chân của em: kiosk + loa + camera + cảm biến"
    )


def _register_connector(domain: str, cap: int) -> str:
    from quan_ai_brain.federation.cloud_connector import CloudConnectorManager
    from quan_ai_brain.federation.node_registry import NodeRegistry

    mgr = CloudConnectorManager(NodeRegistry(WORKSPACE / "data" / "federation_nodes.db"))
    try:
        node = mgr.register_connector(domain, daily_cap=cap)
    except ValueError as exc:
        return f"🤔 {exc}"
    return (
        f"🔗 Đã đăng ký **đầu nối cloud** `{domain}` — hạn ngạch **{cap} lượt/ngày**\n"
        f"• Vượt hạn ngạch: em CHẶN tự động (fail-closed) và báo anh\n"
        f"• Mọi lượt gọi ghi audit — anh kiểm tra bất cứ lúc nào"
    )


# ---------------------------------------------------------------------------
# SEC-S2: Liên bang — trạng thái nút + quét LAN
# ---------------------------------------------------------------------------
def handle_federation_status() -> str:
    from quan_ai_brain.federation.node_registry import NodeRegistry

    registry = NodeRegistry(WORKSPACE / "data" / "federation_nodes.db")
    nodes = registry.list_nodes()
    lines = ["🌐 **LIÊN BANG TONY** — lõi điều khiển: PC này (E:\\BRAIN)",
             f"• Số nút đã đăng ký: **{len(nodes)}**"]
    for n in nodes:
        cap = f" | hạn ngạch: {n.calls_today}/{n.daily_cap} hôm nay" if n.kind == "CONNECTOR" else ""
        lines.append(
            f"   — [{n.kind}] {n.node_id} → {n.host} : **{n.status}**{cap}")
    if not nodes:
        lines.append("• (chưa đăng ký nút nào — Pi5/cổng GSM/connector cloud sẽ hiện ở đây)")
    lines.append("\nLệnh: `quét mạng` (tìm thiết bị LAN) · đăng ký nút: nhắn "
                 "'đăng ký nút edge <IP> [tên]'" )
    return "\n".join(lines)


def handle_lan_scan() -> str:
    from quan_ai_brain.federation.lan_scanner import LanScanner
    from quan_ai_brain.federation.node_registry import NodeRegistry

    registry = NodeRegistry(WORKSPACE / "data" / "federation_nodes.db")
    reg_hosts = {n.host: n.node_id for n in registry.list_nodes() if n.kind in ("PC", "EDGE")}
    scanner = LanScanner()
    summary = scanner.scan_summary(registered_hosts=reg_hosts)
    lines = [
        f"📡 **QUÉT MẠNG** {summary['subnet']} (lúc {summary['scanned_at'][11:19]} UTC)",
        f"• Thiết bị phản hồi: **{summary['total_alive']}**",
    ]
    for d in summary["devices"][:12]:
        mark = "🟢 NÚT MÌNH" if d["is_registered_node"] else ("🍓 Pi5?" if d["vendor_hint"] else "•")
        name = d["hostname"] or "?"
        lines.append(f"   {mark} {d['ip']:15s} MAC={d['mac'] or '??':18s} {name}")
    if summary["total_alive"] > 12:
        lines.append(f"   ... và {summary['total_alive'] - 12} thiết bị khác")
    raspi = summary["raspberry_pi_candidates"]
    if raspi:
        lines.append(f"🍓 Ứng viên Raspberry Pi: {', '.join(d['ip'] for d in raspi)} "
                     f"— nhắn 'đăng ký nút edge <IP> pi5' để đưa vào liên bang")
    unreg = [d for d in summary["devices"] if not d["is_registered_node"]]
    lines.append(f"• Chưa đăng ký: **{len(unreg)}** — anh có thể 'đăng ký nút edge <IP>' "
                 "để em giám sát thường xuyên")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Chu kỳ watchdog: quét + auto-contain + DM alert (1 tin/cycle có vi phạm mới)
# ---------------------------------------------------------------------------
def security_watchdog_cycle() -> int:
    """Trả số vi phạm MỚI phát hiện trong cycle này. Không raise ra ngoài.

    SENTINEL-S3: mọi vi phạm đo được đều cập nhật hồ sơ danh tính agent
    (apply_violation) — trust giảm, risk tăng, phân loại tự động theo quy tắc
    deterministic (UNKNOWN→UNAUTHORIZED, TRUSTED→SUSPICIOUS).
    """
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

    # SENTINEL: cập nhật hồ sơ danh tính theo vi phạm đo được (deterministic)
    try:
        registry = _agents_registry()
    except Exception:
        registry = None
    for v in violations:
        if registry is None:
            break
        try:
            pname = str(v.get("process_name", "")) or "unknown"
            aid = f"proc_{v.get('pid', 0)}"
            if registry.get(aid) is None:
                registered = v.get("violation") != "UNREGISTERED"
                registry.observe(aid, pname, "PROCESS", registered=registered)
            registry.apply_violation(
                aid, str(v.get("violation", "?")),
                evidence_ref=f"security_events:pid={v.get('pid')}")
        except Exception:
            continue  # hồ sơ lỗi không được giết chu kỳ an ninh

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


# ---------------------------------------------------------------------------
# SEC-S2: chu kỳ liên bang — probe nút đã đăng ký, cảnh báo mất kết nối
# (cooldown 1 lần/giờ/nút qua marker file — chống spam khi nút offline lâu)
# ---------------------------------------------------------------------------
_FED_ALERT_MARKER = WORKSPACE / "data" / "fed_alert_last.json"


def federation_watchdog_cycle() -> int:
    """Trả số nút CHUYỂN sang UNREACHABLE trong cycle này. Đã DM cảnh báo."""
    from quan_ai_brain.federation.node_registry import NodeRegistry

    registry = NodeRegistry(WORKSPACE / "data" / "federation_nodes.db")
    nodes = registry.list_nodes()
    if not nodes:
        return 0
    import json as _json
    import time as _time

    last_alerts: dict[str, float] = {}
    try:
        last_alerts = _json.loads(_FED_ALERT_MARKER.read_text(encoding="utf-8"))
    except Exception:
        last_alerts = {}
    now_ts = _time.time()
    changed: list[str] = []
    for n in nodes:
        if n.kind == "CONNECTOR":
            continue
        result = registry.probe_node(n.node_id)
        if result.get("changed") and result.get("status") == "UNREACHABLE":
            if now_ts - last_alerts.get(n.node_id, 0) > 3600:  # 1 lần/giờ/nút
                last_alerts[n.node_id] = now_ts
                # (07/11/2026, owner) Rút gọn nội dung: '🔴 PC (192.168.1.9)
                # MẤT KẾT NỐI' — label DB dài ('PC lõi QUANPT (này)') và host
                # stale (192.168.1.9 cũ) không sửa trong tin; dùng KIND viết
                # hoa làm tên gọn + host thật từ registry.
                _kind_vn = {"PC": "PC", "EDGE": "Pi5", "CONNECTOR": "Cổng"}.get(
                    str(n.kind), str(n.kind))
                changed.append(f"🔴 {_kind_vn} ({n.host}) MẤT KẾT NỐI")
    try:
        _FED_ALERT_MARKER.write_text(
            _json.dumps(last_alerts, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    if changed:
        # (07/11/2026, owner) Bỏ header '🌐 LIÊN BANG — nút mất kết nối' —
        # tin đủ nghĩa khi gọn: mỗi nút 1 dòng '🔴 <tên> (<IP>) MẤT KẾT NỐI'.
        _dm_send("\n".join(changed[:5]))
    return len(changed)


# ---------------------------------------------------------------------------
# SENTINEL-S3: dashboard NOC + hồ sơ agent + threat level (governance 3 cấp)
# ---------------------------------------------------------------------------
_SENTINEL_AGENTS_DB = WORKSPACE / "data" / "sentinel_agents.db"
_SENTINEL_LEVELS_DB = WORKSPACE / "data" / "sentinel_threat_levels.db"


def _agents_registry():
    """Registry tính path theo WORKSPACE ĐỘNG (test monkeypatch được, không cứng)."""
    from quan_ai_brain.security.agent_identity import AgentIdentityRegistry

    return AgentIdentityRegistry(WORKSPACE / "data" / "sentinel_agents.db")


def _levels_machine():
    from quan_ai_brain.security.threat_levels import ThreatLevelMachine


    return ThreatLevelMachine(WORKSPACE / "data" / "sentinel_threat_levels.db")


def handle_sentinel_dashboard() -> str:

    registry = _agents_registry()
    counts = registry.counts()
    level = _levels_machine().current_level()
    lines = [
        f"🛡️ **SENTINEL — NOC DASHBOARD** | Threat Level: **{level}**",
        f"• Agent đang quản lý: **{sum(counts.values())}** — "
        f"TRUSTED {counts.get('TRUSTED', 0)} · UNKNOWN {counts.get('UNKNOWN', 0)} · "
        f"SUSPICIOUS {counts.get('SUSPICIOUS', 0)} · COMPROMISED {counts.get('COMPROMISED', 0)} · "
        f"MALICIOUS {counts.get('MALICIOUS', 0)} · UNAUTHORIZED {counts.get('UNAUTHORIZED', 0)}",
    ]
    risky = [i for i in registry.list_identities()
             if i.classification not in ("TRUSTED", "UNKNOWN")]
    if risky:
        lines.append("• Đối tượng chú ý:")
        for i in risky[:6]:
            lines.append(
                f"   — [{i.classification}] {i.name} (trust {i.trust_score}/risk {i.risk_score})"
                f" — {i.security_status}")
    lines.append(
        "\nLệnh: `sentinel agent <tên|pid>` — hồ sơ 1 đối tượng · "
        "`sentinel mức L0..L4` — chuyển cấp (có kiểm soát)")
    return "\n".join(lines)


def handle_sentinel_agent(query: str) -> str:
    registry = _agents_registry()
    idents = registry.find_by_name(query)
    if not idents and query.isdigit():
        found = registry.get(f"proc_{query}")
        idents = [found] if found else []
    if not idents:
        return (f"🛡️ Không có hồ sơ nào khớp '{query}' trong sổ cái SENTINEL.\n"
                "• Agent mới sẽ tự xuất hiện khi watchdog quét thấy (observe).")
    out = []
    for i in idents[:3]:
        out.append(
            f"🛡️ **HỒ SƠ {i.name}** [{i.kind}] — phân loại: **{i.classification}**\n"
            f"• Trust {i.trust_score}/100 · Risk {i.risk_score}/100 · trạng thái: {i.security_status}\n"
            f"• Quyền: {', '.join(i.permission_scope) or '(chưa khai)'}\n"
            f"• Evidence: {i.evidence_count} · gặp gần nhất: {i.last_seen_at[:19]}\n"
            f"• Khuyến nghị: {i.recommended_response}")
    return "\n\n".join(out)


def handle_sentinel_level(level: str) -> str:
    tlm = _levels_machine()
    current = tlm.current_level()
    target = level.upper()
    if target == current:
        return f"🛡️ Hệ thống đang ở **{current}** — không cần chuyển."
    # DM từ owner = quyền CẤP 3; SENTINEL tự chạy by='sentinel' sẽ bị gate
    result = tlm.set_level(target, reason=f"Owner ra lệnh qua DM ({target})",
                           by="owner", evidence_ref="owner_dm_directive")
    return (f"🛡️ Đã chuyển Threat Level: **{result['from']} → {result['to']}**\n"
            f"• Lý do: {result['reason']} (audit đầy đủ trong history)")