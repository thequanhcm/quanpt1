from quan_ai_brain.core.redaction import redact_text, redact_value


def test_redacts_common_assignment_patterns():
    original = 'password="top-secret" API_KEY=abc123 access_token:xyz Bearer eyJhbGciOiJ'
    result = redact_text(original)
    assert "top-secret" not in result
    assert "abc123" not in result
    assert "xyz" not in result
    assert "eyJhbGciOiJ" not in result
    assert "[REDACTED]" in result


def test_redacts_nested_json_like_values():
    result = redact_value({"detail": "client_secret=shhh", "items": ["Bearer token123"]})
    assert "shhh" not in str(result)
    assert "token123" not in str(result)
