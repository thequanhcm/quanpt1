/*!
 * CHERRY PHYSICS — Sprint V7-M1 (18/11/2026)
 * =========================================================================
 * Nguồn sự thật duy nhất cho: damping (quán tính), spring (lực kéo),
 * smoothing (low-pass), và easing curves. MỌI engine khác (avatar,
 * presence, motion_scheduler, head_dynamics) chỉ được DÙNG module này
 * để làm mượt — KHÔNG tự ý nội suy.
 *
 * Lý do (motion profile từ Cherry final.mp4, MC talking-head):
 *   - Khi nói, motion 0.18/pixel + mouth_active 99% → nếu KHÔNG damping
 *     sẽ thấy giật (đo độ dừng giữa 2 frame < 16ms)
 *   - Blink cố định 2.8s dễ nhận ra → jitter ±2.5s cần dùng smoothing
 *
 * Fail-open: mọi hàm đều nhận số thực, KHÔNG throw — fallback linear.
 *
 * Xuất global: window.CherryPhysics = { damp, spring, smooth, easeInOut,
 *                                        clamp, lerp, nextIntervalRand }
 */
(function (global) {
  "use strict";

  var VERSION = "v7m1_1811";

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  /* ================================================================
   * 1. DAMPING — quán tính mượt, tham số alpha 0..1
   *    alpha = 0 → bám sát target tức thì (giật)
   *    alpha = 0.15 → quán tính tự nhiên (chuẩn sinh học, ~150ms đáp ứng)
   *    alpha = 0.05 → rất mượt, trễ 400ms (chỉ dùng cho head pose)
   * ================================================================ */
  function damp(current, target, alpha, dt) {
    // Nếu dt lớn (lag spike), scale alpha để ổn định công thức tích phân
    var a = 1 - Math.pow(1 - clamp(alpha, 0, 1), Math.max(dt, 0.001) * 60);
    return lerp(current, target, a);
  }

  /* ================================================================
   * 2. SPRING — lực kéo về target với đàn hồi (dùng cho head pose)
   *    state = { pos, vel }
   *    stiffness: 0-500 (cao = cứng, thấp = lười)
   *    damping: 0-1 (0 = dao động mãi, 1 = critical damping)
   * ================================================================ */
  function spring(state, target, dt, stiffness, damping) {
    if (!state || typeof state.pos !== "number") return target;
    var s = stiffness == null ? 180 : stiffness;
    var d = damping == null ? 18 : damping;
    var force = (target - state.pos) * s - state.vel * d;
    state.vel += force * dt;
    state.pos += state.vel * dt;
    return state.pos;
  }

  /* ================================================================
   * 3. SMOOTH — low-pass exponential, dùng cho viseme RMS, audio peak
   *    alpha = 0.4 → đáp ứng ~30ms (chuẩn audio lip-sync)
   *    alpha = 0.15 → đáp ứng ~120ms (motion thường)
   * ================================================================ */
  function smooth(current, sample, alpha) {
    return lerp(current, sample, clamp(alpha || 0.15, 0, 1));
  }

  /* ================================================================
   * 4. EASING — đầy đủ ease curves, dùng cho state transitions
   * ================================================================ */
  function easeLinear(t) { return t; }
  function easeIn(t) { return t * t; }
  function easeOut(t) { return 1 - (1 - t) * (1 - t); }
  function easeInOut(t) {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  }
  function easeCosine(t) { return 0.5 - 0.5 * Math.cos(Math.PI * t); }

  var EASING = {
    linear: easeLinear,
    "ease-in": easeIn,
    "ease-out": easeOut,
    "ease-in-out": easeInOut,
    cosine: easeCosine
  };

  function applyEasing(t, name) {
    var fn = EASING[name] || easeOut;
    return fn(clamp(t, 0, 1));
  }

  /* ================================================================
   * 5. NEXT_INTERVAL_RAND — lấy interval ngẫu nhiên có TLB (ghi nhớ
   *    để tránh burst), dùng cho blink/saccade/micro-expression.
   *    min..max là khoảng ms; lưu last ra registry.
   * ================================================================ */
  function nextIntervalRand(min, max, registry) {
    if (typeof registry !== "object") registry = {};
    var lo = Math.min(min, max);
    var hi = Math.max(min, max);
    var span = hi - lo;
    var next;
    if (typeof registry.last === "number") {
      // tránh 2 lần liên tiếp gần nhau quá (< 30% span) hoặc xa quá (> 90%)
      var minDelta = span * 0.30;
      var maxDelta = span * 0.90;
      do {
        next = lo + Math.random() * span;
      } while (Math.abs(next - registry.last) < minDelta ||
               Math.abs(next - registry.last) > maxDelta);
    } else {
      next = lo + Math.random() * span;
    }
    registry.last = next;
    return next;
  }

  /* ================================================================
   * 6. MOTION_JITTER — thêm vi-rung chuẩn người thật (Gaussian-ish,
   *    mean=0, std = amplitude). Tránh chuyển động robot.
   * ================================================================ */
  function jitter(amplitude) {
    var amp = amplitude || 0.5;
    // Box-Muller — Gaussian đơn giản
    var u1 = Math.random() || 1e-9;
    var u2 = Math.random();
    var g = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    return clamp(g * amp * 0.4, -amp, amp);
  }

  /* ================================================================
   * 7. ANGULAR_INTERTIA — quán tính góc cho đầu (yaw/pitch/roll)
   *    Khi target đổi đột ngột, đầu CHƯA tới ngay mà "treo" 80-200ms
   *    rồi mới tới — đúng chuẩn sinh học (đầu người có moment quán tính).
   * ================================================================ */
  function angularIntertia(current, target, dt, inertia) {
    // inertia = 0.15 → đáp ứng ~150ms (chuẩn MC talking-head)
    var i = inertia == null ? 0.15 : inertia;
    var a = 1 - Math.pow(1 - i, Math.max(dt, 0.001) * 60);
    // Thêm quán tính bậc 2: nếu velocity tăng đột biến, giảm a
    var delta = target - current;
    var velFactor = 1 / (1 + Math.abs(delta) * 0.02);  // big move = slower
    return lerp(current, target, a * velFactor);
  }

  var api = {
    VERSION: VERSION,
    clamp: clamp,
    lerp: lerp,
    damp: damp,
    spring: spring,
    smooth: smooth,
    easing: EASING,
    applyEasing: applyEasing,
    nextIntervalRand: nextIntervalRand,
    jitter: jitter,
    angularIntertia: angularIntertia
  };

  if (typeof global !== "undefined") {
    global.CherryPhysics = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
