"""Q-4 (01/11/2026, ĐÃ DUYỆT): Owner approval verifier cho R4 promotion.

Fail-closed verifier nối KnowledgeQuarantine.approve_and_promote() với surface
phê duyệt owner đã xác thực (NetChatApprovalAdapter + ApprovalCardStore):

  1. approval_evidence = task_code của một approval card trong governance.db
  2. Card phải ở trạng thái APPROVED (chỉ qua approve_card — không tự sửa DB)
  3. Bằng chứng APPROVED phải ghi nhận auth_method thuộc tập cho phép
     (netchat_dm = sender đã kiểm qua NetChatApprovalAdapter;
      owner_desktop_directive = mệnh lệnh verbatim của owner trong phiên desktop)
  4. approvals table phải có record của quanpt1 cho request_id của card
  5. Card chưa hết TTL, chưa bị một batch khác tiêu dùng (ledger 1-lần-dùng,
     cho phép resume khi batch đang IN_PROGRESS — an toàn khi crash giữa chừng)

Không bao giờ trả True "mặc định": thiếu bất kỳ bằng chứng nào → False/PermissionError.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# auth_method hợp lệ — chỉ 2 đường owner đã xác thực danh tính
ALLOWED_AUTH_METHODS = {"netchat_dm", "owner_desktop_directive"}
OWNER_IDS = {"quanpt1", "Quanpt1"}
LEDGER_NAME = "data/q4_batch_ledger.json"


class Q4BatchLedger:
    """Sổ tiêu dùng 1-lần-dùng cho batch promotion (crash-safe)."""

    def __init__(self, workspace: Path) -> None:
        self.path = workspace / LEDGER_NAME

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def get(self, task_code: str) -> dict[str, Any] | None:
        return self._read().get(task_code)

    def mark_in_progress(self, task_code: str, batch_id: str) -> None:
        data = self._read()
        data[task_code] = {
            "status": "IN_PROGRESS",
            "batch_id": batch_id,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "items_done": data.get(task_code, {}).get("items_done", 0),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def increment(self, task_code: str, n: int = 1) -> None:
        data = self._read()
        entry = data.get(task_code)
        if not entry:
            raise KeyError(f"Ledger entry missing for {task_code}")
        entry["items_done"] = int(entry.get("items_done", 0)) + n
        entry["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def mark_done(self, task_code: str, total: int) -> None:
        data = self._read()
        entry = data.get(task_code)
        if not entry:
            raise KeyError(f"Ledger entry missing for {task_code}")
        entry["status"] = "DONE"
        entry["items_done"] = total
        entry["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class GovernanceApprovalVerifier:
    """ApprovalVerifier fail-closed: đọc bằng chứng từ governance.db."""

    def __init__(self, governance_db: str | Path, workspace: str | Path | None = None) -> None:
        self.db_path = Path(governance_db)
        ws = Path(workspace) if workspace else self.db_path.parent.parent
        self.ledger = Q4BatchLedger(ws)
        if not self.db_path.exists():
            raise FileNotFoundError(f"governance.db không tồn tại: {self.db_path}")

    def _load_card(self, task_code: str) -> dict[str, Any] | None:
        con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            row = con.execute(
                "SELECT task_code, status, request_id, ttl_expires_at_utc, evidence_json "
                "FROM approval_cards WHERE task_code = ?",
                (task_code,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            con.close()

    def _has_owner_approval_record(self, request_id: str) -> bool:
        con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        try:
            # status hợp lệ: 'completed' (đã consume) hoặc 'approved' (mới grant)
            row = con.execute(
                "SELECT COUNT(*) FROM approvals WHERE request_id = ? "
                "AND status IN ('completed', 'approved')",
                (request_id,),
            ).fetchone()
            count = int(row[0]) if row else 0
            row2 = con.execute(
                "SELECT COUNT(*) FROM approvals WHERE request_id = ? "
                "AND status IN ('completed', 'approved') "
                "AND LOWER(approver) IN ('quanpt1')",
                (request_id,),
            ).fetchone()
            owner_count = int(row2[0]) if row2 else 0
            return count >= 1 and owner_count >= 1
        finally:
            con.close()

    def verify(self, candidate_id: str, approved_by: str, approval_evidence: str) -> bool:
        """Trả về True CHỈ khi toàn bộ chuỗi bằng chứng khớp. Fail-closed."""
        task_code = (approval_evidence or "").strip()
        if not task_code:
            return False
        card = self._load_card(task_code)
        if card is None:
            return False
        if card["status"] != "APPROVED":
            return False
        if approved_by not in OWNER_IDS:
            return False
        # TTL
        try:
            ttl = datetime.fromisoformat(card["ttl_expires_at_utc"])
            if ttl.tzinfo is None:
                ttl = ttl.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > ttl:
                return False
        except (ValueError, TypeError):
            return False
        # Bằng chứng APPROVED với auth_method hợp lệ
        try:
            evidence = json.loads(card.get("evidence_json") or "[]")
        except json.JSONDecodeError:
            evidence = []
        approved_events = [
            ev for ev in evidence
            if isinstance(ev, dict)
            and ev.get("event") == "APPROVED"
            and ev.get("auth_method") in ALLOWED_AUTH_METHODS
            and str(ev.get("approver", "")).lower() in {a.lower() for a in OWNER_IDS}
        ]
        if not approved_events:
            return False
        # Formal approvals record của owner
        if not self._has_owner_approval_record(card["request_id"]):
            return False
        # Ledger 1-lần-dùng (cho phép resume IN_PROGRESS)
        entry = self.ledger.get(task_code)
        if entry and entry.get("status") == "DONE":
            return False
        return True

    def __call__(self, candidate_id: str, approved_by: str, approval_evidence: str) -> bool:
        return self.verify(candidate_id, approved_by, approval_evidence)
