"""Sprint 3 — Expressive Emotion Engine (14/11/2026).

Card: TASK-EMBODIMENT-S3 (APPROVED, auth owner_desktop_chat_directive).
Test 5 ca theo CHERRY_EMBODIMENT_SPRINT_PLAN.md §5.4:
  1. Emotion transition mượt (duration + progress + hold)
  2. Emotion intensity hiển thị đúng (clamp + preset + micro delta)
  3. Micro-emotions phân biệt được
  4. Context-aware emotion đúng (multi-emotion)
  5. Negation handling đúng
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "edge_client"))

import emotion_engine as ee  # noqa: E402


# ===== Helpers =====
def _fixed_now() -> float:
    return 1000000.0


def _engine() -> ee.EmotionTransitionEngine:
    return ee.EmotionTransitionEngine(now_fn=_fixed_now)


# ===== 1. Emotion transition mượt =====
class TestEmotionTransition:
    def test_transition_changes_state_with_preset(self):
        e = _engine()
        r = e.transition_to("HAPPY")
        assert r["changed"] is True
        assert r["from"] == "NEUTRAL" and r["to"] == "HAPPY"
        assert r["duration_ms"] == 300
        assert r["intensity"] == 0.8

    def test_transition_progress_0_to_1(self):
        e = _engine()
        e.transition_to("HAPPY")
        assert e.get_progress(1000000) == 0.0
        assert e.get_progress(1000150) == pytest.approx(0.5)
        assert e.get_progress(1000300) == 1.0
        # hold = 0 → sau 300ms transition null
        e.update(1000300)
        assert e.get_current()["transitioning"] is False

    def test_transition_hold_keeps_transitioning(self):
        e = _engine()
        e.transition_to("SURPRISED")  # 150ms + hold 200ms
        assert e.get_progress(1000150) == 1.0
        e.update(1000150)
        # hold 200ms → vẫn transitioning đến 350ms
        assert e.get_current()["transitioning"] is True
        e.update(1000350)
        assert e.get_current()["transitioning"] is False

    def test_same_state_no_transition(self):
        e = _engine()
        r = e.transition_to("HAPPY")
        r2 = e.transition_to("HAPPY")
        assert r2["changed"] is False
        assert r2["duration_ms"] == 0

    def test_force_retransition(self):
        e = _engine()
        e.transition_to("HAPPY")
        r = e.transition_to("HAPPY", opts={"force": True})
        assert r["changed"] is True

    def test_log_records_transitions(self):
        e = _engine()
        e.transition_to("HAPPY")
        e.transition_to("PROUD")
        log = e.get_log()
        assert len(log) == 2
        assert log[0]["kind"] == "transition" and log[0]["to"] == "HAPPY"
        assert log[1]["to"] == "PROUD"

    def test_transition_log_cap_32(self):
        e = _engine()
        states = ["HAPPY", "PROUD", "NEUTRAL"]
        for i in range(40):
            e.transition_to(states[i % 3], opts={"force": True})
        assert len(e.get_log()) == 32

    def test_alert_transition_fast_120ms(self):
        e = _engine()
        r = e.transition_to("SERIOUS_ALERT")
        assert r["duration_ms"] == 120
        assert r["easing"] == "ease-out"

    def test_sleeping_transition_slow_900ms(self):
        e = _engine()
        r = e.transition_to("SLEEPING")
        assert r["duration_ms"] == 900


# ===== 2. Emotion intensity =====
class TestIntensity:
    def test_preset_intensity(self):
        e = _engine()
        e.transition_to("HAPPY")   # 0.8
        assert e.get_current()["intensity"] == 0.8
        e.transition_to("SERIOUS_ALERT")  # 1.0
        assert e.get_current()["intensity"] == 1.0

    def test_explicit_intensity_clamped(self):
        e = _engine()
        e.transition_to("HAPPY", opts={"intensity": 1.5})
        assert e.get_current()["intensity"] == 1.0
        e.transition_to("HAPPY", opts={"intensity": -1})
        assert e.get_current()["intensity"] == 0.0

    def test_micro_modulates_intensity(self):
        e = _engine()
        e.transition_to("HAPPY", opts={"micro": "gentle_smile"})  # 0.8 - 0.15 = 0.65
        assert e.get_current()["intensity"] == pytest.approx(0.65)
        e.transition_to("HAPPY", opts={"micro": "bright_smile"})  # 0.8 + 0.1 = 0.9
        assert e.get_current()["intensity"] == pytest.approx(0.9)

    def test_unknown_state_default_05(self):
        e = _engine()
        e.transition_to("UNKNOWN_STATE")
        assert e.get_current()["intensity"] == 0.5


# ===== 3. Micro-emotions =====
class TestMicroEmotions:
    def test_micro_registry_has_15(self):
        assert len(ee.MICRO_EMOTIONS) == 15

    def test_micro_applies_head_tilt_hint(self):
        cfg = ee.MICRO_EMOTIONS["CURIOUS:deep_curiosity"]
        assert cfg["head_tilt"] == 8
        assert cfg["motion_hint"] == "head_tilt"

    def test_micro_unknown_ignored(self):
        e = _engine()
        r = e.transition_to("HAPPY", opts={"micro": "nonexistent_micro"})
        # Không có cfg → intensity giữ preset 0.8
        assert e.get_current()["intensity"] == 0.8
        assert r["micro"] == "nonexistent_micro"

    def test_micro_stored_in_current(self):
        e = _engine()
        e.transition_to("PROUD", opts={"micro": "subtle_pride"})
        assert e.get_current()["micro"] == "subtle_pride"


# ===== 4. Context-aware (multi-emotion) =====
class TestContextAware:
    def test_multi_emotion_primary_secondary(self):
        # "thành công" (SUCCESS) + "tự hào" (PROUD) → primary SUCCESS, secondary PROUD
        ctx = ee.extract_emotion_context("Anh ơi hệ thống đã thành công rồi, em tự hào lắm")
        assert ctx["primary"] == "CONFIDENT_SUCCESS"
        emotion = ctx["secondary"]
        assert emotion == "PROUD"

    def test_neutral_when_no_match(self):
        ctx = ee.extract_emotion_context("Trời hôm nay đẹp")
        assert ctx["primary"] == "NEUTRAL"
        assert ctx["secondary"] is None

    def test_priority_order_apologetic_before_alert(self):
        # "xin lỗi... sự cố" → APOLOGETIC trước (plan: apology trước alert)
        ctx = ee.extract_emotion_context("xin lỗi anh, hệ thống gặp sự cố")
        assert ctx["primary"] == "APOLOGETIC"
        assert ctx["secondary"] == "SERIOUS_ALERT"

    def test_empty_text_returns_neutral(self):
        ctx = ee.extract_emotion_context("")
        assert ctx["primary"] == "NEUTRAL"

    def test_none_text_returns_neutral(self):
        ctx = ee.extract_emotion_context(None)
        assert ctx["primary"] == "NEUTRAL"


# ===== 5. Negation handling =====
class TestNegation:
    def test_negation_blocks_success(self):
        # "không thành công" → SUCCESS bị negate → primary KHÔNG phải SUCCESS
        ctx = ee.extract_emotion_context("Rất tiếc hệ thống không thành công")
        assert "CONFIDENT_SUCCESS" in ctx["negated"]
        assert ctx["primary"] == "APOLOGETIC"  # "rất tiếc" khớp trước

    def test_negation_blocks_greeting(self):
        ctx = ee.extract_emotion_context("Em không chào được")
        assert "WARM_GREETING" in ctx["negated"]
        assert ctx["primary"] == "NEUTRAL"

    def test_negation_window_12_chars(self):
        # Phủ định cách 15 ký tự → KHÔNG tính negate
        ctx = ee.extract_emotion_context("không biết nói gì đây, thành công rồi nè")
        assert "CONFIDENT_SUCCESS" not in ctx["negated"]
        assert ctx["primary"] == "CONFIDENT_SUCCESS"

    def test_negation_window_edge(self):
        # Đúng 12 ký tự window: "không" ở index 0, "thành công" ở index 12 → negate
        ctx = ee.extract_emotion_context("không      thành công")
        assert "CONFIDENT_SUCCESS" in ctx["negated"]

    def test_negation_not_false_positive(self):
        # "không" đứng SAU keyword → không negate
        ctx = ee.extract_emotion_context("thành công không biết đâu")
        assert "CONFIDENT_SUCCESS" not in ctx["negated"]
        assert ctx["primary"] == "CONFIDENT_SUCCESS"

    def test_negation_list_when_multiple_negated(self):
        ctx = ee.extract_emotion_context("không thành công và không ổn định")
        assert "CONFIDENT_SUCCESS" in ctx["negated"]
        assert "PROUD" in ctx["negated"]
        assert ctx["primary"] == "NEUTRAL"


# ===== Regression guards =====
class TestGuards:
    def test_version_tag(self):
        assert ee.VERSION == "s3_1411"

    def test_transition_presets_complete(self):
        for s in ("SERIOUS_ALERT", "SURPRISED", "HAPPY", "PROUD", "APOLOGETIC",
                  "EMPATHETIC", "SLEEPING", "OFFLINE", "RECONNECTING", "NEUTRAL", "IDLE"):
            assert f"to_{s}" in ee.TRANSITION_PRESETS

    def test_intensity_presets_cover_21_states(self):
        assert len(ee.INTENSITY_PRESETS) == 21

    def test_js_file_syntax_valid(self):
        js = (REPO / "edge_client" / "emotion_engine.js").read_text(encoding="utf-8")
        assert "CherryEmotionEngine" in js
        assert "EmotionTransitionEngine" in js
        assert "extractEmotionContext" in js
