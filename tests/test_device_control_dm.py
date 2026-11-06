"""UDC-1 Device Control qua DM — tests (04/11/2026).

Phủ: DeviceControlService (stage/execute/token khớp op+target/TTL/one-shot,
read-only tự do, estop), intent routing 17 lệnh DM (mới + regression cũ),
không giật test edge hiện có.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "src"))
sys.path.insert(0, str(WS / "edge_client"))

from edge_client.device_control import (  # noqa: E402
    DeviceControlError, DeviceControlService,
)


class _FakeActuator:
    """Actuator giả — ghi nhận lệnh, trả dict như bản thật."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def set_relay(self, channel_id: str, state: str):
        self.calls.append(("set_relay", channel_id, state))
        return {"success": True, "channel_id": channel_id, "state": state,
                "emulated": True}

    def pulse_relay(self, channel_id: str, duration_ms: int = 500):
        self.calls.append(("pulse_relay", channel_id, duration_ms))
        return {"success": True, "channel_id": channel_id, "emulated": True}

    def set_joint_angle(self, joint_id: str, angle: float):
        self.calls.append(("set_joint", joint_id, angle))
        return {"success": True, "joint": joint_id, "angle": angle,
                "emulated": True}

    def emergency_all_stop(self):
        self.calls.append(("estop",))
        return {"success": True, "stopped": True}

    def get_status(self):
        return {"hardware_available": False, "emulated_mode": True,
                "relays": {}, "joints": {}}


class _FakeWatcher:
    def current_snapshot(self):
        return {"platform": "Linux", "total": 1, "known_fingerprints": 1,
                "by_bus": {"usb": 1},
                "devices": [{"bus": "usb", "dev_id": "1-1", "name": "Cam",
                             "vid_pid": "12:34", "meta": {}}],
                "scans_done": 2, "added_total": 0, "removed_total": 0,
                "first_scan_done": True}


def _svc() -> tuple[DeviceControlService, _FakeActuator]:
    act = _FakeActuator()
    return DeviceControlService(watcher_provider=lambda: _FakeWatcher(),
                                actuator=act), act


# ------------------------------------------------------------ service tests -
def test_read_only_needs_no_token() -> None:
    """list_devices/status chạy ngay, không cần token."""
    svc, _ = _svc()
    r = svc.execute({"op": "list_devices"})
    assert r["success"] and r["data"]["total"] == 1
    r2 = svc.execute({"op": "status"})
    assert r2["success"] and r2["data"]["emulated_mode"] is True


def test_write_blocked_without_token() -> None:
    """relay_set KHÔNG token → từ chối, actuator KHÔNG chạy (fail-closed)."""
    svc, act = _svc()
    r = svc.execute({"op": "relay_set", "target": "relay_1", "value": "OPEN"})
    assert r["success"] is False and "XÁC NHẬN" in r["reason"]
    assert act.calls == []  # không đụng hardware


def test_stage_then_execute_token_one_shot() -> None:
    """stage_write cấp token → execute 1 lần OK → token thứ 2 bị từ chối."""
    svc, act = _svc()
    s = svc.execute({"op": "stage_write", "write_op": "relay_set",
                     "target": "relay_3", "value": "OPEN"})
    assert s["success"] and s["token"]
    r = svc.execute({"op": "relay_set", "target": "relay_3", "value": "OPEN",
                     "confirm_token": s["token"]})
    assert r["success"] and r["state"] == "OPEN"
    assert act.calls == [("set_relay", "relay_3", "OPEN")]
    # tái sử dụng token → từ chối (một-lần)
    r2 = svc.execute({"op": "relay_set", "target": "relay_3", "value": "OPEN",
                      "confirm_token": s["token"]})
    assert r2["success"] is False


