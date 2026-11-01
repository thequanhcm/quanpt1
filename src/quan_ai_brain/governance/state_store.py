"""Persistent SQLite Governance State Store for QUAN AI BRAIN.

Sprint 5: Persistent Governance State + Audit Ledger.
Stores approvals, delegation grants, replay-prevention nonces, emergency state,
and governance event logs.

Principle:
Fail-closed on corrupted, missing, or unreadable state.
No secret values or unredacted credentials stored.
Thread-safe and atomic multi-process transaction safe.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import TYPE_CHECKING, Any
import uuid
from datetime import datetime, timezone
from dataclasses import asdict, dataclass

from quan_ai_brain.core.redaction import redact_value
from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.tools.path_guard import PathGuard

if TYPE_CHECKING:
    from quan_ai_brain.tools.approval import ApprovalRequest, ApprovalStatus, OwnerApproval
    from quan_ai_brain.tools.delegation import DelegationGrant, GrantStatus


CURRENT_SCHEMA_VERSION = 1


class GovernanceStateCorruptError(RuntimeError):
    """Raised when the governance database structure, version, or state cannot be safely verified."""
    pass


class ReplayDetectedError(RuntimeError):
    """Raised when a nonce or single-use token replay attempt is detected."""
    pass


@dataclass
class EmergencyStateRecord:
    """Persistent representation of emergency STOP/FREEZE state."""

    id: str
    state: str  # "normal", "stop", "freeze"
    scope: str
    reason: str
    activated_by: str
    activated_at_utc: str
    cleared_at_utc: str | None = None
    audit_ref: str = ""

    @property
    def activated_at(self) -> str:
        return self.activated_at_utc

    @property
    def cleared_at(self) -> str | None:
        return self.cleared_at_utc

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GovernanceStateStore:
    """Persistent SQLite database manager for governance state.

    Ensures that emergency states, approval consumptions, replay nonces,
    and delegation revocations strictly persist across process restarts.
    """

    def __init__(
        self,
        db_path: str | Path = ":memory:",
        workspace: str | Path | None = None,
        auto_create: bool = True,
    ) -> None:
        self._lock = RLock()
        self._is_memory = str(db_path) == ":memory:"
        self.workspace = Path(workspace).resolve() if workspace else None

        if self._is_memory:
            self.db_path = ":memory:"
        else:
            requested = Path(db_path)
            if self.workspace is not None:
                guard = PathGuard(self.workspace)
                if requested.is_absolute():
                    try:
                        resolved = requested.resolve(strict=False)
                        resolved.relative_to(guard.workspace)
                    except ValueError as exc:
                        raise ValueError("Database path must be inside the authorized workspace") from exc
                    self.db_path = resolved
                else:
                    self.db_path = guard.resolve(requested)
            else:
                self.db_path = requested.resolve(strict=False)

            if not self.db_path.exists() and not auto_create:
                raise GovernanceStateCorruptError(
                    f"Governance database '{self.db_path}' does not exist and auto_create is False"
                )

            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database pragmas, verify integrity, and create schema if needed."""
        with self._lock:
            try:
                self._connection.execute("PRAGMA foreign_keys = ON;")
                if not self._is_memory:
                    self._connection.execute("PRAGMA journal_mode = WAL;")
                    self._connection.execute("PRAGMA synchronous = NORMAL;")

                # Check if schema exists
                cursor = self._connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_info';"
                )
                table_exists = cursor.fetchone() is not None

                if not table_exists:
                    self._create_schema()
                else:
                    self.verify_integrity()
            except sqlite3.DatabaseError as exc:
                raise GovernanceStateCorruptError(
                    f"Governance database at '{self.db_path}' is corrupted or unreadable: {exc}"
                ) from exc

    def _create_schema(self) -> None:
        """Create versioned governance schema."""
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_info (
                    version INTEGER PRIMARY KEY,
                    applied_at_utc TEXT NOT NULL,
                    description TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS emergency_states (
                    id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'global',
                    reason TEXT NOT NULL DEFAULT '',
                    activated_by TEXT NOT NULL DEFAULT '',
                    activated_at_utc TEXT NOT NULL,
                    cleared_at_utc TEXT,
                    audit_ref TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_emergency_scope ON emergency_states(scope, state);

                CREATE TABLE IF NOT EXISTS approval_requests (
                    request_id TEXT PRIMARY KEY,
                    tool_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    resource_scope TEXT NOT NULL,
                    risk_level INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    goal TEXT NOT NULL DEFAULT '',
                    created_at_utc TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_req_fp ON approval_requests(fingerprint);

                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    approver TEXT NOT NULL,
                    tool_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    resource_scope TEXT NOT NULL,
                    risk_level INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    granted_at_utc TEXT NOT NULL,
                    expires_at_utc TEXT,
                    consumed INTEGER NOT NULL DEFAULT 0,
                    consumed_at_utc TEXT,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    revocation_reason TEXT NOT NULL DEFAULT '',
                    auth_method TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    audit_ref TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_app_fp ON approvals(fingerprint);
                CREATE INDEX IF NOT EXISTS idx_app_consumed ON approvals(consumed);
                CREATE INDEX IF NOT EXISTS idx_app_revoked ON approvals(revoked);

                CREATE TABLE IF NOT EXISTS delegation_grants (
                    grant_id TEXT PRIMARY KEY,
                    owner_identity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    allowed_tool_ids_json TEXT NOT NULL,
                    allowed_action_types_json TEXT NOT NULL,
                    allowed_resource_scope TEXT NOT NULL,
                    allowed_project_scope TEXT NOT NULL,
                    maximum_risk_level INTEGER NOT NULL,
                    valid_from_utc TEXT NOT NULL,
                    expires_at_utc TEXT NOT NULL,
                    max_calls INTEGER,
                    calls_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_by TEXT NOT NULL DEFAULT '',
                    approval_reference TEXT NOT NULL DEFAULT '',
                    audit_reference TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_grant_status ON delegation_grants(status);

                CREATE TABLE IF NOT EXISTS consumed_nonces (
                    nonce TEXT PRIMARY KEY,
                    approval_id TEXT NOT NULL,
                    consumed_at_utc TEXT NOT NULL,
                    audit_ref TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS governance_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    risk_level INTEGER,
                    outcome TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_gov_events_ts ON governance_events(timestamp_utc);
                """
            )
            now_ts = datetime.now(timezone.utc).isoformat()
            self._connection.execute(
                "INSERT INTO schema_info (version, applied_at_utc, description) VALUES (?, ?, ?);",
                (CURRENT_SCHEMA_VERSION, now_ts, "Sprint 5 initial persistent governance schema"),
            )

            # Insert default normal emergency state
            self._connection.execute(
                """
                INSERT INTO emergency_states (id, state, scope, reason, activated_by, activated_at_utc)
                VALUES ('global', 'normal', 'global', 'System initialized in normal state', 'SYSTEM', ?);
                """,
                (now_ts,),
            )

    def verify_integrity(self) -> None:
        """Verify schema version, table existence, and SQLite structural integrity."""
        with self._lock:
            # 1. SQLite integrity check
            cursor = self._connection.execute("PRAGMA integrity_check;")
            row = cursor.fetchone()
            if not row or row[0] != "ok":
                raise GovernanceStateCorruptError(f"Governance database failed SQLite integrity check: {row}")

            # 2. Schema info version check
            try:
                cursor = self._connection.execute("SELECT version FROM schema_info ORDER BY version DESC LIMIT 1;")
                ver_row = cursor.fetchone()
                if not ver_row or ver_row["version"] != CURRENT_SCHEMA_VERSION:
                    raise GovernanceStateCorruptError(
                        f"Unsupported governance schema version: expected {CURRENT_SCHEMA_VERSION}, got {ver_row['version'] if ver_row else None}"
                    )
            except sqlite3.OperationalError as exc:
                raise GovernanceStateCorruptError("schema_info table is unreadable or corrupted") from exc

            # 3. Mandatory tables verification
            required_tables = {
                "schema_info",
                "emergency_states",
                "approval_requests",
                "approvals",
                "delegation_grants",
                "consumed_nonces",
                "governance_events",
            }
            cursor = self._connection.execute("SELECT name FROM sqlite_master WHERE type='table';")
            found_tables = {r["name"] for r in cursor.fetchall()}
            missing = required_tables - found_tables
            if missing:
                raise GovernanceStateCorruptError(f"Governance database is missing mandatory tables: {missing}")

    # =========================================================================
    # Emergency State Management
    # =========================================================================

    def set_emergency_state(
        self,
        state: str,
        reason: str = "",
        activated_by: str = "OWNER",
        scope: str = "global",
        audit_ref: str = "",
    ) -> EmergencyStateRecord:
        """Set persistent emergency state (STOP, FREEZE, or NORMAL)."""
        clean_state = state.strip().lower()
        if clean_state not in ("normal", "stop", "freeze"):
            raise ValueError(f"Invalid emergency state '{state}'; must be 'normal', 'stop', or 'freeze'")

        now_ts = datetime.now(timezone.utc).isoformat()
        rec_id = f"{scope}_{clean_state}_{uuid.uuid4().hex[:8]}" if clean_state != "normal" else scope

        with self._lock, self._connection:
            # Clear previous active emergency states for this scope if setting normal
            if clean_state == "normal":
                self._connection.execute(
                    "UPDATE emergency_states SET cleared_at_utc = ? WHERE scope = ? AND state IN ('stop', 'freeze') AND cleared_at_utc IS NULL;",
                    (now_ts, scope),
                )
                self._connection.execute(
                    """
                    INSERT INTO emergency_states (id, state, scope, reason, activated_by, activated_at_utc, audit_ref)
                    VALUES (?, 'normal', ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        state = 'normal',
                        reason = excluded.reason,
                        activated_by = excluded.activated_by,
                        activated_at_utc = excluded.activated_at_utc,
                        audit_ref = excluded.audit_ref;
                    """,
                    (scope, scope, reason, activated_by, now_ts, audit_ref),
                )
            else:
                self._connection.execute(
                    """
                    INSERT INTO emergency_states (id, state, scope, reason, activated_by, activated_at_utc, audit_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (rec_id, clean_state, scope, reason, activated_by, now_ts, audit_ref),
                )

            # Record governance audit event
            self._record_event_unlocked(
                event_type="governance.emergency_state_changed",
                entity_type="emergency_state",
                entity_id=rec_id,
                details={"state": clean_state, "reason": reason, "scope": scope, "activated_by": activated_by},
                risk_level=5 if clean_state == "stop" else (4 if clean_state == "freeze" else 0),
                outcome=clean_state,
            )

        return EmergencyStateRecord(
            id=rec_id,
            state=clean_state,
            scope=scope,
            reason=reason,
            activated_by=activated_by,
            activated_at_utc=now_ts,
            audit_ref=audit_ref,
        )

    def get_emergency_state(self, scope: str = "global") -> EmergencyStateRecord:
        """Fetch current effective emergency state for a given scope."""
        with self._lock:
            # Check for any active STOP first (highest priority)
            cursor = self._connection.execute(
                """
                SELECT * FROM emergency_states
                WHERE scope = ? AND state = 'stop' AND cleared_at_utc IS NULL
                ORDER BY activated_at_utc DESC LIMIT 1;
                """,
                (scope,),
            )
            row = cursor.fetchone()
            if row:
                return EmergencyStateRecord(**dict(row))

            # Check for any active FREEZE
            cursor = self._connection.execute(
                """
                SELECT * FROM emergency_states
                WHERE scope = ? AND state = 'freeze' AND cleared_at_utc IS NULL
                ORDER BY activated_at_utc DESC LIMIT 1;
                """,
                (scope,),
            )
            row = cursor.fetchone()
            if row:
                return EmergencyStateRecord(**dict(row))

            # No active STOP or FREEZE -> Fetch the active normal record
            cursor = self._connection.execute(
                """
                SELECT * FROM emergency_states
                WHERE scope = ? AND state = 'normal'
                ORDER BY activated_at_utc DESC LIMIT 1;
                """,
                (scope,),
            )
            row = cursor.fetchone()
            if row:
                return EmergencyStateRecord(**dict(row))

            # Fallback
            return EmergencyStateRecord(
                id="default",
                state="normal",
                scope=scope,
                reason="Default baseline",
                activated_by="SYSTEM",
                activated_at_utc=datetime.now(timezone.utc).isoformat(),
            )

    # =========================================================================
    # Approval & Request Management
    # =========================================================================

    def save_request(self, request: ApprovalRequest) -> None:
        """Persist or update an ApprovalRequest."""
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO approval_requests (
                    request_id, tool_id, action, params_json, resource_scope,
                    risk_level, fingerprint, status, goal, created_at_utc, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(request_id) DO UPDATE SET
                    status = excluded.status,
                    metadata_json = excluded.metadata_json;
                """,
                (
                    request.request_id,
                    request.tool_id,
                    request.action,
                    json.dumps(redact_value(request.params), ensure_ascii=False),
                    request.resource_scope,
                    int(request.risk_level),
                    request.fingerprint,
                    request.status.value,
                    request.goal,
                    request.created_at,
                    json.dumps(redact_value(request.metadata), ensure_ascii=False),
                ),
            )

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Retrieve an ApprovalRequest from persistent store."""
        with self._lock:
            cursor = self._connection.execute(
                "SELECT * FROM approval_requests WHERE request_id = ?;", (request_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            from quan_ai_brain.tools.approval import ApprovalRequest, ApprovalStatus
            return ApprovalRequest(
                request_id=row["request_id"],
                tool_id=row["tool_id"],
                action=row["action"],
                params=json.loads(row["params_json"]),
                resource_scope=row["resource_scope"],
                risk_level=RiskLevel(row["risk_level"]),
                fingerprint=row["fingerprint"],
                status=ApprovalStatus(row["status"]),
                created_at=row["created_at_utc"],
                goal=row["goal"],
                metadata=json.loads(row["metadata_json"]),
            )

    def save_approval(self, approval: OwnerApproval, auth_method: str = "") -> None:
        """Persist or update an OwnerApproval."""
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO approvals (
                    approval_id, request_id, approver, tool_id, action, params_json,
                    resource_scope, risk_level, fingerprint, status, granted_at_utc,
                    expires_at_utc, consumed, consumed_at_utc, revoked,
                    revocation_reason, auth_method, notes, audit_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(approval_id) DO UPDATE SET
                    status = excluded.status,
                    consumed = excluded.consumed,
                    consumed_at_utc = excluded.consumed_at_utc,
                    revoked = excluded.revoked,
                    revocation_reason = excluded.revocation_reason,
                    notes = excluded.notes;
                """,
                (
                    approval.approval_id,
                    approval.request_id,
                    approval.approver,
                    approval.tool_id,
                    approval.action,
                    json.dumps(redact_value(approval.params), ensure_ascii=False),
                    approval.resource_scope,
                    int(approval.risk_level),
                    approval.fingerprint,
                    approval.status.value,
                    approval.granted_at,
                    approval.expires_at,
                    1 if approval.consumed else 0,
                    datetime.now(timezone.utc).isoformat() if approval.consumed else None,
                    1 if approval.revoked else 0,
                    "",
                    auth_method,
                    approval.notes,
                    "",
                ),
            )

    def get_approval(self, approval_id: str) -> OwnerApproval | None:
        """Retrieve an OwnerApproval from persistent store."""
        with self._lock:
            cursor = self._connection.execute(
                "SELECT * FROM approvals WHERE approval_id = ?;", (approval_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            from quan_ai_brain.tools.approval import ApprovalStatus, OwnerApproval
            return OwnerApproval(
                approval_id=row["approval_id"],
                request_id=row["request_id"],
                approver=row["approver"],
                tool_id=row["tool_id"],
                action=row["action"],
                params=json.loads(row["params_json"]),
                resource_scope=row["resource_scope"],
                risk_level=RiskLevel(row["risk_level"]),
                fingerprint=row["fingerprint"],
                granted_at=row["granted_at_utc"],
                expires_at=row["expires_at_utc"],
                consumed=bool(row["consumed"]),
                revoked=bool(row["revoked"]),
                status=ApprovalStatus(row["status"]),
                notes=row["notes"],
            )

    def consume_approval(self, approval_id: str) -> bool:
        """Atomically mark approval as consumed (one-time use).

        Returns True if successfully consumed by this call;
        Returns False if already consumed, revoked, or non-existent (prevents race-condition reuse).
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE approvals
                SET consumed = 1, status = 'completed', consumed_at_utc = ?
                WHERE approval_id = ? AND consumed = 0 AND revoked = 0;
                """,
                (now_ts, approval_id),
            )
            success = cursor.rowcount > 0
            if success:
                self._record_event_unlocked(
                    event_type="governance.approval_consumed",
                    entity_type="approval",
                    entity_id=approval_id,
                    details={"consumed_at": now_ts},
                    outcome="consumed",
                )
            return success

    def revoke_approval(self, approval_id: str, reason: str = "") -> bool:
        """Mark an approval as revoked."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE approvals
                SET revoked = 1, status = 'revoked', revocation_reason = ?
                WHERE approval_id = ? AND revoked = 0;
                """,
                (reason, approval_id),
            )
            success = cursor.rowcount > 0
            if success:
                self._record_event_unlocked(
                    event_type="governance.approval_revoked",
                    entity_type="approval",
                    entity_id=approval_id,
                    details={"revocation_reason": reason},
                    outcome="revoked",
                )
            return success

    # =========================================================================
    # Delegation Grant Management
    # =========================================================================

    def save_grant(self, grant: DelegationGrant) -> None:
        """Persist or update a DelegationGrant."""
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO delegation_grants (
                    grant_id, owner_identity, description, allowed_tool_ids_json,
                    allowed_action_types_json, allowed_resource_scope, allowed_project_scope,
                    maximum_risk_level, valid_from_utc, expires_at_utc, max_calls,
                    calls_count, status, created_by, approval_reference, audit_reference,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(grant_id) DO UPDATE SET
                    calls_count = excluded.calls_count,
                    status = excluded.status,
                    metadata_json = excluded.metadata_json;
                """,
                (
                    grant.grant_id,
                    grant.owner_identity,
                    grant.description,
                    json.dumps(grant.allowed_tool_ids),
                    json.dumps(grant.allowed_action_types),
                    grant.allowed_resource_scope,
                    grant.allowed_project_scope,
                    int(grant.maximum_risk_level),
                    grant.valid_from,
                    grant.expires_at,
                    grant.max_calls,
                    grant.calls_count,
                    grant.status.value,
                    grant.created_by,
                    grant.approval_reference,
                    grant.audit_reference,
                    json.dumps(redact_value(grant.metadata), ensure_ascii=False),
                ),
            )

    def get_grant(self, grant_id: str) -> DelegationGrant | None:
        """Retrieve a DelegationGrant by ID."""
        with self._lock:
            cursor = self._connection.execute(
                "SELECT * FROM delegation_grants WHERE grant_id = ?;", (grant_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            from quan_ai_brain.tools.delegation import DelegationGrant, GrantStatus
            return DelegationGrant(
                grant_id=row["grant_id"],
                owner_identity=row["owner_identity"],
                description=row["description"],
                allowed_tool_ids=json.loads(row["allowed_tool_ids_json"]),
                allowed_action_types=json.loads(row["allowed_action_types_json"]),
                allowed_resource_scope=row["allowed_resource_scope"],
                allowed_project_scope=row["allowed_project_scope"],
                maximum_risk_level=RiskLevel(row["maximum_risk_level"]),
                valid_from=row["valid_from_utc"],
                expires_at=row["expires_at_utc"],
                max_calls=row["max_calls"],
                calls_count=row["calls_count"],
                status=GrantStatus(row["status"]),
                created_by=row["created_by"],
                approval_reference=row["approval_reference"],
                audit_reference=row["audit_reference"],
                metadata=json.loads(row["metadata_json"]),
            )

    def list_grants(self, status: GrantStatus | None = None) -> list[DelegationGrant]:
        """List grants from persistent store, optionally filtered by status."""
        with self._lock:
            if status is not None:
                cursor = self._connection.execute(
                    "SELECT * FROM delegation_grants WHERE status = ? ORDER BY valid_from_utc DESC;",
                    (status.value,),
                )
            else:
                cursor = self._connection.execute(
                    "SELECT * FROM delegation_grants ORDER BY valid_from_utc DESC;"
                )
            results = []
            from quan_ai_brain.tools.delegation import DelegationGrant, GrantStatus
            for row in cursor.fetchall():
                results.append(
                    DelegationGrant(
                        grant_id=row["grant_id"],
                        owner_identity=row["owner_identity"],
                        description=row["description"],
                        allowed_tool_ids=json.loads(row["allowed_tool_ids_json"]),
                        allowed_action_types=json.loads(row["allowed_action_types_json"]),
                        allowed_resource_scope=row["allowed_resource_scope"],
                        allowed_project_scope=row["allowed_project_scope"],
                        maximum_risk_level=RiskLevel(row["maximum_risk_level"]),
                        valid_from=row["valid_from_utc"],
                        expires_at=row["expires_at_utc"],
                        max_calls=row["max_calls"],
                        calls_count=row["calls_count"],
                        status=GrantStatus(row["status"]),
                        created_by=row["created_by"],
                        approval_reference=row["approval_reference"],
                        audit_reference=row["audit_reference"],
                        metadata=json.loads(row["metadata_json"]),
                    )
                )
            return results

    def revoke_grant(self, grant_id: str, reason: str = "") -> bool:
        """Revoke a delegation grant in persistent store."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE delegation_grants
                SET status = 'revoked'
                WHERE grant_id = ? AND status = 'active';
                """,
                (grant_id,),
            )
            success = cursor.rowcount > 0
            if success:
                self._record_event_unlocked(
                    event_type="governance.grant_revoked",
                    entity_type="delegation_grant",
                    entity_id=grant_id,
                    details={"revocation_reason": reason},
                    outcome="revoked",
                )
            return success

    def increment_grant_usage(self, grant_id: str) -> int:
        """Atomically increment the execution usage counter for a delegation grant."""
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE delegation_grants SET calls_count = calls_count + 1 WHERE grant_id = ?;",
                (grant_id,),
            )
            cursor = self._connection.execute(
                "SELECT calls_count FROM delegation_grants WHERE grant_id = ?;",
                (grant_id,),
            )
            row = cursor.fetchone()
            return row["calls_count"] if row else 0

    # =========================================================================
    # Replay Prevention (Nonces)
    # =========================================================================

    def record_nonce(self, nonce: str, approval_id: str, audit_ref: str = "") -> bool:
        """Record a single-use nonce.

        Returns True if the nonce was fresh and recorded.
        Returns False if the nonce has already been used (replay detected).
        """
        clean_nonce = nonce.strip()
        if not clean_nonce:
            raise ValueError("Nonce must not be empty")

        now_ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connection:
            try:
                self._connection.execute(
                    "INSERT INTO consumed_nonces (nonce, approval_id, consumed_at_utc, audit_ref) VALUES (?, ?, ?, ?);",
                    (clean_nonce, approval_id, now_ts, audit_ref),
                )
                return True
            except sqlite3.IntegrityError:
                # Replay attempt!
                self._record_event_unlocked(
                    event_type="governance.replay_detected",
                    entity_type="nonce",
                    entity_id=clean_nonce,
                    details={"approval_id": approval_id, "attempted_at": now_ts},
                    risk_level=4,
                    outcome="rejected_replay",
                )
                return False

    def is_nonce_consumed(self, nonce: str) -> bool:
        """Check whether a nonce has already been consumed."""
        with self._lock:
            cursor = self._connection.execute(
                "SELECT 1 FROM consumed_nonces WHERE nonce = ?;", (nonce.strip(),)
            )
            return cursor.fetchone() is not None

    # =========================================================================
    # Governance Audit Ledger
    # =========================================================================

    def _record_event_unlocked(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any],
        risk_level: int | None = None,
        outcome: str = "ok",
    ) -> str:
        """Internal helper to write a governance event during an existing lock/transaction."""
        evt_id = f"evt_{uuid.uuid4().hex[:12]}"
        now_ts = datetime.now(timezone.utc).isoformat()
        self._connection.execute(
            """
            INSERT INTO governance_events (
                event_id, event_type, timestamp_utc, entity_type, entity_id, details_json, risk_level, outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                evt_id,
                event_type,
                now_ts,
                entity_type,
                entity_id,
                json.dumps(redact_value(details), ensure_ascii=False),
                risk_level,
                outcome,
            ),
        )
        return evt_id

    def record_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any],
        risk_level: int | None = None,
        outcome: str = "ok",
    ) -> str:
        """Public method to record a governance audit event."""
        with self._lock, self._connection:
            return self._record_event_unlocked(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                risk_level=risk_level,
                outcome=outcome,
            )

    def query_events(self, entity_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Query recent governance audit events."""
        with self._lock:
            if entity_id:
                cursor = self._connection.execute(
                    "SELECT * FROM governance_events WHERE entity_id = ? ORDER BY timestamp_utc DESC LIMIT ?;",
                    (entity_id, limit),
                )
            else:
                cursor = self._connection.execute(
                    "SELECT * FROM governance_events ORDER BY timestamp_utc DESC LIMIT ?;",
                    (limit,),
                )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def close(self) -> None:
        """Close SQLite database connection safely."""
        with self._lock:
            self._connection.close()

    def __enter__(self) -> GovernanceStateStore:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
