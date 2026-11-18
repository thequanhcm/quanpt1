/*!
 * CHERRY MOTION HEARTBEAT — Sprint V7-M6 (18/11/2026)
 * =========================================================================
 * Bộ điều phối TRUNG TÂM. Kết nối 8 module đã build (physics, head,
 * saccade, audio_mouth, body_motion, micro_expression, motion_blender,
 * muscle_controllers) thành 1 "thể thống nhất" — đúng tuyên ngôn V6.
 *
 * Mỗi frame @60Hz:
 *   1. Blender.tick() → state vector (brow/smile/mouth/jaw/head/body)
 *   2. MuscleControllers.setTarget(state) + update() → muscle state
 *   3. HeadDynamics.setTarget(state.head) + update() → pose
 *   4. SaccadeEngine.tick() → gaze + blink
 *   5. AudioMouthDriver.tick() → mouth open/jaw/spread (override blender)
 *   6. MicroExpression.subscribe → blend in micro
 *   7. MotionProfiler.tick() → FPS report
 *
 * Engine này chỉ READ từ các module, KHÔNG tự quyết định.
 *
 * Fail-open: nếu thiếu module nào → engine vẫn chạy với phần còn lại.
 *
 * Xuất global: window.CherryMotionHeartbeat = {
 *   create, start, stop, tick, getFrameState, setEmotion, getReport,
 *   VERSION
 * }
 */
