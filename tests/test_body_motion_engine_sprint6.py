"""Sprint 6 — Body Motion Engine (14/11/2026).

Card: TASK-EMBODIMENT-S6 (APPROVED, auth owner_desktop_chat_directive).
Test: shoulder sway + body lean + breathing + arm reach + speech sync.
Gate 6: body motion human-like, không còn sway cứng.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "edge_client"))

import body_motion_engine as bme  # noqa: E402


# ===== Helpers =====
class _FixedNow:
    def __init__(self, start: float = 1000000.0):
        self.t = start
    def __call__(self) -> float:
        return self.t
    def advance(self, ms: float) -> None:
        self.t += ms


def _engine(now_start: float = 1000000.0) -> tuple[bme.BodyMotionEngine, _FixedNow]:
    now = _FixedNow(now_start)
    eng = bme.BodyMotionEngine(now_fn=now)
    return eng, now


# ===== 1. Body presets =====
class TestBodyPresets:
    def test_body_presets_cover_21_states(self):
        assert len(bme.BODY_PRESETS) == 21

    def test_idle_preset(self):
        p = bme.BODY_PRESETS["IDLE"]
        assert p["leanX"] == 0 and p["leanY"] == 0
        assert p["swayX"] == 0.3 and p["swayY"] == 0.2

    def test_surprised_highest_sway(self):
        """SURPRISED có sway cao nhất (phản ứng giật mình)."""
        max_sway = max(p["swayX"] + p["swayY"] for p in bme.BODY_PRESETS.values())
        assert bme.BODY_PRESETS["SURPRISED"]["swayX"] + bme.BODY_PRESETS["SURPRISED"]["swayY"] == max_sway

    def test_offline_zero_sway(self):
        p = bme.BODY_PRESETS["OFFLINE"]
        assert p["swayX"] == 0 and p["swayY"] == 0

    def test_sleeping_lean_forward(self):
        """SLEEPING lean về phía trước (leanY > 0)."""
        assert bme.BODY_PRESETS["SLEEPING"]["leanY"] > 0

    def test_proud_lean_back(self):
        """PROUD lean về phía sau (leanY < 0)."""
        assert bme.BODY_PRESETS["PROUD"]["leanY"] < 0


# ===== 2. Breath presets =====
class TestBreathPresets:
    def test_breath_presets_5_states(self):
        assert len(bme.BREATH_PRESETS) == 6  # 5 states + default

    def test_speaking_fastest_breath(self):
        """SPEAKING có rate thấp nhất (thở nhanh nhất)."""
        min_rate = min(p["rate"] for p in bme.BREATH_PRESETS.values())
        assert bme.BREATH_PRESETS["SPEAKING"]["rate"] == min_rate

    def test_sleeping_slowest_breath(self):
        """SLEEPING có rate cao nhất (thở chậm nhất)."""
        max_rate = max(p["rate"] for p in bme.BREATH_PRESETS.values())
        assert bme.BREATH_PRESETS["SLEEPING"]["rate"] == max_rate


# ===== 3. Arm reach presets =====
class TestArmReachPresets:
    def test_arm_presets_8_states(self):
        assert len(bme.ARM_REACH_PRESETS) == 9  # 8 states + default

    def test_surprised_max_arm_reach(self):
        """SURPRISED có arm reach cao nhất (giơ tay lên)."""
        max_reach = max(p["leftReach"] for p in bme.ARM_REACH_PRESETS.values())
        assert bme.ARM_REACH_PRESETS["SURPRISED"]["leftReach"] == max_reach

    def test_apologetic_arm_back(self):
        """APOLOGETIC có arm âm (tay ra sau lưng)."""
        assert bme.ARM_REACH_PRESETS["APOLOGETIC"]["leftArm"] < 0


# ===== 4. Engine lifecycle =====
class TestEngineLifecycle:
    def test_initial_state_idle(self):
        eng, _ = _engine()
        assert eng._state == "IDLE"

    def test_initial_transform_zero(self):
        eng, _ = _engine()
        t = eng.get_transform()
        assert t["leanX"] == 0 and t["leanY"] == 0
        assert t["swayX"] == 0 and t["swayY"] == 0
        assert t["breathOffset"] == 0

    def test_set_state_updates_target(self):
        eng, _ = _engine()
        eng.set_state("HAPPY")
        assert eng._target["swayX"] == 0.5

    def test_set_state_same_no_log(self):
        eng, _ = _engine()
        eng.set_state("IDLE")
        log_len = len(eng.get_log())
        eng.set_state("IDLE")
        assert len(eng.get_log()) == log_len

    def test_set_state_different_logs(self):
        eng, _ = _engine()
        eng.set_state("HAPPY")
        log = eng.get_log()
        assert any(e["kind"] == "state" and e["state"] == "HAPPY" for e in log)


# ===== 5. Tick — sway oscillation =====
class TestTickSway:
    def test_tick_updates_breath_offset(self):
        eng, now = _engine()
        eng.tick(now.t)
        # Breath oscillation: sin(0) = 0 → offset = 0
        assert eng.get_transform()["breathOffset"] == pytest.approx(0.0, abs=1e-9)

    def test_tick_breath_oscillates(self):
        eng, now = _engine()
        eng.tick(now.t)
        offset1 = eng.get_transform()["breathOffset"]
        now.advance(500)  # 0.5s → phase = π/4
        eng.tick(now.t)
        offset2 = eng.get_transform()["breathOffset"]
        # Offset thay đổi theo thời gian
        assert offset1 != offset2

    def test_tick_sway_oscillates(self):
        eng, now = _engine()
        eng.set_state("HAPPY")  # swayX=0.5
        eng.tick(now.t)
        sway1 = eng.get_transform()["swayX"]
        now.advance(500)
        eng.tick(now.t)
        sway2 = eng.get_transform()["swayX"]
        # Sway oscillation: sway thay đổi theo thời gian
        assert sway1 != sway2

    def test_tick_lerps_lean(self):
        eng, now = _engine()
        eng.set_state("CURIOUS")  # leanX=0.2
        eng.tick(now.t)
        # Lerp toward 0.2
        assert eng.get_transform()["leanX"] > 0
        assert eng.get_transform()["leanX"] < 0.2


# ===== 6. Speaking boost =====
class TestSpeakingBoost:
    def test_speaking_increases_sway(self):
        eng, now = _engine()
        eng.set_state("IDLE")
        # Tick để phase oscillation khác 0
        now.advance(250)
        eng.tick(now.t)
        sway_idle = eng.get_transform()["swayX"]
        eng.set_speaking(True)
        eng.set_speech_energy(0.5)
        eng.tick(now.t)
        sway_speaking = eng.get_transform()["swayX"]
        # Speaking boost = 1.25 → sway_speaking > sway_idle (cùng phase)
        assert sway_speaking > sway_idle

    def test_speaking_increases_arm_reach(self):
        eng, now = _engine()
        eng.set_state("IDLE")
        now.advance(250)
        eng.tick(now.t)
        reach_idle = eng.get_transform()["leftReach"]
        eng.set_speaking(True)
        eng.set_speech_energy(0.8)
        now.advance(100)  # dt > 0 để lerp hoạt động
        eng.tick(now.t)
        reach_speaking = eng.get_transform()["leftReach"]
        # Arm reach tăng theo speech_energy * 0.2
        assert reach_speaking > reach_idle

    def test_speech_energy_clamped(self):
        eng, _ = _engine()
        eng.set_speech_energy(1.5)
        assert eng._speech_energy == 1.0
        eng.set_speech_energy(-0.5)
        assert eng._speech_energy == 0.0

    def test_speaking_arm_capped_60(self):
        eng, now = _engine()
        eng.set_state("SURPRISED")  # leftArm=45
        eng.set_speaking(True)
        eng.set_speech_energy(1.0)
        for _ in range(10):
            now.advance(100)
            eng.tick(now.t)
        # Cap 60 degrees
        assert eng.get_transform()["leftArm"] <= 60.0


# ===== 7. State transitions =====
class TestStateTransitions:
    def test_idle_to_happy_increases_sway(self):
        eng, now = _engine()
        eng.set_state("IDLE")
        eng.tick(now.t)
        sway_idle = eng.get_transform()["swayX"]
        eng.set_state("HAPPY")
        for _ in range(20):
            now.advance(50)
            eng.tick(now.t)
        sway_happy = eng.get_transform()["swayX"]
        assert sway_happy > sway_idle

    def test_idle_to_offline_decreases_sway(self):
        eng, now = _engine()
        eng.set_state("IDLE")
        now.advance(250)
        eng.tick(now.t)
        sway_idle = eng.get_transform()["swayX"]
        eng.set_state("OFFLINE")
        for _ in range(20):
            now.advance(50)
            eng.tick(now.t)
        sway_offline = eng.get_transform()["swayX"]
        # OFFLINE swayX=0 → sway về 0
        assert sway_offline < sway_idle


# ===== 8. Regression guards =====
class TestGuards:
    def test_version_tag(self):
        assert bme.VERSION == "s6_1411"

    def test_js_file_syntax_valid(self):
        js = (REPO / "edge_client" / "body_motion_engine.js").read_text(encoding="utf-8")
        assert "CherryBodyMotionEngine" in js
        assert "BodyMotionEngine" in js
        assert "BODY_PRESETS" in js
        assert "setSpeechEnergy" in js
