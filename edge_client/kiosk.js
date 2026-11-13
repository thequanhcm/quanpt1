/**
 * QUAN AI BRAIN — Raspberry Pi 5 Touch Kiosk Script & Hands-Free Physical Embodiment
 * 
 * Capabilities:
 * - 24/7 Digital Human (Model F) with responsive emotion states & viseme mouth sync
 * - Hands-free wake word engine ("Hi CHERRY", "Cherry ơi", quá độ "Tony ơi") via USB microphone
 * - Natural Vietnamese female speech playback via USB speaker
 * - Real-time LAN synchronization with PC Executive Core Desk
 */
document.addEventListener("DOMContentLoaded", () => {
  const viewport = document.getElementById("avatar-viewport");
  const coreDot = document.getElementById("core-status-dot");
  const coreText = document.getElementById("core-status-text");
  const clockEl = document.getElementById("kiosk-clock");
  const transcriptEl = document.getElementById("transcript-line");
  const taskTextEl = document.getElementById("task-glance-text");
  const marqueeTrack = document.getElementById("marquee-track");
  const bannerEl = document.getElementById("consultation-banner");
  const bannerText = document.getElementById("consultation-banner-text");
  const overlay = document.getElementById("offline-overlay");
  const btnWake = document.getElementById("btn-touch-wake");
  const btnStop = document.getElementById("btn-touch-stop");
  const canvas = document.getElementById("kiosk-waveform");

  const lidTopL = document.getElementById("lid-top-l");
  const lidBotL = document.getElementById("lid-bot-l");
  const lidTopR = document.getElementById("lid-top-r");
  const lidBotR = document.getElementById("lid-bot-r");
  const browLeft = document.getElementById("avatar-brow-left");
  const browRight = document.getElementById("avatar-brow-right");
  const symbolOverlay = document.getElementById("avatar-symbol-overlay");
  const symbolText = document.getElementById("avatar-symbol-text");
  // (13/11/2026) Overlay effects: caption + particles canvas
  const stateCaption = document.getElementById("state-caption");
  const particlesCanvas = document.getElementById("particles-canvas");

  let currentAvatarState = "IDLE";
  let isCoreConnected = true;
  let latestCoreHost = "192.168.1.11:8766";
  let currentKioskAudio = null;
  let wakeEngine = null;

  // Initialize Digital Human Engine (Model F) on Raspberry Pi 5
  try {
    if (typeof DigitalHumanAvatar !== "undefined") {
      window.digitalHuman = new DigitalHumanAvatar("kiosk-avatar-canvas", {
        basePath: "/assets/avatar",
        initialState: "IDLE"
      });
    }
  } catch (e) {
    console.warn("DigitalHumanAvatar init warning on Pi 5:", e);
  }

  const STATE_CONFIG = {
    IDLE: { css: "state-idle", browL: "M 65 65 Q 90 63 115 65", browR: "M 165 65 Q 190 63 215 65", symbol: null },
    LISTENING: { css: "state-listening", browL: "M 65 60 Q 90 58 115 60", browR: "M 165 60 Q 190 58 215 60", symbol: null },
    THINKING: { css: "state-thinking", browL: "M 65 67 L 115 72", browR: "M 165 72 L 215 67", symbol: null },
    RESEARCHING: { css: "state-researching", browL: "M 65 64 L 115 64", browR: "M 165 64 L 215 64", symbol: null },
    LEARNING: { css: "state-learning", browL: "M 65 62 L 115 64", browR: "M 165 64 L 215 62", symbol: null },
    SPEAKING: { css: "state-speaking", browL: "M 65 65 Q 90 63 115 65", browR: "M 165 65 Q 190 63 215 65", symbol: null },
    WARNING: { css: "state-warning", browL: "M 65 74 L 115 68", browR: "M 165 68 L 215 74", symbol: "⚠️" },
    HAPPY: { css: "state-happy", browL: "M 65 62 Q 90 58 115 62", browR: "M 165 62 Q 190 58 215 62", symbol: null },
    CONFUSED: { css: "state-confused", browL: "M 65 64 Q 90 60 115 66", browR: "M 165 62 Q 190 66 215 64", symbol: "❓" },
    EMPATHETIC: { css: "state-empathic", browL: "M 65 63 Q 90 60 115 64", browR: "M 165 64 Q 190 60 215 63", symbol: null },
    WAITING_FOR_OWNER: { css: "state-waiting", browL: "M 65 62 Q 90 60 115 62", browR: "M 165 62 Q 190 60 215 62", symbol: "📬" },
    BLOCKED: { css: "state-blocked", browL: "M 65 72 L 115 64", browR: "M 165 64 L 215 72", symbol: "🛡️" },
    ERROR: { css: "state-error", browL: "M 65 72 L 115 64", browR: "M 165 64 L 215 72", symbol: "⚠️" },
    SAFE_MODE: { css: "state-safemode", browL: "M 65 65 L 115 65", browR: "M 165 65 L 215 65", symbol: "❄️" },
    OFFLINE: { css: "state-offline", browL: "M 65 68 L 115 68", browR: "M 165 68 L 215 68", symbol: null },
    SLEEPING: { css: "state-sleeping", browL: "M 65 68 L 115 68", browR: "M 165 68 L 215 68", symbol: "💤" },
  };

  // (13/11/2026) Caption tiếng Việt cho từng state (mẫu pi5 template.mp4)
  const STATE_CAPTIONS = {
    IDLE: "SẴN SÀNG",
    LISTENING: "ĐANG LẮNG NGHE",
    THINKING: "ĐANG SUY LUẬN",
    RESEARCHING: "ĐANG NGHIÊN CỨU",
    LEARNING: "ĐANG HỌC",
    SPEAKING: "ĐANG NÓI",
    HAPPY: "HOÀN THÀNH",
    SUCCESS: "THÀNH CÔNG",
    EMPATHETIC: "ĐỒNG CẢM",
    CONFUSED: "CHƯA RÕ",
    WARNING: "CẢNH BÁO",
    WAITING_FOR_OWNER: "CHỜ PHÊ DUYỆT",
    BLOCKED: "ĐÃ CHẶN",
    ERROR: "SỰ CỐ",
    SAFE_MODE: "ĐÓNG BĂNG",
    OFFLINE: "MẤT KẾT NỐI",
    RECONNECTING: "ĐANG KẾT NỐI LẠI",
    SLEEPING: "TẠM NGHỈ",
  };

  function setAvatarState(stateKey) {
    if (!STATE_CONFIG[stateKey]) stateKey = "IDLE";
    currentAvatarState = stateKey;
    const conf = STATE_CONFIG[stateKey];

    if (window.digitalHuman) {
      window.digitalHuman.setState(stateKey);
    }

    if (viewport) {
      Object.values(STATE_CONFIG).forEach(c => viewport.classList.remove(c.css));
      viewport.classList.add(conf.css);
    }

    if (browLeft) browLeft.setAttribute("d", conf.browL);
    if (browRight) browRight.setAttribute("d", conf.browR);

    if (symbolOverlay && symbolText) {
      if (conf.symbol) {
        symbolText.textContent = conf.symbol;
        symbolOverlay.style.display = "block";
      } else {
        symbolOverlay.style.display = "none";
      }
    }

    // (13/11/2026) Cập nhật caption theo state
    if (stateCaption) {
      const captionText = STATE_CAPTIONS[stateKey] || stateKey;
      if (stateCaption.textContent !== captionText) {
        stateCaption.textContent = captionText;
      }
    }

    if (stateKey === "OFFLINE" || stateKey === "SLEEPING") {
      if (lidTopL) lidTopL.setAttribute("height", "21");
      if (lidBotL) { lidBotL.setAttribute("height", "21"); lidBotL.setAttribute("y", "96"); }
      if (lidTopR) lidTopR.setAttribute("height", "21");
      if (lidBotR) { lidBotR.setAttribute("height", "21"); lidBotR.setAttribute("y", "96"); }
    } else {
      if (lidTopL) lidTopL.setAttribute("height", "0");
      if (lidBotL) { lidBotL.setAttribute("height", "0"); lidBotL.setAttribute("y", "117"); }
      if (lidTopR) lidTopR.setAttribute("height", "0");
      if (lidBotR) { lidBotR.setAttribute("height", "0"); lidBotR.setAttribute("y", "117"); }
    }

    updateMouthAnimation(stateKey);
  }

  const mouthLine = document.getElementById("mouth-line");
  let mouthAnimInterval = null;

  function updateMouthAnimation(stateKey) {
    if (mouthAnimInterval) {
      clearInterval(mouthAnimInterval);
      mouthAnimInterval = null;
    }
    if (!mouthLine) return;

    // (06/11/2026, owner: "hình chuyển động theo giọng nói mượt mà") Bộ miệng
    // SVG random 110ms CHỈ là fallback khi canvas avatar chưa có timeline
    // (asset chưa load / engine lỗi). Khi window.digitalHuman sẵn sàng, lip-sync
    // do MouthSyncEngine timeline trên canvas đảm nhiệm — tắt đường cũ để tránh
    // 2 nguồn trộn nhau gây giật (judder).
    if (stateKey === "SPEAKING") {
      if (window.digitalHuman && window.digitalHuman.loaded) return; // canvas lo
      const visemes = ["mouth-open-A", "mouth-open-O", "mouth-open-E", "mouth-open-I", "mouth-open-U"];
      mouthAnimInterval = setInterval(() => {
        visemes.forEach(v => mouthLine.classList.remove(v));
        const v = visemes[Math.floor(Math.random() * visemes.length)];
        mouthLine.classList.add(v);
        setTimeout(() => {
          if (mouthLine) {
            visemes.forEach(cls => mouthLine.classList.remove(cls));
          }
        }, 75);
      }, 110);
    } else {
      ["mouth-open-A", "mouth-open-O", "mouth-open-E", "mouth-open-I", "mouth-open-U"].forEach(v => mouthLine.classList.remove(v));
      mouthLine.classList.add("mouth-rest");
    }
  }

  // Periodic natural eye blinking
  function triggerBlink() {
    if (currentAvatarState !== "OFFLINE" && currentAvatarState !== "BLOCKED" && currentAvatarState !== "SLEEPING") {
      if (lidTopL) lidTopL.setAttribute("height", "20");
      if (lidBotL) { lidBotL.setAttribute("height", "20"); lidBotL.setAttribute("y", "97"); }
      if (lidTopR) lidTopR.setAttribute("height", "20");
      if (lidBotR) { lidBotR.setAttribute("height", "20"); lidBotR.setAttribute("y", "97"); }

      setTimeout(() => {
        if (currentAvatarState !== "OFFLINE" && currentAvatarState !== "SLEEPING") {
          if (lidTopL) lidTopL.setAttribute("height", "0");
          if (lidBotL) { lidBotL.setAttribute("height", "0"); lidBotL.setAttribute("y", "117"); }
          if (lidTopR) lidTopR.setAttribute("height", "0");
          if (lidBotR) { lidBotR.setAttribute("height", "0"); lidBotR.setAttribute("y", "117"); }
        }
      }, 120);
    }
    setTimeout(triggerBlink, 3500 + Math.random() * 2500);
  }
  setTimeout(triggerBlink, 3000);

  // (07/11/2026) FIX TDZ: 3 biến audio phải khai báo TRƯỚC initWaveform() —
  // render() chạy đồng bộ lúc init và đọc kioskAudioAnalyser (L188); khai báo
  // let ở dưới (L257-259) khiến JS ném "Cannot access before initialization"
  // → toàn bộ handler DOMContentLoaded chết → đồng hồ kiosk đứng "--:--:--".
  let kioskAudioCtx = null;
  let kioskAudioAnalyser = null;
  let kioskAudioData = null;

  // (31/10/2026) VU METER DỌC — thanh mức âm thanh dọc bên phải màn:
  // cột bar chạy TỪ DƯỚI LÊN, thể hiện mic (LISTENING) và loa phát (SPEAKING).
  function initWaveform() {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    // (31/10 ~19:30) VU NGANG trong header (canvas ngang 150x18): 16 cột dọc nhỏ
    const numBars = 16;
    let phase = 0;

    function render() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      phase += 0.08;

      const w = canvas.width;
      const h = canvas.height;
      const slot = w / numBars;
      const barW = Math.max(3, slot - 3);

      // (06/11/2026) Energy THẬT từ audio đang phát (nếu analyser sẵn sàng)
      let liveEnergy = 0;
      let liveSpectrum = null;
      if (kioskAudioAnalyser && kioskAudioData && currentAvatarState === "SPEAKING") {
        kioskAudioAnalyser.getByteFrequencyData(kioskAudioData);
        let sum = 0;
        for (let i = 0; i < kioskAudioData.length; i++) sum += kioskAudioData[i];
        liveEnergy = sum / (kioskAudioData.length * 255); // 0..1
        liveSpectrum = kioskAudioData;
      }

      for (let i = 0; i < numBars; i++) {
        const x = i * slot + 1;
        let barH = 3;
        let color = "rgba(0, 229, 255, 0.4)";

        if (currentAvatarState === "SPEAKING") {
          if (liveSpectrum) {
            // Giác quan THẬT: mỗi cột = 1 dải tần của audio đang phát
            const bin = Math.floor((i / numBars) * liveSpectrum.length);
            const v = liveSpectrum[bin] / 255;
            barH = 3 + v * (h - 6);
            color = v > 0.55 ? "rgba(96, 165, 250, 1.0)" : "rgba(59, 130, 246, 0.95)";
          } else {
            const factor = Math.sin(phase * 2.5 + i * 0.55) * 0.5 + 0.5;
            barH = 3 + factor * (h - 6);
            color = "rgba(59, 130, 246, 0.95)";
          }
        } else if (currentAvatarState === "LISTENING") {
          const factor = Math.sin(phase * 3.2 + i * 0.65) * 0.5 + 0.5;
          barH = 3 + factor * (h - 6);
          color = "rgba(6, 182, 212, 0.95)";
        } else if (currentAvatarState === "THINKING") {
          const factor = Math.cos(phase * 1.5 + i * 0.45) * 0.5 + 0.5;
          barH = 3 + factor * (h - 6);
          color = "rgba(168, 85, 247, 0.9)";
        } else if (currentAvatarState === "OFFLINE") {
          barH = 3;
          color = "rgba(100, 116, 139, 0.3)";
        } else {
          const mid = numBars / 2;
          const dist = Math.abs(i - mid);
          const pulse = Math.sin(phase * 0.8) * 0.5 + 0.5;
          barH = 2 + Math.max(1, (h * 0.55 - dist * 1.2) * pulse);
          color = "rgba(0, 229, 255, 0.55)";
        }

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.roundRect(x, h - barH, barW, barH, 2);
        ctx.fill();
      }

      requestAnimationFrame(render);
    }
    render();
  }
  initWaveform();

  // Local Clock
  function updateClock() {
    if (clockEl) {
      const now = new Date();
      clockEl.textContent = now.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    }
  }
  setInterval(updateClock, 1000);
  updateClock();

  // Play Speech Audio on Raspberry Pi 5
  // (06/11/2026) VU meter THẬT: dùng WebAudio AnalyserNode đo amplitude audio
  // đang phát → thanh VU chạy đúng "giác quan" (nghe gì hiện nấy), không giả lập.
  // (07/11/2026) 3 biến đã chuyển lên TRƯỚC initWaveform() — fix TDZ.

  function attachAnalyser(audio) {
    try {
      if (!kioskAudioCtx) kioskAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (kioskAudioCtx.state === "suspended") { kioskAudioCtx.resume().catch(() => {}); }
      const src = kioskAudioCtx.createMediaElementSource(audio);
      kioskAudioAnalyser = kioskAudioCtx.createAnalyser();
      kioskAudioAnalyser.fftSize = 64;
      kioskAudioData = new Uint8Array(kioskAudioAnalyser.frequencyBinCount);
      src.connect(kioskAudioAnalyser);
      kioskAudioAnalyser.connect(kioskAudioCtx.destination);
      return true;
    } catch (err) {
      // Nền tảng chặn WebAudio → fallback về VU giả lập (không chết tiếng)
      kioskAudioAnalyser = null;
      return false;
    }
  }

  function playKioskSpeech(audioBase64, timeline, spokenText) {
    if (!audioBase64) return;
    try {
      if (currentKioskAudio) {
        try { currentKioskAudio.pause(); } catch (_) {}
        currentKioskAudio = null;
      }

      if (wakeEngine) {
        wakeEngine.notifySpeakingStart();
      }

      const audio = new Audio("data:audio/mpeg;base64," + audioBase64);
      currentKioskAudio = audio;
      setAvatarState("SPEAKING");
      // (06/11/2026) Gắn analyser để VU meter + avatar đọc energy THẬT
      const analyserOk = attachAnalyser(audio);

      // (31/10) BIỂU CẢM THEO NỘI DUNG: micro-expression theo cảm xúc câu nói
      if (window.digitalHuman && spokenText) {
        window.digitalHuman.setContextFromText(spokenText);
      }
      if (window.digitalHuman && timeline) {
        window.digitalHuman.setTimeline(timeline);
      } else if (window.digitalHuman && analyserOk) {
        // (06/11/2026) Không có timeline (TTS fallback khác) nhưng có audio thật:
        // chạy chế độ SPEAKING + để engine đọc liveEnergy từ analyser.
        window.digitalHuman.setLiveAudioMeter(() => {
          if (!kioskAudioAnalyser || !kioskAudioData || !currentKioskAudio) return 0;
          kioskAudioAnalyser.getByteFrequencyData(kioskAudioData);
          let sum = 0;
          for (let i = 0; i < kioskAudioData.length; i++) sum += kioskAudioData[i];
          return sum / (kioskAudioData.length * 255); // 0..1
        });
      }

      audio.onended = () => {
        currentKioskAudio = null;
        setAvatarState("IDLE");
        if (window.digitalHuman) {
          window.digitalHuman.cancelUtterance();
          window.digitalHuman.setState("IDLE");
          window.digitalHuman.resetMicroExpression();
          window.digitalHuman.setLiveAudioMeter(null); // (06/11/2026) ngắt meter
        }
        if (wakeEngine) {
          wakeEngine.notifySpeakingEnd();
        }
      };

      audio.onerror = (e) => {
        console.warn("Kiosk audio playback error:", e);
        currentKioskAudio = null;
        setAvatarState("IDLE");
        if (window.digitalHuman) {
          window.digitalHuman.cancelUtterance();
          window.digitalHuman.setState("IDLE");
          window.digitalHuman.resetMicroExpression();
          window.digitalHuman.setLiveAudioMeter(null);
        }
        if (wakeEngine) {
          wakeEngine.notifySpeakingEnd();
        }
      };

      audio.play().catch(e => {
        console.warn("Kiosk audio play warning:", e);
      });
    } catch (err) {
      console.warn("Exception playing speech on kiosk:", err);
    }
  }

  // Handle User Voice Query -> Send to PC Executive Core
  async function handleUserVoiceQuery(userQuery) {
    if (!userQuery || !userQuery.trim()) return;
    const cleanQuery = userQuery.trim();
    if (transcriptEl) transcriptEl.textContent = `Anh: "${cleanQuery}"`;
    setAvatarState("THINKING");

    if (wakeEngine) {
      wakeEngine.notifyThinking();
    }

    try {
      const coreHost = latestCoreHost || "192.168.1.11:8766";
      const coreUrl = `http://${coreHost}/api/voice/interact`;

      const res = await fetch(coreUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: cleanQuery,
          text: cleanQuery,
          is_push_to_talk: false,
          client: "pi5_kiosk",
          device_id: "EDGE-PI5-DESK-01"
        })
      });

      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();

      if (data.success && (data.spoken_text || data.reply || data.response_text)) {
        const replyText = data.spoken_text || data.reply || data.response_text;
        if (transcriptEl) transcriptEl.textContent = `CHERRY: "${replyText}"`;

        if (data.audio_base64) {
          playKioskSpeech(data.audio_base64, data.mouth_timeline || data.timeline);
        } else {
          setAvatarState("IDLE");
          if (wakeEngine) wakeEngine.notifySpeakingEnd();
        }
      } else {
        if (transcriptEl) transcriptEl.textContent = `"Em đã nghe thấy, nhưng chưa nhận được nội dung trả lời từ PC."`;
        setAvatarState("IDLE");
        if (wakeEngine) wakeEngine.notifySpeakingEnd();
      }
    } catch (err) {
      console.warn("Failed to reach PC Core for voice query:", err);
      if (transcriptEl) transcriptEl.textContent = `"Lỗi kết nối với Bàn Điều Hành PC Core."`;
      setAvatarState("IDLE");
      if (wakeEngine) wakeEngine.notifySpeakingEnd();
    }
  }

  // Initialize Wake Word Engine on Pi 5
  function loadWakeEngineScript(cb) {
    if (typeof WakeWordEngine !== "undefined") { cb(); return; }
    const s = document.createElement("script");
    s.src = "/wake_engine.js?v=mic_only_31oct_g";
    s.onload = cb;
    s.onerror = () => console.warn("Không nạp được wake_engine.js");
    document.head.appendChild(s);
  }

  function initVoiceEngine() {
    // (31/10/2026) mic-only: KHÔNG nạp engine khi mở trang. Chỉ nạp khi bấm nút mic.
    if (window.__WAKE_ENGINE_DEFERRED__) return;
    if (typeof WakeWordEngine === "undefined") {
      console.warn("WakeWordEngine script not loaded, retrying in 1s...");
      setTimeout(initVoiceEngine, 1000);
      return;
    }

    try {
      wakeEngine = new WakeWordEngine({
        silenceTimeoutSeconds: 15.0,
        chimeEnabled: true,
        lang: "vi-VN",
        coreHost: latestCoreHost,
        onStateChange: (newState, oldState, reason) => {
          if (currentAvatarState === "SPEAKING") return;
          if (newState === "LISTENING") {
            setAvatarState("LISTENING");
            if (transcriptEl) transcriptEl.textContent = `"Đang lắng nghe Anh..."`;
          } else if (newState === "THINKING") {
            setAvatarState("THINKING");
          } else if (newState === "STANDBY" && currentAvatarState !== "SLEEPING") {
            setAvatarState("IDLE");
          }
        },
        onWakeDetected: (keyword, payload) => {
          console.log(`[Pi5 Wake Word] Detected: ${keyword}`);
          setAvatarState("LISTENING");
          if (transcriptEl) transcriptEl.textContent = `"Dạ em nghe Anh! (${keyword})"`;

          if (btnWake) {
            btnWake.classList.add("listening");
            setTimeout(() => { if (btnWake) btnWake.classList.remove("listening"); }, 3000);
          }

          if (payload && payload.trim().length > 2) {
            handleUserVoiceQuery(payload.trim());
          }
        },
        onCommandRecognized: (transcript) => {
          console.log(`[Pi5 Speech Recognized] ${transcript}`);
          handleUserVoiceQuery(transcript);
        },
        onError: (err) => {
          console.warn("[Pi5 Voice Recognition Warning]:", err);
        }
      });

      // (31/10/2026) Owner policy: CHỈ auto-listen khi config cho phép (enabled=true).
      // Mặc định = IM LẶNG; nút mic "CHERRY ƠI..." trên màn hình vẫn hoạt động.
      wakeEngine.syncConfigFromBackend().then(() => {
        if (wakeEngine.options.autoStart === false) {
          console.log("Voice engine auto-start DISABLED by core config (mic-only activation).");
          return;
        }
        return wakeEngine.start();
      }).then(ok => {
        if (ok) {
          console.log("QUAN AI BRAIN — Hands-Free Voice Engine ACTIVE on Raspberry Pi 5!");
        }
      }).catch(err => {
        console.warn("Voice engine auto-start notice:", err);
      });
    } catch (exc) {
      console.warn("Failed to initialize WakeWordEngine on Pi 5:", exc);
    }
  }
  initVoiceEngine();

  // Poll Local Edge Daemon
  async function pollDaemonStatus() {
    try {
      const res = await fetch("/api/kiosk/status", { cache: "no-store" });
      if (!res.ok) throw new Error("Daemon HTTP error " + res.status);
      const data = await res.json();

      isCoreConnected = data.core_connected === true;
      if (data.core_host) {
        latestCoreHost = data.core_host;
        if (wakeEngine) wakeEngine.options.coreHost = latestCoreHost;
      }

      // (31/10/2026) Điều khiển từ xa: mở URL thật trên màn Pi (YouTube,
      // Google search, trang tin...). Dùng OVERLAY IFRAME fullscreen — giữ
      // kiosk sống (poll/status/wake engine vẫn chạy, CHERRY quay lại được).
      if (data.navigation_url) {
        console.log("Remote navigation received:", data.navigation_url);
        let nv = document.getElementById("kiosk-web-overlay");
        if (!nv) {
          nv = document.createElement("iframe");
          nv.id = "kiosk-web-overlay";
          nv.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;"
            + "border:none;z-index:99999;background:#000;";
          document.body.appendChild(nv);
        }
        if (nv.src !== data.navigation_url) {
          nv.src = data.navigation_url;
        }
      } else if (data.navigation_url === "") {
        // Lệnh "cherry về"/"tony về" (quá độ) — đóng overlay web, hiển thị lại hình thể CHERRY.
        const old = document.getElementById("kiosk-web-overlay");
        if (old) old.remove();
        console.log("Web overlay closed — back to CHERRY avatar");
      }

      // (31/10/2026) Hiển thị ảnh DM trên màn Pi: image_url non-null → overlay
      // <img> fullscreen; null/quá hạn → gỡ overlay, quay về avatar CHERRY.
      // Daemon tự hết hạn theo `until` (show_image duration_sec, mặc định 15s)
      // nên kiosk chỉ phản chiếu trạng thái — không cần timer riêng ở đây.
      let kioskImg = document.getElementById("kiosk-image-overlay");
      if (data.image_url) {
        const srcUrl = data.image_url.startsWith("http")
          ? data.image_url
          : "http://" + location.host + data.image_url;
        if (!kioskImg) {
          kioskImg = document.createElement("img");
          kioskImg.id = "kiosk-image-overlay";
          kioskImg.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;"
            + "object-fit:contain;background:#000;z-index:100000;";
          kioskImg.alt = "Anh gui tu NetChat";
          document.body.appendChild(kioskImg);
        }
        if (kioskImg.getAttribute("src") !== srcUrl) kioskImg.src = srcUrl;
      } else if (kioskImg) {
        kioskImg.remove();
        console.log("Image overlay removed — back to CHERRY avatar");
      }

      // (31/10/2026) LIVE CAMERA: camera_streaming=true → overlay MJPEG fullscreen
      // (ảnh live trực tiếp từ Camera Module 3); false → gỡ overlay về avatar.
      let camLive = document.getElementById("kiosk-camera-live");
      if (data.camera_streaming) {
        if (!camLive) {
          camLive = document.createElement("img");
          camLive.id = "kiosk-camera-live";
          camLive.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;"
            + "object-fit:cover;background:#000;z-index:100001;";
          camLive.alt = "Camera live tu Pi5";
          document.body.appendChild(camLive);
        }
        const mjpegUrl = "http://" + location.host + "/api/kiosk/camera/mjpeg";
        if (camLive.getAttribute("src") !== mjpegUrl) camLive.src = mjpegUrl;
      } else if (camLive) {
        camLive.src = "";
        camLive.remove();
        console.log("Camera live overlay removed — back to CHERRY avatar");
      }

      if (data.need_ui_reload) {
        console.log("Remote reload signal received from PC Core...");
        location.reload();
        return;
      }

      if (isCoreConnected) {
        if (overlay) overlay.classList.add("hidden");
        if (coreDot) { coreDot.className = "status-indicator-dot online"; }
        if (coreText) { coreText.textContent = `CORE: ONLINE (${data.core_host || "PC"})`; }

        // (31/10) MARQUEE: hội thoại đang giao tiếp — bản tiếng Anh từ PC core,
        // fallback transcript gốc nếu chưa có bản dịch.
        if (marqueeTrack) {
          const enText = (data.transcript_en || data.transcript || "").trim();
          if (enText && marqueeTrack.dataset.text !== enText) {
            marqueeTrack.dataset.text = enText;
            marqueeTrack.textContent = enText;
            // restart animation khi text đổi
            marqueeTrack.style.animation = "none";
            void marqueeTrack.offsetWidth;
            marqueeTrack.style.animation = "";
          }
        }

        // Apply pure Face-Only mode
        if (data.face_only_mode) {
          document.body.classList.add("face-only-mode");
        } else {
          document.body.classList.remove("face-only-mode");
        }

        if (data.pending_audio_base64) {
          playKioskSpeech(data.pending_audio_base64, data.pending_timeline, data.transcript);
        } else if (data.avatar_state && currentAvatarState !== "SPEAKING") {
          setAvatarState(data.avatar_state);
        }

        if (data.transcript && transcriptEl) {
          // (31/10) biểu cảm LUÔN theo nội dung giao tiếp mới nhất
          transcriptEl.textContent = `"${data.transcript}"`;
          if (window.digitalHuman && typeof window.digitalHuman.setContextFromText === "function") {
            window.digitalHuman.setContextFromText(data.transcript);
          }
        }

        // Music streaming coordination on Pi 5 Kiosk
        if (data.music && data.music.playing && data.music.video_id) {
          if (!window._kioskCurrentVid || window._kioskCurrentVid !== data.music.video_id) {
            window._kioskCurrentVid = data.music.video_id;
            let mf = document.getElementById("kiosk-music-frame");
            if (!mf) {
              mf = document.createElement("iframe");
              mf.id = "kiosk-music-frame";
              mf.style.cssText = "display:none;width:0;height:0;border:none;";
              mf.allow = "autoplay";
              document.body.appendChild(mf);
            }
            mf.src = `https://www.youtube.com/embed/${data.music.video_id}?autoplay=1&playsinline=1`;
            if (transcriptEl && currentAvatarState === "IDLE") {
              transcriptEl.textContent = `🎵 Đang phát: ${data.music.title || "YouTube Music"}`;
            }
          }
        } else if (!data.music || !data.music.playing) {
          if (window._kioskCurrentVid) {
            window._kioskCurrentVid = null;
            const mf = document.getElementById("kiosk-music-frame");
            if (mf) mf.src = "about:blank";
          }
        }

        if (data.proposals_pending > 0 && bannerEl) {
          bannerEl.classList.remove("hidden");
          // (31/10/2026) Set CỨNG mỗi vòng poll — ghi đè mọi text cũ (kể cả
          // notification tiếng Anh còn sót từ phiên trước) để banner luôn chuẩn.
          const wantText = `Có ${data.proposals_pending} đề xuất cần Anh phê duyệt trên PC`;
          if (bannerText && bannerText.textContent !== wantText) bannerText.textContent = wantText;
        } else if (bannerEl) {
          bannerEl.classList.add("hidden");
        }
      } else {
        triggerDisconnectedState();
      }
    } catch (err) {
      triggerDisconnectedState();
    }
  }

  function triggerDisconnectedState() {
    isCoreConnected = false;
    if (overlay) overlay.classList.add("hidden");
    if (coreDot) { coreDot.className = "status-indicator-dot offline"; }
    if (coreText) { coreText.textContent = "CORE: ĐANG KẾT NỐI WI-FI..."; }
    if (transcriptEl && currentAvatarState !== "SPEAKING") {
      transcriptEl.textContent = `"Đang sẵn sàng... Chờ lệnh từ Bàn Điều Hành PC."`;
    }

    if (currentAvatarState !== "SLEEPING" && currentAvatarState !== "SPEAKING") {
      setAvatarState("IDLE");
    }
  }

  // Touch STOP Button
  if (btnStop) {
    btnStop.addEventListener("click", async () => {
      // (01/11/2026, owner) STOP = CHỈ THOÁT giao diện hiển thị hình thể:
      // đóng chromium kiosk, màn hình + hệ thống giữ nguyên; daemon vẫn
      // ACTIVE; không emergency, không tắt nguồn, không tắt màn.
      // Owner gọi lại "Cherry ơi" (hoặc chạm nút CHERRY ƠI) là giao diện mở lại.
      if (currentKioskAudio) {
        try { currentKioskAudio.pause(); } catch (_) {}
        currentKioskAudio = null;
      }
      try {
        await fetch("/api/kiosk/control", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "close_kiosk",
            reason: "Quanpt1 chạm nút STOP — thoát giao diện hiển thị" })
        });
      } catch (e) {
        console.warn("Close kiosk failed:", e);
      }
    });
  }

  // Touch Wake Button ("CHERRY ƠI...")
  if (btnWake) {
    btnWake.addEventListener("click", async () => {
      // (31/10/2026) Owner policy: chạm nút = GỌI CHERRY dậy NGAY, phản hồi như
      // wake word "Cherry ơi": bật màn + kiosk sống lại nếu đã bị STOP tắt.
      btnWake.classList.add("listening");
      setAvatarState("LISTENING");
      if (transcriptEl) transcriptEl.textContent = `"Dạ em nghe Anh! Đang lắng nghe..."`;

      try {
        await fetch("/api/kiosk/control", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "wake_by_voice" })
        });
      } catch (e) {
        console.warn("Wake request failed:", e);
      }

      // (31/10/2026) mic-only: nạp engine LẦN ĐẦU bấm nút.
      if (!wakeEngine) {
        loadWakeEngineScript(() => {
          try {
            wakeEngine = new WakeWordEngine({
              silenceTimeoutSeconds: 15.0,
              chimeEnabled: true,
              lang: "vi-VN",
              coreHost: latestCoreHost,
              autoStart: true,
              onWakeDetected: (keyword, payload) => {
                setAvatarState("LISTENING");
                if (transcriptEl) transcriptEl.textContent = `"Dạ em nghe Anh! (${keyword})"`;
                if (payload && payload.trim().length > 2) handleUserVoiceQuery(payload.trim());
              },
              onCommandRecognized: (transcript) => handleUserVoiceQuery(transcript),
              onError: (err) => console.warn("[Pi5 Voice Recognition Warning]:", err)
            });
            wakeEngine.start().then(() => {
              try { if (wakeEngine.recognition) wakeEngine.recognition.start(); } catch (_) {}
            });
          } catch (exc) {
            console.warn("Lazy engine init failed:", exc);
          }
        });
      } else if (wakeEngine) {
        wakeEngine.playWakeChime();
        try {
          if (wakeEngine.recognition) {
            wakeEngine.recognition.start();
          }
        } catch (_) {}
      }

      setTimeout(() => {
        btnWake.classList.remove("listening");
      }, 5000);
    });
  }

  // Poll daemon every 1 second
  pollDaemonStatus();
  setInterval(pollDaemonStatus, 1000);

  // (13/11/2026) PARTICLES ANIMATION: 30-50 hạt ánh sáng bay quanh avatar
  // (mẫu pi5 template.mp4). Tối ưu cho Pi5: cap 12 FPS, alpha thấp, không shadowBlur.
  function initParticles() {
    if (!particlesCanvas) return;
    const ctx = particlesCanvas.getContext("2d");
    const w = particlesCanvas.width;
    const h = particlesCanvas.height;
    const NUM = 40;

    const particles = [];
    for (let i = 0; i < NUM; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        r: 1.0 + Math.random() * 1.8,
        alpha: 0.3 + Math.random() * 0.5,
        hue: 180 + Math.random() * 40, // cyan-blue range
      });
    }

    let lastTs = 0;
    const FRAME_MS = 83; // ~12 FPS

    function loop(ts) {
      if (ts - lastTs >= FRAME_MS) {
        lastTs = ts;
        ctx.clearRect(0, 0, w, h);

        for (let i = 0; i < particles.length; i++) {
          const p = particles[i];
          p.x += p.vx;
          p.y += p.vy;

          // Wrap around edges
          if (p.x < 0) p.x = w;
          if (p.x > w) p.x = 0;
          if (p.y < 0) p.y = h;
          if (p.y > h) p.y = 0;

          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
          ctx.fillStyle = `hsla(${p.hue}, 90%, 70%, ${p.alpha})`;
          ctx.fill();
        }
      }
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  }
  initParticles();
});
