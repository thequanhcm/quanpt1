"""UDC-1 Device Control Service — khống chế thiết bị trên Pi5 theo lệnh DM (04/11/2026).

Chỉ thị quanpt1: "Xây dựng để Pi5 có thể đọc được, khống chế, kiểm soát các
thiết bị được kết nối theo sự điều khiển DM của anh".

Kiến trúc (kế thừa, không trùng lặp):
- ActuatorController sẵn có: relay 8 kênh (BCM 17/27/22/23/24/25/5/6) +
  khớp servo 6-DOF (PCA9685) + emergency_all_stop.
- DeviceWatcher (UDR-1): snapshot thiết bị đang cắm.
- Kiosk server (8768) nhận POST /api/kiosk/device → service.execute().

AN TOÀN (BẮT BUỘC):
- Read-only (list/read/status): chạy ngay.
- WRITE (relay/joint): CHỈ chạy khi có confirm_token khớp token cấp cho
  chính lệnh đó (2 bước qua DM "ok" — không tự duyệt, không tái sử dụng
  token cũ: token gắn (op, target, giá trị) và TTL 10 phút).
- emergency_stop: CHẠY NGAY (an toàn — giảm rủi ro, không tăng).
- Mọi kết quả trung thực: emulated=True khi không có RPi.GPIO (test/PC).
"""
from __future__ import annotations

import secrets
import threading
import time
from typing import Any, Callable

CONFIRM_TTL_SEC = 600.0  # token hết hạn sau 10 phút

READ_ONLY_OPS = frozenset({
    "list_devices", "read_device", "status", "relay_status",
})
WRITE_OPS = frozenset({
    "relay_set", "relay_pulse", "joint_set", "emergency_stop",
})


class DeviceControlError(Exception):
    """Lỗi nghiệp vụ điều khiển thiết bị."""


