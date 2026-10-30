"""
V28.2 — Enterprise Connectors (mock, stdlib-only)

Provides:
- :class:`Connector` interface: fetch / send / health_check
- Deterministic mock connectors: Salesforce, Microsoft 365, Slack, SAP
- :class:`CircuitBreaker` — CLOSED -> OPEN after N consecutive failures,
  OPEN -> HALF_OPEN after cooldown, HALF_OPEN allows one probe.

IMPORTANT SCOPE NOTE (honesty):
Every connector here is an **in-memory mock**. No real Salesforce / Graph /
Slack / SAP API is contacted, no network I/O of any kind happens. Mock data
is generated deterministically from counters and simple arithmetic — the
same call sequence produces the same data. This is a simulation layer for
testing QUAN AI BRAIN's integration seams, not a production integration.

Version: V28.2
Author: QUAN AI BRAIN Team
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = [
    "ConnectorError",
    "CircuitOpenError",
    "Connector",
    "MockSalesforceConnector",
    "MockM365Connector",
    "MockSlackConnector",
    "MockSAPConnector",
    "ALL_MOCK_CONNECTOR_CLASSES",
    "CircuitState",
    "CircuitBreaker",
]


class ConnectorError(Exception):
    """Base error for connectors."""


class CircuitOpenError(ConnectorError):
    """Raised when a call is attempted while the breaker is OPEN."""


# ---------------------------------------------------------------------------
# Connector interface + shared plumbing
# ---------------------------------------------------------------------------

class Connector(ABC):
    """Interface every enterprise connector must implement."""

    name: str = "connector"

    @abstractmethod
    def fetch(self, resource: str, **params: Any) -> List[Dict[str, Any]]:
        """Fetch a list of records for ``resource``."""

    @abstractmethod
    def send(self, resource: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send/produce a record; returns an acknowledgment dict."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True when the (mock) backend is healthy."""

    # shared helpers ---------------------------------------------------------

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "healthy": self.health_check()}

    def _generate_id(self, prefix: str, counter: int) -> str:
        digest = hashlib.sha256(f"{self.name}:{counter}".encode("utf-8")).hexdigest()
        return f"{prefix}{digest[:10].upper()}"


class _MockBackendMixin:
    """Shared in-memory backend for mock connectors.

    - ``fail_next`` queue: the next N calls to fetch/send raise ConnectorError
      (simulated backend outage — deterministic, no randomness).
    - every call is recorded in ``calls`` for assertions.
    """

    def _init_backend(self, fail_next: int = 0) -> None:
        self.fail_next = int(fail_next)
        self.total_failures = 0
        self.total_successes = 0
        self.calls: List[Dict[str, Any]] = []

    def _maybe_fail(self, operation: str) -> None:
        self.calls.append({"op": operation, "failed": self.fail_next > 0})
        if self.fail_next > 0:
            self.fail_next -= 1
            self.total_failures += 1
            raise ConnectorError(
                f"{self.name}: simulated backend failure during '{operation}' "
                f"({self.fail_next} more queued)"
            )
        self.total_successes += 1

    def set_healthy(self, healthy: bool) -> None:
        """Force health state True/False (default True)."""
        self._healthy = healthy

    @property
    def healthy(self) -> bool:
        return getattr(self, "_healthy", True)


# ---------------------------------------------------------------------------
# Mock connectors
# ---------------------------------------------------------------------------

