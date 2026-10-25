"""Secure Owner Authentication and Approval Verification for QUAN AI BRAIN.

Sprint 4: Dual-Channel Owner Verification (Owner Private Secret Code + SMS OTP).
Independent, auditable, cryptographic verification gate.
Does NOT activate production execution or services.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import hmac
import secrets
from typing import Any

from quan_ai_brain.core.redaction import redact_text, redact_value
from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.tools.approval import ApprovalStatus
from quan_ai_brain.tools.sandbox import SystemState


class VerificationMethod(str, Enum):
    SECRET_CODE = "secret_code"      # Owner Private Secret Code (HMAC-SHA256 signature)
    SMS_OTP = "sms_otp"              # Out-of-band 6-digit SMS OTP token
    DUAL_FACTOR = "dual_factor"      # Both Private Code and SMS OTP required (Mandatory for R4)


class VerificationOutcome(str, Enum):
    VERIFIED = "verified"
    DENIED_SIGNATURE_MISMATCH = "denied_signature_mismatch"
    DENIED_INVALID_OTP = "denied_invalid_otp"
    DENIED_EXPIRED = "denied_expired"
    DENIED_CONSUMED = "denied_consumed"
    DENIED_REVOKED = "denied_revoked"
    DENIED_FINGERPRINT_MISMATCH = "denied_fingerprint_mismatch"
    DENIED_UNTRUSTED_SIGNER = "denied_untrusted_signer"
    DENIED_NO_TRUST_ANCHOR = "denied_no_trust_anchor"
    DENIED_ATTEMPTS_EXCEEDED = "denied_attempts_exceeded"
    DENIED_SYSTEM_EMERGENCY = "denied_system_emergency"
    BLOCKED_R5_PROHIBITED = "blocked_r5_prohibited"
    DENIED_R4_DUAL_FACTOR_REQUIRED = "denied_r4_dual_factor_required"


def compute_canonical_string(
    approval_id: str,
    tool_id: str,
    action: str,
    fingerprint: str,
    nonce: str,
    expires_at: str,
) -> str:
    """Canonicalize message fields into a deterministic string for signing."""
    parts = [
        str(approval_id).strip(),
        str(tool_id).strip(),
        str(action).strip(),
        str(fingerprint).strip(),
        str(nonce).strip(),
        str(expires_at).strip(),
    ]
    return "|".join(parts)


@dataclass
class SignedApproval:
    """Cryptographically signed approval envelope for tool execution."""

    approval_id: str
    tool_id: str
    action: str
    params: dict[str, Any]
    resource_scope: str
    risk_level: RiskLevel
    fingerprint: str
    nonce: str
    expires_at: str
    signer_identity: str
    verification_method: VerificationMethod
    signature: str = ""
    otp_code: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    consumed: bool = False
    revoked: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["params"] = redact_value(self.params)
        data["risk_level"] = self.risk_level.name if hasattr(self.risk_level, "name") else str(self.risk_level)
        data["verification_method"] = self.verification_method.value
        # Mask signature and OTP for security
        if self.signature:
            data["signature"] = self.signature[:8] + "..." + self.signature[-8:] if len(self.signature) > 16 else "[REDACTED]"
        if self.otp_code:
            data["otp_code"] = "[REDACTED]"
        return data


@dataclass
class SMSOTPChallenge:
    """Active SMS OTP challenge sent to the owner's mobile device."""

    challenge_id: str
    phone_number_masked: str
    action_fingerprint: str
    code_hash: str
    salt: str
    expires_at: str
    attempts: int = 0
    max_attempts: int = 3
    consumed: bool = False
    revoked: bool = False


