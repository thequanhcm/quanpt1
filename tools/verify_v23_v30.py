#!/usr/bin/env python3
"""Verification runner for V23-V30 sprint modules.

Runs the per-sprint test files added by the sprint implementation,
prints an honest per-sprint and combined summary, and exits non-zero
if any test fails. Standard library only.

Usage:
    python tools/verify_v23_v30.py            # run all sprint test files
    python tools/verify_v23_v30.py --quick    # list files only, no pytest
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

SPRINT_TEST_FILES = {
    "V23": "tests/test_v23_advanced.py",
    "V24": "tests/test_v24_backend.py",
    "V25": "tests/test_v25_insights_modules.py",
    "V26": "tests/test_v26_self_learning.py",
    "V27": "tests/test_v27_security_modules.py",
    "V28": "tests/test_v28_enterprise_modules.py",
    "V29": "tests/test_v29_ai_modules.py",
    "V30": "tests/test_v30_scaling_modules.py",
}

# Sprint deliverable modules that must exist after implementation
SPRINT_MODULE_FILES = {
    "V23": [
        "src/quan_ai_brain/learning/federated_orchestrator.py",
        "src/quan_ai_brain/cognition/collaboration.py",
        "src/quan_ai_brain/optimization/performance_optimizer.py",
        "src/quan_ai_brain/security/hardening.py",
    ],
    "V24": [
        "src/quan_ai_brain/nlp/query_engine.py",
        "src/quan_ai_brain/voice/voice_interface.py",
        "src/quan_ai_brain/mobile/offline_sync.py",
        "src/quan_ai_brain/mobile/notifications.py",
    ],
    "V25": [
        "src/quan_ai_brain/analytics/insights_engine.py",
        "src/quan_ai_brain/analytics/report_generator.py",
        "src/quan_ai_brain/analytics/graph_visualization.py",
        "src/quan_ai_brain/analytics/recommendation_system.py",
    ],
    "V26": [
        "src/quan_ai_brain/optimization/self_learning_engine.py",
        "src/quan_ai_brain/optimization/adaptive_algorithms.py",
        "src/quan_ai_brain/optimization/improvement_loop.py",
        "src/quan_ai_brain/optimization/intelligent_cache.py",
    ],
    "V27": [
        "src/quan_ai_brain/security/authentication.py",
        "src/quan_ai_brain/security/rbac.py",
        "src/quan_ai_brain/security/audit_logging.py",
        "src/quan_ai_brain/security/data_protection.py",
        "src/quan_ai_brain/security/security_monitoring.py",
    ],
    "V28": [
        "src/quan_ai_brain/gateway/api_gateway.py",
        "src/quan_ai_brain/gateway/connectors.py",
        "src/quan_ai_brain/gateway/message_queue.py",
        "src/quan_ai_brain/gateway/webhooks.py",
        "src/quan_ai_brain/gateway/versioning.py",
    ],
    "V29": [
        "src/quan_ai_brain/ai/neural_symbolic.py",
        "src/quan_ai_brain/ai/common_sense.py",
        "src/quan_ai_brain/ai/explainable_ai.py",
        "src/quan_ai_brain/ai/transfer_learning.py",
        "src/quan_ai_brain/ai/multi_agent.py",
    ],
    "V30": [
        "src/quan_ai_brain/scaling/horizontal_scaling.py",
        "src/quan_ai_brain/scaling/performance_optimizer.py",
        "src/quan_ai_brain/scaling/disaster_recovery.py",
        "src/quan_ai_brain/scaling/monitoring.py",
        "src/quan_ai_brain/scaling/business_intelligence.py",
    ],
}

SPRINT_REPORTS = {
    "V23": "reports/V23_COMPLETION_REPORT.md",
    "V24": "reports/V24_COMPLETION_REPORT.md",
    "V25": "reports/V25_COMPLETION_REPORT.md",
    "V26": "reports/V26_COMPLETION_REPORT.md",
    "V27": "reports/V27_COMPLETION_REPORT.md",
    "V28": "reports/V28_COMPLETION_REPORT.md",
    "V29": "reports/V29_COMPLETION_REPORT.md",
    "V30": "reports/V30_COMPLETION_REPORT.md",
}


def find_python() -> str:
    venv = WORKSPACE / ".venv" / "Scripts" / "python.exe"
    if venv.exists():
        return str(venv)
    return sys.executable


def check_files() -> tuple[list[str], list[str]]:
    missing_modules: list[str] = []
    missing_tests: list[str] = []
    missing_reports: list[str] = []
    for sprint, rel in SPRINT_TEST_FILES.items():
        if not (WORKSPACE / rel).exists():
            missing_tests.append(f"{sprint}: {rel}")
    for sprint, modules in SPRINT_MODULE_FILES.items():
        for rel in modules:
            if not (WORKSPACE / rel).exists():
                missing_modules.append(f"{sprint}: {rel}")
    for sprint, rel in SPRINT_REPORTS.items():
        if not (WORKSPACE / rel).exists():
            missing_reports.append(f"{sprint}: {rel}")
    return missing_modules + missing_tests + missing_reports, []


def run_one(test_file: str) -> tuple[bool, str]:
    python = find_python()
    cmd = [
        python, "-m", "pytest", test_file, "-q", "--no-header",
        "-p", "no:cacheprovider", "--tb=short",
    ]
    proc = subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True, text=True, timeout=900)
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0
    tail = "\n".join(out.strip().splitlines()[-6:])
    return ok, tail


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Only check files exist")
    args = parser.parse_args()

    missing, _ = check_files()
    if missing:
        print("MISSING ARTIFACTS:")
        for m in missing:
            print("  -", m)
        return 2

    print("All expected modules, tests, and reports exist.")
    if args.quick:
        return 0

    print()
    all_ok = True
    for sprint in sorted(SPRINT_TEST_FILES):
        tf = SPRINT_TEST_FILES[sprint]
        ok, tail = run_one(tf)
        status = "PASS" if ok else "FAIL"
        print(f"[{sprint}] {tf} -> {status}")
        if not ok:
            all_ok = False
            print(tail)
    print()
    print("VERDICT:", "ALL SPRINT TESTS PASS" if all_ok else "FAILURES DETECTED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
