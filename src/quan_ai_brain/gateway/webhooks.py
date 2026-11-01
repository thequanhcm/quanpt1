"""
V28.4 — Webhook Dispatcher (stdlib-only, no real HTTP)

Provides:
- :class:`WebhookDispatcher`: register endpoints (fake URLs), subscribe events
- HMAC-SHA256 payload signing with ``X-Signature`` header (fake delivery)
- Delivery with retry: exponential backoff + jitter, DLQ after max retries
- :func:`verify_signature` for receivers (tests) to validate signatures

IMPORTANT SCOPE NOTE (honesty):
No real HTTP request is ever sent. "Delivery" means handing a signed payload
to a registered in-memory fake endpoint callable. URLs are opaque strings
(e.g. ``https://hooks.example.test/...``) — they are never resolved. Secrets
in tests are TEST-ONLY keys (e.g. ``b"test-secret"``), never real
credentials. Backoff sleeps are avoided in tests by an injectable ``sleeper``
hook.

Version: V28.4
Author: QUAN AI BRAIN Team
"""

from __future__ import annotations

import hashlib
import hmac
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

__all__ = [
    "WebhookError",
    "WebhookEndpoint",
    "DeliveryResult",
    "WebhookDispatcher",
    "verify_signature",
    "compute_signature",
]

SIGNATURE_HEADER = "X-Signature"
TIMESTAMP_HEADER = "X-Webhook-Timestamp"


class WebhookError(Exception):
    """Base error for webhook module."""


# ---------------------------------------------------------------------------
# Signing helpers
# ---------------------------------------------------------------------------

def compute_signature(payload: bytes, secret: bytes) -> str:
    """HMAC-SHA256 hex digest of the raw payload bytes."""
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def verify_signature(payload: bytes, secret: bytes, signature: str) -> bool:
    """Constant-time comparison of a provided signature against the computed one."""
    expected = compute_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WebhookEndpoint:
    """A registered webhook endpoint (fake URL, test secret)."""

    endpoint_id: str
    url: str
    events: List[str]
    secret: str
    active: bool = True
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    deliveries_ok: int = 0
    deliveries_failed: int = 0


@dataclass
class DeliveryResult:
    """Outcome of one delivery attempt chain for one endpoint."""

    endpoint_id: str
    event: str
    success: bool
    attempts: int
    status_codes: List[int] = field(default_factory=list)
    signature: str = ""
    error: Optional[str] = None
    to_dlq: bool = False


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

