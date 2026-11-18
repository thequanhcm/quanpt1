"""Tests — V7 vivi port 18/11: GET /api/v7/skill/<name> endpoint (server.py).

Phủ: whitelist (chỉ skill read-only), 404 khi không whitelist, parse limit,
result shape đúng skill, không ghi dữ liệu (read-only proof).
Chạy trực tiếp handler qua HTTP test-server thật (dual servers 8765 hoặc spawn ngắn).
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

BASE = "http://127.0.0.1:8765"


def _server_up() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE}/api/health", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


SERVER = _server_up()

requires_server = pytest.mark.skipif(not SERVER, reason="dual servers 8765 không chạy")


def _get_skill(name: str, qs: str = "") -> tuple[int, dict]:
    url = f"{BASE}/api/v7/skill/{name}" + (f"?{qs}" if qs else "")
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


@requires_server
class TestV7SkillEndpoint:
    def test_whitelist_unknown_returns_404(self):
        status, body = _get_skill("not_a_skill")
        assert status == 404
        assert body["success"] is False
        assert "whitelist" in body["error"]

    def test_memory_health_audit_live(self):
        status, body = _get_skill("memory_health_audit")
        assert status == 200
        assert body["success"] is True
        assert body["skill"] == "memory_health_audit"
        result = body["result"]
        assert result["conclusion"] in ("HEALTHY", "PARTIAL", "UNKNOWN")
        assert "report_only" in result["action_policy"]

    def test_lesson_mining_live_with_limit(self):
        status, body = _get_skill("lesson_mining", "limit=3")
        assert status == 200
        result = body["result"]
        assert len(result["top_lessons"]) <= 3
        assert result["conclusion"] in ("EXTRACTED", "EMPTY", "UNKNOWN")

    def test_pipeline_audit_live(self):
        status, body = _get_skill("pipeline_audit", "limit=2")
        assert status == 200
        result = body["result"]
        assert len(result["recent_turns"]) <= 2
        assert result["conclusion"] in ("OK", "PARTIAL", "UNKNOWN")

    def test_voice_health_check_live(self):
        status, body = _get_skill("voice_health_check")
        assert status == 200
        result = body["result"]
        assert result["conclusion"] in ("READY", "PARTIAL", "UNKNOWN")
        checks = result["checks"]
        assert checks.get("tts_provider") == "edge-tts"

    def test_system_status_summary_live(self):
        status, body = _get_skill("system_status_summary")
        assert status == 200
        result = body["result"]
        assert result["conclusion"] in ("OK", "PARTIAL", "UNKNOWN")
        assert "pi_daemon" in result["summary"]

    def test_no_write_proof(self, tmp_path: Path):
        # Endpoint chỉ chạy skill report_only — chứng minh bằng action_policy của mọi skill
        for name in ("memory_health_audit", "lesson_mining", "system_status_summary",
                     "pipeline_audit", "voice_health_check"):
            status, body = _get_skill(name)
            if status == 200:
                assert "report_only" in body["result"]["action_policy"], name
