"""Health Monitor Runtime — vòng đánh giá định kỳ + Alert Engine (M1.5).

Server khởi động monitor này như 1 daemon thread: mỗi cycle (mặc định 120s)
lấy snapshot aggregator, đối chiếu ngưỡng, phát alert qua AlertEngine.
Đọc-only + gửi DM khi cảnh báo. Có stop() để test sạch.

Thiết kế chống treo: mọi exception trong cycle bị bắt và ghi log console,
không chết thread; cycle chạy trong try/finally.
"""
from __future__ import annotations

import threading
import traceback
from typing import Any

from quan_ai_brain.monitoring.aggregator import HealthAggregator
from quan_ai_brain.monitoring.alert_engine import AlertEngine

DEFAULT_CYCLE_SEC = 120.0


class HealthMonitor:
    """Vòng đánh giá sức khỏe định kỳ chạy nền."""

    def __init__(self, workspace: Any, aggregator: HealthAggregator,
                 cycle_sec: float = DEFAULT_CYCLE_SEC,
                 alert_engine: AlertEngine | None = None,
                 self_care: Any | None = None) -> None:
        self.workspace = workspace
        self.aggregator = aggregator
        self.cycle_sec = float(cycle_sec)
        self.alert_engine = alert_engine or AlertEngine(workspace)
        # M4: SelfCareEngine tuỳ chọn — nếu inject, mỗi cycle chạy thêm health checks
        # thực (TCP Ollama/8765/8766/Pi5) và cảnh báo qua cùng AlertEngine chống spam.
        self.self_care = self_care
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cycles = 0
        self._last_overall: str = "UNKNOWN"
        self._clo_stall_prev: bool = False  # M4-B: edge-trigger cảnh báo CLO kẹt

    # ----- lifecycle -----
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="tony-health-monitor", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    # ----- vòng chính -----
    def _run_loop(self) -> None:
        # Chạy 1 cycle ngay khi start (không chờ cycle đầu tiên).
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception:
                # Fail-honest: in ra console server, không giết thread.
                print("[HEALTH-MONITOR] cycle error:\n"
                      + traceback.format_exc(limit=3))
            self._stop.wait(self.cycle_sec)

    def run_once(self) -> dict[str, Any]:
        """1 lần đánh giá: snapshot → threshold → alerts. Trả kết quả cycle."""
        snap = self.aggregator.snapshot()
        self._cycles += 1
        self._last_overall = snap.get("overall_status", "UNKNOWN")

        alerts: list[dict[str, Any]] = []
        for comp_id, comp_key in (("pc_host", "pc"), ("pi5_edge", "pi5")):
            comp = snap.get(comp_key) or {}
            checks = comp.get("checks", {})
            thresholds = self._thresholds_for(comp_key)
            if checks and thresholds:
                alerts.extend(self.alert_engine.evaluate_checks(
                    comp_id, checks, thresholds))

        # M4: Self-Care thực — health checks TCP thật mỗi cycle (nếu được inject).
        # Chỉ check KHÔNG healthy mới thành alert (value = 1 WARNING / 2 CRITICAL,
        # rule ">=1"/">=2") — check healthy không bao giờ tạo alert giả.
        self_care_summary: dict[str, Any] | None = None
        if self.self_care is not None:
            try:
                checks = self.self_care.run_all_health_checks()
                self_care_summary = self.self_care.get_health_summary()
                pseudo: dict[str, dict[str, Any]] = {}
                for c in checks:
                    sev_level = {"healthy": 0, "warning": 1, "degraded": 1,
                                 "critical": 2, "down": 2}.get(str(c.status.value), 0)
                    if sev_level == 0:
                        continue
                    pseudo[f"selfcare:{c.component}:{c.metric}"] = {
                        "value": sev_level,
                        "status": "measured", "severity": "measured",
                        "reason": f"{c.message} (self_care thực)", "measured_at": c.timestamp,
                    }
                if pseudo:
                    alerts.extend(self.alert_engine.evaluate_checks(
                        "selfcare_engine", pseudo,
                        {k: (">=1", ">=2") for k in pseudo}))
            except Exception:
                # Fail-honest: lỗi self-care không được giết vòng health chính.
                print("[HEALTH-MONITOR] self_care cycle error:\n"
                      + traceback.format_exc(limit=3))
                self_care_summary = {"error": "self_care_cycle_failed"}

        # M4-B (M5): Self-Learning Health — CLO session RUNNING quá 24h mà
        # không có session mới → cảnh báo edge-trigger (chỉ khi chuyển từ
        # "kẹt" sang "bình thường" hoặc ngược lại), không spam mỗi cycle.
        clo_alert = self._evaluate_clo_stall()
        if clo_alert:
            alerts.append(clo_alert)

        return {
            "cycle": self._cycles,
            "overall_status": self._last_overall,
            "alerts": alerts,
            "self_care_summary": self_care_summary,
        }

    def _evaluate_clo_stall(self) -> dict[str, Any] | None:
        """Cảnh báo vòng tự chủ học (CLO) kẹt. Fail-honest: không đọc được → None.

        Gửi qua AlertEngine THẬT nếu có (đủ cooldown + DB + DM); với alert_engine
        giả (test) → KHÔNG gửi, ghi sent=False + lý do. Không bao giờ khai sent=True
        khi chưa gửi thật.
        """
        try:
            from quan_ai_brain.cognition.self_model_engine import SelfModelEngine
            state = SelfModelEngine(str(self.workspace)).get_learning_checkpoint_state(
                self.workspace)
        except Exception:
            return None
        last = state.get("clo_last_session")
        if not last or str(last.get("status")) != "RUNNING":
            self._clo_stall_prev = False
            # (22/11/2026) Hết kẹt → xoá state persist để cycle sau alert lại bình thường
            try:
                import json as _json
                _sp = self.workspace / "data" / "health_clo_stall_state.json"
                if _sp.exists():
                    _sp.unlink()
            except Exception:
                pass
            return None
        try:
            from datetime import datetime, timezone
            started = datetime.fromisoformat(str(last["started_at"]).replace("Z", "+00:00"))
            age_h = (datetime.now(timezone.utc) - started).total_seconds() / 3600.0
        except Exception:
            return None
        if age_h < 24.0:
            self._clo_stall_prev = False
            return None
        # (22/11/2026, fix spam) Edge-trigger TRƯỚC ĐÂY chỉ ở biến in-memory — mỗi
        # lần restart server process mới reset về False → DM lại owner ngay cycle
        # đầu (thực tế: 20/11 gửi 4 lần = 4 lần restart; 22/11 22:31+23:32 = 2 lần).
        # Fix: persist trạng thái đã-alert vào data/health_clo_stall_state.json
        # (theo cycle). Re-alert chỉ khi age_h tăng thêm ≥12h kể từ lần alert cuối
        # (nhắc lại có chủ đích, không spam); hết RUNNING → xoá state.
        import json as _json
        _state_path = self.workspace / "data" / "health_clo_stall_state.json" \
            if hasattr(self.workspace, "__truediv__") else None
        _prev_cycle = None
        _prev_age = None
        if _state_path is not None:
            try:
                _st = _json.loads(_state_path.read_text(encoding="utf-8"))
                if _st.get("cycle") == last.get("cycle"):
                    _prev_cycle = _st.get("cycle")
                    _prev_age = float(_st.get("alerted_age_h", 0.0))
            except Exception:
                _prev_cycle = None  # fail-honest: state hỏng → coi như chưa alert
        if _prev_cycle is not None and (age_h - _prev_age) < 12.0:
            self._clo_stall_prev = True
            return None  # đã cảnh báo cycle này — không lặp sau restart
        self._clo_stall_prev = True
        if _state_path is not None:
            try:
                _state_path.parent.mkdir(parents=True, exist_ok=True)
                _state_path.write_text(_json.dumps({
                    "cycle": last.get("cycle"),
                    "alerted_age_h": round(age_h, 2),
                    "ts_utc": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass  # fail-honest: không ghi được state → vẫn alert như cũ
        # (01/11/2026, chuẩn hoá tiếng Việt) Trạng thái RUNNING → "ĐANG CHẠY"
        message = (f"Buổi tự học liên tục #{last.get('cycle')} ĐANG CHẠY {age_h:.0f}h "
                   f"không tiến triển — tự chủ học kẹt (thường do Q-4 chưa duyệt)")
        value = f"{age_h:.0f}h"
        sent = False
        suppressed = None
        record_fn = getattr(self.alert_engine, "_record_alert", None)
        if callable(record_fn):
            try:
                rec = record_fn("selfcare", "clo_stalled", "WARNING", value, message)
                sent = bool(rec.get("sent"))
                suppressed = rec.get("suppressed_reason")
            except Exception as exc:
                suppressed = f"send_error:{type(exc).__name__}"
        else:
            suppressed = "no_real_alert_engine"
        from datetime import datetime, timezone
        return {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "check_id": "selfcare:clo_stalled",
            "severity": "WARNING",
            "value": value,
            "message": message,
            "sent": sent,
            "suppressed_reason": suppressed,
        }

    @staticmethod
    def _thresholds_for(comp_key: str) -> dict[str, tuple[str, str]]:
        # import tại chỗ để tránh vòng import
        from quan_ai_brain.monitoring.aggregator import PI5_THRESHOLDS, PC_THRESHOLDS
        return PC_THRESHOLDS if comp_key == "pc" else PI5_THRESHOLDS

    # ----- trạng thái cho API -----
    def status(self) -> dict[str, Any]:
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "cycle_sec": self.cycle_sec,
            "cycles_done": self._cycles,
            "last_overall_status": self._last_overall,
            "recent_alerts": self.alert_engine.recent_alerts(limit=20),
        }
