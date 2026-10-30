"""V13 — Memory Quality Scoring & Automated Maintenance.

Tự động đánh giá chất lượng memory (confidence, freshness, relevance, verification) +
automated maintenance (archiving, dedup, decay, refresh).

**Quality Scoring:**
- Overall quality score: weighted average của confidence, freshness, relevance, verification
- Confidence decay: giảm theo thời gian (decay_rate=0.005/ngày)
- Freshness score: dựa trên valid_from/updated_at (decay exponential)
- Relevance score: semantic similarity với query (placeholder cho embedding)

**Automated Maintenance:**
- Archive stale: KU cũ (valid_until < now hoặc updated_at > 90 ngày)
- Merge duplicates: KU trùng (Jaccard ≥ 0.85) — cần owner confirmation
- Decay confidence: giảm confidence theo thời gian
- Refresh high-value: KU có quality_score > 0.8 nhưng confidence < 0.7

**API endpoints:**
- GET /api/memory/quality/{metrics,scores,low-quality,stale}
- POST /api/memory/maintenance/{run,daily,policy,report}
- GET /api/memory/maintenance/history

**Tests:** 18 tests covering quality scoring, metrics, maintenance, policies.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from enum import Enum

from quan_ai_brain.memory.deep_memory import DeepMemoryStore


# ============================================================================
# QUALITY SCORING
# ============================================================================

class QualityLevel(Enum):
    """Mức độ chất lượng memory."""
    HIGH = "high"       # score >= 0.7
    MEDIUM = "medium"   # 0.4 <= score < 0.7
    LOW = "low"         # score < 0.4


@dataclass
class QualityScore:
    """Quality score cho 1 KU."""
    ku_id: str
    overall: float
    confidence: float
    freshness: float
    relevance: float
    verification: float
    level: QualityLevel
    factors: dict[str, Any] = field(default_factory=dict)


def calculate_confidence_score(ku: dict, decay_rate: float = 0.005) -> float:
    """Tính confidence score với decay theo thời gian.
    
    Args:
        ku: Knowledge unit dict
        decay_rate: Tốc độ decay theo ngày (mặc định: 0.005 = 0.5%/ngày)
    
    Returns:
        Confidence score sau decay (0.0-1.0)
    """
    base_confidence = ku.get('confidence', 0.5)
    updated_at = ku.get('updated_at_utc')
    
    if not updated_at:
        return base_confidence
    
    try:
        update_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        days_elapsed = (datetime.now(timezone.utc) - update_time).days
        decay_factor = math.exp(-decay_rate * days_elapsed)
        
        return max(0.1, base_confidence * decay_factor)
    except:
        return base_confidence


def calculate_freshness_score(ku: dict, reference_date: datetime | None = None) -> float:
    """Tính freshness score dựa trên valid_from/updated_at.
    
    Args:
        ku: Knowledge unit dict
        reference_date: Thời điểm tham chiếu (mặc định: now)
    
    Returns:
        Freshness score (0.0-1.0)
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)
    
    # Ưu tiên valid_from nếu có
    valid_from = ku.get('valid_from_utc')
    updated_at = ku.get('updated_at_utc')
    
    if valid_from:
        try:
            from_time = datetime.fromisoformat(valid_from.replace('Z', '+00:00'))
            days_old = (reference_date - from_time).days
        except:
            days_old = 0
    elif updated_at:
        try:
            update_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            days_old = (reference_date - update_time).days
        except:
            days_old = 0
    else:
        days_old = 0
    
    # Exponential decay: score = e^(-0.01 * days)
    decay_rate = 0.01
    score = math.exp(-decay_rate * days_old)
    
    return max(0.0, min(1.0, score))


def calculate_relevance_score(ku: dict, query: str) -> float:
    """Tính relevance score dựa trên keyword match (placeholder cho embedding).
    
    Args:
        ku: Knowledge unit dict
        query: Truy vấn tìm kiếm
    
    Returns:
        Relevance score (0.0-1.0)
    """
    statement = ku.get('statement', '').lower()
    query_terms = query.lower().split()
    
    if not query_terms:
        return 0.5
    
    # Đếm từ trùng (simple keyword match)
    matches = sum(1 for term in query_terms if term in statement)
    relevance = matches / len(query_terms)
    
    return min(1.0, relevance)


