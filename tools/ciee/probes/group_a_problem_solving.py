"""Nhóm A — Problem Solving.

A1_outcome_verifier_available: kiểm tra chuỗi "làm xong phải xác minh" có
tồn tại trong code thật (PlanOrchestrator có bước verify kết quả step) —
nền tảng để CHERRY không tự đánh giá là ĐÚNG chỉ vì nó đã LÀM.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from probe_base import Probe, ProbeResult, build_result


class A1OutcomeVerifierAvailable(Probe):
    probe_id = "A1_outcome_verifier_available"
    group = "A_PROBLEM"
    title = "Outcome verifier có sẵn trong orchestration (không tin self-report)"

    def run(self, ctx) -> ProbeResult:
        sys.path.insert(0, str(ctx.src_root))
        from quan_ai_brain.orchestration import plan_orchestrator as po

        src = Path(po.__file__).read_text(encoding="utf-8", errors="ignore")
        verify_hooks = sorted(set(re.findall(
            r"\w*verif\w*", src, re.IGNORECASE)))
        has_step_verify = "_verify_step_result" in src or "verification_method" in src

        ok = bool(verify_hooks) and has_step_verify
        detail = (
            f"PlanOrchestrator có {len(verify_hooks)} khái niệm verification: "
            f"{verify_hooks[:6]}{'...' if len(verify_hooks) > 6 else ''}"
        )
        return build_result(
            self,
            "PASS" if ok else "FAIL",
            detail,
            f"import {po.__name__} OK; file={Path(po.__file__).name}",
            extras={"verify_symbols": verify_hooks, "has_step_verify": has_step_verify},
        )


PROBES = [A1OutcomeVerifierAvailable]
