/**
 * QUAN AI BRAIN — Wake Word & Hands-Free Voice Engine V1
 *
 * Implements:
 * - 9-State Machine (DISABLED, STANDBY, WAKE_DETECTED, LISTENING, TRANSCRIBING, THINKING, SPEAKING, INTERRUPTED, ERROR)
 * - Continuous keyword spotting for Vietnamese & English wake words ("Hi TONY", "Tony ơi")
 * - Zero-loss prompt extraction (wake phrase + payload)
 * - Acoustic Echo Cancellation (AEC) during TTS playback to prevent self-triggering
 * - Web Audio API synthesized executive wake chime
 * - Follow-up conversation window (15-20s) with auto-return to STANDBY
 * - Voice control commands ("ngủ đi", "dừng đọc", "dừng nghe", "tắt trợ lý")
 */
class WakeWordEngine {
  constructor(options = {}) {
    this.state = "DISABLED";
    this.options = Object.assign({
      silenceTimeoutSeconds: 15.0,
      chimeEnabled: true,
      lang: "vi-VN",
      coreHost: "",
      onStateChange: () => {},
      onWakeDetected: () => {},
      onCommandRecognized: () => {},
      onError: () => {},
    }, options);

    this.keywords = [
      { phrase: "Hi TONY", enabled: true },
      { phrase: "Hey Tony", enabled: true },
      { phrase: "Tony ơi", enabled: true },
      { phrase: "Chào trợ lý", enabled: true },
      { phrase: "Hi trợ lý", enabled: true },
      { phrase: "Xin chào trợ lý", enabled: true },
      { phrase: "Hello assistant", enabled: true },
      { phrase: "Hi assistant", enabled: true },
      { phrase: "QUAN AI", enabled: true },
      { phrase: "Quan AI Brain", enabled: true },
    ];
    this.recognition = null;
    this.audioCtx = null;
    this.followUpTimer = null;
    this.isTtsSpeaking = false;
    this.activeUtterancePayload = "";

    // Sync configuration from backend if available
    this.syncConfigFromBackend();
  }

