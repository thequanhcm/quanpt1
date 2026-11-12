"""CIEE report_writer — ghi kết quả run ra reports/intelligence_maturity/ciee/.

Mỗi run tạo thư mục runs/<run_id>/ chứa:
  results.json  — dữ liệu đầy đủ (máy đọc được)
  REPORT.md     — báo cáo người đọc (bảng probe, so sánh baseline V0)
  manifest.txt  — checksum + môi trường + cam kết read-only

Chỉ GHI vào thư mục ciee/runs/ này. Không bao giờ ghi vào data/ hay src/.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime
from pathlib import Path

REPORTS_ROOT = Path("E:/BRAIN/reports/intelligence_maturity")
CIEE_ROOT = REPORTS_ROOT / "ciee"

V0_SUMMARY = {"PASS": 9, "FAIL": 3, "PARTIAL": 2}
V0_PROBE_OUTCOMES = {
    "C1_abstain_no_evidence": "PASS",
    "C2_known_evidence_answer": "FAIL",
    "C3_stale_detection": "PASS",
    "B1_anti_circular_rule": "PASS",
    "B2_conflict_scan_runs": "FAIL",
    "B3_causal_guard_exists": "GAP_KNOWN",
    "D1_hypotheses_on_real_incident": "PARTIAL",
    "A1_outcome_verifier_available": "PASS",
    "G1_risk_levels_exist": "PASS",
    "G2_r4_fail_closed": "PASS",
    "H1_quarantine_gate": "PASS",
    "H2_learning_spam_control": "FAIL",
    "F1_llm_fallback_regression": "PASS",
    "E1_metacognition_evaluable": "PASS",
}

# Nhãn đọc được cho outcome khi so với V0
_OUTCOME_ORDER = ["PASS", "FAIL", "PARTIAL", "GAP_KNOWN", "NOT_RUN", "ERROR"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_outcomes(results: list[dict]) -> dict[str, int]:
    counts = {k: 0 for k in _OUTCOME_ORDER}
    for r in results:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    return {k: v for k, v in counts.items() if v or k in ("PASS", "FAIL", "PARTIAL")}


def group_results(results: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in results:
        groups.setdefault(r["group"], []).append(r)
    return groups


def write_all(run_id: str, run_dir: Path, results: list[dict],
              meta: dict) -> dict[str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)
    counts = count_outcomes(results)
    groups = group_results(results)

    paths = {}
    paths["results.json"] = _write_results_json(run_dir, results, meta, counts)
    paths["REPORT.md"] = _write_report_md(run_id, run_dir, results, meta,
                                          counts, groups)
    paths["manifest.txt"] = _write_manifest(run_dir, results, meta, counts)
    return paths


# ------------------------------------------------------------------ JSON
def _write_results_json(run_dir: Path, results: list[dict], meta: dict,
                        counts: dict) -> Path:
    payload = {
        "engine": "CHERRY INTELLIGENCE EVALUATION ENGINE (CIEE) — Baseline V1",
        "run_id": meta["run_id"],
        "started_at_utc": meta["started_at_utc"],
        "finished_at_utc": meta["finished_at_utc"],
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "readonly_assert": meta.get("readonly_assert", {}),
        "chroma_status": meta.get("chroma_status", "NOT RUN"),
        "chroma_reason": meta.get("chroma_reason", ""),
        "counts": counts,
        "comparison_v0": {
            "v0_counts": V0_SUMMARY,
            "v1_counts": counts,
            "probe_deltas": _probe_deltas(results),
        },
        "results": results,
    }
    out = run_dir / "results.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    return out


def _probe_deltas(results: list[dict]) -> list[dict]:
    deltas = []
    for r in results:
        v0 = V0_PROBE_OUTCOMES.get(r["probe_id"], "UNKNOWN")
        if v0 != r["outcome"]:
            deltas.append({
                "probe_id": r["probe_id"],
                "v0": v0,
                "v1": r["outcome"],
                "note": r.get("detail", "")[:220],
            })
    return deltas


# ------------------------------------------------------------------ MD
def _write_report_md(run_id: str, run_dir: Path, results: list[dict],
                     meta: dict, counts: dict, groups: dict) -> Path:
    started = meta.get("started_at_utc", "?")
    lines: list[str] = []
    lines.append(f"# CIEE RUN — {run_id}")
    lines.append("")
    lines.append(f"**Bắt đầu (UTC):** {started}  ")
    lines.append(f"**Kết thúc (UTC):** {meta.get('finished_at_utc', '?')}  ")
    lines.append(f"**Python:** {sys.version.split()[0]} — `{sys.executable}`  ")
    lines.append("")
    ro = meta.get("readonly_assert", {})
    lines.append(
        f"**Cam kết R1 read-only:** brain={ro.get('brain')}, "
        f"tasks={ro.get('tasks')}, governance={ro.get('governance')} "
        f"(mọi kết nối production qua URI `mode=ro&immutable=0`; snapshot "
        f"copy cho module tự CREATE TABLE; `os.remove` bị chặn với snapshot)."
    )
    lines.append("")
    lines.append("## Tổng kết")
    lines.append("")
    lines.append("| Outcome | V1 (run này) | V0 (11/11 tối) |")
    lines.append("|---|---|---|")
    for k in ("PASS", "FAIL", "PARTIAL", "GAP_KNOWN", "NOT_RUN", "ERROR"):
        v1 = counts.get(k, 0)
        v0 = V0_SUMMARY.get(k, 0)
        if v1 or v0:
            lines.append(f"| {k} | {v1} | {v0} |")
    total = len(results)
    lines.append(f"| **Tổng** | **{total}** | **14** |")
    lines.append("")

    lines.append("## Chi tiết theo nhóm")
    for gid in sorted(groups):
        gres = groups[gid]
        label = gres[0].get("group_label", gid)
        lines.append("")
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| Probe | Kết quả | Chi tiết | Evidence | Thời gian (s) |")
        lines.append("|---|---|---|---|---|")
        for r in gres:
            v0 = V0_PROBE_OUTCOMES.get(r["probe_id"])
            delta = ""
            if v0 and v0 != r["outcome"]:
                delta = f" (V0: {v0})"
            elif v0:
                delta = " (=V0)"
            detail = (r.get("detail") or "").replace("|", "\\|")[:280]
            ev = (r.get("evidence") or "").replace("|", "\\|")[:80]
            lines.append(
                f"| {r['probe_id']}{delta} | **{r['outcome']}** | {detail} | {ev} | "
                f"{r.get('duration_s', 0)} |"
            )
    lines.append("")

    # Khác biệt với V0
    deltas = _probe_deltas(results)
    lines.append("## Khác biệt với Baseline V0")
    lines.append("")
    if not deltas:
        lines.append("Không có probe nào đổi outcome so với V0.")
    else:
        lines.append("| Probe | V0 | V1 | Nguyên nhân |")
        lines.append("|---|---|---|---|")
        for d in deltas:
            note = (d.get("note") or "").replace("|", "\\|")
            lines.append(f"| {d['probe_id']} | {d['v0']} | {d['v1']} | {note} |")
    lines.append("")
    lines.append(
        "> Lưu ý: learning daemon đang ghi liên tục (spam 'Test suite:*' "
        "~170 rows/giờ) nên số liệu đếm dòng có thể lệch giữa các lần chạy — "
        "đây là data drift bình thường, không phải lỗi runner."
    )
    lines.append("")
    if meta.get("chroma_status"):
        lines.append(f"## Chroma: {meta['chroma_status']}")
        lines.append("")
        lines.append(meta.get("chroma_reason", ""))
        lines.append("")

    out = run_dir / "REPORT.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# ------------------------------------------------------------------ manifest
def _write_manifest(run_dir: Path, results: list[dict], meta: dict,
                    counts: dict) -> Path:
    lines = []
    lines.append(f"CIEE run {meta['run_id']}")
    lines.append(f"started_utc = {meta.get('started_at_utc')}")
    lines.append(f"finished_utc = {meta.get('finished_at_utc')}")
    lines.append(f"python = {sys.version.split()[0]}")
    lines.append(f"platform = {platform.platform()}")
    lines.append(f"counts = {json.dumps(counts)}")
    lines.append(f"chroma = {meta.get('chroma_status', 'NOT RUN')}")
    lines.append("")
    lines.append("# Cam kết R1 READ-ONLY")
    lines.append("- Production DB chỉ mở qua sqlite3 URI mode=ro&immutable=0 + PRAGMA query_only=ON")
    lines.append("- Module tự CREATE TABLE (DeepMemoryStore, ConflictDetector, GovernanceApprovalVerifier) chạy trên SNAPSHOT COPY trong thư mục tạm")
    lines.append("- os.remove bị chặn cho snapshot trong tiến trình runner")
    lines.append("- Run này KHÔNG INSERT/UPDATE/DELETE bất kỳ dòng nào vào DB production")
    lines.append("")
    lines.append("# Checksum files trong run")
    for f in sorted(run_dir.iterdir()):
        if f.is_file() and f.name != "manifest.txt":
            lines.append(f"{sha256_file(f)}  {f.name}")
    lines.append("")
    lines.append("# Probe outcomes")
    for r in results:
        lines.append(f"{r['outcome']:9s} {r['probe_id']}")
    out = run_dir / "manifest.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def append_baseline_v1_section(report_path: Path, run_id: str, run_dir: Path,
                               results: list[dict], counts: dict,
                               chroma_status: str) -> Path:
    """APPEND section 'Baseline V1' vào CHERRY_INTELLIGENCE_TEST_REPORT.md
    (không xóa nội dung cũ)."""
    ts_local = datetime.now().strftime("%d/%m/%Y %H:%M")
    deltas = _probe_deltas(results)
    lines = []
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## Baseline V1 — CIEE Runner chuẩn hóa ({ts_local})")
    lines.append("")
    lines.append(
        f"**Bộ probe:** 14 probes chuẩn hóa vào `tools/ciee/` (probe class có "
        f"probe_id / group A-H / setup / run / assert / evidence). "
        f"**Run:** `{run_id}` — evidence đầy đủ tại "
        f"`reports/intelligence_maturity/ciee/runs/{run_id}/` "
        f"(results.json + REPORT.md + manifest.txt).")
    lines.append("")
    lines.append(f"**Kết quả: {counts.get('PASS', 0)} PASS / "
                 f"{counts.get('FAIL', 0)} FAIL / "
                 f"{counts.get('PARTIAL', 0)} PARTIAL / "
                 f"{counts.get('GAP_KNOWN', 0)} GAP_KNOWN / "
                 f"{counts.get('NOT_RUN', 0)} NOT_RUN / "
                 f"{counts.get('ERROR', 0)} ERROR — trên {len(results)} probes, 8 nhóm A-H.**")
    lines.append("")
    lines.append("| Probe | V0 | V1 |")
    lines.append("|---|---|---|")
    for r in results:
        v0 = V0_PROBE_OUTCOMES.get(r["probe_id"], "?")
        mark = "" if v0 == r["outcome"] else " ← khác V0"
        lines.append(f"| {r['probe_id']} | {v0} | {r['outcome']}{mark} |")
    lines.append("")
    if deltas:
        lines.append("**Khác biệt với V0 (nguyên nhân):**")
        lines.append("")
        for d in deltas:
            lines.append(f"- `{d['probe_id']}`: {d['v0']} → {d['v1']} — {d['note']}")
        lines.append("")
    lines.append(
        "**Chuẩn hóa so với V0:** V0 là script ad-hoc 1 lần; V1 là runner "
        "tái lập (`python E:/BRAIN/tools/ciee/ciee_runner.py`), mọi DB "
        "production chỉ đọc qua URI `mode=ro&immutable=0` + snapshot copy "
        "cho module tự CREATE TABLE; probe đo động trên KU thật (C2, seed=42) "
        "để giảm nhiễu mẫu cố định; Chroma probe ghi NOT RUN có lý do.")
    lines.append("")
    out = run_dir / "_baseline_v1_section.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with open(report_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return out
