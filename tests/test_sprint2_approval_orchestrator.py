"""Tests for Sprint 2 (Master Prompt V3): ApprovalOrchestrator stack —
ApprovalCardStore + NetChatApprovalAdapter với lời giải thích cụ thể.

Maps V3 Section XII: T3 (sửa phương án), T5 (phê duyệt không hợp lệ),
T8/T11 (restart/OUTCOME — trung thực), T14 (thu hồi), T15 (R5),
T10 (báo cáo giải thích đầy đủ).
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from quan_ai_brain.governance.approval_cards import ApprovalCardStore, new_task_code
from quan_ai_brain.governance.netchat_approval_adapter import NetChatApprovalAdapter
from quan_ai_brain.governance.policy import PolicyEngine, ActionRequest, RiskLevel, DecisionStatus


CARD_MD = (
    "[XIN PHÊ DUYỆT] — Mã nhiệm vụ: {code}\n"
    "1. Mục đích: kiểm thử\n"
    "2. Căn cứ: audit\n"
    "3. Phương án: test\n"
    "4. Rủi ro: thấp\n"
    "5. Xin ý kiến: DUYỆT {code}\n"
    "Trạng thái: ĐANG CHỜ ANH QUANPT1 PHÊ DUYỆT. CHƯA THỰC HIỆN."
)


@pytest.fixture()
def card_store(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    return ApprovalCardStore(ws / "data" / "governance.db", workspace=ws)


@pytest.fixture()
def adapter(card_store, monkeypatch):
    a = NetChatApprovalAdapter(governance_db=card_store.db_path)
    # không post thật ra NetChat trong unit test
    sent: list[str] = []

    def fake_send(text):
        sent.append(text)
        return {"ok": True}

    monkeypatch.setattr(a, "send_to_channel", fake_send)
    a.sent = sent  # for assertions
    return a


def _mk_card(store: ApprovalCardStore, code: str) -> None:
    store.create_card(code, "Nhiệm vụ kiểm thử", CARD_MD.format(code=code), risk_level=1, goal="test")


# ---------------------------------------------------------------------------
# ApprovalCardStore core lifecycle
# ---------------------------------------------------------------------------


def test_create_card_persists_and_is_pending(card_store):
    _mk_card(card_store, "TASK-TEST0001")
    card = card_store.get_card("TASK-TEST0001")
    assert card is not None
    assert card.status == "PENDING_APPROVAL"
    assert card.request_id == "TASK-TEST0001"  # formal request bound to code
    assert card.ttl_expires_at_utc > card.created_at_utc


def test_duplicate_task_code_rejected(card_store):
    _mk_card(card_store, "TASK-DUP0001")
    with pytest.raises(ValueError, match="already exists"):
        _mk_card(card_store, "TASK-DUP0001")


def test_approve_via_formal_gate_one_time(card_store):
    _mk_card(card_store, "TASK-APP00001")
    card_store.approve_card("TASK-APP00001", approver="quanpt1", auth_method="test")
    card = card_store.get_card("TASK-APP00001")
    assert card.status == "APPROVED"
    # formal approvals row exists and is unconsumed
    conn = sqlite3.connect(str(card_store.db_path))
    row = conn.execute("SELECT status, consumed FROM approvals WHERE request_id=?", ("TASK-APP00001",)).fetchone()
    conn.close()
    assert row is not None
    assert row[1] == 0  # not consumed until execution starts


def test_double_approve_blocked_with_reason(card_store):
    _mk_card(card_store, "TASK-APP00002")
    card_store.approve_card("TASK-APP00002", approver="quanpt1")
    with pytest.raises(PermissionError, match="đã được phê duyệt"):
        card_store.approve_card("TASK-APP00002", approver="quanpt1")


def test_reject_and_reapprove_blocked(card_store):
    _mk_card(card_store, "TASK-REJ00001")
    card_store.reject_card("TASK-REJ00001", "Không hợp lý")
    assert card_store.get_card("TASK-REJ00001").status == "REJECTED"
    with pytest.raises(PermissionError):
        card_store.approve_card("TASK-REJ00001", approver="quanpt1")


def test_amend_returns_to_pending_new_version(card_store):
    _mk_card(card_store, "TASK-AMD0001")
    card_store.reject_card("TASK-AMD0001", "cần sửa")
    card = card_store.amend_card("TASK-AMD0001", CARD_MD.format(code="TASK-AMD0001"), reason="đã điều chỉnh")
    assert card.status == "PENDING_APPROVAL"
    assert card.version == 2


def test_ttl_expiry_marks_card_expired(card_store):
    _mk_card(card_store, "TASK-EXP0001")
    # force TTL into the past
    with sqlite3.connect(str(card_store.db_path)) as conn:
        conn.execute("UPDATE approval_cards SET ttl_expires_at_utc='2020-01-01T00:00:00+00:00' WHERE task_code='TASK-EXP0001'")
    n = card_store.refresh_expiry()
    assert n == 1
    assert card_store.get_card("TASK-EXP0001").status == "EXPIRED"


def test_approver_not_trusted_rejected(card_store):
    _mk_card(card_store, "TASK-TRU0001")
    with pytest.raises(PermissionError):
        card_store.approve_card("TASK-TRU0001", approver="impersonator")


def test_new_task_code_unique():
    codes = {new_task_code() for _ in range(50)}
    assert len(codes) == 50
    assert all(c.startswith("TASK-") for c in codes)


# ---------------------------------------------------------------------------
# Adapter: every reply EXPLAINS specifically (owner requirement 26/10)
# ---------------------------------------------------------------------------


def test_plain_duyet_maps_to_single_pending(adapter, card_store):
    _mk_card(card_store, "TASK-ONE0001")
    reply = adapter.handle_owner_message("Duyệt", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False)
    # phải NÓI RÕ duyệt gì — không được trả lời mơ hồ
    assert "TASK-ONE0001" in reply
    assert "ĐÃ DUYỆT" in reply
    assert "Vì sao" in reply or "duyệt theo lệnh" in reply
    assert card_store.get_card("TASK-ONE0001").status == "APPROVED"


def test_plain_duyet_with_multiple_pending_asks_for_code(adapter, card_store):
    _mk_card(card_store, "TASK-MUL0001")
    _mk_card(card_store, "TASK-MUL0002")
    reply = adapter.handle_owner_message("Duyệt", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False)
    assert "CẦN MÃ HỒ SƠ" in reply
    assert "TASK-MUL0001" in reply and "TASK-MUL0002" in reply
    # nothing approved
    assert card_store.get_card("TASK-MUL0001").status == "PENDING_APPROVAL"


def test_plain_duyet_when_nothing_pending_is_honest(adapter, card_store):
    _mk_card(card_store, "TASK-DON0001")
    card_store.approve_card("TASK-DON0001", approver="quanpt1")  # no longer pending
    reply = adapter.handle_owner_message("Duyệt", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False)
    # KHÔNG được lặp lại câu "Mọi quyết định đã được xử lý" gây hiểu nhầm
    assert "Mọi quyết định đã được xử lý" not in reply
    assert "KHÔNG CÓ HỒ SƠ" in reply
    assert "TASK-DON0001" in reply  # liệt kê hồ sơ gần nhất để đối chiếu


def test_duyet_with_exact_code(adapter, card_store):
    _mk_card(card_store, "TASK-CODE001")
    reply = adapter.handle_owner_message("DUYỆT TASK-CODE001", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False)
    assert "ĐÃ DUYỆT — TASK-CODE001" in reply
    assert "quanpt1" in reply
    assert "governance.db" in reply


def test_duyet_twice_is_explained_not_reexecuted(adapter, card_store):
    _mk_card(card_store, "TASK-TWICE01")
    r1 = adapter.handle_owner_message("DUYỆT TASK-TWICE01", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False)
    r2 = adapter.handle_owner_message("Duyệt", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False)
    assert "ĐÃ DUYỆT — TASK-TWICE01" in r1
    # lần 2 phải giải thích consume-once, chỉ rõ hồ sơ đã duyệt lúc nào
    assert "consume-once" in r2
    assert "đã được anh duyệt lúc" in r2
    assert "TASK-TWICE01" in r2


def test_duyet_unknown_code_lists_existing_cards(adapter, card_store):
    _mk_card(card_store, "TASK-HAVE01")
    reply = adapter.handle_owner_message("DUYỆT TASK-KHONGCO", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False)
    assert "KHÔNG TÌM THẤY" in reply
    assert "Vì sao" in reply
    assert "TASK-HAVE01" in reply  # gợi ý hồ sơ thật đang có


def test_reject_with_reason(adapter, card_store):
    _mk_card(card_store, "TASK-REJ0002")
    reply = adapter.handle_owner_message("TỪ CHỐI TASK-REJ0002: rủi ro cao", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False)
    assert "ĐÃ TỪ CHỐI — TASK-REJ0002" in reply
    assert "rủi ro cao" in reply
    assert "KHÔNG thực hiện" in reply


def test_sua_request_creates_amendment_flow(adapter, card_store):
    _mk_card(card_store, "TASK-SUA0001")
    reply = adapter.handle_owner_message("SỬA TASK-SUA0001: chỉ làm bước 1", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False)
    assert "GHI NHẬN YÊU CẦU SỬA" in reply
    assert "chỉ làm bước 1" in reply
    assert "KHÔNG thực hiện" in reply  # chưa duyệt lại thì không chạy


def test_non_owner_is_refused_with_identity_reason(adapter, card_store):
    _mk_card(card_store, "TASK-IDV0001")
    reply = adapter.handle_owner_message("DUYỆT TASK-IDV0001", sender_user_id="impostor_user", post=False)
    assert "KHÔNG THỰC THI" in reply
    assert "danh tính" in reply.lower()
    assert card_store.get_card("TASK-IDV0001").status == "PENDING_APPROVAL"  # untouched


def test_non_command_returns_empty(adapter):
    assert adapter.handle_owner_message("anh có thể phê duyệt được không?", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False) == ""
    assert adapter.handle_owner_message("Xin chào bot", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False) == ""


def test_chat_with_task_code_but_no_verb_is_unknown_explained(adapter, card_store):
    _mk_card(card_store, "TASK-QQQ0001")
    reply = adapter.handle_owner_message("TASK-QQQ0001 là gì vậy anh?", sender_user_id="3b1ughs36i8e9p46im8opnms8w", post=False)
    assert "CHƯA HIỂU LỆNH" in reply
    assert "TASK-QQQ0001" in reply


# ---------------------------------------------------------------------------
# Formal gate protections (V3 5.2/5.3, Section X)
# ---------------------------------------------------------------------------


def test_expired_card_cannot_be_approved(card_store):
    _mk_card(card_store, "TASK-EXP0002")
    with sqlite3.connect(str(card_store.db_path)) as conn:
        conn.execute("UPDATE approval_cards SET ttl_expires_at_utc='2020-01-01T00:00:00+00:00' WHERE task_code='TASK-EXP0002'")
    card_store.refresh_expiry()
    with pytest.raises(PermissionError, match="EXPIRED"):
        card_store.approve_card("TASK-EXP0002", approver="quanpt1")


def test_r5_never_approvable_via_card(card_store):
    # Ngay cả khi tạo card risk 5, policy vẫn BLOCKED độc lập với card
    with pytest.raises(Exception):
        card_store.create_card(
            "TASK-R500001", "Việc nguy hiểm", CARD_MD.format(code="TASK-R500001"),
            risk_level=5, goal="R5 test",
        )


def test_r5_policy_hard_block_unchanged(tmp_path):
    pe = PolicyEngine(tmp_path)
    d = pe.authorize(ActionRequest(action="danger", risk=RiskLevel.R5))
    assert d.status == DecisionStatus.BLOCKED


def test_consume_when_execution_starts(card_store):
    _mk_card(card_store, "TASK-CONS001")
    card_store.approve_card("TASK-CONS001", approver="quanpt1")
    assert card_store.consume_if_execution_started("TASK-CONS001") is True
    # consumed -> cannot consume again
    assert card_store.consume_if_execution_started("TASK-CONS001") is False


def test_revoke_blocks_execution(card_store):
    _mk_card(card_store, "TASK-REV0001")
    card_store.approve_card("TASK-REV0001", approver="quanpt1")
    conn = sqlite3.connect(str(card_store.db_path))
    approval_id = conn.execute(
        "SELECT approval_id FROM approvals WHERE request_id='TASK-REV0001'"
    ).fetchone()[0]
    conn.close()
    card_store._gate.revoke_approval(approval_id, reason="Thu hồi theo yêu cầu")
    req = card_store._gate.get_request("TASK-REV0001")
    ok, why = card_store._gate.evaluate_approval(approval_id, req)
    assert ok is False
    assert "revoked" in why.lower()
