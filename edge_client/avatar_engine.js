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

// M3 EASING (P3 duyệt 16/11): easing chuẩn cho emotion blend — key khớp
// TRANSITION_PRESETS.easing trong emotion_engine.js (s3_1411). Module-level
// (ngoài class) để cả _render lẫn harness đọc được; không đụng global khác.
const M3_EASING = {
  "ease-in-out": (t) => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2,
  "ease-out": (t) => 1 - Math.pow(1 - t, 3),
  "ease-in": (t) => t * t * t,
  "linear": (t) => t,
};

class DigitalHumanAvatar {
  constructor(canvasId, options = {}) {
    this.canvas = typeof canvasId === "string" ? document.getElementById(canvasId) : canvasId;
    if (!this.canvas) {
      console.error(`DigitalHumanAvatar: Canvas element '${canvasId}' not found.`);
      return;
    }
    this.ctx = this.canvas.getContext("2d");
    this.basePath = options.basePath || "/assets/avatar";
    this.state = options.initialState || "IDLE";
    this.onStateChange = options.onStateChange || null;

    // Dimensions
    this.width = this.canvas.width || 720;
    this.height = this.canvas.height || 720;

    // Feature Bounding Boxes (calibrated to Digital Human Model A - Pi5/4.png 1024x1024 master)
    // (14/11 v6emo) Tâm căn lại theo sheet avatar_v3: eyes tâm (496,438), mouth
    // tâm (502,670) — lệch nhẹ so master v2 (eyes 502,482 / mouth 527,702).
    this.EYES_BOX = { x: 316, y: 373, w: 360, h: 130 };
    this.MOUTH_BOX = { x: 427, y: 630, w: 240, h: 100 };

    // (14/11 v6emo) Crossfade portrait state
    this._lastPortraitKey = null;
    this._lastPortraitImg = null;
    this._prevPortrait = null;

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
    // P2 HEAD POSE (V6-001, duyệt 16/11): yaw/pitch/roll quanh trục cổ (độ)
    this.headYaw = 0;      // ±6 — quay trái/phải (lắc đầu)
    this.headPitch = 0;    // ±4 — gật xuống(+)/ngửa(-)
    this.headRoll = 0;     // ±2 — nghiêng đầu qua vai
    this.nextSaccadeTime = performance.now() + 2000;

    // Lip-sync timeline
    this.currentTimeline = null;
    this.timelineStartTime = 0;
    this.activeViseme = "REST";
    this.currentOpenRatio = 0.0;
    this.speechFallbackInterval = null;

    // P1 FACE RIG (V6-001): trạng thái nụ cười rig (0..1, set bởi _renderRigSmile)
    this._rigSmile = 0;

    // Offscreen helper canvases for seamless feathered blending
    this._featherMouthCanvas = null;
    this._featherEyeCanvas = null;
    // (13/11/2026) Body+arms offscreen cache (vẽ thân + tay + đàn keyboard)
    this._bodyCanvas = null;
    this._bodyCacheKey = null;
    // (13/11/2026) Portrait masked offscreen (chỉ giữ đầu + vai, ngực fade dần)
    this._portraitMaskedCanvas = null;
    this._portraitMaskedKey = null;

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
      // (06/11/2026, owner: "đủ đa dạng cử chỉ, giác quan") Tone SURPRISED —
      // kích hoạt portrait_surprised (asset đã có nhưng trước giờ chết code):
      // tin bất ngờ, cảnh báo khẩn chưa xác nhận, sự kiện ngoài dự kiến.
      SURPRISED: {
        browLift: 6.0, browTilt: 0.0, browInward: 0.0, browAsymmetric: 0.0,
        eyeSquint: -0.15, gazeX: 0.0, gazeY: 0.8, glintPulse: 1.6, smileBoost: 0.0,
      },

      // ===== 4 TÔNG ĐỒNG BỘ TỪ PC DASHBOARD (14/11, sprint sync_1314) =====
      APOLOGETIC: {
        browLift: -1.8, browTilt: 2.6, browInward: 2.2, browAsymmetric: 1.6,
        eyeSquint: 0.30, gazeX: 0.0, gazeY: 1.2, glintPulse: 0.90, smileBoost: -0.10,
      },
      CURIOUS: {
        browLift: 4.8, browTilt: 3.6, browInward: 0.0, browAsymmetric: 3.4,
        eyeSquint: 0.12, gazeX: 1.2, gazeY: 0.8, glintPulse: 1.45, smileBoost: 0.18,
      },
      PATIENT_WAITING: {
        browLift: 1.2, browTilt: 1.0, browInward: 0.0, browAsymmetric: 0.0,
        eyeSquint: 0.25, gazeX: 0.0, gazeY: 0.3, glintPulse: 1.10, smileBoost: 0.12,
      },
      PROUD: {
        browLift: 3.0, browTilt: 0.8, browInward: 0.0, browAsymmetric: 0.0,
        eyeSquint: 0.45, gazeX: 0.0, gazeY: -0.4, glintPulse: 1.55, smileBoost: 0.38,
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

      // ===== 4 STATE ĐỒNG BỘ TỪ PC DASHBOARD 22-STATE (14/11, sprint sync_1314) =====
      APOLOGETIC: { name: "APOLOGETIC (XIN LỖI)", auraColor: "#94a3b8", haloSpeed: 0.025, eyes: "open", smile: "closed", symbol: "🙏", defaultTone: "APOLOGETIC" },
      CURIOUS: { name: "CURIOUS (TÒ MÒ)", auraColor: "#0ea5e9", haloSpeed: 0.055, eyes: "thinking", smile: "natural", symbol: "🤔", defaultTone: "CURIOUS" },
      PROUD: { name: "PROUD (TỰ HÀO)", auraColor: "#f59e0b", haloSpeed: 0.07, eyes: "open", smile: "happy", symbol: "🌟", defaultTone: "PROUD" },
      SURPRISED: { name: "SURPRISED (NGẠC NHIÊN)", auraColor: "#8b5cf6", haloSpeed: 0.10, eyes: "open", smile: "neutral", symbol: "😯", defaultTone: "SURPRISED" },
      // M4a fallback (protocol là nguồn sự thật — bản này chỉ khi protocol thiếu)
      GOODBYE: { name: "GOODBYE (TẠM BIỆT)", auraColor: "#00e5ff", haloSpeed: 0.05, eyes: "open", smile: "happy", symbol: "👋", defaultTone: "WARM_GREETING" },
    };

    // Sprint 1 (14/11): Unified Emotion Protocol — avatar_protocol.js là NGUỒN
    // SỰ THẬT khi đã nạp (script tag đứng trước engine); khối literal trên chỉ
    // là fallback khẩn cấp khi protocol file thiếu. Cả PC lẫn Pi5 dùng chung 1
    // file protocol → cùng giá trị tuyệt đối.
    const _PROTO = (typeof window !== "undefined" && window.CHERRY_AVATAR_PROTOCOL) ||
      (typeof globalThis !== "undefined" && globalThis.CHERRY_AVATAR_PROTOCOL) || null;
    if (_PROTO) {
      this.EMOTION_PRESETS = _PROTO.EMOTION_PRESETS;
      this.STATE_CONFIGS = _PROTO.STATE_CONFIGS;
      this._protocol = _PROTO;
    }

    // Sprint 2 (14/11): Natural Motion Engine — motion_scheduler.js là NGUỒN
    // SỰ THẬT cho MotionScheduler + Gesture Library. Cả PC lẫn Pi5 dùng chung.
    const _MOTION = (typeof window !== "undefined" && window.CHERRY_MOTION_SCHEDULER) ||
      (typeof globalThis !== "undefined" && globalThis.CHERRY_MOTION_SCHEDULER) || null;
    if (_MOTION) {
      this._motion = _MOTION;
      this._scheduler = new _MOTION.MotionScheduler();
      this._lastGestureName = null;
    }

    // Sprint 3 (14/11): Expressive Emotion Engine — emotion_engine.js là NGUỒN
    // SỰ THẬT cho EmotionTransitionEngine + Intensity + Micro + Context-aware.
    // Cả PC lẫn Pi5 dùng chung. setState() sẽ đi qua transitionTo() thay vì
    // set trực tiếp → chuyển cảm xúc mượt (duration/easing/hold).
    const _EMOTION = (typeof window !== "undefined" && window.CherryEmotionEngine) ||
      (typeof globalThis !== "undefined" && globalThis.CherryEmotionEngine) || null;
    if (_EMOTION) {
      this._emotion = _EMOTION;
      this._emotionEngine = new _EMOTION.EmotionTransitionEngine();
    }

    // Sprint 4 (14/11): Natural Voice & Lip-Sync — audio_mouth_driver.js là
    // NGUỒN SỰ THẬT cho AudioMouthDriver (audio-driven mouth + interrupt +
    // barge-in). Cả PC lẫn Pi5 dùng chung. startSpeaking() sẽ dùng driver
    // thay vì timer fallback 90ms → miệng theo audio thật (Gate 4).
    const _AUDIO = (typeof window !== "undefined" && window.CherryAudioMouthDriver) ||
      (typeof globalThis !== "undefined" && globalThis.CherryAudioMouthDriver) || null;
    if (_AUDIO) {
      this._audio = _AUDIO;
      this._mouthDriver = new _AUDIO.AudioMouthDriver({
        onViseme: (viseme, open) => {
          this.activeViseme = viseme;
          this.currentOpenRatio = open;
        }
      });
    }

    // Sprint 5 (14/11): Human-Like Interaction — presence_engine.js là NGUỒN
    // SỰ THẬT cho PresenceEngine (eye contact + listening + idle + continuity).
    // Cả PC lẫn Pi5 dùng chung. Render loop sẽ tick presence mỗi frame →
    // gaze + eye contact tự nhiên (Gate 5).
    const _PRESENCE = (typeof window !== "undefined" && window.CherryPresenceEngine) ||
      (typeof globalThis !== "undefined" && globalThis.CherryPresenceEngine) || null;
    if (_PRESENCE) {
      this._presence = _PRESENCE;
      this._presenceEngine = new _PRESENCE.PresenceEngine();
    }

    // Sprint 6 (14/11): Body Motion Engine — body_motion_engine.js là NGUỒN
    // SỰ THẬT cho BodyMotionEngine (shoulder sway + body lean + breathing +
    // arm reach + speech sync). Cả PC lẫn Pi5 dùng chung. Render loop sẽ
    // tick body motion mỗi frame → hình thể linh hoạt uyển chuyển (Gate 6).
    const _BODY = (typeof window !== "undefined" && window.CherryBodyMotionEngine) ||
      (typeof globalThis !== "undefined" && globalThis.CherryBodyMotionEngine) || null;
    if (_BODY) {
      this._body = _BODY;
      this._bodyMotionEngine = new _BODY.BodyMotionEngine();
    }

    this._loadAssets();
    this._startRenderLoop();
  }

