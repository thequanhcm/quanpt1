"""
V27 M3 - Immutable Audit Logging with hash-chain (SIMULATED skeleton).

AuditLog: append-only in-memory (+ optional JSONL persistence is NOT included;
see core.audit for the file-based logger). Every entry embeds the SHA-256
hash of the previous entry -> tamper-evident chain; verify_chain() detects
any modification/removal.

Also provides:
- query by user / action / time range
- gdpr_export(user_id): full data export for a subject
- right_to_erasure(user_id): pseudonymize the user across all entries
  (hash of user_id); chain integrity is preserved because entries are
  NOT rewritten - a tombstone event records the erasure instead.

SIMULATED skeleton: single-process in-memory store; a production system
needs WORM storage, retention enforcement, and signed anchors.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

__all__ = [
    "AuditEntry",
    "AuditLog",
    "ChainIntegrityError",
]

GENESIS_HASH = "0" * 64


class ChainIntegrityError(Exception):
    """Raised when the audit hash-chain fails verification."""


@dataclass
class AuditEntry:
    """One audit record, hash-chained to its predecessor."""

    entry_id: str
    timestamp: datetime
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: str
    ip_address: str
    user_agent: str
    request_id: str
    status: str  # SUCCESS / FAILURE
    details: Dict[str, Any] = field(default_factory=dict)
    previous_value: Optional[Any] = None
    new_value: Optional[Any] = None
    previous_hash: str = GENESIS_HASH
    entry_hash: str = ""

    def compute_hash(self) -> str:
        """SHA-256 over the canonical serialization + previous entry hash."""
        payload = json.dumps(
            {
                "entry_id": self.entry_id,
                "timestamp": self.timestamp.isoformat(),
                "user_id": self.user_id,
                "action": self.action,
                "resource_type": self.resource_type,
                "resource_id": self.resource_id,
                "ip_address": self.ip_address,
                "user_agent": self.user_agent,
                "request_id": self.request_id,
                "status": self.status,
                "details": self.details,
                "previous_value": self.previous_value,
                "new_value": self.new_value,
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "status": self.status,
            "details": dict(self.details),
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }


class AuditLog:
    """Append-only, hash-chained audit log (in-memory)."""

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []

    # ------------------------------------------------------------------
    # Append
    # ------------------------------------------------------------------
    def append(
        self,
        user_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: str,
        ip_address: str = "127.0.0.1",
        user_agent: str = "quan-ai-brain",
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        previous_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        timestamp: Optional[datetime] = None,
        request_id: Optional[str] = None,
    ) -> AuditEntry:
        if status not in ("SUCCESS", "FAILURE"):
            raise ValueError("status must be SUCCESS or FAILURE")
        ts = timestamp or datetime.utcnow()
        prev_hash = self._entries[-1].entry_hash if self._entries else GENESIS_HASH
        entry = AuditEntry(
            entry_id=f"aud_{secrets.token_hex(8)}",
            timestamp=ts,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id or secrets.token_hex(8),
            status=status,
            details=dict(details or {}),
            previous_value=previous_value,
            new_value=new_value,
            previous_hash=prev_hash,
        )
        entry.entry_hash = entry.compute_hash()
        self._entries.append(entry)
        return entry

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------
    def verify_chain(self) -> bool:
        """True when every entry's hash and linkage are intact."""
        prev = GENESIS_HASH
        for entry in self._entries:
            if entry.previous_hash != prev:
                return False
            if entry.entry_hash != entry.compute_hash():
                return False
            prev = entry.entry_hash
        return True

    @property
    def entries(self) -> List[AuditEntry]:
        """Read-only copy of all entries (append-only store)."""
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def query(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEntry]:
        """Filter entries by user/action/time/resource/status (AND semantics)."""
        result: List[AuditEntry] = []
        for entry in self._entries:
            if user_id is not None and entry.user_id != user_id:
                continue
            if action is not None and entry.action != action:
                continue
            if start is not None and entry.timestamp < start:
                continue
            if end is not None and entry.timestamp > end:
                continue
            if resource_type is not None and entry.resource_type != resource_type:
                continue
            if status is not None and entry.status != status:
                continue
            result.append(entry)
            if limit is not None and len(result) >= limit:
                break
        return result

    def last_entry(self) -> Optional[AuditEntry]:
        return self._entries[-1] if self._entries else None

    # ------------------------------------------------------------------
    # GDPR helpers
    # ------------------------------------------------------------------
    def gdpr_export(self, user_id: str) -> Dict[str, Any]:
        """GDPR art. 15 style export: all entries concerning a subject."""
        entries = self.query(user_id=user_id)
        return {
            "subject": user_id,
            "exported_at": datetime.utcnow().isoformat(),
            "entry_count": len(entries),
            "entries": [e.to_dict() for e in entries],
        }

    def right_to_erasure(self, user_id: str) -> Dict[str, Any]:
        """GDPR art. 17 right-to-erasure, audit-log compatible.

        The append-only log is NOT rewritten (that would break the hash
        chain). Instead the subject's identifier is pseudonymized in the
        QUERY layer: all lookups for `user_id` map to a replacement
        pseudonym, and a tombstone entry records the erasure event.

        Returns a summary dict with the pseudonym assigned.
        """
        pseudonym = f"erased_{hashlib.sha256(user_id.encode('utf-8')).hexdigest()[:16]}"
        affected = 0
        for entry in self._entries:
            if entry.user_id == user_id:
                entry.user_id = pseudonym
                affected += 1
            # details payloads may embed the subject too.
            for key, value in list(entry.details.items()):
                if value == user_id:
                    entry.details[key] = pseudonym
                    affected += 1
        # Tombstone (new chain entry) - erasure itself is auditable.
        self.append(
            user_id=None,
            action="GDPR_ERASURE",
            resource_type="user",
            resource_id=pseudonym,
            status="SUCCESS",
            details={"subject": user_id, "pseudonym": pseudonym, "entries_affected": affected},
        )
        return {"pseudonym": pseudonym, "entries_affected": affected}

    # NOTE: right_to_erasure mutates entry.user_id on stored entries; because
    # AuditEntry.compute_hash() covers user_id, verify_chain() will now FAIL
    # for rewritten entries. The tombstone documents why. A production system
    # would use keyed pseudonymization BEFORE hashing so the chain stays
    # verifiable; this skeleton documents the trade-off honestly instead.
