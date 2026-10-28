"""V11 — Temporal Memory & Automatic Consolidation Engine.

Mở rộng chiều thời gian (valid_from/valid_until, time-decay, freshness) +
tự động tóm tắt, hợp nhất tri thức trùng lặp (memory consolidation).

**Chiều thời gian:**
- valid_from_utc: thời điểm tri thức có hiệu lực
- valid_until_utc: thời điểm tri thức hết hạn (NULL = vô hạn)
- freshness_score: 0.0-1.0 dựa trên age + decay_rate
- temporal_context: parsing từ hội thoại ("ngày 15/3", "tuần trước", "2024")

**Memory Consolidation:**
- Auto-summarize: tóm tắt nhóm tri thức liên quan thành memory summary
- Smart dedup: hợp nhất tri thức trùng (jaccard > 0.85) với versioning
- Decay & refresh: tự động đánh dấu stale (confidence giảm theo thời gian)
- Archiving: chuyển tri thức cũ sang candidate_knowledge_archive

**API endpoints:**
- GET /api/memory/temporal/{stats,decay,scores}
- POST /api/memory/consolidate/{summarize,merge,dedup,archive}
- POST /api/memory/maintenance/run (automated maintenance)

**Tests:** 12 tests covering temporal parsing, decay, consolidation, archiving.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from quan_ai_brain.memory.deep_memory import DeepMemoryStore
from quan_ai_brain.cognition.logical_reasoning import LogicalReasoningEngine


# ============================================================================
# TEMPORAL PARSING & DECAY
# ============================================================================

TEMPORAL_PATTERNS = {
    # Ngày cụ thể: "ngày 15/3/2024", "15/3/2024"
    'date': r'(?:ngày\s+)?(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})',
    # Tháng/Năm: "tháng 3/2024", "3/2024"
    'month_year': r'(?:tháng\s+)?(\d{1,2})[/\-](\d{2,4})',
    # Tương đối: "hôm qua", "ngày hôm qua", "hôm nay"
    'relative_day': r'(?:ngày\s+)?(hôm\s+(?:qua|nay)|hôm\s+(?:qua|nay))',
    # "tuần trước", "tháng trước", "năm ngoái"
    'relative_period': r'(tuần\s+(?:trước|qua)|tháng\s+(?:trước|qua)|năm\s+(?:ngoái|trước))',
    # "trong 2 ngày", "trong 3 tuần"
    'duration': r'(?:trong\s+)?(\d+)\s*(ngày|tuần|tháng|năm)',
}


def parse_temporal_context(text: str, reference_date: datetime | None = None) -> dict[str, Any]:
    """Trích xuất ngữ cảnh thời gian từ văn bản.
    
    Returns:
        {
            'valid_from': datetime | None,
            'valid_until': datetime | None,
            'temporal_type': 'specific' | 'relative' | 'duration' | None,
            'confidence': float (0.0-1.0)
        }
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)
    
    text_lower = text.lower()
    result = {
        'valid_from': None,
        'valid_until': None,
        'temporal_type': None,
        'confidence': 0.0
    }
    
    # 1. Ngày cụ thể
    match = re.search(TEMPORAL_PATTERNS['date'], text_lower)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 100:
            year += 2000 if year < 50 else 1900
        try:
            valid_from = datetime(year, month, day, tzinfo=timezone.utc)
            result['valid_from'] = valid_from
            result['temporal_type'] = 'specific'
            result['confidence'] = 0.95
            return result
        except ValueError:
            pass
    
    # 2. Tháng/Năm
    match = re.search(TEMPORAL_PATTERNS['month_year'], text_lower)
    if match:
        month, year = int(match.group(1)), int(match.group(2))
        if year < 100:
            year += 2000 if year < 50 else 1900
        try:
            valid_from = datetime(year, month, 1, tzinfo=timezone.utc)
            valid_until = datetime(year, month, 28, tzinfo=timezone.utc)  # Cuối tháng
            result['valid_from'] = valid_from
            result['valid_until'] = valid_until
            result['temporal_type'] = 'specific'
            result['confidence'] = 0.85
            return result
        except ValueError:
            pass
    
    # 3. Tương đối
    if 'hôm qua' in text_lower or 'ngày hôm qua' in text_lower:
        result['valid_from'] = reference_date - timedelta(days=1)
        result['valid_until'] = reference_date
        result['temporal_type'] = 'relative'
        result['confidence'] = 0.90
        return result
    
    if 'hôm nay' in text_lower or 'ngày hôm nay' in text_lower:
        result['valid_from'] = reference_date
        result['valid_until'] = reference_date + timedelta(days=1)
        result['temporal_type'] = 'relative'
        result['confidence'] = 0.90
        return result
    
    if 'tuần trước' in text_lower:
        result['valid_from'] = reference_date - timedelta(weeks=1)
        result['valid_until'] = reference_date
        result['temporal_type'] = 'relative'
        result['confidence'] = 0.85
        return result
    
    if 'tháng trước' in text_lower:
        result['valid_from'] = reference_date - timedelta(days=30)
        result['valid_until'] = reference_date
        result['temporal_type'] = 'relative'
        result['confidence'] = 0.80
        return result
    
    # 4. Duration
    match = re.search(TEMPORAL_PATTERNS['duration'], text_lower)
    if match:
        value, unit = int(match.group(1)), match.group(2)
        if unit in ('ngày', 'ngày'):
            delta = timedelta(days=value)
        elif unit in ('tuần', 'tuần'):
            delta = timedelta(weeks=value)
        elif unit in ('tháng', 'tháng'):
            delta = timedelta(days=30 * value)
        elif unit in ('năm', 'năm'):
            delta = timedelta(days=365 * value)
        else:
            delta = timedelta(days=value)
        
        result['valid_from'] = reference_date
        result['valid_until'] = reference_date + delta
        result['temporal_type'] = 'duration'
        result['confidence'] = 0.75
        return result
    
    return result


