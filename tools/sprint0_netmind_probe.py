"""Sprint 0.6 probe: verify NetMind GLM-5.3 model catalog availability.

Read-only GET /models. The API key is read from the process environment
INSIDE this script and is NEVER printed, logged, or written to any file.
Only the model catalog (public metadata) is printed.
"""
import json
import os
import ssl
import urllib.request

base = os.environ.get("NETMIND_DESKTOP_LLM_BASE_URL", "").rstrip("/")
if not base:
    base = "https://stream-netmind.viettel.vn/aigw/ai/v1"
key = os.environ.get("HERMES_CUSTOM_NETMIND_API_KEY", "")

out = {"base_url": base, "key_present": bool(key)}

if not key:
    out["result"] = "NO_KEY_IN_ENV"
else:
    req = urllib.request.Request(
        base + "/models",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        method="GET",
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        out["http_status"] = resp.status
        models = [m.get("id") for m in body.get("data", [])]
        out["model_count"] = len(models)
        out["glm_models"] = [m for m in models if m and "glm" in m.lower()]
        out["all_models"] = models
    except Exception as e:
        code = getattr(e, "code", None)
        out["http_status"] = code
        out["result"] = f"FAILED: {type(e).__name__}" + (f" (HTTP {code})" if code else "")

print(json.dumps(out, ensure_ascii=False, indent=2))
