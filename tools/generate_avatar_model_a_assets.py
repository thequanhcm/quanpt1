"""Generate high-quality Digital Human Avatar Model A assets.

Reference standard:
- Identity: Model A (Dịu dàng, thân thiện, thông minh, tóc đen dài, tai nghe cyan, trang phục trắng bạc)
- Master source: reports/model_a_1024_preview.jpg (from Pi5/4.png, Row 0, Col 0)
- Master states:
  * reports/model_a_blink.jpg (biological closed eyes)
  * reports/model_a_thinking.jpg (analytical gaze)
  * reports/model_a_speaking.jpg (natural speech aperture)

Produces 1024x1024 Master Resolution Assets:
1. avatar_v2_portrait.png & .jpg (Master Model A — IDLE / LISTENING)
2. avatar_v2_blink.png & .jpg (Master Model A — BLINK / OFFLINE)
3. avatar_v2_thinking.png & .jpg (Master Model A — THINKING / RESEARCH)
4. avatar_v2_speaking.png & .jpg (Master Model A — SPEAKING)
5. avatar_v2_happy.png & .jpg (Master Model A — HAPPY / SUCCESS)
6. Mood variants (warning, empathic, confused, surprised, error)
7. Feathered mouth visemes (245x105 anchor at X=405, Y=650):
   - mouth_v2_rest.png
   - mouth_v2_speaking.png
   - mouth_v2_open_o.png
   - mouth_v2_happy.png
8. Feathered eye layers (365x115 anchor at X=320, Y=425):
   - eyes_closed.png
   - eyes_thinking.png
   - eyes_open.png
9. Backward compatibility aliases (model_f_*)

Deploys to:
- src/quan_ai_brain/web/static/assets/avatar/
- edge_client/assets/avatar/
"""
from __future__ import annotations

