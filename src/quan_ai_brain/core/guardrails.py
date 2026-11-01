"""Output Guardrails for QUAN AI BRAIN.

Validates and sanitizes LLM and assistant responses to prevent credential leaks,
path traversal disclosures, and ensure safe, compliant output.
"""
from __future__ import annotations

import re
from typing import Any

from quan_ai_brain.core.redaction import redact_text

# Dangerous patterns to detect or sanitize
_FORBIDDEN_FILE_PATTERNS = [
    re.compile(r"(?i)\.env\b"),
    re.compile(r"(?i)id_rsa\b"),
    re.compile(r"(?i)\bcredentials\.json\b"),
    re.compile(r"(?i)id_ed25519\b"),
    re.compile(r"(?i)\bpasswd\b"),
    re.compile(r"(?i)\.aws/credentials\b"),
]

_SCRIPT_INJECTION_RE = re.compile(r"(?i)<script\b[^>]*>.*?</script>", re.DOTALL)


class OutputGuardrails:
    """Verifies assistant outputs against security and privacy invariants."""

    @staticmethod
    def sanitize(text: str) -> tuple[str, list[str]]:
        """Sanitize text response, redact sensitive content, and return detected warnings."""
        if not text:
            return "", ["EMPTY_RESPONSE"]

        warnings: list[str] = []

        # 1. Apply core credential redaction
        sanitized = redact_text(text)
        if sanitized != text:
            warnings.append("CREDENTIAL_REDACTED")

        # 2. Check for script injection attempts
        if _SCRIPT_INJECTION_RE.search(sanitized):
            sanitized = _SCRIPT_INJECTION_RE.sub("[BLOCKED_SCRIPT_TAG]", sanitized)
            warnings.append("SCRIPT_TAG_SANITIZED")

        # 3. Check for sensitive file references
        for pattern in _FORBIDDEN_FILE_PATTERNS:
            if pattern.search(sanitized):
                sanitized = pattern.sub("[PROTECTED_SYSTEM_PATH]", sanitized)
                warnings.append("SYSTEM_PATH_MASKED")

        return sanitized, warnings

    @staticmethod
    def validate_reply(text: str) -> bool:
        """Return True if reply meets minimum quality and non-empty criteria."""
        return bool(text and text.strip())

    @staticmethod
    def analyze_grounding(text: str, context: Any | None = None) -> Any:
        """Evaluates whether the reply text is grounded in verified memory or inferred.
        
        Analyzes overlap with context.used_memories (verification status, source refs).
        """
        from quan_ai_brain.cognition.models import GroundingAnalysis, GroundingStatus
        from quan_ai_brain.memory.models import VerificationStatus

        if not text or not text.strip():
            return GroundingAnalysis(
                status=GroundingStatus.GENERAL_INFERENCE,
                confidence="LOW",
                grounding_notes="Empty response text.",
            )

        if context is None or not getattr(context, "used_memories", None):
            return GroundingAnalysis(
                status=GroundingStatus.GENERAL_INFERENCE,
                confidence="MEDIUM",
                grounding_notes="Phản hồi dựa trên suy luận mô hình; chưa có trích dẫn từ bộ nhớ dài hạn.",
            )

        clean_text = text.lower()
        matched_verified_ids: list[str] = []
        matched_user_ids: list[str] = []
        cited_sources: list[str] = []

        for mem in context.used_memories:
            content = getattr(mem, "content", "").lower()
            source = getattr(mem, "source_ref", "") or "internal_memory"
            mem_id = getattr(mem, "memory_id", "")
            status = getattr(mem, "verification_status", "")

            # Tokenize content into words >= 4 chars
            words = [w for w in re.findall(r"[\w\u00C0-\u1EF9]+", content) if len(w) >= 4]
            if words:
                match_count = sum(1 for w in words if w in clean_text)
                ratio = match_count / len(words)
                if ratio >= 0.25 or content in clean_text:
                    if status == VerificationStatus.VERIFIED.value:
                        matched_verified_ids.append(mem_id)
                        if source not in cited_sources:
                            cited_sources.append(source)
                    elif status == VerificationStatus.USER_PROVIDED.value:
                        matched_user_ids.append(mem_id)
                        if source not in cited_sources:
                            cited_sources.append(source)

        if matched_verified_ids and matched_user_ids:
            return GroundingAnalysis(
                status=GroundingStatus.MIXED,
                confidence="HIGH",
                cited_memory_ids=matched_verified_ids + matched_user_ids,
                cited_sources=cited_sources,
                grounding_notes="Phản hồi kết hợp dữ liệu đã xác minh và thông tin do chủ sở hữu cung cấp.",
            )
        elif matched_verified_ids:
            return GroundingAnalysis(
                status=GroundingStatus.VERIFIED_FACT,
                confidence="HIGH",
                cited_memory_ids=matched_verified_ids,
                cited_sources=cited_sources,
                grounding_notes="Phản hồi được chứng thực bởi bộ nhớ dài hạn đã xác minh độc lập.",
            )
        elif matched_user_ids:
            return GroundingAnalysis(
                status=GroundingStatus.USER_PROVIDED,
                confidence="MEDIUM",
                cited_memory_ids=matched_user_ids,
                cited_sources=cited_sources,
                grounding_notes="Phản hồi dựa trên sở thích / dữ liệu do người dùng cung cấp.",
            )
        else:
            return GroundingAnalysis(
                status=GroundingStatus.GENERAL_INFERENCE,
                confidence="MEDIUM",
                cited_memory_ids=[],
                cited_sources=[],
                inferred_elements=["general_llm_reasoning"],
                grounding_notes="Dựa trên suy luận tổng quát của mô hình; không có trích dẫn trực tiếp từ bộ nhớ.",
            )

