#!/usr/bin/env python
"""CHERRY INTELLIGENCE EVALUATION ENGINE (CIEE) — Baseline Runner V1.

Chạy 14 probes trên 8 nhóm năng lực (A-H) chống lại hệ thống CHERRY thật
(production DB, code V9) ở chế độ READ-ONLY tuyệt đối (R1).

Cách chạy (Windows, git-bash):
    E:/BRAIN/.venv/Scripts/python.exe E:/BRAIN/tools/ciee/ciee_runner.py

Tùy chọn:
    --chroma          : bật probe Chroma (mặc định NOT RUN — đọc vector DB
                        55MB tốn RAM; bật khi cần đo nhóm knowledge_db)
    --no-md           : không ghi REPORT.md (chỉ results.json + manifest)
    --no-baseline-append : KHÔNG append section Baseline V1 vào
                        CHERRY_INTELLIGENCE_TEST_REPORT.md

Exit code (tổng hợp):
    0 = mọi probe PASS
    1 = có FAIL
    2 = có PARTIAL (không FAIL)
    3 = có GAP_KNOWN (không FAIL/PARTIAL)
    4 = có ERROR/NOT_RUN (lỗi hạ tầng runner / probe bị bỏ qua)
    5 = lỗi môi trường (DB mất, read-only assert fail...) — suite không chạy

Output:
    reports/intelligence_maturity/ciee/runs/<UTC timestamp>/
        results.json | REPORT.md | manifest.txt

Cam kết R1: KHÔNG ghi vào bất kỳ DB production nào. Chi tiết README.md.
"""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ---- đảm bảo import được khi chạy từ bất kỳ cwd nào -----------------------
TOOLS_CIEE = Path(__file__).resolve().parent
if str(TOOLS_CIEE) not in sys.path:
    sys.path.insert(0, str(TOOLS_CIEE))
SRC_ROOT = Path("E:/BRAIN/src")
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import probe_base  # noqa: E402
from probe_base import GROUPS, OUTCOMES, ProbeContext  # noqa: E402
import data_access  # noqa: E402
import report_writer  # noqa: E402

VENV_PY = Path("E:/BRAIN/.venv/Scripts/python.exe")
TEST_REPORT_MD = (report_writer.REPORTS_ROOT /
                  "CHERRY_INTELLIGENCE_TEST_REPORT.md")

# Thứ tự nhóm + probes (14 chuẩn, khớp baseline V0)
PROBE_MODULES = [
    "probes.group_a_problem_solving",
    "probes.group_b_reasoning",
    "probes.group_c_epistemic",
    "probes.group_d_critical",
    "probes.group_e_metacognition",
    "probes.group_f_adaptive",
    "probes.group_g_decision",
    "probes.group_h_learning",
]

CHROMA_PROBE_ID = "C4_chroma_vector_store"  # tùy chọn, mặc định NOT RUN


def load_probes():
    """Nạp mọi probe class từ các module nhóm (theo thứ tự khai báo)."""
    probes = []
    for mod_name in PROBE_MODULES:
        mod = importlib.import_module(mod_name)
        for cls in getattr(mod, "PROBES", []):
            probes.append(cls())
    return probes


def build_context(run_id: str) -> ProbeContext:
    run_dir = report_writer.CIEE_ROOT / "runs" / run_id
    tmp_dir = data_access.make_run_tmp_dir(run_id)

    # snapshot copies — cho module tự quản schema (CREATE TABLE lúc init)
    brain_copy = data_access.make_snapshot(data_access.BRAIN_DB, tmp_dir,
                                           "brain_ciee_copy.db")
    tasks_copy = data_access.make_snapshot(data_access.TASKS_DB, tmp_dir,
                                           "tasks_ciee_copy.db")
    gov_copy = data_access.make_snapshot(data_access.GOVERNANCE_DB, tmp_dir,
                                         "governance_ciee_copy.db")

    return ProbeContext(
        run_id=run_id,
        run_dir=run_dir,
        tmp_dir=tmp_dir,
        src_root=SRC_ROOT,
        workspace=data_access.WORKSPACE,
        brain_db=data_access.BRAIN_DB,
        tasks_db=data_access.TASKS_DB,
        governance_db=data_access.GOVERNANCE_DB,
        knowledge_db=data_access.KNOWLEDGE_DB,
        brain_copy=brain_copy,
        tasks_copy=tasks_copy,
        gov_copy=gov_copy,
    )


