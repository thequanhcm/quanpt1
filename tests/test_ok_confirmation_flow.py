"""Tests for 'ok' = owner confirmation + no-runaround behavior (27/10/2026).

Owner requirement (verbatim): "thiết lập khi anh gõ ok, OK có nghĩa là anh đã
xác nhận, còn không sẽ không phản hồi hoặc không có xác nhận, thiết lập để
trợ lý không hỏi lòng vòng".

Three layers tested here:
1. Command center: "ok" executes a STAGED pending action (e.g. re-probe Pi 5)
   immediately; "ok" with nothing pending is SILENT (no runaround reply);
   pending actions expire after TTL (stale confirmations must not fire).
2. Adapter priority: "ok" must NOT fall into the approval-card regex that
   used to treat it as a bare 'Duyệt' (the runaround bug from the screenshot).
3. Responder auto-run: an AI reply that ASKS PERMISSION for a read-only probe
   is replaced by a real probe result — the bot never begs for permission to
   do something it can safely do itself.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from tools import netchat_command_center as cc  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_pending():
    cc._PENDING_ACTIONS.clear()
    yield
    cc._PENDING_ACTIONS.clear()


# ---------------------------------------------------------------------------
# Layer 1: stage → ok → execute
# ---------------------------------------------------------------------------


def test_ok_executes_staged_reprobe_pi5() -> None:
    cc.stage_pending_action("ch1", "chạy lại probe Pi 5", "reprobe_pi5")
    intent, reply = cc.route_message("ok", chat_session_id="ch1")
    assert intent == "ok_confirm"
    assert "Pi 5" in reply
    assert "kiểm tra ngay" in reply
    # consumed once — second 'ok' must be silent
    intent2, reply2 = cc.route_message("ok", chat_session_id="ch1")
    assert intent2 == "ok_silent" and reply2 == ""


def test_ok_silent_when_nothing_pending() -> None:
    intent, reply = cc.route_message("OK", chat_session_id="ch-none")
    assert intent == "ok_silent"
    assert reply == ""


def test_ok_case_insensitive_and_punctuated() -> None:
    cc.stage_pending_action("ch2", "label", "reprobe_full")
    intent, _ = cc.route_message("  OK!  ", chat_session_id="ch2")
    assert intent == "ok_confirm"


def test_pending_action_ttl_expiry_blocks_stale_ok() -> None:
    cc.stage_pending_action("ch3", "label", "reprobe_pi5")
    cc._PENDING_ACTIONS["ch3"]["staged_at"] = time.time() - (cc._PENDING_TTL_S + 5)
    intent, reply = cc.route_message("ok", chat_session_id="ch3")
    assert intent == "ok_silent"  # stale confirmation must NOT fire old action


def test_ok_does_not_reach_approval_adapter() -> None:
    """Regression: the screenshot bug — 'ok' was parsed by the approval
    adapter's bare-'Duyệt' regex → long 'KHÔNG CÓ HỒ SƠ' runaround."""
    cc.stage_pending_action("ch4", "chạy lại probe", "reprobe_full")
    intent, reply = cc.route_message("ok", chat_session_id="ch4")
    assert intent == "ok_confirm"
    assert "HỒ SƠ" not in reply and "DUYỆT" not in reply


def test_reprobe_reports_honest_offline() -> None:
    """E2E honesty: reply must reflect edge monitor truth — either honest
    'chưa xác minh' (offline) or honest ONLINE (heartbeat-connected)."""
    cc.stage_pending_action("ch5", "probe", "reprobe_pi5")
    _, reply = cc.route_message("ok", chat_session_id="ch5")
    assert ("chưa xác minh được" in reply) or ("ONLINE" in reply)
    # Không bao giờ nói sai bản chất "port 8768 trên PC"
    assert "port 8768" not in reply


# ---------------------------------------------------------------------------
# Layer 2: other commands unaffected
# ---------------------------------------------------------------------------


def test_regular_commands_still_route() -> None:
    intent, reply = cc.route_message("giúp", chat_session_id="ch6")
    assert intent == "help"
    assert "KÊNH LÀM VIỆC" in reply


def test_free_chat_still_falls_through() -> None:
    intent, reply = cc.route_message("thời tiết hôm nay thế nào?", chat_session_id="ch7")
    assert intent is None and reply == ""


# ---------------------------------------------------------------------------
# Layer 3: responder auto-runs read-only probes instead of asking permission
# ---------------------------------------------------------------------------


def test_responder_autoruns_probe_when_ai_asks_permission() -> None:
    from tools import netchat_auto_responder as resp

    ai_reply = (
        "Dạ em báo cáo: Pi 5 OFFLINE.\n"
        "Đề xuất: Anh cho phép em chạy lại probe để kiểm tra lần nữa ạ?\n"
        "Anh xác nhận cho em chạy lại probe nhé? Em chờ lệnh ạ."
    )
    out = resp._maybe_autorun_probe(ai_reply)
    assert out is not None
    assert "Đã xác nhận" in out
    assert "chờ lệnh" not in out  # permission beg removed
    assert ("vẫn OFFLINE" in out) or ("ONLINE" in out)


def test_responder_keeps_normal_ai_replies_untouched() -> None:
    from tools import netchat_auto_responder as resp

    normal = "Dạ, em chúc anh một ngày tốt lành ạ."
    assert resp._maybe_autorun_probe(normal) is None
