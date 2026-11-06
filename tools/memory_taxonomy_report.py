#!/usr/bin/env python
"""V7 SUPER MEMORY V2 — Coverage Report per 8 lớp M1–M8 (G2 / WP1).

READ-ONLY: chỉ mở brain.db + tasks.db bằng URI mode=ro, 0 byte ghi vào
production (bằng chứng: test test_memory_taxonomy.py::test_report_is_readonly).
Output: reports/MEMORY_TAXONOMY_LATEST.md + stdout JSON tóm tắt.

Fail-honest: DB mất/không mở được → báo lỗi, KHÔNG tự bịa số liệu.
"""
from __future__ import annotations

import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from quan_ai_brain.memory.taxonomy import (  # noqa: E402
    MemoryCategory,
    map_episode_kind,
    map_knowledge_type,
    map_memory_type,
    map_task_status,
)

BRAIN_DB = BASE_DIR / "data" / "brain.db"
TASKS_DB = BASE_DIR / "data" / "tasks.db"
REPORT_OUT = BASE_DIR / "reports" / "MEMORY_TAXONOMY_LATEST.md"

LAYER_LABELS = {
    MemoryCategory.M1_EPISODIC: "M1 EPISODIC — Sự kiện/trao đổi",
    MemoryCategory.M2_SEMANTIC: "M2 SEMANTIC — Tri thức đã xác minh",
    MemoryCategory.M3_PROCEDURAL: "M3 PROCEDURAL — Quy trình/SOP",
    MemoryCategory.M4_PREFERENCE: "M4 PREFERENCE — Ưu tiên owner",
    MemoryCategory.M5_EXPERIENCE: "M5 EXPERIENCE — Bài học kinh nghiệm",
    MemoryCategory.M6_EMOTIONAL: "M6 EMOTIONAL — Cảm xúc/xã hội",
    MemoryCategory.M7_TASK_STATE: "M7 TASK/STATE — Trạng thái nhiệm vụ",
    MemoryCategory.M8_REFLECTIVE: "M8 REFLECTIVE — Phản tư/metacognitive",
    MemoryCategory.UNMAPPED: "UNMAPPED — giá trị lạ (fail-honest)",
}


def _ro_connect(db: Path) -> sqlite3.Connection:
    """Kết nối chỉ-đọc (mode=ro) — không thể ghi kể cả vô tình."""
    return sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)


def collect(brain_db: Path = BRAIN_DB, tasks_db: Path = TASKS_DB) -> dict:
    """Đếm items per lớp M1–M8 từ các nguồn thật (read-only)."""
    stats: dict[str, Counter] = {c.value: Counter() for c in MemoryCategory}
    if not brain_db.exists():
        raise FileNotFoundError(f"brain.db không tồn tại: {brain_db}")

    conn = _ro_connect(brain_db)
    try:
        # memories.memory_type → taxonomy
        for mt, n in conn.execute(
            "SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type"
        ):
            cat = map_memory_type(mt)
            stats[cat.value]["memories"] += n
        # knowledge_units.knowledge_type (Deep Memory V9)
        tables = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "knowledge_units" in tables:
            kt_col = next(
                (r[1] for r in conn.execute("PRAGMA table_info(knowledge_units)")
                 if r[1] in ("knowledge_type", "type", "ku_type")),
                None,
            )
            if kt_col:
                for kt, n in conn.execute(
                    f"SELECT {kt_col}, COUNT(*) FROM knowledge_units GROUP BY {kt_col}"
                ):
                    cat = map_knowledge_type(kt)
                    stats[cat.value]["knowledge_units"] += n
        # episodes.kind
        if "episodes" in tables:
            for kind, n in conn.execute(
                "SELECT kind, COUNT(*) FROM episodes GROUP BY kind"
            ):
                cat = map_episode_kind(kind)
                stats[cat.value]["episodes"] += n
        # semantic_memory (canonical M2) + candidate_knowledge (quarantine —
        # trạng thái lifecycle, KHÔNG đếm vào lớp nhớ; ghi riêng)
        if "semantic_memory" in tables:
            stats[MemoryCategory.M2_SEMANTIC.value]["semantic_memory"] = (
                conn.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0]
            )
        candidate_total = 0
        if "candidate_knowledge" in tables:
            candidate_total = conn.execute(
                "SELECT COUNT(*) FROM candidate_knowledge"
            ).fetchone()[0]
    finally:
        conn.close()

    # tasks.db durable_tasks → M7
    if tasks_db.exists():
        tconn = _ro_connect(tasks_db)
        try:
            ttables = {
                r[0] for r in tconn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "durable_tasks" in ttables:
                st_col = next(
                    (r[1] for r in tconn.execute("PRAGMA table_info(durable_tasks)")
                     if r[1] in ("status", "state")),
                    None,
                )
                if st_col:
                    for st, n in tconn.execute(
                        f"SELECT {st_col}, COUNT(*) FROM durable_tasks GROUP BY {st_col}"
                    ):
                        cat = map_task_status(st)
                        stats[cat.value]["durable_tasks"] += n
        finally:
            tconn.close()

    return {"stats": stats, "candidate_knowledge_total": candidate_total}


def render_markdown(result: dict) -> str:
    """Render báo cáo markdown — số liệu trung thực, không làm đẹp."""
    stats = result["stats"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# V7 SUPER MEMORY — TAXONOMY COVERAGE REPORT (M1–M8)",
        f"*Sinh: {now} · WP1 G2 · nguồn: brain.db + tasks.db (read-only)*",
        "",
        "| Lớp | memories | knowledge_units | episodes | durable_tasks | Tổng |",
        "|---|---|---|---|---|---|",
    ]
    for cat in MemoryCategory:
        c = stats[cat.value]
        total = sum(c.values())
        lines.append(
            f"| {LAYER_LABELS[cat]} | {c.get('memories', 0)} | "
            f"{c.get('knowledge_units', 0)} | {c.get('episodes', 0)} | "
            f"{c.get('durable_tasks', 0)} | **{total}** |"
        )
    lines += [
        "",
        f"**candidate_knowledge (quarantine — KHÔNG thuộc lớp nhớ, chờ owner duyệt):** "
        f"{result['candidate_knowledge_total']} items",
        "",
        "Ghi chú thiết kế: DECISION map về M1 (kind=decision); CANDIDATE là trạng thái",
        "lifecycle không phải lớp nhớ; UNMAPPED = giá trị lạ chưa có mapping (fail-honest).",
        "Tham chiếu: docs/V7_SUPER_MEMORY_ARCHITECTURE.md §C.2, src/quan_ai_brain/memory/taxonomy.py",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    try:
        # Truyền tường minh (không dùng default arg — mặc định bind lúc def
        # khiến monkeypatch trong test không hiệu lực)
        result = collect(brain_db=BRAIN_DB, tasks_db=TASKS_DB)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    md = render_markdown(result)
    REPORT_OUT.write_text(md, encoding="utf-8")
    # JSON tóm tắt ra stdout
    import json
    print(json.dumps({
        "report": str(REPORT_OUT),
        "layers": {
            LAYER_LABELS[MemoryCategory(k)]: sum(v.values())
            for k, v in result["stats"].items()
        },
        "candidate_knowledge": result["candidate_knowledge_total"],
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
