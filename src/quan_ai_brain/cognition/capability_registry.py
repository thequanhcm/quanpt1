"""Capability Registry for QUAN AI BRAIN.

Provides an auditable, truthful ground-truth registry of system capabilities,
modules, tools, and satellite ecosystems to prevent LLM hallucinations.
"""
from __future__ import annotations


# (12/11/2026) Loader secret tập trung
import sys as _sys
from pathlib import Path
_SECRET_DIR = Path('E:/BRAIN/user, pass, token')
if str(_SECRET_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SECRET_DIR))
from loader import get_secret as _get_secret
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
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=0,
        dependencies=("data/brain.db", "MemoryStore"),
        evidence_notes=( "(06/11) LIVE: episodes 2.975, semantic 5.052 đang ghi sống; "
                        "xóa trí nhớ hard-delete qua dashboard E2E POST→DELETE→404; "
                        "tests 51/51 gồm delete_memory_roundtrip."),
    ),
    SystemCapability(
        capability_id="local_llm_inference",
        name="Suy Luận AI (NetMind Cloud GLM-5.3-Flash + Ollama Local)",
        description="Chat chính qua NetMind Cloud GLM-5.3-Flash (responder L867); Ollama qwen2.5:7b dự phòng offline/khi cần riêng tư trên máy cá nhân.",
        domain="Cognitive Inference",
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=0,
        dependencies=("NetMind Cloud API", "http://127.0.0.1:11434 (optional)", "OllamaClient"),
        evidence_notes=("(06/11) E2E LLM 2.7s qua NetMind Cloud GLM-5.3-Flash; "
                        "Ollama 11434 hiện KHÔNG chạy trên PC — chỉ bật khi cần offline."),
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
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=2,
        dependencies=("SelfLearningEngine", "cognition/self_study.py", "candidate_knowledge"),
        evidence_notes=("Self-Study Engine V2 (02/11): chu trình SCAN→STUDY→SYNTHESIZE→"
                        "DEDUP→QUARANTINE→REPORT chạy thử THẬT trên copy brain.db — "
                        "7/7 test, demo web_search thật quarantine 2 knowledge có "
                        "provenance (conf 0.7); dedup word-set chống dupes 44%. "
                        "Kiến thức mới luôn quarantined chờ Quanpt1 duyệt (§XI)."),
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
    SystemCapability(
        capability_id="edge_embodiment_pi5",
        name="Hình Thể Số Pi5 — Kết Nối LAN-first, Kiosk Avatar, Wake Voice, Camera (Edge Embodiment)",
        description="PC↔Pi5 LAN/WiFi-first (mesh/BT dự phòng), HMAC đồng bộ; kiosk avatar 7\" lip-sync FPS 24/18/12; wake 'CHERRY ơi' offline Vosk matcher siết false-positive; camera IMX708 chụp ảnh qua DM (media-only); panel sức khỏe Pi5 thời gian thực (Edge Agent V41).",
        domain="Edge Embodiment",
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=1,
        dependencies=("edge_client/client_daemon.py", "edge_client/edge_agent.py", "wake_word_service.py", "kiosk.js"),
        evidence_notes=("(06/11) LIVE: heartbeat READY RTT 28-35ms misses=0; LAN-first "
                        "selector+resolver commit 61782fb; health panel commit 4ecbf47; "
                        "avatar e89866f CPU 0.3-0.5%; wake 22 case test sau siết matcher; "
                        "camera IMX708 detected; HDMI mirror chưa xong (labwc từ chối "
                        "enable HDMI-A-2 — báo cáo HDMI_MIRROR_BUG_20261106)."),
    ),
    SystemCapability(
        capability_id="netchat_dm_channel",
        name="Kênh DM NetChat 2 Chiều 4 Tầng (DM 100% Garantee)",
        description="DM bot_tony nhận/gửi mọi tin owner qua 4 tầng bảo đảm: poll 10s → heartbeat → watchdog → catchup 720'; self-filter bot; greeting 2 dòng; lệnh điều khiển PC+Pi5 qua command center với phê duyệt DM 2 bước.",
        domain="Owner Channel",
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=1,
        dependencies=("tools/netchat_auto_responder.py", "tools/netchat_command_center.py", f"bot_tony {_get_secret('netchat_channel_owner', 'mwp3nk3ciprjjr4hdmcoqgk6jr')}"),  # (12/11) đọc từ loader
        evidence_notes=("(06/11) LIVE: 476 tin 0 pending; greeting 2 dòng 38/38; "
                        "media-only DM 5680fb7; audit log ghi nhận lệnh DM."),
    ),
    SystemCapability(
        capability_id="speech_learning_quarantine",
        name="Học Văn Phong Từ Hội Thoại Giọng Nói Thật (Speech Corpus Learning — Quarantined)",
        description="Kéo hội thoại Vosk 24h từ Pi5 → lọc noise/độ dài/trùng → 516 câu quarantined trong candidate_knowledge chờ owner duyệt; chưa nối vào prompt giọng nói (đề xuất A: few-shot qua Phase F).",
        domain="Evolution & Learning",
        status=CapabilityStatus.IMPLEMENTED_UNTESTED,
        risk_level=1,
        dependencies=("tools/speech_corpus.py", "candidate_knowledge"),
        evidence_notes=("(06/11) journal 1.242 dòng → 674 đạt → 516 quarantined "
                        "(158 trùng); commit 29c8fe6; chưa E2E nối vào prompt."),
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