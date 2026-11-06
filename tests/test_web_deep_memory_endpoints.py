"""V9.0 — Tests cho 6 route /api/memory/deep/* (Tab 10 Trí Nhớ Sâu).

Master Prompt V9.0 + yêu cầu owner 06/11/2026:
- Tab 10 executive gọi 6 endpoint; server.py phải implement ĐỦ và fail-honest.
- 4 route GET: stats / units / questions / timeline.
- 3 route POST: answer / extract / review.
- Validation: status filter sai → 400; body thiếu → 400; question lạ → 404.
- Đọc/ghi qua DeepMemoryStore trên brain.db của TEST workspace (isolate).
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from quan_ai_brain.memory.deep_memory import DeepMemoryStore
from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer


@pytest.fixture(scope="module")
def deep_server(tmp_path_factory: pytest.TempPathFactory):
    test_workspace = tmp_path_factory.mktemp("deep_memory_ws")
    (test_workspace / "data").mkdir(parents=True, exist_ok=True)

    old_env = os.environ.get("QUAN_AI_BRAIN_WORKSPACE")
    os.environ["QUAN_AI_BRAIN_WORKSPACE"] = str(test_workspace)

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)

    yield f"http://{host}:{port}", test_workspace

    server.shutdown()
    server.server_close()
    if old_env is None:
        os.environ.pop("QUAN_AI_BRAIN_WORKSPACE", None)
    else:
        os.environ["QUAN_AI_BRAIN_WORKSPACE"] = old_env


def _get(base: str, path: str) -> tuple[int, dict]:
    with urllib.request.urlopen(base + path, timeout=5.0) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _post(base: str, path: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


# ------------------------------------------------------------------ GET routes

def test_deep_stats_empty_db(deep_server) -> None:
    base, _ws = deep_server
    status, data = _get(base, "/api/memory/deep/stats")
    assert status == 200
    assert data["success"] is True
    s = data["stats"]
    assert s["knowledge_units_total"] == 0
    assert s["owner_questions_open"] == 0
    assert "units_by_status" in s and "last_review_run" in s


def test_deep_units_and_timeline_empty(deep_server) -> None:
    base, _ws = deep_server
    status, data = _get(base, "/api/memory/deep/units?limit=10")
    assert status == 200
    assert data["success"] is True and data["units"] == []

    status, data = _get(base, "/api/memory/deep/timeline")
    assert status == 200
    assert data["success"] is True and data["events"] == []


def test_deep_questions_no_open(deep_server) -> None:
    base, _ws = deep_server
    status, data = _get(base, "/api/memory/deep/questions?status=OPEN")
    assert status == 200
    assert data["success"] is True and data["questions"] == []


# ------------------------------------------------------------------ Validation

def test_deep_units_invalid_status_400(deep_server) -> None:
    base, _ws = deep_server
    try:
        with urllib.request.urlopen(base + "/api/memory/deep/units?status=HACKED", timeout=5.0) as resp:
            status = resp.status
        assert status != 200, "status filter sai không được phép 200"
    except urllib.error.HTTPError as exc:
        assert exc.code == 400


def test_deep_answer_missing_fields_400(deep_server) -> None:
    base, _ws = deep_server
    code, data = _post(base, "/api/memory/deep/answer", {"question_id": "", "answer": ""})
    assert code == 400
    assert data["success"] is False


def test_deep_answer_unknown_question_404(deep_server) -> None:
    base, _ws = deep_server
    code, data = _post(
        base, "/api/memory/deep/answer",
        {"question_id": "OQ_KHONG_TON_TAI", "answer": "thử"},
    )
    assert code == 404
    assert data["success"] is False


# ------------------------------------------------------------------ E2E flow

def test_deep_full_flow_extract_review_answer(deep_server) -> None:
    base, ws = deep_server

    # Seed 1 episode chat_turn như hội thoại thật (đúng schema iter_chat_turns đọc).
    store = DeepMemoryStore(ws / "data" / "brain.db")
    try:
        store._connection.execute(
            """
            INSERT INTO episodes (id, created_at_utc, kind, summary, source_ref, status, metadata_json)
            VALUES ('ep_seed_v9api_1', '2026-11-06T10:00:00+00:00', 'chat_turn',
                    'seed summary', 'test://deep_api', 'recorded', ?)
            """,
            (
                json.dumps(
                    {
                        "session_id": "sess_deep_api",
                        "user_query": "Server 8216 đang chạy ổn định không? Tôi nghĩ là ổn.",
                        "assistant_reply": (
                            "Server PID 8216 giữ cổng 8765 và 8766. "
                            "Watchdog phải luôn chạy nền 24/7."
                        ),
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        store._connection.commit()
    finally:
        store.close()

    # 1) POST extract → units được tạo
    code, data = _post(base, "/api/memory/deep/extract", {"limit": 30})
    assert code == 200, data
    assert data["success"] is True
    assert data["extraction"]["units_created"] > 0

    # 2) GET units → có tri thức + quan hệ list
    code, data = _get(base, "/api/memory/deep/units?limit=60")
    assert code == 200 and data["success"] is True
    assert len(data["units"]) > 0
    u0 = data["units"][0]
    for field in ("knowledge_id", "statement", "status", "version", "confidence", "knowledge_type", "relations"):
        assert field in u0, f"thiếu field {field} cho JS render"

    # 3) GET stats phản ánh số unit vừa tạo
    code, data = _get(base, "/api/memory/deep/stats")
    assert code == 200
    assert data["stats"]["knowledge_units_total"] > 0

    # 4) POST review (10 stage MemoryReviewCycle) → COMPLETED
    code, data = _post(base, "/api/memory/deep/review", {"batch_limit": 20})
    assert code == 200, data
    assert data["success"] is True
    assert data["review"]["status"] == "COMPLETED"
    assert len(data["review"]["stages_completed"]) == 10

    # 5) Timeline có sự kiện review_run + knowledge_update
    code, data = _get(base, "/api/memory/deep/timeline")
    assert code == 200
    kinds = {e["kind"] for e in data["events"]}
    assert "review_run" in kinds and "knowledge_update" in kinds

    # 6) Owner question: tạo qua store → GET thấy → POST answer → ANSWERED
    store = DeepMemoryStore(ws / "data" / "brain.db")
    try:
        q_id = store.create_owner_question(
            problem="mâu thuẫn thử nghiệm",
            evidence="evidence thử nghiệm",
            current_view="quan điểm hiện tại",
            interpretations_json=json.dumps(["cách hiểu A"], ensure_ascii=False),
            question="Quanpt1 chọn cách hiểu nào?",
            impact="ảnh hưởng phạm vi test",
            scope_hint="test",
        )
    finally:
        store.close()

    code, data = _get(base, "/api/memory/deep/questions?status=OPEN")
    assert code == 200
    matched = [q for q in data["questions"] if q["question_id"] == q_id]
    assert matched, "câu hỏi mới tạo phải xuất hiện trong GET questions"
    q = matched[0]
    for field in ("problem", "question", "evidence", "current_view", "status"):
        assert field in q, f"thiếu field {field} cho JS render"

    code, data = _post(
        base, "/api/memory/deep/answer",
        {"question_id": q_id, "answer": "Chọn cách hiểu A — phạm vi test."},
    )
    assert code == 200, data
    assert data["success"] is True
    assert data["question"]["status"] == "ANSWERED"

    # Sau khi trả lời, OPEN không còn câu này
    code, data = _get(base, "/api/memory/deep/questions?status=OPEN")
    assert all(qq["question_id"] != q_id for qq in data["questions"])
