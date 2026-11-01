"""Edge Connection Monitor & Watchdog for QUAN AI BRAIN PC Core.

Monitors Raspberry Pi 5 Edge Embodiment connection health, tracks heartbeat deadlines,
evaluates network channel quality, and emits independent server-side alerts (A to F)
even when Raspberry Pi 5 loses power, disconnects from Wi-Fi, or crashes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import threading
import time
from typing import Any


class EdgeConnectionState(str, Enum):
    """Formal 9-state lifecycle for Edge Embodiment connection."""

    DISCONNECTED = "DISCONNECTED"  # No active session or timed out
    CONNECTING = "CONNECTING"      # Handshake / pairing initiated
    CONNECTED = "CONNECTED"        # Authenticated channel established
    DEGRADED = "DEGRADED"          # Connected but latency/loss exceeds threshold
    SYNCING = "SYNCING"            # Synchronizing state, task queue or config
    READY = "READY"                # All health checks passed and fully operational
    RECOVERING = "RECOVERING"      # Recovering from transient drop
    AUTH_FAILED = "AUTH_FAILED"    # Cryptographic HMAC or pairing PIN failure
    STOPPED = "STOPPED"            # Intentionally halted by safety stop


class EdgeAlertCode(str, Enum):
    """The 6 mandatory alert categories for PC Core monitoring."""

    ALERT_A_PI5_NOT_CONNECTED = "ALERT_A_PI5_NOT_CONNECTED"
    ALERT_B_SUDDEN_DISCONNECT = "ALERT_B_PI5_SUDDEN_DISCONNECT"
    ALERT_C_CHANNEL_DEGRADED = "ALERT_C_CHANNEL_DEGRADED"
    ALERT_D_SYNC_FAILED = "ALERT_D_SYNC_FAILED"
    ALERT_E_PI5_RECOVERED = "ALERT_E_PI5_RECOVERED"
    ALERT_F_SECURITY_OR_AUTH_FAULT = "ALERT_F_SECURITY_OR_AUTH_FAULT"
    ALERT_G_MIC_FAULT = "ALERT_G_MIC_FAULT"
    ALERT_H_CAMERA_FAULT = "ALERT_H_CAMERA_FAULT"


@dataclass
class EdgeAlertRecord:
    """Immutable record of an alert incident on PC Core."""

    alert_id: str
    code: EdgeAlertCode
    title: str
    message: str
    severity: str  # "INFO", "WARNING", "CRITICAL"
    timestamp_utc: str
    device_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "code": self.code.value,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "timestamp_utc": self.timestamp_utc,
            "device_id": self.device_id,
            "metadata": self.metadata,
            "acknowledged": self.acknowledged,
        }


class EdgeConnectionMonitor:
    """Thread-safe connection monitor running inside PC Central Brain Core.

    Passively and actively monitors Edge device heartbeats, round-trip latency,
    and timeout thresholds. Immediately transitions to DISCONNECTED and triggers
    Alert B if the Pi stops communicating.
    """

    def __init__(
        self,
        heartbeat_timeout_sec: float = 4.0,
        degraded_rtt_threshold_ms: float = 350.0,
        device_id: str = "EDGE-PI5-DESK-01",
    ) -> None:
        self.lock = threading.RLock()
        self.heartbeat_timeout_sec = max(0.05, float(heartbeat_timeout_sec))
        self.degraded_rtt_threshold_ms = max(50.0, float(degraded_rtt_threshold_ms))
        self.device_id = device_id

        self.state: EdgeConnectionState = EdgeConnectionState.DISCONNECTED
        self.last_heartbeat_epoch: float = 0.0
        self.last_heartbeat_utc: str | None = None
        self.last_rtt_ms: float = 0.0
        self.consecutive_misses: int = 0
        self.paired: bool = False
        self.device_label: str = "Raspberry Pi 5 Digital Avatar"

        # Alert tracking & anti-spam
        self.active_alerts: dict[EdgeAlertCode, EdgeAlertRecord] = {}
        self.alert_history: list[EdgeAlertRecord] = []
        self._alert_counter: int = 0

        # Background watchdog thread
        self._stop_event = threading.Event()
        self._watchdog_thread: threading.Thread | None = None

        # Emit initial Alert A if not connected
        self._trigger_alert(
            code=EdgeAlertCode.ALERT_A_PI5_NOT_CONNECTED,
            title="RASPBERRY PI 5 — CHƯA KẾT NỐI",
            message="Chưa phát hiện kết nối từ hình thể số Raspberry Pi 5 trên mạng Wi-Fi.",
            severity="WARNING",
            metadata={"reason": "initial_unconnected_state"},
        )

    def start_watchdog(self, interval_sec: float = 0.5) -> None:
        """Launch background watchdog thread to check deadlines."""
        with self.lock:
            if self._watchdog_thread and self._watchdog_thread.is_alive():
                return
            self._stop_event.clear()
            self._watchdog_thread = threading.Thread(
                target=self._watchdog_loop,
                args=(interval_sec,),
                daemon=True,
                name="EdgeConnectionMonitorWatchdog",
            )
            self._watchdog_thread.start()

    def stop_watchdog(self) -> None:
        """Stop background watchdog thread."""
        self._stop_event.set()
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            self._watchdog_thread.join(timeout=1.0)

    def record_pairing(self, device_id: str, device_label: str) -> None:
        """Record successful pairing handshake with Pi 5."""
        with self.lock:
            self.device_id = device_id
            self.device_label = device_label
            self.paired = True
            self.state = EdgeConnectionState.CONNECTING
            # Clear initial un-paired alert
            self.active_alerts.pop(EdgeAlertCode.ALERT_A_PI5_NOT_CONNECTED, None)

    def record_heartbeat(
        self,
        device_id: str,
        rtt_ms: float = 0.0,
        subsystems_ready: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record authenticated heartbeat received from Edge client."""
        now = time.time()
        now_utc = datetime.now(timezone.utc).isoformat()

        with self.lock:
            was_disconnected = self.state in (
                EdgeConnectionState.DISCONNECTED,
                EdgeConnectionState.RECOVERING,
                EdgeConnectionState.AUTH_FAILED,
            )
            self.last_heartbeat_epoch = now
            self.last_heartbeat_utc = now_utc
            self.last_rtt_ms = max(0.0, float(rtt_ms))
            self.consecutive_misses = 0

            # Evaluate channel health
            if self.last_rtt_ms > self.degraded_rtt_threshold_ms:
                self.state = EdgeConnectionState.DEGRADED
                self._trigger_alert(
                    code=EdgeAlertCode.ALERT_C_CHANNEL_DEGRADED,
                    title="CẢNH BÁO: KÊNH TRUYỀN PC CORE ↔ PI 5 BỊ GIÁN ĐOẠN",
                    message=f"Độ trễ RTT mạng Wi-Fi tăng cao ({self.last_rtt_ms:.1f}ms > {self.degraded_rtt_threshold_ms}ms).",
                    severity="WARNING",
                    metadata={"rtt_ms": self.last_rtt_ms},
                )
            else:
                # Normal healthy channel -> clear degraded alert if any
                self.active_alerts.pop(EdgeAlertCode.ALERT_C_CHANNEL_DEGRADED, None)
                if subsystems_ready:
                    self.state = EdgeConnectionState.READY
                else:
                    self.state = EdgeConnectionState.CONNECTED

            # Clear sudden disconnect alert if active
            had_disconnect = EdgeAlertCode.ALERT_B_SUDDEN_DISCONNECT in self.active_alerts
            self.active_alerts.pop(EdgeAlertCode.ALERT_B_SUDDEN_DISCONNECT, None)
            self.active_alerts.pop(EdgeAlertCode.ALERT_A_PI5_NOT_CONNECTED, None)

            # If recovering from previous disconnect, trigger Alert E
            if was_disconnected and had_disconnect:
                self._trigger_alert(
                    code=EdgeAlertCode.ALERT_E_PI5_RECOVERED,
                    title="RASPBERRY PI 5 ĐÃ KHÔI PHỤC KẾT NỐI",
                    message="Đường truyền hai chiều và xác thực HMAC đã được phục hồi thành công.",
                    severity="INFO",
                    metadata={"recovered_at_utc": now_utc, "rtt_ms": self.last_rtt_ms},
                )

            return self.get_status()

    def record_auth_failure(self, reason: str, metadata: dict[str, Any] | None = None) -> None:
        """Record authentication or cryptographic verification fault."""
        with self.lock:
            self.state = EdgeConnectionState.AUTH_FAILED
            self._trigger_alert(
                code=EdgeAlertCode.ALERT_F_SECURITY_OR_AUTH_FAULT,
                title="CẢNH BÁO: LỖI BẢO MẬT HOẶC THIẾT BỊ KHÔNG HỢP LỆ",
                message=f"Từ chối gói tin từ thiết bị: {reason}",
                severity="CRITICAL",
                metadata=metadata or {"reason": reason},
            )

    def record_sync_failure(self, reason: str) -> None:
        """Record failure during state or task synchronization."""
        with self.lock:
            self._trigger_alert(
                code=EdgeAlertCode.ALERT_D_SYNC_FAILED,
                title="CẢNH BÁO: KHÔNG THỂ HOÀN TẤT ĐỒNG BỘ",
                message=f"Lỗi đồng bộ trạng thái: {reason}",
                severity="WARNING",
                metadata={"reason": reason},
            )

    def record_mic_fault(self, reason: str, metadata: dict[str, Any] | None = None) -> EdgeAlertRecord | None:
        """Record microphone hardware or recording fault."""
        with self.lock:
            return self._trigger_alert(
                code=EdgeAlertCode.ALERT_G_MIC_FAULT,
                title="CẢNH BÁO: LỖI THIẾT BỊ MICROPHONE PI 5",
                message=f"Lỗi phần cứng hoặc ngắt thu âm micro: {reason}",
                severity="WARNING",
                metadata=metadata or {"reason": reason},
            )

    def record_camera_fault(self, reason: str, metadata: dict[str, Any] | None = None) -> EdgeAlertRecord | None:
        """Record camera hardware or capture fault."""
        with self.lock:
            return self._trigger_alert(
                code=EdgeAlertCode.ALERT_H_CAMERA_FAULT,
                title="CẢNH BÁO: LỖI THIẾT BỊ CAMERA PI 5",
                message=f"Lỗi phần cứng hoặc không tìm thấy camera: {reason}",
                severity="WARNING",
                metadata=metadata or {"reason": reason},
            )

    def check_deadline(self) -> None:
        """Evaluate if last heartbeat exceeded timeout (called by watchdog or manual check)."""
        now = time.time()
        with self.lock:
            if not self.last_heartbeat_epoch:
                # Never received any heartbeat
                if self.state != EdgeConnectionState.DISCONNECTED:
                    self.state = EdgeConnectionState.DISCONNECTED
                return

            elapsed = now - self.last_heartbeat_epoch
            if elapsed > self.heartbeat_timeout_sec:
                # Missed deadline!
                self.consecutive_misses += 1
                if self.state in (
                    EdgeConnectionState.CONNECTED,
                    EdgeConnectionState.READY,
                    EdgeConnectionState.DEGRADED,
                    EdgeConnectionState.SYNCING,
                ):
                    self.state = EdgeConnectionState.DISCONNECTED
                    self._trigger_alert(
                        code=EdgeAlertCode.ALERT_B_SUDDEN_DISCONNECT,
                        title="CẢNH BÁO: MẤT KẾT NỐI RASPBERRY PI 5",
                        message=(
                            f"Không nhận được tín hiệu nhịp tim từ {self.device_id} trong {elapsed:.1f}s "
                            f"(Ngưỡng cho phép: {self.heartbeat_timeout_sec}s). Pi 5 có thể đã tắt nguồn hoặc mất sóng Wi-Fi."
                        ),
                        severity="CRITICAL",
                        metadata={
                            "elapsed_sec": round(elapsed, 2),
                            "last_heartbeat_utc": self.last_heartbeat_utc,
                            "misses": self.consecutive_misses,
                        },
                    )

    def _trigger_alert(
        self,
        code: EdgeAlertCode,
        title: str,
        message: str,
        severity: str,
        metadata: dict[str, Any] | None = None,
    ) -> EdgeAlertRecord:
        """Create and store alert record with anti-spam deduplication."""
        self._alert_counter += 1
        record = EdgeAlertRecord(
            alert_id=f"alt_{int(time.time())}_{self._alert_counter}",
            code=code,
            title=title,
            message=message,
            severity=severity,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            device_id=self.device_id,
            metadata=metadata or {},
        )
        self.active_alerts[code] = record
        self.alert_history.append(record)
        # Cap in-memory history to last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
        return record

    def _watchdog_loop(self, interval_sec: float) -> None:
        """Continuous background loop inspecting heartbeat deadline."""
        while not self._stop_event.is_set():
            self.check_deadline()
            self._stop_event.wait(interval_sec)

    def get_status(self) -> dict[str, Any]:
        """Return comprehensive telemetry of Edge connection and active alerts."""
        with self.lock:
            now = time.time()
            elapsed_since_hb = (
                round(now - self.last_heartbeat_epoch, 2)
                if self.last_heartbeat_epoch > 0
                else None
            )
            return {
                "device_id": self.device_id,
                "device_label": self.device_label,
                "state": self.state.value,
                "paired": self.paired,
                "last_heartbeat_utc": self.last_heartbeat_utc,
                "seconds_since_heartbeat": elapsed_since_hb,
                "timeout_sec": self.heartbeat_timeout_sec,
                "rtt_ms": self.last_rtt_ms,
                "active_alert_count": len(self.active_alerts),
                "active_alerts": [a.to_dict() for a in self.active_alerts.values()],
            }

    def get_alert_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return historical connection incident log without erasing past drops."""
        with self.lock:
            return [a.to_dict() for a in self.alert_history[-limit:]]
