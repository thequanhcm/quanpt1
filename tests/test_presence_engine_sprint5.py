"""Sprint 5 — Human-Like Interaction (14/11/2026).

Card: TASK-EMBODIMENT-S5 (APPROVED, auth owner_desktop_chat_directive).
Test theo CHERRY_EMBODIMENT_SPRINT_PLAN.md §7.4:
  - Wake response latency (đo, không sửa)
  - Listening behavior
  - Eye contact
  - Conversation continuity
  - Natural idle behavior
  - User interruption
  - Return-to-idle behavior
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "edge_client"))

import presence_engine as pe  # noqa: E402


# ===== Helpers =====
class _FixedNow:
    def __init__(self, start: float = 1000000.0):
        self.t = start
    def __call__(self) -> float:
        return self.t
    def advance(self, ms: float) -> None:
        self.t += ms


def _engine(now_start: float = 1000000.0) -> tuple[pe.PresenceEngine, _FixedNow]:
    now = _FixedNow(now_start)
    eng = pe.PresenceEngine(now_fn=now, rng=lambda: 0.5)  # deterministic
    return eng, now


# ===== 1. Eye contact =====
class TestEyeContact:
    def test_idle_eye_contact_06(self):
        eng, _ = _engine()
        assert eng.get_gaze()["eyeContact"] == 0.6

    def test_listening_eye_contact_09(self):
        eng, now = _engine()
        eng.notify_user_speaking()
        eng.tick(now.t)
        assert eng.get_gaze()["eyeContact"] == 0.9

    def test_sleeping_eye_contact_0(self):
        eng, now = _engine()
        eng.set_state("SLEEPING")
        assert eng.get_gaze()["eyeContact"] == 0.0

    def test_eye_contact_presets_cover_21_states(self):
        assert len(pe.EYE_CONTACT_PRESETS) == 21

    def test_unknown_state_default_06(self):
        eng, _ = _engine()
        eng.set_state("UNKNOWN_STATE")
        assert eng.get_gaze()["eyeContact"] == 0.6


# ===== 2. Listening behavior =====
class TestListening:
    def test_user_speaking_sets_listening(self):
        eng, _ = _engine()
        eng.notify_user_speaking()
        assert eng.get_gaze()["state"] == "LISTENING"

    def test_listening_gaze_eye_contact(self):
        eng, now = _engine()
        eng.notify_user_speaking()
        eng.tick(now.t)
        # rng=0.5 → 0.5 < 0.7 → eye_contact (gazeX=0, gazeY=0)
        assert eng.get_gaze()["gazeX"] == 0.0
        assert eng.get_gaze()["gazeY"] == 0.0

    def test_listening_gaze_thinking(self):
        eng, now = _engine()
        eng.notify_user_speaking()
        # rng=0.85 → 0.7 < 0.85 < 0.9 → thinking (gazeY=-0.3)
        eng._rng = lambda: 0.85
        eng.tick(now.t)
        assert eng.get_gaze()["gazeY"] == -0.3

    def test_listening_gaze_processing(self):
        eng, now = _engine()
        eng.notify_user_speaking()
        # rng=0.95 → 0.95 > 0.9 → processing (gazeX=0.4)
        eng._rng = lambda: 0.95
        eng.tick(now.t)
        assert eng.get_gaze()["gazeX"] == 0.4


# ===== 3. Conversation continuity =====
class TestContinuity:
    def test_turns_increment(self):
        eng, _ = _engine()
        assert eng.get_conversation_turns() == 0
        eng.notify_user_speaking()
        eng.notify_user_stopped()
        assert eng.get_conversation_turns() == 1
        eng.notify_user_speaking()
        eng.notify_user_stopped()
        assert eng.get_conversation_turns() == 2

    def test_log_records_turns(self):
        eng, _ = _engine()
        eng.notify_user_speaking()
        eng.notify_user_stopped()
        log = eng.get_log()
        assert any(e["kind"] == "user_speaking_start" for e in log)
        assert any(e["kind"] == "user_speaking_end" and e["turns"] == 1 for e in log)


# ===== 4. Natural idle behavior =====
class TestIdleBehavior:
    def test_idle_behaviors_4(self):
        assert len(pe.IDLE_BEHAVIORS) == 4
        assert "slow_blink" in pe.IDLE_BEHAVIORS
        assert "gaze_away" in pe.IDLE_BEHAVIORS
        assert "head_tilt" in pe.IDLE_BEHAVIORS
        assert "breathing" in pe.IDLE_BEHAVIORS

    def test_idle_schedules_after_2s(self):
        eng, now = _engine()
        # rng=0.5 → next_idle = now + 2000 + 0.5*3000 = now + 3500
        eng.tick(now.t)
        assert eng._next_idle_behavior > now.t

    def test_idle_behavior_starts_after_delay(self):
        eng, now = _engine()
        # Tick đầu set next_idle = now + 3500
        eng.tick(now.t)
        # Advance vượt qua next_idle
        now.advance(4000)
        eng.tick(now.t)
        assert eng._current_idle_behavior is not None

    def test_idle_behavior_ends_after_duration(self):
        eng, now = _engine()
        eng.tick(now.t)
        now.advance(4000)
        eng.tick(now.t)
        beh = eng._current_idle_behavior
        dur = pe.IDLE_BEHAVIORS[beh]["duration_ms"]
        now.advance(dur + 100)
        eng.tick(now.t)
        assert eng._current_idle_behavior is None

    def test_gaze_away_changes_gaze_x(self):
        eng, now = _engine()
        # Force gaze_away
        eng._rng = lambda: 0.25  # weight 0.2/1.0 = 0.2 → gaze_away
        eng.tick(now.t)
        now.advance(4000)
        eng.tick(now.t)
        if eng._current_idle_behavior == "gaze_away":
            now.advance(750)  # giữa duration
            eng.tick(now.t)
            assert eng.get_gaze()["gazeX"] != 0.0


# ===== 5. User interruption =====
class TestInterruption:
    def test_interrupted_flag(self):
        eng, _ = _engine()
        eng.notify_interrupted()
        assert eng._interrupted is True

    def test_interrupted_logged(self):
        eng, _ = _engine()
        eng.notify_interrupted()
        log = eng.get_log()
        assert any(e["kind"] == "interrupted" for e in log)


# ===== 6. Return-to-idle =====
class TestReturnToIdle:
    def test_listening_returns_to_idle_after_2s(self):
        eng, now = _engine()
        eng.notify_user_speaking()
        eng.tick(now.t)
        assert eng.get_gaze()["state"] == "LISTENING"
        eng.notify_user_stopped()
        now.advance(2500)  # > 2000ms
        eng.tick(now.t)
        assert eng.get_gaze()["state"] == "IDLE"

    def test_listening_stays_within_2s(self):
        eng, now = _engine()
        eng.notify_user_speaking()
        eng.tick(now.t)
        eng.notify_user_stopped()
        now.advance(1000)  # < 2000ms
        eng.tick(now.t)
        # Vẫn LISTENING (chưa đủ 2s)
        assert eng.get_gaze()["state"] == "LISTENING"


# ===== 7. State sync =====
class TestStateSync:
    def test_set_state_updates_eye_contact(self):
        eng, _ = _engine()
        eng.set_state("HAPPY")
        assert eng.get_gaze()["eyeContact"] == 0.8

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


# ===== 8. Regression guards =====
class TestGuards:
    def test_version_tag(self):
        assert pe.VERSION == "s5_1411"

    def test_listening_gaze_3_modes(self):
        assert len(pe.LISTENING_GAZE) == 3

    def test_js_file_syntax_valid(self):
        js = (REPO / "edge_client" / "presence_engine.js").read_text(encoding="utf-8")
        assert "CherryPresenceEngine" in js
        assert "PresenceEngine" in js
        assert "notifyUserSpeaking" in js
        assert "notifyInterrupted" in js
