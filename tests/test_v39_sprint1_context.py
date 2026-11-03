"""Tests for Sprint 1: Context & Session Memory.

Tests:
- ContextStore: Session creation, context entry, retrieval
- SessionManager: Lifecycle management, state transitions
- ContextRetriever: Search, relevance scoring, summarization
"""
import pytest
import json
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from quan_ai_brain.memory.context_store import ContextStore, ContextEntry, SessionContext
from quan_ai_brain.memory.session_manager import SessionManager, SessionState, SessionStatus
from quan_ai_brain.memory.context_retriever import ContextRetriever, ContextMatch, ContextWindow


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_brain.db"
    
    yield str(db_path)
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def context_store(temp_db):
    """Create a ContextStore instance."""
    return ContextStore(db_path=temp_db)


@pytest.fixture
def session_manager(context_store):
    """Create a SessionManager instance."""
    return SessionManager(context_store)


@pytest.fixture
def context_retriever(context_store):
    """Create a ContextRetriever instance."""
    return ContextRetriever(context_store)


class TestContextStore:
    """Tests for ContextStore class."""
    
    def test_create_session(self, context_store):
        """Test creating a new session."""
        session = context_store.create_session(
            session_id="test_001",
            title="Test Session",
            metadata={"user": "test_user"}
        )
        
        assert session.session_id == "test_001"
        assert session.title == "Test Session"
        assert session.status == "active"
        assert session.turn_count == 0
        assert json.loads(session.metadata_json)["user"] == "test_user"
    
    def test_add_context_entry(self, context_store):
        """Test adding context entries."""
        context_store.create_session("test_001", "Test")
        
        entry1 = context_store.add_context(
            session_id="test_001",
            role="user",
            content="Hello",
            metadata={"timestamp": "2024-01-01"}
        )
        
        entry2 = context_store.add_context(
            session_id="test_001",
            role="assistant",
            content="Hi there!",
            metadata={"timestamp": "2024-01-01"}
        )
        
        assert entry1.role == "user"
        assert entry1.content == "Hello"
        assert entry1.turn_number == 1
        
        assert entry2.role == "assistant"
        assert entry2.turn_number == 2
        
        # Check session turn count updated
        session = context_store.get_session("test_001")
        assert session.turn_count == 2
    
    def test_get_context_window(self, context_store):
        """Test retrieving context window."""
        context_store.create_session("test_001", "Test")
        
        # Add 15 entries
        for i in range(15):
            context_store.add_context(
                session_id="test_001",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
        
        # Get last 5
        window = context_store.get_context_window("test_001", last_n=5)
        
        assert len(window) == 5
        assert window[0].turn_number == 11  # First in chronological order
        assert window[-1].turn_number == 15  # Last
    
    def test_archive_session(self, context_store):
        """Test archiving a session."""
        context_store.create_session("test_001", "Test")
        context_store.add_context("test_001", "user", "Hello")
        
        context_store.archive_session("test_001")
        
        session = context_store.get_session("test_001")
        assert session.status == "archived"
    
    def test_list_sessions(self, context_store):
        """Test listing sessions."""
        context_store.create_session("test_001", "Active 1")
        context_store.create_session("test_002", "Active 2")
        context_store.create_session("test_003", "To Archive")
        
        # Archive one
        context_store.archive_session("test_003")
        
        active = context_store.list_sessions(status="active")
        archived = context_store.list_sessions(status="archived")
        
        assert len(active) == 2
        assert len(archived) == 1
    
    def test_delete_session(self, context_store):
        """Test deleting a session."""
        context_store.create_session("test_001", "Test")
        context_store.add_context("test_001", "user", "Hello")
        
        context_store.delete_session("test_001")
        
        session = context_store.get_session("test_001")
        assert session is None
        
        # Verify entries also deleted
        window = context_store.get_context_window("test_001", last_n=10)
        assert len(window) == 0
    
    def test_get_statistics(self, context_store):
        """Test getting statistics."""
        context_store.create_session("test_001", "Test 1")
        context_store.create_session("test_002", "Test 2")
        context_store.add_context("test_001", "user", "Hello")
        context_store.add_context("test_001", "assistant", "Hi")
        
        stats = context_store.get_statistics()
        
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 2
        assert stats["total_entries"] == 2
        assert stats["avg_turns_per_session"] == 1.0


class TestSessionManager:
    """Tests for SessionManager class."""
    
    def test_create_session(self, session_manager):
        """Test creating a session."""
        state = session_manager.create_session(
            title="New Test Session",
            user_id="user_123",
            metadata={"source": "test"}
        )
        
        assert state.status == SessionStatus.ACTIVE
        assert state.title == "New Test Session"
        assert state.user_id == "user_123"
    
    def test_add_message(self, session_manager):
        """Test adding messages to session."""
        state = session_manager.create_session("Test")
        
        entry = session_manager.add_message(
            session_id=state.session_id,
            role="user",
            content="Hello"
        )
        
        assert entry.role == "user"
        assert entry.content == "Hello"
        
        # Verify session updated
        updated = session_manager.get_session(state.session_id)
        assert updated.last_activity_at > updated.created_at
    
    def test_pause_and_resume(self, session_manager):
        """Test pausing and resuming session."""
        state = session_manager.create_session("Test")
        
        # Pause
        paused = session_manager.pause_session(state.session_id, "Taking a break")
        assert paused.status == SessionStatus.PAUSED
        
        # Resume
        resumed = session_manager.resume_session(state.session_id)
        assert resumed.status == SessionStatus.ACTIVE
    
    def test_archive_session(self, session_manager):
        """Test archiving session."""
        state = session_manager.create_session("Test")
        session_manager.add_message(state.session_id, "user", "Hello")
        
        archived = session_manager.archive_session(
            state.session_id,
            summary="Test session summary"
        )
        
        assert archived.status == SessionStatus.ARCHIVED
        
        # Verify not in active sessions
        active = session_manager.list_active_sessions()
        assert state.session_id not in [s.session_id for s in active]
    
    def test_close_session(self, session_manager):
        """Test closing session."""
        state = session_manager.create_session("Test")
        
        closed = session_manager.close_session(state.session_id, "Completed")
        assert closed.status == SessionStatus.CLOSED
    
    def test_delete_session(self, session_manager):
        """Test deleting session."""
        state = session_manager.create_session("Test")
        
        session_manager.delete_session(state.session_id)
        
        # Verify deleted
        retrieved = session_manager.get_session(state.session_id)
        assert retrieved is None
    
    def test_error_on_inactive_session(self, session_manager):
        """Test error when adding message to inactive session."""
        state = session_manager.create_session("Test")
        session_manager.pause_session(state.session_id)
        
        with pytest.raises(ValueError, match="Cannot add message"):
            session_manager.add_message(state.session_id, "user", "Hello")
    
    def test_list_active_sessions(self, session_manager):
        """Test listing active sessions."""
        session_manager.create_session("Test 1", user_id="user_1")
        session_manager.create_session("Test 2", user_id="user_2")
        session_manager.create_session("Test 3", user_id="user_1")
        
        all_active = session_manager.list_active_sessions()
        user1_active = session_manager.list_active_sessions(user_id="user_1")
        
        assert len(all_active) == 3
        assert len(user1_active) == 2


class TestContextRetriever:
    """Tests for ContextRetriever class."""
    
    def test_get_recent_context(self, context_retriever):
        """Test getting recent context."""
        state = context_retriever.session_manager.create_session("Test")
        
        for i in range(15):
            context_retriever.session_manager.add_message(
                state.session_id,
                "user" if i % 2 == 0 else "assistant",
                f"Message {i}"
            )
        
        window = context_retriever.get_recent_context(state.session_id, last_n=5)
        
        assert len(window.entries) == 5
        assert window.session_id == state.session_id
    
    def test_search_context(self, context_retriever):
        """Test searching context."""
        # Create sessions with relevant content
        state1 = context_retriever.session_manager.create_session("Python Session")
        context_retriever.session_manager.add_message(
            state1.session_id, "user", "How do I use Python lists?"
        )
        context_retriever.session_manager.add_message(
            state1.session_id, "assistant", "Python lists are dynamic arrays..."
        )
        
        state2 = context_retriever.session_manager.create_session("General Session")
        context_retriever.session_manager.add_message(
            state2.session_id, "user", "What is programming?"
        )
        
        # Search for "Python"
        matches = context_retriever.search_context("Python")
        
        assert len(matches) > 0
        assert matches[0].relevance_score > 0.3
        assert "Python" in matches[0].entry.content
    
    def test_search_context_no_match(self, context_retriever):
        """Test search with no matches."""
        state = context_retriever.session_manager.create_session("Test")
        context_retriever.session_manager.add_message(
            state.session_id, "user", "Hello world"
        )
        
        matches = context_retriever.search_context("xyz123nonexistent")
        assert len(matches) == 0
    
    def test_context_window_to_prompt(self, context_retriever):
        """Test converting context window to prompt format."""
        state = context_retriever.session_manager.create_session("Test Session")
        context_retriever.session_manager.add_message(
            state.session_id, "user", "Hello"
        )
        context_retriever.session_manager.add_message(
            state.session_id, "assistant", "Hi there!"
        )
        
        window = context_retriever.get_recent_context(state.session_id, last_n=10)
        prompt = window.to_prompt_format()
        
        assert "## Session: Test Session" in prompt
        assert "USER: Hello" in prompt
        assert "ASSISTANT: Hi there!" in prompt
    
    def test_summarize_session(self, context_retriever):
        """Test session summarization."""
        state = context_retriever.session_manager.create_session("Python Tutorial")
        context_retriever.session_manager.add_message(
            state.session_id, "user", "How do I create a Python class?"
        )
        context_retriever.session_manager.add_message(
            state.session_id, "assistant", "You create a class using the class keyword..."
        )
        context_retriever.session_manager.add_message(
            state.session_id, "user", "What about inheritance?"
        )
        
        summary = context_retriever.summarize_session(state.session_id)
        
        assert len(summary) > 0
        assert "Python" in summary or "class" in summary.lower()
    
    def test_auto_summarize_and_archive(self, context_retriever):
        """Test auto-summarize and archive."""
        state = context_retriever.session_manager.create_session("Test")
        context_retriever.session_manager.add_message(
            state.session_id, "user", "Testing Python classes"
        )
        
        summary = context_retriever.auto_summarize_and_archive(state.session_id)
        
        assert len(summary) > 0
        
        # Verify session archived
        session = context_retriever.session_manager.get_session(state.session_id)
        assert session.status == SessionStatus.ARCHIVED
    
    def test_get_cross_session_context(self, context_retriever):
        """Test getting context from multiple sessions."""
        # Create multiple sessions with related content
        state1 = context_retriever.session_manager.create_session("Python Basics")
        context_retriever.session_manager.add_message(
            state1.session_id, "user", "How to use Python lists?"
        )
        
        state2 = context_retriever.session_manager.create_session("Python Advanced")
        context_retriever.session_manager.add_message(
            state2.session_id, "user", "Python list comprehensions"
        )
        
        state3 = context_retriever.session_manager.create_session("General")
        context_retriever.session_manager.add_message(
            state3.session_id, "user", "What is programming?"
        )
        
        # Search for "Python"
        results = context_retriever.get_cross_session_context("Python", max_sessions=2)
        
        assert len(results) <= 2
        # Should find Python-related sessions
        assert any("Python" in s.title for s in results.values())
    
    def test_get_context_stats(self, context_retriever):
        """Test getting context statistics."""
        context_retriever.session_manager.create_session("Test 1")
        context_retriever.session_manager.create_session("Test 2")
        
        stats = context_retriever.get_context_stats()
        
        assert "total_sessions" in stats
        assert "active_sessions" in stats
        assert stats["total_sessions"] == 2


class TestContextIntegration:
    """Integration tests for context system."""
    
    def test_full_workflow(self, temp_db):
        """Test complete context workflow."""
        store = ContextStore(db_path=temp_db)
        manager = SessionManager(store)
        retriever = ContextRetriever(store)
        
        # Create session
        state = manager.create_session("Development Session", user_id="dev_001")
        
        # Add conversation
        manager.add_message(state.session_id, "user", "How do I implement a REST API?")
        manager.add_message(state.session_id, "assistant", "You can use Flask or FastAPI...")
        manager.add_message(state.session_id, "user", "What about authentication?")
        manager.add_message(state.session_id, "assistant", "Use JWT tokens for authentication...")
        
        # Get context window
        window = retriever.get_recent_context(state.session_id, last_n=10)
        assert len(window.entries) == 4
        
        # Search context
        matches = retriever.search_context("authentication")
        assert len(matches) > 0
        
        # Summarize and archive
        summary = retriever.auto_summarize_and_archive(state.session_id)
        assert len(summary) > 0
        
        # Verify archived - fetch fresh from database (bypass cache)
        # Delete from cache first to force fresh fetch
        if state.session_id in manager._active_sessions:
            del manager._active_sessions[state.session_id]
        
        session = manager.get_session(state.session_id)
        assert session.status == SessionStatus.ARCHIVED
    
    def test_multiple_users_isolation(self, temp_db):
        """Test that different users' sessions are isolated."""
        store = ContextStore(db_path=temp_db)
        manager = SessionManager(store)
        
        # User 1 creates session
        state1 = manager.create_session("User 1 Session", user_id="user_1")
        manager.add_message(state1.session_id, "user", "User 1 message")
        
        # User 2 creates session
        state2 = manager.create_session("User 2 Session", user_id="user_2")
        manager.add_message(state2.session_id, "user", "User 2 message")
        
        # List user 1's sessions only
        user1_sessions = manager.list_active_sessions(user_id="user_1")
        assert len(user1_sessions) == 1
        assert user1_sessions[0].session_id == state1.session_id
        
        # List user 2's sessions only
        user2_sessions = manager.list_active_sessions(user_id="user_2")
        assert len(user2_sessions) == 1
        assert user2_sessions[0].session_id == state2.session_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])