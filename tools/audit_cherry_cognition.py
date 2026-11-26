"""AUDIT BỘ NÃO CHERRY — rà soát toàn bộ nhận thức: trí nhớ, tư duy, vai trò.

(26/11/2026) Owner: "audit, rà soát, xây dựng để cherry có quan điểm, suy nghĩ,
trí nhớ, tư duy..... như vai trò trợ lý đa nghiệp vụ".

Checklist audit (đều chỉ-đọc):
  A. TRÍ NHỚ   — brain.db (episodes/memories/teach), semantic ChromaDB,
                 conversation_state (multi-turn), memory_recall, session history
  B. TƯ DUY    — health_snapshot (mới), grounding_facts, self_qa (M4-C),
                 self_model_engine, teach_pipeline, OutputGuardrails self-check
  C. VAI TRÒ   — role_orchestrator, executive_persona, capability_registry
  D. SỐNG SỐT  — module nào WIRED vào /api/chat, module nào chết code
  E. LỖI THẬT  — reminder job (No module named quan_ai_brain), dm read error
Kết quả: in báo cáo + lưu E:/BRAIN/reports/AUDIT_CHERRY_COGNITION_2611.md
"""
from __future__ import annotations

import json
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
SRC = WORKSPACE / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

REPORT: list[str] = []
def sec(t: str) -> None:
    REPORT.append("")
    REPORT.append(f"## {t}")
    print(f"\n=== {t} ===")

def item(label: str, ok: bool | str, detail: str = "") -> None:
    mark = {"True": "✅ LIVE", "False": "❌ DEAD", "PARTIAL": "⚠️ PARTIAL",
            "ERR": "💥 ERROR", "UNKNOWN": "❓"}.get(str(ok), str(ok))
    line = f"- [{mark}] {label}" + (f" — {detail}" if detail else "")
    REPORT.append(line)
    print(line)

db = WORKSPACE / "data" / "brain.db"

# ================= A. TRÍ NHỚ =================
sec("A. TRÍ NHỚ (memory systems)")
try:
    con = sqlite3.connect(str(db))
    cur = con.cursor()
    tables = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    item("brain.db tồn tại", db.exists(), f"{db.stat().st_size/1e6:.1f} MB" if db.exists() else "")
    for t in ("memories", "episodes", "session_history"):
        if t in tables:
            n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            item(f"table {t}", True, f"{n} rows")
        else:
            item(f"table {t}", False, "không có trong brain.db")
    # memories theo verification_status
    if "memories" in tables:
        cols = {r[1] for r in cur.execute(f"PRAGMA table_info(memories)").fetchall()}
        if "verification_status" in cols:
            for vs, n in cur.execute(
                "SELECT verification_status, COUNT(*) FROM memories GROUP BY 1").fetchall():
                item(f"memories[{vs}]", True, f"{n} mục")
    # episode mới nhất
    if "episodes" in tables:
        cols = {r[1] for r in cur.execute(f"PRAGMA table_info(episodes)").fetchall()}
        tcol = "created_at" if "created_at" in cols else ("timestamp" if "timestamp" in cols else None)
        if tcol:
            row = cur.execute(f"SELECT MAX({tcol}) FROM episodes").fetchone()
            item("episodes mới nhất", True, str(row[0])[:32])
    con.close()
except Exception as e:
    item("brain.db đọc", "ERR", str(e)[:120])

# Semantic memory (ChromaDB MiniLM)
try:
    from quan_ai_brain.cognition.semantic_memory import SemanticMemoryEngine
    eng = SemanticMemoryEngine(WORKSPACE / "data" / "vector_db_semantic", db)
    stats = eng.stats() if hasattr(eng, "stats") else {}
    n = stats.get("n_chunks") or 0
    hits = eng.search("nhắc việc reminder job", top_k=2)
    item("semantic_memory (ChromaDB)", bool(n), f"{n} chunks, probe search: {len(hits)} hits")
except Exception as e:
    item("semantic_memory (ChromaDB)", "ERR", str(e)[:120])

# Conversation state (multi-turn M5-C) — API đúng: get(channel)
try:
    from quan_ai_brain.cognition.conversation_state import ConversationStateManager
    csm = ConversationStateManager(str(WORKSPACE))
    st = csm.get("dm") or {}
    item("conversation_state (M5-C multi-turn)", bool(st),
         f"last_user: {str(st.get('last_user_text', ''))[:40]!r}")
except Exception as e:
    item("conversation_state", "ERR", str(e)[:120])

# ================= B. TƯ DUY =================
sec("B. TƯ DUY (cognition & metacognition)")
try:
    from quan_ai_brain.tools.health_snapshot import collect_health_snapshot
    hs = collect_health_snapshot()
    item("health_snapshot (26/11)", True,
         f"errors={len(hs.get('recent_errors', []))}, pending={hs.get('self_improve_pending')}")
except Exception as e:
    item("health_snapshot", "ERR", str(e)[:120])
try:
    from quan_ai_brain.cognition.grounding_facts import collect_grounding_facts
    gf = collect_grounding_facts()
    item("grounding_facts", True, f"components: {gf.get('components')}")
except Exception as e:
    item("grounding_facts", "ERR", str(e)[:120])
try:
    from quan_ai_brain.cognition.self_qa import SelfQA
    reply = SelfQA(str(WORKSPACE)).answer("em là ai")
    item("self_qa (M4-C)", bool(reply), (reply or "")[:80])
except Exception as e:
    item("self_qa (M4-C)", "ERR", str(e)[:120])
