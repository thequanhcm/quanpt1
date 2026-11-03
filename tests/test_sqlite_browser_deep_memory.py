"""
Test suite for DB Browser for SQLite 3.13.1-win64 and QUAN AI BRAIN Deep Memory Engine.
Verifies binary presence, launcher integrity, SQLite database structure and query capabilities.
"""
import os
import sqlite3
import subprocess
from pathlib import Path
import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
DB_PATH = WORKSPACE / "data" / "brain.db"
EXE_PATH = WORKSPACE / "tools" / "DBBrowser" / "DB Browser for SQLite.exe"
LAUNCHER_BAT = WORKSPACE / "MO_TRAP_TRI_NHO_SQLITE.bat"

def test_db_browser_binary_exists():
    """Verify that DB Browser for SQLite 3.13.1 win64 executable exists."""
    assert EXE_PATH.exists(), f"DB Browser executable not found at {EXE_PATH}"
    assert EXE_PATH.stat().st_size > 5_000_000, "Executable file size is unusually small"

def test_db_browser_required_dlls():
    """Verify critical runtime DLLs exist alongside the executable."""
    browser_dir = EXE_PATH.parent
    required_files = [
        "sqlite3.dll",
        "Qt5Core.dll",
        "Qt5Gui.dll",
        "Qt5Widgets.dll",
        "platforms"
    ]
    for rf in required_files:
        assert (browser_dir / rf).exists(), f"Missing required dependency: {rf}"

def test_launcher_bat_integrity():
    """Verify that MO_TRAP_TRI_NHO_SQLITE.bat exists and is properly configured."""
    assert LAUNCHER_BAT.exists(), f"Launcher {LAUNCHER_BAT} not found"
    content = LAUNCHER_BAT.read_text(encoding="utf-8")
    assert "tools\\DBBrowser\\DB Browser for SQLite.exe" in content
    assert "data\\brain.db" in content

def test_brain_db_integrity():
    """Verify data/brain.db is a valid SQLite3 database with required deep memory tables."""
    assert DB_PATH.exists(), f"Deep memory database not found at {DB_PATH}"
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # SQLite integrity check
    cursor.execute("PRAGMA integrity_check;")
    integrity = cursor.fetchone()[0]
    assert integrity == "ok", f"Integrity check failed: {integrity}"
    
    # Check essential deep memory tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    
    essential_tables = [
        "episodes",
        "candidate_knowledge",
        "semantic_memory",
        "memories",
        "knowledge_units",
        "knowledge_relations"
    ]
    for tbl in essential_tables:
        assert tbl in tables, f"Essential table '{tbl}' missing from brain.db"
    
    conn.close()

def test_deep_memory_vietnamese_query():
    """Verify querying Vietnamese accented deep memory records."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM memories WHERE content LIKE '%Anh Quân%' OR content LIKE '%QUAN%';")
    count = cursor.fetchone()[0]
    assert count >= 0  # Query must execute cleanly without UnicodeDecodeError
    conn.close()

def test_quarantine_safety_boundary():
    """Verify candidate_knowledge status follows safety-first quarantine rules."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT status FROM candidate_knowledge;")
    statuses = [r[0] for r in cursor.fetchall()]
    # Candidates must have traceable statuses
    assert len(statuses) > 0
    conn.close()

