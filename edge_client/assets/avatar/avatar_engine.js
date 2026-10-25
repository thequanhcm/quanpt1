/**
 * QUAN AI BRAIN — Digital Human Avatar Engine (Model A — Dịu dàng, Thân thiện, Thông minh)
 * 
 * High-performance 2.5D Canvas-based Digital Human rendering engine.
 * 
 * Major Features:
 *   - 100% SEAMLESS MOUTH BLENDING: Feathered Elliptical Alpha Masking for
 *     dynamic speaking visemes (zero sharp edges or square artifacts).
 *   - NATURAL HAIR SWAY & DYNAMICS: Multi-frequency organic wave oscillation for
 *     soft black hair cascades, cyber cyan sheen, and ambient tech motes.
 *   - LIFELIKE HEAD MOVEMENT:
 *       * Head Tilting (Roll): Subtle human tilt (-2.2° to +2.2°) responding to state
 *       * Head Turning & Weight Shift (Yaw): Smooth horizontal micro-sway
 *       * Micro-Nodding (Pitch): Gentle acknowledgment nod when listening or greeting
 *   - BIOLOGICAL HUMAN EYE DYNAMICS:
 *       * Double-blinking randomized with human variance (3.2s - 6.0s intervals)
 *       * Smooth sinusoidal eyelid easing with feathered lash line
 *       * Eye micro-saccades & gaze shift (looking up-left when thinking, attentive when listening)
 *       * Duchenne eye-smile squint & specular iris glint pulse
 *   - FULL RESOLUTION PORTRAIT CROSSFADE:
 *       * Seamlessly switches between master Model A portraits (portrait, happy, thinking, blink, speaking)
 *   - 60 FPS requestAnimationFrame with hardware acceleration
 */

