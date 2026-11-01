"""Workflow State - Persistent workflow state management.

Provides:
- Workflow state persistence
- Step-by-step progress tracking
- Workflow recovery and resume
- Workflow history
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pathlib import Path


class WorkflowStatus(str, Enum):
    """Workflow lifecycle status."""
    CREATED = 'created'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class StepStatus(str, Enum):
    """Individual step status."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'


@dataclass
class WorkflowStep:
    """Individual workflow step."""
    step_id: str
    workflow_id: str
    step_number: int
    name: str
    status: StepStatus
    started_at: str | None = None
    completed_at: str | None = None
    result: str | None = None
    error_message: str | None = None
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'WorkflowStep':
        return cls(**data)


@dataclass
class WorkflowState:
    """Complete workflow state."""
    workflow_id: str
    name: str
    status: WorkflowStatus
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    current_step: int = 0
    total_steps: int = 0
    progress_percentage: float = 0.0
    error_message: str | None = None
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'WorkflowState':
        return cls(**data)


class WorkflowStateManager:
    """Manage workflow state persistence."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize workflow tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                current_step INTEGER NOT NULL DEFAULT 0,
                total_steps INTEGER NOT NULL DEFAULT 0,
                progress_percentage REAL NOT NULL DEFAULT 0.0,
                error_message TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Workflow steps table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_steps (
                step_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                error_message TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
            )
        """)
        
        # Workflow state snapshots (for history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                snapshot_at TEXT NOT NULL,
                status TEXT NOT NULL,
                current_step INTEGER NOT NULL,
                total_steps INTEGER NOT NULL,
                progress_percentage REAL NOT NULL,
                state_json TEXT NOT NULL,
                FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflows_status 
            ON workflows(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_steps_workflow 
            ON workflow_steps(workflow_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_workflow 
            ON workflow_snapshots(workflow_id)
        """)
        
        conn.commit()
        conn.close()
    
    def create_workflow(self, name: str, total_steps: int,
                       metadata: dict | None = None) -> WorkflowState:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        state = WorkflowState(
            workflow_id=workflow_id,
            name=name,
            status=WorkflowStatus.CREATED,
            created_at=now,
            updated_at=now,
            total_steps=total_steps,
            metadata_json=json.dumps(metadata or {})
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO workflows 
            (workflow_id, name, status, created_at, updated_at, 
             total_steps, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            state.workflow_id,
            state.name,
            state.status.value,
            state.created_at,
            state.updated_at,
            state.total_steps,
            state.metadata_json
        ))
        
        # Create initial steps
        for i in range(1, total_steps + 1):
            step = WorkflowStep(
                step_id=f"step_{workflow_id}_{i}",
                workflow_id=workflow_id,
                step_number=i,
                name=f"Step {i}",
                status=StepStatus.PENDING
            )
            
            cursor.execute("""
                INSERT INTO workflow_steps 
                (step_id, workflow_id, step_number, name, status, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                step.step_id,
                step.workflow_id,
                step.step_number,
                step.name,
                step.status.value,
                step.metadata_json
            ))
        
        conn.commit()
        conn.close()
        
        return state
    
    def start_workflow(self, workflow_id: str) -> WorkflowState:
        """Start a workflow."""
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE workflows 
            SET status = ?, started_at = ?, updated_at = ?
            WHERE workflow_id = ?
        """, (WorkflowStatus.RUNNING.value, now, now, workflow_id))
        
        conn.commit()
        conn.close()
        
        return self.get_workflow_state(workflow_id)
    
    def update_step(self, workflow_id: str, step_number: int,
                   status: StepStatus, result: str | None = None,
                   error_message: str | None = None,
                   metadata: dict | None = None) -> WorkflowStep:
        """Update a workflow step."""
        now = datetime.now(timezone.utc).isoformat()
        step_id = f"step_{workflow_id}_{step_number}"
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get current step
        cursor.execute("""
            SELECT * FROM workflow_steps WHERE step_id = ?
        """, (step_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Step {step_number} not found in workflow {workflow_id}")
        
        # Update step
        started_at = row['started_at']
        completed_at = row['completed_at']
        
        if status == StepStatus.RUNNING and not started_at:
            started_at = now
        elif status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED]:
            completed_at = now
        
        cursor.execute("""
            UPDATE workflow_steps 
            SET status = ?, started_at = ?, completed_at = ?,
                result = ?, error_message = ?, metadata_json = ?
            WHERE step_id = ?
        """, (
            status.value,
            started_at,
            completed_at,
            result,
            error_message,
            json.dumps(metadata or {}),
            step_id
        ))
        
        # Update workflow progress
        self._update_workflow_progress(cursor, workflow_id)
        
        conn.commit()
        conn.close()
        
        return WorkflowStep(
            step_id=step_id,
            workflow_id=workflow_id,
            step_number=step_number,
            name=row['name'],
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            result=result,
            error_message=error_message,
            metadata_json=json.dumps(metadata or {})
        )
    
    def _update_workflow_progress(self, cursor, workflow_id: str):
        """Update workflow progress based on step statuses."""
        # Count completed steps
        cursor.execute("""
            SELECT COUNT(*) FROM workflow_steps 
            WHERE workflow_id = ? AND status = 'completed'
        """, (workflow_id,))
        completed = cursor.fetchone()[0]
        
        # Get total steps
        cursor.execute("""
            SELECT total_steps FROM workflows WHERE workflow_id = ?
        """, (workflow_id,))
        total = cursor.fetchone()[0]
        
        # Calculate progress
        progress = (completed / total * 100) if total > 0 else 0
        
        # Update current step
        cursor.execute("""
            SELECT MAX(step_number) FROM workflow_steps 
            WHERE workflow_id = ? AND status IN ('running', 'completed')
        """, (workflow_id,))
        current = cursor.fetchone()[0] or 0
        
        # Determine workflow status
        cursor.execute("""
            SELECT status, completed_at FROM workflows WHERE workflow_id = ?
        """, (workflow_id,))
        row = cursor.fetchone()
        current_status = row['status']
        completed_at = row['completed_at']
        
        now = datetime.now(timezone.utc).isoformat()
        new_status = current_status
        new_completed_at = completed_at
        
        if completed == total and not completed_at:
            new_status = WorkflowStatus.COMPLETED.value
            new_completed_at = now
        elif current_status == WorkflowStatus.RUNNING.value:
            new_status = WorkflowStatus.RUNNING.value
        
        cursor.execute("""
            UPDATE workflows 
            SET current_step = ?, progress_percentage = ?, 
                status = ?, completed_at = ?, updated_at = ?
            WHERE workflow_id = ?
        """, (current, progress, new_status, new_completed_at, now, workflow_id))
    
    def get_workflow_state(self, workflow_id: str) -> WorkflowState | None:
        """Get current workflow state."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT workflow_id, name, status, created_at, updated_at,
                   started_at, completed_at, current_step, total_steps,
                   progress_percentage, error_message, metadata_json
            FROM workflows
            WHERE workflow_id = ?
        """, (workflow_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return WorkflowState(
            workflow_id=row['workflow_id'],
            name=row['name'],
            status=WorkflowStatus(row['status']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            current_step=row['current_step'],
            total_steps=row['total_steps'],
            progress_percentage=row['progress_percentage'],
            error_message=row['error_message'],
            metadata_json=row['metadata_json']
        )
    
    def get_workflow_steps(self, workflow_id: str) -> list[WorkflowStep]:
        """Get all steps for a workflow."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT step_id, workflow_id, step_number, name, status,
                   started_at, completed_at, result, error_message, metadata_json
            FROM workflow_steps
            WHERE workflow_id = ?
            ORDER BY step_number
        """, (workflow_id,))
        
        steps = []
        for row in cursor.fetchall():
            steps.append(WorkflowStep(
                step_id=row['step_id'],
                workflow_id=row['workflow_id'],
                step_number=row['step_number'],
                name=row['name'],
                status=StepStatus(row['status']),
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                result=row['result'],
                error_message=row['error_message'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return steps
    
    def create_snapshot(self, workflow_id: str) -> str:
        """Create a state snapshot for recovery."""
        snapshot_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        workflow = self.get_workflow_state(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        steps = self.get_workflow_steps(workflow_id)
        
        state_json = json.dumps({
            'workflow': workflow.to_dict(),
            'steps': [s.to_dict() for s in steps]
        })
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO workflow_snapshots 
            (snapshot_id, workflow_id, snapshot_at, status, current_step,
             total_steps, progress_percentage, state_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id,
            workflow_id,
            now,
            workflow.status.value,
            workflow.current_step,
            workflow.total_steps,
            workflow.progress_percentage,
            state_json
        ))
        
        conn.commit()
        conn.close()
        
        return snapshot_id
    
    def restore_from_snapshot(self, workflow_id: str, 
                             snapshot_id: str) -> WorkflowState:
        """Restore workflow from a snapshot."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT state_json FROM workflow_snapshots
            WHERE snapshot_id = ? AND workflow_id = ?
        """, (snapshot_id, workflow_id))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError("Snapshot not found")
        
        state_data = json.loads(row['state_json'])
        
        # Restore workflow
        workflow_data = state_data['workflow']
        cursor.execute("""
            UPDATE workflows 
            SET status = ?, current_step = ?, total_steps = ?,
                progress_percentage = ?, updated_at = ?
            WHERE workflow_id = ?
        """, (
            workflow_data['status'],
            workflow_data['current_step'],
            workflow_data['total_steps'],
            workflow_data['progress_percentage'],
            datetime.now(timezone.utc).isoformat(),
            workflow_id
        ))
        
        # Restore steps
        for step_data in state_data['steps']:
            cursor.execute("""
                UPDATE workflow_steps 
                SET status = ?, started_at = ?, completed_at = ?,
                    result = ?, error_message = ?, metadata_json = ?
                WHERE step_id = ?
            """, (
                step_data['status'],
                step_data['started_at'],
                step_data['completed_at'],
                step_data['result'],
                step_data['error_message'],
                step_data['metadata_json'],
                step_data['step_id']
            ))
        
        conn.commit()
        conn.close()
        
        return self.get_workflow_state(workflow_id)
    
    def get_snapshots(self, workflow_id: str) -> list[dict[str, Any]]:
        """Get all snapshots for a workflow."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT snapshot_id, workflow_id, snapshot_at, status,
                   current_step, total_steps, progress_percentage
            FROM workflow_snapshots
            WHERE workflow_id = ?
            ORDER BY snapshot_at DESC
        """, (workflow_id,))
        
        snapshots = []
        for row in cursor.fetchall():
            snapshots.append({
                'snapshot_id': row['snapshot_id'],
                'snapshot_at': row['snapshot_at'],
                'status': row['status'],
                'current_step': row['current_step'],
                'total_steps': row['total_steps'],
                'progress_percentage': row['progress_percentage']
            })
        
        conn.close()
        return snapshots
    
    def get_statistics(self) -> dict[str, Any]:
        """Get workflow statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Count by status
        for status in WorkflowStatus:
            cursor.execute("""
                SELECT COUNT(*) FROM workflows WHERE status = ?
            """, (status.value,))
            stats[f'{status.value}_count'] = cursor.fetchone()[0]
        
        # Total workflows
        cursor.execute("SELECT COUNT(*) FROM workflows")
        stats['total_workflows'] = cursor.fetchone()[0]
        
        # Average progress
        cursor.execute("SELECT AVG(progress_percentage) FROM workflows")
        stats['avg_progress'] = cursor.fetchone()[0] or 0
        
        conn.close()
        return stats