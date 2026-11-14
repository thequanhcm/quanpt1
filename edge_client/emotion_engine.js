/*
 * CHERRY EMOTION ENGINE — Sprint 3: Expressive Emotion Engine (14/11/2026)
 * =========================================================================
 * Nguồn sự thật DUY NHẤT cho emotion transition + intensity + micro-emotions
 * + context-aware extraction (negation + multi-emotion). Dùng chung PC + Pi5.
 *
 * Nguồn thiết kế: CHERRY_EMBODIMENT_SPRINT_PLAN.md §5 (Sprint 3).
 *
 * Xuất global: window.CherryEmotionEngine = {
 *   VERSION, INTENSITY_PRESETS, MICRO_EMOTIONS, TRANSITION_PRESETS,
 *   EmotionTransitionEngine, extractEmotionContext
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "s3_1411";

  function clamp01(v) {
    if (typeof v !== "number" || isNaN(v)) return null;
    return Math.max(0, Math.min(1, v));
  }

  /* ================================================================
   * 1. INTENSITY_PRESETS — cường độ mặc định theo state (0.0–1.0)
   * ================================================================ */
  var INTENSITY_PRESETS = {
    IDLE: 0.3,
    LISTENING: 0.4,
    THINKING: 0.5,
    ANALYTICAL_THINKING: 0.5,
    CURIOUS: 0.6,
    WARM_GREETING: 0.7,
    HAPPY: 0.8,
    PROUD: 0.8,
    CONFIDENT_SUCCESS: 0.9,
    SURPRISED: 0.9,
    WARNING: 0.8,
    SERIOUS_ALERT: 1.0,
    APOLOGETIC: 0.6,
    EMPATHETIC: 0.6,
    CONSULTATIVE_INQUIRING: 0.5,
    SPEAKING: 0.6,
    ERROR: 0.9,
    SLEEPING: 0.1,
    OFFLINE: 0.1,
    RECONNECTING: 0.5,
    NEUTRAL: 0.3
  };

  /* ================================================================
   * 2. MICRO_EMOTIONS — biến thể vi-cảm xúc (plan §5.2)
   *    key "<STATE>:<micro>" → hiệu chỉnh intensity + motion hint.
   * ================================================================ */
  var MICRO_EMOTIONS = {
    "HAPPY:gentle_smile": { intensity_delta: -0.15, motion_hint: "micro_nod" },
    "HAPPY:bright_smile": { intensity_delta: 0.1, motion_hint: "micro_nod" },
    "CONFIDENT_SUCCESS:broad_smile": { intensity_delta: 0.05, motion_hint: "proud_nod" },
    "PROUD:subtle_pride": { intensity_delta: -0.1, motion_hint: "proud_nod" },
    "PROUD:broad_pride": { intensity_delta: 0.1, motion_hint: "proud_nod" },
    "SURPRISED:soft_surprise": { intensity_delta: -0.2, motion_hint: "quick_lean" },
    "SURPRISED:strong_surprise": { intensity_delta: 0.1, motion_hint: "quick_lean" },
    "EMPATHETIC:warm_empathy": { intensity_delta: -0.1, motion_hint: "slow_blink" },
    "EMPATHETIC:deep_empathy": { intensity_delta: 0.15, motion_hint: "slow_blink" },
    "APOLOGETIC:soft_apology": { intensity_delta: -0.15, motion_hint: "head_down" },
    "APOLOGETIC:deep_apology": { intensity_delta: 0.2, motion_hint: "head_down" },
    "CURIOUS:light_curiosity": { head_tilt: 3, motion_hint: "head_tilt" },
    "CURIOUS:deep_curiosity": { head_tilt: 8, motion_hint: "head_tilt" },
    "THINKING:light_thinking": { head_tilt: 3, motion_hint: "head_tilt" },
    "THINKING:deep_thinking": { head_tilt: 8, motion_hint: "head_tilt" }
  };

  /* ================================================================
   * 3. TRANSITION_PRESETS — duration/easing/hold theo state đích.
   *    Chọn preset: từ state cũ → state mới; default 300ms ease-in-out.
   * ================================================================ */
  var TRANSITION_PRESETS = {
    default: { duration_ms: 300, easing: "ease-in-out", hold_ms: 0 },
    to_SERIOUS_ALERT: { duration_ms: 120, easing: "ease-out", hold_ms: 0 },
    to_SURPRISED: { duration_ms: 150, easing: "ease-out", hold_ms: 200 },
    to_HAPPY: { duration_ms: 300, easing: "ease-in-out", hold_ms: 0 },
    to_PROUD: { duration_ms: 350, easing: "ease-in-out", hold_ms: 100 },
    to_APOLOGETIC: { duration_ms: 400, easing: "ease-in-out", hold_ms: 150 },
    to_EMPATHETIC: { duration_ms: 400, easing: "ease-in-out", hold_ms: 150 },
    to_SLEEPING: { duration_ms: 900, easing: "ease-in-out", hold_ms: 0 },
    to_OFFLINE: { duration_ms: 900, easing: "ease-in-out", hold_ms: 0 },
    to_RECONNECTING: { duration_ms: 200, easing: "ease-out", hold_ms: 0 },
    to_NEUTRAL: { duration_ms: 450, easing: "ease-in-out", hold_ms: 0 },
    to_IDLE: { duration_ms: 450, easing: "ease-in-out", hold_ms: 0 }
  };

  function pickTransition(toState) {
    return TRANSITION_PRESETS["to_" + toState] || TRANSITION_PRESETS.default;
  }

  /* ================================================================
   * 4. EmotionTransitionEngine — máy trạng thái chuyển cảm xúc.
   *    transitionTo(to, opts): đổi state qua transition (duration/
   *    easing/hold). update(now): tick — trả snapshot hiện tại.
   *    Intensity 0.0–1.0 (clamp); micro-emotion modulates.
   * ================================================================ */
  function EmotionTransitionEngine(opts) {
    opts = opts || {};
    this._state = "NEUTRAL";
    this._intensity = INTENSITY_PRESETS.NEUTRAL;
    this._micro = null;
    this._transition = null; // { from, to, startMs, durationMs, easing, holdUntilMs }
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });
    this._log = [];
    this._maxLog = 32;
  }

  EmotionTransitionEngine.prototype._pushLog = function (entry) {
    this._log.push(entry);
    if (this._log.length > this._maxLog) this._log.shift();
  };

  EmotionTransitionEngine.prototype.getLog = function () {
    return this._log.slice();
  };

  /* main API — chuyển sang state mới */
  EmotionTransitionEngine.prototype.transitionTo = function (toState, opts) {
    opts = opts || {};
    var from = this._state;
    var micro = opts.micro || null;
    var explicitIntensity = clamp01(opts.intensity);

    if (toState === from && !opts.force) {
      // Cùng state → chỉ hiệu chỉnh micro/intensity
      if (micro) this._micro = micro;
      var base = explicitIntensity !== null ? explicitIntensity
        : (INTENSITY_PRESETS[toState] != null ? INTENSITY_PRESETS[toState] : 0.5);
      var microCfg = micro ? MICRO_EMOTIONS[toState + ":" + micro] : null;
      if (microCfg && typeof microCfg.intensity_delta === "number") {
        var adj = clamp01(base + microCfg.intensity_delta);
        if (adj !== null) this._intensity = adj;
      } else if (explicitIntensity !== null) {
        this._intensity = explicitIntensity;
      }
      this._pushLog({ t: this._nowFn(), kind: "adjust", state: from, micro: micro,
                      intensity: this._intensity });
      return { changed: false, from: from, to: toState, duration_ms: 0,
               intensity: this._intensity, micro: this._micro };
    }

    var preset = pickTransition(toState);
    var now = this._nowFn();
    var duration = opts.duration_ms || preset.duration_ms;
    var hold = opts.hold_ms != null ? opts.hold_ms : preset.hold_ms;

    // Micro-emotion modulates intensity
    var base = explicitIntensity !== null ? explicitIntensity
      : (INTENSITY_PRESETS[toState] != null ? INTENSITY_PRESETS[toState] : 0.5);
    var microCfg = micro ? MICRO_EMOTIONS[toState + ":" + micro] : null;
    var intensity = base;
    if (microCfg && typeof microCfg.intensity_delta === "number") {
      intensity = clamp01(base + microCfg.intensity_delta);
      if (intensity === null) intensity = base;
    }

    this._transition = {
      from: from,
      to: toState,
      startMs: now,
      durationMs: duration,
      easing: preset.easing,
      holdUntilMs: now + duration + hold,
      micro: micro,
      intensity: intensity
    };
    this._state = toState;
    this._micro = micro;
    this._intensity = intensity;
    this._pushLog({ t: now, kind: "transition", from: from, to: toState,
                    duration_ms: duration, hold_ms: hold, intensity: intensity, micro: micro });
    return { changed: true, from: from, to: toState, duration_ms: duration,
             hold_ms: hold, intensity: intensity, micro: micro, easing: preset.easing };
  };

  /* tick — gọi mỗi frame; trả snapshot */
  EmotionTransitionEngine.prototype.update = function (nowMs) {
    var now = nowMs != null ? nowMs : this._nowFn();
    var tr = this._transition;
    if (tr && now >= tr.holdUntilMs) {
      this._transition = null; // transition hoàn tất
    }
    return this.getCurrent();
  };

  /* progress 0→1 của transition đang chạy (null nếu không có) */
  EmotionTransitionEngine.prototype.getProgress = function (nowMs) {
    var now = nowMs != null ? nowMs : this._nowFn();
    var tr = this._transition;
    if (!tr) return null;
    var p = (now - tr.startMs) / tr.durationMs;
    return Math.max(0, Math.min(1, p));
  };

  EmotionTransitionEngine.prototype.getCurrent = function () {
    return { state: this._state, intensity: this._intensity, micro: this._micro,
             transitioning: this._transition != null };
  };

  /* ================================================================
   * 5. extractEmotionContext — context-aware extractor (plan §5.2):
   *    - Negation handling: "không thành công" → KHÔNG tính Success.
   *    - Multi-emotion: trả tối đa 2 emotion theo thứ tự ưu tiên.
   *    Dùng bảng keyword của extractVietnameseEmotion (avatar_protocol).
   *    Trả { primary, secondary, negated: [category...] }.
   * ================================================================ */
  var EMOTION_CATEGORIES = [
    { name: "APOLOGETIC",
      re: /xin lỗi|chia buồn|rất tiếc|đáng tiếc|gây phiền|thừa nhận|mất thời gian|tạm biệt|không may/ },
    { name: "SERIOUS_ALERT",
      re: /cảnh báo|chú ý|lưu ý|nguy hiểm|rủi ro|không được|chặn|thất bại|lỗi|bất thường|sự cố|dừng|khẩn cấp|nghiêm cấm/ },
    { name: "CONFIDENT_SUCCESS",
      re: /hoàn thành|thành công|chính xác|đạt chuẩn|vượt qua|tốt đẹp|100%|xuất sắc|hoàn hảo|thắng lợi/ },
    { name: "ANALYTICAL_THINKING",
      re: /phân tích|dữ liệu|kết quả|nghiên cứu|thuật toán|kiến trúc|thông số|đo lường|logic|thống kê|chi tiết|báo cáo|kiểm tra|xác nhận|chỉ số/ },
    { name: "CONSULTATIVE_INQUIRING",
      re: /kính trình|đề xuất|chờ anh|xin ý kiến|phê duyệt|chỉ đạo|chờ xác nhận|tham vấn/ },
    { name: "WARM_GREETING",
      re: /chào|xin chào|dạ|vâng|rất vui|hân hạnh|sẵn sàng|chúc|em đây|em nghe|tuyệt vời|cảm ơn/ },
    { name: "SURPRISED",
      re: /bất ngờ|ngạc nhiên|ọe|trời ơi|ổn quá|wow|hoàn toàn mới|lần đầu tiên|khám phá/ },
    { name: "CURIOUS",
      re: /tại sao|như thế nào|thế nào|làm sao|giải thích|cho em hỏi|thắc mắc|tò mò|muốn biết|hỏi anh|câu hỏi/ },
    { name: "PROUD",
      re: /tự hào|cải thiện|tiến bộ|tối ưu|nâng cấp|hoàn thiện|phát triển|nhất quán|ổn định|học được|nắm bắt/ }
  ];

  /* Patterns phủ định — tìm trong cửa sổ 12 ký tự TRƯỚC keyword */
  var NEGATION_RE = /(không|chưa|chẳng|đừng|không phải|không thể|không được)\s*$/;

  function isNegated(raw, index) {
    if (index <= 0) return false;
    var windowStart = Math.max(0, index - 12);
    var window = raw.slice(windowStart, index);
    return NEGATION_RE.test(window);
  }

  function extractEmotionContext(text) {
    var result = { primary: "NEUTRAL", secondary: null, negated: [] };
    if (!text || typeof text !== "string") return result;
    var raw = text.toLowerCase();
    var hits = [];
    for (var i = 0; i < EMOTION_CATEGORIES.length; i++) {
      var cat = EMOTION_CATEGORIES[i];
      var m = cat.re.exec(raw);
      if (m) {
        if (isNegated(raw, m.index)) {
          result.negated.push(cat.name);
        } else {
          hits.push(cat.name);
        }
      }
    }
    if (hits.length > 0) result.primary = hits[0];
    if (hits.length > 1) result.secondary = hits[1];
    return result;
  }

  /* Export */
  global.CherryEmotionEngine = {
    VERSION: VERSION,
    INTENSITY_PRESETS: INTENSITY_PRESETS,
    MICRO_EMOTIONS: MICRO_EMOTIONS,
    TRANSITION_PRESETS: TRANSITION_PRESETS,
    EmotionTransitionEngine: EmotionTransitionEngine,
    extractEmotionContext: extractEmotionContext
  };

})(typeof window !== "undefined" ? window : this);
