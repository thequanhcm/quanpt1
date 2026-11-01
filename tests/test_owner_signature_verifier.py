"""Unit tests for OwnerSignatureVerifier and cryptographic trust anchor validation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.tools.signature import (
    OwnerSignatureEvidence,
    OwnerSignatureVerifier,
    SignatureAlgorithm,
    SignatureVerificationOutcome,
    TrustAnchor,
    create_test_signature,
)


@pytest.fixture
def trust_anchor() -> TrustAnchor:
    return TrustAnchor(
        key_id="key_owner_primary",
        signer_identity="owner_quan",
        algorithm=SignatureAlgorithm.HMAC_SHA256,
        public_key_or_secret=b"test_secret_key_32_bytes_minimum",
        valid_from="2026-01-01T00:00:00Z",
        valid_to="2027-01-01T00:00:00Z",
    )


@pytest.fixture
def valid_evidence(trust_anchor: TrustAnchor) -> OwnerSignatureEvidence:
    now = datetime.now(timezone.utc)
    exp = (now + timedelta(minutes=10)).isoformat()
    canonical = "app_123|file_write_new|write|fp_abc|nonce_001|" + exp
    sig = create_test_signature(trust_anchor, canonical)
    return OwnerSignatureEvidence(
        signer_identity="owner_quan",
        key_id="key_owner_primary",
        algorithm=SignatureAlgorithm.HMAC_SHA256,
        signature_hex=sig,
        canonical_payload=canonical,
        action_fingerprint="fp_abc",
        nonce="nonce_001",
        expires_at=exp,
        approval_id="app_123",
    )


def test_missing_trust_anchor_fails_closed(valid_evidence: OwnerSignatureEvidence):
    """Verify default-deny when verifier has no trust anchors."""
    verifier = OwnerSignatureVerifier(trust_anchors={})
    ok, outcome, msg = verifier.verify_signature(valid_evidence, current_fingerprint="fp_abc")
    assert ok is False
    assert outcome == SignatureVerificationOutcome.DENIED_NO_TRUST_ANCHOR
    assert "No trust anchor found" in msg


def test_untrusted_signer_rejected(trust_anchor: TrustAnchor, valid_evidence: OwnerSignatureEvidence):
    """Verify signer identity mismatch is rejected."""
    verifier = OwnerSignatureVerifier(trust_anchors={trust_anchor.key_id: trust_anchor})
    # Impersonate different signer
    valid_evidence.signer_identity = "imposter_user"
    ok, outcome, msg = verifier.verify_signature(valid_evidence, current_fingerprint="fp_abc")
    assert ok is False
    assert outcome == SignatureVerificationOutcome.DENIED_UNTRUSTED_SIGNER
    assert "Signer identity mismatch" in msg


def test_signature_tampering_rejected(trust_anchor: TrustAnchor, valid_evidence: OwnerSignatureEvidence):
    """Verify corrupted signature is rejected."""
    verifier = OwnerSignatureVerifier(trust_anchors={trust_anchor.key_id: trust_anchor})
    valid_evidence.signature_hex = "0" * 64
    ok, outcome, msg = verifier.verify_signature(valid_evidence, current_fingerprint="fp_abc")
    assert ok is False
    assert outcome == SignatureVerificationOutcome.DENIED_SIGNATURE_MISMATCH
    assert "signature mismatch" in msg


def test_action_fingerprint_mismatch_rejected(trust_anchor: TrustAnchor, valid_evidence: OwnerSignatureEvidence):
    """Verify that altered action parameters (fingerprint change) are rejected."""
    verifier = OwnerSignatureVerifier(trust_anchors={trust_anchor.key_id: trust_anchor})
    ok, outcome, msg = verifier.verify_signature(valid_evidence, current_fingerprint="fp_tampered_parameters")
    assert ok is False
    assert outcome == SignatureVerificationOutcome.DENIED_FINGERPRINT_MISMATCH
    assert "Action fingerprint mismatch" in msg


def test_expired_signature_rejected(trust_anchor: TrustAnchor, valid_evidence: OwnerSignatureEvidence):
    """Verify that expired signatures fail validation."""
    verifier = OwnerSignatureVerifier(trust_anchors={trust_anchor.key_id: trust_anchor})
    expired_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    valid_evidence.expires_at = expired_time
    ok, outcome, msg = verifier.verify_signature(valid_evidence, current_fingerprint="fp_abc")
    assert ok is False
    assert outcome == SignatureVerificationOutcome.DENIED_EXPIRED
    assert "expired" in msg


def test_replay_nonce_rejected(trust_anchor: TrustAnchor, valid_evidence: OwnerSignatureEvidence):
    """Verify consumed nonces cannot be re-used."""
    verifier = OwnerSignatureVerifier(trust_anchors={trust_anchor.key_id: trust_anchor})

    # First verification passes
    ok1, outcome1, _ = verifier.verify_signature(valid_evidence, current_fingerprint="fp_abc")
    assert ok1 is True
    assert outcome1 == SignatureVerificationOutcome.VERIFIED

    # Consume nonce
    consumed = verifier.consume_signature_nonce(valid_evidence)
    assert consumed is True

    # Replay verification fails
    ok2, outcome2, msg2 = verifier.verify_signature(valid_evidence, current_fingerprint="fp_abc")
    assert ok2 is False
    assert outcome2 == SignatureVerificationOutcome.DENIED_REPLAY_NONCE
    assert "already been consumed" in msg2


def test_revoked_key_anchor_rejected(trust_anchor: TrustAnchor, valid_evidence: OwnerSignatureEvidence):
    """Verify revoked trust anchor immediately blocks verification."""
    verifier = OwnerSignatureVerifier(trust_anchors={trust_anchor.key_id: trust_anchor})
    verifier.revoke_trust_anchor(trust_anchor.key_id, reason="Owner revoked compromised key")

    ok, outcome, msg = verifier.verify_signature(valid_evidence, current_fingerprint="fp_abc")
    assert ok is False
    assert outcome == SignatureVerificationOutcome.DENIED_REVOKED
    assert "revoked" in msg


def test_governance_store_revocation_enforced(
    tmp_path: Path,
    trust_anchor: TrustAnchor,
    valid_evidence: OwnerSignatureEvidence,
):
    """Verify persistent revocation in GovernanceStateStore blocks signature verification."""
    from quan_ai_brain.governance.policy import RiskLevel
    from quan_ai_brain.tools.approval import ApprovalStatus, OwnerApproval

    db_path = tmp_path / "gov.db"
    store = GovernanceStateStore(db_path, workspace=tmp_path)
    approval = OwnerApproval(
        approval_id=valid_evidence.approval_id,
        request_id="req_123",
        approver="owner_quan",
        tool_id="file_write_new",
        action="write",
        params={},
        resource_scope="workspace",
        risk_level=RiskLevel.R2,
        fingerprint=valid_evidence.action_fingerprint,
        granted_at=datetime.now(timezone.utc).isoformat(),
        expires_at=valid_evidence.expires_at,
        status=ApprovalStatus.APPROVED,
    )
    store.save_approval(approval)
    store.revoke_approval(valid_evidence.approval_id, reason="Owner emergency revoke")

    verifier = OwnerSignatureVerifier(trust_anchors={trust_anchor.key_id: trust_anchor}, store=store)
    ok, outcome, msg = verifier.verify_signature(valid_evidence, current_fingerprint="fp_abc")
    assert ok is False
    assert outcome == SignatureVerificationOutcome.DENIED_REVOKED
    assert "revoked in persistent store" in msg

    store.close()


def test_corrupted_governance_store_fails_closed(
    tmp_path: Path,
    trust_anchor: TrustAnchor,
    valid_evidence: OwnerSignatureEvidence,
):
    """Verify corrupted database triggers fail-closed denial."""
    bad_db = tmp_path / "bad.db"
    bad_db.write_text("CORRUPTED_NON_SQLITE_DATA", encoding="utf-8")

    class FakeCorruptStore:
        def verify_integrity(self):
            from quan_ai_brain.governance.state_store import GovernanceStateCorruptError
            raise GovernanceStateCorruptError("Database file corrupted")

    verifier = OwnerSignatureVerifier(
        trust_anchors={trust_anchor.key_id: trust_anchor},
        store=FakeCorruptStore(),
    )
    ok, outcome, msg = verifier.verify_signature(valid_evidence, current_fingerprint="fp_abc")
    assert ok is False
    assert outcome == SignatureVerificationOutcome.DENIED_GOVERNANCE_CORRUPT
    assert "Governance state store corrupted" in msg


def test_asymmetric_test_fixture_signature_verification():
    """Verify deterministic asymmetric test fixture signature verification."""
    anchor = TrustAnchor(
        key_id="ed25519_fixture_key",
        signer_identity="owner_quan",
        algorithm=SignatureAlgorithm.ED25519_TEST_FIXTURE,
        public_key_or_secret=b"ed25519_test_public_key_32_bytes",
        valid_from="2026-01-01T00:00:00Z",
        valid_to="2027-01-01T00:00:00Z",
    )
    canonical = "payload_canonical_test"
    sig = create_test_signature(anchor, canonical)
    exp = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    evidence = OwnerSignatureEvidence(
        signer_identity="owner_quan",
        key_id="ed25519_fixture_key",
        algorithm=SignatureAlgorithm.ED25519_TEST_FIXTURE,
        signature_hex=sig,
        canonical_payload=canonical,
        action_fingerprint="fp_asym",
        nonce="nonce_asym_1",
        expires_at=exp,
    )

    verifier = OwnerSignatureVerifier(trust_anchors={anchor.key_id: anchor})
    ok, outcome, _ = verifier.verify_signature(evidence, current_fingerprint="fp_asym")
    assert ok is True
    assert outcome == SignatureVerificationOutcome.VERIFIED


def test_r4_dual_factor_required_and_r5_hard_blocked():
    """Verify that R4 strictly requires Dual-Factor and R5 is unconditionally hard-blocked."""
    from quan_ai_brain.governance.policy import RiskLevel
    from quan_ai_brain.tools.verifier import (
        AuthenticatedApprovalVerifier,
        SignedApproval,
        VerificationMethod,
        VerificationOutcome,
    )

    secret_key = "test_owner_secret_key"
    verifier = AuthenticatedApprovalVerifier(
        owner_secret_key=secret_key,
        trusted_phone="+84987654321",
    )

    now = datetime.now(timezone.utc)
    exp = (now + timedelta(minutes=5)).isoformat()

    # R4 with SECRET_CODE only -> rejected (dual-factor required)
    r4_app = SignedApproval(
        approval_id="app_r4_test",
        tool_id="system_reconfigure",
        action="update_config",
        params={"target": "system"},
        resource_scope="workspace",
        risk_level=RiskLevel.R4,
        fingerprint="fp_r4",
        nonce="nonce_r4_1",
        expires_at=exp,
        signer_identity="owner_quan",
        verification_method=VerificationMethod.SECRET_CODE,
    )
    r4_app.signature = verifier.sign_approval(r4_app)

    ok_r4, outcome_r4, msg_r4 = verifier.verify_approval(
        r4_app,
        current_fingerprint="fp_r4",
        current_risk=RiskLevel.R4,
    )
    assert ok_r4 is False
    assert outcome_r4 == VerificationOutcome.DENIED_R4_DUAL_FACTOR_REQUIRED
    assert "Dual-Factor" in msg_r4

    # R5 with Dual-Factor -> unconditionally blocked
    r5_app = SignedApproval(
        approval_id="app_r5_test",
        tool_id="drop_database",
        action="destroy_all",
        params={},
        resource_scope="workspace",
        risk_level=RiskLevel.R5,
        fingerprint="fp_r5",
        nonce="nonce_r5_1",
        expires_at=exp,
        signer_identity="owner_quan",
        verification_method=VerificationMethod.DUAL_FACTOR,
    )
    r5_app.signature = verifier.sign_approval(r5_app)

    ok_r5, outcome_r5, msg_r5 = verifier.verify_approval(
        r5_app,
        current_fingerprint="fp_r5",
        current_risk=RiskLevel.R5,
    )
    assert ok_r5 is False
    assert outcome_r5 == VerificationOutcome.BLOCKED_R5_PROHIBITED
    assert "prohibited" in msg_r5

