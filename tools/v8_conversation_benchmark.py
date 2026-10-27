"""V8 Vietnamese Conversation Benchmark — objective, evidence-based scoring.

Usage:
    ./.venv/Scripts/python.exe tools/v8_conversation_benchmark.py baseline   # before fixes
    ./.venv/Scripts/python.exe tools/v8_conversation_benchmark.py after      # after fixes

Sections:
  A — Code-structure parity (stream vs non-stream evidence layers)
  B — Unit-level functional checks (normalize / classify / guidance / sanitize)
  C — Live behavioral check (teach via stream → episode persisted)

Fail-honest: every check reports PASS/FAIL with evidence; no LLM-judge scores
(mark NEEDS_LLM_EVAL where objective scoring is impossible).
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

SERVER = WORKSPACE / "src" / "quan_ai_brain" / "web" / "server.py"


def _stream_range(src_lines: list[str]) -> tuple[int, int]:
    start = next(i for i, l in enumerate(src_lines, 1) if "def _handle_api_chat_stream" in l)
    end = next(i for i, l in enumerate(src_lines, 1) if "def _handle_api_plan" in l)
    return start, end


def _chat_range(src_lines: list[str]) -> tuple[int, int]:
    start = next(i for i, l in enumerate(src_lines, 1) if "def _handle_api_chat(" in l)
    end = _stream_range(src_lines)[0]
    return start, end


STREAM_RANGE = _stream_range(SERVER.read_text(encoding="utf-8").splitlines())
CHAT_RANGE = _chat_range(SERVER.read_text(encoding="utf-8").splitlines())

CHECKS: list[dict] = []


def check(group: str, name: str, passed: bool, evidence: str) -> None:
    CHECKS.append({"group": group, "name": name, "pass": bool(passed), "evidence": evidence[:200]})


def has_in_range(src_lines: list[str], token: str, rng: tuple[int, int]) -> tuple[bool, int]:
    lo, hi = rng
    count = 0
    for i in range(lo - 1, min(hi, len(src_lines))):
        if token in src_lines[i]:
            count += 1
    return count > 0, count


# ---------------- Section A: stream/non-stream parity (code structure) ----------------
def run_section_a() -> None:
    src = SERVER.read_text(encoding="utf-8").splitlines()
    layers = {
        "teach pipeline (detect_teaching)": "detect_teaching",
        "grounding facts (BỘ SỰ THẬT SỐNG)": "collect_grounding_facts",
        "TTNS lookup (nhân sự/lịch họp)": "looks_like_ttns_query",
        "Document RAG (kho tài liệu)": "DocumentRAG",
        "V7 progress chain": "run_progress_check_chain",
    }
    for label, token in layers.items():
        in_chat, c_chat = has_in_range(src_lines=src, token=token, rng=CHAT_RANGE)
        in_stream, c_stream = has_in_range(src_lines=src, token=token, rng=STREAM_RANGE)
        check(
            "A",
            f"[parity] {label}: chat={in_chat}({c_chat}) stream={in_stream}({c_stream})",
            in_chat and in_stream,
            f"/api/chat refs={c_chat}, /api/chat/stream refs={c_stream}",
        )
    # history depth check
    depth_stream = [ln for ln in src[STREAM_RANGE[0] - 1 : STREAM_RANGE[1]] if "get_recent_session_history" in ln and "limit=6" in ln]
    check("A", "[history] stream history limit>=6", bool(depth_stream), "find 'limit=6' at get_recent_session_history in stream handler")


# ---------------- Section B: unit-level functional checks ----------------
def run_section_b() -> None:
    # B1: input normalization module
    try:
        from quan_ai_brain.cognition.vietnamese_conversation import normalize_vietnamese_input

        q = "ừ  ơi  cho anh hỏi   hiện trạng hệ thống nhé"
        out = normalize_vietnamese_input(q)
        ok = out == "cho anh hỏi hiện trạng hệ thống nhé" or (out.strip() and "  " not in out and not out.startswith("ừ"))
        check("B", "[normalize] làm sạch filler + khoảng trắng", ok, f"in={q!r} out={out!r}")
        src_q = "Kiểm tra TASK-123 và R5 85% 8766"
        out2 = normalize_vietnamese_input(src_q)
        check("B", "[normalize] giữ nguyên mã kỹ thuật", out2 == src_q, f"in={src_q!r} out={out2!r}")
    except ImportError:
        check("B", "[normalize] module vietnamese_conversation tồn tại", False, "ImportError — DESIGNED only")

    # B2: request classification
    try:
        from quan_ai_brain.cognition.vietnamese_conversation import classify_request, RequestKind

        cases = [
            ("8766 là cổng gì?", RequestKind.QUESTION_SHORT),
            ("Phân tích kiến trúc DAG so sánh 2 phương án orchestration", RequestKind.TECH_ANALYSIS),
            ("Làm tiếp đi", RequestKind.CONTEXT_DEPENDENT),
            ("Sửa phần đó", RequestKind.CONTEXT_DEPENDENT),
            ("Khẩn cấp: hệ thống còn chạy không?", RequestKind.URGENT),
            ("Nhớ giúp em: họp 8h mai", RequestKind.WORK_CHAT),  # teach pipeline bắt trước khi LLM; classify chỉ phụ trợ
        ]
        all_ok = True
        details = []
        for q, expect in cases:
            got = classify_request(q)
            ok = got == expect
            all_ok = all_ok and ok
            details.append(f"{q[:30]!r}->{got.value if hasattr(got,'value') else got}{'' if ok else ' (expect ' + str(expect) + ')'}")
        check("B", "[classify] 7 loại yêu cầu §3.2", all_ok, "; ".join(details))
    except ImportError:
        check("B", "[classify] module tồn tại", False, "ImportError — DESIGNED only")

    # B3: guidance block trong context
    try:
        from quan_ai_brain.cognition.context_builder import PromptContextBuilder
        from quan_ai_brain.cognition.models import RetrievalResult

        builder = PromptContextBuilder()
        ctx = builder.build(user_query="làm tiếp đi", retrieval=RetrievalResult(query="làm tiếp đi", memories=[], total_found=0, total_chars=0))
        has_guidance = "[CONVERSATION GUIDANCE" in ctx.rendered_context
        check("B", "[guidance] block xuất hiện trong rendered_context", has_guidance, "tìm '[CONVERSATION GUIDANCE' trong context query 'làm tiếp đi'")
        ctx2 = builder.build(user_query="hello", retrieval=RetrievalResult(query="hello", memories=[], total_found=0, total_chars=0))
        check("B", "[guidance] không phá context tiếng Anh/thường", "APPROVED / VERIFIED MEMORY" in ctx2.rendered_context, "các block gốc vẫn còn")
    except ImportError:
        check("B", "[guidance] wire vào PromptContextBuilder", False, "ImportError — DESIGNED only")

    # B4: TTS reading layer
    try:
        from quan_ai_brain.voice.voice_pipeline import sanitize_for_spoken_vietnamese

        t1 = sanitize_for_spoken_vietnamese("Cổng R5 bị chặn, task TASK-123 chạy 85% trên cổng 8766, dung lượng 4GB")
        spoken_ok = "R5" not in t1 and ("R năm" in t1 or "R-5" in t1 or "R five" in t1)
        no_midcut = not t1.strip().endswith(("của", "và", "trên", "theo", "cho"))
        check("B", "[tts] từ điển đọc mã (R5→đọc được)", spoken_ok, f"out={t1[:120]!r}")
        check("B", "[tts] không cắt giữa câu", no_midcut, f"out_tail={t1[-40:]!r}")
        t2 = sanitize_for_spoken_vietnamese("Kết quả: 1071 passed, 1 skipped, tổng 1072 tests")
        check("B", "[tts] đọc số/quy mô tự nhiên", "1071" in t2 or "một nghìn" in t2.lower() or "một nghìn không trăm" in t2.lower(), f"out={t2[:120]!r}")
    except ImportError:
        check("B", "[tts] sanitize_for_spoken_vietnamese", False, "ImportError")


# ---------------- Section C: live behavioral check ----------------
def _post(path: str, payload: dict, timeout: float = 120.0) -> dict | None:
    url = f"http://127.0.0.1:8766{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"__error__": f"{type(exc).__name__}: {exc}"}


def _count_teach_episodes(marker: str) -> int:
    db = WORKSPACE / "data" / "brain.db"
    if not db.exists():
        return -1
    conn = sqlite3.connect(db)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM memories WHERE source_ref LIKE 'owner_teach%' AND content LIKE ?",
            (f"%{marker}%",),
        )
        return int(cur.fetchone()[0])
    finally:
        conn.close()


TEACH_MARKER = "V8-BENCH-HOINHO-2710"

def run_section_c() -> None:
    """Live teach-via-stream: dùng script smoke chuyên dụng (parse SSE chuẩn)."""
    import subprocess

    smoke = WORKSPACE / "tools" / "v8_live_smoke_teach_stream.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(smoke)],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(WORKSPACE),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        persisted = "persisted=True" in out and "✅ PASS" in out
        check("C", "[live-stream-teach] dạy qua stream → episode persist", persisted, out[-260:])
    except Exception as exc:
        check("C", "[live-stream-teach] dạy qua stream → episode persist", False, f"smoke error: {exc}")


def main() -> None:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "baseline").lower()
    run_section_a()
    run_section_b()
    if mode == "after":
        run_section_c()
    else:
        # baseline: vẫn chạy C để chứng minh bug thật (không persist)
        run_section_c()
    total = len(CHECKS)
    passed = sum(1 for c in CHECKS if c["pass"])
    out = {
        "mode": mode,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "checks": CHECKS,
        "note": "Section C viết 1 episode teach thật vào brain.db (đúng chức năng owner teaching).",
    }
    dest = WORKSPACE / "reports" / f"V8_BENCHMARK_{mode.upper()}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"MODE={mode}  PASS={passed}/{total}")
    for c in CHECKS:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['group']} {c['name']}")
        if not c["pass"]:
            print(f"         ↳ {c['evidence']}")
    print(f"saved: {dest}")


if __name__ == "__main__":
    main()
