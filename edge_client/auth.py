"""Anti-Replay HMAC Authentication Module for Raspberry Pi 5 Edge Client.

Implements mutual authentication between PC Central Brain Core and Edge Client.
Zero storage of production private keys or database passwords on Edge.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import secrets
import time
from typing import Any


class EdgeHMACAuth:
    """Handles token signing, nonce generation, and anti-replay verification."""

    HEADER_DEVICE_ID = "X-Quan-Device-Id"
    HEADER_TIMESTAMP = "X-Quan-Timestamp-Utc"
    HEADER_NONCE = "X-Quan-Nonce"
    HEADER_SIGNATURE = "X-Quan-Signature"

    def __init__(self, device_id: str, secret: str, max_drift_seconds: float = 10.0) -> None:
        self.device_id = device_id
        self.secret = secret
        self.max_drift_seconds = max_drift_seconds
        # In-memory consumed nonces: maps nonce -> expire_timestamp
        self._consumed_nonces: dict[str, float] = {}

    def generate_nonce(self) -> str:
        """Generate a cryptographically secure 16-byte random hex string."""
        return secrets.token_hex(16)

    def compute_signature(self, timestamp_utc: str, nonce: str, payload_bytes: bytes) -> str:
        """Compute HMAC-SHA256 over canonical header and payload hash."""
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        canonical_msg = f"{self.device_id}:{timestamp_utc}:{nonce}:{payload_hash}".encode("utf-8")
        secret_bytes = self.secret.encode("utf-8")
        return hmac.new(secret_bytes, canonical_msg, hashlib.sha256).hexdigest()

    def create_signed_headers(self, payload_bytes: bytes = b"") -> dict[str, str]:
        """Generate all required HTTP headers for an authenticated Edge request."""
        now_ts = datetime.now(timezone.utc).isoformat()
        nonce = self.generate_nonce()
        sig = self.compute_signature(now_ts, nonce, payload_bytes)
        return {
            self.HEADER_DEVICE_ID: self.device_id,
            self.HEADER_TIMESTAMP: now_ts,
            self.HEADER_NONCE: nonce,
            self.HEADER_SIGNATURE: sig,
        }

    def verify_request(
        self,
        headers: dict[str, str],
        payload_bytes: bytes = b"",
        current_time_epoch: float | None = None,
    ) -> tuple[bool, str]:
        """Verify inbound request headers against replay, clock drift, and signature forgery."""
        device_id = headers.get(self.HEADER_DEVICE_ID, "")
        ts_str = headers.get(self.HEADER_TIMESTAMP, "")
        nonce = headers.get(self.HEADER_NONCE, "")
        sig = headers.get(self.HEADER_SIGNATURE, "")

        if not all([device_id, ts_str, nonce, sig]):
            return False, "MISSING_REQUIRED_HEADERS"

        if device_id != self.device_id:
            return False, f"DEVICE_ID_MISMATCH: expected '{self.device_id}', got '{device_id}'"

        # 1. Verify Timestamp & Clock Drift
        try:
            req_time = datetime.fromisoformat(ts_str)
            if req_time.tzinfo is None:
                req_time = req_time.replace(tzinfo=timezone.utc)
            req_epoch = req_time.timestamp()
        except Exception:
            return False, "INVALID_TIMESTAMP_FORMAT"

        now_epoch = current_time_epoch if current_time_epoch is not None else time.time()
        drift = abs(now_epoch - req_epoch)
        if drift > self.max_drift_seconds:
            return False, f"CLOCK_DRIFT_EXCEEDED: {drift:.2f}s > {self.max_drift_seconds}s"

        # 2. Check Replay Prevention (Nonce check)
        self._purge_expired_nonces(now_epoch)
        if nonce in self._consumed_nonces:
            return False, "REPLAY_DETECTED_NONCE_ALREADY_USED"

        # 3. Verify Signature
        expected_sig = self.compute_signature(ts_str, nonce, payload_bytes)
        if not hmac.compare_digest(sig, expected_sig):
            return False, "INVALID_SIGNATURE"

        # Record consumed nonce with TTL
        self._consumed_nonces[nonce] = now_epoch + (self.max_drift_seconds * 2)
        return True, "VALID"

    def _purge_expired_nonces(self, current_epoch: float) -> None:
        """Purge nonces that have passed the replay time window."""
        expired = [n for n, expire_ts in self._consumed_nonces.items() if expire_ts < current_epoch]
        for n in expired:
            self._consumed_nonces.pop(n, None)
