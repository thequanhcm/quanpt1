"""Brain Foundation Contract V1 for QUAN AI BRAIN.

Defines canonical interfaces and data envelopes for agents and components
communicating with the Brain Cognitive Control Plane.
"""
from __future__ import annotations

from quan_ai_brain.contract.control_plane import BrainControlPlane
from quan_ai_brain.contract.models import (
    AgentIdentity,
    AgentTrustLevel,
    AgentType,
    CapabilityRequest,
    EvidenceRecord,
    MemoryProposal,
    TaskOutcome,
    TaskRequest,
    TaskState,
)

__all__ = [
    "AgentIdentity",
    "AgentTrustLevel",
    "AgentType",
    "BrainControlPlane",
    "CapabilityRequest",
    "EvidenceRecord",
    "MemoryProposal",
    "TaskOutcome",
    "TaskRequest",
    "TaskState",
]
