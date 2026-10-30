"""Cognitive Executive Coordinator for QUAN AI BRAIN.

Translates natural language goals into structured, stepwise TaskPlans,
performs independent R0-R5 risk assessment, and enforces governance policies.
THIS MODULE PLANS ONLY — NO ACTIONS ARE EXECUTED.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any
import uuid

from quan_ai_brain.cognition.cognitive_state import (
    BeliefItem,
    BeliefKind,
    CognitiveState,
    ContradictionRecord,
    UncertaintyItem,
)
from quan_ai_brain.cognition.context_builder import PromptContextBuilder
from quan_ai_brain.cognition.models import BuiltContext, MemoryQuery
from quan_ai_brain.cognition.retrieval import CognitiveRetriever
from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.governance.policy import ActionRequest, DecisionStatus, PolicyEngine, RiskLevel
from quan_ai_brain.llm.models import FallbackMode, LLMRequest, LLMResponse
from quan_ai_brain.llm.provider import LLMProvider
from quan_ai_brain.planning.models import StepStatus, TaskPlan, TaskStep, TaskStatus

# High-risk keywords for independent heuristic risk escalation
_R5_KEYWORDS = (
    "rm -rf", "delete all", "drop database", "drop table", "shutdown host",
    "override secret", "disable safety", "wipe", "format disk", "destroy",
    "rmdir /s", "kill -9 1", "rm -r /", "chmod 777 /",
)

_R4_KEYWORDS = (
    "restart service", "modify config", "update firmware", "grant permission",
    "deploy", "production change", "truncate", "alter table", "write production",
)

_R2_KEYWORDS = (
    "write file", "save report", "create file", "export json", "write log",
)

# Adversarial prompt injection keywords (Master Prompt V3 §X)
_ADVERSARIAL_INJECTION_KEYWORDS = (
    "bỏ qua quy tắc an toàn", "ignore safety", "override policy",
    "giả lập approval", "fake approval", "bypass governance",
    "tự cấp quyền", "disable guardrails", "ignore previous instructions",
    "bypass safety", "bỏ qua hàng rào", "bỏ qua kiểm tra",
)


def _extract_json_object(text: str) -> dict[str, Any]:
    """Robust extraction of JSON object from LLM response text."""
    clean = text.strip()
    # Try markdown json block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
    if match:
        clean = match.group(1)
    else:
        # Try outermost braces
        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            clean = clean[start : end + 1]

    data = json.loads(clean)
    if not isinstance(data, dict):
        raise ValueError("Parsed JSON root must be an object (dict)")
    return data


class ExecutiveCoordinator:
    """Orchestrates goal analysis, plan generation, and governance verification."""

    def __init__(
        self,
        workspace: str | Path,
        llm_provider: LLMProvider | None = None,
        policy_engine: PolicyEngine | None = None,
        retriever: CognitiveRetriever | None = None,
        context_builder: PromptContextBuilder | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.llm_provider = llm_provider or LLMProvider()
        self.policy_engine = policy_engine or PolicyEngine(self.workspace)
        self.retriever = retriever
        self.context_builder = context_builder or PromptContextBuilder()

    def plan(
        self,
        goal: str,
        *,
        project_scope: str | None = None,
        model: str = "qwen2.5:7b",
        fallback: bool | None = None,
        max_chars: int = 4000,
    ) -> TaskPlan:
        """Create a validated, risk-assessed TaskPlan for a given goal.

        NO ACTIONS ARE EXECUTED. This is strictly a planning and validation step.
        """
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("Plan goal must be a non-empty string")

        clean_goal = redact_text(goal.strip())
        memory_refs: list[str] = []
        context_text = ""
        plan_warnings: list[str] = []

        # 0. Initialize CognitiveState model & Epistemic Grounding
        cog_state = CognitiveState(
            task_id=f"plan-cog-{uuid.uuid4().hex[:8]}",
            goal=clean_goal,
        )
        cog_state.add_belief(
            statement=f"Mục tiêu do người dùng chỉ định: {clean_goal}",
            kind=BeliefKind.FACT_USER,
            source_ref="user_request",
            confidence=1.0,
            verification_status="user_provided",
        )

        # Detect adversarial injection keywords in goal (Master Prompt V3 §X)
        goal_lower = clean_goal.lower()
        adversarial_flag = any(kw in goal_lower for kw in _ADVERSARIAL_INJECTION_KEYWORDS)
        if adversarial_flag:
            cog_state.add_uncertainty(
                unknown_key="adversarial_instruction_detected",
                description="Phát hiện dấu hiệu chỉ thị đối kháng (adversarial prompt) nhằm can thiệp quy tắc an toàn.",
                why_critical="Chính sách an toàn QUAN AI BRAIN cấm can thiệp hoặc ghi đè quy tắc an toàn qua prompt.",
                suggested_verification_action="Từ chối nâng quyền và yêu cầu thẩm định phê duyệt tường minh từ Anh Quân.",
                requires_owner_input=True,
            )
            plan_warnings.append("CẢNH BÁO: Phát hiện chỉ thị có dấu hiệu bypass an toàn; lập kế hoạch yêu cầu phê duyệt bảo mật nghiêm ngặt.")

        # 1. Retrieve cognitive memory if retriever is available
        if self.retriever is not None:
            retrieval_query = MemoryQuery(
                query=clean_goal,
                project_scope=project_scope,
                top_k=5,
                max_chars=max_chars,
            )
            retrieval_res = self.retriever.retrieve(retrieval_query)
            memory_refs = [m.memory_id for m in retrieval_res.memories]

            stale_mems: list[str] = []
            seen_topics: dict[str, Any] = {}
            for rm in retrieval_res.memories:
                m_meta = getattr(rm, "metadata", {}) or {}
                rm_tags = getattr(rm, "tags", []) or []
                is_stale = bool(m_meta.get("is_stale") or m_meta.get("expired") or ("stale" in rm_tags))
                if is_stale:
                    stale_mems.append(rm.memory_id)
                    b_kind = BeliefKind.UNKNOWN
                    conf = 0.1
                elif rm.verification_status in ("verified", "observed"):
                    b_kind = BeliefKind.FACT_RETRIEVED
                    conf = max(0.6, rm.score)
                elif rm.verification_status == "candidate":
                    # Master Prompt V3 §X.7: CANDIDATE knowledge must never be treated as verified fact
                    b_kind = BeliefKind.HYPOTHESIS
                    conf = 0.3
                else:
                    b_kind = BeliefKind.INFERENCE
                    conf = 0.5

                cog_state.add_belief(
                    statement=rm.content,
                    kind=b_kind,
                    source_ref=f"memory:{rm.memory_id}",
                    confidence=conf,
                    verification_status=rm.verification_status,
                )

                # Check topic contradictions
                topic_key = m_meta.get("topic") or m_meta.get("subject") or (rm_tags[0] if rm_tags else None)
                if topic_key:
                    if topic_key in seen_topics:
                        prev_rm = seen_topics[topic_key]
                        if prev_rm.content != rm.content:
                            cog_state.record_contradiction(
                                topic=str(topic_key),
                                claim_a=prev_rm.content,
                                source_a=f"memory:{prev_rm.memory_id}",
                                status_a=prev_rm.verification_status,
                                claim_b=rm.content,
                                source_b=f"memory:{rm.memory_id}",
                                status_b=rm.verification_status,
                                notes="Phát hiện mâu thuẫn giữa 2 bản ghi tri thức cùng chủ đề.",
                            )
                    else:
                        seen_topics[topic_key] = rm

            if stale_mems:
                plan_warnings.append(
                    f"CẢNH BÁO DỮ LIỆU CŨ (Stale State): {len(stale_mems)} bản ghi tri thức đã cũ; kết luận cần được làm mới trước khi thực thi."
                )
                cog_state.add_uncertainty(
                    unknown_key="stale_knowledge_retrieved",
                    description=f"Tri thức {', '.join(stale_mems)} đã hết hạn hoặc bị đánh dấu cũ.",
                    why_critical="Dữ liệu cũ có thể làm sai lệch kế hoạch so với hiện trạng thực tế.",
                    suggested_verification_action="Đọc dữ liệu hiện hành trực tiếp qua thao tác R0.",
                )

            if not memory_refs:
                cog_state.add_uncertainty(
                    unknown_key="no_context_found",
                    description="Không tìm thấy tri thức hoặc kinh nghiệm đã lưu liên quan đến mục tiêu.",
                    why_critical="Kế hoạch được lập chủ yếu dựa trên suy diễn mô hình, thiếu căn cứ dữ liệu cục bộ.",
                    suggested_verification_action="Thu thập dữ liệu hoặc xác nhận lại yêu cầu.",
                )

            built_ctx = self.context_builder.build(
                user_query=clean_goal,
                retrieval=retrieval_res,
                max_chars=max_chars,
                project_scope=project_scope,
            )
            context_text = built_ctx.rendered_context

        # 2. Build LLM planning prompt
        system_prompt = (
            "You are the Executive Planning Coordinator of QUAN AI BRAIN.\n"
            "Your task is to analyze the goal and context, then generate a stepwise TaskPlan.\n"
            "CRITICAL CONSTRAINTS:\n"
            "1. Respond ONLY with a valid JSON object matching the requested schema.\n"
            "2. Propose actions in logical sequence.\n"
            "3. Assess risk levels truthfully (0=Read, 1=Analyze, 2=Workspace write, 3=External low impact, 4=Significant change, 5=Dangerous/prohibited).\n"
            "4. NEVER execute any commands. You are planning only."
        )

        user_prompt = (
            f"GOAL: {clean_goal}\n\n"
            f"CONTEXT:\n{context_text or '(No relevant memories found)'}\n\n"
            "Respond ONLY with a JSON object following this exact schema:\n"
            "{\n"
            '  "summary": "<short plan summary>",\n'
            '  "steps": [\n'
            "    {\n"
            '      "step_id": "step-1",\n'
            '      "name": "<action_identifier>",\n'
            '      "description": "<detailed action description>",\n'
            '      "expected_output": "<verifiable outcome>",\n'
            '      "risk_level": <integer 0 to 5>,\n'
            '      "preconditions": ["<precondition 1>"],\n'
            '      "verification_method": "<how output is verified>",\n'
            '      "dependencies": [],\n'
            '      "target_path": "<optional workspace relative path or null>"\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        # 3. Call LLMProvider
        req = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=0.1,  # Low temperature for deterministic planning
            timeout_seconds=120.0,
        )
        llm_resp = self.llm_provider.generate(req, allow_fallback=fallback)

        # 4. Handle LLM failure
        if not llm_resp.success:
            return TaskPlan(
                goal=clean_goal,
                status=TaskStatus.FAILED,
                summary="LLM planning generation failed",
                source=llm_resp.provider,
                warnings=[llm_resp.warning or "LLM request failed"],
                validation_errors=[llm_resp.error_message or "Unknown LLM failure"],
                memory_refs=memory_refs,
                cognitive_state=cog_state,
            )

        # 5. Parse JSON proposal
        try:
            plan_data = _extract_json_object(llm_resp.text)
        except Exception as exc:
            # LLM did not return valid JSON; do NOT guess or fabricate steps!
            return TaskPlan(
                goal=clean_goal,
                status=TaskStatus.FAILED,
                summary="Failed to parse LLM proposal into structured plan schema",
                source="mock" if llm_resp.is_mock else llm_resp.provider,
                warnings=["LLM response was not valid JSON; manual review required."],
                validation_errors=[f"JSON parse error: {exc}"],
                memory_refs=memory_refs,
                cognitive_state=cog_state,
            )

        summary = str(plan_data.get("summary", "")).strip() or f"Plan for: {clean_goal}"
        raw_steps = plan_data.get("steps", [])
        if not isinstance(raw_steps, list) or not raw_steps:
            return TaskPlan(
                goal=clean_goal,
                status=TaskStatus.FAILED,
                summary="Plan rejected: LLM returned zero steps",
                source="mock" if llm_resp.is_mock else llm_resp.provider,
                validation_errors=["Plan must contain at least one step"],
                memory_refs=memory_refs,
                cognitive_state=cog_state,
            )

        # 6. Process each step and perform INDEPENDENT GOVERNANCE VERIFICATION
        processed_steps: list[TaskStep] = []
        if llm_resp.is_mock:
            plan_warnings.append("MOCK MODE — Plan generated via synthetic mock, not actual LLM inference.")

        for idx, raw_s in enumerate(raw_steps, start=1):
            if not isinstance(raw_s, dict):
                continue

            sid = str(raw_s.get("step_id", f"step-{idx}")).strip() or f"step-{idx}"
            name = str(raw_s.get("name", f"step_{idx}")).strip() or f"step_{idx}"
            desc = str(raw_s.get("description", "")).strip() or name
            output = str(raw_s.get("expected_output", "")).strip() or "Verified output"

            # Parse proposed risk
            try:
                proposed_risk = int(raw_s.get("risk_level", 0))
                proposed_risk = max(0, min(5, proposed_risk))
            except (ValueError, TypeError):
                proposed_risk = 0

            # Independent Risk Escalation: Check for dangerous keywords in action/desc
            effective_risk = self._evaluate_inherent_risk(name, desc, proposed_risk)

            preconditions = tuple(str(p).strip() for p in raw_s.get("preconditions", []) if str(p).strip())
            verif_method = str(raw_s.get("verification_method", "")).strip() or "Standard check"
            deps = tuple(str(d).strip() for d in raw_s.get("dependencies", []) if str(d).strip())
            target_path = raw_s.get("target_path")
            if target_path is not None:
                target_path = str(target_path).strip() or None

            # Independent Policy Engine authorization
            action_req = ActionRequest(
                action=name,
                risk=RiskLevel(effective_risk),
                target_path=target_path,
            )
            decision = self.policy_engine.authorize(action_req)

            # Determine StepStatus and approval requirement based on policy verdict
            step_warnings: list[str] = []
            requires_approval = False
            step_status = StepStatus.PROPOSED

            if decision.status == DecisionStatus.BLOCKED:
                step_status = StepStatus.BLOCKED
                step_warnings.append(f"Hard-blocked by Policy Engine: {decision.reason}")
            elif decision.status == DecisionStatus.APPROVAL_REQUIRED:
                step_status = StepStatus.PENDING_APPROVAL
                requires_approval = True
                step_warnings.append("Explicit owner approval required prior to execution.")
            elif decision.status == DecisionStatus.DENY:
                step_status = StepStatus.BLOCKED
                step_warnings.append(f"Action denied by Policy Engine: {decision.reason}")
            elif decision.status == DecisionStatus.ALLOW_WITH_NOTICE:
                step_status = StepStatus.READY_FOR_REVIEW
                step_warnings.append("Notice required upon execution.")
            elif decision.status == DecisionStatus.ALLOW:
                step_status = StepStatus.VALIDATED

            if effective_risk > proposed_risk:
                step_warnings.append(
                    f"Risk escalated independently from R{proposed_risk} to R{effective_risk} by Coordinator."
                )

            step_obj = TaskStep(
                name=name,
                description=desc,
                expected_output=output,
                risk_level=effective_risk,
                requires_approval=requires_approval,
                step_id=sid,
                sequence=idx,
                preconditions=preconditions,
                verification_method=verif_method,
                dependencies=deps,
                status=step_status,
                policy_status=decision.status.value,
                policy_reason=decision.reason,
                target_path=decision.normalized_target or target_path,
                warnings=tuple(step_warnings),
            )
            processed_steps.append(step_obj)

        # 7. Metacognitive Evaluation & Decision Dossier
        metacog = cog_state.evaluate_metacognition()
        if not metacog.can_conclude:
            if metacog.abstention_reason:
                plan_warnings.append(f"CẢNH BÁO NHẬN THỨC (Metacognitive Abstention): {metacog.abstention_reason}")

        # If adversarial flag or unresolved contradiction, enforce approval
        requires_approval_forced = adversarial_flag or (metacog.unresolved_contradiction_count > 0)

        # Construct TaskPlan
        task_plan = TaskPlan(
            goal=clean_goal,
            steps=processed_steps,
            summary=summary,
            source="mock" if llm_resp.is_mock else llm_resp.provider,
            warnings=plan_warnings,
            memory_refs=memory_refs,
            requires_approval=requires_approval_forced,
            cognitive_state=cog_state,
        )

        # 8. Validate plan integrity
        try:
            task_plan.validate()
        except ValueError as exc:
            task_plan.status = TaskStatus.FAILED
            task_plan.validation_errors.append(str(exc))

        # If metacognition abstained due to critical unknowns or contradictions, ensure plan stays in WAITING_APPROVAL
        if not metacog.can_conclude and task_plan.status == TaskStatus.READY_FOR_REVIEW:
            task_plan.status = TaskStatus.WAITING_APPROVAL

        return task_plan

    def _evaluate_inherent_risk(self, name: str, description: str, proposed_risk: int) -> int:
        """Independently assess risk based on description content; never trust LLM alone."""
        combined = f"{name} {description}".lower()

        # Check R5 prohibitions
        for kw in _R5_KEYWORDS:
            if kw in combined:
                return RiskLevel.R5.value

        # Check R4 significant changes
        for kw in _R4_KEYWORDS:
            if kw in combined:
                return max(proposed_risk, RiskLevel.R4.value)

        # Check R2 workspace file operations
        for kw in _R2_KEYWORDS:
            if kw in combined:
                return max(proposed_risk, RiskLevel.R2.value)

        return proposed_risk

    # Backward-compatible alias
    create_plan = plan

