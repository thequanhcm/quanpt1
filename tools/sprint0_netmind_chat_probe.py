"""Sprint 0.6b: minimal chat smoke test against zai-org/GLM-5.3-Flash via NetMind.

One tiny completion. Key stays in process env, never printed. No secrets in output.
"""
import json
import os
import ssl
import time
import urllib.request

base = os.environ.get("NETMIND_DESKTOP_LLM_BASE_URL", "https://stream-netmind.viettel.vn/aigw/ai/v1").rstrip("/")
key = os.environ.get("HERMES_CUSTOM_NETMIND_API_KEY", "")
model = "zai-org/GLM-5.3-Flash"

payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": "Bạn là TONY PHAM, trợ lý điều hành số của anh Quân. Trả lời tiếng Việt ngắn gọn."},
        {"role": "user", "content": "Chào em, hãy giới thiệu một câu về bản thân."},
    ],
    "max_tokens": 80,
    "temperature": 0.2,
    "stream": False,
}

req = urllib.request.Request(
    base + "/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    method="POST",
)
ctx = ssl.create_default_context()
out = {"model": model, "base_url": base}
t0 = time.perf_counter()
try:
    with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    out["http_status"] = resp.status
    out["wall_s"] = round(time.perf_counter() - t0, 2)
    out["content_preview"] = body["choices"][0]["message"]["content"][:300]
    out["usage"] = body.get("usage")
    out["finish_reason"] = body["choices"][0].get("finish_reason")
except Exception as e:
    out["error"] = f"{type(e).__name__}: {e}"

print(json.dumps(out, ensure_ascii=False, indent=2))