  _loadAssets() {
    const assetList = [
      // (14/11 v6emo) Portrait cảm xúc THẬT sheet anh Quân cung cấp (avatar_v3_*)
      // làm primary; avatar_v2_* giữ làm fallback. 2 slot mới: listening + dreamy.
      { key: "portrait", src: `${this.basePath}/avatar_v3_thu_thai.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_portrait.png` },
      { key: "portrait_happy", src: `${this.basePath}/avatar_v3_vui_suong.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_happy.png` },
      { key: "portrait_thinking", src: `${this.basePath}/avatar_v3_tap_trung.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_thinking.png` },
      // (14/11 v6emo) tuc_gian = biểu cảm tức giận thật thay cho confused-trầm-tư cũ
      { key: "portrait_warning", src: `${this.basePath}/avatar_v3_tuc_gian.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_confused.png` },
      { key: "portrait_empathic", src: `${this.basePath}/avatar_v3_buon_ba.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_empathic.png` },
      { key: "portrait_confused", src: `${this.basePath}/avatar_v3_nghieng_dau.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_confused.png` },
      { key: "portrait_surprised", src: `${this.basePath}/avatar_v3_ngac_nhien.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_surprised.png` },
      { key: "portrait_error", src: `${this.basePath}/avatar_v3_tap_trung.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_error.png` },
      { key: "portrait_blink", src: `${this.basePath}/avatar_v3_chop_mat.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_blink.png` },
      { key: "portrait_speaking", src: `${this.basePath}/avatar_v3_dang_noi.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_portrait.png` },
      // (14/11 v6emo) 2 slot MỚI: lắng nghe + mơ mộng (chờ duyệt / kết nối lại)
      { key: "portrait_listening", src: `${this.basePath}/avatar_v3_lang_nghe.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_portrait.png` },
      { key: "portrait_dreamy", src: `${this.basePath}/avatar_v3_mo_mong.png?v=v6full2_1511`, fallback: `${this.basePath}/avatar_v2_portrait.png` },
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
    // (31/10/2026) AUDIT HIỆU NĂNG: 60 FPS trên SwiftShader (software GL) ngốn
    // ~300% CPU → nhiệt 66°C, phản ứng chậm. Màn DSI 800x480 không cần 60 FPS:
    // giới hạn 15 FPS (66ms/frame) — mắt thường vẫn mượt, CPU giảm ~4 lần.
    // (06/11/2026, owner: "hình thể mượt nhất") IDLE/SLEEPING 12 FPS đủ (ít chuyển
    // động), SPEAKING/LISTENING/THINKING 24 FPS cho lip-sync + đầu mượt theo giọng —
    // thích ứng theo trạng thái thay vì cap cứng một mức.
    this._lastFrameTs = 0;
    // M5a (duyệt 16/11): FPS meter THẬT — đo tần suất frame render + thời gian
    // render mỗi frame; window.__cherryPerf để kiosk.js/benchmark đọc.
    this._fpsWindowStart = performance.now();
    this._fpsWindowFrames = 0;
    this._fpsWindowRenderMs = 0;
    const loop = (timestamp) => {
      const cap = this._frameIntervalMs();
      if (timestamp - this._lastFrameTs >= cap) {
        this._lastFrameTs = timestamp;
        const rStart = performance.now();
        this._update(timestamp);
        this._render(timestamp);
        const rMs = performance.now() - rStart;
        this._fpsWindowFrames++;
        this._fpsWindowRenderMs += rMs;
        const wEl = timestamp - this._fpsWindowStart;
        if (wEl >= 10000) {  // cửa sổ 10s → fps trung bình thật
          this._lastMeasuredFps = Math.round(this._fpsWindowFrames / (wEl / 1000) * 10) / 10;
          this._lastAvgRenderMs = Math.round(this._fpsWindowRenderMs / this._fpsWindowFrames * 100) / 100;
          this._fpsWindowStart = timestamp;
          this._fpsWindowFrames = 0;
          this._fpsWindowRenderMs = 0;
        }
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  /* M5a: chỉ số hiệu năng thật (đọc từ ngoài — kiosk.js đẩy lên daemon). */
  getPerfStats() {
    return {
      fps_target: Math.round(1000 / this._frameIntervalMs()),
      fps_measured: this._lastMeasuredFps || null,
      render_ms_avg: this._lastAvgRenderMs || null,
      perf_profile: this._perfProfile || "NORMAL",
    };
  }

  /* M5b: PROFILE A — giảm chi phí khi CPU cao (Edge Agent phát hiện, daemon
     đẩy xuống qua to_kiosk_dict → kiosk.js gọi hàm này).
     LOW  : IDLE/SLEEPING 8 FPS, SPEAKING 15 FPS, tắt micro-saccade, particles nửa.
     NORMAL: bảng FPS thích ứng theo state như cũ (12/18/24). */
  setPerfProfile(profile) {
    const p = profile === "LOW" ? "LOW" : "NORMAL";
    if (this._perfProfile === p) return p;
    this._perfProfile = p;
    return p;
  }

  _frameIntervalMs() {
    // M5b: PROFILE LOW — cap cứng thấp hơn mọi state (CPU quá tải → ưu tiên hạ nhiệt)
    if (this._perfProfile === "LOW") {
      switch (this.state) {
        case "SPEAKING": return 66;   // ~15 FPS — vẫn đủ lip-sync nhìn được
        case "LISTENING":
        case "THINKING": return 100;  // ~10 FPS
        default: return 125;          // ~8 FPS — IDLE/SLEEPING tiết kiệm tối đa
      }
    }
    switch (this.state) {
      case "SPEAKING": return 42;  // ~24 FPS — miệng + đầu theo nhịp giọng
      case "LISTENING":
      case "THINKING":
      case "RESEARCHING": return 56; // ~18 FPS
      default: return 83;          // ~12 FPS — IDLE/SLEEPING tiết kiệm CPU
    }
  }

  setState(newState) {
    // Sprint 1 (14/11): state lạ/cũ → state canonical qua protocol (aliases).
    if (this._protocol && this._protocol.normalizeState) {
      newState = this._protocol.normalizeState(newState);
    }
    if (!this.STATE_CONFIGS[newState]) newState = "IDLE";
    const oldState = this.state;
    this.state = newState;

    if (oldState === "SPEAKING" && newState !== "SPEAKING") {
      this.cancelUtterance();
    }

    // Sprint 2 (14/11): clear scheduler khi đổi state — motion cũ không
    // chạy đè lên state mới (interrupt by design §3.1).
    if (this._scheduler && oldState !== newState) {
      this._scheduler.clear();
    }

    // Sprint 3 (14/11): đi qua EmotionTransitionEngine — chuyển cảm xúc mượt
    // (duration/easing/hold) thay vì set trực tiếp. Cùng state → adjust micro.
    if (this._emotionEngine) {
      this._emotionEngine.transitionTo(newState);
    }

    const conf = this.STATE_CONFIGS[this.state];
    if (conf && conf.defaultTone && this.activeEmotionTone !== conf.defaultTone) {
      this.setMicroExpression(conf.defaultTone);
    }

    if (typeof this.onStateChange === "function") {
      this.onStateChange(this.state, this.STATE_CONFIGS[this.state]);
    }
  }

  // Sprint 2 (14/11): playGesture(context) — chọn gesture theo context, đẩy
  // motions vào scheduler. Trả về tên gesture đã chọn (hoặc null).
  playGesture(context) {
    if (!this._motion || !this._scheduler) return null;
    const pick = this._motion.selectGesture(context, this._lastGestureName);
    if (!pick) return null;
    this._lastGestureName = pick.name;
    for (const m of pick.gesture.motions) {
      this._scheduler.add(m);
    }
    return pick.name;
  }

  getState() {
    return this.state;
  }

  // ================= CONTEXTUAL VIETNAMESE EMOTION EXTRACTOR =================

  extractVietnameseEmotion(text) {
    // Sprint 1 (14/11): extractor hợp nhất sống trong avatar_protocol.js —
    // hàm này chỉ còn là fallback khi protocol file chưa nạp.
    if (this._protocol && this._protocol.extractVietnameseEmotion) {
      return this._protocol.extractVietnameseEmotion(text);
    }
    if (!text || typeof text !== "string") return "NEUTRAL";
    let lower = text.toLowerCase();
    // (31/10) TTS/telemetry hay gửi text KHÔNG DẤU — chuẩn hóa: bỏ dấu để
    // regex tiếng Việt có dấu khớp cả hai dạng.
    try {
      lower = lower.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d");
    } catch (_) {}

    // 0. (14/11 sync_1314) Apology rõ ràng → đồng cảm trước — khớp PC dashboard:
    // "xin lỗi anh, em gặp sự cố" là lời xin lỗi, không phải cảnh báo
    if (/xin loi|chia buon|rat tiec|dang tiec|gay phien/.test(lower)) {
      return "APOLOGETIC";
    }

    // 1. Alert / Warning / Safety Block / Prohibited
    if (/canh bao|chuy|luu y|nguy hiem|rui ro|khong duoc|chan|that bai|loi |bi loi|bat thuong|su co|dung |khan cap|nghiem cam/.test(lower)) {
      return "SERIOUS_ALERT";
    }

    // 1b. (06/11/2026) Bất ngờ / khẩn cấp / đột xuất — tone SURPRISED mới
    if (/bat ngo|ngac nhien|dang le|khong mong doi|khan|dot xuat|mau than|choang|bat thuong|on ao/.test(lower)) {
      return "SURPRISED";
    }

    // 2. Success / Accomplished / Certified / 100% / Excellent
    if (/hoan thanh|thanh cong|chinh xac|dat chuan|vuot qua|tot dep|100%|xuat sac|hoan hao|thang loi/.test(lower)) {
      return "CONFIDENT_SUCCESS";
    }

    // 3. Analytical / Data / Metrics / Architecture / Reasoning
    if (/phan tich|du lieu|ket qua|nghien cuu|thuat toan|kien truc|thong so|do luong|logic|thong ke|chi tiet|bao cao|kiem tra|xac nhan|chi so/.test(lower)) {
      return "ANALYTICAL_THINKING";
    }

    // 4. Consultation / Proposal / Inquiring Owner
    if (/inh trinh|de xuat|cho anh|xin kien|phe duyet|chi dao|cho xac nhan|tham van/.test(lower)) {
      return "CONSULTATIVE_INQUIRING";
    }

    // 5. Warm Greeting / Politeness / Readiness
    if (/chao|xin chao|da |vang |rat vui|han hanh|san sang|chuc|em day|em nghe|tuyet voi|cam on/.test(lower)) {
      return "WARM_GREETING";
    }

    // 7. (14/11 sync_1314) Curiosity — khớp PC dashboard
    if (/tai sao|nhu the nao|the nao|lam sao|giai thich|cho em hoi|thac mac|to mo|muon biet|hoi anh|cau hoi/.test(lower)) {
      return "CURIOUS";
    }

    // 9. (14/11 sync_1314) Pride — khớp PC dashboard
    if (/tu hao|cai thien|tien bo|toi uu|nang cap|hoan thien|phat trien|nhat quan|on dinh|hoc duoc|nam bat/.test(lower)) {
      return "PROUD";
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

  // (06/11/2026, owner: "hình chuyển động theo giọng nói") Nguồn năng lượng
  // THẬT từ audio đang phát (WebAudio AnalyserNode do kiosk.js cấp). Khi có,
  // miệng + gật đầu dẫn động theo amplitude thay vì chỉ timeline chữ.
  setLiveAudioMeter(fn) {
    this._liveAudioMeter = typeof fn === "function" ? fn : null;
  }

  cancelUtterance() {
    this.currentTimeline = null;
    this.activeViseme = "REST";
    this.currentOpenRatio = 0.0;
    if (this.speechFallbackInterval) {
      clearInterval(this.speechFallbackInterval);
      this.speechFallbackInterval = null;
    }
    // Sprint 4 (14/11): dừng mouth driver nếu đang chạy
    if (this._mouthDriver && this._mouthDriver.isActive()) {
      this._mouthDriver.stop("cancel");
    }
  }

  /* Sprint 4 (14/11): setAudioSource — kiosk.js gọi để wire audio element
     + analyser vào engine. Sau đó startSpeaking() sẽ dùng mouth driver. */
  setAudioSource(audio, analyser) {
    this._currentAudio = audio;
    this._currentAnalyser = analyser;
  }

  /* Sprint 4 (14/11): bargeIn — người dùng ngắt lời. */
  bargeIn() {
    if (this._mouthDriver && this._mouthDriver.isActive()) {
      this._mouthDriver.bargeIn();
    }
    this.cancelUtterance();
    this.setState("IDLE");
  }

  /* M4a (duyệt 16/11): playGoodbye — phun state GOODBYE (gật chào 2 nhịp +
     lean-back + tự về IDLE sau 2.5s). Gọi khi KẾT THÚC phát thoại có tone tích
     cực (tạm biệt lịch sự) hoặc kiosk yêu cầu tường minh. */
  playGoodbye() {
    this.cancelUtterance();
    this.setState("GOODBYE");
    return "GOODBYE";
  }

  startSpeaking(durationMs = 3000) {
    this.setState("SPEAKING");
    this.cancelUtterance();

    // Sprint 4 (14/11): nếu có mouth driver + audio element → dùng driver
    // (audio-driven). Nếu không → giữ timer fallback (backward compat).
    if (this._mouthDriver && this._currentAudio) {
      this._mouthDriver.start(this._currentAudio, {
        existingAnalyser: this._currentAnalyser
      });
      return;
    }

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
      // Fallback: use smooth bell-curve envelope instead of random viseme
      // This prevents the "chewing" artifact when timeline is missing
      const phase = (cycle % 6) / 6.0;
      const envelope = Math.sin(Math.PI * phase); // Bell curve: 0→1→0
      this.activeViseme = visemes[cycle % 5]; // Cycle through A/O/E/I/U
      this.currentOpenRatio = 0.35 * envelope; // Smooth opening/closing, no random
    }, 90);
  }

  _update(now) {
    let config = this.STATE_CONFIGS[this.state] || this.STATE_CONFIGS.IDLE;

    // Sprint 5 (14/11): tick presence engine → gaze + eye contact tự nhiên
    if (this._presenceEngine) {
      this._presenceEngine.setState(this.state);
      const gaze = this._presenceEngine.tick(now);
      this.targetMicro.gazeX = gaze.gazeX;
      this.targetMicro.gazeY = gaze.gazeY;
    }

    // Sprint 6 (14/11): tick body motion engine → shoulder sway + body lean
    // + breathing + arm reach + speech sync. Apply vào targetBody để render
    // loop vẽ body theo transform.
    if (this._bodyMotionEngine) {
      this._bodyMotionEngine.setState(this.state);
      // Sync speaking + speech energy từ mouth driver (Sprint 4).
      // (TASK001 audit 14/11) FIX: API thật của driver là getCurrent() →
      // {viseme, open, envelope, active}. Bản trước gọi getCurrentEnergy()
      // KHÔNG TỒN TẠI → TypeError mỗi frame → render loop crash → CPU 110%
      // + avatar đứng yên trên Pi5. Dùng getCurrent().envelope (0..1).
      if (this._mouthDriver) {
        const mouth = this._mouthDriver.getCurrent();
        this._bodyMotionEngine.setSpeaking(this._mouthDriver.isActive());
        this._bodyMotionEngine.setSpeechEnergy(mouth ? (mouth.envelope || 0) : 0);
      }
      const bodyTransform = this._bodyMotionEngine.tick(now);
      this.targetBody = bodyTransform;
    }

    // (31/10) TONE AURA OVERRIDE: màu hào quang/viền theo CẢM XÚC CÂU NÓI
    // (khách quan nhìn thấy ngay cả khi portrait nền không đổi được):
    if (this.activeEmotionTone === "SERIOUS_ALERT") {
      config = { ...config, auraColor: "#ef4444", haloSpeed: 0.05, symbol: "⚠️" };
    } else if (this.activeEmotionTone === "CONFIDENT_SUCCESS") {
      config = { ...config, auraColor: "#10b981", haloSpeed: 0.07 };
    } else if (this.activeEmotionTone === "ANALYTICAL_THINKING") {
      config = { ...config, auraColor: "#a855f7" };
    } else if (this.activeEmotionTone === "CONSULTATIVE_INQUIRING") {
      config = { ...config, auraColor: "#eab308" };
    }

    // Halo rotation
    this.haloAngle += (config.haloSpeed || 0.025);

    // Smooth Interpolation (lerp) helper
    const lerp = (a, b, t) => a + (b - a) * t;

    // M3b (P3 duyệt 16/11): MICRO LERP THEO EASING + INTENSITY — thay factor
    // cứng 0.08. Progress transition (easing theo preset) × intensity (clamp
    // 0.1..1) → chuyển nhanh khi SERIOUS_ALERT (120ms), chậm khi SLEEPING
    // (900ms); intensity thấp → biểu cảm dịu. Không transition → base 0.08
    // (hành vi cũ, không hồi quy micro khi idle).
    let factor = 0.08;
    if (this._emotionEngine) {
      const snapNow = this._emotionEngine.getCurrent();
      const prog = this._emotionEngine.getProgress(now);
      if (prog !== null) {
        const eased = this._m3Ease && this._m3Ease.fn ? this._m3Ease.fn(prog) : prog;
        const inten = Math.max(0.1, Math.min(1, snapNow.intensity || 0.5));
        factor = Math.max(0.02, Math.min(0.6, eased * (0.12 + inten * 0.5)));
      }
    }

    // 1. Muscle Transitions for Micro-Expressions
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
        // (06/11/2026, owner: "hình chuyển động theo giọng nói") Đầu GẬT THEO
        // NHỊP LỜI NÓI: dùng open_ratio hiện tại của lip-sync làm xung gật đầu —
        // mỗi âm tiết mở miệng mạnh → gật nhẹ xuống, khép → nâng lên. Cộng thêm
        // cadence sin chậm để không máy móc. Khi không có timeline vẫn có sway.
        const speechPulse = this.currentOpenRatio; // 0..1 theo timeline/fallback
        // (15/11/2026 v6mou — REF: mẫu.mp4) nhịp gật-theo-lời: viseme chính
        // 0.64 Hz (chu kỳ 1.56s) → lớp cadence 4.03 rad/s rất nhẹ, cộng gật
        // theo openRatio — đầu "đi theo" câu nói như ca sĩ trong mẫu.
        const speechCadence = Math.sin(now * 0.00403) * 0.9;
        // (15/11/2026 v6mot — REF: 6.mp4) GẬT-THEO-CÂU: người nói camera gật
        // nhè nhẹ theo CỤM TỪ (chu kỳ 1.4–4s, V/H 1.11–1.55 — gật dọc CHỦ ĐẠO,
        // ngược ca sĩ 3/4/5). Lớp sin chậm 0.44 rad/s (~14.3s khớp FFT 4.mp4)
        // cộng xung openRatio → đầu gật theo câu nói thật, không máy móc.
        const phraseNod = Math.sin(now * 0.00044 + 1.1) * 1.1; // ~14.3s
        this.targetHeadNodY = speechPulse * 3.2 + speechCadence * 0.8 + phraseNod;
        this.targetHeadTilt = Math.sin(now * 0.003) * 0.014 + speechPulse * 0.008;
        this.targetHeadSwayX = Math.cos(now * 0.002) * 1.2 + speechCadence * 0.4;
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

    // (15/11/2026 v6cin) OWNER: tham chiếu video vi1/vi2 (cinematic female) —
    // đầu nghiêng chậm theo nhịp 20.8s (optical flow FFT) + lớp vi mô 6.2s.
    // Biên độ nhỏ (0.6° tilt, 1.2px sway) để KHÔNG đè lên micro-expression
    // từ scheduler (priority 30+). Chỉ áp dụng khi scheduler không active.
    // (15/11/2026 v6mot — REF: 3/4/5.mp4 + 6.mp4) NÂNG CẤP 2 LỚP:
    //   1) LATERAL LEAN ±1.0° chu kỳ ~10s (FFT head 9.1–12.5s cả 3 video ca sĩ)
    //      + micro sway ngang 0.8px — nghiêng ngang mượt như "đổi trọng tâm".
    //   2) MICRO-REST 87% (6.mp4 người nói camera still 87–98%): khi speechEnergy
    //      ≈0 (không nói) → toàn bộ lớp cinematic co còn ~35%: gần như đứng im,
    //      chỉ còn "thở". Khi nói → đầy đủ để chuyển động theo câu.
    if (!this._scheduler || !this._scheduler._activeGesture) {
      const t = (now - this.startTime) * 0.001;
      const cinematicSway = Math.sin(t * 1.013) * 1.2; // ~6.2s/vòng
      const lateralSway = Math.cos(t * 0.534) * 0.8; // ~11.8s — ngang, đè nhẹ
      const phraseSway = Math.sin(t * 0.628) * 1.2; // ~10s (FFT 9.1–12.5s) — ngang
      // MICRO-REST (v6mot): energy 0..1 từ mouth driver; ≤0.08 → co còn 35%
      let restFactor = 1.0;
      if (this._mouthDriver) {
        const m = this._mouthDriver.getCurrent();
        const energy = m ? (m.envelope || 0) : 0;
        if (energy <= 0.08) restFactor = 0.35;
      }
      // (15/11/2026 v6ges) OWNER: "không xoay khung ảnh" — headTilt KHÔNG còn
      // được cộng vào render (root bỏ ctx.rotate); mọi lớp giờ là sway ngang.
      this.headSwayX += (cinematicSway + lateralSway + phraseSway) * restFactor;
    }

    // Sprint 2 (14/11): tick MotionScheduler — blend motion từ gesture/state.
    // Áp dụng blend lên headTilt/headSwayX/headNodY (override nếu priority cao hơn).
    if (this._scheduler) {
      const blend = this._scheduler.update(now);
      if (blend["head.tilt"] && blend["head.tilt"].priority >= 30) {
        this.headTilt = blend["head.tilt"].value * (Math.PI / 180); // deg → rad
      }
      if (blend["head.sway"] && blend["head.sway"].priority >= 30) {
        this.headSwayX = blend["head.sway"].value;
      }
      if (blend["head.nod"] && blend["head.nod"].priority >= 30) {
        this.headNodY = blend["head.nod"].value;
      }
    }

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

    // 4. Saccades (gaze wander) — P2: mở rộng theo state (mắt sống khi nói/cười)
    if (now >= this.nextSaccadeTime) {
      if (this.state === "IDLE" || this.state === "LISTENING") {
        this.saccadeX = (Math.random() - 0.5) * 2.4;
        this.saccadeY = (Math.random() - 0.5) * 1.4;
      } else if (this.state === "THINKING") {
        this.saccadeX = 1.6;
        this.saccadeY = -1.2;
      } else if (this.state === "SPEAKING" || this.state === "HAPPY" || this.state === "PROUD" || this.state === "SUCCESS") {
        // P2: khi nói/nơi vui — mắt quét khán giả/chủ nhân tự nhiên (±1.6px, hiếm khi đứng yên)
        this.saccadeX = (Math.random() - 0.5) * 3.2;
        this.saccadeY = (Math.random() - 0.5) * 1.6;
        // Micro-fixation: 30% saccade gần như đứng yên (đang nhìn thẳng chủ nhân)
        if (Math.random() < 0.30) { this.saccadeX *= 0.15; this.saccadeY *= 0.15; }
      } else {
        this.saccadeX = 0;
        this.saccadeY = 0;
      }
      this.nextSaccadeTime = now + 2200 + Math.random() * 3000;
    }

    // 4b. P2 HEAD POSE (V6-001): đầu chuyển động quanh trục cổ như người thật.
    //     Thành phần: (a) nghỉ sinh học — drift chậm ±1.5° yaw + thở pitch nhẹ,
    //     (b) state — SPEAKING gật/nghiêng theo nhịp lời, LISTENING nghiêng lắng nghe,
    //     (c) dẫn gaze — đầu quay về hướng mắt (mắt liếc trước, đầu theo sau ~40%).
    const poseT = now - this.startTime;
    const driftYaw = Math.sin(poseT * 0.00031) * 1.5 + Math.sin(poseT * 0.00073 + 1.7) * 0.5;
    const driftPitch = Math.sin(poseT * 0.00042 + 0.9) * 0.8;
    const driftRoll = Math.sin(poseT * 0.00023 + 2.4) * 0.8;
    let stateYaw = 0, statePitch = 0, stateRoll = 0;
    if (this.state === "SPEAKING") {
      // Gật/nghiêng theo nhịp viseme chính 0.64Hz + trọng âm câu (~2.8s) — đo từ 6.mp4
      const beat = Math.sin(poseT * 0.00402);
      const phrase = Math.sin(poseT * 0.00224);
      stateYaw = phrase * 2.2 + Math.sin(poseT * 0.00335 + 0.6) * 0.8;
      statePitch = Math.max(0, beat) * 1.1;          // gật nhẹ theo nhịp nói
      stateRoll = Math.sin(poseT * 0.00161) * 1.2;   // đổi trọng tâm đầu theo câu
    } else if (this.state === "LISTENING") {
      stateYaw = -2.2;                                // hướng vào chủ nhân
      stateRoll = -1.4;                               // nghiêng đầu lắng nghe
      statePitch = -0.5;
    } else if (this.state === "THINKING" || this.state === "RESEARCHING") {
      stateYaw = 2.6;                                 // hướng mắt lên-trái như đang suy nghĩ
      statePitch = -1.2;
      stateRoll = 1.0;
    } else if (this.state === "SLEEPING" || this.state === "OFFLINE") {
      statePitch = 2.6;                               // đầu gục nhẹ
      stateRoll = 1.6;
    } else if (this.state === "SURPRISED") {
      statePitch = -1.6;                              // ngửa nhẹ khi giật mình
    } else if (this.state === "APOLOGETIC" || this.state === "ERROR") {
      statePitch = 1.8;                               // cúi đầu nhẹ
    }
    // Gaze-lead: đầu theo hướng mắt sau (mắt đã có saccade riêng ±1.2px scale)
    const gazeYaw = this.saccadeX * 0.35 + (this.currentMicro.gazeX || 0) * 0.5;
    const gazePitch = -this.saccadeY * 0.25 + (this.currentMicro.gazeY || 0) * 0.3;
    // M2a "ĐẦU VỮNG KHI MỞ MIỆNG LỚN" (đo video mẫu: mở 50-60% = đầu frontal,
    // yaw chỉ 5-10° — người hát giữ đầu để khẩu hình rõ). Steady factor 1→0.45
    // theo openRatio: state pitch/roll giảm mạnh khi nói to, drift giữ lại 100%
    // (thở không phụ thuộc nói).
    const openNow = Math.max(0, Math.min(1, this.currentOpenRatio || 0));
    const steady = 1 - openNow * 0.55;
    const targetYaw = this._clamp(driftYaw + stateYaw * steady + gazeYaw, -6, 6);
    const targetPitch = this._clamp(driftPitch + statePitch * steady + gazePitch, -4, 4);
    const targetRoll = this._clamp(driftRoll + stateRoll * steady, -2, 2);
    // Lerp chậm (một chút quán tính cổ) — nhanh hơn là chóng mặt, chậm là ì
    this.headYaw = this.headYaw + (targetYaw - this.headYaw) * 0.045;
    this.headPitch = this.headPitch + (targetPitch - this.headPitch) * 0.05;
    this.headRoll = this.headRoll + (targetRoll - this.headRoll) * 0.035;

    // 4c. M1b LISTENING GẬT NHẸ XÁC NHẬN (§4B brief): thi thoảng gật 1-2 nhịp nhẹ
    //     khi nghe — khoảng 6-14s/lần, biên độ pitch 1.2°, đúng "gật đầu nhẹ".
    if (this.state === "LISTENING") {
      if (this._nodNextT === undefined) this._nodNextT = now + 5000 + Math.random() * 6000;
      if (!this._nodActive && now >= this._nodNextT) {
        this._nodActive = true;
        this._nodT0 = now;
        this._nodCount = Math.random() < 0.4 ? 2 : 1;   // 40% gật đôi
      }
      if (this._nodActive) {
        const el = now - this._nodT0;
        const nodDur = 620 * this._nodCount;             // 1 gật 620ms
        if (el >= nodDur) {
          this._nodActive = false;
          this._nodNextT = now + 6000 + Math.random() * 8000;
        } else {
          // cộng thêm vào pitch đã có (không đè) — 1.5 chu kỳ sin cho 2 gật
          const cycles = this._nodCount === 2 ? 1.5 : 0.75;
          this._nodExtra = Math.sin((el / nodDur) * Math.PI * 2 * cycles) * 1.2;
        }
      } else this._nodExtra = 0;
    } else { this._nodExtra = 0; this._nodActive = false; this._nodNextT = now + 6000; }
    if (this._nodExtra) this.headPitch += this._nodExtra;

    // 4d. M1c THINKING CHỚP CHẬM (§4C brief): nhắm mắt chậm ~500ms thay vì blink
    //     120-150ms — "chìm vào suy nghĩ", kèm thời gian blink dài hơn.
    if (this.state === "THINKING" || this.state === "RESEARCHING") {
      if (this._slowBlinkNextT === undefined) this._slowBlinkNextT = now + 2500 + Math.random() * 2500;
      if (!this._slowBlinkActive && now >= this._slowBlinkNextT) {
        this._slowBlinkActive = true;
        this._slowBlinkT0 = now;
      }
      if (this._slowBlinkActive) {
        const el = now - this._slowBlinkT0;
        if (el >= 900) {                                  // 450ms nhắm + 450ms mở
          this._slowBlinkActive = false;
          this._slowBlinkNextT = now + 3500 + Math.random() * 3500;
        } else if (el >= 450) {
          this.isBlinking = true;                          // đang mở dần — vẫn dùng blink asset
        } else {
          this.isBlinking = true;
        }
      }
    } else { this._slowBlinkActive = false; this._slowBlinkNextT = now + 3000; }

    // 4d. M1d IDLE MỈM CƯỜI THI THOẢNG (§4A brief): "thỉnh thoảng mỉm cười nhẹ"
    //     12-20s/lần, giữ ~2.5-4s rồi tạnh — rig smile đọc _idleSmile khi IDLE.
    if (this.state === "IDLE" || this.state === "NEUTRAL") {
      if (this._idleSmileNextT === undefined) this._idleSmileNextT = now + 6000 + Math.random() * 6000;
      if (!this._idleSmileActive && now >= this._idleSmileNextT) {
        this._idleSmileActive = true;
        this._idleSmileT0 = now;
        this._idleSmileDur = 2500 + Math.random() * 1500;
      }
      if (this._idleSmileActive) {
        const el = now - this._idleSmileT0;
        if (el >= this._idleSmileDur) {
          this._idleSmileActive = false;
          this._idleSmileNextT = now + 12000 + Math.random() * 8000;
          this._idleSmile = 0;
        } else {
          // ease in/out (sin nửa chu kỳ) — không bật/tắt đột ngột (§5 brief)
          this._idleSmile = Math.sin((el / this._idleSmileDur) * Math.PI) * 0.55;
        }
      }
    } else { this._idleSmileActive = false; this._idleSmile = 0; this._idleSmileNextT = now + 8000; }

    // 4e. M4a GOODBYE (duyệt 16/11, nhóm H brief): gật chào 2 nhịp (pitch sin 2
    //     chu kỳ 0.64Hz — nhịp gật chuẩn đã đo) + lean-back nhẹ (scale chest giảm
    //     ~1.5% + sway ngược) trong 2.5s rồi TỰ VỀ IDLE. Không tay (M4b PoC riêng).
    if (this.state === "GOODBYE") {
      if (this._goodbyeT0 === undefined || this._goodbyeT0 === null) {
        this._goodbyeT0 = now;
        this._goodbyeNodSeed = Math.random();
      }
      const gel = now - this._goodbyeT0;
      if (gel >= 2500) {
        // hết phim: dọn state về IDLE (setState qua transition engine — mượt)
        this._goodbyeT0 = null;
        this._goodbyeNodExtra = 0;
        this.setState("IDLE");
      } else {
        // 2 gật chào: 2 chu kỳ sin đầy đủ trong 1.6s đầu, biên độ 2.2° (rõ hơn
        // gật-listen 1.2° — chào phải thấy); sau đó nghỉ, lean-back ease-out.
        const nodPhase = Math.min(1, gel / 1600);
        this._goodbyeNodExtra = Math.sin(nodPhase * Math.PI * 2) * 2.2 * (1 - nodPhase * 0.35);
        this._goodbyeLean = M3_EASING["ease-out"](Math.min(1, gel / 900)) * (1 - Math.min(1, Math.max(0, (gel - 1900) / 600)));
      }
    } else {
      if (this._goodbyeT0 !== undefined && this._goodbyeT0 !== null) {
        this._goodbyeT0 = null; this._goodbyeNodExtra = 0; this._goodbyeLean = 0;
      }
    }
    if (this._goodbyeNodExtra) this.headPitch += this._goodbyeNodExtra;

    // 5. Lip-Sync Frame Lookup from timeline
    if (this.state === "SPEAKING") {
      // (06/11/2026) ƯU TIÊN NĂNG LƯỢNG THẬT: khi có live audio meter (WebAudio
      // đo chính file mp3 đang phát), openRatio dẫn động theo amplitude — khớp
      // nhịp tuyệt đối với tiếng loa; viseme suy từ mức mở (khép→REST).
      // (15/11/2026 v6mou — REF: mẫu.mp4 4K, ca sĩ ballad) Dẫn động miệng theo
      // dải độ mở + nhịp ĐO ĐƯỢC từ video mẫu (không còn hiểu "energy=max"):
      //   • mouth open p10=0.421, p90=0.782 → dải mở tự nhiên khi nói 0.42..0.78
      //   • nhịp viseme chính 0.64 Hz (chu kỳ 1.56s) → nghỉ không đậy nhanh hơn 1/1.56s
      //   • EMA trong video chuẩn alpha≈0.35 @30fps → trên frame ~24fps dùng 0.35
      // energy từ live audio meter được NỐI SÁT vào dải [floor, ceiling] thay vì
      // nhân thẳng 0.95 (dải cũ 0→0.95 làm miệng chụp hẳn khi lời nhỏ, không
      // giống chuyển động miệng người thật trong mẫu).
      if (this._liveAudioMeter) {
        let energy = 0;
        try { energy = Math.max(0, Math.min(1, this._liveAudioMeter())); } catch (_) { energy = 0; }
        const MAU_FLOOR = 0.42, MAU_CEIL = 0.78;          // p10/p90 mouth-open (mẫu.mp4)
        const mauTarget = MAU_FLOOR + energy * (MAU_CEIL - MAU_FLOOR);
        if (energy > 0.02) {
          this.currentOpenRatio += (mauTarget - this.currentOpenRatio) * 0.35;
          this.activeViseme = this.currentOpenRatio < 0.12 ? "REST"
            : (this.currentOpenRatio > 0.68 ? "O" : (this.currentOpenRatio < 0.35 ? "I" : "A"));
        } else {
          // Nghỉ giữa câu: khép về REST theo nhịp tự nhiên (≤1/1.56s chu kỳ mẫu)
          this.currentOpenRatio = this.currentOpenRatio * 0.72;
          if (this.currentOpenRatio < 0.05) this.activeViseme = "REST";
        }
      } else if (this.currentTimeline && this.currentTimeline.frames) {
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

    // 3. ROOT TRANSFORM — CHỈ DỊCH, TUYỆT ĐỐI KHÔNG XOAY
    // (15/11/2026 v6ges — OWNER: "đang xoay cả khung ảnh") Portrait là 1 ảnh
    // full-canvas: BẤT KỲ ctx.rotate nào ở root đều XOAY CẢ TẤM ẢNH như lắc
    // khung hình → ĐÃ BỎ toàn bộ rotate (headTilt + bodyLean). Tilt/lean giờ
    // chỉ còn là dữ liệu định hướng cho micro-expression, không xoay pixel.
    // Giữ translate rất nhỏ (sway + nod + thở) = hiện diện, không phải xoay.
    // (15/11/2026 v6mot — Sprint 6 consume fix) targetBody giờ được VẼ THẬT.
    const bodyT = this.targetBody || null;
    const bodySwayX = bodyT ? (bodyT.swayX || 0) * 1.4 : 0;
    const bodySwayY = bodyT ? (bodyT.swayY || 0) * 0.8 : 0;
    const bodyBreath = bodyT ? (bodyT.breathOffset || 0) * 2.0 : 0;
    ctx.save();
    ctx.translate(bodySwayX + this.headSwayX * 0.5, bodySwayY + bodyBreath + this.headNodY * 0.5 + breathOffset * 0.5);

    // (15/11/2026 v6ges — OWNER: "xây dựng avatar chuyển động cử chỉ") LỚP
    // CỬ CHỈ = translate + scale quanh TÂM ĐÁY (ngực) — KHÔNG xoay:
    //   1) TIẾN NGƯỜI THEO LỜI: scale 1.000→1.006 quanh đáy canvas theo
    //      openRatio — như người thật "lệch người tới" khi nhấn âm tiết.
    //   2) ĐỔI TRỌNG TÂM THEO CÂU (6.mp4 chu kỳ 1.4–4s): dịch ngang ±1.8px
    //      theo beat pattern 2 sóng lệch nhau (~2.8s + ~3.9s), nói thì rõ,
    //      nghỉ còn 40% — đúng micro-rest 87%.
    //   3) NÂNG VAI THỞ: breathOffset đã nằm ở translate trên (±2px).
    const speakingNow = this.state === "SPEAKING";
    const speechLean = speakingNow ? Math.max(0, this.currentOpenRatio) : 0;
    // M4a: lean-back khi GOODBYE — lùi người nhẹ (scale < 1), ease-out vào, ease về
    const goodbyeLean = (this.state === "GOODBYE" && this._goodbyeLean) ? this._goodbyeLean : 0;
    const chestScale = 1.0 + speechLean * 0.006 + Math.max(0, bodyBreath) * 0.0006 - goodbyeLean * 0.015;
    const gestAmp = speakingNow ? 1.0 : 0.4;
    const gestureX = Math.sin(now * 0.00224) * Math.sin(now * 0.00161) * 1.8 * gestAmp;
    ctx.translate(w * 0.5, h);          // tâm đáy = trục ngực
    ctx.scale(chestScale, chestScale);   // tiến người (gesture tới — không xoay)
    ctx.translate(gestureX, 0);          // đổi trọng tâm ngang theo câu
    ctx.translate(-w * 0.5, -h);

    // 4. Base Character Portrait Selection (Authentic Master Expressions from Pi5 Collection)
    let baseImg = this.assets.portrait;
    let usedFullBlink = false;
    let usedFullThinking = false;
    let isSpecialExpression = false;

    if ((this.isBlinking || this.state === "OFFLINE" || this.state === "SLEEPING" || this.state === "SAFE_MODE") && this.assets.portrait_blink && this.assets.portrait_blink.complete && this.assets.portrait_blink.naturalWidth > 0) {
      baseImg = this.assets.portrait_blink;
      usedFullBlink = true;
    } else if ((this.state === "LISTENING") && this.assets.portrait_listening && this.assets.portrait_listening.complete && this.assets.portrait_listening.naturalWidth > 0) {
      // (14/11 v6emo) LẮNG NGHE: portrait lắng nghe thật (ánh mắt hướng chủ nhân)
      baseImg = this.assets.portrait_listening;
      isSpecialExpression = true;
    } else if ((this.state === "WAITING_FOR_OWNER" || this.state === "RECONNECTING") && this.assets.portrait_dreamy && this.assets.portrait_dreamy.complete && this.assets.portrait_dreamy.naturalWidth > 0) {
      // (14/11 v6emo) CHỜ/KẾT NỐI LẠI: mơ mộng (ánh mắt xa xăm chờ đợi)
      baseImg = this.assets.portrait_dreamy;
      isSpecialExpression = true;
    } else if ((this.state === "THINKING" || this.state === "RESEARCHING" || this.activeEmotionTone === "ANALYTICAL_THINKING") && this.assets.portrait_thinking && this.assets.portrait_thinking.complete && this.assets.portrait_thinking.naturalWidth > 0) {
      baseImg = this.assets.portrait_thinking;
      usedFullThinking = true;
      isSpecialExpression = true;
    } else if ((this.state === "HAPPY" || this.state === "SUCCESS" || this.state === "LEARNING" || this.state === "PROUD" || this.activeEmotionTone === "CONFIDENT_SUCCESS") && this.assets.portrait_happy && this.assets.portrait_happy.complete && this.assets.portrait_happy.naturalWidth > 0) {
      baseImg = this.assets.portrait_happy;
      isSpecialExpression = true;
    } else if (this.state === "EMPATHETIC" && this.assets.portrait_empathic && this.assets.portrait_empathic.complete && this.assets.portrait_empathic.naturalWidth > 0) {
      baseImg = this.assets.portrait_empathic;
      isSpecialExpression = true;
    } else if ((this.state === "APOLOGETIC" || this.activeEmotionTone === "APOLOGETIC") && this.assets.portrait_empathic && this.assets.portrait_empathic.complete && this.assets.portrait_empathic.naturalWidth > 0) {
      // (14/11 sync_1314) APOLOGETIC: ánh mắt dịu của empathic + tông APOLOGETIC
      baseImg = this.assets.portrait_empathic;
      isSpecialExpression = true;
    } else if ((this.state === "CONFUSED" || this.state === "WAITING_FOR_OWNER" || this.state === "CURIOUS" || this.activeEmotionTone === "CONSULTATIVE_INQUIRING") && this.assets.portrait_confused && this.assets.portrait_confused.complete && this.assets.portrait_confused.naturalWidth > 0) {
      baseImg = this.assets.portrait_confused;
      isSpecialExpression = true;
    } else if ((this.state === "WARNING" || this.state === "BLOCKED" || this.activeEmotionTone === "SERIOUS_ALERT") && this.assets.portrait_warning && this.assets.portrait_warning.complete && this.assets.portrait_warning.naturalWidth > 0) {
      baseImg = this.assets.portrait_warning;
      isSpecialExpression = true;
    } else if ((this.state === "SURPRISED" || this.activeEmotionTone === "SURPRISED") && this.assets.portrait_surprised && this.assets.portrait_surprised.complete && this.assets.portrait_surprised.naturalWidth > 0) {
      // (06/11/2026) SURPRISED: dùng đúng asset portrait_surprised vốn bỏ không
      // (14/11 sync_1314) + state SURPRISED (PC 22-state) cùng dùng asset này
      baseImg = this.assets.portrait_surprised;
      isSpecialExpression = true;
    } else if (this.state === "ERROR" && this.assets.portrait_error && this.assets.portrait_error.complete && this.assets.portrait_error.naturalWidth > 0) {
      baseImg = this.assets.portrait_error;
      isSpecialExpression = true;
    } else if (this.state === "SPEAKING" && this.assets.portrait_speaking && this.assets.portrait_speaking.complete && this.assets.portrait_speaking.naturalWidth > 0) {
      baseImg = this.assets.portrait_speaking;
    }

    if (baseImg && baseImg.complete && baseImg.naturalWidth > 0) {
      // (14/11 v6emo) CROSSFADE 350ms giữa 2 portrait cảm xúc khác nhau:
      // giữ ảnh cũ vẽ trước với alpha giảm dần, ảnh mới đè lên với alpha tăng dần
      // → chuyển cảm xúc mượt, không nhấp nháy. Blink vẫn tức thì (fade ngắn).
      // (15/11) CONFLICT RESOLVED: giữ upstream crossfade v6emo; bỏ stash cũ
      // body_sync_1311 (_renderBodyAndArms/_drawMaskedPortrait — hướng đã chôn).
      const portraitKey = (baseImg === this.assets.portrait) ? "portrait"
        : (baseImg === this.assets.portrait_blink) ? "blink"
        : (baseImg === this.assets.portrait_speaking) ? "speaking"
        : (baseImg === this.assets.portrait_listening) ? "listening"
        : (baseImg === this.assets.portrait_dreamy) ? "dreamy"
        : (baseImg === this.assets.portrait_happy) ? "happy"
        : (baseImg === this.assets.portrait_thinking) ? "thinking"
        : (baseImg === this.assets.portrait_warning) ? "warning"
        : (baseImg === this.assets.portrait_empathic) ? "empathic"
        : (baseImg === this.assets.portrait_confused) ? "confused"
        : (baseImg === this.assets.portrait_surprised) ? "surprised"
        : (baseImg === this.assets.portrait_error) ? "error" : "other";
      if (portraitKey !== this._lastPortraitKey) {
        this._prevPortrait = { img: this._lastPortraitImg, key: this._lastPortraitKey, t0: now };
        this._lastPortraitKey = portraitKey;
        this._lastPortraitImg = baseImg;
      }
      // M3a (P3, duyệt 16/11): FADE THEO EMOTION ENGINE — duration lấy từ
      // transition preset đang chạy (SERIOUS_ALERT 120ms → nhanh, SLEEPING
      // 900ms → chậm), easing ease-in-out thay linear. Engine chưa transition
      // (hoặc chưa load) → fallback 350ms như v6emo (không hồi quy).
      const emoSnap = this._emotionEngine ? this._emotionEngine.update(now) : null;
      let FADE_MS = 350;
      let easeFn = null;
      if (emoSnap && emoSnap.transitioning && this._emotionEngine._transition) {
        const tr = this._emotionEngine._transition;
        const el = now - tr.startMs;
        if (el < tr.durationMs + (tr.holdUntilMs ? tr.holdUntilMs - tr.startMs - tr.durationMs : 0)) {
          FADE_MS = tr.durationMs + Math.max(0, tr.holdUntilMs - tr.startMs - tr.durationMs) || FADE_MS;
          // hold chỉ kéo dài thời điểm blend hoàn tất, không kéo thời gian blend:
          FADE_MS = tr.durationMs + (tr.holdUntilMs - tr.startMs - tr.durationMs > 0
            ? Math.min(150, tr.holdUntilMs - tr.startMs - tr.durationMs) : 0);
        }
        easeFn = M3_EASING[tr.easing] || M3_EASING["ease-in-out"];
        this._m3Ease = { fn: easeFn, dur: FADE_MS };
      } else if (this._m3Ease && (now - (this._prevPortrait ? this._prevPortrait.t0 : now)) < this._m3Ease.dur) {
        easeFn = this._m3Ease.fn;  // transition kết thúc giữa chừng — giữ easing của nó
      }
      let fade = 1.0;
      if (this._prevPortrait && this._prevPortrait.img && this._prevPortrait.img.complete && this._prevPortrait.img.naturalWidth > 0) {
        const rawT = Math.min(1.0, (now - this._prevPortrait.t0) / FADE_MS);
        fade = easeFn ? easeFn(rawT) : rawT;   // M3a: easing, không còn linear cứng
        if (fade >= 1.0) this._prevPortrait = null;
      }
      if (this._prevPortrait && this._prevPortrait.img && fade < 1.0) {
        ctx.globalAlpha = 1.0;
        this._renderHeadPose(ctx, this._prevPortrait.img, w, h);
        ctx.globalAlpha = fade;
        this._renderHeadPose(ctx, baseImg, w, h);
        ctx.globalAlpha = 1.0;
      } else {
        this._renderHeadPose(ctx, baseImg, w, h);
      }
      // (15/11) CONFLICT RESOLVED: bỏ stash cũ body_sync_1311
      // (_renderBodyAndArms/_drawMaskedPortrait — hướng procedural đã chôn,
      // thay bằng v6ges gesture layer ở root transform).

      // (14/11, owner: "bỏ các đường trên hình thể, giữ hình nguyên gốc")
      // Tắt toàn bộ vẽ đè trang trí lên portrait: hair strands cyan + tendril
      // xuyên mặt + sheen + motes. Portrait asset đã có tóc thật; giữ hàm
      // _renderNaturalHairSway nguyên vẹn bên dưới để rollback bằng git.
      // this._renderNaturalHairSway(ctx, scaleX, scaleY, now);

      // 6. Dynamic Eye Rendering (Blink fallback, saccades, gaze, Duchenne squint, iris glint)
      //    P2: mắt overlay đi CÙNG đầu đã warp (offset _poseAt.eye) — không trôi.
      {
        const p = this._poseAt || { eye: { dx: 0, dy: 0 } };
        this._renderEyes(ctx, scaleX, scaleY, 0, usedFullBlink, usedFullThinking, isSpecialExpression, p.eye);
      }

      // 7. P1 FACE RIG (V6-001 duyệt 16/11): mesh warp mày + miệng + cười trên
      //    chính ảnh portrait — thay lớp sprite/SVG đè. Ảnh portrait đang vẽ
      //    (baseImg hoặc _prevPortrait khi crossfade) làm nguồn warp cho mày.
      this._rigPortraitImg = (fade < 1.0 && this._prevPortrait && this._prevPortrait.img)
        ? this._prevPortrait.img : baseImg;
      // P2: rig mày/miệng/cười đi CÙNG đầu đã warp — truyền breathOffset = dy pose
      // (dịch dọc của dải tại chiều cao đó) + dx qua _poseOffsetX cho rig vẽ lệch ngang.
      {
        const p = this._poseAt || { brow: { dx: 0, dy: 0 }, mouth: { dx: 0, dy: 0 } };
        this._rigBrowDx = p.brow.dx; this._rigMouthDx = p.mouth.dx;
        this._renderRigBrows(ctx, scaleX, scaleY, p.brow.dy);
        this._renderRigMouth(ctx, scaleX, scaleY, p.mouth.dy);
        this._renderRigSmile(ctx, scaleX, scaleY, p.mouth.dy);
      }

      // 8. 100% Seamless Feathered Mouth Lip-Sync (NO RECTANGLE EVER) — SPRITE
      //    CŨ ĐÃ TẮT (P1): rig miệng mesh thay hoàn toàn (DESIGN: "tự nói bằng
      //    miệng của chính ảnh"; "bỏ SVG mày đè"; không còn lớp vẽ đè).
      // this._renderMouth(ctx, scaleX, scaleY, 0);
      // this._renderSmile(ctx, scaleX, scaleY, 0);
      // 7. Eyebrow Micro-Expressions — SVG no-op từ 14/11, thay bằng rig mày
      // this._renderEyebrows(ctx, scaleX, scaleY, 0, isSpecialExpression);

      // (15/11/2026 v6mou — REF: mẫu.mp4) BIỂU CẢM THEO LỜI NÓI: sprite smile
      // cũ TẮT từ P1 (v6rig_1611) — nụ cười giờ do _renderRigSmile mesh đảm
      // nhiệm (kéo khóe + mở khoang theo tone tích cực).
      // this._renderSmile(ctx, scaleX, scaleY, 0);

      // 9. Cyber Lighting & High-Tech Vignette
      this._renderCyberLighting(ctx, w, h, config.auraColor);

      // (13/11/2026) Tay SAU portrait (đè lên vai + đàn) — vẽ cuối để luôn thấy
      // (13/11/2026) TẮT render arms (2 cánh tay tím đang quay) — owner yêu cầu xoá.
      // this._renderArmsOverPortrait(ctx, w, h, now, config);
    } else {
      // Clean cyber loading backdrop; no ghost silhouette or watermark
      this._renderProceduralAssistant(ctx, w, h, 0, config.auraColor);
    }

    ctx.restore(); // Restore head transform

    // 10. Status Symbol Overlay (Fixed HUD tier)
    if (config.symbol) {
      this._renderSymbolOverlay(ctx, w, h, config.symbol, config.auraColor);
    }
  }

  _drawHolographicHalo(ctx, w, h, color) {
    // (14/11/2026 v6emo) OWNER: "bỏ vòng tròn đang quay... chỉ để nguyên bản
    // giao diện như ảnh số 2" → HALO TẮT HOÀN TOÀN (giữ hàm để rollback git).
    return;
  }

  _drawHolographicHalo_disabled(ctx, w, h, color) {
    // (06/11/2026, owner: "mượt nhất") Halo tĩnh ít đổi → CACHE offscreen:
    // chỉ vẽ lại khi màu aura đổi hoặc vòng quay vượt 1 bậc cung nhỏ. Giảm
    // shadowBlur đắt mỗi frame → tăng FPS thực trên Pi5 đáng kể.
    const cx = w * 0.5;
    const cy = h * 0.46;
    const radius = w * 0.42;

    const cacheKey = `${color}|${Math.floor(this.haloAngle / 0.35)}`;
    if (!this._haloCache || this._haloCacheKey !== cacheKey) {
      if (!this._haloCache) {
        this._haloCache = document.createElement("canvas");
        this._haloCache.width = w;
        this._haloCache.height = h;
      }
      const hctx = this._haloCache.getContext("2d");
      hctx.clearRect(0, 0, w, h);
      hctx.save();
      hctx.translate(cx, cy);
      hctx.rotate(this.haloAngle);

      hctx.shadowBlur = 18;
      hctx.shadowColor = color;
      hctx.strokeStyle = color;
      hctx.lineWidth = 2.0;
      hctx.globalAlpha = 0.45;

      hctx.beginPath();
      hctx.arc(0, 0, radius, 0, Math.PI * 2);
      hctx.stroke();

      hctx.lineWidth = 3.5;
      hctx.globalAlpha = 0.75;
      hctx.beginPath();
      hctx.arc(0, 0, radius, 0, Math.PI * 0.4);
      hctx.stroke();

      hctx.beginPath();
      hctx.arc(0, 0, radius, Math.PI * 0.9, Math.PI * 1.3);
      hctx.stroke();

      hctx.beginPath();
      hctx.arc(0, 0, radius, Math.PI * 1.6, Math.PI * 1.9);
      hctx.stroke();

      hctx.restore();
      this._haloCacheKey = cacheKey;
    }

    ctx.drawImage(this._haloCache, 0, 0);

    // Telemetry node dots — nhẹ, vẽ trực tiếp (đủ mượt 24 FPS)
    ctx.save();
    const numDots = 8;
    ctx.fillStyle = "#ffffff";
    for (let i = 0; i < numDots; i++) {
      const angle = this.haloAngle + (i * Math.PI * 2) / numDots;
      const x = cx + Math.cos(angle) * radius;
      const y = cy + Math.sin(angle) * radius;
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
    // (06/11/2026) shadowBlur là operation đắt nhất canvas 2D — giảm 4→2 và
    // chỉ giữ trên strand ngoài; hiệu ứng sheen giữ nguyên nhờ gradient.
    ctx.shadowBlur = 2;
    ctx.shadowColor = "rgba(0, 229, 255, 0.18)";

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
    // (06/11/2026) Motes: bỏ shadowBlur (đắt), glow giả bằng 2 lớp bán trong suốt
    ctx.shadowBlur = 0;

    motes.forEach(m => {
      const my = ((m.by + Math.sin(now * 0.002 + m.phase) * 16) % 1024) * scaleY;
      const mx = (m.bx + Math.cos(now * 0.0018 + m.phase) * 10) * scaleX;
      // Glow 2 lớp rẻ: vầng lớn mờ + lõi sáng (không dùng shadowBlur)
      ctx.fillStyle = "rgba(0, 229, 255, 0.18)";
      ctx.beginPath();
      ctx.arc(mx, my, 4.2 * scaleX, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "rgba(235, 250, 255, 0.9)";
      ctx.beginPath();
      ctx.arc(mx, my, 1.6 * scaleX, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.restore();
  }

  // ================= EYES & MICRO-GAZE =================

  _renderEyes(ctx, scaleX, scaleY, breathOffset, usedFullBlink, usedFullThinking, isSpecialExpression = false, poseOff = null) {
    if (isSpecialExpression && !this.isBlinking) return;

    const eb = this.EYES_BOX;
    const totalGazeX = this.saccadeX + this.currentMicro.gazeX * scaleX * 2.0 + (poseOff ? poseOff.dx : 0);
    const totalGazeY = this.saccadeY + this.currentMicro.gazeY * scaleY * 2.0 + (poseOff ? poseOff.dy : 0);

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

  // (15/11/2026 v6mou — REF: mẫu.mp4) NỤ CƯỜI THEO LỜI NÓI — smile 33% samples
  // trong video mẫu: khi giọng nói mang tone cảm xúc tích cực, thay asset miệng
  // "đang nói" bằng "happy" (môi cong nhẹ) để KHUÔN MẶT khớp cảm xúc câu nói.
  _renderSmile(ctx, scaleX, scaleY, breathOffset) {
    if (this.state !== "SPEAKING") return;
    const SMILE_TONES = { WARM_GREETING: 1, CONFIDENT_SUCCESS: 1, PROUD: 1, CURIOUS: 1 };
    if (!SMILE_TONES[this.activeEmotionTone]) return;
    const smileAsset = this.assets.mouth_happy;
    if (!smileAsset || !smileAsset.complete || smileAsset.naturalWidth === 0) return;

    const openRatio = Math.max(0.0, Math.min(1.0, this.currentOpenRatio));
    if (openRatio <= 0.08) return; // nghỉ giữa câu → để môi portrait nguyên

    const mb = this.MOUTH_BOX;
    const destX = mb.x * scaleX;
    const destY = mb.y * scaleY + breathOffset;
    const destW = mb.w * scaleX;
    const destH = mb.h * scaleY;

    // Feathered ellipse mask giống _renderMouth → viền 100% trong suốt
    if (!this._featherSmileCanvas) {
      this._featherSmileCanvas = document.createElement("canvas");
    }
    const sCanvas = this._featherSmileCanvas;
    const targetW = Math.max(10, Math.round(destW));
    const targetH = Math.max(10, Math.round(destH));
    if (sCanvas.width !== targetW || sCanvas.height !== targetH) {
      sCanvas.width = targetW;
      sCanvas.height = targetH;
    }
    const sCtx = sCanvas.getContext("2d");
    sCtx.clearRect(0, 0, targetW, targetH);
    sCtx.drawImage(smileAsset, 0, 0, targetW, targetH);
    sCtx.globalCompositeOperation = "destination-in";
    const scx = targetW * 0.5;
    const scy = targetH * 0.5;
    const srx = targetW * 0.48;
    const sry = targetH * 0.46;
    const sGrad = sCtx.createRadialGradient(scx, scy, sry * 0.30, scx, scy, srx);
    sGrad.addColorStop(0.0, "rgba(0,0,0,1.0)");
    sGrad.addColorStop(0.68, "rgba(0,0,0,0.92)");
    sGrad.addColorStop(0.88, "rgba(0,0,0,0.35)");
    sGrad.addColorStop(1.0, "rgba(0,0,0,0.0)");
    sCtx.fillStyle = sGrad;
    sCtx.beginPath();
    sCtx.ellipse(scx, scy, srx, sry, 0, 0, Math.PI * 2);
    sCtx.fill();

    ctx.save();
    // Nụ cười giữ alpha nhẹ hơn miệng nói → chuyển mượt, không đè môi portrait
    ctx.globalAlpha = Math.min(1.0, 0.30 + openRatio * 0.55);
    ctx.drawImage(sCanvas, destX, destY, destW, destH);
    ctx.restore();
  }

  // ================= M1 FACIAL ENGINE 12-PARAM (V6, duyệt 16/11/2026) =================
  // Chuẩn hoá §5 brief CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN: bảng tham số biểu cảm
  // DUY NHẤT — accessor ĐỌC state có sẵn của engine (không tạo engine thứ 2, không
  // phá render P1/P2). Dùng cho: debug/tune, mở rộng tương lai, introspection.
  // Trả về giá trị 0..1 (hoặc px cho gaze) trong khung hiện tại.
  _facialParams() {
    const eb = this.EYES_BOX;
    return {
      // Mắt
      eyeBlinkLeft: this.isBlinking ? 1 : 0,          // nhắm=1 (engine dùng ảnh blink cả 2 mắt)
      eyeBlinkRight: this.isBlinking ? 1 : 0,
      eyeLookX: this._clamp(this.saccadeX + this.currentMicro.gazeX * 2.0, -3, 3),  // px 1024-space
      eyeLookY: this._clamp(this.saccadeY + this.currentMicro.gazeY * 2.0, -3, 3),
      // Mày (P1: browAmt -0.70..+0.80 → chuẩn hoá raise dương/lower âm)
      browRaise: Math.max(0, this._browAmtFor(this.state)),
      browLower: Math.max(0, -this._browAmtFor(this.state)),
      // Miệng (P1 rig)
      smile: this._rigSmile || 0,
      mouthOpen: Math.max(0, Math.min(1, this.currentOpenRatio || 0)),
      jawOpen: Math.max(0, Math.min(1, (this.currentOpenRatio || 0) * 0.85)),  // hàm = ~85% mở
      lipPucker: (this.activeViseme === "O" || this.activeViseme === "U") ? 1 : 0,
      cheekRaise: (this._rigSmile || 0) * 0.6,        // má nâng theo cười (Duchenne cơ sở)
      // Đầu/cổ (P2 — đơn vị độ)
      headTilt: this.headRoll || 0,                   // roll ±2°
      headYaw: this.headYaw || 0,                     // ±6°
      headPitch: this.headPitch || 0,                 // ±4° (neck = pivot cổ 896:802)
      // meta
      _box: { eyes: eb, mouth: { x: 427, y: 630, w: 240, h: 100 }, neckY896: 802 },
    };
  }

  // Helper: biên độ mày theo state (tách khỏi _renderRigBrows để 12-param đọc được;
  // _renderRigBrows gọi hàm này — 1 nguồn sự thật)
  _browAmtFor(st) {
    const PRESET = {
      SPEAKING: 0, IDLE: 0, LISTENING: 0,
      THINKING: -0.45, RESEARCHING: -0.45, WARNING: -0.70, ERROR: -0.70,
      SURPRISED: 0.80, HAPPY: 0.35, EMPATHETIC: -0.30, CONFUSED: -0.40,
      RECONNECTING: -0.40, OFFLINE: -0.30,
    };
    return PRESET[st] || 0;
  }

  // ================= P2 HEAD POSE (V6-001, duyệt 16/11) =================
  // Clamp helper (dùng cho head pose + gaze)
  _clamp(v, lo, hi) {
    return v < lo ? lo : (v > hi ? hi : v);
  }

  // ===== HEAD POSE MESH: warp dải ngang quanh trục cổ — lắc/nghiêng là chuyển
  // động của ĐẦU, thân giữ nguyên (DESIGN P2: hết "lắc cả tấm ảnh"). =====
  // Cơ chế: chia dải đầu (yHeadTop → yNeck) thành 16 dải ngang; dải tại cổ có
  // biên độ 0 (liền mạch với thân), càng lên đỉnh biên độ tăng theo ease
  // (pow 1.25) → xoay tương đương quay quanh trục cổ nhưng KHÔNG xoay tấm ảnh:
  // thân/vai/cổ áo vẫn nguyên vẹn, không lật nền, không xoay viền.
  // Mỗi dải = drawImage bản sao canvas đầu (render 1 lần/_render, reuse) dịch
  // xoay quanh trục cổ. Chi phí ~16 drawImage 896-dải — Pi5 chịu được (đo P1
  // mesh 24 tam giác ~2ms; dải ngang rẻ hơn vì không cần tính tam giác).
  _renderHeadPose(ctx, baseImg, w, h) {
    const yaw = this.headYaw, pitch = this.headPitch, roll = this.headRoll;
    if (Math.abs(yaw) < 0.05 && Math.abs(pitch) < 0.05 && Math.abs(roll) < 0.05) return;

    const fY = 896 / h;                      // canvas-y → 896-space
    const neckY = h * (802 / 896);           // trục cổ (896-space 802 → canvas)
    const headTopY = h * (76 / 896);         // đỉnh tóc (đo asset v3: tóc ~76px)
    const span = neckY - headTopY;
    if (span <= 0) return;

    // Ease theo khoảng cách tới cổ: 0 tại cổ → 1 tại đỉnh (pow 1.25)
    const easeAt = (yCanvas) => Math.pow(Math.max(0, (neckY - yCanvas) / span), 1.25);
    const kx = w / 896, ky = h / 896;        // scale biên độ theo buffer

    ctx.save();
    // Roll quanh trục cổ (2D): xoay nhẹ cả khối đầu quanh điểm cổ — vẽ TRONG
    // crop dải đầu nên thân không bị kéo theo.
    ctx.translate(w * 0.5, neckY);
    ctx.rotate(roll * Math.PI / 180);
    ctx.translate(-w * 0.5, -neckY);

    // Yaw = dịch ngang mỗi dải theo ease → mép dưới (cổ) đứng yên.
    // Pitch = dịch dọc theo ease (đầu gục: xuống; ngửa: lên).
    const bands = 16;
    for (let i = 0; i < bands; i++) {
      const t0 = i / bands, t1 = (i + 1) / bands;
      const y0 = headTopY + span * t0, y1 = headTopY + span * t1;
      const yMid = (y0 + y1) * 0.5;
      const ease = easeAt(yMid);
      const dx = yaw * 0.95 * kx * ease;     // 6° → ~6.8px đỉnh đầu @1080 buffer
      const dy = pitch * 0.95 * ky * ease;   // 4° → ~4.5px
      const bandH = (y1 - y0) + 0.7;         // chồng 0.7px tránh khe sáng
      ctx.drawImage(baseImg, 0, y0 * fY, baseImg.naturalWidth, (bandH) * fY,
        dx - 0.35, y0 + dy - 0.35, w, bandH);
    }
    ctx.restore();

    // Offset cho lớp đè (mắt blink/thinking overlay + rig P1) — same ease để
    // chúng dính chặt vào mặt đã warp, không trôi khi đầu quay.
    const offAt = (y896) => {
      const e = easeAt(y896 * ky);
      return { dx: yaw * 0.95 * kx * e, dy: pitch * 0.95 * ky * e };
    };
    const eyeOff = offAt(438);   // tâm mắt (đo: y≈438)
    const browOff = offAt(408);  // chân mày (rig base)
    const mouthOff = offAt(680); // tâm môi (rig base)
    this._poseAt = { eye: eyeOff, brow: browOff, mouth: mouthOff };
  }

  // ================= P1 FACE RIG (V6-001, duyệt 16/11/2026) =================
  // Mesh warp trên CHÍNH ảnh portrait — Cherry tự nói/cười/nhíu mày bằng
  // nét mặt gốc của ảnh, không đè sprite/SVG. Nguyên tắc (DESIGN §2, §5):
  //  - Toạ độ 896-space (portrait v3); map về canvas qua 896/w.
  //  - Chỉ warp ĐẶC ĐIỂM GỐC (môi + mày), không vẽ đặc điểm mới (Model A).
  //  - Khu vực EYES_BOX (y 373-503) KHÔNG bị vẽ đè — bảo đảm mắt sạch.
  //  - Pi5 4GB: ~24 tam giác, feather offscreen, đường biên mềm — rẻ CPU.

  _rigBase() {
    // Toạ độ môi đo pixel thật trên asset v3 (căn theo MOUTH_BOX engine)
    // MOUTH_BOX = {x:427, y:630, w:240, h:100} → tâm môi (547, 680)
    if (this._rigBaseCache) return this._rigBaseCache;
    this._rigBaseCache = {
      mouthCx: 547, mouthCy: 680, mouthW: 264, mouthH: 92,
      // Vùng dải môi (để vẽ lại khi khoét): 8px đệm quanh hộp môi
      lipTop: 634, lipBottom: 726,
      // Lông mày: đo pixel thật (đo 16/11): trái tâm (351,409), phải (594,407),
      // rộng ~142px, dày ~28px (vùng đậm giữa mày)
      browL: { cx: 351, cy: 409, w: 142, h: 30 },
      browR: { cx: 594, cy: 407, w: 142, h: 30 },
    };
    return this._rigBaseCache;
  }

  // ===== MÔI MESH: khoét khoang tối + răng mờ theo openRatio (thay sprite) =====
  _renderRigMouth(ctx, scaleX, scaleY, breathOffset) {
    const openRatio = Math.max(0.0, Math.min(1.0, this.currentOpenRatio));
    if (this.state !== "SPEAKING" || openRatio <= 0.08) return;

    const R = this._rigBase();
    const f = 896 / this.width;
    const cx = R.mouthCx * f, cy = R.mouthCy * f + breathOffset;
    const mw = R.mouthW * f, mh = R.mouthH * f;

    // Biên độ mở theo viseme: A/E mở rộng, O/U mở tròn hẹp
    const vis = this.activeViseme || "A";
    let shape = 1.0;                  // hệ số chiều rộng khoang
    if (vis === "O" || vis === "U") shape = 0.62;
    else if (vis === "E" || vis === "I") shape = 1.08;

    const openPx = openRatio * mh * 1.35;
    if (openPx < 2) return;

    // Khoang miệng: hình hạt đậu (2 đường cong bậc 2) — tối trong, viền môi
    // lấy màu từ chính ảnh (không vẽ môi mới — chỉ thay vùng ĐEN bên trong môi)
    ctx.save();
    const grad = ctx.createLinearGradient(0, cy - mh * 0.5, 0, cy + mh * 0.55);
    grad.addColorStop(0, "rgba(74,24,30,0.94)");
    grad.addColorStop(0.45, "rgba(42,8,14,0.97)");
    grad.addColorStop(1, "rgba(66,22,26,0.90)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    const halfW = mw * 0.5 * shape;
    // P2: khoang miệng đi CÙNG đầu đã warp (dx từ _poseAt)
    const poseDx = this._rigMouthDx || 0;
    // Điểm khóe: y dịch theo cười (tone tích cực khóe lên nhẹ)
    const smileLift = (this._rigSmile > 0.02) ? -openPx * 0.22 * this._rigSmile : 0;
    ctx.moveTo(cx - halfW + poseDx, cy + smileLift);
    ctx.quadraticCurveTo(cx + poseDx, cy - openPx * 0.42 + smileLift, cx + halfW + poseDx, cy + smileLift);
    ctx.quadraticCurveTo(cx + poseDx, cy + openPx * 1.02 + smileLift * 0.6, cx - halfW + poseDx, cy + smileLift);
    ctx.closePath();
    ctx.fill();

    // Răng trên: dải trắng mờ dính sát mép môi trên — CHỈ khi mở đủ
    if (openPx > mh * 0.30) {
      const th = Math.min(openPx * 0.34, mh * 0.40);
      ctx.fillStyle = "rgba(243,236,228,0.72)";
      ctx.beginPath();
      ctx.moveTo(cx - halfW * 0.78, cy - openPx * 0.30 + smileLift);
      ctx.quadraticCurveTo(cx, cy - openPx * 0.55 + smileLift, cx + halfW * 0.78, cy - openPx * 0.30 + smileLift);
      ctx.quadraticCurveTo(cx, cy - openPx * 0.30 + smileLift + th * 0.75, cx - halfW * 0.78, cy - openPx * 0.30 + smileLift);
      ctx.closePath();
      ctx.fill();
    }
    // M2b: RĂNG DƯỚI khi mở RẤT LỚN (>0.8 openRatio) — đo video mẫu (frame mở
    // tối đa "hình thể.mp4"): hàm hạ lộ răng dưới mờ sát mép môi dưới, hẹp hơn
    // và mờ hơn răng trên. Ngưỡng 0.8 tránh răng dưới hiện ở khẩu hình vừa.
    if (openRatio > 0.8) {
      const lowerT = (openRatio - 0.8) / 0.2;      // fade in 0.8→1.0
      const th2 = Math.min(openPx * 0.22, mh * 0.26);
      ctx.fillStyle = "rgba(238,230,222," + (0.5 * lowerT).toFixed(3) + ")";
      ctx.beginPath();
      ctx.moveTo(cx - halfW * 0.62, cy + openPx * 0.72 + smileLift * 0.6);
      ctx.quadraticCurveTo(cx, cy + openPx * 0.88 + smileLift * 0.6, cx + halfW * 0.62, cy + openPx * 0.72 + smileLift * 0.6);
      ctx.quadraticCurveTo(cx, cy + openPx * 0.72 + smileLift * 0.6 - th2 * 0.7, cx - halfW * 0.62, cy + openPx * 0.72 + smileLift * 0.6);
      ctx.closePath();
      ctx.fill();
    }
    // Lưỡi khi mở lớn
    if (openPx > mh * 0.72) {
      ctx.fillStyle = "rgba(186,88,98,0.50)";
      ctx.beginPath();
      ctx.ellipse(cx, cy + openPx * 0.66 + smileLift, halfW * 0.34, openPx * 0.24, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  // M3c helper: lerp Duchenne — method trong class (harness trích class riêng
  // vẫn chạy được; module-level function không nằm theo class)
  _lerpDuchenne(a, b, t) { return a + (b - a) * t; }

  // ===== NỤ CƯỜI MESH: kéo khóe môi bằng highlight mềm 2 bên (thay sprite) =====
  _renderRigSmile(ctx, scaleX, scaleY, breathOffset) {
    // M1d: IDLE mỉm cười thi thoảng — highlight khóe khi _idleSmile đang active
    if ((this.state === "IDLE" || this.state === "NEUTRAL")) {
      const s = this._idleSmile || 0;
      if (s < 0.02) { this._rigSmile = 0; return; }
      this._rigSmile = s;
      const R = this._rigBase();
      const f = 896 / this.width;
      const poseDx = this._rigMouthDx || 0;
      const cy = R.mouthCy * f + breathOffset;
      const halfW = R.mouthW * 0.5 * f;
      ctx.save();
      ctx.strokeStyle = "rgba(214,132,132," + (0.26 * s).toFixed(3) + ")";
      ctx.lineWidth = Math.max(1, f * 2.2);
      ctx.lineCap = "round";
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.moveTo(R.mouthCx * f + poseDx + side * halfW * 0.86, cy - s * f * 2.2);
        ctx.quadraticCurveTo(R.mouthCx * f + poseDx + side * halfW * 0.62, cy - s * f * 3.4, R.mouthCx * f + poseDx + side * halfW * 0.42, cy - s * f * 4.2);
        ctx.stroke();
      }
      ctx.restore();
      return;
    }
    // M3c: state VUI không nói (HAPPY/PROUD/SUCCESS + tone CONFIDENT_SUCCESS)
    // vẫn Duchenne — mắt cong + má nâng theo intensity + highlight khóe nhẹ.
    // (PHẢI đứng TRƯỚC guard SPEAKING — state HAPPY không phải SPEAKING.)
    if (this.state === "HAPPY" || this.state === "PROUD" || this.state === "SUCCESS" ||
        this.activeEmotionTone === "CONFIDENT_SUCCESS") {
      const emo = this._emotionEngine ? this._emotionEngine.getCurrent() : null;
      const inten = emo ? Math.max(0.2, Math.min(1, emo.intensity || 0.8)) : 0.8;
      const s = 0.45 * inten;
      this._rigSmile = s;
      this.currentMicro.eyeSquint = this._lerpDuchenne(this.currentMicro.eyeSquint, 0.26 * inten, 0.16);
      this.currentMicro.smileBoost = this._lerpDuchenne(this.currentMicro.smileBoost, 0.40 * inten, 0.16);
      // highlight khóe 2 nét (như nhánh SPEAKING nhưng lift cố định theo s)
      const R = this._rigBase();
      const f = 896 / this.width;
      const poseDx = this._rigMouthDx || 0;
      const cy = R.mouthCy * f + breathOffset;
      const halfW = R.mouthW * 0.5 * f;
      ctx.save();
      ctx.strokeStyle = "rgba(214,132,132," + (0.30 * s).toFixed(3) + ")";
      ctx.lineWidth = Math.max(1, f * 2.2);
      ctx.lineCap = "round";
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.moveTo(R.mouthCx * f + poseDx + side * halfW * 0.86, cy - s * f * 3.0);
        ctx.quadraticCurveTo(R.mouthCx * f + poseDx + side * halfW * 0.62, cy - s * f * 4.2, R.mouthCx * f + poseDx + side * halfW * 0.42, cy - s * f * 4.8);
        ctx.stroke();
      }
      ctx.restore();
      return;
    }
    if (this.state !== "SPEAKING") return;
    const SMILE_TONES = { WARM_GREETING: 1, CONFIDENT_SUCCESS: 1, PROUD: 1, CURIOUS: 1 };
    if (!SMILE_TONES[this.activeEmotionTone]) { this._rigSmile = 0; return; }
    const openRatio = Math.max(0.0, Math.min(1.0, this.currentOpenRatio));
    const smile = Math.min(1, 0.25 + openRatio * 0.5);
    this._rigSmile = smile;
    // M3c HAPPY DUCHENNE (§4F brief "Mắt hơi cong khi cười", không cường điệu):
    // squint sync theo smile đang hiển thị — max 0.30 (nhẹ), giới hạn bởi
    // intensity engine (tone mạnh → rõ hơn). currentMicro.eyeSquint là nguồn
    // lerp; ghi đè mục tiêu Duchenne để mắt CONG ĐI CÙNG khóe (1 nguồn sync).
    {
      const emo = this._emotionEngine ? this._emotionEngine.getCurrent() : null;
      const inten = emo ? Math.max(0.2, Math.min(1, emo.intensity || 0.6)) : 0.6;
      this.currentMicro.eyeSquint = this._lerpDuchenne(this.currentMicro.eyeSquint, 0.30 * smile * inten, 0.18);
      this.currentMicro.smileBoost = this._lerpDuchenne(this.currentMicro.smileBoost, 0.45 * smile * inten, 0.18);
    }
    const R = this._rigBase();
    const f = 896 / this.width;
    // P2: nụ cười đi CÙNG đầu đã warp
    const poseDx = this._rigMouthDx || 0;
    const cy = R.mouthCy * f + breathOffset;
    const halfW = R.mouthW * 0.5 * f;
    const lift = openRatio > 0.08 ? smile * f * 7 : 0; // px khóe nhấc lên
    // 2 highlight mềm tại khóe — màu môi gốc lấy dạng hồng môi
    ctx.save();
    ctx.strokeStyle = "rgba(214,132,132," + (0.30 * smile).toFixed(3) + ")";
    ctx.lineWidth = Math.max(1, f * 2.2);
    ctx.lineCap = "round";
    for (const s of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(R.mouthCx * f + poseDx + s * halfW * 0.86, cy + lift * 0.55);
      ctx.quadraticCurveTo(R.mouthCx * f + poseDx + s * halfW * 0.62, cy + lift * 0.9, R.mouthCx * f + poseDx + s * halfW * 0.42, cy + lift);
      ctx.stroke();
    }
    ctx.restore();
  }

  // ===== MÀY MESH: vẽ lại dải mày gốc (lấy mẫu từ ảnh) dịch dọc + nghiêng
  // theo cảm xúc — thay SVG đè (DESIGN P1: "thay SVG mày đè") =====
  _renderRigBrows(ctx, scaleX, scaleY, breathOffset) {
    const st = this.state;
    // M1: preset tách vào _browAmtFor (1 nguồn sự thật cho render + 12-param)
    const browAmt = this._browAmtFor(st);
    if (browAmt === 0) return; // state trung tính: mày gốc nguyên vẹn

    const R = this._rigBase();
    const f = 896 / this.width;
    const img = this._rigPortraitImg;   // ảnh portrait đang render (đặt ở _render)
    if (!img || !img.complete || img.naturalWidth === 0) return;

    for (const [brow, side] of [[R.browL, -1], [R.browR, 1]]) {
      const lift = browAmt * 12 * f;                    // px dọc
      const tilt = -browAmt * 0.10 * side;              // nghiêng: nhíu = trong hạ, nhấc = ngoài nâng
      const srcX = (brow.cx - brow.w / 2) * (img.naturalWidth / 896);
      const srcY = (brow.cy - brow.h / 2) * (img.naturalHeight / 896);
      const srcW = brow.w * (img.naturalWidth / 896);
      const srcH = brow.h * (img.naturalHeight / 896);
      // P2: dải mày đi CÙNG đầu đã warp (dx từ _poseAt)
      const poseDx = this._rigBrowDx || 0;
      ctx.save();
      ctx.translate(brow.cx * f + poseDx, (brow.cy + browAmt * 12) * f + breathOffset);
      ctx.rotate(tilt);
      // Vẽ dải mày gốc (lấy từ chính ảnh) tại vị trí đã dịch — che nền bằng
      // chính dải da trên mày (lấy từ trên mày) để không để lỗ hổng
      ctx.drawImage(img, srcX, srcY - srcH * 0.9, srcW, srcH,
        -brow.w * f / 2, -brow.h * f / 2, brow.w * f, brow.h * f);
      ctx.restore();
    }
  }

  // ================= LIGHTING & SYMBOLS =================

  _renderCyberLighting(ctx, w, h, color) {
    // (14/11/2026 v6emo) OWNER: giữ ảnh portrait nguyên gốc, không phủ vignette tối.
    return;
  }

  _renderCyberLighting_disabled(ctx, w, h, color) {
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
    // (14/11/2026 v6emo) OWNER: bỏ huy hiệu tròn zZz/⚠️/✨ đè lên chân dung.
    return;
  }

  _renderSymbolOverlay_disabled(ctx, w, h, symbol, color) {
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

  // ================= CLEAN CYBERNETIC BACKDROP (NO GHOST WATERMARK) =================

  _renderProceduralAssistant(ctx, w, h, breathOffset, auraColor) {
    // Model A loading backdrop: Clean cybernetic radial gradient only.
    // Legacy Model F ghost silhouette (face mask, lilac hair shroud, hazel eye dots, collar)
    // is permanently removed to eliminate watermark / ghost artifacts on page reload.
    const cx = w * 0.5;
    const cy = h * 0.44 + breathOffset;

    ctx.save();
    const bgGrad = ctx.createRadialGradient(cx, cy, 20, cx, cy, w * 0.5);
    bgGrad.addColorStop(0, "rgba(18, 30, 60, 0.85)");
    bgGrad.addColorStop(0.65, "rgba(8, 16, 36, 0.95)");
    bgGrad.addColorStop(1, "rgba(4, 8, 20, 1.0)");
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);
    ctx.restore();
  }

  // (13/11/2026) Vẽ thân + đàn keyboard TRƯỚC portrait (sẽ bị portrait che 1 phần).
  // Mẫu: nữ nghệ sĩ chơi keyboard, váy tím lavender, tươi cười hiền dịu.
  _renderBodyAndArms(ctx, w, h, now, config) {
    // (13/11 đêm) BỎ sway riêng: body nằm TRONG head transform — mọi lớp
    // (portrait/body/arms) dịch CÙNG headSwayX + breathOffset → hết seam ngang.
    ctx.save();

    // 1. VÁY / THÂN — gradient tím lavender (mẫu ảnh image_955013)
    // (13/11 đêm) HẠ SÂU: portrait mặt cận chiếm tới 0.84h → thân chỉ còn
    // dải hẹp dưới cùng (0.88→0.99h), như vai/váy lộ sau bệ đàn.
    const bodyTop = h * 0.88;   // bắt đầu dưới portrait
    const bodyBot = h * 0.99;
    const bodyGrad = ctx.createLinearGradient(0, bodyTop, 0, bodyBot);
    bodyGrad.addColorStop(0, "rgba(180, 140, 220, 0.95)");   // lavender sáng
    bodyGrad.addColorStop(0.5, "rgba(150, 110, 200, 0.95)"); // tím giữa
    bodyGrad.addColorStop(1, "rgba(120, 80, 180, 0.95)");    // tím đậm dưới
    ctx.fillStyle = bodyGrad;

    // Váy hình thang rộng dần xuống dưới (mẫu váy xòe)
    ctx.beginPath();
    ctx.moveTo(w * 0.32, bodyTop);
    ctx.bezierCurveTo(
      w * 0.28, h * 0.75,
      w * 0.22, h * 0.85,
      w * 0.18, bodyBot
    );
    ctx.lineTo(w * 0.82, bodyBot);
    ctx.bezierCurveTo(
      w * 0.78, h * 0.85,
      w * 0.72, h * 0.75,
      w * 0.68, bodyTop
    );
    ctx.closePath();
    ctx.fill();

    // (13/11 tối) Bèo nhún MỀM: sóng sin nhiều khúc, alpha thấp — vải mềm
    ctx.strokeStyle = "rgba(205, 175, 235, 0.35)";
    ctx.lineWidth = 1.2;
    for (let i = 0; i < 3; i++) {
      const y0 = bodyTop + (bodyBot - bodyTop) * (0.3 + i * 0.2);
      const amp = 3 + i * 1.2;
      ctx.beginPath();
      for (let s = 0; s <= 8; s++) {
        const t = s / 8;
        const x = w * (0.25 + t * 0.5);
        const y = y0 + Math.sin(t * Math.PI * 3 + i) * amp;
        if (s === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    // (13/11 đêm) Bóng mềm nơi cạnh dưới portrait gặp váy — che đường nối
    const collar = ctx.createLinearGradient(0, h * 0.855, 0, h * 0.895);
    collar.addColorStop(0, "rgba(10, 8, 18, 0)");
    collar.addColorStop(1, "rgba(10, 8, 18, 0.55)");
    ctx.fillStyle = collar;
    ctx.fillRect(w * 0.10, h * 0.855, w * 0.80, h * 0.04);

    // Hoa hồng vải ở ngực trái (mẫu ảnh)
    const flowerX = w * 0.30;
    const flowerY = h * 0.905;
    const flowerR = w * 0.018;
    // (13/11 tối) Hoa MỀM: 2 lớp cánh ellip + tâm gradient (không phải chấm tròn cứng)
    ctx.fillStyle = "rgba(225, 160, 190, 0.35)";
    ctx.beginPath();
    ctx.arc(flowerX, flowerY, flowerR * 1.25, 0, Math.PI * 2);
    ctx.fill();
    for (let i = 0; i < 6; i++) {
      const angle = (i / 6) * Math.PI * 2 + 0.3;
      const px = flowerX + Math.cos(angle) * flowerR * 0.62;
      const py = flowerY + Math.sin(angle) * flowerR * 0.62;
      ctx.fillStyle = "rgba(228, 158, 188, 0.9)";
      ctx.beginPath();
      ctx.ellipse(px, py, flowerR * 0.52, flowerR * 0.38, angle, 0, Math.PI * 2);
      ctx.fill();
    }
    for (let i = 0; i < 5; i++) {
      const angle = (i / 5) * Math.PI * 2 + 0.9;
      const px = flowerX + Math.cos(angle) * flowerR * 0.3;
      const py = flowerY + Math.sin(angle) * flowerR * 0.3;
      ctx.fillStyle = "rgba(245, 190, 210, 0.95)";
      ctx.beginPath();
      ctx.ellipse(px, py, flowerR * 0.4, flowerR * 0.3, angle, 0, Math.PI * 2);
      ctx.fill();
    }
    const heart = ctx.createRadialGradient(flowerX, flowerY, 1, flowerX, flowerY, flowerR * 0.42);
    heart.addColorStop(0, "rgba(255, 236, 214, 0.98)");
    heart.addColorStop(1, "rgba(250, 200, 170, 0.9)");
    ctx.fillStyle = heart;
    ctx.beginPath();
    ctx.arc(flowerX, flowerY, flowerR * 0.4, 0, Math.PI * 2);
    ctx.fill();

    // 2. ĐÀN KEYBOARD — dải ngang phía dưới
    const kbTop = h * 0.935;
    const kbBot = h * 0.995;
    const kbLeft = w * 0.08;
    const kbRight = w * 0.92;

    // (13/11 tối) Thân đàn MỀM: bo góc (roundRect) — không còn khối vuông sắc
    const kbGrad = ctx.createLinearGradient(0, kbTop, 0, kbBot);
    kbGrad.addColorStop(0, "rgba(24, 24, 36, 0.92)");
    kbGrad.addColorStop(1, "rgba(6, 6, 16, 0.96)");
    ctx.fillStyle = kbGrad;
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(kbLeft, kbTop, kbRight - kbLeft, kbBot - kbTop, 8);
    } else {
      ctx.rect(kbLeft, kbTop, kbRight - kbLeft, kbBot - kbTop);
    }
    ctx.fill();

    // Phím trắng
    const whiteKeyCount = 14;
    const whiteKeyW = (kbRight - kbLeft) / whiteKeyCount;
    const whiteKeyH = (kbBot - kbTop) * 0.85;
    const whiteKeyTop = kbTop + (kbBot - kbTop) * 0.05;
    for (let i = 0; i < whiteKeyCount; i++) {
      const kx = kbLeft + i * whiteKeyW;
      ctx.fillStyle = "rgba(240, 240, 250, 0.92)";
      ctx.fillRect(kx + 1, whiteKeyTop, whiteKeyW - 2, whiteKeyH);
      // Viền phím
      ctx.strokeStyle = "rgba(60, 60, 80, 0.4)";
      ctx.lineWidth = 0.5;
      ctx.strokeRect(kx + 1, whiteKeyTop, whiteKeyW - 2, whiteKeyH);
    }

    // Phím đen (mỗi nhóm 2 phím đen giữa 3 phím trắng)
    const blackKeyW = whiteKeyW * 0.6;
    const blackKeyH = whiteKeyH * 0.6;
    const blackKeyTop = whiteKeyTop;
    for (let i = 0; i < whiteKeyCount - 1; i++) {
      // Pattern phím đen: sau phím trắng 1 và 2 (không phải sau 3, 6, 8, 10, 13)
      const blackPattern = [1, 2, 4, 5, 6, 8, 9, 11, 12, 13];
      if (blackPattern.includes(i)) {
        const kx = kbLeft + (i + 1) * whiteKeyW - blackKeyW / 2;
        ctx.fillStyle = "rgba(10, 10, 20, 0.95)";
        ctx.fillRect(kx, blackKeyTop, blackKeyW, blackKeyH);
      }
    }

    // (13/11 tối) Viền đàn MỀM: bo góc alpha thấp + dải sáng phản chiếu trên phím
    ctx.strokeStyle = "rgba(0, 229, 255, 0.22)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(kbLeft, kbTop, kbRight - kbLeft, kbBot - kbTop, 8);
    } else {
      ctx.rect(kbLeft, kbTop, kbRight - kbLeft, kbBot - kbTop);
    }
    ctx.stroke();
    const kbSheen = ctx.createLinearGradient(0, kbTop, 0, kbTop + 6);
    kbSheen.addColorStop(0, "rgba(120, 225, 255, 0.28)");
    kbSheen.addColorStop(1, "rgba(120, 225, 255, 0)");
    ctx.fillStyle = kbSheen;
    ctx.fillRect(kbLeft + 4, kbTop + 1, kbRight - kbLeft - 8, 5);

    ctx.restore();
  }

  // (13/11/2026) Vẽ portrait với MASK gradient: chỉ giữ đầu + vai (y < 0.62*h),
  // ngực fade dần → lộ thân procedural phía sau.
  _drawMaskedPortrait(ctx, baseImg, w, h) {
    const cacheKey = `${baseImg.src}|${w}|${h}`;
    if (!this._portraitMaskedCanvas || this._portraitMaskedKey !== cacheKey) {
      if (!this._portraitMaskedCanvas) {
        this._portraitMaskedCanvas = document.createElement("canvas");
      }
      this._portraitMaskedCanvas.width = w;
      this._portraitMaskedCanvas.height = h;
      const mctx = this._portraitMaskedCanvas.getContext("2d");
      mctx.clearRect(0, 0, w, h);
      mctx.drawImage(baseImg, 0, 0, w, h);

      // (13/11 đêm) Mask HẠ SÂU: portrait MẶT CẬN chiếm tới ~0.84h (da/tóc/
      // môi hồng kéo dài) — fade 0.86→0.97 chỉ lộ phần dưới cùng, KHÔNG cắt mặt.
      const maskY1 = h * 0.84;
      const maskY2 = h * 0.99;
      const maskGrad = mctx.createLinearGradient(0, maskY1, 0, maskY2);
      maskGrad.addColorStop(0, "rgba(0,0,0,1)");
      maskGrad.addColorStop(1, "rgba(0,0,0,0)");
      mctx.globalCompositeOperation = "destination-out";
      mctx.fillStyle = maskGrad;
      mctx.fillRect(0, maskY1, w, maskY2 - maskY1);
      mctx.globalCompositeOperation = "source-over";

      this._portraitMaskedKey = cacheKey;
    }
    ctx.drawImage(this._portraitMaskedCanvas, 0, 0);
  }

  // (13/11/2026) Tay SAU portrait (đè lên vai + đàn) — vẽ cuối để luôn thấy.
  // 2 tay đánh đàn: rotate theo nhịp, ngón tay chạm phím.
  _renderArmsOverPortrait(ctx, w, h, now, config) {
    // (13/11 đêm) BỎ sway riêng — cùng head transform với portrait → hết seam.

    // Nhịp đánh đàn: nhanh hơn khi SPEAKING, chậm hơn khi IDLE
    const beatSpeed = this.state === "SPEAKING" ? 0.008 : 0.004;
    const beatPhase = (now - this.startTime) * beatSpeed;

    ctx.save();

    // (13/11 đêm) Anchor MỚI: vai thật của portrait mặt cận nằm ở cạnh dưới
    // (0.88h, x 0.24/0.76) — tay vươn XUỐNG vào đàn dưới đáy, không đè mặt.
    const shoulderL = { x: w * 0.26, y: h * 0.88 };
    const shoulderR = { x: w * 0.74, y: h * 0.88 };

    // reach ngắn (0.10): bàn tay rơi ~0.93-0.97h — NGAY TRÊN PHÍM (kbTop 0.935h)
    const leftHandAngle = Math.sin(beatPhase) * 0.10 + 0.42;
    const leftHandReach = 0.105 + Math.sin(beatPhase * 1.3) * 0.008;
    this._drawArm(ctx, shoulderL, leftHandAngle, leftHandReach, w, h, "left");

    const rightHandAngle = Math.sin(beatPhase + Math.PI * 0.55) * 0.08 - 0.42;
    const rightHandReach = 0.100 + Math.sin(beatPhase * 1.7 + 1.0) * 0.007;
    this._drawArm(ctx, shoulderR, rightHandAngle, rightHandReach, w, h, "right");

    ctx.restore();
  }

  // (13/11 tối) Cánh tay MỀM: cong vai→khuỷu→cổ tay (quadratic), nét thon dần,
  // bàn tay ellipse da có gradient + highlight — hết cảm giác que cắm hoa.
  _drawArm(ctx, shoulder, angle, reach, w, h, side) {
    const armLen = w * reach;
    const handX = shoulder.x + Math.sin(angle) * armLen;
    const handY = shoulder.y + Math.cos(angle) * armLen;
    // Khuỷu: lệch nhẹ ra ngoài + xuống dưới → cánh tay cong tự nhiên
    const elbowX = shoulder.x + Math.sin(angle * 0.55) * armLen * 0.52
      + (side === "left" ? -w * 0.014 : w * 0.014);
    const elbowY = shoulder.y + Math.cos(angle * 0.55) * armLen * 0.52 + w * 0.010;

    ctx.save();
    ctx.lineCap = "round";
    // Tay áo: 2 nét cong lồng (đậm dưới, nhạt trên) — cảm giác vải mềm
    ctx.beginPath();
    ctx.moveTo(shoulder.x, shoulder.y);
    ctx.quadraticCurveTo(elbowX, elbowY, handX, handY);
    ctx.strokeStyle = "rgba(150, 110, 200, 0.55)";
    ctx.lineWidth = w * 0.055;
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(shoulder.x, shoulder.y);
    ctx.quadraticCurveTo(elbowX, elbowY, handX, handY);
    ctx.strokeStyle = "rgba(195, 160, 235, 0.60)";
    ctx.lineWidth = w * 0.040;
    ctx.stroke();

    // Bàn tay: ellipse da gradient + highlight mềm
    const handR = w * 0.026;
    const handGrad = ctx.createRadialGradient(
      handX - handR * 0.3, handY - handR * 0.3, handR * 0.2,
      handX, handY, handR * 1.2
    );
    handGrad.addColorStop(0, "rgba(255, 228, 208, 0.98)");
    handGrad.addColorStop(1, "rgba(238, 192, 168, 0.95)");
    ctx.fillStyle = handGrad;
    ctx.beginPath();
    ctx.ellipse(handX, handY, handR * 1.18, handR * 0.88, angle * 0.4, 0, Math.PI * 2);
    ctx.fill();

    // Lắc tay bạc (mẫu ảnh) — nét mảnh nhẹ nhàng
    if (side === "right") {
      ctx.strokeStyle = "rgba(225, 225, 245, 0.75)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(handX - w * 0.014, handY - w * 0.004, w * 0.011, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.restore();
  }
}

if (typeof window !== "undefined") {
  window.DigitalHumanAvatar = DigitalHumanAvatar;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = { DigitalHumanAvatar };
}
