"""Daily morning report 08:00 — Sprint 6-GOP hạng mục (3).

Job chạy hằng ngày 08:00: thu thập trạng thái hệ thống thật (probe), số việc
chờ duyệt + task chờ info-gap, gửi 1 tin gọn kênh NetChat.

Nguyên tắc:
- Probe thật qua /api/status + /api/executive/edge/status + schtasks + sqlite —
  KHÔNG bịa số; lỗi probe → "chưa xác minh được X" (trung thực).
- Fail-closed: lỗi收集 → in log, không chết daemon scheduler.
- Gửi qua netchat_bot.py 2 bước (--confirmed) như chuẩn hiện có.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent
NETCHAT_BOT = (
    r"C:/Users/DELL/AppData/Local/netmind_desktop/netmind-agent/venv/Scripts/python.exe",
    r"C:/Users/DELL/AppData/Local/netmind_desktop/skills/bot-netchat/netchat_bot.py",
)
CHANNEL_ID = "4phc9b1mx78qjq3grxcw89u94a"

STATUS_URLS = {
    "dashboard_8765": "http://127.0.0.1:8765/api/status",
    "core_8766": "http://127.0.0.1:8766/api/executive/edge/status",
}


def _probe(url: str, timeout: float = 4.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _ollama_status() -> str:
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:11434/api/tags", timeout=3
        ) as resp:
            data = json.loads(resp.read().decode())
            models = ", ".join(m.get("name", "?") for m in data.get("models", [])[:3])
            return f"🟢 ONLINE ({models})" if models else "🟢 ONLINE"
    except Exception:
        return "🔴 OFFLINE"


def _backup_status() -> str:
    backups = sorted((WORKSPACE / "backups").glob("brain_*.db"), key=lambda p: p.stat().st_mtime)
    if not backups:
        return "⚠️ CHƯA CÓ backup nào"
    import time

    newest = backups[-1]
    age_h = (time.time() - newest.stat().st_mtime) / 3600
    task_ok = "?"
    try:
        r = subprocess.run(
            ["schtasks", "/query", "/tn", "QUAN_AI_BRAIN_BACKUP_2AM", "/fo", "CSV", "/nh"],
            capture_output=True, text=True, timeout=15,
        )
        task_ok = "✅ Ready" if (r.returncode == 0 and "Ready" in r.stdout) else "⚠️ KHÔNG Ready"
    except Exception:
        task_ok = "chưa xác minh được"
    return f"{task_ok} | backup gần nhất {newest.name} ({age_h:.0f}h trước)"


def _pending_counts() -> tuple[int, int]:
    """(số card chờ duyệt, số task chờ info-gap). Lỗi DB → (-1, -1)."""
    pending_cards = pending_gaps = -1
    try:
        conn = sqlite3.connect(WORKSPACE / "data" / "governance.db")
        row = conn.execute(
            "SELECT COUNT(*) FROM approval_cards WHERE status='PENDING_APPROVAL'"
        ).fetchone()
        pending_cards = int(row[0]) if row else 0
        conn.close()
    except Exception:
        pass
    try:
        conn = sqlite3.connect(WORKSPACE / "data" / "information_gaps.db")
        row = conn.execute("SELECT COUNT(*) FROM info_gap_tasks").fetchone()
        pending_gaps = int(row[0]) if row else 0
        conn.close()
    except Exception:
        pass
    return pending_cards, pending_gaps


def collect_report() -> str:
    lines = ["☀️ BÁO CÁO SÁNG — QUAN AI BRAIN"]

    # Servers
    dash = _probe(STATUS_URLS["dashboard_8765"])
    core = _probe(STATUS_URLS["core_8766"])
    lines.append(f"• Dashboard 8765: {'🟢' if dash else '🔴'} | Core 8766: {'🟢' if core else '🔴'}")
    if core and isinstance(core, dict):
        edge = core.get("edge") or core
        state = edge.get("state") or edge.get("status") or "?"
        lines.append(f"• Pi 5 edge: {state} (nguồn /api/executive/edge/status)")
    else:
        lines.append("• Pi 5 edge: chưa xác minh được (probe lỗi)")
    lines.append(f"• Ollama: {_ollama_status()}")
    lines.append(f"• Backup 2AM: {_backup_status()}")

    # Pending work
    cards, gaps = _pending_counts()
    if cards >= 0:
        lines.append(f"• Card chờ anh duyệt: {cards}")
    else:
        lines.append("• Card chờ duyệt: chưa xác minh được (DB lỗi)")
    if gaps >= 0:
        lines.append(f"• Task đang chờ anh bổ sung thông tin: {gaps}")
    else:
        lines.append("• Task chờ thông tin: chưa xác minh được (DB lỗi)")

    # Sprint 8 (a): to-do quá hạn + đến hạn hôm nay
    try:
        from quan_ai_brain.tools.todo_store import TodoStore

        todo = TodoStore(WORKSPACE / "data" / "todos.db")
        groups = todo.overdue_and_today()
        if groups["overdue"]:
            names = "; ".join(t["title"] for t in groups["overdue"][:5])
            lines.append(f"• 🔴 Việc QUÁ HẠN: {len(groups['overdue'])} — {names}")
        if groups["today"]:
            names = "; ".join(t["title"] for t in groups["today"][:5])
            lines.append(f"• 📅 Việc đến hạn HÔM NAY: {len(groups['today'])} — {names}")
        if not groups["overdue"] and not groups["today"]:
            lines.append("• Việc cần làm: không có việc quá hạn/hạn hôm nay")
    except Exception:
        lines.append("• Việc cần làm: chưa xác minh được (DB lỗi)")

    lines.append("— Chi tiết: hỏi em trực tiếp hoặc xem dashboard 8765.")
    return "\n".join(lines)


def send_to_netchat(message: str) -> bool:
    """Gửi qua netchat_bot 2 bước (send → CONFIRM → resend --confirmed)."""
    py, bot = NETCHAT_BOT
    r1 = subprocess.run(
        [py, bot, "send", CHANNEL_ID, "--to-channel", message],
        capture_output=True, text=True, timeout=60,
    )
    out = r1.stdout
    if "--confirmed" in out or "CONFIRM" not in out.upper():
        # một số build trả về thành công ngay khi exit 0 và có post id
        if r1.returncode == 0 and '"id"' in out:
            return True
    import re

    m = re.search(r"CONFIRM-REQUIRED:\s*([a-f0-9]+)", out)
    if not m:
        return False
    r2 = subprocess.run(
        [py, bot, "send", CHANNEL_ID, "--to-channel", message, "--confirmed", m.group(1)],
        capture_output=True, text=True, timeout=60,
    )
    return r2.returncode == 0 and '"id"' in r2.stdout


def main() -> int:
    # Sprint 7a fix: chạy qua Task Scheduler → console cp1252 không in được
    # tiếng Việt/emoji → UnicodeEncodeError giết script (đã xảy ra 12:02 sau
    # boot). Force stdout UTF-8 + ErrorsIgnore để KHÔNG chết vì in console.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    report = collect_report()
    print(report)
    ok = send_to_netchat(report)
    print(f"netchat_sent: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
