"""Dynamic LLM Router for QUAN AI BRAIN.

Routes prompts to the optimal model based on query complexity, task type,
and latency budget (e.g. lightweight fast model for conversational chat,
heavyweight 7B model for planning and deep reasoning).
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence


@dataclass(frozen=True)
class RoutingDecision:
    """Outcome of model routing decision."""
    model: str
    tier: str  # 'fast', 'reasoning', 'explicit'
    reason: str
    is_fallback: bool = False


class LLMRouter:
    """Selects the most suitable LLM based on task characteristics.

    Sprint 2 routing (owner-approved, evidence: Sprint 1 Vietnamese benchmark —
    GLM-5.3-Flash 88.5% keyword accuracy / 1.33s avg vs Qwen2.5:1.5b 69.2% / 1.76s):
    - fast + reasoning tiers -> NetMind GLM-5.3-Flash (cloud, streamed).
    - deep tier -> NetMind Qwen3.5-122B (always-reasons planner, ~22s) for
      research-grade analysis only.
    - Local Qwen models remain the offline/privacy fallback path (never removed).
    """

    DEFAULT_FAST_MODEL = "zai-org/GLM-5.3-Flash"
    FALLBACK_FAST_MODEL = "qwen2.5:0.5b"
    DEFAULT_REASONING_MODEL = "zai-org/GLM-5.3-Flash"
    DEFAULT_DEEP_MODEL = "Qwen/Qwen3.5-122B-A10B-FP8"
    LOCAL_REASONING_FALLBACK_MODEL = "qwen2.5:7b"

    _COMPLEX_PATTERNS = [
        re.compile(r"(?i)\b(?:plan|planning|architecture|decompose|dag|algorithm|refactor|benchmark)\b"),
        re.compile(r"(?i)\b(?:lập kế hoạch|kế hoạch|phân tích|kiến trúc|chia nhỏ|thuật toán|đánh giá|suy luận sâu)\b"),
        re.compile(r"(?i)\b(?:governance|security audit|containment|sandbox|policy engine)\b"),
    ]

    _DEEP_PATTERNS = [
        re.compile(r"(?i)(phân tích chuyên sâu|nghiên cứu sâu|đọc và phân tích tài liệu|tổng hợp báo cáo dài)"),
        re.compile(r"(?i)(deep dive|comprehensive analysis|exhaustive research|research-grade)"),
    ]

    def __init__(
        self,
        default_fast: str = DEFAULT_FAST_MODEL,
        default_reasoning: str = DEFAULT_REASONING_MODEL,
    ) -> None:
        self.default_fast = default_fast
        self.default_reasoning = default_reasoning

    def is_deep_query(self, query: str, task_hint: str = "chat") -> bool:
        """Evaluate if query requires the deep reasoning tier (research-grade)."""
        if task_hint in ("deep_research", "document_analysis"):
            return True
        if len(query.strip()) > 1200:
            return True
        for pattern in self._DEEP_PATTERNS:
            if pattern.search(query):
                return True
        return False

    def is_complex_query(self, query: str, task_hint: str = "chat") -> bool:
        """Evaluate if query requires heavy reasoning tier."""
        if task_hint in ("planning", "reasoning", "learning", "audit", "governance"):
            return True

        if len(query.strip()) > 300:
            return True

        for pattern in self._COMPLEX_PATTERNS:
            if pattern.search(query):
                return True

        return False

    def route(
        self,
        query: str,
        *,
        task_hint: str = "chat",
        explicit_model: str | None = None,
        available_models: Sequence[str] | None = None,
    ) -> RoutingDecision:
        """Determine the model to dispatch the request to."""
        # 1. Caller explicit override
        if explicit_model and explicit_model.strip():
            target = explicit_model.strip()
            # If available_models provided, check if it exists
            if available_models and not self._is_model_present(target, available_models):
                # Fallback to default reasoning model
                return RoutingDecision(
                    model=self.default_reasoning,
                    tier="fallback",
                    reason=f"Explicit model '{target}' not in available models; fell back to {self.default_reasoning}",
                    is_fallback=True,
                )
            return RoutingDecision(
                model=target,
                tier="explicit",
                reason=f"Caller specified explicit model '{target}'",
                is_fallback=False,
            )

        # 2. Heuristic tier classification (deep first — strictest match wins).
        if self.is_deep_query(query, task_hint=task_hint):
            target = self.DEFAULT_DEEP_MODEL
            tier = "deep"
            reason = "Research-grade analysis requested; deep reasoning tier selected"
        elif self.is_complex_query(query, task_hint=task_hint):
            target = self.default_reasoning
            tier = "reasoning"
            reason = "Complex reasoning, planning, or long query detected"
        else:
            target = self.default_fast
            tier = "fast"
            reason = "Conversational chat, low-latency target"

        # 3. Model availability validation
        if available_models:
            if not self._is_model_present(target, available_models):
                # If fast model not available, try fallback fast or reasoning
                if tier == "fast" and self._is_model_present(self.FALLBACK_FAST_MODEL, available_models):
                    return RoutingDecision(
                        model=self.FALLBACK_FAST_MODEL,
                        tier="fast",
                        reason=f"Preferred {target} not available, using fallback fast model {self.FALLBACK_FAST_MODEL}",
                        is_fallback=True,
                    )
                # Cloud reasoning target missing (offline/no key): keep the tier,
                # swap to the local reasoning model — tier semantics preserved.
                if self._is_model_present(self.LOCAL_REASONING_FALLBACK_MODEL, available_models):
                    return RoutingDecision(
                        model=self.LOCAL_REASONING_FALLBACK_MODEL,
                        tier=tier,
                        reason=f"Preferred {target} not available, using local reasoning model {self.LOCAL_REASONING_FALLBACK_MODEL}",
                        is_fallback=True,
                    )
                if self._is_model_present(self.default_reasoning, available_models):
                    return RoutingDecision(
                        model=self.default_reasoning,
                        tier="reasoning",
                        reason=f"Preferred model {target} not available, fell back to {self.default_reasoning}",
                        is_fallback=True,
                    )
                # Fallback to whatever first model is available
                first_avail = next(iter(available_models), self.default_reasoning)
                return RoutingDecision(
                    model=first_avail,
                    tier="fallback",
                    reason=f"Preferred model {target} not available, using available model {first_avail}",
                    is_fallback=True,
                )

        return RoutingDecision(
            model=target,
            tier=tier,
            reason=reason,
            is_fallback=False,
        )

    @staticmethod
    def _is_model_present(model: str, available_models: Sequence[str]) -> bool:
        target = model.lower().strip()
        for m in available_models:
            m_lower = m.lower()
            if m_lower == target or m_lower.startswith(f"{target}:") or target.startswith(f"{m_lower}:"):
                return True
        return False