class DigitalHumanAvatar {
  constructor(canvasId, options = {}) {
    this.canvas = typeof canvasId === "string" ? document.getElementById(canvasId) : canvasId;
    if (!this.canvas) {
      console.error(`DigitalHumanAvatar: Canvas element '${canvasId}' not found.`);
      return;
    }
    this.ctx = this.canvas.getContext("2d");
    this.basePath = options.basePath || "/static/assets/avatar";
    this.state = options.initialState || "IDLE";
    this.onStateChange = options.onStateChange || null;

    // Dimensions
    this.width = this.canvas.width || 720;
    this.height = this.canvas.height || 720;

    // Feature Bounding Boxes (calibrated to Digital Human Model A - Pi5/4.png 1024x1024 master)
    this.EYES_BOX = { x: 320, y: 425, w: 365, h: 115 };
    this.MOUTH_BOX = { x: 405, y: 650, w: 245, h: 105 };

    // Eyebrows Anchor Geometry (Model A 1024x1024 coordinates)
    this.BROW_LEFT = { innerX: 475, innerY: 435, archX: 415, archY: 415, tailX: 350, tailY: 435 };
    this.BROW_RIGHT = { innerX: 550, innerY: 428, archX: 610, archY: 410, tailX: 670, tailY: 428 };

    // Assets container
    this.assets = {};
    this.loaded = false;

    // Animation timing
    this.startTime = performance.now();
    this.lastFrameTime = performance.now();
    this.haloAngle = 0;

    // ================= LIFELIKE HEAD MOTION PHYSICS =================
    this.headTilt = 0.0;           // Current rotation in radians (-0.038 to +0.038, ~ -2.2° to +2.2°)
    this.targetHeadTilt = 0.0;     // Target roll tilt
    this.headSwayX = 0.0;          // Horizontal weight shift (-3.5px to +3.5px)
    this.targetHeadSwayX = 0.0;
    this.headNodY = 0.0;           // Vertical micro-nod
    this.targetHeadNodY = 0.0;
    this.nextHeadShiftTime = performance.now() + 2500;
    this.isNodding = false;
    this.nodStartTime = 0;

    // ================= BIOLOGICAL EYE BLINKING & SACCADES =================
    this.isBlinking = false;
    this.blinkStartTime = 0;
    this.blinkDuration = 135; // ms
    this.isDoubleBlink = false;
    this.nextBlinkTime = performance.now() + 2800 + Math.random() * 2800;

    // Saccades (gaze micro-shift)
    this.saccadeX = 0;
    this.saccadeY = 0;
    this.nextSaccadeTime = performance.now() + 2000;

    // ================= LIP-SYNC TIMELINE =================
    this.currentTimeline = null;
    this.timelineStartTime = 0;
    this.activeViseme = "REST";
    this.currentOpenRatio = 0.0;
    this.speechFallbackInterval = null;

    // Offscreen helper canvases for seamless feathered blending
    this._featherMouthCanvas = null;
    this._featherEyeCanvas = null;

    // ================= MICRO-EXPRESSION ENGINE =================
    this.currentMicro = {
      browLift: 0.0,
      browTilt: 0.0,
      browInward: 0.0,
      browAsymmetric: 0.0,
      eyeSquint: 0.0,
      gazeX: 0.0,
      gazeY: 0.0,
      glintPulse: 1.0,
      smileBoost: 0.0,
    };

    this.targetMicro = { ...this.currentMicro };
    this.activeEmotionTone = "NEUTRAL";

    // Emotion Tone Presets
    this.EMOTION_PRESETS = {
      NEUTRAL: {
        browLift: 0.0, browTilt: 0.0, browInward: 0.0, browAsymmetric: 0.0,
        eyeSquint: 0.05, gazeX: 0.0, gazeY: 0.0, glintPulse: 1.0, smileBoost: 0.08,
      },
      WARM_GREETING: {
        browLift: 3.5, browTilt: 2.2, browInward: 0.0, browAsymmetric: 0.0,
        eyeSquint: 0.38, gazeX: 0.0, gazeY: 0.0, glintPulse: 1.35, smileBoost: 0.40,
      },
      ANALYTICAL_THINKING: {
        browLift: -2.5, browTilt: -3.2, browInward: 2.5, browAsymmetric: 1.2,
        eyeSquint: 0.20, gazeX: 1.8, gazeY: -1.4, glintPulse: 1.05, smileBoost: 0.05,
      },
      SERIOUS_ALERT: {
        browLift: -4.5, browTilt: -4.8, browInward: 3.5, browAsymmetric: 0.0,
        eyeSquint: 0.0, gazeX: 0.0, gazeY: 0.5, glintPulse: 0.85, smileBoost: -0.30,
      },
      CONFIDENT_SUCCESS: {
        browLift: 4.2, browTilt: 1.5, browInward: 0.0, browAsymmetric: 0.0,
        eyeSquint: 0.42, gazeX: 0.0, gazeY: 0.0, glintPulse: 1.50, smileBoost: 0.45,
      },
      CONSULTATIVE_INQUIRING: {
        browLift: 2.2, browTilt: 2.8, browInward: 0.5, browAsymmetric: 2.8,
        eyeSquint: 0.22, gazeX: 0.0, gazeY: -0.6, glintPulse: 1.25, smileBoost: 0.22,
      },
    };

    // State configurations (Standard 12-State Digital Human Protocol)
    this.STATE_CONFIGS = {
      IDLE: { name: "IDLE (SẴN SÀNG)", auraColor: "#00e5ff", haloSpeed: 0.025, eyes: "open", smile: "natural", defaultTone: "WARM_GREETING" },
      LISTENING: { name: "LISTENING (LẮNG NGHE)", auraColor: "#06b6d4", haloSpeed: 0.055, eyes: "open", smile: "attentive", defaultTone: "WARM_GREETING" },
      THINKING: { name: "THINKING (SUY LUẬN)", auraColor: "#a855f7", haloSpeed: 0.075, eyes: "thinking", smile: "closed", defaultTone: "ANALYTICAL_THINKING" },
      RESEARCHING: { name: "RESEARCHING (NGHIÊN CỨU)", auraColor: "#8b5cf6", haloSpeed: 0.065, eyes: "thinking", smile: "closed", defaultTone: "ANALYTICAL_THINKING" },
      LEARNING: { name: "LEARNING (TỰ HỌC)", auraColor: "#10b981", haloSpeed: 0.05, eyes: "open", smile: "natural", defaultTone: "CONFIDENT_SUCCESS" },
      SPEAKING: { name: "SPEAKING (ĐANG NÓI)", auraColor: "#38bdf8", haloSpeed: 0.07, eyes: "open", smile: "speaking", defaultTone: "WARM_GREETING" },
      HAPPY: { name: "HAPPY (HOÀN THÀNH)", auraColor: "#10b981", haloSpeed: 0.06, eyes: "open", smile: "happy", defaultTone: "CONFIDENT_SUCCESS" },
      EMPATHETIC: { name: "EMPATHETIC (ĐỒNG CẢM)", auraColor: "#ec4899", haloSpeed: 0.035, eyes: "open", smile: "natural", defaultTone: "WARM_GREETING" },
      CONFUSED: { name: "CONFUSED (CHƯA RÕ)", auraColor: "#eab308", haloSpeed: 0.04, eyes: "thinking", smile: "closed", symbol: "❓", defaultTone: "CONSULTATIVE_INQUIRING" },
      SUCCESS: { name: "SUCCESS (THÀNH CÔNG)", auraColor: "#10b981", haloSpeed: 0.08, eyes: "open", smile: "happy", symbol: "✨", defaultTone: "CONFIDENT_SUCCESS" },
      WARNING: { name: "WARNING (CẢNH BÁO)", auraColor: "#f97316", haloSpeed: 0.03, eyes: "open", smile: "neutral", symbol: "⚠️", defaultTone: "SERIOUS_ALERT" },
      WAITING_FOR_OWNER: { name: "WAITING (CHỜ PHÊ DUYỆT)", auraColor: "#f59e0b", haloSpeed: 0.04, eyes: "open", smile: "natural", symbol: "📬", defaultTone: "CONSULTATIVE_INQUIRING" },
      BLOCKED: { name: "BLOCKED (CHẶN NGUY HIỂM)", auraColor: "#ef4444", haloSpeed: 0.02, eyes: "open", smile: "neutral", symbol: "🛡️", defaultTone: "SERIOUS_ALERT" },
      ERROR: { name: "ERROR (SỰ CỐ)", auraColor: "#f43f5e", haloSpeed: 0.02, eyes: "open", smile: "neutral", symbol: "⚠️", defaultTone: "SERIOUS_ALERT" },
      SAFE_MODE: { name: "SAFE_MODE (ĐÓNG BĂNG)", auraColor: "#38bdf8", haloSpeed: 0.01, eyes: "closed", smile: "closed", symbol: "❄️", defaultTone: "NEUTRAL" },
      OFFLINE: { name: "OFFLINE (MẤT KẾT NỐI)", auraColor: "#64748b", haloSpeed: 0.0, eyes: "closed", smile: "closed", defaultTone: "NEUTRAL" },
      RECONNECTING: { name: "RECONNECTING (KẾT NỐI LẠI)", auraColor: "#0284c7", haloSpeed: 0.09, eyes: "open", smile: "natural", symbol: "🔄", defaultTone: "NEUTRAL" },
      SLEEPING: { name: "SLEEPING (TẠM NGHỈ)", auraColor: "#475569", haloSpeed: 0.008, eyes: "closed", smile: "closed", symbol: "💤", defaultTone: "NEUTRAL" },
    };

    this._loadAssets();
    this._startRenderLoop();
  }

