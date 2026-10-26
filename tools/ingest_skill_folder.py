"""Ingest DC/Battery AI knowledge from Skill/ folder into QUAN AI BRAIN memory.

SAFETY: Read-only against the source folders. Never modifies Skill/, SKILL_BAT_AI/,
BATTERY_AI_V4, DC-COMMAND, BOT projects (per AGENTS.md preserve rules).

Applies knowledge_ingestion pipeline (Sprint 3): every item goes to
candidate_knowledge with provenance → quarantined until owner approves.

Classification (from owner's request 2026-10-26):
- KNOWLEDGE items  → ingestion candidates (tri thức DC/power/NOC/SOP/safety)
- FEATURE items    → catalogued as capability references, not ingested as truth
"""
from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"E:\AI\QUAN AI BRAIN")
SKILL = ROOT / "Skill"
DB = ROOT / "data" / "brain.db"

sys.path.insert(0, str(ROOT / "src"))

BOT_ID = "dc_skill_ingest_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_candidate(cur, statement: str, source_ref: str, rationale: str) -> str:
    cid = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO candidate_knowledge (id, created_at_utc, statement, source_ref, rationale, status, decision_note) "
        "VALUES (?, ?, ?, ?, ?, 'quarantined', ?)",
        (cid, utc_now(), statement, source_ref, rationale, f"batch={BOT_ID}"),
    )
    return cid


