"""
MFA TOTP helpers (M1 authentication).

RFC 6238 TOTP re-implemented with stdlib hmac/hashlib/base64/struct only.
No external dependency (pyotp etc.) is used.

SIMULATED/simple implementation for the V27 security skeleton: it follows
RFC 4226/6238 but omits production concerns such as secret storage in an HSM,
replay-attack tracking, and per-attempt rate limiting on OTP verification.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import Optional

__all__ = [
    "generate_totp_secret",
    "hotp_at",
    "totp_now",
    "verify_totp",
    "provisioning_uri",
]

_B32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def _decode_base32(secret: str) -> bytes:
    cleaned = "".join(ch for ch in secret.upper() if ch in _B32_ALPHABET)
    if not cleaned:
        raise ValueError("empty TOTP secret")
    pad = (-len(cleaned)) % 8
    return base64.b32decode(cleaned + "=" * pad)


def generate_totp_secret(num_bytes: int = 20) -> str:
    """Random TOTP secret; RFC 4226 recommends at least 160 bits."""
    raw = secrets.token_bytes(num_bytes)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def hotp_at(secret_b32: str, counter: int, digits: int = 6) -> str:
    """RFC 4226 HOTP value at `counter`, implemented with hmac."""
    key = _decode_base32(secret_b32)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    )
    return str(code % (10 ** digits)).zfill(digits)


def totp_now(secret_b32: str, timestamp: Optional[float] = None, step: int = 30, digits: int = 6) -> str:
    """RFC 6238 TOTP at `timestamp` (defaults to current wall-clock time)."""
    if timestamp is None:
        timestamp = time.time()
    counter = int(timestamp // step)
    return hotp_at(secret_b32, counter, digits=digits)


def verify_totp(
    secret_b32: str,
    code: str,
    timestamp: Optional[float] = None,
    step: int = 30,
    digits: int = 6,
    window: int = 1,
) -> bool:
    """Verify a TOTP code with a +/- `window` step tolerance (RFC 6238 section 5.2)."""
    if timestamp is None:
        timestamp = time.time()
    counter = int(timestamp // step)
    candidates = [hotp_at(secret_b32, counter + off, digits=digits) for off in range(-window, window + 1)]
    return any(hmac.compare_digest(code, candidate) for candidate in candidates)


def provisioning_uri(secret_b32: str, account: str = "user", issuer: str = "QUAN-AI-BRAIN") -> str:
    """Standard otpauth:// URI for QR provisioning (informational only)."""
    return f"otpauth://totp/{issuer}:{account}?secret={secret_b32}&issuer={issuer}"
