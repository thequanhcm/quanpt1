"""Best-effort credential redaction for logs and handoff text.

This filter is defense-in-depth, not a substitute for never collecting secrets.
"""
from __future__ import annotations

import re
from typing import Any

_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_AUTH_ASSIGNMENT_RE = re.compile(
    r"(?i)([\"']?\b(?:api[_ -]?key|(?:access[_ -]?|refresh[_ -]?)?token|"
    r"password|passwd|secret|authorization|client[_ -]?secret)[\"']?\s*[:=]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_URL_CREDENTIAL_RE = re.compile(r"(?i)(https?://)[^/@\s:]+:[^/@\s]+@")
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(?:^|[^a-z0-9])(?:api[_ -]?key|(?:access[_ -]?|refresh[_ -]?)?token|"
    r"password|passwd|secret|authorization|client[_ -]?secret|private[_ -]?key)(?:$|[^a-z0-9])"
)


def redact_text(value: str) -> str:
    """Mask common credential forms without trying to parse arbitrary documents."""
    value = _BEARER_RE.sub("Bearer [REDACTED]", value)
    value = _AUTH_ASSIGNMENT_RE.sub(r"\1[REDACTED]", value)
    value = _URL_CREDENTIAL_RE.sub(r"\1[REDACTED]@", value)
    return value


def redact_value(value: Any) -> Any:
    """Recursively redact strings inside simple JSON-compatible structures."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            safe_key = redact_text(str(key))
            if _SENSITIVE_KEY_RE.search(str(key)):
                cleaned[safe_key] = "[REDACTED]"
            else:
                cleaned[safe_key] = redact_value(item)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    return value
