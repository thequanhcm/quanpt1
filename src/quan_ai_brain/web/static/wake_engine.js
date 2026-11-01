/**
 * QUAN AI BRAIN — Wake Word & Hands-Free Voice Engine V1
 *
 * Implements:
 * - 9-State Machine (DISABLED, STANDBY, WAKE_DETECTED, LISTENING, TRANSCRIBING, THINKING, SPEAKING, INTERRUPTED, ERROR)
 * - Continuous keyword spotting for Vietnamese & English wake words
 * - Zero-loss prompt extraction (wake phrase + payload)
 * - Acoustic Echo Cancellation (AEC) during TTS playback to prevent self-triggering
 * - Web Audio API synthesized executive wake chime
 * - Follow-up conversation window (20s) with auto-return to STANDBY
 * - Voice control commands ("ngủ đi", "dừng đọc", "dừng nghe", "tắt trợ lý")
 */
class WakeWordEngine {
  constructor(options = {}) {
    this.state = "DISABLED";
    this.options = Object.assign({
      silenceTimeoutSeconds: 20.0,
      chimeEnabled: true,
      lang: "vi-VN",
      onStateChange: () => {},
      onWakeDetected: () => {},
      onCommandRecognized: () => {},
      onError: () => {},
    }, options);

    this.keywords = [];
    this.recognition = null;
    this.audioCtx = null;
    this.followUpTimer = null;
    this.isTtsSpeaking = false;
    this.activeUtterancePayload = "";

    // Load backend configuration
    this.syncConfigFromBackend();
  }

  async syncConfigFromBackend() {
    try {
      const res = await fetch("/api/voice/wake-config");
      if (res.ok) {
        const data = await res.json();
        const cfg = data.config || data;
        this.keywords = cfg.keywords || cfg.wake_words || [];
        if (cfg.silence_timeout_seconds || cfg.silence_timeout_sec) {
          this.options.silenceTimeoutSeconds = cfg.silence_timeout_seconds || cfg.silence_timeout_sec;
        }
        if (typeof cfg.chime_enabled === "boolean") {
          this.options.chimeEnabled = cfg.chime_enabled;
        }
      }
    } catch (err) {
      console.warn("Could not sync wake config from backend, using defaults:", err);
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
    fetch("/api/voice/telemetry", {
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
      gain.gain.linearRampToValueAtTime(0.18, now + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      osc.start(now);
      osc.stop(now + 0.23);
    } catch (err) {
      console.warn("Chime generation error:", err);
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
      this.options.onError("Trình duyệt không hỗ trợ Web Speech API. Vui lòng sử dụng Google Chrome hoặc Edge.");
      return false;
    }

    try {
      // Prompt mic permission
      await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      this.transitionTo("ERROR", "Microphone permission denied");
      this.options.onError("Quyền truy cập Microphone bị từ chối.");
      return false;
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
      console.warn("Recognition error:", event.error);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        this.transitionTo("ERROR", event.error);
        this.options.onError("Microphone bị từ chối quyền truy cập.");
      }
    };

    this.recognition.onend = () => {
      // Auto-restart if we are in active modes and not disabled or speaking
      if (this.state !== "DISABLED" && this.state !== "ERROR") {
        try {
          if (!this.isTtsSpeaking) {
            this.recognition.start();
          }
        } catch (_) {}
      }
    };

    try {
      this.recognition.start();
    } catch (e) {
      console.warn("Recognition start error:", e);
    }
  }

  handleSpeechResult(event) {
    // Acoustic Echo Cancellation: Ignore recognition if Brain is speaking via TTS
    if (this.isTtsSpeaking || this.state === "SPEAKING") {
      return;
    }

    let transcript = "";
    let isFinal = false;
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
      if (event.results[i].isFinal) isFinal = true;
    }
    const clean = this.normalize(transcript);
    if (!clean) return;

    // Check voice control commands first
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
      window.speechSynthesis && window.speechSynthesis.cancel();
      this.isTtsSpeaking = false;
      this.startFollowUpWindow();
      return;
    }
    if (clean.includes("tắt trợ lý") || clean.includes("tắt đánh thức") || clean.includes("disable wake word")) {
      this.stop();
      return;
    }

    // STATE: STANDBY -> Check for wake words
    if (this.state === "STANDBY") {
      const match = this.matchWakeWord(clean);
      if (match) {
        this.clearFollowUpTimer();
        this.playWakeChime();
        this.transitionTo("WAKE_DETECTED", `Wake word detected: ${match.keyword}`);

        if (this.options.onWakeDetected) {
          this.options.onWakeDetected(match.keyword, match.payload);
        }

        // If user already said their query in the same breath ("Hi Tony hãy lập kế hoạch...")
        if (match.payload && match.payload.trim().length > 3) {
          this.transitionTo("LISTENING", "Payload extracted from wake utterance");
          this.transitionTo("TRANSCRIBING", "Passing payload to processing");
          if (this.options.onCommandRecognized) {
            this.options.onCommandRecognized(match.payload.trim());
          }
        } else {
          // Transition to LISTENING for next utterance
          this.transitionTo("LISTENING", "Waiting for command input");
          this.startFollowUpWindow();
        }
      }
      return;
    }

    // STATE: LISTENING -> Capture user query
    if (this.state === "LISTENING") {
      this.clearFollowUpTimer();
      if (isFinal && clean.length > 2) {
        this.transitionTo("TRANSCRIBING", "Speech recognized");
        if (this.options.onCommandRecognized) {
          this.options.onCommandRecognized(transcript.trim());
        }
      } else {
        // Reset follow-up window while speaking
        this.startFollowUpWindow();
      }
    }
  }

  matchWakeWord(cleanText) {
    const activeKeywords = this.keywords.filter(k => k.enabled !== false);
    // Sort descending by phrase length
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

  // Notified by main app when LLM starts thinking
  notifyThinking() {
    this.clearFollowUpTimer();
    this.transitionTo("THINKING", "Processing query via AI engine");
  }

  // Notified by main app when TTS begins speaking
  notifySpeakingStart() {
    this.isTtsSpeaking = true;
    this.clearFollowUpTimer();
    this.transitionTo("SPEAKING", "Brain reading answer");

    // Pause recognition during TTS to prevent acoustic loop
    if (this.recognition) {
      try { this.recognition.abort(); } catch (_) {}
    }
  }

  // Notified by main app when TTS finishes speaking
  notifySpeakingEnd() {
    this.isTtsSpeaking = false;
    // Resume recognition after 400ms settling time
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
    const timeoutSec = this.options.silenceTimeoutSeconds || 20.0;
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