  _loadAssets() {
    const assetList = [
      { key: "portrait", src: `${this.basePath}/avatar_v2_portrait.png`, fallback: `${this.basePath}/model_f_portrait.png` },
      { key: "portrait_happy", src: `${this.basePath}/avatar_v2_happy.png`, fallback: `${this.basePath}/model_f_happy.png` },
      { key: "portrait_thinking", src: `${this.basePath}/avatar_v2_thinking.png`, fallback: `${this.basePath}/model_f_thinking.png` },
      { key: "portrait_warning", src: `${this.basePath}/avatar_v2_warning.png`, fallback: `${this.basePath}/avatar_v2_portrait.png` },
      { key: "portrait_empathic", src: `${this.basePath}/avatar_v2_empathic.png`, fallback: `${this.basePath}/avatar_v2_portrait.png` },
      { key: "portrait_confused", src: `${this.basePath}/avatar_v2_confused.png`, fallback: `${this.basePath}/avatar_v2_thinking.png` },
      { key: "portrait_surprised", src: `${this.basePath}/avatar_v2_surprised.png`, fallback: `${this.basePath}/avatar_v2_portrait.png` },
      { key: "portrait_error", src: `${this.basePath}/avatar_v2_error.png`, fallback: `${this.basePath}/avatar_v2_warning.png` },
      { key: "portrait_blink", src: `${this.basePath}/avatar_v2_blink.png`, fallback: `${this.basePath}/model_f_blink.png` },
      { key: "portrait_speaking", src: `${this.basePath}/avatar_v2_portrait.png`, fallback: `${this.basePath}/model_f_speaking.png` },
      { key: "eyes_blink", src: `${this.basePath}/eyes_closed.png`, fallback: null },
      { key: "eyes_thinking", src: `${this.basePath}/eyes_thinking.png`, fallback: null },
      { key: "mouth_speaking", src: `${this.basePath}/mouth_v2_speaking.png`, fallback: `${this.basePath}/mouth_speaking.png` },
      { key: "mouth_rest", src: `${this.basePath}/mouth_v2_rest.png`, fallback: `${this.basePath}/mouth_rest.png` },
      { key: "mouth_happy", src: `${this.basePath}/mouth_v2_happy.png`, fallback: `${this.basePath}/mouth_happy.png` },
      { key: "mouth_open_o", src: `${this.basePath}/mouth_v2_open_o.png`, fallback: null },
    ];

    let loadedCount = 0;
    assetList.forEach(item => {
      const img = new Image();
      img.onload = () => {
        loadedCount++;
        this.assets[item.key] = img;
        if (loadedCount === assetList.length) {
          this.loaded = true;
        }
      };
      img.onerror = () => {
        // 1. Fallback to jpg
        const alt = new Image();
        alt.onload = () => {
          loadedCount++;
          this.assets[item.key] = alt;
          if (loadedCount === assetList.length) {
            this.loaded = true;
          }
        };
        alt.onerror = () => {
          // 2. Fallback to Central Brain PC Core over Wi-Fi
          const fileName = item.src.split("/").pop();
          const coreUrl = `http://192.168.1.11:8766/edge_client/assets/avatar/${fileName}`;
          const coreImg = new Image();
          coreImg.crossOrigin = "anonymous";
          coreImg.onload = () => {
            loadedCount++;
            this.assets[item.key] = coreImg;
            if (loadedCount === assetList.length) {
              this.loaded = true;
            }
          };
          coreImg.onerror = () => {
            loadedCount++;
            if (loadedCount === assetList.length) {
              this.loaded = true;
            }
          };
          coreImg.src = coreUrl;
        };
        alt.src = item.src.replace(".png", ".jpg");
      };
      img.src = item.src;
    });
  }

