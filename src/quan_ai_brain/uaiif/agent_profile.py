"""UAIIF-S4 (GĐ1): Universal Agent Profile — hồ sơ chuẩn 24 trường.

Master prompt UAIIF v1.0 mục VI: mỗi agent phát hiện được phải có hồ sơ với
24 trường tối thiểu. MỖI TRƯỜNG có trạng thái nhận thức luận riêng:
Verified / Observed / Inferred / Unknown / Not_Accessible.
KHÔNG được tự điền thông tin chưa xác minh thành sự thật (fail-honest).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Trạng thái từng trường
VERIFIED = "Verified"
OBSERVED = "Observed"
INFERRED = "Inferred"
UNKNOWN = "Unknown"
NOT_ACCESSIBLE = "Not_Accessible"
FIELD_STATUSES = (VERIFIED, OBSERVED, INFERRED, UNKNOWN, NOT_ACCESSIBLE)

# 24 trường chuẩn (master prompt mục VI)
PROFILE_FIELDS = (
    "Agent_ID", "Agent_Name", "Owner", "Provider", "Agent_Type",
    "Architecture", "Runtime", "Model", "Version",
    "Communication_Protocol", "API_Endpoints", "Tool_Registry",
    "Memory_Type", "Knowledge_Source", "Capability_Map",
    "Permission_Scope", "Dependencies", "Operational_Status",
    "Security_Status", "Trust_Level", "Risk_Score",
    "Last_Inspection", "Evidence_References", "Known_Limitations",
)

VN_TZ = timezone(timedelta(hours=7))


def _now() -> str:
    return datetime.now(VN_TZ).isoformat()


class UniversalAgentProfileStore:
    """SQLite data/uaiif_profiles.db — hồ sơ agent + trạng thái từng trường."""

    def __init__(self, db_path: str | Any) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_profiles (
                    profile_id TEXT PRIMARY KEY,
                    target TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    fields_json TEXT NOT NULL,          -- {field: {value, status}}
                    assessment_type TEXT NOT NULL DEFAULT '',
                    discovery_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )

    # ------------------------------------------------------------------
    def create_from_discovery(self, target: str,
                              discovery_steps: list[dict[str, Any]],
                              ident_fields: dict[str, tuple[str, str]]) -> str:
        """Tạo/cập nhật profile từ kết quả discovery 7 bước. Idempotent theo target."""
        fields: dict[str, dict[str, str]] = {
            f: {"value": "", "status": UNKNOWN} for f in PROFILE_FIELDS
        }
        for name, (value, status) in (ident_fields or {}).items():
            if name in fields and status in FIELD_STATUSES:
                fields[name] = {"value": str(value), "status": status}
        # Từ discovery: thao tác được → Operational_Status Observed; không → Not_Accessible
        step1 = next((s for s in discovery_steps if s["step"] == "DISCOVERY"), None)
        if step1:
            ok = step1["status"] == "DONE"
            fields["Operational_Status"] = {
                "value": "REACHABLE" if ok else "UNREACHABLE",
                "status": "Observed" if step1["status"] in ("DONE", "PARTIAL") else "Not_Accessible",
            }
        # Security/Trust mặc định trung thực: chưa audit → Unknown
        fields.setdefault("Trust_Level", {"value": "UNKNOWN", "status": UNKNOWN})
        fields.setdefault("Risk_Score", {"value": "0", "status": UNKNOWN})
        fields["Last_Inspection"] = {"value": _now(), "status": VERIFIED}
        ev_refs = [e for s in discovery_steps for e in s.get("evidence", [])]
        fields["Evidence_References"] = {
            "value": "; ".join(ev_refs[:8]), "status": OBSERVED}
        assessment = ("Internal Architecture Inspection"
                      if all(s["status"] == "DONE"
                             for s in discovery_steps[:3])
                      else "External Behavioral Assessment")
        fields["Known_Limitations"] = {
            "value": assessment, "status": OBSERVED}

        now = _now()
        profile_id = f"uap_{abs(hash(target)) % 10_000_000:07d}"
        with self._connect() as conn:
            row = conn.execute(
                "SELECT profile_id FROM agent_profiles WHERE target=?",
                (target,)).fetchone()
            if row:
                profile_id = row["profile_id"]
                conn.execute(
                    "UPDATE agent_profiles SET updated_at=?, fields_json=?,"
                    " assessment_type=?, discovery_json=? WHERE target=?",
                    (now, json.dumps(fields, ensure_ascii=False), assessment,
                     json.dumps(discovery_steps, ensure_ascii=False), target))
            else:
                conn.execute(
                    "INSERT INTO agent_profiles (profile_id, target, created_at,"
                    " updated_at, fields_json, assessment_type, discovery_json)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (profile_id, target, now, now,
                     json.dumps(fields, ensure_ascii=False), assessment,
                     json.dumps(discovery_steps, ensure_ascii=False)))
        return profile_id

    def get(self, target_or_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM agent_profiles WHERE target=? OR profile_id=?",
                (target_or_id, target_or_id)).fetchone()
            if row is None:
                return None
            return {
                "profile_id": row["profile_id"], "target": row["target"],
                "created_at": row["created_at"], "updated_at": row["updated_at"],
                "assessment_type": row["assessment_type"],
                "fields": json.loads(row["fields_json"]),
            }

    def list_profiles(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT profile_id, target, updated_at, assessment_type"
                " FROM agent_profiles ORDER BY updated_at DESC").fetchall()
            return [dict(r) for r in rows]

    def set_field(self, target_or_id: str, field: str, value: str,
                  status: str) -> bool:
        """Cập nhật 1 trường — status phải trung thực (không 'Verified' suông)."""
        if field not in PROFILE_FIELDS:
            raise ValueError(f"trường không hợp lệ: {field}")
        if status not in FIELD_STATUSES:
            raise ValueError(f"trạng thái không hợp lệ: {status}")
        prof = self.get(target_or_id)
        if prof is None:
            return False
        fields = prof["fields"]
        fields[field] = {"value": str(value), "status": status}
        with self._connect() as conn:
            conn.execute(
                "UPDATE agent_profiles SET fields_json=?, updated_at=?"
                " WHERE profile_id=?",
                (json.dumps(fields, ensure_ascii=False), _now(),
                 prof["profile_id"]))
        return True

    def completeness(self, target_or_id: str) -> dict[str, int]:
        """Đếm trường theo trạng thái — đánh giá hồ sơ đã chắc chắn đến đâu."""
        prof = self.get(target_or_id)
        if prof is None:
            return {}
        counts = {s: 0 for s in FIELD_STATUSES}
        for f in prof["fields"].values():
            counts[f["status"]] = counts.get(f["status"], 0) + 1
        return counts
