"""Test Self-Improvement Loop (24/11/2026, owner: cherry tự hoàn thiện, tự học).

Bất biến kiểm chứng:
- log_unmatched ghi file local, không bao giờ raise.
- propose tạo đề xuất PENDING_REVIEW — KHÔNG tự áp.
- approve = điểm duyệt DUY NHẤT learned_keywords; duyệt 2 lần → từ chối.
- detect_intent nhận kw đã duyệt (fail-open khi thiếu file).
- Kw tĩnh hệ thống vẫn ưu tiên hơn kw học được.
"""
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parent / "src"))

from tools.self_improvement import (  # noqa: E402
    LEARNED_PATH,
    PROPOSALS_PATH,
    UNMATCHED_PATH,
    approve,
    list_proposals,
    log_unmatched,
    propose,
    read_learned,
    stats,
)


@pytest.fixture(autouse=True)
def _clean_state(tmp_path, monkeypatch):
    """Cô lập state self_improve vào tmp_path — không đụng data thật."""
    import tools.self_improvement as si

    monkeypatch.setattr(si, "DATA_DIR", tmp_path)
    monkeypatch.setattr(si, "UNMATCHED_PATH", tmp_path / "unmatched.jsonl")
    monkeypatch.setattr(si, "PROPOSALS_PATH", tmp_path / "proposals.json")
    monkeypatch.setattr(si, "LEARNED_PATH", tmp_path / "learned.json")
    yield