class MockSalesforceConnector(Connector, _MockBackendMixin):
    """Deterministic mock Salesforce connector (accounts / opportunities)."""

    name = "salesforce"

    ACCOUNT_NAMES = ("Acme Corp", "Globex", "Initech", "Umbrella", "Stark Industries")

    def __init__(self, fail_next: int = 0) -> None:
        self._init_backend(fail_next=fail_next)
        self._account_seq = 0
        self._opportunity_seq = 0

    def fetch(self, resource: str, **params: Any) -> List[Dict[str, Any]]:
        self._maybe_fail(f"fetch:{resource}")
        limit = int(params.get("limit", 3))
        if resource == "accounts":
            records = []
            for _ in range(limit):
                digest = hashlib.sha256(
                    f"sf-account:{self._account_seq}".encode()
                ).hexdigest()
                idx = self._account_seq % len(self.ACCOUNT_NAMES)
                records.append(
                    {
                        "id": self._generate_id("ACC", self._account_seq),
                        "name": self.ACCOUNT_NAMES[idx],
                        "industry": ["manufacturing", "software", "retail"][self._account_seq % 3],
                        "annual_revenue": 1_000_000 * (self._account_seq + 1),
                        "digest": digest[:8],
                    }
                )
                self._account_seq += 1
            return records
        if resource == "opportunities":
            records = []
            for _ in range(limit):
                records.append(
                    {
                        "id": self._generate_id("OPP", self._opportunity_seq),
                        "stage": ["prospecting", "qualification", "closed_won"][self._opportunity_seq % 3],
                        "amount": 50_000 * (self._opportunity_seq + 1),
                    }
                )
                self._opportunity_seq += 1
            return records
        raise ConnectorError(f"{self.name}: unknown resource '{resource}'")

    def send(self, resource: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._maybe_fail(f"send:{resource}")
        if resource not in ("accounts", "opportunities"):
            raise ConnectorError(f"{self.name}: unknown resource '{resource}'")
        seq = self._account_seq if resource == "accounts" else self._opportunity_seq
        self._account_seq += 1 if resource == "accounts" else 0
        self._opportunity_seq += 1 if resource == "opportunities" else 0
        return {
            "ok": True,
            "connector": self.name,
            "resource": resource,
            "id": self._generate_id("SF", seq),
            "received_fields": sorted(payload.keys()),
        }

    def health_check(self) -> bool:
        return self.healthy


class MockM365Connector(Connector, _MockBackendMixin):
    """Deterministic mock Microsoft 365 connector (mail / calendar / files)."""

    name = "m365"

    def __init__(self, fail_next: int = 0) -> None:
        self._init_backend(fail_next=fail_next)
        self._mail_seq = 0
        self._event_seq = 0

    def fetch(self, resource: str, **params: Any) -> List[Dict[str, Any]]:
        self._maybe_fail(f"fetch:{resource}")
        limit = int(params.get("limit", 3))
        if resource == "mail":
            records = []
            for _ in range(limit):
                records.append(
                    {
                        "id": self._generate_id("MSG", self._mail_seq),
                        "subject": f"Weekly report #{self._mail_seq}",
                        "from": f"sender{self._mail_seq}@contoso.com",
                        "unread": self._mail_seq % 2 == 0,
                        "body": f"Deterministic mail body {self._mail_seq}",
                    }
                )
                self._mail_seq += 1
            return records
        if resource == "calendar":
            base = datetime(2026, 10, 28, 9, 0, 0)
            records = []
            for _ in range(limit):
                start = base + timedelta(hours=2 * self._event_seq)
                records.append(
                    {
                        "id": self._generate_id("EVT", self._event_seq),
                        "title": f"Meeting {self._event_seq}",
                        "start": start.isoformat() + "Z",
                        "duration_minutes": 60,
                    }
                )
                self._event_seq += 1
            return records
        raise ConnectorError(f"{self.name}: unknown resource '{resource}'")

    def send(self, resource: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._maybe_fail(f"send:{resource}")
        if resource == "mail":
            recipients = payload.get("to", [])
            return {
                "ok": True,
                "connector": self.name,
                "resource": "mail",
                "id": self._generate_id("MSG", self._mail_seq),
                "delivered_to": list(recipients),
            }
        if resource == "calendar":
            return {
                "ok": True,
                "connector": self.name,
                "resource": "calendar",
                "id": self._generate_id("EVT", self._event_seq),
                "created_event": payload.get("title", "(untitled)"),
            }
        raise ConnectorError(f"{self.name}: unknown resource '{resource}'")

    def health_check(self) -> bool:
        return self.healthy


class MockSlackConnector(Connector, _MockBackendMixin):
    """Deterministic mock Slack connector (channels / messages)."""

    name = "slack"

    CHANNELS = ("#general", "#engineering", "#alerts")

    def __init__(self, fail_next: int = 0) -> None:
        self._init_backend(fail_next=fail_next)
        self._message_seq = 0

    def fetch(self, resource: str, **params: Any) -> List[Dict[str, Any]]:
        self._maybe_fail(f"fetch:{resource}")
        limit = int(params.get("limit", 3))
        if resource == "messages":
            records = []
            for _ in range(limit):
                records.append(
                    {
                        "id": self._generate_id("SLK", self._message_seq),
                        "channel": self.CHANNELS[self._message_seq % len(self.CHANNELS)],
                        "text": f"Deterministic slack message {self._message_seq}",
                        "user": f"U{1000 + self._message_seq}",
                    }
                )
                self._message_seq += 1
            return records
        if resource == "channels":
            return [{"id": f"C{i}", "name": ch} for i, ch in enumerate(self.CHANNELS)]
        raise ConnectorError(f"{self.name}: unknown resource '{resource}'")

    def send(self, resource: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._maybe_fail(f"send:{resource}")
        if resource == "messages":
            channel = payload.get("channel", "#general")
            if not channel.startswith("#"):
                raise ConnectorError(f"{self.name}: invalid channel {channel!r}")
            self._message_seq += 1
            return {
                "ok": True,
                "connector": self.name,
                "resource": "messages",
                "id": self._generate_id("SLK", self._message_seq),
                "channel": channel,
            }
        raise ConnectorError(f"{self.name}: unknown resource '{resource}'")

    def health_check(self) -> bool:
        return self.healthy


class MockSAPConnector(Connector, _MockBackendMixin):
    """Deterministic mock SAP connector (RFC-style BAPI calls)."""

    name = "sap"

    BAPI_FUNCTIONS = ("BAPI_MATERIAL_GET_DETAIL", "BAPI_PO_GET_DETAIL")

    def __init__(self, fail_next: int = 0) -> None:
        self._init_backend(fail_next=fail_next)
        self._bapi_seq = 0

    def fetch(self, resource: str, **params: Any) -> List[Dict[str, Any]]:
        self._maybe_fail(f"fetch:{resource}")
        limit = int(params.get("limit", 3))
        if resource == "materials":
            records = []
            for _ in range(limit):
                records.append(
                    {
                        "material_no": f"MAT-{100000 + self._bapi_seq}",
                        "description": f"Material {self._bapi_seq}",
                        "plant": ["1000", "2000"][self._bapi_seq % 2],
                        "stock_qty": 100 * (self._bapi_seq + 1),
                    }
                )
                self._bapi_seq += 1
            return records
        if resource == "purchase_orders":
            records = []
            for _ in range(limit):
                records.append(
                    {
                        "po_number": f"PO-{450000 + self._bapi_seq}",
                        "vendor": f"VENDOR-{self._bapi_seq}",
                        "total_value": 10_000 * (self._bapi_seq + 1),
                    }
                )
                self._bapi_seq += 1
            return records
        raise ConnectorError(f"{self.name}: unknown resource '{resource}'")

    def send(self, resource: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._maybe_fail(f"send:{resource}")
        if resource == "bapi_call":
            fn = payload.get("function", "")
            if fn not in self.BAPI_FUNCTIONS:
                raise ConnectorError(f"{self.name}: unknown BAPI function {fn!r}")
            self._bapi_seq += 1
            return {
                "ok": True,
                "connector": self.name,
                "resource": "bapi_call",
                "function": fn,
                "return_code": "00",
                "id": self._generate_id("SAP", self._bapi_seq),
            }
        raise ConnectorError(f"{self.name}: unknown resource '{resource}'")

    def health_check(self) -> bool:
        return self.healthy


ALL_MOCK_CONNECTOR_CLASSES = (
    MockSalesforceConnector,
    MockM365Connector,
    MockSlackConnector,
    MockSAPConnector,
)


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker wrapper around any callable operation.

    - CLOSED: calls pass through. After ``failure_threshold`` consecutive
      failures the breaker OPENS.
    - OPEN: every call raises :class:`CircuitOpenError` immediately (no
      underlying call) until ``cooldown_seconds`` elapses.
    - HALF_OPEN: one probe call is allowed; success closes the breaker,
      failure re-opens it.

    Clock is injectable for deterministic tests.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if failure_threshold < 1:
            raise ConnectorError("failure_threshold must be >= 1")
        self.failure_threshold = int(failure_threshold)
        self.cooldown_seconds = float(cooldown_seconds)
        self.clock = clock or time.monotonic
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.opened_at: Optional[float] = None
        self._half_open_probe_in_flight = False
        self.total_calls = 0
        self.total_rejected = 0
        self.state_transitions: List[Tuple[CircuitState, CircuitState]] = []

    # -- state helpers ---------------------------------------------------------

    def _transition(self, new_state: CircuitState) -> None:
        if new_state is not self.state:
            self.state_transitions.append((self.state, new_state))
            self.state = new_state

    def _cooldown_elapsed(self) -> bool:
        if self.opened_at is None:
            return False
        return (self.clock() - self.opened_at) >= self.cooldown_seconds

    def _enter_half_open_if_ready(self) -> None:
        if self.state is CircuitState.OPEN and self._cooldown_elapsed():
            self.opened_at = None
            self._half_open_probe_in_flight = False
            self._transition(CircuitState.HALF_OPEN)

    # -- public API ---------------------------------------------------------

    def call(self, operation: Callable[[], Any]) -> Any:
        """Run ``operation`` under breaker protection."""
        self.total_calls += 1
        self._enter_half_open_if_ready()

        if self.state is CircuitState.OPEN:
            self.total_rejected += 1
            raise CircuitOpenError(
                f"circuit is OPEN (retry after {self.cooldown_seconds}s cooldown)"
            )

        if self.state is CircuitState.HALF_OPEN:
            if self._half_open_probe_in_flight:
                self.total_rejected += 1
                raise CircuitOpenError("half-open probe already in flight")
            self._half_open_probe_in_flight = True

        try:
            result = operation()
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self) -> None:
        if self.state is CircuitState.HALF_OPEN:
            self._half_open_probe_in_flight = False
            self.consecutive_failures = 0
            self._transition(CircuitState.CLOSED)
        else:
            self.consecutive_failures = 0

    def _on_failure(self) -> None:
        if self.state is CircuitState.HALF_OPEN:
            self._half_open_probe_in_flight = False
            self.opened_at = self.clock()
            self._transition(CircuitState.OPEN)
            return
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.opened_at = self.clock()
            self._transition(CircuitState.OPEN)

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.opened_at = None
        self._half_open_probe_in_flight = False
