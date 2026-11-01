"""Alert Engine — phát hiện bất thường + gửi cảnh báo DM NetChat (M1.5).

Nguyên tắc:
- Chỉ ĐỌC trạng thái từ collectors; quyết định cảnh báo từ ngưỡng tường minh.
- Chống spam: 1 alert / check_id / cooldown (mặc định 300s); alert vẫn được
  ghi log DB ngay cả khi bị chặn gửi.
- Ghi lịch sử vào data/health_alerts.db (audit + hoàn tác được).
- Gửi qua netchat_bridge.send_message (đã có confirm 2 bước tự động).
- Fail-honest: lỗi gửi không được nuốt — ghi lại vào DB với sent=False.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.monitoring.health_state import CRITICAL, NORMAL, UNKNOWN, WARNING

DEFAULT_COOLDOWN_SEC = 300.0
_DB_NAME = "health_alerts.db"
# (01/11/2026, owner-ACK) File trạng thái cảnh báo owner đã xác nhận giữ nguyên.
# Owner ack 'giữ nguyên hiện trạng' (vd: giữ loa TẮT) → AlertEngine KHÔNG còn
# gửi lại cảnh báo đó nữa — tôn trọng quyết định, không spam mỗi cooldown.
_ACK_DB_NAME = "alert_owner_ack.json"

# (02/11/2026, owner yêu cầu) VN-LANG — chuẩn hoá tiếng Việt TẦNG CUỐI cho DM.
# Bản dịch trạng thái/mức độ/mật ngữ kỹ thuật thường gặp; từ lạ giữ nguyên kèm
# giá trị gốc — KHÔNG bao giờ biến dữ liệu kỹ thuật thành chữ khác nghĩa.
_VN_STATUS = {
    "CRITICAL": "NGHIÊM TRỌNG",
    "WARNING": "CẢNH BÁO",
    "NORMAL": "BÌNH THƯỜNG",
    "UNKNOWN": "KHÔNG RÕ",
    "MAINTENANCE": "BẢO TRÌ",
    "ONLINE": "HOẠT ĐỘNG",
    "OFFLINE": "MẤT KẾT NỐI",
    "READY": "SẴN SÀNG",
    "RUNNING": "ĐANG CHẠY",
    "STOPPED": "ĐÃ DỪNG",
    "PAUSED": "TẠM DỪNG",
    "OK": "BÌNH THƯỜNG",
    "FAIL": "LỖI",
    "FAILED": "THẤT BẠI",
    "DOWN": "MẤT KẾT NỐI",
    "HEALTHY": "KHỎE MẠNH",
    "BLOCKED": "BỊ CHẶN",
    "PENDING": "CHỜ XỬ LÝ",
    "APPROVED": "ĐÃ DUYỆT",
    "COMPLETED": "HOÀN THÀNH",
    "IN_PROGRESS": "ĐANG LÀM",
    "WAITING_APPROVAL": "CHỜ DUYỆT",
}
_VN_COMPONENTS = {
    "pc_host": "máy chính",
    "pi5_edge": "Pi 5",
    "selfcare_engine": "tự chăm sóc",
    "ram_percent": "RAM",
    "disk_percent": "ổ đĩa",
    "cpu_percent": "CPU",
    "connectivity": "kết nối",
}


def _vn_message(message: str) -> str:
    """Chuẩn hoá 1 dòng alert/status kỹ thuật → tiếng Việt tự nhiên.

    Giữ nguyên số liệu + token lạ (tên riêng, ID). Ví dụ:
    '[pc_host] ram_percent=95.5 → CRITICAL' → '[máy chính] RAM=95.5 → NGHIÊM TRỌNG'
    """
    out = str(message or "")
    for en, vi in _VN_COMPONENTS.items():
        out = out.replace(en, vi)
    for en, vi in _VN_STATUS.items():
        # chỉ đếm từ nguyên (viết HOA trong thông báo kỹ thuật) — không đụng số liệu
        out = out.replace(f" {en}", f" {vi}").replace(f"→ {en}", f"→ {vi}")
    return out


def load_owner_acks(workspace: Path) -> dict[str, str]:
    """Đọc các cảnh báo owner đã ack. Trả {check_id: reason}."""
    p = Path(workspace) / "data" / _ACK_DB_NAME
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def save_owner_ack(workspace: Path, check_id: str, reason: str = "") -> None:
    """Owner xác nhận một cảnh báo: hệ thống ngừng gửi lại check_id đó."""
    p = Path(workspace) / "data" / _ACK_DB_NAME
    p.parent.mkdir(parents=True, exist_ok=True)
    acks = load_owner_acks(workspace)
    acks[check_id] = {
        "reason": reason or "owner-ack: giữ nguyên hiện trạng",
        "ack_at": datetime.now(timezone.utc).isoformat(),
    }
    p.write_text(json.dumps(acks, ensure_ascii=False, indent=2), encoding="utf-8")


class AlertEngine:
    """Đánh giá ngưỡng + phát alert chống spam + lưu lịch sử."""

    def __init__(self, workspace: Path, cooldown_sec: float = DEFAULT_COOLDOWN_SEC,
                 sender: Any | None = None) -> None:
        self.workspace = Path(workspace)
        self.cooldown_sec = float(cooldown_sec)
        self._lock = threading.Lock()
        self._last_sent: dict[str, float] = {}
        # sender: callable(message: str) -> dict — inject để test không gửi thật.
        self._sender = sender or self._default_sender
        self._ensure_db()

    # ---------- DB ----------
    def _db_path(self) -> Path:
        return self.workspace / "data" / _DB_NAME

    def _ensure_db(self) -> None:
        self._db_path().parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS health_alerts (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       ts_utc TEXT NOT NULL,
                       check_id TEXT NOT NULL,
                       severity TEXT NOT NULL,
                       value TEXT,
                       message TEXT,
                       sent INTEGER NOT NULL DEFAULT 0,
                       suppressed_reason TEXT
                   )""")

    # ---------- gửi ----------
    @staticmethod
    def _default_sender(message: str) -> dict[str, Any]:
        """Gửi DM qua bridge chuẩn (confirm 2 bước tự động).

        (02/11/2026, owner yêu cầu) VN-LANG: mọi DM cho owner chuẩn hoá tiếng
        Việt ở TẦNG CUỐI trước khi rời hệ thống — áp cho tất cả đường gửi qua
        AlertEngine (không phụ thuộc từng đường gọi).
        """
        try:
            from quan_ai_brain.integration.netchat_bridge import send_message
            return send_message(
                "131u5z64pj8q9da3k1xqp3y6pe", _vn_message(message))  # noqa: E501
        except Exception as exc:
            return {"success": False, "error": f"send_error:{type(exc).__name__}"}

    # ---------- API chính ----------
    def evaluate_checks(self, component_id: str,
                        checks: dict[str, dict[str, Any]],
                        thresholds: dict[str, tuple[str, str]]) -> list[dict[str, Any]]:
        """Đánh giá bảng ngưỡng trên snapshot checks của 1 component.

        thresholds: {check_id: (warn_expr, crit_expr)} với expr dạng
        '>=75', '<=2', '==no', '!=yes'. Chỉ hỗ trợ số + chuỗi so sánh đơn giản.
        Trả list alert records (đã ghi DB; 'sent' cho biết đã gửi DM).
        """
        alerts: list[dict[str, Any]] = []
        # (01/11/2026, owner-ACK) Cảnh báo owner đã xác nhận "giữ nguyên" →
        # KHÔNG cảnh báo lại (ghi nhận trong data/alert_owner_ack.json).
        acked = load_owner_acks(self.workspace)
        for check_id, rule in thresholds.items():
            info = checks.get(check_id)
            if not info:
                continue
            value = info.get("value")
            severity = self._classify(value, rule)
            if severity in (WARNING, CRITICAL):
                if check_id in acked:
                    # Vẫn ghi DB để audit, nhưng chặn gửi + đánh dấu lý do.
                    _msg = f"[{component_id}] {check_id}={value} → {severity}"
                    with sqlite3.connect(self._db_path()) as conn:
                        conn.execute(
                            "INSERT INTO health_alerts (ts_utc, check_id, severity, "
                            "value, message, sent, suppressed_reason) "
                            "VALUES (?,?,?,?,?,0,?)",
                            (datetime.now(timezone.utc).isoformat(),
                             f"{component_id}:{check_id}", severity,
                             json.dumps(value, ensure_ascii=False, default=str),
                             f"[OWNER-ACK] {_msg}", "owner_ack"))
                    continue
                alerts.append(self._record_alert(
                    component_id, check_id, severity, value,
                    f"[{component_id}] {check_id}={value} → {severity}"))
        return alerts

    # ---------- classify ----------
    @staticmethod
    def _classify(value: Any, rule: tuple[str, str]) -> str:
        warn_expr, crit_expr = rule
        if value is None:
            return UNKNOWN
        for expr, sev in ((crit_expr, CRITICAL), (warn_expr, WARNING)):
            if not expr:
                continue
            op = None
            for candidate in (">=", "<=", "==", "!=", ">", "<"):
                if expr.startswith(candidate):
                    op = candidate
                    rhs = expr[len(candidate):].strip()
                    break
            if op is None or not rhs:
                continue
            try:
                left, right = float(value), float(rhs)
            except (TypeError, ValueError):
                left, right = str(value), rhs
            ok = False
            if op == ">=":
                ok = left >= right
            elif op == "<=":
                ok = left <= right
            elif op == ">":
                ok = left > right
            elif op == "<":
                ok = left < right
            elif op == "==":
                ok = left == right
            elif op == "!=":
                ok = left != right
            if ok:
                return sev
        return NORMAL

    # ---------- record + gửi chống spam ----------
    def _record_alert(self, component_id: str, check_id: str, severity: str,
                      value: Any, message: str) -> dict[str, Any]:
        ts = datetime.now(timezone.utc).isoformat()
        sent = 0
        suppressed = None
        with self._lock:
            key = f"{component_id}:{check_id}:{severity}"
            now = time.time()
            if now - self._last_sent.get(key, 0.0) < self.cooldown_sec:
                suppressed = f"cooldown:{int(self.cooldown_sec)}s"
            else:
                # VN-LANG (02/11/2026, owner): chuẩn hoá tiếng Việt TRƯỚC khi gọi
                # sender nào (mặc định lẫn inject) — mọi DM ra ngoài đều tiếng Việt.
                result = self._sender(_vn_message(message))
                sent = 1 if result.get("success") else 0
                if not result.get("success"):
                    suppressed = f"send_failed:{result.get('error', 'unknown')[:80]}"
                else:
                    self._last_sent[key] = now
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute(
                "INSERT INTO health_alerts (ts_utc, check_id, severity, value, "
                "message, sent, suppressed_reason) VALUES (?,?,?,?,?,?,?)",
                (ts, f"{component_id}:{check_id}", severity,
                 json.dumps(value, ensure_ascii=False, default=str),
                 message, sent, suppressed))
        return {"ts_utc": ts, "check_id": f"{component_id}:{check_id}",
                "severity": severity, "value": value, "message": message,
                "sent": bool(sent), "suppressed_reason": suppressed}

    # ---------- lịch sử ----------
    def recent_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(self._db_path()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM health_alerts ORDER BY id DESC LIMIT ?",
                (int(limit),)).fetchall()
        return [dict(r) for r in rows]
