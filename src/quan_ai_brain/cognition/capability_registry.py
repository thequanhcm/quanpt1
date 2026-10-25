"""Capability Registry for QUAN AI BRAIN.

Provides an auditable, truthful ground-truth registry of system capabilities,
modules, tools, and satellite ecosystems to prevent LLM hallucinations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CapabilityStatus(str, Enum):
    VERIFIED_ACTIVE = "VERIFIED_ACTIVE"          # Implemented, tested, and actively functioning
    IMPLEMENTED_UNTESTED = "IMPLEMENTED_UNTESTED"  # Code exists but not E2E tested
    INERT_STAGING = "INERT_STAGING"              # Implemented in inert mode, pending owner sign-off
    EXTERNAL_PLANNED = "EXTERNAL_PLANNED"        # Sibling ecosystem project, preserved, not integrated
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"          # Planned future feature, not yet in codebase


@dataclass(frozen=True)
class SystemCapability:
    capability_id: str
    name: str
    description: str
    domain: str
    status: CapabilityStatus
    risk_level: int
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    evidence_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "status": self.status.value,
            "risk_level": self.risk_level,
            "dependencies": list(self.dependencies),
            "evidence_notes": self.evidence_notes,
        }


SYSTEM_CAPABILITIES: list[SystemCapability] = [
    SystemCapability(
        capability_id="long_term_memory",
        name="Trí Nhớ Dài Hạn (Long-Term Memory)",
        description="Lưu trữ và truy xuất bền vững các sự kiện, sở thích, quy trình và tri thức vào SQLite WAL.",
        domain="Memory & Knowledge",
        status=CapabilityStatus.IMPLEMENTED_UNTESTED,
        risk_level=0,
        dependencies=("data/brain.db", "MemoryStore"),
        evidence_notes="Code implemented (sqlite_store.py 523 lines); DB tables exist but 0 episodes/memories/candidates — E2E test pending Sprint 3",
    ),
    SystemCapability(
        capability_id="local_llm_inference",
        name="Suy Luận AI Cục Bộ (Local Ollama Engine)",
        description="Giao tiếp với mô hình AI cục bộ qwen2.5:7b và qwen2.5:1.5b trên máy cá nhân không gửi dữ liệu ra ngoài.",
        domain="Cognitive Inference",
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=0,
        dependencies=("http://127.0.0.1:11434", "OllamaClient"),
        evidence_notes="Active on loopback with <1ms pre-flight socket probe",
    ),
    SystemCapability(
        capability_id="safe_task_planning",
        name="Lập Kế Hoạch Nhiệm Vụ An Toàn (DAG Executive Planning)",
        description="Phân rã mục tiêu thành các bước hành động có đồ thị phụ thuộc (DAG) và đánh giá rủi ro R0-R5 độc lập.",
        domain="Planning & Governance",
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=1,
        dependencies=("ExecutiveCoordinator", "PolicyEngine"),
        evidence_notes="Zero-execution planning; prevents LLM self-escalation",
    ),
    SystemCapability(
        capability_id="tool_sandbox",
        name="Hộp Cát Công Cụ An Toàn (Safe Tool Sandbox R0-R2)",
        description="Thực thi các công cụ đọc tệp, liệt kê thư mục, kiểm tra sức khỏe với chốt chặn quyền Chủ nhân.",
        domain="Execution Sandbox",
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=2,
        dependencies=("SafeToolSandbox", "PathGuard"),
        evidence_notes="Owner consent first; sensitive files protected",
    ),
    SystemCapability(
        capability_id="self_learning_v1",
        name="Động Cơ Tự Học & Nâng Cấp (Self-Learning Engine V1)",
        description="Tự quan sát lỗi, tự nghiên cứu tài liệu, tự sinh bản vá (diff) và cách ly tri thức ứng viên chờ Chủ nhân duyệt.",
        domain="Evolution & Learning",
        status=CapabilityStatus.IMPLEMENTED_UNTESTED,
        risk_level=2,
        dependencies=("SelfLearningEngine", "data/learning_sandbox.db"),
        evidence_notes="Code implemented (autonomous_mind.py 250 lines); learning_reports.db minimal (28KB) — full learning pipeline pending Sprint 5",
    ),
    SystemCapability(
        capability_id="web_ui_voice",
        name="Giao Diện Web Chat & Giọng Nói (Local Web UI & Voice)",
        description="Bảng điều khiển đồ họa tối sang trọng, hỗ trợ chat bong bóng, thu âm tiếng Việt và đọc to câu trả lời.",
        domain="User Interface",
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=0,
        dependencies=("http://127.0.0.1:8765", "Web Speech API", "SpeechSynthesis"),
        evidence_notes="Served locally via Python standard-library ThreadedHTTPServer",
    ),
    SystemCapability(
        capability_id="os_job_containment",
        name="Kiểm Soát Tiến Trình OS (Win32 Job Object Containment)",
        description="Cơ chế giới hạn tài nguyên RAM/CPU và cô lập tiến trình cấp hệ điều hành Windows.",
        domain="OS Execution",
        status=CapabilityStatus.INERT_STAGING,
        risk_level=4,
        dependencies=("ProcessContainmentConfig", "InertProcessBackend"),
        evidence_notes="Pending owner sign-off in docs/SPRINT6_DESIGN_SIGNOFF.md",
    ),
    SystemCapability(
        capability_id="ecosystem_adapters",
        name="Hệ Sinh Thái Vệ Tinh (DC-COMMAND, Kernel L3, Battery AI, BOT)",
        description="Các hệ thống vệ tinh chuyên ngành của Chủ nhân, được bảo tồn read-only và kết nối qua adapter.",
        domain="Ecosystem Integration",
        status=CapabilityStatus.EXTERNAL_PLANNED,
        risk_level=4,
        dependencies=(),
        evidence_notes="Preserved read-only; not directly connected in Sprint 1-7",
    ),
    SystemCapability(
        capability_id="universal_software_integration",
        name="Tích Hợp Đa Phần Mềm & Vận Hành Có Kiểm Soát (Universal Software Integration)",
        description="Khám phá cấu trúc, kết nối adapter, kiểm tra quyền, lập kế hoạch DAG, xác minh kết quả thực tế trên hệ thống đích và chủ động phát hiện sự cố.",
        domain="Universal Software Integration",
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=2,
        dependencies=("IntegrationRegistry", "SystemTelemetryConnector", "ResultVerifier", "SafeToolSandbox"),
        evidence_notes="Verified by 20 acceptance tests; bounded autonomy A0-A3 active",
    ),
]


class CapabilityRegistry:
    """Registry providing truthful system capabilities to prompt context builders."""

    def __init__(self, capabilities: list[SystemCapability] | None = None) -> None:
        self._capabilities = list(capabilities or SYSTEM_CAPABILITIES)

    def list_capabilities(self) -> list[SystemCapability]:
        return list(self._capabilities)

    def get_capability(self, capability_id: str) -> SystemCapability | None:
        """Lookup capability by capability_id; returns None if not registered."""
        for cap in self._capabilities:
            if cap.capability_id == capability_id:
                return cap
        return None

    def is_capability_query(self, query: str) -> bool:
        """Detect if the user is asking about Brain's assistants, tools, or capabilities."""
        q = query.lower()
        keywords = (
            "trợ lý", "tro ly", "năng lực", "nang luc", "làm được gì", "lam duoc gi",
            "chức năng", "chuc nang", "bạn là ai", "ban la ai", "em là ai", "em la ai",
            "công cụ", "cong cu", "offline", "ngoại tuyến", "hoạt động thế nào",
            "khả năng", "kha nang"
        )
        return any(kw in q for kw in keywords)

    def format_for_prompt(self) -> str:
        """Format capabilities into an explainable ground-truth prompt section."""
        lines = ["[VERIFIED CAPABILITIES & ARCHITECTURE REALITY]"]
        for cap in self._capabilities:
            status_str = cap.status.value
            lines.append(
                f"- [{cap.name}] (Status: {status_str}, Domain: {cap.domain}, Risk: R{cap.risk_level})\n"
                f"  Mô tả: {cap.description}\n"
                f"  Ghi chú: {cap.evidence_notes}"
            )
        lines.append(
            "IMPORTANT INSTRUCTION: When asked what assistants or capabilities you have, base your answer "
            "strictly on the verified list above. Clearly distinguish between VERIFIED_ACTIVE (ready now), "
            "INERT_STAGING (safely inert), and EXTERNAL_PLANNED (sibling systems like DC-COMMAND/Battery AI not yet connected)."
        )
        return "\n".join(lines)
