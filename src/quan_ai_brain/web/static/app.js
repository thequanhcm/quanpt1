// QUAN AI BRAIN — Interactive Web Client with Voice STT/TTS
document.addEventListener('DOMContentLoaded', () => {
    // State
    const state = {
        activeTab: 'chat',
        selectedModel: 'zai-org/GLM-5.3-Flash',
        ttsEnabled: true,
        isListening: false,
        recognition: null,
        currentAudio: null,
        activeVoiceId: 'vi-VN-HoaiMyNeural',
        ttsStatus: 'READY',
    };

    // Elements
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const btnSend = document.getElementById('btn-send');
    const btnMic = document.getElementById('btn-mic');
    const voiceBanner = document.getElementById('voice-listening-banner');
    const btnCancelVoice = document.getElementById('btn-cancel-voice');
    const ttsToggle = document.getElementById('tts-toggle');
    const ttsStatusBadge = document.getElementById('tts-status-badge');
    const modelSelector = document.getElementById('model-selector');
    const ollamaIndicator = document.getElementById('ollama-indicator');
    const ollamaStatusText = document.getElementById('ollama-status-text');
    const activeModelName = document.getElementById('active-model-name');

    // Digital Human (Model F — TONY) & Edge Pi 5 Elements
    const avatarCanvas = document.getElementById('tony-avatar-canvas');
    const avatarViewport = document.getElementById('avatar-viewport');
    const avatarStateTag = document.getElementById('avatar-state-tag');
    const avatarStateIcon = document.getElementById('avatar-state-icon');
    const avatarStateName = document.getElementById('avatar-state-name');
    const avatarWaveformCanvas = document.getElementById('avatar-waveform-canvas');
    const btnPi5SpeakTest = document.getElementById('btn-pi5-speak-test');
    const pi5SyncStatus = document.getElementById('pi5-sync-status');
    const pi5SyncLed = document.getElementById('pi5-sync-led');

    let currentAvatarState = 'IDLE';

    // Initialize Digital Human Model F Canvas
    try {
        if (typeof DigitalHumanAvatar !== 'undefined' && avatarCanvas) {
            window.digitalHuman = new DigitalHumanAvatar('tony-avatar-canvas', {
                basePath: '/static/assets/avatar',
                initialState: 'IDLE',
            });
        }
    } catch (e) {
        console.warn('DigitalHumanAvatar init warning on Port 8765:', e);
    }

    const AVATAR_STATE_CONFIG = {
        IDLE: { css: 'state-idle', name: 'IDLE (SẴN SÀNG)', icon: '●' },
        LISTENING: { css: 'state-listening', name: 'LISTENING (LẮNG NGHE)', icon: '🎙️' },
        THINKING: { css: 'state-thinking', name: 'THINKING (SUY NGHĨ)', icon: '🧠' },
        SPEAKING: { css: 'state-speaking', name: 'SPEAKING (ĐANG NÓI)', icon: '🗣️' },
        RESEARCHING: { css: 'state-researching', name: 'RESEARCH (TRA CỨU)', icon: '🔍' },
        LEARNING: { css: 'state-learning', name: 'LEARN (TỰ HỌC)', icon: '⚡' },
        WAITING_FOR_OWNER: { css: 'state-waiting', name: 'WAITING (CHỜ DUYỆT)', icon: '📬' },
        SAFE_MODE: { css: 'state-safemode', name: 'SAFE_MODE (AN TOÀN)', icon: '❄️' },
        BLOCKED: { css: 'state-blocked', name: 'BLOCKED (BỊ CHẶN)', icon: '🛡️' },
    };

    function setAvatarState(stateKey, contextText = null) {
        if (!AVATAR_STATE_CONFIG[stateKey]) stateKey = 'IDLE';
        currentAvatarState = stateKey;
        const conf = AVATAR_STATE_CONFIG[stateKey];

        if (window.digitalHuman) {
            window.digitalHuman.setState(stateKey);
            if (contextText && typeof window.digitalHuman.setContextFromText === 'function') {
                window.digitalHuman.setContextFromText(contextText);
            }
        }

        if (avatarViewport) {
            Object.values(AVATAR_STATE_CONFIG).forEach(c => avatarViewport.classList.remove(c.css));
            avatarViewport.classList.add(conf.css);
        }

        if (avatarStateTag) {
            Object.values(AVATAR_STATE_CONFIG).forEach(c => avatarStateTag.classList.remove(c.css));
            avatarStateTag.classList.add(conf.css);
        }
        if (avatarStateIcon) avatarStateIcon.textContent = conf.icon;
        if (avatarStateName) avatarStateName.textContent = conf.name;

        // Highlight active preview pill
        document.querySelectorAll('.pill-state').forEach(pill => {
            if (pill.getAttribute('data-state') === stateKey) {
                pill.classList.add('active');
            } else {
                pill.classList.remove('active');
            }
        });
    }

    // State preview pills click listeners
    document.querySelectorAll('.pill-state').forEach(pill => {
        pill.addEventListener('click', () => {
            const targetState = pill.getAttribute('data-state');
            if (targetState) setAvatarState(targetState);
        });
    });

    // Dynamic Waveform 60 FPS Canvas Animation
    function initWaveform() {
        if (!avatarWaveformCanvas) return;
        const ctx = avatarWaveformCanvas.getContext('2d');
        const numBars = 26;
        let phase = 0;

        function drawWaveform() {
            ctx.clearRect(0, 0, avatarWaveformCanvas.width, avatarWaveformCanvas.height);
            phase += 0.08;

            const w = avatarWaveformCanvas.width;
            const h = avatarWaveformCanvas.height;
            const barWidth = Math.max(3, (w - (numBars * 3)) / numBars);

            for (let i = 0; i < numBars; i++) {
                const x = i * (barWidth + 3) + 4;
                let barHeight = 4;
                let strokeColor = 'rgba(0, 229, 255, 0.4)';

                if (currentAvatarState === 'SPEAKING') {
                    const factor = Math.sin(phase * 2.2 + i * 0.45) * 0.5 + 0.5;
                    barHeight = 5 + factor * 20;
                    strokeColor = 'rgba(59, 130, 246, 0.9)';
                } else if (currentAvatarState === 'LISTENING') {
                    const factor = Math.sin(phase * 3.0 + i * 0.6) * 0.5 + 0.5;
                    barHeight = 6 + factor * 16;
                    strokeColor = 'rgba(6, 182, 212, 0.9)';
                } else if (currentAvatarState === 'THINKING') {
                    const factor = Math.cos(phase * 1.5 + i * 0.3) * 0.5 + 0.5;
                    barHeight = 4 + factor * 12;
                    strokeColor = 'rgba(168, 85, 247, 0.85)';
                } else if (currentAvatarState === 'RESEARCHING') {
                    const factor = (i === Math.floor((phase * 4) % numBars)) ? 1 : 0.2;
                    barHeight = 4 + factor * 16;
                    strokeColor = 'rgba(16, 185, 129, 0.9)';
                } else if (currentAvatarState === 'LEARNING') {
                    const factor = Math.sin(phase * 4 + i) > 0.3 ? 0.9 : 0.2;
                    barHeight = 5 + factor * 14;
                    strokeColor = 'rgba(245, 158, 11, 0.9)';
                } else if (currentAvatarState === 'SAFE_MODE') {
                    barHeight = 5;
                    strokeColor = 'rgba(56, 189, 248, 0.6)';
                } else {
                    const mid = numBars / 2;
                    const dist = Math.abs(i - mid);
                    const pulse = Math.sin(phase * 0.8) * 0.5 + 0.5;
                    barHeight = 3 + Math.max(0, (5 - dist * 0.4) * pulse);
                    strokeColor = 'rgba(0, 229, 255, 0.5)';
                }

                const y = (h - barHeight) / 2;
                ctx.fillStyle = strokeColor;
                ctx.beginPath();
                ctx.roundRect(x, y, barWidth, barHeight, 2);
                ctx.fill();
            }

            requestAnimationFrame(drawWaveform);
        }
        drawWaveform();
    }
    initWaveform();

    // Raspberry Pi 5 Audio Synchronization Function
    async function syncSpeechToPi5(cleanText, audioBase64, timeline, durationMs) {
        try {
            const res = await fetch('/api/executive/edge/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'speak',
                    text: cleanText,
                    state: 'SPEAKING',
                    audio_base64: audioBase64,
                    timeline: timeline,
                    duration_ms: durationMs || Math.max(1200, cleanText.length * 110),
                }),
            });
            const data = await res.json();
            if (pi5SyncStatus) {
                if (data.success) {
                    pi5SyncStatus.textContent = 'ĐÃ PHÁT TRÊN PI 5';
                    if (pi5SyncLed) pi5SyncLed.className = 'pi5-sync-led online';
                    setTimeout(() => {
                        if (pi5SyncStatus) pi5SyncStatus.textContent = 'ĐỒNG BỘ PHÁT THOẠI';
                    }, 4000);
                } else {
                    pi5SyncStatus.textContent = 'CHỜ KẾT NỐI WI-FI';
                }
            }
        } catch (e) {
            console.warn('Sync speech to Pi 5 warning:', e);
            if (pi5SyncStatus) pi5SyncStatus.textContent = 'CHỜ KẾT NỐI WI-FI';
        }
    }

    // Button to test speech on Raspberry Pi 5
    if (btnPi5SpeakTest) {
        btnPi5SpeakTest.addEventListener('click', () => {
            const greeting = 'Xin chào Anh Quanpt1! Em là TONY, trợ lý điều hành số của Anh. Em đang phát lời thoại trực tiếp trên loa Raspberry Pi 5 và sẵn sàng nhận lệnh!';
            speakText(greeting);
        });
    }

    // 1. Tab Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const tabPanels = document.querySelectorAll('.tab-panel');

    navItems.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-tab');
            navItems.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const targetPanel = document.getElementById(`panel-${tab}`);
            if (targetPanel) targetPanel.classList.add('active');
            state.activeTab = tab;

            if (tab === 'memories') loadMemories();
        });
    });

    // 2. Fetch Initial System Status
    async function updateSystemStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.llm && data.llm.ollama_online) {
                ollamaIndicator.className = 'status-indicator online';
                ollamaStatusText.textContent = 'Trực tuyến (127.0.0.1)';
                if (data.llm.default_model) {
                    activeModelName.textContent = data.llm.default_model;
                }
                if (Array.isArray(data.llm.available_models) && data.llm.available_models.length > 0) {
                    modelSelector.innerHTML = '';
                    data.llm.available_models.forEach(m => {
                        const opt = document.createElement('option');
                        opt.value = m;
                        opt.textContent = m + (m === 'qwen2.5:7b' ? ' (Khuyến nghị)' : '');
                        if (m === 'qwen2.5:7b') opt.selected = true;
                        modelSelector.appendChild(opt);
                    });
                }
            } else {
                ollamaIndicator.className = 'status-indicator offline';
                ollamaStatusText.textContent = 'Chưa kết nối';
            }
        } catch (err) {
            ollamaIndicator.className = 'status-indicator offline';
            ollamaStatusText.textContent = 'Lỗi server API';
        }
    }
    updateSystemStatus();

    // Model Selector Change
    modelSelector.addEventListener('change', (e) => {
        state.selectedModel = e.target.value;
        activeModelName.textContent = e.target.value;
    });

    // TTS Status Helper
    function setTTSStatus(status, text) {
        state.ttsStatus = status;
        if (!ttsStatusBadge) return;
        ttsStatusBadge.className = 'tts-badge ' + status.toLowerCase();
        ttsStatusBadge.textContent = text;
    }

    function stopAudio() {
        if (currentAvatarState === 'SPEAKING') {
            setAvatarState('IDLE');
        }
        if (state.currentAudio) {
            try {
                state.currentAudio.pause();
                state.currentAudio.currentTime = 0;
            } catch (_) {}
            state.currentAudio = null;
        }
        if ('speechSynthesis' in window) {
            try { window.speechSynthesis.cancel(); } catch (_) {}
        }
        if (state.ttsEnabled) {
            setTTSStatus('READY', 'vi-VN (Hoài My)');
        } else {
            setTTSStatus('DISABLED', 'Đã tắt');
        }
    }

    // Load Initial TTS Configuration from Core Backend
    async function initTTSConfig() {
        try {
            const res = await fetch('/api/voice/tts-config');
            const data = await res.json();
            if (data.success && data.config) {
                state.ttsEnabled = Boolean(data.config.tts_enabled);
                if (ttsToggle) ttsToggle.checked = state.ttsEnabled;
                if (data.active_voice) {
                    state.activeVoiceId = data.active_voice.voice_id;
                    const name = data.active_voice.name.includes('HoaiMy') ? 'vi-VN (Hoài My)' : data.active_voice.voice_id;
                    setTTSStatus(state.ttsEnabled ? 'READY' : 'DISABLED', name);
                }
            }
        } catch (e) {
            console.warn('Failed to load tts-config from backend:', e);
        }
    }
    initTTSConfig();

    // TTS Toggle Change
    ttsToggle.addEventListener('change', (e) => {
        state.ttsEnabled = e.target.checked;
        if (!state.ttsEnabled) {
            stopAudio();
            setTTSStatus('DISABLED', 'Đã tắt');
        } else {
            setTTSStatus('READY', 'vi-VN (Hoài My)');
        }
    });

    // 3. Web Speech API (Voice Input - STT)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        state.recognition = new SpeechRecognition();
        state.recognition.lang = 'vi-VN';
        state.recognition.continuous = false;
        state.recognition.interimResults = false;

        state.recognition.onstart = () => {
            console.log('🎤 Started listening');
            stopAudio(); // Cancel speech when user starts talking
            state.isListening = true;
            btnMic.classList.add('recording');
            voiceBanner.style.display = 'flex';
            setAvatarState('LISTENING');
        };

        state.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            console.log('🗣️ Transcript:', transcript);
            chatInput.value = transcript;
            chatInput.focus();
            stopVoiceListening();
        };

        state.recognition.onerror = (event) => {
            console.error('🚫 SpeechRecognition error:', event.error);
            stopVoiceListening();
            alert(`Lỗi nhận diện giọng nói: ${event.error}. Hãy kiểm tra quyền Micro trong trình duyệt.`);
        };

        state.recognition.onend = () => {
            console.log('🔇 Stopped listening');
            stopVoiceListening();
        };
    } else {
        console.warn('⚠️ SpeechRecognition NOT supported. Use Chrome/Edge.');
        btnMic.disabled = true;
        btnMic.title = 'Voice input not supported. Use Chrome or Edge.';
        btnMic.style.opacity = '0.5';
    }

    function startVoiceListening() {
        stopAudio();
        if (!state.recognition) {
            alert('Trình duyệt này chưa hỗ trợ nhận diện giọng nói trực tiếp. Anh hãy dùng Microsoft Edge hoặc Google Chrome, hoặc nhấn tổ hợp phím Windows + H để nói nhé!');
            return;
        }
        try {
            state.recognition.start();
        } catch (err) {
            console.error('Error starting recognition:', err);
        }
    }

    function stopVoiceListening() {
        state.isListening = false;
        btnMic.classList.remove('recording');
        voiceBanner.style.display = 'none';
        if (state.recognition) {
            try { state.recognition.stop(); } catch (_) {}
        }
        if (currentAvatarState === 'LISTENING') {
            setAvatarState('IDLE');
        }
    }

    chatInput.addEventListener('focus', () => {
        if (currentAvatarState === 'IDLE') setAvatarState('LISTENING');
    });
    chatInput.addEventListener('input', () => {
        if (currentAvatarState === 'IDLE' && chatInput.value.trim()) setAvatarState('LISTENING');
    });

    btnMic.addEventListener('click', () => {
        stopAudio();
        if (state.isListening) {
            stopVoiceListening();
        } else {
            startVoiceListening();
        }
    });

    btnCancelVoice.addEventListener('click', () => {
        stopAudio();
        stopVoiceListening();
    });

    // 4. Text-To-Speech (TTS Voice Output)
    async function speakText(text) {
        if (!state.ttsEnabled) return;
        stopAudio();

        if (!text || !text.trim()) return;

        // Clean text preserving Vietnamese diacritics, numbers and technical terms
        let clean = text.replace(/```[\s\S]*?```/g, ' [Khối mã nguồn kỹ thuật] ')
                        .replace(/`([^`]+)`/g, ' $1 ')
                        .replace(/\{[^{}]*\}/g, '')
                        .replace(/https?:\/\/\S+/g, '')
                        .replace(/[A-Za-z]:\\[\w\\\.-]+/g, '')
                        .replace(/[*_#~]/g, '')
                        .replace(/\s+/g, ' ')
                        .trim();
        if (!clean) return;

        setTTSStatus('SPEAKING', 'Đang đọc...');
        setAvatarState('SPEAKING');

        // Step 1: Synthesize with Core Edge-TTS (Natural Vietnamese Female Voice)
        try {
            const res = await fetch('/api/voice/tts-synthesize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: clean,
                    voice_id: state.activeVoiceId || 'vi-VN-HoaiMyNeural',
                }),
            });
            const data = await res.json();
            if (data.success && data.audio_base64) {
                // Synchronize mouth animation visemes to Digital Human Model F
                if (window.digitalHuman && data.timeline) {
                    window.digitalHuman.setTimeline(data.timeline);
                }

                // Broadcast speech and audio payload directly to Raspberry Pi 5
                syncSpeechToPi5(clean, data.audio_base64, data.timeline, data.duration_ms);

                const audio = new Audio('data:audio/mpeg;base64,' + data.audio_base64);
                state.currentAudio = audio;
                audio.onplay = () => {
                    setTTSStatus('SPEAKING', 'Đang nói (Hoài My)...');
                    setAvatarState('SPEAKING');
                };
                audio.onended = () => {
                    state.currentAudio = null;
                    setAvatarState('IDLE');
                    if (state.ttsEnabled) setTTSStatus('READY', 'vi-VN (Hoài My)');
                };
                audio.onerror = (err) => {
                    console.warn('Audio playback error, falling back to browser:', err);
                    state.currentAudio = null;
                    fallbackBrowserTTS(clean);
                };
                await audio.play();
                return;
            } else {
                console.warn('Core TTS synthesize returned non-success:', data.error);
                fallbackBrowserTTS(clean);
            }
        } catch (exc) {
            console.warn('Core TTS network error:', exc);
            fallbackBrowserTTS(clean);
        }
    }

    function fallbackBrowserTTS(cleanText) {
        if (!('speechSynthesis' in window)) {
            setTTSStatus('UNAVAILABLE', 'TTS không khả dụng');
            setAvatarState('IDLE');
            return;
        }

        window.speechSynthesis.cancel();
        const voices = window.speechSynthesis.getVoices();

        // STRICT POLICY: Must find actual Vietnamese voice; reject English or OS default!
        const viVoice = voices.find(v => {
            const lang = (v.lang || '').toLowerCase();
            const name = (v.name || '').toLowerCase();
            return lang.startsWith('vi') || lang === 'vi-vn' || name.includes('vietnam') || name.includes('hoaimy');
        });

        if (!viVoice) {
            // Non-negotiable constraint: Never speak Vietnamese with an English voice!
            console.warn('TTS_UNAVAILABLE: Không tìm thấy giọng đọc tiếng Việt nào trong trình duyệt. Từ chối phát giọng tiếng Anh.');
            setTTSStatus('UNAVAILABLE', 'Thiếu voice tiếng Việt');
            setAvatarState('IDLE');
            return;
        }

        try {
            const utter = new SpeechSynthesisUtterance(cleanText);
            utter.voice = viVoice;
            utter.lang = viVoice.lang || 'vi-VN';
            utter.rate = 1.0;
            setTTSStatus('SPEAKING', `Đang nói (${viVoice.name})...`);
            setAvatarState('SPEAKING');
            utter.onend = () => {
                setAvatarState('IDLE');
                if (state.ttsEnabled) setTTSStatus('READY', 'vi-VN (Trình duyệt)');
            };
            utter.onerror = (e) => {
                console.warn('Browser speech error:', e);
                setAvatarState('IDLE');
                setTTSStatus('ERROR', 'Lỗi phát giọng');
            };
            window.speechSynthesis.speak(utter);
        } catch (e) {
            console.warn('Browser SpeechSynthesis exception:', e);
            setAvatarState('IDLE');
            setTTSStatus('ERROR', 'Lỗi phát giọng');
        }
    }

    // 5. Chat Messaging Flow
    function appendMessage(sender, text, isUser = false, meta = null) {
        const row = document.createElement('div');
        row.className = `message-row ${isUser ? 'user' : 'assistant'}`;

        const timeStr = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });

        let metaHtml = '';
        if (meta) {
            metaHtml = `<div class="msg-meta">
                ${meta.model ? `<span class="meta-tag">Model: ${meta.model}</span>` : ''}
                ${meta.elapsed_ms ? `<span class="meta-tag">Thời gian: ${meta.elapsed_ms}ms</span>` : ''}
                ${meta.used_memories && meta.used_memories.length > 0 ? `<span class="meta-tag">Trí nhớ: ${meta.used_memories.length} bản ghi</span>` : ''}
            </div>`;
        }

        // Basic formatting for line breaks and bold
        let formattedBody = text.replace(/\n/g, '<br>')
                                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                .replace(/`([^`]+)`/g, '<code>$1</code>');

        row.innerHTML = `
            <div class="msg-avatar">
                ${isUser ? 'Q' : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path></svg>'}
            </div>
            <div class="msg-bubble">
                <div class="msg-header">
                    <span class="msg-sender">${sender}</span>
                    <span class="msg-time">${timeStr}</span>
                </div>
                <div class="msg-body">${formattedBody}</div>
                ${metaHtml}
            </div>
        `;

        chatMessages.appendChild(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return row;
    }

    function appendTypingIndicator() {
        const row = document.createElement('div');
        row.className = 'message-row assistant typing-indicator-row';
        row.id = 'typing-indicator';
        row.innerHTML = `
            <div class="msg-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path></svg>
            </div>
            <div class="msg-bubble">
                <div class="msg-body" style="color: var(--text-muted); font-style: italic;">
                    QUAN AI BRAIN đang truy xuất trí nhớ và suy luận...
                </div>
            </div>
        `;
        chatMessages.appendChild(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    async function handleSendMessage() {
        const query = chatInput.value.trim();
        if (!query) return;

        stopAudio(); // Cancel any prior audio playback immediately
        chatInput.value = '';
        btnSend.disabled = true;

        appendMessage('Quanpt1', query, true);
        appendTypingIndicator();
        setAvatarState('THINKING');

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query,
                    model: state.selectedModel,
                    fallback: false,
                    timeout: 120,
                }),
            });

            removeTypingIndicator();
            const data = await res.json();

            if (data.success && data.answer) {
                appendMessage('QUAN AI BRAIN', data.answer, false, {
                    model: data.model,
                    elapsed_ms: data.elapsed_ms,
                    used_memories: data.used_memories,
                });
                // Analyze Vietnamese semantic intent for dynamic facial expressions
                if (window.digitalHuman && typeof window.digitalHuman.setContextFromText === 'function') {
                    window.digitalHuman.setContextFromText(data.answer);
                }
                speakText(data.answer);
            } else {
                setAvatarState('IDLE');
                appendMessage('QUAN AI BRAIN', `⚠️ Lỗi xử lý: ${data.error_message || data.error || 'Không nhận được phản hồi'}`, false);
            }
        } catch (err) {
            removeTypingIndicator();
            setAvatarState('IDLE');
            appendMessage('Hệ thống', `⚠️ Không thể kết nối tới máy chủ QUAN AI BRAIN: ${err.message}`, false);
        } finally {
            btnSend.disabled = false;
            chatInput.focus();
        }
    }

    btnSend.addEventListener('click', handleSendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    // 6. Memories Tab Handler
    async function loadMemories() {
        const listEl = document.getElementById('memories-list');
        listEl.innerHTML = '<div style="color: var(--text-muted);">Đang tải danh sách trí nhớ...</div>';

        try {
            const res = await fetch('/api/memories');
            const data = await res.json();
            if (data.success && Array.isArray(data.memories)) {
                if (data.memories.length === 0) {
                    listEl.innerHTML = '<div style="color: var(--text-muted);">Chưa có bản ghi trí nhớ nào. Hãy thêm mẩu thông tin đầu tiên!</div>';
                    return;
                }
                listEl.innerHTML = '';
                data.memories.forEach(m => {
                    const card = document.createElement('div');
                    card.className = 'memory-card';
                    card.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="mem-badge">${m.kind || 'Episode'}</span>
                            <span class="mem-date">${m.created_at ? m.created_at.substring(0, 19).replace('T', ' ') : ''}</span>
                        </div>
                        <p class="mem-text">${m.summary}</p>
                        <div style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">Source: ${m.source_ref || 'unknown'}</div>
                    `;
                    listEl.appendChild(card);
                });
            }
        } catch (err) {
            listEl.innerHTML = `<div style="color: var(--accent-rose);">Lỗi tải trí nhớ: ${err.message}</div>`;
        }
    }

    // Modal Add Memory
    const modalAddMemory = document.getElementById('modal-add-memory');
    const btnOpenAddMemory = document.getElementById('btn-open-add-memory');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const btnCancelMemory = document.getElementById('btn-cancel-memory');
    const btnSaveMemory = document.getElementById('btn-save-memory');

    btnOpenAddMemory.addEventListener('click', () => { modalAddMemory.style.display = 'flex'; });
    const closeModal = () => { modalAddMemory.style.display = 'none'; };
    btnCloseModal.addEventListener('click', closeModal);
    btnCancelMemory.addEventListener('click', closeModal);

    btnSaveMemory.addEventListener('click', async () => {
        const summary = document.getElementById('new-memory-summary').value.trim();
        const kind = document.getElementById('new-memory-kind').value;
        if (!summary) return alert('Vui lòng nhập tóm tắt thông tin cần ghi nhớ!');

        try {
            const res = await fetch('/api/memories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ summary, kind }),
            });
            const data = await res.json();
            if (data.success) {
                closeModal();
                document.getElementById('new-memory-summary').value = '';
                loadMemories();
            } else {
                alert(`Lỗi: ${data.error}`);
            }
        } catch (err) {
            alert(`Lỗi lưu: ${err.message}`);
        }
    });

    // 7. Planning Tab Handler
    const btnGeneratePlan = document.getElementById('btn-generate-plan');
    const planGoalInput = document.getElementById('plan-goal-input');
    const planResultContainer = document.getElementById('plan-result-container');

    btnGeneratePlan.addEventListener('click', async () => {
        const goal = planGoalInput.value.trim();
        if (!goal) return alert('Vui lòng nhập mục tiêu cần lập kế hoạch!');

        btnGeneratePlan.disabled = true;
        btnGeneratePlan.textContent = 'Đang phân tích & lập kế hoạch...';
        planResultContainer.style.display = 'block';
        planResultContainer.innerHTML = '<div style="color: var(--accent-cyan); font-style: italic;">Đang phân rã mục tiêu và đối chiếu Hiến pháp R0-R5 với mô hình Ollama...</div>';

        try {
            const res = await fetch('/api/plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    goal: goal,
                    model: state.selectedModel,
                    fallback: false,
                }),
            });
            const data = await res.json();
            if (data.success && data.plan) {
                const plan = data.plan;
                let stepsHtml = '';
                if (Array.isArray(plan.steps)) {
                    stepsHtml = `
                        <table style="width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 0.9rem;">
                            <thead>
                                <tr style="border-bottom: 1px solid var(--border-subtle); text-align: left; color: var(--text-secondary);">
                                    <th style="padding: 8px;">Bước</th>
                                    <th style="padding: 8px;">Hành động</th>
                                    <th style="padding: 8px;">Mức rủi ro</th>
                                    <th style="padding: 8px;">Kết quả kỳ vọng</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${plan.steps.map(s => `
                                    <tr style="border-bottom: 1px solid var(--border-subtle);">
                                        <td style="padding: 8px; font-family: var(--font-mono);">${s.step_id}</td>
                                        <td style="padding: 8px; font-weight: 600;">${s.name}</td>
                                        <td style="padding: 8px;"><span class="risk-badge risk-r${s.risk_level}">R${s.risk_level}</span></td>
                                        <td style="padding: 8px; color: var(--text-secondary);">${s.expected_output || ''}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `;
                }

                planResultContainer.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h4>Bản Kế Hoạch: ${plan.plan_id || 'plan-auto'}</h4>
                        <span class="badge ${plan.status === 'blocked' ? 'badge-danger' : 'badge-primary'}">${plan.status}</span>
                    </div>
                    <p style="color: var(--text-secondary); margin-bottom: 8px;"><strong>Tóm tắt:</strong> ${plan.summary}</p>
                    ${stepsHtml}
                    <div style="margin-top: 16px; padding: 12px; background: rgba(0,0,0,0.3); border-radius: var(--radius-sm); font-size: 0.8rem; color: var(--text-muted);">
                        🛡️ <strong>Lưu ý Quản trị:</strong> Kế hoạch này được lập phục vụ Chủ nhân xem xét. Không có hành động nào được tự ý thực thi.
                    </div>
                `;
            } else {
                planResultContainer.innerHTML = `<div style="color: var(--accent-rose);">Lỗi lập kế hoạch: ${data.error || 'Thao tác không thành công'}</div>`;
            }
        } catch (err) {
            planResultContainer.innerHTML = `<div style="color: var(--accent-rose);">Lỗi kết nối: ${err.message}</div>`;
        } finally {
            btnGeneratePlan.disabled = false;
            btnGeneratePlan.textContent = 'Lập Kế Hoạch';
        }
    });

    // 8. Self-Learning Tab Handler
    const btnRunLearning = document.getElementById('btn-run-learning-cycle');
    const learningResultContainer = document.getElementById('learning-result-container');

    btnRunLearning.addEventListener('click', async () => {
        btnRunLearning.disabled = true;
        btnRunLearning.textContent = 'Đang tự nghiên cứu và chạy thử nghiệm...';
        learningResultContainer.style.display = 'block';
        learningResultContainer.innerHTML = '<div style="color: var(--accent-cyan); font-style: italic;">Đang quan sát lỗ hổng -> Trích xuất tài liệu -> Tạo hồ sơ cách ly -> Sinh bản vá đề xuất...</div>';

        try {
            const res = await fetch('/api/learning', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scope: 'general' }),
            });
            const data = await res.json();
            if (data.success && data.proposal) {
                const prop = data.proposal;
                learningResultContainer.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                        <h4>Hồ Sơ Đề Xuất Nâng Cấp: ${prop.proposal_id}</h4>
                        <span class="badge badge-primary">Confidence: ${(prop.confidence_score * 100).toFixed(0)}%</span>
                    </div>
                    <p style="margin-bottom: 8px;"><strong>Vấn đề:</strong> ${prop.problem_statement}</p>
                    <p style="margin-bottom: 8px;"><strong>Giải pháp:</strong> ${prop.proposed_solution}</p>
                    <div style="margin: 14px 0; background: #000; padding: 14px; border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 0.8rem; overflow-x: auto;">
                        <pre style="color: #38bdf8;">${prop.unified_diff}</pre>
                    </div>
                    <div style="padding: 10px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: var(--radius-sm); font-size: 0.85rem; color: #6ee7b7;">
                        ✅ Tri thức mới đã được cách ly an toàn (QUARANTINED) tại SQLite. Quyết định áp dụng hoàn toàn thuộc về Chủ nhân Quanpt1.
                    </div>
                `;
            } else {
                learningResultContainer.innerHTML = `<div style="color: var(--accent-rose);">Lỗi chu kỳ tự học: ${data.error || 'Không thành công'}</div>`;
            }
        } catch (err) {
            learningResultContainer.innerHTML = `<div style="color: var(--accent-rose);">Lỗi kết nối: ${err.message}</div>`;
        } finally {
            btnRunLearning.disabled = false;
            btnRunLearning.textContent = '⚡ Chạy Một Chu Kỳ Tự Học Mẫu (Supervised Dry-Run)';
        }
    });
});
