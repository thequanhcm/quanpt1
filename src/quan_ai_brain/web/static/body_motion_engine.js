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

  var VERSION = "v6mot_1511";

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
    // (15/11/2026 v6mot) Đồng bộ mirror Python: seed _target từ IDLE preset
    // để oscillation có biên độ NGAY từ tick đầu. Trước đây: setState("IDLE")
    // early-return (this._state đã là "IDLE") → _target.swayX = 0 mãi → sway=0
    // ở IDLE dù preset IDLE có swayX=0.3. Production luôn chạy IDLE khi rảnh
    // → thân đứng im vô lý; mirror Python đã seed đúng, JS bị lệch.
    var _idleBody = BODY_PRESETS["IDLE"];
    var _idleArm = ARM_REACH_PRESETS["IDLE"];
    this._target.leanX = _idleBody.leanX;
    this._target.leanY = _idleBody.leanY;
    this._target.swayX = _idleBody.swayX;
    this._target.swayY = _idleBody.swayY;
    this._target.leftArm = _idleArm.leftArm;
    this._target.rightArm = _idleArm.rightArm;
    this._target.leftReach = _idleArm.leftReach;
    this._target.rightReach = _idleArm.rightReach;
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
    // (15/11/2026 v6mot — REF: 6.mp4 "English with CTM" + 3/4/5.mp4 tổng hợp).
    // 6.mp4 (người nói camera): flow thân rất nhỏ 0.3–2.3px, đứng gần im 87–98%,
    // chuyển động theo CÂU NÓI (chu kỳ đầu 1.4–4s) chứ không lắc đều. Ca sĩ
    // 3/4/5.mp4 bổ sung 2 tầng chậm 12.5s (0.08Hz) + 50s (0.02Hz). → Sway 3 tầng:
    //   slow  0.08Hz (12.5s — đổi tư thế theo câu, từ 3.mp4/4.mp4)
    //   ultra 0.02Hz (50s — sway tổng thể rất chậm, từ 5.mp4)
    //   micro 0.16Hz (6.2s — vi mô giữ lại từ v6cin, biên nhỏ)
    var slowX = this._target.swayX * (0.7 + 0.3 * Math.sin((now / 1000) * 0.08));
    var slowY = this._target.swayY * (0.7 + 0.3 * Math.cos((now / 1000) * 0.064));
    var microX = this._target.swayX * 0.12 * Math.sin((now / 1000) * 0.16);
    var microY = this._target.swayY * 0.12 * Math.cos((now / 1000) * 0.112);
    var ultraX = this._target.swayX * 0.2 * Math.sin((now / 1000) * 0.02);
    var ultraY = this._target.swayY * 0.2 * Math.cos((now / 1000) * 0.012);

    // (15/11/2026 v6mot — REF: 6.mp4) MICRO-REST: người nói camera 87–98% thời
    // gian đứng gần im (<3px), chỉ chuyển động theo câu nói. Khi speechEnergy≈0
    // (giữa 2 câu) → tắt hẳn tầng vi mô + co sway chậm còn 50%: chỉ còn thở +
    // sway rất chậm như "đậu" giữa câu. Khi nói → đủ 3 tầng + boost ở dưới.
    if (this._speechEnergy <= 0.08) {
      microX = 0; microY = 0;
      slowX *= 0.5; slowY *= 0.5;
    }

    var swayX = slowX + microX + ultraX;
    var swayY = slowY + microY + ultraY;

    // 3. Speaking boost: tăng sway + arm reach khi đang nói
    // (15/11/2026 v6mot — REF: 3.mp4 vui = torso-dominant 0.74, 4.mp4 buồn =
    // head-dominant 1.23) Tone-driven amplitude: preset đã mang "tính cách"
    // theo state (WARM_GREETING/HAPPY sway cao; SERIOUS_ALERT/APOLOGETIC thấp
    // — gần như đứng yên, đúng 4.mp4 "đầu gục, thân gần đứng").
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
/*
 * (15/11/2026 v6mot — LỊCH SỬ NHỊP SWAY)
 *   s6_1411:    1.2Hz (giật cục — đã bị thay)
 *   v6cin_1411: 0.048Hz (20.8s vi1/vi2) + 0.16Hz vi mô
 *   v6mot_1511: 0.08Hz (12.5s, 3/4.mp4) + 0.02Hz (50s, 5.mp4) + 0.16Hz vi mô
 *               + micro-rest (energy≈0 → tắt vi mô, sway ×0.5 — 6.mp4 still 87–98%)
 */
