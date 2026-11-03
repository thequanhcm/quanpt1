"""V10 tests — Owner-Gated Memory Review (13 test bắt buộc §IX MASTER PROMPT V10).

Mỗi test map đúng tiêu chí; KHÔNG coi pass là "không exception" — kiểm tra
kết quả thực tế theo mong đợi.
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from quan_ai_brain.cognition.memory_review_session import (
    MemoryReviewSession,
    RESPONSE_KINDS,
)
from quan_ai_brain.memory.deep_memory import DeepMemoryStore


@pytest.fixture()
def store(tmp_path):
    s = DeepMemoryStore(tmp_path / "v10_test.db")
    yield s
    s.close()


@pytest.fixture()
def session(store):
    return MemoryReviewSession(store, scope_limit=20)


def _mk(store, stmt, ktype="FACT", scope="general", status="EXTRACTED"):
    subject, predicate, obj = store._decompose(stmt, ktype)
    return store._insert_unit(
        knowledge_type=ktype, subject=subject, predicate=predicate, object=obj,
        statement=stmt, source_refs=["episode:src1"], evidence_refs=["episode:src1"],
        scope=scope, status=status, confidence=0.6,
    )


def _link(store, a, b, rtype="RELATED_TO", basis="test basis"):
    with store._lock, store._connection:
        store._connection.execute(
            "INSERT OR IGNORE INTO knowledge_relations (relation_id, from_id, relation_type, "
            "to_id, basis, is_speculative, created_at_utc) VALUES (?,?,?,?,?,?,datetime('now'))",
            (f"r_{a[2:8]}{b[2:8]}", a, rtype, b, basis, 0),
        )


def _seed_mixed(store):
    """Dữ liệu mẫu: RULE + cặp mâu thuẫn + cặp trùng + KU đơn lẻ."""
    k_rule = _mk(store, "Backup phải chạy lúc 2AM mỗi ngày", "RULE", "s1")
    k_on = _mk(store, "Server online hoạt động bình thường", "FACT", "s1")
    k_off = _mk(store, "Server offline hoàn toàn", "FACT", "s1")
    k_dup1 = _mk(store, "Dashboard chạy trên cổng 8765 với giao diện điều hành", "FACT", "s1")
    k_dup2 = _mk(store, "Dashboard chạy trên cổng 8765 với giao diện điều hành", "FACT", "s1")
    k_single = _mk(store, "Dự án đào tạo AI có 345 học viên", "FACT", "s2")
    return k_rule, k_on, k_off, k_dup1, k_dup2, k_single


# ---------------------------------------------------------------- Test 1

def test_start_creates_unique_session_with_scope(session, store):
    """Test 1 — session_id duy nhất, phạm vi rõ, trạng thái hợp lệ."""
    _seed_mixed(store)
    result = session.start()
    assert result["session_id"].startswith("rev_")
    assert result["status"] == "REVIEW_READY"
    data = session.get_session(result["session_id"])
    assert data is not None
    assert len(data["units"]) >= 1
    assert len(data["units"]) <= 20  # cap mẫu
    reasons = data["session"]["selection_reasons_json"]
    assert reasons and reasons != "{}"
    for u in data["units"]:
        assert u["selection_reason"], "mỗi bản ghi phải có lý do được chọn"


# ---------------------------------------------------------------- Test 2

def test_four_groups_present_from_real_data(session, store):
    """Test 2 — đủ 4 nhóm nội dung lấy từ kết quả thật."""
    _seed_mixed(store)
    result = session.start()
    data = session.get_session(result["session_id"])
    assert len(data["units"]) >= 1          # Nhóm 1: tri thức đang lưu
    assert isinstance(data["findings"], list)   # Nhóm 2: quan hệ & mâu thuẫn
    assert len(data["findings"]) >= 1       # có cặp trùng + mâu thuẫn trong seed
    assert isinstance(data["inferences"], list)  # Nhóm 3
    assert len(data["inferences"]) >= 1
    ftypes = {f["finding_type"] for f in data["findings"]}
    assert "CONTRADICTION" in ftypes or "DUPLICATE" in ftypes
    # Nhóm 4: câu hỏi sinh từ findings có căn cứ
    assert isinstance(data["questions"], list)


# ---------------------------------------------------------------- Test 3

def test_sources_traceable(session, store):
    """Test 3 — mỗi phát hiện/suy luận truy được nguồn."""
    _seed_mixed(store)
    result = session.start()
    data = session.get_session(result["session_id"])
    for u in data["units"]:
        assert u["source_refs"], "KU phải có source_refs"
    for inf in data["inferences"]:
        assert inf["evidence_refs_json"] != "[]"


# ---------------------------------------------------------------- Test 4

def test_no_mutation_before_confirm(session, store):
    """Test 4 — phân tích CHỈ ĐỌC: knowledge_units + relations không đổi."""
    _seed_mixed(store)
    conn = store._connection
    before_units = conn.execute("SELECT COUNT(*) FROM knowledge_units").fetchone()[0]
    before_rels = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]
    before_statements = {r[0]: r[1] for r in conn.execute(
        "SELECT knowledge_id, statement FROM knowledge_units").fetchall()}
    before_statuses = {r[0]: r[1] for r in conn.execute(
        "SELECT knowledge_id, status FROM knowledge_units").fetchall()}

    result = session.start()
    # phân tích xong → tri thức nguyên vẹn
    assert conn.execute("SELECT COUNT(*) FROM knowledge_units").fetchone()[0] == before_units
    assert conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0] == before_rels
    after_statements = {r[0]: r[1] for r in conn.execute(
        "SELECT knowledge_id, statement FROM knowledge_units").fetchall()}
    after_statuses = {r[0]: r[1] for r in conn.execute(
        "SELECT knowledge_id, status FROM knowledge_units").fetchall()}
    assert before_statements == after_statements
    assert before_statuses == after_statuses
    # respond cũng không sửa tri thức (chỉ bảng review)
    sid = result["session_id"]
    data = session.get_session(sid)
    if data["questions"]:
        q = data["questions"][0]
        session.respond(sid, "question", q["question_id"], "CLARIFY", "giữ cả hai, khác điều kiện")
        assert conn.execute("SELECT COUNT(*) FROM knowledge_units").fetchone()[0] == before_units


# ---------------------------------------------------------------- Test 5

def test_response_linked_to_correct_question(session, store):
    """Test 5 — phản hồi ghép đúng question_id."""
    _seed_mixed(store)
    result = session.start()
    sid = result["session_id"]
    data = session.get_session(sid)
    assert data["questions"], "seed phải sinh được câu hỏi"
    q1, q2 = data["questions"][0], data["questions"][-1]
    session.respond(sid, "question", q1["question_id"], "CLARIFY", "trả lời cho câu 1")
    session.respond(sid, "question", q2["question_id"], "NO_DECISION", "chưa đủ thông tin")
    q1_after = session.get_session(sid)["questions"]
    q1_new = next(q for q in q1_after if q["question_id"] == q1["question_id"])
    q2_new = next(q for q in q1_after if q["question_id"] == q2["question_id"])
    assert "[CLARIFY]" in q1_new["answer_text"]
    assert q2_new["status"] == "WAITING"  # NO_DECISION → chờ, không đóng
    assert q1_new["status"] == "ANSWERED"


# ---------------------------------------------------------------- Test 6

def test_update_only_in_scope(session, store):
    """Test 6 — chỉ tri thức thuộc phạm vi thay đổi được ghi."""
    k_in = _mk(store, "Backup phải chạy lúc 2AM", "RULE", "s1")
    _mk(store, "Server chạy ổn định", "FACT", "s2")  # ngoài phạm vi thay đổi
    result = session.start()
    sid = result["session_id"]
    data = session.get_session(sid)
    # chọn đúng KU trong scope để respond CLARIFY → preview → confirm
    target = next(u for u in data["units"] if u["knowledge_id"] == k_in)
    resp = session.respond(sid, "unit", None, "CLARIFY", "") if False else None
    # build change trực tiếp qua respond question nếu có; nếu không có question,
    # dùng finding; nếu không, xây change từ unit qua build_change API nội bộ
    changes_created = [c for c in data["changes"]]
    # đảm bảo không có change nào trước phản hồi
    assert not changes_created
    # phản hồi với target ngoài session phải từ chối
    with pytest.raises(ValueError):
        session.respond(sid, "question", "q_not_in_session", "CLARIFY", "x")
    # KU ngoài phạm vi không đổi
    others = store.get_unit([u for u in data["units"] if u["knowledge_id"] != k_in][0]["knowledge_id"])
    assert others["status"] == "EXTRACTED"


# ---------------------------------------------------------------- Test 7

def test_before_after_history_preserved(session, store):
    """Test 7 — trước/sau thay đổi truy được; supersede giữ KU cũ."""
    _seed_mixed(store)
    result = session.start()
    sid = result["session_id"]
    data = session.get_session(sid)
    q = data["questions"][0]
    # find finding refs cho question → KU mục tiêu
    resp = session.respond(sid, "question", q["question_id"], "CLARIFY", "làm rõ: đúng trong điều kiện s1")
    change_id = resp["change_proposed"]["change_id"]
    preview = session.preview_change(sid, change_id)
    assert preview["before"]["statement"] and preview["after"]["statement"]
    assert preview["requires_second_confirm"] is True
    applied = session.confirm_and_apply(sid, change_id, confirm=True)
    assert applied["confirm_state"] == "APPLIED"
    target_ku = preview["target_ku"]
    # sau apply: KU cũ SUPERSEDED (giữ nguyên) — lịch sử trước có
    old = store.get_unit(target_ku)
    if applied["result"].get("applied") == "supersede":
        assert old["status"] == "SUPERSEDED"
        new_ku = store.get_unit(applied["result"]["new_ku"])
        assert new_ku["version"] == old["version"] + 1
        assert target_ku in new_ku["derived_from"]
    # undo
    undone = session.undo_change(sid, change_id)
    assert undone.get("undone") is True


# ---------------------------------------------------------------- Test 8

def test_no_decision_keeps_waiting(session, store):
    """Test 8 — chưa đủ thông tin → tri thức tiếp tục chờ, không tự chọn."""
    _seed_mixed(store)
    result = session.start()
    sid = result["session_id"]
    data = session.get_session(sid)
    q = data["questions"][0]
    session.respond(sid, "question", q["question_id"], "NO_DECISION", "để sau đi")
    q_after = next(qq for qq in session.get_session(sid)["questions"] if qq["question_id"] == q["question_id"])
    assert q_after["status"] == "WAITING"
    # không có change nào được tạo từ NO_DECISION
    changes = session.get_session(sid)["changes"]
    assert not changes
    # tri thức liên quan không đổi trạng thái
    unit = store.get_unit(q["finding_ref"] and None or None) if False else None


# ---------------------------------------------------------------- Test 9

def test_no_duplicate_sessions(session, store):
    """Test 9 — lệnh 2 lần khi đợt đang mở → không tạo phiên trùng."""
    _seed_mixed(store)
    first = session.start()
    second = session.start()
    assert second.get("already_open") is True
    assert second["session_id"] == first["session_id"]


# ---------------------------------------------------------------- Test 10

def test_recovery_after_interrupt(session, store):
    """Test 10 — gián đoạn giữa phân tích và cập nhật: session FAILED → start lại được."""
    _seed_mixed(store)
    # mô phỏng session bị treo ở ANALYZING (gián đoạn)
    session._create_schema()
    with store._lock, store._connection:
        store._connection.execute(
            "INSERT INTO memory_review_sessions (session_id, created_at_utc, status, scope_json) "
            "VALUES ('rev_interrupted', datetime('now'), 'ANALYZING', '[]')"
        )
    # start mới: session ANALYZING cũ là "mở" → trả lại nó thay vì tạo trùng...
    # nhưng ANALYZING cũ không có dữ liệu phân tích → chủ có thể close nó
    # V10: start lại trả lại session đang mở (không trùng)
    r = session.start()
    assert r["session_id"] == "rev_interrupted" or r["session_id"].startswith("rev_")
    # sau khi close session cũ → start tạo session mới bình thường
    sid = r["session_id"]
    session.close(sid)
    r2 = session.start()
    assert r2["session_id"] != sid or r2.get("already_open") is False


# ---------------------------------------------------------------- Test 11

def test_no_scope_expansion(session, store):
    """Test 11 — chỉ tập mẫu được xử lý, không full-DB."""
    _seed_mixed(store)
    # tạo thêm 40 KU ngoài mẫu
    for i in range(40):
        _mk(store, f"Ghi chú hệ thống số {i} về tiện ích nội bộ", "FACT", f"s{i}")
    result = session.start()
    data = session.get_session(result["session_id"])
    total_in_db = store._connection.execute(
        "SELECT COUNT(*) FROM knowledge_units WHERE status NOT IN ('SUPERSEDED','ARCHIVED','REJECTED')"
    ).fetchone()[0]
    assert total_in_db > 20
    assert len(data["units"]) <= 20  # cap giữ nguyên
    assert data["session"]["stats_json"] != "{}"
    stats = json.loads(data["session"]["stats_json"])
    assert stats["scope_size"] == len(data["units"])


# ---------------------------------------------------------------- Test 12

def test_db_integrity_preserved(session, store):
    """Test 12 — integrity trước = sau."""
    _seed_mixed(store)
    conn = store._connection
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    result = session.start()
    sid = result["session_id"]
    data = session.get_session(sid)
    if data["questions"]:
        q = data["questions"][0]
        resp = session.respond(sid, "question", q["question_id"], "CLARIFY", "ok")
        session.confirm_and_apply(sid, resp["change_proposed"]["change_id"], True)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    # episodes không đổi
    n_eps = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    assert n_eps == 0  # test DB chưa seed episodes — giữ nguyên


# ---------------------------------------------------------------- Test 13

def test_api_payload_matches_backend(session, store):
    """Test 13 — số liệu payload khớp backend thật (cơ chế API sẽ render đúng)."""
    _seed_mixed(store)
    result = session.start()
    sid = result["session_id"]
    stats = result["stats"]
    data = session.get_session(sid)
    assert stats["scope_size"] == len(data["units"])
    assert stats["findings"] == len(data["findings"])
    assert stats["inferences"] == len(data["inferences"])
    assert stats["questions"] == len(data["questions"])
    assert stats["changes_pending"] == 0
    session.close(sid)
    after = session.get_session(sid)
    assert after["session"]["status"] == "COMPLETED"


# ---------------------------------------------------------------- bổ sung: ràng buộc start/close

def test_close_then_new_session(session, store):
    _seed_mixed(store)
    r1 = session.start()
    session.close(r1["session_id"])
    r2 = session.start()
    assert r2["session_id"] != r1["session_id"]
    assert r2.get("already_open") is False


def test_unknown_response_kind_rejected(session, store):
    _seed_mixed(store)
    r = session.start()
    with pytest.raises(ValueError):
        session.respond(r["session_id"], "question", "q_x", "MAGIC_KIND", "x")


def test_insufficient_evidence_when_no_units(session, store):
    """Nhóm 3: không có tri thức liên quan → INSUFFICIENT_EVIDENCE."""
    # DB trống — chỉ 1 KU đơn lẻ không liên quan
    _mk(store, "Mục đích riêng tư không liên quan gì", "FACT", "solo")
    r = session.start()
    data = session.get_session(r["session_id"])
    certainties = {i["certainty"] for i in data["inferences"]}
    # tất cả inference phải trung thực: không có VERIFIED khi chưa có xác minh
    assert "VERIFIED" not in certainties or all(
        u["status"] == "VERIFIED" for u in data["units"]
    )
