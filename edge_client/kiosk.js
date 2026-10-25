/**
 * QUAN AI BRAIN — Raspberry Pi 5 Touch Kiosk Script & Hands-Free Physical Embodiment
 * 
 * Capabilities:
 * - 24/7 Digital Human (Model F) with responsive emotion states & viseme mouth sync
 * - Hands-free wake word engine ("Hi TONY", "Tony ơi") via USB microphone
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

  let currentAvatarState = "IDLE";
  let isCoreConnected = true;
  let latestCoreHost = "192.168.1.11:8766";
  let currentKioskAudio = null;
  let wakeEngine = null;

  // Guard chống phát đôi: lưu hash của audio đã phát gần nhất
  // Mỗi audio_base64 có độ dài khác nhau, dùng length + 8 ký tự đầu/cuối làm fingerprint
  let _lastPlayedAudioFingerprint = "";
  let _lastPlayedAt = 0;  // epoch ms

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
    WAITING_FOR_OWNER: { css: "state-waiting", browL: "M 65 62 Q 90 60 115 62", browR: "M 165 62 Q 190 60 215 62", symbol: "📬" },
    BLOCKED: { css: "state-blocked", browL: "M 65 72 L 115 64", browR: "M 165 64 L 215 72", symbol: "🛡️" },
    ERROR: { css: "state-error", browL: "M 65 72 L 115 64", browR: "M 165 64 L 215 72", symbol: "⚠️" },
    SAFE_MODE: { css: "state-safemode", browL: "M 65 65 L 115 65", browR: "M 165 65 L 215 65", symbol: "❄️" },
    OFFLINE: { css: "state-offline", browL: "M 65 68 L 115 68", browR: "M 165 68 L 215 68", symbol: null },
    SLEEPING: { css: "state-sleeping", browL: "M 65 68 L 115 68", browR: "M 165 68 L 215 68", symbol: "💤" },
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

    if (stateKey === "SPEAKING") {
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

  // Dynamic Audio Waveform Canvas
  function initWaveform() {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const numBars = 24;
    let phase = 0;

    function render() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      phase += 0.08;

      const w = canvas.width;
      const h = canvas.height;
      const barWidth = Math.max(3, (w - (numBars * 3)) / numBars);

      for (let i = 0; i < numBars; i++) {
        const x = i * (barWidth + 3) + 4;
        let barHeight = 4;
        let color = "rgba(0, 229, 255, 0.4)";

        if (currentAvatarState === "SPEAKING") {
          const factor = Math.sin(phase * 2.5 + i * 0.5) * 0.5 + 0.5;
          barHeight = 5 + factor * 18;
          color = "rgba(59, 130, 246, 0.9)";
        } else if (currentAvatarState === "LISTENING") {
          const factor = Math.sin(phase * 3.2 + i * 0.6) * 0.5 + 0.5;
          barHeight = 5 + factor * 16;
          color = "rgba(6, 182, 212, 0.9)";
        } else if (currentAvatarState === "THINKING") {
          const factor = Math.cos(phase * 1.5 + i * 0.4) * 0.5 + 0.5;
          barHeight = 4 + factor * 12;
          color = "rgba(168, 85, 247, 0.85)";
        } else if (currentAvatarState === "OFFLINE") {
          barHeight = 2;
          color = "rgba(100, 116, 139, 0.25)";
        } else {
          const mid = numBars / 2;
          const dist = Math.abs(i - mid);
          const pulse = Math.sin(phase * 0.8) * 0.5 + 0.5;
          barHeight = 3 + Math.max(0, (5 - dist * 0.4) * pulse);
          color = "rgba(0, 229, 255, 0.5)";
        }

        const y = (h - barHeight) / 2;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
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
  function playKioskSpeech(audioBase64, timeline) {
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

      if (window.digitalHuman && timeline) {
        window.digitalHuman.setTimeline(timeline);
      }

      audio.onended = () => {
        currentKioskAudio = null;
        setAvatarState("IDLE");
        if (window.digitalHuman) {
          window.digitalHuman.cancelUtterance();
          window.digitalHuman.setState("IDLE");
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
        }
        if (wakeEngine) wakeEngine.notifySpeakingEnd();
      };

      audio.play().catch(e => {
        console.warn("Kiosk audio play warning:", e);
      });
    } catch (err) {
      console.warn("Exception playing speech on kiosk:", err);
    }
  }

  // Sprint 2 barge-in: hàm toàn cục — wake_engine gọi khi mic nghe thấy giọng
  // người trong lúc TTS đang phát. Dừng audio kiosk + avatar về LISTENING.
  // Trả về true nếu thực sự có audio bị dừng.
  window.bargeInStopSpeaking = function () {
    let stopped = false;
    if (currentKioskAudio) {
      try {
        currentKioskAudio.pause();
        currentKioskAudio.currentTime = 0;
        stopped = true;
      } catch (err) {
        console.warn("[Kiosk] Barge-in stop error:", err);
      }
      currentKioskAudio = null;
    }
    if (window.digitalHuman && typeof window.digitalHuman.cancelUtterance === "function") {
      try { window.digitalHuman.cancelUtterance(); stopped = true; } catch (_) {}
    }
    if (stopped) {
      setAvatarState("LISTENING");
      if (transcriptEl) transcriptEl.textContent = `"Dạ, em dừng lại nghe Anh ạ."`;
      if (wakeEngine && wakeEngine.notifySpeakingEnd) wakeEngine.notifySpeakingEnd();
    }
    return stopped;
  };

  // Phát một lần duy nhất — dùng trong vòng lặp poll để chống phát đôi
  function playSpeechOnce(audioBase64, timeline) {
    if (!audioBase64) return;

    // Tạo fingerprint gọn: độ dài + 12 ký tự đầu + 12 ký tự cuối
    const fp = audioBase64.length + "|" + audioBase64.slice(0, 12) + "|" + audioBase64.slice(-12);
    const now = Date.now();

    // Nếu đã phát âm này trong vòng 500ms gần đây, bỏ qua
    if (fp === _lastPlayedAudioFingerprint && (now - _lastPlayedAt) < 500) {
      console.log("[Kiosk] Đã phát audio này rồi, bỏ qua trénh chồng lấn.");
      return;
    }

    // Nếu đang phát audio và đó là cùng một audio, bỏ qua
    if (currentKioskAudio && fp === _lastPlayedAudioFingerprint) {
      return;
    }

    _lastPlayedAudioFingerprint = fp;
    _lastPlayedAt = now;
    playKioskSpeech(audioBase64, timeline);
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
        if (transcriptEl) transcriptEl.textContent = `TONY: "${replyText}"`;

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
  function initVoiceEngine() {
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

      // Auto-start continuous wake word listening on Pi 5
      wakeEngine.start().then(ok => {
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

      if (data.need_ui_reload) {
        console.log("Remote reload signal received from PC Core...");
        location.reload();
        return;
      }

      if (isCoreConnected) {
        if (overlay) overlay.classList.add("hidden");
        if (coreDot) { coreDot.className = "status-indicator-dot online"; }
        if (coreText) { coreText.textContent = `CORE: ONLINE (${data.core_host || "PC"})`; }

        // Apply pure Face-Only mode
        if (data.face_only_mode) {
          document.body.classList.add("face-only-mode");
        } else {
          document.body.classList.remove("face-only-mode");
        }

        if (data.pending_audio_base64) {
          // Dùng playSpeechOnce() — chống phát đôi khi daemon và Chromium cùng nhận audio
          playSpeechOnce(data.pending_audio_base64, data.pending_timeline);
        } else if (data.avatar_state && currentAvatarState !== "SPEAKING") {
          setAvatarState(data.avatar_state);
        }

        if (data.transcript && transcriptEl && currentAvatarState !== "SPEAKING" && currentAvatarState !== "THINKING") {
          transcriptEl.textContent = `"${data.transcript}"`;
          if (window.digitalHuman && typeof window.digitalHuman.setContextFromText === "function") {
            window.digitalHuman.setContextFromText(data.transcript);
          }
        }

        if (data.proposals_pending > 0 && bannerEl) {
          bannerEl.classList.remove("hidden");
          if (bannerText) bannerText.textContent = `Có ${data.proposals_pending} đề xuất cần Anh phê duyệt trên PC`;
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
      setAvatarState("BLOCKED");
      if (currentKioskAudio) {
        try { currentKioskAudio.pause(); } catch (_) {}
        currentKioskAudio = null;
      }
      try {
        await fetch("/api/kiosk/emergency_stop", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: "Quanpt1 chạm nút STOP trên màn hình cảm ứng Pi 5" })
        });
      } catch (e) {
        console.warn("Emergency stop failed:", e);
      }
    });
  }

  // Touch Wake Button ("TONY ƠI...")
  if (btnWake) {
    btnWake.addEventListener("click", async () => {
      btnWake.classList.add("listening");
      setAvatarState("LISTENING");
      if (transcriptEl) transcriptEl.textContent = `"Dạ em nghe Anh! Đang lắng nghe..."`;

      if (wakeEngine) {
        wakeEngine.playWakeChime();
        try {
          if (wakeEngine.recognition) {
            wakeEngine.recognition.start();
          }
        } catch (_) {}
      }

      try {
        await fetch("/api/kiosk/wake", { method: "POST" });
      } catch (e) {
        console.warn("Wake request failed:", e);
      }

      setTimeout(() => {
        btnWake.classList.remove("listening");
      }, 5000);
    });
  }

  // Poll daemon every 1 second
  pollDaemonStatus();
  setInterval(pollDaemonStatus, 1000);
});
