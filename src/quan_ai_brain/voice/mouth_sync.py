"""Mouth Synchronization & Real-Time Lip-Sync Engine for QUAN AI BRAIN.

Generates precise mouth shape and opening timelines aligned with spoken utterances,
syllable durations, natural punctuation pauses, and audio energy.
Supports real-time frame lookup, timeline streaming to Raspberry Pi 5,
and instant cancellation on owner interruption.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
import time
from typing import Any


@dataclass
class MouthFrame:
    """Single discrete mouth animation state at an offset in time."""

    offset_ms: int
    open_ratio: float  # 0.0 (closed/rest) to 1.0 (wide open)
    viseme: str        # "REST", "A", "O", "E", "I", "U"
    audio_energy: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset_ms": self.offset_ms,
            "open_ratio": round(self.open_ratio, 3),
            "viseme": self.viseme,
            "audio_energy": round(self.audio_energy, 3),
        }


@dataclass
class UtteranceTimeline:
    """Complete synchronized lip-sync timeline for an AI spoken response."""

    utterance_id: str
    text: str
    total_duration_ms: int
    frame_interval_ms: int = 50
    frames: list[MouthFrame] = field(default_factory=list)
    is_cancelled: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "utterance_id": self.utterance_id,
            "text": self.text,
            "total_duration_ms": self.total_duration_ms,
            "frame_interval_ms": self.frame_interval_ms,
            "frame_count": len(self.frames),
            "is_cancelled": self.is_cancelled,
            "frames": [f.to_dict() for f in self.frames],
        }


class MouthSyncEngine:
    """Synthesizes, caches, and samples real-time lip-sync timelines."""

    def __init__(self, frame_interval_ms: int = 50) -> None:
        self.frame_interval_ms = max(20, min(100, int(frame_interval_ms)))
        self.active_timelines: dict[str, UtteranceTimeline] = {}

    def synthesize_timeline(self, text: str, utterance_id: str | None = None) -> UtteranceTimeline:
        """Synthesize a timeline with an auto-generated utterance ID."""
        u_id = utterance_id or f"utt_{int(time.time() * 1000)}"
        return self.generate_timeline(u_id, text)

    def generate_timeline(
        self,
        utterance_id: str,
        text: str,
        target_duration_ms: int | None = None,
    ) -> UtteranceTimeline:
        """Construct deterministic mouth movement frames based on Vietnamese text syllables and pauses."""
        clean_text = text.strip()
        if not clean_text:
            empty = UtteranceTimeline(
                utterance_id=utterance_id,
                text="",
                total_duration_ms=0,
                frame_interval_ms=self.frame_interval_ms,
                frames=[MouthFrame(offset_ms=0, open_ratio=0.0, viseme="REST")],
            )
            self.active_timelines[utterance_id] = empty
            return empty

        # Tokenize by words and punctuation pauses
        tokens = re.findall(r"[\wÀ-ỹ]+|[.,!?;:]", clean_text, flags=re.UNICODE)
        segments: list[tuple[str, int]] = []  # (token, duration_ms)

        for tok in tokens:
            if tok in (",", ";", ":"):
                segments.append((tok, 250))  # Short breathing pause
            elif tok in (".", "!", "?"):
                segments.append((tok, 450))  # Full sentence pause
            else:
                # Word syllable duration estimate (~160ms - 240ms per Vietnamese word)
                length = len(tok)
                syllable_ms = max(140, min(300, 150 + length * 15))
                segments.append((tok, syllable_ms))

        calculated_duration = sum(d for _, d in segments)
        scale_factor = 1.0
        if target_duration_ms and target_duration_ms > 0 and calculated_duration > 0:
            scale_factor = target_duration_ms / calculated_duration
            total_duration = target_duration_ms
        else:
            total_duration = calculated_duration

        frames: list[MouthFrame] = []
        current_time_ms = 0

        for tok, raw_dur in segments:
            seg_duration = int(raw_dur * scale_factor)
            seg_end = current_time_ms + seg_duration

            if tok in (",", ";", ":", ".", "!", "?"):
                # Natural resting pause -> mouth closed
                t = current_time_ms
                while t < seg_end:
                    frames.append(MouthFrame(offset_ms=t, open_ratio=0.0, viseme="REST"))
                    t += self.frame_interval_ms
            else:
                # Syllable pronunciation -> determine dominant vowel viseme
                lower = tok.lower()
                viseme = "A"
                peak_open = 0.75
                if re.search(r"[oôơòóỏõọồốổỗộờớởỡợ]", lower):
                    viseme = "O"
                    peak_open = 0.85
                elif re.search(r"[uưùúủũụừứửữự]", lower):
                    viseme = "U"
                    peak_open = 0.60
                elif re.search(r"[eêèéẻẽẹềếểễệ]", lower):
                    viseme = "E"
                    peak_open = 0.65
                elif re.search(r"[iìíỉĩịyỳýỷỹỵ]", lower):
                    viseme = "I"
                    peak_open = 0.45

                # Parabolic or sine bell curve for smooth mouth opening and closing
                t = current_time_ms
                while t < seg_end:
                    norm = (t - current_time_ms) / max(1, seg_duration)
                    # Bell shape: sin(pi * norm)
                    envelope = math.sin(math.pi * min(1.0, max(0.0, norm)))
                    ratio = max(0.0, min(1.0, peak_open * envelope))
                    frames.append(MouthFrame(
                        offset_ms=t,
                        open_ratio=ratio,
                        viseme=viseme if ratio > 0.15 else "REST",
                        audio_energy=ratio,
                    ))
                    t += self.frame_interval_ms

            current_time_ms = seg_end

        final_duration_ms = target_duration_ms if (target_duration_ms and target_duration_ms > 0) else current_time_ms
        frames.append(MouthFrame(offset_ms=final_duration_ms, open_ratio=0.0, viseme="REST"))

        timeline = UtteranceTimeline(
            utterance_id=utterance_id,
            text=clean_text,
            total_duration_ms=final_duration_ms,
            frame_interval_ms=self.frame_interval_ms,
            frames=frames,
        )
        self.active_timelines[utterance_id] = timeline

        # Prune old timelines (keep last 50)
        if len(self.active_timelines) > 50:
            oldest_key = min(self.active_timelines, key=lambda k: self.active_timelines[k].created_at)
            self.active_timelines.pop(oldest_key, None)

        return timeline

    def get_mouth_frame_at(self, utterance_id: str, offset_ms: int) -> MouthFrame:
        """Sample mouth frame at exact millisecond offset. Shuts immediately if cancelled."""
        timeline = self.active_timelines.get(utterance_id)
        if not timeline or timeline.is_cancelled:
            return MouthFrame(offset_ms=offset_ms, open_ratio=0.0, viseme="REST")

        if offset_ms >= timeline.total_duration_ms or not timeline.frames:
            return MouthFrame(offset_ms=offset_ms, open_ratio=0.0, viseme="REST")

        # Find closest frame by offset
        idx = max(0, min(len(timeline.frames) - 1, offset_ms // timeline.frame_interval_ms))
        return timeline.frames[idx]

    def cancel_utterance(self, utterance_id: str) -> bool:
        """CRITICAL: Immediately stop audio & snap mouth to closed rest position when interrupted."""
        timeline = self.active_timelines.get(utterance_id)
        if timeline:
            timeline.is_cancelled = True
            return True
        return False
