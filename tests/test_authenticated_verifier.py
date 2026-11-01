"""Unit tests for AuthenticatedApprovalVerifier (Sprint 4).

Verifies:
- Channel 1: Owner Private Secret Code (HMAC-SHA256 signature verification).
- Channel 2: Phone SMS OTP challenge and verification.
- Dual-Factor mode (Mandatory for R4).
- Anti-replay (single-use consumption and nonce tracking).
- Parameter & scope fingerprint tampering protection.
- Expiration and revocation handling.
- Default-deny when trust anchors are unconfigured.
- R5 hard-block unconditional enforcement.
- STOP/FREEZE emergency state enforcement.
"""
from datetime import datetime, timedelta, timezone
import pytest

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.tools.approval import compute_action_fingerprint
from quan_ai_brain.tools.sandbox import SystemState
from quan_ai_brain.tools.verifier import (
    AuthenticatedApprovalVerifier,
    SignedApproval,
    VerificationMethod,
    VerificationOutcome,
)


@pytest.fixture
def test_verifier():
    """Verifier configured with test mock secret key and test phone."""
    return AuthenticatedApprovalVerifier(
        owner_secret_key="test_owner_secret_passcode_2026",
        trusted_phone="+84901234567",
        trusted_signers={"owner:quanpt1"},
    )


def _make_sample_approval(
    tool_id: str = "file_read",
    action: str = "read",
    params: dict | None = None,
    risk_level: RiskLevel = RiskLevel.R0,
    method: VerificationMethod = VerificationMethod.SECRET_CODE,
    ttl_hours: int = 1,
) -> SignedApproval:
    p = params or {"file_path": "README.md"}
    fp = compute_action_fingerprint(tool_id, action, p, "workspace", int(risk_level))
    exp = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
    return SignedApproval(
        approval_id="app-test-001",
        tool_id=tool_id,
        action=action,
        params=p,
        resource_scope="workspace",
        risk_level=risk_level,
        fingerprint=fp,
        nonce="nonce-abc-123",
        expires_at=exp,
        signer_identity="owner:quanpt1",
        verification_method=method,
    )


# -----------------------------------------------------------------------------
# Channel 1: Owner Private Secret Code (HMAC-SHA256 Signature)
# -----------------------------------------------------------------------------

def test_valid_signature_verified(test_verifier):
    approval = _make_sample_approval()
    # Sign using the verifier's configured test secret
    approval.signature = test_verifier.sign_approval(approval)

    ok, outcome, msg = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
    )
    assert ok is True
    assert outcome == VerificationOutcome.VERIFIED
    assert "successfully" in msg


def test_invalid_signature_rejected(test_verifier):
    approval = _make_sample_approval()
    approval.signature = "a" * 64  # Fake invalid signature

    ok, outcome, msg = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
    )
    assert ok is False
    assert outcome == VerificationOutcome.DENIED_SIGNATURE_MISMATCH
    assert "mismatch" in msg.lower()


def test_signature_tampered_payload_rejected(test_verifier):
    approval = _make_sample_approval()
    approval.signature = test_verifier.sign_approval(approval)

    # Tampered action fingerprint (e.g., file path changed from README.md to .env)
    altered_fp = compute_action_fingerprint(
        approval.tool_id, approval.action, {"file_path": ".env"}, "workspace", int(approval.risk_level)
    )

    ok, outcome, msg = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=altered_fp,
        current_risk=approval.risk_level,
    )
    assert ok is False
    assert outcome == VerificationOutcome.DENIED_FINGERPRINT_MISMATCH
    assert "fingerprint mismatch" in msg.lower()


# -----------------------------------------------------------------------------
# Channel 2: Phone SMS OTP Verification
# -----------------------------------------------------------------------------

def test_valid_sms_otp_verified(test_verifier):
    approval = _make_sample_approval(method=VerificationMethod.SMS_OTP)
    challenge, raw_code = test_verifier.create_sms_challenge(
        action_fingerprint=approval.fingerprint,
        phone_number="+84901234567",
        ttl_seconds=180,
    )
    approval.otp_code = raw_code

    ok, outcome, msg = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
        sms_challenge=challenge,
    )
    assert ok is True
    assert outcome == VerificationOutcome.VERIFIED
    assert challenge.consumed is True


def test_invalid_sms_otp_rejected_with_attempts_count(test_verifier):
    approval = _make_sample_approval(method=VerificationMethod.SMS_OTP)
    challenge, _ = test_verifier.create_sms_challenge(
        action_fingerprint=approval.fingerprint,
        phone_number="+84901234567",
    )
    approval.otp_code = "000000"  # Wrong code

    # Attempt 1
    ok1, outcome1, _ = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
        sms_challenge=challenge,
    )
    assert ok1 is False
    assert outcome1 == VerificationOutcome.DENIED_INVALID_OTP
    assert challenge.attempts == 1

    # Attempt 2
    ok2, outcome2, _ = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
        sms_challenge=challenge,
    )
    assert ok2 is False
    assert challenge.attempts == 2

    # Attempt 3: Exhaustion
    ok3, outcome3, _ = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
        sms_challenge=challenge,
    )
    assert ok3 is False
    assert challenge.attempts == 3

    # Attempt 4: Blocked due to attempts exceeded
    ok4, outcome4, msg4 = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
        sms_challenge=challenge,
    )
    assert ok4 is False
    assert outcome4 == VerificationOutcome.DENIED_ATTEMPTS_EXCEEDED
    assert "attempts exceeded" in msg4.lower()


# -----------------------------------------------------------------------------
# Dual-Factor Verification (Mandatory for R4)
# -----------------------------------------------------------------------------

