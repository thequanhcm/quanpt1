"""Context Store - Persistent context management for multi-turn conversations.

Provides:
- Session-based context storage
- Context window management
- Automatic summarization
- Context retrieval with relevance scoring
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from pathlib import Path


@dataclass
class ContextEntry:
    """Single context entry within a session."""
    id: str
    session_id: str
    turn_number: int
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: str
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ContextEntry':
        return cls(**data)


@dataclass
class SessionContext:
    """Complete session context with metadata."""
    session_id: str
    created_at: str
    updated_at: str
    title: str
    status: str  # 'active', 'archived', 'summarized'
    turn_count: int
    summary: str | None = None
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SessionContext':
        return cls(**data)


class ContextStore:
    """Persistent context storage with window management."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize context tables if not exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Context sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                turn_count INTEGER NOT NULL DEFAULT 0,
                summary TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Context entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_entries (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES context_sessions(session_id)
            )
        """)
        
        # Index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_context_session_turn 
            ON context_entries(session_id, turn_number)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_context_session_status 
            ON context_sessions(status)
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_id: str, title: str = "Untitled", 
                      metadata: dict | None = None) -> SessionContext:
        """Create a new context session."""
        now = datetime.now(timezone.utc).isoformat()
        
        context = SessionContext(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            title=title,
            status='active',
            turn_count=0,
            metadata_json=json.dumps(metadata or {})
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO context_sessions 
            (session_id, created_at, updated_at, title, status, turn_count, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            context.session_id,
            context.created_at,
            context.updated_at,
            context.title,
            context.status,
            context.turn_count,
            context.metadata_json
        ))
        
        conn.commit()
        conn.close()
        
        return context
    
    def add_context(self, session_id: str, role: str, content: str,
                   metadata: dict | None = None) -> ContextEntry:
        """Add a context entry to a session."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get next turn number
        cursor.execute("""
            SELECT COALESCE(MAX(turn_number), 0) + 1 
            FROM context_entries WHERE session_id = ?
        """, (session_id,))
        turn_number = cursor.fetchone()[0]
        
        now = datetime.now(timezone.utc).isoformat()
        entry_id = f"ctx_{session_id}_{turn_number}"
        
        entry = ContextEntry(
            id=entry_id,
            session_id=session_id,
            turn_number=turn_number,
            role=role,
            content=content,
            timestamp=now,
            metadata_json=json.dumps(metadata or {})
        )
        
        cursor.execute("""
            INSERT INTO context_entries 
            (id, session_id, turn_number, role, content, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.session_id,
            entry.turn_number,
            entry.role,
            entry.content,
            entry.timestamp,
            entry.metadata_json
        ))
        
        # Update session turn count
        cursor.execute("""
            UPDATE context_sessions 
            SET turn_count = turn_count + 1, updated_at = ?
            WHERE session_id = ?
        """, (now, session_id))
        
        conn.commit()
        conn.close()
        
        return entry
    
    def get_context_window(self, session_id: str, last_n: int = 10) -> list[ContextEntry]:
        """Get the last N turns of context for a session."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, session_id, turn_number, role, content, timestamp, metadata_json
            FROM context_entries
            WHERE session_id = ?
            ORDER BY turn_number DESC
            LIMIT ?
        """, (session_id, last_n))
        
        entries = []
        for row in cursor.fetchall():
            entries.append(ContextEntry(
                id=row['id'],
                session_id=row['session_id'],
                turn_number=row['turn_number'],
                role=row['role'],
                content=row['content'],
                timestamp=row['timestamp'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return list(reversed(entries))  # Return in chronological order
    
    def get_session(self, session_id: str) -> SessionContext | None:
        """Get session metadata."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, created_at, updated_at, title, status, 
                   turn_count, summary, metadata_json
            FROM context_sessions
            WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return SessionContext(
            session_id=row['session_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            title=row['title'],
            status=row['status'],
            turn_count=row['turn_count'],
            summary=row['summary'],
            metadata_json=row['metadata_json']
        )
    
    def update_session_summary(self, session_id: str, summary: str):
        """Update session with summary."""
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE context_sessions 
            SET summary = ?, updated_at = ?
            WHERE session_id = ?
        """, (summary, now, session_id))
        
        conn.commit()
        conn.close()
    
    def archive_session(self, session_id: str):
        """Archive a session."""
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE context_sessions 
            SET status = 'archived', updated_at = ?
            WHERE session_id = ?
        """, (now, session_id))
        
        conn.commit()
        conn.close()
    
    def list_sessions(self, status: str = 'active') -> list[SessionContext]:
        """List all sessions, optionally filtered by status."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT session_id, created_at, updated_at, title, status, 
                       turn_count, summary, metadata_json
                FROM context_sessions
                WHERE status = ?
                ORDER BY updated_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT session_id, created_at, updated_at, title, status, 
                       turn_count, summary, metadata_json
                FROM context_sessions
                ORDER BY updated_at DESC
            """)
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append(SessionContext(
                session_id=row['session_id'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                title=row['title'],
                status=row['status'],
                turn_count=row['turn_count'],
                summary=row['summary'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return sessions
    
    def delete_session(self, session_id: str):
        """Delete a session and all its entries."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Delete entries first
        cursor.execute("""
            DELETE FROM context_entries WHERE session_id = ?
        """, (session_id,))
        
        # Delete session
        cursor.execute("""
            DELETE FROM context_sessions WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> dict[str, Any]:
        """Get context store statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total sessions
        cursor.execute("SELECT COUNT(*) FROM context_sessions")
        stats['total_sessions'] = cursor.fetchone()[0]
        
        # Active sessions
        cursor.execute("SELECT COUNT(*) FROM context_sessions WHERE status = 'active'")
        stats['active_sessions'] = cursor.fetchone()[0]
        
        # Archived sessions
        cursor.execute("SELECT COUNT(*) FROM context_sessions WHERE status = 'archived'")
        stats['archived_sessions'] = cursor.fetchone()[0]
        
        # Total context entries
        cursor.execute("SELECT COUNT(*) FROM context_entries")
        stats['total_entries'] = cursor.fetchone()[0]
        
        # Average turns per session
        cursor.execute("SELECT AVG(turn_count) FROM context_sessions")
        stats['avg_turns_per_session'] = cursor.fetchone()[0] or 0
        
        conn.close()
        return stats