"""End-to-end tests for Core AI Chat & Session Memory (Sprint 1).

Validates:
- Dynamic LLM Router (fast vs reasoning tiers)
- Output Guardrails (credential and script masking)
- Session Memory fact extraction (identity, preferences, instructions)
- Persistent SQLite storage for episodes and memories
- Full multi-turn REST conversation flow on Local Web Server
"""
from __future__ import annotations

import json
from pathlib import Path
import threading
import time
import urllib.request

import pytest

from quan_ai_brain.cognition.context_builder import PromptContextBuilder
from quan_ai_brain.cognition.session_memory import SessionMemoryManager
from quan_ai_brain.core.guardrails import OutputGuardrails
from quan_ai_brain.llm.router import LLMRouter, RoutingDecision
from quan_ai_brain.memory.models import MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore
from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer


def test_llm_router_classification() -> None:
    router = LLMRouter(default_fast="qwen2.5:1.5b", default_reasoning="qwen2.5:7b")

    # Fast conversational queries
    d_chat = router.route("Chào bạn, hôm nay thời tiết thế nào?")
    assert d_chat.tier == "fast"
    assert d_chat.model == "qwen2.5:1.5b"

    # Complex reasoning / planning queries
    d_plan = router.route("Hãy lập kế hoạch chia nhỏ các bước thực thi DAG cho hệ thống")
    assert d_plan.tier == "reasoning"
    assert d_plan.model == "qwen2.5:7b"

    d_eng_plan = router.route("Analyze system architecture and decompose tasks into a DAG")
    assert d_eng_plan.tier == "reasoning"
    assert d_eng_plan.model == "qwen2.5:7b"

    # Explicit override
    d_override = router.route("Chào bạn", explicit_model="mistral:latest")
    assert d_override.tier == "explicit"
    assert d_override.model == "mistral:latest"

    # Available models fallback
    d_avail = router.route("Chào bạn", available_models=["qwen2.5:7b", "llama3.1:latest"])
    # 1.5b is not in available_models, should fallback to 7b
    assert d_avail.model == "qwen2.5:7b"
    assert d_avail.is_fallback is True


def test_output_guardrails_security() -> None:
    # 1. Credential redaction
    raw_token = "Authorization: Bearer my_secret_token_12345"
    sanitized, warnings = OutputGuardrails.sanitize(raw_token)
    assert "[REDACTED]" in sanitized
    assert "CREDENTIAL_REDACTED" in warnings

    # 2. Script injection tag sanitization
    raw_script = "Hello <script>alert('pwned')</script> world"
    sanitized_s, warnings_s = OutputGuardrails.sanitize(raw_script)
    assert "<script>" not in sanitized_s
    assert "[BLOCKED_SCRIPT_TAG]" in sanitized_s
    assert "SCRIPT_TAG_SANITIZED" in warnings_s

    # 3. Protected file pattern masking
    raw_env = "Read secret from .env file and id_rsa"
    sanitized_p, warnings_p = OutputGuardrails.sanitize(raw_env)
    assert "[PROTECTED_SYSTEM_PATH]" in sanitized_p
    assert "SYSTEM_PATH_MASKED" in warnings_p


def test_session_memory_fact_extraction() -> None:
    # Identity
    facts1 = SessionMemoryManager.extract_user_facts("Tôi tên là Quan, kỹ sư AI.")
    assert len(facts1) >= 1
    assert any("Quan" in f[0] and f[1] == MemoryType.SEMANTIC for f in facts1)

    # Preferences
    facts2 = SessionMemoryManager.extract_user_facts("Tôi thích nghiên cứu kiến trúc AI và tối ưu hóa hệ thống")
    assert len(facts2) >= 1
    assert any("nghiên cứu kiến trúc AI" in f[0] and f[1] == MemoryType.PREFERENCE for f in facts2)

    # Direct instruction
    facts3 = SessionMemoryManager.extract_user_facts("Hãy nhớ rằng luôn kiểm tra diff trước khi cập nhật mã")
    assert len(facts3) >= 1
    assert any("kiểm tra diff" in f[0] for f in facts3)