def probe_chroma(ctx: ProbeContext) -> dict:
    """Probe tùy chọn Chroma — đọc metadata collection, KHÔNG query embedding
    (tránh tải model nặng). Bị tắt mặc định: ghi NOT_RUN + lý do."""
    result = {
        "probe_id": CHROMA_PROBE_ID,
        "group": "C_EPISTEMIC",
        "group_label": GROUPS["C_EPISTEMIC"],
        "title": "Chroma vector store đọc được metadata (tùy chọn)",
        "outcome": "NOT_RUN",
        "detail": "Bỏ qua theo mặc định: chroma startup tải embedding stack nặng (~RAM), "
                  "không thuộc 14 probes chuẩn của baseline. Chạy lại với --chroma để bật.",
        "evidence": f"knowledge_db tại {ctx.knowledge_db}",
        "duration_s": 0.0,
        "started_at_utc": probe_base.utc_now_iso(),
    }
    try:
        import chromadb  # noqa: F401

        client = chromadb.PersistentClient(path=str(ctx.knowledge_db))
        cols = client.list_collections()
        n_vec = 0
        for c in cols:
            try:
                n_vec += c.count()
            except Exception:  # noqa: BLE001
                pass
        result.update({
            "outcome": "PASS",
            "detail": f"{len(cols)} collections, ~{n_vec} vectors đọc được "
                      f"(chỉ metadata, không query embedding)",
            "evidence": f"chromadb.PersistentClient('{ctx.knowledge_db}')",
            "duration_s": 0.5,
            "extras": {"collections": len(cols), "vectors": n_vec},
        })
    except Exception as exc:  # noqa: BLE001
        result.update({
            "outcome": "NOT_RUN",
            "detail": f"chromadb không dùng được: {type(exc).__name__}: {exc}",
        })
    return result


