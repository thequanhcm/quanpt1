"""Sprint 1 — Unified Emotion Protocol (14/11/2026).

Card: TASK-EMBODIMENT-S1 (APPROVED, auth owner_desktop_chat_directive).
Test 8 ca theo CHERRY_EMBODIMENT_SPRINT_PLAN.md §3.4:
  1. PC → Pi5 state sync (canonical 22)
  2. Pi5 → PC state sync (mirror)
  3. Disconnect/reconnect (validator reset)
  4. Duplicate event (event_id trùng)
  5. Out-of-order event (sequence lùi)
  6. Invalid payload (thiếu event_id/timestamp)
  7. Stale state (timestamp skew > 30s)
  8. Offline recovery (sequence gap chấp nhận)

Mock 100% (theo policy: không đụng DB/LLM thật).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "edge_client"))

import edge_envelope as ee  # noqa: E402


# ===== 1. PC → Pi5 state sync (canonical 22) =====
class TestStateCanonical:
    def test_all_22_states_known(self):
        assert len(ee.STATES) == 22
        for s in [
            "IDLE", "LISTENING", "THINKING", "RESEARCHING", "LEARNING",
            "SPEAKING", "HAPPY", "EMPATHETIC", "CONFUSED", "SUCCESS",
            "WARNING", "WAITING_FOR_OWNER", "BLOCKED", "ERROR", "SAFE_MODE",
            "OFFLINE", "RECONNECTING", "SLEEPING", "SURPRISED", "CURIOUS",
            "APOLOGETIC", "PROUD",
        ]:
            assert s in ee.STATES, f"missing canonical state: {s}"

    def test_normalize_state_aliases(self):
        assert ee.normalize_state("ONLINE") == "IDLE"
        assert ee.normalize_state("SPEAK") == "SPEAKING"
        assert ee.normalize_state("LISTEN") == "LISTENING"
        assert ee.normalize_state("WAIT") == "WAITING_FOR_OWNER"
        assert ee.normalize_state("FAIL") == "ERROR"
        assert ee.normalize_state("CRITICAL") == "BLOCKED"
        assert ee.normalize_state("BOOTING") == "RECONNECTING"

    def test_normalize_state_unknown_falls_back_idle(self):
        assert ee.normalize_state("") == "IDLE"
        assert ee.normalize_state(None) == "IDLE"
        assert ee.normalize_state("garbage") == "IDLE"
        assert ee.normalize_state("  ") == "IDLE"


# ===== 2. Pi5 → PC state sync (mirror) =====
class TestEnvelopeBuild:
    def test_build_envelope_has_17_fields(self):
        ev = ee.build_envelope("set_expression", state="IDLE", transcript="hi")
        # 14 field cố định + action + state + transcript = 17
        for f in [
            "event_id", "sequence", "platform", "timestamp", "expiry",
            "operational_state", "emotion", "emotion_intensity", "gesture",
            "motion_profile", "speaking_status", "audio_status",
            "animation_duration", "protocol_version", "action", "state",
            "transcript",
        ]:
            assert f in ev, f"missing field: {f}"

    def test_event_id_unique(self):
        a = ee.new_event_id()
        b = ee.new_event_id()
        assert a != b
        assert a.startswith("evt_")
        assert len(a) == 16  # evt_ + 12 hex


# ===== 3. Disconnect/reconnect (validator reset) =====
class TestValidatorReset:
    def test_new_validator_starts_empty(self):
        v = ee.EnvelopeValidator()
        assert v.seen == {}
        assert v.last_seq == {}


# ===== 4. Duplicate event =====
class TestDuplicate:
    def test_duplicate_event_id_rejected(self):
        v = ee.EnvelopeValidator()
        ev = ee.build_envelope("set_expression", state="IDLE", sequence=1)
        assert v.validate(ev)["ok"] is True
        # Lần 2 cùng event_id → DUPLICATE
        assert v.validate(ev)["ok"] is False
        assert v.validate(ev)["reason"] == "DUPLICATE"


# ===== 5. Out-of-order event =====
class TestOutOfOrder:
    def test_sequence_monotonic_per_platform(self):
        v = ee.EnvelopeValidator()
        ev1 = ee.build_envelope("set_expression", state="IDLE", sequence=5)
        ev2 = ee.build_envelope("set_expression", state="IDLE", sequence=3)
        assert v.validate(ev1)["ok"] is True
        # sequence 3 < 5 → OUT_OF_ORDER
        assert v.validate(ev2)["ok"] is False
        assert v.validate(ev2)["reason"] == "OUT_OF_ORDER"

    def test_sequence_increasing_accepted(self):
        v = ee.EnvelopeValidator()
        for seq in (1, 2, 3, 4, 5):
            ev = ee.build_envelope("set_expression", state="IDLE", sequence=seq)
            assert v.validate(ev)["ok"] is True

    def test_different_platforms_independent(self):
        v = ee.EnvelopeValidator()
        ev_pc = ee.build_envelope("set_expression", state="IDLE", sequence=10)
        ev_pi = ee.build_envelope("set_expression", state="IDLE", sequence=1)
        # Đổi platform thành PI5 cho ev_pi
        ev_pi["platform"] = "PI5"
        assert v.validate(ev_pc)["ok"] is True
        assert v.validate(ev_pi)["ok"] is True  # platform khác → OK


# ===== 6. Invalid payload =====
class TestInvalidPayload:
    def test_missing_event_id(self):
        v = ee.EnvelopeValidator()
        ev = ee.build_envelope("set_expression", state="IDLE")
        ev.pop("event_id")
        assert v.validate(ev)["ok"] is False
        assert "event_id" in v.validate(ev)["reason"]

    def test_missing_timestamp(self):
        v = ee.EnvelopeValidator()
        ev = ee.build_envelope("set_expression", state="IDLE")
        ev.pop("timestamp")
        assert v.validate(ev)["ok"] is False
        assert "timestamp" in v.validate(ev)["reason"]

    def test_none_envelope(self):
        v = ee.EnvelopeValidator()
        assert v.validate(None)["ok"] is False
        assert v.validate({})["ok"] is False


# ===== 7. Stale state =====
class TestStale:
    def test_stale_timestamp_rejected(self):
        # Clock giả: now = 1_000_000_000 ms; event timestamp = now - 60s
        fixed_now = 1_000_000_000.0
        v = ee.EnvelopeValidator(clock=lambda: fixed_now)
        ev = ee.build_envelope(
            "set_expression", state="IDLE", sequence=1,
            timestamp_ms=fixed_now - 60_000,
        )
        assert v.validate(ev)["ok"] is False
        assert v.validate(ev)["reason"] == "STALE"

    def test_fresh_timestamp_accepted(self):
        fixed_now = 1_000_000_000.0
        v = ee.EnvelopeValidator(clock=lambda: fixed_now)
        ev = ee.build_envelope(
            "set_expression", state="IDLE", sequence=1,
            timestamp_ms=fixed_now - 5_000,  # 5s trước, trong tolerance 30s
        )
        assert v.validate(ev)["ok"] is True


# ===== 8. Offline recovery (sequence gap chấp nhận) =====
class TestOfflineRecovery:
    def test_sequence_gap_accepted(self):
        v = ee.EnvelopeValidator()
        ev1 = ee.build_envelope("set_expression", state="IDLE", sequence=1)
        ev2 = ee.build_envelope("set_expression", state="IDLE", sequence=100)
        assert v.validate(ev1)["ok"] is True
        # Gap lớn (mất gói 2..99) → vẫn OK vì sequence tăng
        assert v.validate(ev2)["ok"] is True

    def test_expired_envelope_rejected(self):
        fixed_now = 1_000_000_000.0
        v = ee.EnvelopeValidator(clock=lambda: fixed_now)
        ev = ee.build_envelope(
            "set_expression", state="IDLE", sequence=1,
            timestamp_ms=fixed_now - 1_000, expiry_ms=fixed_now - 500,
        )
        assert v.validate(ev)["ok"] is False
        assert v.validate(ev)["reason"] == "EXPIRED"


# ===== Bonus: validate_envelope_once (stateless) =====
class TestStateless:
    def test_once_validates_basic_shape(self):
        ev = ee.build_envelope("set_expression", state="IDLE")
        assert ee.validate_envelope_once(ev)["ok"] is True

    def test_once_rejects_missing_event_id(self):
        ev = ee.build_envelope("set_expression", state="IDLE")
        ev.pop("event_id")
        assert ee.validate_envelope_once(ev)["ok"] is False
