"""UDR-1 Device Store — lưu + phát sự kiện thiết bị Pi5, DM NetChat cho chủ (04/11/2026).

Nhận diff thiết bị từ Edge Agent (kênh /api/executive/edge/events đã HMAC),
lưu SQLite data/edge_devices.db, và gửi DM TONY qua AlertEngine (chống-spam
cooldown 300s/sự kiện) đúng chỉ thị quanpt1: "gửi về DM TONY cho anh biết hiện
trạng".

Fail-closed: lỗi DB/net không giết server; DM lỗi chỉ ghi sent=False.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COOLDOWN_SEC = 300.0  # chống spam DM: 1 DM / loại sự kiện / 5 phút


class DeviceStore:
    """Lưu thiết bị hiện có + lịch sử cắm/rút + gửi DM owner (cooldown)."""

    def __init__(self, db_path: Path | str, sender: Any = None,
                 cooldown_sec: float = COOLDOWN_SEC) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._sender = sender  # callable(message) -> dict; None = chỉ lưu DB
        self._cooldown = float(cooldown_sec)
        self._last_sent: dict[str, float] = {}
        self._init_db()

    # ------------------------------------------------------------------
    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS edge_device_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_utc TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    bus TEXT NOT NULL,
                    name TEXT,
                    vid_pid TEXT,
                    event TEXT NOT NULL,          -- ADDED / REMOVED / SNAPSHOT
                    meta_json TEXT
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS edge_device_current (
                    fingerprint TEXT PRIMARY KEY,
                    bus TEXT NOT NULL,
                    dev_id TEXT NOT NULL,
                    name TEXT,
                    vid_pid TEXT,
                    first_seen_utc TEXT NOT NULL,
                    last_seen_utc TEXT NOT NULL,
                    meta_json TEXT
                )
            """)
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_ede_ts ON edge_device_events(ts_utc)")

    # ------------------------------------------------------------------
    def record_added(self, device_id: str, ev: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        det = ev.get("details", {}) or {}
        fp = str(det.get("fingerprint", ""))[:160]
        dev = det.get("device", {}) or {}
        bus = str(dev.get("bus", det.get("fingerprint", "?").split(":", 1)[0]))[:20]
        name = str(dev.get("name", det.get("desc", "")))[:120]
        vid_pid = str(dev.get("vid_pid", ""))[:20]
        import json as _json
        meta = _json.dumps(dev.get("meta", {}), ensure_ascii=False)[:400]
        with self._lock, sqlite3.connect(self.db_path) as con:
            con.execute(
                "INSERT INTO edge_device_events (ts_utc, device_id, fingerprint,"
                " bus, name, vid_pid, event, meta_json)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (now, device_id, fp, bus, name, vid_pid, "ADDED", meta))
            con.execute(
                "INSERT INTO edge_device_current (fingerprint, bus, dev_id,"
                " name, vid_pid, first_seen_utc, last_seen_utc, meta_json)"
                " VALUES (?,?,?,?,?,?,?,?)"
                " ON CONFLICT(fingerprint) DO UPDATE SET"
                " last_seen_utc=excluded.last_seen_utc,"
                " name=excluded.name",
                (fp, bus, str(dev.get("dev_id", ""))[:80], name, vid_pid,
                 now, now, meta))
        dm = self._maybe_send(
            f"🔌 Thiết bị CẮM vào Pi5: {name}" +
            (f" ({vid_pid})" if vid_pid else "") +
            f"\nBus: {bus} | lúc {now[11:19]} UTC",
            key=f"ADDED:{fp}")
        return {"stored": True, "dm": dm}

    # ------------------------------------------------------------------
    def record_removed(self, device_id: str, ev: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        det = ev.get("details", {}) or {}
        fp = str(det.get("fingerprint", ""))[:160]
        bus = fp.split(":", 1)[0] if ":" in fp else "?"
        desc = str(det.get("desc", ""))[:120]
        with self._lock, sqlite3.connect(self.db_path) as con:
            con.execute(
                "INSERT INTO edge_device_events (ts_utc, device_id, fingerprint,"
                " bus, name, vid_pid, event, meta_json)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (now, device_id, fp, bus, desc, "", "REMOVED", "{}"))
            con.execute(
                "DELETE FROM edge_device_current WHERE fingerprint = ?", (fp,))
        dm = self._maybe_send(
            f"⚠️ Thiết bị RÚT khỏi Pi5: {desc}\nlúc {now[11:19]} UTC",
            key=f"REMOVED:{fp}")
        return {"stored": True, "dm": dm}

    # ------------------------------------------------------------------
    def record_snapshot(self, device_id: str,
                        summary: dict[str, Any]) -> dict[str, Any]:
        """Lưu bản chụp định kỳ từ heartbeat (không DM — tránh spam)."""
        now = datetime.now(timezone.utc).isoformat()
        import json as _json
        try:
            with self._lock, sqlite3.connect(self.db_path) as con:
                for dev in summary.get("devices", []) or []:
                    if not isinstance(dev, dict) or not dev.get("dev_id"):
                        continue
                    fp = f"{dev.get('bus', '?')}:{dev.get('dev_id', '?')}"[:160]
                    con.execute(
                        "INSERT INTO edge_device_current (fingerprint, bus,"
                        " dev_id, name, vid_pid, first_seen_utc,"
                        " last_seen_utc, meta_json)"
                        " VALUES (?,?,?,?,?,?,?,?)"
                        " ON CONFLICT(fingerprint) DO UPDATE SET"
                        " last_seen_utc=excluded.last_seen_utc",
                        (fp, str(dev.get("bus", "?"))[:20],
                         str(dev.get("dev_id", ""))[:80],
                         str(dev.get("name", ""))[:120],
                         str(dev.get("vid_pid", ""))[:20], now, now,
                         _json.dumps(dev.get("meta", {}),
                                     ensure_ascii=False)[:400]))
        except Exception:
            pass
        return {"stored": True}

    # ------------------------------------------------------------------
    def current_devices(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT fingerprint, bus, dev_id, name, vid_pid,"
                " first_seen_utc, last_seen_utc FROM edge_device_current"
                " ORDER BY bus, dev_id").fetchall()
        return [dict(r) for r in rows]

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT ts_utc, device_id, fingerprint, bus, name, event,"
                " vid_pid FROM edge_device_events"
                " ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    def _maybe_send(self, message: str, key: str) -> dict[str, Any]:
        """DM owner qua AlertEngine sender — cooldown chống spam; fail-closed."""
        if self._sender is None:
            return {"sent": False, "reason": "no_sender"}
        now = time.time()
        with self._lock:
            last = self._last_sent.get(key, 0.0)
            if now - last < self._cooldown:
                return {"sent": False, "reason": "cooldown",
                        "retry_in_s": round(self._cooldown - (now - last), 1)}
            self._last_sent[key] = now
        try:
            raw = self._sender(message) or {}
            # chuẩn hoá: sender thật (netchat_bridge) trả {"success": True,...}
            sent = bool(raw.get("sent", raw.get("success", False)))
            return {"sent": sent, "raw": raw}
        except Exception as exc:
            return {"sent": False, "reason": f"send_error:{type(exc).__name__}"}


def default_sender() -> Any:
    """Sender chuẩn: netchat DM TONY (kênh owner đã dùng cho mọi alert)."""
    try:
        from quan_ai_brain.monitoring.alert_engine import AlertEngine
        return AlertEngine._default_sender
    except Exception:
        return None