(function (global) {
  "use strict";

  var VERSION = "v7m6_1811";

  function MotionHeartbeat(opts) {
    opts = opts || {};
    this._physics = opts.physics || global.CherryPhysics;
    this._nowFn = opts.nowFn || (typeof performance !== "undefined"
      ? function () { return performance.now(); }
      : function () { return Date.now(); });

    // Module references — fail-open nếu thiếu
    this._blender = opts.blender || (global.CherryMotionBlender &&
      global.CherryMotionBlender.create({ physics: this._physics }));
    this._muscle = opts.muscle || (global.CherryMuscleControllers &&
      global.CherryMuscleControllers.create({ physics: this._physics }));
    this._head = opts.head || (global.CherryHeadDynamics &&
      global.CherryHeadDynamics.create({ physics: this._physics }));
    this._saccade = opts.saccade || (global.CherrySaccadeEngine &&
      global.CherrySaccadeEngine.create({ physics: this._physics }));
    this._mouth = opts.mouth || (global.CherryAudioMouthDriver &&
      global.CherryAudioMouthDriver.create({ physics: this._physics }));
    this._micro = opts.micro || (global.CherryMicroExpression &&
      global.CherryMicroExpression.create());
    this._profiler = opts.profiler || (global.CherryMotionProfiler &&
      global.CherryMotionProfiler.create());

    // Trạng thái
    this._running = false;
    this._current_emotion = "IDLE";
    this._frame_state = {};
    this._rafId = null;
    this._last_tick = 0;

    // Wire micro-expression events
    var self = this;
    if (typeof global.addEventListener === "function" && this._micro) {
      global.addEventListener("cherry:micro", function (e) {
        if (!e || !e.detail) return;
        var d = e.detail;
        // Áp micro-expression lên muscle (chỉ phase=start)
        if (d.phase !== "start") return;
        if (!self._muscle) return;
        var intensity = d.intensity || 0.35;
        var cur = self._muscle.getMuscleState();
        // Micro params ghi đè TẠM THỜI vào target, sau duration sẽ tự blend về
        if (d.params && self._muscle._target) {
          for (var k in d.params) {
            if (self._muscle._target.hasOwnProperty(k)) {
              self._muscle._target[k] = cur[k] + d.params[k] * intensity;
            }
          }
        }
      });
    }
  }

  MotionHeartbeat.prototype.start = function () {
    if (this._running) return;
    this._running = true;
    if (this._micro) this._micro.start();
    if (this._profiler) this._profiler.start();
    this._last_tick = this._nowFn();
    var self = this;
    var loop = function () {
      if (!self._running) return;
      var now = self._nowFn();
      var dt = (now - self._last_tick) / 1000;
      self._last_tick = now;
      self.tick(dt);
      if (typeof global.requestAnimationFrame === "function") {
        self._rafId = global.requestAnimationFrame(loop);
      } else {
        self._rafId = setTimeout(loop, 16);
      }
    };
    if (typeof global.requestAnimationFrame === "function") {
      self._rafId = global.requestAnimationFrame(loop);
    } else {
      self._rafId = setTimeout(loop, 16);
    }
  };

  MotionHeartbeat.prototype.stop = function () {
    this._running = false;
    if (this._micro) this._micro.stop();
    if (this._profiler) this._profiler.stop();
    if (this._rafId) {
      if (typeof global.cancelAnimationFrame === "function") {
        global.cancelAnimationFrame(this._rafId);
      } else {
        clearTimeout(this._rafId);
      }
    }
  };

  MotionHeartbeat.prototype.setEmotion = function (emotion) {
    this._current_emotion = emotion;
    if (this._blender) this._blender.blendTo(emotion);
    if (this._micro && this._micro.setIntensity) {
      var intensity_map = {
        SLEEPING: 0.05, OFFLINE: 0.0, IDLE: 0.25,
        LISTENING: 0.40, THINKING: 0.50, SPEAKING: 0.55,
        HAPPY: 0.70, SURPRISED: 0.75, EMPATHETIC: 0.45,
        WARNING: 0.35, ERROR: 0.30
      };
      this._micro.setIntensity(intensity_map[emotion] != null
        ? intensity_map[emotion] : 0.35);
    }
  };

  MotionHeartbeat.prototype.tick = function (dt) {
    if (typeof dt !== "number" || dt <= 0) dt = 0.016;

    // 1. Blender → state vector
    var state = {};
    if (this._blender) {
      this._blender.tick(dt);
      state = this._blender.getCurrent();
    }

    // 2. Muscle: set target từ blender state + update smoothing
    if (this._muscle) {
      this._muscle.setTarget(state);
      this._muscle.update(dt);
    }

    // 3. Head: target + update damping
    if (this._head) {
      this._head.setTarget(state.headYaw, state.headPitch, state.headRoll);
      this._head.update(dt);
    }

    // 4. Saccade: gaze + blink
    if (this._saccade) {
      this._saccade.tick(dt);
    }

    // 5. Mouth: nếu mode=audio/text → ghi đè mouthOpen/jaw/spread
    if (this._mouth) {
      this._mouth.tick(dt);
      var mv = this._mouth.getCurrentViseme();
      // Khi nói, override miệng từ driver
      if (this._current_emotion === "SPEAKING" && mv.intensity > 0.05) {
        if (this._muscle) {
          this._muscle._target.jaw = mv.open;
        }
      }
    }

    // 6. Snapshot frame state
    this._frame_state = {
      t: this._nowFn(),
      emotion: this._current_emotion,
      blender: state,
      muscle: this._muscle ? this._muscle.getMuscleState() : null,
      head: this._head ? this._head.getPose() : null,
      eye: this._saccade ? this._saccade.getGaze() : null,
      mouth: this._mouth ? this._mouth.getCurrentViseme() : null
    };
    return this._frame_state;
  };

  MotionHeartbeat.prototype.getFrameState = function () {
    return Object.assign({}, this._frame_state);
  };

  MotionHeartbeat.prototype.getReport = function () {
    return {
      version: VERSION,
      running: this._running,
      emotion: this._current_emotion,
      modules: {
        blender: !!this._blender,
        muscle: !!this._muscle,
        head: !!this._head,
        saccade: !!this._saccade,
        mouth: !!this._mouth,
        micro: !!this._micro,
        profiler: !!this._profiler
      },
      profiler: this._profiler ? this._profiler.getReport() : null,
      micro: this._micro ? this._micro.getStats() : null
    };
  };

  MotionHeartbeat.VERSION = VERSION;

  var api = {
    VERSION: VERSION,
    create: function (opts) { return new MotionHeartbeat(opts); }
  };

  if (typeof global !== "undefined") {
    global.CherryMotionHeartbeat = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
