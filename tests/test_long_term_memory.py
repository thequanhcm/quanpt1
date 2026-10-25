"""Tests for QUAN AI BRAIN Long-Term Memory Engine V1."""
from __future__ import annotations

import pytest

from quan_ai_brain.memory.models import LifecycleStatus, MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


def test_store_and_retrieve_all_memory_types():
    """Verify storing and retrieving all 6 memory types."""
    with MemoryStore(":memory:") as store:
        types_and_samples = [
            (MemoryType.EPISODIC, "Cuộc họp điều hành hạ tầng ngày 17/10/2026", "meeting:101"),
            (MemoryType.SEMANTIC, "Pin Lithium Iron Phosphate (LiFePO4) có tuổi thọ vòng đời 3000-5000 chu kỳ", "manual:ups_v4"),
            (MemoryType.PROCEDURAL, "SOP-01: Quy trình ngắt điện khẩn cấp khi nhiệt độ ắc quy vượt 65 độ C", "sop:01"),
            (MemoryType.DECISION, "Quyết định giữ R5 ở mức hard-blocked để bảo vệ an toàn hệ thống", "governance:policy"),
            (MemoryType.PREFERENCE, "Quanpt1 ưu tiên báo cáo kỹ thuật súc tích, có bằng chứng thực tế", "user:preference"),
            (MemoryType.CANDIDATE, "Đề xuất cập nhật thuật toán sạc thích ứng cho module VDCIM", "research:clae"),
        ]

        for m_type, content, source in types_and_samples:
            rec = store.store_memory(
                content=content,
                memory_type=m_type,
                source_ref=source,
                verification_status=VerificationStatus.VERIFIED if m_type != MemoryType.CANDIDATE else VerificationStatus.CANDIDATE,
            )
            assert rec.id is not None
            assert rec.memory_type == m_type.value
            assert rec.content == content
            assert rec.source_ref == source

            retrieved = store.get_memory(rec.id)
            assert retrieved is not None
            assert retrieved.id == rec.id
            assert retrieved.content == content
            assert retrieved.memory_type == m_type.value


def test_persistence_across_reconnect(tmp_path):
    """Verify data persists when database is closed and reopened."""
    db_file = tmp_path / "data" / "persistent_brain.db"
    record_id: str

    with MemoryStore(db_file, workspace=tmp_path) as store1:
        rec = store1.store_memory(
            content="Quy tắc cốt lõi: Không can thiệp vào các hệ thống ngoài workspace",
            memory_type=MemoryType.PROCEDURAL,
            source_ref="AGENTS.md",
            verification_status=VerificationStatus.VERIFIED,
            tags=["core", "safety"],
        )
        record_id = rec.id

    # Reopen database in a fresh store instance
    with MemoryStore(db_file, workspace=tmp_path) as store2:
        retrieved = store2.get_memory(record_id)
        assert retrieved is not None
        assert retrieved.id == record_id
        assert "Không can thiệp vào các hệ thống ngoài workspace" in retrieved.content
        assert retrieved.tags == ["core", "safety"]
        assert retrieved.verification_status == VerificationStatus.VERIFIED.value


def test_vietnamese_diacritics_search():
    """Verify exact and substring search with Vietnamese accented text."""
    with MemoryStore(":memory:") as store:
        store.store_memory(
            content="Quy trình khởi động trạm biến áp trung thế 22kV",
            memory_type=MemoryType.PROCEDURAL,
            tags=["điện", "biến_áp"],
        )
        store.store_memory(
            content="Đánh giá hiệu suất bộ đệm pin Lithium LiFePO4",
            memory_type=MemoryType.SEMANTIC,
            tags=["pin", "năng_lượng"],
        )
        store.store_memory(
            content="Ghi nhận thông số điện áp phòng máy chủ DC",
            memory_type=MemoryType.EPISODIC,
            tags=["hạ_tầng", "phòng_máy"],
        )

        results_bien_ap = store.search_memories(query="biến áp")
        assert len(results_bien_ap) == 1
        assert "22kV" in results_bien_ap[0].content

        results_lithium = store.search_memories(query="Lithium")
        assert len(results_lithium) == 1
        assert "LiFePO4" in results_lithium[0].content

        results_tag = store.search_memories(tag="phòng_máy")
        assert len(results_tag) == 1
        assert "phòng máy chủ" in results_tag[0].content


