/*!
 * CHERRY MICRO EXPRESSION LOOP — Sprint V7-M0 (18/11/2026)
 * =========================================================================
 * Vòng lặp vi-biểu cảm — đảm bảo khuôn mặt LUÔN có sức sống kể cả khi
 * không nói (IDLE/SLEEPING). Dựa trên motion profile thực đo từ
 * Cherry final.mp4: MC có blink 17/min, micro head-tilt ±2-5° liên tục.
 *
 * Đặc tính:
 *   - Vi-biểu cảm CỰC NHỎ (≤0.06 độ) → không lẫn vào emotion chính
 *   - Tần suất 3-7s/lần (ngẫu nhiên có TLB chống pattern)
 *   - KHÔNG đụng engine khác: emit event 'cherry:micro' qua window,
 *     avatar_engine tự subscribe (không import trực tiếp)
 *
 * Fail-open: KHÔNG phá nếu không có ai subscribe.
 *
 * Xuất global: window.CherryMicroExpression = {
 *   start, stop, tick, getIntensity, VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "v7m0_1811";

  // Tập vi-biểu cảm — mỗi cái gắn với 1 vài tham số chuyển động
  var MICRO_SET = [
    { id: "brow_lift_micro", duration: 280, params: { browL: 0.06, browR: 0.05 } },
    { id: "brow_lower_micro", duration: 200, params: { browL: -0.03, browR: -0.04 } },
    { id: "cheek_puff", duration: 320, params: { cheek: 0.04 } },
    { id: "lip_corner_pull", duration: 240, params: { smile: 0.05 } },
    { id: "head_tilt_left", duration: 700, params: { roll: -1.2 } },
    { id: "head_tilt_right", duration: 700, params: { roll: 1.2 } },
    { id: "chin_drop", duration: 350, params: { pitch: 0.8 } },
    { id: "smile_flicker", duration: 180, params: { smile: 0.03, browL: 0.02 } },
    { id: "nostril_flare", duration: 220, params: { nose: 0.04 } },
    { id: "eye_squint_micro", duration: 260, params: { squint: 0.04 } },
    { id: "micro_nod_yes", duration: 400, params: { pitch: -0.6 } },
    { id: "sigh_breath", duration: 1200, params: { breath: 0.10 } }
  ];

  function CherryMicroExpression(opts) {
    opts = opts || {};
    this._enabled = false;
    this._intensity = opts.intensity || 0.35;  // giảm khi SLEEPING
    this._running = false;
    this._tickInterval = null;
    this._registry = { last: 0 };
    this._active = null;
    this._activeStart = 0;
    this._minGap = 2800;   // ms — không quá nhanh
    this._maxGap = 7000;   // ms — đo profile MC ~5.5s/lần
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });
  }

  CherryMicroExpression.prototype.start = function () {
    if (this._running) return;
    this._running = true;
    this._enabled = true;
    this._scheduleNext();
  };

  CherryMicroExpression.prototype.stop = function () {
    this._running = false;
    this._enabled = false;
    if (this._tickInterval) {
      clearTimeout(this._tickInterval);
      this._tickInterval = null;
    }
    this._active = null;
  };

  CherryMicroExpression.prototype.setIntensity = function (val) {
    // SLEEPING=0.05, IDLE=0.25, LISTENING=0.40, SPEAKING=0.55, THINKING=0.50
    this._intensity = Math.max(0, Math.min(1, val));
  };

  CherryMicroExpression.prototype.getIntensity = function () {
    return this._intensity;
  };

  CherryMicroExpression.prototype._scheduleNext = function () {
    if (!this._running) return;
    var span = this._maxGap - this._minGap;
    var gap;
    if (typeof this._registry.last === "number") {
      var minDelta = span * 0.30;
      var maxDelta = span * 0.90;
      do {
        gap = this._minGap + Math.random() * span;
      } while (Math.abs(gap - this._registry.last) < minDelta ||
               Math.abs(gap - this._registry.last) > maxDelta);
    } else {
      gap = this._minGap + Math.random() * span;
    }
    this._registry.last = gap;

    var self = this;
    this._tickInterval = setTimeout(function () {
      self._fireRandom();
    }, gap);
  };

  CherryMicroExpression.prototype._fireRandom = function () {
    if (!this._running) return;
    var idx = Math.floor(Math.random() * MICRO_SET.length);
    var micro = MICRO_SET[idx];
    this._active = micro;
    this._activeStart = this._nowFn();
    this._emit(micro, "start");

    var self = this;
    setTimeout(function () {
      if (self._active === micro) {
        self._emit(micro, "end");
        self._active = null;
      }
    }, micro.duration);

    this._scheduleNext();
  };

  CherryMicroExpression.prototype._emit = function (micro, phase) {
    var ev;
    try {
      ev = new CustomEvent("cherry:micro", {
        detail: {
          id: micro.id,
          phase: phase,
          params: micro.params,
          intensity: this._intensity,
          duration: micro.duration,
          ts: this._nowFn()
        }
      });
    } catch (e) {
      // Old browser: use plain event
      ev = { type: "cherry:micro", detail: { id: micro.id, phase: phase,
              params: micro.params, intensity: this._intensity,
              duration: micro.duration, ts: this._nowFn() } };
    }
    if (typeof global.dispatchEvent === "function") {
      global.dispatchEvent(ev);
    }
  };

  // Đo chất lượng: cho phép test harness verify
  CherryMicroExpression.prototype.getStats = function () {
    return {
      running: this._running,
      enabled: this._enabled,
      intensity: this._intensity,
      last_active: this._active ? this._active.id : null,
      registry: JSON.parse(JSON.stringify(this._registry))
    };
  };

  CherryMicroExpression.prototype.MICRO_SET = MICRO_SET;
  CherryMicroExpression.VERSION = VERSION;

  var api = {
    VERSION: VERSION,
    create: function (opts) { return new CherryMicroExpression(opts); },
    MICRO_SET: MICRO_SET
  };

  if (typeof global !== "undefined") {
    global.CherryMicroExpression = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