def calculate_verification_score(ku: dict) -> float:
    """Tính verification score dựa trên verification_status.
    
    Args:
        ku: Knowledge unit dict
    
    Returns:
        Verification score (0.0-1.0)
    """
    status = ku.get('verification_status', 'unverified')
    review_status = ku.get('review_status', '')
    
    # Mapping status → score
    status_scores = {
        'verified': 1.0,
        'owner_clarified': 0.9,
        'reviewed': 0.8,
        'pending_review': 0.5,
        'unverified': 0.3,
        'rejected': 0.0,
    }
    
    base_score = status_scores.get(status, 0.3)
    
    # Boost nếu có owner clarification
    if 'OWNER_CLARIFIED' in review_status or 'RESTORED_BY_UNDO' in review_status:
        base_score = min(1.0, base_score + 0.1)
    
    return base_score


def calculate_quality_score(
    ku: dict,
    query: str | None = None,
    confidence_weight: float = 0.3,
    freshness_weight: float = 0.3,
    relevance_weight: float = 0.2,
    verification_weight: float = 0.2
) -> QualityScore:
    """Tính overall quality score cho 1 KU.
    
    Args:
        ku: Knowledge unit dict
        query: Truy vấn (optional, cho relevance score)
        confidence_weight: Trọng số confidence
        freshness_weight: Trọng số freshness
        relevance_weight: Trọng số relevance
        verification_weight: Trọng số verification
    
    Returns:
        QualityScore object
    """
    confidence = calculate_confidence_score(ku)
    freshness = calculate_freshness_score(ku)
    relevance = calculate_relevance_score(ku, query) if query else 0.5
    verification = calculate_verification_score(ku)
    
    # Weighted average
    overall = (
        confidence_weight * confidence +
        freshness_weight * freshness +
        relevance_weight * relevance +
        verification_weight * verification
    )
    
    # Determine level
    if overall >= 0.7:
        level = QualityLevel.HIGH
    elif overall >= 0.4:
        level = QualityLevel.MEDIUM
    else:
        level = QualityLevel.LOW
    
    return QualityScore(
        ku_id=ku['knowledge_id'],
        overall=round(overall, 3),
        confidence=round(confidence, 3),
        freshness=round(freshness, 3),
        relevance=round(relevance, 3),
        verification=round(verification, 3),
        level=level,
        factors={
            'status': ku.get('status'),
            'verification_status': ku.get('verification_status'),
            'review_status': ku.get('review_status'),
            'valid_from': ku.get('valid_from_utc'),
            'updated_at': ku.get('updated_at_utc'),
        }
    )


# ============================================================================
# QUALITY METRICS
# ============================================================================

@dataclass
class QualityMetrics:
    """Thống kê chất lượng memory."""
    total_kus: int
    high_quality_count: int
    medium_quality_count: int
    low_quality_count: int
    average_quality: float
    average_confidence: float
    average_freshness: float
    average_verification: float
    by_scope: dict[str, dict[str, int]] = field(default_factory=dict)


