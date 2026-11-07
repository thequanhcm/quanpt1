"""Tests — M5: Human-like Conversation (phần 1).

Phạm vi:
1. ConversationStateManager — lưu/get/update state per-channel, TTL, anaphora,
   build_contextualized_query (có/không đại từ, hết hạn, không state).
2. SelfQA — classify 6 nhóm câu hỏi self + answer grounded từ dữ liệu thật
   (workspace thật, read-only); câu không self → None; câu "tôi" không khớp.
3. HealthMonitor CLO-stall — edge-trigger, không spam, fail-honest sent flag.
4. Wire /converse — Self-QA intercept đứng trước intent (kiểm qua source).
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.cognition.conversation_state import (  # noqa: E402
    ConversationStateManager,
)
from quan_ai_brain.cognition.self_qa import SelfQA  # noqa: E402
from quan_ai_brain.monitoring.health_monitor import HealthMonitor  # noqa: E402


# ---------------------------------------------------------------------------
# ConversationStateManager
# ---------------------------------------------------------------------------

class TestConversationState:
    def test_update_and_get_roundtrip(self, tmp_path):
        mgr = ConversationStateManager(tmp_path)
        mgr.update("voice", "Docker là gì anh?", "Docker là nền tảng container.")
        entry = mgr.get("voice")
        assert entry is not None
        assert "Docker" in entry["last_user_text"]
        assert "container" in entry["last_reply"]

    def test_get_missing_channel_none(self, tmp_path):
        assert ConversationStateManager(tmp_path).get("web") is None

    def test_ttl_expired(self, tmp_path):
        mgr = ConversationStateManager(tmp_path, ttl_sec=0.05)
        mgr.update("voice", "q", "a")
        time.sleep(0.08)
        assert mgr.get("voice") is None

    def test_corrupt_file_fail_honest(self, tmp_path):
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "conversation_state.json").write_text(
            "{không phải json", encoding="utf-8")
        mgr = ConversationStateManager(tmp_path)
        assert mgr.get("voice") is None  # không crash, coi như không có state
        mgr.update("voice", "q2", "a2")  # và ghi đè được
        assert mgr.get("voice") is not None

    def test_anaphora_detection(self, tmp_path):
        mgr = ConversationStateManager(tmp_path)
        assert mgr.has_anaphora("Nó có bản trả phí không?")
        assert mgr.has_anaphora("Thế còn bản free thì sao?")
        assert mgr.has_anaphora("Vậy cài như thế nào?")
        assert not mgr.has_anaphora("Giờ Việt Nam mấy giờ?")

    def test_contextualized_with_anaphora(self, tmp_path):
        mgr = ConversationStateManager(tmp_path)
        mgr.update("voice", "GLM-5.3 là gì?", "Là mô hình ngôn ngữ của Z.ai.")
        out = mgr.build_contextualized_query("voice", "Nó free không?")
        assert "NGỮ CẢNH" in out
        assert "GLM-5.3" in out
        assert "Nó free không?" in out

    def test_no_anaphora_returns_original(self, tmp_path):
        mgr = ConversationStateManager(tmp_path)
        mgr.update("voice", "GLM là gì?", "Là mô hình.")
        assert mgr.build_contextualized_query("voice", "Giờ mấy giờ?") == "Giờ mấy giờ?"

    def test_expired_state_returns_original(self, tmp_path):
        mgr = ConversationStateManager(tmp_path, ttl_sec=0.05)
        mgr.update("voice", "q", "a")
        time.sleep(0.08)
        assert mgr.build_contextualized_query("voice", "Nó vậy?") == "Nó vậy?"


# ---------------------------------------------------------------------------
# SelfQA — classify + grounded answers
# ---------------------------------------------------------------------------

class TestSelfQAClassify:
    def setup_method(self):
        self.qa = SelfQA(WORKSPACE)

    def test_identity(self):
        assert self.qa.classify("Em là ai vậy?") == "identity"
        assert self.qa.classify("bạn tên gì") == "identity"

    def test_capabilities(self):
        assert self.qa.classify("Em làm được những gì?") == "capabilities"
        assert self.qa.classify("Em có năng lực gì?") == "capabilities"

    def test_location(self):
        assert self.qa.classify("Em đang chạy ở đâu?") == "location"

    def test_health(self):
        assert self.qa.classify("Hệ thống có khỏe không?") == "health"
        assert self.qa.classify("Em ổn không?") == "health"

    def test_learning(self):
        assert self.qa.classify("Em đã học được gì?") == "learning"
        assert self.qa.classify("Em đang học gì vậy?") == "learning"

    def test_limits(self):
        assert self.qa.classify("Em không làm được gì?") == "limits"
        assert self.qa.classify("Em còn hạn chế gì?") == "limits"

    def test_not_self_questions(self):
        assert self.qa.classify("Tôi là ai?") is None        # hỏi về ANH, không phải em
        assert self.qa.classify("Thời tiết hôm nay thế nào?") is None
        assert self.qa.classify("Mở Chrome lên") is None
        assert self.qa.classify("") is None
        assert self.qa.classify("x" * 400) is None           # quá dài


class TestSelfQAAnswersGrounded:
    def setup_method(self):
        self.qa = SelfQA(WORKSPACE)

    def test_identity_answer_truthful(self):
        out = self.qa.answer("Em là ai vậy?")
        # (07/11/2026) rename TONY→CHERRY theo lệnh owner — identity trả CHERRY
        assert out and "CHERRY" in out
        assert "Quanpt1" in out or "Quân" in out

    def test_capabilities_mentions_verified_count(self):
        out = self.qa.answer("Em làm được những gì?")
        assert "năng lực đã kiểm chứng" in out
        assert "không phóng đại" in out

    def test_health_uses_real_snapshot(self):
        out = self.qa.answer("Hệ thống có khỏe không?")
        assert out and ("bình thường" in out or "cảnh báo" in out
                        or "nghiêm trọng" in out or "chưa đo được" in out)

    def test_learning_uses_real_db(self):
        out = self.qa.answer("Em đã học được gì?")
        assert "CLO" in out or "Tự chủ học" in out
        assert "Q-4" in out  # nhắc đúng trạng thái quarantine chờ duyệt

    def test_limits_lists_real_limitations(self):
        out = self.qa.answer("Em còn hạn chế gì?")
        assert out and "self model" in out.lower()

    def test_error_fail_honest(self, tmp_path):
        """Workspace rỗng → dữ liệu lỗi → trả lời trung thực, không crash."""
        qa = SelfQA(tmp_path)
        out = qa.answer("Em là ai?")
        # vẫn trả lời identity (không cần DB) hoặc fail-honest — không crash
        assert out is None or "Em" in out


# ---------------------------------------------------------------------------
# HealthMonitor — CLO stall (edge-trigger, fail-honest)
# ---------------------------------------------------------------------------

class _FakeAgg:
    def snapshot(self, force=False):
        return {"overall_status": "NORMAL", "pc": {}, "pi5": {}}


class _FakeAlertEngine:
    """Không có _record_alert → mô phỏng test stub; CLO alert phải sent=False."""

    def evaluate_checks(self, component_id, checks, thresholds):
        return []

    def recent_alerts(self, limit=20):
        return []


class TestCLOStallAlert:
    def _make_monitor(self, tmp_path, sessions):
        con = sqlite3.connect(tmp_path / "data" / "learning_checkpoints.db")
        con.execute("CREATE TABLE learning_sessions (session_id TEXT, cycle_number INTEGER, "
                    "started_at TEXT, ended_at TEXT, status TEXT)")
        for cyc, started, status in sessions:
            con.execute("INSERT INTO learning_sessions VALUES (?,?,?,?,?)",
                        (f"s{cyc}", cyc, started, None, status))
        con.commit()
        con.close()

    def test_running_over_24h_triggers_once(self, tmp_path):
        (tmp_path / "data").mkdir()
        old = "2026-10-30T16:10:16+00:00"  # > 24h trước (today 01/11)
        self._make_monitor(tmp_path, [(7, old, "RUNNING")])
        mon = HealthMonitor(tmp_path, _FakeAgg(), alert_engine=_FakeAlertEngine())
        r1 = mon.run_once()
        clo = [a for a in r1["alerts"] if a["check_id"] == "selfcare:clo_stalled"]
        assert len(clo) == 1
        assert clo[0]["sent"] is False  # fake engine — KHÔNG khai sent=True
        assert clo[0]["suppressed_reason"] == "no_real_alert_engine"
        assert "Q-4" in clo[0]["message"]

    def test_edge_trigger_no_repeat(self, tmp_path):
        (tmp_path / "data").mkdir()
        old = "2026-10-30T16:10:16+00:00"
        self._make_monitor(tmp_path, [(7, old, "RUNNING")])
        mon = HealthMonitor(tmp_path, _FakeAgg(), alert_engine=_FakeAlertEngine())
        r1 = mon.run_once()
        r2 = mon.run_once()
        n1 = sum(1 for a in r1["alerts"] if a["check_id"] == "selfcare:clo_stalled")
        n2 = sum(1 for a in r2["alerts"] if a["check_id"] == "selfcare:clo_stalled")
        assert n1 == 1 and n2 == 0  # lần 2 không lặp

    def test_fresh_session_no_alert(self, tmp_path):
        (tmp_path / "data").mkdir()
        from datetime import datetime, timedelta, timezone
        fresh = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self._make_monitor(tmp_path, [(8, fresh, "RUNNING")])
        mon = HealthMonitor(tmp_path, _FakeAgg(), alert_engine=_FakeAlertEngine())
        r = mon.run_once()
        assert not any(a["check_id"] == "selfcare:clo_stalled" for a in r["alerts"])

    def test_completed_session_no_alert(self, tmp_path):
        (tmp_path / "data").mkdir()
        old = "2026-10-30T16:10:16+00:00"
        self._make_monitor(tmp_path, [(7, old, "COMPLETED")])
        mon = HealthMonitor(tmp_path, _FakeAgg(), alert_engine=_FakeAlertEngine())
        r = mon.run_once()
        assert not any(a["check_id"] == "selfcare:clo_stalled" for a in r["alerts"])


# ---------------------------------------------------------------------------
# Wire /converse — Self-QA đứng trước intent (source check)
# ---------------------------------------------------------------------------

class TestConverseWiring:
    def test_converse_has_self_qa_before_intent(self):
        src = (WORKSPACE / "src" / "quan_ai_brain" / "web" / "server.py").read_text(
            encoding="utf-8")
        conv = src[src.find("def _handle_api_edge_converse"):src.find("def _handle_api_executive_netchat_send")]
        self_pos = conv.find("self_qa import SelfQA")
        intent_pos = conv.find("route_message as _route")
        conv_pos = conv.find("ConversationStateManager")
        assert self_pos != -1 and intent_pos != -1
        assert self_pos < intent_pos, "Self-QA phải đứng trước intent"
        assert conv_pos != -1, "phải ghi ConversationStateManager"

    def test_voice_command_also_wired(self):
        src = (WORKSPACE / "src" / "quan_ai_brain" / "web" / "server.py").read_text(
            encoding="utf-8")
        vc = src[src.find("def _handle_api_edge_voice_command"):src.find("def _handle_api_edge_converse")]
        assert vc.find("self_qa import SelfQA") != -1
        assert vc.find("ConversationStateManager") != -1
