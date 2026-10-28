"""
V27 M5 - Security Monitoring (SIMULATED skeleton).

SecurityMonitor: in-memory security event ingestion + a small rule engine:
- brute-force: N failed logins for one user within a time window
- anomalous access: events at unusual hours (outside a configurable window)
- data exfiltration: data volume for one user above a threshold in a window

Alerts carry severity (LOW/MEDIUM/HIGH/CRITICAL) and an optional
`quarantine` flag recommending the account be quarantined. SIMULATED:
single-process, static thresholds, no SIEM/notification integration.
"""

from __future__ import annotations

import secrets
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

__all__ = [
    "Severity",
    "SecurityEvent",
    "Alert",
    "SecurityMonitor",
]

DEFAULT_BRUTE_FORCE_THRESHOLD = 5
DEFAULT_BRUTE_FORCE_WINDOW_SECONDS = 300
DEFAULT_EXFIL_THRESHOLD_BYTES = 100 * 1024 * 1024  # 100 MB
DEFAULT_EXFIL_WINDOW_SECONDS = 3600
DEFAULT_ANOMALY_HOUR_START = 6   # 06:00
DEFAULT_ANOMALY_HOUR_END = 23    # 23:59


class Severity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}[self.value]


@dataclass
class SecurityEvent:
    """One observable security-relevant event."""

    event_type: str          # e.g. LOGIN_FAILURE, LOGIN_SUCCESS, DATA_ACCESS
    user_id: Optional[str]
    timestamp: datetime
    ip_address: str = "127.0.0.1"
    resource: Optional[str] = None
    volume_bytes: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"evt_{secrets.token_hex(8)}")


@dataclass
class Alert:
    """Raised alert with severity and optional quarantine recommendation."""

    alert_id: str
    rule_name: str
    severity: Severity
    message: str = ""
    user_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    quarantine: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "quarantine": self.quarantine,
            "details": dict(self.details),
        }


