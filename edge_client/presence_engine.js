/*
 * CHERRY PRESENCE ENGINE — Sprint 5: Human-Like Interaction (14/11/2026)
 * =========================================================================
 * Nguồn sự thật DUY NHẤT cho presence (eye contact + listening + continuity +
 * idle + interruption + return-to-idle). Dùng chung PC + Pi5.
 *
 * Nguồn thiết kế: CHERRY_EMBODIMENT_SPRINT_PLAN.md §7 (Sprint 5).
 *
 * Xuất global: window.CherryPresenceEngine = {
 *   PresenceEngine, IDLE_BEHAVIORS, LISTENING_GAZE, EYE_CONTACT_PRESETS,
 *   VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "s5_1411";

  /* ================================================================
   * 1. IDLE_BEHAVIORS — hành vi tự nhiên khi không có tương tác
   *    (plan §7.2: Natural idle behavior)
   * ================================================================ */
  var IDLE_BEHAVIORS = {
    /* Thỉnh thoảng chớp mắt chậm (3-5s) */
    slow_blink: { interval_ms: 4000, duration_ms: 200, weight: 0.3 },
    /* Nhìn đi chỗ khác (gaze away) rồi quay lại camera */
    gaze_away: { interval_ms: 8000, duration_ms: 1500, weight: 0.2 },
    /* Đầu nghiêng nhẹ sang một bên */
    head_tilt: { interval_ms: 6000, duration_ms: 800, weight: 0.2 },
    /* Thở nhẹ (chest rise/fall) */
    breathing: { interval_ms: 3000, duration_ms: 1500, weight: 0.3 }
  };

  /* ================================================================
   * 2. LISTENING_GAZE — ánh mắt khi đang nghe user nói
   *    (plan §7.2: Listening behavior + Eye contact)
   * ================================================================ */
  var LISTENING_GAZE = {
    /* Mắt nhìn vào camera (eye contact) — 70% thời gian */
    eye_contact: { gazeX: 0, gazeY: 0, weight: 0.7 },
    /* Mắt nhìn xuống (đang suy nghĩ) — 20% */
    thinking: { gazeX: 0, gazeY: -0.3, weight: 0.2 },
    /* Mắt nhìn sang ngang (đang xử lý) — 10% */
    processing: { gazeX: 0.4, gazeY: 0, weight: 0.1 }
  };

  /* ================================================================
   * 3. EYE_CONTACT_PRESETS — cường độ eye contact theo state
   * ================================================================ */
  var EYE_CONTACT_PRESETS = {
    IDLE: 0.6,
    LISTENING: 0.9,
    THINKING: 0.4,
    ANALYTICAL_THINKING: 0.5,
    CURIOUS: 0.8,
    WARM_GREETING: 0.9,
    HAPPY: 0.8,
    PROUD: 0.7,
    CONFIDENT_SUCCESS: 0.7,
    SURPRISED: 0.9,
    WARNING: 0.8,
    SERIOUS_ALERT: 0.9,
    APOLOGETIC: 0.5,
    EMPATHETIC: 0.8,
    CONSULTATIVE_INQUIRING: 0.9,
    SPEAKING: 0.7,
    ERROR: 0.6,
    SLEEPING: 0.0,
    OFFLINE: 0.0,
    RECONNECTING: 0.5,
    NEUTRAL: 0.6
  };

  /* ================================================================
   * 4. PresenceEngine — máy trạng thái presence
   *    tick(now): cập nhật gaze + idle behavior + continuity
   *    notifyUserSpeaking(): user bắt đầu nói → listening
   *    notifyUserStopped(): user dừng nói → return-to-idle
   *    notifyInterrupted(): user ngắt lời
   *    getGaze(): trả { gazeX, gazeY, eyeContact } hiện tại
   * ================================================================ */
  function PresenceEngine(opts) {
    opts = opts || {};
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });
    this._state = "IDLE";
    this._gazeX = 0;
    this._gazeY = 0;
    this._eyeContact = EYE_CONTACT_PRESETS.IDLE;
    this._lastIdleTick = 0;
    this._nextIdleBehavior = 0;
    this._currentIdleBehavior = null;
    this._idleBehaviorStart = 0;
    this._userSpeaking = false;
    this._lastUserActivity = 0;
    this._conversationTurns = 0;
    this._lastTurnEnd = 0;
    this._interrupted = false;
    this._log = [];
    this._maxLog = 32;
  }

  PresenceEngine.prototype._pushLog = function (entry) {
    this._log.push(entry);
    if (this._log.length > this._maxLog) this._log.shift();
  };

  PresenceEngine.prototype.getLog = function () {
    return this._log.slice();
  };

  PresenceEngine.prototype.getGaze = function () {
    return { gazeX: this._gazeX, gazeY: this._gazeY,
             eyeContact: this._eyeContact, state: this._state };
  };

  PresenceEngine.prototype.getConversationTurns = function () {
    return this._conversationTurns;
  };

  /* setState — đồng bộ với engine state */
  PresenceEngine.prototype.setState = function (state) {
    if (this._state === state) return;
    this._state = state;
    this._eyeContact = EYE_CONTACT_PRESETS[state] != null
      ? EYE_CONTACT_PRESETS[state] : 0.6;
    this._pushLog({ t: this._nowFn(), kind: "state", state: state,
                    eyeContact: this._eyeContact });
  };

  /* notifyUserSpeaking — user bắt đầu nói → listening gaze */
  PresenceEngine.prototype.notifyUserSpeaking = function () {
    this._userSpeaking = true;
    this._lastUserActivity = this._nowFn();
    if (this._state === "IDLE" || this._state === "SLEEPING") {
      this.setState("LISTENING");
    }
    this._pushLog({ t: this._nowFn(), kind: "user_speaking_start" });
  };

  /* notifyUserStopped — user dừng nói → return-to-idle sau 2s */
  PresenceEngine.prototype.notifyUserStopped = function () {
    this._userSpeaking = false;
    this._lastUserActivity = this._nowFn();
    this._conversationTurns++;
    this._lastTurnEnd = this._nowFn();
    this._pushLog({ t: this._nowFn(), kind: "user_speaking_end",
                    turns: this._conversationTurns });
  };

  /* notifyInterrupted — user ngắt lời */
  PresenceEngine.prototype.notifyInterrupted = function () {
    this._interrupted = true;
    this._pushLog({ t: this._nowFn(), kind: "interrupted" });
  };

  /* pickIdleBehavior — chọn hành vi idle theo weight */
  function pickIdleBehavior(rng) {
    var behaviors = Object.keys(IDLE_BEHAVIORS);
    var totalWeight = 0;
    for (var i = 0; i < behaviors.length; i++) {
      totalWeight += IDLE_BEHAVIORS[behaviors[i]].weight;
    }
    var r = rng() * totalWeight;
    var cum = 0;
    for (var j = 0; j < behaviors.length; j++) {
      cum += IDLE_BEHAVIORS[behaviors[j]].weight;
      if (r < cum) return behaviors[j];
    }
    return behaviors[behaviors.length - 1];
  }

  /* tick — gọi mỗi frame; cập nhật gaze + idle */
  PresenceEngine.prototype.tick = function (nowMs) {
    var now = nowMs != null ? nowMs : this._nowFn();

    // 1. Listening gaze khi user đang nói
    if (this._userSpeaking) {
      // 70% eye contact, 20% thinking, 10% processing
      var r = Math.random();
      if (r < 0.7) {
        this._gazeX = 0; this._gazeY = 0;
      } else if (r < 0.9) {
        this._gazeX = 0; this._gazeY = -0.3;
      } else {
        this._gazeX = 0.4; this._gazeY = 0;
      }
      this._eyeContact = EYE_CONTACT_PRESETS.LISTENING;
      return this.getGaze();
    }

    // 2. Return-to-idle sau 2s user dừng
    if (!this._userSpeaking && this._lastUserActivity > 0 &&
        (now - this._lastUserActivity) > 2000 && this._state === "LISTENING") {
      this.setState("IDLE");
    }

    // 3. Idle behavior scheduling
    if (this._state === "IDLE" || this._state === "NEUTRAL") {
      if (this._nextIdleBehavior === 0) {
        this._nextIdleBehavior = now + 2000 + Math.random() * 3000;
      }
      if (now >= this._nextIdleBehavior && !this._currentIdleBehavior) {
        this._currentIdleBehavior = pickIdleBehavior(Math.random);
        this._idleBehaviorStart = now;
        var beh = IDLE_BEHAVIORS[this._currentIdleBehavior];
        this._pushLog({ t: now, kind: "idle_start", behavior: this._currentIdleBehavior });
        this._nextIdleBehavior = now + beh.interval_ms;
      }
      if (this._currentIdleBehavior) {
        var beh2 = IDLE_BEHAVIORS[this._currentIdleBehavior];
        var elapsed = now - this._idleBehaviorStart;
        if (elapsed >= beh2.duration_ms) {
          this._pushLog({ t: now, kind: "idle_end", behavior: this._currentIdleBehavior });
          this._currentIdleBehavior = null;
        } else if (this._currentIdleBehavior === "gaze_away") {
          // Gaze away: nhìn sang ngang rồi quay lại
          var phase = elapsed / beh2.duration_ms;
          this._gazeX = Math.sin(phase * Math.PI) * 0.5;
          this._gazeY = 0;
        } else if (this._currentIdleBehavior === "head_tilt") {
          // Head tilt: lerp gazeY nhẹ
          var phase2 = elapsed / beh2.duration_ms;
          this._gazeY = Math.sin(phase2 * Math.PI) * 0.1;
        }
      }
    }

    return this.getGaze();
  };

  /* Export */
  global.CherryPresenceEngine = {
    VERSION: VERSION,
    IDLE_BEHAVIORS: IDLE_BEHAVIORS,
    LISTENING_GAZE: LISTENING_GAZE,
    EYE_CONTACT_PRESETS: EYE_CONTACT_PRESETS,
    PresenceEngine: PresenceEngine
  };

})(typeof window !== "undefined" ? window : this);
