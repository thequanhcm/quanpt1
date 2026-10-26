"""Auto-responder for QUAN AI BRAIN on NetChat.

This script:
1. Monitors the NetChat channel 4phc9b1mx78qjq3grccw89u94a
2. Reads new messages from the channel
3. Processes them through QUAN AI BRAIN
4. Sends responses back to the channel

Run continuously to enable 24/7 auto-response.
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# 24/7 reboot-proof (27/10/2026): watchdog giám sát responder qua "heartbeat"
# — file log được touch mỗi vòng poll. Không có heartbeat => responder chết/stuck
# và watchdog (check_netchat_bot) sẽ cảnh báo. Đây là file duy nhất responder ghi.
HEARTBEAT_PATH = Path(__file__).resolve().parent.parent / "logs" / "netchat_responder_heartbeat.log"


def touch_heartbeat() -> None:
    """Update heartbeat file mtime (watchdog reads freshness from this)."""
    try:
        HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_PATH.touch()
    except Exception:
        pass

# 27/10/2026 (owner): "trợ lý không hỏi lòng vòng" — nếu câu trả lời AI đang
# XIN PHÉP làm việc probe CHỈ ĐỌC (an toàn tuyệt đối), responder TỰ CHẠY probe
# thật ngay và trả KẾT QUẢ thay vì câu hỏi. Không ai phải trả lời "ok" cho
# việc bot tự làm được.
_PERMISSION_ASK_RE = re.compile(
    r"(cho phép em|cho em chạy|xác nhận cho em|em chờ lệnh|chờ anh xác nhận|"
    r"anh xác nhận[^\n]*nhé\?|xin phép anh|anh cho phép)",
    re.IGNORECASE,
)
_SAFE_PROBE_RE = re.compile(r"(probe|kiểm tra|trạng thái|xác minh)", re.IGNORECASE)


def _maybe_autorun_probe(ai_response: str) -> str | None:
    """AI vừa hỏi xin phép probe chỉ-đọc? → chạy thật, trả kết quả (không hỏi lại)."""
    if not ai_response:
        return None
    if not (_PERMISSION_ASK_RE.search(ai_response) and _SAFE_PROBE_RE.search(ai_response)):
        return None
    try:
        from tools.netchat_command_center import _reprobe_full
        fresh = _reprobe_full("probe lại toàn hệ thống")
    except Exception:
        return None
    # Giữ phần phân tích của AI (trước mục 'Đề xuất'), thay phần xin phép bằng kết quả thật
    head = ai_response.split("Đề xuất")[0].strip()
    return f"{head}\n\n{fresh}" if head else fresh

CHANNEL_ID = "4phc9b1mx78qjq3grxcw89u94a"  # kênh 'Trợ lý Tony Pham' (đã sửa typo c→x)
CHANNEL_NAME = "Trợ lý Tony Pham"
BOT_USER_ID = "edojmne9d7gcxx8axu1mzas3pr"
CATCHUP_WINDOW_MIN = 60  # sau restart: chỉ trả lời tin trong N phút qua

NETCHAT_SCRIPT = r"C:\Users\DELL\AppData\Local\netmind_desktop\skills\bot-netchat\netchat_bot.py"
PYTHON_EXE = r"C:\Users\DELL\AppData\Local\netmind_desktop\netmind-agent\venv\Scripts\python.exe"

def read_channel_messages(count=10):
    """Read recent messages from the channel."""
    try:
        result = subprocess.run(
            [PYTHON_EXE, NETCHAT_SCRIPT, "read", CHANNEL_ID, str(count)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Error reading messages: {e}")
    return []

def send_message(text, confirmed_token=None):
    """Send message to the channel."""
    def _parse(stdout):
        try:
            return json.loads(stdout)
        except (ValueError, TypeError):
            # success output may be plain text — don't crash after a real send
            return {"ok": True, "raw": (stdout or "").strip()[:200]}

    try:
        cmd = [PYTHON_EXE, NETCHAT_SCRIPT, "send", CHANNEL_ID, text, "--to-channel"]
        if confirmed_token:
            cmd.extend(["--confirmed", confirmed_token])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return _parse(result.stdout)
        elif "CONFIRM-REQUIRED" in result.stdout:
            # Extract confirm token and auto-confirm
            for line in result.stdout.split("\n"):
                if line.startswith("CONFIRM-REQUIRED:"):
                    token = line.split(":", 1)[1].strip()
                    print(f"   🔄 Auto-confirming with token: {token}")
                    cmd_with_confirm = [PYTHON_EXE, NETCHAT_SCRIPT, "send", CHANNEL_ID, text, "--to-channel", "--confirmed", token]
                    result2 = subprocess.run(cmd_with_confirm, capture_output=True, text=True, timeout=30)
                    if result2.returncode == 0:
                        return _parse(result2.stdout)
                    else:
                        return {"error": f"Confirm failed: {result2.stderr or result2.stdout}"}
        return {"error": result.stderr if result.stderr else result.stdout}
    except Exception as e:
        return {"error": str(e)}

def process_message_with_ai(message_text):
    """Process message through QUAN AI BRAIN and get response."""
    try:
        # Call QUAN AI BRAIN API using urllib (no requests dependency)
        import urllib.request
        import urllib.error
        import json
        
        data = json.dumps({
            "query": message_text,
            "session_id": "netchat_auto_responder",
            "model": "zai-org/GLM-5.3-Flash",
            "reasoning_effort": "low"  # CRITICAL: GLM-5.3-Flash requires this!
        }).encode('utf-8')
        
        req = urllib.request.Request(
            "http://127.0.0.1:8765/api/chat",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("answer", "Xin lỗi, em chưa xử lý được yêu cầu này.")
    except urllib.error.HTTPError as e:
        return f"⚠️ Lỗi HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"⚠️ Không kết nối được server: {e.reason}. Vui lòng kiểm tra server QUAN AI BRAIN đang chạy."
    except Exception as e:
        return f"⚠️ Lỗi xử lý: {str(e)}"


def process_message(message_text, sender_user_id="", chat_session_id="default"):
    """Route: ok-confirm → system commands → approval cards → AI fallback.

    The channel is a dedicated owner<->assistant command center — no @bot
    needed. Commands like 'phê duyệt' execute real system actions; other
    messages fall through to the conversational AI. sender_user_id enables
    owner-identity verification in the approval adapter (V3 Section 5.2).

    27/10/2026 (owner): intent 'ok_silent' = anh xác nhận nhưng không có việc
    chờ → KHÔNG gửi gì cả (không lòng vòng). 'ok_confirm' = đã thực thi việc
    chờ xác nhận.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from tools.netchat_command_center import route_message
        intent, response = route_message(
            message_text, sender_user_id=sender_user_id, chat_session_id=chat_session_id
        )
        if intent == "ok_silent":
            print("   🔇 'ok' nhưng không có việc chờ xác nhận → im lặng (không spam).")
            return None  # responder sẽ không gửi gì
        if intent is not None:
            print(f"   ⚡ System command: {intent}")
            return response
    except Exception as e:
        print(f"   ⚠️ Command router error: {e}")
    ai_reply = process_message_with_ai(message_text)
    autorun = _maybe_autorun_probe(ai_reply)
    if autorun is not None:
        print("   🤖 AI hỏi xin phép probe chỉ-đọc → tự chạy probe thật, trả kết quả.")
        return autorun
    return ai_reply

