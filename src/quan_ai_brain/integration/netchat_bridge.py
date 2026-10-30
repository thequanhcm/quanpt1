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
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.core.audit import AuditLogger

NETCHAT_SCRIPT = Path(
    r"C:\Users\DELL\AppData\Local\netmind_desktop\skills\bot-netchat\netchat_bot.py"
)
NETCHAT_PYTHON = Path(
    r"C:\Users\DELL\AppData\Local\netmind_desktop\netmind-agent\venv\Scripts\python.exe"
)

DEFAULT_CHANNEL_ID = "4phc9b1mx78qjq3grxcw89u94a"
DEFAULT_CHANNEL_NAME = "Trợ lý Tony Pham"
BOT_USER_ID = "edojmne9d7gcxx8axu1mzas3pr"

# Simple single-flight lock: dashboard requests are serialized to avoid
# hammering the NetChat API (HTTP 429 rate limit when sending in bursts).
_NETCHAT_LOCK = threading.Lock()
_LAST_SEND_AT = 0.0
_MIN_SEND_INTERVAL_SEC = 3.0


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
    """Channel + bot status. Read-only, no message bodies."""
    code, out, err = _run_script(["whoami"])
    if code != 0:
        raise NetChatBridgeError((err or out or "whoami failed")[:300])
    me = _parse_json_or_raise(out, err)
    return {
        "success": True,
        "bot": {
            "id": me.get("id"),
            "username": me.get("username"),
            "is_bot": me.get("is_bot", True),
        },
        "channel": {"id": channel_id, "name": DEFAULT_CHANNEL_NAME},
        "responder_hint": "tools/netchat_auto_responder.py (poll 5s)",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    }


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
    """
    global _LAST_SEND_AT
    text = (text or "").strip()
    if not text:
        raise NetChatBridgeError("Message is empty")
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
