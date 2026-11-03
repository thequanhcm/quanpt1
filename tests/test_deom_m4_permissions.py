"""DEOM M4 — Tests: ApprovalCardService + PermissionResolver.

Bao phủ nghiệm thu M1 doc 4/4 (§6):
  self-approval BLOCKED, agent escalation BLOCKED, token/card 1 lần,
  hết hạn fail-closed, R5 hard-block, R4 không card → APPROVAL_REQUIRED,
  card hợp lệ → ALLOW_WITH_NOTICE, approve:action chỉ owner.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from quan_ai_brain.governance.approval_service import (
    OWNER_ID,
    ApprovalCardError,
    ApprovalCardService,
)
from quan_ai_brain.governance.permission_resolver import PermissionResolver


@pytest.fixture()
def svc(tmp_path):
    return ApprovalCardService(tmp_path / "approval_v2.db")


@pytest.fixture()
def resolver(tmp_path, svc):
    return PermissionResolver(workspace=tmp_path, approval_service=svc)


def _mk_card(svc: ApprovalCardService, **kw):
    base = dict(
        task_id="task-1",
        action_summary="test action",
        risk_level="R4",
        requested_by="tony",
        scope=["deploy:staging"],
        evidence_bundle=["evidence://unit-test"],
    )
    base.update(kw)
    return svc.create_card(**base)


# ===========================================================================
# ApprovalCardService
# ===========================================================================
class TestCardLifecycle:
    def test_create_r4_pending_with_ttl(self, svc):
        card = _mk_card(svc)
        assert card.state == "PENDING"
        assert card.risk_level == "R4"
        exp = datetime.fromisoformat(card.expires_at_utc)
        assert exp > datetime.now(timezone.utc) + timedelta(hours=23)

    def test_create_r5_never(self, svc):
        with pytest.raises(ApprovalCardError, match="R5"):
            _mk_card(svc, risk_level="R5")

    def test_create_lower_risk_rejected(self, svc):
        with pytest.raises(ApprovalCardError):
            _mk_card(svc, risk_level="R2")

    def test_empty_summary_rejected(self, svc):
        with pytest.raises(ApprovalCardError):
            _mk_card(svc, action_summary="  ")


class TestApprovalSeparation:
    def test_self_approval_blocked(self, svc):
        card = _mk_card(svc, requested_by="tony")
        with pytest.raises(ApprovalCardError, match="self-approval"):
            svc.approve(card.approval_id, decided_by="tony", approval_evidence="evidence://try")
        assert svc.get_card(card.approval_id).state == "PENDING"

    def test_agent_escalation_blocked(self, svc):
        card = _mk_card(svc, requested_by="tony")
        with pytest.raises(ApprovalCardError, match="only"):
            svc.approve(card.approval_id, decided_by="agent-x", approval_evidence="evidence://try")
        assert svc.get_card(card.approval_id).state == "PENDING"

    def test_owner_approval_succeeds(self, svc):
        card = _mk_card(svc, requested_by="tony")
        ok = svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://ok-code")
        assert ok.state == "APPROVED"
        assert ok.decided_by == OWNER_ID

    def test_owner_direct_task_owner_is_requestor_and_decider(self, svc):
        # Task do owner giao trực tiếp: requested_by=owner, decided_by=owner
        # → đây là owner phê duyệt lệnh của CHÍNH MÌNH (actor=owner), không phải
        # TONY tự duyệt — hợp lệ theo M1 §4 (self-approval chỉ chặn requestor≠decider
        # khi requestor là tony/agent).
        card = _mk_card(svc, requested_by="quanpt1")
        ok = svc.approve(card.approval_id, decided_by="quanpt1", approval_evidence="dm://owner-direct")
        assert ok.state == "APPROVED"

    def test_approval_evidence_required(self, svc):
        card = _mk_card(svc)
        with pytest.raises(ApprovalCardError, match="evidence"):
            svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="")

    def test_reject_owner_only(self, svc):
        card = _mk_card(svc)
        with pytest.raises(ApprovalCardError):
            svc.reject(card.approval_id, decided_by="tony")
        ok = svc.reject(card.approval_id, decided_by=OWNER_ID, reason="not now")
        assert ok.state == "REJECTED"


class TestOneTimeConsumption:
    def test_consume_once_only(self, svc):
        card = _mk_card(svc)
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://ok")
        svc.consume(card.approval_id, actor="test")
        with pytest.raises(ApprovalCardError, match="one-time"):
            svc.consume(card.approval_id, actor="test-again")

    def test_consume_pending_rejected(self, svc):
        card = _mk_card(svc)
        with pytest.raises(ApprovalCardError, match="PENDING"):
            svc.consume(card.approval_id)

    def test_consume_rejected_card_rejected(self, svc):
        card = _mk_card(svc)
        svc.reject(card.approval_id, decided_by=OWNER_ID, reason="no")
        with pytest.raises(ApprovalCardError):
            svc.consume(card.approval_id)


class TestExpiryFailClosed:
    def test_approve_after_expiry_becomes_expired(self, svc):
        card = _mk_card(svc, ttl_hours=1)
        # lùi expires_at_utc về quá khứ bằng SQL trực tiếp (mô phỏng thời gian trôi)
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        svc._conn.execute(
            "UPDATE approval_cards_v2 SET expires_at_utc = ? WHERE approval_id = ?",
            (past, card.approval_id),
        )
        svc._conn.commit()
        with pytest.raises(ApprovalCardError, match="expired"):
            svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://late")
        assert svc.get_card(card.approval_id).state == "EXPIRED"

    def test_consume_after_expiry_rejected(self, svc):
        card = _mk_card(svc, ttl_hours=1)
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://ok")
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        svc._conn.execute(
            "UPDATE approval_cards_v2 SET expires_at_utc = ? WHERE approval_id = ?",
            (past, card.approval_id),
        )
        svc._conn.commit()
        with pytest.raises(ApprovalCardError, match="expired"):
            svc.consume(card.approval_id)
        assert svc.get_card(card.approval_id).state == "EXPIRED"

    def test_expire_overdue_sweep(self, svc):
        c1 = _mk_card(svc)
        c2 = _mk_card(svc)
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        svc._conn.execute(
            "UPDATE approval_cards_v2 SET expires_at_utc = ? WHERE approval_id = ?",
            (past, c1.approval_id),
        )
        svc._conn.commit()
        expired = svc.expire_overdue()
        assert expired == [c1.approval_id]
        assert svc.get_card(c1.approval_id).state == "EXPIRED"
        assert svc.get_card(c2.approval_id).state == "PENDING"

    def test_corrupt_expiry_treated_expired(self, svc):
        card = _mk_card(svc)
        svc._conn.execute(
            "UPDATE approval_cards_v2 SET expires_at_utc = 'not-a-date' WHERE approval_id = ?",
            (card.approval_id,),
        )
        svc._conn.commit()
        with pytest.raises(ApprovalCardError):
            svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://x")


class TestEvents:
    def test_event_trail_complete(self, svc):
        card = _mk_card(svc, requested_by="tony")
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://ok-123")
        svc.consume(card.approval_id)
        evs = [e["event"] for e in svc.events(card.approval_id)]
        assert evs == ["CREATED", "APPROVED", "CONSUMED"]


# ===========================================================================
# PermissionResolver
# ===========================================================================
class TestResolverLowRisk:
    def test_p1_read_allow(self, resolver):
        d = resolver.resolve(permission_id="P1")
        assert d.status == "ALLOW"
        assert d.allowed

    def test_p2_memory_read_allow(self, resolver):
        assert resolver.resolve(permission_id="P2").status == "ALLOW"

    def test_p3_memory_write_r2_allow(self, resolver):
        d = resolver.resolve(permission_id="P3", target_path="notes/test.md")
        assert d.status == "ALLOW"

    def test_r2_outside_workspace_blocked(self, resolver):
        d = resolver.resolve(permission_id="P3", target_path="../outside.md")
        assert d.status == "BLOCKED"


class TestResolverR3R4:
    def test_p7_messages_send_r3_requires_confirmation(self, resolver):
        d = resolver.resolve(permission_id="P7")
        assert d.status == "APPROVAL_REQUIRED"

    def test_p5_computer_act_r4_no_card(self, resolver):
        d = resolver.resolve(permission_id="P5", task_id="t-9")
        assert d.status == "APPROVAL_REQUIRED"
        assert "no approval card" in d.reason

    def test_p5_with_approved_card_allow_with_notice(self, resolver, svc):
        card = _mk_card(svc, requested_by="tony")
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://ok-555")
        d = resolver.resolve(permission_id="P5", task_id=card.task_id, approval_id=card.approval_id)
        assert d.status == "ALLOW_WITH_NOTICE"
        assert d.consumed is True
        assert d.approval_id == card.approval_id

    def test_card_reuse_second_time_blocked(self, resolver, svc):
        card = _mk_card(svc)
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://ok")
        first = resolver.resolve(permission_id="P5", approval_id=card.approval_id)
        assert first.allowed
        second = resolver.resolve(permission_id="P5", approval_id=card.approval_id)
        assert second.status == "BLOCKED"
        assert "consumed" in second.reason

    def test_pending_card_not_enough(self, resolver, svc):
        card = _mk_card(svc)  # PENDING, owner chưa duyệt
        d = resolver.resolve(permission_id="P5", approval_id=card.approval_id)
        assert d.status == "APPROVAL_REQUIRED"

    def test_card_of_other_subject_blocked(self, resolver, svc):
        card = _mk_card(svc, requested_by="agent-x")
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://ok")
        d = resolver.resolve(permission_id="P5", subject_id="tony", approval_id=card.approval_id)
        assert d.status == "BLOCKED"

    def test_ghost_card_blocked(self, resolver):
        d = resolver.resolve(permission_id="P5", approval_id="appr_does_not_exist")
        assert d.status == "BLOCKED"


class TestOwnerInvariants:
    def test_p13_approve_action_owner_only_allow_path(self, resolver):
        d = resolver.resolve(permission_id="P13", subject_id="quanpt1")
        # R5 policy BLOCK trước — bất biến kép (policy + resolver)
        assert d.status == "BLOCKED"

    def test_p13_approve_action_tony_blocked(self, resolver):
        d = resolver.resolve(permission_id="P13", subject_id="tony")
        assert d.status == "BLOCKED"

    def test_unknown_subject_blocked_on_r4(self, resolver):
        d = resolver.resolve(permission_id="P5", subject_id="intruder")
        assert d.status == "BLOCKED"

    def test_unknown_permission_blocked(self, resolver):
        d = resolver.resolve(permission_id="P99")
        assert d.status == "BLOCKED"


class TestAbacContext:
    def test_abac_deny_policy_blocks_even_low_risk(self, tmp_path, svc):
        from quan_ai_brain.security.rbac import ABACEngine, ABACPolicy

        abac = ABACEngine()
        abac.add_policy(
            ABACPolicy(
                name="quiet-hours-deny",
                required_attributes={"environment.quiet_hours": True},
                effect="deny",
            )
        )
        r = PermissionResolver(workspace=tmp_path, approval_service=svc, abac_engine=abac)
        d = r.resolve(permission_id="P1", environment_attrs={"quiet_hours": True})
        assert d.status == "BLOCKED"
        assert "quiet-hours-deny" in d.reason

    def test_abac_no_match_allows_flow(self, tmp_path, svc):
        from quan_ai_brain.security.rbac import ABACEngine, ABACPolicy

        abac = ABACEngine()
        abac.add_policy(
            ABACPolicy(name="quiet-hours-deny", required_attributes={"environment.quiet_hours": True}, effect="deny")
        )
        r = PermissionResolver(workspace=tmp_path, approval_service=svc, abac_engine=abac)
        d = r.resolve(permission_id="P1", environment_attrs={"quiet_hours": False})
        assert d.status == "ALLOW"


class TestLayersTrace:
    def test_layers_recorded(self, resolver, svc):
        card = _mk_card(svc)
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://ok")
        d = resolver.resolve(permission_id="P5", approval_id=card.approval_id)
        names = [l["layer"] for l in d.layers]
        assert "policy_engine" in names and "rbac" in names and "approval" in names
