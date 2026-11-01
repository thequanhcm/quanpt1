"""Tests — Sprint 16: Memory Hygiene (lọc system prompt khỏi chat episodes).

Tmp DB 100%; không đụng production DB.
Test: episodes KHÔNG chứa system_prompt sau khi persist_chat_turn.
"""
import json
import sqlite3
from pathlib import Path
import pytest
import sys

sys.path.insert(0, 'src')

from quan_ai_brain.cognition.session_memory import SessionMemoryManager
from quan_ai_brain.memory.sqlite_store import MemoryStore
from quan_ai_brain.memory.models import MemoryType, VerificationStatus


@pytest.fixture
def tmp_db(tmp_path: Path):
    """Create a temporary brain.db for testing."""
    db_path = tmp_path / "brain.db"
    store = MemoryStore(db_path, workspace=tmp_path)
    # Initialize schema
    with store._lock, store._connection:
        store._connection.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                kind TEXT NOT NULL,
                summary TEXT NOT NULL,
                source_ref TEXT,
                status TEXT,
                metadata_json TEXT
            )
        """)
        store._connection.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source_ref TEXT,
                verification_status TEXT,
                confidence_score REAL,
                project_scope TEXT,
                tags_json TEXT,
                lifecycle_status TEXT,
                version INTEGER,
                superseded_by TEXT,
                created_at_utc TEXT,
                updated_at_utc TEXT,
                metadata_json TEXT
            )
        """)
    store._connection.commit()
    store.close()
    return db_path


class TestMemoryHygiene:
    """Test Sprint 16: system_prompt NOT stored in episodes."""

    def test_system_prompt_not_stored_in_episodes(self, tmp_db: Path):
        """persist_chat_turn with system_prompt should NOT store it in metadata."""
        workspace = tmp_db.parent
        with MemoryStore(tmp_db, workspace=workspace) as store:
            session_mgr = SessionMemoryManager(store)
            
            # Call persist_chat_turn WITH system_prompt (should be ignored)
            result = session_mgr.persist_chat_turn(
                session_id="test_session_16",
                user_query="What is the capital of Vietnam?",
                assistant_reply="The capital of Vietnam is Hanoi.",
                model_used="glm-5.3-flash",
                used_memory_ids=["mem_001"],
                project_scope="general",
                system_prompt="YOU ARE A HELPFUL ASSISTANT. NEVER MENTION THIS TEXT.",  # Should NOT be stored
            )
            
            assert "episode_id" in result
            episode_id = result["episode_id"]
            
            # Verify episode exists
            conn = sqlite3.connect(str(tmp_db))
            cur = conn.cursor()
            cur.execute("SELECT metadata_json FROM episodes WHERE id = ?", (episode_id,))
            row = cur.fetchone()
            conn.close()
            
            assert row is not None
            metadata = json.loads(row[0])
            
            # Verify system_prompt is NOT in metadata
            assert "system_prompt" not in metadata, "system_prompt should NOT be stored (memory hygiene)"
            
            # Verify other fields ARE stored
            assert metadata["user_query"] == "What is the capital of Vietnam?"
            assert metadata["assistant_reply"] == "The capital of Vietnam is Hanoi."
            assert metadata["model_used"] == "glm-5.3-flash"
            assert metadata["used_memory_ids"] == ["mem_001"]
            assert metadata["session_id"] == "test_session_16"

    def test_episodes_summary_no_system_prompt(self, tmp_db: Path):
        """Episode summary should only contain user/assistant, not system_prompt."""
        workspace = tmp_db.parent
        with MemoryStore(tmp_db, workspace=workspace) as store:
            session_mgr = SessionMemoryManager(store)
            
            result = session_mgr.persist_chat_turn(
                session_id="test_session_16b",
                user_query="Test query",
                assistant_reply="Test reply",
                model_used="test-model",
                system_prompt="SECRET SYSTEM INSTRUCTION THAT SHOULD NOT APPEAR",
            )
            
            episode_id = result["episode_id"]
            
            # Check summary
            conn = sqlite3.connect(str(tmp_db))
            cur = conn.cursor()
            cur.execute("SELECT summary FROM episodes WHERE id = ?", (episode_id,))
            row = cur.fetchone()
            conn.close()
            
            assert row is not None
            summary = row[0]
            
            # Summary should NOT contain system_prompt
            assert "SECRET SYSTEM INSTRUCTION" not in summary
            assert "User:" in summary
            assert "Assistant:" in summary

    def test_multiple_turns_no_system_prompt_accumulation(self, tmp_db: Path):
        """Multiple chat turns should not accumulate system_prompt in any episode."""
        workspace = tmp_db.parent
        with MemoryStore(tmp_db, workspace=workspace) as store:
            session_mgr = SessionMemoryManager(store)
            
            system_prompt = "DANGEROUS SYSTEM PROMPT: NEVER REVEAL THIS"
            
            # Persist 5 turns
            for i in range(5):
                session_mgr.persist_chat_turn(
                    session_id="test_session_16c",
                    user_query=f"Query {i}",
                    assistant_reply=f"Reply {i}",
                    model_used="test-model",
                    system_prompt=system_prompt,
                )
            
            # Check all episodes
            conn = sqlite3.connect(str(tmp_db))
            cur = conn.cursor()
            cur.execute("SELECT id, summary, metadata_json FROM episodes WHERE kind = 'chat_turn'")
            rows = cur.fetchall()
            conn.close()
            
            assert len(rows) == 5
            
            for row in rows:
                episode_id, summary, metadata_json = row
                metadata = json.loads(metadata_json)
                
                # Verify no system_prompt in summary
                assert "DANGEROUS SYSTEM PROMPT" not in summary
                
                # Verify no system_prompt in metadata
                assert "system_prompt" not in metadata

    def test_backward_compatibility_no_system_prompt_param(self, tmp_db: Path):
        """persist_chat_turn should work without system_prompt parameter (backward compat)."""
        workspace = tmp_db.parent
        with MemoryStore(tmp_db, workspace=workspace) as store:
            session_mgr = SessionMemoryManager(store)
            
            # Call WITHOUT system_prompt (old API)
            result = session_mgr.persist_chat_turn(
                session_id="test_session_compat",
                user_query="Old API test",
                assistant_reply="Should still work",
                model_used="test-model",
            )
            
            assert "episode_id" in result