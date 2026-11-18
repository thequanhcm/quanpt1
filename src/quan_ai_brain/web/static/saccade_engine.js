/*!
 * CHERRY SACCADE ENGINE — Sprint V7-M3 (18/11/2026)
 * =========================================================================
 * Chuyển động mắt ngẫu nhiên + chớp mắt sinh học. Dựa trên motion
 * profile đo được từ Cherry final.mp4:
 *   - approx_blink_rate_per_min = 17 → trung bình ~3.5s/blink
 *   - Saccade: tần suất 2-4 Hz (random look-around)
 *   - Biên độ: ±5° từ gaze chính, không bao giờ > 10° (tránh mắt trợn)
 *
 * KHÔNG track người dùng (không có camera). Mọi chuyển động là random
 * có TLB để không nhận ra pattern.
 *
 * Fail-open: nếu thiếu physics → trả gaze = center.
 *
 * Xuất global: window.CherrySaccadeEngine = {
 *   create, tick, getGaze, blinkNow, VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "v7m3_1811";

  // Blink: profile thực 2.5-6s (TLB chống robot)
  var BLINK_MIN_MS = 2500;
  var BLINK_MAX_MS = 6000;

  // Saccade: 2-4 Hz, biên độ ±5°
  var SACCADE_HZ_MIN = 2;
  var SACCADE_HZ_MAX = 4;
  var SACCADE_AMP_MAX = 5.0;  // degree

  // Gaze center có thể override (khi nói với user → look at camera)
  function SaccadeEngine(opts) {
    opts = opts || {};
    this._physics = opts.physics || global.CherryPhysics;
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });

    // Gaze: hướng mắt hiện tại (degree từ tâm)
    this._gaze = { x: 0, y: 0 };
    this._gaze_target = { x: 0, y: 0 };
    this._next_saccade = 0;
    this._saccade_duration = 80;  // ms

    // Blink state
    this._blink_progress = 0;  // 0..1 (1 = đang nhắm)
    this._blink_target = 0;    // 0 hoặc 1
    this._blink_speed = 14;    // giây⁻¹ khi đổi state
    this._next_blink = 0;
    this._blink_registry = {};

    // Override gaze (vd khi "nói chuyện" → look at camera)
    this._gaze_override = null;

    this._last_tick = 0;
    this._t = 0;
  }

  SaccadeEngine.prototype.setGazeOverride = function (x, y) {
    // null = không override
    if (x == null || y == null) {
      this._gaze_override = null;
    } else {
      this._gaze_override = { x: x, y: y };
    }
  };

  SaccadeEngine.prototype.blinkNow = function () {
    this._blink_target = 1;
  };

  SaccadeEngine.prototype.tick = function (dt) {
    var now = this._nowFn();
    if (typeof dt !== "number" || dt <= 0) {
      dt = this._last_tick ? (now - this._last_tick) / 1000 : 0.016;
    }
    dt = Math.min(dt, 0.1);
    this._last_tick = now;
    this._t += dt;

    // ====== SACCADE ======
    if (this._gaze_override) {
      this._gaze_target.x = this._gaze_override.x;
      this._gaze_target.y = this._gaze_override.y;
    } else {
      if (now >= this._next_saccade) {
        // Random saccade: 2-4 Hz → period 250-500ms
        var hz = SACCADE_HZ_MIN + Math.random() * (SACCADE_HZ_MAX - SACCADE_HZ_MIN);
        this._next_saccade = now + (1000 / hz);
        // Biên độ: phân bố Gaussian hẹp (ít khi ra xa tâm)
        var ang = Math.random() * Math.PI * 2;
        var r = Math.sqrt(Math.random()) * SACCADE_AMP_MAX;
        this._gaze_target.x = Math.cos(ang) * r;
        this._gaze_target.y = Math.sin(ang) * r * 0.6;  // ít lên/xuống
        // Giữ ngắn: 80ms saccade, rồi fixate ~150-300ms
        var self = this;
        setTimeout(function () {
          self._gaze_target.x *= 0.4;
          self._gaze_target.y *= 0.4;
        }, this._saccade_duration);
      }
    }

    // Smooth gaze
    if (this._physics && this._physics.damp) {
      this._gaze.x = this._physics.damp(this._gaze.x, this._gaze_target.x, 0.3, dt);
      this._gaze.y = this._physics.damp(this._gaze.y, this._gaze_target.y, 0.3, dt);
    } else {
      this._gaze.x = this._gaze.x * 0.7 + this._gaze_target.x * 0.3;
      this._gaze.y = this._gaze.y * 0.7 + this._gaze_target.y * 0.3;
    }

    // ====== BLINK ======
    if (this._next_blink === 0) {
      // Schedule first blink
      this._scheduleNextBlink();
    } else if (now >= this._next_blink && this._blink_target === 0) {
      this._blink_target = 1;
      this._scheduleNextBlink();
    }

    // Animate blink progress toward target
    var delta = this._blink_target - this._blink_progress;
    if (Math.abs(delta) > 0.01) {
      this._blink_progress += delta * this._blink_speed * dt;
      this._blink_progress = Math.max(0, Math.min(1, this._blink_progress));
    } else if (this._blink_target === 1 && this._blink_progress >= 0.99) {
      // Đã nhắm kín → mở lại sau 80ms
      var self = this;
      setTimeout(function () {
        self._blink_target = 0;
      }, 80);
    }

    return {
      gaze: { x: this._gaze.x, y: this._gaze.y },
      blink: this._blink_progress
    };
  };

  SaccadeEngine.prototype._scheduleNextBlink = function () {
    var phy = this._physics;
    if (phy && phy.nextIntervalRand) {
      this._next_blink = this._nowFn() + phy.nextIntervalRand(
        BLINK_MIN_MS, BLINK_MAX_MS, this._blink_registry);
    } else {
      this._next_blink = this._nowFn() + BLINK_MIN_MS +
        Math.random() * (BLINK_MAX_MS - BLINK_MIN_MS);
    }
  };

  SaccadeEngine.prototype.getGaze = function () {
    return { gaze: { x: this._gaze.x, y: this._gaze.y }, blink: this._blink_progress };
  };

  SaccadeEngine.prototype.reset = function () {
    this._gaze = { x: 0, y: 0 };
    this._gaze_target = { x: 0, y: 0 };
    this._next_saccade = 0;
    this._blink_progress = 0;
    this._blink_target = 0;
    this._next_blink = 0;
    this._gaze_override = null;
    this._t = 0;
    this._last_tick = 0;
  };

  SaccadeEngine.VERSION = VERSION;

  var api = {
    VERSION: VERSION,
    create: function (opts) { return new SaccadeEngine(opts); },
    BLINK_MIN_MS: BLINK_MIN_MS,
    BLINK_MAX_MS: BLINK_MAX_MS
  };

  if (typeof global !== "undefined") {
    global.CherrySaccadeEngine = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
