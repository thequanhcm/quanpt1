/*!
 * CHERRY HEAD DYNAMICS — Sprint V7-M1 (18/11/2026)
 * =========================================================================
 * Quán tính đầu (yaw/pitch/roll) + breathing sway. Dựa trên motion
 * profile đo được từ Cherry final.mp4 (MC talking-head):
 *   - Đầu nghiêng/gật ±2-5° liên tục với nhịp 2-4s
 *   - Quán tính 80-200ms (đầu người có moment quán tính)
 *   - Biên độ ±5°, không bao giờ > 8° trong MC chuyên nghiệp
 *
 * Module này ĐỌC motion heartbeat (yaw/pitch/roll targets) + APPLY
 * physics damping + angular inertia. KHÔNG tự quyết định target.
 *
 * Fail-open: nếu thiếu CherryPhysics → trả target thẳng (no smoothing).
 *
 * Xuất global: window.CherryHeadDynamics = {
 *   create, update, getPose, reset, VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "v7m1_1811";

  // Biên độ tối đa (degree) — fail-honest guard
  var YAW_MAX = 8.0;
  var PITCH_MAX = 6.0;
  var ROLL_MAX = 4.0;

  // Damping alpha — cao → mượt hơn (chuẩn MC: 0.12-0.18)
  var DEFAULT_DAMP = 0.16;

  function HeadDynamics(opts) {
    opts = opts || {};
    this._physics = opts.physics || (global.CherryPhysics);
    this._damp = opts.damp == null ? DEFAULT_DAMP : opts.damp;
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });

    // Trạng thái hiện tại (đã qua damping)
    this._cur = { yaw: 0, pitch: 0, roll: 0 };
    // Target (motion heartbeat đặt vào)
    this._target = { yaw: 0, pitch: 0, roll: 0 };
    this._lastTick = null;
    this._velocity = { yaw: 0, pitch: 0, roll: 0 };

    // Breathing: ngực nhô 12-18 lần/phút (chuẩn sinh lý)
    this._breath_rate_hz = 0.27;  // ~16 lần/phút (calm MC)
    this._breath_amp = 0.5;       // đơn vị: degree pitch, không đáng kể
    this._t = 0;
  }

  HeadDynamics.prototype.setTarget = function (yaw, pitch, roll) {
    this._target.yaw = clamp(yaw || 0, -YAW_MAX, YAW_MAX);
    this._target.pitch = clamp(pitch || 0, -PITCH_MAX, PITCH_MAX);
    this._target.roll = clamp(roll || 0, -ROLL_MAX, ROLL_MAX);
  };

  HeadDynamics.prototype.update = function (dt) {
    if (typeof dt !== "number" || dt <= 0) {
      var now = this._nowFn();
      dt = (now - this._lastTick) / 1000;
      this._lastTick = now;
    }
    dt = Math.min(dt, 0.1);  // cap 100ms để tránh lag spike

    var phy = this._physics;

    if (phy && phy.angularIntertia && phy.damp) {
      // Angular inertia cho từng trục — quán tính bậc 2
      this._cur.yaw = phy.angularIntertia(this._cur.yaw, this._target.yaw, dt, 0.15);
      this._cur.pitch = phy.angularIntertia(this._cur.pitch, this._target.pitch, dt, 0.13);
      this._cur.roll = phy.damp(this._cur.roll, this._target.roll, 0.18, dt);
    } else {
      // Fail-open: trả target thẳng
      this._cur.yaw = this._target.yaw;
      this._cur.pitch = this._target.pitch;
      this._cur.roll = this._target.roll;
    }

    // Thêm breathing sway (rất nhỏ, ~0.3° pitch)
    this._t += dt;
    var breath = Math.sin(this._t * this._breath_rate_hz * Math.PI * 2) * this._breath_amp * 0.3;
    this._cur.pitch += breath;

    // Jitter ngẫu nhiên (MC không bao giờ đứng yên)
    if (phy && phy.jitter) {
      this._cur.yaw += phy.jitter(0.08);
      this._cur.pitch += phy.jitter(0.05);
      this._cur.roll += phy.jitter(0.03);
    }

    return this._cur;
  };

  HeadDynamics.prototype.getPose = function () {
    return {
      yaw: this._cur.yaw,
      pitch: this._cur.pitch,
      roll: this._cur.roll,
      breath_rate_hz: this._breath_rate_hz
    };
  };

  HeadDynamics.prototype.reset = function () {
    this._cur.yaw = 0; this._cur.pitch = 0; this._cur.roll = 0;
    this._target.yaw = 0; this._target.pitch = 0; this._target.roll = 0;
    this._velocity.yaw = 0; this._velocity.pitch = 0; this._velocity.roll = 0;
    this._t = 0;
    this._lastTick = null;
  };

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  HeadDynamics.VERSION = VERSION;

  var api = {
    VERSION: VERSION,
    create: function (opts) { return new HeadDynamics(opts); },
    YAW_MAX: YAW_MAX, PITCH_MAX: PITCH_MAX, ROLL_MAX: ROLL_MAX
  };

  if (typeof global !== "undefined") {
    global.CherryHeadDynamics = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
