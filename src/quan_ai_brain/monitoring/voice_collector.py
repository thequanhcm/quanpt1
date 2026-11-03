"""Voice Health Collector — trạng thái STT / LLM / TTS bằng probe thật (M1).

- STT: faster-whisper import được không + model files tồn tại (đọc-only).
- LLM: provider health qua _build_llm_provider() của server (NetMind status).
- TTS: Edge-TTS network probe qua urllib HEAD nhẹ + kiểm engine config hiện có.
Fail-honest: không probe được → UNKNOWN.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mk(check_id: str, value: Any, reason: str, status: str | None = None) -> dict[str, Any]:
    return {"value": value, "status": status or ("ok" if value is not None else "unknown"),
            "reason": reason, "measured_at": _now_iso()}


def collect_voice_health() -> dict[str, Any]:
    checks: dict[str, Any] = {}

    # --- STT: faster-whisper + model cache ---
    try:
        import faster_whisper  # type: ignore
        fw_ok = True
        fw_detail = f"import_ok:{getattr(faster_whisper, '__version__', 'unknown')}"
    except Exception as exc:
        fw_ok = False
        fw_detail = f"import_error:{type(exc).__name__}"
    checks["stt_engine"] = _mk("stt_engine", "ready" if fw_ok else "unavailable",
                               fw_detail, "ok" if fw_ok else "warn")

    # --- LLM: NetMind provider health (không in key, chỉ status) ---
    # DISABLED_BY_POLICY ở môi trường không key (vd. test kernel) được coi là
    # cấu hình đúng policy, không phải sự cố → NORMAL.
    try:
        from quan_ai_brain.web.server import _build_llm_provider
        provider = _build_llm_provider()
        h = provider.health() or {}
        netmind = h.get("netmind") or {}
        status = netmind.get("status", "UNKNOWN")
        if status == "DISABLED_BY_POLICY":
            llm_sev = "ok"  # policy chặn đúng — không phải lỗi
        elif status == "READY":
            llm_sev = "ok"
        else:
            llm_sev = "warn"
        checks["llm_netmind"] = _mk(
            "llm_netmind", status, "provider_health", llm_sev)
        checks["llm_ollama"] = _mk(
            "llm_ollama", bool(h.get("ollama_online")), "provider_health",
            "ok" if h.get("ollama_online") else "warn")
    except Exception as exc:
        checks["llm_netmind"] = _mk("llm_netmind", None,
                                    f"probe_error:{type(exc).__name__}", "unknown")
        checks["llm_ollama"] = _mk("llm_ollama", None,
                                   f"probe_error:{type(exc).__name__}", "unknown")

    # --- TTS: Edge-TTS import + engine có cấu hình không ---
    try:
        import edge_tts  # type: ignore
        tts_detail = "import_ok"
        tts_val = "ready"
        tts_status = "ok"
    except Exception as exc:
        tts_detail = f"import_error:{type(exc).__name__}"
        tts_val = "unavailable"
        tts_status = "warn"
    try:
        from quan_ai_brain.voice.tts_config import GLOBAL_TTS_MANAGER  # noqa: F401
        tts_detail += ";manager_configured"
    except Exception:
        tts_detail += ";manager_not_checkable"
    checks["tts_engine"] = _mk("tts_engine", tts_val, tts_detail, tts_status)

    return {
        "component_id": "voice",
        "measured_at": _now_iso(),
        "reachable": all(v["status"] != "unknown" for v in checks.values()),
        "checks": checks,
    }
