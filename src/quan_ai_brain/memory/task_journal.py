"""Task Journal - Detailed task execution journaling.

Provides:
- Granular action logging (every step)
- Task outcome tracking
- Execution timeline
- Task pattern analysis
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pathlib import Path


class ActionStatus(str, Enum):
    """Status of an action."""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'
    CANCELLED = 'cancelled'


class ActionType(str, Enum):
    """Type of action."""
    COMPUTE = 'compute'
    DATA_READ = 'data_read'
    DATA_WRITE = 'data_write'
    API_CALL = 'api_call'
    DECISION = 'decision'
    VALIDATION = 'validation'
    TRANSFORMATION = 'transformation'
    NOTIFICATION = 'notification'
    OTHER = 'other'


@dataclass
class TaskAction:
    """Single action in task execution."""
    id: str
    task_id: str
    action_number: int
    action_type: ActionType
    name: str
    description: str
    status: ActionStatus
    started_at: str | None = None
    completed_at: str | None = None
    input_data: str | None = None  # JSON
    output_data: str | None = None  # JSON
    error_message: str | None = None
    duration_ms: int | None = None
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TaskAction':
        return cls(**data)


@dataclass
class TaskJournal:
    """Complete task journal."""
    task_id: str
    title: str
    description: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    status: str = 'pending'  # pending, running, completed, failed, cancelled
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    total_duration_ms: int = 0
    result: str | None = None
    error_message: str | None = None
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TaskJournal':
        return cls(**data)


class TaskJournalManager:
    """Manage task execution journals."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize task journal tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Task journals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_journals (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                status TEXT NOT NULL,
                total_actions INTEGER NOT NULL DEFAULT 0,
                successful_actions INTEGER NOT NULL DEFAULT 0,
                failed_actions INTEGER NOT NULL DEFAULT 0,
                total_duration_ms INTEGER NOT NULL DEFAULT 0,
                result TEXT,
                error_message TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Task actions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_actions (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                action_number INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                input_data TEXT,
                output_data TEXT,
                error_message TEXT,
                duration_ms INTEGER,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (task_id) REFERENCES task_journals(task_id)
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_journals_status 
            ON task_journals(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_actions_task 
            ON task_actions(task_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_actions_type 
            ON task_actions(action_type)
        """)
        
        conn.commit()
        conn.close()
    
    def create_journal(self, task_id: str, title: str, description: str,
                      metadata: dict | None = None) -> TaskJournal:
        """Create a new task journal."""
        now = datetime.now(timezone.utc).isoformat()
        
        journal = TaskJournal(
            task_id=task_id,
            title=title,
            description=description,
            created_at=now,
            metadata_json=json.dumps(metadata or {})
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO task_journals 
            (task_id, title, description, created_at, status, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            journal.task_id,
            journal.title,
            journal.description,
            journal.created_at,
            journal.status,
            journal.metadata_json
        ))
        
        conn.commit()
        conn.close()
        
        return journal
    
    def start_task(self, task_id: str) -> TaskJournal:
        """Start a task."""
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE task_journals 
            SET status = 'running', started_at = ?
            WHERE task_id = ?
        """, (now, task_id))
        
        conn.commit()
        conn.close()
        
        return self.get_journal(task_id)
    
    def complete_task(self, task_id: str, result: str | None = None,
                     error_message: str | None = None):
        """Complete a task."""
        now = datetime.now(timezone.utc).isoformat()
        status = 'completed' if not error_message else 'failed'
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE task_journals 
            SET status = ?, completed_at = ?, result = ?, error_message = ?
            WHERE task_id = ?
        """, (status, now, result, error_message, task_id))
        
        conn.commit()
        conn.close()
    
    def add_action(self, task_id: str, action_type: ActionType, name: str,
                  description: str, input_data: dict | None = None,
                  metadata: dict | None = None) -> TaskAction:
        """Add an action to the task journal."""
        import uuid
        now = datetime.now(timezone.utc).isoformat()
        
        # Get next action number
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COALESCE(MAX(action_number), 0) + 1 
            FROM task_actions WHERE task_id = ?
        """, (task_id,))
        action_number = cursor.fetchone()[0]
        
        action_id = f"action_{task_id}_{action_number}"
        
        action = TaskAction(
            id=action_id,
            task_id=task_id,
            action_number=action_number,
            action_type=action_type,
            name=name,
            description=description,
            status=ActionStatus.PENDING,
            started_at=now,
            input_data=json.dumps(input_data or {}),
            metadata_json=json.dumps(metadata or {})
        )
        
        cursor.execute("""
            INSERT INTO task_actions 
            (id, task_id, action_number, action_type, name, description,
             status, started_at, input_data, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            action.id,
            action.task_id,
            action.action_number,
            action.action_type.value,
            action.name,
            action.description,
            action.status.value,
            action.started_at,
            action.input_data,
            action.metadata_json
        ))
        
        # Update journal action count
        cursor.execute("""
            UPDATE task_journals 
            SET total_actions = total_actions + 1
            WHERE task_id = ?
        """, (task_id,))
        
        conn.commit()
        conn.close()
        
        return action
    
    def complete_action(self, action_id: str, output_data: dict | None = None,
                       error_message: str | None = None):
        """Mark an action as completed."""
        now = datetime.now(timezone.utc).isoformat()
        status = ActionStatus.COMPLETED if not error_message else ActionStatus.FAILED
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get action
        cursor.execute("""
            SELECT * FROM task_actions WHERE id = ?
        """, (action_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Action {action_id} not found")
        
        # Calculate duration
        started_at = datetime.fromisoformat(row['started_at'])
        completed_at = datetime.fromisoformat(now)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        # Update action
        cursor.execute("""
            UPDATE task_actions 
            SET status = ?, completed_at = ?, output_data = ?, 
                error_message = ?, duration_ms = ?
            WHERE id = ?
        """, (
            status.value,
            now,
            json.dumps(output_data or {}),
            error_message,
            duration_ms,
            action_id
        ))
        
        # Update journal stats
        self._update_journal_stats(cursor, row['task_id'])
        
        conn.commit()
        conn.close()
    
    def _update_journal_stats(self, cursor, task_id: str):
        """Update journal statistics."""
        # Count actions by status
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(COALESCE(duration_ms, 0)) as total_duration
            FROM task_actions WHERE task_id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        
        cursor.execute("""
            UPDATE task_journals 
            SET total_actions = ?, successful_actions = ?, 
                failed_actions = ?, total_duration_ms = ?
            WHERE task_id = ?
        """, (
            row['total'] or 0,
            row['successful'] or 0,
            row['failed'] or 0,
            row['total_duration'] or 0,
            task_id
        ))
    
    def get_journal(self, task_id: str) -> TaskJournal | None:
        """Get task journal."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM task_journals WHERE task_id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return TaskJournal(
            task_id=row['task_id'],
            title=row['title'],
            description=row['description'],
            created_at=row['created_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            status=row['status'],
            total_actions=row['total_actions'],
            successful_actions=row['successful_actions'],
            failed_actions=row['failed_actions'],
            total_duration_ms=row['total_duration_ms'],
            result=row['result'],
            error_message=row['error_message'],
            metadata_json=row['metadata_json']
        )
    
    def get_actions(self, task_id: str) -> list[TaskAction]:
        """Get all actions for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM task_actions 
            WHERE task_id = ?
            ORDER BY action_number
        """, (task_id,))
        
        actions = []
        for row in cursor.fetchall():
            actions.append(TaskAction(
                id=row['id'],
                task_id=row['task_id'],
                action_number=row['action_number'],
                action_type=ActionType(row['action_type']),
                name=row['name'],
                description=row['description'],
                status=ActionStatus(row['status']),
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                input_data=row['input_data'],
                output_data=row['output_data'],
                error_message=row['error_message'],
                duration_ms=row['duration_ms'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return actions
    
    def get_timeline(self, task_id: str) -> list[dict[str, Any]]:
        """Get execution timeline."""
        actions = self.get_actions(task_id)
        
        timeline = []
        for action in actions:
            timeline.append({
                'action_number': action.action_number,
                'name': action.name,
                'type': action.action_type.value,
                'status': action.status.value,
                'started_at': action.started_at,
                'completed_at': action.completed_at,
                'duration_ms': action.duration_ms,
                'error': action.error_message
            })
        
        return timeline
    
    def search_journals(self, status: str | None = None,
                       limit: int = 50) -> list[TaskJournal]:
        """Search task journals."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM task_journals WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        journals = []
        for row in cursor.fetchall():
            journals.append(TaskJournal(
                task_id=row['task_id'],
                title=row['title'],
                description=row['description'],
                created_at=row['created_at'],
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                status=row['status'],
                total_actions=row['total_actions'],
                successful_actions=row['successful_actions'],
                failed_actions=row['failed_actions'],
                total_duration_ms=row['total_duration_ms'],
                result=row['result'],
                error_message=row['error_message'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return journals
    
    def get_statistics(self) -> dict[str, Any]:
        """Get journal statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*) FROM task_journals GROUP BY status
        """)
        stats['by_status'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total journals
        cursor.execute("SELECT COUNT(*) FROM task_journals")
        stats['total_journals'] = cursor.fetchone()[0]
        
        # Average duration
        cursor.execute("SELECT AVG(total_duration_ms) FROM task_journals")
        stats['avg_duration_ms'] = cursor.fetchone()[0] or 0
        
        # Success rate
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                COUNT(*) as total
            FROM task_journals
        """)
        row = cursor.fetchone()
        total = row['total'] or 1
        stats['success_rate'] = (row['completed'] / total) * 100
        
        conn.close()
        return stats