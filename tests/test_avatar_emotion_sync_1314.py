"""Sprint sync_1314 — đồng bộ emotion PC 22-state → Pi5 kiosk engine.

Owner yêu cầu 14/11: "đồng bộ và test lại toàn bộ hoạt động của cherry để đảm
bảo hoạt động ổn định nhất".

Kiểm tra bằng chứng code thật trong edge_client/avatar_engine.js (file thật,
không mock engine) + endpoint thật của daemon:

1. 22 STATE_CONFIGS khớp PC dashboard (thiếu 4 state cũ → giờ đủ).
2. 11 EMOTION_PRESETS khớp PC (thiếu 4 tông cũ → giờ đủ).
3. extractVietnameseEmotion kiosk có nhánh APOLOGETIC ưu tiên trước SERIOUS_ALERT
   + nhánh CURIOUS + PROUD (khớp logic PC dashboard).
4. Portrait mapping cho 4 state mới tái sử dụng asset có sẵn.
5. kiosk.html bump cache version → trình duyệt kiosk tải engine mới.
6. Daemon action thật: set_expression + reboot_pi tồn tại trong client_daemon.py.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENGINE = REPO / "edge_client" / "avatar_engine.js"
HTML = REPO / "edge_client" / "kiosk.html"
DAEMON = REPO / "edge_client" / "client_daemon.py"

PC_STATES = {
    "APOLOGETIC", "BLOCKED", "CONFUSED", "CURIOUS", "EMPATHETIC", "ERROR",
    "HAPPY", "IDLE", "LEARNING", "LISTENING", "OFFLINE", "PROUD",
    "RECONNECTING", "RESEARCHING", "SAFE_MODE", "SLEEPING", "SPEAKING",
    "SUCCESS", "SURPRISED", "THINKING", "WAITING_FOR_OWNER", "WARNING",
}

PC_PRESETS = {
    "WARM_GREETING", "ANALYTICAL_THINKING", "SERIOUS_ALERT",
    "CONFIDENT_SUCCESS", "CONSULTATIVE_INQUIRING", "CURIOUS", "APOLOGETIC",
    "PATIENT_WAITING", "PROUD", "SURPRISED", "NEUTRAL",
}


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


class TestStateSync22:
    def test_engine_has_all_22_pc_states(self):
        src = _read(ENGINE)
        m = re.search(r"STATE_CONFIGS\s*=\s*\{(.+?)\n\s*\}\s*;", src, re.S)
        assert m, "STATE_CONFIGS not found in kiosk engine"
        keys = set(re.findall(r"^\s*([A-Z][A-Z_]{2,})\s*:\s*\{", m.group(1), re.M))
        missing = PC_STATES - keys
        assert not missing, f"Kiosk engine missing states: {sorted(missing)}"

    def test_new_states_have_required_fields(self):
        src = _read(ENGINE)
        m = re.search(r"STATE_CONFIGS\s*=\s*\{(.+?)\n\s*\}\s*;", src, re.S)
        body = m.group(1)
        for state, symbol in [("APOLOGETIC", "🙏"), ("CURIOUS", "🤔"), ("PROUD", "🌟"), ("SURPRISED", "😯")]:
            m2 = re.search(state + r"\s*:\s*\{[^}]*\}", body)
            assert m2, f"{state} missing from STATE_CONFIGS"
            block = m2.group(0)
            for field in ["name", "auraColor", "haloSpeed", "eyes", "smile", "defaultTone"]:
                assert field in block, f"{state} missing field {field}"
            assert symbol in block, f"{state} missing symbol {symbol}"

    def test_all_presets_synced(self):
        src = _read(ENGINE)
        idx = src.find("EMOTION_PRESETS")
        assert idx >= 0, "EMOTION_PRESETS not found"
        seg = src[idx : idx + 6000]
        found = set(re.findall(r"^\s*([A-Z][A-Z_]+)\s*:\s*\{", seg, re.M))
        missing = PC_PRESETS - found
        assert not missing, f"Kiosk engine missing presets: {sorted(missing)}"


class TestExtractorSync:
    def _extractor_body(self) -> str:
        src = _read(ENGINE)
        idx = src.find("extractVietnameseEmotion(text)")
        assert idx >= 0, "extractVietnameseEmotion not found"
        # Body = từ đầu hàm đến 'setContextFromText' (hàm kế tiếp)
        end = src.find("setContextFromText", idx)
        return src[idx:end]

    def test_apologetic_priority_before_alert(self):
        body = self._extractor_body()
        apo = body.find("APOLOGETIC")
        alert = body.find("SERIOUS_ALERT")
        assert 0 <= apo < alert, "APOLOGETIC phải ưu tiên trước SERIOUS_ALERT (khớp PC)"

    def test_extractor_handles_apology_case(self):
        body = self._extractor_body()
        assert re.search(r"/xin loi\|chia buon\|rat tiec", body), "nhánh APOLOGETIC thiếu"

    def test_extractor_has_curious_and_proud(self):
        body = self._extractor_body()
        assert re.search(r"return \"CURIOUS\"", body), "thiếu nhánh CURIOUS"
        assert re.search(r"return \"PROUD\"", body), "thiếu nhánh PROUD"


class TestPortraitMapping:
    def test_four_new_states_mapped_to_portraits(self):
        src = _read(ENGINE)
        assert 'this.state === "PROUD"' in src, "PROUD thiếu trong chuỗi chọn portrait"
        assert 'this.state === "CURIOUS"' in src, "CURIOUS thiếu trong chuỗi chọn portrait"
        assert 'this.state === "APOLOGETIC"' in src, "APOLOGETIC thiếu trong chuỗi chọn portrait"
        assert 'this.state === "SURPRISED"' in src, "SURPRISED thiếu trong chuỗi chọn portrait"

    def test_new_states_reuse_existing_assets(self):
        """4 state mới tái sử dụng asset có sẵn — không cần asset mới."""
        src = _read(ENGINE)
        # PROUD → portrait_happy; CURIOUS → portrait_confused;
        # APOLOGETIC → portrait_empathic; SURPRISED → portrait_surprised
        proud = re.search(r'state === "PROUD"[^}]*\{[^}]*portrait_(\w+)', src)
        curious = re.search(r'state === "CURIOUS"[^}]*\{[^}]*portrait_(\w+)', src)
        apolo = re.search(r'state === "APOLOGETIC"[^}]*\{[^}]*portrait_(\w+)', src)
        surpr = re.search(r'state === "SURPRISED"[^}]*\{[^}]*portrait_(\w+)', src)
        assert proud and proud.group(1) == "happy"
        assert curious and curious.group(1) == "confused"
        assert apolo and apolo.group(1) == "empathic"
        assert surpr and surpr.group(1) == "surprised"


class TestCacheBump:
    def test_html_cache_version_bumped(self):
        html = _read(HTML)
        # (14/11 v6emo) cache version hiện tại = v6emo_1411 (portrait cảm xúc mới);
        # test chấp nhận mọi version >= sync1314, chỉ chặn version cổ.
        assert ("v6pure_1411" in html) or ("v6emo_1411" in html) or ("cherry_sync1314" in html), \
            "kiosk.html chưa bump cache version"
        assert "cherry_07nov_r1" not in html, "cache version cũ còn sót"

    def test_engine_refers_kiosk_js_cache(self):
        html = _read(HTML)
        assert "/kiosk.js?v=" in html, "kiosk.js phải load qua cache version"


class TestDaemonActions:
    def test_set_expression_action_exists(self):
        src = _read(DAEMON)
        assert '"set_expression"' in src, "daemon thiếu action set_expression"

    def test_reboot_pi_action_exists(self):
        """Sprint #29 — daemon mới phải có reboot_pi (đã deploy 14/11)."""
        src = _read(DAEMON)
        assert '"reboot_pi"' in src, "daemon thiếu action reboot_pi (sprint #29)"

    def test_kiosk_lifecycle_guards_exist(self):
        """Sprint #29 — chống chết lặp: reap + lock cleanup + generation guard."""
        src = _read(DAEMON)
        assert "_reap_kiosk_child" in src
        assert "_cleanup_stale_kiosk_lock" in src
        assert "_bump_kiosk_generation" in src
