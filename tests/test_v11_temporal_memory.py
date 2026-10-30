"""V11 tests — Temporal Memory & Automatic Consolidation (12 tests)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from quan_ai_brain.cognition.temporal_memory import (
    TemporalMemoryEngine,
    MemoryConsolidator,
    parse_temporal_context,
    calculate_freshness_score,
)
from quan_ai_brain.memory.deep_memory import DeepMemoryStore


@pytest.fixture()
def store(tmp_path):
    s = DeepMemoryStore(tmp_path / "v11_test.db")
    yield s
    s.close()


@pytest.fixture()
def engine(store):
    return TemporalMemoryEngine(store)


@pytest.fixture()
def consolidator(store):
    return MemoryConsolidator(store)


# ============================================================================
# TEMPORAL PARSING TESTS
# ============================================================================

def test_parse_specific_date():
    """Test parsing ngày cụ thể: 'ngày 15/3/2024'."""
    result = parse_temporal_context("ngày 15/3/2024")
    assert result['valid_from'] is not None
    assert result['valid_from'].day == 15
    assert result['valid_from'].month == 3
    assert result['valid_from'].year == 2024
    assert result['temporal_type'] == 'specific'
    assert result['confidence'] >= 0.9


def test_parse_month_year():
    """Test parsing tháng/năm: 'tháng 3/2024'."""
    result = parse_temporal_context("tháng 3/2024")
    assert result['valid_from'] is not None
    assert result['valid_from'].month == 3
    assert result['valid_from'].year == 2024
    assert result['valid_until'] is not None
    assert result['temporal_type'] == 'specific'


def test_parse_relative_today():
    """Test parsing 'hôm nay'."""
    ref = datetime(2024, 3, 15, tzinfo=timezone.utc)
    result = parse_temporal_context("hôm nay", ref)
    assert result['valid_from'] == ref
    assert result['temporal_type'] == 'relative'
    assert result['confidence'] >= 0.85


def test_parse_relative_yesterday():
    """Test parsing 'hôm qua'."""
    ref = datetime(2024, 3, 15, tzinfo=timezone.utc)
    result = parse_temporal_context("ngày hôm qua", ref)
    assert result['valid_from'] == ref - timedelta(days=1)
    assert result['valid_until'] == ref
    assert result['temporal_type'] == 'relative'


def test_parse_duration():
    """Test parsing duration: 'trong 3 ngày'."""
    ref = datetime(2024, 3, 15, tzinfo=timezone.utc)
    result = parse_temporal_context("trong 3 ngày", ref)
    assert result['valid_from'] == ref
    assert result['valid_until'] == ref + timedelta(days=3)
    assert result['temporal_type'] == 'duration'


def test_parse_no_temporal():
    """Test văn bản không có thông tin thời gian."""
    result = parse_temporal_context("Đây là thông tin chung")
    assert result['valid_from'] is None
    assert result['valid_until'] is None
    assert result['temporal_type'] is None


# ============================================================================
# FRESHNESS SCORE TESTS
# ============================================================================

def test_freshness_new_memory():
    """Memory mới → freshness ~1.0."""
    now = datetime.now(timezone.utc)
    score = calculate_freshness_score(now, None, now)
    assert score >= 0.95


def test_freshness_old_memory():
    """Memory cũ (365 ngày) → freshness thấp."""
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=365)
    score = calculate_freshness_score(old, None, now, decay_rate=0.01)
    assert score < 0.05


def test_freshness_expired_memory():
    """Memory hết hạn (valid_until < now) → 0.0."""
    now = datetime.now(timezone.utc)
    expired = now - timedelta(days=10)
    score = calculate_freshness_score(now - timedelta(days=100), expired, now)
    assert score == 0.0


def test_freshness_decay_rate():
    """Kiểm tra decay rate ảnh hưởng đến score."""
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=100)
    
    score_fast = calculate_freshness_score(old, None, now, decay_rate=0.02)
    score_slow = calculate_freshness_score(old, None, now, decay_rate=0.005)
    
    assert score_fast < score_slow  # Decay nhanh → score thấp hơn


# ============================================================================
# DUPLICATE DETECTION TESTS
# ============================================================================

def test_find_duplicates_exact_match(consolidator, store):
    """Tìm trùng lặp chính xác."""
    # Tạo 2 KU giống hệt
    store._insert_unit(
        knowledge_type='FACT', subject='Anh', predicate='là', object='Quan',
        statement="Anh là Quan", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    store._insert_unit(
        knowledge_type='FACT', subject='Anh', predicate='là', object='Quan',
        statement="Anh là Quan", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    
    dups = consolidator.find_duplicates()
    assert len(dups) >= 1
    assert dups[0]['similarity'] == 1.0
    assert dups[0]['action'] == 'merge'


def test_find_duplicates_similar(consolidator, store):
    """Tìm trùng lặp tương tự."""
    store._insert_unit(
        knowledge_type='FACT', subject='Anh', predicate='là', object='Quan',
        statement="Anh là Quanpt1", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    store._insert_unit(
        knowledge_type='FACT', subject='Anh', predicate='là', object='Quan',
        statement="Anh là Quan", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    
    dups = consolidator.find_duplicates()
    # (30/10/2026) FIX expectation: "Anh là Quanpt1" vs "Anh là Quan" chỉ
    # jaccard 0.5 (token-level) — dưới threshold 0.85 nên KHÔNG được báo là
    # duplicate (tránh merge nhầm tri thức khác nhau). Exact-match case
    # (test_find_duplicates_exact_match phía trên) đã cover đường 1.0.
    assert dups == []


def test_jaccard_similarity():
    """Test Jaccard similarity calculation."""
    # Tạo store tạm để test
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        s = DeepMemoryStore(f"{tmp}/test.db")
        consolidator = MemoryConsolidator(s)
        sim = consolidator._jaccard_similarity("anh là quan", "anh là quan")
        assert sim == 1.0
        
        sim = consolidator._jaccard_similarity("anh là quan", "em là tony")
        assert sim < 0.5
        s.close()


# ============================================================================
# CONSOLIDATION TESTS
# ============================================================================

def test_summarize_group(consolidator, store):
    """Tóm tắt nhóm tri thức."""
    # Tạo 3 KU
    ids = []
    for i in range(3):
        ku_id = store._insert_unit(
            knowledge_type='FACT', subject='Info', predicate='is', object=str(i),
            statement=f"Thông tin số {i}", source_refs=[], evidence_refs=[], scope='general',
            status='EXTRACTED', confidence=0.75
        )
        ids.append(ku_id)
    
    result = consolidator.summarize_group(ids, 'concise')
    assert 'summary_id' in result
    assert result['source_ku_ids'] == ids
    # (30/10/2026) FIX expectation: statement concise là "Tổng hợp N thông
    # tin: ..." (không có chữ SUMMARY — đó chỉ là prefix của chế độ
    # 'structured'); kiểm tra đúng format concise thực tế.
    assert 'Tổng hợp 3 thông tin' in result['summary_statement']


def test_merge_duplicates_a(consolidator, store):
    """Hợp nhất 2 KU, giữ bản A."""
    ku_a = store._insert_unit(
        knowledge_type='FACT', subject='A', predicate='is', object='1',
        statement="Statement A", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    ku_b = store._insert_unit(
        knowledge_type='FACT', subject='B', predicate='is', object='2',
        statement="Statement B", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    
    result = consolidator.merge_duplicates(ku_a, ku_b, keep='a')
    assert result['merged_id'] == ku_a
    assert ku_b in result['superseded_ids']
    assert result['action'] == 'supersede'


def test_merge_duplicates_combined(consolidator, store):
    """Hợp nhất 2 KU, kết hợp cả 2."""
    ku_a = store._insert_unit(
        knowledge_type='FACT', subject='A', predicate='is', object='1',
        statement="Statement A", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    ku_b = store._insert_unit(
        knowledge_type='FACT', subject='B', predicate='is', object='2',
        statement="Statement B", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    
    result = consolidator.merge_duplicates(ku_a, ku_b, keep='combined')
    assert result['merged_id'] != ku_a
    assert result['merged_id'] != ku_b
    assert set(result['superseded_ids']) == {ku_a, ku_b}
    assert result['action'] == 'combine'


# ============================================================================
# TEMPORAL ENGINE TESTS
# ============================================================================

def test_update_temporal_context(engine, store):
    """Cập nhật ngữ cảnh thời gian cho KU."""
    ku_id = store._insert_unit(
        knowledge_type='FACT', subject='A', predicate='is', object='1',
        statement="Test statement", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    
    # Use a recent date to ensure freshness > 0
    result = engine.update_temporal_context(ku_id, "hôm nay")
    assert result['ku_id'] == ku_id
    assert result['valid_from'] is not None
    assert result['freshness_score'] > 0


def test_get_freshness_scores(engine, store):
    """Lấy freshness scores."""
    # Tạo KU mới
    store._insert_unit(
        knowledge_type='FACT', subject='A', predicate='is', object='1',
        statement="New statement", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    
    scores = engine.get_freshness_scores()
    assert len(scores) >= 1
    assert scores[0]['freshness_score'] > 0.5


def test_run_maintenance(engine, store):
    """Chạy automated maintenance."""
    # Tạo 1 KU cũ (giả lập)
    ku_id = store._insert_unit(
        knowledge_type='FACT', subject='A', predicate='is', object='1',
        statement="Old statement", source_refs=[], evidence_refs=[], scope='general',
        status='EXTRACTED', confidence=0.75
    )
    
    result = engine.run_maintenance(archive_threshold_days=1)  # Archive sau 1 ngày
    assert 'archived' in result
    assert 'duplicates_found' in result
    assert 'stale_count' in result


def test_consolidate_memory(engine, store):
    """Tự động tóm tắt nhóm tri thức."""
    # Tạo 5 KU cùng scope
    for i in range(5):
        store._insert_unit(
            knowledge_type='FACT', subject='Info', predicate='is', object=str(i),
            statement=f"Thông tin {i}", source_refs=[], evidence_refs=[], scope='test_scope',
            status='EXTRACTED', confidence=0.75
        )
    
    result = engine.consolidate_memory(scope='test_scope', min_group_size=3)
    assert result['summaries_created'] >= 1
    assert result['groups_processed'] >= 1
    assert len(result['summary_ids']) >= 1


# ============================================================================
# EDGE CASES
# ============================================================================

def test_archive_stale_nothing(engine, store):
    """Archive không có gì để archive."""
    result = engine._consolidator.archive_stale(days_threshold=365)
    assert result['archived_count'] == 0


def test_summarize_empty_group(consolidator, store):
    """Tóm tắt nhóm rỗng."""
    with pytest.raises(ValueError):
        consolidator.summarize_group([])


def test_merge_nonexistent_units(consolidator, store):
    """Hợp nhất KU không tồn tại."""
    with pytest.raises(ValueError):
        consolidator.merge_duplicates('nonexistent_a', 'nonexistent_b')