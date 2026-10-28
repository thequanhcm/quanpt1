"""QUAN AI BRAIN — Media & YouTube Music Engine.

Provides zero-dependency YouTube music search and streaming coordination
for Central Brain Core and Raspberry Pi 5 edge embodiment.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger("quan_ai_brain.media.youtube")

# Intent patterns for Vietnamese & English music requests
_MUSIC_PATTERNS = [
    # Bật/phát/mở bài hát X
    r"(?:bật|phát|mở|nghe|chơi)\s+(?:bài\s+hát|bài|nhạc|ca\s+khúc|mv|video|track)\s+[\"']?([^\"'\n\.,;]+)[\"']?",
    # Bật/phát/mở X cho anh/em
    r"(?:bật|phát|mở|nghe)\s+[\"']?([^\"'\n\.,;]+)[\"']?\s+(?:cho\s+(?:anh|chị|em|tôi)|trên\s+(?:pi\s*5|pi|loa)|qua\s+loa)",
    # Tìm nhạc X / Search nhạc X
    r"(?:tìm|search|kiếm|tra)\s+(?:bài\s+hát|nhạc|ca\s+khúc|youtube)\s+[\"']?([^\"'\n\.,;]+)[\"']?",
    # Muốn nghe bài X
    r"(?:muốn\s+nghe|thích\s+nghe)\s+(?:bài\s+hát|bài|nhạc|ca\s+khúc)?\s*[\"']?([^\"'\n\.,;]+)[\"']?",
]

_STOP_PATTERNS = [
    r"(?:dừng|tắt|ngừng|stop|pause)\s+(?:nhạc|bài\s+hát|phát\s+nhạc|loa|audio|youtube)",
    r"^(?:dừng\s+lại|tắt\s+đi|stop\s+music)$",
]


def looks_like_music_request(text: str) -> tuple[bool, str]:
    """Detect if user query is a request to play or stop music.

    Returns:
        (is_music_request: bool, song_title_or_action: str)
        If stop request, song_title_or_action is "STOP".
        If play request, song_title_or_action is the extracted search term.
    """
    if not text or not text.strip():
        return False, ""

    clean = text.strip().lower()

    # 1. Check stop patterns
    for pat in _STOP_PATTERNS:
        if re.search(pat, clean, re.IGNORECASE):
            return True, "STOP"

    # 2. Check play patterns
    for pat in _MUSIC_PATTERNS:
        m = re.search(pat, clean, re.IGNORECASE)
        if m:
            query = m.group(1).strip()
            # Remove trailing filler words
            query = re.sub(
                r"\s+(?:cho\s+anh|cho\s+chị|cho\s+em|ngay|luôn|nhé|nha|đi|với|trên\s+pi|qua\s+loa)$",
                "",
                query,
                flags=re.IGNORECASE,
            ).strip()
            if len(query) >= 2:
                return True, query

    return False, ""


def search_youtube_music(query: str, max_results: int = 5, timeout: float = 8.0) -> list[dict[str, Any]]:
    """Search YouTube for music videos and return structured results.

    Zero external dependencies: uses standard urllib and robust regex parsing.
    Extracts videoId, title, duration, channel name, and watch URL.
    """
    if not query or not query.strip():
        return []

    encoded = urllib.parse.quote(query.strip())
    url = f"https://www.youtube.com/results?search_query={encoded}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        logger.warning("YouTube search network error for '%s': %s", query, exc)
        return []

    results: list[dict[str, Any]] = []

    # Pattern 1: Parse embedded ytInitialData JSON
    match = re.search(r"var ytInitialData\s*=\s*({.+?});</script>", html)
    if match:
        try:
            data = json.loads(match.group(1))
            contents = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )
            for section in contents:
                item_section = section.get("itemSectionRenderer", {}).get("contents", [])
                for item in item_section:
                    vr = item.get("videoRenderer")
                    if not vr:
                        continue
                    vid = vr.get("videoId")
                    title_runs = vr.get("title", {}).get("runs", [])
                    title = "".join(r.get("text", "") for r in title_runs)
                    duration = vr.get("lengthText", {}).get("simpleText", "")
                    owner_runs = vr.get("ownerText", {}).get("runs", [])
                    channel = "".join(r.get("text", "") for r in owner_runs)
                    if vid and title:
                        results.append({
                            "video_id": vid,
                            "title": title,
                            "duration": duration,
                            "channel": channel,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "thumbnail_url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                        })
                        if len(results) >= max_results:
                            return results
        except Exception as parse_err:
            logger.debug("ytInitialData parse failed: %s", parse_err)

    # Pattern 2: Regex fallback if JSON parsing structure changed
    if not results:
        vids = list(dict.fromkeys(re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", html)))
        for vid in vids[:max_results]:
            results.append({
                "video_id": vid,
                "title": f"Video YouTube ({vid})",
                "duration": "",
                "channel": "",
                "url": f"https://www.youtube.com/watch?v={vid}",
                "thumbnail_url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            })

    return results


def dispatch_play_music_to_pi5(
    video_id: str,
    title: str,
    url: str,
    edge_ip: str = "192.168.1.21",
    edge_port: int = 8768,
    timeout: float = 4.0,
) -> dict[str, Any]:
    """Send playback command to Raspberry Pi 5 Edge Kiosk Daemon."""
    endpoint = f"http://{edge_ip}:{edge_port}/api/kiosk/music/play"
    payload = {
        "video_id": video_id,
        "title": title,
        "url": url,
    }
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "data": res_data, "title": title, "url": url}
    except Exception as exc:
        logger.warning("Failed to dispatch music play to Pi 5 (%s): %s", endpoint, exc)
        return {"success": False, "error": str(exc), "title": title, "url": url}


def dispatch_stop_music_to_pi5(
    edge_ip: str = "192.168.1.21",
    edge_port: int = 8768,
    timeout: float = 3.0,
) -> dict[str, Any]:
    """Send stop music command to Raspberry Pi 5 Edge Kiosk Daemon."""
    endpoint = f"http://{edge_ip}:{edge_port}/api/kiosk/music/stop"
    try:
        body = json.dumps({}).encode("utf-8")
        req = urllib.request.Request(endpoint, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "data": res_data}
    except Exception as exc:
        logger.warning("Failed to dispatch music stop to Pi 5 (%s): %s", endpoint, exc)
        return {"success": False, "error": str(exc)}