def test_log_unmatched_creates_file(tmp_path):
    log_unmatched("tổng hợp tiến độ dự án", sender="owner")
    assert (tmp_path / "unmatched.jsonl").exists()
    entry = json.loads((tmp_path / "unmatched.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert entry["text"] == "tổng hợp tiến độ dự án"


def test_log_unmatched_never_raises():
    # text rỗng/None/ký tự lạ không được raise
    log_unmatched("")
    log_unmatched(None)
    log_unmatched("x" * 5000)


def test_stats_counts_bigrams(tmp_path):
    for txt in ("gửi báo cáo a", "gửi báo cáo b", "gửi báo cáo c"):
        log_unmatched(txt)
    st = stats()
    assert st["total"] == 3
    words = dict(st["top"])
    assert words.get("gửi báo", 0) == 3
    assert words.get("báo cáo", 0) == 3


def test_propose_pending_not_applied(tmp_path):
    for txt in ("tổng hợp tiến độ a", "tổng hợp tiến độ b"):
        log_unmatched(txt)
    r = propose(min_count=2, max_proposals=5)
    assert r["ok"] is True and r["created"] >= 1
    # KHÔNG tự áp: learned phải trống
    assert read_learned() == {}
    pend = list_proposals("PENDING_REVIEW")["proposals"]
    assert len(pend) == r["created"]
    for p in pend.values():
        assert p["status"] == "PENDING_REVIEW"


def test_propose_empty_state(tmp_path):
    r = propose(min_count=2)
    assert r["ok"] is True and r["created"] == 0


def test_approve_flow_and_double_approve(tmp_path):
    for txt in ("xem tiến độ a", "xem tiến độ b"):
        log_unmatched(txt)
    r = propose(min_count=2)
    pend = list_proposals("PENDING_REVIEW")["proposals"]
    kw = list(pend.values())[0]["kw"]
    ok = approve(kw)
    assert ok["ok"] is True
    assert kw in read_learned().get(ok["intent"], [])
    # duyệt lần 2 → từ chối (không double-apply)
    again = approve(kw)
    assert again["ok"] is False


def test_approve_unknown_rejected(tmp_path):
    # Không có proposals.json → fail-honest với thông báo lỗi rõ ràng
    r = approve("khong ton tai xyz")
    assert r["ok"] is False
    # Có proposals.json nhưng kw lạ → "không tìm thấy"
    (tmp_path / "proposals.json").write_text("{}", encoding="utf-8")
    r2 = approve("khong ton tai xyz")
    assert r2["ok"] is False and "không tìm thấy" in r2["error"]


def test_detect_intent_uses_learned_kw(tmp_path, monkeypatch):
    import netchat_command_center as cc

    # kw giả lập đã duyệt: 'xem tiến độ' → tasks
    monkeypatch.setattr(cc, "_vmail_flag_unused", None, raising=False)
    learned_file = Path("data/self_improve_learned_test.json")
    learned_file.write_text(json.dumps({"tasks": ["xem tiến độ"]}, ensure_ascii=False), encoding="utf-8")
    import tools.self_improvement as si

    monkeypatch.setattr(si, "LEARNED_PATH", learned_file)
    try:
        # đọc qua read_learned của si (detect_intent import read_learned trong hàm)
        got = cc.detect_intent("xem tiến độ abc")
        assert got == "tasks"
    finally:
        learned_file.unlink(missing_ok=True)


def test_detect_intent_static_kw_wins_over_learned():
    # 'báo cáo' là kw tĩnh của report — kw learned không được lấn
    import netchat_command_center as cc

    assert cc.detect_intent("báo cáo") == "report"


def test_vmail_and_dynamic_kw_still_work():
    import netchat_command_center as cc

    assert cc.detect_intent("Tóm tắt 5 email gần nhất cho anh") == "email_today"
    assert cc.detect_intent("tắt vmail") == "vmail_toggle"
    assert cc.detect_intent("5 email gần nhất") == "email_today"


# ─── S2 AUTO-TUNE (24/11, owner: tự học liên tục) ───

def test_auto_cycle_creates_pending_dm_not_learned(tmp_path, monkeypatch):
    """S3-DM-GATE: auto_cycle không tự áp nữa, chỉ tạo pending_dm + chờ owner OK."""
    import tools.self_improvement as si

    monkeypatch.setattr(si, "DATA_DIR", tmp_path)
    for name in ("UNMATCHED_PATH", "PROPOSALS_PATH", "LEARNED_PATH", "AUTO_CONFIG_PATH",
                 "AUTO_BACKUP_PATH", "AUTO_STATE_PATH", "PENDING_DM_PATH"):
        monkeypatch.setattr(si, name, tmp_path / f"{name}.json")

    for txt in ("xem tiến độ a", "xem tiến độ b", "xem tiến độ c", "mở helpdesk"):
        si.log_unmatched(txt)
    rep = si.auto_cycle()
    assert rep["applied"] == []  # không tự áp nữa
    assert len(rep["requests"]) >= 1
    req = rep["requests"][0]
    assert req["kw"] == "tiến độ"
    assert req["intent"] == "tasks"
    # pending_dm có item WAITING_OWNER:
    pend = si.list_pending_dm()["items"]
    assert any(p["kw"] == "tiến độ" and p["status"] == "WAITING_OWNER" for p in pend.values())
    # learned RỖNG (chờ owner OK):
    assert si.read_learned() == {}
    # owner_ok mới áp:
    r = si.owner_ok("tất cả")
    assert r["ok"] and len(r["applied"]) >= 1
    learned = si.read_learned()
    assert "tiến độ" in learned.get("tasks", [])
    assert "tiến độ" in learned.get("_auto", [])
    # backup đã tạo:
    assert si.AUTO_BACKUP_PATH.exists()
    # detect_intent nhận kw đã OK:
    import netchat_command_center as cc
    assert cc.detect_intent("tiến độ dự án abc") == "tasks"


def test_auto_cycle_skips_unclear_domain(tmp_path, monkeypatch):
    """S3-DM-GATE: kw không rõ miền -> KHÔNG tạo request (chờ owner OK)."""
    import tools.self_improvement as si

    monkeypatch.setattr(si, "DATA_DIR", tmp_path)
    for name in ("UNMATCHED_PATH", "PROPOSALS_PATH", "LEARNED_PATH", "AUTO_CONFIG_PATH",
                 "AUTO_BACKUP_PATH", "AUTO_STATE_PATH", "PENDING_DM_PATH"):
        monkeypatch.setattr(si, name, tmp_path / f"{name}.json")
    for txt in ("mở helpdesk a", "mở helpdesk b", "mở helpdesk c"):
        si.log_unmatched(txt)
    rep = si.auto_cycle()
    assert rep["applied"] == []  # không tự áp nữa
    assert rep["requests"] == []  # kw không rõ miền KHÔNG được build request
    assert si.read_learned() == {}


def test_auto_cycle_respects_off_switch(tmp_path, monkeypatch):
    import tools.self_improvement as si

    monkeypatch.setattr(si, "DATA_DIR", tmp_path)
    for name in ("UNMATCHED_PATH", "PROPOSALS_PATH", "LEARNED_PATH", "AUTO_CONFIG_PATH",
                 "AUTO_BACKUP_PATH", "AUTO_STATE_PATH"):
        monkeypatch.setattr(si, name, tmp_path / f"{name}.json")
    si.set_auto(auto_apply=False)
    for txt in ("xem tiến độ a", "xem tiến độ b", "xem tiến độ c"):
        si.log_unmatched(txt)
    rep = si.auto_cycle()
    assert rep["applied"] == []
    assert si.read_learned().get("_auto", []) == []


def test_rollback_restores_backup(tmp_path, monkeypatch):
    """S3-DM-GATE: owner_ok -> backup được tạo -> rollback phục hồi."""
    import tools.self_improvement as si

    monkeypatch.setattr(si, "DATA_DIR", tmp_path)
    for name in ("UNMATCHED_PATH", "PROPOSALS_PATH", "LEARNED_PATH", "AUTO_CONFIG_PATH",
                 "AUTO_BACKUP_PATH", "AUTO_STATE_PATH", "PENDING_DM_PATH"):
        monkeypatch.setattr(si, name, tmp_path / f"{name}.json")
    for txt in ("xem tiến độ a", "xem tiến độ b", "xem tiến độ c"):
        si.log_unmatched(txt)
    si.auto_cycle()
    si.owner_ok("tất cả")  # backup + learned
    assert "tiến độ" in si.read_learned().get("_auto", [])
    r = si.rollback("toàn bộ")
    assert r["ok"] is True
    assert si.read_learned().get("_auto", []) == []


def test_rollback_no_backup_fail_honest(tmp_path, monkeypatch):
    import tools.self_improvement as si

    monkeypatch.setattr(si, "DATA_DIR", tmp_path)
    for name in ("UNMATCHED_PATH", "PROPOSALS_PATH", "LEARNED_PATH", "AUTO_CONFIG_PATH",
                 "AUTO_BACKUP_PATH", "AUTO_STATE_PATH"):
        monkeypatch.setattr(si, name, tmp_path / f"{name}.json")
    r = si.rollback("toàn bộ")
    assert r["ok"] is False and "không có backup" in r["error"]


def test_auto_never_overrides_static_kw(tmp_path, monkeypatch):
    """S3-DM-GATE: kw trùng kw tĩnh KHÔNG được build request (vì sẽ bị static ưu tiên)."""
    import tools.self_improvement as si

    monkeypatch.setattr(si, "DATA_DIR", tmp_path)
    for name in ("UNMATCHED_PATH", "PROPOSALS_PATH", "LEARNED_PATH", "AUTO_CONFIG_PATH",
                 "AUTO_BACKUP_PATH", "AUTO_STATE_PATH", "PENDING_DM_PATH"):
        monkeypatch.setattr(si, name, tmp_path / f"{name}.json")
    # 'báo cáo' là kw tĩnh report — lặp 3 lần nhưng auto phải BỎ vì trùng kw tĩnh:
    for txt in ("báo cáo abc", "báo cáo bcd", "báo cáo cde"):
        si.log_unmatched(txt)
    rep = si.auto_cycle()
    kws_req = {a["kw"] for a in rep["requests"]}
    assert "báo cáo" not in kws_req


# ─── S3-DM-GATE (24/11, owner: trước khi học gửi DM, anh OK/duyệt mới thực hiện) ───

def test_owner_ok_partial_one_keyword(tmp_path, monkeypatch):
    """owner_ok nhận 1 kw cụ thể — chỉ duyệt đúng kw đó."""
    import tools.self_improvement as si
    monkeypatch.setattr(si, "DATA_DIR", tmp_path)
    for name in ("UNMATCHED_PATH", "PROPOSALS_PATH", "LEARNED_PATH", "AUTO_CONFIG_PATH",
                 "AUTO_BACKUP_PATH", "AUTO_STATE_PATH", "PENDING_DM_PATH"):
        monkeypatch.setattr(si, name, tmp_path / f"{name}.json")
    for txt in ("xem tiến độ a", "xem tiến độ b", "xem tiến độ c",
                "xem lịch họp d", "xem lịch họp e", "xem lịch họp f"):
        si.log_unmatched(txt)
    si.auto_cycle()
    r = si.owner_ok("tiến độ")
    assert r["ok"] and len(r["applied"]) == 1
    learned = si.read_learned()
    assert "tiến độ" in learned.get("tasks", [])
    assert "lịch họp" not in (learned.get("tasks", []) + sum(learned.values(), []))


def test_owner_reject_blocks_pending(tmp_path, monkeypatch):
    """owner_reject: REJECTED — không học."""
    import tools.self_improvement as si
    monkeypatch.setattr(si, "DATA_DIR", tmp_path)
    for name in ("UNMATCHED_PATH", "PROPOSALS_PATH", "LEARNED_PATH", "AUTO_CONFIG_PATH",
                 "AUTO_BACKUP_PATH", "AUTO_STATE_PATH", "PENDING_DM_PATH"):
        monkeypatch.setattr(si, name, tmp_path / f"{name}.json")
    for txt in ("xem tiến độ a", "xem tiến độ b", "xem tiến độ c"):
        si.log_unmatched(txt)
    si.auto_cycle()
    pend_before = si.list_pending_dm()
    assert pend_before["items"]
    r = si.owner_reject("tất cả")
    assert r["ok"] and len(r["rejected"]) >= 1
    pend_after = si.list_pending_dm()
    assert not pend_after["items"]  # đã rỗng WAITING_OWNER
    # learned RỖNG (vì reject):
    assert si.read_learned() == {}


def test_owner_ok_unknown_fails_honest(tmp_path, monkeypatch):
    """owner_ok với kw không có trong pending → fail-honest."""
    import tools.self_improvement as si
    monkeypatch.setattr(si, "DATA_DIR", tmp_path)
    for name in ("UNMATCHED_PATH", "PROPOSALS_PATH", "LEARNED_PATH", "AUTO_CONFIG_PATH",
                 "AUTO_BACKUP_PATH", "AUTO_STATE_PATH", "PENDING_DM_PATH"):
        monkeypatch.setattr(si, name, tmp_path / f"{name}.json")
    # seed 1 pending để có hàng chờ:
    for txt in ("xem tiến độ a", "xem tiến độ b", "xem tiến độ c"):
        si.log_unmatched(txt)
    si.auto_cycle()
    # giờ OK kw lạ → "không tìm thấy":
    r = si.owner_ok("kw không tồn tại")
    assert r["ok"] is False and "không tìm thấy" in r["error"]


def test_detect_intent_ok_all_routes_to_self_improve():
    """detect_intent cho 'ok/oke/ok hết/duyệt hết/đồng ý hết/hủy học' → self_improve."""
    import netchat_command_center as cc
    for t in ("ok", "oke", "okie", "okay", "ok anh",
              "ok hết", "ok het", "duyệt hết", "duyet het",
              "đồng ý hết", "dong y het", "duyệt tất cả", "duyet tat ca",
              "hủy học", "huy hoc", "từ chối", "tu choi"):
        assert cc.detect_intent(t) == "self_improve", f"FAIL on {t!r}"