try:
    from quan_ai_brain.cognition.self_model_engine import SelfModelEngine
    sme = SelfModelEngine(WORKSPACE)
    fn = [m for m in dir(sme) if not m.startswith('_')]
    item("self_model_engine", True, f"methods: {fn[:6]}")
except Exception as e:
    item("self_model_engine", "ERR", str(e)[:120])
try:
    from quan_ai_brain.cognition.teach_pipeline import detect_teaching
    t = detect_teaching("nhớ rằng anh thích báo cáo ngắn")
    item("teach_pipeline", t.is_teaching, f"content: {getattr(t, 'content', '')[:60]}")
except Exception as e:
    item("teach_pipeline", "ERR", str(e)[:120])
# Self-check (Self-RAG lite) — wire check
srv_src = (WORKSPACE / "src" / "quan_ai_brain" / "web" / "server.py").read_text(encoding="utf-8", errors="replace")
item("self_check (Self-RAG lite M6)", "self_check_reply" in srv_src,
     "được gọi trong _handle_api_chat" if "self_check_reply" in srv_src else "chưa wire")

# ================= C. VAI TRÒ (đa nghiệp vụ) =================
sec("C. VAI TRÒ — TRỢ LÝ ĐA NGHIỆP VỤ")
try:
    from quan_ai_brain.cognition.role_orchestrator import RoleOrchestrator
    ro = RoleOrchestrator(WORKSPACE)
    fns = [m for m in dir(ro) if not m.startswith('_')]
    item("role_orchestrator", True, f"methods: {fns[:8]}")
    wired = "role_orchestrator" in srv_src or "RoleOrchestrator" in srv_src
    item("role_orchestrator WIRED vào /api/chat", wired,
         "có" if wired else "CHẾT CODE — model không bao giờ dùng")
except ImportError as e:
    item("role_orchestrator", "ERR", f"import fail: {e}")
except Exception as e:
    item("role_orchestrator", "ERR", str(e)[:120])
try:
    from quan_ai_brain.cognition.executive_persona import ExecutivePersona
    ep = ExecutivePersona()
    p = ep.to_dict() if hasattr(ep, "to_dict") else vars(ep)
    item("executive_persona", True, str(p)[:140])
except Exception as e:
    item("executive_persona", "ERR", str(e)[:120])
try:
    from quan_ai_brain.cognition.capability_registry import CapabilityRegistry
    cr = CapabilityRegistry()
    caps = cr.list_capabilities() if hasattr(cr, "list_capabilities") else []
    item("capability_registry", True, f"{len(caps)} capabilities")
except Exception as e:
    item("capability_registry", "ERR", str(e)[:120])

# ================= D. WIRE CHECK trên /api/chat =================
sec("D. WIRE CHECK — module nào được /api/chat dùng THẬT")
for name, needle in [
    ("memory_recall (2.1)", "recall_memory_summary"),
    ("semantic_memory (2.15)", "SemanticMemoryEngine"),
    ("grounding_facts (2.5)", "collect_grounding_facts"),
    ("health_snapshot (2.52 — MỚI)", "collect_health_snapshot"),
    ("teach_pipeline (2.0)", "detect_teaching"),
    ("external_lookup (2.6)", "collect_external_evidence"),
    ("ttns_lookup (2.7)", "looks_like_ttns_query"),
    ("document_rag (2.8)", "DocumentRAG"),
    ("knowledge KB-RAG (2.9)", "KnowledgeQueryEngine"),
    ("music→Pi5 (2.85)", "looks_like_music_request"),
    ("chat_tool_bridge (2.95)", "ChatToolBridge"),
    ("input_shield", "scan_input"),
]:
    item(name, needle in srv_src)

# ================= E. LỖI THẬT đang mở =================
sec("E. LỖI THẬT đang mở (từ log sống)")
try:
    log = WORKSPACE / "logs" / "netchat_auto_responder_stdout.log"
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()[-400:]
    uniq = []
    for ln in reversed(lines):
        if ("No module named" in ln or "reminder job error" in ln) and ln.strip() not in uniq:
            uniq.append(ln.strip()[:180])
        if len(uniq) >= 3:
            break
    for u in uniq:
        item("LOG", "ERR", u)
    if not uniq:
        item("reminder job", True, "không thấy lỗi trong 400 dòng gần nhất")
except Exception as e:
    item("log đọc", "ERR", str(e)[:120])

# Reminder jobs đăng ký ở đâu?
sec("E2. REMINDER/CRON jobs — đăng ký ở đâu, chạy bằng python nào")
import re as _re
for pat in ("reminder", "cron", "scheduled"):
    hits = []
    for f in (WORKSPACE / "tools").glob("*.py"):
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
            if pat in src.lower() and ("schedule" in src.lower() or "sleep" in src.lower()):
                hits.append(f.name)
        except Exception:
            pass
    if pat == "reminder" and hits:
        break
item("file tools có reminder logic", True, ", ".join(hits[:8]) if hits else "không rõ")

# ================= TỔNG HỢP =================
sec("KẾT LUẬN AUDIT")
out = "\n".join(REPORT)
dst = WORKSPACE / "reports" / "AUDIT_CHERRY_COGNITION_2611.md"
dst.write_text(
    f"# AUDIT BỘ NÃO CHERRY — {datetime.now(timezone.utc).isoformat()}\n\n"
    f"Owner: 'audit, rà soát, xây dựng để cherry có quan điểm, suy nghĩ, trí nhớ, "
    f"tư duy..... như vai trò trợ lý đa nghiệp vụ'\n{out}\n",
    encoding="utf-8")
print(f"\n>>> Đã lưu: {dst}")
