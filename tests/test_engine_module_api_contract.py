"""TASK001 audit 14/11 — Engine↔Module API contract test.

Bối cảnh: Sprint 6 wire engine gọi this._mouthDriver.getCurrentEnergy() —
method KHÔNG TỒN TẠI trên AudioMouthDriver → TypeError MỖI FRAME trong
_update() → render loop crash → Pi5 CPU 110% (gpu 60% + renderer 48%) +
avatar đứng yên. pytest 29/29 pass vì chỉ test Python mirror + module độc lập —
KHÔNG có test contract giữa engine và module.

Test này quét mọi call this._<driver>.<method>( trên cả 2 engine (PC + Pi5)
và xác minh method tồn tại trong module JS tương ứng. Chặn vĩnh viễn bug
"class gọi method không tồn tại" mà không cần jsdom.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EDGE = REPO / "edge_client"
STATIC = REPO / "src" / "quan_ai_brain" / "web" / "static"

ENGINES = {
    "Pi5": EDGE / "avatar_engine.js",
    "PC": STATIC / "avatar_engine.js",
}

# attr name trên engine → module JS định nghĩa prototype
DRIVER_MODULES = {
    "_mouthDriver": EDGE / "audio_mouth_driver.js",
    "_presenceEngine": EDGE / "presence_engine.js",
    "_bodyMotionEngine": EDGE / "body_motion_engine.js",
    "_motionScheduler": EDGE / "motion_scheduler.js",
    "_emotionEngine": EDGE / "emotion_engine.js",
}

# pattern: this._mouthDriver.method( hoặc this._mouthDriver.method(  (không bắt method = func ref)
CALL_RE = re.compile(r"this\.(" + "|".join(re.escape(k) for k in DRIVER_MODULES) + r")\.([A-Za-z_$][\w$]*)\s*\(")

# pattern method định nghĩa trong module JS (cả 2 style):
#   X.prototype.method = / method: function / method(  (class) / method = function
DEF_RE = re.compile(r"(?:prototype\.|^\s*)({m})\s*(?:=\s*(?:async\s+)?function|\(|:)", re.M)


def _defined_methods(module_js: str) -> set[str]:
    """Trích mọi method name có vẻ được định nghĩa trong module JS."""
    names: set[str] = set()
    # style 1: X.prototype.method = function
    for m in re.finditer(r"prototype\.([A-Za-z_$][\w$]*)\s*=", module_js):
        names.add(m.group(1))
    # style 2: method(args) { — class method (indent 2+)
    for m in re.finditer(r"^\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{", module_js, re.M):
        names.add(m.group(1))
    # style 3: method: function
    for m in re.finditer(r"([A-Za-z_$][\w$]*)\s*:\s*(?:async\s+)?function", module_js):
        names.add(m.group(1))
    return names


class TestEngineModuleApiContract:
    """Mọi method engine gọi trên driver module PHẢI tồn tại trong module."""

    def test_no_phantom_get_current_energy_anywhere(self):
        """Bug gốc Sprint 6: getCurrentEnergy không tồn tại — cấm tên này
        trong CODE (bỏ qua comment //)."""
        for label, engine in ENGINES.items():
            src = engine.read_text(encoding="utf-8")
            code_only = re.sub(r"//[^\n]*", "", src)  # bỏ comment dòng
            assert "getCurrentEnergy" not in code_only, (
                f"{label} engine gọi getCurrentEnergy — method không tồn tại trên "
                "AudioMouthDriver (bug Sprint 6 tái diễn)"
            )

    def test_all_engine_driver_calls_exist_in_modules(self):
        for label, engine in ENGINES.items():
            src = engine.read_text(encoding="utf-8")
            calls = CALL_RE.findall(src)
            assert calls, f"{label} engine: không tìm thấy driver call nào (pattern sai?)"
            for attr, method in calls:
                module_path = DRIVER_MODULES[attr]
                module_js = module_path.read_text(encoding="utf-8")
                defined = _defined_methods(module_js)
                assert method in defined, (
                    f"{label} engine gọi this.{attr}.{method}() nhưng method này "
                    f"KHÔNG TỒN TẠI trong {module_path.name} (defined: {sorted(defined)})"
                )

    def test_mouth_driver_get_current_contract(self):
        """getCurrent() phải trả đủ {viseme, open, envelope, active} — engine
        đọc .envelope từ kết quả này."""
        js = (EDGE / "audio_mouth_driver.js").read_text(encoding="utf-8")
        assert "getCurrent" in js
        assert "envelope" in js
        # Python mirror đồng bộ
        py = (EDGE / "audio_mouth_driver.py").read_text(encoding="utf-8")
        assert "def get_current" in py
        assert "envelope" in py

    def test_presence_engine_tick_set_state_contract(self):
        js = (EDGE / "presence_engine.js").read_text(encoding="utf-8")
        for method in ("tick", "setState"):
            assert re.search(rf"prototype\.{method}\s*=", js), f"presence_engine.js thiếu prototype.{method}"

    def test_body_motion_engine_tick_set_state_contract(self):
        js = (EDGE / "body_motion_engine.js").read_text(encoding="utf-8")
        for method in ("tick", "setState", "setSpeaking", "setSpeechEnergy"):
            assert re.search(rf"prototype\.{method}\s*=", js), f"body_motion_engine.js thiếu prototype.{method}"

    def test_both_engines_use_same_fixed_call(self):
        """Cả 2 engine phải dùng getCurrent() với guard null — fix đồng bộ."""
        for label, engine in ENGINES.items():
            src = engine.read_text(encoding="utf-8")
            assert "getCurrent()" in src, f"{label} engine thiếu getCurrent()"
            assert "mouth.envelope" in src, f"{label} engine không đọc mouth.envelope"
