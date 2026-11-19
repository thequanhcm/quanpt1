/*!
 * CHERRY AUDIO MOUTH DRIVER — Sprint V7-M2 (18/11/2026)
 * =========================================================================
 * Chuyển audio RMS → viseme intensity (chuẩn Preston Blair 12 viseme).
 * Dựa trên motion profile đo được từ Cherry final.mp4:
 *   - mouth_active_ratio_when_speaking = 99% → miệng gần như lúc nào cũng động
 *   - mouth_peak_intensity = 0.71-0.87 → nguyên âm mở RẤT LỚN
 *   - approx_syllable_peaks_per_sec = 4.5 → nhịp nói chuẩn
 *
 * 12 viseme (Preston Blair):
 *   AA (A), EE, OO, OH, MM_BP, FV_L, S_T, N_TH, CH_SH_J, R_ER, W_Q, REST
 * - Mỗi viseme có openRatio + jawDrop + lipSpread
 * - VA và EE có intensity cao nhất khi MC nói tiếng Anh
 *
 * Fail-open: nếu không có audio → dùng fallback text-driven viseme.
 *
 * Xuất global: window.CherryAudioMouthDriver = {
 *   create, feedAudioBuffer, feedText, tick, getCurrentViseme, VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "v7m2_1811";

  // Preston Blair 12-viseme set
  // open: độ mở hàm 0..1, jaw: độ rơi cằm 0..1, spread: độ rộng môi -1..1
  var VISEMES = {
    AA:   { open: 0.85, jaw: 0.75, spread: 0.5,  label: "AA (a, á, à)" },
    EE:   { open: 0.45, jaw: 0.35, spread: 0.7,  label: "EE (e, ê, i)" },
    OO:   { open: 0.55, jaw: 0.55, spread: -0.3, label: "OO (o, ô, u)" },
    OH:   { open: 0.65, jaw: 0.60, spread: 0.0,  label: "OH (ơ, ờ)" },
    MM_BP:{ open: 0.0,  jaw: 0.0,  spread: -0.1, label: "M/B/P (đóng môi)" },
    FV_L: { open: 0.30, jaw: 0.20, spread: 0.4,  label: "F/V/L (môi dưới chạm răng)" },
    S_T:  { open: 0.25, jaw: 0.15, spread: 0.2,  label: "S/T (răng-lưỡi)" },
    N_TH: { open: 0.35, jaw: 0.20, spread: 0.0,  label: "N/TH (lưỡi-răng)" },
    CH_SH_J: { open: 0.20, jaw: 0.10, spread: 0.5, label: "CH/SH/J (môi rộng)" },
    R_ER: { open: 0.55, jaw: 0.45, spread: 0.0,  label: "R/ER (môi tròn)" },
    W_Q:  { open: 0.40, jaw: 0.40, spread: -0.6, label: "W/Q (môi chu)" },
    REST: { open: 0.0,  jaw: 0.0,  spread: 0.0,  label: "REST (im lặng)" }
  };

  // Map text phoneme → viseme (English + Vietnamese cơ bản)
  var TEXT_TO_VISEME = {
    "a": "AA", "á": "AA", "à": "AA", "ả": "AA", "ã": "AA", "ạ": "AA",
    "ă": "AA", "ắ": "AA", "ằ": "AA", "ẳ": "AA", "ẵ": "AA", "ặ": "AA",
    "â": "AA", "ấ": "AA", "ầ": "AA", "ẩ": "AA", "ẫ": "AA", "ậ": "AA",
    "e": "EE", "é": "EE", "è": "EE", "ẻ": "EE", "ẽ": "EE", "ẹ": "EE",
    "ê": "EE", "ế": "EE", "ề": "EE", "ể": "EE", "ễ": "EE", "ệ": "EE",
    "i": "EE", "í": "EE", "ì": "EE", "ỉ": "EE", "ĩ": "EE", "ị": "EE",
    "o": "OO", "ó": "OO", "ò": "OO", "ỏ": "OO", "õ": "OO", "ọ": "OO",
    "ô": "OO", "ố": "OO", "ồ": "OO", "ổ": "OO", "ỗ": "OO", "ộ": "OO",
    "ơ": "OH", "ớ": "OH", "ờ": "OH", "ở": "OH", "ỡ": "OH", "ợ": "OH",
    "u": "OO", "ú": "OO", "ù": "OO", "ủ": "OO", "ũ": "OO", "ụ": "OO",
    "ư": "OO", "ứ": "OO", "ừ": "OO", "ử": "OO", "ữ": "OO", "ự": "OO",
    "y": "EE", "ý": "EE", "ỳ": "EE", "ỷ": "EE", "ỹ": "EE", "ỵ": "EE",
    "m": "MM_BP", "b": "MM_BP", "p": "MM_BP",
    "f": "FV_L", "v": "FV_L", "l": "FV_L",
    "s": "S_T", "t": "S_T", "x": "S_T",
    "n": "N_TH", "d": "N_TH", "đ": "N_TH", "th": "CH_SH_J",
    "ch": "CH_SH_J", "sh": "CH_SH_J", "j": "CH_SH_J", "z": "CH_SH_J",
    "r": "R_ER", "er": "R_ER",
    "w": "W_Q", "q": "W_Q", "qu": "W_Q",
    " ": "REST", ".": "REST", ",": "REST", "?": "REST", "!": "REST"
  };

  function AudioMouthDriver(opts) {
    opts = opts || {};
    this._physics = opts.physics || global.CherryPhysics;
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });

    // Trạng thái hiện tại
    this._cur = { viseme: "REST", open: 0, jaw: 0, spread: 0, intensity: 0 };

    // Audio buffer (last RMS samples)
    this._audio_buf = [];
    this._audio_buf_max = 60;  // 1s @ 60fps

    // Text stream
    this._text_buf = [];
    this._text_idx = 0;

    // Time tracking
    this._last_tick = 0;
    this._viseme_start = 0;
    this._viseme_dur_ms = 80;  // 80ms/viseme = 12.5 viseme/s
    this._t = 0;

    // Fallback: nếu không có audio, dùng text
    this._mode = "idle";  // idle | audio | text
  }

  AudioMouthDriver.prototype.feedAudioBuffer = function (samples) {
    // samples: Float32Array [-1..1]
    if (!samples || samples.length === 0) return;
    var sum = 0;
    for (var i = 0; i < samples.length; i++) {
      sum += samples[i] * samples[i];
    }
    var rms = Math.sqrt(sum / samples.length);
    // Đẩy RMS vào buffer
    this._audio_buf.push(rms);
    if (this._audio_buf.length > this._audio_buf_max) {
      this._audio_buf.shift();
    }
    this._mode = "audio";
  };

  AudioMouthDriver.prototype.feedText = function (text) {
    // text: chuỗi cần nói (tiếng Việt + tiếng Anh cơ bản)
    if (!text) {
      this._mode = "idle";
      return;
    }
    var chars = text.toLowerCase();
    var buf = [];
    for (var i = 0; i < chars.length; i++) {
      // Ưu tiên digraph trước (ch, th, sh, qu, er)
      var dig = chars.substr(i, 2);
      if (TEXT_TO_VISEME[dig]) {
        buf.push(TEXT_TO_VISEME[dig]);
        i++;  // skip next char
      } else if (TEXT_TO_VISEME[chars[i]]) {
        buf.push(TEXT_TO_VISEME[chars[i]]);
      } else {
        buf.push("REST");
      }
    }
    this._text_buf = buf;
    this._text_idx = 0;
    this._mode = "text";
    this._viseme_start = this._nowFn();
  };

  AudioMouthDriver.prototype.tick = function (dt) {
    var now = this._nowFn();
    if (typeof dt !== "number" || dt <= 0) {
      dt = this._last_tick ? (now - this._last_tick) / 1000 : 0.016;
    }
    dt = Math.min(dt, 0.1);
    this._last_tick = now;
    this._t += dt;

    var target_viseme = "REST";
    var target_intensity = 0;

    if (this._mode === "audio" && this._audio_buf.length > 0) {
      // Audio mode: lấy RMS gần nhất + smoothing
      var rms = this._audio_buf[this._audio_buf.length - 1];
      if (this._physics && this._physics.smooth) {
        this._cur.intensity = this._physics.smooth(this._cur.intensity, rms * 1.4, 0.4);
      } else {
        this._cur.intensity = this._cur.intensity * 0.6 + rms * 1.4 * 0.4;
      }
      // Audio intensity quyết định open + chọn viseme theo biên độ
      target_intensity = Math.min(1, this._cur.intensity);
      target_viseme = _rmsToViseme(target_intensity);
    } else if (this._mode === "text" && this._text_buf.length > 0) {
      // Text mode: tick qua từng viseme theo tốc độ
      var elapsed = now - this._viseme_start;
      var idx = Math.floor(elapsed / this._viseme_dur_ms);
      if (idx >= this._text_buf.length) {
        // hết text → idle
        this._mode = "idle";
        target_viseme = "REST";
        target_intensity = 0;
      } else {
        target_viseme = this._text_buf[idx];
        target_intensity = 0.7;  // text luôn có intensity ~0.7
      }
    } else {
      // Idle: miệng đóng dần về REST
      target_intensity = 0;
      target_viseme = "REST";
      if (this._physics && this._physics.smooth) {
        this._cur.intensity = this._physics.smooth(this._cur.intensity, 0, 0.1);
      } else {
        this._cur.intensity *= 0.9;
      }
    }

    // Áp dụng viseme params
    var v = VISEMES[target_viseme] || VISEMES.REST;
    if (this._physics && this._physics.smooth) {
      this._cur.open = this._physics.smooth(this._cur.open, v.open * target_intensity, 0.5);
      this._cur.jaw = this._physics.smooth(this._cur.jaw, v.jaw * target_intensity, 0.5);
      this._cur.spread = this._physics.smooth(this._cur.spread, v.spread, 0.4);
    } else {
      this._cur.open = this._cur.open * 0.5 + v.open * target_intensity * 0.5;
      this._cur.jaw = this._cur.jaw * 0.5 + v.jaw * target_intensity * 0.5;
      this._cur.spread = this._cur.spread * 0.6 + v.spread * 0.4;
    }
    this._cur.viseme = target_viseme;

    return this._cur;
  };

  function _rmsToViseme(rms) {
    if (rms < 0.05) return "REST";
    if (rms < 0.15) return "MM_BP";
    if (rms < 0.25) return "S_T";
    if (rms < 0.40) return "EE";
    if (rms < 0.55) return "OO";
    if (rms < 0.70) return "OH";
    return "AA";
  }

  AudioMouthDriver.prototype.getCurrentViseme = function () {
    return Object.assign({}, this._cur);
  };

  // (19/11) SPRINT-4 CONTRACT FIX — avatar_engine.js gọi 5 method mà bản V7-M2
  // chưa export: start/stop/isActive/getCurrent/bargeIn. Thiếu → TypeError mỗi
  // frame → render loop crash → viewport avatar trắng trên dashboard 8765.
  // Envelope = RMS trung bình gần đây (0..1) dùng cho micro-rest + speech energy.
  AudioMouthDriver.prototype._envelope = function () {
    if (!this._audio_buf.length) return 0;
    var sum = 0;
    for (var i = 0; i < this._audio_buf.length; i++) sum += this._audio_buf[i];
    var avg = sum / this._audio_buf.length;
    return Math.max(0, Math.min(1, avg * 4));  // RMS ~0.25 → sat 1.0
  };

  AudioMouthDriver.prototype.isActive = function () {
    return this._active === true;
  };

  AudioMouthDriver.prototype.getCurrent = function () {
    return {
      viseme: this._cur.viseme,
      open: this._cur.open,
      jaw: this._cur.jaw,
      spread: this._cur.spread,
      intensity: this._cur.intensity,
      envelope: this._envelope(),
      active: this._active === true
    };
  };

  AudioMouthDriver.prototype.start = function (audioEl, opts) {
    // audioEl: HTMLAudioElement/HTMLVideoElement phát TTS (engine đã set src).
    // Driver V7-M2 là text/RMS-fed: engine sẽ feed RMS qua feedAudioBuffer hoặc
    // feedText; start() chỉ đánh dấu session + cắm analyser nếu có sẵn.
    this._active = true;
    this._audioEl = audioEl || null;
    this._analyser = (opts && opts.existingAnalyser) || null;
    if (!this._mode || this._mode === "idle") this._mode = "text";
  };

  AudioMouthDriver.prototype.stop = function (reason) {
    this._active = false;
    this._audioEl = null;
    this._analyser = null;
    this.reset();
  };

  AudioMouthDriver.prototype.bargeIn = function () {
    // Người dùng ngắt lời — cắt ngay, không mượt.
    this._active = false;
    this._audioEl = null;
    this._analyser = null;
    this._audio_buf = [];
    this._text_buf = [];
    this._text_idx = 0;
    this._mode = "idle";
    this._cur = { viseme: "REST", open: 0, jaw: 0, spread: 0, intensity: 0 };
  };

  AudioMouthDriver.prototype.reset = function () {
    this._cur = { viseme: "REST", open: 0, jaw: 0, spread: 0, intensity: 0 };
    this._audio_buf = [];
    this._text_buf = [];
    this._text_idx = 0;
    this._mode = "idle";
    this._t = 0;
    this._last_tick = 0;
  };

  AudioMouthDriver.VISEMES = VISEMES;
  AudioMouthDriver.TEXT_TO_VISEME = TEXT_TO_VISEME;
  AudioMouthDriver.VERSION = VERSION;

  var api = {
    VERSION: VERSION,
    // (19/11) FIX: avatar_engine.js constructor gọi `new _AUDIO.AudioMouthDriver(...)`
    // nhưng api trước đây chỉ export `create` → TypeError khi engine init trên
    // dashboard 8765 → viewport avatar trắng. Export thêm class để engine dùng
    // trực tiếp; `create` giữ nguyên cho backward-compat.
    create: function (opts) { return new AudioMouthDriver(opts); },
    AudioMouthDriver: AudioMouthDriver,
    VISEMES: VISEMES,
    TEXT_TO_VISEME: TEXT_TO_VISEME
  };

  if (typeof global !== "undefined") {
    global.CherryAudioMouthDriver = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
