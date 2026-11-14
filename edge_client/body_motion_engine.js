/*
 * CHERRY BODY MOTION ENGINE — Sprint 6: Body Motion Engine (14/11/2026)
 * =========================================================================
 * Nguồn sự thật DUY NHẤT cho body motion human-like: shoulder sway + body lean
 * + breathing + arm reach + speech sync. Dùng chung PC + Pi5.
 *
 * Nguồn thiết kế: CHERRY_EMBODIMENT_SPRINT_PLAN.md §8 (Performance) — thay
 * bằng Body Motion Engine theo yêu cầu owner "hình thể linh hoạt uyển chuyển".
 *
 * Xuất global: window.CherryBodyMotionEngine = {
 *   BodyMotionEngine, BODY_PRESETS, BREATH_PRESETS, ARM_REACH_PRESETS,
 *   VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "s6_1411";

  /* ================================================================
   * 1. BODY_PRESETS — body lean + sway theo state (degrees)
   *    leanX: nghiêng trái/phải (-1..1, đơn vị tỉ lệ)
   *    leanY: nghiêng trước/sau (-1..1)
   *    swayX: sway ngang (-1..1)
   *    swayY: sway dọc (-1..1)
   * ================================================================ */
  var BODY_PRESETS = {
    IDLE: { leanX: 0, leanY: 0, swayX: 0.3, swayY: 0.2 },
    LISTENING: { leanX: 0.1, leanY: 0.05, swayX: 0.2, swayY: 0.15 },
    THINKING: { leanX: -0.15, leanY: 0, swayX: 0.1, swayY: 0.1 },
    ANALYTICAL_THINKING: { leanX: -0.1, leanY: 0, swayX: 0.15, swayY: 0.1 },
    CURIOUS: { leanX: 0.2, leanY: 0, swayX: 0.25, swayY: 0.15 },
    WARM_GREETING: { leanX: 0.1, leanY: 0.1, swayX: 0.4, swayY: 0.3 },
    HAPPY: { leanX: 0.05, leanY: 0, swayX: 0.5, swayY: 0.4 },
    PROUD: { leanX: 0, leanY: -0.1, swayX: 0.3, swayY: 0.2 },
    CONFIDENT_SUCCESS: { leanX: 0, leanY: -0.15, swayX: 0.35, swayY: 0.25 },
    SURPRISED: { leanX: 0, leanY: -0.2, swayX: 0.6, swayY: 0.5 },
    WARNING: { leanX: 0, leanY: 0, swayX: 0.2, swayY: 0.15 },
    SERIOUS_ALERT: { leanX: 0, leanY: 0, swayX: 0.1, swayY: 0.1 },
    APOLOGETIC: { leanX: -0.1, leanY: 0.15, swayX: 0.15, swayY: 0.1 },
    EMPATHETIC: { leanX: 0.05, leanY: 0.05, swayX: 0.25, swayY: 0.2 },
    CONSULTATIVE_INQUIRING: { leanX: 0.1, leanY: 0, swayX: 0.2, swayY: 0.15 },
    SPEAKING: { leanX: 0, leanY: 0, swayX: 0.3, swayY: 0.2 },
    ERROR: { leanX: 0, leanY: 0.1, swayX: 0.15, swayY: 0.1 },
    SLEEPING: { leanX: 0, leanY: 0.2, swayX: 0.05, swayY: 0.05 },
    OFFLINE: { leanX: 0, leanY: 0, swayX: 0, swayY: 0 },
    RECONNECTING: { leanX: 0, leanY: 0, swayX: 0.1, swayY: 0.1 },
    NEUTRAL: { leanX: 0, leanY: 0, swayX: 0.2, swayY: 0.15 }
  };

  /* ================================================================
   * 2. BREATH_PRESETS — nhịp thở theo state (Hz, amplitude)
   *    rate: chu kỳ thở (giây/vòng)
   *    amplitude: biên độ (0..1)
   * ================================================================ */
  var BREATH_PRESETS = {
    IDLE: { rate: 4.0, amplitude: 0.3 },
    LISTENING: { rate: 3.5, amplitude: 0.25 },
    THINKING: { rate: 5.0, amplitude: 0.2 },
    SPEAKING: { rate: 3.0, amplitude: 0.4 },
    SLEEPING: { rate: 6.0, amplitude: 0.5 },
    default: { rate: 4.0, amplitude: 0.3 }
  };

  /* ================================================================
   * 3. ARM_REACH_PRESETS — với tay theo state (degrees, 0 = thẳng xuống)
   *    leftArm: góc tay trái (degrees, 0 = thẳng xuống, + = ra trước)
   *    rightArm: góc tay phải
   *    leftReach: độ vươn tay trái (0..1)
   *    rightReach: độ vươn tay phải (0..1)
   * ================================================================ */
  var ARM_REACH_PRESETS = {
    IDLE: { leftArm: 0, rightArm: 0, leftReach: 0.3, rightReach: 0.3 },
    LISTENING: { leftArm: 5, rightArm: 5, leftReach: 0.4, rightReach: 0.4 },
    SPEAKING: { leftArm: 15, rightArm: 15, leftReach: 0.6, rightReach: 0.6 },
    WARM_GREETING: { leftArm: 30, rightArm: 30, leftReach: 0.7, rightReach: 0.7 },
    HAPPY: { leftArm: 25, rightArm: 25, leftReach: 0.6, rightReach: 0.6 },
    PROUD: { leftArm: 10, rightArm: 10, leftReach: 0.5, rightReach: 0.5 },
    SURPRISED: { leftArm: 45, rightArm: 45, leftReach: 0.8, rightReach: 0.8 },
    APOLOGETIC: { leftArm: -10, rightArm: -10, leftReach: 0.2, rightReach: 0.2 },
    default: { leftArm: 0, rightArm: 0, leftReach: 0.3, rightReach: 0.3 }
  };

  /* ================================================================
   * 4. BodyMotionEngine — máy trạng thái body motion
   *    tick(now, opts): cập nhật sway/lean/breath/arm theo state + speech
   *    setState(state): đổi state → áp preset
   *    setSpeaking(bool): đang nói → tăng sway + arm reach
   *    getTransform(): trả { leanX, leanY, swayX, swayY, breathOffset,
   *                          leftArm, rightArm, leftReach, rightReach }
   * ================================================================ */
  function BodyMotionEngine(opts) {
    opts = opts || {};
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });
    this._state = "IDLE";
    this._speaking = false;
    this._speechEnergy = 0; // 0..1, từ audio mouth driver
    this._current = {
      leanX: 0, leanY: 0, swayX: 0, swayY: 0,
      breathOffset: 0,
      leftArm: 0, rightArm: 0, leftReach: 0.3, rightReach: 0.3
    };
    this._target = Object.assign({}, this._current);
    this._lastTick = 0;
    this._log = [];
    this._maxLog = 16;
  }

  BodyMotionEngine.prototype._pushLog = function (entry) {
    this._log.push(entry);
    if (this._log.length > this._maxLog) this._log.shift();
  };

  BodyMotionEngine.prototype.getLog = function () {
    return this._log.slice();
  };

  BodyMotionEngine.prototype.getTransform = function () {
    return Object.assign({}, this._current);
  };

  BodyMotionEngine.prototype.setState = function (state) {
    if (this._state === state) return;
    this._state = state;
    var body = BODY_PRESETS[state] || BODY_PRESETS.IDLE;
    var arm = ARM_REACH_PRESETS[state] || ARM_REACH_PRESETS.default;
    this._target.leanX = body.leanX;
    this._target.leanY = body.leanY;
    this._target.swayX = body.swayX;
    this._target.swayY = body.swayY;
    this._target.leftArm = arm.leftArm;
    this._target.rightArm = arm.rightArm;
    this._target.leftReach = arm.leftReach;
    this._target.rightReach = arm.rightReach;
    this._pushLog({ t: this._nowFn(), kind: "state", state: state });
  };

  BodyMotionEngine.prototype.setSpeaking = function (speaking) {
    this._speaking = !!speaking;
  };

  BodyMotionEngine.prototype.setSpeechEnergy = function (energy) {
    this._speechEnergy = Math.max(0, Math.min(1, energy || 0));
  };

  /* tick — gọi mỗi frame; cập nhật sway oscillation + breath + lerp */
  BodyMotionEngine.prototype.tick = function (nowMs) {
    var now = nowMs != null ? nowMs : this._nowFn();
    var dt = this._lastTick ? (now - this._lastTick) : 16;
    this._lastTick = now;

    // 1. Breath oscillation (sin wave theo rate)
    var breath = BREATH_PRESETS[this._state] || BREATH_PRESETS.default;
    var breathPhase = (now / 1000) * (2 * Math.PI / breath.rate);
    var breathOffset = Math.sin(breathPhase) * breath.amplitude;

    // 2. Sway oscillation (lerp toward target + sin wave)
    var swayPhase = (now / 1000) * 1.2; // 1.2 Hz sway
    var swayX = this._target.swayX * (0.7 + 0.3 * Math.sin(swayPhase));
    var swayY = this._target.swayY * (0.7 + 0.3 * Math.cos(swayPhase * 0.8));

    // 3. Speaking boost: tăng sway + arm reach khi đang nói
    if (this._speaking) {
      var speechBoost = 1 + this._speechEnergy * 0.5;
      swayX *= speechBoost;
      swayY *= speechBoost;
      this._target.leftArm = Math.min(60, this._target.leftArm + 10 * this._speechEnergy);
      this._target.rightArm = Math.min(60, this._target.rightArm + 10 * this._speechEnergy);
      this._target.leftReach = Math.min(1, this._target.leftReach + 0.2 * this._speechEnergy);
      this._target.rightReach = Math.min(1, this._target.rightReach + 0.2 * this._speechEnergy);
    }

    // 4. Lerp current toward target (smooth)
    var lerpFactor = Math.min(1, dt / 100);
    this._current.leanX = lerp(this._current.leanX, this._target.leanX, lerpFactor);
    this._current.leanY = lerp(this._current.leanY, this._target.leanY, lerpFactor);
    this._current.swayX = swayX;
    this._current.swayY = swayY;
    this._current.breathOffset = breathOffset;
    this._current.leftArm = lerp(this._current.leftArm, this._target.leftArm, lerpFactor);
    this._current.rightArm = lerp(this._current.rightArm, this._target.rightArm, lerpFactor);
    this._current.leftReach = lerp(this._current.leftReach, this._target.leftReach, lerpFactor);
    this._current.rightReach = lerp(this._current.rightReach, this._target.rightReach, lerpFactor);

    return this.getTransform();
  };

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  /* Export */
  global.CherryBodyMotionEngine = {
    VERSION: VERSION,
    BODY_PRESETS: BODY_PRESETS,
    BREATH_PRESETS: BREATH_PRESETS,
    ARM_REACH_PRESETS: ARM_REACH_PRESETS,
    BodyMotionEngine: BodyMotionEngine
  };

})(typeof window !== "undefined" ? window : this);
