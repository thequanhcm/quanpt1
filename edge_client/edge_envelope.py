"""Cherry Edge Envelope — Sprint 1: Unified Emotion Protocol (14/11/2026).

Mirror Python của edge_client/avatar_protocol.js (IPC envelope validator +
state normalization). PC server bọc envelope trước khi gửi xuống Pi5 daemon;
Pi5 daemon validate bằng chính module này (file đứng cạnh client_daemon.py
trên Pi5) — 2 nền tảng dùng 1 nguồn sự thật.

Card: TASK-EMBODIMENT-S1 (APPROVED, auth owner_desktop_chat_directive).
"""
from __future__ import annotations

import time
import uuid
from typing import Any

PROTOCOL_VERSION = "s1_1411"

# ===== 22 STATE (canonical — khớp avatar_protocol.js) =====
STATES: set[str] = {
    "IDLE", "LISTENING", "THINKING", "RESEARCHING", "LEARNING", "SPEAKING",
    "HAPPY", "EMPATHETIC", "CONFUSED", "SUCCESS", "WARNING",
    "WAITING_FOR_OWNER", "BLOCKED", "ERROR", "SAFE_MODE", "OFFLINE",
    "RECONNECTING", "SLEEPING", "SURPRISED", "CURIOUS", "APOLOGETIC", "PROUD",
}

STATE_ALIASES: dict[str, str] = {
    "ONLINE": "IDLE", "READY": "IDLE", "STANDBY": "IDLE",
    "SPEAK": "SPEAKING", "TALKING": "SPEAKING",
    "LISTEN": "LISTENING", "HEARING": "LISTENING",
    "WAIT": "WAITING_FOR_OWNER", "WAITING": "WAITING_FOR_OWNER",
    "PENDING": "WAITING_FOR_OWNER", "FAIL": "ERROR", "CRITICAL": "BLOCKED",
    "BOOTING": "RECONNECTING", "CONNECTING": "RECONNECTING",
}

DEFAULT_MAX_SKEW_MS = 30_000
DEFAULT_SEQ_TOLERANCE = 0


def normalize_state(state: Any) -> str:
    """State lạ/cũ → state canonical 22 (JS: normalizeState)."""
    s = str(state or "").strip().upper()
    if s in STATES:
        return s
    return STATE_ALIASES.get(s, "IDLE")


def new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


def build_envelope(
    action: str,
    *,
    platform: str = "PC",
    sequence: int | None = None,
    timestamp_ms: float | None = None,
    expiry_ms: float | None = None,
    **payload: Any,
) -> dict[str, Any]:
    """Bọc payload IPC vào envelope 17 field (MASTER PROMPT V4.0 §3.7).

    Fields cố định: event_id, sequence, platform, timestamp, expiry,
    operational_state, emotion, emotion_intensity, gesture, motion_profile,
    speaking_status, audio_status, animation_duration, protocol_version.
    Payload riêng của action (state, text, timeline...) đè lên bằng update.
    """
    ts = float(timestamp_ms) if timestamp_ms is not None else time.time() * 1000.0
    ev: dict[str, Any] = {
        "event_id": new_event_id(),
        "sequence": sequence,
        "platform": platform,
        "timestamp": ts,
        "expiry": expiry_ms,
        "operational_state": None,
        "emotion": None,
        "emotion_intensity": None,
        "gesture": None,
        "motion_profile": None,
        "speaking_status": None,
        "audio_status": None,
        "animation_duration": None,
        "protocol_version": PROTOCOL_VERSION,
    }
    if action:
        ev["action"] = action
    if payload:
        ev.update(payload)
    return ev


