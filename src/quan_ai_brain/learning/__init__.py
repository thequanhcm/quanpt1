"""Self-Learning & Self-Upgrade Engine V1 for QUAN AI BRAIN.

Enables evidence-based observation, local-safe research, candidate knowledge
quarantine, isolated experiment design, and owner-gated upgrade proposals.
"""
from __future__ import annotations

from quan_ai_brain.learning.engine import SelfLearningEngine
from quan_ai_brain.learning.models import (
    ExperimentPlan,
    ExperimentResult,
    LearningGap,
    ResearchDossier,
    UpgradeProposal,
    UpgradeProposalStatus,
)

__all__ = [
    "ExperimentPlan",
    "ExperimentResult",
    "LearningGap",
    "ResearchDossier",
    "SelfLearningEngine",
    "UpgradeProposal",
    "UpgradeProposalStatus",
]
