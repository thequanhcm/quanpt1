"""Sprint 2 E2E — REAL Pi 5 hardware test (owner instructed Pi is online).

Flow: PC Core synthesizes Vietnamese TTS (vi-VN-HoaiMyNeural) -> sends the
speak command with audio_base64 + mouth-sync timeline to the Pi 5 kiosk daemon
over Wi-Fi -> polls kiosk status to verify the avatar transitions to SPEAKING
and then back to IDLE. No simulation: every state is read from the Pi daemon.
"""
import base64
import json
import sys
import time
import urllib.request

sys.path.insert(0, "src")

PI_BASE = "http://192.168.1.21:8768"


def kiosk_get(path: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(PI_BASE + path, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def kiosk_post(path: str, body: dict, timeout: float = 8.0) -> dict:
    req = urllib.request.Request(
        PI_BASE + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    print("[pi-e2e] 1. Kiosk daemon reachable?")
    status = kiosk_get("/api/kiosk/status")
    print(f"[pi-e2e]    core_connected={status.get('core_connected')} kiosk_running={status.get('kiosk_running')} "
          f"avatar={status.get('avatar_state')} device={status.get('device_id')}")
    if not status.get("kiosk_running"):
        print("[pi-e2e] RESULT: FAIL (kiosk not running)")
        return 1

    print("[pi-e2e] 2. PC Core TTS synthesis (vi-VN-HoaiMyNeural)...")
    from quan_ai_brain.voice.tts_config import GLOBAL_TTS_MANAGER
    from quan_ai_brain.voice.mouth_sync import MouthSyncEngine

    text = "Dạ chào anh Quân. Em là TONY PHAM, em rất vui được gặp anh trên Raspberry Pi 5."
    audio_bytes, err = GLOBAL_TTS_MANAGER.synthesize_audio(text)
    if err or not audio_bytes:
        print(f"[pi-e2e] RESULT: FAIL (TTS error: {err})")
        return 1
    print(f"[pi-e2e]    audio={len(audio_bytes)} bytes, voice={GLOBAL_TTS_MANAGER.active_voice_id}")

    timeline = MouthSyncEngine(frame_interval_ms=50).generate_timeline("sprint2_pi5_e2e", text)
    print(f"[pi-e2e]    timeline: {len(timeline.frames)} frames, {timeline.total_duration_ms}ms")

    print("[pi-e2e] 3. Sending speak command to Pi 5...")
    resp = kiosk_post("/api/kiosk/control", {
        "action": "speak",
        "text": text,
        "state": "SPEAKING",
        "duration_ms": timeline.total_duration_ms,
        "timeline": timeline.to_dict(),
        "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
    })
    print(f"[pi-e2e]    daemon response: {json.dumps(resp, ensure_ascii=False)[:160]}")

    print("[pi-e2e] 4. Polling avatar state for 15s...")
    speaking_seen = False
    idle_after = False
    t0 = time.time()
    while time.time() - t0 < 15:
        s = kiosk_get("/api/kiosk/status")
        state = s.get("avatar_state")
        if state == "SPEAKING":
            speaking_seen = True
        if speaking_seen and state == "IDLE":
            idle_after = True
            break
        time.sleep(0.4)
    transcript = kiosk_get("/api/kiosk/status").get("transcript", "")
    print(f"[pi-e2e]    speaking_seen={speaking_seen} returned_to_idle={idle_after}")
    print(f"[pi-e2e]    transcript on Pi: {transcript[:80]!r}")

    ok = speaking_seen and idle_after
    print("[pi-e2e] RESULT:", "PASS" if ok else "PARTIAL (see flags above)")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