class WebhookDispatcher:
    """Register fake endpoints, sign payloads, "deliver" with retry/DLQ.

    The dispatcher simulates HTTP POST semantics:
      - each registered endpoint gets a *fake transport* (a callable returning
        an HTTP-ish status code int); default transport accepts everything
        (200).
      - non-2xx responses trigger retries with exponential backoff + jitter.
      - after ``max_retries`` failed attempts the delivery goes to the DLQ.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_backoff: float = 0.05,
        jitter_fraction: float = 0.2,
        rng: Optional[random.Random] = None,
        sleeper: Optional[Callable[[float], None]] = None,
    ) -> None:
        if max_retries < 1:
            raise WebhookError("max_retries must be >= 1")
        self.max_retries = int(max_retries)
        self.base_backoff = float(base_backoff)
        self.jitter_fraction = float(jitter_fraction)
        self._rng = rng or random.Random(42)  # deterministic default
        self._sleeper = sleeper or (lambda _seconds: None)
        self._endpoints: Dict[str, WebhookEndpoint] = {}
        self._transports: Dict[str, Callable[[str, bytes, Dict[str, str]], int]] = {}
        self._deliveries: List[Dict[str, Any]] = []
        self._dlq: List[Dict[str, Any]] = []
        self._id_seq = 0

    # -- registration ---------------------------------------------------------

    def register(
        self,
        url: str,
        events: List[str],
        secret: str = "test-secret",
    ) -> WebhookEndpoint:
        if not url or not url.startswith(("http://", "https://")):
            raise WebhookError(f"invalid (fake) webhook URL: {url!r}")
        if not events:
            raise WebhookError("endpoint must subscribe to at least one event")
        self._id_seq += 1
        endpoint_id = f"whk-{self._id_seq:04d}"
        endpoint = WebhookEndpoint(
            endpoint_id=endpoint_id,
            url=url,
            events=list(events),
            secret=secret,
        )
        self._endpoints[endpoint_id] = endpoint
        self._transports[endpoint_id] = lambda url_, body_, headers_: 200
        return endpoint

    def set_transport(
        self,
        endpoint_id: str,
        transport: Callable[[str, bytes, Dict[str, str]], int],
    ) -> None:
        """Replace the fake transport for an endpoint (used to simulate 500s)."""
        if endpoint_id not in self._endpoints:
            raise WebhookError(f"unknown endpoint '{endpoint_id}'")
        self._transports[endpoint_id] = transport

    def unregister(self, endpoint_id: str) -> bool:
        removed = self._endpoints.pop(endpoint_id, None) is not None
        self._transports.pop(endpoint_id, None)
        return removed

    def get(self, endpoint_id: str) -> Optional[WebhookEndpoint]:
        return self._endpoints.get(endpoint_id)

    def endpoints(self) -> List[WebhookEndpoint]:
        return list(self._endpoints.values())

    def enable(self, endpoint_id: str) -> None:
        self._require(endpoint_id).active = True

    def disable(self, endpoint_id: str) -> None:
        self._require(endpoint_id).active = False

    # -- delivery ----------------------------------------------------------------

    def dispatch(self, event: str, payload: Dict[str, Any]) -> List[DeliveryResult]:
        """Deliver ``event`` to all matching active endpoints."""
        if not isinstance(payload, dict):
            raise WebhookError("payload must be a dict")
        results: List[DeliveryResult] = []
        for endpoint in self._endpoints.values():
            if not endpoint.active:
                continue
            if event not in endpoint.events:
                continue
            results.append(self._deliver_with_retry(endpoint, event, payload))
        return results

    def _deliver_with_retry(
        self, endpoint: WebhookEndpoint, event: str, payload: Dict[str, Any]
    ) -> DeliveryResult:
        envelope = {
            "event": event,
            "endpoint_id": endpoint.endpoint_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        body = json.dumps(envelope, sort_keys=True).encode("utf-8")
        signature = compute_signature(body, endpoint.secret.encode("utf-8"))
        headers = {
            SIGNATURE_HEADER: signature,
            TIMESTAMP_HEADER: envelope["timestamp"],
            "Content-Type": "application/json",
        }

        transport = self._transports[endpoint.endpoint_id]
        status_codes: List[int] = []
        attempts = 0
        last_error: Optional[str] = None

        while attempts < self.max_retries:
            attempts += 1
            try:
                status = transport(endpoint.url, body, headers)
            except Exception as exc:  # noqa: BLE001 — transport crash = failed attempt
                status = 0
                last_error = f"transport exception: {type(exc).__name__}: {exc}"
            status_codes.append(status)
            self._deliveries.append(
                {
                    "endpoint_id": endpoint.endpoint_id,
                    "event": event,
                    "attempt": attempts,
                    "status": status,
                }
            )
            if 200 <= status < 300:
                endpoint.deliveries_ok += 1
                return DeliveryResult(
                    endpoint_id=endpoint.endpoint_id,
                    event=event,
                    success=True,
                    attempts=attempts,
                    status_codes=status_codes,
                    signature=signature,
                )
            last_error = last_error or f"HTTP {status}"
            if attempts < self.max_retries:
                delay = self._backoff_delay(attempts)
                self._sleeper(delay)

        endpoint.deliveries_failed += 1
        dlq_entry = {
            "endpoint_id": endpoint.endpoint_id,
            "event": event,
            "payload": payload,
            "signature": signature,
            "attempts": attempts,
            "status_codes": status_codes,
            "error": last_error,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        self._dlq.append(dlq_entry)
        return DeliveryResult(
            endpoint_id=endpoint.endpoint_id,
            event=event,
            success=False,
            attempts=attempts,
            status_codes=status_codes,
            signature=signature,
            error=last_error,
            to_dlq=True,
        )

    def _backoff_delay(self, attempt: int) -> float:
        """Exponential backoff with additive jitter: base * 2^(attempt-1) ± jitter."""
        base = self.base_backoff * (2 ** (attempt - 1))
        jitter = base * self.jitter_fraction
        return base + self._rng.uniform(-jitter, jitter)

    # -- inspection ---------------------------------------------------------------

    def deliveries_for(self, endpoint_id: str) -> List[Dict[str, Any]]:
        return [d for d in self._deliveries if d["endpoint_id"] == endpoint_id]

    def dead_letter_queue(self) -> List[Dict[str, Any]]:
        return list(self._dlq)

    def retry_dlq(self, event: Optional[str] = None) -> int:
        """Re-dispatch DLQ entries (optionally for one event). Returns count retried."""
        entries = [e for e in self._dlq if event is None or e["event"] == event]
        self._dlq = [e for e in self._dlq if not (event is None or e["event"] == event)]
        for entry in entries:
            self.dispatch(entry["event"], entry["payload"])
        return len(entries)

    def stats(self) -> Dict[str, int]:
        ok = sum(1 for d in self._deliveries if 200 <= d["status"] < 300)
        return {
            "endpoints": len(self._endpoints),
            "delivery_attempts_total": len(self._deliveries),
            "delivery_attempts_ok": ok,
            "delivery_attempts_failed": len(self._deliveries) - ok,
            "dlq_total": len(self._dlq),
        }

    # -- internals ---------------------------------------------------------------

    def _require(self, endpoint_id: str) -> WebhookEndpoint:
        endpoint = self._endpoints.get(endpoint_id)
        if endpoint is None:
            raise WebhookError(f"unknown endpoint '{endpoint_id}'")
        return endpoint
