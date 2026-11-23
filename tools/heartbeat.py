# -*- coding: utf-8 -*-
"""Heartbeat cho 4 task nền (P0-4, audit 23/11).

Mỗi task nền ghi 1 file data/heartbeat_<task>.json sau khi chạy xong. morning_report
8AM đọc các file này — task nào quá hạn (sync >30', monitor >15', backup >26h)
→ cảnh báo trong báo cáo sáng.

Tác động = ZERO:
- Chỉ GHI file nhỏ (JSON), không can thiệp logic task cũ
- morning_report chỉ ĐỌC thêm 1 thư mục, fail-safe (không có heartbeat → skip)
- KHÔNG bật auto-restart (giữ manual-start owner 19/11)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
HEARTBEAT_DIR = WORKSPACE / "data" / "heartbeat"

# Tên task → ngưỡng quá hạn (giờ)
TASK_THRESHOLDS = {
    "QUAN_AI_BRAIN_BACKUP_2AM": 26,        # backup 1 lần/ngày, hạn 26h
    "QUAN_AI_BRAIN_MORNING_REPORT_8AM": 26,
    "QUAN_AI_BRAIN_PI5_FILE_SYNC_15MIN": 1.0,   # 60 phút
    "QUAN_AI_BRAIN_PI5_MONITOR_5MIN": 0.5,     # 30 phút
    "QUAN_AI_BRAIN_MIRROR_D_DAILY": 26,        # mirror 1 lần/ngày 02:30
}


def _heartbeat_path(task_name: str) -> Path:
    safe = task_name.replace("QUAN_AI_BRAIN_", "").lower()
    return HEARTBEAT_DIR / f"{safe}.json"


def write_heartbeat(task_name: str, status: str = "ok", extra: dict | None = None) -> Path:
    """Ghi heartbeat 1 task. Trả về path. Không raise (best-effort)."""
    try:
        HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "task": task_name,
            "ts": time.time(),
            "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "status": status,
        }
        if extra:
            payload["extra"] = extra
        p = _heartbeat_path(task_name)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return p
    except Exception as e:
        # Không để heartbeat lỗi làm hỏng task chính
        print(f"[heartbeat] write fail for {task_name}: {e}")
        return Path()


def check_heartbeat(task_name: str, max_age_h: float | None = None) -> dict:
    """Đọc heartbeat. Trả {fresh, age_h, status, last_iso, threshold_h}.

    fresh=True nếu age_h <= max_age_h (hoặc threshold mặc định).
    fresh=False nếu quá hạn HOẶC file không tồn tại (chưa từng chạy → báo).
    """
    threshold = max_age_h if max_age_h is not None else TASK_THRESHOLDS.get(task_name, 24)
    p = _heartbeat_path(task_name)
    out = {
        "task": task_name,
        "fresh": False,
        "age_h": None,
        "status": "no_heartbeat_yet",
        "last_iso": None,
        "threshold_h": threshold,
    }
    if not p.exists():
        return out
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        ts = float(data.get("ts", 0))
        age_h = (time.time() - ts) / 3600
        out["age_h"] = round(age_h, 2)
        out["status"] = data.get("status", "unknown")
        out["last_iso"] = data.get("ts_iso")
        out["fresh"] = age_h <= threshold
    except Exception as e:
        out["status"] = f"parse_error: {e}"
    return out


def check_all() -> list[dict]:
    """Kiểm tra tất cả task trong TASK_THRESHOLDS. Trả list các dict check_heartbeat."""
    return [check_heartbeat(t) for t in TASK_THRESHOLDS]


def summarize_stale() -> str:
    """Trả 1 dòng tóm tắt task nào stale (cho morning_report).

    Mọi task fresh → trả '' (rỗng, không thêm dòng thừa).
    Có stale → trả '⚠️ TASK NỀN BẤT THƯỜNG: ...'
    """
    rows = check_all()
    stale = [r for r in rows if not r["fresh"]]
    if not stale:
        return ""
    parts = []
    for r in stale:
        if r["age_h"] is None:
            parts.append(f"{r['task']} (chưa từng chạy)")
        else:
            parts.append(f"{r['task']} ({r['age_h']}h, ngưỡng {r['threshold_h']}h)")
    return "⚠️ TASK NỀN BẤT THƯỜNG: " + "; ".join(parts)


if __name__ == "__main__":
    # CLI test: python tools/heartbeat.py check
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else "check"
    if arg == "check":
        rows = check_all()
        for r in rows:
            mark = "🟢" if r["fresh"] else "🔴"
            print(f"{mark} {r['task']:<45} age={r['age_h']}h status={r['status']}")
        print()
        s = summarize_stale()
        if s:
            print(s)
        else:
            print("Mọi task đều fresh.")
    elif arg == "write-test":
        # Test write cho 4 task
        for t in TASK_THRESHOLDS:
            write_heartbeat(t, "test")
            print(f"wrote {t}")
