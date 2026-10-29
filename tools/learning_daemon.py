"""QUAN AI BRAIN Continuous Learning Daemon — Learn from ALL sources continuously.

Usage:
    python tools/learning_daemon.py

This daemon:
1. Ingests ALL documents (docs/, reports/, AGENTS.md)
2. Ingests ALL code documentation (docstrings, comments)
3. Ingests ALL git history (commit messages, diffs)
4. Ingests ALL test results (pytest output, coverage)
5. Ingests ALL configuration files (pyproject.toml, .env.example)
6. Reports quarantine status every cycle (không tự promote — Sprint 7)
7. Survives transient errors (database is locked, file locks) — Sprint 7

Runs continuously in background — learns 24/7.

Sprint 7 (b) governance fix (27/10/2026):
- BỎ auto-approve quarantine (vi phạm "Learning is not deployment" — AGENTS.md).
  Tri thức cách ly chỉ owner duyệt; daemon chỉ đếm + log.
- Vòng lặp chính CHỨNG TỬ lỗi tạm thời: 1 vòng fail = log + thử chu kỳ sau,
  daemon KHÔNG chết im re (nguyên nhân chết 08:09 sáng nay: database is
  locked khi regression chạy song song → traceback → SystemExit).
"""
import json
import os
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# (29/10/2026) pythonw windowless mode: sys.stdout là None dưới pythonw.exe —
# print() sẽ crash service im lặng. Redirect ra log file.
if sys.stdout is None or sys.stderr is None:
    _LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        sys.stdout = open(_LOG_DIR / "learning_daemon_stdout.log", "a", buffering=1, encoding="utf-8", errors="replace")
        sys.stderr = sys.stdout
    except Exception:
        pass
from typing import Any

sys.path.insert(0, "src")

from quan_ai_brain.memory.knowledge_ingestion import KnowledgeIngestionEngine, KnowledgeSource
from quan_ai_brain.memory.sqlite_store import MemoryStore

# Configuration
CONFIG = {
    "workspace": Path(r"E:\AI\QUAN AI BRAIN"),
    "db_path": "data/brain.db",
    "owner_id": "Quanpt1",
    "consolidation_interval": 300,  # 5 minutes
    "crash_log": "logs/learning_daemon_crash.log",
    "sources_to_ingest": [
        "docs/",
        "reports/",
        "AGENTS.md",
        "src/quan_ai_brain/",
        "tests/",
        "tools/",
        "pyproject.toml",
        "README.md",
        "Skill/",
        ".agents/skills/",
    ],
}


def ingest_document(engine: KnowledgeIngestionEngine, file_path: Path, source_type: KnowledgeSource, tags: list[str]) -> int:
    """Ingest a single document."""
    try:
        content = file_path.read_text(encoding="utf-8")
        if len(content.strip()) < 100:
            return 0  # Skip tiny files

        # Extract key facts (simplified for Sprint 5)
        statements = []

        # For markdown: extract headers as facts
        if file_path.suffix == ".md":
            headers = re.findall(r"^#+\s+(.+)$", content, re.MULTILINE)
            statements.extend([h.strip() for h in headers[:10]])  # Top 10 headers

        # For Python: extract docstrings
        elif file_path.suffix == ".py":
            docstrings = re.findall(r'"""(.*?)"""', content, re.DOTALL)
            statements.extend([d.split("\n")[0].strip() for d in docstrings[:5]])  # First line of each docstring

        # For config files: extract key-value pairs
        elif file_path.name == "pyproject.toml":
            lines = content.split("\n")[:20]
            statements.extend([l.strip() for l in lines if "=" in l and not l.startswith("#")])

        if not statements:
            # Fallback: use first 500 chars
            statements = [content[:500].strip() + "..."]

        ingested = 0
        for stmt in statements[:5]:  # Max 5 facts per file
            engine.ingest(
                content=stmt,
                source_type=source_type,
                source_ref=str(file_path.relative_to(CONFIG["workspace"])),
                source_version="continuous_learning_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
                tags=tags,
                skip_duplicates=True,  # Sprint 7 (b): idempotent — chặn trùng
            )
            ingested += 1

        return ingested
    except Exception as e:
        print(f"  ⚠️  Failed {file_path.name}: {e}")
        return 0


