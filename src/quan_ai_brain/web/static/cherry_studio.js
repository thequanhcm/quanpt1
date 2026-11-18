/* ================================================================
 * CHERRY STUDIO — khối điều khiển trên Console :8765 (17/11/2026)
 * Owner duyệt: "Studio điều khiển (4 khối A/B/C/D)"
 *
 * A. Chọn trạng thái — 23 state engine thật (setState trực tiếp PC)
 * B. Test lip-sync — viseme tiếng Việt + speak text (tái dùng speakText)
 * C. Perf profile — FPS/render_ms thật (getPerfStats) + NORMAL/LOW (M5)
 * D. Điều khiển Pi5 — set_expression + reload_ui qua core (envelope chuẩn)
 *
 * Nguyên tắc:
 * - KHÔNG nhân bản logic app.js — đi qua window.cherryStudioHooks.
 * - KHÔNG đụng engine/avatar_engine.js — chỉ gọi API công khai có sẵn.
 * - Engine là nguồn sự thật: tickStudio đọc getPerfStats() + dh.state.
 * - Fail-honest: API lỗi → hiển thị lỗi, không fake thành công.
 * ================================================================ */
(function () {
    'use strict';

    var STUDIO_STATES = [
        'IDLE', 'LISTENING', 'THINKING', 'SPEAKING', 'HAPPY', 'GREETING',
        'GOODBYE', 'EMPATHETIC', 'SERIOUS_ALERT', 'APOLOGETIC', 'PROUD',
        'SUCCESS', 'SURPRISED', 'CURIOUS', 'CONFUSED', 'DREAMY', 'SLEEPING',
        'RESEARCHING', 'LEARNING', 'WAITING_FOR_OWNER', 'SAFE_MODE',
        'BLOCKED', 'ERROR',
        // (17/11) M4b: 2 state mới cho cử chỉ tay — đồng bộ engine (commit 0c3adc7)
        'EXPLAINING',
    ];

    // 12 nguyên âm tiếng Việt — khớp VISEME_VI trong audio_mouth_driver.js
    // (shape A/E/I/O/U; open 0.25-0.75; round 0-1). UI chỉ hiển thị nhãn
    // + open_ratio thật của từng nguyên âm — driver là nguồn sự thật.
    var VISEME_VI_LABELS = [
        { key: 'a', label: 'a', open: 0.75 },
        { key: 'ă', label: 'ă', open: 0.70 },
        { key: 'â', label: 'â', open: 0.55 },
        { key: 'e', label: 'e', open: 0.55 },
        { key: 'ê', label: 'ê', open: 0.45 },
        { key: 'i', label: 'i', open: 0.25 },
        { key: 'o', label: 'o', open: 0.60 },
        { key: 'ô', label: 'ô', open: 0.50 },
        { key: 'ơ', label: 'ơ', open: 0.45 },
        { key: 'u', label: 'u', open: 0.30 },
        { key: 'ư', label: 'ư', open: 0.28 },
        { key: 'REST', label: 'REST', open: 0.0 },
    ];

    function $(id) { return document.getElementById(id); }
    function dh() { return window.digitalHuman || null; }

    function log(msg, isError) {
        var el = $('studio-log');
        if (!el) return;
        var t = new Date().toLocaleTimeString('vi-VN', { hour12: false });
        var line = document.createElement('div');
        line.className = 'studio-log-line' + (isError ? ' err' : '');
        line.textContent = '[' + t + '] ' + msg;
        el.appendChild(line);
        while (el.childElementCount > 40) el.removeChild(el.firstChild);
        el.scrollTop = el.scrollHeight;
    }

    /* ============================================================
     * Khối A — 23 chip trạng thái
     * ============================================================ */
    function renderStateChips() {
        var wrap = $('studio-state-chips');
        if (!wrap) return;
        wrap.innerHTML = '';
        STUDIO_STATES.forEach(function (s) {
            var chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'studio-chip';
            chip.setAttribute('data-state', s);
            chip.textContent = s;
            chip.addEventListener('click', function () {
                var hooks = window.cherryStudioHooks;
                var engine = dh();
                if (!engine) { log('Engine chưa khởi tạo', true); return; }
                // State lạ → engine tự normalize (protocol) hoặc về IDLE (guard).
                if (hooks && hooks.setAvatarState) hooks.setAvatarState(s);
                else engine.setState(s);
                log('setState("' + s + '") → engine state = ' + engine.state);
                markActiveChip();
            });
            wrap.appendChild(chip);
        });
    }

    function markActiveChip() {
        var engine = dh();
        var cur = engine ? engine.state : null;
        document.querySelectorAll('.studio-chip').forEach(function (c) {
            c.classList.toggle('active', c.getAttribute('data-state') === cur);
        });
    }

    /* ============================================================
     * Khối B — lip-sync test
     * ============================================================ */
    var visemeTimer = null;

    function renderVisemeChips() {
        var wrap = $('studio-viseme-chips');
        if (!wrap) return;
        wrap.innerHTML = '';
        VISEME_VI_LABELS.forEach(function (v) {
            var chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'studio-chip viseme';
            chip.textContent = v.label;
            chip.title = 'open=' + v.open;
            chip.addEventListener('click', function () {
                var engine = dh();
                if (!engine) { log('Engine chưa khởi tạo', true); return; }
                // Giữ state hiện tại, chỉ đè miệng 1s rồi về REST — KHÔNG đổi state
                // (setState SPEAKING sẽ clear scheduler + transition cảm xúc, quá mạnh
                // cho test viseme đơn). Vẽ trực tiếp qua currentOpenRatio/activeViseme.
                engine.activeViseme = (v.key === 'REST') ? 'REST' : v.key.toUpperCase();
                engine.currentOpenRatio = v.open;
                log('viseme "' + v.label + '" open=' + v.open + ' (giữ 1s)');
                if (visemeTimer) clearTimeout(visemeTimer);
                visemeTimer = setTimeout(function () {
                    engine.activeViseme = 'REST';
                    engine.currentOpenRatio = 0.0;
                }, 1000);
            });
            wrap.appendChild(chip);
        });
    }

    function wireSpeakTest() {
        var btn = $('studio-btn-speak');
        var input = $('studio-speak-text');
        if (!btn || !input) return;
        btn.addEventListener('click', function () {
            var text = (input.value || '').trim();
            if (!text) { log('Nhập câu để test TTS', true); return; }
            var hooks = window.cherryStudioHooks;
            if (!hooks || !hooks.speakText) { log('speakText chưa sẵn sàng (app.js)', true); return; }
            log('speakText("' + text.slice(0, 60) + (text.length > 60 ? '…' : '') + '")');
            hooks.speakText(text);
        });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                btn.click();
            }
        });
    }

    /* ============================================================
     * Khối C — perf profile (M5)
     * ============================================================ */
    function renderPerf() {
        var engine = dh();
        var fpsEl = $('studio-perf-fps');
        var msEl = $('studio-perf-render');
        var profEl = $('studio-perf-profile');
        if (!fpsEl || !msEl || !profEl) return;
        var stats = engine && typeof engine.getPerfStats === 'function' ? engine.getPerfStats() : null;
        fpsEl.textContent = stats && stats.fps_measured != null ? String(stats.fps_measured) : '--';
        msEl.textContent = stats && stats.render_ms_avg != null ? stats.render_ms_avg.toFixed(2) + ' ms' : '--';
        var profile = stats ? (stats.perf_profile || 'NORMAL') : 'NORMAL';
        profEl.textContent = profile;
        profEl.className = 'studio-perf-profile ' + (profile === 'LOW' ? 'low' : 'normal');
        profEl.title = 'fps_target=' + (stats ? stats.fps_target : '--');
        // Đồng bộ nút active theo profile THẬT của engine (nguồn sự thật)
        var btnN = $('studio-btn-normal');
        var btnL = $('studio-btn-low');
        if (btnN) btnN.classList.toggle('active', profile !== 'LOW');
        if (btnL) btnL.classList.toggle('active', profile === 'LOW');
    }

    function wirePerfButtons() {
        var btnN = $('studio-btn-normal');
        var btnL = $('studio-btn-low');
        [btnN, btnL].forEach(function (btn) {
            if (!btn) return;
            btn.addEventListener('click', function () {
                var engine = dh();
                if (!engine || typeof engine.setPerfProfile !== 'function') {
                    log('setPerfProfile không có (engine cũ?)', true);
                    return;
                }
                var p = btn === btnL ? 'LOW' : 'NORMAL';
                engine.setPerfProfile(p);
                log('setPerfProfile("' + p + '") — fps_target=' +
                    (engine.getPerfStats ? engine.getPerfStats().fps_target : '?'));
                renderPerf();
            });
        });
    }

    /* ============================================================
     * Khối D — điều khiển Pi5 (qua core, envelope chuẩn)
     * ============================================================ */
    function wirePi5() {
        var btnExp = $('studio-btn-pi5-apply');
        var sel = $('studio-pi5-state');
        var btnReload = $('studio-btn-pi5-reload');
        var out = $('studio-pi5-result');

        if (!sel) return;
        STUDIO_STATES.forEach(function (s) {
            var opt = document.createElement('option');
            opt.value = s;
            opt.textContent = s;
            sel.appendChild(opt);
        });
        sel.value = 'HAPPY';

        function post(action, extra) {
            var body = Object.assign({ action: action }, extra || {});
            return fetch('/api/executive/edge/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            }).then(function (r) { return r.json(); });
        }

        if (btnExp) {
            btnExp.addEventListener('click', function () {
                var state = sel.value;
                post('set_expression', { state: state, transcript: '' })
                    .then(function (data) {
                        if (data && data.success) {
                            out.textContent = 'set_expression("' + state + '") → ' + (data.state || state);
                            log('Pi5 set_expression("' + state + '") OK');
                        } else {
                            out.textContent = 'set_expression lỗi: ' + JSON.stringify(data);
                            log('Pi5 set_expression lỗi: ' + JSON.stringify(data), true);
                        }
                    })
                    .catch(function (e) {
                        out.textContent = 'Lỗi kết nối: ' + e.message;
                        log('Pi5 set_expression lỗi: ' + e.message, true);
                    });
            });
        }

        if (btnReload) {
            btnReload.addEventListener('click', function () {
                post('reload_ui')
                    .then(function (data) {
                        if (data && data.success) {
                            out.textContent = 'reload_ui → ' + (data.message || 'đã gửi');
                            log('Pi5 reload_ui OK');
                        } else {
                            out.textContent = 'reload_ui lỗi: ' + JSON.stringify(data);
                            log('Pi5 reload_ui lỗi: ' + JSON.stringify(data), true);
                        }
                    })
                    .catch(function (e) {
                        out.textContent = 'Lỗi kết nối: ' + e.message;
                        log('Pi5 reload_ui lỗi: ' + e.message, true);
                    });
            });
        }
    }

    /* ============================================================
     * Collapse + boot + tick 1s
     * ============================================================ */
    function wireCollapse() {
        var head = $('studio-head');
        var body = $('studio-body');
        if (!head || !body) return;
        head.addEventListener('click', function () {
            var open = body.classList.toggle('open');
            head.classList.toggle('open', open);
        });
    }

    function boot() {
        if (!$('studio-root')) return;  // trang không có khối studio → noop
        renderStateChips();
        renderVisemeChips();
        wireSpeakTest();
        wirePerfButtons();
        wirePi5();
        wireCollapse();
        renderPerf();
        setInterval(function () {
            renderPerf();
            markActiveChip();
        }, 1000);
        log('Cherry Studio sẵn sàng — engine: ' + (dh() ? 'OK' : 'CHƯA LOAD'));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
