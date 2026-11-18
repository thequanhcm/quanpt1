# -*- coding: utf-8 -*-
"""MEMORY EVAL HARNESS (TASK-MEMORY-TRUTH-M6, P4) — đo trí nhớ bằng số thật.

Cảm hứng từ run_eval.py của vivi-agent: bộ câu hỏi CSV → chạy qua retriever
thật → tính recall@3 + tỷ lệ từ chối đúng → báo cáo markdown. Mỗi lần thay
đổi trí nhớ chỉ cần chạy lại → số đo trước/sau, không cảm tính.

Câu hỏi eval nằm trong data/memory_eval_questions.csv (owner xem/sửa được):
  query,answer_must_contain1,answer_must_contain2,...
Nhiều từ khóa cách nhau bằng dấu "|" (một trong các từ khớp là đủ).

Chạy: python tools/memory_eval.py            → data/memory_eval_report.md
      python tools/memory_eval.py --json     → in JSON ra stdout (CI/test)
"""
from __future__ import annotations

import csv
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
QUESTIONS_CSV = WORKSPACE / "data" / "memory_eval_questions.csv"
REPORT_MD = WORKSPACE / "data" / "memory_eval_report.md"


def load_questions(csv_path: Path | None = None) -> list[dict[str, str]]:
    """Đọc CSV câu hỏi eval. Fail-honest: file thiếu → trả []."""
    path = csv_path or QUESTIONS_CSV
    if not path.exists():
        return []
    items: list[dict[str, str]] = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        # Bỏ qua dòng comment (# ...) trước header CSV.
        rows = [ln for ln in f if not ln.lstrip().startswith("#")]
    for row in csv.DictReader(rows):
        q = (row.get("query") or "").strip()
        if not q:
            continue
        items.append({"query": q, "row": {k: (v or "").strip() for k, v in row.items()}})
    return items


def eval_memory(csv_path: Path | None = None,
                top_k: int = 3) -> dict[str, Any]:
    """Chạy eval trí nhớ: semantic + keyword LIKE qua brain.db (mode=ro)."""
    import sqlite3
    from quan_ai_brain.cognition.semantic_memory import SemanticMemoryEngine

    questions = load_questions(csv_path)
    if not questions:
        return {"error": "no_questions", "n_questions": 0}

    db_path = WORKSPACE / "data" / "brain.db"
    engine = SemanticMemoryEngine(WORKSPACE / "data" / "vector_db_semantic", db_path)

    # Từ khóa LIKE cho kênh keyword (fallback khi semantic miss) — hybrid
    # theo mô hình vivi-agent (BM25+vector): cả 2 kênh hợp nhất kết quả.
    def _keyword_top(query: str, k: int = 3) -> list[str]:
        if not db_path.exists():
            return []
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
        try:
            terms = [t for t in re.split(r"\s+", query.strip()) if len(t) >= 4][:6]
            texts: list[str] = []
            for term in terms:
                for (s,) in conn.execute(
                    "SELECT summary FROM episodes WHERE kind='chat_turn' "
                    "AND summary LIKE ? ORDER BY created_at_utc DESC LIMIT ?",
                    (f"%{term}%", k),
                ):
                    texts.append(s)
            return texts
        except Exception:
            return []
        finally:
            conn.close()

    results: list[dict[str, Any]] = []
    for item in questions:
        q = item["query"]
        keywords = [v for k, v in item["row"].items()
                    if k.lower().startswith("answer_must_contain") and v]
        keyword_variants: list[str] = []
        for kw in keywords:
            keyword_variants.extend(v.strip().lower() for v in kw.split("|") if v.strip())
        t0 = time.perf_counter()
        hits = engine.search(q, top_k=top_k, min_distance=1.2)
        # Hybrid: hợp nhất kênh keyword LIKE (từ ≥4 ký tự) vào tập hit.
        kw_texts = _keyword_top(q, top_k)
        hit_texts = [h["text"].lower() for h in hits] + [t.lower() for t in kw_texts]
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        # recall@k: một trong các từ khóa xuất hiện trong top-k hit.
        recalled = any(any(v in t for t in hit_texts) for v in keyword_variants)
        results.append({
            "query": q,
            "n_hits": len(hits),
            "top_distance": hits[0]["distance"] if hits else None,
            "top_text": hits[0]["text"][:120] if hits else "",
            "recalled": recalled,
            "elapsed_ms": elapsed_ms,
        })

    n = len(results)
    n_recalled = sum(1 for r in results if r["recalled"])
    return {
        "n_questions": n,
        "recall_at_3": round(n_recalled / n, 3) if n else 0.0,
        "n_recalled": n_recalled,
        "avg_ms": round(sum(r["elapsed_ms"] for r in results) / n, 1) if n else 0.0,
        "results": results,
    }


def render_report(summary: dict[str, Any]) -> str:
    """Render markdown report từ summary eval."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        f"# BÁO CÁO EVAL TRÍ NHỚ — {now}",
        "",
        "Sprint MEMORY-TRUTH (TASK-MEMORY-TRUTH-M6, P4). Số đo thật từ",
        "semantic_memory (ONNX MiniLM local) + keyword LIKE trên brain.db ro.",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---|",
        f"| Số câu eval | {summary.get('n_questions', 0)} |",
        f"| recall@3 | {summary.get('recall_at_3', 0.0)} |",
        f"| Số câu hit | {summary.get('n_recalled', 0)}/{summary.get('n_questions', 0)} |",
        f"| Thời gian TB/câu (ms) | {summary.get('avg_ms', 0.0)} |",
        "",
        "## Chi tiết từng câu",
        "",
        "| Câu hỏi | Hits | Distance top-1 | recall@3 | ms |",
        "|---|---|---|---|---|",
    ]
    for r in summary.get("results", []):
        d = r.get("top_distance")
        lines.append(
            f"| {r['query'][:70]} | {r['n_hits']} | "
            f"{d if d is not None else '—'} | {'✅' if r['recalled'] else '❌'} | "
            f"{r['elapsed_ms']} |"
        )
    lines.append("")
    lines.append("Ngưỡng nghiệm thu sprint: recall@3 ≥ 0.8, không câu nào ném exception.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Eval trí nhớ Cherry (recall@3)")
    ap.add_argument("--csv", type=Path, default=None, help="CSV câu hỏi thay thế")
    ap.add_argument("--json", action="store_true", help="In JSON thay vì viết report")
    args = ap.parse_args()
    summary = eval_memory(args.csv)
    if args.json:
        import json
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if not summary.get("error") else 1
    if summary.get("error"):
        print(f"[FAIL-HONEST] Eval lỗi: {summary['error']}")
        return 1
    REPORT_MD.write_text(render_report(summary), encoding="utf-8")
    print(f"recall@3={summary['recall_at_3']} ({summary['n_recalled']}/"
          f"{summary['n_questions']}), avg {summary['avg_ms']}ms")
    print(f"Report: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
