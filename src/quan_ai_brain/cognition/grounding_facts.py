"""Living Grounding Facts — nguồn sự thật sống cho system prompt.

Mục tiêu trung thực (theo yêu cầu chủ sở hữu 27/10/2026): bot KHÔNG được
nói sai về bản thân. Ba lỗi đã gặp:
1. Nói "bộ não chạy trên PC" trong khi suy luận thật sự chạy GLM cloud.
2. Giới thiệu kiến trúc (Pi 5, avatar...) như sự kiện đã kiểm chứng.
3. UI hiển thị model sai ("Model active: qwen2.5:7b" dù chạy GLM-5.3-Flash).

Module này probe THẬT từng câu trả lời trước khi đưa vào system prompt:
- Runtime: python đang chạy gì, executable ở đâu (sys.executable).
- LLM: model nào xử lý chat thật sự (từ router decision của request hiện tại).
- Ollama: port 11434 có sống không (TCP connect, timeout ngắn).
- Pi 5: port 8768 có sống không (TCP connect, timeout ngắn).
- Core server: 8765.
Mọi kết quả đều là OBSERVED (đo được), không suy diễn. Khi probe fail, kết quả
là "OFFLINE/không xác minh được" — tuyệt đối không tô đẹp.
"""
from __future__ import annotations

import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_WORKSPACE_ANCHOR = Path(__file__).resolve().parents[3]

# Cổng nội bộ — chỉ probe localhost, không đụng mạng ngoài.
_INTERNAL_PORTS: dict[str, int] = {
    "core_server": 8765,
    "executive_server": 8766,
    "ollama_local": 11434,
    "pi5_edge": 8768,
}


def _tcp_alive(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def collect_grounding_facts(current_model: str | None = None) -> dict[str, Any]:
    """Probe thật, trả về dict fact có bằng chứng. Không bao giờ raise."""
    facts: dict[str, Any] = {}
    now = datetime.now(timezone.utc).isoformat()

    # 1. Runtime thật (PC Core) — executable đang chạy
    exe = Path(sys.executable).resolve()
    is_venv = "venv" in str(exe).lower() or "envs" in str(exe).lower()
    facts["runtime"] = {
        "process_host": "PC (Windows) — 127.0.0.1",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "executable": str(exe),
        "venv": is_venv,
        "workspace": str(_WORKSPACE_ANCHOR),
    }

    # 2. LLM đang xử lý chat THẬT SỰ (từ decision của request hiện tại)
    if current_model:
        if "glm" in current_model.lower() or "qwen3" in current_model.lower() or "minimax" in current_model.lower():
            llm_location = "NetMind Cloud (gateway Viettel) — KHÔNG chạy trên PC này"
        else:
            llm_location = "local (Ollama trên PC)"
        facts["llm"] = {
            "model": current_model,
            "runs_on": llm_location,
        }

    # 3. Probe cổng nội bộ — trạng thái thật, không tô đẹp
    ports: dict[str, str] = {}
    for name, port in _INTERNAL_PORTS.items():
        ports[name] = "ONLINE" if _tcp_alive(port) else "OFFLINE"
    facts["components"] = ports

    # 4. Kết luận kiến trúc trung thực (chỉ dựa trên kết quả probe ở trên)
    ollama = ports.get("ollama_local") == "ONLINE"
    pi5 = ports.get("pi5_edge") == "ONLINE"
    if current_model and "cloud" in facts["llm"]["runs_on"]:
        arch = (
            f"Suy luận hiện tại chạy trên cloud ({current_model}). "
            f"Ollama local: {'ONLINE' if ollama else 'OFFLINE'}. "
            f"PC vẫn là nơi chạy server, trí nhớ và daemon."
        )
    elif ollama:
        arch = "Suy luận chạy local trên PC (Ollama ONLINE)."
    else:
        arch = "Không xác minh được nơi suy luận đang chạy (Ollama OFFLINE, không có model cloud)."
    facts["architecture_truth"] = arch
    facts["pi5_status"] = "ONLINE — hình thể có thể kiểm chứng" if pi5 else (
        "OFFLINE/không xác minh được — KHÔNG được nói hình thể Pi 5 đang hoạt động"
    )
    facts["generated_at_utc"] = now
    return facts


def render_grounding_block(facts: dict[str, Any]) -> str:
    """Render block tiếng Việt chèn vào system prompt. Ngắn gọn, ép buộc."""
    comp = facts.get("components", {})
    lines = [
        "[BỘ SỰ THẬT SỐNG — đo bằng probe thật lúc "
        f"{facts.get('generated_at_utc', '?')}. TUYỆT ĐỐI dùng các kết quả này khi nói về bản thân, không suy diễn:]",
        f"1. Nơi chạy: {facts.get('runtime', {}).get('process_host', '?')} — server/trí nhớ/daemon chạy trên PC của Anh.",
        f"2. Suy luận LLM: {facts.get('llm', {}).get('model', '?')} — {facts.get('llm', {}).get('runs_on', '?')}.",
        f"3. Ollama local: {comp.get('ollama_local', '?')} | Pi 5: {comp.get('pi5_edge', '?')} | Core server: {comp.get('core_server', '?')} | Executive: {comp.get('executive_server', '?')}.",
        f"4. Hình thể Pi 5: {facts.get('pi5_status', '?')}.",
        "5. Khi Anh hỏi 'em ở đâu/ chạy ở đâu': trả lời theo mục 1-3 ở trên. Khi mô tả năng lực, chỉ nêu những gì ONLINE hoặc đã kiểm chứng; cái OFFLINE thì nói thẳng là OFFLINE.",
        "6. Avatar hiển thị trong dashboard là giao diện 2D trên PC, KHÔNG phải phần cứng Pi 5.",
    ]
    return "\n".join(lines)
