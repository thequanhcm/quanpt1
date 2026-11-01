"""Sprint 2 probe: verify Qwen/Qwen3.5-122B-A10B-FP8 serves chat on NetMind gateway.

Key from env, never printed. Measures latency + reasoning token behaviour.
"""
import json
import os
import ssl
import time
import urllib.request

base = os.environ.get("NETMIND_DESKTOP_LLM_BASE_URL", "https://stream-netmind.viettel.vn/aigw/ai/v1").rstrip("/")
key = os.environ.get("HERMES_CUSTOM_NETMIND_API_KEY", "")
model = "Qwen/Qwen3.5-122B-A10B-FP8"

out = {"model": model}

def chat(extra: dict, label: str) -> None:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Bạn là TONY PHAM, trợ lý điều hành số. Trả lời tiếng Việt ngắn gọn."},
            {"role": "user", "content": "Lập kế hoạch 3 bước kiểm tra an toàn hệ thống R0-R5."},
        ],
        "max_tokens": 200,
        "temperature": 0.2,
        "stream": False,
        **extra,
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=90, context=ssl.create_default_context()) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        usage = body.get("usage") or {}
        out[label] = {
            "http": resp.status,
            "wall_s": round(time.perf_counter() - t0, 2),
            "content_head": (body["choices"][0]["message"].get("content") or "")[:150],
            "reasoning_tokens": ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens")),
            "completion_tokens": usage.get("completion_tokens"),
        }
    except urllib.error.HTTPError as e:
        out[label] = {"http": e.code, "error": f"HTTP {e.code}"}
    except Exception as e:
        out[label] = {"error": f"{type(e).__name__}: {e}"}

chat({"reasoning_effort": "low"}, "with_effort_low")
chat({}, "default")

print(json.dumps(out, ensure_ascii=False, indent=2))
