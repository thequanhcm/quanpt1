"""Integration Policy Engine for Universal Software Integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any

from quan_ai_brain.core.guardrails import OutputGuardrails
from quan_ai_brain.governance.policy import PolicyEngine, RiskLevel
from quan_ai_brain.integration.manifest import ConnectorManifest, ConnectorOperation


class IntegrationPolicyViolationError(PermissionError):
    """Raised when an operation violates Integration Policy constraints."""
    pass


@dataclass
class RateLimitWindow:
    """Sliding rate limit tracking per system."""
    timestamps: list[float] = field(default_factory=list)


class IntegrationPolicy:
    """Enforces 14 Security & Governance Principles for software integrations."""

    def __init__(
        self,
        allowed_connectors: list[str] | None = None,
        allowed_hosts: list[str] | None = None,
        max_rate_limit: int = 120,
    ) -> None:
        self.allowed_connectors: set[str] = set(allowed_connectors or [])
        self.allowed_hosts: set[str] = set(allowed_hosts or ["127.0.0.1", "localhost", "192.168.1.11", "192.168.1.21"])
        self.max_rate_limit = max_rate_limit
        self._rate_limits: dict[str, RateLimitWindow] = {}
        self.guardrails = OutputGuardrails()

    def allow_connector(self, system_id: str) -> None:
        self.allowed_connectors.add(system_id)

    def revoke_connector(self, system_id: str) -> None:
        self.allowed_connectors.discard(system_id)

    def is_connector_allowed(self, system_id: str) -> bool:
        return system_id in self.allowed_connectors

    def check_operation_authorization(
        self,
        manifest: ConnectorManifest,
        operation: ConnectorOperation,
        params: dict[str, Any],
        system_emergency_state: str = "normal",
    ) -> tuple[bool, str | None]:
        """Validate all policy constraints before executing an external operation."""
        # 1. Emergency state check (Fail-closed)
        if system_emergency_state in ("stop", "freeze"):
            return False, f"Integration operation blocked: emergency state is {system_emergency_state.upper()}"

        # 2. Allowlist verification
        if not self.is_connector_allowed(manifest.system_id):
            return False, f"Connector '{manifest.system_id}' is not in the authorized connector allowlist"

        # 3. R5 Hard-Block
        if int(operation.risk_level) >= int(RiskLevel.R5):
            return False, f"Operation '{operation.operation_id}' is R5, which is permanently hard-blocked"

        # 4. Read-only default guard
        if manifest.read_only_default and (operation.side_effects or operation.action_type == "write"):
            return False, f"Operation '{operation.operation_id}' attempts write/side-effects on read-only connector"

        # 5. Rate limit verification
        now = datetime.now(timezone.utc).timestamp()
        window = self._rate_limits.setdefault(manifest.system_id, RateLimitWindow())
        # Clean timestamps older than 60s
        window.timestamps = [t for t in window.timestamps if now - t < 60.0]
        effective_limit = min(manifest.rate_limit_per_minute, self.max_rate_limit)
        if len(window.timestamps) >= effective_limit:
            return False, f"Rate limit exceeded for '{manifest.system_id}': max {effective_limit} calls/min"

        window.timestamps.append(now)

        # 6. Parameter prompt-injection & secret leak pre-flight
        for k, v in params.items():
            if isinstance(v, str):
                # Prompt injection defense: scan for system prompt override attempts
                if self.detect_prompt_injection(v):
                    return False, f"Prompt injection pattern detected in parameter '{k}'"

        return True, None

    def validate_and_sanitize_output(self, raw_data: Any) -> tuple[Any, list[str]]:
        """Scans external output for credentials, script tags, or dangerous tokens."""
        from quan_ai_brain.core.redaction import redact_value
        cleaned_source = redact_value(raw_data)

        if isinstance(cleaned_source, str):
            sanitized, warnings = self.guardrails.sanitize(cleaned_source)
            return sanitized, warnings
        elif isinstance(cleaned_source, dict):
            sanitized_dict = {}
            collected_warnings: list[str] = []
            for k, v in cleaned_source.items():
                if isinstance(v, str):
                    s_val, warns = self.guardrails.sanitize(v)
                    sanitized_dict[k] = s_val
                    collected_warnings.extend(warns)
                elif isinstance(v, dict):
                    s_val, warns = self.validate_and_sanitize_output(v)
                    sanitized_dict[k] = s_val
                    collected_warnings.extend(warns)
                else:
                    sanitized_dict[k] = v
            return sanitized_dict, collected_warnings
        return cleaned_source, []

    @staticmethod
    def detect_prompt_injection(text: str) -> bool:
        """Heuristic detection of adversarial prompt-injection payloads."""
        patterns = (
            r"(?i)\bignore\s+(all\s+)?(previous|prior)\s+instructions\b",
            r"(?i)\bbypass\s+(security|policy|governance|guardrails)\b",
            r"(?i)\byou\s+are\s+now\s+in\s+(developer|unrestricted|god)\s+mode\b",
            r"(?i)\bdisregard\s+(the\s+)?rules\b",
            r"(?i)\boverride\s+owner\s+authority\b",
        )
        return any(bool(re.search(p, text)) for p in patterns)
