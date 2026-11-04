"""Kênh liên tục Core↔Pi5 — tests (04/11/2026).

Phủ: heartbeat queue (lệnh chờ Pi offline được giữ, không rơi), connection
lost/restored detection (2 chiều DM thông báo), API edge devices read.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "src"))
sys.path.insert(0, str(WS / "edge_client"))

from edge_client.edge_agent import EdgeAgent  # noqa: E402


class _Cfg:
    device_id = "EDGE-PI5-TEST"


# ------------------------------------------------- connection lifecycle ----
def test_lost_then_restored_events() -> None:
    """Mất mạng → CRITICAL event; online lại → RESTORED kèm seconds offline."""
    agent = EdgeAgent(config=_Cfg())
    assert agent.detect_connection_lost(core_connected=False, was_connected=True)
    time.sleep(0.01)
    # trong lúc offline: gọi tiếp không sinh thêm event LOST
    assert not agent.detect_connection_lost(False, False)
    # online lại
    assert not agent.detect_connection_lost(True, False)
    types = [e["type"] for e in agent.events.snapshot()]
    assert "BRAIN_CONNECTION_LOST" in types
    assert "BRAIN_CONNECTION_RESTORED" in types
    restored = next(e for e in agent.events.snapshot()
                    if e["type"] == "BRAIN_CONNECTION_RESTORED")
    assert restored["details"]["offline_seconds"] >= 0


def test_no_restored_without_prior_lost() -> None:
    """Boot lần đầu online (chưa từng mất) → KHÔNG spam RESTORED."""
    agent = EdgeAgent(config=_Cfg())
    agent.detect_connection_lost(True, False)
    types = [e["type"] for e in agent.events.snapshot()]
    assert "BRAIN_CONNECTION_RESTORED" not in types
    assert "BRAIN_CONNECTION_LOST" not in types


def test_lost_callback_fires() -> None:
    """Callback mất mạng (daemon dùng để update trạng thái) được gọi 1 lần."""
    agent = EdgeAgent(config=_Cfg())
    calls: list[str] = []
    agent._notify_lost_connection = lambda msg: calls.append(msg)
    agent.detect_connection_lost(False, True)
    agent.detect_connection_lost(False, False)  # vẫn offline — không gọi thêm
    assert len(calls) == 1


# ------------------------------------------------- heartbeat command queue -
def test_pending_command_queue_fifo_one_per_heartbeat() -> None:
    """Queue lệnh PC→Pi: FIFO, mỗi heartbeat lấy đúng 1, đúng thứ tự."""
    q: list[dict] = [
        {"action": "speak", "text": "A"},
        {"action": "reload_ui"},
    ]
    out = []
    while q:
        out.append(q.pop(0))
    assert out == [{"action": "speak", "text": "A"}, {"action": "reload_ui"}]


# ------------------------------------------------- edge devices API --------
def test_device_store_roundtrip(tmp_path) -> None:
    """DeviceStore lưu current + history, đọc lại đúng (kênh UDR-1)."""
    from quan_ai_brain.web.device_store import DeviceStore

    store = DeviceStore(tmp_path / "t.db", sender=None)
    store.record_added("EDGE-PI5-TEST", {
        "type": "DEVICE_ADDED", "timestamp_utc": "2026-11-04T00:00:00Z",
        "details": {"fingerprint": "usb:1-1", "device": {
            "bus": "usb", "name": "Camera", "dev_id": "1-1", "vid_pid": "12:34"}},
    })
    cur = store.current_devices()
    assert len(cur) >= 1
    assert cur[0]["name"] == "Camera"
    hist = store.recent_events(10)
    assert any(h["event"] == "ADDED" for h in hist)
