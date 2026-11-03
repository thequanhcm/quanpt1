"""
Security Hardening Module (V23.5)

Scans a configuration dict for weak settings and returns risk-scored
recommendations. Pure static analysis of caller-supplied dicts.

SIMULATED COMPONENTS:
- The "scan" is static pattern matching over a config dict; it does not load
  .env files, secrets, or live system state. Findings are advisory only —
  applying them is out of scope for this module.

Version: V23.5
Author: QUAN AI BRAIN Team
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

_RISK_ORDER = {RISK_LOW: 0, RISK_MEDIUM: 1, RISK_HIGH: 2, RISK_CRITICAL: 3}


class RiskLevel:
    """Helpers around risk levels."""

    LEVELS: Sequence[str] = (RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_CRITICAL)

    @staticmethod
    def order(level: str) -> int:
        return _RISK_ORDER.get(level, -1)

    @staticmethod
    def is_valid(level: str) -> bool:
        return level in _RISK_ORDER


# Sensitive patterns that must never appear in logs (case-insensitive).
SENSITIVE_LOG_PATTERNS: Dict[str, "re.Pattern[str]"] = {
    "password": re.compile(r"password", re.IGNORECASE),
    "secret": re.compile(r"secret", re.IGNORECASE),
    "api_key": re.compile(r"api[_-]?key", re.IGNORECASE),
    "token": re.compile(r"token", re.IGNORECASE),
    "bearer": re.compile(r"bearer\s+[a-z0-9._-]+", re.IGNORECASE),
    "private_key": re.compile(r"private[_-]?key", re.IGNORECASE),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
}


@dataclass
class Finding:
    """One weak-configuration finding."""

    finding_id: str
    path: str
    issue: str
    risk: str  # low | medium | high | critical
    recommendation: str
    current_value: Any = None
    suggested_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "path": self.path,
            "issue": self.issue,
            "risk": self.risk,
            "recommendation": self.recommendation,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
        }


@dataclass
class HardeningReport:
    """Result of one config scan."""

    findings: List[Finding]
    risk_score: float  # 0..100 (higher = riskier)
    overall_risk: str  # low | medium | high | critical
    scanned_paths: int
    summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "risk_score": self.risk_score,
            "overall_risk": self.overall_risk,
            "scanned_paths": self.scanned_paths,
            "summary": dict(self.summary),
        }


class ConfigHardeningScanner:
    """Static scanner for weak configuration dicts.

    Detects:
    - timeout = 0 (unbounded wait)
    - infinite retries (retry == -1 or retry count too large)
    - sensitive patterns inside log config (format strings / fields)
    - disabled verification / auth toggles set unsafely
    - overly permissive binds (0.0.0.0) and debug mode on
    """

    def __init__(
        self,
        max_reasonable_retries: int = 10,
        min_timeout_seconds: float = 1.0,
    ) -> None:
        self.max_reasonable_retries = max_reasonable_retries
        self.min_timeout_seconds = min_timeout_seconds

    # ----------------------------------------------------------------- helpers
    def _iter_paths(self, config: Dict[str, Any], prefix: str = "") -> List[tuple]:
        """Flatten nested dicts/lists into (path, value) pairs."""
        pairs: List[tuple] = []
        for key, value in config.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                pairs.extend(self._iter_paths(value, path))
            elif isinstance(value, list):
                pairs.append((path, value))
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        pairs.extend(self._iter_paths(item, f"{path}[{idx}]"))
            else:
                pairs.append((path, value))
        return pairs

    def _add(
        self,
        findings: List[Finding],
        path: str,
        issue: str,
        risk: str,
        recommendation: str,
        current_value: Any = None,
        suggested_value: Any = None,
    ) -> None:
        findings.append(
            Finding(
                finding_id=f"F{len(findings) + 1:03d}",
                path=path,
                issue=issue,
                risk=risk,
                recommendation=recommendation,
                current_value=current_value,
                suggested_value=suggested_value,
            )
        )

    # ------------------------------------------------------------------- rules
    def _check_timeout(
        self, path: str, value: Any, findings: List[Finding]
    ) -> None:
        name = path.rsplit(".", 1)[-1].lower()
        if "timeout" not in name:
            return
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if value == 0:
                self._add(
                    findings,
                    path,
                    "timeout is 0 (wait forever / no timeout)",
                    RISK_HIGH,
                    f"set {path} to a finite timeout >= {self.min_timeout_seconds}s",
                    current_value=value,
                    suggested_value=30,
                )
            elif value < self.min_timeout_seconds:
                self._add(
                    findings,
                    path,
                    f"timeout below {self.min_timeout_seconds}s may cause spurious failures",
                    RISK_LOW,
                    f"raise {path} to >= {self.min_timeout_seconds}s",
                    current_value=value,
                    suggested_value=self.min_timeout_seconds,
                )

    def _check_retries(
        self, path: str, value: Any, findings: List[Finding]
    ) -> None:
        name = path.rsplit(".", 1)[-1].lower()
        if not any(t in name for t in ("retry", "retries", "attempts", "max_attempts")):
            return
        if isinstance(value, bool):
            return
        if value == -1:
            self._add(
                findings,
                path,
                "infinite retries (-1) can cause unbounded loops",
                RISK_CRITICAL,
                f"cap {path} at {self.max_reasonable_retries} with exponential backoff",
                current_value=value,
                suggested_value=self.max_reasonable_retries,
            )
        elif isinstance(value, (int, float)) and value > self.max_reasonable_retries:
            self._add(
                findings,
                path,
                f"retry count {value} exceeds sane bound {self.max_reasonable_retries}",
                RISK_MEDIUM,
                f"cap {path} at {self.max_reasonable_retries}",
                current_value=value,
                suggested_value=self.max_reasonable_retries,
            )

    def _check_log_patterns(
        self, path: str, value: Any, findings: List[Finding]
    ) -> None:
        name = path.rsplit(".", 1)[-1].lower()
        if not any(t in name for t in ("log", "format", "message", "template")):
            return
        if not isinstance(value, str):
            return
        for label, pattern in SENSITIVE_LOG_PATTERNS.items():
            if pattern.search(value):
                self._add(
                    findings,
                    path,
                    f"log setting may leak sensitive data (pattern: {label})",
                    RISK_HIGH,
                    f"remove '{label}' pattern from {path}; mask sensitive fields before logging",
                    current_value=value,
                    suggested_value="<masked>",
                )

    def _check_bool_flags(
        self, path: str, value: Any, findings: List[Finding]
    ) -> None:
        name = path.rsplit(".", 1)[-1].lower()
        if value is True and name in ("debug", "verbose", "insecure", "unsafe"):
            self._add(
                findings,
                path,
                f"'{name}' enabled in configuration",
                RISK_MEDIUM if name in ("debug", "verbose") else RISK_HIGH,
                f"disable {path} in production",
                current_value=value,
                suggested_value=False,
            )
        if value is False and name in ("verify", "verify_ssl", "verify_tls"):
            self._add(
                findings,
                path,
                "TLS/SSL verification disabled",
                RISK_CRITICAL,
                f"enable {path}",
                current_value=value,
                suggested_value=True,
            )

    def _check_bind_address(
        self, path: str, value: Any, findings: List[Finding]
    ) -> None:
        name = path.rsplit(".", 1)[-1].lower()
        if name in ("host", "bind", "address", "listen") and isinstance(value, str):
            if value.strip() in ("0.0.0.0", "::", ""):
                self._add(
                    findings,
                    path,
                    "service binds to all interfaces",
                    RISK_MEDIUM,
                    f"bind {path} to a specific interface or localhost",
                    current_value=value,
                    suggested_value="127.0.0.1",
                )

    # -------------------------------------------------------------------- scan
    def scan(self, config: Dict[str, Any]) -> HardeningReport:
        """Scan a config dict and return a risk-scored hardening report."""
        if not isinstance(config, dict):
            raise TypeError("config must be a dict")
        pairs = self._iter_paths(config)
        findings: List[Finding] = []
        for path, value in pairs:
            self._check_timeout(path, value, findings)
            self._check_retries(path, value, findings)
            self._check_log_patterns(path, value, findings)
            self._check_bool_flags(path, value, findings)
            self._check_bind_address(path, value, findings)

        summary: Dict[str, int] = {}
        for finding in findings:
            summary[finding.risk] = summary.get(finding.risk, 0) + 1

        risk_score = self.compute_risk_score(findings)
        overall = self.overall_risk(risk_score, len(findings))
        return HardeningReport(
            findings=findings,
            risk_score=risk_score,
            overall_risk=overall,
            scanned_paths=len(pairs),
            summary=summary,
        )

    # ------------------------------------------------------------ risk scoring
    def compute_risk_score(self, findings: Sequence[Finding]) -> float:
        """Weighted risk score in 0..100 (weights: critical 30, high 15, medium 5, low 1)."""
        weights = {RISK_CRITICAL: 30.0, RISK_HIGH: 15.0, RISK_MEDIUM: 5.0, RISK_LOW: 1.0}
        raw = sum(weights.get(f.risk, 0.0) for f in findings)
        return min(100.0, raw)

    def overall_risk(self, risk_score: float, n_findings: int) -> str:
        """Map score to a risk band."""
        if n_findings == 0:
            return RISK_LOW
        if risk_score >= 60:
            return RISK_CRITICAL
        if risk_score >= 30:
            return RISK_HIGH
        if risk_score >= 10:
            return RISK_MEDIUM
        return RISK_LOW

    def recommendations(self, config: Dict[str, Any]) -> List[str]:
        """Human-readable recommendation strings, most severe first."""
        report = self.scan(config)
        order = {RISK_CRITICAL: 0, RISK_HIGH: 1, RISK_MEDIUM: 2, RISK_LOW: 3}
        ordered = sorted(report.findings, key=lambda f: order.get(f.risk, 9))
        return [f.recommendation for f in ordered]
