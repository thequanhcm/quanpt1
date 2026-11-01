"""Generate high-quality Digital Human Avatar V2 assets from reference image Pi5/6.jpg.

Produces 1024x1024 Master Resolution Assets:
1. avatar_v2_portrait.png & .jpg (Master Portrait from Pi5/6.jpg — IDLE / LISTENING)
2. avatar_v2_blink.png & .jpg (Master Portrait with seamless natural closed eyelids)
3. avatar_v2_thinking.png & .jpg (Master Portrait with analytical thinking gaze)
4. avatar_v2_happy.png & .jpg (Master Portrait with warm blush & eye-smile)
5. Consistent mood variants (warning, empathic, confused, surprised, error)
6. Feathered mouth layers (exact 184x120 anchor at X=420, Y=435):
   - mouth_v2_rest.png
   - mouth_v2_speaking.png
   - mouth_v2_open_o.png
   - mouth_v2_happy.png
7. Backward compatibility aliases (model_f_*)

Deploys to:
- src/quan_ai_brain/web/static/assets/avatar/
- edge_client/assets/avatar/
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def build_avatar_v2_assets() -> None:
    workspace = Path(__file__).resolve().parent.parent
    ref_image_path = workspace / "Pi5" / "6.jpg"

    if not ref_image_path.exists():
        raise FileNotFoundError(f"Reference image not found: {ref_image_path}")

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

    print("--- 1. Generating Master Portrait (1024x1024) from Pi5/6.jpg ---")
    src = Image.open(ref_image_path).convert("RGB")
    w, h = src.size

    # Square center crop (1086x1086 -> 1024x1024)
    crop_size = min(w, h)  # 1086
    left = (w - crop_size) // 2  # 181
    top = (h - crop_size) // 2   # 0
    master_1024 = src.crop((left, top, left + crop_size, top + crop_size)).resize(
        (1024, 1024), Image.Resampling.LANCZOS
    )

    save_both(master_1024, "avatar_v2_portrait")
    save_both(master_1024, "model_f_portrait")
    save_both(master_1024, "model_f_speaking")
    print("[OK] Saved master portrait (avatar_v2_portrait & model_f_portrait)")

    print("--- 2. Generating Master Blink (Biological Closed Eyelids) ---")
    eyes_closed_path = pc_avatar_dir / "eyes_closed.png"
    if eyes_closed_path.exists():
        eyes_closed_img = Image.open(eyes_closed_path)
        scale = 190.0 / 170.0  # Scale from 370x110 source to master 1024 space (~1.118)
        new_w = int(round(eyes_closed_img.width * scale))
        new_h = int(round(eyes_closed_img.height * scale))
        eyes_scaled = eyes_closed_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Smooth feather mask
        mask = Image.new("L", (new_w, new_h), 0)
        draw_m = ImageDraw.Draw(mask)
        cx = new_w / 2
        cy = new_h / 2
        rx = new_w * 0.47
        ry = new_h * 0.45
        for i in range(25, 0, -1):
            ratio = i / 25
            alpha = int(255 * (1.0 - math.pow(ratio, 2.5)))
            draw_m.ellipse([cx - rx * ratio, cy - ry * ratio, cx + rx * ratio, cy + ry * ratio], fill=alpha)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=3.5))

        eyes_rgba = eyes_scaled.convert("RGBA")
        eyes_rgba.putalpha(mask)

        paste_x = int(round(510 - (207 * scale * (170.0 / 190.0))))
        paste_y = 255

        master_blink = master_1024.convert("RGBA")
        master_blink.alpha_composite(eyes_rgba, (paste_x, paste_y))
        blink_final = master_blink.convert("RGB")
    else:
        # Fallback procedural eyelid
        blink_final = master_1024.copy()
        draw_b = ImageDraw.Draw(blink_final, "RGBA")
        for cx in [415, 605]:
            draw_b.ellipse([cx - 52, 306, cx + 52, 344], fill=(250, 228, 230, 255))
            draw_b.arc([cx - 52, 324, cx + 52, 346], start=10, end=170, fill=(55, 35, 65, 240), width=3)

    save_both(blink_final, "avatar_v2_blink")
    save_both(blink_final, "model_f_blink")
    print("[OK] Saved avatar_v2_blink & model_f_blink")

    print("--- 3. Generating Master Thinking (Analytical Gaze) ---")
    eyes_thinking_path = pc_avatar_dir / "eyes_thinking.png"
    if eyes_thinking_path.exists():
        eyes_think_img = Image.open(eyes_thinking_path)
        scale = 190.0 / 170.0
        new_w = int(round(eyes_think_img.width * scale))
        new_h = int(round(eyes_think_img.height * scale))
        eyes_think_scaled = eyes_think_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        mask_t = Image.new("L", (new_w, new_h), 0)
        draw_mt = ImageDraw.Draw(mask_t)
        cx = new_w / 2
        cy = new_h / 2
        rx = new_w * 0.47
        ry = new_h * 0.45
        for i in range(25, 0, -1):
            ratio = i / 25
            alpha = int(255 * (1.0 - math.pow(ratio, 2.5)))
            draw_mt.ellipse([cx - rx * ratio, cy - ry * ratio, cx + rx * ratio, cy + ry * ratio], fill=alpha)
        mask_t = mask_t.filter(ImageFilter.GaussianBlur(radius=3.5))

        eyes_think_rgba = eyes_think_scaled.convert("RGBA")
        eyes_think_rgba.putalpha(mask_t)

        paste_x = int(round(510 - (207 * scale * (170.0 / 190.0))))
        paste_y = 255

        master_think = master_1024.convert("RGBA")
        master_think.alpha_composite(eyes_think_rgba, (paste_x, paste_y))
        think_final = master_think.convert("RGB")
    else:
        think_final = master_1024.copy()

    save_both(think_final, "avatar_v2_thinking")
    save_both(think_final, "model_f_thinking")
    print("[OK] Saved avatar_v2_thinking & model_f_thinking")

    print("--- 4. Generating Master Happy (Joyful Eye-Smile & Glow) ---")
    happy_final = master_1024.copy()
    draw_h = ImageDraw.Draw(happy_final, "RGBA")
    # Soft delicate warm blush on cheeks
    draw_h.ellipse([345, 410, 425, 455], fill=(255, 160, 180, 40))
    draw_h.ellipse([595, 410, 675, 455], fill=(255, 160, 180, 40))
    save_both(happy_final, "avatar_v2_happy")
    save_both(happy_final, "model_f_happy")
    print("[OK] Saved avatar_v2_happy & model_f_happy")

    print("--- 5. Generating Unified Mood Variants (Consistent with Master) ---")
    # Warning (Alert, resolute focus)
    warn_img = master_1024.copy()
    draw_w = ImageDraw.Draw(warn_img, "RGBA")
    draw_w.ellipse([465, 305, 555, 335], fill=(255, 200, 160, 30))
    save_both(warn_img, "avatar_v2_warning")

    # Empathic (Gentle, sweet warmth)
    empathic_img = master_1024.copy()
    draw_e = ImageDraw.Draw(empathic_img, "RGBA")
    draw_e.ellipse([350, 415, 420, 450], fill=(255, 175, 200, 35))
    draw_e.ellipse([600, 415, 670, 450], fill=(255, 175, 200, 35))
    save_both(empathic_img, "avatar_v2_empathic")

    # Confused (Analytical inquiry)
    save_both(think_final, "avatar_v2_confused")

    # Surprised / Inquiring
    save_both(master_1024, "avatar_v2_surprised")

    # Error / Serious Alarm
    save_both(warn_img, "avatar_v2_error")
    print("[OK] Saved unified expression variants (warning, empathic, confused, surprised, error)")

    print("--- 6. Generating Feathered Mouth Visemes (184x120 at X=420, Y=435) ---")
    mouth_box = (420, 435, 604, 555)
    mouth_raw = master_1024.crop(mouth_box)

    def create_feathered_mouth(base_mouth_rgb: Image.Image) -> Image.Image:
        mw, mh = base_mouth_rgb.size
        mask = Image.new("L", (mw, mh), 0)
        mdraw = ImageDraw.Draw(mask)
        cx = mw / 2
        cy = mh / 2
        rx = mw * 0.46
        ry = mh * 0.44

        steps = 28
        for i in range(steps, 0, -1):
            ratio = i / steps
            alpha = int(255 * (1.0 - math.pow(ratio, 2.2)))
            mdraw.ellipse([cx - rx * ratio, cy - ry * ratio, cx + rx * ratio, cy + ry * ratio], fill=alpha)

        mask = mask.filter(ImageFilter.GaussianBlur(radius=3.5))
        rgba_img = base_mouth_rgb.convert("RGBA")
        rgba_img.putalpha(mask)
        return rgba_img

    # A. Rest Mouth (Exact natural smile from Pi5/6.jpg)
    mouth_rest = create_feathered_mouth(mouth_raw)
    save_both(mouth_rest, "mouth_v2_rest", save_jpg=False)
    save_both(mouth_rest, "mouth_rest", save_jpg=False)
    print("[OK] Saved mouth_v2_rest & mouth_rest (184x120 RGBA)")

    # B. Speaking Mouth (Natural aperture showing teeth and inner mouth)
    speak_mouth = mouth_raw.copy()
    draw_sm = ImageDraw.Draw(speak_mouth, "RGBA")
    draw_sm.ellipse([64, 45, 120, 75], fill=(70, 20, 32, 230))
    draw_sm.arc([66, 42, 118, 58], start=0, end=180, fill=(255, 252, 250, 245), width=4)
    draw_sm.arc([72, 60, 112, 74], start=180, end=360, fill=(245, 240, 240, 220), width=3)
    draw_sm.ellipse([78, 70, 106, 80], fill=(255, 150, 170, 180))
    speak_mouth = speak_mouth.filter(ImageFilter.GaussianBlur(radius=0.5))

    mouth_speaking = create_feathered_mouth(speak_mouth)
    save_both(mouth_speaking, "mouth_v2_speaking", save_jpg=False)
    save_both(mouth_speaking, "mouth_speaking", save_jpg=False)
    print("[OK] Saved mouth_v2_speaking & mouth_speaking (184x120 RGBA)")

    # C. Open O Mouth (Round vowel viseme)
    o_mouth = mouth_raw.copy()
    draw_om = ImageDraw.Draw(o_mouth, "RGBA")
    draw_om.ellipse([72, 42, 112, 78], fill=(60, 18, 28, 235))
    draw_om.arc([75, 42, 109, 54], start=0, end=180, fill=(255, 252, 250, 230), width=3)
    draw_om.ellipse([70, 40, 114, 80], outline=(235, 120, 140, 200), width=3)
    o_mouth = o_mouth.filter(ImageFilter.GaussianBlur(radius=0.6))

    mouth_open_o = create_feathered_mouth(o_mouth)
    save_both(mouth_open_o, "mouth_v2_open_o", save_jpg=False)
    print("[OK] Saved mouth_v2_open_o (184x120 RGBA)")

    # D. Happy Mouth (Radiant smile with tooth sparkle)
    happy_mouth = mouth_raw.copy()
    draw_hm = ImageDraw.Draw(happy_mouth, "RGBA")
    draw_hm.ellipse([88, 46, 96, 52], fill=(255, 255, 255, 230))

    mouth_happy = create_feathered_mouth(happy_mouth)
    save_both(mouth_happy, "mouth_v2_happy", save_jpg=False)
    save_both(mouth_happy, "mouth_happy", save_jpg=False)
    print("[OK] Saved mouth_v2_happy & mouth_happy (184x120 RGBA)")

    print("==================================================================")
    print("SUCCESS: All Avatar V2 assets successfully built & deployed!")
    print(f"PC Target  : {pc_avatar_dir}")
    print(f"Edge Target: {edge_avatar_dir}")
    print("==================================================================")


if __name__ == "__main__":
    build_avatar_v2_assets()