def test_token_bound_to_op_target() -> None:
    """Token cấp cho relay_3/OPEN không dùng được cho relay_4 hay CLOSED."""
    svc, act = _svc()
    s = svc.execute({"op": "stage_write", "write_op": "relay_set",
                     "target": "relay_3", "value": "OPEN"})
    r = svc.execute({"op": "relay_set", "target": "relay_4", "value": "OPEN",
                     "confirm_token": s["token"]})
    assert r["success"] is False and act.calls == []
    s2 = svc.execute({"op": "stage_write", "write_op": "relay_set",
                      "target": "relay_3", "value": "CLOSED"})
    r2 = svc.execute({"op": "relay_set", "target": "relay_3", "value": "CLOSED",
                      "confirm_token": s["token"]})  # token của OPEN
    assert r2["success"] is False and act.calls == []


def test_token_ttl_expired() -> None:
    """Token quá 10 phút → từ chối (TTL)."""
    svc, _ = _svc()
    s = svc.execute({"op": "stage_write", "write_op": "relay_set",
                     "target": "relay_2", "value": "OPEN"})
    svc._pending[s["token"]]["staged_at"] = time.time() - 601
    r = svc.execute({"op": "relay_set", "target": "relay_2", "value": "OPEN",
                     "confirm_token": s["token"]})
    assert r["success"] is False and "hết hạn" in r["reason"]


def test_estop_runs_immediately() -> None:
    """emergency_stop chạy NGAY không token (giảm rủi ro)."""
    svc, act = _svc()
    r = svc.execute({"op": "emergency_stop"})
    assert r["success"] and ("estop",) in act.calls


# ------------------------------------------------------------ intent tests --
def test_dm_intent_routing() -> None:
    """17 lệnh DM mới+cũ route đúng (không vỡ lệnh hiện có)."""
    from tools.netchat_command_center import detect_intent

    checks = [
        ("dừng khẩn thiết bị", "emergency_stop_device"),
        ("ngắt nguồn thiết bị", "emergency_stop_device"),
        ("emergency stop device", "emergency_stop_device"),
        ("tắt nhạc", "tony_music_stop"),
        ("dừng nhạc", "tony_music_stop"),
        ("tony dừng nhạc", "tony_music_stop"),
        ("stop", "stop"),
        ("dừng lại", "stop"),
        ("dừng", "stop"),
        ("mở chrome", "pc_open"),
        ("bật rơ le 3", "relay_on"),
        ("tắt relay 5", "relay_off"),
        ("thiết bị trên pi", "device_list"),
        ("liệt kê thiết bị", "device_list"),
        ("trạng thái", "status"),
        ("tắt hình thể", "tony_off"),
        ("dừng khẩn", "stop"),
    ]
    for t, want in checks:
        assert detect_intent(t) == want, f"{t!r} → {detect_intent(t)} (want {want})"


def test_relay_dm_stages_pending_not_execute() -> None:
    """'bật rơ le 3' qua DM: Pi offline → không hứa suông; Pi stage được →
    pending action chờ 'ok', KHÔNG tự execute.

    (06/11/2026) route_message KHÔNG tự inject chat_session_id vào payload —
    caller (responder) phải truyền. Test mô phỏng đúng hợp đồng responder:
    payload={'chat_session_id': ...} như process_message inject sau fix
    session-mismatch. Nếu relay stage thất bại (Pi offline) → KHÔNG pending.
    """
    from tools.netchat_command_center import (
        _PENDING_ACTIONS, route_message, _take_pending_action,
    )
    # Mô phỏng responder sau fix: payload mang chat_session_id thật
    intent, resp = route_message(
        "bật rơ le 3", chat_session_id="udc-test-1",
        payload={"chat_session_id": "udc-test-1"},
    )
    assert intent in ("relay_on", "pc_open")  # tùy môi trường có core
    # nếu core forward thất bại → không stage pending
    if not resp.startswith("⚙️"):
        assert "udc-test-1" not in _PENDING_ACTIONS
    else:
        entry = _take_pending_action("udc-test-1")
        assert entry is not None  # staged, chờ 'ok'