class MemoryQualityAnalyzer:
    """Phân tích chất lượng memory."""
    
    def __init__(self, store: DeepMemoryStore):
        self._store = store
    
    def get_quality_metrics(self, scope: str | None = None) -> QualityMetrics:
        """Lấy thống kê chất lượng.
        
        Args:
            scope: Lọc theo scope (None = tất cả)
        
        Returns:
            QualityMetrics object
        """
        # Lấy tất cả KU
        query = "SELECT * FROM knowledge_units WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED')"
        if scope:
            query += " AND scope = ?"
            rows = self._store._connection.execute(query, (scope,)).fetchall()
        else:
            rows = self._store._connection.execute(query).fetchall()
        
        kus = [dict(r) for r in rows]
        
        if not kus:
            return QualityMetrics(
                total_kus=0,
                high_quality_count=0,
                medium_quality_count=0,
                low_quality_count=0,
                average_quality=0.0,
                average_confidence=0.0,
                average_freshness=0.0,
                average_verification=0.0
            )
        
        # Tính quality scores
        scores = [calculate_quality_score(ku) for ku in kus]
        
        # Thống kê
        high_count = sum(1 for s in scores if s.level == QualityLevel.HIGH)
        medium_count = sum(1 for s in scores if s.level == QualityLevel.MEDIUM)
        low_count = sum(1 for s in scores if s.level == QualityLevel.LOW)
        
        avg_quality = sum(s.overall for s in scores) / len(scores)
        avg_confidence = sum(s.confidence for s in scores) / len(scores)
        avg_freshness = sum(s.freshness for s in scores) / len(scores)
        avg_verification = sum(s.verification for s in scores) / len(scores)
        
        # By scope
        by_scope: dict[str, dict[str, int]] = {}
        for ku in kus:
            ku_scope = ku.get('scope') or 'general'
            if ku_scope not in by_scope:
                by_scope[ku_scope] = {'high': 0, 'medium': 0, 'low': 0}
        
        for s in scores:
            ku_scope = next((ku.get('scope') or 'general' for ku in kus if ku['knowledge_id'] == s.ku_id), 'general')
            by_scope[ku_scope][s.level.value] += 1
        
        return QualityMetrics(
            total_kus=len(kus),
            high_quality_count=high_count,
            medium_quality_count=medium_count,
            low_quality_count=low_count,
            average_quality=round(avg_quality, 3),
            average_confidence=round(avg_confidence, 3),
            average_freshness=round(avg_freshness, 3),
            average_verification=round(avg_verification, 3),
            by_scope=by_scope
        )
    
    def find_low_quality_kus(self, threshold: float = 0.4, limit: int = 50) -> list[QualityScore]:
        """Tìm KU chất lượng thấp.
        
        Args:
            threshold: Ngưỡng quality score (dưới threshold = low quality)
            limit: Giới hạn số kết quả
        
        Returns:
            List of QualityScore sorted by overall ascending
        """
        query = "SELECT * FROM knowledge_units WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED') LIMIT 200"
        rows = self._store._connection.execute(query).fetchall()
        kus = [dict(r) for r in rows]
        
        scores = [calculate_quality_score(ku) for ku in kus]
        low_quality = [s for s in scores if s.overall < threshold]
        low_quality.sort(key=lambda s: s.overall)
        
        return low_quality[:limit]
    
    def find_stale_kus(self, days_threshold: int = 90, limit: int = 50) -> list[dict[str, Any]]:
        """Tìm KU cũ (stale).
        
        Args:
            days_threshold: Số ngày để coi là cũ (mặc định: 90)
            limit: Giới hạn số kết quả
        
        Returns:
            List of KU dicts sorted by updated_at descending
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        
        query = """
            SELECT knowledge_id, statement, updated_at_utc, valid_until_utc
            FROM knowledge_units
            WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED')
            AND (
                (updated_at_utc IS NOT NULL AND datetime(updated_at_utc) < datetime(?))
                OR (valid_until_utc IS NOT NULL AND datetime(valid_until_utc) < datetime(?))
            )
            ORDER BY updated_at_utc DESC
            LIMIT ?
        """
        
        rows = self._store._connection.execute(
            query, (cutoff_date.isoformat(), cutoff_date.isoformat(), limit)
        ).fetchall()
        
        return [dict(r) for r in rows]
    
    def get_quality_scores(self, scope: str | None = None, limit: int = 100) -> list[QualityScore]:
        """Lấy quality scores cho danh sách KU.
        
        Args:
            scope: Lọc theo scope
            limit: Giới hạn số kết quả
        
        Returns:
            List of QualityScore
        """
        query = "SELECT * FROM knowledge_units WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED')"
        if scope:
            query += " AND scope = ?"
            query += " LIMIT ?"
            rows = self._store._connection.execute(query, (scope, limit)).fetchall()
        else:
            query += " LIMIT ?"
            rows = self._store._connection.execute(query, (limit,)).fetchall()
        
        kus = [dict(r) for r in rows]
        return [calculate_quality_score(ku) for ku in kus]


# ============================================================================
# AUTOMATED MAINTENANCE
# ============================================================================

@dataclass
class MaintenancePolicy:
    """Policy cho automated maintenance."""
    archive_threshold_days: int = 90
    merge_threshold: float = 0.85
    confidence_decay_rate: float = 0.005
    refresh_high_value_threshold: float = 0.8
    min_confidence_for_refresh: float = 0.7
    scope: str | None = None


@dataclass
class MaintenanceResult:
    """Kết quả maintenance run."""
    run_id: str
    started_at: str
    finished_at: str
    policy: dict[str, Any]
    archived_count: int
    merged_count: int
    decayed_count: int
    refreshed_count: int
    errors: list[str] = field(default_factory=list)


class AutomatedMaintenance:
    """Automated maintenance cho memory."""
    
    def __init__(self, store: DeepMemoryStore, policy: MaintenancePolicy | None = None):
        self._store = store
        self._policy = policy or MaintenancePolicy()
        self._analyzer = MemoryQualityAnalyzer(store)
    
    def run_daily_maintenance(self) -> MaintenanceResult:
        """Chạy maintenance hàng ngày.
        
        Returns:
            MaintenanceResult
        """
        import uuid
        run_id = f"maint_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now(timezone.utc).isoformat()
        errors = []
        
        archived = 0
        merged = 0
        decayed = 0
        refreshed = 0
        
        try:
            # 1. Archive stale
            archived = self.archive_stale(self._policy.archive_threshold_days)
            
            # 2. Merge duplicates (chỉ báo cáo, không tự merge — cần owner confirmation)
            merged = self._find_duplicates_for_merge(self._policy.merge_threshold)
            
            # 3. Decay confidence
            decayed = self.decay_confidence(self._policy.confidence_decay_rate)
            
            # 4. Refresh high-value KU
            refreshed = self.refresh_high_value_kus(
                self._policy.refresh_high_value_threshold,
                self._policy.min_confidence_for_refresh
            )
        except Exception as e:
            errors.append(str(e))
        
        finished_at = datetime.now(timezone.utc).isoformat()
        
        return MaintenanceResult(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            policy={
                'archive_threshold_days': self._policy.archive_threshold_days,
                'merge_threshold': self._policy.merge_threshold,
                'confidence_decay_rate': self._policy.confidence_decay_rate,
                'refresh_high_value_threshold': self._policy.refresh_high_value_threshold,
                'min_confidence_for_refresh': self._policy.min_confidence_for_refresh,
                'scope': self._policy.scope
            },
            archived_count=archived,
            merged_count=merged,
            decayed_count=decayed,
            refreshed_count=refreshed,
            errors=errors
        )
    
    def archive_stale(self, days_threshold: int | None = None) -> int:
        """Archive KU cũ.
        
        Args:
            days_threshold: Số ngày để coi là cũ (override policy)
        
        Returns:
            Số KU đã archive
        """
        threshold = days_threshold or self._policy.archive_threshold_days
        stale_kus = self._analyzer.find_stale_kus(threshold, limit=100)
        
        archived = 0
        for ku in stale_kus:
            try:
                self._store._connection.execute(
                    "UPDATE knowledge_units SET status = 'ARCHIVED', updated_at_utc = datetime('now') "
                    "WHERE knowledge_id = ?",
                    (ku['knowledge_id'],)
                )
                archived += 1
            except Exception:
                pass
        
        return archived
    
    def _find_duplicates_for_merge(self, threshold: float | None = None) -> int:
        """Tìm KU trùng để merge (chỉ đếm, không merge).
        
        Args:
            threshold: Jaccard threshold (override policy)
        
        Returns:
            Số cặp trùng tìm thấy
        """
        from quan_ai_brain.cognition.temporal_memory import MemoryConsolidator
        
        consolidator = MemoryConsolidator(self._store)
        threshold = threshold or self._policy.merge_threshold
        
        duplicates = consolidator.find_duplicates(threshold=threshold)
        return len(duplicates)
    
    def decay_confidence(self, decay_rate: float | None = None) -> int:
        """Giảm confidence theo thời gian.
        
        Args:
            decay_rate: Decay rate (override policy)
        
        Returns:
            Số KU đã decay
        """
        rate = decay_rate or self._policy.confidence_decay_rate
        
        # Lấy tất cả KU
        rows = self._store._connection.execute(
            "SELECT knowledge_id, confidence, updated_at_utc FROM knowledge_units "
            "WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED')"
        ).fetchall()
        
        decayed = 0
        for r in rows:
            ku_id, confidence, updated_at = r
            
            # Tính decay
            if updated_at:
                try:
                    update_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    days_elapsed = (datetime.now(timezone.utc) - update_time).days
                    new_confidence = max(0.1, confidence * math.exp(-rate * days_elapsed))
                    
                    if new_confidence != confidence:
                        self._store._connection.execute(
                            "UPDATE knowledge_units SET confidence = ?, updated_at_utc = datetime('now') "
                            "WHERE knowledge_id = ?",
                            (round(new_confidence, 3), ku_id)
                        )
                        decayed += 1
                except:
                    pass
        
        return decayed
    
    def refresh_high_value_kus(
        self,
        quality_threshold: float | None = None,
        min_confidence: float | None = None
    ) -> int:
        """Refresh KU có giá trị cao nhưng confidence thấp.
        
        Args:
            quality_threshold: Quality score threshold (override policy)
            min_confidence: Minimum confidence (override policy)
        
        Returns:
            Số KU đã refresh
        """
        threshold = quality_threshold or self._policy.refresh_high_value_threshold
        confidence_min = min_confidence or self._policy.min_confidence_for_refresh
        
        # Lấy KU có quality cao nhưng confidence thấp
        scores = self._analyzer.get_quality_scores(limit=200)
        high_value_low_conf = [s for s in scores if s.overall >= threshold and s.confidence < confidence_min]
        
        refreshed = 0
        for score in high_value_low_conf:
            try:
                # Boost confidence
                self._store._connection.execute(
                    "UPDATE knowledge_units SET confidence = GREATEST(confidence + 0.1, ?), "
                    "verification_status = 'reviewed', updated_at_utc = datetime('now') "
                    "WHERE knowledge_id = ?",
                    (confidence_min, score.ku_id)
                )
                refreshed += 1
            except Exception:
                pass
        
        return refreshed
    
    def apply_policy(self, policy: MaintenancePolicy) -> None:
        """Áp dụng policy mới.
        
        Args:
            policy: MaintenancePolicy object
        """
        self._policy = policy
    
    def generate_maintenance_report(self, result: MaintenanceResult) -> str:
        """Tạo báo cáo maintenance.
        
        Args:
            result: MaintenanceResult object
        
        Returns:
            Markdown report
        """
        report = f"""# Maintenance Report — {result.run_id}

**Started:** {result.started_at}  
**Finished:** {result.finished_at}  
**Duration:** {result.finished_at}

## Policy
- Archive threshold: {result.policy['archive_threshold_days']} days
- Merge threshold: {result.policy['merge_threshold']}
- Confidence decay rate: {result.policy['confidence_decay_rate']}
- Refresh high-value threshold: {result.policy['refresh_high_value_threshold']}

## Results
- **Archived:** {result.archived_count} KU
- **Duplicates found:** {result.merged_count} pairs (chờ owner confirmation)
- **Confidence decayed:** {result.decayed_count} KU
- **High-value refreshed:** {result.refreshed_count} KU

## Errors
"""
        if result.errors:
            for error in result.errors:
                report += f"- {error}\n"
        else:
            report += "None\n"
        
        return report