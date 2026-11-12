"""NetChat bridge for the Executive Dashboard (port 8766).

Provides read-only channel status/message listing and audited send/command
operations for the 'Quản trị kênh NetChat' tab. Credentials are NEVER read,
printed, or logged here — all NetChat access goes through the skill script
``netchat_bot.py`` (which resolves the token from env var itself).

Security notes:
- No token is passed to subprocesses; the skill script handles auth.
- Send and command operations append an audit event (owner actions from the
  dashboard are attributable).
- Message content is passed through verbatim; redaction is the responsibility
  of the caller for logging (we never log message bodies).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.core.audit import AuditLogger
import sys as _sys
_SECRET_DIR = Path('E:/BRAIN/user, pass, token')
if str(_SECRET_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SECRET_DIR))
from loader import get_secret as _get_secret

# (12/11/2026) Loader secret tập trung
import sys as _sys
_SECRET_DIR = Path('E:/BRAIN/user, pass, token')
if str(_SECRET_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SECRET_DIR))
from loader import get_secret as _get_secret

_local_appdata = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\DELL\AppData\Local"))
_script_cand = [
    _local_appdata / "netmind_desktop" / "skills" / "bot-netchat" / "netchat_bot.py",
    Path(r"C:\Users\DELL\AppData\Local\netmind_desktop\skills\bot-netchat\netchat_bot.py"),
]
NETCHAT_SCRIPT = next((p for p in _script_cand if p.exists()), _script_cand[0])

_py_cand = [
    _local_appdata / "netmind_desktop" / "netmind-agent" / "venv" / "Scripts" / "python.exe",
    Path(r"C:\Users\DELL\AppData\Local\netmind_desktop\netmind-agent\venv\Scripts\python.exe"),
]
NETCHAT_PYTHON = next((p for p in _py_cand if p.exists()), _py_cand[0])

# (31/10/2026) Thong nhat: chi con lai DM voi chu so huu — kenh 'Tro ly Tony Pham' da bi bo (owner yeu cau xoa cac kenh khac, chi giu DM)
DEFAULT_CHANNEL_ID = _get_secret("netchat_channel_owner", "mwp3nk3ciprjjr4hdmcoqgk6jr")  # (12/11) đọc từ loader
CHANNEL_ID = _get_secret("netchat_channel_owner", "mwp3nk3ciprjjr4hdmcoqgk6jr")  # (12/11) đọc từ loader
DEFAULT_CHANNEL_NAME = "Trợ lý Tony Pham"
# (02/11/2026) Thay bot_quanpt1 thanh bot_tony
BOT_USER_ID = _get_secret("netchat_bot_user_id", "66opztx9ut8rjxny555xhj84je")  # (12/11) loader

# ---------------------------------------------------------------------------
# (02/11/2026, owner yêu cầu) VN-LANG — chuẩn hoá tiếng Việt TẦNG CUỐI cho DM.
# Mọi tin gửi owner qua bridge được dịch trạng thái/mật ngữ kỹ thuật sang
# tiếng Việt. Số liệu, ID, tên riêng (Pi 5, Ollama, GLM…) GIỮ NGUYÊN — không
# bao giờ biến dữ liệu kỹ thuật thành chữ khác nghĩa.
# ---------------------------------------------------------------------------
_VN_STATUS = {
    "CRITICAL": "NGHIÊM TRỌNG",
    "WARNING": "CẢNH BÁO",
    "NORMAL": "BÌNH THƯỜNG",
    "UNKNOWN": "KHÔNG RÕ",
    "MAINTENANCE": "BẢO TRÌ",
    "ONLINE": "HOẠT ĐỘNG",
    "OFFLINE": "MẤT KẾT NỐI",
    "READY": "SẴN SÀNG",
    "RUNNING": "ĐANG CHẠY",
    "STOPPED": "ĐÃ DỪNG",
    "PAUSED": "TẠM DỪNG",
    "OK": "BÌNH THƯỜNG",
    "FAIL": "LỖI",
    "FAILED": "THẤT BẠI",
    "DOWN": "MẤT KẾT NỐI",
    "HEALTHY": "KHỎE MẠNH",
    "BLOCKED": "BỊ CHẶN",
    "PENDING": "CHỜ XỬ LÝ",
    "APPROVED": "ĐÃ DUYỆT",
    "COMPLETED": "HOÀN THÀNH",
    "IN_PROGRESS": "ĐANG LÀM",
    "WAITING_APPROVAL": "CHỜ DUYỆT",
    "ERROR": "LỖI",
    "ACTIVE": "ĐANG HOẠT ĐỘNG",
    "CONNECTED": "ĐÃ KẾT NỐI",
    "DISCONNECTED": "MẤT KẾT NỐI",
    "TIMEOUT": "QUÁ THỜI GIAN CHỜ",
}
_VN_COMPONENTS = {
    "pc_host": "máy chính",
    "pi5_edge": "Pi 5",
    "selfcare_engine": "tự chăm sóc",
    "ram_percent": "RAM",
    "disk_percent": "ổ đĩa",
    "cpu_percent": "CPU",
    "connectivity": "kết nối",
    "response_time": "thời gian phản hồi",
}


def _vn_normalize(text: str) -> str:
    """Chuẩn hoá 1 tin DM → tiếng Việt tự nhiên (giữ số liệu + tên riêng)."""
    out = str(text or "")
    if not out:
        return out
    for en, vi in _VN_COMPONENTS.items():
        out = out.replace(en, vi)
    for en, vi in _VN_STATUS.items():
        out = out.replace(f" {en}", f" {vi}").replace(f"→ {en}", f"→ {vi}")
    return out


# Simple single-flight lock: dashboard requests are serialized to avoid
# hammering the NetChat API (HTTP 429 rate limit when sending in bursts).
_NETCHAT_LOCK = threading.Lock()
_LAST_SEND_AT = 0.0
_MIN_SEND_INTERVAL_SEC = 3.0
# (31/10/2026) Rate-limit protection: status cache TTL + suspended circuit
# breaker (chi tiết ở get_status). re được import ở dưới cùng file.
_STATUS_CACHE: dict | None = None
_STATUS_CACHED_AT: float = 0.0
_SUSPENDED_UNTIL: float = 0.0


class NetChatBridgeError(RuntimeError):
    """Raised when the NetChat skill script fails or is unavailable."""


def _run_script(args: list[str], timeout: float = 25.0) -> tuple[int, str, str]:
    if not NETCHAT_SCRIPT.exists():
        raise NetChatBridgeError(f"Skill script not found: {NETCHAT_SCRIPT}")
    python = str(NETCHAT_PYTHON) if NETCHAT_PYTHON.exists() else "python"
    try:
        proc = subprocess.run(
            [python, str(NETCHAT_SCRIPT), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise NetChatBridgeError(f"NetChat script timed out after {timeout:.0f}s") from exc
    return proc.returncode, proc.stdout, proc.stderr


def _parse_json_or_raise(stdout: str, stderr: str) -> Any:
    """Parse JSON from script stdout, tolerating human-readable noise lines.

    netchat_bot.py prints 'BOT: ...' / 'TARGET: ...' headers before the JSON
    payload (confirmed-send path) — parse the LAST balanced JSON object line
    instead of the whole stdout (root cause of 'Unparseable NetChat response'
    on the dashboard send, 27/10/2026 — the post actually was sent).
    """
    text = (stdout or "").strip()
    if not text:
        raise NetChatBridgeError((stderr or "Empty response from NetChat script")[:300])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fallback: scan lines bottom-up for a balanced JSON object/array
    decoder = json.JSONDecoder()
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line or not (line.startswith("{") or line.startswith("[")):
            continue
        try:
            obj, _end = decoder.raw_decode(line)
            return obj
        except json.JSONDecodeError:
            continue
    raise NetChatBridgeError(f"Unparseable NetChat response: {text[:200]}")


def get_status(channel_id: str = DEFAULT_CHANNEL_ID) -> dict[str, Any]:
    """Channel + bot status. Read-only, no message bodies.

    (31/10/2026) CACHE TTL 30s + Circuit breaker 429: tab Cockpit tự refresh
    10s/lần → mỗi lần gọi whoami THẬT qua gateway → cộng với responder poll 5s
    → bot bị gateway đình chỉ 15 phút vì rate_limit_violation. Giờ status chỉ
    gọi gateway tối đa 1 lần/30s; khi gặp 429 trả về trạng thái cached kèm
    cờ suspended (không bắn tiếp request vào gateway đang phạt).
    """
    global _STATUS_CACHE, _STATUS_CACHED_AT, _SUSPENDED_UNTIL
    now = time.time()
    if _STATUS_CACHE is not None and now - _STATUS_CACHED_AT < 30:
        cached = dict(_STATUS_CACHE)
        cached["cached"] = True
        if now < _SUSPENDED_UNTIL:
            cached["suspended_until_epoch_s"] = _SUSPENDED_UNTIL
        return cached

    if now < _SUSPENDED_UNTIL:
        # Đang trong thời gian phạt: KHÔNG gọi gateway, trả cached báo suspended
        cached = dict(_STATUS_CACHE or {"success": True, "bot": {}, "channel": {"id": channel_id, "name": DEFAULT_CHANNEL_NAME}})
        cached["cached"] = True
        cached["suspended"] = True
        cached["suspended_until_epoch_s"] = _SUSPENDED_UNTIL
        return cached

    try:
        code, out, err = _run_script(["whoami"])
        if code != 0:
            raise NetChatBridgeError((err or out or "whoami failed")[:300])
        me = _parse_json_or_raise(out, err)
    except NetChatBridgeError as exc:
        txt = str(exc)
        m = re.search(r"suspended_until[\"':\s]+(\d{13})", txt)
        if m:
            _SUSPENDED_UNTIL = int(m.group(1)) / 1000
            cached = dict(_STATUS_CACHE or {"success": True, "bot": {}, "channel": {"id": channel_id, "name": DEFAULT_CHANNEL_NAME}})
            cached["cached"] = True
            cached["suspended"] = True
            cached["suspended_until_epoch_s"] = _SUSPENDED_UNTIL
            return cached
        raise
    _STATUS_CACHE = {
        "success": True,
        "bot": {
            "id": me.get("id"),
            "username": me.get("username"),
            "is_bot": me.get("is_bot", True),
        },
        "channel": {"id": channel_id, "name": DEFAULT_CHANNEL_NAME},
        "responder_hint": "tools/netchat_auto_responder.py (poll 5s, backoff 429)",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    _STATUS_CACHED_AT = now
    return dict(_STATUS_CACHE)


def get_messages(channel_id: str = DEFAULT_CHANNEL_ID, count: int = 20) -> dict[str, Any]:
    """Recent channel messages with sender classification."""
    count = max(1, min(int(count), 50))
    code, out, err = _run_script(["read", channel_id, str(count)])
    if code != 0:
        raise NetChatBridgeError((err or out or "read failed")[:300])
    posts = _parse_json_or_raise(out, err)
    messages = []
    for p in posts:
        messages.append({
            "id": p.get("id"),
            "user_id": p.get("user_id"),
            "sender": "bot" if p.get("user_id") == BOT_USER_ID else "owner",
            "message": p.get("message", ""),
            "create_at": p.get("create_at"),
        })
    # oldest first for chat display
    messages.reverse()
    return {"success": True, "channel_id": channel_id, "messages": messages}


def send_message(channel_id: str, text: str) -> dict[str, Any]:
    """Send a message as the bot, with 2-step confirm handled transparently.

    NetChat requires a confirmation round-trip for sends; we replay the exact
    command with --confirmed <hash>. Rate-limited to one send per 3s.

    VN-LANG (02/11/2026, owner yêu cầu): TẦNG CUỐI trước khi tin rời hệ thống —
    mọi tin gửi qua bridge được chuẩn hoá tiếng Việt (trạng thái/mật ngữ kỹ
    thuật → tiếng Việt; số liệu + tên riêng giữ nguyên). Đây là điểm chặn duy
    nhất mọi đường gửi DM đi qua, nên không đường nào bỏ sót.
    """
    global _LAST_SEND_AT
    text = (text or "").strip()
    if not text:
        raise NetChatBridgeError("Message is empty")
    text = _vn_normalize(text)
    if len(text) > 3500:
        raise NetChatBridgeError("Message too long (max 3500 chars)")

    with _NETCHAT_LOCK:
        wait = _MIN_SEND_INTERVAL_SEC - (time.time() - _LAST_SEND_AT)
        if wait > 0:
            time.sleep(wait)

        args = ["send", channel_id, text, "--to-channel"]
        code, out, err = _run_script(args)
        confirm_token = None
        for line in (out or "").splitlines():
            if line.startswith("CONFIRM-REQUIRED:"):
                confirm_token = line.split(":", 1)[1].strip()
                break

        if confirm_token is not None:
            code, out, err = _run_script([*args, "--confirmed", confirm_token])

        _LAST_SEND_AT = time.time()

    if code != 0:
        raise NetChatBridgeError((err or out or "send failed")[:300])
    result = _parse_json_or_raise(out, err)
    post_id = result.get("id") if isinstance(result, dict) else None

    _audit("dashboard_netchat.send", {"channel_id": channel_id, "chars": len(text), "post_id": post_id})
    return {"success": True, "post_id": post_id, "channel_id": channel_id}


def run_command(text: str) -> dict[str, Any]:
    """Execute a NetChat command-center command ('phê duyệt', 'trạng thái'…)
    through the real command router and return its output.

    This is the dashboard equivalent of the owner typing the command in the
    channel. Approval commands follow the same safety rules as the channel
    (questions never trigger state changes; result includes ticket IDs).
    """
    from tools.netchat_command_center import route_message


    text = (text or "").strip()
    if not text:
        raise NetChatBridgeError("Command is empty")
    intent, response = route_message(text)
    _audit("dashboard_netchat.command", {"intent": intent, "text_len": len(text)})
    return {
        "success": True,
        "intent": intent,
        "response": response,
        "note": "" if intent else "Không phải lệnh hệ thống — câu hỏi tự do cần AI hội thoại.",
    }


def _audit(event_type: str, details: dict[str, Any]) -> None:
    try:
        workspace = Path(__file__).resolve().parents[4]
        AuditLogger(workspace).record(event_type, details)
    except Exception:
        pass