import math
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFilter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def build_avatar_model_a_assets() -> None:
    workspace = Path(__file__).resolve().parent.parent
    reports_dir = workspace / "reports"

    idle_path = reports_dir / "model_a_1024_preview.jpg"
    blink_path = reports_dir / "model_a_blink.jpg"
    think_path = reports_dir / "model_a_thinking.jpg"
    speak_path = reports_dir / "model_a_speaking.jpg"

    for p in (idle_path, blink_path, think_path, speak_path):
        if not p.exists():
            raise FileNotFoundError(f"Required Model A master asset not found: {p}")

    # Destination directories
    pc_avatar_dir = workspace / "src" / "quan_ai_brain" / "web" / "static" / "assets" / "avatar"
    edge_avatar_dir = workspace / "edge_client" / "assets" / "avatar"
    pc_avatar_dir.mkdir(parents=True, exist_ok=True)
    edge_avatar_dir.mkdir(parents=True, exist_ok=True)

    def save_both(img: Image.Image, name_base: str, save_jpg: bool = True) -> None:
        png_pc = pc_avatar_dir / f"{name_base}.png"
        png_edge = edge_avatar_dir / f"{name_base}.png"
        img.save(png_pc, format="PNG")
        img.save(png_edge, format="PNG")
        if save_jpg:
            rgb = img.convert("RGB")
            jpg_pc = pc_avatar_dir / f"{name_base}.jpg"
            jpg_edge = edge_avatar_dir / f"{name_base}.jpg"
            rgb.save(jpg_pc, format="JPEG", quality=95)
            rgb.save(jpg_edge, format="JPEG", quality=95)

    print("--- 1. Loading Master Model A Images (1024x1024) ---")
    master_idle = Image.open(idle_path).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
    master_blink = Image.open(blink_path).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
    master_think = Image.open(think_path).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
    master_speak = Image.open(speak_path).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)

    # Save Master Portraits
    save_both(master_idle, "avatar_v2_portrait")
    save_both(master_idle, "model_f_portrait")  # Alias for compatibility
    save_both(master_blink, "avatar_v2_blink")
    save_both(master_blink, "model_f_blink")
    save_both(master_think, "avatar_v2_thinking")
    save_both(master_think, "model_f_thinking")
    save_both(master_speak, "avatar_v2_speaking")
    save_both(master_speak, "model_f_speaking")
    print("[OK] Saved master portraits: portrait, blink, thinking, speaking")

    print("--- 2. Generating Happy Portrait (Joyful Eye-Smile & Blush) ---")
    happy_img = master_idle.copy()
    draw_h = ImageDraw.Draw(happy_img, "RGBA")
    # Soft warm blush on cheeks (calibrated to Model A cheekbone geometry: y=530..600)
    draw_h.ellipse([310, 535, 415, 595], fill=(255, 155, 175, 42))
    draw_h.ellipse([625, 515, 730, 575], fill=(255, 155, 175, 42))
    save_both(happy_img, "avatar_v2_happy")
    save_both(happy_img, "model_f_happy")
    print("[OK] Saved avatar_v2_happy")

    print("--- 3. Generating Unified Expression Variants ---")
    # Warning (Alert, serious focus)
    warn_img = master_idle.copy()
    draw_w = ImageDraw.Draw(warn_img, "RGBA")
    draw_w.ellipse([450, 410, 560, 445], fill=(255, 190, 150, 30))
    save_both(warn_img, "avatar_v2_warning")

    # Empathic (Gentle, warm, compassionate)
    empathic_img = master_idle.copy()
    draw_e = ImageDraw.Draw(empathic_img, "RGBA")
    draw_e.ellipse([315, 540, 410, 590], fill=(255, 170, 195, 38))
    draw_e.ellipse([630, 520, 725, 570], fill=(255, 170, 195, 38))
    save_both(empathic_img, "avatar_v2_empathic")

    # Confused (Thoughtful inquiry)
    save_both(master_think, "avatar_v2_confused")

    # Surprised / Inquiring
    save_both(master_idle, "avatar_v2_surprised")

    # Error / Severe Alert
    save_both(warn_img, "avatar_v2_error")
    print("[OK] Saved mood variants: warning, empathic, confused, surprised, error")

    print("--- 4. Generating Feathered Mouth Visemes (245x105 at X=405, Y=650) ---")
    mouth_box = (405, 650, 405 + 245, 650 + 105)
    mouth_rest_raw = master_idle.crop(mouth_box)
    mouth_speak_raw = master_speak.crop(mouth_box)

    def create_feathered_mouth(base_mouth_rgb: Image.Image) -> Image.Image:
        mw, mh = base_mouth_rgb.size
        mask = Image.new("L", (mw, mh), 0)
        mdraw = ImageDraw.Draw(mask)
        cx = mw / 2
        cy = mh / 2
        rx = mw * 0.47
        ry = mh * 0.45

        steps = 28
        for i in range(steps, 0, -1):
            ratio = i / steps
            alpha = int(255 * (1.0 - math.pow(ratio, 2.2)))
            mdraw.ellipse([cx - rx * ratio, cy - ry * ratio, cx + rx * ratio, cy + ry * ratio], fill=alpha)

        mask = mask.filter(ImageFilter.GaussianBlur(radius=3.5))
        rgba_img = base_mouth_rgb.convert("RGBA")
        rgba_img.putalpha(mask)
        return rgba_img

    # A. Rest Mouth (Exact natural smile of Model A)
    mouth_rest = create_feathered_mouth(mouth_rest_raw)
    save_both(mouth_rest, "mouth_v2_rest", save_jpg=False)
    save_both(mouth_rest, "mouth_rest", save_jpg=False)
    print("[OK] Saved mouth_v2_rest (245x105 RGBA)")

    # B. Speaking Mouth (Natural aperture from Model A speaking master)
    mouth_speaking = create_feathered_mouth(mouth_speak_raw)
    save_both(mouth_speaking, "mouth_v2_speaking", save_jpg=False)
    save_both(mouth_speaking, "mouth_speaking", save_jpg=False)
    print("[OK] Saved mouth_v2_speaking (245x105 RGBA)")

    # C. Open O Mouth (Round vowel viseme)
    o_mouth = mouth_speak_raw.copy()
    draw_om = ImageDraw.Draw(o_mouth, "RGBA")
    # Soft rounded contour
    draw_om.ellipse([88, 32, 158, 82], outline=(235, 120, 140, 180), width=3)
    o_mouth = o_mouth.filter(ImageFilter.GaussianBlur(radius=0.5))
    mouth_open_o = create_feathered_mouth(o_mouth)
    save_both(mouth_open_o, "mouth_v2_open_o", save_jpg=False)
    print("[OK] Saved mouth_v2_open_o (245x105 RGBA)")

    # D. Happy Mouth (Radiant smile)
    happy_mouth_raw = happy_img.crop(mouth_box)
    mouth_happy = create_feathered_mouth(happy_mouth_raw)
    save_both(mouth_happy, "mouth_v2_happy", save_jpg=False)
    save_both(mouth_happy, "mouth_happy", save_jpg=False)
    print("[OK] Saved mouth_v2_happy (245x105 RGBA)")

    print("--- 5. Generating Feathered Eyes Layers (365x115 at X=320, Y=425) ---")
    eyes_box = (320, 425, 320 + 365, 425 + 115)
    eyes_idle_raw = master_idle.crop(eyes_box)
    eyes_blink_raw = master_blink.crop(eyes_box)
    eyes_think_raw = master_think.crop(eyes_box)

    def create_feathered_eyes(base_eyes_rgb: Image.Image) -> Image.Image:
        ew, eh = base_eyes_rgb.size
        mask = Image.new("L", (ew, eh), 0)
        edraw = ImageDraw.Draw(mask)
        cx = ew / 2
        cy = eh / 2
        rx = ew * 0.48
        ry = eh * 0.46

        steps = 26
        for i in range(steps, 0, -1):
            ratio = i / steps
            alpha = int(255 * (1.0 - math.pow(ratio, 2.2)))
            edraw.ellipse([cx - rx * ratio, cy - ry * ratio, cx + rx * ratio, cy + ry * ratio], fill=alpha)

        mask = mask.filter(ImageFilter.GaussianBlur(radius=3.5))
        rgba_img = base_eyes_rgb.convert("RGBA")
        rgba_img.putalpha(mask)
        return rgba_img

    eyes_open = create_feathered_eyes(eyes_idle_raw)
    eyes_closed = create_feathered_eyes(eyes_blink_raw)
    eyes_thinking = create_feathered_eyes(eyes_think_raw)

    save_both(eyes_open, "eyes_open", save_jpg=False)
    save_both(eyes_closed, "eyes_closed", save_jpg=False)
    save_both(eyes_closed, "eyes_blink_test", save_jpg=False)
    save_both(eyes_thinking, "eyes_thinking", save_jpg=False)
    print("[OK] Saved eyes layers: eyes_open, eyes_closed, eyes_thinking (365x115 RGBA)")

    print("==================================================================")
    print("SUCCESS: All Digital Human Model A assets successfully built & deployed!")
    print(f"PC Target  : {pc_avatar_dir}")
    print(f"Edge Target: {edge_avatar_dir}")
    print("==================================================================")


if __name__ == "__main__":
    build_avatar_model_a_assets()
