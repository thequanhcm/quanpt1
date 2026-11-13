"""
Test 13/11/2026: Pi5 kiosk overlay effects (hologram cylinder, particles, laser, lightning, caption).
Nguồn gốc (owner 13/11): "em hãy dựa theo video này, tiến hành cấu hình và xây dựng Pi5 giao diện hình thể
có thể thực hiện được giống như video này @file:pi5 template.mp4"
"""
import re
from pathlib import Path

ROOT = Path(r"E:/BRAIN/edge_client")
HTML = (ROOT / "kiosk.html").read_text(encoding="utf-8")
CSS = (ROOT / "kiosk.css").read_text(encoding="utf-8")
JS = (ROOT / "kiosk.js").read_text(encoding="utf-8")


def test_html_hologram_cylinder():
    assert 'id="hologram-cylinder"' in HTML
    assert 'class="cylinder-glass"' in HTML
    assert 'class="cylinder-led-ring"' in HTML
    assert 'class="cylinder-base"' in HTML


def test_html_particles_canvas():
    assert 'id="particles-canvas"' in HTML
    assert 'class="particles-canvas"' in HTML


def test_html_laser_bar():
    assert 'id="laser-bar"' in HTML
    assert 'class="laser-bar"' in HTML


def test_html_lightning_bolts():
    assert 'id="lightning-bolts"' in HTML
    for i in range(1, 5):
        assert f'class="bolt bolt-{i}"' in HTML


def test_html_state_caption():
    assert 'id="state-caption"' in HTML
    assert 'class="state-caption"' in HTML


def test_css_hologram_styles():
    assert ".hologram-cylinder" in CSS
    assert ".cylinder-glass" in CSS
    assert ".cylinder-led-ring" in CSS
    assert ".cylinder-base" in CSS
    assert "@keyframes cylinderPulse" in CSS
    assert "@keyframes ledRingRotate" in CSS


def test_css_laser_styles():
    assert ".laser-bar" in CSS
    assert "@keyframes laserScan" in CSS
    assert ".state-thinking .laser-bar" in CSS
    assert ".state-researching .laser-bar" in CSS


def test_css_lightning_styles():
    assert ".lightning-bolts" in CSS
    assert ".bolt" in CSS
    assert "@keyframes boltFlicker" in CSS
    assert ".state-speaking .lightning-bolts" in CSS
    assert ".state-speaking .bolt" in CSS


def test_css_caption_styles():
    assert ".state-caption" in CSS
    for state in ["listening", "thinking", "speaking", "happy", "warning", "blocked", "offline", "sleeping"]:
        assert f".state-{state} .state-caption" in CSS


def test_css_responsive_breakpoints():
    assert re.search(r"@media\s*\(\s*min-width:\s*1280px\s*\)", CSS)
    assert re.search(r"@media\s*\(\s*min-width:\s*1920px\s*\)", CSS)
    assert re.search(r"@media\s*\(\s*min-width:\s*2560px\s*\)", CSS)


def test_js_state_captions_map():
    assert "STATE_CAPTIONS" in JS
    assert 'IDLE: "SẴN SÀNG"' in JS
    assert 'LISTENING: "ĐANG LẮNG NGHE"' in JS
    assert 'THINKING: "ĐANG SUY LUẬN"' in JS
    assert 'SPEAKING: "ĐANG NÓI"' in JS
    assert 'OFFLINE: "MẤT KẾT NỐI"' in JS
    assert 'SLEEPING: "TẠM NGHỈ"' in JS


def test_js_caption_update():
    assert "stateCaption.textContent = captionText" in JS


def test_js_particles_init():
    assert "initParticles" in JS
    assert 'getElementById("particles-canvas")' in JS
    assert "particlesCanvas.getContext" in JS
    assert "requestAnimationFrame(loop)" in JS
    assert "NUM = 40" in JS
    assert "FRAME_MS = 83" in JS


def test_js_dom_refs():
    assert 'getElementById("state-caption")' in JS
    assert 'getElementById("particles-canvas")' in JS
