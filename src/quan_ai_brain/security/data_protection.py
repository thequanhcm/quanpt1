"""
V27 M4 - Data Protection (SIMULATED / DEMO-ONLY cipher).

CRITICAL WARNING - DEMO CIPHER, NOT PRODUCTION:
`EncryptionService` implements a XOR-stream cipher whose keystream is derived
from hashlib-based PBKDF2 output. Python's stdlib has NO AES. This is NOT a
secure construction: it lacks authenticated encryption (no MAC/tag), the
keystream reuse properties are weaker than a real block cipher in counter
mode, and nothing here resists a real cryptanalyst. DO NOT use it to protect
real secrets. In production, replace with a vetted library (e.g.
`cryptography` -> AES-256-GCM) and a real KMS/HSM.

Provided:
- EncryptionService: XOR-stream "encryption" (demo), versioned keys,
  key rotation, field-level encrypt/decrypt helpers.
- masking: email / phone / generic token masking utilities.
- FieldCipher: field-level encryption envelopes carrying key_version.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

__all__ = [
    "EncryptionService",
    "EncryptedField",
    "mask_email",
    "mask_phone",
    "mask_token",
    "mask_string",
]

# --- demo cipher constants ---------------------------------------------------
_KEY_BYTES = 32  # 256-bit derived keys
_BLOCK_SIZE = 64  # sha256 output size per keystream block


@dataclass
class EncryptedField:
    """Field-level encryption envelope. Carries the key version for rotation."""

    ciphertext_b64: str
    nonce_b64: str
    key_version: int
    algorithm: str = "xor-stream-hashlib-DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ciphertext_b64": self.ciphertext_b64,
            "nonce_b64": self.nonce_b64,
            "key_version": self.key_version,
            "algorithm": self.algorithm,
        }


class EncryptionService:
    """DEMO-ONLY XOR-stream encryption with versioned keys.

    Keystream construction (per 64-byte block i):
        block_i = sha256(key || nonce || uint32(i))
    Plaintext XOR keystream => ciphertext. Again: this is a teaching-grade
    construction WITHOUT integrity protection. Not production use.
    """

    def __init__(self, master_key: Optional[bytes] = None) -> None:
        if master_key is None:
            master_key = secrets.token_bytes(_KEY_BYTES)
        if len(master_key) < 16:
            raise ValueError("master key must be at least 16 bytes")
        self._keys: Dict[int, bytes] = {1: master_key}
        self._current_version = 1
        self._active_version = 1

    # -- key management -------------------------------------------------
    @property
    def current_key_version(self) -> int:
        return self._current_version

    def rotate_key(self) -> int:
        """Generate a new key version AND make it active for new encryptions.

        Old versions are retained so existing ciphertexts stay decryptable.
        """
        self._current_version += 1
        self._keys[self._current_version] = secrets.token_bytes(_KEY_BYTES)
        self._active_version = self._current_version
        return self._current_version

    def set_active_key_version(self, version: int) -> None:
        if version not in self._keys:
            raise KeyError(f"unknown key version: {version}")
        self._active_version = version

    # -- demo keystream ---------------------------------------------------
    def _keystream(self, key: bytes, nonce: bytes, length: int) -> bytes:
        stream = bytearray()
        counter = 0
        while len(stream) < length:
            block = hashlib.sha256(
                key + nonce + counter.to_bytes(4, "big")
            ).digest()
            stream.extend(block)
            counter += 1
        return bytes(stream[:length])

    def encrypt_bytes(self, plaintext: bytes, nonce: Optional[bytes] = None) -> tuple:
        """XOR plaintext with the hashlib keystream (DEMO cipher)."""
        if not isinstance(plaintext, (bytes, bytearray)):
            raise TypeError("plaintext must be bytes")
        version = self._active_version
        key = self._keys[version]
        nonce = nonce if nonce is not None else secrets.token_bytes(12)
        stream = self._keystream(key, nonce, len(plaintext))
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream))
        return ciphertext, nonce, version

    def decrypt_bytes(self, ciphertext: bytes, nonce: bytes, key_version: int) -> bytes:
        """Reverse of encrypt_bytes using the stored key version."""
        key = self._keys.get(key_version)
        if key is None:
            raise KeyError(f"unknown key version: {key_version}")
        stream = self._keystream(key, nonce, len(ciphertext))
        return bytes(a ^ b for a, b in zip(ciphertext, stream))

    # -- field-level API ---------------------------------------------------
    def encrypt_field(self, plaintext: str) -> EncryptedField:
        """Encrypt a string field into an EncryptedField envelope."""
        pt = plaintext.encode("utf-8")
        ciphertext, nonce, version = self.encrypt_bytes(pt)
        return EncryptedField(
            ciphertext_b64=base64.b64encode(ciphertext).decode("ascii"),
            nonce_b64=base64.b64encode(nonce).decode("ascii"),
            key_version=version,
        )

    def decrypt_field(self, field: EncryptedField) -> str:
        ct = base64.b64decode(field.ciphertext_b64)
        nonce = base64.b64decode(field.nonce_b64)
        return self.decrypt_bytes(ct, nonce, field.key_version).decode("utf-8")


# ---------------------------------------------------------------------------
# Masking utilities
# ---------------------------------------------------------------------------

def mask_email(email: str) -> str:
    """Mask an email: keep first char of local part and the domain.

    "nguyen.van.a@viettel.com.vn" -> "n**********@viettel.com.vn"
    """
    if "@" not in email:
        raise ValueError("not a valid email")
    local, domain = email.rsplit("@", 1)
    if not local:
        raise ValueError("email local part is empty")
    visible = local[0]
    return f"{visible}{'*' * max(len(local) - 1, 1)}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask a phone number: keep country code + last 3 digits.

    "+84912345678" -> "+84******678"
    """
    digits = phone.lstrip("+")
    if not digits.isdigit() or len(digits) < 6:
        raise ValueError("not a valid phone number")
    country = digits[:2]
    last3 = digits[-3:]
    middle = "*" * (len(digits) - 5)
    return f"+{country}{middle}{last3}"


def mask_token(token: str, keep: int = 4) -> str:
    """Mask a secret token, keeping only the last `keep` chars."""
    if keep < 0:
        raise ValueError("keep must be >= 0")
    if len(token) <= keep:
        return "*" * len(token)
    return "*" * (len(token) - keep) + token[-keep:]


def mask_string(value: str, visible_head: int = 1, visible_tail: int = 1) -> str:
    """Generic mask keeping head+tail characters."""
    if visible_head < 0 or visible_tail < 0:
        raise ValueError("visible counts must be >= 0")
    if len(value) <= visible_head + visible_tail:
        return "*" * len(value)
    middle = "*" * (len(value) - visible_head - visible_tail)
    return value[:visible_head] + middle + value[-visible_tail:]
