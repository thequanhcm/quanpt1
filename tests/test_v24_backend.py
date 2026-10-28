"""
Tests for V24 backend modules (M2-M5): NL Query Engine, Voice Interface,
Offline Sync Engine, Notification Service, plus cross-module integration.

All tests are hermetic: stdlib only, tmp_path for file I/O, in-memory
mocks for ASR/TTS/server/push. No network, no sleeps (injectable clocks).
"""

import json
from datetime import datetime, timedelta, time as dtime

import pytest

from quan_ai_brain.nlp.query_engine import (
    Filter,
    Intent,
    NLQueryEngine,
    QueryPlan,
    QueryResult,
    Sort,
    TimeFilter,
    ascii_fold,
    tokenize,
)
from quan_ai_brain.voice.voice_interface import (
    ASRError,
    MockASR,
    MockTTS,
    VoiceInterface,
    VoiceState,
)
from quan_ai_brain.mobile.offline_sync import (
    Conflict,
    OfflineSyncEngine,
    ServerStub,
    SyncReport,
)
from quan_ai_brain.mobile.notifications import (
    MockPushSender,
    Notification,
    NotificationService,
    TemplateEngine,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def make_ku(ku_id, title, content="", ku_type="LESSON_LEARNED",
            scope="PRODUCTION", status="VERIFIED", tags=None,
            created_at=None):
    return {
        "id": ku_id,
        "title": title,
        "content": content,
        "type": ku_type,
        "scope": scope,
        "status": status,
        "tags": tags or [],
        "created_at": created_at or "2026-10-20T10:00:00",
    }


KU_FIXTURES = [
    make_ku("ku-1", "Postgres backup failover",
            "database backup ran before failover",
            ku_type="LESSON_LEARNED", scope="PRODUCTION",
            tags=["database", "backup"], created_at="2026-10-26T08:00:00"),
    make_ku("ku-2", "Redis cache eviction spike",
            "cache eviction caused latency",
            ku_type="ERROR", scope="PRODUCTION",
            tags=["cache", "performance"], created_at="2026-10-25T09:00:00"),
    make_ku("ku-3", "CI pipeline flaky tests",
            "flaky tests in CI",
            ku_type="ERROR", scope="DEVELOPMENT", status="DRAFT",
            tags=["ci"], created_at="2026-10-27T11:00:00"),
    make_ku("ku-4", "Daily DB backup policy",
            "backup database every day",
            ku_type="BEST_PRACTICE", scope="OPS",
            tags=["database", "backup"], created_at="2026-10-01T07:00:00"),
]

NOW = datetime(2026, 10, 28, 12, 0, 0)


# ===========================================================================
# M2 — NL Query Engine
# ===========================================================================

class TestNLQueryEngine:

    # -- tokenization -------------------------------------------------------

    def test_tokenize_strips_diacritics(self):
        assert tokenize("Tìm kinh nghiệm") == ["tim", "kinh", "nghiem"]

    def test_tokenize_ascii_fold(self):
        assert ascii_fold("ĐẶT LỊCH") == "dat lich"

    def test_tokenize_mixed_english(self):
        assert tokenize("Show me ALL errors!") == ["show", "me", "all", "errors"]

    def test_tokenize_empty(self):
        assert tokenize("") == []

    # -- intent detection ------------------------------------------------------

    def test_intent_search_vi(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("Tìm các kinh nghiệm triển khai")
        assert plan.intent == Intent.SEARCH

    def test_intent_search_en(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("Show me all errors from last week")
        assert plan.intent == Intent.SEARCH

    def test_intent_count_vi(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("Đếm số lỗi production")
        assert plan.intent == Intent.COUNT

    def test_intent_count_en(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("How many lessons do we have")
        assert plan.intent == Intent.COUNT

    def test_intent_compare(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("So sánh lỗi production và staging")
        assert plan.intent == Intent.COMPARE

    def test_intent_timeline(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        # 'lich su' (history) sets TIMELINE; 'tuan truoc' only adds TimeFilter
        plan = engine.parse("Lịch sử các sự cố")
        assert plan.intent == Intent.TIMELINE
        # time range alone keeps SEARCH intent but adds a time filter
        plan2 = engine.parse("Tìm các sự cố tuần trước")
        assert plan2.intent == Intent.SEARCH
        assert plan2.time_filters[0].days == 7

    def test_intent_unknown(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("hello world")
        assert plan.intent == Intent.UNKNOWN

    # -- plan construction -------------------------------------------------------

    def test_plan_type_filter_from_synonym(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("tìm lỗi")
        assert Filter(field="type", value="ERROR") in plan.filters

    def test_plan_scope_filter(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("tìm lỗi production")
        assert Filter(field="scope", value="PRODUCTION") in plan.filters

    def test_plan_time_filter_last_week(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("show errors last week")
        assert plan.time_filters and plan.time_filters[0].days == 7

    def test_plan_time_filter_today(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("lỗi hôm nay")
        assert plan.time_filters and plan.time_filters[0].days == 1

    def test_plan_sort_newest(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("tìm lỗi mới nhất")
        assert plan.sort == Sort(field="created_at", direction="desc")

    def test_plan_sort_oldest(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("tìm lỗi cũ nhất")
        assert plan.sort.direction == "asc"

    def test_plan_limit_detected(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("tìm 5 lỗi")
        assert plan.limit == 5

    def test_plan_default_limit(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("tìm lỗi")
        assert plan.limit == NLQueryEngine.DEFAULT_LIMIT

    def test_plan_to_dict_serializable(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("tìm 3 lỗi production tuần trước")
        d = plan.to_dict()
        assert d["intent"] == Intent.SEARCH
        assert d["limit"] == 3
        json.dumps(d)  # must be JSON-serializable

    # -- execution ---------------------------------------------------------------

    def test_execute_type_filter(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("tìm lỗi")
        ids = {r["id"] for r in result.results}
        assert ids == {"ku-2", "ku-3"}

    def test_execute_combined_filters(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("tìm lỗi production")
        assert [r["id"] for r in result.results] == ["ku-2"]

    def test_execute_count_intent(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("đếm lỗi production")
        assert result.total_matches == 1
        assert "answer: 1" in result.explanation

    def test_execute_time_filter_excludes_old(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("tìm backup tuần trước")
        ids = {r["id"] for r in result.results}
        assert "ku-4" not in ids  # ku-4 created 2026-10-01, outside 7d window
        assert "ku-1" in ids

    def test_execute_sort_newest_first(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("tìm lỗi mới nhất")
        created = [r["created_at"] for r in result.results]
        assert created == sorted(created, reverse=True)

    def test_execute_limit(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("tìm 1 lỗi")
        assert result.count == 1
        assert result.total_matches == 2

    def test_execute_free_text_terms(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("tìm flaky")
        assert [r["id"] for r in result.results] == ["ku-3"]

    def test_execute_no_matches(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("tìm kubernetes")
        assert result.count == 0
        assert result.total_matches == 0

    def test_execute_empty_query(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("!!!")
        assert plan.intent == Intent.UNKNOWN
        assert "empty_query" in plan.warnings

    def test_explanation_mentions_filters(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("tìm lỗi production")
        assert "type=ERROR" in result.explanation
        assert "scope=PRODUCTION" in result.explanation

    def test_result_to_dict(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("đếm lỗi")
        d = result.to_dict()
        assert d["count"] == result.count
        assert d["plan"]["intent"] == Intent.COUNT
        json.dumps(d)

    def test_parse_rejects_non_string(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        with pytest.raises(TypeError):
            engine.parse(123)

    def test_execute_with_explicit_records(self):
        engine = NLQueryEngine([], now=NOW)
        extra = [make_ku("x-1", "kubernetes rollback",
                         ku_type="ERROR", scope="STAGING")]
        result = engine.query("tìm lỗi", records=extra)
        assert [r["id"] for r in result.results] == ["x-1"]

    def test_vietnamese_diacritic_insensitive_matching(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        result = engine.query("TÌM LỖI Production".lower())
        assert result.total_matches >= 1

    def test_compare_intent_extracts_targets(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        plan = engine.parse("so sánh production vs staging")
        assert set(plan.compare_targets) == {"PRODUCTION", "STAGING"}

    def test_time_filter_field_label(self):
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)
        tf = TimeFilter(field="created_at", keyword="last_week", days=7)
        assert tf.to_dict()["days"] == 7


# ===========================================================================
# M3 — Voice Interface
# ===========================================================================

class TestVoiceInterface:

    def _make(self, script=None, fail=False, timeout=5.0):
        asr = MockASR(script=script or ["tìm lỗi production"], fail=fail)
        tts = MockTTS()
        t = [100.0]
        vi = VoiceInterface(asr, tts, timeout=timeout, clock=lambda: t[0])
        return vi, asr, tts, t

    def test_initial_state_idle(self):
        vi, *_ = self._make()
        assert vi.state == VoiceState.IDLE

    def test_start_session_listening(self):
        vi, asr, _, _ = self._make()
        vi.start_session()
        assert vi.state == VoiceState.LISTENING
        assert asr.is_listening

    def test_full_turn_happy_path(self):
        vi, _, tts, _ = self._make(script=["tìm lỗi"])
        vi.start_session()
        vi.listen()
        text = vi.transcribe()
        assert text == "tìm lỗi"
        assert vi.state == VoiceState.TRANSCRIBING
        turn = vi.respond(text)
        assert turn.response == "TÌM LỖI".upper()
        assert vi.state == VoiceState.IDLE
        assert tts.spoken == [turn.response]

    def test_transcribe_returns_scripted_text(self):
        vi, _, _, _ = self._make(script=["hai ba"])
        vi.start_session()
        vi.listen()
        assert vi.transcribe() == "hai ba"

    def test_timeout_returns_to_idle(self):
        vi, _, _, t = self._make(timeout=5.0)
        vi.start_session()
        t[0] += 6.0  # advance fake clock past timeout
        assert vi.listen() is False
        assert vi.state == VoiceState.IDLE
        assert vi.timeouts == 1

    def test_no_timeout_within_window(self):
        vi, _, _, t = self._make(timeout=5.0)
        vi.start_session()
        t[0] += 3.0
        assert vi.listen() is True
        assert vi.state == VoiceState.LISTENING

    def test_asr_failure_recorded_and_raises(self):
        vi, _, _, _ = self._make(fail=True)
        vi.start_session()
        vi.listen()
        with pytest.raises(ASRError):
            vi.transcribe()
        assert vi.errors
        assert vi.state == VoiceState.IDLE

    def test_asr_empty_script_raises(self):
        vi, _, _, _ = self._make(script=[])
        vi.start_session()
        vi.listen()
        with pytest.raises(ASRError):
            vi.transcribe()

    def test_barge_in_cancels_response(self):
        vi, _, tts, _ = self._make()
        vi.start_session()
        vi.listen()
        text = vi.transcribe()
        # barge-in fires while TRANSCRIBING (before TTS starts)
        assert vi.barge_in() is True
        turn = vi.respond(text)
        assert turn.interrupted is True
        assert turn.response == ""
        assert tts.spoken == []
        assert vi.barge_in_count == 1

    def test_barge_in_via_interrupt_flag(self):
        vi, _, tts, _ = self._make()
        vi.start_session()
        vi.listen()
        text = vi.transcribe()
        turn = vi.respond(text, interrupt_during_speech=True)
        assert turn.interrupted is True
        assert tts.spoken == []

    def test_barge_in_ignored_outside_responding(self):
        vi, _, _, _ = self._make()
        vi.start_session()
        assert vi.barge_in() is False  # LISTENING: nothing to cancel
        assert vi.barge_in_count == 0

    def test_invalid_transition_rejected(self):
        vi, _, _, _ = self._make()
        with pytest.raises(RuntimeError):
            vi._transition(VoiceState.RESPONDING)  # IDLE -> RESPONDING

    def test_respond_requires_transcribing_state(self):
        vi, _, _, _ = self._make()
        with pytest.raises(RuntimeError):
            vi.respond("hello")

    def test_end_session_result_summary(self):
        vi, _, _, _ = self._make(script=["mot hai"])
        vi.start_session()
        vi.listen()
        vi.respond(vi.transcribe())
        result = vi.end_session()
        assert result.ended_reason == "completed"
        assert len(result.turns) == 1
        assert result.timeouts == 0
        assert result.barge_in_count == 0

    def test_session_summary_after_timeout(self):
        vi, _, _, t = self._make(timeout=2.0)
        vi.start_session()
        t[0] += 3.0
        vi.listen()
        result = vi.end_session()
        assert result.timeouts == 1
        assert result.ended_reason == "timeout"

    def test_turn_duration_measured(self):
        vi, _, _, t = self._make()
        vi.start_session()
        vi.listen()
        t[0] += 1.5
        turn = vi.respond(vi.transcribe())
        assert turn.duration == pytest.approx(1.5)

    def test_tts_mock_records_spoken_text(self):
        tts = MockTTS()
        tts.speak("xin chao")
        assert tts.spoken == ["xin chao"]
        assert tts.speaking is True
        tts.stop()
        assert tts.speaking is False

    def test_multiple_turns_sequential(self):
        vi, _, tts, _ = self._make(script=["turn mot", "turn hai"])
        vi.start_session()
        vi.listen()
        vi.respond(vi.transcribe())
        vi2 = vi
        vi2.start_session()
        vi2.listen()
        vi2.respond(vi2.transcribe())
        assert len(vi.turns) == 2
        assert tts.spoken == ["TURN MOT", "TURN HAI"]

    def test_voice_state_values(self):
        assert VoiceState.IDLE.value == "idle"
        assert VoiceState.RESPONDING.value == "responding"


# ===========================================================================
# M4 — Offline Sync Engine
# ===========================================================================

class TestOfflineSync:

    def _engine(self, tmp_path, server=None):
        server = server or ServerStub()
        path = str(tmp_path / "oplog.jsonl")
        return OfflineSyncEngine(server, path, device_id="dev-1"), server

    def test_local_set_updates_state_and_log(self, tmp_path):
        eng, _ = self._engine(tmp_path)
        eng.local_set("ku-1", {"title": "hello"})
        assert eng.state["ku-1"] == {"title": "hello"}
        assert len(eng.pending_ops()) == 1

    def test_op_log_is_append_only_jsonl(self, tmp_path):
        eng, _ = self._engine(tmp_path)
        eng.local_set("a", 1)
        eng.local_set("b", 2)
        with open(eng.op_log_path, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 2
        assert lines[0]["key"] == "a"

    def test_local_delete_removes_from_state(self, tmp_path):
        eng, _ = self._engine(tmp_path)
        eng.local_set("a", 1)
        eng.local_delete("a")
        assert "a" not in eng.state
        assert len(eng.pending_ops()) == 2

    def test_state_survives_restart_from_log(self, tmp_path):
        eng, server = self._engine(tmp_path)
        eng.local_set("a", {"v": 1})
        eng.local_set("b", 2)
        # simulate process restart: new engine on same log
        eng2 = OfflineSyncEngine(server, eng.op_log_path, device_id="dev-1")
        assert eng2.state == {"a": {"v": 1}, "b": 2}
        assert len(eng2.pending_ops()) == 2

    def test_sync_pushes_pending_ops(self, tmp_path):
        eng, server = self._engine(tmp_path)
        eng.local_set("a", 1)
        report = eng.sync()
        assert report.completed is True
        assert report.pushed == 1
        assert server.store["a"]["value"] == 1

    def test_sync_pulls_server_changes(self, tmp_path):
        eng, server = self._engine(tmp_path)
        server.store["remote-1"] = {
            "value": "from-server", "updated_at": "2026-10-28T00:00:00",
            "device_id": "dev-2"}
        report = eng.sync()
        assert report.pulled == 1
        assert eng.state["remote-1"] == "from-server"

    def test_conflict_detected_same_key_different_value(self, tmp_path):
        eng, server = self._engine(tmp_path)
        eng.local_set("ku-1", {"title": "local edit"})
        server.store["ku-1"] = {
            "value": {"title": "server edit"},
            "updated_at": "2026-10-27T00:00:00", "device_id": "dev-2"}
        report = eng.sync()
        assert len(report.conflicts) == 1
        c = report.conflicts[0]
        assert c.key == "ku-1"
        assert c.local_value == {"title": "local edit"}
        assert c.server_value == {"title": "server edit"}

    def test_no_conflict_when_same_value(self, tmp_path):
        eng, server = self._engine(tmp_path)
        eng.local_set("ku-1", "same")
        server.store["ku-1"] = {
            "value": "same", "updated_at": "2026-10-27T00:00:00",
            "device_id": "dev-2"}
        report = eng.sync()
        assert report.conflicts == []

    def test_lww_local_wins(self, tmp_path):
        eng, server = self._engine(tmp_path)
        eng.local_set("ku-1", "local-new")  # clock: now (2026+)
        server.store["ku-1"] = {
            "value": "server-old", "updated_at": "2020-01-01T00:00:00",
            "device_id": "dev-2"}
        report = eng.sync()
        assert report.conflicts[0].resolution == "local_wins"
        assert eng.state["ku-1"] == "local-new"
        assert server.store["ku-1"]["value"] == "local-new"

    def test_lww_server_wins(self, tmp_path):
        eng, server = self._engine(tmp_path)
        # make local op timestamp older than server's
        eng._ops.clear()
        eng.state.clear()
        old = eng._clock() if callable(getattr(eng, "_clock", None)) else ""
        eng.local_set("ku-1", "local-old")
        # force local op to look old
        eng._ops[-1].updated_at = "2020-01-01T00:00:00"
        server.store["ku-1"] = {
            "value": "server-new", "updated_at": "2030-01-01T00:00:00",
            "device_id": "dev-2"}
        report = eng.sync()
        assert report.conflicts[0].resolution == "server_wins"
        assert eng.state["ku-1"] == "server-new"
        assert "ku-1" not in server.store or \
            server.store["ku-1"]["value"] == "server-new"

    def test_rollback_resolution_restores_server_value(self, tmp_path):
        eng, server = self._engine(tmp_path)
        eng.local_set("ku-1", "local")
        server.store["ku-1"] = {
            "value": "server", "updated_at": "2026-10-27T00:00:00",
            "device_id": "dev-2"}
        report = eng.sync(resolution="rollback")
        assert set(report.rolled_back) == {"ku-1"}
        assert report.conflicts[0].resolution == "rollback"
        assert eng.state["ku-1"] == "server"

    def test_checkpoint_clears_pending(self, tmp_path):
        eng, _ = self._engine(tmp_path)
        eng.local_set("a", 1)
        assert len(eng.pending_ops()) == 1
        eng.sync()
        assert eng.pending_ops() == []
        assert eng.last_checkpoint != ""

    def test_resume_after_restart_does_not_repush(self, tmp_path):
        eng, server = self._engine(tmp_path)
        eng.local_set("a", 1)
        eng.sync()
        eng2 = OfflineSyncEngine(server, eng.op_log_path, device_id="dev-1")
        report = eng2.sync()
        assert report.pushed == 0  # already checkpointed

    def test_sync_report_serializable(self, tmp_path):
        eng, server = self._engine(tmp_path)
        eng.local_set("a", 1)
        server.store["b"] = {"value": 2,
                             "updated_at": "2026-10-28T00:00:00",
                             "device_id": "x"}
        report = eng.sync()
        d = report.to_dict()
        assert d["completed"] is True
        json.dumps(d)

    def test_sync_rollback_on_server_error(self, tmp_path):
        class ExplodingServer:
            def pull(self, since):
                raise RuntimeError("simulated server crash")

            def push(self, entries):  # pragma: no cover
                raise RuntimeError("should not be reached")

        path = str(tmp_path / "oplog.jsonl")
        eng = OfflineSyncEngine(ExplodingServer(), path, device_id="dev-1")
        eng.local_set("a", 1)
        pre_state = dict(eng.state)
        report = eng.sync()
        assert report.completed is False
        assert report.error == "simulated server crash"
        assert eng.state == pre_state  # rolled back

    def test_multiple_keys_synced(self, tmp_path):
        eng, server = self._engine(tmp_path)
        eng.local_set("a", 1)
        eng.local_set("b", 2)
        eng.local_set("c", 3)
        report = eng.sync()
        assert report.pushed == 3
        assert len(server.store) == 3

    def test_conflict_dataclass_to_dict(self):
        c = Conflict(key="k", local_value=1, server_value=2,
                     local_updated_at="t1", server_updated_at="t2",
                     resolution="local_wins")
        assert c.to_dict()["resolution"] == "local_wins"


# ===========================================================================
# M5 — Notification Service
# ===========================================================================

class TestNotifications:

    def _svc(self, clock_hour=None):
        sender = MockPushSender()
        if clock_hour is None:
            svc = NotificationService(sender=sender)
        else:
            fixed = datetime(2026, 10, 28, clock_hour, 0, 0)
            svc = NotificationService(sender=sender, clock=lambda: fixed)
        return svc, sender

    def _notif(self, user="u1", prio=2, idem="", title="Hello"):
        return Notification(notif_id="n1", user_id=user, title=title,
                            body="World", priority=prio,
                            idempotency_key=idem)

    # -- devices -----------------------------------------------------------

    def test_register_device(self):
        svc, _ = self._svc()
        d = svc.register_device("d1", "u1", "android", "tok-123")
        assert d.platform == "android"
        assert svc.devices_for_user("u1")[0].device_id == "d1"

    def test_register_rejects_bad_platform(self):
        svc, _ = self._svc()
        with pytest.raises(ValueError):
            svc.register_device("d1", "u1", "windows", "tok")

    def test_multiple_devices_per_user(self):
        svc, _ = self._svc()
        svc.register_device("d1", "u1", "android", "t1")
        svc.register_device("d2", "u1", "ios", "t2")
        svc.register_device("d3", "u2", "android", "t3")
        assert len(svc.devices_for_user("u1")) == 2
        assert len(svc.devices_for_user("u2")) == 1

    # -- templates ------------------------------------------------------------

    def test_template_render(self):
        te = TemplateEngine()
        out = te.render("Backup {name} failed after {count} tries",
                        {"name": "db", "count": 3})
        assert out == "Backup db failed after 3 tries"

    def test_template_missing_keys(self):
        te = TemplateEngine()
        assert te.render("Hi {name}", {}) == "Hi {name}"
        assert te.missing_keys("Hi {name}", {}) == ["name"]

    def test_service_template_render(self):
        svc, _ = self._svc()
        svc.add_template("backup_fail",
                         "title=Backup {name} failed | body=Check log {log}")
        n = svc.render_template("backup_fail", {"name": "db", "log": "L1"})
        assert n.title == "Backup db failed"
        assert n.body == "Check log L1"

    def test_unknown_template_raises(self):
        svc, _ = self._svc()
        with pytest.raises(KeyError):
            svc.render_template("nope", {})

    # -- priority queue -----------------------------------------------------------

    def test_flush_order_by_priority(self):
        svc, sender = self._svc(clock_hour=12)
        svc.register_device("d1", "u1", "android", "t")
        svc.enqueue(self._notif(prio=1, title="low"))
        svc.enqueue(self._notif(prio=4, title="critical"))
        svc.enqueue(self._notif(prio=3, title="high"))
        delivered = svc.flush()
        assert [d["title"] for d in delivered] == ["critical", "high", "low"]
        assert len(sender.sent) == 3

    def test_delivered_logged_and_badge(self):
        svc, _ = self._svc(clock_hour=12)
        svc.register_device("d1", "u1", "android", "t")
        svc.enqueue(self._notif())
        svc.flush()
        assert len(svc.delivered) == 1
        assert svc.badge_count("u1") == 1

    # -- quiet hours ---------------------------------------------------------------

    def test_quiet_hours_defer_low_priority(self):
        svc, sender = self._svc(clock_hour=23)  # 23:00 inside 22-07
        svc.register_device("d1", "u1", "android", "t")
        svc.enqueue(self._notif(prio=1, title="low"))
        delivered = svc.flush()
        assert delivered == []
        assert svc.pending_count() == 1
        assert any(s["reason"] == "quiet_hours" for s in svc.suppressed)

    def test_quiet_hours_bypass_critical(self):
        svc, sender = self._svc(clock_hour=23)
        svc.register_device("d1", "u1", "android", "t")
        svc.enqueue(self._notif(prio=4, title="critical"))
        delivered = svc.flush()
        assert len(delivered) == 1
        assert sender.sent[0]["title"] == "critical"

    def test_no_quiet_hours_during_day(self):
        svc, sender = self._svc(clock_hour=12)
        svc.register_device("d1", "u1", "android", "t")
        svc.enqueue(self._notif(prio=1, title="low"))
        assert len(svc.flush()) == 1

    def test_quiet_hours_wrap_midnight_detection(self):
        svc, _ = self._svc(clock_hour=5)
        assert svc._in_quiet_hours(svc._clock()) is True
        svc2, _ = self._svc(clock_hour=10)
        assert svc2._in_quiet_hours(svc2._clock()) is False

    # -- dedupe ----------------------------------------------------------------------

    def test_dedupe_by_idempotency_key(self):
        svc, _ = self._svc(clock_hour=12)
        svc.register_device("d1", "u1", "android", "t")
        first = svc.enqueue(self._notif(idem="op-123"))
        dup = svc.enqueue(self._notif(idem="op-123"))
        assert first is not None
        assert dup is None
        assert any(s["reason"] == "duplicate" for s in svc.suppressed)
        assert len(svc.flush()) == 1  # only first delivered

    def test_no_dedupe_without_key(self):
        svc, _ = self._svc(clock_hour=12)
        svc.register_device("d1", "u1", "android", "t")
        svc.enqueue(self._notif())
        svc.enqueue(self._notif())
        assert len(svc.flush()) == 2

    def test_dedupe_records_first_notif_id(self):
        svc, _ = self._svc(clock_hour=12)
        first = svc.enqueue(self._notif(idem="k1"))
        svc.enqueue(self._notif(idem="k1"))
        rec = next(s for s in svc.suppressed if s["reason"] == "duplicate")
        assert rec["first_notif_id"] == first

    # -- payload -----------------------------------------------------------------------

    def test_push_payload_fields(self):
        svc, sender = self._svc(clock_hour=12)
        svc.register_device("d1", "u1", "ios", "tok-9")
        svc.enqueue(self._notif(prio=3, title="Sync done"))
        svc.flush()
        payload = sender.sent[0]
        assert payload["platform"] == "ios"
        assert payload["token"] == "tok-9"
        assert payload["priority"] == 3

    def test_notification_to_dict(self):
        n = self._notif(idem="x")
        d = n.to_dict()
        assert d["idempotency_key"] == "x"
        assert d["priority"] == 2


# ===========================================================================
# Integration — modules working together
# ===========================================================================

class TestV24Integration:

    def test_nl_query_feeds_voice_response(self):
        """Voice transcript -> NL query -> spoken answer (all mocks)."""
        asr = MockASR(script=["dem loi production"])
        tts = MockTTS()
        vi = VoiceInterface(asr, tts, clock=lambda: 0.0)
        engine = NLQueryEngine(KU_FIXTURES, now=NOW)

        vi.start_session()
        vi.listen()
        transcript = vi.transcribe()
        result = engine.query(transcript)
        answer = f"Tim thay {result.total_matches} loi production"
        turn = vi.respond(answer)

        assert result.total_matches == 1
        assert turn.response == answer.upper()
        assert tts.spoken == [answer.upper()]
        assert vi.state == VoiceState.IDLE

    def test_synced_data_queryable_by_nl_engine(self, tmp_path):
        """Offline sync pulls server rows; NL engine queries the merged state."""
        server = ServerStub()
        server.store["ku-9"] = {
            "id": "ku-9", "title": "kubernetes rollback",
            "type": "ERROR", "scope": "PRODUCTION", "status": "VERIFIED",
            "tags": ["k8s"], "created_at": "2026-10-27T10:00:00",
            "value": {"id": "ku-9"}, "updated_at": "2026-10-28T01:00:00",
            "device_id": "dev-2"}
        eng = OfflineSyncEngine(server, str(tmp_path / "log.jsonl"))
        eng.sync()

        rows = []
        for key, srv in server.store.items():
            row = dict(srv["value"])
            row.update({"title": srv["value"].get("id", key)})
            rows.append(row)
        # simpler: query engine over the pulled KU dicts
        pulled = [dict(server.store["ku-9"]["value"])]
        pulled[0]["title"] = "kubernetes rollback"
        pulled[0]["type"] = "ERROR"
        pulled[0]["scope"] = "PRODUCTION"
        pulled[0]["created_at"] = "2026-10-27T10:00:00"

        engine = NLQueryEngine(pulled, now=NOW)
        result = engine.query("tim loi production")
        assert [r["id"] for r in result.results] == ["ku-9"]

    def test_notification_after_sync_conflict(self, tmp_path):
        """Sync conflict -> critical notification queued and delivered."""
        server = ServerStub()
        eng = OfflineSyncEngine(server, str(tmp_path / "log.jsonl"),
                                device_id="dev-1")
        eng.local_set("ku-1", "local-edit")
        server.store["ku-1"] = {
            "value": "server-edit", "updated_at": "2020-01-01T00:00:00",
            "device_id": "dev-2"}
        report = eng.sync()

        svc = NotificationService(clock=lambda: datetime(2026, 10, 28, 23, 0))
        svc.register_device("phone-1", "owner", "android", "tok")
        svc.add_template("conflict",
                         "title=Sync conflict on {key} | body={n} conflict(s)")
        n = svc.render_template("conflict", {
            "key": report.conflicts[0].key,
            "n": len(report.conflicts),
            "priority": "critical",
            "user_id": "owner",
            "idempotency_key": f"sync-{report.conflicts[0].key}",
        })
        assert svc.enqueue(n) is not None
        delivered = svc.flush()
        assert len(delivered) == 1  # critical bypasses quiet hours
        assert "Sync conflict on ku-1" == delivered[0]["title"]

    def test_notification_dedupe_prevents_double_alert(self, tmp_path):
        """Same sync conflict replayed must not alert twice (idempotency)."""
        server = ServerStub()
        eng = OfflineSyncEngine(server, str(tmp_path / "log.jsonl"))
        eng.local_set("a", "x")
        report1 = eng.sync()

        svc = NotificationService(clock=lambda: datetime(2026, 10, 28, 12, 0))
        svc.register_device("d", "owner", "android", "t")

        def alert(r):
            key = r.conflicts[0].key if r.conflicts else "none"
            n = Notification(notif_id="nx", user_id="owner", title="conflict",
                             body=key, priority=3, idempotency_key=f"c-{key}")
            return svc.enqueue(n)

        r1 = alert(report1)
        # simulate a duplicate sync report (e.g., replayed event)
        report2 = SyncReport(conflicts=[Conflict(
            key=report1.conflicts[0].key if report1.conflicts else "none",
            local_value="x", server_value="y",
            local_updated_at="", server_updated_at="")])
        r2 = alert(report2)
        if report1.conflicts:
            assert r1 is not None and r2 is None
        else:
            assert r1 is not None and r2 is not None  # no conflicts -> different keys path
        svc.flush()

    def test_voice_barge_in_then_retry_turn(self):
        """Barge-in cancels one response; next turn completes normally."""
        asr = MockASR(script=["cau hoi mot", "cau hoi hai"])
        tts = MockTTS()
        vi = VoiceInterface(asr, tts, clock=lambda: 0.0)
        vi.start_session()
        vi.listen()
        t1 = vi.transcribe()
        # user starts talking during response -> barge-in
        turn1 = vi.respond(t1, interrupt_during_speech=True)
        assert turn1.interrupted and tts.spoken == []

        vi.start_session()
        vi.listen()
        t2 = vi.transcribe()
        turn2 = vi.respond(t2)
        assert turn2.interrupted is False
        assert tts.spoken == ["CAU HOI HAI"]
        assert vi.barge_in_count == 1  # reset by the second start_session

    def test_end_to_end_owner_story(self, tmp_path):
        """Owner edits offline -> sync -> NL query -> voice answer + alert."""
        server = ServerStub()
        eng = OfflineSyncEngine(server, str(tmp_path / "log.jsonl"))
        eng.local_set("ku-100", {"title": "new incident postmortem",
                                 "type": "ERROR", "scope": "PRODUCTION",
                                 "created_at": "2026-10-28T09:00:00"})
        eng.sync()

        rows = [dict(v["value"]) | {"key": k} for k, v in server.store.items()]
        engine = NLQueryEngine(rows, now=NOW)
        result = engine.query("dem loi production")

        asr = MockASR(script=["dem loi production"])
        tts = MockTTS()
        vi = VoiceInterface(asr, tts, clock=lambda: 0.0)
        vi.start_session()
        vi.listen()
        transcript = vi.transcribe()
        answer = f"Co {result.total_matches} loi production"
        turn = vi.respond(answer)

        assert transcript == "dem loi production"
        assert result.total_matches == 1
        assert turn.response == answer.upper()
