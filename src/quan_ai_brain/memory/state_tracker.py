"""State Tracker - Real-time state tracking for tasks and workflows.

Provides:
- Task state machine (pending → running → completed/failed)
- State transition validation
- State history logging
- State recovery
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pathlib import Path


class TaskState(str, Enum):
    """Task lifecycle states."""
    PENDING = 'pending'
    QUEUED = 'queued'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    RETRYING = 'retrying'


class StateTransition(str, Enum):
    """Valid state transitions."""
    PENDING_TO_QUEUED = 'pending_to_queued'
    PENDING_TO_RUNNING = 'pending_to_running'
    QUEUED_TO_RUNNING = 'queued_to_running'
    QUEUED_TO_CANCELLED = 'queued_to_cancelled'
    RUNNING_TO_PAUSED = 'running_to_paused'
    RUNNING_TO_COMPLETED = 'running_to_completed'
    RUNNING_TO_FAILED = 'running_to_failed'
    PAUSED_TO_RUNNING = 'paused_to_running'
    PAUSED_TO_CANCELLED = 'paused_to_cancelled'
    FAILED_TO_RETRYING = 'failed_to_retrying'
    RETRYING_TO_RUNNING = 'retrying_to_running'
    ANY_TO_CANCELLED = 'any_to_cancelled'


# Define valid transitions
VALID_TRANSITIONS = {
    TaskState.PENDING: [TaskState.QUEUED, TaskState.RUNNING, TaskState.CANCELLED],
    TaskState.QUEUED: [TaskState.RUNNING, TaskState.CANCELLED],
    TaskState.RUNNING: [TaskState.PAUSED, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED],
    TaskState.PAUSED: [TaskState.RUNNING, TaskState.CANCELLED],
    TaskState.COMPLETED: [],  # Terminal state
    TaskState.FAILED: [TaskState.RETRYING, TaskState.CANCELLED],
    TaskState.CANCELLED: [],  # Terminal state
    TaskState.RETRYING: [TaskState.RUNNING, TaskState.FAILED],
}


@dataclass
class StateTransitionRecord:
    """Record of a state transition."""
    id: str
    task_id: str
    from_state: TaskState
    to_state: TaskState
    transitioned_at: str
    transitioned_by: str
    reason: str
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'StateTransitionRecord':
        return cls(**data)


@dataclass
class TaskStateInfo:
    """Complete task state information."""
    task_id: str
    current_state: TaskState
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    retry_count: int = 0
    error_message: str | None = None
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TaskStateInfo':
        return cls(**data)


class StateTracker:
    """Track and manage task states."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize state tracking tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Task states table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_states (
                task_id TEXT PRIMARY KEY,
                current_state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # State transition history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_transitions (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT NOT NULL,
                transitioned_at TEXT NOT NULL,
                transitioned_by TEXT NOT NULL,
                reason TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (task_id) REFERENCES task_states(task_id)
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_state 
            ON task_states(current_state)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transitions_task 
            ON state_transitions(task_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transitions_time 
            ON state_transitions(transitioned_at)
        """)
        
        conn.commit()
        conn.close()
    
    def create_task(self, task_id: str, metadata: dict | None = None,
                   creator: str = "system") -> TaskStateInfo:
        """Create a new task in PENDING state."""
        now = datetime.now(timezone.utc).isoformat()
        
        state_info = TaskStateInfo(
            task_id=task_id,
            current_state=TaskState.PENDING,
            created_at=now,
            updated_at=now,
            metadata_json=json.dumps(metadata or {})
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO task_states 
            (task_id, current_state, created_at, updated_at, metadata_json)
            VALUES (?, ?, ?, ?, ?)
        """, (
            state_info.task_id,
            state_info.current_state.value,
            state_info.created_at,
            state_info.updated_at,
            state_info.metadata_json
        ))
        
        # Record initial transition
        self._record_transition(
            cursor, task_id, None, TaskState.PENDING,
            creator, "Task created", {}
        )
        
        conn.commit()
        conn.close()
        
        return state_info
    
    def transition_state(self, task_id: str, new_state: TaskState,
                        transitioned_by: str = "system",
                        reason: str = "",
                        metadata: dict | None = None) -> TaskStateInfo:
        """Transition task to a new state."""
        # Get current state
        current = self.get_task_state(task_id)
        if not current:
            raise ValueError(f"Task {task_id} not found")
        
        # Validate transition
        if new_state not in VALID_TRANSITIONS.get(current.current_state, []):
            raise ValueError(
                f"Invalid transition from {current.current_state} to {new_state}"
            )
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Update task state
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Set timestamps based on state
        started_at = current.started_at
        completed_at = current.completed_at
        
        if new_state == TaskState.RUNNING and not started_at:
            started_at = now
        elif new_state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
            completed_at = now
        
        # Update retry count if retrying
        retry_count = current.retry_count
        if new_state == TaskState.RETRYING:
            retry_count += 1
        
        cursor.execute("""
            UPDATE task_states 
            SET current_state = ?, updated_at = ?, started_at = ?, 
                completed_at = ?, retry_count = ?, error_message = ?
            WHERE task_id = ?
        """, (
            new_state.value,
            now,
            started_at,
            completed_at,
            retry_count,
            None if new_state == TaskState.RUNNING else current.error_message,
            task_id
        ))
        
        # Record transition
        self._record_transition(
            cursor, task_id, current.current_state, new_state,
            transitioned_by, reason, metadata or {}
        )
        
        conn.commit()
        conn.close()
        
        # Return updated state
        return self.get_task_state(task_id)
    
    def get_task_state(self, task_id: str) -> TaskStateInfo | None:
        """Get current state of a task."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_id, current_state, created_at, updated_at,
                   started_at, completed_at, retry_count, error_message, metadata_json
            FROM task_states
            WHERE task_id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return TaskStateInfo(
            task_id=row['task_id'],
            current_state=TaskState(row['current_state']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            retry_count=row['retry_count'],
            error_message=row['error_message'],
            metadata_json=row['metadata_json']
        )
    
    def get_state_history(self, task_id: str, 
                         limit: int = 100) -> list[StateTransitionRecord]:
        """Get state transition history for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, task_id, from_state, to_state, transitioned_at,
                   transitioned_by, reason, metadata_json
            FROM state_transitions
            WHERE task_id = ?
            ORDER BY transitioned_at DESC
            LIMIT ?
        """, (task_id, limit))
        
        records = []
        for row in cursor.fetchall():
            from_state = TaskState(row['from_state']) if row['from_state'] else None
            records.append(StateTransitionRecord(
                id=row['id'],
                task_id=row['task_id'],
                from_state=from_state,
                to_state=TaskState(row['to_state']),
                transitioned_at=row['transitioned_at'],
                transitioned_by=row['transitioned_by'],
                reason=row['reason'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return list(reversed(records))
    
    def set_error(self, task_id: str, error_message: str,
                  by: str = "system"):
        """Set error message for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            UPDATE task_states 
            SET error_message = ?, updated_at = ?
            WHERE task_id = ?
        """, (error_message, now, task_id))
        
        conn.commit()
        conn.close()
    
    def cancel_task(self, task_id: str, reason: str = "",
                   by: str = "system") -> TaskStateInfo:
        """Cancel a task from any state."""
        current = self.get_task_state(task_id)
        if not current:
            raise ValueError(f"Task {task_id} not found")
        
        return self.transition_state(
            task_id, TaskState.CANCELLED, by, reason
        )
    
    def retry_task(self, task_id: str, by: str = "system") -> TaskStateInfo:
        """Retry a failed task."""
        return self.transition_state(
            task_id, TaskState.RETRYING, by, "Retrying failed task"
        )
    
    def _record_transition(self, cursor, task_id: str,
                          from_state: TaskState | None,
                          to_state: TaskState,
                          by: str, reason: str, metadata: dict):
            """Record a state transition in history."""
            import uuid
            now = datetime.now(timezone.utc).isoformat()
            transition_id = f"trans_{uuid.uuid4().hex[:12]}"
        
            cursor.execute(
                "INSERT INTO state_transitions "
                "(id, task_id, from_state, to_state, transitioned_at, "
                "transitioned_by, reason, metadata_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (transition_id, task_id,
                 from_state.value if from_state else None,
                 to_state.value, now, by, reason, json.dumps(metadata))
            )
    
    def get_tasks_by_state(self, state: TaskState) -> list[TaskStateInfo]:
        """Get all tasks in a specific state."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_id, current_state, created_at, updated_at,
                   started_at, completed_at, retry_count, error_message, metadata_json
            FROM task_states
            WHERE current_state = ?
            ORDER BY updated_at DESC
        """, (state.value,))
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append(TaskStateInfo(
                task_id=row['task_id'],
                current_state=TaskState(row['current_state']),
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                retry_count=row['retry_count'],
                error_message=row['error_message'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return tasks
    
    def get_statistics(self) -> dict[str, Any]:
        """Get state tracking statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Count by state
        for state in TaskState:
            cursor.execute("""
                SELECT COUNT(*) FROM task_states WHERE current_state = ?
            """, (state.value,))
            stats[f'{state.value}_count'] = cursor.fetchone()[0]
        
        # Total tasks
        cursor.execute("SELECT COUNT(*) FROM task_states")
        stats['total_tasks'] = cursor.fetchone()[0]
        
        # Total transitions
        cursor.execute("SELECT COUNT(*) FROM state_transitions")
        stats['total_transitions'] = cursor.fetchone()[0]
        
        # Failed tasks with errors
        cursor.execute("""
            SELECT COUNT(*) FROM task_states 
            WHERE current_state = 'failed' AND error_message IS NOT NULL
        """)
        stats['failed_with_errors'] = cursor.fetchone()[0]
        
        conn.close()
        return stats