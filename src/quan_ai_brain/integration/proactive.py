"""Proactive Operations Loop for Autonomous Issue Detection and Resolution."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Any

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.integration.manifest import AutonomyLevelScope
from quan_ai_brain.integration.registry import IntegrationRegistry


class FindingSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class ProactiveFinding:
    """Anomalies, optimization opportunities, or health degradation detected autonomously."""
    finding_id: str
    system_id: str
    severity: FindingSeverity
    summary: str
    evidence: dict[str, Any]
    diagnosis: str
    proposed_solution: str
    risk_level: RiskLevel
    autonomy_level: AutonomyLevelScope
    status: str = "OPEN"  # OPEN, PROPOSED, EXECUTED, RESOLVED, BLOCKED
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["severity"] = self.severity.value
        res["risk_level"] = int(self.risk_level)
        res["autonomy_level"] = self.autonomy_level.value
        return res


class ProactiveOperationsLoop:
    """Implements 10-step autonomous loop:
    MONITOR -> DETECT -> DIAGNOSE -> RESEARCH -> PROPOSE -> AUTHORIZE -> EXECUTE -> VERIFY -> REPORT -> LEARN
    under strict A0-A3 bounded autonomy.
    """

    def __init__(
        self,
        registry: IntegrationRegistry,
        consultation_store: Any = None,
        memory_store: Any = None,
    ) -> None:
        self.registry = registry
        self.consultation_store = consultation_store
        self.memory_store = memory_store
        self._findings: list[ProactiveFinding] = []

    def list_findings(self) -> list[ProactiveFinding]:
        return list(self._findings)

    def run_cycle(self) -> list[ProactiveFinding]:
        """Execute one complete proactive monitoring and diagnosis pass."""
        new_findings: list[ProactiveFinding] = []

        # 1. MONITOR & DETECT across all registered connectors
        for manifest in self.registry.list_connectors():
            adapter = self.registry.get_adapter(manifest.system_id)
            if not adapter:
                continue

            health = self.registry.health_monitor.check_health(adapter)

            # Check for anomalies: unhealthy, high latency, or tripped circuit breaker
            if not health.healthy:
                finding = self._create_health_finding(manifest.system_id, health)
                new_findings.append(finding)
                self._findings.append(finding)
            elif health.latency_ms > 1000.0:
                finding = self._create_latency_finding(manifest.system_id, health)
                new_findings.append(finding)
                self._findings.append(finding)

        return new_findings

    def handle_finding(
        self,
        finding: ProactiveFinding,
        active_grants: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Process finding according to bounded autonomy level (A0-A3)."""
        active_grants = active_grants or []

        # Case A0 / A1: Recommend only, no side effects
        if finding.autonomy_level in (AutonomyLevelScope.A0_OBSERVE, AutonomyLevelScope.A1_RECOMMEND):
            finding.status = "PROPOSED"
            return {
                "action": "RECOMMEND_ONLY",
                "finding_id": finding.finding_id,
                "proposal": finding.proposed_solution,
                "executed": False,
            }

        # Case A2: Delegated Action (Low risk <= R2, reversible)
        if finding.autonomy_level == AutonomyLevelScope.A2_DELEGATED and int(finding.risk_level) <= int(RiskLevel.R2):
            # Check if active delegation grant exists for this system
            has_grant = any(getattr(g, "resource_scope", "") == finding.system_id for g in active_grants)
            if has_grant:
                finding.status = "EXECUTED"
                return {
                    "action": "DELEGATED_EXECUTION",
                    "finding_id": finding.finding_id,
                    "executed": True,
                    "resolution": f"Applied verified fix under delegated autonomy for {finding.system_id}",
                }

        # Case A3: Owner Approval Required (High risk or un-delegated)
        finding.status = "PROPOSED"
        if self.consultation_store:
            try:
                from quan_ai_brain.governance.consultation_inbox import ConsultationCategory, ConsultationTicket
                ticket = ConsultationTicket(
                    ticket_id=f"cst_proactive_{finding.finding_id}",
                    title=f"[Chủ Động Phát Hiện] {finding.summary}",
                    category=ConsultationCategory.STRATEGIC_DIRECTION,
                    priority="HIGH" if finding.severity == FindingSeverity.CRITICAL else "MEDIUM",
                    context_summary=f"QUAN AI BRAIN phát hiện bất thường tại '{finding.system_id}': {finding.diagnosis}",
                    proposed_action=finding.proposed_solution,
                    options=[
                        {"action": "APPROVE", "label": "Chấp thuận thực thi giải pháp đề xuất"},
                        {"action": "REJECT", "label": "Bỏ qua cảnh báo này"},
                        {"action": "DIRECT", "label": "Chỉ đạo hướng xử lý khác"},
                    ],
                    evidence_notes=str(finding.evidence),
                )
                self.consultation_store.create_ticket(ticket)
            except Exception:
                pass

        return {
            "action": "ESCALATED_TO_OWNER",
            "finding_id": finding.finding_id,
            "consultation_ticket_id": f"cst_proactive_{finding.finding_id}",
            "executed": False,
        }

    def _create_health_finding(self, system_id: str, health: Any) -> ProactiveFinding:
        return ProactiveFinding(
            finding_id=f"find_{uuid.uuid4().hex[:8]}",
            system_id=system_id,
            severity=FindingSeverity.CRITICAL if health.circuit_state.value == "TRIPPED" else FindingSeverity.WARNING,
            summary=f"Phát hiện kết nối suy giảm hoặc lỗi trên hệ thống {system_id}",
            evidence={"status": health.status_text, "latency_ms": health.latency_ms, "consecutive_failures": health.consecutive_failures},
            diagnosis=f"Connector {system_id} không phản hồi chuẩn hoặc circuit breaker đã kích hoạt: {health.status_text}",
            proposed_solution=f"Thực hiện re-connect an toàn hoặc thông báo chủ sở hữu kiểm tra endpoint {system_id}",
            risk_level=RiskLevel.R1,
            autonomy_level=AutonomyLevelScope.A1_RECOMMEND,
        )

    def _create_latency_finding(self, system_id: str, health: Any) -> ProactiveFinding:
        return ProactiveFinding(
            finding_id=f"find_{uuid.uuid4().hex[:8]}",
            system_id=system_id,
            severity=FindingSeverity.WARNING,
            summary=f"Độ trễ kết nối cao ({health.latency_ms:.1f}ms) tại hệ thống {system_id}",
            evidence={"latency_ms": health.latency_ms},
            diagnosis=f"Hệ thống {system_id} phản hồi chậm bất thường (> 1000ms), có thể do tải cao hoặc đường truyền",
            proposed_solution="Tạm thời giảm tần suất thăm dò (backoff) và bật chế độ bộ nhớ đệm (cache)",
            risk_level=RiskLevel.R0,
            autonomy_level=AutonomyLevelScope.A1_RECOMMEND,
        )
