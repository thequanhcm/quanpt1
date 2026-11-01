"""M3 (01/11/2026, ĐÃ DUYỆT): Memory API consolidation — 5 lớp memory chuẩn hoá.

Vấn đề trước M3 (audit 16:33):
  - 5 store độc lập, mỗi store một API khác nhau (add_memory/add_experience/
    add_knowledge/add_context) — caller phải biết store nội bộ.
  - Không có khái niệm FACT/INFERENCE thống nhất: verification_status nằm rải rác,
    search trả về lẫn lộn suy luận chưa kiểm chứng với dữ kiện đã xác thực.
  - Facade cũ MemoryService.add_memory gọi method không tồn tại (bug chết im lặng).

Thiết kế M3 (smallest safe change — KHÔNG đụng store gốc đang tốt):
  - MemoryFacade: API thống nhất add/search/stats trên 5 lớp:
      MemoryStore (episodic/semantic sqlite) · DeepMemoryStore (units + review) ·
      ExperienceStore (kinh nghiệm) · ContextStore (session context) ·
      QuarantineStore (R4 knowledge chờ duyệt)
  - FactLevel: FACT / OBSERVED / INFERENCE / QUARANTINED — ánh xạ từ
    VerificationStatus của MemoryStore + heuristic classify_statement() cho văn
    bản mới (tiếng Việt: "có thể/sẽ/dự kiến/tôi nghĩ..." → INFERENCE).
  - search(..., fact_only=True) loại INFERENCE khi trả kết quả.
  - promote_to_fact(): INFERENCE → VERIFIED YÊU CẦU owner approval evidence
    (chuẩn R4 — không tự tin chuỗi LLM).

Store gốc giữ nguyên; facade là điểm vào mới, backward-compatible.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from quan_ai_brain.memory.sqlite_store import (
    MemoryStore,
    MemoryType,
    VerificationStatus,
)


class FactLevel(str, Enum):
    """Mức độ dữ kiện — ngôn ngữ chung cho 5 lớp memory."""

    FACT = "FACT"                    # USER_PROVIDED / VERIFIED — dùng được ngay
    OBSERVED = "OBSERVED"            # hệ thống tự quan sát (telemetry, log)
    INFERENCE = "INFERENCE"          # suy luận chưa kiểm chứng — phải gắn nhãn
    QUARANTINED = "QUARANTINED"      # candidate chờ phê duyệt (R4)


# Ánh xạ chuẩn VerificationStatus → FactLevel
VERIFICATION_TO_FACT: dict[str, FactLevel] = {
    VerificationStatus.USER_PROVIDED.value: FactLevel.FACT,
    VerificationStatus.VERIFIED.value: FactLevel.FACT,
    VerificationStatus.OBSERVED.value: FactLevel.OBSERVED,
    VerificationStatus.INFERRED.value: FactLevel.INFERENCE,
    VerificationStatus.UNVERIFIED.value: FactLevel.INFERENCE,
    VerificationStatus.CANDIDATE.value: FactLevel.QUARANTINED,
}

# Heuristic tiếng Việt: dấu hiệu suy luận/dự đoán → INFERENCE
_INFERENCE_PATTERNS = re.compile(
    r"\b(có thể|có khi|sẽ|sắp|dự kiến|dự đoán|tôi nghĩ|chắc|có lẽ|phải chăng|"
    r"likely|maybe|probably|perhaps|supposed to|presumably)\b",
    re.IGNORECASE,
)
# Dấu hiệu dữ kiện đã xác thực/quan sát trực tiếp
_OBSERVED_PATTERNS = re.compile(
    r"\b(đã (chạy|kiểm tra|xác minh|đo|test)|telemetry|log cho thấy|kết quả (test|pytest)|"
    r"verified|measured|observed)\b",
    re.IGNORECASE,
)


def classify_statement(text: str) -> FactLevel:
    """Phân loại câu tiếng Việt/Anh thành mức dữ kiện (heuristic, conservatively)."""
    t = (text or "").strip()
    if not t:
        return FactLevel.INFERENCE
    if _INFERENCE_PATTERNS.search(t):
        return FactLevel.INFERENCE
    if _OBSERVED_PATTERNS.search(t):
        return FactLevel.OBSERVED
    # Mặc định: dữ kiện chưa kiểm chứng → INFERENCE (fail-closed về mặt nhận thức)
    return FactLevel.INFERENCE


@dataclass
class UnifiedMemoryHit:
    """Kết quả search thống nhất từ bất kỳ lớp nào."""

    source_layer: str                 # semantic | deep | experience | context | quarantine
    content: str
    fact_level: FactLevel
    verification_status: str = ""
    id: str = ""
    score: float = 0.0
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_layer": self.source_layer,
            "id": self.id,
            "content": self.content,
            "fact_level": self.fact_level.value,
            "verification_status": self.verification_status,
            "score": self.score,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class MemoryFacade:
    """API thống nhất trên 5 lớp memory. KHÔNG thay thế store — chỉ chuẩn hoá."""

    def __init__(
        self,
        memory_store: MemoryStore | None = None,
        *,
        deep_store: Any = None,
        experience_store: Any = None,
        context_store: Any = None,
        quarantine_store: Any = None,
        workspace: str | Path | None = None,
    ) -> None:
        ws = Path(workspace) if workspace else Path.cwd()
        self.workspace = ws
        self.memory = memory_store or MemoryStore(ws / "data" / "brain.db", workspace=ws)
        self.deep = deep_store          # optional — lazy khi caller cần
        self.experience = experience_store
        self.context = context_store
        self.quarantine = quarantine_store
        self._owned = memory_store is None

    # --------------------------------------------------------------
    # ADD — một API, route theo memory_type
    # --------------------------------------------------------------
    def add(
        self,
        content: str,
        *,
        memory_type: str = "semantic",
        source_ref: str = "",
        verification_status: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        fact_level: FactLevel | None = None,
    ) -> dict[str, Any]:
        """Thêm kiến thức vào lớp phù hợp; trả {layer, id, fact_level}.

        verification_status None → suy từ fact_level/heuristic classify_statement.
        fact_level=QUARANTINED (hoặc memory_type='candidate') → vào R4 quarantine.
        """
        content = (content or "").strip()
        if not content:
            raise ValueError("Nội dung memory không được rỗng")

        mt = (memory_type or "semantic").lower()

        # caller có thể truyền "FACT" (str) hoặc FactLevel.FACT — chuẩn hoá
        if isinstance(fact_level, str):
            try:
                fact_level = FactLevel(fact_level.upper())
            except ValueError:
                fact_level = None

        if fact_level is None and verification_status is None:
            fact_level = classify_statement(content)
        if verification_status is None:
            verification_status = {
                FactLevel.FACT: VerificationStatus.VERIFIED.value,
                FactLevel.OBSERVED: VerificationStatus.OBSERVED.value,
                FactLevel.INFERENCE: VerificationStatus.INFERRED.value,
                FactLevel.QUARANTINED: VerificationStatus.CANDIDATE.value,
            }.get(fact_level or FactLevel.INFERENCE, VerificationStatus.UNVERIFIED.value)

        # Candidate → quarantine R4 (nếu store có mặt) — KHÔNG tự vào semantic
        if mt in ("candidate", "quarantined") or verification_status == VerificationStatus.CANDIDATE.value:
            if self.quarantine is not None:
                qid = self.quarantine.add_knowledge(
                    content, source_ref=source_ref or "facade",
                    metadata=metadata or {},
                )
                return {"layer": "quarantine", "id": qid,
                        "fact_level": FactLevel.QUARANTINED.value}

        rec = self.memory.store_memory(
            content,
            memory_type=mt,
            source_ref=source_ref,
            verification_status=verification_status,
            tags=tags,
            metadata=metadata,
        )
        return {
            "layer": "semantic",
            "id": rec.id if hasattr(rec, "id") else str(rec),
            "fact_level": VERIFICATION_TO_FACT.get(
                verification_status.upper(), FactLevel.INFERENCE
            ).value,
        }

    def add_episode(self, summary: str, *, kind: str = "task", source_ref: str = "",
                    status: str = "recorded", metadata: dict[str, Any] | None = None) -> str:
        """Episode = sự kiện đã xảy ra → luôn OBSERVED (không phải suy luận)."""
        return self.memory.add_episode(summary, kind=kind, source_ref=source_ref,
                                       status=status, metadata=metadata)

    # --------------------------------------------------------------
    # SEARCH — hợp nhất kết quả + sàng lọc FACT/INFERENCE
    # --------------------------------------------------------------
    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        fact_only: bool = False,
        include_inference: bool = True,
        memory_type: str | None = None,
    ) -> list[UnifiedMemoryHit]:
        """Search semantic memory + gắn FactLevel; fact_only loại INFERENCE."""
        hits: list[UnifiedMemoryHit] = []
        # fact_only → push verification filter xuống SQL (chỉ FACT status), tiết kiệm quét
        if fact_only:
            rows = self.memory.search_memories(
                query, memory_type=memory_type, limit=top_k * 2,
                verification_status=None,
            )
            # Lấy cả USER_PROVIDED + VERIFIED (2 status = FACT) qua 2 lần gọi gọn
            up = self.memory.search_memories(query, memory_type=memory_type,
                                             verification_status="USER_PROVIDED", limit=top_k)
            ver = self.memory.search_memories(query, memory_type=memory_type,
                                              verification_status="VERIFIED", limit=top_k)
            rows = up + ver
        else:
            rows = self.memory.search_memories(query, memory_type=memory_type, limit=top_k)
        for row in rows:
            v_status = str(getattr(row, "verification_status", "UNVERIFIED")).upper()
            level = VERIFICATION_TO_FACT.get(v_status, FactLevel.INFERENCE)
            meta = getattr(row, "metadata", None)
            hit = UnifiedMemoryHit(
                source_layer="semantic",
                id=str(getattr(row, "id", "")),
                content=str(getattr(row, "content", "")),
                fact_level=level,
                verification_status=v_status,
                created_at=str(getattr(row, "created_at_utc", "")),
                metadata=meta if isinstance(meta, dict) else {},
            )
            hits.append(hit)

        if fact_only:
            hits = [h for h in hits if h.fact_level == FactLevel.FACT]
        elif not include_inference:
            hits = [h for h in hits if h.fact_level != FactLevel.INFERENCE]
        return hits[:top_k]

    # --------------------------------------------------------------
    # PROMOTION — INFERENCE → FACT yêu cầu bằng chứng owner (R4)
    # --------------------------------------------------------------
    def promote_to_fact(
        self,
        memory_id: str,
        *,
        approved_by: str,
        approval_evidence: str,
        verifier: Any = None,
    ) -> bool:
        """Nâng memory INFERENCE → VERIFIED. Fail-closed: không verifier hợp lệ → từ chối."""
        if verifier is None:
            from quan_ai_brain.governance.approval_verifier import GovernanceApprovalVerifier
            db_path = getattr(self.memory, "db_path", None)
            base_dir = Path(self.workspace) if self.workspace else (
                Path(db_path).parent if db_path and str(db_path) != ":memory:" else Path.cwd()
            )
            gov_db = base_dir / "governance.db" if (base_dir / "governance.db").exists() else base_dir / "data" / "governance.db"
            if not gov_db.exists():
                raise PermissionError("governance.db không tồn tại — không thể verify approval")
            verifier = GovernanceApprovalVerifier(gov_db)
        rec = self.memory.get_memory(memory_id)
        if rec is None:
            raise KeyError(f"Memory {memory_id} không tồn tại")
        if not verifier(memory_id, approved_by, approval_evidence):
            raise PermissionError("Owner approval không xác minh được — memory giữ nguyên INFERENCE")
        # Ghi đè verification_status qua supersede (chuẩn API, không UPDATE tay)
        new_rec = self.memory.store_memory(
            rec.content,
            memory_type=rec.memory_type,
            source_ref=rec.source_ref,
            verification_status=VerificationStatus.VERIFIED,
            tags=rec.tags,
            metadata={**rec.metadata, "promoted_from": rec.verification_status.value,
                      "approval_evidence": approval_evidence},
            memory_id=memory_id,
        )
        return new_rec.verification_status == VerificationStatus.VERIFIED

    # --------------------------------------------------------------
    # STATS — tổng quan 5 lớp
    # --------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        with self.memory._lock:
            rows = self.memory._connection.execute(
                "SELECT verification_status, COUNT(*) FROM memories WHERE lifecycle_status='active' "
                "GROUP BY verification_status"
            ).fetchall()
        by_status = {r[0]: int(r[1]) for r in rows}
        fact_counts = {lvl.value: 0 for lvl in FactLevel}
        for status, count in by_status.items():
            level = VERIFICATION_TO_FACT.get(str(status).upper(), FactLevel.INFERENCE)
            fact_counts[level.value] += count
        episodes = self.memory._connection.execute(
            "SELECT COUNT(*) FROM episodes"
        ).fetchone()[0] if self._owned else None
        return {
            "semantic_by_verification": by_status,
            "semantic_by_fact_level": fact_counts,
            "episodes_total": episodes,
        }

    def close(self) -> None:
        if self._owned:
            self.memory.close()

    def __enter__(self) -> "MemoryFacade":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
