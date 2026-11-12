"""Nhóm E — Metacognition.

E1_metacognition_evaluable: CognitiveState.evaluate_metacognition() phải
trả MetacognitiveEvaluation với các chỉ số định lượng (grounding_score,
unverified_claim_count, can_conclude...).
"""

from __future__ import annotations

import sys

from probe_base import Probe, ProbeResult, build_result


class E1MetacognitionEvaluable(Probe):
    probe_id = "E1_metacognition_evaluable"
    group = "E_METACOG"
    title = "MetacognitiveEvaluation chạy được và có chỉ số định lượng"

    def run(self, ctx) -> ProbeResult:
        sys.path.insert(0, str(ctx.src_root))
        from quan_ai_brain.cognition.cognitive_state import (
            CognitiveClaim,
            CognitiveState,
            MetacognitiveEvaluation,
            VerificationStatus,
        )

        state = CognitiveState(
            task_id="ciee-e1-probe",
            goal="Đánh giá năng lực metacognition của CHERRY",
        )
        # thêm 1 hypothesis chưa verified → unverified_claim_count phải đếm được
        # (evaluate_metacognition chỉ đếm kind INFERENCE/HYPOTHESIS/PREDICTION/UNKNOWN)
        state.beliefs.append(CognitiveClaim(
            claim_id="ciee-e1-unverified",
            statement="Giả thuyết chưa xác minh (probe E1)",
            kind="hypothesis",
            verification_status=VerificationStatus.UNVERIFIED.value,
        ))
        ev = state.evaluate_metacognition()

        quantitative = {
            "grounding_score": getattr(ev, "grounding_score", None),
            "unverified_claim_count": getattr(ev, "unverified_claim_count", None),
            "stale_claim_count": getattr(ev, "stale_claim_count", None),
        }
        # PASS: trả đúng type MetacognitiveEvaluation, có chỉ số định lượng,
        # và hypothesis chưa verified được ĐẾM (không phải type-check suông).
        ok = (
            isinstance(ev, MetacognitiveEvaluation)
            and quantitative["grounding_score"] is not None
            and quantitative["unverified_claim_count"] is not None
            and quantitative["unverified_claim_count"] >= 1
        )
        return build_result(
            self,
            "PASS" if ok else "FAIL",
            f"type={type(ev).__name__}; grounding_score={quantitative['grounding_score']}; "
            f"unverified={quantitative['unverified_claim_count']} "
            f"(hypothesis UNVERIFIED được đếm đúng)",
            "CognitiveState(task_id, goal).evaluate_metacognition()",
            extras=quantitative,
        )


def _default_vs(ctx) -> str:
    try:
        sys.path.insert(0, str(ctx.src_root))
        from quan_ai_brain.cognition.cognitive_state import VerificationStatus
        return VerificationStatus.UNVERIFIED.value
    except Exception:  # noqa: BLE001
        return "?"


PROBES = [E1MetacognitionEvaluable]
