"""Unit and Integration Tests for EdgeTransferService (D01 - D10).

Verifies:
- D01: Small file transfer PC -> Pi with SHA-256 hash integrity and ACK.
- D02: Small file transfer Pi -> PC, verify origin and prevent system file overwrite.
- D03: Large packet transfer with chunking and progress.
- D04: Disrupted / incomplete transfer handling.
- D05: Bad hash detection and rejection.
- D06: File size exceeding quota / limit rejection.
- D07: Unauthorized device rejection.
- D08: Duplicate transaction ID handling (idempotency).
- D09: Sensitive file barrier (blocking .env, *.key, *.pem, id_rsa*, credentials).
- D10: Multi-device scope separation (device_id authorization).
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import tempfile
import pytest

from quan_ai_brain.edge.models import (
    DataClassification,
    DeviceIdentity,
    TransferChunk,
    TransferDirection,
    TransferStatus,
)
from quan_ai_brain.edge.transfer_service import EdgeTransferService


@pytest.fixture
def transfer_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "edge_data"
        service = EdgeTransferService(
            base_dir=base_dir,
            max_file_size_bytes=100_000,  # 100 KB limit for testing
        )
        # Register a valid Pi 5 device
        pi5 = DeviceIdentity(
            device_id="PI5-ARM64-EDGE-01",
            device_type="RASPBERRY_PI_5",
            device_version="0.2.0",
            capabilities=["kiosk_display", "audio_io", "avatar_render"],
        )
        service.register_device(pi5)
        yield service, base_dir, pi5


def test_d01_pc_to_pi_small_file_transfer(transfer_env):
    """D01: Transfer small file from PC to Pi with SHA-256 integrity and ACK."""
    service, base_dir, pi5 = transfer_env
    content = b"Avatar Model F configuration payload for Raspberry Pi 5"
    expected_hash = hashlib.sha256(content).hexdigest()

    ok, msg, manifest = service.initiate_transfer(
        transfer_id="XFER-D01-001",
        source_device_id="CORE-PC-WINDOWS-01",
        target_device_id="PI5-ARM64-EDGE-01",
        filename="model_f_config.json",
        total_size_bytes=len(content),
        content_hash=expected_hash,
        data_type="avatar_asset",
        direction=TransferDirection.CORE_TO_EDGE,
        classification=DataClassification.OPERATIONAL,
        chunk_size=1024,
    )

    assert ok is True
    assert manifest is not None
    assert manifest.status == TransferStatus.INITIATED
    assert manifest.content_hash == expected_hash

    # Deliver chunk 0
    chunk = TransferChunk(
        transfer_id="XFER-D01-001",
        chunk_index=0,
        total_chunks=1,
        size_bytes=len(content),
        chunk_hash=expected_hash,
        data_b64=base64.b64encode(content).decode("utf-8"),
    )
    rec_ok, rec_msg = service.receive_chunk(chunk)
    assert rec_ok is True

    # After single chunk assembly, status should be STAGED
    current = service.get_transfer(manifest.transfer_id)
    assert current.status == TransferStatus.STAGED

    # Acknowledge transfer
    ack_ok, ack_msg = service.acknowledge_transfer(manifest.transfer_id)
    assert ack_ok is True
    assert service.get_transfer(manifest.transfer_id).status == TransferStatus.COMPLETED


def test_d02_pi_to_pc_telemetry_transfer(transfer_env):
    """D02: Transfer telemetry from Pi to PC, verify origin and prevent overwrite."""
    service, base_dir, pi5 = transfer_env
    content = b'{"cpu_temp": 48.2, "ram_usage_pct": 32.1}'
    expected_hash = hashlib.sha256(content).hexdigest()

    ok, msg, manifest = service.initiate_transfer(
        transfer_id="XFER-D02-001",
        source_device_id="PI5-ARM64-EDGE-01",
        target_device_id="CORE-PC-WINDOWS-01",
        filename="telemetry_metrics.json",
        total_size_bytes=len(content),
        content_hash=expected_hash,
        data_type="telemetry",
        direction=TransferDirection.EDGE_TO_CORE,
    )
    assert ok is True
    assert manifest.source_device_id == "PI5-ARM64-EDGE-01"
    assert manifest.target_device_id == "CORE-PC-WINDOWS-01"

    chunk = TransferChunk(
        transfer_id="XFER-D02-001",
        chunk_index=0,
        total_chunks=1,
        size_bytes=len(content),
        chunk_hash=expected_hash,
        data_b64=base64.b64encode(content).decode("utf-8"),
    )
    rec_ok, _ = service.receive_chunk(chunk)
    assert rec_ok is True

    # Path traversal attempt in filename is stripped to basename
    ok_trav, _, m_trav = service.initiate_transfer(
        transfer_id="XFER-D02-TRAV",
        source_device_id="PI5-ARM64-EDGE-01",
        target_device_id="CORE-PC-WINDOWS-01",
        filename="../../src/quan_ai_brain/core/audit.py",
        total_size_bytes=10,
        content_hash=hashlib.sha256(b"malicious!").hexdigest(),
    )
    assert ok_trav is True
    assert m_trav.filename == "audit.py"
    assert ".." not in m_trav.filename


def test_d03_large_packet_chunking_and_progress(transfer_env):
    """D03: Verify chunking across multiple parts with progress tracking."""
    service, base_dir, pi5 = transfer_env
    content = b"X" * 3500
    expected_hash = hashlib.sha256(content).hexdigest()
    chunk_size = 1000  # 4 chunks: 1000, 1000, 1000, 500

    ok, _, manifest = service.initiate_transfer(
        transfer_id="XFER-D03-001",
        source_device_id="CORE-PC-WINDOWS-01",
        target_device_id="PI5-ARM64-EDGE-01",
        filename="dataset_chunked.bin",
        total_size_bytes=len(content),
        content_hash=expected_hash,
        chunk_size=chunk_size,
    )
    assert ok is True
    assert manifest.total_chunks == 4

    for i in range(4):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, len(content))
        part = content[start:end]
        c_hash = hashlib.sha256(part).hexdigest()

        chunk = TransferChunk(
            transfer_id="XFER-D03-001",
            chunk_index=i,
            total_chunks=4,
            size_bytes=len(part),
            chunk_hash=c_hash,
            data_b64=base64.b64encode(part).decode("utf-8"),
        )
        c_ok, c_msg = service.receive_chunk(chunk)
        assert c_ok is True

    final_m = service.get_transfer("XFER-D03-001")
    assert final_m.status == TransferStatus.STAGED
    assert final_m.chunks_received == [0, 1, 2, 3]


def test_d04_interrupted_transfer_not_completed(transfer_env):
    """D04: Disrupted transfer does not mark as verified or completed."""
    service, base_dir, pi5 = transfer_env
    content = b"A" * 2000
    expected_hash = hashlib.sha256(content).hexdigest()

    ok, _, manifest = service.initiate_transfer(
        transfer_id="XFER-D04-001",
        source_device_id="CORE-PC-WINDOWS-01",
        target_device_id="PI5-ARM64-EDGE-01",
        filename="interrupted.dat",
        total_size_bytes=len(content),
        content_hash=expected_hash,
        chunk_size=1000,
    )
    assert manifest.total_chunks == 2

    # Deliver only chunk 0
    part0 = content[:1000]
    chunk0 = TransferChunk(
        transfer_id="XFER-D04-001",
        chunk_index=0,
        total_chunks=2,
        size_bytes=len(part0),
        chunk_hash=hashlib.sha256(part0).hexdigest(),
        data_b64=base64.b64encode(part0).decode("utf-8"),
    )
    service.receive_chunk(chunk0)

    current = service.get_transfer("XFER-D04-001")
    assert current.status == TransferStatus.IN_PROGRESS
    assert len(current.chunks_received) == 1

    # ACK cannot succeed
    ack_ok, _ = service.acknowledge_transfer("XFER-D04-001")
    assert ack_ok is False


def test_d05_corrupt_bad_hash_rejection(transfer_env):
    """D05: Altered or bad chunk hash is rejected and marks transfer failed."""
    service, base_dir, pi5 = transfer_env
    content = b"Integrity check payload"
    expected_hash = hashlib.sha256(content).hexdigest()

    service.initiate_transfer(
        transfer_id="XFER-D05-001",
        source_device_id="CORE-PC-WINDOWS-01",
        target_device_id="PI5-ARM64-EDGE-01",
        filename="bad_hash.dat",
        total_size_bytes=len(content),
        content_hash=expected_hash,
    )

    corrupted_data = b"Corrupted chunk data"
    bad_chunk = TransferChunk(
        transfer_id="XFER-D05-001",
        chunk_index=0,
        total_chunks=1,
        size_bytes=len(corrupted_data),
        chunk_hash="fake_hash_value_12345",
        data_b64=base64.b64encode(corrupted_data).decode("utf-8"),
    )
    ok, msg = service.receive_chunk(bad_chunk)
    assert ok is False
    assert service.get_transfer("XFER-D05-001").status == TransferStatus.FAILED


def test_d06_file_size_exceeding_quota_rejection(transfer_env):
    """D06: Reject transfers that exceed the configured size quota."""
    service, base_dir, pi5 = transfer_env
    too_large_bytes = 150_000  # Max is 100_000

    ok, msg, manifest = service.initiate_transfer(
        transfer_id="XFER-D06-001",
        source_device_id="CORE-PC-WINDOWS-01",
        target_device_id="PI5-ARM64-EDGE-01",
        filename="too_large.dat",
        total_size_bytes=too_large_bytes,
        content_hash="dummy_hash",
    )
    assert ok is False
    assert "exceeds maximum permitted file limit" in msg


def test_d07_unauthorized_device_rejection(transfer_env):
    """D07: Reject transfer from an unknown / unpaired edge device."""
    service, base_dir, pi5 = transfer_env

    ok, msg, manifest = service.initiate_transfer(
        transfer_id="XFER-D07-001",
        source_device_id="ROGUE-PI-HACKER",
        target_device_id="CORE-PC-WINDOWS-01",
        filename="rogue.txt",
        total_size_bytes=100,
        content_hash="dummy_hash",
    )
    assert ok is False
    assert "not registered or authorized" in msg


def test_d08_duplicate_transaction_id_handling(transfer_env):
    """D08: Idempotency check prevents duplicate transfers with same ID."""
    service, base_dir, pi5 = transfer_env
    content = b"Idempotent payload"
    h = hashlib.sha256(content).hexdigest()

    ok1, _, m1 = service.initiate_transfer(
        transfer_id="XFER-D08-001",
        source_device_id="CORE-PC-WINDOWS-01",
        target_device_id="PI5-ARM64-EDGE-01",
        filename="idempotent.txt",
        total_size_bytes=len(content),
        content_hash=h,
    )
    assert ok1 is True

    # Second call with same transfer_id attaches to existing
    ok2, msg2, m2 = service.initiate_transfer(
        transfer_id="XFER-D08-001",
        source_device_id="CORE-PC-WINDOWS-01",
        target_device_id="PI5-ARM64-EDGE-01",
        filename="idempotent.txt",
        total_size_bytes=len(content),
        content_hash=h,
    )
    assert ok2 is True
    assert "already exists" in msg2
    assert m2.transfer_id == m1.transfer_id


def test_d09_sensitive_file_barrier(transfer_env):
    """D09: Strictly block .env, credentials, keys, private certs from transfer."""
    service, base_dir, pi5 = transfer_env
    forbidden_files = [
        ".env",
        ".env.local",
        "id_rsa",
        "server.key",
        "certificate.pem",
        "credentials.json",
        "production.db",
    ]

    for fname in forbidden_files:
        ok, msg, manifest = service.initiate_transfer(
            transfer_id=f"XFER-D09-{fname}",
            source_device_id="CORE-PC-WINDOWS-01",
            target_device_id="PI5-ARM64-EDGE-01",
            filename=fname,
            total_size_bytes=50,
            content_hash="dummy_hash",
        )
        assert ok is False, f"Failed to block {fname}"
        assert manifest.status == TransferStatus.BLOCKED_SENSITIVE


def test_d10_multi_device_scope_separation(transfer_env):
    """D10: Multi-device scope isolation between registered edge nodes."""
    service, base_dir, pi5 = transfer_env

    # Register second device
    dev2 = DeviceIdentity(
        device_id="PI5-ARM64-EDGE-02",
        device_type="RASPBERRY_PI_5",
        device_version="0.2.0",
        capabilities=["sensor_only"],
    )
    service.register_device(dev2)

    assert service.get_device("PI5-ARM64-EDGE-01") is not None
    assert service.get_device("PI5-ARM64-EDGE-02") is not None

    # Both devices can have distinct concurrent transfer sessions
    ok1, _, m1 = service.initiate_transfer(
        transfer_id="XFER-D10-DEV1",
        source_device_id="CORE-PC-WINDOWS-01",
        target_device_id="PI5-ARM64-EDGE-01",
        filename="avatar1.json",
        total_size_bytes=100,
        content_hash="hash1",
    )
    ok2, _, m2 = service.initiate_transfer(
        transfer_id="XFER-D10-DEV2",
        source_device_id="CORE-PC-WINDOWS-01",
        target_device_id="PI5-ARM64-EDGE-02",
        filename="avatar2.json",
        total_size_bytes=100,
        content_hash="hash2",
    )

    assert ok1 is True and ok2 is True
    assert m1.target_device_id == "PI5-ARM64-EDGE-01"
    assert m2.target_device_id == "PI5-ARM64-EDGE-02"
