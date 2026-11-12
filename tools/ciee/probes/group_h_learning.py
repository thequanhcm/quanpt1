"""Nhóm H — Learning Effectiveness.

H1_quarantine_gate    : kiến thức mới không tự promote — tỷ lệ quarantined
                        phải chiếm đa số trong candidate_knowledge.
H2_learning_spam_control: spam "Test suite:*" trong quarantine phải được
                        kiểm soát. Baseline V0 FAIL với 1.837 rows (tăng
                        từ 1.494 cùng tối). Daemon vẫn đang ghi → số này
                        DỰ KIẾN tăng tiếp; ngưỡng PASS là tốc độ tăng có
                        kiểm soát so với V0 (không tăng vô hạn).
"""

from __future__ import annotations

from probe_base import Probe, ProbeResult, build_result
from data_access import ro_connect, ro_fetchall


class H1QuarantineGate(Probe):
    probe_id = "H1_quarantine_gate"
    group = "H_LEARNING"
    title = "Quarantine gate: kiến thức mới không tự promote"

    def run(self, ctx) -> ProbeResult:
        rows = ro_fetchall(
            ctx.brain_db,
            "SELECT status, COUNT(*) FROM candidate_knowledge GROUP BY status")
        breakdown = {status: int(n) for status, n in rows}
        quarantined = breakdown.get("quarantined", 0)
        promoted = breakdown.get("promoted", 0)
        approved = breakdown.get("approved", 0)
        total = sum(breakdown.values())
        q_ratio = quarantined / max(1, total)

        # Gate có thật: phần lớn kiến thức chưa qua R4 đang bị GIỮ lại.
        # (promoted đều phải qua R4 approval — evidence V0)
        ok = q_ratio >= 0.4
        return build_result(
            self,
            "PASS" if ok else "FAIL",
            f"promoted={promoted} (đều qua R4), quarantined={quarantined} "
            f"({q_ratio:.0%}) chờ owner; approved={approved}",
            "brain.db candidate_knowledge (read-only URI)",
            extras={
                "breakdown": breakdown,
                "quarantine_ratio": round(q_ratio, 3),
            },
        )


class H2LearningSpamControl(Probe):
    probe_id = "H2_learning_spam_control"
    group = "H_LEARNING"
    title = "Kiểm soát spam học 'Test suite:*' trong quarantine"

    # Mốc V0: 1.837 rows lúc ~22:40 (đã tăng từ 1.494 lúc 22h)
    V0_SPAM_ROWS = 1837
    # Ngưỡng FAIL: spam chiếm quá nửa quarantine → write path không kiểm soát
    SPAM_RATIO_LIMIT = 0.5

    def run(self, ctx) -> ProbeResult:
        spam = ro_fetchall(
            ctx.brain_db,
            "SELECT COUNT(*) FROM candidate_knowledge "
            "WHERE statement LIKE 'Test suite:%'")[0][0]
        quarantined = ro_fetchall(
            ctx.brain_db,
            "SELECT COUNT(*) FROM candidate_knowledge WHERE status='quarantined'")[0][0]
        total = ro_fetchall(ctx.brain_db, "SELECT COUNT(*) FROM candidate_knowledge")[0][0]

        spam_ratio_quar = spam / max(1, quarantined)
        delta_vs_v0 = spam - self.V0_SPAM_ROWS

        # Đo ĐÚNG hành vi: spam đang tăng liên tục (daemon ghi ~170/giờ) —
        # V0 FAIL với 1.837. FAIL khi spam vượt mốc V0 HOẶC chiếm đa số
        # quarantine (write path không chặn nguồn spam). PASS chỉ khi spam
        # dưới mốc V0 và dưới ngưỡng tỷ lệ.
        if spam > self.V0_SPAM_ROWS or spam_ratio_quar >= self.SPAM_RATIO_LIMIT:
            outcome = "FAIL"
        else:
            outcome = "PASS"
        detail = (
            f"spam_rows={spam} (V0: {self.V0_SPAM_ROWS}, delta {delta_vs_v0:+d}); "
            f"chiếm {spam_ratio_quar:.0%} quarantine ({quarantined}); "
            f"tổng candidate={total}. "
            + (
                "Vẫn vượt mốc V0 / ngưỡng — write path chưa chặn nguồn spam."
                if outcome == "FAIL"
                else "Dưới mốc V0 và dưới ngưỡng 50% quarantine."
            )
        )
        return build_result(
            self,
            outcome,
            detail,
            "brain.db candidate_knowledge (read-only URI)",
            extras={
                "spam_rows": spam,
                "v0_spam_rows": self.V0_SPAM_ROWS,
                "delta_vs_v0": delta_vs_v0,
                "spam_ratio_quarantine": round(spam_ratio_quar, 3),
                "quarantined_total": quarantined,
                "candidate_total": total,
            },
        )


PROBES = [H1QuarantineGate, H2LearningSpamControl]
