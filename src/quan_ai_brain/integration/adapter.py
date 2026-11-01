"""Base Connector Adapter Interface and Response Envelopes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from quan_ai_brain.integration.manifest import ConnectorManifest


@dataclass
class ConnectorResponse:
    """Standardized response from an executed connector operation."""
    success: bool
    data: Any
    error: str | None = None
    status_code: int = 200
    latency_ms: float = 0.0
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    """Evidence-based outcome of target state verification on external systems."""
    verified: bool
    method: str
    target_state_observed: Any = None
    evidence_payload: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseConnectorAdapter(ABC):
    """Abstract base adapter for all external software connectors."""

    def __init__(self, manifest: ConnectorManifest) -> None:
        self.manifest = manifest
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    def connect(self) -> bool:
        """Establish or verify connectivity with the target software system."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Safely terminate session/connection."""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Perform non-destructive connectivity and health probe."""
        pass

    @abstractmethod
    def discover_schema(self) -> dict[str, Any]:
        """Inspect and return observable schema, tables, endpoints, and capabilities."""
        pass

    @abstractmethod
    def execute_operation(self, operation_id: str, params: dict[str, Any]) -> ConnectorResponse:
        """Execute a declared, bounded operation on the target system."""
        pass

    @abstractmethod
    def verify_target_state(
        self,
        operation_id: str,
        params: dict[str, Any],
        response: ConnectorResponse,
    ) -> VerificationResult:
        """Verify the true state on the target system rather than relying solely on tool ACK."""
        pass