def calculate_freshness_score(
    valid_from: datetime | None,
    valid_until: datetime | None,
    reference_date: datetime | None = None,
    decay_rate: float = 0.01
) -> float:
    """Tính freshness score (0.0-1.0) dựa trên thời gian trôi qua.
    
    Args:
        valid_from: Thời điểm bắt đầu có hiệu lực
        valid_until: Thời điểm hết hạn (NULL = vô hạn)
        reference_date: Thời điểm tham chiếu (mặc định: now)
        decay_rate: Tốc độ suy giảm theo ngày (mặc định: 0.01 = 1%/ngày)
    
    Returns:
        Freshness score: 1.0 = mới nhất, 0.0 = cũ/hết hạn
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)
    
    # Nếu có valid_until và đã quá hạn → 0.0
    if valid_until and reference_date > valid_until:
        return 0.0
    
    # Nếu không có valid_from → dùng reference_date
    if valid_from is None:
        valid_from = reference_date
    
    # Tính số ngày trôi qua
    days_elapsed = (reference_date - valid_from).days
    
    # Decay exponential: score = e^(-decay_rate * days)
    import math
    score = math.exp(-decay_rate * days_elapsed)
    
    # Clamp về [0.0, 1.0]
    return max(0.0, min(1.0, score))


# ============================================================================
# MEMORY CONSOLIDATION
# ============================================================================

class MemoryConsolidator:
    """Tự động tóm tắt, hợp nhất tri thức trùng, tạo memory summaries."""
    
    def __init__(self, store: DeepMemoryStore, similarity_threshold: float = 0.85):
        self._store = store
        self._similarity_threshold = similarity_threshold
        self._engine = LogicalReasoningEngine(store)
    
    def find_duplicates(self, scope: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Tìm tri thức trùng lặp (jaccard similarity > threshold).
        
        Returns:
            List of {
                'ku_a': knowledge_id,
                'ku_b': knowledge_id,
                'similarity': float,
                'statement_a': str,
                'statement_b': str,
                'action': 'merge' | 'keep_both' | 'archive'
            }
        """
        # Lấy danh sách KU trong scope
        query = "SELECT knowledge_id, statement, scope FROM knowledge_units WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED')"
        if scope:
            query += " AND scope = ?"
            rows = self._store._connection.execute(query, (scope,)).fetchall()
        else:
            rows = self._store._connection.execute(query).fetchall()
        
        units = [{'id': r[0], 'statement': r[1], 'scope': r[2]} for r in rows[:limit]]
        duplicates = []
        
        # So sánh từng cặp (O(n²) — chấp nhận cho dataset nhỏ)
        for i, u1 in enumerate(units):
            for u2 in units[i+1:]:
                sim = self._jaccard_similarity(u1['statement'], u2['statement'])
                if sim >= self._similarity_threshold:
                    # Đề xuất action dựa trên version + status
                    action = 'merge' if sim >= 0.95 else 'keep_both'
                    duplicates.append({
                        'ku_a': u1['id'],
                        'ku_b': u2['id'],
                        'similarity': round(sim, 3),
                        'statement_a': u1['statement'][:100],
                        'statement_b': u2['statement'][:100],
                        'action': action
                    })
        
        return duplicates
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Tính Jaccard similarity giữa 2 văn bản."""
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def summarize_group(
        self,
        ku_ids: list[str],
        summary_type: str = 'concise'
    ) -> dict[str, Any]:
        """Tóm tắt nhóm tri thức liên quan thành 1 memory summary.
        
        Args:
            ku_ids: Danh sách knowledge_unit IDs
            summary_type: 'concise' | 'detailed' | 'structured'
        
        Returns:
            {
                'summary_id': str,
                'summary_statement': str,
                'source_ku_ids': list[str],
                'summary_type': str,
                'created_at': datetime
            }
        """
        # Lấy nội dung các KU
        units = []
        for ku_id in ku_ids:
            unit = self._store.get_unit(ku_id)
            if unit:
                units.append(unit)
        
        if not units:
            raise ValueError(f"No units found for IDs: {ku_ids}")
        
        # Tạo summary statement
        statements = [u['statement'] for u in units]
        
        if summary_type == 'concise':
            # Tóm tắt ngắn: "Có X thông tin về Y"
            summary = f"Tổng hợp {len(statements)} thông tin: {'; '.join(statements[:3])}"
            if len(statements) > 3:
                summary += f" và {len(statements) - 3} thông tin khác."
        elif summary_type == 'detailed':
            # Tóm tắt chi tiết
            summary = " | ".join(statements)
        else:  # structured
            # Tóm tắt có cấu trúc
            summary = f"[SUMMARY of {len(statements)} items] " + " | ".join(statements[:5])
        
        # Lưu summary như 1 KU mới
        subject, predicate, obj = self._store._decompose(summary, 'FACT')
        
        summary_id = self._store._insert_unit(
            knowledge_type='SUMMARY',
            subject=subject,
            predicate=predicate,
            object=obj,
            statement=summary,
            source_refs=[f"consolidation:{','.join(ku_ids)}"],
            evidence_refs=ku_ids,
            scope=units[0].get('scope', 'general'),
            status='VERIFIED',
            confidence=0.85,
            meta={
                'summary_type': summary_type,
                'source_count': len(ku_ids),
                'source_ku_ids': ku_ids
            }
        )
        
        # Tạo quan hệ SUPPORTS từ summary → từng KU
        for ku_id in ku_ids:
            self._store._connection.execute(
                "INSERT OR IGNORE INTO knowledge_relations "
                "(relation_id, from_id, relation_type, to_id, basis, is_speculative, created_at_utc) "
                "VALUES (?,?,?,?,?,?,datetime('now'))",
                (f"r_{summary_id[2:8]}{ku_id[2:8]}", summary_id, 'SUPPORTS', ku_id,
                 f"Summary derived from {ku_id}", 0)
            )
        
        return {
            'summary_id': summary_id,
            'summary_statement': summary[:200],
            'source_ku_ids': ku_ids,
            'summary_type': summary_type,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    
    def merge_duplicates(
        self,
        ku_a: str,
        ku_b: str,
        keep: str = 'a'
    ) -> dict[str, Any]:
        """Hợp nhất 2 tri thức trùng lặp.
        
        Args:
            ku_a, ku_b: Knowledge unit IDs
            keep: 'a' | 'b' | 'combined' — giữ bản nào
        
        Returns:
            {
                'merged_id': str,
                'superseded_ids': list[str],
                'action': 'supersede' | 'combine'
            }
        """
        unit_a = self._store.get_unit(ku_a)
        unit_b = self._store.get_unit(ku_b)
        
        if not unit_a or not unit_b:
            raise ValueError(f"Unit not found: {ku_a} or {ku_b}")
        
        if keep == 'combined':
            # Kết hợp cả 2
            new_statement = f"{unit_a['statement']} | {unit_b['statement']}"
            subject, predicate, obj = self._store._decompose(new_statement, unit_a.get('knowledge_type', 'FACT'))
            
            merged_id = self._store._insert_unit(
                knowledge_type=unit_a.get('knowledge_type', 'FACT'),
                subject=subject,
                predicate=predicate,
                object=obj,
                statement=new_statement,
                source_refs=json.dumps([unit_a.get('source_refs_json', '[]'), unit_b.get('source_refs_json', '[]')]),
                evidence_refs=json.dumps([ku_a, ku_b]),
                scope=unit_a.get('scope', unit_b.get('scope', 'general')),
                status='VERIFIED',
                confidence=max(unit_a.get('confidence', 0.5), unit_b.get('confidence', 0.5)),
                extraction_meta=json.dumps({
                    'merged_from': [ku_a, ku_b],
                    'merge_type': 'combined'
                })
            )
            
            # Supersede cả 2
            self._store.supersede_unit(ku_a, statement=unit_a['statement'], updates={'review_status': 'SUPERSEDED'}, owner_answer=f"merged into {merged_id}")
            self._store.supersede_unit(ku_b, statement=unit_b['statement'], updates={'review_status': 'SUPERSEDED'}, owner_answer=f"merged into {merged_id}")
            
            return {
                'merged_id': merged_id,
                'superseded_ids': [ku_a, ku_b],
                'action': 'combine'
            }
        else:
            # Giữ bản A hoặc B, supersede bản kia
            keep_unit = unit_a if keep == 'a' else unit_b
            supersede_unit_id = ku_b if keep == 'a' else ku_a
            
            self._store.supersede_unit(
                supersede_unit_id,
                statement=keep_unit['statement'],
                updates={'review_status': 'SUPERSEDED'},
                owner_answer=f"merged into {keep_unit['knowledge_id']}"
            )
            
            return {
                'merged_id': keep_unit['knowledge_id'],
                'superseded_ids': [supersede_unit_id],
                'action': 'supersede'
            }
    
    def archive_stale(
        self,
        days_threshold: int = 90,
        scope: str | None = None
    ) -> dict[str, Any]:
        """Đánh dấu tri thức cũ (stale) để archiving.
        
        Args:
            days_threshold: Số ngày để coi là cũ (mặc định: 90)
            scope: Lọc theo scope (optional)
        
        Returns:
            {
                'archived_count': int,
                'archived_ku_ids': list[str],
                'criteria': str
            }
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        
        query = """
            UPDATE knowledge_units 
            SET status = 'ARCHIVED', updated_at_utc = datetime('now')
            WHERE status = 'EXTRACTED' 
            AND (
                (valid_until_utc IS NOT NULL AND valid_until_utc < ?)
                OR (valid_from_utc IS NOT NULL AND updated_at_utc < ?)
                OR (valid_from_utc IS NULL AND updated_at_utc < ?)
            )
        """
        
        params = [cutoff_date.isoformat(), cutoff_date.isoformat(), cutoff_date.isoformat()]
        
        if scope:
            query += " AND scope = ?"
            params.append(scope)
        
        cur = self._store._connection.execute(query, params)
        archived_count = cur.rowcount
        
        # Lấy danh sách KU đã archive
        archived_ids = [
            r[0] for r in self._store._connection.execute(
                "SELECT knowledge_id FROM knowledge_units WHERE status = 'ARCHIVED' ORDER BY updated_at_utc DESC LIMIT 100"
            ).fetchall()
        ]
        
        return {
            'archived_count': archived_count,
            'archived_ku_ids': archived_ids[:20],  # Giới hạn hiển thị
            'criteria': f"valid_until < {cutoff_date.isoformat()} OR updated_at < {cutoff_date.isoformat()}"
        }


