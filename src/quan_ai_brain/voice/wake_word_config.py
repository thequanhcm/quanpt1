"""Unified Wake Word Configuration and Pattern Matcher for QUAN AI BRAIN."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any
import unicodedata


@dataclass(frozen=True)
class WakeWordItem:
    keyword_id: str
    phrase: str
    language: str  # "vi", "en", "any"
    enabled: bool = True
    risk_level: str = "LOW"  # LOW, MEDIUM


@dataclass
class WakeWordMatchResult:
    matched: bool
    keyword: str = ""
    extracted_payload: str = ""
    confidence: float = 0.0
    is_control_command: bool = False
    control_action: str = ""  # "SLEEP", "STOP_LISTENING", "STOP_SPEAKING", "DISABLE"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_WAKE_WORDS: list[WakeWordItem] = [
    WakeWordItem("ww_hi_tony", "Hi TONY", "en", True, "LOW"),
    WakeWordItem("ww_hey_tony", "Hey Tony", "en", True, "LOW"),
    WakeWordItem("ww_tony_oi", "Tony ơi", "vi", True, "LOW"),
    WakeWordItem("ww_chao_tro_ly", "Chào trợ lý", "vi", True, "LOW"),
    WakeWordItem("ww_hi_tro_ly", "Hi trợ lý", "vi", True, "LOW"),
    WakeWordItem("ww_xin_chao_tro_ly", "Xin chào trợ lý", "vi", True, "LOW"),
    WakeWordItem("ww_hello_assistant", "Hello assistant", "en", True, "LOW"),
    WakeWordItem("ww_hi_assistant", "Hi assistant", "en", True, "LOW"),
    WakeWordItem("ww_quan_ai", "QUAN AI", "any", True, "MEDIUM"),
    WakeWordItem("ww_quan_ai_brain", "Quan AI Brain", "any", True, "LOW"),
]


def normalize_text(text: str) -> str:
    """Normalize text by trimming, lowering, collapsing spaces, and stripping punctuation."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFC", text).strip().lower()
    norm = re.sub(r"[,\.!\?;\:\-\(\)\[\]\"']", " ", norm)
    return re.sub(r"\s+", " ", norm).strip()


class WakeWordConfig:
    """Centralized wake word configuration manager and matching engine."""

    def __init__(
        self,
        items: list[WakeWordItem] | None = None,
        enabled: bool = False,
        silence_timeout_seconds: float = 20.0,
        chime_enabled: bool = True,
        language_mode: str = "vi-VN",
    ) -> None:
        self.items: dict[str, WakeWordItem] = {
            w.keyword_id: w for w in (items or DEFAULT_WAKE_WORDS)
        }
        self.enabled = enabled
        self.silence_timeout_seconds = silence_timeout_seconds
        self.chime_enabled = chime_enabled
        self.language_mode = language_mode

    def to_dict(self) -> dict[str, Any]:
        kw_list = [asdict(w) for w in self.items.values()]
        return {
            "enabled": self.enabled,
            "assistant_name": "TONY — QUAN AI BRAIN Voice Assistant",
            "silence_timeout_seconds": self.silence_timeout_seconds,
            "silence_timeout_sec": self.silence_timeout_seconds,
            "chime_enabled": self.chime_enabled,
            "language_mode": self.language_mode,
            "keywords": kw_list,
            "wake_words": kw_list,
        }

    def update_item(self, keyword_id: str, enabled: bool) -> bool:
        if keyword_id not in self.items:
            return False
        old = self.items[keyword_id]
        self.items[keyword_id] = WakeWordItem(
            keyword_id=old.keyword_id,
            phrase=old.phrase,
            language=old.language,
            enabled=enabled,
            risk_level=old.risk_level,
        )
        return True

    def match(self, spoken_text: str) -> WakeWordMatchResult:
        """Check if spoken text contains a wake word or special control command."""
        clean = normalize_text(spoken_text)
        if not clean:
            return WakeWordMatchResult(matched=False)

        # 1. Check control commands first
        control_map: list[tuple[tuple[str, ...], str]] = [
            (("dừng đọc", "dừng nói", "stop speaking", "shut up"), "STOP_SPEAKING"),
            (("ngủ đi", "tạm ngủ", "go to sleep", "sleep"), "SLEEP"),
            (("dừng nghe", "stop listening"), "STOP_LISTENING"),
            (("tắt trợ lý", "tắt đánh thức", "disable wake word"), "DISABLE"),
        ]
        for phrases, action in control_map:
            for phrase in phrases:
                if clean == phrase or clean.startswith(phrase + " "):
                    return WakeWordMatchResult(
                        matched=True,
                        keyword=phrase,
                        confidence=1.0,
                        is_control_command=True,
                        control_action=action,
                    )

        # 2. Check enabled wake words (sort by length descending to match longest phrase first)
        sorted_items = sorted(
            [it for it in self.items.values() if it.enabled],
            key=lambda x: len(normalize_text(x.phrase)),
            reverse=True,
        )

        for item in sorted_items:
            norm_phrase = normalize_text(item.phrase)

            # Case A: Exact match
            if clean == norm_phrase:
                return WakeWordMatchResult(
                    matched=True,
                    keyword=item.phrase,
                    extracted_payload="",
                    confidence=0.98,
                )

            # Case B: Utterance starts with wake word ("Hi Tony thời tiết hôm nay thế nào")
            if clean.startswith(norm_phrase + " "):
                payload = clean[len(norm_phrase) :].strip()
                return WakeWordMatchResult(
                    matched=True,
                    keyword=item.phrase,
                    extracted_payload=payload,
                    confidence=0.95,
                )

        return WakeWordMatchResult(matched=False)