def test_filtering_by_verification_status():
    """Verify filtering across all verification statuses."""
    with MemoryStore(":memory:") as store:
        statuses = [
            VerificationStatus.USER_PROVIDED,
            VerificationStatus.OBSERVED,
            VerificationStatus.VERIFIED,
            VerificationStatus.INFERRED,
            VerificationStatus.UNVERIFIED,
            VerificationStatus.CANDIDATE,
        ]
        for idx, status in enumerate(statuses):
            store.store_memory(
                content=f"Thông tin số {idx} với trạng thái {status.value}",
                memory_type=MemoryType.SEMANTIC,
                verification_status=status,
            )

        for status in statuses:
            matched = store.search_memories(verification_status=status)
            assert len(matched) == 1
            assert matched[0].verification_status == status.value


def test_candidate_knowledge_isolation_and_quarantine():
    """Verify candidate knowledge is quarantined and distinct from approved memory."""
    with MemoryStore(":memory:") as store:
        cand_rec = store.quarantine_candidate_knowledge(
            statement="Cần tăng dòng nạp nổi của ắc quy lên 15%",
            source_ref="experimental_agent_log",
            rationale="Tối ưu thời gian sạc bù sau cúp điện",
            tags=["battery", "tuning"],
        )
        assert cand_rec.verification_status == VerificationStatus.CANDIDATE.value
        assert cand_rec.lifecycle_status == LifecycleStatus.QUARANTINED.value
        assert "candidate" in cand_rec.tags
        assert "quarantined" in cand_rec.tags

        # Default active search should NOT return quarantined candidates
        active_memories = store.search_memories(lifecycle_status="active")
        assert not any(m.id == cand_rec.id for m in active_memories)

        # Explicit search for quarantined returns it
        quarantined_memories = store.search_memories(lifecycle_status="quarantined")
        assert any(m.id == cand_rec.id for m in quarantined_memories)

        # Backward compatibility check: candidate_knowledge table also has it
        candidates_raw = store.list_candidates()
        assert any(c["id"] == cand_rec.id for c in candidates_raw)


def test_versioning_and_history_preservation():
    """Verify updating a memory creates a new version, supersedes old, and preserves lineage."""
    with MemoryStore(":memory:") as store:
        v1 = store.store_memory(
            content="Quy định nhiệt độ phòng ắc quy: 25 độ C (+- 2 độ C)",
            memory_type=MemoryType.PROCEDURAL,
            source_ref="sop_v1",
            verification_status=VerificationStatus.VERIFIED,
            tags=["battery", "temp"],
        )
        assert v1.version == 1
        assert v1.lifecycle_status == LifecycleStatus.ACTIVE.value
        assert v1.superseded_by is None

        # Supersede with updated operational parameters
        v2 = store.supersede_memory(
            old_memory_id=v1.id,
            new_content="Quy định nhiệt độ phòng ắc quy cập nhật: 23 độ C (+- 1 độ C)",
            source_ref="sop_v2",
            verification_status=VerificationStatus.VERIFIED,
            tags=["battery", "temp", "updated"],
        )

        assert v2.version == 2
        assert v2.lifecycle_status == LifecycleStatus.ACTIVE.value
        assert v2.id != v1.id

        # Check old record was marked superseded
        old_v1 = store.get_memory(v1.id)
        assert old_v1 is not None
        assert old_v1.lifecycle_status == LifecycleStatus.SUPERSEDED.value
        assert old_v1.superseded_by == v2.id

        # Verify lineage tracking
        trace = store.trace_source(v2.id)
        assert trace["memory_id"] == v2.id
        assert trace["version"] == 2
        assert trace["predecessor_count"] == 1
        assert trace["predecessors"][0]["id"] == v1.id
        assert "25 độ C" in trace["predecessors"][0]["content"]

        # Attempting to supersede an already superseded record should fail
        with pytest.raises(ValueError, match="already been superseded"):
            store.supersede_memory(old_memory_id=v1.id, new_content="Cannot supersede twice")


