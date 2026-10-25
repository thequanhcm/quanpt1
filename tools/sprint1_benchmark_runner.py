"""Sprint 1 benchmark runner (approved D3): Qwen local vs GLM-5.3-Flash (NetMind).

Same 28-prompt Vietnamese dataset, same system prompt, same deterministic scoring.
Scoring is programmatic (keyword hits, forbidden-pattern misses, empty-answer check,
Vietnamese-tone preservation) — no model self-grading, no subjective-only verdicts.

Safety: NETMIND_EXTERNAL_DATA_ALLOWED is turned on inside this script ONLY for the
benchmark run (owner-approved D2/D3). Prompts are synthetic; no workspace data or
secrets leave the machine. The API key stays in process env, never printed.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import os
os.environ["NETMIND_EXTERNAL_DATA_ALLOWED"] = "true"  # benchmark-only, owner-approved

from quan_ai_brain.llm.models import LLMRequest  # noqa: E402
from quan_ai_brain.llm.netmind_provider import NETMIND_CHAT_MODEL, NetMindProvider  # noqa: E402
from quan_ai_brain.llm.client import OllamaClient  # noqa: E402
from sprint1_benchmark_dataset import DATASET, SYSTEM_PROMPT  # noqa: E402

TONED = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"


def score(resp_text: str, item: dict, elapsed_s: float, success: bool, is_mock: bool) -> dict:
    text = (resp_text or "").strip()
    low = text.lower()
    keyword_hits = sum(1 for kw in item["expected"] if kw.lower() in low)
    forbidden_hits = [f for f in item["forbidden"] if f.lower() in low]
    return {
        "id": item["id"],
        "category": item["category"],
        "success": success,
        "is_mock": is_mock,
        "empty": len(text) == 0,
        "keyword_hits": f"{keyword_hits}/{len(item['expected'])}",
        "forbidden_violations": forbidden_hits,
        "has_vietnamese_tone": any(ch in TONED for ch in text.lower()),
        "latency_s": round(elapsed_s, 2),
        "chars": len(text),
        "answer": text[:220],
    }


def run_provider(label: str, call) -> dict:
    rows = []
    for item in DATASET:
        t0 = time.perf_counter()
        try:
            text, success, is_mock = call(item["prompt"])
        except Exception as exc:  # noqa: BLE001
            text, success, is_mock = "", False, False
            print(f"  [{label}] {item['id']}: EXC {type(exc).__name__}")
        row = score(text, item, time.perf_counter() - t0, success, is_mock)
        rows.append(row)
        flag = "OK " if (success and not row["forbidden_violations"]) else "!! "
        print(f"  [{label}] {flag}{item['id']} {row['latency_s']}s kw={row['keyword_hits']} forb={row['forbidden_violations'] or '-'}")
    return {
        "provider": label,
        "rows": rows,
        "summary": summarize(rows),
    }


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    ok = [r for r in rows if r["success"] and not r["forbidden_violations"] and not r["empty"]]
    kw_total = sum(int(r["keyword_hits"].split("/")[0]) for r in rows)
    kw_max = sum(int(r["keyword_hits"].split("/")[1]) for r in rows)
    return {
        "total": n,
        "clean_pass": len(ok),
        "clean_pass_pct": round(100 * len(ok) / n, 1) if n else 0.0,
        "keyword_accuracy_pct": round(100 * kw_total / kw_max, 1) if kw_max else None,
        "empty_answers": sum(1 for r in rows if r["empty"]),
        "forbidden_violations": sum(1 for r in rows if r["forbidden_violations"]),
        "mock_answers": sum(1 for r in rows if r["is_mock"]),
        "vi_tone_preserved_pct": round(100 * sum(1 for r in rows if r["has_vietnamese_tone"]) / n, 1) if n else 0.0,
        "latency_avg_s": round(sum(r["latency_s"] for r in rows) / n, 2) if n else None,
        "latency_p95_s": round(sorted(r["latency_s"] for r in rows)[int(0.95 * n) - 1], 2) if n >= 2 else None,
    }


def main() -> None:
    results = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "n_prompts": len(DATASET), "providers": []}

    # --- GLM-5.3-Flash via NetMind (verified catalog, reasoning_effort=low) ---
    nm = NetMindProvider(reasoning_effort="low", max_retries=1)

    def nm_call(prompt: str):
        resp = nm.generate(LLMRequest(
            prompt=prompt, model=NETMIND_CHAT_MODEL, system_prompt=SYSTEM_PROMPT,
            timeout_seconds=45, metadata={"max_tokens": 400, "tier": "benchmark"},
        ))
        return resp.text, resp.success, resp.is_mock

    results["providers"].append(run_provider("glm-5.3-flash", nm_call))

    # --- Qwen local (1.5b fast tier) ---
    oc = OllamaClient(default_timeout=45)
    if oc.is_daemon_online():
        def qwen_call(prompt: str):
            resp = oc.generate(LLMRequest(
                prompt=prompt, model="qwen2.5:1.5b", system_prompt=SYSTEM_PROMPT,
                timeout_seconds=45,
            ))
            return resp.text, resp.success, resp.is_mock
        results["providers"].append(run_provider("qwen2.5-1.5b-local", qwen_call))
    else:
        print("  [qwen2.5-1.5b-local] Ollama offline — skipped (recorded honestly)")
        results["providers"].append({"provider": "qwen2.5-1.5b-local", "skipped": "ollama_offline", "rows": [], "summary": None})

    out = Path("reports/SPRINT1_VIETNAMESE_BENCHMARK.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== SUMMARY ===")
    for p in results["providers"]:
        print(p["provider"], "->", json.dumps(p.get("summary"), ensure_ascii=False))
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
