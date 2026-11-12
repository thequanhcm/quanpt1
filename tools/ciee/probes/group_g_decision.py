"""Nhóm G — Decision & Governance.

G1_risk_levels_exist : thang rủi ro R0–R5 phải có 6 mức trong policy.py.
G2_r4_fail_closed    : R4 (approval) phải fail-closed — verify() trả False
                       cho card giả. Chạy trên SNAPSHOT COPY của
                       governance.db + workspace tạm để Q4BatchLedger không
                       chạm file thật (R1 read-only).
"""

from __future__ import annotations

import sys

from probe_base import Probe, ProbeResult, build_result


class G1RiskLevelsExist(Probe):
    probe_id = "G1_risk_levels_exist"
    group = "G_DECISION"
    title = "Thang rủi ro R0–R5 tồn tại (6 mức)"

    def run(self, ctx) -> ProbeResult:
        sys.path.insert(0, str(ctx.src_root))
        from quan_ai_brain.governance.policy import RiskLevel

        levels = [m.name for m in RiskLevel]
        expected = ["R0", "R1", "R2", "R3", "R4", "R5"]
        ok = levels == expected or set(expected).issubset(set(levels))
        return build_result(
            self,
            "PASS" if ok else "FAIL",
            f"levels={levels}",
            "governance/policy.py RiskLevel",
            extras={"levels": levels},
        )


class G2R4FailClosed(Probe):
    probe_id = "G2_r4_fail_closed"
    group = "G_DECISION"
    title = "R4 fail-closed: verify() trả False cho fake card"

    def run(self, ctx) -> ProbeResult:
        from data_access import make_snapshot

        sys.path.insert(0, str(ctx.src_root))
        import tempfile

        from quan_ai_brain.governance.approval_verifier import (
            GovernanceApprovalVerifier,
        )

        # governance.db COPY + workspace tạm: Q4BatchLedger ghi (nếu có ghi)
        # chỉ vào temp, KHÔNG vào E:/BRAIN.
        gov_snap = make_snapshot(ctx.governance_db, ctx.tmp_dir,
                                 "governance_g2_copy.db")
        tmp_ws = tempfile.mkdtemp(prefix=f"ciee_g2ws_{ctx.run_id}_")
        verifier = GovernanceApprovalVerifier(gov_snap, workspace=tmp_ws)
        result_bool = verifier.verify(
            "FAKE-CARD-XYZ",
            approved_by="ciee-probe",
            approval_evidence="ciee-fake-evidence",
        )
        ok = (result_bool is False)  # fail-closed: bool False, không raise, không True
        return build_result(
            self,
            "PASS" if ok else "FAIL",
            f"verify('FAKE-CARD-XYZ') → {result_bool!r} ({type(result_bool).__name__}) "
            f"{'— fail-closed đúng contract' if ok else '— VI PHẠM fail-closed'}",
            "approval_verifier.GovernanceApprovalVerifier.verify trên snapshot COPY",
            extras={
                "fake_verify_result": result_bool,
                "governance_snapshot": str(gov_snap),
            },
        )


PROBES = [G1RiskLevelsExist, G2R4FailClosed]
