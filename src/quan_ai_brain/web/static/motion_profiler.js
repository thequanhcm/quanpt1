/*!
 * CHERRY MOTION PROFILER — Sprint V7-M0 (18/11/2026)
 * =========================================================================
 * FPS monitor + adaptive LOD cho Pi5. Đo thật trong runtime, KHÔNG
 * dùng performance.now() ảo. Mục tiêu: Pi5 kiosk ≥50 FPS khi chạy
 * motion engine đầy đủ.
 *
 * Thuật toán:
 *   - EMA (alpha=0.1) cho FPS ổn định
 *   - P95 latency: track 60 frame gần nhất → percentile 95
 *   - Adaptive LOD: nếu P95 > 25ms trong 2s → giảm saccade freq
 *     + tắt micro-expression micro-details
 *
 * Fail-open: nếu rAF không khả dụng → fallback setInterval(16ms).
 *
 * Xuất global: window.CherryMotionProfiler = {
 *   start, stop, tick, getReport, setLOD, VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "v7m0_1811";

  var DEFAULT_TARGET_FPS = 50;
  var P95_WINDOW = 60;            // 60 frame buffer
  var LOD_DOWNSHIFT_MS = 25;      // nếu P95 > 25ms → giảm LOD
  var LOD_UPSHIFT_MS = 14;        // nếu P95 < 14ms → tăng LOD
  var LOD_DURATION_MS = 2000;     // giữ LOD ít nhất 2s trước khi đổi

  var LOD_LEVELS = [
    { name: "FULL",     saccade_hz: 4, micro_detail: true,  blur_ms: 0  },
    { name: "BALANCED", saccade_hz: 3, micro_detail: true,  blur_ms: 1  },
    { name: "ECONOMY",  saccade_hz: 2, micro_detail: false, blur_ms: 2  },
    { name: "MINIMAL",  saccade_hz: 1, micro_detail: false, blur_ms: 4  }
  ];

  function MotionProfiler(opts) {
    opts = opts || {};
    this._running = false;
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });
    this._rafFn = opts.rafFn || (typeof global.requestAnimationFrame === "function"
      ? global.requestAnimationFrame.bind(global)
      : function (cb) { return setTimeout(cb, 16); });

    this._fps_ema = DEFAULT_TARGET_FPS;
    this._frame_count = 0;
    this._session_start = 0;

    this._p95_window = [];
    this._p95_index = 0;

    this._lod = 0;            // 0..3
    this._lod_since = 0;
    this._target_fps = opts.target_fps || DEFAULT_TARGET_FPS;

    this._dropped_frames = 0;
    this._long_frames = 0;    // > 33ms = missed vsync

    this._last_lod_change = 0;
  }

  MotionProfiler.prototype.start = function () {
    if (this._running) return;
    this._running = true;
    this._session_start = this._nowFn();
    this._last_lod_change = this._nowFn();
    var self = this;
    var loop = function () {
      if (!self._running) return;
      self.tick();
      self._rafId = self._rafFn(loop);
    };
    self._rafId = self._rafFn(loop);
  };

  MotionProfiler.prototype.stop = function () {
    this._running = false;
    if (this._rafId && typeof global.cancelAnimationFrame === "function") {
      global.cancelAnimationFrame(this._rafId);
    }
    this._rafId = null;
  };

  MotionProfiler.prototype.tick = function () {
    var now = this._nowFn();
    if (this._lastTick == null) {
      this._lastTick = now;
      return;
    }
    var dt = now - this._lastTick;
    this._lastTick = now;

    // Cập nhật P95 window
    this._p95_window[this._p95_index % P95_WINDOW] = dt;
    this._p95_index++;

    // FPS EMA
    if (dt > 0 && dt < 1000) {
      var instant_fps = 1000 / dt;
      this._fps_ema = this._fps_ema * 0.9 + instant_fps * 0.1;
    }

    if (dt > 33) this._long_frames++;
    if (dt > 50) this._dropped_frames++;

    // Cập nhật LOD mỗi 30 frame
    if (this._p95_index % 30 === 0) {
      this._maybeShiftLOD();
    }

    this._frame_count++;
  };

  MotionProfiler.prototype._maybeShiftLOD = function () {
    var now = this._nowFn();
    if (now - this._last_lod_change < LOD_DURATION_MS) return;

    var p95 = this.getP95();
    if (p95 > LOD_DOWNSHIFT_MS && this._lod < LOD_LEVELS.length - 1) {
      this._lod++;
      this._last_lod_change = now;
    } else if (p95 < LOD_UPSHIFT_MS && this._lod > 0) {
      this._lod--;
      this._last_lod_change = now;
    }
  };

  MotionProfiler.prototype.getP95 = function () {
    if (this._p95_window.length === 0) return 16.67;
    var sorted = this._p95_window.slice().sort(function (a, b) { return a - b; });
    var idx = Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95));
    return sorted[idx];
  };

  MotionProfiler.prototype.getLOD = function () {
    return LOD_LEVELS[this._lod];
  };

  MotionProfiler.prototype.getLODIndex = function () {
    return this._lod;
  };

  MotionProfiler.prototype.setLOD = function (idx) {
    this._lod = Math.max(0, Math.min(LOD_LEVELS.length - 1, idx));
    this._last_lod_change = this._nowFn();
  };

  MotionProfiler.prototype.getReport = function () {
    var now = this._nowFn();
    var elapsed = (now - this._session_start) / 1000;
    return {
      fps: Math.round(this._fps_ema * 10) / 10,
      p95_frame_ms: Math.round(this.getP95() * 100) / 100,
      target_fps: this._target_fps,
      frame_count: this._frame_count,
      long_frames: this._long_frames,
      dropped_frames: this._dropped_frames,
      lod: this.getLOD(),
      lod_index: this._lod,
      session_seconds: Math.round(elapsed * 10) / 10,
      healthy: this._fps_ema >= this._target_fps * 0.9
    };
  };

  MotionProfiler.LOD_LEVELS = LOD_LEVELS;
  MotionProfiler.VERSION = VERSION;

  var api = {
    VERSION: VERSION,
    create: function (opts) { return new MotionProfiler(opts); },
    LOD_LEVELS: LOD_LEVELS
  };

  if (typeof global !== "undefined") {
    global.CherryMotionProfiler = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
