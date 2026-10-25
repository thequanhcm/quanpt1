"""Manual test for NetChat auto-responder - Debug step by step."""
import json
import subprocess
import sys
import urllib.request
import urllib.error

CHANNEL_ID = "4phc9b1mx78qjq3grxcw89u94a"
NETCHAT_SCRIPT = r"C:\Users\DELL\AppData\Local\netmind_desktop\skills\bot-netchat\netchat_bot.py"
PYTHON_EXE = r"C:\Users\DELL\AppData\Local\netmind_desktop\netmind-agent\venv\Scripts\python.exe"

print("=" * 70)
print("NETCHAT AUTO-RESPONDER DEBUG TEST")
print("=" * 70)

# Step 1: Read messages
print("\n[1/3] Reading messages from channel...")
result = subprocess.run(
    [PYTHON_EXE, NETCHAT_SCRIPT, "read", CHANNEL_ID, "5"],
    capture_output=True, text=True, timeout=30
)

if result.returncode != 0:
    print(f"❌ Failed to read messages: {result.stderr}")
    sys.exit(1)

messages = json.loads(result.stdout)
print(f"✅ Found {len(messages)} messages")

# Find latest non-bot message
latest_user_msg = None
for msg in reversed(messages):
    if not msg.get("user_id", "").startswith("edojmne"):  # Not bot
        latest_user_msg = msg
        break

if not latest_user_msg:
    print("⚠️ No user messages found")
    sys.exit(0)

print(f"✅ Latest user message: '{latest_user_msg['message'][:50]}...'")
print(f"   ID: {latest_user_msg['id']}")

# Step 2: Process with AI
print("\n[2/3] Processing with QUAN AI BRAIN...")
try:
    data = json.dumps({
        "query": latest_user_msg["message"],
        "session_id": "debug_test",
        "model": "zai-org/GLM-5.3-Flash",
        "reasoning_effort": "low"  # CRITICAL: GLM-5.3-Flash requires this!
    }).encode('utf-8')
    
    req = urllib.request.Request(
        "http://127.0.0.1:8765/api/chat",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        result_api = json.loads(response.read().decode('utf-8'))
        response_text = result_api.get("answer", "No answer")
        
    print(f"✅ AI Response received ({len(response_text)} chars)")
    print(f"   Preview: {response_text[:100]}...")
    
except Exception as e:
    print(f"❌ API Error: {e}")
    sys.exit(1)

# Step 3: Send response
print("\n[3/3] Sending response...")
response_cmd = [
    PYTHON_EXE, NETCHAT_SCRIPT, "send", CHANNEL_ID, response_text, "--to-channel"
]

result_send = subprocess.run(response_cmd, capture_output=True, text=True, timeout=30)

if result_send.returncode != 0:
    if "CONFIRM-REQUIRED" in result_send.stdout:
        print("⚠️ Confirm required, extracting token...")
        for line in result_send.stdout.split("\n"):
            if line.startswith("CONFIRM-REQUIRED:"):
                token = line.split(":")[1].strip()
                print(f"   Token: {token}")
                
                # Auto-confirm
                confirm_cmd = [
                    PYTHON_EXE, NETCHAT_SCRIPT, "send", CHANNEL_ID, response_text,
                    "--to-channel", "--confirmed", token
                ]
                result_confirm = subprocess.run(confirm_cmd, capture_output=True, text=True, timeout=30)
                
                if result_confirm.returncode == 0:
                    print("✅ Response sent successfully (auto-confirm)!")
                else:
                    print(f"❌ Confirm failed: {result_confirm.stderr}")
                    sys.exit(1)
                break
    else:
        print(f"❌ Send failed: {result_send.stderr}")
        sys.exit(1)
else:
    print("✅ Response sent successfully!")

print("\n" + "=" * 70)
print("✅ DEBUG TEST COMPLETE")
print("=" * 70)