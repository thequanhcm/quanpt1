"""Nhóm B — Reasoning Accuracy.

B1_anti_circular_rule : rule "nhiều KU cùng gốc 1 nguồn ≠ đa bằng chứng
                        độc lập" (shared_origins) phải có thật trong code V9.
B2_conflict_scan_runs : ConflictDetector V31 query schema CŨ (id/content/
                        lifecycle_status) không khớp knowledge_units V9
                        (knowledge_id/statement/status) → đo ĐÚNG hành vi
                        dead-code trên production, KHÔNG sửa nó (R1).
B3_causal_guard_exists: năng lực causal guard — correlation ≠ causation
                        chưa được kiểm soát tự động (gap đã ghi nhận).
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

from probe_base import Probe, ProbeResult, build_result


class B1AntiCircularRule(Probe):
    probe_id = "B1_anti_circular_rule"
    group = "B_REASONING"
    title = "Chống vòng tròn: shared_origins rule trong code V9"

    def run(self, ctx) -> ProbeResult:
        sys.path.insert(0, str(ctx.src_root))
        from quan_ai_brain.cognition import logical_reasoning as lr

        src = Path(lr.__file__).read_text(encoding="utf-8", errors="ignore")
        # rule nằm ở bước (7)-(8): _support_against trả shared_origins
        has_rule = "_support_against" in src and "shared_origins" in src
        doc_mentions = len(re.findall(r"vòng\s*circular|circular|chống\s*vòng", src, re.I))

        ok = has_rule
        return build_result(
            self,
            "PASS" if ok else "FAIL",
            f"{'Rule anti-circular CÓ' if ok else 'KHÔNG'} trong code V9 "
            f"(_support_against + shared_origins; {doc_mentions} mention circular)",
            f"{Path(lr.__file__).name} — hàm _support_against",
            extras={"has_shared_origins_rule": has_rule, "circular_mentions": doc_mentions},
        )


class B2ConflictScanRuns(Probe):
    probe_id = "B2_conflict_scan_runs"
    group = "B_REASONING"
    title = "ConflictDetector chạy được trên DB thật (schema V9)"

    def run(self, ctx) -> ProbeResult:
        # B1: đọc schema thật từ production qua read-only URI
        conn = sqlite3.connect(
            f"file:{ctx.brain_db.as_posix()}?mode=ro&immutable=0", uri=True)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(knowledge_units)")]
        n_ku = conn.execute("SELECT COUNT(*) FROM knowledge_units").fetchone()[0]
        conn.close()

        # B2: đo hành vi thật của ConflictDetector trên SNAPSHOT COPY
        # (detector tự CREATE TABLE lúc init → không được phép mở production rw)
        from data_access import make_snapshot
        sys.path.insert(0, str(ctx.src_root))
        from quan_ai_brain.memory.conflict_detector import ConflictDetector

        snap = make_snapshot(ctx.brain_db, ctx.tmp_dir, "brain_b2_copy.db")
        import sqlite3 as _sqlite3

        snap_conn = _sqlite3.connect(str(snap))
        detector = ConflictDetector(snap_conn)
        schema_error = None
        try:
            records = detector.detect_all_conflicts()
            outcome, detail = "PASS", f"Scan OK, {len(records)} conflicts trên {n_ku} KU"
        except sqlite3.OperationalError as exc:
            records = []
            schema_error = str(exc)
            outcome = "FAIL"
            detail = (
                "FINDING THẬT: ConflictDetector query schema CŨ "
                "(id/content/lifecycle_status) không khớp knowledge_units V9 "
                "(knowledge_id/statement/status) → dead code trên production DB. "
                "Chỉ tương thích bảng 'memories' cũ."
            )
        old_cols = {"id", "content", "lifecycle_status"} & set(cols)
        new_cols = {"knowledge_id", "statement", "status"} & set(cols)
        snap_conn.close()
        return build_result(
            self,
            outcome,
            detail,
            f"ConflictDetector.detect_all_conflicts(); KU={n_ku}; "
            f"schema cũ khớp: {sorted(old_cols)}; schema V9 có: {sorted(new_cols)}",
            extras={
                "ku_columns": cols,
                "operational_error": schema_error,
                "n_conflicts": len(records),
            },
        )


class B3CausalGuardExists(Probe):
    probe_id = "B3_causal_guard_exists"
    group = "B_REASONING"
    title = "Causal guard: correlation ≠ causation có được kiểm soát?"

    def run(self, ctx) -> ProbeResult:
        sys.path.insert(0, str(ctx.src_root))
        # 1) engine suy luận chính có nhắc causal?
        from quan_ai_brain.cognition import logical_reasoning as lr
        src = Path(lr.__file__).read_text(encoding="utf-8", errors="ignore")
        causal_in_engine = bool(re.search(r"causal|nhân\s*quả", src, re.I))

        # 2) có module causal riêng nhưng có được wire vào reasoning không?
        causal_mod_path = ctx.src_root / "quan_ai_brain" / "memory" / "causal_reasoning.py"
        causal_mod_exists = causal_mod_path.exists()
        wired = False
        if causal_mod_exists:
            mod_src = causal_mod_path.read_text(encoding="utf-8", errors="ignore")
            wired = "CausalGraph" in mod_src  # self-reference chỉ; kiểm tra usage bên ngoài
            usage_hits = 0
            for py in (ctx.src_root / "quan_ai_brain").rglob("*.py"):
                if py.name in ("causal_reasoning.py", "causal_chains.py"):
                    continue
                try:
                    if "CausalGraph" in py.read_text(encoding="utf-8", errors="ignore"):
                        usage_hits += 1
                except OSError:
                    continue
            wired = usage_hits > 0
            causal_mod_exists = True

        engine_reasoning = "logical_reasoning" in str(lr.__file__)
        guarded = causal_in_engine and wired
        return build_result(
            self,
            "PASS" if guarded else "GAP_KNOWN",
            (
                f"Causal guard CHƯA wire vào engine suy luận: "
                f"logical_reasoning.py nhắc causal={causal_in_engine}; "
                f"module causal_reasoning.py tồn tại={causal_mod_exists} nhưng "
                f"usage bên ngoài={'có' if wired else '0 file'} "
                f"(gap #7 đã ghi nhận trong Cognitive Core)."
            ) if not guarded else "Causal guard có thật và được wire.",
            "logical_reasoning.py + quan_ai_brain/memory/causal_reasoning.py",
            extras={
                "causal_in_engine": causal_in_engine,
                "causal_module_exists": causal_mod_exists,
                "wired_into_reasoning": wired,
                "engine_is_v9_reasoning": engine_reasoning,
            },
        )


PROBES = [B1AntiCircularRule, B2ConflictScanRuns, B3CausalGuardExists]