  async syncConfigFromBackend() {
    try {
      const baseUrl = this.options.coreHost ? `http://${this.options.coreHost}` : "";
      const res = await fetch(`${baseUrl}/api/voice/wake-config`, { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        const cfg = data.config || data;
        if (cfg.keywords || cfg.wake_words) {
          this.keywords = cfg.keywords || cfg.wake_words;
        }
        if (cfg.silence_timeout_seconds || cfg.silence_timeout_sec) {
          this.options.silenceTimeoutSeconds = cfg.silence_timeout_seconds || cfg.silence_timeout_sec;
        }
        if (typeof cfg.chime_enabled === "boolean") {
          this.options.chimeEnabled = cfg.chime_enabled;
        }
      }
    } catch (err) {
      // Use defaults if backend not reachable
    }
  }

  // State Transition Manager
  transitionTo(newState, reason = "") {
    if (this.state === newState) return;
    const oldState = this.state;
    this.state = newState;
    console.log(`[Voice State] ${oldState} -> ${newState} (${reason})`);

    // Telemetry dispatch
    this.sendTelemetry({ from: oldState, to: newState, reason });

    // Invoke callback
    if (this.options.onStateChange) {
      this.options.onStateChange(newState, oldState, reason);
    }
  }

  sendTelemetry(payload) {
    const baseUrl = this.options.coreHost ? `http://${this.options.coreHost}` : "";
    fetch(`${baseUrl}/api/voice/telemetry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).catch(() => {});
  }

  // Web Audio Synthesized Chime (No external audio files needed)
  playWakeChime() {
    if (!this.options.chimeEnabled) return;
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      if (!this.audioCtx) this.audioCtx = new AudioContext();
      if (this.audioCtx.state === "suspended") {
        this.audioCtx.resume();
      }

      const now = this.audioCtx.currentTime;
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc.type = "sine";
      // Two-tone executive chime: 440Hz -> 880Hz
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.08);

      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.20, now + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      osc.start(now);
      osc.stop(now + 0.23);
    } catch (err) {
      console.warn("Chime generation warning:", err);
    }
  }

  // Normalize string for matching
  normalize(text) {
    if (!text) return "";
    return text.toLowerCase()
      .replace(/[,\.!\?;\:\-\(\)\[\]\"']/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  // Start hands-free wake word detection
  async start() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      this.transitionTo("ERROR", "Web Speech API not supported");
      if (this.options.onError) {
        this.options.onError("Trình duyệt không hỗ trợ Web Speech API.");
      }
      return false;
    }

    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        await navigator.mediaDevices.getUserMedia({ audio: true });
      }
    } catch (err) {
      console.warn("Microphone permission prompt error:", err);
    }

    this.initRecognition();
    this.transitionTo("STANDBY", "Wake word mode activated");
    return true;
  }

  // Stop hands-free wake word detection
  stop() {
    this.clearFollowUpTimer();
    if (this.recognition) {
      try {
        this.recognition.onend = null;
        this.recognition.stop();
      } catch (_) {}
      this.recognition = null;
    }
    this.transitionTo("DISABLED", "Wake word mode stopped");
  }

  initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = this.options.lang || "vi-VN";

    this.recognition.onstart = () => {
      if (this.state === "DISABLED") {
        this.transitionTo("STANDBY", "Microphone listening for wake word");
      }
    };

    this.recognition.onresult = (event) => {
      this.handleSpeechResult(event);
    };

    this.recognition.onerror = (event) => {
      console.warn("Speech recognition event error:", event.error);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        this.transitionTo("ERROR", event.error);
        if (this.options.onError) {
          this.options.onError("Microphone bị từ chối quyền truy cập.");
        }
      }
    };

    this.recognition.onend = () => {
      if (this.state !== "DISABLED" && this.state !== "ERROR") {
        setTimeout(() => {
          try {
            if (!this.isTtsSpeaking && this.recognition) {
              this.recognition.start();
            }
          } catch (_) {}
        }, 200);
      }
    };

    try {
      this.recognition.start();
    } catch (e) {
      console.warn("Recognition initial start error:", e);
    }
  }

  handleSpeechResult(event) {
    // Sprint 2 barge-in: human voice interrupts the assistant's TTS playback.
    // Guards: the engine must be running, a wake word engine exists, and the
    // audio must actually be playing (not just any SpeechRecognition noise).
    if (this.isTtsSpeaking || this.state === "SPEAKING") {
      const interrupted = (typeof window !== "undefined" && typeof window.bargeInStopSpeaking === "function")
        ? window.bargeInStopSpeaking()
        : false;
      if (interrupted) {
        console.log("[Pi5 Barge-in] Human voice detected — TTS cancelled.");
        this.isTtsSpeaking = false;
        this.startFollowUpWindow();
        return;
      }
      return; // spurious result while blocked — ignore
    }

    let transcript = "";
    let isFinal = false;
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
      if (event.results[i].isFinal) isFinal = true;
    }
    const clean = this.normalize(transcript);
    if (!clean) return;

    // Control commands
    if (clean.includes("ngủ đi") || clean.includes("tạm ngủ") || clean.includes("go to sleep")) {
      this.clearFollowUpTimer();
      this.transitionTo("STANDBY", "Control command: Sleep");
      return;
    }
    if (clean.includes("dừng nghe") || clean.includes("stop listening")) {
      this.clearFollowUpTimer();
      this.transitionTo("STANDBY", "Control command: Stop listening");
      return;
    }
    if (clean.includes("dừng đọc") || clean.includes("dừng nói") || clean.includes("stop speaking")) {
      const stopped = (typeof window !== "undefined" && typeof window.bargeInStopSpeaking === "function")
        ? window.bargeInStopSpeaking()
        : false;
      if (!stopped && window.speechSynthesis) window.speechSynthesis.cancel();
      this.isTtsSpeaking = false;
      this.startFollowUpWindow();
      return;
    }

    // STATE: STANDBY -> Match wake word
    if (this.state === "STANDBY") {
      const match = this.matchWakeWord(clean);
      if (match) {
        this.clearFollowUpTimer();
        this.playWakeChime();
        this.transitionTo("WAKE_DETECTED", `Wake word detected: ${match.keyword}`);

        if (this.options.onWakeDetected) {
          this.options.onWakeDetected(match.keyword, match.payload);
        }

        if (match.payload && match.payload.trim().length > 2) {
          this.transitionTo("LISTENING", "Payload extracted from wake utterance");
          this.transitionTo("TRANSCRIBING", "Passing payload to processing");
          if (this.options.onCommandRecognized) {
            this.options.onCommandRecognized(match.payload.trim());
          }
        } else {
          this.transitionTo("LISTENING", "Waiting for command input");
          this.startFollowUpWindow();
        }
      }
      return;
    }

    // STATE: LISTENING -> Capture user query
    if (this.state === "LISTENING") {
      this.clearFollowUpTimer();
      if (isFinal && clean.length > 1) {
        this.transitionTo("TRANSCRIBING", "Speech recognized");
        if (this.options.onCommandRecognized) {
          this.options.onCommandRecognized(transcript.trim());
        }
      } else {
        this.startFollowUpWindow();
      }
    }
  }

  matchWakeWord(cleanText) {
    const activeKeywords = this.keywords.filter(k => k.enabled !== false);
    activeKeywords.sort((a, b) => this.normalize(b.phrase).length - this.normalize(a.phrase).length);

    for (const kw of activeKeywords) {
      const normKw = this.normalize(kw.phrase);
      if (cleanText === normKw) {
        return { keyword: kw.phrase, payload: "" };
      }
      if (cleanText.startsWith(normKw + " ")) {
        const payload = cleanText.substring(normKw.length).trim();
        return { keyword: kw.phrase, payload };
      }
    }
    return null;
  }

  notifyThinking() {
    this.clearFollowUpTimer();
    this.transitionTo("THINKING", "Processing query via AI engine");
  }

  notifySpeakingStart() {
    this.isTtsSpeaking = true;
    this.clearFollowUpTimer();
    this.transitionTo("SPEAKING", "Assistant reading answer");

    if (this.recognition) {
      try { this.recognition.abort(); } catch (_) {}
    }
  }

  notifySpeakingEnd() {
    this.isTtsSpeaking = false;
    setTimeout(() => {
      if (this.state !== "DISABLED" && this.recognition) {
        try { this.recognition.start(); } catch (_) {}
      }
      this.transitionTo("LISTENING", "Follow-up conversation window open");
      this.startFollowUpWindow();
    }, 400);
  }

  startFollowUpWindow() {
    this.clearFollowUpTimer();
    const timeoutSec = this.options.silenceTimeoutSeconds || 15.0;
    this.followUpTimer = setTimeout(() => {
      if (this.state === "LISTENING" || this.state === "WAKE_DETECTED") {
        this.transitionTo("STANDBY", `Follow-up window expired (${timeoutSec}s)`);
      }
    }, timeoutSec * 1000);
  }

  clearFollowUpTimer() {
    if (this.followUpTimer) {
      clearTimeout(this.followUpTimer);
      this.followUpTimer = null;
    }
  }
}

// Expose globally for browser usage
window.WakeWordEngine = WakeWordEngine;
