"""Target State Verification Engine for Universal Software Integration."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from quan_ai_brain.contract.models import EvidenceRecord
from quan_ai_brain.integration.adapter import BaseConnectorAdapter, ConnectorResponse


class ExecutionStage(str, Enum):
    """Five-tier execution verification stages defined in Master Prompt V6 Section VII.4."""
    COMMAND_SENT = "COMMAND_SENT"          # Lệnh đã được dispatch
    ACK_RECEIVED = "ACK_RECEIVED"          # Đã nhận phản hồi kỹ thuật từ tool/HTTP
    STATE_CHANGED = "STATE_CHANGED"        # Trạng thái hệ thống đích đã thay đổi
    RESULT_VERIFIED = "RESULT_VERIFIED"    # Kết quả đã được xác minh bằng bằng chứng độc lập
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"    # Chưa xác định được kết quả (fail-closed)


@dataclass
class VerificationDossier:
    """Complete evidence dossier validating the true outcome of an integration operation."""
    stage: ExecutionStage
    verified: bool
    target_system: str
    operation_id: str
    tool_ack_ok: bool
    target_state_query_ok: bool
    target_state_observed: Any = None
    evidence_records: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["stage"] = self.stage.value
        return res


class ResultVerifier:
    """Verifies actual state change on target software rather than trusting tool ACK alone."""

    def __init__(self, workspace: Any = None) -> None:
        self.workspace = workspace

    def verify_operation_result(
        self,
        adapter: BaseConnectorAdapter,
        operation_id: str,
        params: dict[str, Any],
        response: ConnectorResponse,
    ) -> VerificationDossier:
        """Conduct independent target state verification."""
        # 1. Evaluate tool technical acknowledgment
        if not response.success:
            return VerificationDossier(
                stage=ExecutionStage.OUTCOME_UNKNOWN,
                verified=False,
                target_system=adapter.manifest.system_id,
                operation_id=operation_id,
                tool_ack_ok=False,
                target_state_query_ok=False,
                notes=f"Tool execution returned error: {response.error}",
            )

        # 2. Call adapter's target state verification logic
        try:
            verif_res = adapter.verify_target_state(operation_id, params, response)
        except Exception as exc:
            return VerificationDossier(
                stage=ExecutionStage.ACK_RECEIVED,
                verified=False,
                target_system=adapter.manifest.system_id,
                operation_id=operation_id,
                tool_ack_ok=True,
                target_state_query_ok=False,
                notes=f"Target state verification threw exception: {exc}",
            )

        # 3. Construct evidence record
        evidence_entry = {
            "evidence_id": f"ev_{adapter.manifest.system_id}_{operation_id}_{int(datetime.now(timezone.utc).timestamp())}",
            "method": verif_res.method,
            "observed": verif_res.target_state_observed,
            "evidence_payload": verif_res.evidence_payload,
            "verified": verif_res.verified,
        }

        if verif_res.verified:
            stage = ExecutionStage.RESULT_VERIFIED
        else:
            stage = ExecutionStage.ACK_RECEIVED  # ACK received but target state unverified!

        return VerificationDossier(
            stage=stage,
            verified=verif_res.verified,
            target_system=adapter.manifest.system_id,
            operation_id=operation_id,
            tool_ack_ok=True,
            target_state_query_ok=True,
            target_state_observed=verif_res.target_state_observed,
            evidence_records=[evidence_entry],
            notes=verif_res.notes or ("State verified successfully" if verif_res.verified else "Verification criteria unmet"),
        )
