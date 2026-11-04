"""UDR-1 Universal Device Reader — tests (04/11/2026).

Phủ: scanner platform-trung thực (Windows → rỗng + note), watcher diff
cắm/rút → event đúng, device store lưu + DM cooldown, không giật regression
QPIG (25 tool cũ giữ nguyên vì tool UDR tách module riêng).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "edge_client"))

from edge_client.device_readers import (  # noqa: E402
    device_fingerprint, flatten_devices, scan_all_devices,
)
from edge_client.device_watcher import DeviceWatcher  # noqa: E402
from quan_ai_brain.web.device_store import DeviceStore  # noqa: E402


# ---------------------------------------------------------------- scanners --
def test_scan_all_devices_honest_on_windows() -> None:
    """Trên Windows: trả dict đầy đủ kênh, total=0, có note — không giả data."""
    snap = scan_all_devices()
    assert snap["platform"] in ("Windows", "Linux")
    for bus in ("usb", "serial", "i2c", "gpio_spi", "storage",
                "hdmi", "camera", "bluetooth", "lan", "sensors"):
        assert bus in snap and isinstance(snap[bus], list)
    assert isinstance(snap["total"], int)
    if snap["platform"] == "Windows":
        assert snap["total"] == 0
        assert "note" in snap


def test_flatten_and_fingerprint_stable() -> None:
    """Flatten giữ bus/dev_id; fingerprint ổn định + khác nhau giữa 2 thiết bị."""
    snap = {"platform": "Linux", "total": 2,
            "usb": [{"bus": "usb", "dev_id": "1-2", "name": "Cam X",
                     "vid_pid": "1234:5678", "meta": {}},
                    {"bus": "usb", "dev_id": "1-3", "name": "Disk Y",
                     "vid_pid": "abcd:ef01", "meta": {}}]}
    flat = flatten_devices(snap)
    assert len(flat) == 2
    fp1 = device_fingerprint(flat[0])
    fp2 = device_fingerprint(flat[1])
    assert fp1 == device_fingerprint(flat[0])  # ổn định
    assert fp1 != fp2
    assert fp1.startswith("usb:1-2:1234:5678")


# ----------------------------------------------------------------- watcher --
class _Buffer:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def __call__(self, event_type, severity="INFO", details=None):
        ev = {"type": event_type, "severity": severity, "details": details or {}}
        self.events.append(ev)
        return ev


def test_watcher_detects_add_and_remove() -> None:
    """Lần 1 baseline (không event); thêm thiết bị → DEVICE_ADDED; rút → REMOVED."""
    buf = _Buffer()
    w = DeviceWatcher(buf, interval_sec=15)
    snap1 = {"platform": "Linux", "total": 1, "usb": [
        {"bus": "usb", "dev_id": "1-1", "name": "Base", "vid_pid": "",
         "meta": {}}]}
    try:
        _patch_scan(w, lambda: snap1)
        r1 = w.scan_once()
        assert r1["first_scan"] is True and not buf.events

        snap2 = {"platform": "Linux", "total": 2, "usb": [
            {"bus": "usb", "dev_id": "1-1", "name": "Base", "vid_pid": "",
             "meta": {}},
            {"bus": "usb", "dev_id": "1-2", "name": "USB Cam",
             "vid_pid": "1234:5678", "meta": {}}]}
        _patch_scan(w, lambda: snap2)
        r2 = w.scan_once()
        types = [e["type"] for e in buf.events]
        assert types == ["DEVICE_ADDED"]
        assert "USB Cam" in str(buf.events[0]["details"]["desc"])

        snap3 = {"platform": "Linux", "total": 1, "usb": [
            {"bus": "usb", "dev_id": "1-1", "name": "Base", "vid_pid": "",
             "meta": {}}]}
        _patch_scan(w, lambda: snap3)
        w.scan_once()
        types = [e["type"] for e in buf.events]
        assert types == ["DEVICE_ADDED", "DEVICE_REMOVED"]
        cur = w.current_snapshot()
        assert cur["known_fingerprints"] == 1
        assert cur["added_total"] == 1 and cur["removed_total"] == 1
    finally:
        _restore_scan(w)


# ------------------------------------------------------------- device store -
def test_store_records_and_dm_cooldown(tmp_path) -> None:
    """Store: lưu ADDED/REMOVED vào DB; DM gửi đúng 1 lần, lần 2 cooldown."""
    sent: list[str] = []

    def sender(msg: str):
        sent.append(msg)
        return {"success": True}

    st = DeviceStore(tmp_path / "dev.db", sender=sender, cooldown_sec=60)
    ev_add = {"type": "DEVICE_ADDED", "severity": "INFO", "details": {
        "fingerprint": "usb:1-2:1234:5678",
        "desc": "Thiết bị cắm vào Pi5: [usb] USB Cam (1234:5678)",
        "device": {"bus": "usb", "dev_id": "1-2", "name": "USB Cam",
                   "vid_pid": "1234:5678", "meta": {}}}}
    r1 = st.record_added("EDGE-PI5-DESK-01", ev_add)
    assert r1["stored"] and r1["dm"].get("sent") is True
    r2 = st.record_added("EDGE-PI5-DESK-01", ev_add)
    assert r2["dm"]["sent"] is False and r2["dm"]["reason"] == "cooldown"
    assert len(sent) == 1 and "USB Cam" in sent[0]

    ev_rm = {"type": "DEVICE_REMOVED", "severity": "INFO", "details": {
        "fingerprint": "usb:1-2:1234:5678",
        "desc": "Thiết bị rút khỏi Pi5: [usb] USB Cam (1234:5678)"}}
    r3 = st.record_removed("EDGE-PI5-DESK-01", ev_rm)
    assert r3["stored"] and r3["dm"]["sent"] is True  # key khác → không cooldown

    cur = st.current_devices()
    assert cur == []  # đã rút → current rỗng
    evs = st.recent_events(10)
    # 2 lần record_added đều ghi DB (audit trail); riêng DM bị cooldown
    assert [e["event"] for e in evs] == ["REMOVED", "ADDED", "ADDED"]


def test_store_no_sender_never_crashes(tmp_path) -> None:
    """Không sender: chỉ lưu DB, trả sent=False — không raise."""
    st = DeviceStore(tmp_path / "dev2.db", sender=None)
    ev = {"type": "DEVICE_ADDED", "severity": "INFO", "details": {
        "fingerprint": "serial:/dev/ttyUSB0", "desc": "[serial] /dev/ttyUSB0"}}
    r = st.record_added("EDGE-PI5", ev)
    assert r["dm"]["sent"] is False
    assert len(st.current_devices()) == 1


# ------------------------------------------------------------------ helpers -
def _patch_scan(watcher: DeviceWatcher, fn) -> None:
    watcher.__dict__["_orig_scan"] = None
    import edge_client.device_watcher as dw
    watcher.__dict__["_dw_mod"] = dw
    watcher.__dict__["_orig_fn"] = dw.scan_all_devices
    dw.scan_all_devices = fn


def _restore_scan(watcher: DeviceWatcher) -> None:
    dw = watcher.__dict__.get("_dw_mod")
    if dw is not None and watcher.__dict__.get("_orig_fn") is not None:
        dw.scan_all_devices = watcher.__dict__["_orig_fn"]


# placeholder to keep name defined before use in test body
device_watcher_scan_all = None
orig = None  # noqa: E305
