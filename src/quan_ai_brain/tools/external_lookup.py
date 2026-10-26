"""External lookup evidence — tra cứu thông tin ngoài hệ thống (tin tức, giá, tỷ giá...).

Owner requirement (27/10/2026): "Hãy nạp thông tin này vào cho hệ thống để sau anh
hỏi các thông tin liên quan tra cứu ngoài hệ thống, tin tức thì tự truy xuất,
tìm kiếm và phản hồi." — với Gemini API key được cung cấp.

Thiết kế 2 tầng:
  Tầng 1 — Gemini + Google Search grounding (tự quyết định cần search, có nguồn).
           CHẤP NHẬN CHỈ KHI response có groundingMetadata (bằng chứng thật);
           429/quota → im lặng chuyển tầng 2, không báo lỗi cho owner.
  Tầng 2 — Google News RSS (không cần key) + Gemini tổng hợp không-search.

An toàn (khớp AGENTS.md):
  - Key chỉ đọc từ env (GEMINI_API_KEY, user-level registry qua persist_gemini_env.ps1);
    KHÔNG hard-code, KHÔNG log, KHÔNG ghi vào DB/prompt.
  - Query được redact_text() trước khi rời máy — không gửi secret ra ngoài.
  - Fail-closed: mọi lỗi → trả None; chat pipeline vẫn chạy bình thường không evidence.
  - BLOCKER khớp code hiện có: search-grounding free tier hiện KHÔNG khả dụng
    cho project mới (429 triền miên trên mọi model; gemini-2.5-flash bị retire →
    404). Do đó tầng 1 thường không chạy; tầng 2 (RSS + tổng hợp) là đường chính.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from quan_ai_brain.core.redaction import redact_text

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
# Model mặc định cho search + tổng hợp. gemini-flash-latest hay 503 high-demand;
# gemini-3-flash-preview free tier (20 RPD) ổn định hơn. Env ghi đè được;
# model 2.5 bị retire (404) tự đổi sang mặc định trong _gemini_synth_evidence.
_DEFAULT_SEARCH_MODEL = "gemini-3-flash-preview"
_DEFAULT_SYNTH_MODEL = "gemini-3-flash-preview"

# Chỉ những câu HỎI THÔNG TIN BÊN NGOÀI mới tốn thời gian tra cứu (an toàn chi phí:
# Gemini free chat ~RPM thấp; câu nội bộ/điều khiển không bao giờ gọi ra ngoài).
_EXTERNAL_PATTERNS = [
    r"\btin\s+(tức|moi|mới)\b",
    r"\bhôm\s*nay\b",
    r"\bhien\s*tai\b",
    r"\bhiện\s*tại\b",
    r"\bgiá\b.*\b(hôm nay|hiện tại|bao nhiêu)\b",
    r"\b(tỷ|ty)\s*giá\b",
    r"\bthời\s*tiết\b",
    r"\bket\s*qua\b",
    r"\bkết\s*quả\b",
    r"\bxổ\s*số\b",
    r"\blich\b.*\b(bong|bóng)\b",
    r"\blịch\b.*\b(bóng|bong)\b",
    r"\btìm\s*(kiếm|kiem)\b",
    r"\btra\s*cứu\b",
    r"\btra\s*cuu\b",
    r"\bgoogle\s*(search|kiếm)\b",
    r"\bnews\b",
    r"\bgiá\s*vàng\b",
    r"\bcó\s*(gì|tin)\s*(mới|nào)\b",
]

_RSS_TTL_SECONDS = 300  # cache RSS 5 phút — tránh bị Google chặn vì poll dồn
_rss_cache: dict[str, tuple[float, list[dict[str, str]]]] = {}

# Cooldown tầng 1 (search grounding): khi quota search bị chặn (429 triền miên),
# ngừng thử trong 6 tiếng — đừng đốt quota chat (20 RPD/model) vào request chết.
_SEARCH_COOLDOWN_SECONDS = 6 * 3600
_search_cooldown_until = 0.0

# Test kiểm soát việc đọc registry (giữ deterministic — test không đọc máy thật).
_ALLOW_REGISTRY_FALLBACK = True


@dataclass
class ExternalEvidence:
    """Bằng chứng tra cứu ngoài — đưa vào prompt, KHÔNG bao giờ gọi là 'kiến thức'."""

    query: str
    source_layer: str  # "gemini_search" | "news_rss" | "none"
    summary: str = ""
    sources: list[dict[str, str]] = field(default_factory=list)
    note: str = ""

    def is_empty(self) -> bool:
        return self.source_layer == "none" or not (self.summary or self.sources)

    def render_block(self) -> str:
        if self.is_empty():
            return ""
        lines = ["", "=== BẰNG CHỨNG TRA CỨU NGOÀI (lấy THỜI ĐIỂM HỎI, không phải trí nhớ) ==="]
        if self.summary:
            lines.append(f"Kết quả: {self.summary}")
        if self.sources:
            lines.append("Nguồn:")
            for s in self.sources[:5]:
                lines.append(f"  - {s.get('title', '')[:90]} — {s.get('url', '')}")
        lines.append(
            "Quy tắc: DÙNG bằng chứng trên để trả lời câu hỏi thời sự; "
            "KHÔNG bịa số liệu; nếu bằng chứng không đủ, nói rõ 'em chưa tra được tin cậy'."
        )
        return "\n".join(lines)


def should_lookup_external(query: str) -> bool:
    """True nếu câu hỏi khả năng cao cần thông tin ngoài (tin tức, giá, tỷ giá...)."""
    q = (query or "").lower()
    if not q:
        return False
    return any(re.search(p, q) for p in _EXTERNAL_PATTERNS)


def _gemini_api_key() -> str | None:
    """Đọc key từ env; nếu thiếu → đọc user-level registry (HKCU\\Environment).

    Reboot-proof: server con có thể được khởi động bởi watchdog/launcher chưa nạp
    env — registry là nguồn tồn tại vĩnh viễn trên máy. KHÔNG in/log giá trị.
    Cờ _ALLOW_REGISTRY_FALLBACK=False trong test để giữ deterministic.
    """
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    if not _ALLOW_REGISTRY_FALLBACK:
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            val, _ = winreg.QueryValueEx(k, "GEMINI_API_KEY")
            key = str(val).strip()
            if key:
                os.environ["GEMINI_API_KEY"] = key  # cache cho các lần sau
                return key
    except Exception:
        pass
    return None


def _gemini_generate(model: str, payload: dict[str, Any], timeout: float) -> dict[str, Any] | None:
    """POST generateContent. Trả dict JSON hoặc None (mọi lỗi fail-closed)."""
    key = _gemini_api_key()
    if not key:
        return None
    url = f"{_GEMINI_BASE}/models/{model}:generateContent"
    req = urllib.request.Request(
        f"{url}?key={key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        # 429/403/timeout/JSON — all fail-closed. KHÔNG log body (có thể chứa echo key?).
        return None
    finally:
        # Không giữ tham chiếu key trong exception traceback đáng kể, nhưng xoá biến
        # req/data để GC sớm; key nằm trong closure — không log ở bất kỳ đâu.
        pass


def _extract_text_and_sources(data: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    text = ""
    sources: list[dict[str, str]] = []
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        gm = data["candidates"][0].get("groundingMetadata", {})
        for chunk in gm.get("groundingChunks", [])[:8]:
            web = chunk.get("web", {})
            if web.get("uri"):
                sources.append({
                    "title": (web.get("title") or web.get("uri"))[:120],
                    "url": web.get("uri", ""),
                })
    except Exception:
        return "", []
    return text, sources


def gemini_search_evidence(query: str, timeout: float = 45.0) -> ExternalEvidence:
    """Tầng 1: Gemini + Google Search grounding.

    CHẤP NHẬN chỉ khi có groundingMetadata (bằng chứng search thật).
    429 RESOURCE_EXHAUSTED (free tier hiện không có search grounding cho project
    mới) → trả ExternalEvidence(layer="none") — tầng 2 sẽ接管.
    """
    redacted = redact_text(query)
    payload = {
        "contents": [{"parts": [{"text": (
            f"Tra cứu thông tin mới nhất về: {redacted}. "
            "Trả lời ngắn gọn (tối đa 4 câu) kèm nguồn."
        )}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"maxOutputTokens": 700},
    }
    model = os.environ.get("GEMINI_SEARCH_MODEL", _DEFAULT_SEARCH_MODEL)
    global _search_cooldown_until
    if time.time() < _search_cooldown_until:
        return ExternalEvidence(query=redacted, source_layer="none",
                                note="gemini_search cooldown (quota search đang bị chặn)")
    data = _gemini_generate(model, payload, timeout=timeout)
    if data is None:
        # Đánh dấu cooldown: request search vừa rồi đã thất bại (không phân biệt
        # nguyên nhân — an toàn quota là ưu tiên). Tầng 2 RSS không bị ảnh hưởng.
        _search_cooldown_until = time.time() + _SEARCH_COOLDOWN_SECONDS
        return ExternalEvidence(query=redacted, source_layer="none",
                                note="gemini_search unavailable (quota/network)")
    text, sources = _extract_text_and_sources(data)
    if not sources:
        # Không có grounding metadata → không phải bằng chứng search thật → không nhận.
        return ExternalEvidence(query=redacted, source_layer="none",
                                note="gemini_search không trả nguồn (có thể do quota)")
    return ExternalEvidence(query=redacted, source_layer="gemini_search",
                            summary=text, sources=sources)


_RSS_STOPWORDS = re.compile(
    r"\b(hôm nay|hom nay|hiện tại|hien tai|hiện nay|bao nhiêu|bao nhieu|mới nhất|"
    r"moi nhat|mới nh?t|xin|vui lòng|giúp|giup|ạ|à|nhé|nhe|được không|tôi|anh|em)\b",
    re.IGNORECASE,
)


def _clean_rss_query(query: str) -> str:
    """Rút gọn câu hỏi thành cụm tìm kiếm tin (Google News ranking tệ với câu dài).

    'giá vàng SJC hôm nay bao nhiêu ạ?' → 'giá vàng SJC'
    """
    q = redact_text(query).strip()
    q = re.sub(r"[?!.]+$", "", q).strip()
    q = _RSS_STOPWORDS.sub(" ", q)
    q = re.sub(r"\s{2,}", " ", q).strip()
    # Giữ tối đa ~5 từ — Google News search hoạt động tốt với cụm ngắn
    words = q.split()
    return " ".join(words[:5]) if len(words) > 5 else q


def fetch_news_rss(query: str, max_items: int = 5) -> list[dict[str, str]]:
    """Tầng 2a: Google News RSS (không cần key) — luôn khả dụng, không quota API."""
    q = _clean_rss_query(query)
    cache_key = q[:80]
    now = time.time()
    cached = _rss_cache.get(cache_key)
    if cached and now - cached[0] < _RSS_TTL_SECONDS:
        return cached[1]

    rss_url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(q)
        + "&hl=vi&gl=VN&ceid=VN:vi"
    )
    items: list[dict[str, str]] = []
    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        for it in re.findall(r"<item>(.*?)</item>", data, re.S)[:max_items]:
            title_m = re.search(r"<title>(.*?)</title>", it, re.S)
            link_m = re.search(r"<link>(.*?)</link>", it, re.S)
            date_m = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
            if title_m:
                items.append({
                    "title": title_m.group(1).strip()[:150],
                    "url": (link_m.group(1).strip() if link_m else ""),
                    "date": (date_m.group(1).strip() if date_m else ""),
                })
        _rss_cache[cache_key] = (now, items)
    except Exception:
        return []
    return items


def _gemini_synth_evidence(query: str, timeout: float = 45.0) -> ExternalEvidence:
    """Tầng 2b: Gemini tổng hợp KHÔNG search (không tốn search quota) trên tin RSS.

    Dùng model free-chat còn quota. Fail-closed: lỗi → trả Evidence rỗng với
    nguồn RSS thô (bot vẫn có nguồn thật để dẫn).
    """
    items = fetch_news_rss(query, max_items=6)
    if not items:
        return ExternalEvidence(query=redact_text(query), source_layer="none",
                                note="RSS không trả kết quả")
    model = os.environ.get("GEMINI_MODEL", _DEFAULT_SYNTH_MODEL) or _DEFAULT_SYNTH_MODEL
    if model in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
        model = _DEFAULT_SYNTH_MODEL  # 2.5-flash đã bị retire với project mới (404)
    redacted = redact_text(query)
    feed_text = "\n".join(
        f"- {it['title']} ({it.get('date', '')[:16]})" for it in items
    )
    payload = {
        "contents": [{"parts": [{"text": (
            f"Câu hỏi: {redacted}\n\n"
            f"Danh sách tin mới nhất từ Google News:\n{feed_text}\n\n"
            "Chọn các tin LIÊN QUAN trực tiếp đến câu hỏi (nếu không tin nào liên "
            "quan, nói rõ). Trả lời ngắn gọn tối đa 4 câu, nhắc tên báo trong ngoặc."
        )}]}],
        "generationConfig": {"maxOutputTokens": 500},
    }
    # Chuỗi fallback model: primary → default → alias (mỗi model free quota riêng).
    tried: list[str] = []
    for m in dict.fromkeys([model, _DEFAULT_SYNTH_MODEL, "gemini-flash-latest"]):
        data = _gemini_generate(m, payload, timeout=timeout)
        if data is not None:
            text, _ = _extract_text_and_sources(data)
            if text:
                return ExternalEvidence(query=redacted, source_layer="news_rss",
                                        summary=text,
                                        sources=[{"title": it["title"], "url": it["url"]}
                                                 for it in items[:5]])
        tried.append(m)
    # Mọi model đều fail (quota/503) → vẫn trả nguồn RSS thô: bằng chứng thật.
    return ExternalEvidence(
        query=redacted, source_layer="news_rss", summary="",
        sources=[{"title": it["title"], "url": it["url"]} for it in items[:5]],
        note=f"Gemini tổng hợp không khả dụng ({', '.join(tried)}) — nguồn thô Google News RSS",
    )


def collect_external_evidence(query: str, timeout: float = 45.0) -> ExternalEvidence:
    """Điều phối: tầng 1 (Gemini search grounding) → tầng 2 (RSS + tổng hợp).

    Hàm duy nhất chat pipeline gọi. Mọi lỗi fail-closed → Evidence rỗng.
    """
    if not should_lookup_external(query):
        return ExternalEvidence(query=query, source_layer="none",
                                note="not an external-lookup question")
    try:
        ev = gemini_search_evidence(query, timeout=timeout)
        if not ev.is_empty():
            return ev
        return _gemini_synth_evidence(query, timeout=timeout)
    except Exception as exc:  # phòng hờ — không bao giờ làm chết chat
        return ExternalEvidence(query=query, source_layer="none",
                                note=f"external_lookup error: {type(exc).__name__}")