def test_archive_memory():
    """Verify archiving a memory record."""
    with MemoryStore(":memory:") as store:
        rec = store.store_memory(
            content="Cấu hình tạm thời cho đợt bảo trì tháng 10",
            memory_type=MemoryType.DECISION,
        )
        store.archive_memory(rec.id)
        archived = store.get_memory(rec.id)
        assert archived is not None
        assert archived.lifecycle_status == LifecycleStatus.ARCHIVED.value

        # Active search should not include archived record
        active = store.search_memories(lifecycle_status="active")
        assert not any(m.id == rec.id for m in active)


def test_record_task_result():
    """Verify task outcomes are recorded with episodic memory and structured fields."""
    with MemoryStore(":memory:") as store:
        rec = store.record_task_result(
            task_id="TASK-2026-001",
            goal="Kiểm tra điện áp các chuỗi pin UPS",
            result="Tất cả 40 bình đạt tiêu chuẩn 13.6V nạp nổi",
            status="succeeded",
            metadata={"operator": "Quanpt1"},
        )
        assert rec.memory_type == MemoryType.EPISODIC.value
        assert rec.verification_status == VerificationStatus.OBSERVED.value
        assert "TASK-2026-001" in rec.content
        assert "succeeded" in rec.tags

        # Check backward compatibility with list_episodes
        episodes = store.list_episodes()
        assert any(e["source_ref"] == "task:TASK-2026-001" for e in episodes)


def test_sql_injection_resistance():
    """Verify parameterized queries prevent SQL injection."""
    with MemoryStore(":memory:") as store:
        malicious_input = "'; DROP TABLE memories; --"
        rec = store.store_memory(
            content=malicious_input,
            memory_type=MemoryType.SEMANTIC,
            source_ref=malicious_input,
            tags=[malicious_input],
        )
        assert rec.id is not None

        # Search with SQL injection payload should match cleanly without syntax error or table drop
        results = store.search_memories(query="'; DROP TABLE")
        assert len(results) == 1
        assert "DROP TABLE" in results[0].content

        # Table is still intact and accessible
        all_memories = store.search_memories()
        assert len(all_memories) >= 1


def test_input_validation_and_rejections():
    """Verify empty content and invalid confidence scores are rejected."""
    with MemoryStore(":memory:") as store:
        with pytest.raises(ValueError, match="must not be empty"):
            store.store_memory(content="", memory_type=MemoryType.SEMANTIC)

        with pytest.raises(ValueError, match="must not be empty"):
            store.store_memory(content="   ", memory_type=MemoryType.SEMANTIC)

        with pytest.raises(ValueError, match="confidence_score"):
            store.store_memory(content="Hợp lệ", memory_type=MemoryType.SEMANTIC, confidence_score=1.5)

        with pytest.raises(ValueError, match="confidence_score"):
            store.store_memory(content="Hợp lệ", memory_type=MemoryType.SEMANTIC, confidence_score=-0.1)

        with pytest.raises(ValueError, match="limit"):
            store.search_memories(limit=0)

        with pytest.raises(ValueError, match="limit"):
            store.search_memories(limit=1000)

        with pytest.raises(KeyError):
            store.get_memory("non-existent-id")
            store.archive_memory("non-existent-id")


def test_redaction_in_memory_engine():
    """Verify sensitive tokens and passwords are automatically redacted before storage."""
    with MemoryStore(":memory:") as store:
        rec = store.store_memory(
            content='Cấu hình xác thực với api_key="sk-secret12345" và Bearer abcdef1234567890',
            memory_type=MemoryType.PROCEDURAL,
            source_ref="token=xyz987654321",
            metadata={"password": "my_master_password", "safe_param": "100ms"},
        )
        assert "sk-secret12345" not in rec.content
        assert "[REDACTED]" in rec.content
        assert "xyz987654321" not in rec.source_ref
        assert rec.metadata["password"] == "[REDACTED]"
        assert rec.metadata["safe_param"] == "100ms"
