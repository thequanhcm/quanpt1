"""Sprint 0 runtime probe: measure real cold/warm latency of Ollama models.

Read-only diagnostics. No secrets involved. Writes nothing outside reports/.
"""
import json
import time
import urllib.request

BASE = "http://127.0.0.1:11434"


def post(path: str, payload: dict, timeout: float = 120.0) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return {"wall_s": round(time.perf_counter() - t0, 3), "data": data}


def measure_generate(model: str, prompt: str, num_predict: int = 64) -> dict:
    r = post("/api/generate", {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict},
    })
    d = r["data"]
    return {
        "model": model,
        "wall_s": r["wall_s"],
        "load_s": d.get("load_duration", 0) / 1e9,
        "eval_count": d.get("eval_count", 0),
        "eval_s": round(d.get("eval_duration", 0) / 1e9, 3),
        "tok_s": round(d.get("eval_count", 0) / (d.get("eval_duration", 1) / 1e9), 1),
        "prompt_chars": len(prompt),
        "response_chars": len(d.get("response", "")),
    }


def measure_embed(model: str, text: str) -> dict:
    r = post("/api/embed", {"model": model, "input": text})
    vec = r["data"].get("embeddings", [[]])[0]
    return {"model": model, "wall_s": r["wall_s"], "dim": len(vec), "text_chars": len(text)}


results = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "host": BASE}

# --- warm-up state check: is anything already loaded?
try:
    ps = post("/api/ps", {}, timeout=5)
    results["loaded_before"] = [m.get("model") for m in ps["data"].get("models", [])]
except Exception as e:
    results["loaded_before"] = f"error: {e}"

# --- BGE-M3: cold then warm (matches the 9.64s claim investigation)
try:
    results["bge_m3_cold"] = measure_embed("bge-m3", "Kiểm tra hiệu năng embedding tiếng Việt của hệ thống QUAN AI BRAIN")
    results["bge_m3_warm"] = measure_embed("bge-m3", "Câu hỏi thứ hai để đo warm latency của BGE-M3 trên PC Core")
except Exception as e:
    results["bge_m3_cold"] = f"error: {e}"

# --- Qwen fast tier
for m in ["qwen2.5:0.5b", "qwen2.5:1.5b"]:
    try:
        results[m] = [
            measure_generate(m, "Chào em, em là ai?", 32),
            measure_generate(m, "Cho em biết hệ thống R0-R5 là gì, trả lời ngắn gọn.", 64),
        ]
    except Exception as e:
        results[m] = f"error: {e}"

# --- Qwen reasoning tier (7B)
try:
    results["qwen2.5:7b"] = [
        measure_generate("qwen2.5:7b", "Lập kế hoạch ngắn 3 bước để kiểm tra hệ thống an toàn R0-R5.", 96),
    ]
except Exception as e:
    results["qwen2.5:7b"] = f"error: {e}"

# --- final loaded state
try:
    ps = post("/api/ps", {}, timeout=5)
    results["loaded_after"] = [(m.get("model"), round(m.get("size_vram", 0) / 1e6)) for m in ps["data"].get("models", [])]
except Exception as e:
    results["loaded_after"] = f"error: {e}"

with open("reports/SPRINT0_RUNTIME_PROBE.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(json.dumps(results, ensure_ascii=False, indent=2))
