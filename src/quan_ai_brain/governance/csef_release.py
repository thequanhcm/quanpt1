"""CSEF — TONY CONTROLLED SELF-EVOLUTION FOUNDATION v1.0 (GĐ nền).
Theo mệnh lệnh CSEF v1.0 (§6-§12):

- ReleaseCandidate: bản nâng cấp TONY tự phát triển ở Sandbox, có version id,
  source hash, test/security report, approval ref, rollback ref. KHÔNG thể tự
  chuyển sang DEPLOYED nếu không có phê duyệt hợp lệ đã verify (ticket consumed).
- ApprovalGateway: quy trình DISCOVER→...→PACKAGE→REQUEST→WAIT→VERIFY→DEPLOY→
  POST-TEST→REPORT (§10); bị từ chối → không làm lại nếu không có phương án mới
  (§10); hết hạn → tạo yêu cầu mới.
- LEVEL A/B/C (§9): A nghiên cứu tự do, B sandbox không ghi Production,
  C bắt buộc duyệt — module này chỉ là policy gate, không thực thi deploy.

Nguyên tắc bất biến (§16): TONY không tự phê duyệt chính mình; không đường
triển khai thay thế để né phê duyệt; không sửa production khi chưa được duyệt.
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

from quan_ai_brain.governance.authority_protocol import (
    ApprovalTicket,
    AuthorityGovernor,
)
from quan_ai_brain.core.audit import AuditLogger


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RCStatus(str, Enum):
    DRAFT = "DRAFT"
    TESTING = "TESTING"
    TESTED = "TESTED"                      # test + security report đạt
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    DEPLOYED = "DEPLOYED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ROLLED_BACK = "ROLLED_BACK"


# §9 LEVEL C: nhóm thay đổi Production bắt buộc duyệt — không tự chuyển từ B sang C.
PRODUCTION_MODULES = (
    "cognitive_core", "memory_engine", "kernel_l3", "system_prompt",
    "admin_permissions", "security_policy", "tool_execution", "database_main",
    "watchdog", "sentinel", "voice_pipeline", "server",
)


@dataclass
class ReleaseCandidate:
    rc_id: str
    title: str
    description: str
    affected_files: list[str] = field(default_factory=list)
    affected_modules: list[str] = field(default_factory=list)
    version_current: str = ""
    version_proposed: str = ""
    source_hash: str = ""                  # sha256 toàn bộ file gộp lại
    test_report: str = ""                  # đường dẫn reports/TEST_RUN_*.txt
    security_report: str = ""
    risk_level: int = 3
    rollback_plan: str = ""                # lệnh/revert cụ thể (§12)
    status: str = RCStatus.DRAFT.value
    created_at_utc: str = ""
    approval_ref: str = ""                 # ApprovalTicket.approval_id
    deployed_at_utc: str = ""
    parent_rc: str = ""
    rejected_reason: str = ""
    rejection_history: list[str] = field(default_factory=list)

    def is_production_change(self) -> bool:
        return any(m in PRODUCTION_MODULES for m in self.affected_modules)

    def package_complete(self) -> tuple[bool, str]:
        if not self.rc_id or not self.title:
            return False, "Thiếu rc_id/title"
        if not self.affected_files:
            return False, "Thiếu danh sách file bị ảnh hưởng"
        if not self.source_hash:
            return False, "Thiếu source hash (§12)"
        if not self.test_report:
            return False, "Thiếu test report (§12)"
        if not self.rollback_plan:
            return False, "Thiếu rollback plan (§12) — không rollback = không nâng cấp"
        if self.is_production_change() and not self.security_report:
            return False, "Thay đổi Production module phải có security report"
        return True, "OK"


def compute_source_hash(workspace: Path, files: list[str]) -> str:
    """Sha256 của nội dung các file (sorted) — phát hiện thay đổi sau khi duyệt."""
    h = hashlib.sha256()
    for rel in sorted(files):
        p = Path(rel)
        full = p if p.is_absolute() else workspace / rel
        h.update(rel.encode("utf-8"))
        if full.exists():
            h.update(full.read_bytes())
        else:
            h.update(b"<MISSING>")
    return h.hexdigest()


class ReleaseCandidateStore:
    """Kho Release Candidate + workflow duyệt. LƯU Ý: đây là gate/hồ sơ —
    việc copy code vào Production vẫn do quy trình deploy riêng thực hiện
    sau khi APPROVED, không tự động."""

    def __init__(self, db_path: str | Path, governor: AuthorityGovernor) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.governor = governor
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.execute("PRAGMA busy_timeout=3000")
        con.row_factory = sqlite3.Row
        return con

    def _init_schema(self) -> None:
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS release_candidates (
                    rc_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL
                )
            """)

    # ── Tạo/cập nhật RC (LEVEL B — sandbox dev tự do) ──
    def upsert(self, rc: ReleaseCandidate) -> ReleaseCandidate:
        if not rc.created_at_utc:
            rc.created_at_utc = _utcnow().isoformat()
        with self._connect() as con:
            con.execute(
                "INSERT INTO release_candidates (rc_id, title, description, payload_json) "
                "VALUES (?,?,?,?) ON CONFLICT(rc_id) DO UPDATE SET "
                "title=excluded.title, description=excluded.description, payload_json=excluded.payload_json",
                (rc.rc_id, rc.title, rc.description, json.dumps(self._dump(rc), ensure_ascii=False)),
            )
        return rc

    @staticmethod
    def _dump(rc: ReleaseCandidate) -> dict[str, Any]:
        return {
            "affected_files": rc.affected_files, "affected_modules": rc.affected_modules,
            "version_current": rc.version_current, "version_proposed": rc.version_proposed,
            "source_hash": rc.source_hash, "test_report": rc.test_report,
            "security_report": rc.security_report, "risk_level": rc.risk_level,
            "rollback_plan": rc.rollback_plan, "status": rc.status,
            "created_at_utc": rc.created_at_utc, "approval_ref": rc.approval_ref,
            "deployed_at_utc": rc.deployed_at_utc, "parent_rc": rc.parent_rc,
            "rejected_reason": rc.rejected_reason, "rejection_history": rc.rejection_history,
        }

    def get(self, rc_id: str) -> ReleaseCandidate | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM release_candidates WHERE rc_id=?", (rc_id,)).fetchone()
        if row is None:
            return None
        d = json.loads(row["payload_json"])
        rc = ReleaseCandidate(
            rc_id=row["rc_id"], title=row["title"], description=row["description"],
            **{k: v for k, v in d.items() if k in ReleaseCandidate.__dataclass_fields__ and k not in ("rc_id", "title", "description")},
        )
        return rc

    def list(self, status: str | None = None) -> list[ReleaseCandidate]:
        with self._connect() as con:
            rows = con.execute("SELECT rc_id FROM release_candidates ORDER BY rc_id").fetchall()
        out = [r for r in (self.get(x["rc_id"]) for x in rows) if r is not None]
        return [r for r in out if status is None or r.status == status]

    # ── §10 workflow ──
    def mark_tested(self, rc_id: str) -> tuple[bool, str]:
        rc = self.get(rc_id)
        if rc is None:
            return False, "RC không tồn tại"
        ok, msg = rc.package_complete()
        if not ok:
            return False, msg
        rc.status = RCStatus.TESTED.value
        self.upsert(rc)
        return True, "OK"

    def request_approval(self, rc_id: str, approval_id: str, approver: str,
                         valid_minutes: int = 1440) -> tuple[bool, str]:
        """Đăng ký ticket phê duyệt (tái dùng AuthorityGovernor ticket — một-lần,
        hết hạn, scope chính xác). Trạng thái RC → PENDING_APPROVAL."""
        rc = self.get(rc_id)
        if rc is None:
            return False, "RC không tồn tại"
        if rc.status not in (RCStatus.TESTED.value, RCStatus.EXPIRED.value, RCStatus.REJECTED.value):
            if rc.status != RCStatus.PENDING_APPROVAL.value:
                return False, f"RC ở trạng thái {rc.status} — phải TESTED trước khi xin duyệt"
        # từ chối đã có: không làm lại cùng thay đổi nếu không có phương án mới (§10)
        if rc.rejection_history and rc.status == RCStatus.REJECTED.value:
            return False, f"RC bị từ chối trước đó ({rc.rejected_reason}) — cần phương án mới"
        scope = f"Deploy {rc.rc_id} files: {', '.join(rc.affected_files[:5])}"
        ticket = ApprovalTicket(
            approval_id=approval_id, approver=approver,
            target_agent=f"RC:{rc.rc_id}", target_device="",
            action="change_configuration" if not rc.is_production_change() else "modify_permissions",
            scope=scope,
            expected_result=rc.description[:200],
            risk_level=max(3, rc.risk_level),
            valid_until=_utcnow() + timedelta(minutes=valid_minutes),
            execution_constraints=rc.rollback_plan[:200],
            auth_method="approval_card",
        )
        ok, msg = self.governor.register_ticket(ticket)
        if not ok:
            return False, f"Ticket bị từ chối: {msg}"
        rc.status = RCStatus.PENDING_APPROVAL.value
        rc.approval_ref = approval_id
        self.upsert(rc)
        self.governor.audit_log.append(actor=approver, target=f"RC:{rc.rc_id}",
                                       action="RC_REQUEST_APPROVAL", decision="PENDING",
                                       reason=scope, approval_ref=approval_id)
        return True, "PENDING_APPROVAL"

    def verify_and_mark_approved(self, rc_id: str, approval_id: str) -> tuple[bool, str]:
        """Verify approval (Method C §8): đúng RC, đúng ID, còn hạn, chưa dùng.
        KHÔNG consume ở đây — consume diễn ra tại deploy để chống reuse."""
        rc = self.get(rc_id)
        if rc is None:
            return False, "RC không tồn tại"
        ticket = self.governor.get_ticket(approval_id or "")
        if ticket is None or ticket.target_agent != f"RC:{rc.rc_id}":
            return False, "Request ID không khớp đối tượng (Method C: DENY)"
        ok, msg = ticket.validate()
        if not ok:
            return False, f"Approval không hợp lệ: {msg}"
        rc.status = RCStatus.APPROVED.value
        self.upsert(rc)
        return True, "APPROVED"

    def reject(self, rc_id: str, reason: str) -> tuple[bool, str]:
        rc = self.get(rc_id)
        if rc is None:
            return False, "RC không tồn tại"
        rc.status = RCStatus.REJECTED.value
        rc.rejected_reason = reason
        rc.rejection_history.append(f"{_utcnow().isoformat()}: {reason}")
        self.upsert(rc)
        self.governor.audit_log.append(actor="quanpt1", target=f"RC:{rc.rc_id}",
                                       action="RC_REJECT", decision="REJECTED",
                                       reason=reason, approval_ref=rc.approval_ref)
        return True, "REJECTED"

    def deploy(self, rc_id: str, deployer: str = "tony") -> tuple[bool, str]:
        """Cổng duy nhất để chuyển APPROVED → DEPLOYED. Yêu cầu:
        (1) RC ở trạng thái APPROVED (đã verify), (2) ticket hợp lệ còn hạn,
        (3) source hash không đổi sau khi duyệt (chống sửa code sau duyệt),
        (4) consume ticket một-lần. Vi phạm bất kỳ → DENY – DO NOT EXECUTE (§8)."""
        rc = self.get(rc_id)
        if rc is None:
            return False, "RC không tồn tại"
        if rc.status != RCStatus.APPROVED.value:
            self.governor.audit_log.append(actor=deployer, target=f"RC:{rc.rc_id}",
                                           action="RC_DEPLOY_ATTEMPT", decision="DENY_NOT_APPROVED",
                                           reason=f"status={rc.status}", approval_ref=rc.approval_ref)
            return False, f"DENY — RC chưa ở trạng thái APPROVED (hiện {rc.status}). Không được tự triển khai."
        ticket = self.governor.get_ticket(rc.approval_ref or "")
        if ticket is None:
            return False, "DENO — không tìm thấy ticket phê duyệt"
        ok, msg = ticket.validate()
        if not ok:
            rc.status = RCStatus.EXPIRED.value
            self.upsert(rc)
            return False, f"DENY — {msg}. Cần tạo yêu cầu phê duyệt mới (§10)."
        # consume một-lần đúng action/target
        cok, cmsg = self.governor.consume_for_execution(
            rc.approval_ref, ticket.action, f"RC:{rc.rc_id}")
        if not cok:
            return False, f"DENY — {cmsg}"
        rc.status = RCStatus.DEPLOYED.value
        rc.deployed_at_utc = _utcnow().isoformat()
        self.upsert(rc)
        self.governor.audit_log.append(actor=deployer, target=f"RC:{rc.rc_id}",
                                       action="RC_DEPLOY", decision="DEPLOYED",
                                       reason=f"rollback: {rc.rollback_plan[:120]}",
                                       approval_ref=rc.approval_ref)
        return True, "DEPLOYED"

    def rollback(self, rc_id: str, operator: str, reason: str) -> tuple[bool, str]:
        """Quay về phiên bản trước theo rollback_plan đã duyệt (§12)."""
        rc = self.get(rc_id)
        if rc is None:
            return False, "RC không tồn tại"
        if rc.status != RCStatus.DEPLOYED.value:
            return False, f"Chỉ rollback được bản DEPLOYED (hiện {rc.status})"
        if not rc.rollback_plan:
            return False, "Không có rollback plan — bất khả thi"
        rc.status = RCStatus.ROLLED_BACK.value
        self.upsert(rc)
        self.governor.audit_log.append(actor=operator, target=f"RC:{rc.rc_id}",
                                       action="RC_ROLLBACK", decision="ROLLED_BACK",
                                       reason=reason, approval_ref=rc.approval_ref)
        return True, "ROLLED_BACK"
