/*!
 * CHERRY MUSCLE CONTROLLERS — Sprint V7-M4 (18/11/2026)
 * =========================================================================
 * Bộ điều khiển cơ mặt — wrap các tham số blink/brow/cheek/jaw/forehead
 * và apply từ motion_blender state vector. Tách riêng khỏi avatar_engine
 * để không đụng engine đang chạy.
 *
 * Fail-open: nếu thiếu physics → trả giá trị thẳng.
 *
 * Xuất global: window.CherryMuscleControllers = {
 *   create, update, getMuscleState, VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "v7m4_1811";

  function MuscleControllers(opts) {
    opts = opts || {};
    this._physics = opts.physics || global.CherryPhysics;
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });
    this._t = 0;
    this._lastTick = 0;

    // Muscle state hiện tại (đã smoothed)
    this._cur = {
      browL: 0.0, browR: 0.0,
      cheekL: 0.0, cheekR: 0.0,
      forehead: 0.0, nose: 0.0,
      squint: 0.0, jaw: 0.0,
      cornerPull: 0.0
    };
    this._target = Object.assign({}, this._cur);
  }

  MuscleControllers.prototype.setTarget = function (state) {
    // state: { brow, browL, browR, smile, mouthOpen, ... } từ blender
    if (state.brow != null) {
      // brow chung → áp đều 2 bên
      this._target.browL = state.brow;
      this._target.browR = state.brow;
    }
    if (state.browL != null) this._target.browL = state.browL;
    if (state.browR != null) this._target.browR = state.browR;

    // Smile → cornerPull (kéo khóe miệng)
    if (state.smile != null) {
      this._target.cornerPull = state.smile * 0.7;
      this._target.cheekL = Math.max(0, state.smile) * 0.4;
      this._target.cheekR = Math.max(0, state.smile) * 0.4;
    }

    // Mouth open → jaw + squint (khi mở to, hơi nheo mắt tự nhiên)
    if (state.mouthOpen != null) {
      this._target.jaw = state.mouthOpen * 0.8;
      if (state.mouthOpen > 0.5) {
        this._target.squint = (state.mouthOpen - 0.5) * 0.3;
      }
    }
  };

  MuscleControllers.prototype.update = function (dt) {
    var now = this._nowFn();
    if (typeof dt !== "number" || dt <= 0) {
      dt = this._lastTick ? (now - this._lastTick) / 1000 : 0.016;
    }
    dt = Math.min(dt, 0.1);
    this._last_tick = now;
    this._t += dt;

    var phy = this._physics;

    // Smooth từng muscle (chuẩn 80-150ms đáp ứng cơ mặt)
    for (var k in this._cur) {
      if (this._target.hasOwnProperty(k)) {
        if (phy && phy.damp) {
          this._cur[k] = phy.damp(this._cur[k], this._target[k], 0.18, dt);
        } else {
          this._cur[k] = this._cur[k] * 0.82 + this._target[k] * 0.18;
        }
      }
    }

    // Forehead: brow cao → nhăn trán nhẹ (proportional)
    if (phy && phy.damp) {
      this._cur.forehead = phy.damp(this._cur.forehead,
        Math.abs(this._cur.browL + this._cur.browR) * 0.5 * 0.4, 0.18, dt);
    } else {
      this._cur.forehead = this._cur.forehead * 0.82 +
        Math.abs(this._cur.browL + this._cur.browR) * 0.2;
    }

    return this._cur;
  };

  MuscleControllers.prototype.getMuscleState = function () {
    return Object.assign({}, this._cur);
  };

  MuscleControllers.prototype.reset = function () {
    this._cur = {
      browL: 0.0, browR: 0.0,
      cheekL: 0.0, cheekR: 0.0,
      forehead: 0.0, nose: 0.0,
      squint: 0.0, jaw: 0.0,
      cornerPull: 0.0
    };
    this._target = Object.assign({}, this._cur);
    this._t = 0;
    this._lastTick = 0;
  };

  MuscleControllers.VERSION = VERSION;

  var api = {
    VERSION: VERSION,
    create: function (opts) { return new MuscleControllers(opts); }
  };

  if (typeof global !== "undefined") {
    global.CherryMuscleControllers = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
