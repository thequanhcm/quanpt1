"""V7 Skills — implement thực tế 5 skill nghiệp vụ mục tiêu (Master Prompt V7 §3.3).

Mỗi skill là một hàm có:
- Input validation (schema bắt buộc; sai -> ValueError, không đoán)
- Error policy fail_honest: thiếu dữ liệu -> UNKNOWN/NOT_VERIFIED, không suy diễn
- Output theo schema đã khai báo trong SkillRegistry
- Không tự thực hiện hành động ghi/gửi ngoài phạm vi (chỉ đọc nguồn được phép)

Nguồn dữ liệu được phép: data/tasks.db, data/consultations.db, data/todos.db,
reports/ (đọc), email_text do chủ cung cấp trực tiếp. Vmail/Outlook BLOCKED.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UNKNOWN = "UNKNOWN"
NOT_VERIFIED = "NOT_VERIFIED"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# EMAIL_ANALYSIS (§4.2.A)
# ---------------------------------------------------------------------------

_EMAIL_FIELD_PATTERNS: list[tuple[str, str]] = [
    ("sender", r"^(?:from|người gửi|nguoi gui)\s*[:：]\s*(.+)$"),
    ("recipient", r"^(?:to|người nhận|nguoi nhan|kính gửi|to:\s*)[:：]?\s*(.+)$"),
    ("subject", r"^(?:subject|tiêu đề|tieu de)\s*[:：]\s*(.+)$"),
]

_DEADLINE_PATTERNS: list[tuple[str, str]] = [
    (r"(?:deadline|hạn|han)\s*[:：]?\s*([0-9]{1,2}[/-][0-9]{1,2}(?:[/-][0-9]{2,4})?)", "deadline_date"),
    (r"(?:due|do\s+ngày|hoàn thành trước|trước ngày)\s*[:：]?\s*([0-9]{1,2}[/-][0-9]{1,2}(?:[/-][0-9]{2,4})?)", "deadline_date"),
    (r"([0-9]{1,2}[/-][0-9]{1,2}(?:[/-][0-9]{2,4})?)", "mentioned_date"),
]

# Câu hỏi: dòng kết thúc bằng '?' hoặc bắt đầu bằng từ hỏi
_QUESTION_RE = re.compile(r"([^\n.!?]*\?)")

# Cam kết / mốc: động từ hành động + đối tượng
_COMMIT_RE = re.compile(
    r"\b(?:sẽ|se|cam kết|cam ket|dự kiến|du kien|hoàn thành|hoan thanh|báo cáo|bao cao|gửi|gui|cập nhật|cap nhat)\b"
    r"[^\n.!?]{5,160}",
    re.IGNORECASE,
)

# Nhiệm vụ/khối lượng cần làm (dòng mệnh lệnh hoặc bullet)
_TASK_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$", re.MULTILINE)


def analyze_email(email_text: str) -> dict[str, Any]:
    """EMAIL_ANALYSIS: trích xuất 8 trường §4.2.A từ email text.

    Fail-honest: trường không xác định được -> UNKNOWN. Suy luận được đánh
    dấu rõ trong 'inferences', không lẫn vào nội dung trực tiếp.
    """
    if not isinstance(email_text, str) or len(email_text.strip()) < 20:
        raise ValueError("email_text must be a string of at least 20 chars (fail-closed)")

    text = email_text.strip()
    lines = text.splitlines()
    analysis: dict[str, str] = {}

    # 1. Header fields (sender/recipient/subject) — chỉ nhận từ dòng header rõ ràng
    for field_name, pattern in _EMAIL_FIELD_PATTERNS:
        val = UNKNOWN
        for ln in lines[:15]:  # header nằm gần đầu
            m = re.match(pattern, ln.strip(), re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                break
        analysis[field_name] = val if val else UNKNOWN

    # 2. Yêu cầu chính: câu chứa động từ yêu cầu hoặc dòng mệnh lệnh đầu tiên
    request_match = re.search(
        r"(?:yêu cầu|yeu cau|đề nghị|de nghi|request|vui lòng|vui long|kiểm tra|kiem tra|cần|can)\b[^\n]{10,300}",
        text,
        re.IGNORECASE,
    )
    analysis["request"] = request_match.group(0).strip() if request_match else UNKNOWN

    # 3. Dự án / nhóm: tên viết hoa trong ngoặc hoặc sau từ 'dự án'/'project'
    proj_m = re.search(r"(?:dự án|du an|project|nhóm|nhom)\s*[:：]?\s*([A-ZÀ-Ỹ][^\n,.:;]{2,60})", text)
    analysis["project_or_team"] = proj_m.group(1).strip() if proj_m else UNKNOWN

    # 4. Người phụ trách: 'anh/chị/em + Tên' hoặc 'phụ trách'
    owner_m = re.search(r"(?:phụ trách|phu trach|owner|responsible)\s*[:：]?\s*([^\n,.:;]{2,50})", text, re.IGNORECASE)
    person_m = re.search(r"\b(?:anh|chị|chi|em|mr|mrs|ms)\.?\s+([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+)?)", text)
    analysis["owner_hint"] = (owner_m.group(1).strip() if owner_m else (person_m.group(1).strip() if person_m else UNKNOWN))

    # 5. Thời hạn: pattern ngày; không có -> UNKNOWN (không đoán)
    deadline = UNKNOWN
    for pat, _tag in _DEADLINE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            deadline = m.group(1).strip()
            break
    analysis["deadline"] = deadline

    # 6. Cam kết & mốc (trực tiếp trích nguyên văn câu)
    commitments = [m.group(0).strip() for m in _COMMIT_RE.finditer(text)][:10]

    # 7. Câu hỏi cần trả lời
    questions = [q.strip() for q in _QUESTION_RE.findall(text) if len(q.strip()) > 10][:10]

    # 8. Đầu ra cần tạo
    deliverable_m = re.search(
        r"(?:báo cáo|bao cao|danh sách|danh sach|bảng|bang|tóm tắt|tom tat)\s+([^\n.!?]{5,120})",
        text,
        re.IGNORECASE,
    )
    analysis["expected_output"] = deliverable_m.group(0).strip() if deliverable_m else UNKNOWN

    # Suy luận (đánh dấu rõ, KHÔNG lẫn vào direct content)
    inferences: list[str] = []
    if analysis["project_or_team"] != UNKNOWN:
        inferences.append(f"Dự án/nhóm liên quan có thể là: {analysis['project_or_team']} (suy luận từ ngữ cảnh)")
    if analysis["deadline"] != UNKNOWN:
        inferences.append(f"Thời hạn được hiểu là: {analysis['deadline']} (cần xác nhận định dạng ngày)")

    # Task items (bullet/numbered) — nguyên văn
    task_items = [m.group(1).strip() for m in _TASK_RE.finditer(text)][:15]

    return {
        "analysis": {
            "sender": analysis["sender"],
            "recipient": analysis["recipient"],
            "subject": analysis["subject"],
            "request": analysis["request"],
            "project_or_team": analysis["project_or_team"],
            "owner_hint": analysis["owner_hint"],
            "deadline": analysis["deadline"],
            "expected_output": analysis["expected_output"],
        },
        "commitments": commitments,
        "questions": questions,
        "task_items": task_items,
        "inferences": inferences,  # mọi suy luận nằm riêng, đánh dấu rõ
        "sources_accessed": ["email_text (do chủ cung cấp trực tiếp)"],
        "sources_blocked": ["Vmail/Outlook connector (BLOCKED — chờ chủ cấu hình)"],
        "analyzed_at": now_utc(),
    }


# ---------------------------------------------------------------------------
# TASK_STATUS_RECONCILIATION (§4.2.B/C — đối chiếu email vs DB thật)
# ---------------------------------------------------------------------------

_ALLOWED_TASK_DB_READS = ("data/tasks.db",)


def run_progress_check_chain(query_text: str, workspace: str | Path) -> dict[str, Any]:
    """Luồng thực thi tích hợp: chat query (yêu cầu kiểm tra tiến độ) -> chain.

    Trình tự: EMAIL_ANALYSIS (query như yêu cầu ngắn) -> TASK_STATUS_RECONCILIATION
    -> PROGRESS_RISK_DETECTION -> OWNER_ADVISORY_REPORT. Mọi skill đều fail-honest;
    trả về kết quả đầy đủ kèm truy vết nguồn để gắn vào response chat.
    """
    if not isinstance(query_text, str) or len(query_text.strip()) < 10:
        raise ValueError("query_text must be a string of at least 10 chars")

    analysis = {
        "analysis": {
            "sender": "Quanpt1 (chat trực tiếp)",
            "recipient": "QUAN AI BRAIN",
            "subject": UNKNOWN,
            "request": query_text.strip(),
            "project_or_team": UNKNOWN,
            "owner_hint": UNKNOWN,
            "deadline": UNKNOWN,
            "expected_output": "báo cáo tư vấn tiến độ",
        },
        "commitments": [],
        "questions": [],
        "task_items": [],
        "inferences": ["Yêu cầu đến từ chat trực tiếp — không phải email gốc (ghi rõ trong báo cáo)"],
        "sources_accessed": ["chat query (do chủ cung cấp trực tiếp)"],
        "sources_blocked": ["Vmail/Outlook connector (BLOCKED — chờ chủ cấu hình)"],
        "analyzed_at": now_utc(),
    }
    reconciliation = reconcile_task_status(analysis, workspace)
    risks = progress_risk_detection(reconciliation.get("unified_records", []))
    cross = cross_source_evidence_analysis([], reconciliation.get("unified_records", []))
    advisory = owner_advisory_report(analysis, reconciliation, risks, cross)

    return {
        "chain": ["EMAIL_ANALYSIS(light)", "TASK_STATUS_RECONCILIATION", "PROGRESS_RISK_DETECTION", "OWNER_ADVISORY_REPORT"],
        "query_text": query_text.strip(),
        "reconciliation": {
            "conclusion": reconciliation.get("conclusion"),
            "records_matched": len(reconciliation.get("unified_records", [])),
            "sources_accessed": reconciliation.get("sources_accessed", []),
            "sources_blocked": reconciliation.get("sources_blocked", []),
        },
        "risk_summary": {
            "risks": len(risks.get("risks", [])),
            "high": sum(1 for r in risks.get("risks", []) if r.get("severity") == "HIGH"),
            "unknowns": len(risks.get("unknowns", [])),
        },
        "report_md": advisory["report_md"],
        "executed_at": now_utc(),
    }


def reconcile_task_status(
    email_analysis: dict[str, Any],
    workspace: str | Path,
) -> dict[str, Any]:
    """Đối chiếu yêu cầu tiến độ trong email với nguồn DB được cấp quyền.

    Fail-honest: task không tìm thấy bằng chứng -> status NOT_VERIFIED;
    không có nguồn nào -> trả về sources empty + conclusion UNKNOWN.
    KHÔNG ghi/sửa DB — chỉ SELECT.
    """
    if not isinstance(email_analysis, dict) or "analysis" not in email_analysis:
        raise ValueError("email_analysis must be the dict returned by analyze_email()")

    ws = Path(workspace)
    sources_accessed: list[str] = []
    sources_blocked: list[str] = []
    unified: list[dict[str, Any]] = []

    request_text = email_analysis["analysis"].get("request", UNKNOWN)
    subject = email_analysis["analysis"].get("subject", UNKNOWN)
    keywords_src = f"{request_text} {subject}"

    tasks_db = ws / "data" / "tasks.db"
    if tasks_db.exists():
        try:
            conn = sqlite3.connect(f"file:{tasks_db}?mode=ro", uri=True, timeout=5.0)
            rows = conn.execute(
                """
                SELECT task_id, goal, status, created_at_utc, updated_at_utc
                FROM durable_tasks
                ORDER BY updated_at_utc DESC LIMIT 200
                """
            ).fetchall()
            conn.close()
            sources_accessed.append("data/tasks.db (read-only)")
            kw = [w for w in re.findall(r"[a-zA-Zàáảãạăằẳẵặâầẩẫậèéẻẽẹêềểễệìíỉĩịòóỏõọôồổỗộơờởỡợùúủũụưừửữựỳýỷỹỵđ]+", keywords_src.lower()) if len(w) > 3]
            for tid, goal, status, created, updated in rows:
                relevance = sum(1 for w in kw if w in (goal or "").lower())
                if relevance == 0 and len(kw) > 0:
                    continue
                unified.append({
                    "task_id": tid,
                    "name": goal,
                    "status_per_report": "email",  # email chưa nêu trạng thái từng task
                    "status_verified": status,      # từ DB thật
                    "email_claim": UNKNOWN,
                    "db_status": status,
                    "progress_reported": UNKNOWN,
                    "progress_evidenced": UNKNOWN,
                    "last_updated": updated,
                    "owner": UNKNOWN,
                    "deadline": UNKNOWN,
                    "evidence_refs": [f"data/tasks.db#durable_tasks/{tid}"],
                    "missing_fields": ["owner", "deadline", "progress_percent"],
                    "relevance_score": relevance,
                })
        except sqlite3.Error as exc:
            sources_blocked.append(f"data/tasks.db (error: {type(exc).__name__})")
    else:
        sources_blocked.append("data/tasks.db (không tồn tại)")

    todos_db = ws / "data" / "todos.db"
    if todos_db.exists():
        try:
            conn = sqlite3.connect(f"file:{todos_db}?mode=ro", uri=True, timeout=5.0)
            rows = conn.execute("SELECT id, title, due, priority, status FROM todos LIMIT 100").fetchall()
            conn.close()
            sources_accessed.append("data/todos.db (read-only)")
            for tid, title, due, prio, status in rows:
                unified.append({
                    "task_id": f"todo_{tid}",
                    "name": title,
                    "status_per_report": "email",
                    "status_verified": status,
                    "email_claim": UNKNOWN,
                    "db_status": status,
                    "progress_reported": UNKNOWN,
                    "progress_evidenced": UNKNOWN,
                    "last_updated": UNKNOWN,
                    "owner": UNKNOWN,
                    "deadline": due or UNKNOWN,
                    "evidence_refs": [f"data/todos.db#todos/{tid}"],
                    "missing_fields": ["owner", "progress_percent"],
                    "relevance_score": 0,
                })
        except sqlite3.Error as exc:
            sources_blocked.append(f"data/todos.db (error: {type(exc).__name__})")
    else:
        sources_blocked.append("data/todos.db (không tồn tại)")

    if not sources_accessed:
        return {
            "unified_records": [],
            "conclusion": UNKNOWN,
            "sources_accessed": [],
            "sources_blocked": sources_blocked,
            "reconciled_at": now_utc(),
        }

    # Đối chiếu: email claim (chưa có per-task) vs DB status
    conflicts: list[dict[str, Any]] = []
    for rec in unified:
        if rec["email_claim"] != UNKNOWN and rec["email_claim"].lower() != rec["db_status"].lower():
            conflicts.append({
                "task_id": rec["task_id"],
                "email_claim": rec["email_claim"],
                "db_status": rec["db_status"],
                "resolution": "chưa phân xử được — cần bằng chứng bổ sung",
            })
        # status 'PENDING' lâu không cập nhật -> dấu hiệu báo cáo chưa cập nhật
        if rec["db_status"] == "PENDING" and rec["last_updated"] not in (UNKNOWN, None):
            rec["staleness_flag"] = "PENDING chưa chuyển động — cần xác minh hiện trạng"

    return {
        "unified_records": unified,
        "conflicts": conflicts,
        "conclusion": "RECONCILED_WITH_LIMITS" if unified else "NO_MATCHING_RECORDS",
        "sources_accessed": sources_accessed,
        "sources_blocked": sources_blocked,
        "reconciled_at": now_utc(),
    }


# ---------------------------------------------------------------------------
# CROSS_SOURCE_EVIDENCE_ANALYSIS (§4.2.D)
# ---------------------------------------------------------------------------

_STATUS_SYNONYMS = {
    "hoàn thành": {"hoan thanh", "done", "completed", "xong", "finished", "100%"},
    "đang làm": {"dang lam", "in progress", "wip", "đang thực hiện"},
    "chưa làm": {"chua lam", "pending", "todo", "chưa bắt đầu"},
}


def _normalize_status(s: str) -> str:
    sl = (s or "").strip().lower()
    for canon, syns in _STATUS_SYNONYMS.items():
        if sl in syns or sl == canon:
            return canon
    return sl or UNKNOWN


def cross_source_evidence_analysis(
    email_claims: list[dict[str, Any]],
    db_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Đối chiếu chéo claim email vs bản ghi DB; phát hiện mâu thuẫn.

    email_claims: [{'task_name': str, 'claim_status': str, 'evidence': str}]
    db_records: output 'unified_records' của reconcile_task_status.
    Không mặc định nguồn nào đúng — mâu thuẫn được trình bày nguyên vẹn.
    """
    if not isinstance(email_claims, list) or not isinstance(db_records, list):
        raise ValueError("email_claims and db_records must be lists")

    conflicts: list[dict[str, Any]] = []
    verified: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    db_by_name: dict[str, dict[str, Any]] = {}
    for rec in db_records:
        name = (rec.get("name") or "").lower()
        if name:
            db_by_name[name] = rec

    for claim in email_claims:
        cname = (claim.get("task_name") or "").strip().lower()
        cstatus = _normalize_status(claim.get("claim_status", ""))
        evidence = claim.get("evidence", "")
        match = None
        # khớp chính xác hoặc chứa
        if cname in db_by_name:
            match = db_by_name[cname]
        else:
            for name, rec in db_by_name.items():
                if cname and (cname in name or name in cname):
                    match = rec
                    break
        if match is None:
            unresolved.append({
                "task_name": claim.get("task_name"),
                "reason": "không tìm thấy trong nguồn DB nào",
                "email_evidence": evidence,
            })
            continue
        db_status = _normalize_status(match.get("db_status", ""))
        if cstatus != UNKNOWN and db_status != UNKNOWN and cstatus != db_status:
            conflicts.append({
                "task_name": claim.get("task_name"),
                "email_says": cstatus,
                "db_says": db_status,
                "email_evidence": evidence,
                "db_evidence": match.get("evidence_refs", []),
                "resolution": "chưa phân xử được — trình bày cả hai, đề xuất xác minh nguồn gốc",
            })
        else:
            verified.append({
                "task_name": claim.get("task_name"),
                "status": cstatus if cstatus != UNKNOWN else db_status,
                "evidence_refs": match.get("evidence_refs", []),
                "verification": "email và DB thống nhất" if cstatus == db_status else "chỉ một nguồn nêu trạng thái",
            })

    return {
        "conflicts": conflicts,
        "verified_agreements": verified,
        "unresolved": unresolved,
        "rule": "không nguồn nào được mặc định đúng; mâu thuẫn trình bày nguyên vẹn",
        "analyzed_at": now_utc(),
    }


