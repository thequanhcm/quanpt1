"""Nhóm D — Critical Thinking.

D1_hypotheses_on_real_incident: sinh giả thuyết trên sự cố thật
("Vì sao Pi5 mất kết nối?"). Baseline V0 PARTIAL: 0 hypotheses vì
retrieval không có evidence → không sinh được giả thuyết (đúng về
fail-honest, sai về usefulness). Khung support/against CÓ trong code.
"""

from __future__ import annotations

from probe_base import Probe, ProbeResult, build_result

INCIDENT_QUESTION = "Vì sao Pi5 mất kết nối?"


class D1HypothesesOnRealIncident(Probe):
    probe_id = "D1_hypotheses_on_real_incident"
    group = "D_CRITICAL"
    title = "Sinh giả thuyết trên sự cố thật (Pi5 mất kết nối)"

    def run(self, ctx) -> ProbeResult:
        sys_path_added = False
        if str(ctx.src_root) not in __import__("sys").path:
            __import__("sys").path.insert(0, str(ctx.src_root))
            sys_path_added = True
        try:
            from quan_ai_brain.memory.deep_memory import DeepMemoryStore
            from quan_ai_brain.cognition.logical_reasoning import (
                LogicalReasoningEngine,
            )

            store = DeepMemoryStore(ctx.brain_copy)
            engine = LogicalReasoningEngine(store)
            res = engine.answer_question(INCIDENT_QUESTION)
            n_hyp = len(res.get("hypotheses") or [])
            n_missing = len(res.get("missing_info") or [])
            ctype = res.get("conclusion_type")
            has_support_against = "support" in res and "against" in res

            # PARTIAL giữ nghĩa V0: khung có (support/against/missing) nhưng
            # 0 hypotheses vì retrieval trống → phụ thuộc retrieval (gap C2).
            if n_hyp > 0 and has_support_against:
                outcome = "PASS"
                detail = f"{n_hyp} giả thuyết sinh được; missing_info={n_missing}"
            elif has_support_against or n_missing > 0:
                outcome = "PARTIAL"
                detail = (
                    f"{n_hyp} hypotheses — cùng gốc rễ C2: retrieval không có "
                    f"evidence → không sinh được giả thuyết. Khung support/"
                    f"against CÓ trong code (missing_info={n_missing}, "
                    f"conclusion_type={ctype})."
                )
            else:
                outcome = "FAIL"
                detail = f"Không có khung hypotheses lẫn support/against (type={ctype})"
            return build_result(
                self, outcome, detail,
                f"V9 on real incident ('{INCIDENT_QUESTION}')",
                extras={
                    "n_hypotheses": n_hyp,
                    "n_missing_info": n_missing,
                    "conclusion_type": ctype,
                    "has_support_against_frame": has_support_against,
                },
            )
        finally:
            if sys_path_added:
                try:
                    __import__("sys").path.remove(str(ctx.src_root))
                except ValueError:
                    pass


PROBES = [D1HypothesesOnRealIncident]
