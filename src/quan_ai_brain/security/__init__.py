"""QUAN AI BRAIN - V27 Security & Compliance package (SIMULATED skeleton).

Modules:
- authentication: AuthManager (PBKDF2, sessions, TOTP MFA, lockout,
  simulated OAuth2/OIDC flow)
- rbac: RBAC + simple ABAC, role hierarchy, deny-by-default
- audit_logging: hash-chained append-only audit log, GDPR export/erasure
- data_protection: DEMO XOR-stream EncryptionService + masking utilities
- security_monitoring: SecurityMonitor rule engine (brute-force, odd-hour
  access, exfiltration volume) with severity + quarantine flags

WARNING: this package is a security SKELETON for Sprint V27, not a
production security stack. The EncryptionService cipher is a demo-only
XOR-stream (no AES in stdlib); the OAuth/OIDC flow is simulated without any
network or real identity provider.
"""

from quan_ai_brain.security.audit_logging import (
    AuditEntry,
    AuditLog,
    ChainIntegrityError,
)
from quan_ai_brain.security.authentication import (
    AccountLockedError,
    AuthError,
    AuthManager,
    AuthorizationCode,
    InvalidCredentialsError,
    MFARequiredError,
    OAuthError,
    OAuthToken,
    Session,
    SessionExpiredError,
    User,
)
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

__all__ = [
    "AuditEntry",
    "AuditLog",
    "ChainIntegrityError",
    "AccountLockedError",
    "AuthError",
    "AuthManager",
    "AuthorizationCode",
    "InvalidCredentialsError",
    "MFARequiredError",
    "OAuthError",
    "OAuthToken",
    "Session",
    "SessionExpiredError",
    "User",
    "EncryptedField",
    "EncryptionService",
    "mask_email",
    "mask_phone",
    "mask_string",
    "mask_token",
    "ABACEngine",
    "ABACPolicy",
    "AccessDecision",
    "AuthorizationEngine",
    "Permission",
    "RBACEngine",
    "Role",
    "Alert",
    "SecurityEvent",
    "SecurityMonitor",
    "Severity",
]
