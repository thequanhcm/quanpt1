"""Tests external_lookup — tra cứu ngoài (tin tức, giá...).

Quy tắc test repo: KHÔNG gọi mạng thật; KHÔNG đọc key thật. HTTP được mock qua
patch urllib.request.urlopen; env GEMINI_API_KEY được set/clear trong test env.
"""

from __future__ import annotations

import io
import time
import xml.sax.saxutils as saxutils
from unittest.mock import patch

import pytest

from quan_ai_brain.tools.external_lookup import (
    ExternalEvidence,
    _rss_cache,
    collect_external_evidence,
    fetch_news_rss,
    gemini_search_evidence,
    should_lookup_external,
)


def _rss_xml(items: list[tuple[str, str]]) -> bytes:
    rows = "".join(
        "<item><title>" + saxutils.escape(t) + "</title>"
        "<link>https://example.vn/a" + str(i) + "</link>"
        "<pubDate>Mon, 26 Oct 2026 10:0" + str(i) + ":00 +0700</pubDate></item>"
        for i, (t, _d) in enumerate(items)
    )
    return ("<?xml version=\"1.0\"?><rss><channel>" + rows + "</channel></rss>").encode("utf-8")


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return self._payload


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_SEARCH_MODEL", raising=False)
    _rss_cache.clear()
    yield


class TestShouldLookupExternal:
    @pytest.mark.parametrize(
        "query,expected",
        [
            ("tin tức Việt Nam hôm nay", True),
            ("giá vàng hôm nay bao nhiêu", True),
            ("tỷ giá USD hiện tại", True),
            ("thời tiết Hà Nội", True),
            ("tra cứu điểm thi", True),
            ("tìm kiếm thông tin AI", True),
            ("em đang ở đâu", False),
            ("trạng thái hệ thống", False),
            ("anh dạy em nhớ rằng PC Core ở tầng 3", False),
            ("ok", False),
        ],
    )
    def test_classification(self, query, expected):
        assert should_lookup_external(query) is expected


class TestExternalEvidence:
    def test_render_block_contains_sources_and_rule(self):
        ev = ExternalEvidence(
            query="giá vàng", source_layer="news_rss",
            summary="SJC 120 triệu lượng",
            sources=[{"title": "VnExpress", "url": "https://vnexpress.net"}],
        )
        block = ev.render_block()
        assert "BẰNG CHỨNG TRA CỨU NGOÀI" in block
        assert "SJC 120 triệu lượng" in block
        assert "https://vnexpress.net" in block
        assert "KHÔNG bịa số liệu" in block

    def test_empty_evidence_renders_nothing(self):
        assert ExternalEvidence(query="x", source_layer="none").render_block() == ""

    def test_is_empty_logic(self):
        assert ExternalEvidence(query="x", source_layer="none").is_empty()
        assert not ExternalEvidence(query="x", source_layer="news_rss",
                                    summary="s").is_empty()


class TestFetchNewsRss:
    def test_parses_items_and_caches(self, monkeypatch):
        xml = _rss_xml([("Giá vàng tăng", "desc"), ("Cổ phiếu giảm", "desc")])

        def fake_urlopen(req, timeout=0):
            return _FakeResponse(xml)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        items = fetch_news_rss("giá vàng")
        assert len(items) == 2
        assert items[0]["title"] == "Giá vàng tăng"
        assert items[0]["url"].startswith("https://example.vn/")

        # Lần 2 dùng cache (urlopen không được gọi thêm)
        with patch("urllib.request.urlopen", side_effect=AssertionError("must be cached")):
            items2 = fetch_news_rss("giá vàng")
        assert items2 == items

    def test_network_failure_returns_empty(self, monkeypatch):
        def boom(req, timeout=0):
            raise OSError("network down")

        monkeypatch.setattr("urllib.request.urlopen", boom)
        assert fetch_news_rss("giá vàng") == []


class TestCollectExternalEvidence:
    def test_non_external_question_skips_everything(self):
        ev = collect_external_evidence("trạng thái hệ thống")
        assert ev.source_layer == "none"

    def test_no_key_falls_back_to_rss_layer(self, monkeypatch):
        # Không key → tầng 1 tắt (fail-closed) → tầng 2 RSS vẫn chạy (không cần key)
        xml = _rss_xml([("Tin A hôm nay", "d")])

        def fake_urlopen(req, timeout=0):
            return _FakeResponse(xml)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        ev = collect_external_evidence("tin tức hôm nay")
        assert ev.source_layer == "news_rss"
        assert len(ev.sources) == 1
        assert "nguồn thô" in ev.note

    def test_rss_layer_uses_gemini_when_key_present(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
        xml = _rss_xml([("Tin vàng hôm nay", "d")])
        gemini_json = {
            "candidates": [{"content": {"parts": [{"text": "Vàng tăng 2%."}]}}],
        }

        def fake_urlopen(req, timeout=0):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "generativelanguage" in url:
                return _FakeResponse(io.BytesIO(
                    __import__("json").dumps(gemini_json).encode()).read())
            return _FakeResponse(xml)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        ev = collect_external_evidence("giá vàng hôm nay")
        assert ev.source_layer == "news_rss"
        assert ev.summary == "Vàng tăng 2%."

    def test_gemini_search_layer_accepted_only_with_sources(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
        grounded = {
            "candidates": [{
                "content": {"parts": [{"text": "Kết quả có nguồn."}]},
                "groundingMetadata": {"groundingChunks": [
                    {"web": {"uri": "https://vnexpress.net/a", "title": "VNE"}}]},
            }],
        }

        def fake_urlopen(req, timeout=0):
            return _FakeResponse(__import__("json").dumps(grounded).encode())

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        # Reset cooldown để tầng 1 được thử
        import quan_ai_brain.tools.external_lookup as ex
        ex._search_cooldown_until = 0.0
        ev = gemini_search_evidence("giá vàng")
        assert ev.source_layer == "gemini_search"
        assert ev.sources[0]["url"] == "https://vnexpress.net/a"

    def test_gemini_search_cooldown_after_failure(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")

        def boom(req, timeout=0):
            raise OSError("429 quota")

        monkeypatch.setattr("urllib.request.urlopen", boom)
        import quan_ai_brain.tools.external_lookup as ex
        ex._search_cooldown_until = 0.0
        ev1 = gemini_search_evidence("giá vàng")
        assert ev1.source_layer == "none"
        # Lần 2 phải vào cooldown — KHÔNG gọi urlopen nữa
        with patch("urllib.request.urlopen", side_effect=AssertionError("cooldown")):
            ev2 = gemini_search_evidence("giá vàng khác")
        assert ev2.source_layer == "none"
        assert "cooldown" in ev2.note
        # dọn dẹp cho test khác
        ex._search_cooldown_until = 0.0