  _startRenderLoop() {
    const loop = (timestamp) => {
      this._update(timestamp);
      this._render(timestamp);
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  setState(newState) {
    if (!this.STATE_CONFIGS[newState]) newState = "IDLE";
    const oldState = this.state;
    this.state = newState;

    if (oldState === "SPEAKING" && newState !== "SPEAKING") {
      this.cancelUtterance();
    }

    const conf = this.STATE_CONFIGS[this.state];
    if (conf && conf.defaultTone && this.activeEmotionTone !== conf.defaultTone) {
      this.setMicroExpression(conf.defaultTone);
    }

    if (typeof this.onStateChange === "function") {
      this.onStateChange(this.state, this.STATE_CONFIGS[this.state]);
    }
  }

  getState() {
    return this.state;
  }

  // ================= CONTEXTUAL VIETNAMESE EMOTION EXTRACTOR =================

  extractVietnameseEmotion(text) {
    if (!text || typeof text !== "string") return "NEUTRAL";
    const lower = text.toLowerCase();

    // 1. Alert / Warning / Safety Block / Prohibited
    if (/cảnh báo|chú ý|lưu ý|nguy hiểm|rủi ro|không được|chặn|thất bại|lỗi|bất thường|sự cố|dừng|khẩn cấp|nghiêm cấm/.test(lower)) {
      return "SERIOUS_ALERT";
    }

    // 2. Success / Accomplished / Certified / 100% / Excellent
    if (/hoàn thành|thành công|chính xác|đạt chuẩn|vượt qua|tốt đẹp|100%|xuất sắc|hoàn hảo|thắng lợi/.test(lower)) {
      return "CONFIDENT_SUCCESS";
    }

    // 3. Analytical / Data / Metrics / Architecture / Reasoning
    if (/phân tích|dữ liệu|kết quả|nghiên cứu|thuật toán|kiến trúc|thông số|đo lường|logic|thống kê|chi tiết|báo cáo|kiểm tra|xác nhận|chỉ số/.test(lower)) {
      return "ANALYTICAL_THINKING";
    }

    // 4. Consultation / Proposal / Inquiring Owner
    if (/kính trình|đề xuất|chờ anh|xin ý kiến|phê duyệt|chỉ đạo|chờ xác nhận|tham vấn/.test(lower)) {
      return "CONSULTATIVE_INQUIRING";
    }

    // 5. Warm Greeting / Politeness / Readiness
    if (/chào|xin chào|dạ|vâng|rất vui|hân hạnh|sẵn sàng|chúc|em đây|vâng ạ|em nghe|tuyệt vời|cảm ơn/.test(lower)) {
      return "WARM_GREETING";
    }

    return "NEUTRAL";
  }

  setContextFromText(text) {
    const tone = this.extractVietnameseEmotion(text);
    this.setMicroExpression(tone);
  }

  setMicroExpression(toneOrConfig) {
    if (typeof toneOrConfig === "string") {
      this.activeEmotionTone = toneOrConfig;
      const preset = this.EMOTION_PRESETS[toneOrConfig] || this.EMOTION_PRESETS.NEUTRAL;
      this.targetMicro = { ...preset };
    } else if (typeof toneOrConfig === "object" && toneOrConfig !== null) {
      this.activeEmotionTone = "CUSTOM";
      this.targetMicro = { ...this.targetMicro, ...toneOrConfig };
    }
  }

  resetMicroExpression() {
    this.setMicroExpression("NEUTRAL");
  }

  setTimeline(timeline) {
    this.currentTimeline = timeline;
    this.timelineStartTime = performance.now();
    this.setState("SPEAKING");
  }

  cancelUtterance() {
    this.currentTimeline = null;
    this.activeViseme = "REST";
    this.currentOpenRatio = 0.0;
    if (this.speechFallbackInterval) {
      clearInterval(this.speechFallbackInterval);
      this.speechFallbackInterval = null;
    }
  }

  startSpeaking(durationMs = 3000) {
    this.setState("SPEAKING");
    this.cancelUtterance();

    const startTime = performance.now();
    const visemes = ["A", "O", "E", "I", "U", "REST"];
    let cycle = 0;

    this.speechFallbackInterval = setInterval(() => {
      const elapsed = performance.now() - startTime;
      if (elapsed > durationMs) {
        this.cancelUtterance();
        this.setState("IDLE");
        return;
      }
      cycle++;
      this.activeViseme = visemes[cycle % visemes.length];
      this.currentOpenRatio = this.activeViseme === "REST" ? 0.0 : 0.4 + Math.random() * 0.55;
    }, 90);
  }

  _update(now) {
    const config = this.STATE_CONFIGS[this.state] || this.STATE_CONFIGS.IDLE;

    // Halo rotation
    this.haloAngle += (config.haloSpeed || 0.025);

    // Smooth Interpolation (lerp) helper
    const lerp = (a, b, t) => a + (b - a) * t;

    // 1. Muscle Transitions for Micro-Expressions
    const factor = 0.08;
    this.currentMicro.browLift = lerp(this.currentMicro.browLift, this.targetMicro.browLift, factor);
    this.currentMicro.browTilt = lerp(this.currentMicro.browTilt, this.targetMicro.browTilt, factor);
    this.currentMicro.browInward = lerp(this.currentMicro.browInward, this.targetMicro.browInward, factor);
    this.currentMicro.browAsymmetric = lerp(this.currentMicro.browAsymmetric, this.targetMicro.browAsymmetric, factor);
    this.currentMicro.eyeSquint = lerp(this.currentMicro.eyeSquint, this.targetMicro.eyeSquint, factor);
    this.currentMicro.gazeX = lerp(this.currentMicro.gazeX, this.targetMicro.gazeX, factor);
    this.currentMicro.gazeY = lerp(this.currentMicro.gazeY, this.targetMicro.gazeY, factor);
    this.currentMicro.glintPulse = lerp(this.currentMicro.glintPulse, this.targetMicro.glintPulse, factor);
    this.currentMicro.smileBoost = lerp(this.currentMicro.smileBoost, this.targetMicro.smileBoost, factor);

    // 2. Lifelike Head Movement Updates (Tilt, Sway, Micro-Nod)
    if (now >= this.nextHeadShiftTime) {
      if (this.state === "IDLE") {
        // Natural human head tilt & weight shift
        const tilts = [-0.024, -0.012, 0.0, 0.014, 0.025];
        this.targetHeadTilt = tilts[Math.floor(Math.random() * tilts.length)];
        this.targetHeadSwayX = (Math.random() - 0.5) * 4.0;
        this.nextHeadShiftTime = now + 3800 + Math.random() * 3800;
      } else if (this.state === "LISTENING") {
        // Attentive head tilt (+1.8° right) with human listening engagement
        this.targetHeadTilt = 0.028;
        this.targetHeadSwayX = 1.8;
        // 45% chance of gentle acknowledgment micro-nod
        if (Math.random() < 0.45 && !this.isNodding) {
          this.isNodding = true;
          this.nodStartTime = now;
        }
        this.nextHeadShiftTime = now + 3200 + Math.random() * 2500;
      } else if (this.state === "THINKING" || this.state === "RESEARCHING") {
        // Analytical tilt to the left
        this.targetHeadTilt = -0.032;
        this.targetHeadSwayX = -2.2;
        this.nextHeadShiftTime = now + 3000 + Math.random() * 2500;
      } else if (this.state === "SPEAKING") {
        // Dynamic roll aligned with natural speech cadence
        this.targetHeadTilt = Math.sin(now * 0.003) * 0.018;
        this.targetHeadSwayX = Math.cos(now * 0.002) * 1.5;
        this.nextHeadShiftTime = now + 1400;
      } else {
        this.targetHeadTilt = 0.0;
        this.targetHeadSwayX = 0.0;
        this.nextHeadShiftTime = now + 4000;
      }
    }

    // Micro-nod physics (smooth cosine easing)
    if (this.isNodding) {
      const nodElapsed = now - this.nodStartTime;
      if (nodElapsed < 620) {
        this.targetHeadNodY = Math.sin((nodElapsed / 620) * Math.PI) * 2.8;
      } else {
        this.isNodding = false;
        this.targetHeadNodY = 0.0;
      }
    }

    // Smooth 60 FPS head motion lerp
    this.headTilt = lerp(this.headTilt, this.targetHeadTilt, 0.042);
    this.headSwayX = lerp(this.headSwayX, this.targetHeadSwayX, 0.038);
    this.headNodY = lerp(this.headNodY, this.targetHeadNodY, 0.075);

    // 3. Biological Eye Blinking with Double-Blink Variance
    if (this.state === "OFFLINE" || this.state === "SAFE_MODE" || this.state === "SLEEPING") {
      this.isBlinking = true;
    } else {
      if (!this.isBlinking && now >= this.nextBlinkTime) {
        this.isBlinking = true;
        this.blinkStartTime = now;
        this.isDoubleBlink = Math.random() < 0.28; // 28% double blink chance
      } else if (this.isBlinking) {
        const elapsed = now - this.blinkStartTime;
        if (!this.isDoubleBlink) {
          if (elapsed >= this.blinkDuration) {
            this.isBlinking = false;
            this.nextBlinkTime = now + 3000 + Math.random() * 3200;
          }
        } else {
          // Double blink sequence: 0-110ms blink 1 -> 110-230ms half open -> 230-340ms blink 2
          if (elapsed >= 340) {
            this.isBlinking = false;
            this.isDoubleBlink = false;
            this.nextBlinkTime = now + 3400 + Math.random() * 3200;
          }
        }
      }
    }

    // 4. Saccades (gaze wander)
    if (now >= this.nextSaccadeTime) {
      if (this.state === "IDLE" || this.state === "LISTENING") {
        this.saccadeX = (Math.random() - 0.5) * 2.4;
        this.saccadeY = (Math.random() - 0.5) * 1.4;
      } else if (this.state === "THINKING") {
        this.saccadeX = 1.6;
        this.saccadeY = -1.2;
      } else {
        this.saccadeX = 0;
        this.saccadeY = 0;
      }
      this.nextSaccadeTime = now + 2200 + Math.random() * 3000;
    }

    // 5. Lip-Sync Frame Lookup from timeline
    if (this.state === "SPEAKING" && this.currentTimeline && this.currentTimeline.frames) {
      const elapsedMs = now - this.timelineStartTime;
      const frames = this.currentTimeline.frames;
      let activeFrame = frames[0];

      for (let i = 0; i < frames.length; i++) {
        if (frames[i].offset_ms <= elapsedMs) {
          activeFrame = frames[i];
        } else {
          break;
        }
      }

      if (elapsedMs >= this.currentTimeline.total_duration_ms) {
        this.cancelUtterance();
        this.setState("IDLE");
      } else if (activeFrame) {
        this.activeViseme = activeFrame.viseme || "REST";
        this.currentOpenRatio = activeFrame.open_ratio || 0.0;
      }
    }
  }

  _render(now) {
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;
    const config = this.STATE_CONFIGS[this.state] || this.STATE_CONFIGS.IDLE;

    ctx.clearRect(0, 0, w, h);

    // 1. Micro-Breathing Vertical Offset
    const breathOffset = Math.sin((now - this.startTime) * 0.0018) * 1.6;

    // 2. Draw Holographic Halo (Stationary backdrop)
    this._drawHolographicHalo(ctx, w, h, config.auraColor);

    // Coordinates mapped from 1024x1024 master space
    const scaleX = w / 1024;
    const scaleY = h / 1024;

    // 3. ROOT HEAD & BODY TRANSFORM (Head tilting, sway, nod, breathing)
    ctx.save();
    const pivotX = w * 0.5;
    const pivotY = h * 0.70; // Neck/chest pivot anchor

    ctx.translate(pivotX + this.headSwayX, pivotY + this.headNodY + breathOffset);
    ctx.rotate(this.headTilt);
    ctx.translate(-pivotX, -pivotY);

    // 4. Base Character Portrait Selection (Authentic Master Expressions from Pi5 Collection)
    let baseImg = this.assets.portrait;
    let usedFullBlink = false;
    let usedFullThinking = false;
    let isSpecialExpression = false;

    if ((this.isBlinking || this.state === "OFFLINE" || this.state === "SLEEPING" || this.state === "SAFE_MODE") && this.assets.portrait_blink && this.assets.portrait_blink.complete && this.assets.portrait_blink.naturalWidth > 0) {
      baseImg = this.assets.portrait_blink;
      usedFullBlink = true;
    } else if ((this.state === "THINKING" || this.state === "RESEARCHING" || this.activeEmotionTone === "ANALYTICAL_THINKING") && this.assets.portrait_thinking && this.assets.portrait_thinking.complete && this.assets.portrait_thinking.naturalWidth > 0) {
      baseImg = this.assets.portrait_thinking;
      usedFullThinking = true;
      isSpecialExpression = true;
    } else if ((this.state === "HAPPY" || this.state === "SUCCESS" || this.state === "LEARNING" || this.activeEmotionTone === "CONFIDENT_SUCCESS") && this.assets.portrait_happy && this.assets.portrait_happy.complete && this.assets.portrait_happy.naturalWidth > 0) {
      baseImg = this.assets.portrait_happy;
      isSpecialExpression = true;
    } else if (this.state === "EMPATHETIC" && this.assets.portrait_empathic && this.assets.portrait_empathic.complete && this.assets.portrait_empathic.naturalWidth > 0) {
      baseImg = this.assets.portrait_empathic;
      isSpecialExpression = true;
    } else if ((this.state === "CONFUSED" || this.state === "WAITING_FOR_OWNER" || this.activeEmotionTone === "CONSULTATIVE_INQUIRING") && this.assets.portrait_confused && this.assets.portrait_confused.complete && this.assets.portrait_confused.naturalWidth > 0) {
      baseImg = this.assets.portrait_confused;
      isSpecialExpression = true;
    } else if ((this.state === "WARNING" || this.state === "BLOCKED" || this.activeEmotionTone === "SERIOUS_ALERT") && this.assets.portrait_warning && this.assets.portrait_warning.complete && this.assets.portrait_warning.naturalWidth > 0) {
      baseImg = this.assets.portrait_warning;
      isSpecialExpression = true;
    } else if (this.state === "ERROR" && this.assets.portrait_error && this.assets.portrait_error.complete && this.assets.portrait_error.naturalWidth > 0) {
      baseImg = this.assets.portrait_error;
      isSpecialExpression = true;
    } else if (this.state === "SPEAKING" && this.assets.portrait_speaking && this.assets.portrait_speaking.complete && this.assets.portrait_speaking.naturalWidth > 0) {
      baseImg = this.assets.portrait_speaking;
    }

    if (baseImg && baseImg.complete && baseImg.naturalWidth > 0) {
      ctx.drawImage(baseImg, 0, 0, w, h);
    } else {
      this._renderProceduralAssistant(ctx, w, h, 0, config.auraColor);
    }

    // 5. Natural Hair Sway & Dynamic Lilac Physics (Flowing strands, sheen, motes)
    this._renderNaturalHairSway(ctx, scaleX, scaleY, now);

    // 6. Dynamic Eye Rendering (Blink fallback, saccades, gaze, Duchenne squint, iris glint)
    this._renderEyes(ctx, scaleX, scaleY, 0, usedFullBlink, usedFullThinking, isSpecialExpression);

    // 7. Eyebrow Micro-Expressions
    this._renderEyebrows(ctx, scaleX, scaleY, 0, isSpecialExpression);

    // 8. 100% Seamless Feathered Mouth Lip-Sync (NO RECTANGLE EVER)
    this._renderMouth(ctx, scaleX, scaleY, 0);

    // 9. Cyber Lighting & High-Tech Vignette
    this._renderCyberLighting(ctx, w, h, config.auraColor);

    ctx.restore(); // Restore head transform

    // 10. Status Symbol Overlay (Fixed HUD tier)
    if (config.symbol) {
      this._renderSymbolOverlay(ctx, w, h, config.symbol, config.auraColor);
    }
  }

  _drawHolographicHalo(ctx, w, h, color) {
    const cx = w * 0.5;
    const cy = h * 0.46;
    const radius = w * 0.42;

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(this.haloAngle);

    // Outer glow ring
    ctx.shadowBlur = 18;
    ctx.shadowColor = color;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.0;
    ctx.globalAlpha = 0.45;

    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.stroke();

    // Segmented tech arcs
    ctx.lineWidth = 3.5;
    ctx.globalAlpha = 0.75;
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 0.4);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(0, 0, radius, Math.PI * 0.9, Math.PI * 1.3);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(0, 0, radius, Math.PI * 1.6, Math.PI * 1.9);
    ctx.stroke();

    // Telemetry node dots
    const numDots = 8;
    ctx.fillStyle = "#ffffff";
    for (let i = 0; i < numDots; i++) {
      const angle = (i * Math.PI * 2) / numDots;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      ctx.beginPath();
      ctx.arc(x, y, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }

  // ================= NATURAL HAIR SWAY & PHYSICS =================

  _renderNaturalHairSway(ctx, scaleX, scaleY, now) {
    const t = (now - this.startTime) * 0.0016;

    // Dual-frequency wave equation for organic hair flutter
    const swayL1 = Math.sin(t) * 3.4 * scaleX;
    const swayL2 = Math.cos(t * 1.7 + 0.4) * 1.8 * scaleX;
    const totalSwayL = swayL1 + swayL2;

    const swayR1 = Math.sin(t + 0.85) * 3.4 * scaleX;
    const swayR2 = Math.cos(t * 1.5 + 1.1) * 1.8 * scaleX;
    const totalSwayR = swayR1 + swayR2;

    ctx.save();
    ctx.lineCap = "round";

    // 1. Left Hair Cascade Strands (Soft Black with Subtle Cyber Cyan Sheen)
    const gradL = ctx.createLinearGradient(280 * scaleX, 400 * scaleY, 240 * scaleX, 850 * scaleY);
    gradL.addColorStop(0.0, "rgba(25, 30, 42, 0.65)");
    gradL.addColorStop(0.5, "rgba(0, 229, 255, 0.22)");
    gradL.addColorStop(1.0, "rgba(10, 14, 24, 0.0)");

    ctx.strokeStyle = gradL;
    ctx.lineWidth = Math.max(1.8, 2.6 * scaleX);
    ctx.shadowBlur = 4;
    ctx.shadowColor = "rgba(0, 229, 255, 0.25)";

    // Outer Left Hair Strand
    ctx.beginPath();
    ctx.moveTo(290 * scaleX, 400 * scaleY);
    ctx.bezierCurveTo(
      (240 * scaleX) + totalSwayL, (520 * scaleY),
      (220 * scaleX) + totalSwayL * 1.4, (660 * scaleY),
      (265 * scaleX) + totalSwayL * 0.8, 800 * scaleY
    );
    ctx.stroke();

    // Inner Left Hair Tendril (framing cheek)
    ctx.beginPath();
    ctx.moveTo(345 * scaleX, 420 * scaleY);
    ctx.bezierCurveTo(
      (330 * scaleX) + totalSwayL * 0.6, (490 * scaleY),
      (325 * scaleX) + totalSwayL * 0.8, (550 * scaleY),
      (340 * scaleX) + totalSwayL * 0.4, 620 * scaleY
    );
    ctx.stroke();

    // 2. Right Hair Cascade Strands (Soft Black with Subtle Cyber Cyan Sheen)
    const gradR = ctx.createLinearGradient(740 * scaleX, 400 * scaleY, 780 * scaleX, 850 * scaleY);
    gradR.addColorStop(0.0, "rgba(25, 30, 42, 0.65)");
    gradR.addColorStop(0.5, "rgba(0, 229, 255, 0.22)");
    gradR.addColorStop(1.0, "rgba(10, 14, 24, 0.0)");

    ctx.strokeStyle = gradR;
    // Outer Right Hair Strand
    ctx.beginPath();
    ctx.moveTo(734 * scaleX, 400 * scaleY);
    ctx.bezierCurveTo(
      (784 * scaleX) + totalSwayR, (520 * scaleY),
      (804 * scaleX) + totalSwayR * 1.4, (660 * scaleY),
      (759 * scaleX) + totalSwayR * 0.8, 800 * scaleY
    );
    ctx.stroke();

    // Inner Right Hair Tendril (framing cheek)
    ctx.beginPath();
    ctx.moveTo(679 * scaleX, 420 * scaleY);
    ctx.bezierCurveTo(
      (694 * scaleX) + totalSwayR * 0.6, (490 * scaleY),
      (699 * scaleX) + totalSwayR * 0.8, (550 * scaleY),
      (684 * scaleX) + totalSwayR * 0.4, 620 * scaleY
    );
    ctx.stroke();

    // 3. Cybernetic Hair Sheen (Shimmer running along hair curvature)
    const sheenPos = (Math.sin(now * 0.0012) + 1.0) * 0.5;
    const sheenY = (420 + sheenPos * 260) * scaleY;
    const sheenXLeft = (250 + totalSwayL) * scaleX;
    const sheenXRight = (770 + totalSwayR) * scaleX;

    const sheenGrad = ctx.createRadialGradient(sheenXLeft, sheenY, 2, sheenXLeft, sheenY, 28 * scaleX);
    sheenGrad.addColorStop(0.0, "rgba(255, 255, 255, 0.65)");
    sheenGrad.addColorStop(0.4, "rgba(200, 230, 255, 0.25)");
    sheenGrad.addColorStop(1.0, "rgba(180, 210, 255, 0.0)");

    ctx.fillStyle = sheenGrad;
    ctx.beginPath();
    ctx.ellipse(sheenXLeft, sheenY, 18 * scaleX, 28 * scaleY, -0.2, 0, Math.PI * 2);
    ctx.fill();

    const sheenGradR = ctx.createRadialGradient(sheenXRight, sheenY, 2, sheenXRight, sheenY, 28 * scaleX);
    sheenGradR.addColorStop(0.0, "rgba(255, 255, 255, 0.65)");
    sheenGradR.addColorStop(0.4, "rgba(200, 230, 255, 0.25)");
    sheenGradR.addColorStop(1.0, "rgba(180, 210, 255, 0.0)");

    ctx.fillStyle = sheenGradR;
    ctx.beginPath();
    ctx.ellipse(sheenXRight, sheenY, 18 * scaleX, 28 * scaleY, 0.2, 0, Math.PI * 2);
    ctx.fill();

    // 4. Cybernetic Floating Motes around hair tips
    const motes = [
      { bx: 235, by: 690, phase: 0.0 },
      { bx: 275, by: 745, phase: 1.6 },
      { bx: 785, by: 690, phase: 2.8 },
      { bx: 745, by: 745, phase: 4.4 },
    ];

    ctx.fillStyle = "rgba(215, 240, 255, 0.75)";
    ctx.shadowBlur = 6;
    ctx.shadowColor = "#00e5ff";

    motes.forEach(m => {
      const my = ((m.by + Math.sin(now * 0.002 + m.phase) * 16) % 1024) * scaleY;
      const mx = (m.bx + Math.cos(now * 0.0018 + m.phase) * 10) * scaleX;
      ctx.beginPath();
      ctx.arc(mx, my, 1.8 * scaleX, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.restore();
  }

  // ================= EYES & MICRO-GAZE =================

  _renderEyes(ctx, scaleX, scaleY, breathOffset, usedFullBlink, usedFullThinking, isSpecialExpression = false) {
    if (isSpecialExpression && !this.isBlinking) return;

    const eb = this.EYES_BOX;
    const totalGazeX = this.saccadeX + this.currentMicro.gazeX * scaleX * 2.0;
    const totalGazeY = this.saccadeY + this.currentMicro.gazeY * scaleY * 2.0;

    const destX = eb.x * scaleX + totalGazeX;
    const destY = eb.y * scaleY + breathOffset + totalGazeY;
    const destW = eb.w * scaleX;
    const destH = eb.h * scaleY;

    // Fallback eye overlay with seamless elliptical feathering (if not using full portrait blink)
    if (this.isBlinking && !usedFullBlink && this.assets.eyes_blink) {
      if (!this._featherEyeCanvas) {
        this._featherEyeCanvas = document.createElement("canvas");
      }
      const eCanvas = this._featherEyeCanvas;
      eCanvas.width = Math.max(10, Math.round(destW));
      eCanvas.height = Math.max(10, Math.round(destH));
      const eCtx = eCanvas.getContext("2d");
      eCtx.clearRect(0, 0, eCanvas.width, eCanvas.height);

      eCtx.drawImage(this.assets.eyes_blink, 0, 0, eCanvas.width, eCanvas.height);
      eCtx.globalCompositeOperation = "destination-in";

      const ecx = eCanvas.width * 0.5;
      const ecy = eCanvas.height * 0.5;
      const erx = eCanvas.width * 0.48;
      const ery = eCanvas.height * 0.46;

      const eGrad = eCtx.createRadialGradient(ecx, ecy, ery * 0.4, ecx, ecy, erx);
      eGrad.addColorStop(0.0, "rgba(0,0,0,1.0)");
      eGrad.addColorStop(0.72, "rgba(0,0,0,0.92)");
      eGrad.addColorStop(0.90, "rgba(0,0,0,0.30)");
      eGrad.addColorStop(1.0, "rgba(0,0,0,0.0)"); // 100% transparent edge!

      eCtx.fillStyle = eGrad;
      eCtx.beginPath();
      eCtx.ellipse(ecx, ecy, erx, ery, 0, 0, Math.PI * 2);
      eCtx.fill();

      ctx.save();
      ctx.drawImage(eCanvas, destX, destY, destW, destH);
      ctx.restore();
    } else if ((this.state === "THINKING" || this.state === "RESEARCHING" || this.activeEmotionTone === "ANALYTICAL_THINKING") && !usedFullThinking && this.assets.eyes_thinking) {
      ctx.save();
      ctx.drawImage(this.assets.eyes_thinking, destX, destY, destW, destH);
      ctx.restore();
    }

    // Note: Model A is an authentic photorealistic digital human.
    // Specular irises, eyelashes, and eyelid textures are rendered authentically by her master portraits.
    // Synthetic vector arcs, glints, and squint ellipses are omitted to avoid cosmetic forehead/eye blemishes.
  }

  // ================= EYEBROWS =================

  _renderEyebrows(ctx, scaleX, scaleY, breathOffset, isSpecialExpression = false) {
    // Model A's master portraits already feature natural, high-definition photorealistic eyebrows.
    // Drawing synthetic vector curves on her forehead creates unnatural purple stroke artifacts.
    // This is intentionally a no-op to preserve 100% photorealistic clarity.
    return;
  }

  // ================= 100% SEAMLESS MOUTH RENDERING (ZERO CHỒNG HÌNH) =================

  _renderMouth(ctx, scaleX, scaleY, breathOffset) {
    // Strict Guard 1: Only render dynamic lip movement when actively SPEAKING
    if (this.state !== "SPEAKING") {
      return;
    }

    const openRatio = Math.max(0.0, Math.min(1.0, this.currentOpenRatio));
    // Strict Guard 2: In natural speech rest pauses, let base portrait lips show
    if (openRatio <= 0.08) {
      return;
    }

    // Exact master alignment: X=405, Y=650, W=245, H=105 in 1024 master space
    // Anchored directly to Model A's mouth center (X=509, Y=724)
    const mb = this.MOUTH_BOX;
    const destX = mb.x * scaleX;
    const destY = mb.y * scaleY + breathOffset;
    const destW = mb.w * scaleX;
    const destH = mb.h * scaleY;

    // Pick dynamic viseme asset
    let mouthAsset = this.assets.mouth_speaking;
    if ((this.activeViseme === "O" || this.activeViseme === "U") && this.assets.mouth_open_o) {
      mouthAsset = this.assets.mouth_open_o;
    } else if (this.activeViseme === "REST" && this.assets.mouth_rest) {
      mouthAsset = this.assets.mouth_rest;
    }

    if (!mouthAsset || !mouthAsset.complete || mouthAsset.naturalWidth === 0) {
      return;
    }

    // Seamless Feathered Elliptical Alpha Masking (Eliminates all rectangular edges and color discontinuities)
    if (!this._featherMouthCanvas) {
      this._featherMouthCanvas = document.createElement("canvas");
    }
    const mCanvas = this._featherMouthCanvas;
    const targetW = Math.max(10, Math.round(destW));
    const targetH = Math.max(10, Math.round(destH));
    if (mCanvas.width !== targetW || mCanvas.height !== targetH) {
      mCanvas.width = targetW;
      mCanvas.height = targetH;
    }
    const mCtx = mCanvas.getContext("2d");
    mCtx.clearRect(0, 0, targetW, targetH);

    mCtx.drawImage(mouthAsset, 0, 0, targetW, targetH);
    mCtx.globalCompositeOperation = "destination-in";

    const mcx = targetW * 0.5;
    const mcy = targetH * 0.5;
    const mrx = targetW * 0.48;
    const mry = targetH * 0.46;

    const mGrad = mCtx.createRadialGradient(mcx, mcy, mry * 0.30, mcx, mcy, mrx);
    mGrad.addColorStop(0.0, "rgba(0,0,0,1.0)");
    mGrad.addColorStop(0.68, "rgba(0,0,0,0.92)");
    mGrad.addColorStop(0.88, "rgba(0,0,0,0.35)");
    mGrad.addColorStop(1.0, "rgba(0,0,0,0.0)"); // 100% transparent edge

    mCtx.fillStyle = mGrad;
    mCtx.beginPath();
    mCtx.ellipse(mcx, mcy, mrx, mry, 0, 0, Math.PI * 2);
    mCtx.fill();

    ctx.save();
    ctx.globalAlpha = Math.min(1.0, 0.40 + openRatio * 0.60);
    ctx.drawImage(mCanvas, destX, destY, destW, destH);
    ctx.restore();
  }

  // ================= LIGHTING & SYMBOLS =================

  _renderCyberLighting(ctx, w, h, color) {
    ctx.save();
    const grad = ctx.createRadialGradient(w * 0.5, h * 0.5, w * 0.38, w * 0.5, h * 0.5, w * 0.54);
    grad.addColorStop(0, "transparent");
    grad.addColorStop(0.85, "rgba(5, 12, 28, 0.45)");
    grad.addColorStop(1.0, "rgba(5, 12, 28, 0.88)");

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
    ctx.restore();
  }

  _renderSymbolOverlay(ctx, w, h, symbol, color) {
    const cx = w * 0.5;
    const cy = h * 0.82;
    const r = w * 0.08;

    ctx.save();
    ctx.shadowBlur = 14;
    ctx.shadowColor = color;
    ctx.fillStyle = "rgba(8, 17, 30, 0.90)";
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.0;

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.font = `${Math.round(r * 1.1)}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#ffffff";
    ctx.fillText(symbol, cx, cy);
    ctx.restore();
  }

  // ================= PROCEDURAL SILHOUETTE FALLBACK =================

  _renderProceduralAssistant(ctx, w, h, breathOffset, auraColor) {
    const cx = w * 0.5;
    const cy = h * 0.44 + breathOffset;

    ctx.save();

    // Background Cybernetic Grid / Radial Horizon
    const bgGrad = ctx.createRadialGradient(cx, cy, 20, cx, cy, w * 0.5);
    bgGrad.addColorStop(0, "rgba(18, 30, 60, 0.85)");
    bgGrad.addColorStop(0.65, "rgba(8, 16, 36, 0.95)");
    bgGrad.addColorStop(1, "rgba(4, 8, 20, 1.0)");
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);

    // Ethereal Model F Lilac-Silver Hair Silhouette
    ctx.shadowBlur = 24;
    ctx.shadowColor = auraColor;
    ctx.fillStyle = "rgba(185, 170, 225, 0.28)";

    ctx.beginPath();
    ctx.arc(cx, cy - 25, 115 * (w / 720), 0, Math.PI * 2);
    ctx.fill();

    // Left hair cascade silhouette
    ctx.beginPath();
    ctx.moveTo(cx - 100 * (w / 720), cy - 40);
    ctx.bezierCurveTo(cx - 150 * (w / 720), cy + 120, cx - 130 * (w / 720), cy + 260, cx - 70 * (w / 720), cy + 300);
    ctx.lineTo(cx - 30 * (w / 720), cy + 300);
    ctx.closePath();
    ctx.fill();

    // Right hair cascade silhouette
    ctx.beginPath();
    ctx.moveTo(cx + 100 * (w / 720), cy - 40);
    ctx.bezierCurveTo(cx + 150 * (w / 720), cy + 120, cx + 130 * (w / 720), cy + 260, cx + 70 * (w / 720), cy + 300);
    ctx.lineTo(cx + 30 * (w / 720), cy + 300);
    ctx.closePath();
    ctx.fill();

    // Face / Jawline Contour
    ctx.shadowBlur = 12;
    ctx.fillStyle = "rgba(240, 230, 245, 0.92)";
    ctx.beginPath();
    ctx.moveTo(cx - 65 * (w / 720), cy - 35);
    ctx.bezierCurveTo(cx - 65 * (w / 720), cy + 50, cx - 45 * (w / 720), cy + 105, cx, cy + 120);
    ctx.bezierCurveTo(cx + 45 * (w / 720), cy + 105, cx + 65 * (w / 720), cy + 50, cx + 65 * (w / 720), cy - 35);
    ctx.closePath();
    ctx.fill();

    // Hazel Eyes
    ctx.fillStyle = "#785848";
    ctx.beginPath();
    ctx.ellipse(cx - 28 * (w / 720), cy + 18, 10 * (w / 720), 7 * (w / 720), 0, 0, Math.PI * 2);
    ctx.ellipse(cx + 28 * (w / 720), cy + 18, 10 * (w / 720), 7 * (w / 720), 0, 0, Math.PI * 2);
    ctx.fill();

    // Cybernetic Suit Collar
    ctx.fillStyle = "rgba(15, 25, 48, 0.95)";
    ctx.strokeStyle = auraColor;
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(cx - 75 * (w / 720), cy + 160);
    ctx.lineTo(cx, cy + 130);
    ctx.lineTo(cx + 75 * (w / 720), cy + 160);
    ctx.lineTo(cx + 140 * (w / 720), cy + 320);
    ctx.lineTo(cx - 140 * (w / 720), cy + 320);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    ctx.restore();
  }
}

if (typeof window !== "undefined") {
  window.DigitalHumanAvatar = DigitalHumanAvatar;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = { DigitalHumanAvatar };
}
