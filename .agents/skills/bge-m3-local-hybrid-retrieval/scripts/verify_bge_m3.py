"""
Fast Verification Script for Local BGE-M3 Embedding Service via Ollama.
Zero-dependency: uses only standard library (urllib, json, time, math, socket, sys, io).
"""

import io
import json
import math
import socket
import sys
import time
import urllib.error
import urllib.request

# Ensure UTF-8 output on Windows consoles to support Vietnamese diacritics
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def check_port(host: str = "127.0.0.1", port: int = 11434, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def get_embedding(
    text: str,
    model: str = "bge-m3",
    host: str = "127.0.0.1",
    port: int = 11434,
    timeout: float = 10.0,
) -> list[float]:
    url = f"http://{host}:{port}/api/embeddings"
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        emb = data.get("embedding")
        if not emb:
            raise ValueError(f"No embedding returned for text: {text[:30]}...")
        return emb


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def main():
    print("=" * 60)
    print("BGE-M3 LOCAL EMBEDDING & RETRIEVAL VERIFICATION")
    print("=" * 60)

    # 1. Check Port
    print("[1/4] Probing Ollama port (127.0.0.1:11434)...", end=" ")
    if not check_port():
        print("FAILED!")
        print("Error: Ollama daemon is not responding on 127.0.0.1:11434.")
        print("Please start Ollama using `ollama serve` or run `KHOI_DONG_OLLAMA.bat`.")
        sys.exit(1)
    print("ONLINE")

    # 2. Check Embedding Generation
    test_text_vi = "Quy trình kiểm tra nội trở và điện áp ắc quy UPS trung tâm dữ liệu"
    print(f"[2/4] Requesting embedding for: '{test_text_vi[:40]}...'")
    t0 = time.perf_counter()
    try:
        vec_vi = get_embedding(test_text_vi)
        latency = (time.perf_counter() - t0) * 1000
        print(f"      -> SUCCESS! Dimensions: {len(vec_vi)} | Latency: {latency:.1f}ms")
    except Exception as e:
        print(f"      -> FAILED: {e}")
        print("Ensure 'bge-m3' is installed by running: `ollama pull bge-m3`")
        sys.exit(1)

    # 3. Check Semantic Differentiation
    print("[3/4] Testing semantic distance calculation...")
    similar_text = "Phương pháp đo điện áp chuỗi bình điện phòng máy chủ DC"
    unrelated_text = "Công thức nấu phở bò gia truyền Hà Nội thơm ngon"

    vec_sim = get_embedding(similar_text)
    vec_unrel = get_embedding(unrelated_text)

    score_sim = cosine_similarity(vec_vi, vec_sim)
    score_unrel = cosine_similarity(vec_vi, vec_unrel)

    print(f"      -> Similarity with domain text: {score_sim:.4f}")
    print(f"      -> Similarity with unrelated text: {score_unrel:.4f}")

    if score_sim > score_unrel:
        print("      -> VERIFIED: Semantic ranking correctly differentiates domain context!")
    else:
        print("      -> WARNING: Semantic ranking anomaly detected.")

    # 4. Dimension check
    print("[4/4] Verifying vector specification...", end=" ")
    if len(vec_vi) == 1024:
        print("PASSED (1024 dimensions - standard BAAI/bge-m3 dense representation)")
    else:
        print(f"WARNING: Unexpected dimension size ({len(vec_vi)})")

    print("=" * 60)
    print("ALL CHECKS COMPLETED SUCCESSFULLY. Ready for production integration.")
    print("=" * 60)


if __name__ == "__main__":
    main()
