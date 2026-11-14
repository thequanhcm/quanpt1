"""UDR-1 DeviceWatcher — diff thiết bị trên Pi5, phát hiện CẮM/RÚT (04/11/2026).

Chu kỳ 60s: scan_all_devices() → so với bộ dấu vân tay lần trước → sinh event
DEVICE_ADDED / DEVICE_REMOVED vào EdgeEventBuffer (kênh HMAC sẵn có gửi về Core
qua /api/executive/edge/events). Read-only, fail-closed, không bao giờ raise.

(07/11/2026) FIX FLAP LAN: 'LAN fe80::1' (router) hay rớt khỏi `ip neigh` 1 chu kỳ
(NDP INCOMPLETE thoáng qua — router không trả Neighbor Solicitation ~1 phút) →
REMOVE rồi ADD lại ngay → spam DM 'Mất kết nối'. Debounce: REMOVE phải VẮNG
REMOVE_DEBOUNCE_SCANS lần quét LIÊN TIẾP; quay lại trước ngưỡng → không event.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

try:
    # chạy như package edge_client (daemon thật)
    from edge_client.device_readers import (  # type: ignore
        SCANNERS, device_fingerprint, flatten_devices, scan_all_devices,
    )
except Exception:  # pragma: no cover — fallback import trực tiếp (tests/PC)
    from device_readers import (  # type: ignore
        SCANNERS, device_fingerprint, flatten_devices, scan_all_devices,
    )

SCAN_INTERVAL_SEC = 60.0
# Số lần quét liên tiếp device phải VẮNG trước khi báo REMOVE (debounce flap).
# 2 × 60s = 120s grace — che pha NDP INCOMPLETE của router, không che rút thật.
REMOVE_DEBOUNCE_SCANS = 2


class DeviceWatcher:
    """Vòng lặp nền diff thiết bị — cắm/rút đều thành event cho TONY."""

    def __init__(self, add_event: Callable[..., dict[str, Any]],
                 interval_sec: float = SCAN_INTERVAL_SEC) -> None:
        self._add_event = add_event
        self._interval = max(10.0, float(interval_sec))
        self._lock = threading.Lock()
        self._known: set[str] = set()
        self._last_snapshot: dict[str, Any] = {}
        self._last_devices: list[dict[str, Any]] = []
        self._first_scan_done = False
        # (07/11) debounce REMOVE: đếm số lần quét liên tiếp device vắng mặt
        self._missing_counts: dict[str, int] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        # thống kê
        self.scans_done = 0
        self.added_total = 0
        self.removed_total = 0

    # ------------------------------------------------------------------
    def scan_once(self) -> dict[str, Any]:
        """Quét 1 lần + diff. Trả tóm tắt những gì đã phát hiện/ghi event."""
        snap = scan_all_devices()
        flat = flatten_devices(snap)
        current = {device_fingerprint(d) for d in flat}
        with self._lock:
            known = set(self._known)
        if not self._first_scan_done:
            with self._lock:
                self._known = current
                self._last_snapshot = snap
                self._last_devices = flat
                self._first_scan_done = True
            with self._lock:
                self.scans_done += 1
            return {"first_scan": True, "known": len(current), "added": [],
                    "removed": []}
        # (07/11) Debounce REMOVE + FLAP-IMMUNE ADD — xem comment đầu file.
        # _missing_counts[fp] = số chuột quét liên tiếp fp đang vắng mặt (độc lập
        # với _known vốn cập nhật ∅ ngay chu kỳ đầu vắng mặt).
        removed: set[str] = set()
        flapped_back: set[str] = set()  # vắng <ngưỡng rồi quay lại → không ADD
        with self._lock:
            tracked = set(self._missing_counts)
            # fp quay lại khi ĐANG bị đếm vắng (<ngưỡng) = flap — dù known đã ∅
            for fp in tracked & current:
                if self._missing_counts[fp] < REMOVE_DEBOUNCE_SCANS:
                    flapped_back.add(fp)
                self._missing_counts.pop(fp, None)
            still_there = known & current
            for fp in still_there:
                self._missing_counts.pop(fp, None)
            # device từng thấy gần nhất (known ∪ đang đếm) mà không còn trong current
            for fp in (known | tracked) - current:
                self._missing_counts[fp] = self._missing_counts.get(fp, 0) + 1
                if self._missing_counts[fp] >= REMOVE_DEBOUNCE_SCANS:
                    removed.add(fp)
                    self._missing_counts.pop(fp, None)  # bắn 1 lần — không lặp
        added = {fp for fp in (current - known) if fp not in flapped_back}
        events: list[dict[str, Any]] = []
        for fp in sorted(added):
            dev = next((d for d in flat if device_fingerprint(d) == fp), None)
            info = self._describe(dev)
            # (06/11/2026, owner) desc chỉ chứa ĐỊNH DANH ([bus] tên (vid_pid)) —
            # câu văn "kết nối/mất kết nối" do DeviceStore soạn 1 chỗ duy nhất,
            # tránh lặp chữ ("Thiết bị CẮM vào Pi5: Thiết bị cắm vào Pi5: …").
            ev = self._safe_add("DEVICE_ADDED", "INFO", {
                "desc": info,
                "fingerprint": fp,
                **({"device": dev} if dev else {}),
            })
            if ev:
                events.append(ev)
            with self._lock:
                self.added_total += 1
        for fp in sorted(removed):
            with self._lock:
                last = self._last_devices
            dev = next((d for d in last if device_fingerprint(d) == fp), None)
            info = self._describe(dev)
            ev = self._safe_add("DEVICE_REMOVED", "INFO", {
                "desc": info,  # định danh thuần — câu văn do DeviceStore soạn
                "fingerprint": fp,
            })
            if ev:
                events.append(ev)
            with self._lock:
                self.removed_total += 1
        with self._lock:
            self._known = current
            self._last_snapshot = snap
            self._last_devices = flat
            self.scans_done += 1
        return {"first_scan": False, "added": [e for e in events
                if "DEVICE_ADDED" in str(e.get("type", ""))],
                "removed": [e for e in events
                if "DEVICE_REMOVED" in str(e.get("type", ""))],
                "known": len(current)}

    # ------------------------------------------------------------------
    def current_snapshot(self) -> dict[str, Any]:
        """Snapshot lần quét gần nhất (cho heartbeat telemetry + QPIG query)."""
        with self._lock:
            return {
                "platform": self._last_snapshot.get("platform", "?"),
                "total": len(self._known),
                "known_fingerprints": len(self._known),
                "by_bus": {bus: len(self._last_snapshot.get(bus, []) or [])
                           for bus, _ in SCANNERS},
                "devices": list(self._last_devices),
                "scans_done": self.scans_done,
                "added_total": self.added_total,
                "removed_total": self.removed_total,
                "first_scan_done": self._first_scan_done,
            }

    # ------------------------------------------------------------------
    def start_background(self) -> bool:
        """Bật luồng nền (idempotent). Trả True nếu luồng được tạo."""
        if self._thread and self._thread.is_alive():
            return False
        self._stop.clear()

        def _loop() -> None:
            # quét ngay 1 lần để có baseline (không spam event lúc mới lên)
            try:
                self.scan_once()
            except Exception:
                pass
            while not self._stop.wait(self._interval):
                try:
                    self.scan_once()
                except Exception:
                    pass  # fail-closed

        self._thread = threading.Thread(target=_loop, daemon=True,
                                        name="edge-device-watcher")
        self._thread.start()
        return True

    def stop_background(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------
    @staticmethod
    def _describe(dev: dict[str, Any] | None) -> str:
        if not dev:
            return "không rõ chi tiết"
        name = dev.get("name") or dev.get("dev_id") or "?"
        bus = dev.get("bus", "?")
        vp = dev.get("vid_pid") or ""
        return f"[{bus}] {name}" + (f" ({vp})" if vp else "")

    def _safe_add(self, etype: str, severity: str,
                  details: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return self._add_event(etype, severity=severity, details=details)
        except Exception:
            try:
                return self._add_event(etype)  # chữ ký đơn giản hoá
            except Exception:
                return None
