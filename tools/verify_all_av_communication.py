import sys
import urllib.request
import json

sys.stdout.reconfigure(encoding="utf-8")

# 1. Turn camera ON
req_on = urllib.request.Request(
    "http://127.0.0.1:8766/api/executive/edge/camera/control",
    data=b'{"action":"camera_on"}',
    headers={"Content-Type": "application/json"}
)
res_on = json.loads(urllib.request.urlopen(req_on, timeout=5).read().decode("utf-8"))
print("1. Camera ON:", res_on)

# 2. Test Camera
req_test = urllib.request.Request(
    "http://127.0.0.1:8766/api/executive/edge/camera/control",
    data=b'{"action":"test_camera"}',
    headers={"Content-Type": "application/json"}
)
res_test = json.loads(urllib.request.urlopen(req_test, timeout=5).read().decode("utf-8"))
print("2. Test Camera:", res_test)

# 3. Take Snapshot
req_snap = urllib.request.Request(
    "http://127.0.0.1:8766/api/executive/edge/camera/snapshot"
)
res_snap = json.loads(urllib.request.urlopen(req_snap, timeout=10).read().decode("utf-8"))
print("3. Snapshot:")
print("   - Success:", res_snap.get("success"))
print("   - Snapshot ID:", res_snap.get("snapshot_id"))
print("   - Size (bytes):", res_snap.get("size_bytes"))
print("   - SHA-256:", res_snap.get("sha256_hash"))
print("   - Captured at:", res_snap.get("timestamp"))

# 4. Test Microphone
req_mic = urllib.request.Request(
    "http://127.0.0.1:8766/api/executive/edge/audio/control",
    data=b'{"action":"test_mic"}',
    headers={"Content-Type": "application/json"}
)
res_mic = json.loads(urllib.request.urlopen(req_mic, timeout=8).read().decode("utf-8"))
print("4. Microphone Test:")
print("   - Success:", res_mic.get("success"))
print("   - Audio level (dB):", res_mic.get("audio_level_db"))
print("   - Device:", res_mic.get("device"))
print("   - Message:", res_mic.get("message"))

# 5. Test Voice Communication
req_voice = urllib.request.Request(
    "http://127.0.0.1:8766/api/voice/interact",
    data=json.dumps({"query": "Tony ơi, em có nghe rõ anh nói không?"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
res_voice = json.loads(urllib.request.urlopen(req_voice, timeout=30).read().decode("utf-8"))
print("5. Voice Communication Test:")
print("   - Success:", res_voice.get("success"))
print("   - Response:", res_voice.get("response_text"))
print("   - Audio TTS Base64:", bool(res_voice.get("audio_base64")))
print("   - Mouth timeline visemes:", len(res_voice.get("mouth_timeline", [])))
