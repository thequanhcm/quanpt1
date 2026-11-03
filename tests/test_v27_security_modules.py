"""
V27 security module tests (M1-M5).

Covers: authentication (PBKDF2, sessions, TOTP MFA, lockout, simulated
OAuth), RBAC/ABAC, hash-chained audit log + GDPR, data protection (demo
XOR cipher + masking + rotation), security monitoring rules, and an
end-to-end integration suite.

Run:  ./.venv/Scripts/python.exe -m pytest tests/test_v27_security_modules.py -q
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from quan_ai_brain.security.audit_logging import AuditEntry, AuditLog
from quan_ai_brain.security.authentication import (
    AccountLockedError,
    AuthError,
    AuthManager,
    InvalidCredentialsError,
    MFARequiredError,
    OAuthError,
    SessionExpiredError,
)
from quan_ai_brain.security._totp import hotp_at, totp_now, verify_totp, generate_totp_secret
from quan_ai_brain.security.data_protection import (
    EncryptedField,
    EncryptionService,
    mask_email,
    mask_phone,
    mask_string,
    mask_token,
)
from quan_ai_brain.security.rbac import (
    ABACEngine,
    ABACPolicy,
    AccessDecision,
    AuthorizationEngine,
    Permission,
    RBACEngine,
    Role,
)
from quan_ai_brain.security.security_monitoring import (
    Alert,
    SecurityEvent,
    SecurityMonitor,
    Severity,
)

# ============================================================================
# M1 - Authentication
# ============================================================================


class TestAuthentication:
    def setup_method(self):
        self.auth = AuthManager(pbkdf2_iterations=1000)
        self.user = self.auth.create_user("quan", "S3curePass!", roles=["user"])

    # -- user store / password hashing ---------------------------------
    def test_create_user_returns_user_with_id(self):
        assert self.user.user_id.startswith("usr_")
        assert self.user.username == "quan"
        assert self.user.password_hash != b"S3curePass!"

    def test_password_hash_uses_pbkdf2_and_salt(self):
        # Recompute PBKDF2 manually and compare.
        import hashlib

        expected = hashlib.pbkdf2_hmac("sha256", b"S3curePass!", self.user.salt, 1000)
        assert self.user.password_hash == expected

    def test_duplicate_username_rejected(self):
        with pytest.raises(AuthError):
            self.auth.create_user("quan", "AnotherPass1!")

    def test_get_user_by_username(self):
        found = self.auth.get_user_by_username("quan")
        assert found is not None and found.user_id == self.user.user_id
        assert self.auth.get_user_by_username("nobody") is None

    def test_public_dict_never_contains_password_material(self):
        public = self.user.to_public_dict()
        blob = repr(public)
        assert "password_hash" not in blob and "salt" not in blob

    # -- login success/failure ------------------------------------------
    def test_authenticate_success_returns_session(self):
        session = self.auth.authenticate("quan", "S3curePass!")
        assert session.user_id == self.user.user_id
        assert len(session.token) == 64  # secrets.token_hex(32)

    def test_authenticate_wrong_password_raises(self):
        with pytest.raises(InvalidCredentialsError):
            self.auth.authenticate("quan", "wrong-password")

    def test_authenticate_unknown_user_raises(self):
        with pytest.raises(InvalidCredentialsError):
            self.auth.authenticate("ghost", "whatever")

    def test_tokens_are_random_not_repeated(self):
        s1 = self.auth.authenticate("quan", "S3curePass!")
        s2 = self.auth.authenticate("quan", "S3curePass!")
        assert s1.token != s2.token

    # -- lockout ----------------------------------------------------------
    def test_lockout_after_max_failed_attempts(self):
        for _ in range(5):
            with pytest.raises(InvalidCredentialsError):
                self.auth.authenticate("quan", "bad")
        with pytest.raises(AccountLockedError):
            self.auth.authenticate("quan", "S3curePass!")  # even correct pw

    def test_lockout_expires_after_window(self):
        t0 = 1_700_000_000.0
        auth = AuthManager(pbkdf2_iterations=1000, lockout_seconds=60)
        auth.create_user("bob", "Password1!")
        for i in range(5):
            with pytest.raises(InvalidCredentialsError):
                auth.authenticate("bob", "bad", now=t0 + i)
        with pytest.raises(AccountLockedError):
            auth.authenticate("bob", "Password1!", now=t0 + 10)
        # After the lockout window (locked at t0+4 for 60s -> until t0+64)
        # the account works again.
        session = auth.authenticate("bob", "Password1!", now=t0 + 65)
        assert session.user_id == auth.get_user_by_username("bob").user_id

    def test_successful_login_resets_failure_counter(self):
        with pytest.raises(InvalidCredentialsError):
            self.auth.authenticate("quan", "bad")
        with pytest.raises(InvalidCredentialsError):
            self.auth.authenticate("quan", "bad")
        self.auth.authenticate("quan", "S3curePass!")
        assert self.user.failed_attempts == 0
        # 4 more failures: below threshold of 5 -> no lockout yet.
        for _ in range(4):
            with pytest.raises(InvalidCredentialsError):
                self.auth.authenticate("quan", "bad")
        with pytest.raises(InvalidCredentialsError):
            self.auth.authenticate("quan", "bad")  # 5th total since reset -> lockout
        with pytest.raises(AccountLockedError):
            self.auth.authenticate("quan", "S3curePass!")

    # -- sessions -----------------------------------------------------------
    def test_session_validation_and_expiry(self):
        t0 = 1_700_000_000.0
        auth = AuthManager(pbkdf2_iterations=1000, session_ttl_seconds=60)
        auth.create_user("carl", "Password1!")
        session = auth.authenticate("carl", "Password1!", now=t0)
        assert auth.validate_session(session.token, now=t0 + 59).user_id
        with pytest.raises(SessionExpiredError):
            auth.validate_session(session.token, now=t0 + 61)

    def test_unknown_token_raises(self):
        with pytest.raises(SessionExpiredError):
            self.auth.validate_session("nonexistent-token")

    def test_session_revocation(self):
        session = self.auth.authenticate("quan", "S3curePass!")
        self.auth.revoke_session(session.token)
        with pytest.raises(SessionExpiredError):
            self.auth.validate_session(session.token)

    def test_active_sessions_listing(self):
        s1 = self.auth.authenticate("quan", "S3curePass!")
        s2 = self.auth.authenticate("quan", "S3curePass!")
        active = self.auth.active_sessions(self.user.user_id)
        assert {s.token for s in active} == {s1.token, s2.token}

    # -- MFA TOTP -------------------------------------------------------------
    def test_mfa_enablement_requires_code(self):
        secret = self.auth.enable_mfa(self.user.user_id)
        assert len(secret) >= 32  # base32 of >=20 bytes
        with pytest.raises(MFARequiredError):
            self.auth.authenticate("quan", "S3curePass!")  # no code given

    def test_mfa_correct_code_authenticates(self):
        secret = self.auth.enable_mfa(self.user.user_id)
        code = totp_now(secret, timestamp=1_700_000_000)
        session = self.auth.authenticate("quan", "S3curePass!", mfa_code=code, now=1_700_000_000)
        assert session.mfa_verified is True

    def test_mfa_window_plus_minus_one_step(self):
        secret = self.auth.enable_mfa(self.user.user_id)
        t0 = 1_700_000_000  # step index 56666666
        code_prev = hotp_at(secret, t0 // 30 - 1)
        code_next = hotp_at(secret, t0 // 30 + 1)
        assert self.auth.authenticate("quan", "S3curePass!", mfa_code=code_prev, now=t0)
        assert self.auth.authenticate("quan", "S3curePass!", mfa_code=code_next, now=t0)

    def test_mfa_wrong_code_rejected_and_counts_toward_lockout(self):
        self.auth.enable_mfa(self.user.user_id)
        for _ in range(5):
            with pytest.raises(InvalidCredentialsError):
                self.auth.authenticate("quan", "S3curePass!", mfa_code="000000")
        with pytest.raises(AccountLockedError):
            self.auth.authenticate("quan", "S3curePass!", mfa_code="000000")

    def test_mfa_disable(self):
        self.auth.enable_mfa(self.user.user_id)
        self.auth.disable_mfa(self.user.user_id)
        session = self.auth.authenticate("quan", "S3curePass!")
        assert session.user_id == self.user.user_id

    def test_totp_module_rejects_wrong_step_outside_window(self):
        secret = generate_totp_secret()
        t0 = 1_700_000_000
        far_code = hotp_at(secret, t0 // 30 + 10)
        assert verify_totp(secret, far_code, timestamp=t0, window=1) is False

    # -- OAuth2 / OIDC simulated flow -------------------------------------------
    def test_oauth_register_client_returns_secret(self):
        client_secret = self.auth.register_oauth_client("web-app")
        assert len(client_secret) == 32

    def test_oauth_authorize_issues_code(self):
        self.auth.register_oauth_client("web-app")
        code = self.auth.oauth_authorize("web-app", self.user.user_id, "https://app/callback")
        assert len(code.code) >= 32
        assert code.consumed is False
        assert "openid" in code.scope

    def test_oauth_authorize_unknown_client_rejected(self):
        with pytest.raises(OAuthError):
            self.auth.oauth_authorize("unknown", self.user.user_id, "https://app/callback")

    def test_oauth_full_flow_token_exchange(self):
        client_secret = self.auth.register_oauth_client("web-app")
        code = self.auth.oauth_authorize("web-app", self.user.user_id, "https://app/callback")
        token = self.auth.oauth_token_exchange(
            "web-app", client_secret, code.code, "https://app/callback"
        )
        assert token.token_type == "Bearer"
        assert token.access_token and token.refresh_token and token.id_token
        info = self.auth.oauth_introspect(token.access_token)
        assert info is not None and info["user_id"] == self.user.user_id

    def test_oauth_code_single_use(self):
        client_secret = self.auth.register_oauth_client("web-app")
        code = self.auth.oauth_authorize("web-app", self.user.user_id, "https://app/callback")
        self.auth.oauth_token_exchange("web-app", client_secret, code.code, "https://app/callback")
        with pytest.raises(OAuthError):
            self.auth.oauth_token_exchange("web-app", client_secret, code.code, "https://app/callback")

    def test_oauth_bad_client_secret_rejected(self):
        self.auth.register_oauth_client("web-app")
        code = self.auth.oauth_authorize("web-app", self.user.user_id, "https://app/callback")
        with pytest.raises(OAuthError):
            self.auth.oauth_token_exchange("web-app", "wrong-secret", code.code, "https://app/callback")

    def test_oauth_redirect_uri_mismatch_rejected(self):
        client_secret = self.auth.register_oauth_client("web-app")
        code = self.auth.oauth_authorize("web-app", self.user.user_id, "https://app/callback")
        with pytest.raises(OAuthError):
            self.auth.oauth_token_exchange("web-app", client_secret, code.code, "https://evil/callback")


# ============================================================================
# M2 - RBAC / ABAC
# ============================================================================


class TestRBAC:
    def setup_method(self):
        self.rbac = RBACEngine()
        self.rbac.add_role(Role("viewer", [Permission("document", "read")]))
        self.rbac.add_role(Role("editor", [Permission("document", "write")], parent_names=["viewer"]))
        self.rbac.add_role(Role("admin", [Permission("*", "*")], parent_names=["editor"]))

    def test_deny_by_default_unknown_user(self):
        decision = self.rbac.check("stranger", "document", "read")
        assert decision.allowed is False
        assert "deny-by-default" in decision.reason

    def test_direct_permission_grants(self):
        self.rbac.assign_role_to_user("u1", "viewer")
        assert self.rbac.check("u1", "document", "read").allowed is True

    def test_missing_action_denied(self):
        self.rbac.assign_role_to_user("u1", "viewer")
        assert self.rbac.check("u1", "document", "write").allowed is False

    def test_role_hierarchy_inheritance(self):
        # editor inherits viewer permissions.
        self.rbac.assign_role_to_user("u2", "editor")
        assert self.rbac.check("u2", "document", "read").allowed is True
        assert self.rbac.check("u2", "document", "write").allowed is True

    def test_admin_wildcard(self):
        self.rbac.assign_role_to_user("u3", "admin")
        assert self.rbac.check("u3", "anything", "delete").allowed is True

    def test_effective_permissions_expanded(self):
        self.rbac.assign_role_to_user("u2", "editor")
        perms = {p.as_string() for p in self.rbac.effective_permissions("u2")}
        assert perms == {"document:read", "document:write"}

    def test_revoke_role_removes_access(self):
        self.rbac.assign_role_to_user("u1", "viewer")
        self.rbac.revoke_role_from_user("u1", "viewer")
        assert self.rbac.check("u1", "document", "read").allowed is False

    def test_explicit_role_names_param(self):
        # Caller may pass roles directly (e.g. from the user store).
        assert self.rbac.check("uX", "document", "read", role_names=["viewer"]).allowed
        assert not self.rbac.check("uX", "document", "write", role_names=["viewer"]).allowed

    def test_role_cycle_is_safe(self):
        self.rbac.add_role(Role("a", [], parent_names=["b"]))
        self.rbac.add_role(Role("b", [], parent_names=["a"]))
        assert set(self.rbac.effective_roles("a")) == {"a", "b"}


class TestABAC:
    def test_policy_attribute_match_allows(self):
        abac = ABACEngine()
        abac.add_policy(
            ABACPolicy(
                "own-document",
                {"subject.department": "finance", "resource.owner": "finance"},
            )
        )
        decision = abac.evaluate(
            subject={"department": "finance"},
            resource={"owner": "finance"},
            environment={},
        )
        assert decision.allowed is True and decision.matched_policy == "own-document"

    def test_no_matching_policy_denies(self):
        abac = ABACEngine()
        decision = abac.evaluate(subject={"department": "hr"}, resource={"owner": "finance"}, environment={})
        assert decision.allowed is False
        assert "deny-by-default" in decision.reason

    def test_list_of_acceptable_values(self):
        abac = ABACEngine()
        abac.add_policy(ABACPolicy("clearance", {"subject.clearance": ["secret", "top-secret"]}))
        assert abac.evaluate({"clearance": "secret"}, {}, {}).allowed
        assert not abac.evaluate({"clearance": "public"}, {}, {}).allowed

    def test_deny_policy_effect(self):
        abac = ABACEngine()
        abac.add_policy(ABACPolicy("blocked-contractor", {"subject.employment": "contractor"}, effect="deny"))
        decision = abac.evaluate({"employment": "contractor"}, {}, {})
        assert decision.allowed is False and decision.matched_policy == "blocked-contractor"

    def test_environment_attribute_time_window(self):
        abac = ABACEngine()
        abac.add_policy(ABACPolicy("office-hours", {"environment.hour": list(range(6, 24))}))
        assert abac.evaluate({}, {}, {"hour": 10}).allowed
        assert not abac.evaluate({}, {}, {"hour": 3}).allowed


class TestAuthorizationEngine:
    def setup_method(self):
        self.rbac = RBACEngine()
        self.rbac.add_role(Role("viewer", [Permission("document", "read")]))
        self.engine = AuthorizationEngine(rbac=self.rbac)

    def test_rbac_grant_wins(self):
        self.rbac.assign_role_to_user("u1", "viewer")
        assert self.engine.check_permission("u1", "document", "read").allowed is True

    def test_abac_allow_fills_gap(self):
        self.engine.abac.add_policy(
            ABACPolicy("same-dept", {"subject.department": "finance", "resource.owner": "finance"})
        )
        decision = self.engine.check_permission(
            "u9",
            "document",
            "read",
            subject_attrs={"department": "finance"},
            resource_attrs={"owner": "finance"},
        )
        assert decision.allowed is True and decision.matched_policy == "same-dept"

    def test_explicit_deny_overrides_rbac(self):
        self.rbac.assign_role_to_user("u1", "viewer")
        self.engine.abac.add_policy(
            ABACPolicy("deny-contractor", {"subject.employment": "contractor"}, effect="deny")
        )
        decision = self.engine.check_permission(
            "u1",
            "document",
            "read",
            role_names=["viewer"],
            subject_attrs={"employment": "contractor"},
        )
        assert decision.allowed is False and decision.matched_policy == "deny-contractor"

    def test_final_deny_by_default(self):
        decision = self.engine.check_permission("nobody", "document", "delete")
        assert decision.allowed is False


# ============================================================================
# M3 - Audit logging
# ============================================================================


class TestAuditLogging:
    def setup_method(self):
        self.log = AuditLog()

    def _add(self, user="u1", action="READ", **kw):
        return self.log.append(user_id=user, action=action, resource_type="document", resource_id="d-1", **kw)

    def test_append_returns_entry_with_hash(self):
        entry = self._add()
        assert entry.entry_hash and len(entry.entry_hash) == 64
        assert entry.previous_hash == "0" * 64  # genesis

    def test_chain_links_each_entry_to_previous(self):
        e1 = self._add(user="u1")
        e2 = self._add(user="u2")
        assert e2.previous_hash == e1.entry_hash

    def test_verify_chain_intact(self):
        for i in range(5):
            self._add(user=f"u{i}")
        assert self.log.verify_chain() is True

    def test_tamper_detection_modification(self):
        self._add()
        entry = self._add()
        self._add()
        entry.action = "TAMPERED"  # simulate in-place modification
        assert self.log.verify_chain() is False

    def test_append_only_no_delete_api(self):
        self._add()
        assert not hasattr(self.log, "delete")
        assert not hasattr(self.log, "remove")

    def test_query_by_user(self):
        self._add(user="alice")
        self._add(user="bob")
        self._add(user="alice", action="DELETE")
        alice_entries = self.log.query(user_id="alice")
        assert len(alice_entries) == 2
        assert all(e.user_id == "alice" for e in alice_entries)

    def test_query_by_action(self):
        self._add(action="LOGIN")
        self._add(action="LOGIN")
        self._add(action="LOGOUT")
        assert len(self.log.query(action="LOGIN")) == 2

    def test_query_by_time_range(self):
        t0 = datetime(2026, 10, 28, 10, 0, 0)
        self._add(timestamp=t0)
        self._add(timestamp=t0 + timedelta(hours=2))
        self._add(timestamp=t0 + timedelta(hours=5))
        hits = self.log.query(start=t0 + timedelta(minutes=30), end=t0 + timedelta(hours=3))
        assert len(hits) == 1

    def test_query_combined_filters(self):
        t0 = datetime(2026, 10, 28, 10, 0, 0)
        self._add(user="a", action="READ", timestamp=t0)
        self._add(user="a", action="WRITE", timestamp=t0)
        self._add(user="b", action="READ", timestamp=t0)
        hits = self.log.query(user_id="a", action="READ", start=t0 - timedelta(hours=1))
        assert len(hits) == 1

    def test_query_limit(self):
        for _ in range(5):
            self._add()
        assert len(self.log.query(limit=3)) == 3

    def test_gdpr_export_contains_all_subject_entries(self):
        self._add(user="alice", action="READ")
        self._add(user="bob")
        self._add(user="alice", action="WRITE")
        export = self.log.gdpr_export("alice")
        assert export["entry_count"] == 2
        assert export["subject"] == "alice"
        assert all(e["user_id"] == "alice" for e in export["entries"])

    def test_right_to_erasure_pseudonymizes(self):
        self._add(user="alice")
        self._add(user="bob")
        result = self.log.right_to_erasure("alice")
        assert result["entries_affected"] == 1
        assert result["pseudonym"].startswith("erased_")
        remaining = [e for e in self.log.entries if e.user_id == "alice"]
        assert remaining == []  # no raw identifier left in query layer

    def test_right_to_erasure_writes_tombstone(self):
        self._add(user="alice")
        self.log.right_to_erasure("alice")
        tombstones = self.log.query(action="GDPR_ERASURE")
        assert len(tombstones) == 1
        assert tombstones[0].details["subject"] == "alice"

    def test_hash_is_deterministic_given_same_content(self):
        ts = datetime(2026, 10, 28, 12, 0, 0)
        e1 = AuditEntry(
            entry_id="x", timestamp=ts, user_id="u", action="READ", resource_type="doc",
            resource_id="1", ip_address="ip", user_agent="ua", request_id="r",
            status="SUCCESS", previous_hash="0" * 64,
        )
        e2 = AuditEntry(
            entry_id="x", timestamp=ts, user_id="u", action="READ", resource_type="doc",
            resource_id="1", ip_address="ip", user_agent="ua", request_id="r",
            status="SUCCESS", previous_hash="0" * 64,
        )
        assert e1.compute_hash() == e2.compute_hash()

    def test_different_content_different_hash(self):
        ts = datetime(2026, 10, 28, 12, 0, 0)
        kwargs = dict(
            entry_id="x", timestamp=ts, user_id="u", action="READ", resource_type="doc",
            resource_id="1", ip_address="ip", user_agent="ua", request_id="r",
            status="SUCCESS", previous_hash="0" * 64,
        )
        e1 = AuditEntry(**kwargs)
        e2 = AuditEntry(**{**kwargs, "action": "WRITE"})
        assert e1.compute_hash() != e2.compute_hash()

    def test_invalid_status_rejected(self):
        with pytest.raises(ValueError):
            self.log.append(user_id="u", action="READ", resource_type="doc", resource_id="1", status="MAYBE")


# ============================================================================
# M4 - Data protection
# ============================================================================


class TestDataProtection:
    def setup_method(self):
        self.svc = EncryptionService()

    # -- demo cipher ------------------------------------------------------
    def test_encrypt_decrypt_roundtrip(self):
        secret = "mach-troi-giup-do"
        field = self.svc.encrypt_field(secret)
        assert field.ciphertext_b64 != secret
        assert self.svc.decrypt_field(field) == secret

    def test_ciphertext_differs_per_nonce(self):
        f1 = self.svc.encrypt_field("same-plaintext")
        f2 = self.svc.encrypt_field("same-plaintext")
        assert f1.ciphertext_b64 != f2.ciphertext_b64  # random nonce

    def test_wrong_key_version_cannot_decrypt(self):
        field = self.svc.encrypt_field("data")
        self.svc.rotate_key()
        with pytest.raises(KeyError):
            # Version 99 was never issued.
            self.svc.decrypt_bytes(
                __import__("base64").b64decode(field.ciphertext_b64),
                __import__("base64").b64decode(field.nonce_b64),
                99,
            )

    def test_tampered_ciphertext_garbles_output_not_crash(self):
        # XOR cipher has no integrity: a flipped bit yields wrong plaintext.
        field = self.svc.encrypt_field("important-data")
        raw = bytearray(__import__("base64").b64decode(field.ciphertext_b64))
        raw[0] ^= 0x01
        field.ciphertext_b64 = __import__("base64").b64encode(bytes(raw)).decode()
        assert self.svc.decrypt_field(field) != "important-data"

    def test_key_rotation_old_ciphertexts_still_decrypt(self):
        old = self.svc.encrypt_field("old-secret")
        v2 = self.svc.rotate_key()
        assert v2 == 2 and self.svc.current_key_version == 2
        new = self.svc.encrypt_field("new-secret")
        assert new.key_version == 2
        assert self.svc.decrypt_field(old) == "old-secret"
        assert self.svc.decrypt_field(new) == "new-secret"

    def test_rotate_multiple_versions(self):
        self.svc.rotate_key()
        self.svc.rotate_key()
        assert self.svc.current_key_version == 3

    def test_set_active_key_version(self):
        old = self.svc.encrypt_field("v1-data")
        self.svc.rotate_key()
        self.svc.set_active_key_version(1)
        again = self.svc.encrypt_field("also-v1")
        assert again.key_version == 1 and old.key_version == 1

    def test_field_level_envelope_shape(self):
        field = self.svc.encrypt_field("pii-value")
        d = field.to_dict()
        assert set(d) == {"ciphertext_b64", "nonce_b64", "key_version", "algorithm"}
        assert "DEMO" in field.algorithm  # honest labeling

    def test_encrypt_requires_bytes(self):
        with pytest.raises(TypeError):
            self.svc.encrypt_bytes("not-bytes")

    def test_demo_cipher_is_not_aes(self):
        # Honest marker: algorithm field must NOT claim AES.
        field = self.svc.encrypt_field("x")
        assert "aes" not in field.algorithm.lower()

    # -- masking ----------------------------------------------------------
    def test_mask_email(self):
        masked = mask_email("nguyen.van.an@viettel.com.vn")
        local = "nguyen.van.an"  # 13 chars -> first char + 12 stars
        assert masked == f"n{'*' * (len(local) - 1)}@viettel.com.vn"
        assert "@" in masked and "nguyen" not in masked

    def test_mask_email_short_local_part(self):
        # 1-char local part: first char kept + exactly 1 star.
        assert mask_email("a@x.vn") == "a*@x.vn"

    def test_mask_email_invalid(self):
        with pytest.raises(ValueError):
            mask_email("not-an-email")

    def test_mask_phone(self):
        assert mask_phone("+84912345678") == "+84******678"

    def test_mask_phone_invalid(self):
        with pytest.raises(ValueError):
            mask_phone("12345")

    def test_mask_token_keeps_tail(self):
        token = "sk-" + "a" * 30
        masked = mask_token(token, keep=4)
        assert masked.endswith("aaaa") and masked.startswith("*")

    def test_mask_string_middle(self):
        # "secretvalue" (11 chars), 2+2 visible -> 7 stars in the middle.
        assert mask_string("secretvalue", visible_head=2, visible_tail=2) == "se" + "*" * 7 + "ue"
        assert len(mask_string("secretvalue")) == len("secretvalue")


# ============================================================================
# M5 - Security monitoring
# ============================================================================


def _evt(event_type, user="u1", at=None, **kw):
    return SecurityEvent(
        event_type=event_type,
        user_id=user,
        timestamp=at or datetime(2026, 10, 28, 10, 0, 0),
        **kw,
    )


class TestSecurityMonitoring:
    def test_no_alert_on_normal_activity(self):
        mon = SecurityMonitor()
        assert mon.ingest(_evt("LOGIN_SUCCESS", at=datetime(2026, 10, 28, 10, 0, 0))) == []
        assert mon.ingest(_evt("DATA_ACCESS", at=datetime(2026, 10, 28, 10, 5, 0))) == []
        assert mon.alerts() == []

    def test_brute_force_alert_at_threshold(self):
        mon = SecurityMonitor(brute_force_threshold=5)
        base = datetime(2026, 10, 28, 10, 0, 0)
        fired = []
        for i in range(5):
            fired = mon.ingest(_evt("LOGIN_FAILURE", user="u1", at=base + timedelta(seconds=i * 10)))
        assert len(fired) == 1
        assert fired[0].rule_name == "brute_force"
        assert fired[0].severity == Severity.MEDIUM

    def test_brute_force_escalates_and_quarantines_at_2x(self):
        mon = SecurityMonitor(brute_force_threshold=5)
        base = datetime(2026, 10, 28, 10, 0, 0)
        fired = []
        for i in range(10):
            fired = mon.ingest(_evt("LOGIN_FAILURE", user="u1", at=base + timedelta(seconds=i)))
        assert fired[0].severity == Severity.HIGH
        assert fired[0].quarantine is True
        assert mon.is_quarantined("u1") is True

    def test_brute_force_window_expires(self):
        mon = SecurityMonitor(brute_force_threshold=5, brute_force_window_seconds=60)
        base = datetime(2026, 10, 28, 10, 0, 0)
        for i in range(4):
            mon.ingest(_evt("LOGIN_FAILURE", user="u1", at=base + timedelta(seconds=i * 10)))
        # Next failure far outside the window: no alert.
        fired = mon.ingest(_evt("LOGIN_FAILURE", user="u1", at=base + timedelta(minutes=30)))
        assert fired == []

    def test_failures_of_different_users_do_not_merge(self):
        mon = SecurityMonitor(brute_force_threshold=3)
        base = datetime(2026, 10, 28, 10, 0, 0)
        for i in range(3):
            mon.ingest(_evt("LOGIN_FAILURE", user=f"u{i}", at=base + timedelta(seconds=i)))
        assert mon.alerts() == []

    def test_anomalous_hours_alert(self):
        mon = SecurityMonitor()
        fired = mon.ingest(_evt("LOGIN_SUCCESS", at=datetime(2026, 10, 28, 3, 0, 0)))
        assert len(fired) == 1
        assert fired[0].rule_name == "anomalous_hours"
        assert fired[0].severity == Severity.MEDIUM
        assert fired[0].quarantine is False

    def test_business_hours_no_anomaly(self):
        mon = SecurityMonitor()
        assert mon.ingest(_evt("LOGIN_SUCCESS", at=datetime(2026, 10, 28, 14, 0, 0))) == []

    def test_data_exfiltration_over_threshold(self):
        mon = SecurityMonitor(exfil_threshold_bytes=1000, exfil_window_seconds=3600)
        base = datetime(2026, 10, 28, 10, 0, 0)
        mon.ingest(_evt("DATA_ACCESS", user="u1", at=base, volume_bytes=600))
        fired = mon.ingest(_evt("DATA_ACCESS", user="u1", at=base + timedelta(seconds=60), volume_bytes=600))
        assert len(fired) == 1
        assert fired[0].rule_name == "data_exfiltration"
        assert fired[0].severity == Severity.HIGH

    def test_data_exfiltration_critical_and_quarantine_at_2x(self):
        mon = SecurityMonitor(exfil_threshold_bytes=1000)
        base = datetime(2026, 10, 28, 10, 0, 0)
        fired = mon.ingest(_evt("DATA_ACCESS", user="u1", at=base, volume_bytes=2500))
        assert fired[0].severity == Severity.CRITICAL
        assert fired[0].quarantine is True

    def test_no_exfil_below_threshold(self):
        mon = SecurityMonitor(exfil_threshold_bytes=1000)
        fired = mon.ingest(_evt("DATA_ACCESS", user="u1", at=datetime(2026, 10, 28, 10, 0, 0), volume_bytes=500))
        assert fired == []

    def test_alert_acknowledgement(self):
        mon = SecurityMonitor()
        fired = mon.ingest(_evt("LOGIN_SUCCESS", at=datetime(2026, 10, 28, 3, 0, 0)))
        alert_id = fired[0].alert_id
        assert mon.ack_alert(alert_id) is True
        assert mon.alerts()[0].details["acknowledged"] is True
        assert mon.ack_alert("missing-id") is False

    def test_severity_filter(self):
        mon = SecurityMonitor(exfil_threshold_bytes=1000)
        mon.ingest(_evt("LOGIN_SUCCESS", at=datetime(2026, 10, 28, 3, 0, 0)))  # MEDIUM
        mon.ingest(_evt("DATA_ACCESS", user="u1", at=datetime(2026, 10, 28, 10, 0, 0), volume_bytes=2500))
        high_only = mon.alerts(min_severity=Severity.HIGH)
        assert all(a.severity.rank >= Severity.HIGH.rank for a in high_only)
        assert len(high_only) == 1

    def test_manual_quarantine_and_release(self):
        mon = SecurityMonitor()
        mon.quarantine_user("u9", reason="suspected compromise")
        assert mon.is_quarantined("u9") is True
        assert mon.release_user("u9") is True
        assert mon.is_quarantined("u9") is False

    def test_stats_summary(self):
        mon = SecurityMonitor()
        mon.ingest(_evt("LOGIN_FAILURE", user="u1", at=datetime(2026, 10, 28, 10, 0, 0)))
        stats = mon.stats()
        assert stats["events_ingested"] == 1
        assert stats["alerts_total"] == 0
        assert "MEDIUM" in stats["alerts_by_severity"]

    def test_ingest_batch(self):
        mon = SecurityMonitor()
        alerts = mon.ingest_batch(
            [
                _evt("LOGIN_FAILURE", user="u1", at=datetime(2026, 10, 28, 10, 0, 0)),
                _evt("LOGIN_FAILURE", user="u1", at=datetime(2026, 10, 28, 10, 0, 1)),
            ]
        )
        assert alerts == []


# ============================================================================
# Integration - modules working together
# ============================================================================


class TestV27Integration:
    def _build(self):
        auth = AuthManager(pbkdf2_iterations=1000)
        user = auth.create_user("quan", "S3curePass!", roles=["viewer"])
        rbac = RBACEngine()
        rbac.add_role(Role("viewer", [Permission("document", "read")]))
        rbac.assign_role_to_user(user.user_id, "viewer")
        audit = AuditLog()
        monitor = SecurityMonitor()
        return auth, user, rbac, audit, monitor

    def test_login_success_logged_and_no_alert(self):
        auth, user, rbac, audit, monitor = self._build()
        session = auth.authenticate("quan", "S3curePass!")
        entry = audit.append(
            user_id=user.user_id, action="LOGIN", resource_type="session",
            resource_id=session.token[:8], status="SUCCESS",
        )
        monitor.ingest(
            SecurityEvent(
                event_type="LOGIN_SUCCESS",
                user_id=user.user_id,
                timestamp=datetime(2026, 10, 28, 10, 0, 0),
            )
        )
        assert audit.verify_chain() is True
        assert audit.query(user_id=user.user_id, action="LOGIN")
        assert monitor.alerts() == []
        assert entry.status == "SUCCESS"

    def test_failed_logins_end_to_end_lockout_audit_alert(self):
        auth, user, rbac, audit, monitor = self._build()
        base = datetime(2026, 10, 28, 10, 0, 0)
        for i in range(5):
            with pytest.raises(InvalidCredentialsError):
                auth.authenticate("quan", "wrong")
            monitor.ingest(
                SecurityEvent(
                    event_type="LOGIN_FAILURE",
                    user_id=user.user_id,
                    timestamp=base + timedelta(seconds=i),
                )
            )
            audit.append(
                user_id=user.user_id, action="LOGIN", resource_type="session",
                resource_id="attempt", status="FAILURE",
            )
        # Auth manager locked the account...
        with pytest.raises(AccountLockedError):
            auth.authenticate("quan", "S3curePass!")
        # ...monitor raised a brute-force alert...
        assert any(a.rule_name == "brute_force" for a in monitor.alerts())
        # ...and the audit chain remains intact.
        assert audit.verify_chain() is True

    def test_rbac_gates_data_access_with_audit(self):
        auth, user, rbac, audit, monitor = self._build()
        denied = rbac.check(user.user_id, "salary", "read")
        assert denied.allowed is False  # viewer cannot read salary data
        audit.append(
            user_id=user.user_id, action="READ", resource_type="salary",
            resource_id="s-1", status="FAILURE", details={"reason": denied.reason},
        )
        allowed = rbac.check(user.user_id, "document", "read")
        assert allowed.allowed is True
        audit.append(user_id=user.user_id, action="READ", resource_type="document", resource_id="d-1")
        assert len(audit.query(user_id=user.user_id)) == 2
        assert audit.verify_chain() is True

    def test_encrypted_field_stored_in_audit_safe_display(self):
        auth, user, rbac, audit, monitor = self._build()
        svc = EncryptionService()
        secret_field = svc.encrypt_field("internal-memo-contents")
        # Only the envelope (never plaintext) is displayed/logged.
        audit.append(
            user_id=user.user_id, action="CREATE", resource_type="document",
            resource_id="d-9", details={"payload": secret_field.to_dict()},
        )
        blob = repr(audit.entries[0].to_dict())
        assert "internal-memo-contents" not in blob
        assert svc.decrypt_field(secret_field) == "internal-memo-contents"

    def test_gdpr_erasure_after_activity(self):
        auth, user, rbac, audit, monitor = self._build()
        session = auth.authenticate("quan", "S3curePass!")
        audit.append(user_id=user.user_id, action="LOGIN", resource_type="session", resource_id="s")
        audit.append(user_id=user.user_id, action="READ", resource_type="document", resource_id="d")
        result = audit.right_to_erasure(user.user_id)
        assert result["entries_affected"] == 2
        assert audit.query(user_id=user.user_id) == []
        tombstones = audit.query(action="GDPR_ERASURE")
        assert tombstones and tombstones[0].details["subject"] == user.user_id

    def test_mfa_login_flow_with_monitoring(self):
        auth, user, rbac, audit, monitor = self._build()
        secret = auth.enable_mfa(user.user_id)
        # One wrong MFA code -> LOGIN_FAILURE event -> no alert yet.
        with pytest.raises(InvalidCredentialsError):
            auth.authenticate("quan", "S3curePass!", mfa_code="000000", now=1_700_000_000)
        monitor.ingest(_evt("LOGIN_FAILURE", user=user.user_id, at=datetime(2026, 10, 28, 10, 0, 0)))
        # Correct TOTP within the +/- 1 step window.
        from quan_ai_brain.security._totp import hotp_at

        code = hotp_at(secret, 1_700_000_000 // 30)
        session = auth.authenticate("quan", "S3curePass!", mfa_code=code, now=1_700_000_000)
        assert session.mfa_verified is True
        assert monitor.alerts() == []

    def test_oauth_session_feeds_rbac_check(self):
        auth, user, rbac, audit, monitor = self._build()
        client_secret = auth.register_oauth_client("web-app")
        code = auth.oauth_authorize("web-app", user.user_id, "https://app/callback")
        token = auth.oauth_token_exchange("web-app", client_secret, code.code, "https://app/callback")
        info = auth.oauth_introspect(token.access_token)
        assert info["user_id"] == user.user_id
        assert rbac.check(info["user_id"], "document", "read").allowed is True
        assert rbac.check(info["user_id"], "salary", "delete").allowed is False

    def test_full_pipeline_snapshot(self):
        """Smoke test: every module participates once."""
        auth, user, rbac, audit, monitor = self._build()
        svc = EncryptionService()
        # 1. Login + MFA
        secret = auth.enable_mfa(user.user_id)
        code = hotp_at(secret, 1_700_000_000 // 30)
        session = auth.authenticate("quan", "S3curePass!", mfa_code=code, now=1_700_000_000)
        # 2. Authorize
        decision = rbac.check(user.user_id, "document", "read")
        # 3. Access encrypted data
        field = svc.encrypt_field("doc-1-body")
        plaintext = svc.decrypt_field(field)
        # 4. Audit + monitor
        audit.append(user_id=user.user_id, action="READ", resource_type="document", resource_id="doc-1")
        monitor.ingest(_evt("DATA_ACCESS", user=user.user_id, at=datetime(2026, 10, 28, 10, 0, 0)))
        assert decision.allowed and plaintext == "doc-1-body"
        assert audit.verify_chain() and monitor.alerts() == []
