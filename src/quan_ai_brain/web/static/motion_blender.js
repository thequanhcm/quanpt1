/*!
 * CHERRY MOTION BLENDER — Sprint V7-M5 (18/11/2026)
 * =========================================================================
 * Chuyển state mượt giữa emotion (IDLE → HAPPY → SPEAKING → ...) bằng
 * tween 200-900ms với easing. Đây là module "thể thống nhất" — KHI 1 bộ
 * phận đổi thì các bộ phận khác chuyển theo cùng 1 timing.
 *
 * Ví dụ:
 *   - Từ IDLE sang HAPPY: 600ms ease-out, miệng mỉm cười + brow lift + body
 *     sway tăng đồng bộ
 *   - Từ HAPPY về IDLE: 800ms ease-in (chậm dần)
 *   - Từ SPEAKING về LISTENING: 400ms (nhanh vì cảm xúc liên tục)
 *
 * Fail-open: nếu thiếu physics → dùng linear.
 *
 * Xuất global: window.CherryMotionBlender = {
 *   create, blendTo, tick, getCurrent, getBlendState, VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "v7m5_1811";

  // Default durations (ms) — fail-honest có thể override
  var DEFAULT_DURATION_MS = 600;
  var DURATION_BY_FROM_TO = {
    // Từ SPEAKING → các state khác: NHANH (cảm xúc liên tục)
    "SPEAKING>IDLE": 300,
    "SPEAKING>LISTENING": 300,
    "SPEAKING>THINKING": 350,
    "SPEAKING>HAPPY": 250,
    "SPEAKING>SURPRISED": 200,
    "SPEAKING>WARNING": 200,
    "SPEAKING>EMPATHETIC": 300,
    "SPEAKING>SLEEPING": 1500,
    // Từ IDLE → emotion: VỪA (600ms)
    "IDLE>HAPPY": 600,
    "IDLE>SURPRISED": 350,
    "IDLE>WARNING": 400,
    "IDLE>EMPATHETIC": 600,
    "IDLE>THINKING": 500,
    "IDLE>LISTENING": 400,
    "IDLE>SLEEPING": 2000,
    "IDLE>SPEAKING": 400,
    // Sleep wake-up
    "SLEEPING>IDLE": 1500
  };

  function MotionBlender(opts) {
    opts = opts || {};
    this._physics = opts.physics || global.CherryPhysics;
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });

    // Current state
    this._cur = this._defaultState();
    this._from = this._defaultState();
    this._to = this._defaultState();
    this._blend_t = 1;  // 0..1
    this._blend_start = 0;
    this._blend_dur = 0;
    this._blend_easing = "ease-out";
    this._blend_from_state = "IDLE";
    this._blend_to_state = "IDLE";
    this._blend_active = false;
  }

  MotionBlender.prototype._defaultState = function () {
    return {
      smile: 0.30, brow: 0.0, browL: 0.0, browR: 0.0,
      mouthOpen: 0.0, jawDrop: 0.0, lipSpread: 0.0,
      headYaw: 0.0, headPitch: 0.0, headRoll: 0.0,
      bodyLeanX: 0.0, bodyLeanY: 0.0,
      bodySwayX: 0.0, bodySwayY: 0.0,
      armLeft: 0.0, armRight: 0.0,
      gazeX: 0.0, gazeY: 0.0, blink: 0.0
    };
  };

  MotionBlender.prototype._emotionToState = function (emotion) {
    // Map emotion string → state vector
    var s = this._defaultState();
    switch (emotion) {
      case "IDLE": break;  // giữ default
      case "LISTENING":
        s.bodyLeanX = 0.1; s.bodyLeanY = 0.05;
        s.bodySwayX = 0.2; s.bodySwayY = 0.15; break;
      case "THINKING":
        s.brow = -0.45; s.bodyLeanX = -0.15;
        s.bodySwayX = 0.1; break;
      case "HAPPY":
        s.smile = 0.85; s.brow = 0.35; s.mouthOpen = 0.10;
        s.bodyLeanX = 0.05; s.bodySwayX = 0.5; s.bodySwayY = 0.4; break;
      case "EMPATHETIC":
        s.smile = 0.15; s.brow = -0.30; s.mouthOpen = 0.05;
        s.bodyLeanX = 0.05; s.bodyLeanY = 0.05;
        s.bodySwayX = 0.25; break;
      case "WARNING":
        s.smile = -0.55; s.brow = -0.70; break;
      case "SURPRISED":
        s.smile = 0.05; s.brow = 0.80; s.mouthOpen = 0.45;
        s.bodyLeanY = -0.2; s.bodySwayX = 0.6; break;
      case "SPEAKING":
        s.mouthOpen = 0.5;  // miệng mở vừa (driver sẽ tinh chỉnh)
        s.bodySwayX = 0.3; s.bodySwayY = 0.2; break;
      case "SLEEPING":
        s.bodyLeanY = 0.2; s.bodySwayX = 0.05; s.bodySwayY = 0.05;
        s.headPitch = 5.0; break;
      case "ERROR":
        s.brow = -0.40; s.mouthOpen = 0.10; s.bodyLeanY = 0.1; break;
      case "OFFLINE":
        // Đứng yên
        break;
      default:
        // unknown → IDLE
        break;
    }
    return s;
  };

  MotionBlender.prototype.blendTo = function (emotion, opts) {
    opts = opts || {};
    // Capture current state (đã qua blending cũ) làm FROM mới
    this._from = Object.assign({}, this._cur);
    this._to = this._emotionToState(emotion);
    this._blend_from_state = this._blend_to_state || "IDLE";
    this._blend_to_state = emotion;

    // Duration
    var key = this._blend_from_state + ">" + emotion;
    if (typeof opts.duration_ms === "number") {
      this._blend_dur = opts.duration_ms;
    } else if (DURATION_BY_FROM_TO[key] != null) {
      this._blend_dur = DURATION_BY_FROM_TO[key];
    } else {
      this._blend_dur = DEFAULT_DURATION_MS;
    }

    // Easing
    this._blend_easing = opts.easing || "ease-out";
    this._blend_start = this._nowFn();
    this._blend_t = 0;
    this._blend_active = true;
  };

  MotionBlender.prototype.tick = function (dt) {
    var now = this._nowFn();
    if (!this._blend_active) {
      return this._cur;
    }
    if (typeof dt === "number" && dt > 0) {
      this._blend_t += dt / (this._blend_dur / 1000);
    } else {
      this._blend_t = (now - this._blend_start) / this._blend_dur;
    }
    if (this._blend_t >= 1) {
      this._blend_t = 1;
      this._blend_active = false;
      this._cur = Object.assign({}, this._to);
      return this._cur;
    }

    // Tween
    var phy = this._physics;
    var eased_t = phy && phy.applyEasing
      ? phy.applyEasing(this._blend_t, this._blend_easing)
      : this._blend_t;

    for (var k in this._to) {
      if (this._cur.hasOwnProperty(k) && this._from.hasOwnProperty(k)) {
        this._cur[k] = this._from[k] + (this._to[k] - this._from[k]) * eased_t;
      }
    }
    return this._cur;
  };

  MotionBlender.prototype.getCurrent = function () {
    return Object.assign({}, this._cur);
  };

  MotionBlender.prototype.getBlendState = function () {
    return {
      from: this._blend_from_state,
      to: this._blend_to_state,
      t: this._blend_t,
      active: this._blend_active,
      duration_ms: this._blend_dur,
      easing: this._blend_easing
    };
  };

  MotionBlender.prototype.reset = function () {
    this._cur = this._defaultState();
    this._from = this._defaultState();
    this._to = this._defaultState();
    this._blend_active = false;
    this._blend_t = 0;
    this._blend_to_state = "IDLE";
  };

  MotionBlender.VERSION = VERSION;
  MotionBlender.DEFAULT_DURATION_MS = DEFAULT_DURATION_MS;
  MotionBlender.DURATION_BY_FROM_TO = DURATION_BY_FROM_TO;

  var api = {
    VERSION: VERSION,
    create: function (opts) { return new MotionBlender(opts); },
    DEFAULT_DURATION_MS: DEFAULT_DURATION_MS,
    DURATION_BY_FROM_TO: DURATION_BY_FROM_TO
  };

  if (typeof global !== "undefined") {
    global.CherryMotionBlender = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
