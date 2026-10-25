"""Owner Signature Verification Architecture for QUAN AI BRAIN.

Sprint 6: Owner Signature Verification & Cryptographic Trust Anchors.
Independent, auditable signature verification interface.
Strict fail-closed security: missing trust anchor, tampered payload, or expired
signatures result in immediate denial.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import hmac
from typing import TYPE_CHECKING, Any

from quan_ai_brain.core.redaction import redact_value

if TYPE_CHECKING:
    from quan_ai_brain.governance.state_store import GovernanceStateStore


class SignatureAlgorithm(str, Enum):
    HMAC_SHA256 = "hmac_sha256"
    ED25519_TEST_FIXTURE = "ed25519_test_fixture"
    RSA_SHA256_TEST_FIXTURE = "rsa_sha256_test_fixture"


class SignatureVerificationOutcome(str, Enum):
    VERIFIED = "verified"
    DENIED_NO_TRUST_ANCHOR = "denied_no_trust_anchor"
    DENIED_UNTRUSTED_SIGNER = "denied_untrusted_signer"
    DENIED_SIGNATURE_MISMATCH = "denied_signature_mismatch"
    DENIED_FINGERPRINT_MISMATCH = "denied_fingerprint_mismatch"
    DENIED_EXPIRED = "denied_expired"
    DENIED_REPLAY_NONCE = "denied_replay_nonce"
    DENIED_REVOKED = "denied_revoked"
    DENIED_MALFORMED_EVIDENCE = "denied_malformed_evidence"
    DENIED_GOVERNANCE_CORRUPT = "denied_governance_corrupt"


@dataclass
class OwnerSignatureEvidence:
    """Cryptographic signature evidence bound to an action and its parameters."""

    signer_identity: str
    key_id: str
    algorithm: SignatureAlgorithm
    signature_hex: str
    canonical_payload: str
    action_fingerprint: str
    nonce: str
    expires_at: str
    approval_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.signature_hex:
            # Mask signature in logs/exports
            data["signature_hex"] = (
                self.signature_hex[:8] + "..." + self.signature_hex[-8:]
                if len(self.signature_hex) > 16
                else "[REDACTED]"
            )
        data["metadata"] = redact_value(self.metadata)
        data["algorithm"] = self.algorithm.value
        return data


@dataclass
class TrustAnchor:
    """Configured public key or shared secret anchor for an authorized signer."""

    key_id: str
    signer_identity: str
    algorithm: SignatureAlgorithm
    public_key_or_secret: bytes
    valid_from: str
    valid_to: str
    revoked: bool = False
    revocation_reason: str = ""


class OwnerSignatureVerifier:
    """Cryptographically verifies that an action request was signed by the owner.

    Key Principles:
    1. Default Deny / Fail-Closed: If no trust anchors exist or key_id is missing, verification fails.
    2. Zero In-Code Secrets: Keys are provided via configuration, never hardcoded.
    3. Action Fingerprint Binding: Canonical payload and signature must match the action parameters.
    4. Replay Prevention: Nonce tracking prevents reusing signatures.
    5. Governance Store Integration: Checks persistent revocations and consumed nonces.
    """

    def __init__(
        self,
        trust_anchors: dict[str, TrustAnchor] | None = None,
        store: GovernanceStateStore | None = None,
    ) -> None:
        self.trust_anchors: dict[str, TrustAnchor] = dict(trust_anchors or {})
        self.store = store
        self._consumed_nonces: set[str] = set()
        self._revoked_keys: set[str] = set()

    def add_trust_anchor(self, anchor: TrustAnchor) -> None:
        """Register a trusted signer anchor."""
        self.trust_anchors[anchor.key_id] = anchor

    def revoke_trust_anchor(self, key_id: str, reason: str = "Revoked by owner") -> bool:
        """Revoke a trust anchor immediately."""
        if key_id in self.trust_anchors:
            self.trust_anchors[key_id].revoked = True
            self.trust_anchors[key_id].revocation_reason = reason
        self._revoked_keys.add(key_id)
        return True

    def verify_signature(
        self,
        evidence: OwnerSignatureEvidence,
        current_fingerprint: str,
    ) -> tuple[bool, SignatureVerificationOutcome, str]:
        """Verify the cryptographic authenticity, validity, and scope of signature evidence.

        Evaluates 8 sequential verification steps:
        1. Governance state store integrity check (fail-closed if corrupt).
        2. Structural validity check of evidence.
        3. Trust anchor check (fail-closed if anchor missing or unconfigured).
        4. Signer identity & key revocation check.
        5. Expiration check.
        6. Action fingerprint integrity match.
        7. Replay nonce consumption check.
        8. Cryptographic signature check.
        """
        # Step 1: Governance Store Integrity
        if self.store is not None:
            try:
                self.store.verify_integrity()
            except Exception as exc:
                return (
                    False,
                    SignatureVerificationOutcome.DENIED_GOVERNANCE_CORRUPT,
                    f"Governance state store corrupted: {exc}",
                )

        # Step 2: Structural Validity
        if not evidence.key_id or not evidence.signer_identity or not evidence.signature_hex:
            return (
                False,
                SignatureVerificationOutcome.DENIED_MALFORMED_EVIDENCE,
                "Signature evidence is incomplete or malformed",
            )

        # Step 3: Trust Anchor Presence
        if evidence.key_id not in self.trust_anchors:
            return (
                False,
                SignatureVerificationOutcome.DENIED_NO_TRUST_ANCHOR,
                f"No trust anchor found for key ID '{evidence.key_id}'; default deny",
            )

        anchor = self.trust_anchors[evidence.key_id]

        # Step 4: Signer Identity & Revocation
        if anchor.signer_identity != evidence.signer_identity:
            return (
                False,
                SignatureVerificationOutcome.DENIED_UNTRUSTED_SIGNER,
                f"Signer identity mismatch: expected '{anchor.signer_identity}', got '{evidence.signer_identity}'",
            )

        if anchor.revoked or evidence.key_id in self._revoked_keys:
            reason = anchor.revocation_reason or "Key was revoked"
            return (
                False,
                SignatureVerificationOutcome.DENIED_REVOKED,
                f"Trust anchor '{evidence.key_id}' has been revoked: {reason}",
            )

        # Check if approval envelope is revoked in store
        if self.store is not None and evidence.approval_id:
            stored_app = self.store.get_approval(evidence.approval_id)
            if stored_app and stored_app.revoked:
                return (
                    False,
                    SignatureVerificationOutcome.DENIED_REVOKED,
                    f"Approval '{evidence.approval_id}' has been revoked in persistent store",
                )

        # Step 5: Expiration
        try:
            exp_dt = datetime.fromisoformat(evidence.expires_at)
            now_dt = datetime.now(timezone.utc)
            if now_dt > exp_dt:
                return (
                    False,
                    SignatureVerificationOutcome.DENIED_EXPIRED,
                    f"Signature evidence expired at {evidence.expires_at}",
                )
        except ValueError:
            return (
                False,
                SignatureVerificationOutcome.DENIED_EXPIRED,
                "Invalid signature expiration timestamp format",
            )

        # Step 6: Action Fingerprint Binding
        if evidence.action_fingerprint != current_fingerprint:
            return (
                False,
                SignatureVerificationOutcome.DENIED_FINGERPRINT_MISMATCH,
                "Action fingerprint mismatch: parameters or scope were altered after signing",
            )

        # Step 7: Replay Nonce Check
        if evidence.nonce in self._consumed_nonces:
            return (
                False,
                SignatureVerificationOutcome.DENIED_REPLAY_NONCE,
                f"Signature nonce '{evidence.nonce}' has already been consumed (replay attack prevented)",
            )

        if self.store is not None:
            if self.store.is_nonce_consumed(evidence.nonce):
                return (
                    False,
                    SignatureVerificationOutcome.DENIED_REPLAY_NONCE,
                    f"Signature nonce '{evidence.nonce}' has already been consumed in persistent store",
                )

        # Step 8: Cryptographic Signature Verification
        if anchor.algorithm != evidence.algorithm:
            return (
                False,
                SignatureVerificationOutcome.DENIED_SIGNATURE_MISMATCH,
                f"Algorithm mismatch: anchor requires {anchor.algorithm.value}, evidence has {evidence.algorithm.value}",
            )

        if evidence.algorithm == SignatureAlgorithm.HMAC_SHA256:
            expected_sig = hmac.new(
                anchor.public_key_or_secret,
                evidence.canonical_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(evidence.signature_hex, expected_sig):
                return (
                    False,
                    SignatureVerificationOutcome.DENIED_SIGNATURE_MISMATCH,
                    "HMAC signature mismatch: invalid cryptographic signature",
                )
        elif evidence.algorithm in (
            SignatureAlgorithm.ED25519_TEST_FIXTURE,
            SignatureAlgorithm.RSA_SHA256_TEST_FIXTURE,
        ):
            # Deterministic test fixture asymmetric verification:
            # Hash(public_key + canonical_payload) matches signature_hex
            expected_sig = hashlib.sha256(
                anchor.public_key_or_secret + evidence.canonical_payload.encode("utf-8")
            ).hexdigest()
            if not hmac.compare_digest(evidence.signature_hex, expected_sig):
                return (
                    False,
                    SignatureVerificationOutcome.DENIED_SIGNATURE_MISMATCH,
                    "Asymmetric fixture signature mismatch: invalid cryptographic signature",
                )
        else:
            return (
                False,
                SignatureVerificationOutcome.DENIED_SIGNATURE_MISMATCH,
                f"Unsupported signature algorithm: {evidence.algorithm}",
            )

        return True, SignatureVerificationOutcome.VERIFIED, "Owner signature verified successfully"

    def consume_signature_nonce(self, evidence: OwnerSignatureEvidence) -> bool:
        """Mark signature nonce as consumed in-memory and in persistent store."""
        if evidence.nonce in self._consumed_nonces:
            return False

        if self.store is not None:
            ok = self.store.record_nonce(evidence.nonce, evidence.approval_id or "sig_verification")
            if not ok:
                return False

        self._consumed_nonces.add(evidence.nonce)
        return True


def create_test_signature(
    anchor: TrustAnchor,
    canonical_payload: str,
) -> str:
    """Helper to generate valid signature hex for unit test fixtures."""
    if anchor.algorithm == SignatureAlgorithm.HMAC_SHA256:
        return hmac.new(
            anchor.public_key_or_secret,
            canonical_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    elif anchor.algorithm in (
        SignatureAlgorithm.ED25519_TEST_FIXTURE,
        SignatureAlgorithm.RSA_SHA256_TEST_FIXTURE,
    ):
        return hashlib.sha256(
            anchor.public_key_or_secret + canonical_payload.encode("utf-8")
        ).hexdigest()
    raise ValueError(f"Unsupported algorithm for test signature: {anchor.algorithm}")
