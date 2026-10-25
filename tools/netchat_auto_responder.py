"""Auto-responder for QUAN AI BRAIN on NetChat.

This script:
1. Monitors the NetChat channel 4phc9b1mx78qjq3grccw89u94a
2. Reads new messages from the channel
3. Processes them through QUAN AI BRAIN
4. Sends responses back to the channel

Run continuously to enable 24/7 auto-response.
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

CHANNEL_ID = "4phc9b1mx78qjq3grccw89u94a"
CHANNEL_NAME = "Trợ lý Tony Pham"
LAST_MESSAGE_ID = None

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
    try:
        cmd = [PYTHON_EXE, NETCHAT_SCRIPT, "send", CHANNEL_ID, text, "--to-channel"]
        if confirmed_token:
            cmd.extend(["--confirmed", confirmed_token])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        elif "CONFIRM-REQUIRED" in result.stdout:
            # Extract confirm token and auto-confirm
            for line in result.stdout.split("\n"):
                if line.startswith("CONFIRM-REQUIRED:"):
                    token = line.split(":")[1].strip()
                    print(f"   🔄 Auto-confirming with token: {token}")
                    cmd_with_confirm = [PYTHON_EXE, NETCHAT_SCRIPT, "send", CHANNEL_ID, text, "--to-channel", "--confirmed", token]
                    result2 = subprocess.run(cmd_with_confirm, capture_output=True, text=True, timeout=30)
                    if result2.returncode == 0:
                        return json.loads(result2.stdout)
                    else:
                        return {"error": f"Confirm failed: {result2.stderr}"}
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

def main():
    """Main auto-responder loop."""
    print("=" * 70)
    print("QUAN AI BRAIN — NetChat Auto-Responder")
    print("=" * 70)
    print(f"Channel: {CHANNEL_NAME} ({CHANNEL_ID})")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    print("\nMonitoring for new messages... (Ctrl+C to stop)\n")

    global LAST_MESSAGE_ID
    skip_first = True

    while True:
        try:
            # Read messages
            messages = read_channel_messages(count=5)
            
            if messages:
                # Sort by creation time (newest first)
                messages.sort(key=lambda x: x.get("create_at", 0), reverse=True)
                
                for msg in messages:
                    msg_id = msg.get("id")
                    user_id = msg.get("user_id")
                    message_text = msg.get("message", "")
                    
                    # Skip bot's own messages
                    if user_id == "edojmne9d7gcxx8axu1mzas3pr":
                        continue
                    
                    # Skip first iteration (already seen messages)
                    if skip_first:
                        if LAST_MESSAGE_ID is None:
                            LAST_MESSAGE_ID = msg_id
                        continue
                    
                    # New message detected
                    if msg_id != LAST_MESSAGE_ID:
                        timestamp = datetime.fromtimestamp(
                            msg.get("create_at", 0) / 1000, tz=timezone.utc
                        )
                        print(f"\n📩 New message at {timestamp.strftime('%H:%M:%S')}:")
                        print(f"   {message_text[:100]}...")
                        
                        # Process with AI (NO "thinking" placeholder — direct response)
                        print("   🤖 Processing...")
                        response = process_message_with_ai(message_text)
                        
                        # Send response
                        print("   📤 Sending response...")
                        result = send_message(response)
                        
                        if "confirm_required" in result:
                            print("   ⚠️  Confirm required. Auto-confirming...")
                            # Extract command and re-run
                            cmd_str = result["command"].replace("python3 ", "")
                            subprocess.run(cmd_str, shell=True, timeout=30)
                            print("   ✅ Response sent!")
                        elif "error" in result:
                            print(f"   ❌ Error: {result['error']}")
                        else:
                            print("   ✅ Response sent!")
                        
                        LAST_MESSAGE_ID = msg_id
            
            # Wait 5 seconds
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