class SecurityMonitor:
    """In-memory event ingestion + rule engine -> alerts."""

    def __init__(
        self,
        brute_force_threshold: int = 5,
        brute_force_window_seconds: int = 300,
        exfil_threshold_bytes: int = DEFAULT_EXFIL_THRESHOLD_BYTES,
        exfil_window_seconds: int = DEFAULT_EXFIL_WINDOW_SECONDS,
        anomaly_hour_start: int = DEFAULT_ANOMALY_HOUR_START,
        anomaly_hour_end: int = DEFAULT_ANOMALY_HOUR_END,
    ) -> None:
        self.brute_force_threshold = brute_force_threshold
        self.brute_force_window_seconds = brute_force_window_seconds
        self.exfil_threshold_bytes = exfil_threshold_bytes
        self.exfil_window_seconds = exfil_window_seconds
        self.anomaly_hour_start = anomaly_hour_start
        self.anomaly_hour_end = anomaly_hour_end
        self._events: Deque[SecurityEvent] = deque(maxlen=10_000)
        self._alerts: List[Alert] = []
        self._quarantined: Dict[str, str] = {}  # user_id -> alert_id

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def ingest(self, event: SecurityEvent) -> List[Alert]:
        """Store an event and run all rules; returns alerts fired by it."""
        self._events.append(event)
        fired: List[Alert] = []
        fired.extend(self._check_brute_force(event))
        fired.extend(self._check_anomalous_hours(event))
        fired.extend(self._check_exfiltration(event))
        for alert in fired:
            self._alerts.append(alert)
            if alert.quarantine and alert.user_id:
                self._quarantined[alert.user_id] = alert.alert_id
        return fired

    def ingest_batch(self, events: List[SecurityEvent]) -> List[Alert]:
        alerts: List[Alert] = []
        for event in events:
            alerts.extend(self.ingest(event))
        return alerts

    # ------------------------------------------------------------------
    # Rule: brute force
    # ------------------------------------------------------------------
    def _check_brute_force(self, event: SecurityEvent) -> List[Alert]:
        if event.event_type != "LOGIN_FAILURE" or event.user_id is None:
            return []
        window_start = event.timestamp - timedelta(seconds=self.brute_force_window_seconds)
        recent = [
            e
            for e in self._events
            if e.event_type == "LOGIN_FAILURE"
            and e.user_id == event.user_id
            and window_start <= e.timestamp <= event.timestamp
        ]
        if len(recent) >= self.brute_force_threshold:
            severe = len(recent) >= self.brute_force_threshold * 2
            return [
                Alert(
                    alert_id=f"alr_{secrets.token_hex(6)}",
                    rule_name="brute_force",
                    severity=Severity.HIGH if severe else Severity.MEDIUM,
                    message=(
                        f"{len(recent)} failed logins for user '{event.user_id}' "
                        f"within {self.brute_force_window_seconds}s"
                    ),
                    user_id=event.user_id,
                    timestamp=event.timestamp,
                    quarantine=severe,
                    details={"failures": len(recent), "window_seconds": self.brute_force_window_seconds},
                )
            ]
        return []

    # ------------------------------------------------------------------
    # Rule: anomalous access hours
    # ------------------------------------------------------------------
    def _check_anomalous_hours(self, event: SecurityEvent) -> List[Alert]:
        if event.event_type not in ("LOGIN_SUCCESS", "DATA_ACCESS"):
            return []
        hour = event.timestamp.hour
        in_window = self.anomaly_hour_start <= hour <= self.anomaly_hour_end
        if in_window:
            return []
        return [
            Alert(
                alert_id=f"alr_{secrets.token_hex(6)}",
                rule_name="anomalous_hours",
                severity=Severity.MEDIUM,
                message=(
                    f"{event.event_type} at unusual hour {hour:02d}:00 "
                    f"(allowed {self.anomaly_hour_start:02d}:00-{self.anomaly_hour_end:02d}:59)"
                ),
                user_id=event.user_id,
                timestamp=event.timestamp,
                quarantine=False,
                details={"hour": hour, "event_type": event.event_type},
            )
        ]

    # ------------------------------------------------------------------
    # Rule: data exfiltration
    # ------------------------------------------------------------------
    def _check_exfiltration(self, event: SecurityEvent) -> List[Alert]:
        if event.event_type != "DATA_ACCESS" or event.user_id is None:
            return []
        window_start = event.timestamp - timedelta(seconds=self.exfil_window_seconds)
        total = sum(
            e.volume_bytes
            for e in self._events
            if e.event_type == "DATA_ACCESS"
            and e.user_id == event.user_id
            and window_start <= e.timestamp <= event.timestamp
        )
        if total > self.exfil_threshold_bytes:
            severe = total > self.exfil_threshold_bytes * 2
            return [
                Alert(
                    alert_id=f"alr_{secrets.token_hex(6)}",
                    rule_name="data_exfiltration",
                    severity=Severity.CRITICAL if severe > 0 else Severity.HIGH,
                    message=(
                        f"{total} bytes accessed by '{event.user_id}' within "
                        f"{self.exfil_window_seconds}s (threshold {self.exfil_threshold_bytes})"
                    ),
                    user_id=event.user_id,
                    timestamp=event.timestamp,
                    quarantine=severe,
                    details={"volume_bytes": total, "threshold_bytes": self.exfil_threshold_bytes},
                )
            ]
        return []

    # ------------------------------------------------------------------
    # Accessors / ack
    # ------------------------------------------------------------------
    def alerts(self, min_severity: Optional[Severity] = None) -> List[Alert]:
        result = self._alerts
        if min_severity is not None:
            result = [a for a in result if a.severity.rank >= min_severity.rank]
        return list(result)

    def ack_alert(self, alert_id: str) -> bool:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.details["acknowledged"] = True
                return True
        return False

    def is_quarantined(self, user_id: str) -> bool:
        return user_id in self._quarantined

    def quarantine_user(self, user_id: str, reason: str = "manual") -> str:
        """Manually quarantine a user; returns the alert_id created."""
        alert = Alert(
            alert_id=f"alr_{secrets.token_hex(6)}",
            rule_name="manual_quarantine",
            severity=Severity.HIGH,
            message=f"user '{user_id}' quarantined: {reason}",
            user_id=user_id,
            timestamp=datetime.utcnow(),
            quarantine=True,
            details={"reason": reason},
        )
        self._alerts.append(alert)
        self._quarantined[user_id] = alert.alert_id
        return alert.alert_id

    def release_user(self, user_id: str) -> bool:
        return self._quarantined.pop(user_id, None) is not None

    def stats(self) -> Dict[str, Any]:
        by_severity: Dict[str, int] = {s.value: 0 for s in Severity}
        for alert in self._alerts:
            by_severity[alert.severity.value] += 1
        return {
            "events_ingested": len(self._events),
            "alerts_total": len(self._alerts),
            "alerts_by_severity": by_severity,
            "quarantined_users": sorted(self._quarantined.keys()),
        }
