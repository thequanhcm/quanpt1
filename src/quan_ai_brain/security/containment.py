"""SENTINEL-S3 (M06): Containment phân quyền 3 cấp + PreserveEvidence.

Master prompt v1.0 mục 5 (governance):
- CẤP 1 AUTONOMOUS: phân tích, cảnh báo, chặn yêu cầu RÕ RÀNG trái phép,
  từ chối lệnh vi phạm chính sách, contain trong phạm vi ĐÃ phê duyệt trước.
- CẤP 2 CONTROLLED: cần phê duyệt — dừng agent quan trọng, cắt mạng diện rộng,
  đổi cấu hình an ninh, khôi phục dữ liệu.
- CẤP 3 HUMAN AUTHORITY: owner bắt buộc — xóa dữ liệu/bằng chứng, đổi kiến trúc.

Không tấn công ngược, không phá hoại (prompt mục 6.đ).
EVIDENCE TRƯỚC KHI KHỐNG CHẾ: snapshot tiến trình + kết nối mạng vào
data/sentinel_evidence.db (append-only) — phục vụ M09 Investigation sau.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ContainmentResult:
    success: bool
    action: str
    authority: str          # AUTONOMOUS | CONTROLLED | HUMAN
    executed: bool          # False = chưa đủ quyền, KHÔNG chạy
    reason: str
    evidence_id: int | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success, "action": self.action,
            "authority": self.authority, "executed": self.executed,
            "reason": self.reason, "evidence_id": self.evidence_id,
            "details": self.details or {},
        }


class EvidenceStore:
    """Bảo toàn bằng chứng append-only — data/sentinel_evidence.db."""

    def __init__(self, db_path: str | Any) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captured_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    target TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    sha256 TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT ''
                )
                """
            )

    def capture(self, kind: str, target: str, payload: dict[str, Any],
                note: str = "") -> int:
        import hashlib

        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO evidence (captured_at, kind, target, payload_json,"
                " sha256, note) VALUES (?,?,?,?,?,?)",
                (_now(), kind, target, raw, sha, note))
            return int(cur.lastrowid)

    def get(self, evidence_id: int) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM evidence WHERE id=?", (evidence_id,)).fetchone()
            if row is None:
                return None
            return {
                "id": row[0], "captured_at": row[1], "kind": row[2],
                "target": row[3], "payload": json.loads(row[4]),
                "sha256": row[5], "note": row[6],
            }

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()
            return int(row[0])


# Hành động CẤP 2 CONTROLLED (cần phê duyệt — prompt mục 5)
CONTROLLED_ACTIONS = {
    "STOP_IMPORTANT_AGENT",
    "NETWORK_ISOLATION_BROAD",
    "SECURITY_CONFIG_CHANGE",
    "DATA_RECOVERY",
}

# Hành động CẤP 3 HUMAN AUTHORITY (owner bắt buộc)
HUMAN_ACTIONS = {
    "DELETE_EVIDENCE",
    "ARCHITECTURE_CHANGE",
    "GRANT_ADMIN_RIGHTS",
}


class ContainmentEngine:
    """Orchestrate khống chế theo phân quyền 3 cấp. KHÔNG tự thực thi R4/R5."""

    def __init__(self, evidence: EvidenceStore,
                 approval_check: Callable[[str, str], bool] | None = None) -> None:
        self.evidence = evidence
        # callable(action, target) -> bool (có card duyệt hay không)
        self.approval_check = approval_check

    def _has_approval(self, action: str, target: str) -> bool:
        if self.approval_check is None:
            return False
        try:
            return bool(self.approval_check(action, target))
        except Exception:
            return False

    def preserve_evidence(self, pid: int, agent_id: str = "") -> int:
        """Snapshot tiến trình + kết nối mạng (chỉ-đọc) trước khi khống chế."""
        snapshot: dict[str, Any] = {"pid": pid, "agent_id": agent_id}
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace")
            snapshot["tasklist"] = (r.stdout or "")[:2000]
        except Exception as exc:
            snapshot["tasklist_error"] = str(exc)
        try:
            r = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace")
            lines = [ln for ln in (r.stdout or "").splitlines()
                     if ln.rstrip().endswith(str(pid))]
            snapshot["connections"] = lines[:50]
        except Exception as exc:
            snapshot["connections_error"] = str(exc)
        return self.evidence.capture(
            "SNAPSHOT", agent_id or f"pid:{pid}", snapshot,
            note="preserve_evidence trước khống chế")

    def execute(self, action: str, target: str, *, by: str,
                preapproved: bool = False,
                evidence_id: int | None = None) -> ContainmentResult:
        """Thực thi hành động khống chế theo đúng cấp quyền.

        - by=owner: đầy đủ quyền trừ R5 (R5 hard-block toàn hệ thống).
        - preapproved=True: hợp đồng auto_contain (S1) đã duyệt trước.
        - CONTROLLED: cần approval_check trả True.
        - HUMAN: chỉ owner.
        """
        is_owner = by.strip().lower() in ("owner", "quanpt1", "owner_dm")
        if action in HUMAN_ACTIONS and not is_owner:
            return ContainmentResult(
                success=False, action=action, authority="HUMAN", executed=False,
                reason="Quyền người điều hành (CẤP 3) — chỉ owner phê duyệt.")
        if action in CONTROLLED_ACTIONS and not (
                is_owner or preapproved or self._has_approval(action, target)):
            return ContainmentResult(
                success=False, action=action, authority="CONTROLLED", executed=False,
                reason="Hành động CẤP 2 — cần phê duyệt trước khi chạy.")

        # --- Thực thi thật ---
        details: dict[str, Any] = {"target": target, "preapproved": preapproved,
                                   "evidence_id": evidence_id}
        if action == "SUSPEND_PID":
            from quan_ai_brain.security.actions import suspend_process

            res = suspend_process(int(target))
            details["tool_result"] = res.get("reason", "")
            return ContainmentResult(
                success=bool(res.get("success")), action=action,
                authority="AUTONOMOUS", executed=True,
                reason=res.get("reason", ""), evidence_id=evidence_id,
                details=details)
        if action == "KILL_PID":
            from quan_ai_brain.security.actions import kill_process

            res = kill_process(int(target))
            details["tool_result"] = res.get("reason", "")
            return ContainmentResult(
                success=bool(res.get("success")), action=action,
                authority="AUTONOMOUS", executed=True,
                reason=res.get("reason", ""), evidence_id=evidence_id,
                details=details)
        if action in CONTROLLED_ACTIONS or action in HUMAN_ACTIONS:
            # Đã qua gate phía trên; giai đoạn này chỉ GHI KẾ HOẠCH + audit,
            # không tự tay đổi cấu hình/khôi phục dữ liệu (R4 — cần sprint sau).
            details["planned_only"] = True
            return ContainmentResult(
                success=True, action=action,
                authority="HUMAN" if action in HUMAN_ACTIONS else "CONTROLLED",
                executed=False, reason="Đã kiểm duyệt — chờ sprint thực thi R4.",
                evidence_id=evidence_id, details=details)
        # AUTONOMOUS khác: chặn yêu cầu rõ ràng trái phép = từ chối ghi nhận
        return ContainmentResult(
            success=True, action=action, authority="AUTONOMOUS", executed=False,
            reason="Đã ghi nhận quyết định chặn (không có thực thi nào cần thiết).",
            evidence_id=evidence_id, details=details)
