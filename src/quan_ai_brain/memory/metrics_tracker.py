"""Metrics Tracker - Performance metrics collection.

Provides:
- Task performance metrics
- Resource usage tracking
- Quality metrics
- Trend analysis
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from pathlib import Path


@dataclass
class PerformanceMetric:
    """Single performance metric."""
    id: str
    task_id: str
    metric_name: str
    metric_value: float
    unit: str
    timestamp: str
    context_json: str = '{}'
    metadata_json: str = '{}'
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'PerformanceMetric':
        return cls(**data)


@dataclass
class TaskMetrics:
    """Aggregated task metrics."""
    task_id: str
    total_duration_ms: float
    actions_count: int
    success_rate: float
    avg_action_duration_ms: float
    error_count: int
    memory_peak_mb: float | None = None
    cpu_avg_percent: float | None = None
    api_calls_count: int = 0
    data_processed_mb: float = 0.0
    quality_score: float | None = None
    metadata_json: str = '{}'
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TaskMetrics':
        return cls(**data)


class MetricsTracker:
    """Track and analyze performance metrics."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize metrics tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                unit TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                context_json TEXT NOT NULL DEFAULT '{}',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Task metrics summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_metrics_summary (
                task_id TEXT PRIMARY KEY,
                total_duration_ms REAL NOT NULL,
                actions_count INTEGER NOT NULL,
                success_rate REAL NOT NULL,
                avg_action_duration_ms REAL NOT NULL,
                error_count INTEGER NOT NULL,
                memory_peak_mb REAL,
                cpu_avg_percent REAL,
                api_calls_count INTEGER NOT NULL DEFAULT 0,
                data_processed_mb REAL NOT NULL DEFAULT 0.0,
                quality_score REAL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (task_id) REFERENCES task_journals(task_id)
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_task 
            ON performance_metrics(task_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_name 
            ON performance_metrics(metric_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_time 
            ON performance_metrics(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def record_metric(self, task_id: str, metric_name: str, metric_value: float,
                     unit: str = "unit", context: dict | None = None,
                     metadata: dict | None = None) -> str:
        """Record a performance metric."""
        import uuid
        metric_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        metric = PerformanceMetric(
            id=metric_id,
            task_id=task_id,
            metric_name=metric_name,
            metric_value=metric_value,
            unit=unit,
            timestamp=now,
            context_json=json.dumps(context or {}),
            metadata_json=json.dumps(metadata or {})
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO performance_metrics 
            (id, task_id, metric_name, metric_value, unit, timestamp, 
             context_json, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metric.id,
            metric.task_id,
            metric.metric_name,
            metric.metric_value,
            metric.unit,
            metric.timestamp,
            metric.context_json,
            metric.metadata_json
        ))
        
        conn.commit()
        conn.close()
        
        return metric_id
    
    def record_task_metrics(self, task_id: str, total_duration_ms: float,
                           actions_count: int, success_rate: float,
                           avg_action_duration_ms: float, error_count: int,
                           memory_peak_mb: float | None = None,
                           cpu_avg_percent: float | None = None,
                           api_calls_count: int = 0,
                           data_processed_mb: float = 0.0,
                           quality_score: float | None = None,
                           metadata: dict | None = None):
        """Record aggregated task metrics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO task_metrics_summary 
            (task_id, total_duration_ms, actions_count, success_rate,
             avg_action_duration_ms, error_count, memory_peak_mb,
             cpu_avg_percent, api_calls_count, data_processed_mb,
             quality_score, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            total_duration_ms,
            actions_count,
            success_rate,
            avg_action_duration_ms,
            error_count,
            memory_peak_mb,
            cpu_avg_percent,
            api_calls_count,
            data_processed_mb,
            quality_score,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
    
    def get_metrics(self, task_id: str,
                   metric_name: str | None = None) -> list[PerformanceMetric]:
        """Get metrics for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM performance_metrics WHERE task_id = ?"
        params = [task_id]
        
        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)
        
        query += " ORDER BY timestamp ASC"
        
        cursor.execute(query, params)
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append(PerformanceMetric(
                id=row['id'],
                task_id=row['task_id'],
                metric_name=row['metric_name'],
                metric_value=row['metric_value'],
                unit=row['unit'],
                timestamp=row['timestamp'],
                context_json=row['context_json'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return metrics
    
    def get_task_metrics_summary(self, task_id: str) -> TaskMetrics | None:
        """Get aggregated task metrics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM task_metrics_summary WHERE task_id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return TaskMetrics(
            task_id=row['task_id'],
            total_duration_ms=row['total_duration_ms'],
            actions_count=row['actions_count'],
            success_rate=row['success_rate'],
            avg_action_duration_ms=row['avg_action_duration_ms'],
            error_count=row['error_count'],
            memory_peak_mb=row['memory_peak_mb'],
            cpu_avg_percent=row['cpu_avg_percent'],
            api_calls_count=row['api_calls_count'],
            data_processed_mb=row['data_processed_mb'],
            quality_score=row['quality_score'],
            metadata_json=row['metadata_json']
        )
    
    def get_metric_statistics(self, metric_name: str,
                             hours: int = 24) -> dict[str, Any]:
        """Get statistics for a metric."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Calculate time threshold
        from datetime import timedelta
        threshold = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as count,
                AVG(metric_value) as avg_value,
                MIN(metric_value) as min_value,
                MAX(metric_value) as max_value,
                SUM(metric_value) as sum_value
            FROM performance_metrics
            WHERE metric_name = ? AND timestamp > ?
        """, (metric_name, threshold))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row or row['count'] == 0:
            return {}
        
        return {
            'count': row['count'],
            'avg_value': row['avg_value'],
            'min_value': row['min_value'],
            'max_value': row['max_value'],
            'sum_value': row['sum_value'],
            'std_dev': self._calculate_std_dev(metric_name, threshold)
        }
    
    def _calculate_std_dev(self, metric_name: str, threshold: str) -> float:
        """Calculate standard deviation for a metric."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT metric_value FROM performance_metrics
            WHERE metric_name = ? AND timestamp > ?
        """, (metric_name, threshold))
        
        values = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        return variance ** 0.5
    
    def get_trend(self, metric_name: str, hours: int = 24,
                  interval_minutes: int = 15) -> list[dict[str, Any]]:
        """Get metric trend over time."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        from datetime import timedelta
        threshold = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:%M', timestamp) as time_bucket,
                AVG(metric_value) as avg_value,
                COUNT(*) as count
            FROM performance_metrics
            WHERE metric_name = ? AND timestamp > ?
            GROUP BY time_bucket
            ORDER BY time_bucket ASC
        """, (metric_name, threshold))
        
        trend = []
        for row in cursor.fetchall():
            trend.append({
                'time': row['time_bucket'],
                'avg_value': row['avg_value'],
                'count': row['count']
            })
        
        conn.close()
        return trend
    
    def compare_tasks(self, task_ids: list[str]) -> dict[str, Any]:
        """Compare metrics across multiple tasks."""
        comparison = {
            'tasks': [],
            'best_by_metric': {}
        }
        
        for task_id in task_ids:
            summary = self.get_task_metrics_summary(task_id)
            if summary:
                comparison['tasks'].append(summary.to_dict())
        
        # Find best performers
        if comparison['tasks']:
            # Fastest
            fastest = min(comparison['tasks'], 
                         key=lambda x: x['total_duration_ms'])
            comparison['best_by_metric']['fastest'] = fastest['task_id']
            
            # Highest success rate
            best_success = max(comparison['tasks'],
                              key=lambda x: x['success_rate'])
            comparison['best_by_metric']['best_success_rate'] = best_success['task_id']
            
            # Highest quality
            if any(t['quality_score'] for t in comparison['tasks']):
                best_quality = max(comparison['tasks'],
                                  key=lambda x: x['quality_score'] or 0)
                comparison['best_by_metric']['best_quality'] = best_quality['task_id']
        
        return comparison
    
    def get_statistics(self) -> dict[str, Any]:
        """Get overall metrics statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total metrics recorded
        cursor.execute("SELECT COUNT(*) FROM performance_metrics")
        stats['total_metrics'] = cursor.fetchone()[0]
        
        # Unique metrics
        cursor.execute("SELECT COUNT(DISTINCT metric_name) FROM performance_metrics")
        stats['unique_metrics'] = cursor.fetchone()[0]
        
        # Total tasks with metrics
        cursor.execute("SELECT COUNT(DISTINCT task_id) FROM task_metrics_summary")
        stats['total_tasks_tracked'] = cursor.fetchone()[0]
        
        # Average success rate
        cursor.execute("SELECT AVG(success_rate) FROM task_metrics_summary")
        stats['avg_success_rate'] = cursor.fetchone()[0] or 0
        
        # Average duration
        cursor.execute("SELECT AVG(total_duration_ms) FROM task_metrics_summary")
        stats['avg_duration_ms'] = cursor.fetchone()[0] or 0
        
        conn.close()
        return stats