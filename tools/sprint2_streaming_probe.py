"""Sprint 2 probe: does the NetMind gateway support SSE streaming for GLM-5.3-Flash?

Reads the first few SSE events, then stops. Key stays in env, never printed.
"""
import json
import os
import ssl
import time
import urllib.request

base = os.environ.get("NETMIND_DESKTOP_LLM_BASE_URL", "https://stream-netmind.viettel.vn/aigw/ai/v1").rstrip("/")
key = os.environ.get("HERMES_CUSTOM_NETMIND_API_KEY", "")

payload = {
    "model": "zai-org/GLM-5.3-Flash",
    "messages": [{"role": "user", "content": "Dem tu 1 den 5, moi so mot dong."},
                 {"role": "system", "content": "Tra loi ngan gon."}],
    "max_tokens": 120,
    "temperature": 0.0,
    "stream": True,
    "reasoning_effort": "low",
}
req = urllib.request.Request(
    base + "/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
             "Accept": "text/event-stream"},
    method="POST",
)
out = {"events": [], "errors": []}
t0 = time.perf_counter()
first_event_s = None
try:
    with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as resp:
        out["http"] = resp.status
        out["content_type"] = resp.headers.get("Content-Type", "")
        count = 0
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if first_event_s is None:
                first_event_s = round(time.perf_counter() - t0, 2)
            out["events"].append(line[:160])
            count += 1
            if count >= 8:
                break
        out["first_event_s"] = first_event_s
        out["sample_count"] = count
except Exception as e:
    out["errors"].append(type(e).__name__ + ": " + str(e))

print(json.dumps(out, ensure_ascii=False, indent=2))
