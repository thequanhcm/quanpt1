"""Cognition package for QUAN AI BRAIN.

Provides cognitive memory retrieval, deterministic ranking, autonomous thinking,
and structured prompt context building for local LLM inference.
"""
from quan_ai_brain.cognition.autonomous_mind import (
    AutonomousMind,
    CogitationMode,
    GLOBAL_AUTONOMOUS_MIND,
    InternalThought,
)
from quan_ai_brain.cognition.capability_registry import (
    CapabilityRegistry,
    CapabilityStatus,
    SystemCapability,
)
from quan_ai_brain.cognition.context_builder import DEFAULT_SYSTEM_INSTRUCTIONS, PromptContextBuilder
from quan_ai_brain.cognition.embedding import BGEEmbeddingService, cosine_similarity
from quan_ai_brain.cognition.executive_persona import (
    DEFAULT_DIRECTIVES,
    DigitalIdentityProfile,
    ExecutiveDirective,
    ExecutivePersona,
    QUAN_AI_BRAIN_IDENTITY,
    validate_identity_profile,
)
from quan_ai_brain.cognition.models import (
    MEMORY_TYPE_WEIGHTS,
    VERIFICATION_STATUS_WEIGHTS,
    BuiltContext,
    GroundingAnalysis,
    GroundingStatus,
    MemoryQuery,
    RetrievalResult,
    RetrievedMemory,
)
from quan_ai_brain.cognition.retrieval import CognitiveRetriever

__all__ = [
    "AutonomousMind",
    "BGEEmbeddingService",
    "BuiltContext",
    "CapabilityRegistry",
    "CapabilityStatus",
    "CogitationMode",
    "CognitiveRetriever",
    "DEFAULT_DIRECTIVES",
    "DEFAULT_SYSTEM_INSTRUCTIONS",
    "DigitalIdentityProfile",
    "ExecutiveDirective",
    "ExecutivePersona",
    "GLOBAL_AUTONOMOUS_MIND",
    "GroundingAnalysis",
    "GroundingStatus",
    "InternalThought",
    "MEMORY_TYPE_WEIGHTS",
    "MemoryQuery",
    "PromptContextBuilder",
    "QUAN_AI_BRAIN_IDENTITY",
    "RetrievalResult",
    "RetrievedMemory",
    "SystemCapability",
    "VERIFICATION_STATUS_WEIGHTS",
    "cosine_similarity",
]
