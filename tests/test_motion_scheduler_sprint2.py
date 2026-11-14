"""Sprint 2 — Natural Motion Engine (14/11/2026).

Card: TASK-EMBODIMENT-S2 (APPROVED, auth owner_desktop_chat_directive).
Test 6 ca theo CHERRY_EMBODIMENT_SPRINT_PLAN.md §4.4:
  1. Motion priority
  2. Motion interrupt
  3. Motion blending
  4. Gesture selection
  5. Body motion stability (scheduler không leak)
  6. FPS benchmark (smoke — đo thời gian tick 1000 lần)

Mock 100% (theo policy: không đụng DB/LLM thật).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "edge_client"))

import motion_scheduler as ms  # noqa: E402  (Python mirror)


# ===== 1. Motion priority =====
class TestMotionPriority:
    def test_priority_constants(self):
        assert ms.PRIORITY["SAFETY"] == 100
        assert ms.PRIORITY["SPEAKING"] == 80
        assert ms.PRIORITY["LISTENING"] == 70
        assert ms.PRIORITY["THINKING"] == 60
        assert ms.PRIORITY["EMOTION"] == 50
        assert ms.PRIORITY["IDLE"] == 30
        assert ms.PRIORITY["DECORATIVE"] == 10

    def test_higher_priority_wins_blend(self):
        s = ms.MotionScheduler()
        s.add({"target": "head.tilt", "start": 0, "target_value": 5,
               "duration": 1000, "priority": ms.PRIORITY["IDLE"]}, now_ms=0)
        s.add({"target": "head.tilt", "start": 0, "target_value": 10,
               "duration": 1000, "priority": ms.PRIORITY["SPEAKING"]}, now_ms=0)
        blend = s.update(1000)  # full duration → progress=1.0 → value=target
        # SPEAKING (80) > IDLE (30) → value = 10
        assert blend["head.tilt"]["value"] == 10
        assert blend["head.tilt"]["priority"] == ms.PRIORITY["SPEAKING"]


# ===== 2. Motion interrupt =====
class TestMotionInterrupt:
    def test_higher_priority_interrupts_lower(self):
        s = ms.MotionScheduler()
        s.add({"target": "head.tilt", "start": 0, "target_value": 5,
               "duration": 1000, "priority": ms.PRIORITY["IDLE"],
               "interruptible": True}, now_ms=0)
        assert s.size() == 1
        s.add({"target": "head.tilt", "start": 0, "target_value": 10,
               "duration": 1000, "priority": ms.PRIORITY["SPEAKING"]}, now_ms=0)
        # IDLE bị interrupt → chỉ còn SPEAKING
        assert s.size() == 1

    def test_non_interruptible_kept(self):
        s = ms.MotionScheduler()
        s.add({"target": "head.tilt", "start": 0, "target_value": 5,
               "duration": 1000, "priority": ms.PRIORITY["IDLE"],
               "interruptible": False}, now_ms=0)
        s.add({"target": "head.tilt", "start": 0, "target_value": 10,
               "duration": 1000, "priority": ms.PRIORITY["SPEAKING"]}, now_ms=0)
        # Cả 2 cùng tồn tại; SPEAKING thắng blend
        assert s.size() == 2
        blend = s.update(1000)
        assert blend["head.tilt"]["priority"] == ms.PRIORITY["SPEAKING"]


# ===== 3. Motion blending =====
class TestMotionBlending:
    def test_same_priority_additive(self):
        s = ms.MotionScheduler()
        s.add({"target": "head.tilt", "start": 0, "target_value": 5,
               "duration": 1000, "priority": ms.PRIORITY["IDLE"],
               "additive": True}, now_ms=0)
        s.add({"target": "head.tilt", "start": 0, "target_value": 3,
               "duration": 1000, "priority": ms.PRIORITY["IDLE"],
               "additive": True}, now_ms=0)
        blend = s.update(1000)
        # Cùng priority + additive → cộng dồn: 5 + (3 - 0) = 8
        assert blend["head.tilt"]["value"] == 8

    def test_different_target_keys_independent(self):
        s = ms.MotionScheduler()
        s.add({"target": "head.tilt", "start": 0, "target_value": 5,
               "duration": 1000, "priority": ms.PRIORITY["IDLE"]}, now_ms=0)
        s.add({"target": "head.nod", "start": 0, "target_value": 3,
               "duration": 1000, "priority": ms.PRIORITY["IDLE"]}, now_ms=0)
        blend = s.update(1000)
        assert "head.tilt" in blend
        assert "head.nod" in blend
        assert blend["head.tilt"]["value"] == 5
        assert blend["head.nod"]["value"] == 3


# ===== 4. Gesture selection =====
class TestGestureSelection:
    def test_gesture_library_has_10_gestures(self):
        assert len(ms.GESTURE_LIBRARY) == 10

    def test_select_gesture_returns_matching_context(self):
        pick = ms.select_gesture("user_greeting", None)
        assert pick is not None
        assert pick["name"] == "greeting"
        assert pick["gesture"]["context"] == "user_greeting"

    def test_select_gesture_avoids_repeat(self):
        # Chỉ có 1 gesture cho "processing" → fallback trả lại gesture đó
        first = ms.select_gesture("processing", None)
        assert first is not None
        second = ms.select_gesture("processing", first["name"])
        # Chỉ 1 candidate → fallback trả lại (không tránh được)
        assert second is not None
        assert second["name"] == first["name"]

    def test_select_gesture_unknown_context_returns_none(self):
        assert ms.select_gesture("nonexistent_context", None) is None


# ===== 5. Body motion stability (scheduler không leak) =====
class TestSchedulerStability:
    def test_clear_resets_state(self):
        s = ms.MotionScheduler()
        for i in range(20):
            s.add({"target": f"x.{i}", "start": 0, "target_value": 1,
                   "duration": 100, "priority": ms.PRIORITY["IDLE"]}, now_ms=0)
        assert s.size() == 20
        s.clear()
        assert s.size() == 0

    def test_completed_motions_removed(self):
        s = ms.MotionScheduler()
        s.add({"target": "head.tilt", "start": 0, "target_value": 5,
               "duration": 100, "priority": ms.PRIORITY["IDLE"]}, now_ms=0)
        s.update(150)  # progress = 1.5 → complete
        assert s.size() == 0

    def test_onComplete_called(self):
        s = ms.MotionScheduler()
        called = []
        s.add({"target": "head.tilt", "start": 0, "target_value": 5,
               "duration": 100, "priority": ms.PRIORITY["IDLE"],
               "onComplete": lambda: called.append(True)}, now_ms=0)
        s.update(150)
        assert called == [True]


# ===== 6. FPS benchmark (smoke) =====
class TestFpsBenchmark:
    def test_1000_ticks_under_500ms(self):
        """1000 lần tick scheduler phải < 500ms (≈ 2000 FPS theoretical)."""
        s = ms.MotionScheduler()
        # 5 motion song song
        for i in range(5):
            s.add({"target": f"x.{i}", "start": 0, "target_value": 1,
                   "duration": 1000, "priority": ms.PRIORITY["IDLE"]}, now_ms=0)
        t0 = time.perf_counter()
        for i in range(1000):
            s.update(i * 16)
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.5, f"1000 ticks took {elapsed:.3f}s (too slow)"


# ===== Bonus: easing functions =====
class TestEasing:
    def test_easing_endpoints(self):
        for name in ("linear", "ease-in", "ease-out", "ease-in-out"):
            assert ms._apply_easing(0, name) == pytest.approx(0, abs=1e-9)
            assert ms._apply_easing(1, name) == pytest.approx(1, abs=1e-9)

    def test_ease_in_slower_at_start(self):
        assert ms._apply_easing(0.5, "ease-in") < 0.5

    def test_ease_out_faster_at_start(self):
        assert ms._apply_easing(0.5, "ease-out") > 0.5


# ===== Bonus: interpolate =====
class TestInterpolate:
    def test_interpolate_number(self):
        assert ms._interpolate(0, 10, 0.5) == 5
        assert ms._interpolate(0, 10, 0) == 0
        assert ms._interpolate(0, 10, 1) == 10

    def test_interpolate_array(self):
        result = ms._interpolate([0, 0], [10, 20], 0.5)
        assert result == [5, 10]