def test_dual_factor_both_valid_verified(test_verifier):
    approval = _make_sample_approval(
        tool_id="system_config_change",
        action="write",
        risk_level=RiskLevel.R4,
        method=VerificationMethod.DUAL_FACTOR,
    )
    approval.signature = test_verifier.sign_approval(approval)
    challenge, raw_code = test_verifier.create_sms_challenge(
        action_fingerprint=approval.fingerprint,
        phone_number="+84901234567",
    )
    approval.otp_code = raw_code

    ok, outcome, msg = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
        sms_challenge=challenge,
    )
    assert ok is True
    assert outcome == VerificationOutcome.VERIFIED


def test_r4_fails_without_dual_factor(test_verifier):
    # R4 with only secret code signature (missing SMS OTP)
    approval = _make_sample_approval(
        tool_id="system_config_change",
        action="write",
        risk_level=RiskLevel.R4,
        method=VerificationMethod.SECRET_CODE,
    )
    approval.signature = test_verifier.sign_approval(approval)

    ok, outcome, msg = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
    )
    assert ok is False
    assert outcome == VerificationOutcome.DENIED_R4_DUAL_FACTOR_REQUIRED
    assert "dual-factor" in msg.lower()


# -----------------------------------------------------------------------------
# Anti-Replay & Expiration & Revocation
# -----------------------------------------------------------------------------

def test_consumed_approval_cannot_be_replayed(test_verifier):
    approval = _make_sample_approval()
    approval.signature = test_verifier.sign_approval(approval)

    # First verification: success
    ok1, _, _ = test_verifier.verify_approval(approval, approval.fingerprint, approval.risk_level)
    assert ok1 is True

    # Consume token
    consumed = test_verifier.consume_approval(approval)
    assert consumed is True
    assert approval.consumed is True

    # Replay attempt: rejected!
    ok2, outcome2, msg2 = test_verifier.verify_approval(approval, approval.fingerprint, approval.risk_level)
    assert ok2 is False
    assert outcome2 == VerificationOutcome.DENIED_CONSUMED
    assert "already been consumed" in msg2.lower()


def test_expired_approval_rejected(test_verifier):
    # Expired 1 hour ago
    approval = _make_sample_approval(ttl_hours=-1)
    approval.signature = test_verifier.sign_approval(approval)

    ok, outcome, msg = test_verifier.verify_approval(approval, approval.fingerprint, approval.risk_level)
    assert ok is False
    assert outcome == VerificationOutcome.DENIED_EXPIRED
    assert "expired" in msg.lower()


def test_revoked_approval_rejected(test_verifier):
    approval = _make_sample_approval()
    approval.signature = test_verifier.sign_approval(approval)

    # Revoke approval
    test_verifier.revoke_approval(approval.approval_id, reason="Owner revoked token")

    ok, outcome, msg = test_verifier.verify_approval(approval, approval.fingerprint, approval.risk_level)
    assert ok is False
    assert outcome == VerificationOutcome.DENIED_REVOKED
    assert "revoked" in msg.lower()


# -----------------------------------------------------------------------------
# Core Security Boundaries: Untrusted Signer, Unconfigured Trust Anchor, R5, Emergency
# -----------------------------------------------------------------------------

def test_untrusted_signer_rejected(test_verifier):
    approval = _make_sample_approval()
    approval.signer_identity = "attacker:fake_admin"
    approval.signature = test_verifier.sign_approval(approval)

    ok, outcome, msg = test_verifier.verify_approval(approval, approval.fingerprint, approval.risk_level)
    assert ok is False
    assert outcome == VerificationOutcome.DENIED_UNTRUSTED_SIGNER


def test_unconfigured_trust_anchor_default_denies():
    # Verifier with NO secret key and NO phone anchor
    empty_verifier = AuthenticatedApprovalVerifier(
        owner_secret_key=None,
        trusted_phone=None,
    )
    assert not empty_verifier.has_trust_anchor

    approval = _make_sample_approval()
    approval.signature = "dummy_sig"

    ok, outcome, msg = empty_verifier.verify_approval(approval, approval.fingerprint, approval.risk_level)
    assert ok is False
    assert outcome == VerificationOutcome.DENIED_NO_TRUST_ANCHOR
    assert "trust anchor is not configured" in msg.lower()


def test_r5_unconditional_hard_block(test_verifier):
    # Even with a perfectly signed approval, R5 must be unconditionally blocked
    approval = _make_sample_approval(
        tool_id="format_hard_drive",
        action="delete",
        risk_level=RiskLevel.R5,
        method=VerificationMethod.DUAL_FACTOR,
    )
    approval.signature = test_verifier.sign_approval(approval)
    challenge, raw_code = test_verifier.create_sms_challenge(approval.fingerprint, "+84901234567")
    approval.otp_code = raw_code

    ok, outcome, msg = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=RiskLevel.R5,
        sms_challenge=challenge,
    )
    assert ok is False
    assert outcome == VerificationOutcome.BLOCKED_R5_PROHIBITED
    assert "r5 is prohibited" in msg.lower()


def test_emergency_system_state_blocks_verification(test_verifier):
    approval = _make_sample_approval()
    approval.signature = test_verifier.sign_approval(approval)

    # STOP state
    ok_stop, outcome_stop, _ = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
        system_state=SystemState.STOP,
    )
    assert ok_stop is False
    assert outcome_stop == VerificationOutcome.DENIED_SYSTEM_EMERGENCY

    # FREEZE state
    ok_freeze, outcome_freeze, _ = test_verifier.verify_approval(
        approval=approval,
        current_fingerprint=approval.fingerprint,
        current_risk=approval.risk_level,
        system_state=SystemState.FREEZE,
    )
    assert ok_freeze is False
    assert outcome_freeze == VerificationOutcome.DENIED_SYSTEM_EMERGENCY