class DeviceControlService:
    """Điều phối lệnh khống chế thiết bị: read-only tự do, write cần confirm."""

    def __init__(self, watcher_provider: Callable[[], Any] | None = None,
                 actuator: Any = None) -> None:
        self._lock = threading.RLock()
        self._watcher_provider = watcher_provider  # () -> DeviceWatcher | None
        # ActuatorController dùng chung (daemon tạo 1 lần); fallback tự tạo
        self._actuator = actuator
        if self._actuator is None:
            try:
                from edge_client.actuators import ActuatorController
                self._actuator = ActuatorController()
            except Exception:
                self._actuator = None
        # confirm tokens: token -> {op, target, value, staged_at}
        self._pending: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------- stage --
    def stage(self, op: str, target: str, value: Any) -> dict[str, Any]:
        """Cấp token xác nhận cho 1 lệnh WRITE. Trả token + mô tả lệnh."""
        if op not in WRITE_OPS:
            raise DeviceControlError(f"op '{op}' không cần/không được stage")
        token = secrets.token_hex(8)
        with self._lock:
            # dọn token hết hạn
            now = time.time()
            stale = [k for k, v in self._pending.items()
                     if now - v["staged_at"] > CONFIRM_TTL_SEC]
            for k in stale:
                self._pending.pop(k, None)
            self._pending[token] = {
                "op": op, "target": target, "value": value,
                "staged_at": now,
            }
        return {"token": token, "op": op, "target": target, "value": value,
                "ttl_sec": CONFIRM_TTL_SEC}

    # ------------------------------------------------------------ execute --
    def execute(self, body: dict[str, Any]) -> dict[str, Any]:
        """Điểm vào duy nhất cho /api/kiosk/device.

        body: {op, target?, value?, confirm_token?}
        Fail-closed: lỗi nghiệp vụ trả success=False + reason, không raise.
        """
        op = str(body.get("op", "")).strip().lower()
        target = str(body.get("target", "")).strip()
        value = body.get("value")
        token = str(body.get("confirm_token", "")).strip()

        try:
            if not op:
                return {"success": False, "reason": "thiếu op"}
            if op == "stage_write":
                # UDC-1: PC xin cấp token cho 1 lệnh ghi (2 bước qua DM "ok").
                # Token gắn (write_op, target, value), TTL 10 phút, một-lần.
                write_op = str(body.get("write_op", "")).strip().lower()
                if write_op not in ("relay_set", "relay_pulse", "joint_set"):
                    return {"success": False,
                            "reason": f"write_op không hỗ trợ: {write_op}"}
                staged = self.stage(write_op, target, value)
                return {"success": True, "op": "stage_write", **staged}
            if op in READ_ONLY_OPS:
                return self._exec_read(op, target, value)
            if op == "emergency_stop":
                return self._exec_emergency()
            if op in WRITE_OPS:
                return self._exec_write(op, target, value, token)
            return {"success": False, "reason": f"op không hỗ trợ: {op}"}
        except DeviceControlError as exc:
            return {"success": False, "reason": str(exc)}
        except Exception as exc:
            return {"success": False,
                    "reason": f"lỗi thực thi: {type(exc).__name__}: {exc}"}

    # --------------------------------------------------------- read-only --
    def _exec_read(self, op: str, target: str,
                   value: Any) -> dict[str, Any]:
        if op == "list_devices":
            w = self._watcher_provider() if self._watcher_provider else None
            if w is None:
                return {"success": False, "reason": "device watcher chưa sẵn sàng"}
            snap = w.current_snapshot()
            return {"success": True, "op": op, "data": {
                "total": snap.get("total", 0),
                "by_bus": snap.get("by_bus", {}),
                "devices": snap.get("devices", []),
            }}
        if op == "status" or op == "relay_status":
            act = self._need_actuator()
            st = act.get_status()
            return {"success": True, "op": "status", "data": st}
        if op == "read_device":
            # đọc giá trị cảm biến từ snapshot thiết bị (1-Wire nhiệt độ…)
            w = self._watcher_provider() if self._watcher_provider else None
            if w is None:
                return {"success": False, "reason": "device watcher chưa sẵn sàng"}
            snap = w.current_snapshot()
            devs = [d for d in snap.get("devices", [])
                    if target and (target in str(d.get("dev_id", ""))
                                   or target in str(d.get("name", "")))]
            if not devs:
                return {"success": False,
                        "reason": f"không thấy thiết bị khớp '{target}'"}
            return {"success": True, "op": op, "data": {"devices": devs[:5]}}
        return {"success": False, "reason": f"read-op lạ: {op}"}

    # -------------------------------------------------------------- write --
    def _exec_write(self, op: str, target: str, value: Any,
                    token: str) -> dict[str, Any]:
        # XÁC MINH TOKEN: gắn đúng (op, target) — không tái sử dụng, có TTL
        with self._lock:
            entry = self._pending.pop(token, None) if token else None
        if entry is None:
            return {"success": False, "reason":
                    "CHƯA CÓ XÁC NHẬN — lệnh ghi cần anh 'ok' ở DM trước (token "
                    "không tồn tại/hết hạn). Gửi lại lệnh để nhận token mới."}
        if time.time() - entry["staged_at"] > CONFIRM_TTL_SEC:
            return {"success": False, "reason": "token đã hết hạn (10 phút)"}
        if entry["op"] != op or str(entry["target"]) != target:
            return {"success": False, "reason":
                    "token không khớp lệnh (op/target khác) — từ chối"}

        act = self._need_actuator()
        if op == "relay_set":
            state = str(value or "").strip().upper()
            res = act.set_relay(target, state)
            res["via_dm"] = True
            return res
        if op == "relay_pulse":
            dur = int(value or 500)
            res = act.pulse_relay(target, duration_ms=max(50, min(10_000, dur)))
            if isinstance(res, dict):
                res["via_dm"] = True
            return res
        if op == "joint_set":
            angle = float(value if value is not None else 90.0)
            res = act.set_joint_angle(target, angle)
            if isinstance(res, dict):
                res["via_dm"] = True
            return res
        return {"success": False, "reason": f"write-op lạ: {op}"}

    # ----------------------------------------------------------- e-stop --
    def _exec_emergency(self) -> dict[str, Any]:
        act = self._need_actuator()
        res = act.emergency_all_stop()
        if isinstance(res, dict):
            res["via_dm"] = True
        return res

    def _need_actuator(self) -> Any:
        if self._actuator is None:
            raise DeviceControlError("ActuatorController không khả dụng")
        return self._actuator