def main() -> int:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    added = 0

    # ---- 1. DC Organizational model (NOC multi-agent roles = TRI THỨC DC) ----
    dc_items = [
        ("DC organizational model: Data Center được điều hành theo mô hình multi-agent "
         "NOC gồm 1 DC Orchestrator (Tổng giám đốc điều phối, không trực tiếp xử lý kỹ thuật) "
         "và 5 Domain Commanders: Battery, UPS, Cooling, Power, Environment.",
         "Skill/SKILL/NOC/ai_workforce/vibe-bat-dc-orchestrator/SKILL.md",
         "Mô hình tổ chức DC chuẩn hóa — nền tảng cho thiết kế DC-Orchestrator của QUAN AI BRAIN"),
        ("DC incident response SOP 4 phase: (1) Detection — cảm biến/anomaly agent phát hiện và phát "
         "[ALERT]; (2) Triaging & Escalation — Commander lọc nhiễu, sự nghiêm trọng báo Orchestrator; "
         "(3) RCA — Cross-Domain Reasoning (ví dụ nhiệt độ cao → hỏi cả Cooling Commander lẫn Battery "
         "Commander); (4) Resolution & Verification — Orchestrator xuất Decision, chờ NOC phê duyệt "
         "trước khi thực thi, sau đó xác minh sự cố đã hết.",
         "Skill/SKILL/NOC/workflows/incident-response-sop.md",
         "SOP xử lý sự cố DC — đối chiếu trực tiếp với lộ trình DC-2/DC-3 trong báo cáo RPT-QAB-CORE-DC-ROADMAP-V1"),
        ("DC safety bounds: (1) KHÔNG auto-execute nếu độ tin cậy chẩn đoán < 80% — chỉ được ĐỀ XUẤT, "
         "không được ra lệnh; (2) Test xả ắc quy phải hủy ngay nếu nhiệt độ môi trường > 28°C; "
         "(3) RBAC — chỉ Orchestrator có quyền yêu cầu Command Signing cho thao tác thay đổi trạng thái "
         "phần cứng; Commander/Agent chỉ phân tích và đề xuất; (4) Ưu tiên tuyệt đối DC uptime — không "
         "ưu tiên bảo vệ ắc quy nếu làm sập nguồn server, trừ nguy cơ cháy nổ (Thermal Runaway).",
         "Skill/SKILL/NOC/rules/01-safety-bounds.md",
         "Ranh giới an toàn DC — bổ sung cho ma trận R0-R5 của QUAN AI BRAIN ở ngữ cảnh vận hành DC thật"),
        ("DC severity examples: Thermal Runaway (nhiệt độ cell tăng 25°C→45°C trong 2 phút kèm điện áp "
         "giảm) là CRITICAL — anomaly agent phát cảnh báo, Battery Commander báo Orchestrator, "
         "Orchestrator KHÔNG tự động xả ắc quy mà đề xuất NOC kiểm tra phòng ắc quy và bật Emergency Fan. "
         "Connection loss tới monitoring (503/timeout) → chuyển Standalone cache mode, không retry liên tục.",
         "Skill/SKILL/NOC/tests/test-incident-response.md",
         "Kịch bản kiểm thử DC có sẵn — tái sử dụng làm benchmark DC-2"),
    ]
    for stmt, src, why in dc_items:
        add_candidate(cur, stmt, src, why)
        added += 1

    # ---- 2. Battery AI domain knowledge (TRI THỨC chuyên ngành) ----
    bat_items = [
        ("BATTERY AI là nền tảng Edge AI đánh giá, chẩn đoán và dự báo sức khỏe ắc quy cho Tổng trạm/"
         "Data Center; quy mô thực tế tại TTKV1: 53 nguồn điện, 96 chuỗi ắc quy. Kiến trúc gồm "
         "BATTERY_AI_V4 (production, port 9090), BATTERY_AI_V3 (legacy, port 8080, nguồn dữ liệu), "
         "BOT_PDL (5 bot NetChat: bat, tb, vtdp, pauctt, td), Ollama local (port 11434).",
         "Skill/SKILL/BAT AI/battery-ai-system/SKILL.md + Skill/UC/BATTERY_AI_SOURCE_OF_TRUTH_v1.0.md",
         "Kiến thức hệ thống anh em — cần để tích hợp qua interface (WRAP+EXTEND+ORCHESTRATE+INTEGRATE)"),
        ("Battery analytics domain: SOH (State of Health) tính từ chuỗi nội trở IR và capacity dài hạn; "
         "RUL (Remaining Useful Life) dự báo bằng time-series kết hợp KEDB (Known Error Database); "
         "RCA chuẩn 5 Whys phân biệt lỗi Cell/BMS/quá nhiệt/tải UPS; quy luật mẫu: 10 lần xả sâu ở "
         "nhiệt độ >30°C làm nội trở tăng ~5%.",
         "Skill/SKILL/BAT/ai_workforce/vibe-bat-soh-agent/SKILL.md + prognostics + knowledge-engineer",
         "Tri thức chuyên ngành battery — nền cho DC-2 chẩn đoán domain power"),
        ("Nguyên tắc kiến trúc hệ thống anh em: DC-COMMAND là lớp điều hành cấp trên, BATTERY AI V4/BIC "
         "là Domain Brain của domain Battery; KHÔNG xây lại V4 từ đầu — ưu tiên WRAP + EXTEND + "
         "ORCHESTRATE + INTEGRATE. AI được quan sát/phân tích/dự báo/đề xuất; mọi hành động tác động "
         "production phải qua Policy/Authority/Governance; LLM không được là nguồn quyết định duy nhất.",
         "Skill/UC/BATTERY_AI_SOURCE_OF_TRUTH_v1.0.md mục 0",
         "Nguyên tắc kiến trúc chính thức — ràng buộc cách QUAN AI BRAIN tích hợp với DC-COMMAND"),
    ]
    for stmt, src, why in bat_items:
        add_candidate(cur, stmt, src, why)
        added += 1

    # ---- 3. Feature catalog (TÍNH NĂNG — ghi nhận năng lực tham khảo, không phải sự thật nghiệp vụ) ----
    feat_items = [
        ("Tham chiếu tính năng: bộ agent persona Battery AI (intelligence-orchestrator, memory-agent, "
         "causal-rca, prognostics, knowledge-engineer, 5 commanders, anomaly/diagnostic/soh agents) là "
         "các role-prompt tái sử dụng — QUAN AI BRAIN có thể mượn pattern Orchestrator/Commander/Specialist "
         "cho kiến trúc multi-agent DC của mình, không copy nguyên xi.",
         "Skill/BAT/ + Skill/SKILL/NOC/ai_workforce/",
         "Catalog tính năng — dùng làm tham chiếu thiết kế, không ingest làm tri thức nghiệp vụ"),
        ("Tham chiếu tính năng: vibe-aiworkforce (1641 dòng) là methodology chuyển task doanh nghiệp thành "
         "nhân sự số (folder structure + workflow conditional branching + skills + rules/tests). Áp dụng được "
         "khi anh muốn QUAN AI BRAIN sinh mới nhanh các vai trò số cho domain khác sau DC.",
         "Skill/SKILL/vibe-aiworkforce/SKILL.md",
         "Methodology tham khảo — không phải tri thức DC"),
        ("Tham chiếu tính năng: OCR engine (easyocr/pytesseract fallback) + label_parser phục vụ đọc nhãn "
         "thiết bị/ảnh chụp. Ứng dụng tiềm năng trong DC: số hóa bảng tên thiết bị, phiếu bảo trì.",
         "Skill/OCR/ocr_engine.py",
         "Tính năng code tái sử dụng — kích hoạt khi cần ingest tài liệu dạng ảnh"),
    ]
    for stmt, src, why in feat_items:
        add_candidate(cur, stmt, src, why)
        added += 1

    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone()[0]
    batch = cur.execute(
        "SELECT COUNT(*) FROM candidate_knowledge WHERE decision_note LIKE ?", (f"%{BOT_ID}%",)
    ).fetchone()[0]
    conn.close()
    print(f"OK: added {added} quarantined candidates from Skill/ folder")
    print(f"Batch '{BOT_ID}': {batch} items pending owner approval")
    print(f"Total candidate_knowledge now: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
