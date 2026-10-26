"""Self-Contained Verification Suite for Packed Avatar Library (Model A).

Run:
    python test_avatar.py
"""
import sys
from pathlib import Path
from PIL import Image

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_tests():
    current_dir = Path(__file__).resolve().parent
    assets_dir = current_dir / "assets"
    print("==================================================")
    print("QUAN AI BRAIN — AVATAR MODEL A VERIFICATION SUITE")
    print("==================================================")

    # 1. Verify Core Code Files Exist
    core_files = [
        "avatar_engine.js",
        "avatar.css",
        "mouth_sync.py",
        "demo.html",
        "generate_assets.py"
    ]
    for cf in core_files:
        p = current_dir / cf
        assert p.exists(), f"Missing core file: {cf}"
        assert p.stat().st_size > 0, f"Empty core file: {cf}"
    print("[PASS] All core library files exist and non-empty.")

    # 2. Verify Key Asset Files
    required_assets = [
        "avatar_v2_portrait.png",
        "avatar_v2_blink.png",
        "avatar_v2_happy.png",
        "avatar_v2_thinking.png",
        "avatar_v2_speaking.png",
        "avatar_v2_warning.png",
        "avatar_v2_empathic.png",
        "avatar_v2_confused.png",
        "avatar_v2_surprised.png",
        "avatar_v2_error.png",
        "mouth_v2_rest.png",
        "mouth_v2_speaking.png",
        "mouth_v2_open_o.png",
        "mouth_v2_happy.png",
    ]
    for a in required_assets:
        ap = assets_dir / a
        assert ap.exists(), f"Missing asset: {a}"
        assert ap.stat().st_size > 0, f"Empty asset: {a}"
    print(f"[PASS] All {len(required_assets)} required expression and mouth assets verified.")

    # 3. Verify Master Portrait 1024x1024
    with Image.open(assets_dir / "avatar_v2_portrait.png") as img:
        assert img.size == (1024, 1024), f"Master portrait must be 1024x1024, got {img.size}"
    print("[PASS] Master portrait is calibrated to 1024x1024 (1:1 ratio).")

    # 4. Verify Feathered Mouth Has Alpha Transparency
    with Image.open(assets_dir / "mouth_v2_rest.png") as img:
        assert img.mode == "RGBA", "Mouth layer must have RGBA alpha channel for seamless feathering"
    print("[PASS] Mouth layers have RGBA alpha channel for seamless feathering.")

    # 5. Verify avatar_engine.js State Machine & Landmark Coordinates
    js_content = (current_dir / "avatar_engine.js").read_text(encoding="utf-8")
    for state in ["IDLE", "LISTENING", "THINKING", "SPEAKING", "HAPPY", "EMPATHETIC", "CONFUSED", "SUCCESS", "WARNING", "OFFLINE", "ERROR", "RECONNECTING"]:
        assert f"{state}:" in js_content, f"Missing state {state} in avatar_engine.js"
    assert "EYES_BOX = { x: 320, y: 425, w: 365, h: 115 };" in js_content
    assert "MOUTH_BOX = { x: 405, y: 650, w: 245, h: 105 };" in js_content
    assert "Math.random() * 0.55" not in js_content, "Random viseme chewing artifact must be eliminated"
    assert "envelope" in js_content or "Math.sin(Math.PI * phase)" in js_content
    print("[PASS] avatar_engine.js 12-state protocol and Model A facial landmarks calibrated.")

    # 6. Verify Python mouth_sync engine
    sys.path.insert(0, str(current_dir))
    from mouth_sync import MouthSyncEngine
    engine = MouthSyncEngine(frame_interval_ms=50)
    timeline = engine.generate_timeline("backup_test", "Xin chào Anh Quân, em là Tony.", target_duration_ms=2500)
    assert timeline.total_duration_ms == 2500
    assert len(timeline.frames) >= 30
    visemes = {f.viseme for f in timeline.frames}
    assert "REST" in visemes
    print("[PASS] mouth_sync.py generated valid Vietnamese phoneme timeline.")

    print("==================================================")
    print("[SUCCESS] ALL AVATAR VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
