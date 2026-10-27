"""Live smoke V8 — teach qua STREAM path (parity check thật).

POST /api/chat/stream với 'nhớ rằng: <marker>' → parse SSE frames →
verify final frame có teach_note + episode được persist vào brain.db.
Dùng urllib (không curl — bài học UTF-8 git-bash).
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

MARKER = f"V8-SMOKE-2710-{int(time.time())}"
QUERY = f"nhớ rằng: marker smoke V8 {MARKER} — lệnh dạy qua giọng nói phải được lưu dài hạn"


def post_stream(payload: dict, timeout: float = 150.0) -> dict:
    url = "http://127.0.0.1:8766/api/chat/stream"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    frames: list[dict] = []
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        buf = b""
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n\n" in buf:
                frame, buf = buf.split(b"\n\n", 1)
                data_str = b""
                for line in frame.split(b"\n"):
                    if line.startswith(b"data:"):
                        data_str += line[5:].strip()
                if data_str:
                    try:
                        frames.append(json.loads(data_str.decode("utf-8")))
                    except json.JSONDecodeError:
                        pass
    return frames


def count_marker(marker: str) -> int:
    conn = sqlite3.connect(WORKSPACE / "data" / "brain.db")
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM memories WHERE source_ref LIKE 'owner_teach%' AND content LIKE ?",
            (f"%{marker}%",),
        )
        return int(cur.fetchone()[0])
    finally:
        conn.close()


def main() -> None:
    print(f"QUERY: {QUERY[:80]}...")
    before = count_marker(MARKER)
    print(f"episodes BEFORE: {before}")
    frames = post_stream({"message": QUERY})
    types = [f.get("type") for f in frames]
    final = next((f for f in reversed(frames) if f.get("type") == "final"), None)
    print(f"frame types: {types}")
    if final:
        print(f"model: {final.get('model')} | teach_note: {str(final.get('teach_note'))[:100]}")
        print(f"reply head: {str(final.get('reply'))[:150]}")
    time.sleep(0.5)
    after = count_marker(MARKER)
    print(f"episodes AFTER: {after}")
    persisted = after > before
    print(f"\n{'✅ PASS' if persisted and final else '❌ FAIL'}: teach-via-stream persisted={persisted}")
    print(f"MARKER (để đối chiếu DB): {MARKER}")


if __name__ == "__main__":
    main()