class AuthenticatedApprovalVerifier:
    """Independent verifier that cryptographically verifies owner approvals.

    Supports:
    - Channel 1: Owner Private Secret Code (HMAC-SHA256 signature verification).
    - Channel 2: Mobile SMS OTP challenge verification (out-of-band).
    - Dual-Factor: Both Private Code and SMS OTP (mandatory for R4).
    - Anti-replay single-use consumption and persistent revocation blocklist.
    - Strict default-deny when trust anchors are unconfigured.
    """

    def __init__(
        self,
        owner_secret_key: bytes | str | None = None,
        trusted_phone: str | None = None,
        trusted_signers: set[str] | None = None,
        store: Any | None = None,
    ) -> None:
        if isinstance(owner_secret_key, str):
            self._secret_key: bytes | None = owner_secret_key.encode("utf-8")
        else:
            self._secret_key = owner_secret_key

        self.trusted_phone = trusted_phone.strip() if trusted_phone else None
        self.trusted_signers = trusted_signers  # None means any identity accepted in test if key matches
        self.store = store

        self._consumed_approvals: set[str] = set()
        self._consumed_nonces: set[str] = set()
        self._revoked_approvals: dict[str, str] = {}  # approval_id -> reason
        self._active_sms_challenges: dict[str, SMSOTPChallenge] = {}

    @property
    def has_trust_anchor(self) -> bool:
        """Check if at least one cryptographic or phone trust anchor is configured."""
        return self._secret_key is not None or self.trusted_phone is not None

    def sign_approval(self, approval: SignedApproval, secret_key: bytes | str | None = None) -> str:
        """Generate a valid HMAC-SHA256 signature for a SignedApproval token."""
        key = secret_key if secret_key is not None else self._secret_key
        if key is None:
            raise ValueError("No secret key provided or configured for signing")
        key_bytes = key.encode("utf-8") if isinstance(key, str) else key

        canonical = compute_canonical_string(
            approval_id=approval.approval_id,
            tool_id=approval.tool_id,
            action=approval.action,
            fingerprint=approval.fingerprint,
            nonce=approval.nonce,
            expires_at=approval.expires_at,
        )
        return hmac.new(key_bytes, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def create_sms_challenge(
        self,
        action_fingerprint: str,
        phone_number: str,
        ttl_seconds: int = 180,
    ) -> tuple[SMSOTPChallenge, str]:
        """Generate an out-of-band 6-digit SMS OTP challenge.

        Returns (challenge_object, raw_otp_code).
        In production, raw_otp_code is dispatched via SMS gateway and never stored.
        """
        # Generate cryptographically secure 6-digit numeric OTP (000000 to 999999)
        raw_code = f"{secrets.randbelow(1000000):06d}"
        salt = secrets.token_hex(16)
        code_hash = hashlib.sha256(f"{raw_code}:{salt}".encode("utf-8")).hexdigest()

        # Mask phone number (e.g., +84*****789)
        masked_phone = phone_number
        if len(phone_number) > 6:
            masked_phone = phone_number[:3] + "*" * (len(phone_number) - 6) + phone_number[-3:]

        now_dt = datetime.now(timezone.utc)
        from datetime import timedelta
        exp_dt = (now_dt + timedelta(seconds=ttl_seconds)).isoformat()
        c_id = secrets.token_hex(8)

        challenge = SMSOTPChallenge(
            challenge_id=c_id,
            phone_number_masked=masked_phone,
            action_fingerprint=action_fingerprint,
            code_hash=code_hash,
            salt=salt,
            expires_at=exp_dt,
            attempts=0,
            max_attempts=3,
        )
        self._active_sms_challenges[c_id] = challenge
        return challenge, raw_code

    def verify_approval(
        self,
        approval: SignedApproval,
        current_fingerprint: str,
        current_risk: RiskLevel,
        sms_challenge: SMSOTPChallenge | None = None,
        system_state: SystemState = SystemState.NORMAL,
    ) -> tuple[bool, VerificationOutcome, str]:
        """Verify authenticity, integrity, lifecycle, and scope of an approval token.

        Evaluates 10 rigorous defense layers:
        1. Emergency system state (STOP/FREEZE).
        2. R5 Hard-Block: R5 is unconditionally prohibited.
        3. Trust Anchor presence: default deny if unconfigured.
        4. Signer identity trust check.
        5. Revocation blocklist check.
        6. Single-use consumption check (anti-replay).
        7. Expiration check.
        8. Parameter & Scope Fingerprint integrity match.
        9. Verification Method enforcement (Secret Code HMAC, SMS OTP, or Dual-Factor).
        10. R4 Dual-Factor enforcement.
        """
        # 1. Emergency System State
        if system_state in (SystemState.STOP, SystemState.FREEZE):
            return False, VerificationOutcome.DENIED_SYSTEM_EMERGENCY, f"System is in {system_state.value.upper()} state; tool execution is halted"

        # 2. R5 Hard-Block — R5 is NEVER permitted under any circumstances
        if int(current_risk) >= int(RiskLevel.R5) or int(approval.risk_level) >= int(RiskLevel.R5):
            return False, VerificationOutcome.BLOCKED_R5_PROHIBITED, "Risk level R5 is prohibited in this system; approval cannot be granted"

        # 3. Trust Anchor Check — Default deny if neither secret key nor phone anchor configured
        if not self.has_trust_anchor:
            return False, VerificationOutcome.DENIED_NO_TRUST_ANCHOR, "Trust anchor is not configured; verifier defaults to hard denial"

        # 4. Signer Identity Check
        if self.trusted_signers is not None and approval.signer_identity not in self.trusted_signers:
            return False, VerificationOutcome.DENIED_UNTRUSTED_SIGNER, f"Signer identity '{approval.signer_identity}' is not in trusted owner identities"

        # 5. Revocation Check
        if approval.approval_id in self._revoked_approvals or approval.revoked:
            reason = self._revoked_approvals.get(approval.approval_id, "Revoked by owner")
            return False, VerificationOutcome.DENIED_REVOKED, f"Approval has been revoked: {reason}"

        if self.store is not None:
            stored_app = self.store.get_approval(approval.approval_id)
            if stored_app and (stored_app.revoked or stored_app.status == ApprovalStatus.REVOKED):
                return False, VerificationOutcome.DENIED_REVOKED, "Approval has been revoked in persistent governance store"

        # 6. Anti-Replay Single-Use Consumption Check
        if approval.approval_id in self._consumed_approvals or approval.consumed:
            return False, VerificationOutcome.DENIED_CONSUMED, "Approval has already been consumed (replay attack prevented)"

        if approval.nonce in self._consumed_nonces:
            return False, VerificationOutcome.DENIED_CONSUMED, f"Approval nonce '{approval.nonce}' has already been used"

        if self.store is not None:
            stored_app = self.store.get_approval(approval.approval_id)
            if stored_app and (stored_app.consumed or stored_app.status == ApprovalStatus.COMPLETED):
                return False, VerificationOutcome.DENIED_CONSUMED, "Approval has already been consumed in persistent governance store"
            if self.store.is_nonce_consumed(approval.nonce):
                return False, VerificationOutcome.DENIED_CONSUMED, f"Approval nonce '{approval.nonce}' has already been consumed in persistent governance store"

        # 7. Expiration Check
        try:
            exp_dt = datetime.fromisoformat(approval.expires_at)
            now_dt = datetime.now(timezone.utc)
            if now_dt > exp_dt:
                return False, VerificationOutcome.DENIED_EXPIRED, f"Approval expired at {approval.expires_at}"
        except ValueError:
            return False, VerificationOutcome.DENIED_EXPIRED, "Invalid expiration timestamp format"

        # 8. Action Fingerprint Integrity Match
        if approval.fingerprint != current_fingerprint:
            return False, VerificationOutcome.DENIED_FINGERPRINT_MISMATCH, "Action fingerprint mismatch: parameters or scope were altered after approval"

        # 9. Verification Method Evaluation
        method = approval.verification_method

        # R4 requires Dual-Factor
        if int(current_risk) >= int(RiskLevel.R4) and method != VerificationMethod.DUAL_FACTOR:
            return False, VerificationOutcome.DENIED_R4_DUAL_FACTOR_REQUIRED, "R4 actions require Dual-Factor verification (Private Code + SMS OTP)"

        # Check Kênh 1: Private Secret Code (HMAC-SHA256 signature)
        if method in (VerificationMethod.SECRET_CODE, VerificationMethod.DUAL_FACTOR):
            if not self._secret_key:
                return False, VerificationOutcome.DENIED_NO_TRUST_ANCHOR, "Secret key trust anchor not configured for signature verification"
            if not approval.signature:
                return False, VerificationOutcome.DENIED_SIGNATURE_MISMATCH, "Missing required HMAC signature in approval envelope"

            expected_sig = self.sign_approval(approval)
            if not hmac.compare_digest(approval.signature, expected_sig):
                return False, VerificationOutcome.DENIED_SIGNATURE_MISMATCH, "Cryptographic signature mismatch: invalid secret code or tampered envelope"

        # Check Kênh 2: SMS OTP
        if method in (VerificationMethod.SMS_OTP, VerificationMethod.DUAL_FACTOR):
            if not sms_challenge:
                return False, VerificationOutcome.DENIED_INVALID_OTP, "Missing required active SMS OTP challenge"

            # Challenge checks
            if sms_challenge.consumed:
                return False, VerificationOutcome.DENIED_CONSUMED, "SMS OTP challenge has already been consumed"
            # Check attempts limit
            if sms_challenge.attempts >= sms_challenge.max_attempts:
                sms_challenge.revoked = True
                return False, VerificationOutcome.DENIED_ATTEMPTS_EXCEEDED, "SMS OTP maximum verification attempts exceeded; challenge invalidated"

            if sms_challenge.revoked:
                return False, VerificationOutcome.DENIED_REVOKED, "SMS OTP challenge was revoked"

            # Check challenge expiration
            try:
                ch_exp = datetime.fromisoformat(sms_challenge.expires_at)
                if datetime.now(timezone.utc) > ch_exp:
                    return False, VerificationOutcome.DENIED_EXPIRED, f"SMS OTP challenge expired at {sms_challenge.expires_at}"
            except ValueError:
                return False, VerificationOutcome.DENIED_EXPIRED, "Invalid challenge expiration format"

            # Check fingerprint binding
            if sms_challenge.action_fingerprint != current_fingerprint:
                return False, VerificationOutcome.DENIED_FINGERPRINT_MISMATCH, "SMS OTP challenge is bound to a different action fingerprint"

            # Verify OTP hash
            sms_challenge.attempts += 1
            provided_hash = hashlib.sha256(f"{approval.otp_code}:{sms_challenge.salt}".encode("utf-8")).hexdigest()
            if not hmac.compare_digest(provided_hash, sms_challenge.code_hash):
                if sms_challenge.attempts >= sms_challenge.max_attempts:
                    sms_challenge.revoked = True
                return False, VerificationOutcome.DENIED_INVALID_OTP, f"Invalid SMS OTP code (Attempt {sms_challenge.attempts}/{sms_challenge.max_attempts})"

            # Valid OTP! Consume challenge
            sms_challenge.consumed = True

        return True, VerificationOutcome.VERIFIED, "Approval authenticated and verified successfully"

    def consume_approval(self, approval: SignedApproval) -> bool:
        """Mark approval token and its nonce as consumed (anti-replay)."""
        if approval.approval_id in self._consumed_approvals or approval.consumed:
            return False

        if self.store is not None:
            nonce_ok = self.store.record_nonce(approval.nonce, approval.approval_id)
            if not nonce_ok:
                return False
            self.store.consume_approval(approval.approval_id)

        approval.consumed = True
        self._consumed_approvals.add(approval.approval_id)
        self._consumed_nonces.add(approval.nonce)
        return True

    def revoke_approval(self, approval_id: str, reason: str = "Revoked by owner") -> bool:
        """Revoke an approval token immediately."""
        self._revoked_approvals[approval_id] = reason
        if self.store is not None:
            self.store.revoke_approval(approval_id, reason=reason)
        return True

    def is_consumed(self, approval_id: str) -> bool:
        return approval_id in self._consumed_approvals

    def is_revoked(self, approval_id: str) -> bool:
        return approval_id in self._revoked_approvals
