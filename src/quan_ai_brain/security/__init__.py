"""security package — TASK-AGENTIC-SEC-1 (khung ATTT Agentic AI MIT + Viettel).

Modules:
- input_shield: quét prompt injection ở ĐẦU VÀO (EchoLeak CVE-2025-32711).
- trifecta_guard: Lethal Trifecta (slide 13) — đủ 3 cờ → FORCE PROPOSE.
- untrusted_label: nhãn dữ liệu không tin cậy bọc context ngoài (slide 7).
"""
from quan_ai_brain.security.input_shield import (
    BLOCKED_REPLY,
    InputInjectionShield,
    ShieldResult,
    Verdict,
    get_shield,
    scan_input,
)
from quan_ai_brain.security.trifecta_guard import (
    TrifectaDecision,
    TrifectaFlags,
    check_and_upgrade,
    evaluate_task,
)
from quan_ai_brain.security.untrusted_label import (
    label_untrusted,
    strip_untrusted_labels,
    wrap_external_block,
)
from quan_ai_brain.security import audit_sources

__all__ = [
    "BLOCKED_REPLY",
    "InputInjectionShield",
    "ShieldResult",
    "Verdict",
    "get_shield",
    "scan_input",
    "TrifectaDecision",
    "TrifectaFlags",
    "check_and_upgrade",
    "evaluate_task",
    "label_untrusted",
    "strip_untrusted_labels",
    "wrap_external_block",
]
