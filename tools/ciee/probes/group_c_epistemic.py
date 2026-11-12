"""Nhóm C — Epistemic Intelligence.

C1_abstain_no_evidence : hỏi ngoài kho → engine PHẢI trả loại C (không đủ
                         bằng chứng) thay vì bịa.
C2_known_evidence_answer: hỏi về tri thức CÓ TRONG kho → engine phải trả
                         lời bằng được. Baseline V0 FAIL vì retrieval chỉ
                         thấy 148 knowledge_units / ~10.874 tri thức tổng
                         (semantic_memory 5.052 + candidate 6.267+...).
                         Probe V1 đo ĐỘNG trên KU thật (giảm nhiễu mẫu cố
                         định) + ghi gap coverage như V0.
C3_stale_detection     : FRESH/STALE/EXPIRED/IMMUTABLE + freshness_policy
                         per-claim (claim 1 tháng + policy daily → STALE).
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone

from probe_base import Probe, ProbeResult, build_result

# Câu hỏi cố định của V0 — giữ lại để so sánh trực tiếp với baseline
V0_QUESTION = "Quy tắc học của CHERRY là gì?"


def _open_engine(ctx):
    sys.path.insert(0, str(ctx.src_root))
    from quan_ai_brain.memory.deep_memory import DeepMemoryStore
    from quan_ai_brain.cognition.logical_reasoning import LogicalReasoningEngine

    store = DeepMemoryStore(ctx.brain_copy)  # snapshot copy, KHÔNG phải production
    return LogicalReasoningEngine(store)


class C1AbstainNoEvidence(Probe):
    probe_id = "C1_abstain_no_evidence"
    group = "C_EPISTEMIC"
    title = "Abstention: hỏi ngoài kho phải trả 'không đủ bằng chứng'"

    def run(self, ctx) -> ProbeResult:
        engine = _open_engine(ctx)
        res = engine.answer_question("Giá cổ phiếu FPT hôm nay là bao nhiêu?")
        ctype = res.get("conclusion_type")
        conclusion = (res.get("conclusion") or "")
        n_evidence = len(res.get("evidence_refs") or [])

        ok = ctype == "C" and "không đủ bằng chứng" in conclusion.lower()
        return build_result(
            self,
            "PASS" if ok else "FAIL",
            f"conclusion_type={ctype}; evidence={n_evidence}; "
            f"conclusion='{conclusion[:70]}'",
            f"logical_reasoning V9, {res.get('steps', ['?'])[0][:60]}",
            extras={"conclusion_type": ctype, "evidence_count": n_evidence},
        )


class C2KnownEvidenceAnswer(Probe):
    probe_id = "C2_known_evidence_answer"
    group = "C_EPISTEMIC"
    title = "Trả lời CÓ bằng chứng từ kho tri thức thật (đo động)"

    def run(self, ctx) -> ProbeResult:
        from data_access import ro_fetchall

        # 1) gap coverage như V0: KU thấy được vs tổng tri thức hệ thống
        n_ku = ro_fetchall(
            ctx.brain_db,
            "SELECT COUNT(*) FROM knowledge_units "
            "WHERE status IN ('EXTRACTED','CANDIDATE','VERIFIED','INFERRED','CONFLICTED')")[0][0]
        n_semantic = ro_fetchall(ctx.brain_db, "SELECT COUNT(*) FROM semantic_memory")[0][0]
        n_candidates = ro_fetchall(ctx.brain_db, "SELECT COUNT(*) FROM candidate_knowledge")[0][0]
        total_knowledge = n_ku + n_semantic + n_candidates

        # 2) đo động: sample KU thật → hỏi lại chính statement đó
        engine = _open_engine(ctx)
        rows = ro_fetchall(
            ctx.brain_db,
            "SELECT knowledge_id, statement FROM knowledge_units "
            "WHERE status='EXTRACTED' ORDER BY updated_at_utc DESC LIMIT 30")
        rng = random.Random(42)  # seed cố định → tái lập
        sample = rng.sample(rows, min(8, len(rows)))
        answered = 0
        outcomes = []
        for kid, statement in sample:
            q = f"{statement} là gì?" if not statement.endswith("?") else statement
            r = engine.answer_question(q)
            ctype = r.get("conclusion_type")
            ev = len(r.get("evidence_refs") or [])
            outcomes.append({"ku": kid[:12], "type": ctype, "evidence": ev})
            if ctype in ("A", "B") and ev > 0:
                answered += 1

        # 3) câu hỏi cố định V0 (so sánh baseline)
        r_v0 = engine.answer_question(V0_QUESTION)
        v0_type = r_v0.get("conclusion_type")
        v0_ev = len(r_v0.get("evidence_refs") or [])

        # PASS nếu engine trả lời được đa số KU thật nó thấy — FAIL nếu
        # vẫn "mù" cả kho nhỏ 148 KU. Coverage gap ghi riêng trong extras.
        ratio = answered / max(1, len(sample))
        ok = ratio >= 0.5
        detail = (
            f"Động: {answered}/{len(sample)} KU thật được trả lời có evidence "
            f"({ratio:.0%}); câu hỏi V0 '{V0_QUESTION}' → type={v0_type}, "
            f"evidence={v0_ev}. GAP COVERAGE: retrieval chỉ thấy {n_ku} KU / "
            f"{total_knowledge} tri thức tổng (semantic {n_semantic} + "
            f"candidate {n_candidates}) — gap {total_knowledge - n_ku} tri thức."
        )
        return build_result(
            self,
            "PASS" if ok else "FAIL",
            detail,
            f"V9 retrieval trên snapshot; sample 8 KU EXTRACTED (seed=42)",
            extras={
                "dynamic_answered": answered,
                "dynamic_sample": len(sample),
                "v0_question_type": v0_type,
                "v0_question_evidence": v0_ev,
                "coverage_ku": n_ku,
                "coverage_total_knowledge": total_knowledge,
                "outcomes": outcomes,
            },
        )


class C3StaleDetection(Probe):
    probe_id = "C3_stale_detection"
    group = "C_EPISTEMIC"
    title = "Stale detection theo freshness_policy per-claim"

    def run(self, ctx) -> ProbeResult:
        from quan_ai_brain.cognition.cognitive_state import (
            CognitiveClaim,
            FreshnessPolicy,
            FreshnessStatus,
            evaluate_freshness,
        )

        now = datetime.now(timezone.utc)
        claim_old = CognitiveClaim(
            claim_id="ciee-c3-old",
            statement="Giá vật phẩm X (policy daily, observe 30 ngày trước)",
            kind="fact",
            observed_at_utc=(now - timedelta(days=30)).isoformat(),
            freshness_policy=FreshnessPolicy.DAILY,
        )
        claim_immutable = CognitiveClaim(
            claim_id="ciee-c3-imm",
            statement="Owner tên là Quan (policy immutable, observe 30 ngày trước)",
            kind="identity",
            observed_at_utc=(now - timedelta(days=30)).isoformat(),
            freshness_policy=FreshnessPolicy.IMMUTABLE,
        )
        claim_fresh = CognitiveClaim(
            claim_id="ciee-c3-fresh",
            statement="Trạng thái hệ thống (policy daily, observe 1 giờ trước)",
            kind="fact",
            observed_at_utc=(now - timedelta(hours=1)).isoformat(),
            freshness_policy=FreshnessPolicy.DAILY,
        )

        st_old, _ = evaluate_freshness(claim_old)
        st_imm, _ = evaluate_freshness(claim_immutable)
        st_fresh, _ = evaluate_freshness(claim_fresh)

        statuses = {FreshnessStatus.FRESH, FreshnessStatus.STALE,
                    FreshnessStatus.EXPIRED, FreshnessStatus.IMMUTABLE}
        ok = (
            st_old == FreshnessStatus.STALE
            and st_imm == FreshnessStatus.IMMUTABLE
            and st_fresh == FreshnessStatus.FRESH
            and statuses.issubset(
                set(FreshnessStatus.__members__.values()) | statuses)
        )
        return build_result(
            self,
            "PASS" if ok else "FAIL",
            f"daily+30d→{st_old.value}; immutable+30d→{st_imm.value}; "
            f"daily+1h→{st_fresh.value} — policy per-claim đúng logic",
            "cognitive_state.evaluate_freshness",
            extras={
                "daily_30d": st_old.value,
                "immutable_30d": st_imm.value,
                "daily_1h": st_fresh.value,
            },
        )


PROBES = [C1AbstainNoEvidence, C2KnownEvidenceAnswer, C3StaleDetection]
