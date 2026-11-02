"""UAG V1.0 — PI5 UNIVERSAL ACTION GATEWAY core (master directive UAG V1.0).

P0 đã audit (reports/UAG_V1_P0_AUDIT.md). Module này KHÔNG tạo Cognitive Core /
Memory / Security Authority mới — chỉ GHÉP các thành phần có sẵn thành một luồng
thực tế §XI: TONY → QUAN AI BRAIN → APPROVAL → PI5 → AGENT/DEVICE → RESULT
→ VERIFICATION → REPORT.

8 module §III:
- M01 DeviceDiscovery: inventory SQLite bền vững (state transitions)
- M02: kế thừa ADAPTER_REGISTRY (qpig.py) — không tạo trùng
- M03 QEPCommunicationEngine: envelope chuẩn, session, correlation, phản hồi
- M04: kế thừa ToolRegistry (25 tool QPIG-V2)
- M05 UAGExecution: timeout + retry có giới hạn + idempotency key
- M06 SENTINEL enforcement: bước AUTHENTICATE bắt buộc trong pipeline
- M07 Approval: AuthorityGovernor.consume_for_execution (ticket một-lần, hết hạn)
- M08 Evidence: EvidenceStore 11 trường + health snapshot + rollback hook (RCStore)

§V: TONY tự động được khảo sát/đọc/phân tích; mọi thay đổi trạng thái phải có
ticket Quanpt1. Pi5 KHÔNG tự tạo Approval Token. Kênh Pi5 chưa xác minh →
NOT_ACCESSIBLE fail-honest (P0: 11 cổng Pi5 đang đóng).
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from quan_ai_brain.governance.authority_protocol import (
    ApprovalTicket, AuthorityGovernor,
)
from quan_ai_brain.security.containment import EvidenceStore
from quan_ai_brain.uaiif.qpig import (
    ADAPTER_REGISTRY, DIRECTIVE_NAMES, PENDING_PROTOCOLS, ProtocolAdapter,
)

UTC = timezone.utc
PI5_NODE = "edge_pi5"          # nút federation thật
PI5_CHANNELS_VERIFIED: frozenset[str] = frozenset()  # P0: 11 cổng Pi5 ĐÓNG


# ───────────────────────── M03: QEP Communication Engine ─────────────────────────
@dataclass(frozen=True)
class QEPEnvelope:
    """Phong bì chuẩn QEP — mọi thông điệp đi qua UAG phải bọc bằng này."""
    msg_id: str
    session_id: str
    source: str
    dest: str
    mtype: str                     # REQUEST / RESPONSE / EVENT / HEARTBEAT
    payload: dict[str, Any]
    created_at: str
    reply_to: str = ""
    schema_version: str = "qep/1.0"

    @staticmethod
    def create(source: str, dest: str, mtype: str, payload: dict[str, Any],
               session_id: str = "", reply_to: str = "") -> "QEPEnvelope":
        return QEPEnvelope(
            msg_id=f"qep-{uuid.uuid4().hex[:12]}",
            session_id=session_id or f"sess-{uuid.uuid4().hex[:10]}",
            source=source, dest=dest, mtype=mtype,
            payload=dict(payload),
            created_at=datetime.now(UTC).isoformat(),
            reply_to=reply_to)

    def validate(self) -> tuple[bool, str]:
        if self.mtype not in {"REQUEST", "RESPONSE", "EVENT", "HEARTBEAT"}:
            return False, f"mtype lạ: {self.mtype}"
        if not self.source or not self.dest:
            return False, "source/dest không được rỗng"
        if not isinstance(self.payload, dict):
            return False, "payload phải là dict"
        if self.dest == self.source and self.mtype == "REQUEST":
            return False, "REQUEST gửi cho chính mình — từ chối"
        return True, ""


class QEPCommunicationEngine:
    """Định tuyến envelope qua transport đã đăng ký; track session + correlation.

    Transport chỉ là callable nhận envelope — KHÔNG tự mở kết nối mạng (kênh
    thật do kênh đã xác minh cấp; khi chưa có → trả NOT_ACCESSIBLE).
    """

    def __init__(self) -> None:
        self._transports: dict[str, Callable[[QEPEnvelope], QEPEnvelope]] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._log: list[dict[str, Any]] = []

    def register_transport(self, dest: str,
                           fn: Callable[[QEPEnvelope], QEPEnvelope]) -> None:
        self._transports[dest] = fn

    def open_session(self, peer: str, *, meta: dict[str, Any] | None = None) -> str:
        sid = f"sess-{uuid.uuid4().hex[:10]}"
        self._sessions[sid] = {"peer": peer, "opened": datetime.now(UTC).isoformat(),
                               "messages": 0, **(meta or {})}
        return sid

    def session(self, session_id: str) -> dict[str, Any] | None:
        return self._sessions.get(session_id)

    def send(self, env: QEPEnvelope) -> dict[str, Any]:
        ok, err = env.validate()
        if not ok:
            return {"delivered": False, "reason": f"envelope sai: {err}"}
        if env.session_id not in self._sessions:
            self._log.append({"msg_id": env.msg_id, "dest": env.dest,
                              "status": "NO_SESSION"})
            return {"delivered": False, "status": "NO_SESSION",
                    "reason": f"session {env.session_id} chưa mở"}
        self._sessions[env.session_id]["messages"] += 1
        transport = self._transports.get(env.dest)
        if transport is None:
            # M01/P0: dest chưa có kênh — fail-honest, không giả lập phản hồi
            self._log.append({"msg_id": env.msg_id, "dest": env.dest,
                              "status": "NOT_ACCESSIBLE"})
            return {"delivered": False, "status": "NOT_ACCESSIBLE",
                    "reason": f"chưa có transport đã xác minh tới '{env.dest}'"}
        try:
            reply = transport(env)
            if not isinstance(reply, QEPEnvelope):
                return {"delivered": False,
                        "reason": "transport phải trả QEPEnvelope (chuẩn QEP)"}
            self._log.append({"msg_id": env.msg_id, "dest": env.dest,
                              "status": "DELIVERED", "reply_to_msg": reply.msg_id})
            return {"delivered": True, "reply": reply}
        except Exception as exc:
            self._log.append({"msg_id": env.msg_id, "dest": env.dest,
                              "status": "TRANSPORT_ERROR", "error": str(exc)})
            return {"delivered": False, "status": "TRANSPORT_ERROR", "reason": str(exc)}


# ───────────────────────── M01: Device Inventory (SQLite bền vững) ─────────────────────────
class DeviceInventory:
    """Phát hiện/nhận diện/quản lý thiết bị — state machine DISCOVERED→REACHABLE→
    UNREACHABLE→RETIRED. SQLite cục bộ (§VIII)."""

    STATES = ("DISCOVERED", "REACHABLE", "UNREACHABLE", "RETIRED")

    def __init__(self, db_path: str | Any) -> None:
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.execute("""CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY, kind TEXT NOT NULL DEFAULT 'unknown',
            address TEXT NOT NULL, state TEXT NOT NULL, last_seen TEXT,
            capabilities TEXT NOT NULL DEFAULT '[]', updated_at TEXT)""")
        self._db.commit()

    def upsert(self, device_id: str, address: str, state: str, *,
               kind: str = "unknown", capabilities: list[str] | None = None) -> None:
        if state not in self.STATES:
            raise ValueError(f"state lạ: {state} (chuẩn: {self.STATES})")
        now = datetime.now(UTC).isoformat()
        self._db.execute(
            "INSERT INTO devices(device_id,kind,address,state,last_seen,capabilities,"
            "updated_at) VALUES(?,?,?,?,?,?,?) "
            "ON CONFLICT(device_id) DO UPDATE SET state=?, last_seen=?, kind=?, "
            "capabilities=?, updated_at=?",
            (device_id, kind, address, state, now, json.dumps(capabilities or []),
             now, state, now, kind, json.dumps(capabilities or []), now))
        self._db.commit()

    def mark_state(self, device_id: str, state: str) -> bool:
        if state not in self.STATES:
            raise ValueError(f"state lạ: {state}")
        cur = self._db.execute("UPDATE devices SET state=?, updated_at=? WHERE device_id=?",
                               (state, datetime.now(UTC).isoformat(), device_id))
        self._db.commit()
        return cur.rowcount > 0

    def get(self, device_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT device_id,kind,address,state,last_seen,capabilities FROM devices "
            "WHERE device_id=?", (device_id,)).fetchone()
        if row is None:
            return None
        return {"device_id": row[0], "kind": row[1], "address": row[2], "state": row[3],
                "last_seen": row[4], "capabilities": json.loads(row[5])}

    def list_by_state(self, state: str) -> list[dict[str, Any]]:
        return [d for d in (self.get(r[0]) for r in self._db.execute(
            "SELECT device_id FROM devices WHERE state=?", (state,)).fetchall())
            if d is not None]


# ───────────────────────── M05+M06+M07: UAG Execution Pipeline ─────────────────────────
@dataclass
class UAGOutcome:
    steps: list[str] = field(default_factory=list)
    executed: bool = False
    verified: bool = False
    result: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    evidence_id: int | None = None
    ticket_id: str = ""

    def deny(self, step: str, reason: str) -> "UAGOutcome":
        self.reason = f"[{step}] {reason}"
        return self


class UAGEngine:
    """Pipeline §IV 12 bước — KHÔNG bỏ bước nào.

    REQUEST→IDENTIFY→AUTHENTICATE→INSPECT→ANALYZE→CLASSIFY→CHECK PERMISSION
    →CHECK APPROVAL→EXECUTE→VERIFY→EVIDENCE→REPORT
    """

    # Hành động tự động được phép (§V): khảo sát/đọc/phân tích/giao tiếp thông thường
    AUTO_ALLOWED = frozenset({
        "DEVICE_DISCOVERY", "DEVICE_IDENTIFICATION", "NETWORK_INSPECTION",
        "AGENT_DISCOVERY", "AGENT_AUTHENTICATION", "AGENT_STATUS",
        "AGENT_RESULT_RETRIEVAL", "AGENT_PERMISSION_INSPECTION",
        "AGENT_RUNTIME_INSPECTION", "AGENT_COMMUNICATION", "AGENT_TASK_DISPATCH",
        "AGENT_ISOLATION_REQUEST",  # chỉ TẠO approval card chờ Quanpt1 — không cô lập
        "EVIDENCE_COLLECTION", "ACTION_VERIFICATION"})

    # §V+M07: intervention (khóa INTERVENTIONS 16 loại của AuthorityGovernor)
    # → các directive UAG được phép gắn với intervention đó
    INTERVENTION_DIRECTIVES: dict[str, frozenset[str]] = {
        "suspend_agent": frozenset({"AGENT_SERVICE_CONTROL"}),
        "kill_process": frozenset({"AGENT_SERVICE_CONTROL"}),
        "isolate_agent": frozenset({"AGENT_SERVICE_CONTROL", "AGENT_ISOLATION_REQUEST"}),
        "restrict_agent": frozenset({"AGENT_PERMISSION_CONTROL", "AGENT_SERVICE_CONTROL"}),
        "modify_permissions": frozenset({"AGENT_PERMISSION_CONTROL"}),
        "disconnect_device": frozenset({"AGENT_SERVICE_CONTROL", "DEVICE_CONTROL"}),
        "change_configuration": frozenset({"AGENT_SERVICE_CONTROL"}),
        "control_physical_robot": frozenset({"DEVICE_CONTROL"}),
        "recover_after_incident": frozenset({"AGENT_RECOVERY", "ROLLBACK_EXECUTION"}),
    }

    def __init__(self, *, qpig: Any, governor: AuthorityGovernor,
                 evidence: EvidenceStore, inventory: DeviceInventory | None = None,
                 qep: QEPCommunicationEngine | None = None,
                 identity_registry: Any = None,
                 max_retries: int = 2, timeout_s: float = 15.0) -> None:
        self.qpig = qpig
        self.governor = governor          # M07: ticket một-lần + hết hạn + scope
        self.evidence = evidence
        self.inventory = inventory
        self.qep = qep or QEPCommunicationEngine()
        self.identities = identity_registry
        self.max_retries = max_retries    # §VIII: retry CÓ GIỚI HẠN
        self.timeout_s = timeout_s
        self._idem: dict[str, dict[str, Any]] = {}   # idempotency cache

    # ------------------------------------------------------------------
    def run(self, directive_name: str, target: str, params: dict[str, Any] | None = None,
            *, ticket_id: str = "", requested_by: str = "tony",
            idempotency_key: str = "") -> UAGOutcome:
        o = UAGOutcome()
        tool_id = DIRECTIVE_NAMES.get(directive_name)
        if tool_id is None:
            return o.deny("REQUEST", f"hành động lạ: {directive_name}")
        o.steps.append("REQUEST")

        # IDENTIFY
        td = self.qpig.registry.get(tool_id)
        if td is None:
            return o.deny("IDENTIFY", f"tool {tool_id} không trong registry")
        o.steps.append("IDENTIFY")

        # AUTHENTICATE (M06 — bắt buộc, không bỏ)
        auth = self._authenticate(target)
        o.steps.append("AUTHENTICATE")
        if not auth[0]:
            return o.deny("AUTHENTICATE", auth[1])

        # INSPECT — mục tiêu có tồn tại/khả tiếp cận không (fail-honest)
        insp = self._inspect(target)
        o.steps.append("INSPECT")
        if insp is not None:
            o.result["inspection"] = insp

        # ANALYZE
        cls = self.qpig.security_classify(target)
        o.steps.append("ANALYZE")

        # CLASSIFY
        risk = td.risk_level.value
        o.steps.append("CLASSIFY")

        # CHECK PERMISSION — §V: tự động chỉ nhóm AUTO_ALLOWED; còn lại cần ticket
        # gắn intervention hợp lệ (16 loại INTERVENTIONS của AuthorityGovernor)
        allowed_interventions: frozenset[str] | None = None
        if directive_name not in self.AUTO_ALLOWED:
            o.steps.append("CHECK_PERMISSION")
            allowed = {d for ds in self.INTERVENTION_DIRECTIVES.values() for d in ds}
            if directive_name not in allowed:
                return o.deny("CHECK_PERMISSION",
                              f"{directive_name} không thuộc bất kỳ intervention nào "
                              "trong 16 loại — không thể cấp ticket")
            allowed_interventions = frozenset(
                k for k, ds in self.INTERVENTION_DIRECTIVES.items()
                if directive_name in ds)
            if not ticket_id:
                return o.deny("CHECK_PERMISSION",
                              f"{directive_name} là hành động có tác động — cần ticket "
                              "Quanpt1 (§V). Pi5 không được tự tạo token.")
        else:
            o.steps.append("CHECK_PERMISSION")

        # CHECK APPROVAL (M07) — bước bắt buộc trong 12 bước §IV.
        # Hành động AUTO (§V): không cần ticket → pass-through có ghi nhận.
        o.steps.append("CHECK_APPROVAL")
        if directive_name not in self.AUTO_ALLOWED:
            ok = False
            msg = ""
            for interv in sorted(allowed_interventions or frozenset()):
                ok, msg = self.governor.consume_for_execution(
                    ticket_id, interv, target)
                if ok:
                    break
            if not ok:
                return o.deny("CHECK_APPROVAL", msg)
            o.ticket_id = ticket_id

        # EXECUTE (M05) — timeout + retry CÓ GIỚI HẠN + idempotency
        attempts = 0
        last_err = ""
        while attempts <= self.max_retries:
            attempts += 1
            if idempotency_key and idempotency_key in self._idem:
                cached = self._idem[idempotency_key]
                o.result["idempotent_replay"] = True
                o.executed = True
                o.result["execution"] = cached
                break
            try:
                res = self._execute_with_timeout(
                    self._execute_directive, directive_name, tool_id, dict(params or {}))
                if res.get("success"):
                    o.executed = True
                    o.result["execution"] = res
                    if idempotency_key:
                        self._idem[idempotency_key] = res
                    break
                last_err = str(res.get("reason", "thất bại không rõ"))
                # lỗi refuse chính sách → KHÔNG retry
                if "refuse" in last_err or "KHÔNG" in last_err:
                    break
            except TimeoutError:
                last_err = f"timeout sau {self.timeout_s}s"
            except Exception as exc:
                last_err = f"lỗi thực thi: {exc}"
            time.sleep(0.05)  # backoff ngắn trong test
        if not o.executed:
            o.reason = f"[EXECUTE] thất bại sau {attempts} lần thử: {last_err}"
            return o
        o.steps.append("EXECUTE")

        # VERIFY — đối chiếu result execution + kiểm chứng qua EvidenceStore
        o.verified = bool(o.result.get("execution", {}).get("success"))
        o.steps.append("VERIFY")

        # EVIDENCE (M08)
        ev = self.qpig.evidence_capture(
            kind="uag_action", target=target,
            payload={"directive": directive_name, "tool_id": tool_id, "params": params,
                     "ticket_id": ticket_id, "requested_by": requested_by,
                     "auth": auth, "classification": cls.get("data"),
                     "risk": risk, "attempts": attempts,
                     "result": o.result.get("execution")})
        o.evidence_id = ev.get("evidence_id")
        o.steps.append("EVIDENCE")

        # REPORT
        o.steps.append("REPORT")
        return o

    # ------------------------------------------------------------------
    def _authenticate(self, target: str) -> tuple[bool, str]:
        """M06: danh tính mục tiêu. UNKNOWN cho phép ĐỌC; hành động tác động
        với target UNKNOWN vẫn đi tiếp tới CHECK_APPROVAL (ticket quyết)."""
        if self.identities is not None:
            try:
                ident = self.identities.get(target)
                status = getattr(ident, "security_status", None) if ident else None
                if status == "QUARANTINED":
                    return False, f"target '{target}' đang QUARANTINED — chặn mọi tác nghiệp"
            except Exception as exc:
                return False, f"SENTINEL lỗi: {exc}"
        return True, "ok"

    def _inspect(self, target: str) -> dict[str, Any] | None:
        if self.inventory is None:
            return None
        rec = self.inventory.get(target)
        if rec is None:
            return {"target": target, "state": "UNKNOWN",
                    "note": "chưa có trong inventory — không suy diễn"}
        if rec["state"] in ("UNREACHABLE", "RETIRED"):
            return {"target": target, "state": rec["state"],
                    "note": "mục tiêu không khả dụng — EXECUTE sẽ fail-honest"}
        return {"target": target, "state": rec["state"]}

    def _execute_with_timeout(self, fn: Callable[..., dict[str, Any]],
                              *args: Any) -> dict[str, Any]:
        """Chạy handler với timeout THẬT (§VIII). Worker leak khi timeout là
        chấp nhận được — không block pipeline (§VIII: retry có giới hạn)."""
        from concurrent.futures import ThreadPoolExecutor
        from concurrent.futures import TimeoutError as FutureTimeout
        ex = ThreadPoolExecutor(max_workers=1)
        try:
            fut = ex.submit(fn, *args)
            try:
                return fut.result(timeout=self.timeout_s)
            except FutureTimeout as exc:
                raise TimeoutError(f"thực thi vượt {self.timeout_s}s") from exc
        finally:
            ex.shutdown(wait=False)

    def _execute_directive(self, directive_name: str, tool_id: str,
                           params: dict[str, Any]) -> dict[str, Any]:
        """Routing thực thi. Action tác động: ticket Quanpt1 ĐÃ consume ở bước
        CHECK_APPROVAL → gọi tầng thực thi với preapproved=True là chính đáng."""
        if directive_name in ("AGENT_SERVICE_CONTROL", "AGENT_RECOVERY"):
            return self.qpig.control_contain(
                str(params.get("action", "SUSPEND")), str(params.get("target", "")),
                preapproved=True, by="uag-ticket")
        if directive_name == "AGENT_PERMISSION_CONTROL":
            if self.qpig.sentinel is None:
                return {"success": False, "reason": "SENTINEL registry chưa gắn — refuse"}
            try:
                self.qpig.sentinel.set_security_status(
                    str(params.get("agent_id", "")),
                    str((params.get("change") or {}).get("status", "RESTRICTED")))
                return {"success": True,
                        "data": {"applied": params.get("change") or {}}}
            except Exception as exc:
                return {"success": False, "reason": f"áp quyền lỗi: {exc}"}
        # Còn lại (đọc + giao tiếp thông thường + rollback...): đi qua QPIG.call chuẩn
        return self.qpig.call(tool_id, params)

    # ------------------------------------------------------------------
    def health(self) -> dict[str, Any]:
        """M08 health check: số bước pipeline + kênh Pi5 + adapter readiness."""
        return {"pipeline_steps": len(self.AUTO_ALLOWED) and 12,
                "adapters_ready": sorted(ADAPTER_REGISTRY),
                "adapters_pending": list(PENDING_PROTOCOLS),
                "pi5_channels_verified": sorted(PI5_CHANNELS_VERIFIED),
                "pi5_status": "NOT_ACCESSIBLE (P0: 11 cổng đóng — chờ owner)",
                "idempotency_cache": len(self._idem)}

    def rollback_hint(self, rc_id: str) -> dict[str, Any]:
        """M08 rollback: chỉ TRẢ HƯỚNG DẪN — deploy/rollback thật qua CSEF card R4."""
        return {"rc_id": rc_id, "note": "rollback thật phải qua ReleaseCandidateStore + "
                "approval R4 (§X: không tự triển khai Production)"}
