"""Tests — CLO V1: Continuous Learning Session Handoff.

Test:
1. Create session, end session, auto-create next session
2. STOP flag prevents new session creation
3. PAUSE/RESUME state transitions
4. Persistent state survives restart
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, 'src')

from quan_ai_brain.cognition.learning_session import (
    LearningSession,
    LearningSessionManager,
    LearningSessionStatus,
)
from quan_ai_brain.cognition.continuous_learning_engine import (
    ContinuousLearningEngine,
    LearningType,
)
from quan_ai_brain.memory.sqlite_store import MemoryStore


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create temporary workspace with data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return tmp_path


@pytest.fixture
def session_manager(tmp_workspace):
    """Create session manager with temp DB."""
    db_path = tmp_workspace / "data" / "learning_checkpoints.db"
    return LearningSessionManager(db_path)


@pytest.fixture
def clo_engine(tmp_workspace):
    """Create ContinuousLearningEngine with temp workspace."""
    store = MemoryStore(tmp_workspace / "data" / "brain.db", workspace=tmp_workspace)
    return ContinuousLearningEngine(store, workspace=tmp_workspace)


class TestLearningSessionManager:
    """Tests for LearningSessionManager."""

    def test_create_session(self, session_manager):
        """Create a new session."""
        session = session_manager.create_session(
            objectives=["Test objective"],
            source_manifest={"source": "test"}
        )
        
        assert session.session_id is not None
        assert session.cycle_number == 1
        assert session.status == LearningSessionStatus.INITIALIZING
        assert session.learning_objectives == ["Test objective"]

    def test_session_cycle_number_increments(self, session_manager):
        """Cycle number increments for each new session."""
        s1 = session_manager.create_session(["obj1"], {})
        s2 = session_manager.create_session(["obj2"], {})
        s3 = session_manager.create_session(["obj3"], {})
        
        assert s1.cycle_number == 1
        assert s2.cycle_number == 2
        assert s3.cycle_number == 3

    def test_get_current_session(self, session_manager):
        """Get the most recent session."""
        s1 = session_manager.create_session(["obj1"], {})
        s2 = session_manager.create_session(["obj2"], {})
        
        current = session_manager.get_current_session()
        assert current.session_id == s2.session_id
        assert current.cycle_number == 2

    def test_update_session_status(self, session_manager):
        """Update session status."""
        session = session_manager.create_session(["obj"], {})
        session_manager.set_status(session.session_id, LearningSessionStatus.RUNNING)
        
        updated = session_manager.get_session_by_id(session.session_id)
        assert updated.status == LearningSessionStatus.RUNNING

    def test_persistent_state(self, session_manager):
        """Persistent state survives across instances."""
        session_manager.set_learning_state("TEST_KEY", "test_value")
        session_manager.set_learning_state("TEST_BOOL", True)
        
        # Create new instance
        db_path = session_manager.db_path
        new_manager = LearningSessionManager(db_path)
        
        assert new_manager.get_learning_state("TEST_KEY") == "test_value"
        assert new_manager.get_learning_state("TEST_BOOL") is True

    def test_clo_enable_disable(self, session_manager):
        """Enable and disable CLO mode."""
        assert not session_manager.is_clo_enabled()
        
        session_manager.enable_clo()
        assert session_manager.is_clo_enabled()
        
        session_manager.disable_clo()
        assert not session_manager.is_clo_enabled()

    def test_stop_flag(self, session_manager):
        """Set and get stop flag."""
        stop_flag, reason = session_manager.get_stop_flag()
        assert not stop_flag
        
        session_manager.set_stop_flag("Owner requested stop")
        stop_flag, reason = session_manager.get_stop_flag()
        assert stop_flag
        assert reason == "Owner requested stop"

    def test_list_sessions(self, session_manager):
        """List recent sessions."""
        for i in range(5):
            session_manager.create_session([f"obj{i}"], {})
        
        sessions = session_manager.list_sessions(limit=3)
        assert len(sessions) == 3
        assert sessions[0].cycle_number == 5
        assert sessions[1].cycle_number == 4
        assert sessions[2].cycle_number == 3


class TestContinuousLearningEngine:
    """Tests for ContinuousLearningEngine with CLO V1 features."""

    def test_start_continuous_learning(self, clo_engine):
        """Start continuous learning creates first session."""
        session = clo_engine.start_continuous_learning(
            objectives=["Learn knowledge"],
            source_manifest={"sources": ["docs/"]}
        )
        
        assert session.cycle_number == 1
        assert session.status == LearningSessionStatus.PLANNING
        assert clo_engine.session_manager.is_clo_enabled()

    def test_end_session_creates_next(self, clo_engine):
        """Ending session auto-creates next session."""
        # Start first session
        s1 = clo_engine.start_continuous_learning(["obj1"], {"src": "test"})
        
        # End session
        s2 = clo_engine.end_session(
            session_id=s1.session_id,
            evaluation_result={"score": 0.9},
            unresolved_questions=[],
            next_plan={"objectives": ["obj2"], "source_manifest": {"src": "test2"}}
        )
        
        # Check next session was created
        current = clo_engine.session_manager.get_current_session()
        assert current.cycle_number == 2
        assert current.status == LearningSessionStatus.RUNNING

    def test_stop_flag_prevents_new_session(self, clo_engine):
        """STOP flag prevents auto-creation of next session."""
        # Start first session
        s1 = clo_engine.start_continuous_learning(["obj1"], {"src": "test"})
        
        # Set stop flag
        clo_engine.session_manager.set_stop_flag("Owner stop request")
        
        # End session
        s2 = clo_engine.end_session(
            session_id=s1.session_id,
            evaluation_result={"score": 0.9},
            unresolved_questions=[],
            next_plan={"objectives": ["obj2"], "source_manifest": {}}
        )
        
        # Check no new session was created
        current = clo_engine.session_manager.get_current_session()
        assert current.session_id == s1.session_id
        assert current.status == LearningSessionStatus.STOPPING

    def test_pause_continuous_learning(self, clo_engine):
        """Pause stops new session creation."""
        s1 = clo_engine.start_continuous_learning(["obj1"], {"src": "test"})
        
        clo_engine.pause_continuous_learning("Resource limit reached")
        
        status = clo_engine.get_learning_status()
        assert status["pause_flag"] is True
        
        # Current session should be paused
        current = clo_engine.session_manager.get_current_session()
        assert current.status == LearningSessionStatus.PAUSED

    def test_resume_continuous_learning(self, clo_engine):
        """Resume from pause."""
        s1 = clo_engine.start_continuous_learning(["obj1"], {"src": "test"})
        clo_engine.pause_continuous_learning("Temp pause")
        
        clo_engine.resume_continuous_learning()
        
        status = clo_engine.get_learning_status()
        assert status["pause_flag"] is False
        
        # Current session should be running
        current = clo_engine.session_manager.get_current_session()
        assert current.status == LearningSessionStatus.RUNNING

    def test_stop_continuous_learning(self, clo_engine):
        """Stop permanently disables CLO."""
        s1 = clo_engine.start_continuous_learning(["obj1"], {"src": "test"})
        
        clo_engine.stop_continuous_learning("Owner requested stop")
        
        status = clo_engine.get_learning_status()
        assert status["clo_enabled"] is False
        assert status["stop_flag"] is True
        
        # Current session should be stopped
        current = clo_engine.session_manager.get_current_session()
        assert current.status == LearningSessionStatus.STOPPED

    def test_get_learning_status(self, clo_engine):
        """Get learning status returns correct info."""
        # Before starting
        status = clo_engine.get_learning_status()
        assert status["clo_enabled"] is False
        assert status["current_session"] is None
        
        # After starting
        s1 = clo_engine.start_continuous_learning(["obj1"], {"src": "test"})
        status = clo_engine.get_learning_status()
        assert status["clo_enabled"] is True
        assert status["current_session"]["session_id"] == s1.session_id
        assert status["total_sessions"] == 1


class TestContinuousHandoffIntegration:
    """Integration test: multiple sessions in sequence."""

    def test_three_sessions_in_sequence(self, clo_engine):
        """Test three sessions created in sequence."""
        # Session 1
        s1 = clo_engine.start_continuous_learning(["obj1"], {"src": "test1"})
        assert s1.cycle_number == 1
        
        # End session 1 -> creates session 2
        s2 = clo_engine.end_session(
            session_id=s1.session_id,
            evaluation_result={"score": 0.85},
            unresolved_questions=["q1"],
            next_plan={"objectives": ["obj2"], "source_manifest": {"src": "test2"}}
        )
        current = clo_engine.session_manager.get_current_session()
        assert current.cycle_number == 2
        
        # End session 2 -> creates session 3
        s3 = clo_engine.end_session(
            session_id=current.session_id,
            evaluation_result={"score": 0.90},
            unresolved_questions=[],
            next_plan={"objectives": ["obj3"], "source_manifest": {"src": "test3"}}
        )
        current = clo_engine.session_manager.get_current_session()
        assert current.cycle_number == 3
        
        # Verify all sessions exist
        sessions = clo_engine.session_manager.list_sessions(limit=10)
        assert len(sessions) == 3
        assert sessions[0].cycle_number == 3
        assert sessions[1].cycle_number == 2
        assert sessions[2].cycle_number == 1

    def test_session_persists_after_restart(self, tmp_workspace):
        """Session state persists across engine restarts."""
        # Create engine and session
        store1 = MemoryStore(tmp_workspace / "data" / "brain.db", workspace=tmp_workspace)
        engine1 = ContinuousLearningEngine(store1, workspace=tmp_workspace)
        
        s1 = engine1.start_continuous_learning(["obj1"], {"src": "test1"})
        engine1.end_session(
            session_id=s1.session_id,
            evaluation_result={"score": 0.85},
            unresolved_questions=[],
            next_plan={"objectives": ["obj2"], "source_manifest": {"src": "test2"}}
        )
        
        # Create new engine instance (simulating restart)
        store2 = MemoryStore(tmp_workspace / "data" / "brain.db", workspace=tmp_workspace)
        engine2 = ContinuousLearningEngine(store2, workspace=tmp_workspace)
        
        # Check state persisted
        status = engine2.get_learning_status()
        assert status["clo_enabled"] is True
        assert status["total_sessions"] == 2
        assert status["current_session"]["cycle_number"] == 2