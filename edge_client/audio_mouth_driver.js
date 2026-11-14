/*
 * CHERRY AUDIO MOUTH DRIVER — Sprint 4: Natural Voice & Lip-Sync (14/11/2026)
 * =========================================================================
 * Nguồn sự thật DUY NHẤT cho audio-driven mouth animation + interrupt + barge-in.
 * Dùng chung PC + Pi5.
 *
 * Nguồn thiết kế: CHERRY_EMBODIMENT_SPRINT_PLAN.md §6 (Sprint 4).
 *
 * Xuất global: window.CherryAudioMouthDriver = {
 *   AudioMouthDriver, computeRMS, smoothEnvelope, visemeFromRMS,
 *   VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "s4_1411";

  /* ================================================================
   * 1. computeRMS — tính RMS (root mean square) từ byte frequency data.
   *    data: Uint8Array (0..255). Trả 0.0..1.0.
   * ================================================================ */
  function computeRMS(data) {
    if (!data || !data.length) return 0;
    var sum = 0;
    for (var i = 0; i < data.length; i++) {
      var v = (data[i] - 128) / 128; // center về 0
      sum += v * v;
    }
    return Math.sqrt(sum / data.length);
  }

  /* ================================================================
   * 2. smoothEnvelope — exponential moving average (EMA) cho RMS.
   *    alpha: 0..1 (cao = phản ứng nhanh, thấp = mượt).
   * ================================================================ */
  function smoothEnvelope(prev, current, alpha) {
    if (alpha == null) alpha = 0.4;
    if (prev == null) return current;
    return prev * (1 - alpha) + current * alpha;
  }

  /* ================================================================
   * 3. visemeFromRMS — chọn viseme theo RMS envelope.
   *    REST (0..0.05) → A (0.05..0.15) → O (0.15..0.30) → E (0.30..0.50)
   *    → I (0.50..0.70) → U (0.70..1.0).
   * ================================================================ */
  var VISEME_THRESHOLDS = [
    { max: 0.05, viseme: "REST", open: 0.0 },
    { max: 0.15, viseme: "A", open: 0.25 },
    { max: 0.30, viseme: "O", open: 0.45 },
    { max: 0.50, viseme: "E", open: 0.55 },
    { max: 0.70, viseme: "I", open: 0.65 },
    { max: 1.01, viseme: "U", open: 0.75 }
  ];

  function visemeFromRMS(rms) {
    for (var i = 0; i < VISEME_THRESHOLDS.length; i++) {
      if (rms < VISEME_THRESHOLDS[i].max) {
        return { viseme: VISEME_THRESHOLDS[i].viseme, open: VISEME_THRESHOLDS[i].open };
      }
    }
    return { viseme: "REST", open: 0.0 };
  }

  /* ================================================================
   * 4. AudioMouthDriver — máy trạng thái lip-sync.
   *    start(audio, opts): bắt đầu drive mouth từ audio element.
   *    stop(): dừng + reset mouth về REST.
   *    interrupt(): ngắt giữa chừng (audio mới bắt đầu).
   *    bargeIn(): người dùng ngắt lời → dừng audio + reset mouth.
   *    update(): tick mỗi frame — đọc analyser, cập nhật viseme.
   * ================================================================ */
  function AudioMouthDriver(opts) {
    opts = opts || {};
    this._audio = null;
    this._analyser = null;
    this._dataArray = null;
    this._envelope = 0;
    this._alpha = opts.alpha != null ? opts.alpha : 0.4;
    this._active = false;
    this._interrupted = false;
    this._bargedIn = false;
    this._currentViseme = "REST";
    this._currentOpen = 0;
    this._onViseme = opts.onViseme || function () {};
    this._onEnd = opts.onEnd || function () {};
    this._onInterrupt = opts.onInterrupt || function () {};
    this._onBargeIn = opts.onBargeIn || function () {};
    this._log = [];
    this._maxLog = 16;
  }

  AudioMouthDriver.prototype._pushLog = function (entry) {
    this._log.push(entry);
    if (this._log.length > this._maxLog) this._log.shift();
  };

  AudioMouthDriver.prototype.getLog = function () {
    return this._log.slice();
  };

  AudioMouthDriver.prototype.isActive = function () {
    return this._active;
  };

  AudioMouthDriver.prototype.getCurrent = function () {
    return { viseme: this._currentViseme, open: this._currentOpen,
             envelope: this._envelope, active: this._active };
  };

  /* start — gắn analyser vào audio element, bắt đầu drive */
  AudioMouthDriver.prototype.start = function (audio, opts) {
    opts = opts || {};
    if (this._active) {
      // Đã active → interrupt trước
      this.interrupt();
    }
    this._audio = audio;
    this._envelope = 0;
    this._interrupted = false;
    this._bargedIn = false;
    this._active = true;

    // Tạo analyser nếu chưa có (Web Audio API)
    if (opts.audioCtx && !this._analyser) {
      try {
        this._analyser = opts.audioCtx.createAnalyser();
        this._analyser.fftSize = 256;
        this._dataArray = new Uint8Array(this._analyser.frequencyBinCount);
        var src = opts.audioCtx.createMediaElementSource(audio);
        src.connect(this._analyser);
        this._analyser.connect(opts.audioCtx.destination);
      } catch (e) {
        // MediaElementSource có thể đã được gắn từ trước (kiosk.js)
        // → fallback dùng analyser có sẵn
        if (opts.existingAnalyser) {
          this._analyser = opts.existingAnalyser;
          this._dataArray = new Uint8Array(this._analyser.frequencyBinCount);
        }
      }
    } else if (opts.existingAnalyser) {
      this._analyser = opts.existingAnalyser;
      this._dataArray = new Uint8Array(this._analyser.frequencyBinCount);
    }

    // onended → stop
    if (audio) {
      var self = this;
      var prevOnEnded = audio.onended;
      audio.onended = function () {
        if (prevOnEnded) {
          try { prevOnEnded.apply(this, arguments); } catch (_) {}
        }
        self.stop("ended");
      };
    }

    this._pushLog({ t: Date.now(), kind: "start", hasAnalyser: !!this._analyser });
    return true;
  };

  /* update — tick mỗi frame; đọc analyser, cập nhật viseme */
  AudioMouthDriver.prototype.update = function () {
    if (!this._active) return this.getCurrent();
    // Gate 4: không có analyser → KHÔNG đọc data, giữ REST
    if (!this._analyser || !this._dataArray) {
      this._currentViseme = "REST";
      this._currentOpen = 0;
      return this.getCurrent();
    }
    this._analyser.getByteFrequencyData(this._dataArray);
    var rms = computeRMS(this._dataArray);
    this._envelope = smoothEnvelope(this._envelope, rms, this._alpha);
    var v = visemeFromRMS(this._envelope);
    if (v.viseme !== this._currentViseme || Math.abs(v.open - this._currentOpen) > 0.01) {
      this._currentViseme = v.viseme;
      this._currentOpen = v.open;
      this._onViseme(v.viseme, v.open);
    }
    return this.getCurrent();
  };

  /* stop — dừng + reset mouth về REST */
  AudioMouthDriver.prototype.stop = function (reason) {
    if (!this._active) return;
    this._active = false;
    this._envelope = 0;
    this._currentViseme = "REST";
    this._currentOpen = 0;
    this._onViseme("REST", 0);
    this._onEnd(reason || "stop");
    this._pushLog({ t: Date.now(), kind: "stop", reason: reason || "stop" });
  };

  /* interrupt — audio mới bắt đầu (không phải barge-in) */
  AudioMouthDriver.prototype.interrupt = function () {
    if (!this._active) return;
    this._interrupted = true;
    this._pushLog({ t: Date.now(), kind: "interrupt" });
    this._onInterrupt();
    this.stop("interrupt");
  };

  /* bargeIn — người dùng ngắt lời */
  AudioMouthDriver.prototype.bargeIn = function () {
    if (!this._active) return;
    this._bargedIn = true;
    if (this._audio) {
      try { this._audio.pause(); } catch (_) {}
    }
    this._pushLog({ t: Date.now(), kind: "barge_in" });
    this._onBargeIn();
    this.stop("barge_in");
  };

  /* Export */
  global.CherryAudioMouthDriver = {
    VERSION: VERSION,
    computeRMS: computeRMS,
    smoothEnvelope: smoothEnvelope,
    visemeFromRMS: visemeFromRMS,
    VISEME_THRESHOLDS: VISEME_THRESHOLDS,
    AudioMouthDriver: AudioMouthDriver
  };

})(typeof window !== "undefined" ? window : this);