def main():
    """Main auto-responder loop.

    Message tracking: a bounded set of seen message IDs. On startup, all
    existing messages are marked seen EXCEPT the newest ones (within
    CATCHUP_WINDOW_MIN) which are answered — so a restart never replays the
    whole history but still responds to fresh unanswered owner messages.
    """
    print("=" * 70)
    print("QUAN AI BRAIN — NetChat Auto-Responder (Command Center 2 chiều)")
    print("=" * 70)
    print(f"Channel: {CHANNEL_NAME} ({CHANNEL_ID})")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    print("\nMonitoring for new messages... (Ctrl+C to stop)\n")

    seen_ids: set[str] = set()
    first_poll = True
    iteration = 0
    catchup_window_ms = CATCHUP_WINDOW_MIN * 60 * 1000

    while True:
        iteration += 1
        touch_heartbeat()
        try:
            messages = read_channel_messages(count=10)

            if messages:
                # oldest first so replies land in chronological order
                messages.sort(key=lambda x: x.get("create_at", 0))

                if first_poll:
                    now_ms = time.time() * 1000
                    fresh = [
                        m for m in messages
                        if m.get("user_id") != BOT_USER_ID
                        and now_ms - m.get("create_at", 0) <= catchup_window_ms
                    ]
                    for m in messages:
                        seen_ids.add(m.get("id"))
                    first_poll = False
                    # answer at most the 5 newest fresh messages after restart
                    fresh = sorted(fresh, key=lambda x: x.get("create_at", 0))[-5:]
                    if fresh:
                        print(f"[STARTUP] {len(fresh)} tin nhắn mới trong {CATCHUP_WINDOW_MIN} phút qua — sẽ trả lời.")
                        for m in fresh:
                            seen_ids.discard(m.get("id"))
                    else:
                        print("[STARTUP] Không có tin mới nào cần trả lời.")
                else:
                    fresh = [
                        m for m in messages
                        if m.get("id") not in seen_ids and m.get("user_id") != BOT_USER_ID
                    ]

                for msg in fresh:
                    msg_id = msg.get("id")
                    message_text = (msg.get("message") or "").strip()
                    if not message_text:
                        seen_ids.add(msg_id)
                        continue
                    timestamp = datetime.fromtimestamp(
                        msg.get("create_at", 0) / 1000, tz=timezone.utc
                    )
                    print(f"\n📩 New message at {timestamp.strftime('%H:%M:%S')}:")
                    print(f"   {message_text[:100]}")

                    print("   🤖 Processing...")
                    response = process_message(message_text, sender_user_id=msg.get("user_id", ""), chat_session_id=CHANNEL_ID)

                    if response is None:
                        # ok_silent: xác nhận không kèm việc nào → không gửi gì
                        seen_ids.add(msg_id)
                        continue

                    print("   📤 Sending response...")
                    result = send_message(response)
                    if "error" in result:
                        print(f"   ❌ Error: {result['error']}")
                    else:
                        print("   ✅ Response sent!")

                    seen_ids.add(msg_id)
                    # NetChat rate limit (HTTP 429) khi gửi dồn — nghỉ giữa các reply
                    time.sleep(3)

                # keep the seen set bounded
                if len(seen_ids) > 500:
                    seen_ids = set(sorted(seen_ids)[-200:])

            if iteration % 12 == 0:
                print(f"[DEBUG] Iteration {iteration}, seen={len(seen_ids)}")

            time.sleep(5)

        except KeyboardInterrupt:
            print("\n\n🛑 Auto-responder stopped by user")
            break
        except Exception as e:
            print(f"\n⚠️  Error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)