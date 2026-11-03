#!/usr/bin/env python
"""Activate CLO V1 in production."""
import sys
from pathlib import Path

sys.path.insert(0, 'src')

from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine, LearningMode
from quan_ai_brain.memory.sqlite_store import MemoryStore

workspace = Path(__file__).parent
store = MemoryStore(workspace / "data" / "brain.db", workspace=workspace)

engine = ContinuousLearningEngine(store, workspace=workspace)

# Check current status
status = engine.get_learning_status()
print("Current CLO Status:")
print(f"  Enabled: {status['clo_enabled']}")
print(f"  Stop flag: {status['stop_flag']}")
print(f"  Pause flag: {status['pause_flag']}")
print(f"  Current session: {status['current_session']}")
print()

# Start CLO with default mode
print("Starting Continuous Learning...")
session = engine.start_continuous_learning(
    objectives=[
        "Learn from chat interactions",
        "Learn from task execution",
        "Consolidate memory and experiences"
    ],
    source_manifest={
        "sources": ["chat", "tasks", "memory", "web_search"],
        "activated_at": "2026-10-27T22:50:00+07:00",
        "mode": "default"
    }
)

print(f"✅ CLO ACTIVATED!")
print(f"  Session ID: {session.session_id}")
print(f"  Cycle Number: {session.cycle_number}")
print(f"  Status: {session.status.value}")
print(f"  Objectives: {session.learning_objectives}")
print()

# Verify
final_status = engine.get_learning_status()
print("Final Status:")
print(f"  Enabled: {final_status['clo_enabled']}")
print(f"  Current session: {final_status['current_session']['session_id'] if final_status['current_session'] else None}")
print(f"  Total sessions: {final_status['total_sessions']}")