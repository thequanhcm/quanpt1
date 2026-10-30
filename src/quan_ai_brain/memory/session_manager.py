"""Session Manager - Lifecycle management for conversation sessions.

Provides:
- Session creation and lifecycle
- Session state transitions
- Session cleanup and archiving
- Session recovery
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .context_store import ContextStore, ContextEntry, SessionContext


class SessionStatus(str, Enum):
    """Session lifecycle status."""
    CREATED = 'created'
    ACTIVE = 'active'
    PAUSED = 'paused'
    ARCHIVED = 'archived'
    CLOSED = 'closed'
    ERROR = 'error'


@dataclass
class SessionState:
    """Complete session state with all metadata."""
    session_id: str
    status: SessionStatus
    created_at: str
    updated_at: str
    last_activity_at: str
    title: str
    context_summary: str | None = None
    user_id: str | None = None
    metadata_json: str = field(default_factory=lambda: '{}')
    error_message: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SessionState':
        return cls(**data)


class SessionManager:
    """Manages conversation session lifecycle."""
    
    def __init__(self, context_store: ContextStore | None = None):
        self.context_store = context_store or ContextStore()
        self._active_sessions: dict[str, SessionState] = {}
    
    def create_session(self, title: str = "New Session", 
                      user_id: str | None = None,
                      metadata: dict | None = None) -> SessionState:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Merge user_id into metadata
        merged_metadata = metadata or {}
        if user_id:
            merged_metadata['user_id'] = user_id
        
        state = SessionState(
            session_id=session_id,
            status=SessionStatus.CREATED,
            created_at=now,
            updated_at=now,
            last_activity_at=now,
            title=title,
            user_id=user_id,
            metadata_json=json.dumps(merged_metadata)
        )
        
        # Initialize in context store
        self.context_store.create_session(
            session_id=session_id,
            title=title,
            metadata=merged_metadata
        )
        
        # Transition to active
        state = self._transition_state(state, SessionStatus.ACTIVE)
        self._active_sessions[session_id] = state
        
        return state
    
    def get_session(self, session_id: str) -> SessionState | None:
        """Get session state by ID."""
        # Check cache first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]
        
        # Fetch from database
        context = self.context_store.get_session(session_id)
        if not context:
            return None
        
        # Parse user_id from metadata
        metadata = json.loads(context.metadata_json)
        session_user_id = metadata.get('user_id')
        
        state = SessionState(
            session_id=context.session_id,
            status=SessionStatus(context.status),
            created_at=context.created_at,
            updated_at=context.updated_at,
            last_activity_at=context.updated_at,
            title=context.title,
            context_summary=context.summary,
            user_id=session_user_id,
            metadata_json=context.metadata_json
        )
        
        self._active_sessions[session_id] = state
        return state
    
    def add_message(self, session_id: str, role: str, content: str,
                   metadata: dict | None = None) -> ContextEntry:
        """Add a message to the session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != SessionStatus.ACTIVE:
            raise ValueError(f"Cannot add message to session in {session.status} status")
        
        # Add to context store
        entry = self.context_store.add_context(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata
        )
        
        # Update session state
        now = datetime.now(timezone.utc).isoformat()
        session.last_activity_at = now
        session.updated_at = now
        self._active_sessions[session_id] = session
        
        return entry
    
    def get_context_window(self, session_id: str, last_n: int = 10) -> list[ContextEntry]:
        """Get the last N turns of context."""
        return self.context_store.get_context_window(session_id, last_n)
    
    def pause_session(self, session_id: str, reason: str = "") -> SessionState:
        """Pause a session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != SessionStatus.ACTIVE:
            raise ValueError(f"Cannot pause session in {session.status} status")
        
        state = self._transition_state(session, SessionStatus.PAUSED, reason)
        self._active_sessions[session_id] = state
        
        return state
    
    def resume_session(self, session_id: str) -> SessionState:
        """Resume a paused session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != SessionStatus.PAUSED:
            raise ValueError(f"Cannot resume session in {session.status} status")
        
        state = self._transition_state(session, SessionStatus.ACTIVE)
        self._active_sessions[session_id] = state
        
        return state
    
    def archive_session(self, session_id: str, summary: str = "") -> SessionState:
        """Archive a session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status not in [SessionStatus.ACTIVE, SessionStatus.PAUSED]:
            raise ValueError(f"Cannot archive session in {session.status} status")
        
        # Update context summary if provided
        if summary:
            self.context_store.update_session_summary(session_id, summary)
            session.context_summary = summary
        
        state = self._transition_state(session, SessionStatus.ARCHIVED)
        
        # Remove from active cache
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
        
        # Archive in context store
        self.context_store.archive_session(session_id)
        
        # Update local state
        self._active_sessions[session_id] = state
        
        return state
    
    def close_session(self, session_id: str, reason: str = "") -> SessionState:
        """Close a session permanently."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status == SessionStatus.CLOSED:
            return session
        
        state = self._transition_state(session, SessionStatus.CLOSED, reason)
        
        # Remove from active cache
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
        
        return state
    
    def delete_session(self, session_id: str):
        """Delete a session and all its data."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Remove from cache
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
        
        # Delete from context store
        self.context_store.delete_session(session_id)
    
    def _transition_state(self, session: SessionState, 
                         new_status: SessionStatus,
                         reason: str = "") -> SessionState:
        """Transition session to new state."""
        now = datetime.now(timezone.utc).isoformat()
        
        session.status = new_status
        session.updated_at = now
        if reason:
            metadata = json.loads(session.metadata_json)
            metadata['last_transition_reason'] = reason
            session.metadata_json = json.dumps(metadata)
        
        return session
    
    def list_active_sessions(self, user_id: str | None = None) -> list[SessionState]:
        """List all active sessions, optionally filtered by user."""
        contexts = self.context_store.list_sessions(status='active')
        
        states = []
        for context in contexts:
            # Parse user_id from metadata
            metadata = json.loads(context.metadata_json)
            session_user_id = metadata.get('user_id')
            
            state = SessionState(
                session_id=context.session_id,
                status=SessionStatus(context.status),
                created_at=context.created_at,
                updated_at=context.updated_at,
                last_activity_at=context.updated_at,
                title=context.title,
                context_summary=context.summary,
                user_id=session_user_id,
                metadata_json=context.metadata_json
            )
            
            if user_id and state.user_id != user_id:
                continue
            
            states.append(state)
            self._active_sessions[context.session_id] = state
        
        return states
    
    def get_session_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get full conversation history for a session."""
        entries = self.context_store.get_context_window(session_id, last_n=9999)
        return [entry.to_dict() for entry in entries]
    
    def get_statistics(self) -> dict[str, Any]:
        """Get session statistics."""
        stats = self.context_store.get_statistics()
        
        # Add session manager specific stats
        stats['active_in_memory'] = len(self._active_sessions)
        
        return stats