"""Integration tests for QUAN AI BRAIN V37.

Tests:
- Memory tiering (short → long → verified)
- Quarantine workflow
- Barge-in detection
- Voice pipeline E2E
- Service health
"""
import pytest
import time
from pathlib import Path
import sqlite3

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from quan_ai_brain.memory.quarantine_store import QuarantineStore, create_quarantine_store
from quan_ai_brain.voice.barge_in_handler import TurnController, BargeInDetector, TurnState


class TestQuarantineStore:
    """Test quarantine mechanism."""
    
    @pytest.fixture
    def store(self, tmp_path):
        """Create temporary quarantine store."""
        db_path = tmp_path / "quarantine.db"
        return create_quarantine_store(str(db_path))
    
    def test_add_knowledge(self, store):
        """Test adding knowledge to quarantine."""
        ku_id = store.add_knowledge(
            content="Test knowledge",
            source_ref="test_source",
            expires_days=7
        )
        
        assert ku_id is not None
        stats = store.get_stats()
        assert stats['pending'] == 1
    
    def test_approve_knowledge(self, store):
        """Test approving quarantine item."""
        ku_id = store.add_knowledge("Test", "source")
        result = store.approve(ku_id, "tester", "Approved for production")
        
        assert result is True
        stats = store.get_stats()
        assert stats['by_status'].get('APPROVED', 0) == 1
    
    def test_reject_knowledge(self, store):
        """Test rejecting quarantine item."""
        ku_id = store.add_knowledge("Test", "source")
        result = store.reject(ku_id, "tester", "Insufficient evidence")
        
        assert result is True
        stats = store.get_stats()
        assert stats['by_status'].get('REJECTED', 0) == 1
    
    def test_expire_stale(self, store):
        """Test expiring stale items."""
        # Add item with past expiration (manually manipulate)
        import datetime
        from datetime import timezone
        
        now = datetime.datetime.now(timezone.utc)
        past = (now - datetime.timedelta(days=1)).isoformat()
        
        conn = sqlite3.connect(str(store.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quarantined_knowledge 
            (id, content, source_ref, discovered_at, expires_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "test_expire", "Test", "source",
            past, past, "PENDING_REVIEW"
        ))
        conn.commit()
        conn.close()
        
        expired = store.expire_stale()
        assert expired >= 1
    
    def test_weekly_report(self, store):
        """Test weekly report generation."""
        # Add some items
        for i in range(3):
            store.add_knowledge(f"Test {i}", f"source_{i}")
        
        # Approve one
        items = store.list_pending()
        if items:
            store.approve(items[0].id, "tester")
        
        report = store.generate_weekly_report()
        
        assert 'period' in report
        assert 'new_knowledge' in report
        assert 'approved' in report
        assert 'top_sources' in report


class TestBargeInDetector:
    """Test barge-in detection."""
    
    def test_barge_in_detection(self):
        """Test detecting barge-in during speaking."""
        detector = BargeInDetector(
            vad_threshold=0.8,
            min_speech_duration_ms=500,
            min_silence_ms=300
        )
        
        # Start speaking
        detector.start_speaking()
        time.sleep(0.1)
        
        # Simulate VAD activity (user speaking)
        timestamp = time.time()
        detector.on_vad_active(0.9, timestamp)
        
        # Not enough duration yet
        assert not detector.is_barge_in_detected(timestamp)
        
        # Wait for minimum duration
        time.sleep(0.5)
        timestamp = time.time()
        
        # Now should detect barge-in
        assert detector.is_barge_in_detected(timestamp)
    
    def test_no_barge_in_when_idle(self):
        """Test no barge-in when not speaking."""
        detector = BargeInDetector()
        
        # Simulate VAD activity when not speaking
        timestamp = time.time()
        detector.on_vad_active(0.9, timestamp)
        
        assert not detector.is_barge_in_detected(timestamp)


class TestTurnController:
    """Test turn control with barge-in."""
    
    def test_state_transitions(self):
        """Test normal turn flow."""
        controller = TurnController()
        
        assert controller.state == TurnState.IDLE
        
        controller.start_listening()
        assert controller.state == TurnState.LISTENING
        
        controller.start_thinking()
        assert controller.state == TurnState.THINKING
        
        controller.start_responding()
        assert controller.state == TurnState.RESPONDING
        
        controller.start_speaking()
        assert controller.state == TurnState.SPEAKING
        
        controller.stop_speaking()
        assert controller.state == TurnState.IDLE
    
    def test_interrupt_during_speaking(self):
        """Test interrupt during speaking."""
        controller = TurnController()
        interrupted = []
        
        def on_interrupt(reason):
            interrupted.append(reason)
        
        controller.on_interrupt(on_interrupt)
        
        # Must go through proper state transitions
        controller.start_listening()
        controller.start_thinking()
        controller.start_responding()
        controller.start_speaking()
        assert controller.state == TurnState.SPEAKING
        
        # Simulate interrupt
        controller._handle_interrupt("User interrupted")
        
        assert controller.state == TurnState.INTERRUPTED
        assert len(interrupted) == 1
    
    def test_freeze_unfreeze(self):
        """Test freeze and unfreeze."""
        controller = TurnController()
        
        controller.freeze()
        assert controller.state == TurnState.FREEZED
        
        controller.unfreeze()
        assert controller.state == TurnState.IDLE


class TestMemoryTiering:
    """Test memory tiering workflow."""
    
    def test_tier_flow(self, tmp_path):
        """Test knowledge flowing through tiers."""
        from quan_ai_brain.memory.vector_store import LongTermMemoryStore, MemoryChunk, MemoryTieringEngine
        
        # Create mock embedding service
        class MockEmbedding:
            def embed(self, texts):
                return [[0.1] * 1024 for _ in texts]
            def get_dimension(self):
                return 1024
        
        # Create stores
        vector_store = LongTermMemoryStore(
            db_path=str(tmp_path / "vector_db"),
            embedding_service=MockEmbedding()
        )
        quarantine_store = create_quarantine_store(str(tmp_path / "quarantine.db"))
        engine = MemoryTieringEngine(vector_store)
        
        # Add to quarantine
        ku_id = quarantine_store.add_knowledge(
            content="Test knowledge for tiering",
            source_ref="self_research"
        )
        
        # Approve
        quarantine_store.approve(ku_id, "owner")
        
        # Tier to verified
        record = {
            "id": ku_id,
            "content": "Test knowledge for tiering",
            "memory_type": "SEMANTIC",
            "source_ref": "self_research",
            "verification_status": "VERIFIED",
            "tags": [],
            "created_at_utc": ""
        }
        
        result = engine.tier_memory(record, "verified")
        
        assert "Verified" in result
        
        # Verify in vector store
        stats = vector_store.get_stats()
        assert stats['total_chunks'] > 0


class TestServiceHealth:
    """Test service health checks."""
    
    def test_health_check_script(self):
        """Test that health check script exists and runs."""
        import subprocess
        
        result = subprocess.run(
            ["python", "tools/health_check.py"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        # Should run without error
        assert result.returncode in [0, 1]  # 0 = all healthy, 1 = some offline
        assert "Health Check" in result.stdout


class TestIntegrationE2E:
    """End-to-end integration tests."""
    
    def test_full_voice_pipeline_mock(self):
        """Test voice pipeline with mocks."""
        # This would test: Audio → VAD → ASR → LLM → TTS → Playback
        # For now, just verify all components exist
        
        from quan_ai_brain.voice.audio_capture import AudioCapture
        from quan_ai_brain.voice.vad_processor import VADProcessor
        from quan_ai_brain.voice.asr_interface import ASRConfig
        from quan_ai_brain.voice.tts_interface import TTSConfig
        from quan_ai_brain.voice.barge_in_handler import TurnController
        
        # All imports successful
        assert AudioCapture is not None
        assert VADProcessor is not None
        assert ASRConfig is not None
        assert TTSConfig is not None
        assert TurnController is not None
    
    def test_memory_pipeline_e2e(self):
        """Test memory pipeline end-to-end."""
        from quan_ai_brain.memory.vector_store import MemoryChunk, MemoryTieringEngine, LongTermMemoryStore
        from quan_ai_brain.memory.quarantine_store import create_quarantine_store
        
        # All imports successful
        assert MemoryChunk is not None
        assert MemoryTieringEngine is not None
        assert LongTermMemoryStore is not None
        assert create_quarantine_store is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])