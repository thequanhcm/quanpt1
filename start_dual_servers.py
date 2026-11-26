"""Start BOTH QUAN AI BRAIN servers with NETMIND_EXTERNAL_DATA_ALLOWED=true.

- Port 8765: Local Web UI Dashboard (chat, memories, plans)
- Port 8766: Executive Command Center (persona, consultation, NetChat tab)

Run each in its own thread and block forever. Use start_server_fixed.py if
only the 8765 dashboard is needed.
"""
import os
import sys
import threading
import time

# (29/10/2026) pythonw windowless mode: sys.stdout là None dưới pythonw.exe —
# print() sẽ crash. Redirect ra log file.
if sys.stdout is None or sys.stderr is None:
    _LOG_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent / "logs"
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        sys.stdout = open(_LOG_DIR / "dual_servers_stdout.log", "a", buffering=1, encoding="utf-8", errors="replace")
        sys.stderr = sys.stdout
    except Exception:
        pass

# (29/10/2026) pythonw: không còn console cha — các subprocess con (vd
# netchat_bridge gọi skill script khi mở tab NetChat trên dashboard) sẽ tạo
# cửa sổ console riêng → nháy. Patch toàn bộ subprocess.run của process này.
import subprocess as _subprocess

_orig_subprocess_run = _subprocess.run

def _subprocess_run_no_window(*args, **kwargs):
    kwargs.setdefault("creationflags", getattr(_subprocess, "CREATE_NO_WINDOW", 0))
    return _orig_subprocess_run(*args, **kwargs)

_subprocess.run = _subprocess_run_no_window
# (30/10/2026) May moi 16GB: OpenBLAS (chromadb/numpy) tu cap phat thread =
# so CORE -> 6 thread x buffer lon lam cạn RAM khi learning daemon ingest
# song song ("OpenBLAS error: Memory allocation still failed" -> server chet).
# Gioi han 2 thread/BLAS cho toan bo process con.
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

os.environ["NETMIND_EXTERNAL_DATA_ALLOWED"] = "true"

from quan_ai_brain.web.server import run_web_server, run_executive_server  # noqa: E402


def _semantic_refresh_daemon() -> None:
    """(26/11/2026, Sprint CHERRY-ĐA-NGHIỆP-VỤ) Auto-refresh trí nhớ ngữ nghĩa.

    Audit 26/11: ChromaDB semantic_memory chỉ ingest thủ công → 392 memories/
    episodes mới bị lỗ trong retrieval ngữ nghĩa (2.15 /api/chat). Daemon này
    ingest delta (idempotent theo original_id) mỗi 30 phút. Fail-honest: lỗi
    chỉ log, không giết servers; chi phí thấp (delta 0 → skip ngay).
    """
    import time as _t
    while True:
        try:
            from quan_ai_brain.cognition.semantic_memory import SemanticMemoryEngine
            from pathlib import Path as _P
            root = _P(__file__).resolve().parent
            eng = SemanticMemoryEngine(root / "data" / "vector_db_semantic",
                                       root / "data" / "brain.db")
            r = eng.ingest(limit_per_table=4000)
            if r.get("added"):
                print(f"[SEMANTIC-REFRESH] +{r['added']} chunks "
                      f"(total {r.get('total_in_collection')}, {r.get('seconds')}s)")
            else:
                print(f"[SEMANTIC-REFRESH] no new chunks ({r})")
        except Exception as e:
            print(f"[SEMANTIC-REFRESH] error (fail-honest, tiếp tục): {e}")
        _t.sleep(1800)  # 30 phút


def main() -> None:
    t5 = threading.Thread(target=run_web_server, kwargs={"port": 8765, "open_browser": False}, daemon=True)
    t6 = threading.Thread(target=run_executive_server, kwargs={"port": 8766, "open_browser": False}, daemon=True)
    t5.start()
    time.sleep(1.0)
    t6.start()
    # (26/11) Daemon trí nhớ ngữ nghĩa — chờ servers lên rồi chạy nền.
    threading.Thread(target=_semantic_refresh_daemon, daemon=True).start()
    print("[start_dual_servers] Both servers running: 8765 (UI) + 8766 (Executive) + semantic-refresh (30m). Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("[start_dual_servers] Stopping.")


if __name__ == "__main__":
    main()
