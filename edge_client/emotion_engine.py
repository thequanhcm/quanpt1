"""Cherry Emotion Engine — Sprint 3: Expressive Emotion Engine (14/11/2026).

Mirror Python của edge_client/emotion_engine.js — EmotionTransitionEngine +
INTENSITY_PRESETS + MICRO_EMOTIONS + TRANSITION_PRESETS + extract_emotion_context
(negation + multi-emotion). Dùng cho test pytest (mock 100%).

Nguồn thiết kế: CHERRY_EMBODIMENT_SPRINT_PLAN.md §5 (Sprint 3).
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Optional

__all__ = [
    "VERSION", "INTENSITY_PRESETS", "MICRO_EMOTIONS", "TRANSITION_PRESETS",
    "EmotionTransitionEngine", "extract_emotion_context",
]

VERSION = "s3_1411"


def _clamp01(v: Any) -> Optional[float]:
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return None
    return max(0.0, min(1.0, float(v)))


# ===== 1. INTENSITY_PRESETS — cường độ mặc định theo state (0.0–1.0) =====
INTENSITY_PRESETS: Dict[str, float] = {
    "IDLE": 0.3,
    "LISTENING": 0.4,
    "THINKING": 0.5,
    "ANALYTICAL_THINKING": 0.5,
    "CURIOUS": 0.6,
    "WARM_GREETING": 0.7,
    "HAPPY": 0.8,
    "PROUD": 0.8,
    "CONFIDENT_SUCCESS": 0.9,
    "SURPRISED": 0.9,
    "WARNING": 0.8,
    "SERIOUS_ALERT": 1.0,
    "APOLOGETIC": 0.6,
    "EMPATHETIC": 0.6,
    "CONSULTATIVE_INQUIRING": 0.5,
    "SPEAKING": 0.6,
    "ERROR": 0.9,
    "SLEEPING": 0.1,
    "OFFLINE": 0.1,
    "RECONNECTING": 0.5,
    "NEUTRAL": 0.3,
}


# ===== 2. MICRO_EMOTIONS — biến thể vi-cảm xúc (plan §5.2) =====
MICRO_EMOTIONS: Dict[str, Dict[str, Any]] = {
    "HAPPY:gentle_smile": {"intensity_delta": -0.15, "motion_hint": "micro_nod"},
    "HAPPY:bright_smile": {"intensity_delta": 0.1, "motion_hint": "micro_nod"},
    "CONFIDENT_SUCCESS:broad_smile": {"intensity_delta": 0.05, "motion_hint": "proud_nod"},
    "PROUD:subtle_pride": {"intensity_delta": -0.1, "motion_hint": "proud_nod"},
    "PROUD:broad_pride": {"intensity_delta": 0.1, "motion_hint": "proud_nod"},
    "SURPRISED:soft_surprise": {"intensity_delta": -0.2, "motion_hint": "quick_lean"},
    "SURPRISED:strong_surprise": {"intensity_delta": 0.1, "motion_hint": "quick_lean"},
    "EMPATHETIC:warm_empathy": {"intensity_delta": -0.1, "motion_hint": "slow_blink"},
    "EMPATHETIC:deep_empathy": {"intensity_delta": 0.15, "motion_hint": "slow_blink"},
    "APOLOGETIC:soft_apology": {"intensity_delta": -0.15, "motion_hint": "head_down"},
    "APOLOGETIC:deep_apology": {"intensity_delta": 0.2, "motion_hint": "head_down"},
    "CURIOUS:light_curiosity": {"head_tilt": 3, "motion_hint": "head_tilt"},
    "CURIOUS:deep_curiosity": {"head_tilt": 8, "motion_hint": "head_tilt"},
    "THINKING:light_thinking": {"head_tilt": 3, "motion_hint": "head_tilt"},
    "THINKING:deep_thinking": {"head_tilt": 8, "motion_hint": "head_tilt"},
}


# ===== 3. TRANSITION_PRESETS — duration/easing/hold theo state đích =====
TRANSITION_PRESETS: Dict[str, Dict[str, Any]] = {
    "default": {"duration_ms": 300, "easing": "ease-in-out", "hold_ms": 0},
    "to_SERIOUS_ALERT": {"duration_ms": 120, "easing": "ease-out", "hold_ms": 0},
    "to_SURPRISED": {"duration_ms": 150, "easing": "ease-out", "hold_ms": 200},
    "to_HAPPY": {"duration_ms": 300, "easing": "ease-in-out", "hold_ms": 0},
    "to_PROUD": {"duration_ms": 350, "easing": "ease-in-out", "hold_ms": 100},
    "to_APOLOGETIC": {"duration_ms": 400, "easing": "ease-in-out", "hold_ms": 150},
    "to_EMPATHETIC": {"duration_ms": 400, "easing": "ease-in-out", "hold_ms": 150},
    "to_SLEEPING": {"duration_ms": 900, "easing": "ease-in-out", "hold_ms": 0},
    "to_OFFLINE": {"duration_ms": 900, "easing": "ease-in-out", "hold_ms": 0},
    "to_RECONNECTING": {"duration_ms": 200, "easing": "ease-out", "hold_ms": 0},
    "to_NEUTRAL": {"duration_ms": 450, "easing": "ease-in-out", "hold_ms": 0},
    "to_IDLE": {"duration_ms": 450, "easing": "ease-in-out", "hold_ms": 0},
}


def _pick_transition(to_state: str) -> Dict[str, Any]:
    return TRANSITION_PRESETS.get("to_" + to_state, TRANSITION_PRESETS["default"])


# ===== 4. EmotionTransitionEngine — máy trạng thái chuyển cảm xúc =====
class EmotionTransitionEngine:
    """transition_to(to, opts): đổi state qua transition (duration/easing/hold).
    update(now_ms): tick — trả snapshot hiện tại. Intensity 0.0–1.0 (clamp);
    micro-emotion hiệu chỉnh intensity."""

    def __init__(self, now_fn: Optional[Callable[[], float]] = None):
        self._state = "NEUTRAL"
        self._intensity: float = INTENSITY_PRESETS["NEUTRAL"]
        self._micro: Optional[str] = None
        self._transition: Optional[Dict[str, Any]] = None
        self._now_fn = now_fn or (lambda: time.time() * 1000.0)
        self._log: List[Dict[str, Any]] = []
        self._max_log = 32

    def _push_log(self, entry: Dict[str, Any]) -> None:
        self._log.append(entry)
        if len(self._log) > self._max_log:
            self._log.pop(0)

    def get_log(self) -> List[Dict[str, Any]]:
        return list(self._log)

    def _now(self) -> float:
        return self._now_fn()

    def transition_to(self, to_state: str, opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        opts = opts or {}
        from_state = self._state
        micro = opts.get("micro")
        explicit = _clamp01(opts.get("intensity"))

        if to_state == from_state and not opts.get("force"):
            if micro:
                self._micro = micro
            # Same state + micro → vẫn áp dụng micro cfg (intensity delta)
            base = explicit if explicit is not None else INTENSITY_PRESETS.get(to_state, 0.5)
            micro_cfg = MICRO_EMOTIONS.get(f"{to_state}:{micro}") if micro else None
            if micro_cfg and isinstance(micro_cfg.get("intensity_delta"), (int, float)):
                adj = _clamp01(base + micro_cfg["intensity_delta"])
                if adj is not None:
                    self._intensity = adj
            elif explicit is not None:
                self._intensity = explicit
            self._push_log({"t": self._now(), "kind": "adjust", "state": from_state,
                            "micro": micro, "intensity": self._intensity})
            return {"changed": False, "from": from_state, "to": to_state,
                    "duration_ms": 0, "intensity": self._intensity, "micro": self._micro}

        preset = _pick_transition(to_state)
        now = self._now()
        duration = opts.get("duration_ms") or preset["duration_ms"]
        hold = opts["hold_ms"] if opts.get("hold_ms") is not None else preset["hold_ms"]

        base = explicit if explicit is not None else INTENSITY_PRESETS.get(to_state, 0.5)
        micro_cfg = MICRO_EMOTIONS.get(f"{to_state}:{micro}") if micro else None
        intensity = base
        if micro_cfg and isinstance(micro_cfg.get("intensity_delta"), (int, float)):
            adj = _clamp01(base + micro_cfg["intensity_delta"])
            if adj is not None:
                intensity = adj

        self._transition = {
            "from": from_state,
            "to": to_state,
            "start_ms": now,
            "duration_ms": duration,
            "easing": preset["easing"],
            "hold_until_ms": now + duration + hold,
            "micro": micro,
            "intensity": intensity,
        }
        self._state = to_state
        self._micro = micro
        self._intensity = intensity
        self._push_log({"t": now, "kind": "transition", "from": from_state,
                        "to": to_state, "duration_ms": duration, "hold_ms": hold,
                        "intensity": intensity, "micro": micro})
        return {"changed": True, "from": from_state, "to": to_state,
                "duration_ms": duration, "hold_ms": hold, "intensity": intensity,
                "micro": micro, "easing": preset["easing"]}

    def update(self, now_ms: Optional[float] = None) -> Dict[str, Any]:
        now = now_ms if now_ms is not None else self._now()
        tr = self._transition
        if tr and now >= tr["hold_until_ms"]:
            self._transition = None
        return self.get_current()

    def get_progress(self, now_ms: Optional[float] = None) -> Optional[float]:
        now = now_ms if now_ms is not None else self._now()
        tr = self._transition
        if not tr:
            return None
        p = (now - tr["start_ms"]) / tr["duration_ms"]
        return max(0.0, min(1.0, p))

    def get_current(self) -> Dict[str, Any]:
        return {"state": self._state, "intensity": self._intensity,
                "micro": self._micro, "transitioning": self._transition is not None}


# ===== 5. extract_emotion_context — context-aware (negation + multi) =====
EMOTION_CATEGORIES: List[Dict[str, Any]] = [
    {"name": "APOLOGETIC",
     "re": re.compile(r"xin lỗi|chia buồn|rất tiếc|đáng tiếc|gây phiền|thừa nhận|mất thời gian|tạm biệt|không may")},
    {"name": "SERIOUS_ALERT",
     "re": re.compile(r"cảnh báo|chú ý|lưu ý|nguy hiểm|rủi ro|không được|chặn|thất bại|lỗi|bất thường|sự cố|dừng|khẩn cấp|nghiêm cấm")},
    {"name": "CONFIDENT_SUCCESS",
     "re": re.compile(r"hoàn thành|thành công|chính xác|đạt chuẩn|vượt qua|tốt đẹp|100%|xuất sắc|hoàn hảo|thắng lợi")},
    {"name": "ANALYTICAL_THINKING",
     "re": re.compile(r"phân tích|dữ liệu|kết quả|nghiên cứu|thuật toán|kiến trúc|thông số|đo lường|logic|thống kê|chi tiết|báo cáo|kiểm tra|xác nhận|chỉ số")},
    {"name": "CONSULTATIVE_INQUIRING",
     "re": re.compile(r"kính trình|đề xuất|chờ anh|xin ý kiến|phê duyệt|chỉ đạo|chờ xác nhận|tham vấn")},
    {"name": "WARM_GREETING",
     "re": re.compile(r"chào|xin chào|dạ|vâng|rất vui|hân hạnh|sẵn sàng|chúc|em đây|em nghe|tuyệt vời|cảm ơn")},
    {"name": "SURPRISED",
     "re": re.compile(r"bất ngờ|ngạc nhiên|ọe|trời ơi|ổn quá|wow|hoàn toàn mới|lần đầu tiên|khám phá")},
    {"name": "CURIOUS",
     "re": re.compile(r"tại sao|như thế nào|thế nào|làm sao|giải thích|cho em hỏi|thắc mắc|tò mò|muốn biết|hỏi anh|câu hỏi")},
    {"name": "PROUD",
     "re": re.compile(r"tự hào|cải thiện|tiến bộ|tối ưu|nâng cấp|hoàn thiện|phát triển|nhất quán|ổn định|học được|nắm bắt")},
]

NEGATION_RE = re.compile(r"(không|chưa|chẳng|đừng|không phải|không thể|không được)\s*$")


def _is_negated(raw: str, index: int) -> bool:
    if index <= 0:
        return False
    window_start = max(0, index - 12)
    window = raw[window_start:index]
    return bool(NEGATION_RE.search(window))


def extract_emotion_context(text: Optional[str]) -> Dict[str, Any]:
    """Context-aware extractor: trả {primary, secondary, negated: [...]}.
    Negation handling: "không thành công" → SUCCESS bị phủ định.
    Multi-emotion: tối đa 2 emotion theo thứ tự ưu tiên bảng."""
    result: Dict[str, Any] = {"primary": "NEUTRAL", "secondary": None, "negated": []}
    if not text or not isinstance(text, str):
        return result
    raw = text.lower()
    hits: List[str] = []
    for cat in EMOTION_CATEGORIES:
        m = cat["re"].search(raw)
        if m:
            if _is_negated(raw, m.start()):
                result["negated"].append(cat["name"])
            else:
                hits.append(cat["name"])
    if hits:
        result["primary"] = hits[0]
    if len(hits) > 1:
        result["secondary"] = hits[1]
    return result
