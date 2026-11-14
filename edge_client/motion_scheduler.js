/*
 * CHERRY MOTION SCHEDULER — Sprint 2: Natural Motion Engine (14/11/2026)
 * =========================================================================
 * Nguồn sự thật DUY NHẤT cho motion scheduling giữa PC dashboard (8765/8766)
 * và Pi5 kiosk (8768). Cả 2 nền tảng nạp FILE NÀY (cùng md5) TRƯỚC
 * avatar_engine.js. Bản copy local trong engine chỉ là fallback khẩn cấp.
 *
 * Card: TASK-EMBODIMENT-S2 (APPROVED, auth owner_desktop_chat_directive).
 * Thiết kế: CHERRY_MOTION_ENGINE_DESIGN.md §3 (Scheduler) + §4 (Blending)
 * + §5 (Gesture Library).
 */
(function (root) {
  "use strict";

  var PROTOCOL_VERSION = "s2_1411";

  // ===== Motion Priority (design §3.2) =====
  var PRIORITY = {
    SAFETY: 100,
    SPEAKING: 80,
    LISTENING: 70,
    THINKING: 60,
    EMOTION: 50,
    IDLE: 30,
    DECORATIVE: 10,
  };

  // ===== Easing Functions (design §3.3) =====
  function _easeLinear(t) { return t; }
  function _easeIn(t) { return t * t; }
  function _easeOut(t) { return 1 - (1 - t) * (1 - t); }
  function _easeInOut(t) {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  }
  function _easeCosine(t) {
    return 0.5 - 0.5 * Math.cos(Math.PI * t);
  }
  var EASING = {
    linear: _easeLinear,
    "ease-in": _easeIn,
    "ease-out": _easeOut,
    "ease-in-out": _easeInOut,
    cosine: _easeCosine,
  };

  function _applyEasing(t, name) {
    var fn = EASING[name] || EASING["ease-out"];
    return fn(Math.max(0, Math.min(1, t)));
  }

  function _interpolate(start, target, t) {
    if (typeof start === "number" && typeof target === "number") {
      return start + (target - start) * t;
    }
    if (Array.isArray(start) && Array.isArray(target)) {
      var out = new Array(start.length);
      for (var i = 0; i < start.length; i++) {
        out[i] = start[i] + (target[i] - start[i]) * t;
      }
      return out;
    }
    return t < 1 ? start : target;
  }

  /*
   * MotionScheduler — design §3.1.
   * - add(motion): validate, check priority, interrupt lower, push active.
   * - update(now): tick all active motions, apply easing, blend by target key.
   * - interruptLower(priority): drop interruptible motions có priority thấp hơn.
   * - clear(): reset (state change / disconnect).
   *
   * Motion shape:
   *   { target: "head.tilt", start: 0, target: 5, duration: 500,
   *     easing: "ease-out", priority: 30, interruptible: true,
   *     additive: false, onComplete?: fn }
   */
  function MotionScheduler() {
    this.active = [];
    this.queued = [];
    this.lastUpdate = 0;
    this._blendCache = {};
  }

  MotionScheduler.prototype.add = function (motion) {
    if (!motion || typeof motion !== "object") return false;
    var targetKey = motion.target_key || motion.target;
    if (targetKey == null || motion.start == null) return false;
    var targetValue = motion.target_value;
    if (targetValue == null) targetValue = motion.end != null ? motion.end : 0;
    if (!motion.duration || motion.duration <= 0) return false;
    var m = Object.assign({
      priority: PRIORITY.IDLE,
      interruptible: true,
      additive: false,
      easing: "ease-out",
      startTime: 0,
      progress: 0,
      target: targetKey,
      target_value: targetValue,
    }, motion);
    m.startTime = m.startTime || (typeof performance !== "undefined" ? performance.now() : Date.now());
    // Interrupt lower-priority motions trên cùng target key.
    this.interruptLower(m.priority, m.target);
    this.active.push(m);
    return true;
  };

  MotionScheduler.prototype.interruptLower = function (priority, targetKey) {
    for (var i = this.active.length - 1; i >= 0; i--) {
      var m = this.active[i];
      if (!m.interruptible) continue;
      if (m.priority < priority) {
        // Cùng target key → drop; khác target → drop nếu priority thấp hơn nhiều.
        if (targetKey == null || m.target === targetKey || m.priority < priority - 10) {
          this.active.splice(i, 1);
        }
      }
    }
  };

  MotionScheduler.prototype.update = function (now) {
    if (!now) now = typeof performance !== "undefined" ? performance.now() : Date.now();
    var dt = this.lastUpdate ? now - this.lastUpdate : 16;
    this.lastUpdate = now;
    this._blendCache = {};
    for (var i = this.active.length - 1; i >= 0; i--) {
      var m = this.active[i];
      m.progress = Math.min(1, (now - m.startTime) / m.duration);
      var eased = _applyEasing(m.progress, m.easing);
      var value = _interpolate(m.start, m.target_value, eased);
      var key = m.target;
      // Blending: motion cao hơn override; cùng priority + additive → cộng dồn.
      var existing = this._blendCache[key];
      if (!existing || m.priority > existing.priority) {
        this._blendCache[key] = { value: value, priority: m.priority, motion: m };
      } else if (m.priority === existing.priority && m.additive && typeof value === "number" &&
                 typeof existing.value === "number") {
        existing.value = existing.value + (value - m.start);
      }
      if (m.progress >= 1) {
        if (typeof m.onComplete === "function") {
          try { m.onComplete(); } catch (_) { /* swallow */ }
        }
        this.active.splice(i, 1);
      }
    }
    return this._blendCache;
  };

  MotionScheduler.prototype.clear = function () {
    this.active.length = 0;
    this.queued.length = 0;
    this._blendCache = {};
  };

  MotionScheduler.prototype.size = function () { return this.active.length; };

  // ===== Gesture Library (design §5) — 10 gestures =====
  var GESTURE_LIBRARY = {
    greeting: {
      motions: [
        { target: "head.tilt", start: 0, target: 5, duration: 500, easing: "ease-out", priority: PRIORITY.EMOTION },
        { target: "eye.contact", start: 0, target: 1, duration: 300, easing: "ease-out", priority: PRIORITY.EMOTION },
        { target: "mouth.smile", start: 0, target: 0.5, duration: 400, easing: "ease-out", priority: PRIORITY.EMOTION },
      ],
      priority: PRIORITY.EMOTION,
      context: "user_greeting",
    },
    listening: {
      motions: [
        { target: "eye.contact", start: 0, target: 1, duration: 200, easing: "ease-out", priority: PRIORITY.LISTENING },
        { target: "head.nod", start: 0, target: 2, duration: 500, easing: "ease-in-out", priority: PRIORITY.LISTENING, repeat: true },
      ],
      priority: PRIORITY.LISTENING,
      context: "user_speaking",
    },
    thinking: {
      motions: [
        { target: "eye.saccade", start: 0, target: 0.3, duration: 800, easing: "ease-in-out", priority: PRIORITY.THINKING },
        { target: "head.tilt", start: 0, target: 8, duration: 600, easing: "ease-out", priority: PRIORITY.THINKING },
      ],
      priority: PRIORITY.THINKING,
      context: "processing",
    },
    curious: {
      motions: [
        { target: "head.tilt", start: 0, target: 10, duration: 700, easing: "ease-out", priority: PRIORITY.EMOTION },
        { target: "eye.gaze", start: 0, target: 0.6, duration: 500, easing: "ease-in-out", priority: PRIORITY.EMOTION },
      ],
      priority: PRIORITY.EMOTION,
      context: "curious",
    },
    empathic: {
      motions: [
        { target: "head.tilt", start: 0, target: 3, duration: 800, easing: "ease-in-out", priority: PRIORITY.EMOTION },
        { target: "eye.contact", start: 0, target: 0.8, duration: 600, easing: "ease-out", priority: PRIORITY.EMOTION },
      ],
      priority: PRIORITY.EMOTION,
      context: "empathic",
    },
    emphatic: {
      motions: [
        { target: "head.nod", start: 0, target: 4, duration: 400, easing: "ease-out", priority: PRIORITY.EMOTION },
        { target: "mouth.smile", start: 0, target: 0.7, duration: 500, easing: "ease-out", priority: PRIORITY.EMOTION },
      ],
      priority: PRIORITY.EMOTION,
      context: "emphatic",
    },
    acknowledging: {
      motions: [
        { target: "head.nod", start: 0, target: 3, duration: 350, easing: "ease-out", priority: PRIORITY.LISTENING },
      ],
      priority: PRIORITY.LISTENING,
      context: "acknowledging",
    },
    considering: {
      motions: [
        { target: "head.tilt", start: 0, target: 6, duration: 900, easing: "ease-in-out", priority: PRIORITY.THINKING },
        { target: "eye.saccade", start: 0, target: 0.4, duration: 700, easing: "ease-in-out", priority: PRIORITY.THINKING },
      ],
      priority: PRIORITY.THINKING,
      context: "considering",
    },
    responding: {
      motions: [
        { target: "head.tilt", start: 0, target: 2, duration: 300, easing: "ease-out", priority: PRIORITY.SPEAKING },
        { target: "mouth.smile", start: 0, target: 0.3, duration: 400, easing: "ease-out", priority: PRIORITY.SPEAKING },
      ],
      priority: PRIORITY.SPEAKING,
      context: "responding",
    },
    closing: {
      motions: [
        { target: "head.tilt", start: 0, target: 0, duration: 500, easing: "ease-in-out", priority: PRIORITY.EMOTION },
        { target: "eye.contact", start: 0, target: 0.5, duration: 400, easing: "ease-out", priority: PRIORITY.EMOTION },
      ],
      priority: PRIORITY.EMOTION,
      context: "closing",
    },
  };

  /*
   * selectGesture(context, lastName) — design §5.1.
   * Random selection trong candidates có context khớp, tránh lặp lại gesture
   * vừa chạy (nếu có ≥ 2 candidates). Trả null nếu không có candidate.
   */
  function selectGesture(context, lastName) {
    var candidates = [];
    for (var name in GESTURE_LIBRARY) {
      if (GESTURE_LIBRARY[name].context === context) candidates.push(name);
    }
    if (candidates.length === 0) return null;
    var pool = candidates;
    if (lastName && candidates.length > 1) {
      pool = candidates.filter(function (n) { return n !== lastName; });
    }
    var pick = pool[Math.floor(Math.random() * pool.length)];
    return { name: pick, gesture: GESTURE_LIBRARY[pick] };
  }

  var api = {
    version: PROTOCOL_VERSION,
    PRIORITY: PRIORITY,
    EASING: EASING,
    MotionScheduler: MotionScheduler,
    GESTURE_LIBRARY: GESTURE_LIBRARY,
    selectGesture: selectGesture,
    _interpolate: _interpolate,
    _applyEasing: _applyEasing,
  };

  root.CHERRY_MOTION_SCHEDULER = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api; // node (test)
  }
})(typeof window !== "undefined" ? window : globalThis);