def summarize_exit_code(results: list[dict]) -> int:
    outcomes = {r["outcome"] for r in results}
    if "ERROR" in outcomes:
        return 4
    if "FAIL" in outcomes:
        return 1
    if "PARTIAL" in outcomes:
        return 2
    if "GAP_KNOWN" in outcomes:
        return 3
    if "NOT_RUN" in outcomes:
        return 4
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CIEE Baseline Runner V1")
    parser.add_argument("--chroma", action="store_true",
                        help="bật probe Chroma vector store (mặc định NOT RUN)")
    parser.add_argument("--no-md", action="store_true",
                        help="không ghi REPORT.md")
    parser.add_argument("--no-baseline-append", action="store_true",
                        help="không append section Baseline V1 vào test report")
    args = parser.parse_args()

    started_dt = datetime.now(timezone.utc)
    run_id = started_dt.strftime("%Y%m%dT%H%M%SZ")

    print("=" * 72)
    print("CHERRY INTELLIGENCE EVALUATION ENGINE (CIEE) — Baseline V1")
    print(f"run_id = {run_id}")
    print("=" * 72)

    # ---- kiểm tra môi trường trước khi chạy ------------------------------
    missing = [str(p) for p in (data_access.BRAIN_DB, data_access.TASKS_DB,
                                data_access.GOVERNANCE_DB) if not p.exists()]
    if missing:
        print(f"LỖI MÔI TRƯỜNG: thiếu DB production: {missing}")
        return 5

    data_access.install_snapshot_guard()
    ro_assert = data_access.assert_readonly()
    print(f"[R1] read-only assert: {ro_assert}")
    if not all(ro_assert.values()):
        print("LỖI MÔI TRƯỜNG: không mở được DB production ở chế độ read-only.")
        return 5

    ctx = build_context(run_id)
    print(f"[R1] snapshots (temp): {ctx.tmp_dir}")

    probes = load_probes()
    print(f"Đã nạp {len(probes)} probes / {len(PROBE_MODULES)} nhóm\n")

    results: list[dict] = []
    for probe in probes:
        print(f"--- [{probe.group}] {probe.probe_id}")
        res = probe.execute(ctx)
        results.append(res.to_dict())
        icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "PARTIAL": "[PART]",
                "GAP_KNOWN": "[GAP ]", "NOT_RUN": "[SKIP]",
                "ERROR": "[ERR ]"}.get(res.outcome, "[?????]")
        print(f"    {icon} {res.outcome:9s} ({res.duration_s:.2f}s) "
              f"{res.detail[:110]}")

    if args.chroma:
        print(f"--- [C_EPISTEMIC] {CHROMA_PROBE_ID} (tùy chọn --chroma)")
        chroma_result = probe_chroma(ctx)
        results.append(chroma_result)
        print(f"    {chroma_result['outcome']}: {chroma_result['detail'][:100]}")
    else:
        results.append(probe_chroma.__wrapped__(ctx) if hasattr(
            probe_chroma, "__wrapped__") else _not_run_chroma(ctx))

    finished_dt = datetime.now(timezone.utc)
    meta = {
        "run_id": run_id,
        "started_at_utc": started_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at_utc": finished_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "readonly_assert": ro_assert,
        "chroma_status": next((r["outcome"] for r in results
                               if r["probe_id"] == CHROMA_PROBE_ID), "NOT RUN"),
        "chroma_reason": ("Tắt mặc định (chi phí RAM); dùng --chroma để bật."
                          if not args.chroma else ""),
    }

    paths = report_writer.write_all(run_id, ctx.run_dir, results, meta)
    if args.no_md:
        md_path = ctx.run_dir / "REPORT.md"
        if md_path.exists():
            md_path.unlink()
        paths.pop("REPORT.md", None)

    counts = report_writer.count_outcomes(results)
    exit_code = summarize_exit_code(results)

    print("\n" + "=" * 72)
    print("TỔNG KẾT")
    print(f"  {counts.get('PASS', 0)} PASS / {counts.get('FAIL', 0)} FAIL / "
          f"{counts.get('PARTIAL', 0)} PARTIAL / {counts.get('GAP_KNOWN', 0)} "
          f"GAP_KNOWN / {counts.get('NOT_RUN', 0)} NOT_RUN / "
          f"{counts.get('ERROR', 0)} ERROR  (tổng {len(results)} probes)")
    print(f"  Baseline V0: 9 PASS / 3 FAIL / 2 PARTIAL")
    print(f"  Output: {ctx.run_dir}")
    for name, p in paths.items():
        print(f"    - {name}: {p}")
    print(f"  Exit code: {exit_code}")

    # ---- APPEND Baseline V1 section vào test report ----------------------
    if not args.no_baseline_append:
        try:
            section_path = report_writer.append_baseline_v1_section(
                TEST_REPORT_MD, run_id, ctx.run_dir, results, counts,
                meta["chroma_status"])
            print(f"  Đã append 'Baseline V1' vào: {TEST_REPORT_MD}")
        except Exception as exc:  # noqa: BLE001
            print(f"  CẢNH BÁO: append baseline section lỗi: {exc}")
            traceback.print_exc()

    # ---- dọn snapshot tạm (giữ run_dir) ----------------------------------
    # Lưu ý: os.remove đã bị guard chặn cho snapshot (R1). Để dọn, tạm khôi
    # phục os.remove gốc — snapshot ở đây là bản copy của runner, KHÔNG phải
    # production DB.
    try:
        import os as _os

        if hasattr(data_access, "_REAL_REMOVE"):
            _os.remove = data_access._REAL_REMOVE
        shutil.rmtree(ctx.tmp_dir, ignore_errors=True)
        print(f"  Đã dọn snapshot tạm: {ctx.tmp_dir}")
    except Exception:  # noqa: BLE001
        print(f"  Snapshot tạm không dọn được (an toàn — bỏ qua): {ctx.tmp_dir}")

    return exit_code


def _not_run_chroma(ctx: ProbeContext) -> dict:
    return {
        "probe_id": CHROMA_PROBE_ID,
        "group": "C_EPISTEMIC",
        "group_label": GROUPS["C_EPISTEMIC"],
        "title": "Chroma vector store đọc được metadata (tùy chọn)",
        "outcome": "NOT_RUN",
        "detail": ("Bỏ qua theo mặc định: chroma startup tải embedding stack "
                   "nặng (~RAM), không thuộc 14 probes chuẩn của baseline. "
                   "Chạy lại với --chroma để bật."),
        "evidence": f"knowledge_db tại {ctx.knowledge_db}",
        "duration_s": 0.0,
        "started_at_utc": probe_base.utc_now_iso(),
    }


if __name__ == "__main__":
    sys.exit(main())
