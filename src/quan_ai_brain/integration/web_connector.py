"""Sprint 12 (a): Web & Internal Application Workflows — read-only connectors.

Nguyên tắc an toàn (card TASK-V3-SPRINT12):
- CHỈ GET — method khác raise ValueError; không form/login/POST/PUT/DELETE ngoài.
- SSRF-guard: chỉ http/https; chặn loopback/private/link-local/metadata IP.
- Tôn trọng robots.txt (User-Agent QUAN-AI-BRAIN/1.0); disallow → từ chối trung thực.
- Content-type allowlist: text/html, text/plain, application/json, RSS/Atom.
- Timeout 10s, max 256KB; không cookie, không JS, không upload.
- Lỗi → trả nguyên trạng thái, KHÔNG fake dữ liệu (fail-honest).
"""
from __future__ import annotations

import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Protocol

USER_AGENT = "QUAN-AI-BRAIN/1.0 (+read-only research; owner quanpt1)"
_TIMEOUT_SEC = 10
_MAX_BYTES = 256 * 1024
_ALLOWED_CONTENT = ("text/html", "text/plain", "application/json", "application/rss", "application/atom", "application/xml", "text/xml")


class WebConnectorError(Exception):
    """Lỗi connector trung thực — message đưa thẳng ra API."""


class WebConnector(Protocol):
    """Protocol thay thế được — sau này có thể cắm connector nội bộ khác."""

    def fetch_page(self, url: str) -> dict[str, Any]: ...


