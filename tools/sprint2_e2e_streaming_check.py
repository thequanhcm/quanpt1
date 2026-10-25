"""Sprint 2 E2E: real streaming chat through the local API server + live gateway.

Starts the real BrainAPIHandler server on a random port, POSTs /api/chat/stream,
and prints the SSE event sequence. The API key is read from the process
environment INSIDE the server/provider — never printed, never logged.
"""
import json
import sys
import threading
import time
import urllib.request

sys.path.insert(0, "src")

from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer  # noqa: E402


def main() -> int:
    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base = f"http://{host}:{port}"
    time.sleep(0.3)
    print(f"[e2e] server on {base}")

    body = json.dumps({
        "query": "Em hãy giới thiệu bản thân trong 2 câu tiếng Việt.",
        "session_id": "sprint2_e2e_stream",
    }).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/chat/stream",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    deltas = 0
    first_delta_s = None
    final_reply = ""
    meta = None
    with urllib.request.urlopen(req, timeout=90) as resp:
        ctype = resp.headers.get("Content-Type", "")
        print(f"[e2e] HTTP {resp.status} content-type={ctype}")
        buf = b""
        for chunk in iter(lambda: resp.read(1), b""):
            buf += chunk
            while b"\n\n" in buf:
                frame, buf = buf.split(b"\n\n", 1)
                line = frame.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                ev = json.loads(line[5:].strip())
                etype = ev.get("type")
                if etype == "meta":
                    meta = ev
                    print(f"[e2e] meta: model={ev.get('model')} tier={ev.get('tier')}")
                elif etype == "delta":
                    deltas += 1
                    if first_delta_s is None:
                        first_delta_s = round(time.perf_counter() - t0, 2)
                elif etype == "final":
                    final_reply = ev.get("reply", "")
                    print(f"[e2e] final: model={ev.get('model')} elapsed_ms={ev.get('elapsed_ms')} "
                          f"finish={ev.get('finish_reason')} persisted={'persistence' in ev}")
                elif etype == "error":
                    print(f"[e2e] ERROR: {ev.get('code')}: {ev.get('message', '')[:200]}")
                    server.shutdown()
                    return 1

    server.shutdown()
    total_s = round(time.perf_counter() - t0, 2)
    print(f"[e2e] deltas={deltas} first_delta_at={first_delta_s}s total={total_s}s")
    print(f"[e2e] reply_head={final_reply[:160]!r}")
    ok = deltas > 0 and bool(final_reply) and meta is not None
    print("[e2e] RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
