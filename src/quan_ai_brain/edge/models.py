"""Data models for QUAN AI BRAIN — Edge Device & Data Transfer System.

Defines schemas for device registration, chunked data transfers, integrity verification,
manifest hashing, and secure release packaging.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any


class DataClassification(str, Enum):
    """Classification tiers for data transferred across the PC-Edge boundary."""
    PUBLIC = "PUBLIC"
    OPERATIONAL = "OPERATIONAL"
    SENSITIVE = "SENSITIVE"
    AUTHENTICATION_SECRET = "AUTHENTICATION_SECRET"  # Strictly blocked from transmission
    EXECUTABLE_CODE = "EXECUTABLE_CODE"              # Requires release signing and approval


class TransferDirection(str, Enum):
    """Direction of the data transfer."""
    CORE_TO_EDGE = "CORE_TO_EDGE"
    EDGE_TO_CORE = "EDGE_TO_CORE"
    EDGE_TO_EDGE = "EDGE_TO_EDGE"


class TransferStatus(str, Enum):
    """Deterministic status lifecycle of a transfer transaction."""
    INITIATED = "INITIATED"
    IN_PROGRESS = "IN_PROGRESS"
    STAGED = "STAGED"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED_SENSITIVE = "BLOCKED_SENSITIVE"


@dataclass
class DeviceIdentity:
    """Registered identity and authorization bounds for an Edge device."""
    device_id: str
    device_type: str = "RASPBERRY_PI_5"
    device_version: str = "0.2.0"
    protocol_version: str = "1.0"
    connection_status: str = "ONLINE"
    last_seen_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    capabilities: list[str] = field(default_factory=lambda: [
        "display_kiosk",
        "audio_input",
        "audio_output",
        "avatar_visemes",
        "relays",
        "servos",
    ])
    authorized_data_scopes: list[str] = field(default_factory=lambda: [
        "avatar_assets",
        "kiosk_ui",
        "telemetry",
        "logs",
        "releases",
        "tasks",
    ])
    allowed_update_channels: list[str] = field(default_factory=lambda: ["stable"])
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceIdentity:
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class TransferChunk:
    """A single sequential slice of a data transfer."""
    transfer_id: str
    chunk_index: int
    total_chunks: int
    size_bytes: int
    chunk_hash: str  # SHA-256 of raw chunk bytes
    data_b64: str    # Base64 encoded chunk content

    def verify_hash(self) -> bool:
        import base64
        try:
            raw = base64.b64decode(self.data_b64)
            computed = hashlib.sha256(raw).hexdigest()
            return computed == self.chunk_hash
        except Exception:
            return False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransferChunk:
        return cls(
            transfer_id=str(data["transfer_id"]),
            chunk_index=int(data["chunk_index"]),
            total_chunks=int(data["total_chunks"]),
            size_bytes=int(data["size_bytes"]),
            chunk_hash=str(data["chunk_hash"]),
            data_b64=str(data["data_b64"]),
        )


@dataclass
class TransferManifest:
    """Cryptographic manifest governing an entire data transfer session."""
    transfer_id: str
    source_device_id: str
    target_device_id: str
    filename: str
    data_type: str
    total_size_bytes: int
    total_chunks: int
    content_hash: str  # SHA-256 of the complete reconstructed payload
    direction: TransferDirection = TransferDirection.CORE_TO_EDGE
    classification: DataClassification = DataClassification.OPERATIONAL
    schema_version: str = "1.0"
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: TransferStatus = TransferStatus.INITIATED
    approval_status: str = "APPROVED_AUTOMATIC"
    error_message: str | None = None
    chunks_received: list[int] = field(default_factory=list)
    staging_path: str | None = None

    def is_expired(self) -> bool:
        try:
            exp = datetime.fromisoformat(self.expires_at_utc)
            now = datetime.now(timezone.utc)
            return now > exp
        except Exception:
            return False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["direction"] = self.direction.value
        d["classification"] = self.classification.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransferManifest:
        data_copy = dict(data)
        if "direction" in data_copy and isinstance(data_copy["direction"], str):
            data_copy["direction"] = TransferDirection(data_copy["direction"])
        if "classification" in data_copy and isinstance(data_copy["classification"], str):
            data_copy["classification"] = DataClassification(data_copy["classification"])
        if "status" in data_copy and isinstance(data_copy["status"], str):
            data_copy["status"] = TransferStatus(data_copy["status"])
        known = {k: v for k, v in data_copy.items() if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class ReleaseManifest:
    """Signed, verifiable software package for Raspberry Pi 5 Edge Client."""
    release_id: str
    version: str
    required_core_version: str = "0.2.0"
    required_protocol_version: str = "1.0"
    target_arch: str = "aarch64"
    target_os: str = "linux"
    files: dict[str, str] = field(default_factory=dict)       # path -> SHA-256 hash
    file_sizes: dict[str, int] = field(default_factory=dict)  # path -> byte size
    total_size_bytes: int = 0
    changelog: str = ""
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signature: str = ""                                       # HMAC-SHA256 of canonical manifest
    health_check_command: str = "python3 -m unittest discover tests"
    rollback_target_version: str | None = None
    status: str = "CREATED"                                   # CREATED, VALIDATED, APPROVED, STAGED, ACTIVE, ROLLED_BACK

    def compute_canonical_string(self) -> str:
        """Produce a deterministic string representation for signing."""
        sorted_files = sorted(self.files.items())
        files_repr = ";".join(f"{p}:{h}" for p, h in sorted_files)
        return f"{self.release_id}:{self.version}:{self.required_protocol_version}:{self.total_size_bytes}:{files_repr}"

    def sign(self, secret_key: str) -> str:
        canonical = self.compute_canonical_string().encode("utf-8")
        import hmac
        sig = hmac.new(secret_key.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
        self.signature = sig
        return sig

    def verify_signature(self, secret_key: str) -> bool:
        if not self.signature:
            return False
        canonical = self.compute_canonical_string().encode("utf-8")
        import hmac
        expected = hmac.new(secret_key.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReleaseManifest:
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)
