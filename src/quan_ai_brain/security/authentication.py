"""
V27 M1 - Advanced Authentication (SIMULATED security skeleton).

Scope of this module (all in-memory, stdlib only):
- AuthManager: user store hashed with PBKDF2-HMAC (hashlib.pbkdf2_hmac + per-user salt)
- Session tokens generated with secrets.token_hex, TTL + revocation
- MFA TOTP (RFC 6238) implemented locally in security/_totp.py (window +/- 1 step)
- Account lockout after N consecutive failed logins
- OAuth2 / OIDC authorization-code flow SIMULATED: code issuance and token
  exchange are pure in-memory dataclass stubs. NO network calls, NO real
  identity provider, NOT a production OAuth implementation.

This is a security SKELETON for QUAN AI BRAIN Sprint V27. It is explicitly
NOT production-ready: no persistent storage, no rate limiting beyond
lockout counters, no TLS, no HSM-backed secrets.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from quan_ai_brain.security._totp import generate_totp_secret, verify_totp

__all__ = [
    "AuthError",
    "InvalidCredentialsError",
    "AccountLockedError",
    "MFARequiredError",
    "SessionExpiredError",
    "OAuthError",
    "User",
    "Session",
    "AuthorizationCode",
    "OAuthToken",
    "AuthManager",
]

PBKDF2_ITERATIONS = 120_000
DEFAULT_SESSION_TTL_SECONDS = 3600
DEFAULT_MAX_FAILED_ATTEMPTS = 5
DEFAULT_LOCKOUT_SECONDS = 300


class AuthError(Exception):
    """Base authentication error."""


class InvalidCredentialsError(AuthError):
    """Username/password (or MFA code) did not validate."""


class AccountLockedError(AuthError):
    """Account is locked out after too many failed attempts."""


class MFARequiredError(AuthError):
    """MFA code is required to complete authentication."""


class SessionExpiredError(AuthError):
    """Session token is unknown, expired, or revoked."""


class OAuthError(AuthError):
    """OAuth2/OIDC simulated flow error (unknown client, bad code, ...)."""


@dataclass
class User:
    """In-memory user record. Password hash/salt are PBKDF2-HMAC derived."""

    user_id: str
    username: str
    password_hash: bytes
    salt: bytes
    mfa_secret: Optional[str] = None
    mfa_enabled: bool = False
    roles: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    failed_attempts: int = 0
    locked_until: Optional[float] = None

    def to_public_dict(self) -> Dict[str, Any]:
        """Safe view of a user - never includes password material."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "mfa_enabled": self.mfa_enabled,
            "roles": list(self.roles),
            "locked": self.locked_until is not None and time.time() < self.locked_until,
        }


@dataclass
class Session:
    """Server-side session bound to a random bearer token."""

    token: str
    user_id: str
    created_at: float
    expires_at: float
    revoked: bool = False
    mfa_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        # Token itself is intentionally NOT included in dict projections.
        return {
            "user_id": self.user_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
            "mfa_verified": self.mfa_verified,
        }


@dataclass
class AuthorizationCode:
    """SIMULATED OAuth2 authorization code (in-memory, single use)."""

    code: str
    client_id: str
    user_id: str
    redirect_uri: str
    scope: List[str]
    issued_at: float
    expires_in: int = 600
    consumed: bool = False


