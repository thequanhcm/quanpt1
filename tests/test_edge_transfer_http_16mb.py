"""Sprint-1314 — FIX transfer >15MB: test E2E qua HTTP thật (không mock service).

Chuỗi: initiate (EDGE_TO_CORE, 16.5MB) → chunk 65KB × N qua
/api/executive/edge/transfer/chunk → assemble + hash verify → ack → COMPLETED.
Trước fix: initiate TypeError (sai keyword), chunk TypeError (data_bytes không
tồn tại) + unpack 3-tuple, ack TypeError (2 đối số) — toàn chuỗi không thể chạy.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
import time
import urllib.request

import pytest

from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer


@pytest.fixture()
def transfer_server(tmp_path):
    workspace = tmp_path / "ws"
    (workspace / "data").mkdir(parents=True, exist_ok=True)
    old_env = os.environ.get("QUAN_AI_BRAIN_WORKSPACE")
    os.environ["QUAN_AI_BRAIN_WORKSPACE"] = str(workspace)

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base_url = f"http://{host}:{port}"
    time.sleep(0.1)
    yield base_url, str(workspace)

    server.shutdown()
    server.server_close()
    if old_env is None:
        os.environ.pop("QUAN_AI_BRAIN_WORKSPACE", None)
    else:
        os.environ["QUAN_AI_BRAIN_WORKSPACE"] = old_env


def _post_json(base_url: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 400 → trả JSON error body
        return json.loads(exc.read().decode("utf-8"))


def test_edge_transfer_16_5MB_e2e_initiate_chunk_ack(transfer_server):
    """File 16.5MB (>15MB) đi trọn chuỗi initiate→chunk×N→ack → COMPLETED."""
    base_url, workspace = transfer_server

    # 16.5MB dữ liệu deterministic (để so khớp sau assemble)
    total = 16 * 1024 * 1024 + 512 * 1024  # 17,301,504 bytes
    payload_bytes = bytes((i * 7 + (i >> 13)) % 256 for i in range(total))
    content_hash = hashlib.sha256(payload_bytes).hexdigest()

    # 1) INITIATE — khai báo total_size + content_hash (không mang 16.5MB trong body)
    # device_id mặc định CORE-PC-WINDOWS-01 đã đăng ký sẵn trong service.__init__
    r = _post_json(base_url, "/api/executive/edge/transfer/initiate", {
        "transfer_id": "XFER-TEST-16MB-001",
        "device_id": "CORE-PC-WINDOWS-01",
        "direction": "EDGE_TO_CORE",
        "relative_path": "uploads/kiosk_capture_16MB.bin",
        "classification": "OPERATIONAL",
        "total_size_bytes": total,
        "content_hash": content_hash,
    })
    assert r.get("success") is True, f"initiate failed: {r}"
    manifest = r.get("manifest") or {}
    assert manifest.get("status") == "INITIATED"
    assert manifest.get("total_size_bytes") == total

    # 2) CHUNKS 65KB × N
    chunk_size = 65_536
    n_chunks = (total + chunk_size - 1) // chunk_size
    last_resp = None
    for idx in range(n_chunks):
        part = payload_bytes[idx * chunk_size:(idx + 1) * chunk_size]
        data_b64 = base64.b64encode(part).decode("ascii")
        r = _post_json(base_url, "/api/executive/edge/transfer/chunk", {
            "transfer_id": "XFER-TEST-16MB-001",
            "chunk_index": idx,
            "total_chunks": n_chunks,
            "size_bytes": len(part),
            "chunk_hash": hashlib.sha256(part).hexdigest(),
            "chunk_data_base64": data_b64,
        })
        assert r.get("success") is True, f"chunk {idx}: {r}"
        last_resp = r
    m = (last_resp or {}).get("manifest") or {}
    assert m.get("status") == "STAGED", f"final status: {m.get('status')}"

    # 3) STATUS endpoint cũng phải sống (bug get_transfer_status)
    with urllib.request.urlopen(
            f"{base_url}/api/executive/edge/transfer/status?transfer_id=XFER-TEST-16MB-001",
            timeout=10.0) as resp:
        st = json.loads(resp.read().decode("utf-8"))
    assert st.get("success") is True
    assert (st.get("manifest") or {}).get("status") == "STAGED"

    # 4) ACK
    r = _post_json(base_url, "/api/executive/edge/transfer/ack", {
        "transfer_id": "XFER-TEST-16MB-001",
    })
    assert r.get("success") is True
    assert r.get("message") == "Transfer acknowledged and completed successfully"

    # 5) FILE assembled đúng bytes + hash
    # service dùng Path.cwd() / "data" / "edge_transfers" (không đọc env)
    final_path = os.path.join(os.getcwd(), "data", "edge_transfers", "completed",
                              "XFER-TEST-16MB-001", "kiosk_capture_16MB.bin")
    got = open(final_path, "rb").read()
    assert len(got) == total
    assert hashlib.sha256(got).hexdigest() == content_hash


def test_edge_transfer_initiate_rejects_invalid_enum(transfer_server):
    """Initiate với direction không tồn tại → 400 (ValueError → error JSON)."""
    base_url, _ = transfer_server
    r = _post_json(base_url, "/api/executive/edge/transfer/initiate", {
        "transfer_id": "XFER-BAD-001",
        "direction": "PC_TO_EDGE",  # enum không tồn tại
        "relative_path": "x.bin",
        "classification": "OPERATIONAL",
        "total_size_bytes": 10,
        "content_hash": "0" * 64,
    })
    # Handler mới: ValueError → 400 với error JSON
    assert r.get("success") is False
    assert "invalid enum" in (r.get("error") or "").lower() or "PC_TO_EDGE" in (r.get("error") or "")
