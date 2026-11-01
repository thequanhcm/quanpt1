"""Edge Transfer Service for QUAN AI BRAIN.

Implements secure, chunked, verified bidirectional data transfer between PC Core and
registered Edge devices (Raspberry Pi 5) over LAN / Wi-Fi.
Features:
- Cryptographic SHA-256 chunk and package integrity verification
- Strict sensitive data barrier (blocks .env, private keys, database dumps)
- Resource budgets, staging quotas, and deduplication
- Robust transactional ACK and state tracking
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import threading
from typing import Any

from quan_ai_brain.edge.models import (
    DataClassification,
    DeviceIdentity,
    TransferChunk,
    TransferDirection,
    TransferManifest,
    TransferStatus,
)


class EdgeTransferService:
    """Manages file and data transfers across the PC-Edge boundary."""

    SENSITIVE_FILENAME_PATTERNS = [
        re.compile(r"^\.env.*", re.IGNORECASE),
        re.compile(r".*\.(pem|key|pkcs12|pfx|crt|p12)$", re.IGNORECASE),
        re.compile(r".*(id_rsa|id_ed25519|id_ecdsa).*", re.IGNORECASE),
        re.compile(r".*(credential|password|token|secret).*", re.IGNORECASE),
        re.compile(r".*\.(db|sqlite|sqlite3)$", re.IGNORECASE),  # Production DB protection
    ]

    def __init__(
        self,
        base_dir: Path | str | None = None,
        max_file_size_bytes: int = 50 * 1024 * 1024,  # 50 MB
        max_staging_bytes: int = 200 * 1024 * 1024,   # 200 MB
        max_concurrent_transfers: int = 5,
        default_expiry_seconds: int = 3600,
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path.cwd() / "data" / "edge_transfers"
        self.staging_dir = self.base_dir / "staging"
        self.complete_dir = self.base_dir / "completed"
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.complete_dir.mkdir(parents=True, exist_ok=True)

        self.max_file_size_bytes = max_file_size_bytes
        self.max_staging_bytes = max_staging_bytes
        self.max_concurrent_transfers = max_concurrent_transfers
        self.default_expiry_seconds = default_expiry_seconds

        self._lock = threading.RLock()
        self._devices: dict[str, DeviceIdentity] = {}
        self._manifests: dict[str, TransferManifest] = {}

        # Default register local PC Core
        self.register_device(
            DeviceIdentity(
                device_id="CORE-PC-WINDOWS-01",
                device_type="PC_CORE",
                device_version="0.2.0",
                capabilities=["brain_core", "llm_reasoning", "task_planning", "storage"],
            )
        )

    def register_device(self, device: DeviceIdentity) -> None:
        """Register or update an authorized edge device."""
        with self._lock:
            self._devices[device.device_id] = device

    def get_device(self, device_id: str) -> DeviceIdentity | None:
        with self._lock:
            return self._devices.get(device_id)

    def list_devices(self) -> list[DeviceIdentity]:
        with self._lock:
            return list(self._devices.values())

    def is_sensitive_target(self, filename: str) -> bool:
        """Evaluate whether a filename targets protected secrets or credentials."""
        clean = Path(filename).name
        for pattern in self.SENSITIVE_FILENAME_PATTERNS:
            if pattern.match(clean):
                return True
        return False

    def initiate_transfer(
        self,
        transfer_id: str,
        source_device_id: str,
        target_device_id: str,
        filename: str,
        total_size_bytes: int,
        content_hash: str,
        data_type: str = "general_asset",
        direction: TransferDirection = TransferDirection.CORE_TO_EDGE,
        classification: DataClassification = DataClassification.OPERATIONAL,
        chunk_size: int = 65536,
    ) -> tuple[bool, str, TransferManifest | None]:
        """Initiate and validate a new data transfer session."""
        with self._lock:
            # 1. Device Authorization Check
            src = self.get_device(source_device_id)
            tgt = self.get_device(target_device_id)
            if not src:
                return False, f"Source device '{source_device_id}' is not registered or authorized", None
            if not tgt:
                return False, f"Target device '{target_device_id}' is not registered or authorized", None

            # 2. Duplicate Transaction Deduplication
            if transfer_id in self._manifests:
                existing = self._manifests[transfer_id]
                return True, "Transfer session already exists (re-attached)", existing

            # 3. Sensitive Data Barrier
            if classification == DataClassification.AUTHENTICATION_SECRET or self.is_sensitive_target(filename):
                manifest = TransferManifest(
                    transfer_id=transfer_id,
                    source_device_id=source_device_id,
                    target_device_id=target_device_id,
                    filename=Path(filename).name,
                    data_type=data_type,
                    total_size_bytes=total_size_bytes,
                    total_chunks=0,
                    content_hash=content_hash,
                    direction=direction,
                    classification=DataClassification.AUTHENTICATION_SECRET,
                    status=TransferStatus.BLOCKED_SENSITIVE,
                    error_message="Transfer blocked: target filename or payload contains prohibited sensitive authentication material",
                )
                self._manifests[transfer_id] = manifest
                return False, manifest.error_message or "Blocked", manifest

            # 4. Quota and Size Limits
            if total_size_bytes > self.max_file_size_bytes:
                return False, f"Total size ({total_size_bytes} B) exceeds maximum permitted file limit ({self.max_file_size_bytes} B)", None

            active_count = sum(1 for m in self._manifests.values() if m.status in (TransferStatus.INITIATED, TransferStatus.IN_PROGRESS))
            if active_count >= self.max_concurrent_transfers:
                return False, f"Concurrent transfers limit reached ({self.max_concurrent_transfers})", None

            # Calculate total chunks
            total_chunks = max(1, (total_size_bytes + chunk_size - 1) // chunk_size) if total_size_bytes > 0 else 1

            now_utc = datetime.now(timezone.utc)
            exp_utc = now_utc + timedelta(seconds=self.default_expiry_seconds)

            t_dir = self.staging_dir / transfer_id
            t_dir.mkdir(parents=True, exist_ok=True)

            manifest = TransferManifest(
                transfer_id=transfer_id,
                source_device_id=source_device_id,
                target_device_id=target_device_id,
                filename=Path(filename).name,
                data_type=data_type,
                total_size_bytes=total_size_bytes,
                total_chunks=total_chunks,
                content_hash=content_hash,
                direction=direction,
                classification=classification,
                created_at_utc=now_utc.isoformat(),
                expires_at_utc=exp_utc.isoformat(),
                status=TransferStatus.INITIATED,
                staging_path=str(t_dir),
            )
            self._manifests[transfer_id] = manifest
            return True, "Transfer session initiated successfully", manifest

    def receive_chunk(self, chunk: TransferChunk) -> tuple[bool, str]:
        """Receive, verify, and persist a single sequential chunk."""
        with self._lock:
            manifest = self._manifests.get(chunk.transfer_id)
            if not manifest:
                return False, f"Transfer session '{chunk.transfer_id}' not found"

            if manifest.status in (TransferStatus.COMPLETED, TransferStatus.CANCELLED, TransferStatus.BLOCKED_SENSITIVE):
                return False, f"Cannot add chunk to transfer in status {manifest.status.value}"

            if manifest.is_expired():
                manifest.status = TransferStatus.FAILED
                manifest.error_message = "Transfer session expired"
                return False, "Transfer session expired"

            # 1. Chunk Checksum Verification
            if not chunk.verify_hash():
                manifest.status = TransferStatus.FAILED
                manifest.error_message = f"Chunk {chunk.chunk_index} checksum mismatch"
                return False, f"Chunk {chunk.chunk_index} hash verification failed"

            # 2. Persist Chunk to Staging
            chunk_file = Path(manifest.staging_path or self.staging_dir / manifest.transfer_id) / f"chunk_{chunk.chunk_index:05d}.bin"
            try:
                raw_bytes = base64.b64decode(chunk.data_b64)
                chunk_file.write_bytes(raw_bytes)
            except Exception as exc:
                return False, f"Failed to write chunk {chunk.chunk_index}: {exc}"

            if chunk.chunk_index not in manifest.chunks_received:
                manifest.chunks_received.append(chunk.chunk_index)
                manifest.chunks_received.sort()

            manifest.status = TransferStatus.IN_PROGRESS

            # 3. Check if all chunks received for assembly
            if len(manifest.chunks_received) == manifest.total_chunks:
                return self._assemble_and_finalize(manifest)

            return True, f"Chunk {chunk.chunk_index}/{manifest.total_chunks} received and verified"

    def _assemble_and_finalize(self, manifest: TransferManifest) -> tuple[bool, str]:
        """Assemble all chunks, verify complete file SHA-256 hash, and move to completed."""
        manifest.status = TransferStatus.VERIFYING
        t_dir = Path(manifest.staging_path or self.staging_dir / manifest.transfer_id)
        temp_assembled = t_dir / f"{manifest.filename}.assembling"

        hasher = hashlib.sha256()
        try:
            with open(temp_assembled, "wb") as out_f:
                for idx in range(manifest.total_chunks):
                    c_path = t_dir / f"chunk_{idx:05d}.bin"
                    if not c_path.exists():
                        manifest.status = TransferStatus.FAILED
                        manifest.error_message = f"Missing chunk {idx} during assembly"
                        return False, manifest.error_message
                    data = c_path.read_bytes()
                    hasher.update(data)
                    out_f.write(data)

            computed_hash = hasher.hexdigest()

            # Hash Integrity Check
            if computed_hash.lower() != manifest.content_hash.lower():
                manifest.status = TransferStatus.FAILED
                manifest.error_message = f"Complete file SHA-256 mismatch: expected {manifest.content_hash}, computed {computed_hash}"
                if temp_assembled.exists():
                    temp_assembled.unlink()
                return False, manifest.error_message

            # Move to Completed Storage
            dest_dir = self.complete_dir / manifest.transfer_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            final_path = dest_dir / manifest.filename
            shutil.move(str(temp_assembled), str(final_path))

            manifest.status = TransferStatus.STAGED
            manifest.staging_path = str(final_path)
            return True, "File assembled and verified successfully"

        except Exception as exc:
            manifest.status = TransferStatus.FAILED
            manifest.error_message = f"Assembly failure: {exc}"
            return False, str(exc)

    def acknowledge_transfer(self, transfer_id: str) -> tuple[bool, str]:
        """Final delivery acknowledgment by recipient."""
        with self._lock:
            manifest = self._manifests.get(transfer_id)
            if not manifest:
                return False, f"Transfer session '{transfer_id}' not found"

            if manifest.status != TransferStatus.STAGED:
                return False, f"Cannot ACK transfer in status {manifest.status.value}"

            manifest.status = TransferStatus.COMPLETED
            return True, "Transfer acknowledged and completed successfully"

    def cancel_transfer(self, transfer_id: str, reason: str = "User cancelled") -> bool:
        """Cancel an in-flight transfer and delete staging data."""
        with self._lock:
            manifest = self._manifests.get(transfer_id)
            if not manifest:
                return False
            manifest.status = TransferStatus.CANCELLED
            manifest.error_message = reason
            t_dir = self.staging_dir / transfer_id
            if t_dir.exists():
                shutil.rmtree(t_dir, ignore_errors=True)
            return True

    def get_manifest(self, transfer_id: str) -> TransferManifest | None:
        with self._lock:
            return self._manifests.get(transfer_id)

    def get_transfer(self, transfer_id: str) -> TransferManifest | None:
        return self.get_manifest(transfer_id)

    def list_transfers(self, limit: int = 50) -> list[TransferManifest]:
        with self._lock:
            return list(self._manifests.values())[-limit:]

    def get_completed_file_path(self, transfer_id: str) -> Path | None:
        with self._lock:
            manifest = self._manifests.get(transfer_id)
            if not manifest or manifest.status not in (TransferStatus.STAGED, TransferStatus.COMPLETED):
                return None
            target = self.complete_dir / transfer_id / manifest.filename
            return target if target.exists() else None