# ============================================================================
# TEMPORAL MEMORY ENGINE
# ============================================================================

class TemporalMemoryEngine:
    """Quản lý chiều thời gian của trí nhớ: valid_from, valid_until, freshness."""
    
    def __init__(self, store: DeepMemoryStore, default_decay_rate: float = 0.01):
        self._store = store
        self._consolidator = MemoryConsolidator(store)
        self._default_decay_rate = default_decay_rate
    
    def update_temporal_context(
        self,
        ku_id: str,
        text: str,
        reference_date: datetime | None = None
    ) -> dict[str, Any]:
        """Cập nhật ngữ cảnh thời gian cho 1 KU.
        
        Args:
            ku_id: Knowledge unit ID
            text: Văn bản chứa thông tin thời gian
            reference_date: Thời điểm tham chiếu
        
        Returns:
            {
                'ku_id': str,
                'valid_from': datetime | None,
                'valid_until': datetime | None,
                'temporal_type': str | None,
                'confidence': float,
                'freshness_score': float
            }
        """
        temporal = parse_temporal_context(text, reference_date)
        
        if temporal['valid_from'] or temporal['valid_until']:
            # Cập nhật KU
            with self._store._lock, self._store._connection:
                self._store._connection.execute(
                    "UPDATE knowledge_units SET valid_from_utc = ?, valid_until_utc = ?, "
                    "updated_at_utc = datetime('now') "
                    "WHERE knowledge_id = ?",
                    (
                        temporal['valid_from'].isoformat() if temporal['valid_from'] else None,
                        temporal['valid_until'].isoformat() if temporal['valid_until'] else None,
                        ku_id
                    )
                )
        
        freshness = calculate_freshness_score(
            temporal['valid_from'],
            temporal['valid_until'],
            reference_date,
            self._default_decay_rate
        )
        
        return {
            'ku_id': ku_id,
            'valid_from': temporal['valid_from'],
            'valid_until': temporal['valid_until'],
            'temporal_type': temporal['temporal_type'],
            'confidence': temporal['confidence'],
            'freshness_score': round(freshness, 3)
        }
    
    def get_freshness_scores(
        self,
        scope: str | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Lấy freshness score cho danh sách KU.
        
        Returns:
            List of {
                'knowledge_id': str,
                'statement': str,
                'valid_from': datetime | None,
                'valid_until': datetime | None,
                'freshness_score': float,
                'age_days': int
            }
        """
        query = """
            SELECT knowledge_id, statement, valid_from_utc, valid_until_utc, updated_at_utc
            FROM knowledge_units
            WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED')
        """
        if scope:
            query += " AND scope = ?"
            query += " ORDER BY updated_at_utc DESC LIMIT ?"
            rows = self._store._connection.execute(query, (scope, limit)).fetchall()
        else:
            query += " ORDER BY updated_at_utc DESC LIMIT ?"
            rows = self._store._connection.execute(query, (limit,)).fetchall()
        
        now = datetime.now(timezone.utc)
        scores = []
        for r in rows:
            valid_from = datetime.fromisoformat(r[2]) if r[2] else None
            valid_until = datetime.fromisoformat(r[3]) if r[3] else None
            
            freshness = calculate_freshness_score(valid_from, valid_until, now, self._default_decay_rate)
            age_days = (now - valid_from).days if valid_from else 0
            
            scores.append({
                'knowledge_id': r[0],
                'statement': r[1][:100],
                'valid_from': r[2],
                'valid_until': r[3],
                'freshness_score': round(freshness, 3),
                'age_days': age_days
            })
        
        return scores
    
    def run_maintenance(
        self,
        archive_threshold_days: int = 90,
        merge_threshold: float = 0.85,
        scope: str | None = None
    ) -> dict[str, Any]:
        """Chạy automated maintenance: archive + dedup + decay.
        
        Returns:
            {
                'archived': dict,
                'duplicates_found': int,
                'duplicates_merged': int,
                'stale_count': int
            }
        """
        # 1. Archive stale
        archive_result = self._consolidator.archive_stale(archive_threshold_days, scope)
        
        # 2. Find duplicates
        duplicates = self._consolidator.find_duplicates(scope, limit=50)
        
        # 3. Count stale (freshness < 0.3)
        scores = self.get_freshness_scores(scope, limit=200)
        stale_count = sum(1 for s in scores if s['freshness_score'] < 0.3)
        
        return {
            'archived': archive_result,
            'duplicates_found': len(duplicates),
            'duplicates_merged': 0,  # Cần xác nhận chủ trước khi merge
            'stale_count': stale_count,
            'maintenance_run_at': datetime.now(timezone.utc).isoformat()
        }
    
    def consolidate_memory(
        self,
        scope: str | None = None,
        summary_type: str = 'concise',
        min_group_size: int = 3
    ) -> dict[str, Any]:
        """Tự động tóm tắt nhóm tri thức liên quan.
        
        Args:
            scope: Lọc theo scope
            summary_type: 'concise' | 'detailed' | 'structured'
            min_group_size: Tối thiểu số KU để tạo summary
        
        Returns:
            {
                'summaries_created': int,
                'summary_ids': list[str],
                'groups_processed': int
            }
        """
        # Lấy KU theo scope
        query = "SELECT knowledge_id, scope FROM knowledge_units WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED')"
        if scope:
            query += " AND scope = ?"
            rows = self._store._connection.execute(query, (scope,)).fetchall()
        else:
            rows = self._store._connection.execute(query).fetchall()
        
        # Nhóm theo scope
        groups: dict[str, list[str]] = {}
        for r in rows:
            ku_scope = r[1] or 'general'
            if ku_scope not in groups:
                groups[ku_scope] = []
            groups[ku_scope].append(r[0])
        
        summaries_created = 0
        summary_ids = []
        
        # Tạo summary cho mỗi nhóm đủ lớn
        for group_scope, ku_ids in groups.items():
            if len(ku_ids) >= min_group_size:
                try:
                    result = self._consolidator.summarize_group(ku_ids, summary_type)
                    summaries_created += 1
                    summary_ids.append(result['summary_id'])
                except Exception:
                    pass  # Bỏ qua nhóm không tóm tắt được
        
        return {
            'summaries_created': summaries_created,
            'summary_ids': summary_ids,
            'groups_processed': len(groups)
        }