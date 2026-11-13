"""
Test 13/11/2026 (buổi tối): Pi5 avatar body+arms BẢN MỀM (soft).
Nguồn gốc (owner 13/11): "rà soát ... hiệu chỉnh cho giao diện hình thể ... mềm mại,
tự nhiên nhất. lưu ý giữ nguyên khuôn mặt gốc cũ"
- Giữ nguyên khuôn mặt: mask chỉ áp dụng vùng ngực trở xuống (y >= 0.55h).
- Tay: cong 2 khúc (quadratic), reach ~0.27 để bàn tay nằm TRÊN phím (kbTop 0.86h).
- Hoa/đàn/bèo nhún: ellipse + roundRect + alpha thấp — hết khối vuông sắc.
"""
from pathlib import Path

JS = Path(r"E:/BRAIN/edge_client/avatar_engine.js").read_text(encoding="utf-8")
HTML = Path(r"E:/BRAIN/edge_client/kiosk.html").read_text(encoding="utf-8")


def test_body_arms_methods_exist():
    assert "_renderBodyAndArms" in JS
    assert "_drawMaskedPortrait" in JS
    assert "_renderArmsOverPortrait" in JS
    assert "_drawArm" in JS


def test_body_offscreen_cache():
    assert "_bodyCanvas" in JS
    assert "_bodyCacheKey" in JS
    assert "_portraitMaskedCanvas" in JS
    assert "_portraitMaskedKey" in JS


def test_body_lavender_dress():
    # Váy tím lavender gradient (giữ nguyên màu gốc)
    assert "180, 140, 220" in JS
    assert "150, 110, 200" in JS
    assert "120, 80, 180" in JS


def test_flower_soft_petals():
    # Hoa mềm: 2 lớp cánh ellipse + tâm gradient (không còn 5 chấm tròn cứng)
    assert "flowerX" in JS
    assert "flowerY" in JS
    assert "heart.addColorStop" in JS
    assert "ctx.ellipse(px, py, flowerR * 0.52" in JS


def test_keyboard_rounded():
    # Đàn bo góc roundRect + viền mềm + dải sáng phản chiếu
    assert "ctx.roundRect" in JS
    assert "kbSheen" in JS
    assert "rgba(0, 229, 255, 0.22)" in JS


def test_arms_soft_curves():
    # Tay cong quadratic 2 khúc + anchor từ cạnh dưới portrait (0.88h)
    assert "quadraticCurveTo" in JS
    assert "elbowX" in JS
    assert "w * 0.26, y: h * 0.88" in JS
    assert "w * 0.74, y: h * 0.88" in JS
    # KHÔNG còn anchor cũ đè lên mặt (0.62h)
    assert "x: w * 0.36, y: h * 0.62" not in JS
    assert "x: w * 0.64, y: h * 0.62" not in JS


def test_hands_land_on_keyboard():
    # handY = 0.88h + cos(angle)*reach ≈ 0.93-0.97h — NGAY TRÊN phím (kbTop 0.935h)
    # Kiểm gián tiếp: reach nhỏ (0.08-0.13) và kbTop ở 0.93h+
    import re
    m = re.search(r"leftHandReach = ([0-9.]+)", JS)
    assert m and 0.08 <= float(m.group(1)) <= 0.13
    m = re.search(r"rightHandReach = ([0-9.]+)", JS)
    assert m and 0.08 <= float(m.group(1)) <= 0.13
    m = re.search(r"const kbTop = h \* ([0-9.]+)", JS)
    assert m and 0.92 <= float(m.group(1)) <= 0.95
    # Mask fade dài 0.84→0.99 (đêm)
    assert "h * 0.84" in JS
    assert "h * 0.99" in JS


def test_body_sway_synced():
    # (đêm) Body/arms KHÔNG còn sway riêng — cùng head transform với portrait
    # (chống seam ngang qua mũi khi headTilt/sway lệch pha)
    assert "const swayPhase = (now - this.startTime) * 0.0012;" not in JS
    assert "ctx.translate(swayX, swayY);" not in JS
    # beatPhase (nhịp đánh đàn) vẫn giữ
    assert "beatPhase" in JS


def test_mask_soft_fade():
    # (đêm) Fade sâu 0.84→0.99: KHÔNG cắt mặt (mặt chiếm tới ~0.84h)
    assert "h * 0.84" in JS
    assert "h * 0.99" in JS
    assert "h * 0.55" not in JS
    assert "h * 0.68" not in JS


def test_face_untouched_region():
    # Khuôn mặt gốc: mọi biến thể portrait đều vẽ QUA mask (đúng 1 call `this.` + 1 def)
    assert JS.count("this._drawMaskedPortrait(ctx, baseImg, w, h)") == 1
    assert JS.count("_drawMaskedPortrait(ctx, baseImg, w, h) {") == 1
    # Mask chỉ tác động từ 0.55h trở xuống — vùng mặt (y < 0.5h) alpha=1 nguyên vẹn
    mask_block = JS[JS.find("_drawMaskedPortrait(ctx, baseImg"):JS.find("_renderArmsOverPortrait(ctx, w, h, now, config) {")]
    assert "0.55" in mask_block


def test_render_order():
    body_idx = JS.find("_renderBodyAndArms(ctx,")
    mask_idx = JS.find("_drawMaskedPortrait(ctx,")
    arms_idx = JS.find("_renderArmsOverPortrait(ctx,")
    assert 0 < body_idx < mask_idx < arms_idx


def test_smile_default():
    assert 'IDLE: { name: "IDLE (SẴN SÀNG)"' in JS
    assert 'defaultTone: "WARM_GREETING"' in JS


def test_kiosk_html_cache_bust_bumped():
    # Chromium phải fetch engine MỚI — cache-bust phải là bản sync đêm
    assert "avatar_engine.js?v=body_sync_1311" in HTML
    assert "avatar_engine.js?v=cherry_07nov_r1" not in HTML
