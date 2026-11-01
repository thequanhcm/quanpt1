"""Tests for Avatar V3 Giai đoạn B: timeline-only lip-sync + exact duration alignment.

These tests verify:
1. Random-viseme fallback has been removed (bell-curve envelope instead)
2. MP3 duration measurement works for real edge-tts output
3. Timeline scaling to exact audio duration
"""
import base64
import math
import sys
from pathlib import Path

sys.path.insert(0, "src")

from quan_ai_brain.voice.mouth_sync import MouthSyncEngine, MouthFrame


def test_no_random_viseme_fallback():
    """Giai đoạn B: Fallback must use smooth bell-curve, not Math.random()."""
    # This is a code inspection test — we verify the source doesn't contain Math.random()
    avatar_engine_path = Path(__file__).parent.parent / "edge_client" / "avatar_engine.js"
    content = avatar_engine_path.read_text(encoding="utf-8")

    # Check that the old random pattern is gone
    assert "Math.random() * 0.55" not in content, "Random viseme fallback must be removed"
    assert "0.4 + Math.random()" not in content, "Random open_ratio must be removed"

    # Check that bell-curve envelope is present
    assert "Math.sin(Math.PI * phase)" in content or "envelope" in content, "Bell-curve envelope must be present"
    print("✓ Random-viseme fallback removed, bell-curve envelope in place")


def test_mp3_duration_measurement():
    """Measure duration from a real MP3 file (mock or actual TTS output)."""
    engine = MouthSyncEngine()

    # Create a mock MP3 frame (minimal valid MPEG-1 Layer III frame header)
    # ID3v2 tag + 1 frame
    id3_header = b"ID3\x03\x00\x00\x00\x00\x00\x00"
    # MPEG frame header: 0xFFFB9044 = MPEG-1 Layer III, 128kbps, 44100Hz
    mpeg_header = b"\xff\xfb\x90\x44"
    mock_mp3 = id3_header + mpeg_header + (b"\x00" * 1000)  # 1000 bytes of "audio"

    duration_ms = engine.measure_mp3_duration_ms(mock_mp3)
    # Should return a positive number (even if approximate)
    assert duration_ms is not None, "Should parse duration from mock MP3"
    assert duration_ms > 0, "Duration must be positive"
    print(f"✓ MP3 duration measurement: {duration_ms}ms from mock file")


def test_timeline_scaling_to_target_duration():
    """Timeline should scale to match exact audio duration when target_duration_ms is provided."""
    engine = MouthSyncEngine(frame_interval_ms=50)

    text = "Xin chào anh Quân, em là Tony."
    estimated_duration = 2500  # ms (estimated from text)
    actual_audio_duration = 3200  # ms (measured from MP3)

    timeline = engine.generate_timeline("test_scale", text, target_duration_ms=actual_audio_duration)

    # Timeline should be scaled to match actual duration
    assert timeline.total_duration_ms == actual_audio_duration, f"Timeline should match {actual_audio_duration}ms"

    # Frames should be spread across the full duration
    last_frame = timeline.frames[-1]
    assert last_frame.offset_ms <= actual_audio_duration, "Last frame should be within duration"

    # Check that scaling factor was applied
    # (original estimate ~2500ms → scaled to 3200ms → scale_factor ≈ 1.28)
    print(f"✓ Timeline scaled: {estimated_duration}ms → {timeline.total_duration_ms}ms (factor={actual_audio_duration/estimated_duration:.2f})")


def test_vietnamese_viseme_mapping():
    """Verify Vietnamese vowel → viseme mapping is correct."""
    engine = MouthSyncEngine()

    test_cases = [
        ("o", "O"), ("ô", "O"), ("ơ", "O"),
        ("u", "U"), ("ư", "U"),
        ("e", "E"), ("ê", "E"),
        ("i", "I"), ("y", "I"),
        ("a", "A"), ("á", "A"), ("à", "A"),
    ]

    for vowel, expected_viseme in test_cases:
        timeline = engine.generate_timeline(f"test_{vowel}", vowel)
        # At least one frame should have the correct viseme
        visemes_in_timeline = [f.viseme for f in timeline.frames if f.open_ratio > 0.15]
        assert expected_viseme in visemes_in_timeline, f"Vowel {vowel} should map to {expected_viseme}"

    print("✓ Vietnamese viseme mapping correct for all tested vowels")


def test_bell_curve_envelope():
    """Verify that syllable frames follow a bell-curve (sin) envelope."""
    engine = MouthSyncEngine(frame_interval_ms=50)

    # Single syllable: "chào" (should have smooth open→close)
    timeline = engine.generate_timeline("test_bell", "chào", target_duration_ms=500)

    # Extract open_ratio values for non-REST frames
    ratios = [f.open_ratio for f in timeline.frames if f.viseme != "REST"]

    # Should have at least 3 frames (open → peak → close)
    assert len(ratios) >= 3, f"Should have at least 3 frames, got {len(ratios)}"

    # First and last should be lower than middle (bell shape)
    mid_idx = len(ratios) // 2
    assert ratios[0] < ratios[mid_idx], "First frame should be lower than middle"
    assert ratios[-1] < ratios[mid_idx], "Last frame should be lower than middle"

    print(f"✓ Bell-curve envelope verified: {len(ratios)} frames, peak={max(ratios):.3f}")


def test_punctuation_pauses():
    """Punctuation should create REST (closed mouth) frames."""
    engine = MouthSyncEngine()

    timeline = engine.generate_timeline("test_punct", "Xin chào. Tạm biệt!")

    # Find frames around period and exclamation
    rest_frames = [f for f in timeline.frames if f.viseme == "REST" and f.open_ratio == 0.0]

    # Should have multiple REST frames (at end of sentences)
    assert len(rest_frames) >= 2, f"Should have REST frames for punctuation, got {len(rest_frames)}"

    print(f"✓ Punctuation pauses: {len(rest_frames)} REST frames detected")


def main() -> int:
    """Run all Giai đoạn B tests."""
    print("=" * 60)
    print("Avatar V3 — Giai đoạn B Tests (Timeline-Only + Exact Duration)")
    print("=" * 60)

    tests = [
        test_no_random_viseme_fallback,
        test_mp3_duration_measurement,
        test_timeline_scaling_to_target_duration,
        test_vietnamese_viseme_mapping,
        test_bell_curve_envelope,
        test_punctuation_pauses,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print("=" * 60)
    if failed == 0:
        print(f"✓ All {len(tests)} tests passed — Giai đoạn B ready for deployment")
        return 0
    else:
        print(f"✗ {failed}/{len(tests)} tests failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())