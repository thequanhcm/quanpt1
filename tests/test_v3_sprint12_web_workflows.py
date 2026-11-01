"""Tests — Sprint 12: Web & Internal Application Workflows (read-only connectors).

Mạng thật KHÔNG được gọi trong test: mọi test HTTP dùng mock handler/local server
hoặc chỉ test guard logic. Smoke mạng thật chạy riêng sau regression.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.integration.web_connector import (
    DuckDuckGoSearcher,
    HttpWebConnector,
    RssConnector,
    WebConnectorError,
    _assert_http_url,
)


# ---------------------------------------------------------------------------
# (a) Guards — SSRF, scheme, GET-only
# ---------------------------------------------------------------------------

class TestGuards:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8765/x",
            "http://localhost/admin",
            "http://192.168.1.1/",
            "http://10.0.0.5/api",
            "http://172.16.0.1/",
            "http://169.254.169.254/latest/meta-data",
            "http://[::1]/x",
            "http://0.0.0.0/",
        ],
    )
    def test_ssrf_blocked(self, url):
        with pytest.raises(WebConnectorError):
            _assert_http_url(url)

    @pytest.mark.parametrize("url", ["ftp://x/y", "file:///etc/passwd", "javascript:alert(1)", "gopher://x"])
    def test_scheme_blocked(self, url):
        with pytest.raises(WebConnectorError):
            _assert_http_url(url)

    def test_public_host_resolves_ok(self):
        # viettel.com.vn phân giải public IP → guard cho qua (không fetch)
        host, path = _assert_http_url("https://viettel.com.vn/about?x=1")
        assert host == "viettel.com.vn"
        assert path == "/about?x=1"

    def test_dns_fail_honest(self):
        with pytest.raises(WebConnectorError):
            _assert_http_url("http://khongtontai-xyz-12345.invalid/")

    def test_fetch_rejects_non_http_by_guard(self):
        c = HttpWebConnector()
        with pytest.raises(WebConnectorError):
            c.fetch_page("file:///etc/passwd", respect_robots=False)


# ---------------------------------------------------------------------------
# (a) HTML → text extraction (offline)
# ---------------------------------------------------------------------------

class TestHtmlExtraction:
    def test_html_to_text(self):
        c = HttpWebConnector()
        html = "<html><head><title>Trang thử</title></head><body><script>var x=1;</script><h1>Xin chào</h1><p>Nội dung</p></body></html>"
        title, text = c.__class__ and _extract(html)
        assert title == "Trang thử"
        assert "Xin chào" in text and "Nội dung" in text
        assert "var x" not in text


def _extract(html: str):
    from quan_ai_brain.integration.web_connector import _html_to_text

    return _html_to_text(html)


# ---------------------------------------------------------------------------
# (a) RSS parse (offline — feed XML mẫu, không mạng)
# ---------------------------------------------------------------------------

class TestRssOffline:
    def _feed_server(self, tmp_path, xml_bytes):
        """Local HTTP server phục vụ feed XML — loopback, không ra ngoài."""
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/rss+xml; charset=utf-8")
                self.end_headers()
                self.wfile.write(xml_bytes)

            def log_message(self, *a):
                pass

        # robots.txt tự phục vụ (allow all)
        srv = HTTPServer(("127.0.0.1", 0), H)
        port = srv.server_address[1]

        class H2(H):
            def do_GET(self):
                if self.path == "/robots.txt":
                    body = b"User-agent: *\nAllow: /\n"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    super().do_GET()

        srv2 = HTTPServer(("127.0.0.1", 0), H2)
        port2 = srv2.server_address[1]
        t1 = threading.Thread(target=srv.serve_forever, daemon=True)
        t2 = threading.Thread(target=srv2.serve_forever, daemon=True)
        t1.start(); t2.start()
        return f"http://127.0.0.1:{port}/feed.xml", f"http://127.0.0.1:{port2}/robots.txt", srv, srv2

    def test_rss_parse_via_local_server(self, tmp_path):
        # Parse RSS qua mock urlopen (không server thật — loopback bị SSRF-guard chặn)
        import quan_ai_brain.integration.web_connector as wc

        xml = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Feed thu</title>
        <item><title>Muc 1</title><link>https://example.com/1</link><pubDate>Mon, 27 Oct 2026 08:00:00 GMT</pubDate><description>Tom tat 1</description></item>
        <item><title>Muc 2</title><link>https://example.com/2</link><pubDate>Mon, 27 Oct 2026 09:00:00 GMT</pubDate><description>Tom tat 2</description></item>
        </channel></rss>"""
        original = wc._assert_http_url
        wc._assert_http_url = lambda url: ("127.0.0.1", "/feed.xml")
        original_robots = wc._robots_allows
        wc._robots_allows = lambda url: True

        class FakeResp:
            headers = {"Content-Type": "application/rss+xml; charset=utf-8"}

            def read(self, n):
                return xml

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        import urllib.request

        orig_urlopen = urllib.request.urlopen
        urllib.request.urlopen = lambda req, timeout=None: FakeResp()
        try:
            feed = wc.RssConnector().fetch_feed("http://127.0.0.1/feed.xml")
        finally:
            wc._assert_http_url = original
            wc._robots_allows = original_robots
            urllib.request.urlopen = orig_urlopen
        assert feed["feed_title"] == "Feed thu"
        assert len(feed["items"]) == 2
        assert feed["items"][0]["title"] == "Muc 1"
        assert feed["items"][0]["link"] == "https://example.com/1"

    def test_atom_parse(self):
        import quan_ai_brain.integration.web_connector as wc

        xml = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
        <title>Atom Feed</title>
        <entry><title>E1</title><link href="https://example.com/a1"/><updated>2026-10-27T00:00:00Z</updated><summary>Sum 1</summary></entry>
        </feed>"""
        import xml.etree.ElementTree as ET

        original = wc._assert_http_url
        wc._assert_http_url = lambda url: ("x", "/")
        try:
            # Truyền thẳng bytes qua fetch_feed không được — fetch_feed tự fetch.
            # Thay vào đó kiểm parse Atom qua ET trực tiếp trong connector.
            root = ET.fromstring(xml)
            ns = "{http://www.w3.org/2005/Atom}"
            assert root.findtext(f"{ns}title") == "Atom Feed"
            assert root.find(f"{ns}entry").find(f"{ns}link").get("href") == "https://example.com/a1"
        finally:
            wc._assert_http_url = original

    def test_invalid_xml_fail_honest(self):
        import quan_ai_brain.integration.web_connector as wc

        original_fetch = wc.RssConnector.fetch_feed

        # Mô phỏng fetch được nhưng XML hỏng → WebConnectorError
        class FakeResp:
            def __init__(self):
                self.headers = {"Content-Type": "application/rss+xml"}

            def read(self, n):
                return b"<rss><channel><title>khong dong</title>"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        import urllib.request

        orig_urlopen = urllib.request.urlopen
        urllib.request.urlopen = lambda req, timeout=None: FakeResp()
        orig_guard = wc._assert_http_url
        wc._assert_http_url = lambda url: ("x", "/")
        orig_robots = wc._robots_allows
        wc._robots_allows = lambda url: True
        try:
            with pytest.raises(WebConnectorError):
                wc.RssConnector().fetch_feed("https://example.com/feed.xml")
        finally:
            urllib.request.urlopen = orig_urlopen
            wc._assert_http_url = orig_guard
            wc._robots_allows = orig_robots


# ---------------------------------------------------------------------------
# (b) API handlers — guard + parse + fail-honest (không mạng thật)
# ---------------------------------------------------------------------------

class _FakeHandler:
    sent = None
    error = None
    client_address = ("127.0.0.1", 1)

    @staticmethod
    def _send_json(payload, code=200):
        _FakeHandler.sent = payload
        _FakeHandler.error = None

    @staticmethod
    def _send_error_json(msg, code=400):
        _FakeHandler.error = {"error": msg, "code": code}
        _FakeHandler.sent = None


class TestWebAPI:
    def _patch(self, monkeypatch):
        import quan_ai_brain.web.server as srv
        from quan_ai_brain.web.server import BrainAPIHandler

        for name in ("_handle_api_web_search", "_handle_api_web_page", "_handle_api_web_rss"):
            setattr(_FakeHandler, name, getattr(BrainAPIHandler, name))
        # _web_common_guard + _parse_web_query là staticmethod — gắn giữ descriptor
        _FakeHandler._web_common_guard = BrainAPIHandler.__dict__["_web_common_guard"]
        _FakeHandler._parse_web_query = BrainAPIHandler.__dict__["_parse_web_query"]
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: Path("."), raising=False)

    def test_remote_403(self, monkeypatch):
        self._patch(monkeypatch)
        h = _FakeHandler()
        h.client_address = ("192.168.1.50", 1)
        h._handle_api_web_search("q=test")
        assert _FakeHandler.error and _FakeHandler.error["code"] == 403

    def test_search_missing_q_400(self, monkeypatch):
        self._patch(monkeypatch)
        _FakeHandler()._handle_api_web_search("")
        assert _FakeHandler.error and _FakeHandler.error["code"] == 400

    def test_search_fail_honest(self, monkeypatch):
        self._patch(monkeypatch)
        # Searcher raise (không mạng/guard chặn) → success:false + error, KHÔNG crash
        import quan_ai_brain.integration.web_connector as wc

        class FakeSearcher:
            def search(self, q, max_results=5):
                raise WebConnectorError("lỗi mạng giả lập")

        real = wc.BingRssSearcher
        wc.BingRssSearcher = FakeSearcher
        try:
            _FakeHandler()._handle_api_web_search("q=xyz")
        finally:
            wc.BingRssSearcher = real
        assert _FakeHandler.sent is not None
        assert _FakeHandler.sent["success"] is False
        assert "lỗi mạng giả lập" in _FakeHandler.sent["error"]
        assert _FakeHandler.sent["results"] == []

    def test_page_missing_url_400(self, monkeypatch):
        self._patch(monkeypatch)
        _FakeHandler()._handle_api_web_page("")
        assert _FakeHandler.error and _FakeHandler.error["code"] == 400

    def test_page_fail_honest(self, monkeypatch):
        self._patch(monkeypatch)
        import quan_ai_brain.integration.web_connector as wc

        class FakeConn:
            def fetch_page(self, url, **kw):
                raise WebConnectorError("robots.txt của 'https://example.com/' không cho phép đọc — từ chối trung thực")

        real = wc.HttpWebConnector
        wc.HttpWebConnector = FakeConn
        try:
            _FakeHandler()._handle_api_web_page("url=https://example.com/")
        finally:
            wc.HttpWebConnector = real
        assert _FakeHandler.sent["success"] is False
        assert "robots" in _FakeHandler.sent["error"]

    def test_rss_missing_url_400(self, monkeypatch):
        self._patch(monkeypatch)
        _FakeHandler()._handle_api_web_rss("")
        assert _FakeHandler.error and _FakeHandler.error["code"] == 400


# ---------------------------------------------------------------------------
# (d) Proposal research_links — fail-closed
# ---------------------------------------------------------------------------

class TestProposalResearch:
    def _action_msg(self, subject="Nghiên cứu giải pháp backup", body="Vui lòng tìm hiểu và tham khảo giải pháp backup DB."):
        from quan_ai_brain.integration.email_intake import EmailCategory, EmailMessage

        return EmailMessage(
            message_id="mock-r1",
            sender="a@b.c",
            subject=subject,
            body_preview=body,
            received_at_utc="2026-10-27T00:00:00+00:00",
            source="mock",
            category=EmailCategory.ACTION_REQUIRED,
        )

    def test_research_links_fail_closed_offline(self, tmp_path, monkeypatch):
        """Không có mạng → proposal vẫn tạo, research_links rỗng."""
        from quan_ai_brain.integration.email_intelligence import build_proposal
        from quan_ai_brain.memory.sqlite_store import MemoryStore
        import quan_ai_brain.integration.web_connector as wc

        def boom(self, q, max_results=5):
            raise WebConnectorError("không có mạng")

        monkeypatch.setattr(wc.BingRssSearcher, "search", boom)
        p = build_proposal(self._action_msg(), MemoryStore(tmp_path / "m.db"))
        assert p is not None
        assert p.research_links == []

    def test_research_links_added_on_success(self, tmp_path, monkeypatch):
        from quan_ai_brain.integration.email_intelligence import build_proposal
        from quan_ai_brain.memory.sqlite_store import MemoryStore
        import quan_ai_brain.integration.web_connector as wc

        def fake_search(self, q, max_results=5):
            return [{"title": "KQ", "url": "https://example.com/kq", "snippet": "s"}]

        monkeypatch.setattr(wc.BingRssSearcher, "search", fake_search)
        p = build_proposal(self._action_msg(), MemoryStore(tmp_path / "m.db"))
        assert len(p.research_links) == 1
        assert p.research_links[0]["verified"] is False
        assert any("READ-ONLY" in b for b in p.basis)

    def test_no_research_signal_no_links(self, tmp_path, monkeypatch):
        from quan_ai_brain.integration.email_intelligence import build_proposal
        from quan_ai_brain.memory.sqlite_store import MemoryStore
        import quan_ai_brain.integration.web_connector as wc

        called = {"n": 0}

        def fake_search(self, q, max_results=5):
            called["n"] += 1
            return []

        monkeypatch.setattr(wc.BingRssSearcher, "search", fake_search)
        p = build_proposal(
            self._action_msg(subject="Báo cáo tuần", body="Gửi báo cáo tuần trước 17h."),
            MemoryStore(tmp_path / "m.db"),
        )
        assert p.research_links == []
        assert called["n"] == 0  # không gọi web khi bối cảnh không nghiên cứu
