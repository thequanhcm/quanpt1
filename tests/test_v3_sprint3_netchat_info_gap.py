"""Tests — V3 Sprint 3: NetChat integration cho Information Gap (routing).

Quy tắc test: KHÔNG gọi gateway/NetChat thật (send_info_request được mock),
KHÔNG API key. Kiểm tra routing 3 loại giao tiếp (V3 §10) không trộn lẫn.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE))

from quan_ai_brain.cognition.information_gap_analyzer import (  # noqa: E402
    InformationGapAnalyzer,
    InfoItem,
    ReadinessStatus,
    WaitingState,
)
from quan_ai_brain.governance import netchat_info_gap_adapter as adapter  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Mỗi test dùng DB riêng — không đụng data/information_gaps.db thật."""
    ana = InformationGapAnalyzer(workspace=tmp_path)
    monkeypatch.setattr(adapter, "get_analyzer", lambda: ana)
    yield ana


def _seed_waiting(analyzer, task_id="TASK-RT01", extra_inputs=None):
    inputs = [InfoItem(key="url", note="link production")]
    if extra_inputs:
        inputs += extra_inputs
    a = analyzer.analyze_request(
        task_id, goal="Kiểm tra website", acceptance_criteria=["200 OK"],
        required_inputs=inputs,
    )
    analyzer.save_request(a, netchat_message_id="msg_test")
    return a


# ---------------------------------------------------------------------------
# has_waiting_task — phân biệt info-gap task với approval task
# ---------------------------------------------------------------------------


def test_has_waiting_task_true_for_open_task(isolated_db):
    _seed_waiting(isolated_db)
    assert adapter.has_waiting_task("TASK-RT01") is True


def test_has_waiting_task_false_for_unknown(isolated_db):
    assert adapter.has_waiting_task("TASK-KHONGTONTAI") is False


def test_has_waiting_task_false_after_resolved(isolated_db):
    _seed_waiting(isolated_db)
    isolated_db.record_owner_reply("TASK-RT01", "q_TASK-RT01_input_url", "https://x")
    # RESOLVED không còn trong list_waiting mặc định
    assert adapter.has_waiting_task("TASK-RT01") is False


# ---------------------------------------------------------------------------
# handle_owner_info_reply — map trả lời → đúng task/câu hỏi (V3 §8.1)
# ---------------------------------------------------------------------------


def test_reply_updates_waiting_task(isolated_db):
    _seed_waiting(isolated_db)
    reply = adapter.handle_owner_info_reply(
        "TASK-RT01 link là https://noibo.viettel.vn", sender_user_id="3b1ughs36i8e9p46im8opnms8w"
    )
    assert reply is not None
    assert "KHÔNG PHẢI phê duyệt" in reply
    # Trạng thái đã chuyển RESOLVED (đủ thông tin)
    assert adapter.has_waiting_task("TASK-RT01") is False
    row = isolated_db.get_waiting_task("TASK-RT01")
    spec = json.loads(row["spec_json"])
    assert spec["readiness"] == ReadinessStatus.READY.value
    facts = {f["key"]: f for f in spec["known_facts"]}
    assert facts["q_TASK-RT01_input_url"]["evidence"] == "OWNER_PROVIDED"
    assert facts["q_TASK-RT01_input_url"]["source_ref"].startswith("netchat:owner")


def test_reply_partial_still_waiting(isolated_db):
    _seed_waiting(isolated_db, extra_inputs=[InfoItem(key="scope", note="quyền API")])
    reply = adapter.handle_owner_info_reply(
        "TASK-RT01 url là https://x", sender_user_id="quanpt1"
    )
    assert reply is not None
    assert "Còn thiếu" in reply and "VẪN ĐANG CHỜ" in reply
    assert adapter.has_waiting_task("TASK-RT01") is True


def test_reply_unknown_task_returns_none(isolated_db):
    assert adapter.handle_owner_info_reply("TASK-KHONGTONTAI giá trị xyz") is None


def test_reply_without_task_code_returns_none(isolated_db):
    _seed_waiting(isolated_db)
    assert adapter.handle_owner_info_reply("hôm nay thời tiết đẹp không?") is None


# ---------------------------------------------------------------------------
# send_info_request — format + không gửi khi READY (mock subprocess, không thật)
# ---------------------------------------------------------------------------


def test_send_info_request_nothing_to_send(isolated_db, monkeypatch):
    # READY analysis → render rỗng → KHÔNG gọi subprocess
    a = isolated_db.analyze_request("TASK-OK1", goal="g", acceptance_criteria=["c"])
    called = {"n": 0}

    def fake_run(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("subprocess must not be called for READY analysis")

    monkeypatch.setattr("subprocess.run", fake_run)
    r = adapter.send_info_request(a)
    assert r["sent"] is False
    assert r["error"] == "nothing_to_send"
    assert called["n"] == 0


def test_send_info_request_two_step_confirm(isolated_db, monkeypatch):
    a = isolated_db.analyze_request(
        "TASK-SND", goal="Kiểm tra website", acceptance_criteria=["200 OK"],
        required_inputs=[InfoItem(key="url", note="link")],
    )
    calls = []

    class FakeCompleted:
        def __init__(self, returncode, stdout, stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "--confirmed" not in cmd:
            return FakeCompleted(2, "", "CONFIRM-REQUIRED: deadbeef1234")
        return FakeCompleted(0, "posted ok")

    monkeypatch.setattr("subprocess.run", fake_run)
    r = adapter.send_info_request(a)
    assert r["sent"] is True
    assert len(calls) == 2  # 2 bước send → confirm
    assert any("--confirmed" in c for c in calls)
    # Nội dung tin có mã nhiệm vụ + format V3 §7
    text_arg = calls[0][4] if len(calls[0]) > 4 else ""
    assert "TASK-SND" in " ".join(calls[0])
    assert "[CẦN ANH QUANPT1 BỔ SUNG THÔNG TIN]" in text_arg or any(
        "[CẦN ANH QUANPT1 BỔ SUNG THÔNG TIN]" in str(c) for c in calls
    )


def test_send_info_request_subprocess_failure_is_honest(isolated_db, monkeypatch):
    a = isolated_db.analyze_request(
        "TASK-FAIL", goal="g", acceptance_criteria=["c"],
        required_inputs=[InfoItem(key="x", note="n")],
    )

    def fake_run(cmd, **kwargs):
        raise OSError("network unreachable")

    monkeypatch.setattr("subprocess.run", fake_run)
    r = adapter.send_info_request(a)
    assert r["sent"] is False
    assert "network unreachable" in r["error"]
