"""Data models and enums for QUAN AI BRAIN Long-Term Memory Engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from typing import Any


class MemoryType(str, Enum):
    EPISODIC = "EPISODIC"        # Sự kiện, cuộc trao đổi, nhiệm vụ và kết quả
    SEMANTIC = "SEMANTIC"        # Kiến thức, dữ kiện, thực thể và quan hệ
    PROCEDURAL = "PROCEDURAL"    # Quy trình, SOP, hướng dẫn đã kiểm thử
    DECISION = "DECISION"        # Quyết định, lựa chọn cân nhắc, lý do, giả định, kết quả
    PREFERENCE = "PREFERENCE"    # Ưu tiên làm việc đã được người dùng xác nhận
    CANDIDATE = "CANDIDATE"      # Tri thức mới đang chờ xác minh hoặc phê duyệt


class VerificationStatus(str, Enum):
    USER_PROVIDED = "USER_PROVIDED"  # Do người dùng cung cấp
    OBSERVED = "OBSERVED"            # Hệ thống quan sát trực tiếp
    VERIFIED = "VERIFIED"            # Đã có bằng chứng xác minh
    INFERRED = "INFERRED"            # Suy luận, không phải dữ kiện chắc chắn
    UNVERIFIED = "UNVERIFIED"        # Chưa xác minh
    CANDIDATE = "CANDIDATE"          # Tri thức ứng viên đang cách ly


class LifecycleStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    QUARANTINED = "quarantined"
    DEPRECATED = "deprecated"


@dataclass
class MemoryRecord:
    id: str
    memory_type: str
    content: str
    source_ref: str = ""
    verification_status: str = VerificationStatus.UNVERIFIED.value
    confidence_score: float = 1.0
    project_scope: str = "general"
    tags: list[str] = field(default_factory=list)
    lifecycle_status: str = LifecycleStatus.ACTIVE.value
    version: int = 1
    superseded_by: str | None = None
    created_at_utc: str = ""
    updated_at_utc: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Any) -> MemoryRecord:
        data = dict(row)
        tags_raw = data.get("tags_json", "[]")
        meta_raw = data.get("metadata_json", "{}")
        try:
            tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
        except json.JSONDecodeError:
            tags = []
        try:
            metadata = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
        except json.JSONDecodeError:
            metadata = {}

        return cls(
            id=data["id"],
            memory_type=data["memory_type"],
            content=data["content"],
            source_ref=data.get("source_ref", ""),
            verification_status=data.get("verification_status", VerificationStatus.UNVERIFIED.value),
            confidence_score=float(data.get("confidence_score", 1.0)),
            project_scope=data.get("project_scope", "general"),
            tags=tags if isinstance(tags, list) else [],
            lifecycle_status=data.get("lifecycle_status", LifecycleStatus.ACTIVE.value),
            version=int(data.get("version", 1)),
            superseded_by=data.get("superseded_by"),
            created_at_utc=data.get("created_at_utc", ""),
            updated_at_utc=data.get("updated_at_utc", ""),
            metadata=metadata if isinstance(metadata, dict) else {},
        )
