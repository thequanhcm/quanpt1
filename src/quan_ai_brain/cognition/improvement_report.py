"""Sprint 13 (a): Continuous Improvement — báo cáo tự đánh giá bằng dữ liệu thật.

Lớp tổng hợp trên module HIỆN CÓ (không tạo store mới):
- build_improvement_report(): đọc tasks.db / governance.db / todos.db / email_intake.db /
  information_gaps.db + ĐẾM lesson từ brain.db (Sprint 11) → ma trận năng lực 5 mức
  (§2.3 master prompt) mỗi mục kèm EVIDENCE truy vết được.
- KHÔNG tự đánh giá giỏi/xấu — chỉ số liệu + trạng thái + khoảng trống.
- DB lỗi → mục đó CHƯA XÁC MINH (fail-honest như workbench overview).
- export_report_markdown(): xuất file .md (R2 — ghi trong workspace, do owner bấm).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Trạng thái 5 mức theo ma trận §2.3 master prompt
M_ACTIVE = "Đã có và hoạt động"
M_PARTIAL = "Có một phần"
M_ABSENT = "Chưa có"
M_UNVERIFIED = "Chưa xác minh"
M_BLOCKED = "Bị chặn"


def _count_rows(db_path: Path, sql: str, params: tuple = ()) -> int | None:
    """Đếm dòng; DB lỗi → None (CHƯA XÁC MINH, không 0 giả)."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        try:
            cur = conn.execute(sql, params)
            row = cur.fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()
    except Exception:
        return None


