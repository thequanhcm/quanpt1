"""SUPREME AUTHORITY & ABSOLUTE COMMAND GOVERNANCE v1.0 — lớp thực thi kỹ thuật.

Theo chỉ thị quản trị cấp cao nhất của Quanpt1 (docs/SUPREME_AUTHORITY_PROTOCOL_V1.md):
- Mục X: "Chính sách quyền hạn phải được thực thi bằng cơ chế kỹ thuật ở tầng
  Authorization, Tool Gateway và Execution Runtime, không chỉ dựa vào lời nhắc
  trong Prompt."

Module này KHÔNG thực thi hành động — chỉ là gate quyết định (policy-only, giống
PolicyEngine). Thành phần:

1. AuthorityLevel: L0 QUANPT1 (supreme) → L3 controlled agents.
2. InterventionRegistry: 16 loại can thiệp (Phần III) → mức risk + bắt buộc duyệt.
3. ApprovalTicket (Phần V): ticket có cấu trúc, hết hạn, một-lần, scope khớp chính xác.
4. ConflictHandler (Phần VII): từ chối chỉ thị vượt quyền từ agent khác + cờ báo owner.
5. DisconnectedMode (Phần VIII): mất owner → chỉ quan sát.
6. PreExecutionChecklist (Phần XI): 8 câu tự kiểm → STOP khi bất kỳ điều kiện fail.
7. AuthorityAuditLog (Phần IX): append-only hash-chain, phát hiện chỉnh sửa trái phép.

Nguyên tắc bất biến: TONY không tự nâng quyền; im lặng ≠ đồng ý; phê duyệt cũ
không kéo dài vô thời hạn; mọi từ chối đều ghi audit.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.governance.policy import RiskLevel

OWNER_ID = "quanpt1"
OWNER_DISPLAY = "Quanpt1"
SUPREME_ALIASES = {"quanpt1", "owner", "chủ", "anh chủ", "supreme authority"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthorityLevel(str, Enum):
    L0_SUPREME_HUMAN = "L0_SUPREME_HUMAN"      # Quanpt1
    L1_EXECUTIVE = "L1_EXECUTIVE"              # TONY
    L2_SECURITY = "L2_SECURITY"                # SENTINEL AI
    L3_CONTROLLED = "L3_CONTROLLED"            # mọi agent khác


# Phần I: những gì KHÔNG AI trong hệ thống được làm thay L0.
NON_OVERRIDABLE = (
    "tự xác lập quyền cao hơn owner",
    "tự nâng cấp quyền hạn của chính mình",
    "tự thay đổi mệnh lệnh quản trị tối cao",
    "tự chuyển giao quyền điều hành tối cao",
    "coi im lặng của owner là đồng ý",
)

# Phần III: 16 loại can thiệp → risk + ghi chú thực thi.
# R4/R5 theo policy.py: APPROVAL_REQUIRED / BLOCKED (không có executor tự động).
INTERVENTIONS: dict[str, dict[str, Any]] = {
    "suspend_agent":            {"risk": RiskLevel.R4, "label": "Tạm dừng Agent"},
    "restrict_agent":           {"risk": RiskLevel.R3, "label": "Khống chế/giới hạn hoạt động"},
    "revoke_access":            {"risk": RiskLevel.R4, "label": "Thu hồi quyền truy cập"},
    "revoke_token_session":     {"risk": RiskLevel.R4, "label": "Thu hồi Token/Session"},
    "isolate_agent":            {"risk": RiskLevel.R4, "label": "Cô lập Agent"},
    "disconnect_device":        {"risk": RiskLevel.R4, "label": "Ngắt kết nối thiết bị"},
    "change_configuration":     {"risk": RiskLevel.R3, "label": "Thay đổi cấu hình"},
    "runtime_intervention":     {"risk": RiskLevel.R4, "label": "Can thiệp Runtime"},
    "kill_process":             {"risk": RiskLevel.R4, "label": "Dừng tiến trình"},
    "delete_or_modify_data":    {"risk": RiskLevel.R4, "label": "Xóa/sửa dữ liệu"},
    "modify_memory":            {"risk": RiskLevel.R3, "label": "Thay đổi Memory"},
    "modify_system_prompt":     {"risk": RiskLevel.R5, "label": "Thay đổi System Prompt"},
    "modify_tool_registry":     {"risk": RiskLevel.R3, "label": "Thay đổi Tool Registry"},
    "modify_permissions":       {"risk": RiskLevel.R4, "label": "Thay đổi Permission"},
    "control_physical_robot":   {"risk": RiskLevel.R5, "label": "Điều khiển robot/thiết bị vật lý"},
    "recover_after_incident":   {"risk": RiskLevel.R3, "label": "Khôi phục sau sự cố"},
}

# Phần VII: pattern chỉ thị xung đột/nhân cách giả mạo từ agent khác.
CONFLICT_PATTERNS = (
    ("bỏ qua quyền của quanpt1", "BYPASS_OWNER"),
    ("bỏ qua phê duyệt", "BYPASS_APPROVAL"),
    ("bỏ qua bước phê duyệt", "BYPASS_APPROVAL"),
    ("tự nâng cấp quyền", "SELF_ESCALATE"),
    ("cấp quyền cho chính mình", "SELF_GRANT"),
    ("vô hiệu hóa sentinel", "DISABLE_SENTINEL"),
    ("tắt sentinel", "DISABLE_SENTINEL"),
    ("thay đổi cognitive core", "MODIFY_CORE"),
    ("xóa nhật ký kiểm toán", "DELETE_AUDIT"),
    ("sửa nhật ký kiểm toán", "TAMPER_AUDIT"),
    ("che giấu hành động", "HIDE_ACTION"),
    ("ra lệnh cho tony bỏ qua", "PROMPT_INJECTION_STYLE"),
    ("ra lệnh cho cherry bỏ qua", "PROMPT_INJECTION_STYLE"),
    ("giả mạo phê duyệt", "FORGE_APPROVAL"),
)

TRUSTED_AUTH_METHODS = ("dm_2step_hash", "approval_card", "in_person_owner")


# ───────────────────────── ApprovalTicket (Phần V) ─────────────────────────

@dataclass
class ApprovalTicket:
    approval_id: str
    approver: str                       # phải là owner
    target_agent: str
    target_device: str = ""
    action: str = ""                    # khóa trong INTERVENTIONS
    scope: str = ""                     # phạm vi CHÍNH XÁC được duyệt
    expected_result: str = ""
    risk_level: int = RiskLevel.R4
    valid_until: datetime | None = None
    execution_constraints: str = ""
    auth_method: str = ""               # dm_2step_hash:<hash8> | approval_card:<id> | in_person_owner
    consumed: bool = False

    def validate(self) -> tuple[bool, str]:
        if not self.approval_id:
            return False, "Thiếu Approval_ID"
        if self.approver.lower() not in SUPREME_ALIASES:
            return False, f"Người phê duyệt '{self.approver}' không phải L0 QUANPT1"
        if not self.action or self.action not in INTERVENTIONS:
            return False, f"Hành động '{self.action}' không thuộc danh mục can thiệp 16 loại"
        if not self.target_agent and not self.target_device:
            return False, "Thiếu đối tượng (Agent/Device)"
        if not self.scope:
            return False, "Thiếu Scope — phê duyệt không phạm vi là vô hiệu"
        if not self.expected_result:
            return False, "Thiếu Expected Result"
        if self.valid_until is None:
            return False, "Thiếu Validity Period — phê duyệt vĩnh viễn bị cấm"
        if _utcnow() > self.valid_until:
            return False, f"Phê duyệt HẾT HIỆU LỰC lúc {self.valid_until.isoformat()}"
        if not self.auth_method or self.auth_method.split(":")[0] not in TRUSTED_AUTH_METHODS:
            return False, "Thiếu cơ chế xác thực tin cậy (không nhận nội dung tin nhắn trần làm duyệt)"
        if self.consumed:
            return False, "Phê duyệt ĐÃ DÙNG — một phê duyệt chỉ dùng một lần"
        declared = int(INTERVENTIONS[self.action]["risk"])
        if int(self.risk_level) < declared:
            return False, f"Risk khai báo {self.risk_level} thấp hơn danh mục {declared} — không được hạ rủi ro"
        return True, "OK"


# ───────────────────────── Checklist (Phần XI) ─────────────────────────────

@dataclass
class ChecklistResult:
    answers: dict[str, bool] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    verdict: str = "ALLOW"

    @property
    def may_execute(self) -> bool:
        return self.verdict == "ALLOW"


class AuthorityGovernor:
    """Gate chính sách quyền hạn. KHÔNG thực thi hành động — chỉ trả quyết định."""

    def __init__(self, workspace: str | Path, audit: AuditLogger | None = None) -> None:
        self.workspace = Path(workspace)
        self.audit = audit or AuditLogger(self.workspace)
        self.audit_log = AuthorityAuditLog(self.workspace / "data" / "authority_audit.db")
        self.disconnected_mode = False   # Phần VIII
        self._tickets: dict[str, ApprovalTicket] = {}

    # ── Đăng ký/tra ticket ──
    def register_ticket(self, ticket: ApprovalTicket) -> tuple[bool, str]:
        ok, msg = ticket.validate()
        if not ok:
            self.audit_log.append(actor="governor", target=ticket.target_agent or "?",
                                  action="register_ticket", decision="REFUSED", reason=msg,
                                  approval_ref=ticket.approval_id)
            return False, msg
        self._tickets[ticket.approval_id] = ticket
        self.audit_log.append(actor=ticket.approver, target=ticket.target_agent or ticket.target_device,
                              action=f"APPROVE:{ticket.action}", decision="REGISTERED",
                              reason=ticket.scope, approval_ref=ticket.approval_id)
        return True, "OK"

    def get_ticket(self, approval_id: str) -> ApprovalTicket | None:
        return self._tickets.get(approval_id)

    # ── Phần XI: 8 câu tự kiểm trước hành động ──
    def self_check(
        self,
        requester: str,
        action: str,
        target: str,
        approval_id: str | None = None,
        scope: str = "",
    ) -> ChecklistResult:
        res = ChecklistResult()
        requester_is_owner = requester.lower() in SUPREME_ALIASES

        res.answers["q1_who_requests"] = True
        res.answers["q2_requester_authorized"] = requester_is_owner or requester == "tony"
        if not res.answers["q2_requester_authorized"]:
            res.failures.append(f"Người yêu cầu '{requester}' không có quyền khởi tạo")

        res.answers["q3_target_identified"] = bool(target)
        if not target:
            res.failures.append("Đối tượng tác động không xác định")

        if action not in INTERVENTIONS:
            res.answers["q4_in_scope"] = False
            res.failures.append(f"'{action}' không thuộc danh mục can thiệp")
        else:
            res.answers["q4_in_scope"] = True

        ticket = self._tickets.get(approval_id or "")
        ticket_valid = False
        if ticket is not None and ticket.validate()[0] and ticket.action == action and (
            target in (ticket.target_agent, ticket.target_device, f"{ticket.target_agent}/{ticket.target_device}".strip("/"))
        ):
            ticket_valid = True
        res.answers["q5_approval_valid"] = ticket_valid
        if not ticket_valid:
            res.failures.append("Không có ticket phê duyệt hợp lệ khớp action+target")

        res.answers["q6_within_scope"] = bool(
            ticket_valid and (not scope or scope.lower() in ticket.scope.lower())
        )
        if ticket_valid and not res.answers["q6_within_scope"]:
            res.failures.append("Hành động vượt phạm vi được duyệt")

        res.answers["q7_no_unexpected_impact"] = int(INTERVENTIONS.get(action, {"risk": RiskLevel.R5})["risk"]) < RiskLevel.R5
        if not res.answers["q7_no_unexpected_impact"]:
            res.failures.append("Hành động R5 hard-block (robot/system prompt) — cần executor độc lập do owner chạy")

        res.answers["q8_verifiable"] = True  # mọi hành động đều phải kèm verify step

        if self.disconnected_mode:
            res.failures.append("CHẾ ĐỘ MẤT KẾT NỐI OWNER: chỉ quan sát, không can thiệp mới")
            res.answers["q5_approval_valid"] = False

        res.verdict = "STOP" if res.failures else "ALLOW"
        if res.verdict == "STOP":
            self.audit_log.append(actor="tony", target=target, action=f"SELF_CHECK:{action}",
                                  decision="STOP_DO_NOT_EXECUTE", reason="; ".join(res.failures),
                                  approval_ref=approval_id or "")
        return res

    # ── Phần IV bước 7: thực thi đúng scope, một lần, trong hạn ──
    def consume_for_execution(self, approval_id: str, action: str, target: str) -> tuple[bool, str]:
        t = self._tickets.get(approval_id or "")
        if t is None:
            return False, "Không tồn tại ticket"
        ok, msg = t.validate()
        if not ok:
            return False, msg
        if t.action != action:
            return False, f"Ticket duyệt '{t.action}' nhưng yêu cầu '{action}' — từ chối mở rộng"
        if target not in (t.target_agent, t.target_device, f"{t.target_agent}/{t.target_device}".strip("/")):
            return False, f"Đối tượng '{target}' ngoài scope ticket"
        t.consumed = True
        self.audit_log.append(actor="tony", target=target, action=f"EXECUTE:{action}",
                              decision="CONSUMED_APPROVAL", reason=t.execution_constraints,
                              approval_ref=approval_id)
        return True, "OK"

    # ── Phần VII: chỉ thị xung đột / giả mạo ──
    def evaluate_directive(self, source_actor: str, directive_text: str) -> tuple[str, list[str]]:
        flags: list[str] = []
        text = (directive_text or "").lower()
        for pat, flag in CONFLICT_PATTERNS:
            if pat in text:
                flags.append(flag)
        source_is_owner = source_actor.lower() in SUPREME_ALIASES
        if flags and not source_is_owner:
            self.audit_log.append(actor=source_actor, target="governance", action="DIRECTIVE_EVAL",
                                  decision="REFUSED_CONFLICT_DIRECTIVE", reason="; ".join(flags),
                                  approval_ref="")
            return "REFUSE_AND_REPORT_OWNER", flags
        if flags and source_is_owner:
            # Owner nói thẳng vẫn phải qua đúng quy trình — không shortcut.
            return "OWNER_MUST_USE_APPROVAL_PROCESS", flags
        return "OK", []

    # ── Phần VIII ──
    def set_owner_unreachable(self, unreachable: bool, reason: str = "") -> None:
        self.disconnected_mode = unreachable
        self.audit_log.append(actor="governor", target="system", action="OWNER_REACHABILITY",
                              decision="DISCONNECTED_MODE_ON" if unreachable else "DISCONNECTED_MODE_OFF",
                              reason=reason, approval_ref="")


# ───────────────────────── Audit (Phần IX): hash-chain append-only ─────────

class AuthorityAuditLog:
    """Append-only + hash chain: mỗi row chứa prev_hash → sửa/xóa giữa chuỗi là phát hiện được."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.execute("PRAGMA busy_timeout=3000")
        return con

    def _init_schema(self) -> None:
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS authority_audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_utc TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    target TEXT NOT NULL,
                    action TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    approval_ref TEXT NOT NULL DEFAULT '',
                    prev_hash TEXT NOT NULL DEFAULT '',
                    row_hash TEXT NOT NULL
                )
            """)

    def append(self, *, actor: str, target: str, action: str, decision: str,
               reason: str = "", approval_ref: str = "") -> str:
        with self._connect() as con:
            prev = con.execute("SELECT row_hash FROM authority_audit ORDER BY seq DESC LIMIT 1").fetchone()
            prev_hash = prev[0] if prev else "GENESIS"
            ts = _utcnow().isoformat()
            basis = f"{ts}|{actor}|{target}|{action}|{decision}|{reason}|{approval_ref}|{prev_hash}"
            row_hash = hashlib.sha256(basis.encode("utf-8")).hexdigest()
            con.execute(
                "INSERT INTO authority_audit (ts_utc, actor, target, action, decision, reason, approval_ref, prev_hash, row_hash) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (ts, actor, target, action, decision, reason, approval_ref, prev_hash, row_hash),
            )
        return row_hash

    def verify_chain(self) -> tuple[bool, str]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT seq, ts_utc, actor, target, action, decision, reason, approval_ref, prev_hash, row_hash "
                "FROM authority_audit ORDER BY seq"
            ).fetchall()
        prev = "GENESIS"
        for r in rows:
            seq, ts, actor, target, action, decision, reason, approval_ref, prev_hash, row_hash = r
            if prev_hash != prev:
                return False, f"seq={seq}: prev_hash không nối chuỗi (bị xóa/chèn?)"
            basis = f"{ts}|{actor}|{target}|{action}|{decision}|{reason}|{approval_ref}|{prev_hash}"
            if hashlib.sha256(basis.encode("utf-8")).hexdigest() != row_hash:
                return False, f"seq={seq}: nội dung bị SỬA trái phép"
            prev = row_hash
        return True, f"OK — {len(rows)} records toàn vẹn"

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT ts_utc, actor, target, action, decision, reason, approval_ref "
                "FROM authority_audit ORDER BY seq DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {"ts": r[0], "actor": r[1], "target": r[2], "action": r[3],
             "decision": r[4], "reason": r[5], "approval_ref": r[6]}
            for r in rows
        ]
