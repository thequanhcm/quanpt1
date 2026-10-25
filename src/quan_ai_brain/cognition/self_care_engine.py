"""Self-Care Engine for QUAN AI BRAIN — Sprint 6.

Implements self-care capabilities:
- Health monitoring with configurable thresholds
- Auto-recovery for levels 0-2 (3-4 require owner approval)
- Alert generation and escalation
- Root cause analysis
- Incident logging

Levels:
- Level 0: Observe only (log, analyze)
- Level 1: Recommend (analyze, propose, notify owner)
- Level 2: Auto-recovery per policy (safe operations only)
- Level 3: System changes (requires owner approval)
- Level 4: Dangerous operations (blocked, requires special approval)

Giai đoạn Sprint 6 (2026-10-25): Health monitor, auto-recovery, alerting.
"""
from __future__ import annotations

import logging
import socket
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HealthLevel(str, Enum):
    """Health severity levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    DOWN = "down"


class ActionType(str, Enum):
    """Action types by risk level."""
    OBSERVE = "observe"           # Level 0
    RECOMMEND = "recommend"       # Level 1
    AUTO_RECOVER = "auto_recover" # Level 2
    APPROVAL_REQUIRED = "approval" # Level 3
    BLOCKED = "blocked"           # Level 4


@dataclass
class HealthCheck:
    """Single health check result."""
    check_id: str
    component: str
    metric: str
    value: float | str
    threshold: float | str
    status: HealthLevel
    timestamp: str
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Alert:
    """System alert."""
    alert_id: str
    severity: HealthLevel
    component: str
    message: str
    detected_at: str
    acknowledged: bool = False
    resolved: bool = False
    resolution_note: str = ""
    auto_recovered: bool = False
    action_taken: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Incident:
    """Incident record with root cause analysis."""
    incident_id: str
    severity: HealthLevel
    component: str
    symptoms: list[str]
    detected_at: str
    root_cause: str | None = None
    resolution: str | None = None
    resolved_at: str | None = None
    lessons_learned: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SelfCareEngine:
    """Self-care engine with health monitoring and auto-recovery."""

    def __init__(self, workspace: str = ".") -> None:
        self.workspace = workspace
        self._health_checks: list[HealthCheck] = []
        self._alerts: list[Alert] = []
        self._incidents: list[Incident] = []
        self._thresholds: dict[str, dict[str, Any]] = {
            "ollama_response_time": {"warning": 2.0, "critical": 5.0, "unit": "seconds"},
            "web_response_time": {"warning": 1.0, "critical": 3.0, "unit": "seconds"},
            "disk_usage": {"warning": 0.8, "critical": 0.95, "unit": "ratio"},
            "memory_usage": {"warning": 0.85, "critical": 0.95, "unit": "ratio"},
            "pi5_connection": {"warning": 2, "critical": 5, "unit": "failed_attempts"},
        }
        self._auto_recovery_policies: dict[str, list[str]] = {
            "ollama_offline": ["restart_ollama", "probe_ollama"],
            "web_offline": ["restart_web_server"],
            "pi5_disconnected": ["ping_pi5", "check_wifi"],
            "disk_full": ["cleanup_logs", "archive_old_data"],
        }

    def check_ollama_health(self) -> HealthCheck:
        """Check Ollama daemon health."""
        check_id = f"health_{int(time.time()*1000)}"
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            # Probe Ollama endpoint
            t0 = time.perf_counter()
            with socket.create_connection(("127.0.0.1", 11434), timeout=2):
                response_time = (time.perf_counter() - t0) * 1000

            threshold = self._thresholds["ollama_response_time"]
            if response_time < threshold["warning"] * 1000:
                status = HealthLevel.HEALTHY
                message = "Ollama healthy"
            elif response_time < threshold["critical"] * 1000:
                status = HealthLevel.WARNING
                message = f"Ollama slow: {response_time:.2f}ms"
            else:
                status = HealthLevel.CRITICAL
                message = f"Ollama very slow: {response_time:.2f}ms"

            return HealthCheck(
                check_id=check_id,
                component="ollama",
                metric="response_time",
                value=response_time,
                threshold=threshold["warning"] * 1000,
                status=status,
                timestamp=timestamp,
                message=message,
            )

        except (socket.timeout, socket.error, OSError):
            return HealthCheck(
                check_id=check_id,
                component="ollama",
                metric="connectivity",
                value=0,
                threshold=1,
                status=HealthLevel.DOWN,
                timestamp=timestamp,
                message="Ollama offline",
            )

    def check_web_health(self, port: int = 8765) -> HealthCheck:
        """Check web server health."""
        check_id = f"health_{int(time.time()*1000)}"
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            t0 = time.perf_counter()
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                response_time = (time.perf_counter() - t0) * 1000

            threshold = self._thresholds["web_response_time"]
            if response_time < threshold["warning"] * 1000:
                status = HealthLevel.HEALTHY
                message = f"Web:{port} healthy"
            else:
                status = HealthLevel.WARNING
                message = f"Web:{port} slow: {response_time:.2f}ms"

            return HealthCheck(
                check_id=check_id,
                component=f"web_{port}",
                metric="response_time",
                value=response_time,
                threshold=threshold["warning"] * 1000,
                status=status,
                timestamp=timestamp,
                message=message,
            )

        except (socket.timeout, socket.error, OSError):
            return HealthCheck(
                check_id=check_id,
                component=f"web_{port}",
                metric="connectivity",
                value=0,
                threshold=1,
                status=HealthLevel.DOWN,
                timestamp=timestamp,
                message=f"Web:{port} offline",
            )

    def check_pi5_connection(self, pi_ip: str = "192.168.1.21", port: int = 8768) -> HealthCheck:
        """Check Pi 5 connection."""
        check_id = f"health_{int(time.time()*1000)}"
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            with socket.create_connection((pi_ip, port), timeout=3):
                return HealthCheck(
                    check_id=check_id,
                    component="pi5",
                    metric="connectivity",
                    value=1,
                    threshold=1,
                    status=HealthLevel.HEALTHY,
                    timestamp=timestamp,
                    message=f"Pi 5 ({pi_ip}) connected",
                )
        except (socket.timeout, socket.error, OSError):
            return HealthCheck(
                check_id=check_id,
                component="pi5",
                metric="connectivity",
                value=0,
                threshold=1,
                status=HealthLevel.DOWN,
                timestamp=timestamp,
                message=f"Pi 5 ({pi_ip}) disconnected",
            )

    def run_all_health_checks(self) -> list[HealthCheck]:
        """Run all health checks."""
        checks = [
            self.check_ollama_health(),
            self.check_web_health(8765),
            self.check_web_health(8766),
            self.check_pi5_connection(),
        ]
        self._health_checks.extend(checks)
        return checks

    def generate_alerts(self, checks: list[HealthCheck] | None = None) -> list[Alert]:
        """Generate alerts from health checks."""
        if checks is None:
            checks = self.run_all_health_checks()

        alerts = []
        for check in checks:
            if check.status in [HealthLevel.WARNING, HealthLevel.DEGRADED, HealthLevel.CRITICAL, HealthLevel.DOWN]:
                alert = Alert(
                    alert_id=f"alert_{int(time.time()*1000)}_{len(alerts)}",
                    severity=check.status,
                    component=check.component,
                    message=check.message,
                    detected_at=check.timestamp,
                )
                alerts.append(alert)
                self._alerts.append(alert)

                # Auto-recover if level 0-2
                self._attempt_auto_recovery(alert)

        return alerts

    def _attempt_auto_recovery(self, alert: Alert) -> None:
        """Attempt auto-recovery for level 0-2 issues."""
        if alert.severity == HealthLevel.DOWN:
            # Level 2: Auto-recovery for critical issues
            component = alert.component
            if component == "ollama" and "ollama_offline" in self._auto_recovery_policies:
                # Simulate restart (in production, would call actual restart)
                alert.action_taken = "Attempted Ollama restart (simulated)"
                alert.auto_recovered = True
                logger.info(f"Auto-recovery attempted for {component}")

            elif component.startswith("web_") and "web_offline" in self._auto_recovery_policies:
                alert.action_taken = "Attempted web server restart (simulated)"
                alert.auto_recovered = True
                logger.info(f"Auto-recovery attempted for {component}")

            elif component == "pi5" and "pi5_disconnected" in self._auto_recovery_policies:
                alert.action_taken = "Attempted Pi 5 reconnection (simulated)"
                alert.auto_recovered = True
                logger.info(f"Auto-recovery attempted for {component}")

        elif alert.severity in [HealthLevel.WARNING, HealthLevel.DEGRADED]:
            # Level 1: Recommend only
            alert.action_taken = "Recommendation generated (owner notification)"
            logger.warning(f"Alert generated for {alert.component}: {alert.message}")

    def create_incident(self, alert: Alert, root_cause: str | None = None) -> Incident:
        """Create incident record from alert."""
        incident = Incident(
            incident_id=f"incident_{int(time.time()*1000)}",
            severity=alert.severity,
            component=alert.component,
            symptoms=[alert.message],
            detected_at=alert.detected_at,
            root_cause=root_cause,
        )
        self._incidents.append(incident)
        return incident

    def resolve_incident(self, incident_id: str, resolution: str, lessons: list[str] | None = None) -> bool:
        """Resolve an incident."""
        for incident in self._incidents:
            if incident.incident_id == incident_id:
                incident.resolution = resolution
                incident.resolved_at = datetime.now(timezone.utc).isoformat()
                if lessons:
                    incident.lessons_learned.extend(lessons)
                return True
        return False

    def get_health_summary(self) -> dict[str, Any]:
        """Get overall health summary."""
        if not self._health_checks:
            self.run_all_health_checks()

        total = len(self._health_checks)
        healthy = sum(1 for c in self._health_checks if c.status == HealthLevel.HEALTHY)
        warning = sum(1 for c in self._health_checks if c.status == HealthLevel.WARNING)
        critical = sum(1 for c in self._health_checks if c.status == HealthLevel.CRITICAL)
        down = sum(1 for c in self._health_checks if c.status == HealthLevel.DOWN)

        return {
            "total_checks": total,
            "healthy": healthy,
            "warning": warning,
            "critical": critical,
            "down": down,
            "health_percentage": healthy / max(1, total),
            "last_check": self._health_checks[-1].timestamp if self._health_checks else None,
            "active_alerts": len([a for a in self._alerts if not a.resolved]),
            "auto_recoveries": sum(1 for a in self._alerts if a.auto_recovered),
        }

    def get_active_alerts(self, limit: int = 20) -> list[Alert]:
        """Get active (unresolved) alerts."""
        return [a for a in self._alerts if not a.resolved][-limit:]

    def get_incidents(self, limit: int = 20) -> list[Incident]:
        """Get recent incidents."""
        return self._incidents[-limit:]