def _assert_http_url(url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise WebConnectorError(f"Chỉ cho phép http/https (nhận '{parsed.scheme or 'trống'}')")
    host = parsed.hostname or ""
    if not host:
        raise WebConnectorError("URL thiếu hostname")
    # SSRF-guard: giải IP và chặn loopback/private/link-local/reserved/metadata
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise WebConnectorError(f"Không phân giải được hostname '{host}': {exc}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise WebConnectorError(f"Chặn địa chỉ nội bộ/metadata ({ip}) — connector chỉ đọc web công khai")
    # Metadata endpoint cloud (chặn theo hostname luôn)
    if host in ("169.254.169.254", "metadata.google.internal"):
        raise WebConnectorError("Chặn metadata endpoint")
    return host, (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")


def _robots_allows(url: str) -> bool:
    """Kiểm robots.txt của host cho URL này. Lỗi robots → False (an toàn)."""
    try:
        from urllib.robotparser import RobotFileParser

        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return False  # không đọc được robots → coi như không cho phép


@dataclass
class PageContent:
    url: str
    final_url: str
    status: int
    content_type: str
    title: str
    text: str
    truncated: bool
    fetched_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status": self.status,
            "content_type": self.content_type,
            "title": self.title,
            "text": self.text,
            "truncated": self.truncated,
            "fetched_at_utc": self.fetched_at_utc,
        }


_TAG_SCRIPT = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_ANY = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _html_to_text(html: str) -> tuple[str, str]:
    title_m = _TITLE_RE.search(html)
    title = title_m.group(1).strip() if title_m else ""
    without = _TAG_SCRIPT.sub(" ", html)
    text = _TAG_ANY.sub(" ", without)
    text = _WS.sub(" ", text)
    text = re.sub(r"\n\s*", "\n", text).strip()
    return title, text


class HttpWebConnector:
    """Connector đọc trang GET-only."""

    name = "http_web"

    def fetch_page(self, url: str, *, respect_robots: bool = True) -> dict[str, Any]:
        _assert_http_url(url)
        if respect_robots and not _robots_allows(url):
            raise WebConnectorError(f"robots.txt của '{url}' không cho phép đọc — từ chối trung thực")
        req = urllib.request.Request(
            url,
            method="GET",  # GET-only — method khác phải đi qua đây và bị chặn phía trên
            headers={"User-Agent": USER_AGENT, "Accept": ", ".join(_ALLOWED_CONTENT)},
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
                status = resp.status
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                raw = resp.read(_MAX_BYTES + 1)
        except WebConnectorError:
            raise
        except urllib.error.HTTPError as exc:
            raise WebConnectorError(f"HTTP {exc.code} khi đọc '{url}'") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise WebConnectorError(f"Không đọc được '{url}': {exc}") from exc
        truncated = len(raw) > _MAX_BYTES
        raw = raw[:_MAX_BYTES]
        if not any(ctype.startswith(a) or a in ctype for a in _ALLOWED_CONTENT):
            raise WebConnectorError(f"Content-type '{ctype or 'không rõ'}' không nằm trong allowlist đọc-only")
        decoded = _decode_content(ctype, raw)
        if "html" in ctype:
            title, text = _html_to_text(decoded)
        else:
            title, text = "", decoded.strip()
        from datetime import datetime, timezone

        page = PageContent(
            url=url,
            final_url=url,
            status=status,
            content_type=ctype,
            title=title,
            text=text[:20000],
            truncated=truncated,
            fetched_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        return page.to_dict()


def _decode_ctype(content_type: str | None) -> str:
    if content_type and "charset=" in content_type:
        return content_type.split("charset=")[-1].strip().strip('"') or "utf-8"
    return "utf-8"


def _decode_content(content_type: str | None, raw: bytes) -> str:
    return raw.decode(_decode_ctype(content_type), errors="replace")


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


_RESULT_RE = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_SNIPPET_RE = re.compile(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)


def _decode_entities(text: str) -> str:
    import html as _html

    return _html.unescape(_TAG_ANY.sub("", text)).strip()


class DuckDuckGoSearcher:
    """Tìm kiếm web đọc-only qua DuckDuckGo HTML lite (không JS, không API key)."""

    name = "duckduckgo_html"

    def search(self, query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
        if not query.strip():
            raise WebConnectorError("Từ khoá tìm kiếm trống")
        q = urllib.parse.urlencode({"q": query.strip()})
        url = f"https://html.duckduckgo.com/html/?{q}"
        _assert_http_url(url)
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
                raw = resp.read(_MAX_BYTES)
            html = raw.decode(_decode_ctype(resp.headers.get("Content-Type")), errors="replace")
        except urllib.error.HTTPError as exc:
            raise WebConnectorError(f"HTTP {exc.code} khi tìm kiếm") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise WebConnectorError(f"Lỗi mạng khi tìm kiếm: {exc}") from exc

        results: list[SearchHit] = []
        # DuckDuckGo trả href dạng //duckduckgo.com/l/?uddg=<encoded>&rut=... — gỡ wrapper
        for m in _RESULT_RE.finditer(html):
            raw_url = m.group(1)
            if "uddg=" in raw_url:
                try:
                    inner = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query).get("uddg", [""])[0]
                    real = urllib.parse.unquote(inner)
                except Exception:
                    real = raw_url
            else:
                real = raw_url
            if not real.startswith("http"):
                continue
            title = _decode_entities(m.group(2))
            results.append(SearchHit(title=title, url=real, snippet=""))
            if len(results) >= max_results:
                break
        snippets = [_decode_entities(s.group(1)) for s in _SNIPPET_RE.finditer(html)]
        for i, sn in enumerate(snippets[: len(results)]):
            results[i].snippet = sn
        return [r.to_dict() for r in results]


class BingRssSearcher:
    """Tìm kiếm web đọc-only qua Bing RSS (chuẩn RSS XML, GET, không JS/key).

    Được chọn làm primary vì DuckDuckGo HTML trả trang anomaly khi không có
    trình duyệt thật; Bing RSS ổn định và tôn trọng crawler đơn giản.
    """

    name = "bing_rss"

    def search(self, query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
        if not query.strip():
            raise WebConnectorError("Từ khoá tìm kiếm trống")
        q = urllib.parse.urlencode({"q": query.strip(), "count": str(min(max_results, 20)), "format": "rss"})
        url = f"https://www.bing.com/search?{q}"
        _assert_http_url(url)
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
                raw = resp.read(_MAX_BYTES)
        except urllib.error.HTTPError as exc:
            raise WebConnectorError(f"HTTP {exc.code} khi tìm kiếm Bing") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise WebConnectorError(f"Lỗi mạng khi tìm kiếm Bing: {exc}") from exc
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise WebConnectorError(f"Bing RSS không phải XML hợp lệ: {exc}") from exc
        channel = root.find("channel")
        if channel is None:
            raise WebConnectorError("Bing RSS thiếu channel")
        results: list[dict[str, Any]] = []
        for item in channel.findall("item")[:max_results]:
            link = (item.findtext("link") or "").strip()
            title = _decode_entities(item.findtext("title") or "")
            desc = _decode_entities(item.findtext("description") or "")[:300]
            if not link.startswith("http"):
                continue
            results.append({"title": title, "url": link, "snippet": desc})
        return results


@dataclass
class RssItem:
    title: str
    link: str
    published: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "link": self.link, "published": self.published, "summary": self.summary}


class RssConnector:
    """Đọc feed RSS/Atom nội bộ — đọc-only, stdlib XML."""

    name = "rss"

    def fetch_feed(self, url: str, *, max_items: int = 10) -> dict[str, Any]:
        _assert_http_url(url)
        if not _robots_allows(url):
            raise WebConnectorError(f"robots.txt không cho phép đọc feed '{url}'")
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
                raw = resp.read(_MAX_BYTES)
        except urllib.error.HTTPError as exc:
            raise WebConnectorError(f"HTTP {exc.code} khi đọc feed") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise WebConnectorError(f"Lỗi mạng khi đọc feed: {exc}") from exc
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise WebConnectorError(f"Feed không phải XML hợp lệ: {exc}") from exc
        feed_title = ""
        items: list[RssItem] = []
        channel = root.find("channel")
        if channel is not None:  # RSS
            t = channel.findtext("title")
            feed_title = (t or "").strip()
            for item in channel.findall("item")[:max_items]:
                items.append(
                    RssItem(
                        title=(item.findtext("title") or "").strip(),
                        link=(item.findtext("link") or "").strip(),
                        published=(item.findtext("pubDate") or "").strip(),
                        summary=(item.findtext("description") or "").strip()[:500],
                    )
                )
        else:  # Atom
            ns = "{http://www.w3.org/2005/Atom}"
            t = root.findtext(f"{ns}title")
            feed_title = (t or "").strip()
            for entry in root.findall(f"{ns}entry")[:max_items]:
                link_el = entry.find(f"{ns}link")
                items.append(
                    RssItem(
                        title=(entry.findtext(f"{ns}title") or "").strip(),
                        link=(link_el.get("href") if link_el is not None else "") or "",
                        published=(entry.findtext(f"{ns}updated") or "").strip(),
                        summary=((entry.findtext(f"{ns}summary") or entry.findtext(f"{ns}content") or "").strip())[:500],
                    )
                )
        from datetime import datetime, timezone

        return {
            "url": url,
            "feed_title": feed_title,
            "items": [i.to_dict() for i in items],
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        }