class EnvelopeValidator:
    """Stateful validator — mirror JS validateEnvelope.

    DUPLICATE: event_id trùng trong window `seen_capacity` event gần nhất.
    STALE: |now - timestamp| > max_skew_ms (30s mặc định).
    EXPIRED: expiry < now.
    OUT_OF_ORDER: sequence lùi (per-platform monotonic, tolerance mặc định 0).
    seen/last_seq chỉ được cập nhật khi envelope HỢP LỆ (mirror JS).
    """

    def __init__(
        self,
        *,
        max_skew_ms: float = DEFAULT_MAX_SKEW_MS,
        seq_tolerance: int = DEFAULT_SEQ_TOLERANCE,
        seen_capacity: int = 512,
        clock: Any = None,
    ) -> None:
        self.max_skew_ms = float(max_skew_ms)
        self.seq_tolerance = int(seq_tolerance)
        self.seen: dict[str, bool] = {}
        self.last_seq: dict[str, float] = {}
        self._seen_capacity = max(1, int(seen_capacity))
        # clock() trả ms; inject được để test kiểm soát thời gian.
        self._clock = clock or (lambda: time.time() * 1000.0)

    def validate(self, ev: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(ev, dict):
            return {"ok": False, "reason": "MISSING_ENVELOPE"}

        event_id = ev.get("event_id")
        if not event_id:
            return {"ok": False, "reason": "MISSING_FIELD:event_id"}
        if event_id in self.seen:
            return {"ok": False, "reason": "DUPLICATE"}

        now_ms = float(self._clock())

        try:
            ts = float(ev.get("timestamp"))
        except (TypeError, ValueError):
            return {"ok": False, "reason": "MISSING_FIELD:timestamp"}
        if ts <= 0:
            return {"ok": False, "reason": "MISSING_FIELD:timestamp"}
        if abs(now_ms - ts) > self.max_skew_ms:
            return {"ok": False, "reason": "STALE"}

        expiry = ev.get("expiry")
        if expiry is not None:
            try:
                exp = float(expiry)
            except (TypeError, ValueError):
                exp = 0.0
            if exp > 0 and now_ms > exp:
                return {"ok": False, "reason": "EXPIRED"}

        platform = str(ev.get("platform") or "UNKNOWN")
        seq_raw = ev.get("sequence")
        seq: float | None = None
        if seq_raw is not None:
            try:
                seq = float(seq_raw)
            except (TypeError, ValueError):
                return {"ok": False, "reason": "MISSING_FIELD:sequence"}
            prev = self.last_seq.get(platform)
            if prev is not None and seq <= prev - self.seq_tolerance:
                return {"ok": False, "reason": "OUT_OF_ORDER"}

        # Hợp lệ → ghi nhận (duplicate + sequence tracking).
        self.seen[str(event_id)] = True
        if len(self.seen) > self._seen_capacity:
            # FIFO xấp xỉ: bỏ các key cũ nhất (dict giữ thứ tự chèn).
            overflow = len(self.seen) - self._seen_capacity
            for k in list(self.seen.keys())[:overflow]:
                self.seen.pop(k, None)
        if seq is not None:
            cur = self.last_seq.get(platform)
            if cur is None or seq > cur:
                self.last_seq[platform] = seq
        return {"ok": True, "reason": "OK"}


def validate_envelope_once(
    ev: dict[str, Any] | None, *, now_ms: float | None = None
) -> dict[str, Any]:
    """Validate không cần giữ state (tiện test/lệnh đơn lẻ).

    Vẫn chặn DUPLICATE/OUT_OF_ORDER trong phạm vi 1 lần gọi: thiếu
    event_id/timestamp/sequence sai kiểu → báo MISSING_FIELD; còn lại coi OK.
    """
    if not isinstance(ev, dict):
        return {"ok": False, "reason": "MISSING_ENVELOPE"}
    if not ev.get("event_id"):
        return {"ok": False, "reason": "MISSING_FIELD:event_id"}
    try:
        ts = float(ev.get("timestamp"))
    except (TypeError, ValueError):
        return {"ok": False, "reason": "MISSING_FIELD:timestamp"}
    if ts <= 0:
        return {"ok": False, "reason": "MISSING_FIELD:timestamp"}
    if now_ms is not None and abs(now_ms - ts) > DEFAULT_MAX_SKEW_MS:
        return {"ok": False, "reason": "STALE"}
    if ev.get("sequence") is not None:
        try:
            float(ev.get("sequence"))
        except (TypeError, ValueError):
            return {"ok": False, "reason": "MISSING_FIELD:sequence"}
    return {"ok": True, "reason": "OK"}
