"""Context Retriever - Context-aware retrieval and augmentation.

Provides:
- Context-aware retrieval with relevance scoring
- Cross-session context search
- Context summarization
- Context augmentation for LLM prompts
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .context_store import ContextStore, ContextEntry, SessionContext
from .session_manager import SessionManager, SessionState


@dataclass
class ContextMatch:
    """A matched context entry with relevance score."""
    entry: ContextEntry
    session: SessionContext
    relevance_score: float
    match_reason: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'entry': self.entry.to_dict(),
            'session': self.session.to_dict(),
            'relevance_score': self.relevance_score,
            'match_reason': self.match_reason
        }


@dataclass
class ContextWindow:
    """A window of context for LLM consumption."""
    session_id: str
    title: str
    entries: list[ContextEntry]
    summary: str | None = None
    total_tokens: int = 0
    
    def to_prompt_format(self, max_tokens: int = 4000) -> str:
        """Convert to prompt format for LLM."""
        lines = [f"## Session: {self.title}"]
        
        if self.summary:
            lines.append(f"\n**Summary:** {self.summary}\n")
        
        lines.append("\n**Conversation:**\n")
        
        for entry in self.entries:
            role_display = entry.role.upper()
            lines.append(f"{role_display}: {entry.content}")
        
        return "\n\n".join(lines)
    
    def estimate_tokens(self) -> int:
        """Estimate token count (rough approximation)."""
        text = self.to_prompt_format()
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // 4


class ContextRetriever:
    """Context-aware retrieval and augmentation."""
    
    def __init__(self, context_store: ContextStore | None = None,
                 session_manager: SessionManager | None = None):
        self.context_store = context_store or ContextStore()
        self.session_manager = session_manager or SessionManager(self.context_store)
    
    def get_recent_context(self, session_id: str, 
                          last_n: int = 10) -> ContextWindow:
        """Get recent context window for a session."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        entries = self.context_store.get_context_window(session_id, last_n)
        
        return ContextWindow(
            session_id=session_id,
            title=session.title,
            entries=entries,
            summary=session.context_summary
        )
    
    def search_context(self, query: str, 
                      session_ids: list[str] | None = None,
                      max_results: int = 10) -> list[ContextMatch]:
        """Search across context entries for relevant content."""
        matches = []
        
        # Get sessions to search
        if session_ids:
            sessions = [self.context_store.get_session(sid) for sid in session_ids]
            sessions = [s for s in sessions if s]
        else:
            sessions = self.context_store.list_sessions(status='active')
        
        # Search each session
        for session in sessions:
            entries = self.context_store.get_context_window(session.session_id, 100)
            
            for entry in entries:
                score, reason = self._calculate_relevance(query, entry)
                
                if score > 0.3:  # Threshold
                    matches.append(ContextMatch(
                        entry=entry,
                        session=session,
                        relevance_score=score,
                        match_reason=reason
                    ))
        
        # Sort by relevance
        matches.sort(key=lambda m: m.relevance_score, reverse=True)
        return matches[:max_results]
    
    def _calculate_relevance(self, query: str, entry: ContextEntry) -> tuple[float, str]:
        """Calculate relevance score between query and entry."""
        query_lower = query.lower()
        content_lower = entry.content.lower()
        
        # Exact word match
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        intersection = query_words & content_words
        if intersection:
            score = len(intersection) / len(query_words)
            return min(score, 1.0), f"Word overlap: {', '.join(intersection)}"
        
        # Partial match
        if query_lower in content_lower:
            return 0.8, "Exact phrase match"
        
        # Keyword match
        for word in query_words:
            if len(word) > 3 and word in content_lower:
                return 0.5, f"Keyword match: {word}"
        
        return 0.0, "No match"
    
    def get_context_for_continuation(self, session_id: str,
                                    max_tokens: int = 4000) -> ContextWindow:
        """Get context window optimized for continuation."""
        # Start with recent entries
        window = self.get_recent_context(session_id, last_n=20)
        
        # If too long, reduce
        if window.estimate_tokens() > max_tokens:
            window = self.get_recent_context(session_id, last_n=10)
        
        # If still too long, use summary
        if window.estimate_tokens() > max_tokens and window.entries:
            # Keep only last 5 entries + summary
            window.entries = window.entries[-5:]
        
        return window
    
    def summarize_session(self, session_id: str) -> str:
        """Generate a summary of the session."""
        entries = self.context_store.get_context_window(session_id, 100)
        
        if not entries:
            return "Empty session"
        
        # Simple summarization: extract key topics
        topics = set()
        for entry in entries[-20:]:  # Last 20 entries
            # Extract potential topics (capitalized words, key phrases)
            words = re.findall(r'\b[A-Z][a-z]{2,}\b', entry.content)
            topics.update(words)
        
        if topics:
            return f"Session about: {', '.join(list(topics)[:5])}"
        
        return f"Session with {len(entries)} turns"
    
    def auto_summarize_and_archive(self, session_id: str):
        """Auto-summarize and archive a session."""
        summary = self.summarize_session(session_id)
        self.context_store.update_session_summary(session_id, summary)
        self.session_manager.archive_session(session_id, summary)
        
        return summary
    
    def get_cross_session_context(self, query: str,
                                  max_sessions: int = 3,
                                  max_entries_per_session: int = 5) -> dict[str, ContextWindow]:
        """Get relevant context from multiple sessions."""
        matches = self.search_context(query, max_results=50)
        
        # Group by session
        session_entries: dict[str, list[ContextEntry]] = {}
        session_scores: dict[str, float] = {}
        
        for match in matches:
            sid = match.entry.session_id
            if sid not in session_entries:
                session_entries[sid] = []
                session_scores[sid] = 0
            
            session_entries[sid].append(match.entry)
            session_scores[sid] = max(session_scores[sid], match.relevance_score)
            
            if len(session_entries[sid]) >= max_entries_per_session:
                continue
        
        # Sort sessions by best score
        sorted_sessions = sorted(
            session_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_sessions]
        
        result = {}
        for sid, _ in sorted_sessions:
            session = self.context_store.get_session(sid)
            if session:
                result[sid] = ContextWindow(
                    session_id=sid,
                    title=session.title,
                    entries=session_entries[sid]
                )
        
        return result
    
    def get_context_stats(self) -> dict[str, Any]:
        """Get context retrieval statistics."""
        return self.context_store.get_statistics()