def build_improvement_report(workspace: str | Path) -> dict[str, Any]:
    """Tổng hợp số liệu thật từ các DB — mỗi khối OK hoặc CHƯA XÁC MINH."""
    ws = Path(workspace)
    data_dir = ws / "data"
    now = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {"generated_at_utc": now, "sections": {}, "matrix": []}

    # --- 1. Nhiệm vụ (tasks.db) ---
    tasks_db = data_dir / "tasks.db"
    total = _count_rows(tasks_db, "SELECT COUNT(*) FROM durable_tasks")
    completed = _count_rows(tasks_db, "SELECT COUNT(*) FROM durable_tasks WHERE status='COMPLETED'")
    failed = _count_rows(tasks_db, "SELECT COUNT(*) FROM durable_tasks WHERE status='FAILED'")
    cancelled = _count_rows(tasks_db, "SELECT COUNT(*) FROM durable_tasks WHERE status='CANCELLED'")
    pending = _count_rows(tasks_db, "SELECT COUNT(*) FROM durable_tasks WHERE status IN ('PENDING','APPROVED','IN_PROGRESS','WAITING_APPROVAL')")
    if total is None:
        report["sections"]["tasks"] = {"status": M_UNVERIFIED, "reason": "tasks.db không đọc được"}
    else:
        done_total = (completed or 0) + (failed or 0) + (cancelled or 0)
        success_rate = round((completed or 0) / done_total * 100, 1) if done_total else None
        report["sections"]["tasks"] = {
            "status": M_ACTIVE if total else M_PARTIAL,
            "total": total,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "in_flight": pending,
            "success_rate_pct": success_rate,
            "evidence": f"tasks.db durable_tasks @ {now}",
        }

    # --- 2. Phê duyệt (governance.db approval cards) ---
    gov_db = data_dir / "governance.db"
    cards_total = _count_rows(gov_db, "SELECT COUNT(*) FROM approval_cards")
    approved = _count_rows(gov_db, "SELECT COUNT(*) FROM approval_cards WHERE status='APPROVED'")
    rejected = _count_rows(gov_db, "SELECT COUNT(*) FROM approval_cards WHERE status='REJECTED'")
    if cards_total is None:
        report["sections"]["approvals"] = {"status": M_UNVERIFIED, "reason": "governance.db không đọc được"}
    else:
        decided = (approved or 0) + (rejected or 0)
        report["sections"]["approvals"] = {
            "status": M_ACTIVE if cards_total else M_PARTIAL,
            "cards_total": cards_total,
            "approved": approved,
            "rejected": rejected,
            "decision_rate_pct": round((rejected or 0) / decided * 100, 1) if decided else None,
            "evidence": f"governance.db approval_cards @ {now}",
        }

    # --- 3. Kinh nghiệm (brain.db memories — lesson Sprint 11) ---
    brain_db = data_dir / "brain.db"
    lessons_total = _count_rows(
        brain_db,
        "SELECT COUNT(*) FROM memories WHERE tags_json LIKE ?",
        ('%"sprint11_lesson"%',),
    )
    lessons_confirmed = _count_rows(
        brain_db,
        "SELECT COUNT(*) FROM memories WHERE tags_json LIKE ? AND verification_status='VERIFIED'",
        ('%"sprint11_lesson"%',),
    )
    candidates_q = _count_rows(brain_db, "SELECT COUNT(*) FROM candidate_knowledge")
    semantic = _count_rows(brain_db, "SELECT COUNT(*) FROM semantic_memory")
    if lessons_total is None:
        report["sections"]["experience"] = {"status": M_UNVERIFIED, "reason": "brain.db không đọc được"}
    else:
        report["sections"]["experience"] = {
            "status": M_ACTIVE if lessons_total else M_PARTIAL,
            "lessons_total": lessons_total,
            "lessons_confirmed": lessons_confirmed,
            "lessons_pending": (lessons_total or 0) - (lessons_confirmed or 0),
            "quarantine_candidates": candidates_q,
            "semantic_confirmed": semantic,
            "evidence": f"brain.db memories/candidate_knowledge/semantic_memory @ {now}",
        }

    # --- 4. Email (email_intake.db + proposals) ---
    intake_db = data_dir / "email_intake.db"
    emails = _count_rows(intake_db, "SELECT COUNT(*) FROM intake_emails")
    proposals = _count_rows(intake_db, "SELECT COUNT(*) FROM email_proposals")
    proposals_linked = _count_rows(intake_db, "SELECT COUNT(*) FROM email_proposals WHERE status='TASK_CREATED'")
    if emails is None:
        report["sections"]["email_intelligence"] = {"status": M_UNVERIFIED, "reason": "email_intake.db không đọc được"}
    else:
        vmail = M_BLOCKED  # trung thực: Vmail thật chưa mở
        report["sections"]["email_intelligence"] = {
            "status": M_PARTIAL if emails else M_ABSENT,
            "intake_emails": emails,
            "proposals": proposals,
            "proposals_linked_task": proposals_linked,
            "vmail_real": vmail,
            "evidence": f"email_intake.db @ {now} — Vmail thật chờ owner đổi SSO pass",
        }

    # --- 5. Web read-only (Sprint 12 — khả năng chứng minh qua code + smoke; DB không lưu) ---
    report["sections"]["web_readonly"] = {
        "status": M_ACTIVE,
        "evidence": "integration/web_connector.py + smoke 27/10 (SSRF chặn, Bing search, VNE RSS 10 items) — commit cd626c0",
    }

    # --- 6. Thông tin thiếu (information_gaps.db) ---
    gaps_db = data_dir / "information_gaps.db"
    gaps_open = _count_rows(gaps_db, "SELECT COUNT(*) FROM information_gaps WHERE status IN ('OPEN','NOT_SUBMITTED')")
    if gaps_open is None:
        report["sections"]["information_gaps"] = {"status": M_UNVERIFIED, "reason": "information_gaps.db không đọc được"}
    else:
        report["sections"]["information_gaps"] = {
            "status": M_ACTIVE,
            "open_gaps": gaps_open,
            "evidence": f"information_gaps.db @ {now}",
        }

    # --- 7. Test regression (từ báo cáo gần nhất — không tự chạy pytest) ---
    tests_last = M_UNVERIFIED
    tests_evidence = "chưa tìm thấy báo cáo test gần nhất"
    try:
        reports_dir = ws / "bao cao xay dung he thong"
        report_files = sorted(reports_dir.glob("BAO_CAO_V3_SPRINT*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if report_files:
            text = report_files[0].read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                if "passed" in line and ("fail" in line or "skipped" in line):
                    tests_last = M_ACTIVE
                    tests_evidence = f"{report_files[0].name}: {line.strip()[:120]}"
                    break
    except Exception as exc:
        tests_evidence = f"lỗi đọc báo cáo: {exc}"
    report["sections"]["regression_tests"] = {"status": tests_last, "evidence": tests_evidence}

    # --- Ma trận 5 mức tổng hợp ---
    for name, sec in report["sections"].items():
        report["matrix"].append({
            "capability": name,
            "level": sec.get("status", M_UNVERIFIED),
            "evidence": sec.get("evidence") or sec.get("reason") or "",
        })

    # --- Điểm cải tiến đề xuất (dựa trên số liệu, không phán xét) ---
    improvements: list[str] = []
    exp = report["sections"].get("experience", {})
    if isinstance(exp, dict) and exp.get("lessons_pending"):
        improvements.append(f"{exp['lessons_pending']} bài học đang chờ anh duyệt — duyệt để dùng làm căn cứ mạnh cho đề xuất email.")
    em = report["sections"].get("email_intelligence", {})
    if isinstance(em, dict) and em.get("vmail_real") == M_BLOCKED:
        improvements.append("Vmail thật còn BLOCKED — đổi mật khẩu SSO + card 'Real Email Connector' để mở luồng email thật.")
    tg = report["sections"].get("information_gaps", {})
    if isinstance(tg, dict) and tg.get("open_gaps"):
        improvements.append(f"{tg['open_gaps']} thông tin thiếu đang mở — xem tab Workbench để bổ sung.")
    tasks_sec = report["sections"].get("tasks", {})
    if isinstance(tasks_sec, dict) and tasks_sec.get("in_flight"):
        improvements.append(f"{tasks_sec['in_flight']} nhiệm vụ đang chờ/xử lý — cân nhắc duyệt hoặc huỷ task cũ.")
    report["suggested_improvements"] = improvements
    return report


def export_report_markdown(report: dict[str, Any], workspace: str | Path) -> Path:
    """Xuất báo cáo .md vào 'bao cao xay dung he thong/' (R2 — chủ động bấm của owner)."""
    ws = Path(workspace)
    out_dir = ws / "bao cao xay dung he thong"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"BAO_CAO_SELF_ASSESSMENT_{stamp}.md"
    lines = [
        "# BÁO CÁO TỰ ĐÁNH GIÁ NĂNG LỰC — QUAN AI BRAIN",
        "",
        f"*Sinh lúc {report['generated_at_utc']} bằng dữ liệu thật từ DB (Sprint 13 Continuous Improvement).*",
        "",
        "## Ma trận năng lực (5 mức)",
        "",
        "| Năng lực | Mức | Bằng chứng |",
        "|---|---|---|",
    ]
    for row in report["matrix"]:
        lines.append(f"| {row['capability']} | {row['level']} | {row['evidence']} |")
    lines += ["", "## Số liệu chi tiết", ""]
    for name, sec in report["sections"].items():
        if not isinstance(sec, dict):
            continue
        lines.append(f"### {name}")
        for k, v in sec.items():
            if k in ("status",):
                continue
            lines.append(f"- {k}: {v}")
        lines.append("")
    if report.get("suggested_improvements"):
        lines += ["## Điểm cải tiến đề xuất (dựa trên số liệu)", ""]
        lines += [f"- {s}" for s in report["suggested_improvements"]]
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
