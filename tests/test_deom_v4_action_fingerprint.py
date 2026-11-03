"""DEOM V4 G-A — Action Fingerprint (§6.2): binding nội dung hành động đã duyệt.

Bao phủ: compute_action_fingerprint determinstic (đổi scope/thứ tự/whitespace),
card luôn có fingerprint khi create, consume khớp → OK, consume lệch → chặn +
card còn nguyên, card legacy không fingerprint → fail-closed khi consume kèm fp,
consume không kèm fp (workflow cũ) vẫn chạy (backward compat), resolver 4 lớp
đối chiếu fingerprint trước khi consume.
"""
from __future__ import annotations

import pytest

from quan_ai_brain.governance.approval_service import (
    OWNER_ID,
    ApprovalCardError,
    ApprovalCardService,
    compute_action_fingerprint,
)
from quan_ai_brain.governance.permission_resolver import PermissionResolver


@pytest.fixture()
def svc(tmp_path):
    return ApprovalCardService(tmp_path / "approval_fp.db")


class TestComputeActionFingerprint:
    def test_deterministic_same_inputs(self):
        a = compute_action_fingerprint(action_summary="cài đặt X", scope=["a", "b"], params={"k": 1})
        b = compute_action_fingerprint(action_summary="cài đặt X", scope=["a", "b"], params={"k": 1})
        assert a == b and len(a) == 64

    def test_changed_summary_changes_fp(self):
        a = compute_action_fingerprint(action_summary="cài đặt X")
        b = compute_action_fingerprint(action_summary="cài đặt Y")
        assert a != b

    def test_scope_order_and_whitespace_irrelevant(self):
        a = compute_action_fingerprint(action_summary="gỡ  app", scope=["b", "a"])
        b = compute_action_fingerprint(action_summary="gỡ app", scope=["a", "b"])
        assert a == b  # normalize whitespace + sort scope

    def test_changed_params_changes_fp(self):
        a = compute_action_fingerprint(action_summary="chạy", params={"path": "D:/A"})
        b = compute_action_fingerprint(action_summary="chạy", params={"path": "D:/B"})
        assert a != b


class TestCardLifecycleWithFingerprint:
    def test_create_card_auto_binds_fingerprint(self, svc):
        card = svc.create_card(
            task_id="t1", action_summary="cài X", scope=["ws"], action_params={"v": 2}, requested_by="tony"
        )
        assert card.action_fingerprint == compute_action_fingerprint(
            action_summary="cài X", scope=["ws"], params={"v": 2}
        )

    def test_consume_with_matching_fp_ok(self, svc):
        card = svc.create_card(task_id="t1", action_summary="cài X", requested_by="tony")
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://1")
        done = svc.consume(card.approval_id, actor="resolver", action_fingerprint=card.action_fingerprint)
        assert done.consumed_at_utc is not None

    def test_consume_with_wrong_fp_blocked_card_intact(self, svc):
        card = svc.create_card(task_id="t2", action_summary="xoá log", requested_by="tony")
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://2")
        with pytest.raises(ApprovalCardError, match="fingerprint mismatch"):
            svc.consume(card.approval_id, actor="resolver", action_fingerprint="f" * 64)
        intact = svc.get_card(card.approval_id)
        assert intact.consumed_at_utc is None and intact.state == "APPROVED"

    def test_consume_without_fp_backward_compatible(self, svc):
        card = svc.create_card(task_id="t3", action_summary="đọc file", requested_by="tony")
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://3")
        done = svc.consume(card.approval_id, actor="plan_orchestrator")  # không kèm fp
        assert done.consumed_at_utc is not None

    def test_legacy_card_without_fp_fails_closed_on_bound_consume(self, svc, tmp_path):
        """Card tạo trước khi có fingerprint (cột NULL) → consume kèm fp bị chặn."""
        import sqlite3

        db = tmp_path / "approval_fp.db"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO approval_cards_v2 (approval_id, task_id, action_summary, risk_level,"
            " requested_by, scope_json, evidence_bundle_json, created_at_utc, expires_at_utc, state)"
            " VALUES ('appr_legacy','t9','legacy','R4','tony','[]','[]',"
            "'2026-11-01T00:00:00+00:00','2099-01-01T00:00:00+00:00','APPROVED')"
        )
        conn.commit()
        conn.close()
        with pytest.raises(ApprovalCardError, match="no action_fingerprint binding"):
            svc.consume("appr_legacy", actor="resolver", action_fingerprint="a" * 64)


class TestResolverFingerprintGate:
    def _resolver(self, svc):
        return PermissionResolver(approval_service=svc)

    def test_resolver_correct_fp_allows(self, svc):
        r = self._resolver(svc)
        card = svc.create_card(task_id="t1", action_summary="cài X", scope=["ws"], requested_by="tony")
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://r1")
        decision = r.resolve(
            permission_id="P5",
            task_id="t1",
            subject_id="tony",
            approval_id=card.approval_id,
            action_fingerprint=card.action_fingerprint,
        )
        assert decision.status == "ALLOW_WITH_NOTICE"

    def test_resolver_wrong_fp_blocks(self, svc):
        r = self._resolver(svc)
        card = svc.create_card(task_id="t2", action_summary="cài X", scope=["ws"], requested_by="tony")
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://r2")
        decision = r.resolve(
            permission_id="P5",
            task_id="t2",
            subject_id="tony",
            approval_id=card.approval_id,
            action_fingerprint="e" * 64,
        )
        assert decision.status == "BLOCKED"
        intact = svc.get_card(card.approval_id)
        assert intact.consumed_at_utc is None
