"""SEC-S2: NodeRegistry + LanScanner + CloudConnector + DM routing liên bang.

Mock 100% (probe transport qua monkeypatch, tmp_path); live scan thật thuộc
live smoke ở báo cáo. Không mạng thật trong test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE))

from quan_ai_brain.federation.node_registry import FedNode, NodeRegistry  # noqa: E402


@pytest.fixture()
def registry(tmp_path: Path) -> NodeRegistry:
    return NodeRegistry(tmp_path / "fed.db")


# ---------------------------------------------------------------------------
# (a) NodeRegistry
# ---------------------------------------------------------------------------
class TestNodeRegistry:
    def test_register_and_get(self, registry: NodeRegistry) -> None:
        n = registry.register("EDGE", "192.168.1.21", label="Pi5 bàn làm việc",
                              capabilities=["kiosk", "audio"])
        assert n.kind == "EDGE" and n.host == "192.168.1.21"
        assert n.status == "UNKNOWN"
        got = registry.get(n.node_id)
        assert got is not None and got.label == "Pi5 bàn làm việc"
        assert got.capabilities == ["kiosk", "audio"]

    def test_register_upsert_idempotent(self, registry: NodeRegistry) -> None:
        registry.register("EDGE", "192.168.1.21", node_id="edge_pi5", label="a")
        registry.register("EDGE", "192.168.1.21", node_id="edge_pi5", label="b")
        assert len(registry.list_nodes()) == 1
        assert registry.get("edge_pi5").label == "b"

    def test_register_validation(self, registry: NodeRegistry) -> None:
        with pytest.raises(ValueError):
            registry.register("UFO", "1.2.3.4")           # kind sai
        with pytest.raises(ValueError):
            registry.register("EDGE", "   ")               # thiếu host

    def test_remove(self, registry: NodeRegistry) -> None:
        n = registry.register("EDGE", "10.0.0.5")
        assert registry.remove(n.node_id) is True
        assert registry.get(n.node_id) is None
        assert registry.remove(n.node_id) is False

    def test_probe_updates_status(self, registry: NodeRegistry, monkeypatch) -> None:
        n = registry.register("EDGE", "192.168.1.99")
        monkeypatch.setattr(NodeRegistry, "ping_host", staticmethod(lambda h, t=1200: True))
        r = registry.probe_node(n.node_id)
        assert r["status"] == "REACHABLE" and r["changed"] is True
        # probe lần 2 vẫn reachable → changed False
        r2 = registry.probe_node(n.node_id)
        assert r2["status"] == "REACHABLE" and r2["changed"] is False
        # chết → UNREACHABLE + changed
        monkeypatch.setattr(NodeRegistry, "ping_host", staticmethod(lambda h, t=1200: False))
        r3 = registry.probe_node(n.node_id)
        assert r3["status"] == "UNREACHABLE" and r3["changed"] is True
        node = registry.get(n.node_id)
        assert node.status == "UNREACHABLE"
        assert node.last_seen_at != ""                    # giữ mốc thấy cuối

    def test_probe_connector_rejected(self, registry: NodeRegistry) -> None:
        registry.register("CONNECTOR", "api.example.com")
        nid = registry.list_nodes(kind="CONNECTOR")[0].node_id
        r = registry.probe_node(nid)
        assert r["success"] is False and "connector" in r["error"]

    def test_probe_missing_node(self, registry: NodeRegistry) -> None:
        assert registry.probe_node("khong_ton_tai")["success"] is False

    def test_ping_host_heuristic_real_loopback(self) -> None:
        # ping loopback là thật, không ra ngoài mạng — chạy được trên mọi PC
        assert NodeRegistry.ping_host("127.0.0.1") is True


# ---------------------------------------------------------------------------
# (b) LanScanner (mock subprocess)
# ---------------------------------------------------------------------------
class TestLanScanner:
    def test_scan_parses_devices(self, tmp_path: Path, monkeypatch) -> None:
        from quan_ai_brain.federation.lan_scanner import LanScanner

        scanner = LanScanner("192.168.1")
        monkeypatch.setattr(LanScanner, "_detect_local_ip", staticmethod(lambda: "192.168.1.9"))
        monkeypatch.setattr(LanScanner, "_ping_one",
                            staticmethod(lambda ip, t=500: ip if ip.endswith((".1", ".2", ".9")) else None))
        monkeypatch.setattr(LanScanner, "_arp_table",
                            staticmethod(lambda: {"192.168.1.1": "fc-57-03-e1-e3-30",
                                                  "192.168.1.2": "dc-a6-32-aa-bb-cc"}))
        monkeypatch.setattr(LanScanner, "_reverse_dns", staticmethod(lambda ip: ""))
        devices = scanner.scan()
        ips = [d.ip for d in devices]
        assert ips == ["192.168.1.1", "192.168.1.2", "192.168.1.9"]
        pi = [d for d in devices if d.vendor_hint == "Raspberry Pi"]
        assert len(pi) == 1 and pi[0].ip == "192.168.1.2"   # OUI Pi nhận ra

    def test_registered_marker(self, tmp_path: Path, monkeypatch) -> None:
        from quan_ai_brain.federation.lan_scanner import LanScanner

        monkeypatch.setattr(LanScanner, "_detect_local_ip", staticmethod(lambda: "10.0.0.7"))
        monkeypatch.setattr(LanScanner, "_ping_one",
                            staticmethod(lambda ip, t=500: ip if ip.endswith(".21") else None))
        monkeypatch.setattr(LanScanner, "_arp_table", staticmethod(lambda: {}))
        monkeypatch.setattr(LanScanner, "_reverse_dns", staticmethod(lambda ip: ""))
        s = LanScanner("10.0.0")
        summary = s.scan_summary(registered_hosts={"10.0.0.21": "edge_pi5"})
        assert summary["total_alive"] == 1
        assert summary["registered_nodes_seen"][0]["node_id"] == "edge_pi5"

    def test_subnet_from_local_ip(self, monkeypatch) -> None:
        from quan_ai_brain.federation.lan_scanner import LanScanner

        monkeypatch.setattr(LanScanner, "_detect_local_ip", staticmethod(lambda: "10.1.2.3"))
        s = LanScanner()
        assert s.subnet == "10.1.2"


# ---------------------------------------------------------------------------
# (c) CloudConnector — hạn ngạch fail-closed
# ---------------------------------------------------------------------------
class TestCloudConnector:
    def test_register_validation(self, registry: NodeRegistry) -> None:
        from quan_ai_brain.federation.cloud_connector import CloudConnectorManager

        mgr = CloudConnectorManager(registry)
        with pytest.raises(ValueError):
            mgr.register_connector("khong-domain")         # thiếu dot
        with pytest.raises(ValueError):
            mgr.register_connector("api.example.com", daily_cap=-1)
        node = mgr.register_connector("api.example.com", daily_cap=5)
        assert node.kind == "CONNECTOR" and node.daily_cap == 5

    def test_unregistered_refused(self, registry: NodeRegistry) -> None:
        from quan_ai_brain.federation.cloud_connector import CloudConnectorManager

        mgr = CloudConnectorManager(registry)
        r = mgr.call_with_budget("unknown.cloud", {}, lambda p: "x")
        assert r.allowed is False and "CHƯA ĐĂNG KÝ" in r.reason

    def test_budget_blocks_at_cap(self, registry: NodeRegistry) -> None:
        from quan_ai_brain.federation.cloud_connector import CloudConnectorManager

        mgr = CloudConnectorManager(registry)
        mgr.register_connector("api.cap.com", daily_cap=2)
        calls = []
        for i in range(3):
            r = mgr.call_with_budget("api.cap.com", {"i": i}, lambda p: calls.append(p) or "ok")
        assert calls == [{"i": 0}, {"i": 1}]              # 2 lượt đầu đi qua
        assert r.allowed is False and "VƯỢT HẠN NGẠCH" in r.reason
        assert r.remaining_today == 0

    def test_zero_cap_blocked(self, registry: NodeRegistry) -> None:
        from quan_ai_brain.federation.cloud_connector import CloudConnectorManager

        mgr = CloudConnectorManager(registry)
        mgr.register_connector("api.zero.com", daily_cap=0)
        r = mgr.call_with_budget("api.zero.com", {}, lambda p: "x")
        assert r.allowed is False and "BLOCKED" in r.reason

    def test_fn_error_not_counted(self, registry: NodeRegistry) -> None:
        from quan_ai_brain.federation.cloud_connector import CloudConnectorManager

        mgr = CloudConnectorManager(registry)
        mgr.register_connector("api.err.com", daily_cap=3)

        def boom(p):
            raise RuntimeError("lỗi thật")
        r = mgr.call_with_budget("api.err.com", {}, boom)
        assert r.allowed is False and "RuntimeError" in r.reason
        node = registry.get("conn_api_err_com")
        assert node.calls_today == 0                       # lỗi không tính hạn ngạch


# ---------------------------------------------------------------------------
# (d) Lệnh DM liên bang
# ---------------------------------------------------------------------------
class TestFederationDm:
    def test_route_fed_status_empty(self, tmp_path, monkeypatch) -> None:
        import tools.netchat_security_center as sec

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        intent, reply = sec.route_security_command("liên bang")
        assert intent == "lien_bang"
        assert "LIÊN BANG" in reply and "chưa đăng ký" in reply

    def test_route_scan(self, tmp_path, monkeypatch) -> None:
        import tools.netchat_security_center as sec
        from quan_ai_brain.federation.lan_scanner import LanScanner

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        fake = {"scanned_at": "2026-11-02T08:00:00+00:00", "subnet": "192.168.1.0/24",
                "local_ip": "192.168.1.9", "total_alive": 2,
                "devices": [], "registered_nodes_seen": [], "raspberry_pi_candidates": []}
        monkeypatch.setattr(LanScanner, "scan_summary", lambda self, registered_hosts=None: fake)
        intent, reply = sec.route_security_command("quét mạng")
        assert intent == "quet_mang"
        assert "QUÉT MẠNG" in reply and "2" in reply

    def test_route_register_node_probes_real(self, tmp_path, monkeypatch) -> None:
        import tools.netchat_security_center as sec
        from quan_ai_brain.federation.node_registry import NodeRegistry

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        monkeypatch.setattr(NodeRegistry, "ping_host", staticmethod(lambda h, t=1200: False))
        intent, reply = sec.route_security_command("đăng ký nút edge 192.168.1.21 pi5 bàn làm việc")
        assert intent == "dang_ky_nut"
        assert "🔴" in reply and "192.168.1.21" in reply     # fail-honest: unreachable
        # đăng ký là thật (đã vào DB của WORKSPACE tạm)
        reg = NodeRegistry(tmp_path / "data" / "federation_nodes.db")
        assert len(reg.list_nodes(kind="EDGE")) == 1

    def test_route_register_connector(self, tmp_path, monkeypatch) -> None:
        import tools.netchat_security_center as sec
        from quan_ai_brain.federation.node_registry import NodeRegistry

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        intent, reply = sec.route_security_command("đăng ký đầu nối api.openai.com hạn ngạch: 50")
        assert intent == "dang_ky_dau_noi"
        assert "api.openai.com" in reply and "50" in reply
        reg = NodeRegistry(tmp_path / "data" / "federation_nodes.db")
        conn = reg.list_nodes(kind="CONNECTOR")[0]
        assert conn.daily_cap == 50

    def test_route_message_integration(self, tmp_path, monkeypatch) -> None:
        from tools.netchat_command_center import route_message

        monkeypatch.setattr("tools.netchat_security_center.WORKSPACE", tmp_path)
        monkeypatch.setattr("tools.netchat_security_center._dm_send", lambda text: None)
        intent, reply = route_message("liên bang")
        assert intent == "lien_bang"

    def test_federation_watchdog_cycle_alerts(self, tmp_path, monkeypatch) -> None:
        import tools.netchat_security_center as sec
        from quan_ai_brain.federation.node_registry import NodeRegistry

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        monkeypatch.setattr(sec, "_FED_ALERT_MARKER", tmp_path / "data" / "fed.json")
        registry = NodeRegistry(tmp_path / "data" / "federation_nodes.db")
        registry.register("EDGE", "192.168.1.99", node_id="edge_test")
        # lần 1 probe: UNKNOWN -> UNREACHABLE = changed → alert
        monkeypatch.setattr(NodeRegistry, "ping_host", staticmethod(lambda h, t=1200: False))
        sent: list[str] = []
        monkeypatch.setattr(sec, "_dm_send", lambda text: sent.append(text))
        n = sec.federation_watchdog_cycle()
        assert n == 1 and "MẤT KẾT NỐI" in sent[0]
        # lần 2 ngay sau: vẫn UNREACHABLE (không changed) → không alert nữa
        n2 = sec.federation_watchdog_cycle()
        assert n2 == 0 and len(sent) == 1
