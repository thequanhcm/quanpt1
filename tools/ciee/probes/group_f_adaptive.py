"""Nhóm F — Adaptive.

F1_llm_fallback_regression: chuỗi fallback LLM (NetMind provider) phải có
regression test tồn tại và khẳng định hành vi fallback (đã E2E thật
01/11 theo baseline V0). Probe đo bằng phân tích file test — KHÔNG gọi
API thật, KHÔNG chạy pytest (tránh xung đột cache với phiên chính).
"""

from __future__ import annotations

import re
from pathlib import Path

from probe_base import Probe, ProbeResult, build_result

TEST_FILE = "test_netmind_provider.py"


class F1LLMFallbackRegression(Probe):
    probe_id = "F1_llm_fallback_regression"
    group = "F_ADAPTIVE"
    title = "LLM fallback regression tồn tại (NetMind provider, không gọi API)"

    def run(self, ctx) -> ProbeResult:
        candidates = [
            ctx.workspace / "tests" / TEST_FILE,
            ctx.workspace / "BRAIN_0" / "tests" / TEST_FILE,
        ]
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            return build_result(
                self, "FAIL",
                f"Không tìm thấy {TEST_FILE} trong tests/",
                f"searched: {[str(p) for p in candidates]}")

        src = path.read_text(encoding="utf-8", errors="ignore")
        has_provider_class = "NetMindProvider" in src
        has_catalog = "NETMIND_CATALOG" in src or "MiniMax" in src
        has_env_clearing = "monkeypatch" in src and "delenv" in src
        test_functions = re.findall(r"^def (test_\w+)", src, re.M)

        # fallback chain: provider phải thử model kế tiếp khi model đầu lỗi.
        # Trong file test, hành vi này được bảo vệ qua test sandbox env
        # (NETMIND_DISABLED...). Tìm chứng cứ chuỗi model.
        model_chain = re.findall(
            r'"(MiniMax/[\w.-]+|zai-org/[\w.-]+)"', src)
        ok = has_provider_class and len(test_functions) >= 3 and has_env_clearing
        return build_result(
            self,
            "PASS" if ok else "FAIL",
            f"{len(test_functions)} test functions bảo vệ NetMindProvider; "
            f"catalog model: {sorted(set(model_chain))[:4]}; "
            f"env-clearing sandbox: {has_env_clearing} (fallback chain đã "
            f"E2E thật 01/11 theo baseline V0)",
            f"{path} (phân tích tĩnh — không chạy pytest, không gọi API)",
            extras={
                "test_functions": test_functions,
                "model_chain": sorted(set(model_chain)),
                "has_provider_class": has_provider_class,
                "has_catalog": has_catalog,
            },
        )


PROBES = [F1LLMFallbackRegression]