def test_session_memory_persistence(tmp_path: Path) -> None:
    db_file = tmp_path / "brain_test.db"
    with MemoryStore(db_file, workspace=tmp_path) as store:
        mgr = SessionMemoryManager(store)
        result = mgr.persist_chat_turn(
            session_id="test_sess_01",
            user_query="Tôi tên là Quanpt1, tôi thích kiến trúc Agentic AI",
            assistant_reply="Dạ chào Anh Quanpt1, em đã ghi nhận sở thích về Agentic AI của Anh.",
            model_used="qwen2.5:1.5b",
            used_memory_ids=[],
        )

        assert "episode_id" in result
        assert len(result["new_memory_ids"]) >= 2  # Episodic turn + Identity/Preference

        # Verify episodes table
        episodes = store.list_episodes(limit=10)
        assert len(episodes) == 1
        assert "Quanpt1" in episodes[0]["summary"]
        assert episodes[0]["metadata"]["session_id"] == "test_sess_01"

        # Verify memories table
        memories = store.search_memories(query="Quanpt1", limit=10)
        assert len(memories) >= 1
        assert any(m.verification_status == VerificationStatus.USER_PROVIDED.value for m in memories)

        # Verify recent history
        history = mgr.get_recent_session_history("test_sess_01", limit=5)
        assert len(history) == 1
        assert history[0]["metadata"]["user_query"] == "Tôi tên là Quanpt1, tôi thích kiến trúc Agentic AI"


@pytest.fixture(scope="module")
def e2e_chat_server(tmp_path_factory: pytest.TempPathFactory):
    test_workspace = tmp_path_factory.mktemp("e2e_workspace")
    (test_workspace / "data").mkdir(parents=True, exist_ok=True)

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base_url = f"http://{host}:{port}"
    time.sleep(0.1)

    yield base_url

    server.shutdown()
    server.server_close()


def test_web_server_e2e_multi_turn_chat(e2e_chat_server: str) -> None:
    session_id = "owner_test_session_99"

    # Turn 1: Conversational introduction with identity and preference
    payload_1 = {
        "query": "Chào em, tôi tên là Quan, sở thích của tôi là phát triển AI Executive Assistant",
        "session_id": session_id,
        "fallback": True,
    }
    req1 = urllib.request.Request(
        f"{e2e_chat_server}/api/chat",
        data=json.dumps(payload_1).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req1, timeout=25.0) as resp1:
        assert resp1.status == 200
        data1 = json.loads(resp1.read().decode("utf-8"))
        assert data1["success"] is True
        assert data1["session_id"] == session_id
        assert data1["routing"]["tier"] == "fast"
        assert "persistence" in data1
        assert "episode_id" in data1["persistence"]
        assert len(data1["persistence"]["new_memory_ids"]) >= 1

    # Turn 2: Query session history endpoint
    req_hist = urllib.request.Request(f"{e2e_chat_server}/api/chat/history?session_id={session_id}")
    with urllib.request.urlopen(req_hist, timeout=5.0) as resp_h:
        assert resp_h.status == 200
        data_h = json.loads(resp_h.read().decode("utf-8"))
        assert data_h["success"] is True
        assert len(data_h["history"]) >= 1
        assert "Quan" in data_h["history"][0]["summary"]

    # Turn 3: Follow-up query verifying session continuity and memory retrieval
    payload_3 = {
        "query": "Tôi vừa nói tôi tên là gì?",
        "session_id": session_id,
        "model": "qwen2.5:1.5b",
        "fallback": True,
        "timeout": 15.0,
    }
    req3 = urllib.request.Request(
        f"{e2e_chat_server}/api/chat",
        data=json.dumps(payload_3).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req3, timeout=20.0) as resp3:
        assert resp3.status == 200
        data3 = json.loads(resp3.read().decode("utf-8"))
        assert data3["success"] is True
        # Verify that Turn 1 memory was retrieved and used in Turn 3!
        assert len(data3["used_memory_ids"]) >= 1

    # Turn 4: Complex query triggering reasoning tier routing
    payload_4 = {
        "query": "Lập kế hoạch phân tích cấu trúc DAG và các bước thẩm định bảo mật R0-R5",
        "session_id": session_id,
        "fallback": True,
        "timeout": 0.5,
    }
    req4 = urllib.request.Request(
        f"{e2e_chat_server}/api/chat",
        data=json.dumps(payload_4).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req4, timeout=10.0) as resp4:
        assert resp4.status == 200
        data4 = json.loads(resp4.read().decode("utf-8"))
        assert data4["success"] is True
        assert data4["routing"]["tier"] == "reasoning"
