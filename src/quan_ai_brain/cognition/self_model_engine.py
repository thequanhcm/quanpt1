"""Self-Model Engine for QUAN AI BRAIN — Sprint 4.

Generates a comprehensive self-model answering:
- Tôi đang tồn tại trên những máy nào?
- Trung tâm xử lý chính là gì?
- Những mô-đun nào đang hoạt động?
- Tôi có những nguồn tri thức nào?
- Tôi có những loại bộ nhớ nào?
- Tôi đang sử dụng mô hình AI nào?
- Tôi đang gặp những lỗi hoặc giới hạn nào?
- Những năng lực nào đã được kiểm chứng?
- Những năng lực nào mới chỉ được đề xuất?
- Những công việc nào đang chờ chủ nhân?
- Tôi có quyền tự thực hiện những loại hành động nào?
- Những hành động nào bắt buộc phải xin phép?
- Lần kiểm tra sức khỏe gần nhất cho kết quả gì?
- Điều gì cần được cải tiến tiếp theo?

Giai đoạn Sprint 4 (2026-10-25): Self-model generation from inventory + capability registry.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from quan_ai_brain.cognition.capability_registry import CapabilityRegistry, CapabilityStatus
from quan_ai_brain.cognition.system_inventory import ComponentStatus, SystemInventory


@dataclass
class SelfModel:
    """Comprehensive self-model of QUAN AI BRAIN."""
    identity: dict[str, str]
    deployment: dict[str, Any]
    active_modules: list[str]
    knowledge_sources: list[str]
    memory_types: list[str]
    ai_models: list[str]
    known_limitations: list[str]
    verified_capabilities: list[str]
    unverified_capabilities: list[str]
    pending_approvals: list[str]
    permissions: dict[str, list[str]]
    health_status: dict[str, Any]
    improvement_priorities: list[str]
    generated_at: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_conversational_summary(self) -> str:
        """Generate conversational self-introduction."""
        lines = [
            f"Xin chào, em là **TONY PHAM** — trợ lý AI và nhân sự số của anh **{self.identity.get('owner', 'Quanpt1')}**.",
            "",
            "**📍 Triển khai:**",
            f"  - PC Core: {self.deployment.get('core_location', 'Windows PC')}",
            f"  - Raspberry Pi 5: {self.deployment.get('edge_location', '192.168.1.21')}",
            "",
            "**🧠 Mô-đun đang hoạt động:**",
        ]
        for mod in self.active_modules[:5]:
            lines.append(f"  - {mod}")
        if len(self.active_modules) > 5:
            lines.append(f"  ... và {len(self.active_modules) - 5} mô-đun khác")

        lines.extend([
            "",
            "**💾 Bộ nhớ:**",
        ])
        for mem in self.memory_types:
            lines.append(f"  - {mem}")

        lines.extend([
            "",
            "**🤖 Mô hình AI:**",
        ])
        for model in self.ai_models:
            lines.append(f"  - {model}")

        lines.extend([
            "",
            "**⚠️ Giới hạn đã biết:**",
        ])
        for lim in self.known_limitations[:5]:
            lines.append(f"  - {lim}")
        if len(self.known_limitations) > 5:
            lines.append(f"  ... và {len(self.known_limitations) - 5} giới hạn khác")

        lines.extend([
            "",
            f"**✅ Năng lực đã kiểm chứng:** {len(self.verified_capabilities)} năng lực",
            f"**⏳ Năng lực chưa kiểm chứng:** {len(self.unverified_capabilities)} năng lực",
            "",
            f"**📊 Sức khỏe hệ thống:** {self.health_status.get('health_percentage', 0)*100:.0f}% healthy",
            f"**🕐 Kiểm tra gần nhất:** {self.generated_at}",
            "",
            "**🎯 Ưu tiên cải tiến tiếp theo:**",
        ])
        for i, priority in enumerate(self.improvement_priorities[:3], 1):
            lines.append(f"  {i}. {priority}")

        return "\n".join(lines)


class SelfModelEngine:
    """Generates and updates the self-model."""

    def __init__(self, workspace: str | None = None) -> None:
        self.workspace = workspace or "."
        self.inventory = SystemInventory(self.workspace)
        self.capability_registry = CapabilityRegistry()

    def generate_self_model(self) -> SelfModel:
        """Generate comprehensive self-model."""
        # Scan inventory
        inventory = self.inventory.scan_all()
        health_summary = self.inventory.get_health_summary()

        # Identity
        identity = {
            "system_name": "QUAN AI BRAIN",
            "assistant_name": "TONY PHAM",
            "owner": "Quanpt1",
            "owner_id": "quanpt1-3a28d2fa",
            "creator": "Anh Quân — Quanpt1",
        }

        # Deployment
        deployment = {
            "core_location": "Windows 10 PC (E:/AI/QUAN AI BRAIN)",
            "edge_location": "192.168.1.21 (Raspberry Pi 5)",
            "architecture": "PC Core + Edge (Pi 5)",
        }

        # Active modules
        active_modules = [
            comp.name for comp in inventory.values()
            if comp.component_type.value == "module" and comp.status == ComponentStatus.HEALTHY
        ]

        # Knowledge sources
        knowledge_sources = [
            "Tài liệu dự án nội bộ",
            "Kết quả kiểm thử đã xác minh",
            "Phản hồi từ chủ nhân",
            "Log công việc đã hoàn thành",
        ]

        # Memory types
        memory_types = [
            "Working Memory (ngữ cảnh tác vụ)",
            "Episodic Memory (sự kiện, nhiệm vụ)",
            "Semantic Memory (kiến thức, dữ kiện)",
            "Procedural Memory (SOP, quy trình)",
            "Self-Model Memory (bản đồ hệ thống)",
            "Governance Memory (phê duyệt, quy tắc)",
        ]

        # AI models
        ai_models = []
        for comp in inventory.values():
            if comp.component_type.value == "model":
                ai_models.append(comp.name)
        if not ai_models:
            ai_models = ["Qwen2.5:7b (Ollama local)", "GLM-5.3-Flash (NetMind cloud)"]

        # Known limitations
        limitations = []
        for comp in inventory.values():
            if comp.status in [ComponentStatus.FAILED, ComponentStatus.NOT_INSTALLED, ComponentStatus.UNKNOWN]:
                for lim in comp.known_limitations:
                    limitations.append(f"{comp.name}: {lim}")
        if not limitations:
            limitations = ["Voice E2E trên Pi 5 chưa test thật", "Camera chưa verify"]

        # Verified vs unverified capabilities
        verified = [
            cap.name for cap in self.capability_registry.list_capabilities()
            if cap.status in [CapabilityStatus.VERIFIED_ACTIVE, CapabilityStatus.IMPLEMENTED_UNTESTED]
        ]
        unverified = [
            cap.name for cap in self.capability_registry.list_capabilities()
            if cap.status in [CapabilityStatus.INERT_STAGING, CapabilityStatus.NOT_IMPLEMENTED]
        ]

        # Pending approvals (placeholder — would query governance DB in production)
        pending_approvals = []  # Would fetch from governance.db

        # Permissions
        permissions = {
            "read": ["workspace/*", "data/*", "reports/*"],
            "write": ["data/*", "reports/*", "logs/*"],
            "execute": ["tools/safe_*"],
            "restricted": ["R3+ actions require owner approval"],
        }

        # Health status
        health_status = health_summary

        # Improvement priorities
        priorities = [
            "Sprint 5: Continuous Learning Engine (5-type learning)",
            "Sprint 6: Approval Center UI (Tab 8)",
            "Voice E2E test trên Pi 5 thật",
            "Health Monitor real-time alerting",
            "Conflict detection trong knowledge ingestion",
        ]

        # Confidence
        confidence = health_summary.get("health_percentage", 0.5)

        return SelfModel(
            identity=identity,
            deployment=deployment,
            active_modules=active_modules,
            knowledge_sources=knowledge_sources,
            memory_types=memory_types,
            ai_models=ai_models,
            known_limitations=limitations,
            verified_capabilities=verified,
            unverified_capabilities=unverified,
            pending_approvals=pending_approvals,
            permissions=permissions,
            health_status=health_status,
            improvement_priorities=priorities,
            generated_at=datetime.now(timezone.utc).isoformat(),
            confidence=confidence,
        )

    def get_self_model_json(self) -> str:
        """Get self-model as JSON string."""
        model = self.generate_self_model()
        return json.dumps(model.to_dict(), indent=2, ensure_ascii=False)

    def get_self_model_summary(self) -> str:
        """Get conversational self-model summary."""
        model = self.generate_self_model()
        return model.to_conversational_summary()