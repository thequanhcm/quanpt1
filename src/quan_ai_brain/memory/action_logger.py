"""Action Logger - Step-by-step action tracking.

Provides:
- Fine-grained action logging
- Input/output capture
- Error tracking
- Action pattern analysis
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from pathlib import Path
from contextlib import contextmanager

from .task_journal import TaskJournalManager, TaskAction, ActionStatus, ActionType


@dataclass
class LoggedAction:
    """Logged action with timing."""
    id: str
    task_id: str
    action_type: ActionType
    name: str
    status: ActionStatus
    start_time: float
    end_time: float | None = None
    duration_ms: int = 0
    input_snapshot: str | None = None
    output_snapshot: str | None = None
    error_details: str | None = None
    call_stack: str | None = None
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'LoggedAction':
        return cls(**data)


class ActionLogger:
    """Log actions with detailed tracking."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self.journal_manager = TaskJournalManager(db_path)
        self._active_actions: dict[str, dict] = {}
    
    def log_action(self, task_id: str, action_type: ActionType, name: str,
                  description: str = "", input_data: dict | None = None,
                  metadata: dict | None = None) -> str:
        """Log the start of an action. Returns action ID."""
        action = self.journal_manager.add_action(
            task_id=task_id,
            action_type=action_type,
            name=name,
            description=description,
            input_data=input_data,
            metadata=metadata
        )
        
        # Track active action
        self._active_actions[action.id] = {
            'start_time': time.time(),
            'task_id': task_id
        }
        
        return action.id
    
    def complete_action(self, action_id: str, output_data: dict | None = None,
                       error_message: str | None = None):
        """Mark action as completed."""
        if action_id in self._active_actions:
            end_time = time.time()
            duration_ms = int((end_time - self._active_actions[action_id]['start_time']) * 1000)
            del self._active_actions[action_id]
        
        self.journal_manager.complete_action(
            action_id=action_id,
            output_data=output_data,
            error_message=error_message
        )
    
    @contextmanager
    def track_action(self, task_id: str, action_type: ActionType, name: str,
                    description: str = "", input_data: dict | None = None,
                    metadata: dict | None = None):
        """Context manager for tracking action execution."""
        action_id = self.log_action(
            task_id=task_id,
            action_type=action_type,
            name=name,
            description=description,
            input_data=input_data,
            metadata=metadata
        )
        
        try:
            yield action_id
            # If no exception, action will be completed after
            self.complete_action(action_id, output_data={'success': True})
        except Exception as e:
            self.complete_action(
                action_id,
                error_message=str(e)
            )
            raise
    
    def log_function_call(self, task_id: str, func: Callable,
                         action_type: ActionType, name: str,
                         *args, **kwargs) -> Any:
        """Log a function call with all details."""
        # Capture input
        input_data = {
            'args': str(args),
            'kwargs': str(kwargs)
        }
        
        with self.track_action(task_id, action_type, name,
                              f"Executing {name}", input_data) as action_id:
            try:
                result = func(*args, **kwargs)
                
                # Capture output
                output_data = {'result': str(result)}
                self.complete_action(action_id, output_data=output_data)
                
                return result
            except Exception as e:
                self.complete_action(
                    action_id,
                    error_message=f"{type(e).__name__}: {str(e)}"
                )
                raise
    
    def get_action_details(self, action_id: str) -> TaskAction | None:
        """Get detailed action information."""
        # This would require querying the database
        # For now, return None as placeholder
        return None
    
    def get_action_history(self, task_id: str,
                          action_type: ActionType | None = None) -> list[TaskAction]:
        """Get action history for a task."""
        actions = self.journal_manager.get_actions(task_id)
        
        if action_type:
            actions = [a for a in actions if a.action_type == action_type]
        
        return actions
    
    def analyze_action_patterns(self, task_id: str) -> dict[str, Any]:
        """Analyze patterns in task actions."""
        actions = self.journal_manager.get_actions(task_id)
        
        if not actions:
            return {}
        
        patterns = {
            'total_actions': len(actions),
            'by_type': {},
            'by_status': {},
            'avg_duration_ms': 0,
            'total_duration_ms': 0,
            'error_rate': 0.0
        }
        
        durations = []
        for action in actions:
            # Count by type
            type_key = action.action_type.value
            patterns['by_type'][type_key] = patterns['by_type'].get(type_key, 0) + 1
            
            # Count by status
            status_key = action.status.value
            patterns['by_status'][status_key] = patterns['by_status'].get(status_key, 0) + 1
            
            # Track durations
            if action.duration_ms:
                durations.append(action.duration_ms)
                patterns['total_duration_ms'] += action.duration_ms
        
        if durations:
            patterns['avg_duration_ms'] = sum(durations) / len(durations)
        
        failed = patterns['by_status'].get('failed', 0)
        patterns['error_rate'] = (failed / len(actions)) * 100 if actions else 0
        
        return patterns