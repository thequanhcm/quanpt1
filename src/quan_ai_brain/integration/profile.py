"""System Knowledge Profile and Topology Mapping."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class KnowledgeLevel(str, Enum):
    """3 knowledge confidence levels defined in Master Prompt V6 Section V."""
    OBSERVED = "OBSERVED"  # Directly observed behavior or response
    VERIFIED = "VERIFIED"  # Verified by formal evidence and regression tests
    INFERRED = "INFERRED"  # Inferred from documentation or schemas, not yet fully verified


@dataclass
class SystemKnowledgeProfile:
    """Structured knowledge profile of an integrated software system."""
    system_id: str
    system_name: str
    version: str
    environment: str
    owner_organization: str
    documentation_sources: list[str] = field(default_factory=list)
    connector_id: str = ""
    discovered_endpoints: list[dict[str, Any]] = field(default_factory=list)
    supported_read_ops: list[str] = field(default_factory=list)
    supported_write_ops: list[str] = field(default_factory=list)
    forbidden_ops: list[str] = field(default_factory=list)
    approval_conditions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    technical_limits: dict[str, Any] = field(default_factory=dict)
    test_evidence_refs: list[str] = field(default_factory=list)
    last_verified_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence_score: float = 1.0
    verification_status: KnowledgeLevel = KnowledgeLevel.OBSERVED
    is_conflicted: bool = False
    conflict_notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["verification_status"] = self.verification_status.value
        return res

    def mark_verified(self, evidence_ref: str, confidence: float = 1.0) -> None:
        """Promote profile to VERIFIED when supported by empirical evidence."""
        self.verification_status = KnowledgeLevel.VERIFIED
        self.confidence_score = min(max(confidence, 0.0), 1.0)
        if evidence_ref and evidence_ref not in self.test_evidence_refs:
            self.test_evidence_refs.append(evidence_ref)
        self.last_verified_at_utc = datetime.now(timezone.utc).isoformat()

    def mark_conflict(self, notes: str) -> None:
        """Flag contradictory observations without guessing ground truth."""
        self.is_conflicted = True
        self.conflict_notes = notes
        self.confidence_score = min(self.confidence_score, 0.3)
        self.verification_status = KnowledgeLevel.INFERRED

    def format_summary(self) -> str:
        """Format an explainable summary for prompt context builders."""
        status_line = f"Status: {self.verification_status.value} (Confidence: {self.confidence_score:.2f})"
        if self.is_conflicted:
            status_line += f" [CONFLICT DETECTED: {self.conflict_notes}]"
        lines = [
            f"=== SYSTEM PROFILE: {self.system_name} ({self.system_id} v{self.version}) ===",
            status_line,
            f"Environment: {self.environment} | Owner: {self.owner_organization}",
            f"Read Operations ({len(self.supported_read_ops)}): {', '.join(self.supported_read_ops) or 'None'}",
            f"Write Operations ({len(self.supported_write_ops)}): {', '.join(self.supported_write_ops) or 'None'}",
            f"Forbidden Operations: {', '.join(self.forbidden_ops) or 'None'}",
            f"Dependencies: {', '.join(self.dependencies) or 'None'}",
            f"Last Verified: {self.last_verified_at_utc}",
        ]
        return "\n".join(lines)
