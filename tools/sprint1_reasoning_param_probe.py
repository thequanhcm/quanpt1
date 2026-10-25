"""Sprint 1 pre-work probe: discover which reasoning-control parameters the NetMind
gateway accepts for zai-org/GLM-5.3-Flash.

Read-only API probes with tiny max_tokens. Key stays in process env; never printed.
Success criterion: find a param that keeps HTTP 200 AND reduces reasoning_tokens to ~0
without killing answer quality.
"""
import json
import os
import ssl
import time
import urllib.request

base = os.environ.get("NETMIND_DESKTOP_LLM_BASE_URL", "https://stream-netmind.viettel.vn/aigw/ai/v1").rstrip("/")
key = os.environ.get("HERMES_CUSTOM_NETMIND_API_KEY", "")
model = "zai-org/GLM-5.3-Flash"

variants = [
    ("baseline", {}),
    ("reasoning_effort_low", {"reasoning_effort": "low"}),
    ("reasoning_effort_minimal", {"reasoning_effort": "minimal"}),
    ("thinking_disabled", {"thinking": {"type": "disabled"}}),
    ("enable_thinking_false", {"enable_thinking": False}),
]

prompt = "Trả lời đúng 1 câu: thủ đô của Việt Nam là gì?"

results = []
for name, extra in variants:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 60,
        "temperature": 0.0,
        "stream": False,
        **extra,
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    ctx = ssl.create_default_context()
    row = {"variant": name, "extra": extra}
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=45, context=ctx) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        row["http"] = resp.status
        row["wall_s"] = round(time.perf_counter() - t0, 2)
        row["content"] = (body["choices"][0]["message"].get("content") or "")[:120]
        row["reasoning_tokens"] = (body.get("usage", {}).get("completion_tokens_details", {}) or {}).get("reasoning_tokens")
        row["completion_tokens"] = body.get("usage", {}).get("completion_tokens")
    except urllib.error.HTTPError as e:
        row["http"] = e.code
        row["error"] = f"HTTP {e.code}"
        try:
            row["body_snip"] = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"
    results.append(row)
    time.sleep(0.3)

print(json.dumps(results, ensure_ascii=False, indent=2))
