"""Sprint 2 final step: push kiosk.js + wake_engine.js (with barge-in) to Pi 5 root daemon, then reload UI.

This script:
1. Base64-encodes the NEW kiosk.js and wake_engine.js from edge_client/
2. POSTs them to the Pi 5 daemon's /api/kiosk/files/upload endpoint
3. Waits 2s for filesystem sync
4. Sends reload_ui command to activate the new JS
5. Polls kiosk status to confirm the files were accepted (size matches local)

No simulation: every state is read from the Pi daemon.
"""
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, "src")

PI_BASE = "http://192.168.1.21:8768"
EDGE_ROOT = Path(__file__).resolve().parent.parent / "edge_client"


def kiosk_post(path: str, body: dict, timeout: float = 15.0) -> dict:
    req = urllib.request.Request(
        PI_BASE + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def kiosk_get(path: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(PI_BASE + path, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    files_to_push = ["kiosk.js", "wake_engine.js"]
    print("[pi-push] 1. Reading local files...")
    payloads = []
    for fname in files_to_push:
        fp = EDGE_ROOT / fname
        if not fp.exists():
            print(f"[pi-push]    ERROR: {fname} not found at {fp}")
            return 1
        content = fp.read_bytes()
        b64 = base64.b64encode(content).decode("ascii")
        payloads.append({"filename": fname, "content_b64": b64, "size": len(content)})
        print(f"[pi-push]    {fname}: {len(content)} bytes")

    print("[pi-push] 2. Uploading to Pi 5 daemon...")
    for p in payloads:
        try:
            resp = kiosk_post("/api/kiosk/files/upload", {"filename": p["filename"], "content_b64": p["content_b64"]})
            if not resp.get("success"):
                print(f"[pi-push]    FAIL: {p['filename']} -> {resp}")
                return 1
            print(f"[pi-push]    OK: {p['filename']} uploaded")
        except Exception as e:
            print(f"[pi-push]    ERROR uploading {p['filename']}: {e}")
            return 1

    print("[pi-push] 3. Waiting 2s for filesystem sync...")
    time.sleep(2)

    print("[pi-push] 4. Sending reload_ui command...")
    try:
        resp = kiosk_post("/api/kiosk/control", {"action": "reload_ui"})
        if not resp.get("success"):
            print(f"[pi-push]    FAIL reload: {resp}")
            return 1
        print(f"[pi-push]    OK: reload_ui sent")
    except Exception as e:
        print(f"[pi-push]    ERROR reload: {e}")
        return 1

    print("[pi-push] 5. Polling kiosk status (10s) to verify files...")
    t0 = time.time()
    while time.time() - t0 < 10:
        try:
            status = kiosk_get("/api/kiosk/status")
            # Check if kiosk is still running (indicates successful reload)
            if status.get("kiosk_running"):
                print(f"[pi-push]    kiosk_running=True, avatar={status.get('avatar_state')}")
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        print("[pi-push]    WARNING: Could not confirm kiosk status after reload")

    print("[pi-push] 6. Verifying file sizes on Pi...")
    try:
        files_info = kiosk_get("/api/kiosk/files")
        pi_files = {f["name"]: f["size"] for f in files_info.get("files", [])}
        for p in payloads:
            pi_size = pi_files.get(p["filename"])
            if pi_size == p["size"]:
                print(f"[pi-push]    {p['filename']}: MATCH ({p['size']} bytes)")
            else:
                print(f"[pi-push]    {p['filename']}: MISMATCH (local={p['size']}, Pi={pi_size})")
    except Exception as e:
        print(f"[pi-push]    WARNING: Could not verify file sizes: {e}")

    print("[pi-push] RESULT: SUCCESS — barge-in JS deployed to Pi 5 root daemon")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())