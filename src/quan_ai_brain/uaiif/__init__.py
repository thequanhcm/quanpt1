"""UAIIF: Universal Agent Intelligence & Intervention Framework (GĐ1).

Kiến trúc (master prompt v1.0 mục XIII): QUAN AI BRAIN = cognitive core duy nhất;
UAIIF là năng lực chuyên môn mở rộng. Tái sử dụng: ToolRegistry, federation
(SEC-S2), SENTINEL (S3), containment. Pi5 = QPIG tool gateway, không phải não.
"""
from quan_ai_brain.uaiif.agent_knowledge import (
    AGENT_KINDS, INFERRED, LAYERS, OBSERVED, UNKNOWN, VERIFIED,
    UniversalAgentKnowledge)
from quan_ai_brain.uaiif.agent_profile import (
    PROFILE_FIELDS, UniversalAgentProfileStore)
from quan_ai_brain.uaiif.qpig import QPIG

__all__ = [
    "AGENT_KINDS", "INFERRED", "LAYERS", "OBSERVED", "UNKNOWN", "VERIFIED",
    "UniversalAgentKnowledge", "PROFILE_FIELDS", "UniversalAgentProfileStore",
    "QPIG",
]