def ingest_git_history(engine: KnowledgeIngestionEngine) -> int:
    """Ingest git commit messages as learning data."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-50"],
            cwd=CONFIG["workspace"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return 0

        commits = result.stdout.strip().split("\n")
        ingested = 0
        for commit in commits[:20]:  # Last 20 commits
            # Extract commit type and message
            match = re.match(r"^([a-f0-9]+)\s+(feat|fix|chore|docs|perf|refactor):?\s*(.+)$", commit)
            if match:
                commit_hash, commit_type, message = match.groups()
                stmt = f"[{commit_type.upper()}] {message.strip()} (commit {commit_hash[:7]})"
                engine.ingest(
                    content=stmt,
                    source_type=KnowledgeSource.PROJECT_DOCS,  # Sprint 7: CODE_REVIEW không tồn tại trong enum
                    source_ref=f"git:{commit_hash[:7]}",
                    source_version=commit_hash,
                    tags=["git", "commit", commit_type],
                    skip_duplicates=True,  # Sprint 7 (b): idempotent
                )
                ingested += 1

        return ingested
    except Exception as e:
        print(f"  ⚠️  Git ingestion failed: {e}")
        return 0


def ingest_test_results(engine: KnowledgeIngestionEngine) -> int:
    """Ingest recent test results."""
    try:
        result = subprocess.run(
            [".\\.venv\\Scripts\\python.exe", "-m", "pytest", "-q", "tests", "--tb=no"],
            cwd=CONFIG["workspace"],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Parse pytest output
        output = result.stdout
        match = re.search(r"(\d+)\s+passed,?\s*(\d*)\s+skipped,?\s*(\d*)\s+failed", output)
        if match:
            passed, skipped, failed = match.groups()
            stmt = f"Test suite: {passed} passed, {skipped or 0} skipped, {failed or 0} failed"
            engine.ingest(
                content=stmt,
                source_type=KnowledgeSource.TEST_EVIDENCE,
                source_ref="pytest:latest",
                source_version=datetime.now(timezone.utc).isoformat(),
                tags=["testing", "pytest", "quality"],
                skip_duplicates=False,  # kết quả test MỚI là tri thức mới (có version)
            )
            return 1

        return 0
    except Exception as e:
        print(f"  ⚠️  Test ingestion failed: {e}")
        return 0


def consolidate_memories(engine: KnowledgeIngestionEngine, store: MemoryStore) -> int:
    """Sprint 7 governance fix: KHÔNG tự duyệt tri thức quarantine nữa.

    Nguyên tắc AGENTS.md "Learning is not deployment": tri thức cách ly chỉ
    owner (quanpt1) mới được promote. Daemon chỉ ĐẾM + log để báo cáo, không
    gọi approve_knowledge dưới bất kỳ hình thức nào.
    """
    try:
        quarantined_count = store._connection.execute(
            "SELECT COUNT(*) FROM candidate_knowledge WHERE status='quarantined'"
        ).fetchone()[0]
        print(
            f"   🔒 Quarantine: {quarantined_count} items chờ owner duyệt "
            "(daemon không tự promote — V3 governance)"
        )
        return 0
    except Exception as e:
        print(f"  ⚠️  Consolidation check failed: {e}")
        return 0


def _log_crash(fatal: BaseException) -> None:
    """Ghi crash vào log file để post-reboot verify / owner kiểm tra được."""
    try:
        log_path = CONFIG["workspace"] / CONFIG["crash_log"]
        log_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[{ts}] FATAL: {fatal}\n")
            fh.write("".join(traceback.format_exception(fatal)) + "\n")
    except Exception:
        pass  # Không bao giờ chết vì logging


def main() -> int:
    """Main learning daemon loop."""
    print("=" * 70)
    print("QUAN AI BRAIN Continuous Learning Daemon — Starting")
    print("=" * 70)
    print(f"Workspace: {CONFIG['workspace']}")
    print(f"Database: {CONFIG['db_path']}")
    print(f"Cycle interval: {CONFIG['consolidation_interval']}s")
    print("Governance: KHÔNG tự promote quarantine (Sprint 7)")
    print("=" * 70)

    store = MemoryStore(CONFIG["db_path"])
    engine = KnowledgeIngestionEngine(store, owner_id=CONFIG["owner_id"])

    iteration = 0
    while True:
        iteration += 1
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        print(f"\n[{timestamp}] Iteration {iteration} — Starting learning cycle...")

        # Sprint 7 (b): mỗi vòng CHỨNG TỬ lỗi tạm thời (database is locked,
        # file locks khi regression chạy song song). Lỗi vòng → log + đợi
        # chu kỳ sau, KHÔNG làm daemon chết. Chỉ KeyboardInterrupt được thoát.
        try:
            total_ingested = 0

            # 1. Ingest documents
            print("\n1. Ingesting documents...")
            for source_path in CONFIG["sources_to_ingest"]:
                full_path = CONFIG["workspace"] / source_path
                if not full_path.exists():
                    continue

                if full_path.is_file():
                    # Determine source type
                    if "docs/" in str(full_path):
                        source_type = KnowledgeSource.PROJECT_DOCS
                        tags = ["documentation"]
                    elif "reports/" in str(full_path):
                        source_type = KnowledgeSource.TEST_EVIDENCE
                        tags = ["report", "evidence"]
                    elif full_path.suffix == ".py":
                        source_type = KnowledgeSource.TECHNICAL_SPEC
                        tags = ["code", "documentation"]
                    else:
                        source_type = KnowledgeSource.PROJECT_DOCS
                        tags = ["config", "metadata"]

                    ingested = ingest_document(engine, full_path, source_type, tags)
                    total_ingested += ingested
                    if ingested > 0:
                        print(f"   ✅ {full_path.name}: {ingested} facts")

                elif full_path.is_dir():
                    # Ingest all .md and .py files in directory (recursive)
                    for ext in ["*.md", "*.py"]:
                        for file_path in full_path.rglob(ext):
                            p_str = str(file_path)
                            if any(ignored in p_str for ignored in ("node_modules", ".venv", ".git", "__pycache__")):
                                continue

                            if ext == "*.md":
                                source_type = KnowledgeSource.PROJECT_DOCS
                                tags = ["documentation", file_path.parent.name]
                            else:
                                source_type = KnowledgeSource.TECHNICAL_SPEC
                                tags = ["code", file_path.parent.name]

                            ingested = ingest_document(engine, file_path, source_type, tags)
                            total_ingested += ingested

            print(f"   📊 Documents ingested: {total_ingested} facts")

            # 2. Ingest git history
            print("\n2. Ingesting git history...")
            git_facts = ingest_git_history(engine)
            total_ingested += git_facts
            print(f"   ✅ Git commits: {git_facts} facts")

            # 3. Ingest test results
            print("\n3. Ingesting test results...")
            test_facts = ingest_test_results(engine)
            total_ingested += test_facts
            print(f"   ✅ Test results: {test_facts} facts")

            # 4. Quarantine status (KHÔNG auto-promote — Sprint 7)
            print("\n4. Consolidating memories...")
            consolidated = consolidate_memories(engine, store)
            print(f"   ✅ Consolidated: {consolidated} items")

            # 5. Summary
            elapsed = time.time() - start_time

            # Get current stats
            total_knowledge = store._connection.execute(
                "SELECT COUNT(*) FROM candidate_knowledge"
            ).fetchone()[0]
            approved = store._connection.execute(
                "SELECT COUNT(*) FROM candidate_knowledge WHERE status='approved'"
            ).fetchone()[0]
            semantic = store._connection.execute(
                "SELECT COUNT(*) FROM semantic_memory"
            ).fetchone()[0]

            print(f"\n{'=' * 70}")
            print(f"✅ Learning cycle complete: {total_ingested} facts ingested, {consolidated} consolidated")
            print(f"📊 Total knowledge: {total_knowledge} (approved: {approved}, semantic: {semantic})")
            print(f"⏱️  Duration: {elapsed:.1f}s")
            print(f"{'=' * 70}")

            # Wait for next cycle
            sleep_time = max(0, CONFIG["consolidation_interval"] - elapsed)
            if sleep_time > 0:
                print(f"\n⏳ Waiting {sleep_time:.0f}s for next cycle... (Ctrl+C to stop)")
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            raise
        except Exception as cycle_error:
            # Lỗi tạm thời (database is locked, file lock...) → log + thử lại
            elapsed = time.time() - start_time
            ts = datetime.now(timezone.utc).isoformat()
            print(f"\n[{ts}] ⚠️  Cycle {iteration} FAILED (không chết): {cycle_error}")
            _log_crash(cycle_error)
            sleep_time = max(5, CONFIG["consolidation_interval"] - elapsed)
            print(f"⏳ Retry sau {sleep_time:.0f}s...")
            time.sleep(sleep_time)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Learning daemon stopped by user")
        raise SystemExit(0)