# ---------------------------------------------------------------------------
# PROGRESS_RISK_DETECTION (§4.2.D — risk flags)
# ---------------------------------------------------------------------------

def progress_risk_detection(unified_records: list[dict[str, Any]], as_of: str | None = None) -> dict[str, Any]:
    """Phát hiện rủi ro từ bản ghi hợp nhất: quá hạn, stale, thiếu trách nhiệm.

    Fail-honest: thiếu hạn -> unknowns, KHÔNG xếp risk.
    """
    if not isinstance(unified_records, list):
        raise ValueError("unified_records must be a list")

    now = datetime.now(timezone.utc)
    risks: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []

    for rec in unified_records:
        rid = rec.get("task_id", UNKNOWN)
        deadline = rec.get("deadline")
        # Parse deadline an toàn
        parsed_deadline: datetime | None = None
        if deadline and deadline != UNKNOWN:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S"):
                try:
                    parsed_deadline = datetime.strptime(str(deadline)[:19], fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
        if parsed_deadline is None and deadline not in (UNKNOWN, None):
            # thử ISO full
            try:
                parsed_deadline = datetime.fromisoformat(str(deadline)).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                parsed_deadline = None
        if deadline in (UNKNOWN, None) or parsed_deadline is None:
            unknowns.append({"task_id": rid, "field": "deadline", "value": deadline})
        elif parsed_deadline < now and str(rec.get("db_status", "")).lower() not in ("completed", "done", "archived", "cancelled"):
            risks.append({
                "task_id": rid,
                "type": "OVERDUE",
                "evidence": f"deadline {deadline} < as_of; status={rec.get('db_status')}",
                "severity": "HIGH",
                "evidence_refs": rec.get("evidence_refs", []),
            })
        # stale: PENDING quá 7 ngày không cập nhật
        lu = rec.get("last_updated")
        if lu and lu != UNKNOWN and str(rec.get("db_status", "")).upper() == "PENDING":
            try:
                lu_dt = datetime.fromisoformat(str(lu))
                if lu_dt.tzinfo is None:
                    lu_dt = lu_dt.replace(tzinfo=timezone.utc)
                if (now - lu_dt).days >= 7:
                    risks.append({
                        "task_id": rid,
                        "type": "STALE_PENDING",
                        "evidence": f"PENDING chưa chuyển động từ {lu}",
                        "severity": "MEDIUM",
                        "evidence_refs": rec.get("evidence_refs", []),
                    })
            except ValueError:
                pass
        # trách nhiệm không rõ
        if rec.get("owner", UNKNOWN) in (UNKNOWN, None, ""):
            unknowns.append({"task_id": rid, "field": "owner", "value": rec.get("owner")})

    return {
        "risks": risks,
        "unknowns": unknowns,
        "as_of": as_of or now.isoformat(),
        "rule": "thiếu dữ liệu -> unknowns, không suy diễn; mọi risk kèm bằng chứng",
        "analyzed_at": now_utc(),
    }


# ---------------------------------------------------------------------------
# OWNER_ADVISORY_REPORT (§4.2.E — 12 mục)
# ---------------------------------------------------------------------------

_ADVISORY_SECTIONS = [
    "Tình hình tổng thể",
    "Công việc đã xác minh hoàn thành",
    "Công việc đang triển khai",
    "Công việc quá hạn hoặc có nguy cơ chậm",
    "Những điểm bất thường",
    "Nguyên nhân đã được chứng minh",
    "Giả thuyết cần xác minh",
    "Tác động và mức độ ưu tiên",
    "Phương án xử lý đề xuất",
    "Những quyết định cần Quanpt1 xem xét",
    "Nguồn chưa truy cập được",
    "Mức độ tin cậy và giới hạn kết luận",
]


def owner_advisory_report(
    email_analysis: dict[str, Any],
    reconciliation: dict[str, Any],
    risk_analysis: dict[str, Any],
    cross_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Tổng hợp báo cáo tư vấn 12 mục §4.2.E; mỗi kết luận có nguồn.

    KHÔNG tự gửi email / sửa task / thực hiện cam kết — chỉ tạo nội dung
    báo cáo để chủ quyết định.
    """
    for name, obj in (("email_analysis", email_analysis), ("reconciliation", reconciliation), ("risk_analysis", risk_analysis)):
        if not isinstance(obj, dict):
            raise ValueError(f"{name} must be a dict")

    records = reconciliation.get("unified_records", [])
    risks = risk_analysis.get("risks", [])
    unknowns = risk_analysis.get("unknowns", [])
    conflicts = []
    if cross_source:
        conflicts = cross_source.get("conflicts", [])

    completed = [r for r in records if _normalize_status(str(r.get("db_status", ""))) == "hoàn thành"]
    in_progress = [r for r in records if _normalize_status(str(r.get("db_status", ""))) in ("đang làm", "pending")]
    overdue = [r for r in risks if r.get("type") == "OVERDUE"]

    lines: list[str] = []
    lines.append(f"# BÁO CÁO TƯ VẤN TIẾN ĐỘ — {now_utc()[:10]}")
    lines.append("")
    lines.append(f"## 1. {_ADVISORY_SECTIONS[0]}")
    total = len(records)
    lines.append(
        f"- Đối chiếu {total} bản ghi công việc từ {len(reconciliation.get('sources_accessed', []))} nguồn đã truy cập; "
        f"{len(reconciliation.get('sources_blocked', []))} nguồn bị chặn."
    )
    lines.append(f"- Yêu cầu gốc: {email_analysis['analysis'].get('request', UNKNOWN)}")
    lines.append("")
    lines.append(f"## 2. {_ADVISORY_SECTIONS[1]}")
    lines.append(f"- {len(completed)} bản ghi trạng thái hoàn thành (theo DB; cần bằng chứng bổ sung để xác nhận chất lượng)." if completed else "- Không có bản ghi nào ở trạng thái hoàn thành trong phạm vi nguồn.")
    lines.append("")
    lines.append(f"## 3. {_ADVISORY_SECTIONS[2]}")
    lines.append(f"- {len(in_progress)} bản ghi đang triển khai/chờ xử lý.")
    lines.append("")
    lines.append(f"## 4. {_ADVISORY_SECTIONS[3]}")
    if overdue:
        for r in overdue:
            lines.append(f"- [OVERDUE] {r['task_id']}: {r['evidence']}")
    else:
        lines.append("- Không phát hiện quá hạn trong dữ liệu có hạn; các bản ghi thiếu hạn ghi ở mục 12.")
    lines.append("")
    lines.append(f"## 5. {_ADVISORY_SECTIONS[4]}")
    if conflicts:
        for c in conflicts:
            lines.append(f"- Mâu thuẫn: {c.get('task_name')}: email='{c.get('email_says')}' vs DB='{c.get('db_says')}'")
    else:
        lines.append("- Không phát hiện mâu thuẫn giữa email và DB trong phạm vi dữ liệu khớp tên.")
    lines.append("")
    lines.append(f"## 6. {_ADVISORY_SECTIONS[5]}")
    lines.append("- " + ("Mọi kết luận trong báo cáo này dựa trên DB nguồn được truy cập trực tiếp (bằng chứng kèm theo)." if records else "Chưa có kết luận nào được chứng minh — nguồn không truy cập được."))
    lines.append("")
    lines.append(f"## 7. {_ADVISORY_SECTIONS[6]}")
    for inf in email_analysis.get("inferences", []):
        lines.append(f"- {inf}")
    if not email_analysis.get("inferences"):
        lines.append("- Không có suy luận nào cần xác minh thêm.")
    lines.append("")
    lines.append(f"## 8. {_ADVISORY_SECTIONS[7]}")
    lines.append(f"- Rủi ro: {len(risks)} (HIGH: {sum(1 for r in risks if r.get('severity') == 'HIGH')}, MEDIUM: {sum(1 for r in risks if r.get('severity') == 'MEDIUM')}); dữ liệu thiếu: {len(unknowns)} trường.")
    lines.append("")
    lines.append(f"## 9. {_ADVISORY_SECTIONS[8]}")
    lines.append("- Đề xuất: xác minh trực tiếp với người phụ trách các bản ghi OVERDUE/STALE (nếu có); bổ sung hạn hoàn thành cho các bản ghi thiếu hạn.")
    lines.append("- KHÔNG tự thực hiện: hệ thống không gửi email nhắc việc hay sửa trạng thái nếu chưa được chủ duyệt.")
    lines.append("")
    lines.append(f"## 10. {_ADVISORY_SECTIONS[9]}")
    lines.append("- Cần Quanpt1 quyết định: (a) xác nhận phạm vi công việc cần theo dõi; (b) phê duyệt hành động nào (nếu có) được thực hiện thay chủ.")
    lines.append("")
    lines.append(f"## 11. {_ADVISORY_SECTIONS[10]}")
    for src in reconciliation.get("sources_blocked", []):
        lines.append(f"- BLOCKED: {src}")
    lines.append("- Vmail/Outlook connector: BLOCKED (chờ chủ cấu hình/đổi SSO).")
    lines.append("")
    lines.append(f"## 12. {_ADVISORY_SECTIONS[11]}")
    lines.append(f"- Mức tin cậy: {len(reconciliation.get('sources_accessed', []))} nguồn đọc trực tiếp; trạng thái từng bản ghi theo DB tại thời điểm {reconciliation.get('reconciled_at', UNKNOWN)[:19]}.")
    lines.append(f"- Giới hạn: {len(unknowns)} trường dữ liệu thiếu -> ghi UNKNOWN, không suy diễn; email chưa có claim trạng thái từng task nên đối chiếu giới hạn ở mức khớp tên.")
    lines.append("")

    report_md = "\n".join(lines)
    return {
        "report_md": report_md,
        "sections": _ADVISORY_SECTIONS,
        "sections_filled": 12,
        "traceability": {
            "email_analysis_sources": email_analysis.get("sources_accessed", []),
            "reconciliation_sources": reconciliation.get("sources_accessed", []),
            "blocked_sources": reconciliation.get("sources_blocked", []),
            "risk_evidence_count": sum(len(r.get("evidence_refs", [])) for r in risks),
        },
        "generated_at": now_utc(),
        "action_policy": "report_only — không hành động ghi/gửi ngoài nếu chưa duyệt",
    }