@dataclass
class OAuthToken:
    """SIMULATED OAuth2/OIDC token response payload."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    id_token: str
    scope: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "id_token": self.id_token,
            "scope": list(self.scope),
        }


class AuthManager:
    """In-memory authentication manager (users, sessions, MFA, lockout,
    simulated OAuth2/OIDC authorization-code flow)."""

    def __init__(
        self,
        session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        max_failed_attempts: int = DEFAULT_MAX_FAILED_ATTEMPTS,
        lockout_seconds: int = DEFAULT_LOCKOUT_SECONDS,
        pbkdf2_iterations: int = PBKDF2_ITERATIONS,
    ) -> None:
        self.session_ttl_seconds = session_ttl_seconds
        self.max_failed_attempts = max_failed_attempts
        self.lockout_seconds = lockout_seconds
        self.pbkdf2_iterations = pbkdf2_iterations
        self._users: Dict[str, User] = {}
        self._sessions: Dict[str, Session] = {}
        # Simulated OAuth clients: client_id -> client_secret
        self._oauth_clients: Dict[str, str] = {}
        self._auth_codes: Dict[str, AuthorizationCode] = {}
        self._oauth_tokens: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # User management (in-memory store)
    # ------------------------------------------------------------------
    @staticmethod
    def hash_password(password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
        """PBKDF2-HMAC-SHA256 password hash (hashlib.pbkdf2_hmac + salt)."""
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)

    def create_user(
        self,
        username: str,
        password: str,
        roles: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> User:
        if username in {u.username for u in self._users.values()}:
            raise AuthError(f"username already exists: {username}")
        uid = user_id or f"usr_{secrets.token_hex(8)}"
        salt = secrets.token_bytes(16)
        user = User(
            user_id=uid,
            username=username,
            password_hash=self.hash_password(password, salt, self.pbkdf2_iterations),
            salt=salt,
            roles=list(roles or []),
            attributes=dict(attributes or {}),
        )
        self._users[uid] = user
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    # ------------------------------------------------------------------
    # Password + MFA authentication
    # ------------------------------------------------------------------
    def authenticate(
        self,
        username: str,
        password: str,
        mfa_code: Optional[str] = None,
        now: Optional[float] = None,
    ) -> Session:
        """Authenticate with password (+ MFA code when enrolled).

        Raises AccountLockedError, InvalidCredentialsError, MFARequiredError.
        Returns a new Session on success.
        """
        now = time.time() if now is None else now
        user = self.get_user_by_username(username)
        if user is None:
            # Compare against a dummy hash to keep timing roughly uniform.
            self.hash_password(password, b"dummy-salt-dummy-salt", self.pbkdf2_iterations)
            raise InvalidCredentialsError("invalid username or password")

        if user.locked_until is not None:
            if now < user.locked_until:
                raise AccountLockedError(
                    f"account locked for another {int(user.locked_until - now)}s"
                )
            # Lockout elapsed: reset counter.
            user.locked_until = None
            user.failed_attempts = 0

        candidate = self.hash_password(password, user.salt, self.pbkdf2_iterations)
        if not hmac.compare_digest(candidate, user.password_hash):
            self._register_failed_attempt(user, now)
            raise InvalidCredentialsError("invalid username or password")

        if user.mfa_enabled:
            if not mfa_code:
                raise MFARequiredError("MFA code required")
            if not verify_totp(user.mfa_secret or "", mfa_code, timestamp=now, window=1):
                self._register_failed_attempt(user, now)
                raise InvalidCredentialsError("invalid MFA code")

        # Success: reset failure counters.
        user.failed_attempts = 0
        user.locked_until = None
        return self.create_session(user.user_id, now=now, mfa_verified=True)

    def _register_failed_attempt(self, user: User, now: float) -> None:
        user.failed_attempts += 1
        if user.failed_attempts >= self.max_failed_attempts:
            user.locked_until = now + self.lockout_seconds

    def enable_mfa(self, user_id: str) -> str:
        """Enroll a user in TOTP MFA; returns the generated secret."""
        user = self._users.get(user_id)
        if user is None:
            raise AuthError(f"unknown user: {user_id}")
        user.mfa_secret = generate_totp_secret()
        user.mfa_enabled = True
        return user.mfa_secret

    def disable_mfa(self, user_id: str) -> None:
        user = self._users.get(user_id)
        if user is None:
            raise AuthError(f"unknown user: {user_id}")
        user.mfa_enabled = False
        user.mfa_secret = None

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def create_session(self, user_id: str, now: Optional[float] = None, mfa_verified: bool = False) -> Session:
        if user_id not in self._users:
            raise AuthError(f"unknown user: {user_id}")
        now = time.time() if now is None else now
        token = secrets.token_hex(32)
        session = Session(
            token=token,
            user_id=user_id,
            created_at=now,
            expires_at=now + self.session_ttl_seconds,
            mfa_verified=mfa_verified,
        )
        self._sessions[token] = session
        return session

    def validate_session(self, token: str, now: Optional[float] = None) -> Session:
        """Return the session for a bearer token or raise SessionExpiredError."""
        now = time.time() if now is None else now
        session = self._sessions.get(token)
        if session is None or session.revoked:
            raise SessionExpiredError("session not found or revoked")
        if now >= session.expires_at:
            raise SessionExpiredError("session expired")
        return session

    def revoke_session(self, token: str) -> None:
        session = self._sessions.get(token)
        if session is not None:
            session.revoked = True

    def active_sessions(self, user_id: str) -> List[Session]:
        return [s for s in self._sessions.values() if s.user_id == user_id and not s.revoked]

    # ------------------------------------------------------------------
    # Simulated OAuth2 / OIDC authorization-code flow
    # ------------------------------------------------------------------
    def register_oauth_client(self, client_id: str) -> str:
        """Register a simulated OAuth client; returns its client_secret."""
        client_secret = secrets.token_hex(16)
        self._oauth_clients[client_id] = client_secret
        return client_secret

    def oauth_authorize(
        self,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scope: Optional[List[str]] = None,
        now: Optional[float] = None,
    ) -> AuthorizationCode:
        """Simulate the authorization endpoint: issue a single-use code.

        SIMULATED: in production this requires an authenticated user agent
        consent step at a real identity provider. Here the caller is trusted.
        """
        now = time.time() if now is None else now
        if client_id not in self._oauth_clients:
            raise OAuthError(f"unknown client_id: {client_id}")
        if user_id not in self._users:
            raise OAuthError(f"unknown user: {user_id}")
        code = AuthorizationCode(
            code=secrets.token_urlsafe(32),
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=list(scope or ["openid"]),
            issued_at=now,
        )
        self._auth_codes[code.code] = code
        return code

    def oauth_token_exchange(
        self,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        now: Optional[float] = None,
    ) -> OAuthToken:
        """Exchange an authorization code for a simulated token set."""
        now = time.time() if now is None else now
        if self._oauth_clients.get(client_id) != client_secret:
            raise OAuthError("invalid client credentials")
        auth_code = self._auth_codes.get(code)
        if auth_code is None:
            raise OAuthError("unknown authorization code")
        if auth_code.client_id != client_id or auth_code.redirect_uri != redirect_uri:
            raise OAuthError("client_id/redirect_uri mismatch")
        if auth_code.consumed:
            raise OAuthError("authorization code already used")
        if now > auth_code.issued_at + auth_code.expires_in:
            raise OAuthError("authorization code expired")
        auth_code.consumed = True

        token = OAuthToken(
            access_token=secrets.token_hex(32),
            token_type="Bearer",
            expires_in=self.session_ttl_seconds,
            refresh_token=secrets.token_hex(24),
            id_token=secrets.token_hex(24),  # NOT a real JWT - simulated stub
            scope=list(auth_code.scope),
        )
        self._oauth_tokens[token.access_token] = {
            "user_id": auth_code.user_id,
            "client_id": client_id,
            "expires_at": now + self.session_ttl_seconds,
            "scope": list(auth_code.scope),
        }
        return token

    def oauth_introspect(self, access_token: str, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Introspect a simulated access token (None when unknown/expired)."""
        now = time.time() if now is None else now
        info = self._oauth_tokens.get(access_token)
        if info is None or now >= info["expires_at"]:
            return None
        return dict(info)
