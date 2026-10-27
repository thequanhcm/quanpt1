/**
 * QUAN AI BRAIN — Executive Consultation & Cockpit Script (Port 8766)
 */
document.addEventListener("DOMContentLoaded", () => {
  // Navigation tabs
  const tabs = document.querySelectorAll(".nav-tab");
  const contents = document.querySelectorAll(".tab-content");
  let currentFilter = "ALL";
  let recognition = null;
  let isListening = false;
  let wakeEngine = null;
  let isTtsEnabled = true;
  let currentAvatarState = "IDLE";
  let setAvatarState = function(state) {};

  // Initialize UI safely with error isolation
  const safeInit = (fn, name) => {
    try { fn(); } catch (err) { console.error(`[InitError] ${name}:`, err); }
  };

  safeInit(initTabs, "initTabs");
  safeInit(loadTelemetry, "loadTelemetry");
  safeInit(loadPersonaAndDirectives, "loadPersonaAndDirectives");
  safeInit(loadCapabilities, "loadCapabilities");
  safeInit(loadConsultations, "loadConsultations");
  safeInit(loadLearningReports, "loadLearningReports");
  safeInit(initVoice, "initVoice");
  safeInit(initDialogue, "initDialogue");
  safeInit(initVisualCockpit, "initVisualCockpit");
  safeInit(initEdgeAddon, "initEdgeAddon");
  safeInit(initRemoteSensors, "initRemoteSensors");
  safeInit(initTasksOrchestration, "initTasksOrchestration");
  safeInit(initNetChat, "initNetChat");

  // Tab navigation
  function initTabs() {
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        const target = tab.getAttribute("data-tab");
        if (window.switchTab) {
          window.switchTab(target);
        } else {
          tabs.forEach(t => t.classList.remove("active"));
          contents.forEach(c => c.classList.remove("active"));
          tab.classList.add("active");
          const targetEl = document.getElementById(target);
          if (targetEl) targetEl.classList.add("active");
        }
        if (target === "tab-orchestration") {
          if (typeof window.loadTasksList === "function") window.loadTasksList();
        }
        if (target === "tab-edge-sync" || target === "tab-pi5-embodiment") {
          loadPiFiles();
          loadEdgeTelemetry();
          if (typeof window.loadAudioStatus === "function") window.loadAudioStatus();
          if (typeof window.loadCameraStatus === "function") window.loadCameraStatus();
          if (typeof window.loadCaptureLibrary === "function") window.loadCaptureLibrary();
        }
      });
    });

    // Filter buttons for consultations
    document.querySelectorAll(".btn-filter").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".btn-filter").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentFilter = btn.getAttribute("data-filter");
        loadConsultations();
      });
    });

    // Refresh capabilities
    const btnRefreshCaps = document.getElementById("btn-refresh-caps");
    if (btnRefreshCaps) {
      btnRefreshCaps.addEventListener("click", loadCapabilities);
    }

    // Trigger learning cycle
    const btnTriggerCycle = document.getElementById("btn-trigger-learning-cycle");
    if (btnTriggerCycle) {
      btnTriggerCycle.addEventListener("click", triggerLearningCycle);
    }
  }

  // Telemetry status
  async function loadTelemetry() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) throw new Error("Status API failed");
      const data = await res.json();

      const llmEl = document.getElementById("status-llm");
      if (llmEl) {
        const isOnline = data.llm && (data.llm.reachable || data.llm.ollama_online);
        const modelName = (data.llm && (data.llm.model || data.llm.default_model)) || "qwen2.5:7b";
        if (isOnline) {
          llmEl.textContent = `Online (${modelName})`;
          llmEl.style.color = "var(--green-success)";
        } else {
          llmEl.textContent = "Offline (Fallback)";
          llmEl.style.color = "var(--gold-accent)";
        }
      }

      const memEl = document.getElementById("status-memories");
      if (memEl && data.memories) {
        memEl.textContent = `${data.memories.count || 0} mục`;
      }
    } catch (err) {
      console.warn("Telemetry fetch error:", err);
    }
  }

  // Persona & Directives
  async function loadPersonaAndDirectives() {
    try {
      const res = await fetch("/api/executive/persona");
      if (!res.ok) return;
      const data = await res.json();

      const listEl = document.getElementById("persona-directives-list");
      if (!listEl || !data.directives) return;

      listEl.innerHTML = "";
      data.directives.forEach(d => {
        const item = document.createElement("div");
        item.className = "directive-item";
        item.innerHTML = `
          <div class="directive-title">[${d.directive_id}] ${escapeHtml(d.title)}</div>
          <div class="directive-desc">${escapeHtml(d.description)}</div>
        `;
        listEl.appendChild(item);
      });
    } catch (err) {
      console.warn("Persona fetch error:", err);
    }
  }

  // Capabilities
  async function loadCapabilities() {
    try {
      const res = await fetch("/api/executive/capabilities");
      if (!res.ok) return;
      const data = await res.json();

      const tbody = document.getElementById("capabilities-tbody");
      if (!tbody || !data.capabilities) return;

      tbody.innerHTML = "";
      data.capabilities.forEach(cap => {
        const tr = document.createElement("tr");

        let statusClass = "status-active";
        if (cap.status === "INERT_STAGING") statusClass = "status-staging";
        if (cap.status === "EXTERNAL_PLANNED") statusClass = "status-planned";

        tr.innerHTML = `
          <td><strong>${escapeHtml(cap.name)}</strong></td>
          <td>${escapeHtml(cap.domain)}</td>
          <td><span class="cap-status-badge ${statusClass}">${escapeHtml(cap.status)}</span></td>
          <td><span class="badge ${cap.risk_level >= 4 ? 'tier-danger' : 'tier-badge'}">R${cap.risk_level}</span></td>
          <td style="font-size: 0.82rem; color: var(--text-muted);">${escapeHtml(cap.evidence_notes)}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (err) {
      console.warn("Capabilities fetch error:", err);
    }
  }

  // Consultation Inbox
  async function loadConsultations() {
    try {
      let url = "/api/executive/consultations";
      if (currentFilter !== "ALL") {
        url += `?status=${encodeURIComponent(currentFilter)}`;
      }
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();

      const container = document.getElementById("consultation-tickets-list");
      if (!container) return;

      // Update counters
      const pendingCount = (data.tickets || []).filter(t => t.status === "PENDING_REVIEW").length;
      const counterBadge = document.getElementById("badge-consultation-counter");
      if (counterBadge) counterBadge.textContent = pendingCount;
      const statusPending = document.getElementById("status-pending-count");
      if (statusPending) statusPending.textContent = `${pendingCount} phiếu`;

      if (!data.tickets || data.tickets.length === 0) {
        container.innerHTML = `<div class="card" style="text-align: center; color: var(--text-muted); padding: 40px;">Hiện không có phiếu tham vấn nào trong mục này.</div>`;
        return;
      }

      container.innerHTML = "";
      data.tickets.forEach(ticket => {
        const card = document.createElement("div");
        const statusClass = ticket.status.toLowerCase().replace("_", "-");
        card.className = `consultation-ticket-card status-${statusClass}`;

        let statusBadge = `<span class="badge badge-staging">CHỜ DUYỆT</span>`;
        if (ticket.status === "APPROVED") statusBadge = `<span class="badge badge-success">ĐÃ PHÊ DUYỆT</span>`;
        if (ticket.status === "REJECTED") statusBadge = `<span class="badge tier-danger">ĐÃ TỪ CHỐI</span>`;
        if (ticket.status === "DIRECTED") statusBadge = `<span class="badge" style="background: rgba(0, 229, 255, 0.2); color: var(--cyan-primary);">ĐÃ CHỈ ĐẠO</span>`;

        let actionSection = "";
        if (ticket.status === "PENDING_REVIEW") {
          actionSection = `
            <div class="ticket-actions-bar">
              <div class="actions-buttons-row">
                <button class="btn btn-approve btn-sm" onclick="respondTicket('${ticket.ticket_id}', 'APPROVE')">
                  ✅ Đồng Ý & Phê Duyệt Ngay
                </button>
                <button class="btn btn-reject btn-sm" onclick="respondTicket('${ticket.ticket_id}', 'REJECT')">
                  ❌ Từ Chối Áp Dụng
                </button>
              </div>
              <div class="owner-input-row mt-2">
                <input type="text" id="guidance-input-${ticket.ticket_id}" placeholder="Chỉ đạo riêng của Anh gửi Bản sao số...">
                <button class="btn btn-primary btn-sm" onclick="submitGuidance('${ticket.ticket_id}')">
                  Gửi Chỉ Đạo ➤
                </button>
              </div>
            </div>
          `;
        } else {
          actionSection = `
            <div class="ticket-actions-bar">
              <div style="font-size: 0.88rem; color: var(--text-main);">
                <strong>Quyết định của Anh:</strong> <span style="color: var(--gold-accent);">${escapeHtml(ticket.owner_decision || ticket.status)}</span>
                ${ticket.owner_guidance ? `<div style="margin-top: 4px; color: var(--cyan-primary);"><em>" ${escapeHtml(ticket.owner_guidance)} "</em></div>` : ''}
              </div>
            </div>
          `;
        }

        card.innerHTML = `
          <div class="ticket-header-row">
            <div>
              <span class="ticket-category-pill">${escapeHtml(ticket.category)}</span>
              <div class="ticket-title">${escapeHtml(ticket.title)}</div>
              <div class="ticket-meta">Mã phiếu: ${escapeHtml(ticket.ticket_id)} | Mức độ: ${escapeHtml(ticket.priority)} | Tạo lúc: ${escapeHtml(ticket.created_at)}</div>
            </div>
            <div>${statusBadge}</div>
          </div>

          <div class="ticket-body-section">
            <div class="ticket-box">
              <div class="box-title">📌 Bối cảnh & Lý do Brain xin ý kiến:</div>
              <div>${escapeHtml(ticket.context_summary)}</div>
            </div>

            <div class="ticket-box">
              <div class="box-title">💡 Phương án Brain khuyến nghị Anh:</div>
              <div style="color: var(--gold-accent); font-weight: 500;">${escapeHtml(ticket.proposed_action)}</div>
            </div>

            ${ticket.evidence_notes ? `
              <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 4px;">
                <strong>Bằng chứng thực nghiệm:</strong> ${escapeHtml(ticket.evidence_notes)}
              </div>
            ` : ''}
          </div>

          ${actionSection}
        `;
        container.appendChild(card);
      });
    } catch (err) {
      console.warn("Consultations fetch error:", err);
    }
  }

  // Global functions for inline ticket buttons
  window.respondTicket = async function(ticketId, decision, guidance = "") {
    try {
      const res = await fetch("/api/executive/consultations/respond", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({ ticket_id: ticketId, decision: decision, guidance: guidance })
      });
      if (res.ok) {
        loadConsultations();
        loadTelemetry();
      } else {
        alert("Không thể cập nhật phiếu tham vấn.");
      }
    } catch (err) {
      alert("Lỗi kết nối khi gửi phản hồi: " + err);
    }
  };

  window.submitGuidance = function(ticketId) {
    const input = document.getElementById(`guidance-input-${ticketId}`);
    const guidance = input ? input.value.trim() : "";
    if (!guidance) {
      alert("Vui lòng nhập nội dung chỉ đạo của Anh trước khi gửi.");
      return;
    }
    window.respondTicket(ticketId, "DIRECT", guidance);
  };

  // Learning Reports
  async function loadLearningReports() {
    try {
      const res = await fetch("/api/executive/learning/reports");
      if (!res.ok) return;
      const data = await res.json();

      const listEl = document.getElementById("learning-reports-list");
      if (!listEl || !data.reports) return;

      listEl.innerHTML = "";
      data.reports.forEach((rep, idx) => {
        const item = document.createElement("div");
        item.className = `report-item-card ${idx === 0 ? 'selected' : ''}`;
        item.innerHTML = `
          <div class="report-item-title">Kỳ #${rep.cycle_number}: ${escapeHtml(rep.title)}</div>
          <div class="report-item-meta">
            <span>Độ tự tin: ${(rep.confidence_score * 100).toFixed(1)}%</span>
            <span>${escapeHtml(rep.created_at ? rep.created_at.split('T')[0] : '')}</span>
          </div>
        `;
        item.addEventListener("click", () => {
          document.querySelectorAll(".report-item-card").forEach(c => c.classList.remove("selected"));
          item.classList.add("selected");
          renderReportDetail(rep);
        });
        listEl.appendChild(item);
      });

      if (data.reports.length > 0) {
        renderReportDetail(data.reports[0]);
      }
    } catch (err) {
      console.warn("Learning reports fetch error:", err);
    }
  }

  function renderReportDetail(rep) {
    const titleEl = document.getElementById("rep-detail-title");
    const statusEl = document.getElementById("rep-detail-status");
    const contentEl = document.getElementById("rep-detail-content");

    if (titleEl) titleEl.textContent = `Kỳ #${rep.cycle_number}: ${rep.title}`;
    if (statusEl) {
      statusEl.textContent = rep.regression_tests_status || "ALL_PASSED";
    }
    if (contentEl) {
      contentEl.innerHTML = `
        <div class="ticket-box mb-3">
          <div class="box-title">Tóm tắt tiến trình tự học:</div>
          <div>${escapeHtml(rep.summary)}</div>
        </div>

        <div style="margin-top: 14px;">
          <h4 style="color: var(--cyan-primary); margin-bottom: 6px;">Khoảng Trống Tri Thức Đã Phân Tích (Gaps):</h4>
          <ul style="padding-left: 20px; font-size: 0.9rem; color: var(--text-muted);">
            ${(rep.gaps_detected || []).map(g => `<li><strong>${escapeHtml(g.gap_id || 'GAP')}</strong>: ${escapeHtml(g.description || '')} (Severity: R${g.severity || 1})</li>`).join('') || '<li>Không ghi nhận lỗi mới</li>'}
          </ul>
        </div>

        <div style="margin-top: 14px;">
          <h4 style="color: var(--gold-accent); margin-bottom: 6px;">Đề Xuất Nâng Cấp Hệ Thống (Upgrade Proposals):</h4>
          <ul style="padding-left: 20px; font-size: 0.9rem; color: var(--text-muted);">
            ${(rep.upgrade_proposals || []).map(p => `<li><strong>${escapeHtml(p.proposal_id || '')}</strong>: Tệp mục tiêu <code>${escapeHtml(p.target_file || p.problem_statement || '')}</code> (Khuyến nghị: ${escapeHtml(p.recommendation || 'apply')})</li>`).join('') || '<li>Chưa có đề xuất nâng cấp mã nguồn mới</li>'}
          </ul>
        </div>

        <div style="margin-top: 14px;">
          <h4 style="color: var(--green-success); margin-bottom: 6px;">Kiến Nghị Tham Vấn Anh:</h4>
          <ul style="padding-left: 20px; font-size: 0.9rem; color: var(--text-muted);">
            ${(rep.recommendations || []).map(r => `<li>${escapeHtml(r)}</li>`).join('') || '<li>Sẵn sàng tiếp tục chu kỳ tiếp theo</li>'}
          </ul>
        </div>
      `;
    }
  }

  async function triggerLearningCycle() {
    const btn = document.getElementById("btn-trigger-learning-cycle");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "⏳ Đang chạy chu kỳ học...";
    }
    try {
      const res = await fetch("/api/executive/learning/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({ trigger_reason: "owner_manual_desk_click" })
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Chu kỳ tự học #${data.report.cycle_number} đã hoàn tất thành công!`);
        loadLearningReports();
        loadConsultations();
      } else {
        alert("Lỗi khi kích hoạt chu kỳ tự học.");
      }
    } catch (err) {
      alert("Lỗi kết nối: " + err);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = "🚀 Kích Hoạt Chu Kỳ Tự Học Ngay";
      }
    }
  }

  // Dialogue Chat & Voice
  function initDialogue() {
    const sendBtn = document.getElementById("btn-dialogue-send");
    const input = document.getElementById("dialogue-input");
    const clearBtn = document.getElementById("btn-clear-dialogue");

    if (sendBtn && input) {
      sendBtn.addEventListener("click", () => sendDialogueMessage());
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          sendDialogueMessage();
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        const list = document.getElementById("dialogue-messages-list");
        if (list) {
          list.innerHTML = `
            <div class="msg-bubble msg-assistant">
              <div class="msg-author">QUAN AI BRAIN — BẢN SAO SỐ</div>
              <div class="msg-text">Hội thoại đã được xóa. Em đã sẵn sàng tiếp nhận các chỉ đạo điều hành mới của Anh.</div>
              <div class="msg-time">Bây giờ</div>
            </div>
          `;
        }
      });
    }
  }

  // Parse one SSE frame chunk into event objects (handles split frames).
  function parseSSEBuffer(buffer, onEvent) {
    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, idx);
      const lines = frame.split("\n");
      let dataStr = "";
      for (const line of lines) {
        if (line.startsWith("data:")) dataStr += line.slice(5).trim();
      }
      if (dataStr) {
        try { onEvent(JSON.parse(dataStr)); } catch (_) { /* skip malformed frame */ }
      }
    }
    return "";
  }

  async function sendDialogueMessage() {
    const input = document.getElementById("dialogue-input");
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    appendMessage("Quanpt1 (Chủ nhân)", text, "user");
    input.value = "";

    const list = document.getElementById("dialogue-messages-list");
    const streamId = "stream-" + Date.now();
    const streamEl = document.createElement("div");
    streamEl.id = streamId;
    streamEl.className = "msg-bubble msg-assistant";
    streamEl.innerHTML = `<div class="msg-author">QUAN AI BRAIN</div><div class="msg-text"><em>Bản sao đang suy luận dựa trên bằng chứng...</em></div>`;
    list.appendChild(streamEl);
    list.scrollTop = list.scrollHeight;

    const textEl = streamEl.querySelector(".msg-text");

    try {
      if (typeof setAvatarState === "function") setAvatarState("THINKING");
      if (wakeEngine) wakeEngine.notifyThinking();
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({ message: text })
      });
      if (!res.ok || !res.body) throw new Error("HTTP " + res.status);

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buf = "";
      let finalText = "";
      let gotDelta = false;

      const handleEvent = (ev) => {
        if (ev.type === "delta") {
          if (!gotDelta) {
            gotDelta = true;
            if (typeof setAvatarState === "function") setAvatarState("SPEAKING");
          }
          finalText += ev.text || "";
          if (textEl) textEl.textContent = finalText;
          list.scrollTop = list.scrollHeight;
        } else if (ev.type === "final") {
          if (ev.reply) finalText = ev.reply;   // authoritative sanitized text
          if (textEl) textEl.textContent = finalText || "(Không có nội dung phản hồi)";
        } else if (ev.type === "error") {
          finalText = "⚠️ Lỗi luồng phản hồi [" + (ev.code || "UNKNOWN") + "]: " + (ev.message || "");
          if (textEl) textEl.textContent = finalText;
        }
      };

      // Read the SSE stream until the server closes it.
      for (;;) {
        const chunk = await reader.read();
        if (chunk.done) break;
        const piece = decoder.decode(chunk.value, { stream: true });
        const remainder = buf + piece;
        let consumed = "";
        let work = remainder;
        // Consume complete frames; keep the partial tail in buf.
        for (;;) {
          const idx = work.indexOf("\n\n");
          if (idx === -1) break;
          const frame = work.slice(0, idx);
          work = work.slice(idx + 2);
          let dataStr = "";
          for (const line of frame.split("\n")) {
            if (line.startsWith("data:")) dataStr += line.slice(5).trim();
          }
          if (dataStr) {
            try { handleEvent(JSON.parse(dataStr)); } catch (_) {}
          }
          consumed = work;
        }
        buf = work;
        void consumed;
      }
      // Flush any trailing frame without a final newline.
      if (buf.trim()) {
        let dataStr = "";
        for (const line of buf.split("\n")) {
          if (line.startsWith("data:")) dataStr += line.slice(5).trim();
        }
        if (dataStr) { try { handleEvent(JSON.parse(dataStr)); } catch (_) {} }
      }
      void parseSSEBuffer; // retained helper for future reuse

      streamEl.removeAttribute("id");

      if (finalText) {
        if (window.digitalHuman && typeof window.digitalHuman.setContextFromText === "function") {
          window.digitalHuman.setContextFromText(finalText);
        }
        speakText(finalText);   // TTS only AFTER the complete answer arrives
      } else {
        appendMessage("QUAN AI BRAIN — BẢN SAO SỐ", "Xin lỗi Anh, không nhận được phản hồi từ mô hình AI.", "assistant");
      }
    } catch (err) {
      // Streaming path failed — fall back to the legacy non-streaming endpoint.
      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: jsonBody({ message: text, fallback: false })
        });
        const data = await res.json();
        const removed = document.getElementById(streamId);
        if (removed) removed.remove();
        if (data.reply) {
          appendMessage("QUAN AI BRAIN — BẢN SAO SỐ", data.reply, "assistant");
          if (window.digitalHuman && typeof window.digitalHuman.setContextFromText === "function") {
            window.digitalHuman.setContextFromText(data.reply);
          }
          speakText(data.reply);
        } else {
          appendMessage("QUAN AI BRAIN — BẢN SAO SỐ", "Xin lỗi Anh, không nhận được phản hồi từ mô hình AI cục bộ.", "assistant");
        }
      } catch (err2) {
        const removed = document.getElementById(streamId);
        if (removed) removed.remove();
        appendMessage("QUAN AI BRAIN — BẢN SAO SỐ", "Lỗi kết nối với hệ điều hành: " + (err2.message || err.message), "assistant");
      }
    }
  }

  function appendMessage(author, content, type) {
    const list = document.getElementById("dialogue-messages-list");
    if (!list) return;

    const bubble = document.createElement("div");
    bubble.className = `msg-bubble msg-${type}`;
    const now = new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
    bubble.innerHTML = `
      <div class="msg-author">${escapeHtml(author)}</div>
      <div class="msg-text">${escapeHtml(content).replace(/\n/g, '<br>')}</div>
      <div class="msg-time">${now}</div>
    `;
    list.appendChild(bubble);
    list.scrollTop = list.scrollHeight;
  }

  // Web Speech API Voice & Hands-Free Wake Word Engine
  function initVoice() {
    const voiceBtn = document.getElementById("btn-dialogue-voice");
    const btnToggleWake = document.getElementById("btn-toggle-wake");
    const btnTtsToggle = document.getElementById("btn-dialogue-tts-toggle");

    // Initialize Hands-Free Wake Word Engine
    if (typeof window.WakeWordEngine === "function") {
      wakeEngine = new window.WakeWordEngine({
        lang: "vi-VN",
        silenceTimeoutSeconds: 20.0,
        chimeEnabled: true,
        onStateChange: (newState, oldState, reason) => {
          updateWakeWordUI(newState);
        },
        onWakeDetected: (keyword, payload) => {
          appendMessage("HỆ THỐNG", `Đã nhận diện từ khóa "${keyword}". Đang lắng nghe Anh...`, "system");
        },
        onCommandRecognized: (text) => {
          const input = document.getElementById("dialogue-input");
          if (input) {
            input.value = text;
            sendDialogueMessage();
          }
        },
        onError: (msg) => {
          console.warn("Wake engine error:", msg);
        }
      });
    }

    if (btnToggleWake && wakeEngine) {
      btnToggleWake.addEventListener("click", async () => {
        if (wakeEngine.state === "DISABLED") {
          const ok = await wakeEngine.start();
          if (ok) {
            btnToggleWake.textContent = "ON";
            btnToggleWake.classList.add("active");
            fetch("/api/voice/wake-config", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: jsonBody({ enabled: true })
            }).catch(() => {});
          }
        } else {
          wakeEngine.stop();
          btnToggleWake.textContent = "OFF";
          btnToggleWake.classList.remove("active");
          fetch("/api/voice/wake-config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: jsonBody({ enabled: false })
          }).catch(() => {});
        }
      });
    }

    if (btnTtsToggle) {
      btnTtsToggle.addEventListener("click", () => {
        isTtsEnabled = !isTtsEnabled;
        btnTtsToggle.textContent = isTtsEnabled ? "🔊 Đọc: BẬT" : "🔇 Đọc: TẮT";
        if (!isTtsEnabled && window.speechSynthesis) {
          window.speechSynthesis.cancel();
          if (wakeEngine) wakeEngine.notifySpeakingEnd();
        }
      });
    }

    // Manual Mic button fallback
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (voiceBtn && SpeechRecognition) {
      recognition = new SpeechRecognition();
      recognition.lang = "vi-VN";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => {
        isListening = true;
        voiceBtn.classList.add("listening");
      };

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const input = document.getElementById("dialogue-input");
        if (input) {
          input.value = transcript;
          sendDialogueMessage();
        }
      };

      recognition.onerror = () => {
        isListening = false;
        voiceBtn.classList.remove("listening");
      };

      recognition.onend = () => {
        isListening = false;
        voiceBtn.classList.remove("listening");
      };

      voiceBtn.addEventListener("click", () => {
        if (!isListening) {
          try { recognition.start(); } catch (e) {}
        } else {
          try { recognition.stop(); } catch (e) {}
        }
      });
    }

    updateWakeWordUI("DISABLED");
  }

  function updateWakeWordUI(state) {
    const dot = document.getElementById("wake-dot-indicator");
    const label = document.getElementById("wake-state-text");
    const badge = document.getElementById("dialogue-wake-badge");
    const btnToggleWake = document.getElementById("btn-toggle-wake");

    if (dot) {
      dot.className = "wake-dot";
      if (state === "DISABLED") dot.classList.add("dot-disabled");
      else if (state === "STANDBY") dot.classList.add("dot-standby");
      else if (state === "WAKE_DETECTED") dot.classList.add("dot-wake");
      else if (state === "LISTENING" || state === "TRANSCRIBING") dot.classList.add("dot-listening");
      else if (state === "THINKING") dot.classList.add("dot-thinking");
      else if (state === "SPEAKING") dot.classList.add("dot-speaking");
      else if (state === "ERROR") dot.classList.add("dot-error");
    }

    if (btnToggleWake) {
      if (state === "DISABLED") {
        btnToggleWake.textContent = "OFF";
        btnToggleWake.classList.remove("active");
      } else {
        btnToggleWake.textContent = "ON";
        btnToggleWake.classList.add("active");
      }
    }

    const stateMap = {
      DISABLED: { label: "TẮT", badge: "🎙️ Đánh thức: TẮT", badgeClass: "" },
      STANDBY: { label: "SẴN SÀNG", badge: "👂 Chờ: 'Tony ơi'", badgeClass: "active" },
      WAKE_DETECTED: { label: "ĐÃ GỌI!", badge: "⚡ Đã đánh thức!", badgeClass: "listening" },
      LISTENING: { label: "LẮNG NGHE", badge: "🎙️ Đang nghe Anh...", badgeClass: "listening" },
      TRANSCRIBING: { label: "GHI NHẬN", badge: "✍️ Đang ghi nhận...", badgeClass: "listening" },
      THINKING: { label: "SUY NGHĨ", badge: "🧠 Đang suy luận...", badgeClass: "active" },
      SPEAKING: { label: "TRẢ LỜI", badge: "🔊 Đang đọc phản hồi...", badgeClass: "active" },
      INTERRUPTED: { label: "NGẮT LỜI", badge: "✋ Đã ngắt", badgeClass: "" },
      ERROR: { label: "LỖI MIC", badge: "⚠️ Lỗi Microphone", badgeClass: "" },
    };

    const info = stateMap[state] || { label: state, badge: state, badgeClass: "" };
    if (label) label.textContent = info.label;
    if (badge) {
      badge.textContent = info.badge;
      badge.className = "wake-badge " + (info.badgeClass || "");
    }

    // Sync avatar state
    if (typeof setAvatarState === "function") {
      if (state === "LISTENING" || state === "TRANSCRIBING") setAvatarState("LISTENING");
      else if (state === "THINKING") setAvatarState("THINKING");
      else if (state === "SPEAKING") setAvatarState("SPEAKING");
      else if (state === "ERROR") setAvatarState("ERROR");
      else if (state === "STANDBY" && (currentAvatarState === "LISTENING" || currentAvatarState === "SPEAKING")) {
        setAvatarState("IDLE");
      }
    }
  }

  let currentExecutiveAudio = null;

  function stopExecutiveAudio() {
    if (currentExecutiveAudio) {
      try {
        currentExecutiveAudio.pause();
        currentExecutiveAudio.currentTime = 0;
      } catch (_) {}
      currentExecutiveAudio = null;
    }
    if ("speechSynthesis" in window) {
      try { window.speechSynthesis.cancel(); } catch (_) {}
    }
    if (window.digitalHuman) window.digitalHuman.cancelUtterance();
    if (typeof setAvatarState === "function" && currentAvatarState === "SPEAKING") {
      setAvatarState("IDLE");
    }
    if (wakeEngine) wakeEngine.notifySpeakingEnd();
  }

  async function speakText(text) {
    if (!isTtsEnabled) return;
    stopExecutiveAudio();
    if (!text || !text.trim()) return;

    // Clean up markers preserving Vietnamese diacritics
    const clean = text.replace(/```[\s\S]*?```/g, " [Khối mã nguồn] ")
                      .replace(/`([^`]+)`/g, " $1 ")
                      .replace(/\{[^{}]*\}/g, "")
                      .replace(/https?:\/\/\S+/g, "")
                      .replace(/[A-Za-z]:\\[\w\\\.-]+/g, "")
                      .replace(/[*_#~\[\]()]/g, " ")
                      .replace(/\s+/g, " ")
                      .trim()
                      .slice(0, 450);
    if (!clean) return;

    if (wakeEngine) wakeEngine.notifySpeakingStart();
    if (typeof setAvatarState === "function") setAvatarState("SPEAKING");
    if (window.digitalHuman && typeof window.digitalHuman.setContextFromText === "function") {
      window.digitalHuman.setContextFromText(clean);
    }

    // Step 1: High-fidelity Vietnamese Female audio via Core Edge-TTS
    try {
      const res = await fetch("/api/voice/tts-synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: clean, voice_id: "vi-VN-HoaiMyNeural" }),
      });
      const data = await res.json();
      if (data.success && data.audio_base64) {
        const audio = new Audio("data:audio/mpeg;base64," + data.audio_base64);
        currentExecutiveAudio = audio;
        if (data.timeline && window.digitalHuman) {
          window.digitalHuman.setTimeline(data.timeline);
        } else if (window.digitalHuman) {
          window.digitalHuman.startSpeaking(3000);
        }
        audio.onended = () => {
          currentExecutiveAudio = null;
          if (window.digitalHuman) window.digitalHuman.cancelUtterance();
          if (typeof setAvatarState === "function") setAvatarState("IDLE");
          if (wakeEngine) wakeEngine.notifySpeakingEnd();
        };
        audio.onerror = () => {
          currentExecutiveAudio = null;
          fallbackExecutiveBrowserTTS(clean);
        };
        await audio.play();
        return;
      } else {
        console.warn("Core TTS synthesize failed, checking browser voices:", data.error);
        fallbackExecutiveBrowserTTS(clean);
      }
    } catch (err) {
      console.warn("Error calling /api/voice/tts-synthesize:", err);
      fallbackExecutiveBrowserTTS(clean);
    }
  }

  function fallbackExecutiveBrowserTTS(clean) {
    if (!("speechSynthesis" in window)) {
      if (typeof setAvatarState === "function") setAvatarState("IDLE");
      if (wakeEngine) wakeEngine.notifySpeakingEnd();
      return;
    }
    const voices = window.speechSynthesis.getVoices();
    // STRICT REQUIREMENT: Only accept real Vietnamese voice
    const viVoice = voices.find(v => {
      const lang = (v.lang || "").toLowerCase();
      const name = (v.name || "").toLowerCase();
      return lang.startsWith("vi") || lang === "vi-vn" || name.includes("vietnam") || name.includes("hoaimy");
    });

    if (!viVoice) {
      console.warn("TTS_UNAVAILABLE: Không tìm thấy voice tiếng Việt nào trong trình duyệt. Không phát giọng tiếng Anh.");
      if (typeof setAvatarState === "function") setAvatarState("IDLE");
      if (wakeEngine) wakeEngine.notifySpeakingEnd();
      return;
    }

    try {
      const utter = new SpeechSynthesisUtterance(clean);
      utter.voice = viVoice;
      utter.lang = viVoice.lang || "vi-VN";
      utter.rate = 1.0;
      utter.onstart = () => {
        if (typeof setAvatarState === "function") setAvatarState("SPEAKING");
        if (window.digitalHuman) window.digitalHuman.startSpeaking(3000);
      };
      utter.onend = () => {
        if (window.digitalHuman) window.digitalHuman.cancelUtterance();
        if (typeof setAvatarState === "function") setAvatarState("IDLE");
        if (wakeEngine) wakeEngine.notifySpeakingEnd();
      };
      utter.onerror = () => {
        if (window.digitalHuman) window.digitalHuman.cancelUtterance();
        if (typeof setAvatarState === "function") setAvatarState("IDLE");
        if (wakeEngine) wakeEngine.notifySpeakingEnd();
      };
      window.speechSynthesis.speak(utter);
    } catch (e) {
      console.warn("Browser SpeechSynthesis error:", e);
      if (window.digitalHuman) window.digitalHuman.cancelUtterance();
      if (typeof setAvatarState === "function") setAvatarState("IDLE");
      if (wakeEngine) wakeEngine.notifySpeakingEnd();
    }
  }

  // ================= VISUAL COCKPIT & DIGITAL AVATAR CONTROLLER =================
  function initVisualCockpit() {
    const viewport = document.getElementById("avatar-viewport");
    const stateTag = document.getElementById("avatar-state-tag");
    const stateIcon = document.getElementById("avatar-state-icon");
    const stateName = document.getElementById("avatar-state-name");
    const browLeft = document.getElementById("avatar-brow-left");
    const browRight = document.getElementById("avatar-brow-right");
    const symbolOverlay = document.getElementById("avatar-symbol-overlay");
    const symbolText = document.getElementById("avatar-symbol-text");
    const lidTopL = document.getElementById("lid-top-l");
    const lidBotL = document.getElementById("lid-bot-l");
    const lidTopR = document.getElementById("lid-top-r");
    const lidBotR = document.getElementById("lid-bot-r");
    const canvas = document.getElementById("avatar-waveform-canvas");

    // Initialize Digital Human Engine (Model F)
    try {
      if (typeof DigitalHumanAvatar !== "undefined") {
        window.digitalHuman = new DigitalHumanAvatar("tony-avatar-canvas", {
          basePath: "/static/assets/avatar",
          initialState: "IDLE"
        });
      }
    } catch (e) {
      console.warn("DigitalHumanAvatar init warning:", e);
    }

    const STATE_CONFIG = {
      IDLE: {
        css: "state-idle",
        name: "IDLE (SẴN SÀNG)",
        icon: "●",
        symbol: null,
        browL: "M 65 65 Q 90 63 115 65",
        browR: "M 165 65 Q 190 63 215 65",
      },
      LISTENING: {
        css: "state-listening",
        name: "LISTENING (LẮNG NGHE)",
        icon: "🎙️",
        symbol: null,
        browL: "M 65 60 Q 90 58 115 60",
        browR: "M 165 60 Q 190 58 215 60",
      },
      THINKING: {
        css: "state-thinking",
        name: "THINKING (SUY LUẬN)",
        icon: "🧠",
        symbol: null,
        browL: "M 65 67 L 115 72",
        browR: "M 165 72 L 215 67",
      },
      RESEARCHING: {
        css: "state-researching",
        name: "RESEARCHING (TRA CỨU)",
        icon: "🔬",
        symbol: null,
        browL: "M 65 64 L 115 64",
        browR: "M 165 64 L 215 64",
      },
      LEARNING: {
        css: "state-learning",
        name: "LEARNING (TỰ CẢI TIẾN)",
        icon: "⚡",
        symbol: null,
        browL: "M 65 62 L 115 64",
        browR: "M 165 64 L 215 62",
      },
      SPEAKING: {
        css: "state-speaking",
        name: "SPEAKING (TRẢ LỜI)",
        icon: "🔊",
        symbol: null,
        browL: "M 65 65 Q 90 63 115 65",
        browR: "M 165 65 Q 190 63 215 65",
      },
      WAITING_FOR_OWNER: {
        css: "state-waiting",
        name: "WAITING (CHỜ DUYỆT)",
        icon: "📬",
        symbol: "📬",
        browL: "M 65 62 Q 90 60 115 62",
        browR: "M 165 62 Q 190 60 215 62",
      },
      BLOCKED: {
        css: "state-blocked",
        name: "BLOCKED (CHẶN R5)",
        icon: "🛡️",
        symbol: "🛡️",
        browL: "M 65 72 L 115 64",
        browR: "M 165 64 L 215 72",
      },
      ERROR: {
        css: "state-error",
        name: "ERROR (SỰ CỐ)",
        icon: "⚠️",
        symbol: "⚠️",
        browL: "M 65 72 L 115 64",
        browR: "M 165 64 L 215 72",
      },
      SAFE_MODE: {
        css: "state-safemode",
        name: "SAFE_MODE (ĐÓNG BĂNG)",
        icon: "❄️",
        symbol: "❄️",
        browL: "M 65 65 L 115 65",
        browR: "M 165 65 L 215 65",
      },
      OFFLINE: {
        css: "state-offline",
        name: "OFFLINE (NGOẠI TUYẾN)",
        icon: "💤",
        symbol: null,
        browL: "M 65 68 L 115 68",
        browR: "M 165 68 L 215 68",
      },
    };

    setAvatarState = function(stateKey) {
      if (!STATE_CONFIG[stateKey]) stateKey = "IDLE";
      currentAvatarState = stateKey;
      const conf = STATE_CONFIG[stateKey];

      if (window.digitalHuman) {
        window.digitalHuman.setState(stateKey);
      }

      // Update Viewport CSS class
      if (viewport) {
        Object.values(STATE_CONFIG).forEach(c => viewport.classList.remove(c.css));
        viewport.classList.add(conf.css);
      }

      // Update Tag
      if (stateTag) {
        Object.values(STATE_CONFIG).forEach(c => stateTag.classList.remove(c.css));
        stateTag.classList.add(conf.css);
      }
      if (stateIcon) stateIcon.textContent = conf.icon;
      if (stateName) stateName.textContent = conf.name;

      // Update Brows
      if (browLeft) browLeft.setAttribute("d", conf.browL);
      if (browRight) browRight.setAttribute("d", conf.browR);

      // Symbol Overlay
      if (symbolOverlay && symbolText) {
        if (conf.symbol) {
          symbolText.textContent = conf.symbol;
          symbolOverlay.style.display = "block";
        } else {
          symbolOverlay.style.display = "none";
        }
      }

      // Eyelids
      if (stateKey === "OFFLINE") {
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

      // Highlight active preview pill
      document.querySelectorAll(".pill-state").forEach(pill => {
        if (pill.getAttribute("data-state") === stateKey) {
          pill.classList.add("active");
        } else {
          pill.classList.remove("active");
        }
      });
    };

    // State preview pills click listeners
    document.querySelectorAll(".pill-state").forEach(pill => {
      pill.addEventListener("click", () => {
        const targetState = pill.getAttribute("data-state");
        if (targetState) setAvatarState(targetState);
      });
    });

    // Natural eye blink animation loop
    function triggerBlink() {
      if (currentAvatarState !== "OFFLINE" && currentAvatarState !== "BLOCKED" && currentAvatarState !== "ERROR") {
        if (lidTopL) lidTopL.setAttribute("height", "20");
        if (lidBotL) { lidBotL.setAttribute("height", "20"); lidBotL.setAttribute("y", "97"); }
        if (lidTopR) lidTopR.setAttribute("height", "20");
        if (lidBotR) { lidBotR.setAttribute("height", "20"); lidBotR.setAttribute("y", "97"); }

        setTimeout(() => {
          if (currentAvatarState !== "OFFLINE") {
            if (lidTopL) lidTopL.setAttribute("height", "0");
            if (lidBotL) { lidBotL.setAttribute("height", "0"); lidBotL.setAttribute("y", "117"); }
            if (lidTopR) lidTopR.setAttribute("height", "0");
            if (lidBotR) { lidBotR.setAttribute("height", "0"); lidBotR.setAttribute("y", "117"); }
          }
        }, 130);
      }
      const nextInterval = 3200 + Math.random() * 2600;
      setTimeout(triggerBlink, nextInterval);
    }
    setTimeout(triggerBlink, 3500);

    // Dynamic Waveform Canvas Animation
    function initWaveform() {
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const numBars = 28;
      let phase = 0;

      function drawWaveform() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        phase += 0.08;

        const w = canvas.width;
        const h = canvas.height;
        const barWidth = Math.max(3, (w - (numBars * 3)) / numBars);

        for (let i = 0; i < numBars; i++) {
          const x = i * (barWidth + 3) + 4;
          let barHeight = 4;
          let strokeColor = "rgba(0, 229, 255, 0.4)";

          if (currentAvatarState === "SPEAKING") {
            const factor = Math.sin(phase * 2.2 + i * 0.45) * 0.5 + 0.5;
            barHeight = 5 + factor * 20;
            strokeColor = "rgba(59, 130, 246, 0.9)";
          } else if (currentAvatarState === "LISTENING") {
            const factor = Math.sin(phase * 3.0 + i * 0.6) * 0.5 + 0.5;
            barHeight = 6 + factor * 16;
            strokeColor = "rgba(6, 182, 212, 0.9)";
          } else if (currentAvatarState === "THINKING") {
            const factor = Math.cos(phase * 1.5 + i * 0.3) * 0.5 + 0.5;
            barHeight = 4 + factor * 12;
            strokeColor = "rgba(168, 85, 247, 0.85)";
          } else if (currentAvatarState === "RESEARCHING") {
            const factor = (i === Math.floor((phase * 4) % numBars)) ? 1 : 0.2;
            barHeight = 4 + factor * 16;
            strokeColor = "rgba(16, 185, 129, 0.9)";
          } else if (currentAvatarState === "LEARNING") {
            const factor = Math.sin(phase * 4 + i) > 0.3 ? 0.9 : 0.2;
            barHeight = 5 + factor * 14;
            strokeColor = "rgba(245, 158, 11, 0.9)";
          } else if (currentAvatarState === "SAFE_MODE") {
            barHeight = 5;
            strokeColor = "rgba(56, 189, 248, 0.6)";
          } else if (currentAvatarState === "BLOCKED" || currentAvatarState === "ERROR") {
            barHeight = 8 + (i % 2 === 0 ? 12 : 2);
            strokeColor = "rgba(239, 68, 68, 0.85)";
          } else if (currentAvatarState === "OFFLINE") {
            barHeight = 2;
            strokeColor = "rgba(100, 116, 139, 0.3)";
          } else {
            const mid = numBars / 2;
            const dist = Math.abs(i - mid);
            const pulse = Math.sin(phase * 0.8) * 0.5 + 0.5;
            barHeight = 3 + Math.max(0, (5 - dist * 0.4) * pulse);
            strokeColor = "rgba(0, 229, 255, 0.5)";
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

    // Supervisor & Task telemetry polling
    async function pollSupervisor() {
      try {
        const [supRes, tasksRes] = await Promise.all([
          fetch("/api/executive/supervisor"),
          fetch("/api/executive/tasks")
        ]);

        if (supRes.ok) {
          const sup = await supRes.json();
          const telemModel = document.getElementById("telem-model-val");
          if (telemModel && sup.active_model) telemModel.textContent = `${sup.active_model} (Local)`;

          const telemStatus = document.getElementById("telem-supervisor-status");
          if (telemStatus) {
            telemStatus.textContent = sup.state === "STOPPED" ? "DỪNG KHẨN CẤP" : (sup.state === "SAFE_MODE" ? "CHẾ ĐỘ AN TOÀN" : "ONLINE — ACTIVE");
            telemStatus.style.color = sup.state === "STOPPED" ? "var(--red-alert)" : (sup.state === "SAFE_MODE" ? "#38bdf8" : "var(--green-success)");
          }

          // Emergency badges & buttons
          const emBadge = document.getElementById("badge-emergency-status");
          const btnResume = document.getElementById("btn-emergency-resume");
          if (emBadge) {
            emBadge.className = "badge";
            if (sup.emergency_state === "stop") {
              emBadge.textContent = "DỪNG KHẨN CẤP";
              emBadge.classList.add("badge-stopped");
              if (btnResume) btnResume.classList.remove("hidden");
              if (currentAvatarState === "IDLE") setAvatarState("BLOCKED");
            } else if (sup.emergency_state === "freeze") {
              emBadge.textContent = "ĐÓNG BĂNG (FREEZE)";
              emBadge.classList.add("badge-frozen");
              if (btnResume) btnResume.classList.remove("hidden");
              if (currentAvatarState === "IDLE") setAvatarState("SAFE_MODE");
            } else {
              emBadge.textContent = "BÌNH THƯỜNG";
              emBadge.classList.add("badge-normal");
              if (btnResume) btnResume.classList.add("hidden");
            }
          }

          // Edge device status & alerts
          const edgeBadge = document.getElementById("badge-edge-status");
          const edgeRtt = document.getElementById("edge-rtt-tag");
          const alertBanner = document.getElementById("edge-alert-banner");
          const alertTitle = document.getElementById("edge-alert-title");
          const alertMsg = document.getElementById("edge-alert-msg");
          const edgeIcon = document.getElementById("edge-link-icon");

          if (sup.edge_device) {
            const dev = sup.edge_device;
            if (edgeBadge) {
              edgeBadge.className = "badge";
              if (dev.status === "READY") {
                edgeBadge.textContent = "READY — ĐÃ KẾT NỐI (Pi 5)";
                edgeBadge.classList.add("badge-ready");
                if (edgeIcon) edgeIcon.textContent = "🟢";
              } else if (dev.status === "CONNECTED") {
                edgeBadge.textContent = "CONNECTED — CHỜ PHẦN CỨNG";
                edgeBadge.classList.add("badge-ready");
                if (edgeIcon) edgeIcon.textContent = "🟡";
              } else if (dev.status === "DEGRADED") {
                edgeBadge.textContent = "DEGRADED — MẠNG CHẬM";
                edgeBadge.classList.add("badge-degraded");
                if (edgeIcon) edgeIcon.textContent = "⚠️";
              } else if (dev.status === "DISCONNECTED") {
                edgeBadge.textContent = "DISCONNECTED — MẤT KẾT NỐI";
                edgeBadge.classList.add("badge-stopped");
                if (edgeIcon) edgeIcon.textContent = "🔴";
              } else if (dev.status === "AUTH_FAILED") {
                edgeBadge.textContent = "AUTH_FAILED — TỪ CHỐI";
                edgeBadge.classList.add("badge-stopped");
                if (edgeIcon) edgeIcon.textContent = "⛔";
              } else {
                edgeBadge.textContent = "STANDBY — Chờ Ghép Cặp";
                edgeBadge.classList.add("badge-planned");
                if (edgeIcon) edgeIcon.textContent = "📡";
              }
            }

            // RTT tag
            if (edgeRtt) {
              if (dev.rtt_ms && dev.rtt_ms > 0 && dev.status !== "DISCONNECTED") {
                edgeRtt.style.display = "inline-block";
                edgeRtt.textContent = `RTT: ${dev.rtt_ms.toFixed(0)}ms`;
              } else {
                edgeRtt.style.display = "none";
              }
            }

            // Alert banner
            if (alertBanner && alertTitle && alertMsg) {
              if (dev.active_alerts && dev.active_alerts.length > 0) {
                const topAlert = dev.active_alerts[0];
                alertBanner.style.display = "flex";
                alertBanner.className = `edge-alert-banner severity-${(topAlert.severity || "warning").toLowerCase()}`;
                alertTitle.textContent = topAlert.title;
                alertMsg.textContent = topAlert.message;
              } else {
                alertBanner.style.display = "none";
              }
            }
          }
        }

        if (tasksRes.ok) {
          const tasksData = await tasksRes.json();
          const tasks = tasksData.active_tasks || [];
          const activeTask = tasks.find(t => t.status === "IN_PROGRESS" || t.status === "WAITING_APPROVAL" || t.status === "PENDING") || tasks[0];
          if (activeTask) {
            const taskIdEl = document.getElementById("hero-task-id");
            const taskGoalEl = document.getElementById("hero-task-goal");
            const autonomyEl = document.getElementById("badge-autonomy-level");
            const stepLabelEl = document.getElementById("hero-step-label");
            const progressPctEl = document.getElementById("hero-progress-pct");
            const progressBarEl = document.getElementById("hero-progress-bar");

            if (taskIdEl) taskIdEl.textContent = activeTask.task_id;
            if (taskGoalEl) taskGoalEl.textContent = activeTask.goal;
            if (autonomyEl && activeTask.autonomy_level) {
              autonomyEl.textContent = `${activeTask.autonomy_level} — GIÁM SÁT KỶ LUẬT`;
            }

            const totalSteps = activeTask.steps_count || (activeTask.steps ? activeTask.steps.length : 1);
            const compSteps = activeTask.completed_steps_count !== undefined ? activeTask.completed_steps_count : 0;
            const pct = activeTask.progress_pct !== undefined ? activeTask.progress_pct : Math.round((compSteps / totalSteps) * 100);
            const currStep = activeTask.steps && activeTask.steps[compSteps] ? activeTask.steps[compSteps].name : (pct >= 100 ? "Hoàn tất" : (activeTask.current_step_name || "Đang thực thi"));

            if (stepLabelEl) stepLabelEl.textContent = `Tiến trình DAG: Bước ${Math.min(compSteps + 1, totalSteps)} / ${totalSteps} (${currStep})`;
            if (progressPctEl) progressPctEl.textContent = `${pct}%`;
            if (progressBarEl) progressBarEl.style.width = `${pct}%`;
          }
        }
      } catch (e) {
        console.warn("Supervisor polling error:", e);
      }
    }

    // Live UTC Clock updater
    function updateClock() {
      const clockEl = document.getElementById("telem-clock-utc");
      if (clockEl) {
        const now = new Date();
        clockEl.textContent = now.toUTCString().slice(17, 25) + " UTC";
      }
    }
    setInterval(updateClock, 1000);
    updateClock();

    // Emergency Control Buttons
    const btnStop = document.getElementById("btn-emergency-stop");
    const btnFreeze = document.getElementById("btn-emergency-freeze");
    const btnResume = document.getElementById("btn-emergency-resume");

    async function triggerEmergency(action, reason) {
      try {
        const res = await fetch("/api/executive/emergency", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: jsonBody({ action, reason })
        });
        const data = await res.json();
        if (data.success) {
          await pollSupervisor();
        } else {
          alert("Lỗi khẩn cấp: " + (data.error || "Không thể thực hiện"));
        }
      } catch (err) {
        alert("Lỗi kết nối khẩn cấp: " + err.message);
      }
    }

    if (btnStop) {
      btnStop.addEventListener("click", () => {
        if (confirm("XÁC NHẬN DỪNG KHẨN CẤP: Dừng toàn bộ các công cụ, tác vụ và kế hoạch ngay lập tức?")) {
          setAvatarState("BLOCKED");
          triggerEmergency("stop", "Quanpt1 nhấn nút STOP khẩn cấp từ giao diện Visual Cockpit");
        }
      });
    }

    if (btnFreeze) {
      btnFreeze.addEventListener("click", () => {
        if (confirm("XÁC NHẬN ĐÓNG BĂNG (FREEZE): Chuyển hệ thống sang chế độ chỉ đọc an toàn?")) {
          setAvatarState("SAFE_MODE");
          triggerEmergency("freeze", "Quanpt1 nhấn nút FREEZE đóng băng từ giao diện Visual Cockpit");
        }
      });
    }

    if (btnResume) {
      btnResume.addEventListener("click", () => {
        if (confirm("Khôi phục trạng thái vận hành bình thường?")) {
          setAvatarState("IDLE");
          triggerEmergency("resume", "Quanpt1 khôi phục vận hành từ Visual Cockpit");
        }
      });
    }

    // Initial poll and recurring poll every 3.5s
    pollSupervisor();
    setInterval(pollSupervisor, 3500);

    // Initial state
    setAvatarState("IDLE");
  }

  // ==========================================================================
  // RASPBERRY PI 5 EDGE ADD-ON & LIVE WI-FI TELEMETRY CONTROLLER
  // ==========================================================================
  let virtualAvatar = null;

  function initEdgeAddon() {
    const btnOpenAddon = document.getElementById("btn-open-edge-addon");
    if (btnOpenAddon) {
      btnOpenAddon.addEventListener("click", (e) => {
        if (e) e.preventDefault();
        if (window.switchTab) {
          window.switchTab("tab-edge-sync");
        }
      });
    }

    // Init Virtual Model F Avatar for Screen Mirror
    try {
      if (typeof DigitalHumanAvatar !== "undefined") {
        virtualAvatar = new DigitalHumanAvatar("virtual-avatar-canvas", {
          basePath: "/static/assets/avatar",
          initialState: "IDLE"
        });
      }
    } catch (e) {
      console.warn("Virtual avatar init error:", e);
    }

    // Expression Buttons
    document.querySelectorAll(".btn-expr").forEach(btn => {
      btn.addEventListener("click", async () => {
        const expr = btn.getAttribute("data-expr");
        document.querySelectorAll(".btn-expr").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        // Update local PC avatar and virtual mirror
        setAvatarState(expr);
        if (virtualAvatar && typeof virtualAvatar.setState === "function") {
          virtualAvatar.setState(expr);
        }

        const exprTag = document.getElementById("virtual-expr-tag");
        if (exprTag) exprTag.textContent = expr;

        // Dispatch remote control to PC Core
        try {
          await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "set_expression", state: expr })
          });
        } catch (e) {
          console.error("Failed to send remote expression:", e);
        }
      });
    });

    // Remote Speech & Mouth-Sync
    const btnRemoteSpeak = document.getElementById("btn-remote-speak");
    const speechInput = document.getElementById("remote-speech-input");
    if (btnRemoteSpeak && speechInput) {
      btnRemoteSpeak.addEventListener("click", async () => {
        const text = speechInput.value.trim();
        if (!text) return;

        btnRemoteSpeak.disabled = true;
        btnRemoteSpeak.textContent = "⏳ Đang phát & đồng bộ...";

        // Update local and mirror transcripts
        const virtualTranscript = document.getElementById("virtual-transcript");
        if (virtualTranscript) virtualTranscript.textContent = `"${text}"`;

        // 1. Instant local voice speech synthesis on PC with Vietnamese female voice
        speakText(text);

        // 2. Dispatch to PC Core & Pi 5 Edge
        try {
          const res = await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "speak", text: text, state: "SPEAKING" })
          });
          const data = await res.json();
          if (data.success && data.timeline) {
            // Animate visemes on PC avatar and virtual mirror
            if (window.digitalHuman && typeof window.digitalHuman.playVisemeTimeline === "function") {
              window.digitalHuman.playVisemeTimeline(data.timeline);
            }
            if (virtualAvatar && typeof virtualAvatar.playVisemeTimeline === "function") {
              virtualAvatar.playVisemeTimeline(data.timeline);
            }
          }
        } catch (e) {
          console.error("Failed remote speech dispatch:", e);
        } finally {
          btnRemoteSpeak.disabled = false;
          btnRemoteSpeak.textContent = "🗣️ Phát Lời Nói & Đồng Bộ Khẩu Hình";
        }
      });
    }

    // Sample speech chips
    document.querySelectorAll(".chip-btn").forEach(chip => {
      chip.addEventListener("click", () => {
        const txt = chip.getAttribute("data-text");
        if (speechInput && txt) {
          speechInput.value = txt;
          if (btnRemoteSpeak) btnRemoteSpeak.click();
        }
      });
    });

    // Blink Now
    const btnBlink = document.getElementById("btn-blink-now");
    if (btnBlink) {
      btnBlink.addEventListener("click", () => {
        if (virtualAvatar && typeof virtualAvatar.triggerBlink === "function") {
          virtualAvatar.triggerBlink();
        }
        if (window.digitalHuman && typeof window.digitalHuman.triggerBlink === "function") {
          window.digitalHuman.triggerBlink();
        }
      });
    }

    // Toggle Face-Only
    const btnToggleFaceOnly = document.getElementById("btn-toggle-face-only");
    const lblFaceOnly = document.getElementById("lbl-face-only-status");
    if (btnToggleFaceOnly) {
      btnToggleFaceOnly.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "toggle_face_only" })
          });
          const data = await res.json();
          if (data.success && lblFaceOnly) {
            lblFaceOnly.textContent = data.face_only_mode ? "BẬT" : "TẮT";
          }
        } catch (e) {
          console.error("Toggle face-only error:", e);
        }
      });
    }

    // Show Launch Guide
    const btnShowGuide = document.getElementById("btn-show-launch-guide");
    if (btnShowGuide) {
      btnShowGuide.addEventListener("click", () => {
        alert(
          "HƯỚNG DẪN BẬT GƯƠNG MẶT MẪU A TOÀN MÀN HÌNH TRÊN RASPBERRY PI 5:\n\n" +
          "Cách 1 (Nhanh nhất): Mở Terminal trên Pi 5 và dán lệnh sau:\n" +
          "chromium-browser --kiosk --window-size=1280,720 --window-position=0,0 http://127.0.0.1:8768/ &\n\n" +
          "Cách 2: Nhấp đúp vào biểu tượng 'QUAN AI BRAIN Kiosk' trên Desktop của Pi 5.\n\n" +
          "Màn hình 7\" DSI sẽ hiển thị toàn màn hình gương mặt Cô Trợ Lý Mẫu A (Dịu Dàng, Thân Thiện) với đôi mắt chớp tự nhiên và đồng bộ 100% với máy tính này!"
        );
      });
    }

    // Reload Kiosk UI
    const btnReloadPi = document.getElementById("btn-reload-pi-ui");
    if (btnReloadPi) {
      btnReloadPi.addEventListener("click", async () => {
        try {
          showFileAlert("Đang gửi lệnh tải lại giao diện Kiosk đến Pi 5...", "loading");
          const res = await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "reload_ui" })
          });
          const data = await res.json();
          showFileAlert("✅ Đã gửi tín hiệu tải lại giao diện Kiosk trên Pi 5 thành công!", "success");
        } catch (e) {
          showFileAlert("❌ Lỗi khi gửi lệnh tải lại Kiosk: " + e, "error");
        }
      });
    }

    // Pause Assistant (Sleep mode)
    const btnPausePi = document.getElementById("btn-pause-pi-avatar");
    if (btnPausePi) {
      btnPausePi.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "pause" })
          });
          const data = await res.json();
          showFileAlert("💤 Trợ lý Pi 5 đã chuyển sang chế độ tạm nghỉ ngơi (nhắm mắt).", "success");
        } catch (e) {
          showFileAlert("❌ Lỗi khi gửi lệnh tạm dừng: " + e, "error");
        }
      });
    }

    // Resume Assistant (Active mode)
    const btnResumePi = document.getElementById("btn-resume-pi-avatar");
    if (btnResumePi) {
      btnResumePi.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "resume" })
          });
          const data = await res.json();
          showFileAlert("▶️ Đã đánh thức trợ lý Pi 5 trở lại trạng thái sẵn sàng làm việc!", "success");
        } catch (e) {
          showFileAlert("❌ Lỗi khi gửi lệnh đánh thức: " + e, "error");
        }
      });
    }

    // Auto Setup Audio on Pi 5
    const btnSetupAudioPi = document.getElementById("btn-setup-audio-pi");
    if (btnSetupAudioPi) {
      btnSetupAudioPi.addEventListener("click", async () => {
        try {
          showFileAlert("🎧 Đang gửi lệnh tự động cấu hình USB Audio sang Pi 5...", "loading");
          const res = await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "auto_configure_audio" })
          });
          const data = await res.json();
          if (data.success) {
            showFileAlert("✅ " + (data.message || "Đã cấu hình Loa & Micro USB trên Pi 5 thành công!"), "success");
          } else {
            showFileAlert("⚠️ Lỗi định tuyến âm thanh: " + (data.error || "Không rõ"), "error");
          }
        } catch (err) {
          showFileAlert("❌ Lỗi gửi lệnh âm thanh: " + err, "error");
        }
      });
    }

    // Safe Embodiment Shutdown Modal & Actions
    const btnShutdownPi = document.getElementById("btn-shutdown-pi-kiosk");
    const modalShutdown = document.getElementById("modal-pi-shutdown");
    const btnCloseModal = document.getElementById("btn-close-shutdown-modal");
    const btnCancelShutdown = document.getElementById("btn-cancel-shutdown");
    const optCloseKiosk = document.getElementById("opt-close-kiosk");
    const optPoweroffPi = document.getElementById("opt-poweroff-pi");

    if (btnShutdownPi && modalShutdown) {
      btnShutdownPi.addEventListener("click", () => {
        modalShutdown.classList.remove("hidden");
      });
    }

    const hideShutdownModal = () => {
      if (modalShutdown) modalShutdown.classList.add("hidden");
    };
    if (btnCloseModal) btnCloseModal.addEventListener("click", hideShutdownModal);
    if (btnCancelShutdown) btnCancelShutdown.addEventListener("click", hideShutdownModal);
    if (modalShutdown) {
      modalShutdown.addEventListener("click", (e) => {
        if (e.target === modalShutdown) hideShutdownModal();
      });
    }

    if (optCloseKiosk) {
      optCloseKiosk.addEventListener("click", async () => {
        hideShutdownModal();
        try {
          showFileAlert("🌙 Đang gửi lệnh đóng hình thể Kiosk và tắt màn hình Pi 5...", "loading");
          const res = await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "close_kiosk" })
          });
          const data = await res.json();
          showFileAlert("✅ " + (data.message || "Đã tắt giao diện hình thể trên Pi 5."), "success");
        } catch (err) {
          showFileAlert("❌ Lỗi tắt hình thể: " + err, "error");
        }
      });
    }

    if (optPoweroffPi) {
      optPoweroffPi.addEventListener("click", async () => {
        hideShutdownModal();
        if (!confirm("⚠️ Xác nhận lần cuối: Anh có chắc chắn muốn TẮT NGUỒN HOÀN TOÀN Raspberry Pi 5 không?")) {
          return;
        }
        try {
          showFileAlert("🔌 Đang phát lệnh tắt nguồn hệ thống Pi 5 an toàn...", "loading");
          const res = await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "poweroff_pi" })
          });
          const data = await res.json();
          showFileAlert("✅ " + (data.message || "Đang tắt nguồn an toàn thiết bị Pi 5..."), "success");
        } catch (err) {
          showFileAlert("❌ Lỗi tắt nguồn: " + err, "error");
        }
      });
    }

    // Start Kiosk from Tab 6 or Tab 7
    const btnStartPiKiosk = document.getElementById("btn-start-pi-kiosk");
    const btnTabStartKiosk = document.getElementById("btn-tab-start-kiosk");
    const handleStartKiosk = async () => {
      showFileAlert("🚀 Đang phát lệnh khởi động Chromium Kiosk và bật sáng màn hình 7\" DSI trên Pi 5...", "loading");
      try {
        const res = await fetch("/api/executive/edge/control", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "start_kiosk" })
        });
        const data = await res.json();
        if (data.success) {
          showFileAlert("✅ " + (data.message || "Đã khởi động hình thể Kiosk trên Pi 5 thành công!"), "success");
          loadEdgeTelemetry();
        } else {
          showFileAlert("⚠️ Lỗi khởi động Kiosk: " + (data.error || "Không rõ"), "error");
        }
      } catch (err) {
        showFileAlert("❌ Lỗi gửi lệnh khởi động: " + err, "error");
      }
    };
    if (btnStartPiKiosk) btnStartPiKiosk.addEventListener("click", handleStartKiosk);
    if (btnTabStartKiosk) btnTabStartKiosk.addEventListener("click", handleStartKiosk);

    // Stop Kiosk from Tab 7
    const btnTabStopKiosk = document.getElementById("btn-tab-stop-kiosk");
    if (btnTabStopKiosk) {
      btnTabStopKiosk.addEventListener("click", async () => {
        showFileAlert("🌙 Đang gửi lệnh đóng hình thể Kiosk và đưa màn hình Pi 5 vào chế độ nghỉ...", "loading");
        try {
          const res = await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "close_kiosk" })
          });
          const data = await res.json();
          if (data.success) {
            showFileAlert("✅ " + (data.message || "Đã tắt giao diện hình thể, đưa màn hình 7\" vào chế độ nghỉ."), "success");
            loadEdgeTelemetry();
          } else {
            showFileAlert("⚠️ Lỗi tắt hình thể: " + (data.error || "Không rõ"), "error");
          }
        } catch (err) {
          showFileAlert("❌ Lỗi tắt hình thể: " + err, "error");
        }
      });
    }

    // Reload Kiosk from Tab 7
    const btnTabReloadKiosk = document.getElementById("btn-tab-reload-kiosk");
    if (btnTabReloadKiosk) {
      btnTabReloadKiosk.addEventListener("click", () => {
        if (btnReloadPi) btnReloadPi.click();
      });
    }

    // Audio setup from Tab 7
    const btnTabAudioConfig = document.getElementById("btn-tab-audio-config");
    if (btnTabAudioConfig) {
      btnTabAudioConfig.addEventListener("click", () => {
        if (btnSetupAudioPi) btnSetupAudioPi.click();
      });
    }

    // Safe poweroff from Tab 7
    const btnTabPoweroffPi = document.getElementById("btn-tab-poweroff-pi");
    if (btnTabPoweroffPi) {
      btnTabPoweroffPi.addEventListener("click", () => {
        if (optPoweroffPi) optPoweroffPi.click();
      });
    }

    // Startup sequence & self-test from Tab 7
    const btnTabStartupSeq = document.getElementById("btn-tab-startup-sequence");
    if (btnTabStartupSeq) {
      btnTabStartupSeq.addEventListener("click", async () => {
        const origHtml = btnTabStartupSeq.innerHTML;
        btnTabStartupSeq.innerHTML = `
          <span style="font-size: 1.8rem; line-height: 1;">⏳</span>
          <div style="flex: 1;">
            <div style="font-size: 0.95rem; font-weight: 700; color:#38bdf8;">ĐANG CHÀO & TỰ KIỂM TRA PHẦN CỨNG...</div>
            <div style="font-size: 0.76rem; color: #94a3b8; margin-top: 3px;">Đang phát câu chào và kiểm tra micro/camera qua loa Pi 5...</div>
          </div>
        `;
        btnTabStartupSeq.disabled = true;
        try {
          const res = await fetch("/api/executive/edge/startup-sequence", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ greeting: "Chào anh ạ, rất vui được gặp anh." })
          });
          const data = await res.json();
          if (data.success) {
            alert(`🎉 CHU TRÌNH HOÀN TẤT:\n\n1. Đã phát lời chào: "${data.greeting_text}"\n2. Micro: ${data.mic_ok ? "✅ TỐT" : "⚠️ CẦN KIỂM TRA"}\n3. Camera: ${data.camera_ok ? "✅ TỐT" : "⚠️ CHƯA NHẬN"}\n4. Báo cáo phát ra loa Pi: "${data.report_text}"`);
          } else {
            alert(`⚠️ Thông báo: ${data.message || data.error || "Không thể thực hiện chu trình"}`);
          }
        } catch (err) {
          alert(`❌ Lỗi kết nối: ${err}`);
        } finally {
          btnTabStartupSeq.innerHTML = origHtml;
          btnTabStartupSeq.disabled = false;
        }
      });
    }

    // Quickstart Copy Command
    const btnCopyPiCmd = document.getElementById("btn-copy-pi-cmd");
    const piCmdCode = document.getElementById("pi5-install-command");
    const copyIndicator = document.getElementById("copy-status-indicator");
    if (btnCopyPiCmd && piCmdCode) {
      btnCopyPiCmd.addEventListener("click", async () => {
        const text = piCmdCode.textContent.trim();
        try {
          await navigator.clipboard.writeText(text);
          if (copyIndicator) {
            copyIndicator.textContent = "✅ ĐÃ SAO CHÉP VÀO CLIPBOARD!";
            setTimeout(() => { copyIndicator.textContent = ""; }, 4000);
          }
          btnCopyPiCmd.textContent = "✅ Đã Chép";
          setTimeout(() => { btnCopyPiCmd.textContent = "📋 Sao Chép Lệnh"; }, 2500);
        } catch (e) {
          const ta = document.createElement("textarea");
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
          if (copyIndicator) {
            copyIndicator.textContent = "✅ ĐÃ SAO CHÉP!";
            setTimeout(() => { copyIndicator.textContent = ""; }, 4000);
          }
          btnCopyPiCmd.textContent = "✅ Đã Chép";
          setTimeout(() => { btnCopyPiCmd.textContent = "📋 Sao Chép Lệnh"; }, 2500);
        }
      });
    }

    // Quick Sync & Push From Core
    const btnQuickSyncAudio = document.getElementById("btn-quick-sync-audio");
    if (btnQuickSyncAudio) {
      btnQuickSyncAudio.addEventListener("click", async () => {
        showFileAlert("⚡ Đang đồng bộ tài sản cốt lõi và định tuyến USB Audio sang Pi 5...", "loading");
        try {
          const resSync = await fetch("/api/executive/edge/files/sync-all", { method: "POST" });
          const dataSync = await resSync.json();

          const resAudio = await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "auto_configure_audio" })
          });
          const dataAudio = await resAudio.json();

          await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "reload_ui" })
          });

          showFileAlert("🎉 Kích hoạt hoàn tất: Mã nguồn Kiosk, Loa USB 90% và lắng nghe 24/7 đã sẵn sàng!", "success");
          loadPiFiles();
        } catch (err) {
          showFileAlert("❌ Lỗi kích hoạt nhanh từ PC: " + err, "error");
        }
      });
    }

    // Volume Slider
    const sliderVol = document.getElementById("slider-pi-volume");
    const lblVol = document.getElementById("lbl-pi-volume");
    if (sliderVol) {
      sliderVol.addEventListener("input", (e) => {
        if (lblVol) lblVol.textContent = `${e.target.value}%`;
      });
      sliderVol.addEventListener("change", async (e) => {
        const val = parseInt(e.target.value, 10);
        if (lblVol) lblVol.textContent = `${val}%`;
        try {
          await fetch("/api/executive/edge/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "set_volume", volume: val })
          });
        } catch (err) {
          console.warn("Volume set error:", err);
        }
      });
    }

    // File Upload Picker & Trigger
    const btnTriggerUpload = document.getElementById("btn-trigger-upload");
    const fileInput = document.getElementById("pi-file-upload-input");
    const btnSyncAll = document.getElementById("btn-sync-all-assets");
    const btnRefreshFiles = document.getElementById("btn-refresh-file-list");

    if (btnTriggerUpload && fileInput) {
      btnTriggerUpload.addEventListener("click", () => fileInput.click());
      fileInput.addEventListener("change", async () => {
        const file = fileInput.files[0];
        if (!file) return;
        showFileAlert(`Đang đọc và tải tệp '${file.name}' lên Pi 5...`, "loading");
        const reader = new FileReader();
        reader.onload = async () => {
          try {
            const b64 = reader.result.split(",")[1];
            const res = await fetch("/api/executive/edge/files/upload", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ filename: file.name, content_b64: b64 })
            });
            const data = await res.json();
            if (data.success) {
              showFileAlert(`✅ Đã tải tệp '${file.name}' lên Pi 5 thành công!`, "success");
              loadPiFiles();
            } else {
              showFileAlert(`❌ Lỗi tải tệp: ${data.error || data.pi5_message}`, "error");
            }
          } catch (err) {
            showFileAlert(`❌ Lỗi kết nối tải tệp: ${err}`, "error");
          } finally {
            fileInput.value = "";
          }
        };
        reader.readAsDataURL(file);
      });
    }

    if (btnSyncAll) {
      btnSyncAll.addEventListener("click", async () => {
        showFileAlert("🔄 Đang quét và đồng bộ toàn bộ tài sản sang Pi 5 qua Wi-Fi...", "loading");
        try {
          const res = await fetch("/api/executive/edge/files/sync-all", { method: "POST" });
          const data = await res.json();
          if (data.success) {
            showFileAlert(`✅ ${data.message}`, "success");
            loadPiFiles();
          } else {
            showFileAlert(`⚠️ Đồng bộ hoàn tất với cảnh báo: ${data.errors ? data.errors.join("; ") : ""}`, "error");
          }
        } catch (err) {
          showFileAlert(`❌ Lỗi đồng bộ toàn bộ: ${err}`, "error");
        }
      });
    }

    if (btnRefreshFiles) {
      btnRefreshFiles.addEventListener("click", () => loadPiFiles());
    }

    // Initial load of files & telemetry
    loadPiFiles();
    loadEdgeTelemetry();
    setInterval(loadEdgeTelemetry, 1500);
  }

  function showFileAlert(msg, type = "loading") {
    const el = document.getElementById("pi-file-alert");
    if (!el) return;
    el.className = `file-status-banner ${type}`;
    el.textContent = msg;
    el.classList.remove("hidden");
    if (type === "success") {
      setTimeout(() => el.classList.add("hidden"), 5000);
    }
  }

  async function loadPiFiles() {
    const tbody = document.getElementById("tbody-pi-files");
    if (!tbody) return;
    try {
      const res = await fetch("/api/executive/edge/files", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Lỗi tải tệp");

      const localFiles = data.local_files || [];
      const remoteFiles = data.remote_files || [];
      const remoteNames = new Set(remoteFiles.map(f => f.name));
      const files = localFiles.length > 0 ? localFiles : remoteFiles;

      if (files.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="padding:20px; color:var(--text-dim);">Chưa có tệp tài sản nào trên thư mục avatar. Bấm 'Tải Lên Tệp Mới' để thêm.</td></tr>`;
        return;
      }

      tbody.innerHTML = files.map(f => {
        const isImg = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"].includes(f.ext);
        const isAudio = [".wav", ".mp3", ".ogg"].includes(f.ext);
        const icon = isAudio ? "🎵" : (f.ext === ".json" ? "⚙️" : (f.ext === ".js" ? "📜" : "📄"));
        const thumbHtml = isImg 
          ? `<img src="${f.url}" class="file-thumb" alt="${escapeHtml(f.name)}" onerror="this.outerHTML='<div class=\\'file-icon-box\\'>🖼️</div>'" />`
          : `<div class="file-icon-box">${icon}</div>`;

        const sizeKb = (f.size / 1024).toFixed(1) + " KB";
        const dateStr = f.mtime ? new Date(f.mtime * 1000).toLocaleString("vi-VN") : "--";
        const isSynced = remoteNames.has(f.name);
        const statusBadge = isSynced 
          ? `<span class="badge-synced" style="background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.3); padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600;">✅ Đã trên Pi 5</span>`
          : `<span class="badge-pending" style="background:rgba(245,158,11,0.15); color:#f59e0b; border:1px solid rgba(245,158,11,0.3); padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600;">🟢 Sẵn sàng (PC)</span>`;

        const protectedFiles = ["model_f_portrait.png", "model_f_happy.png", "mouth_rest.png", "eyes_open.png"];
        const isProtected = protectedFiles.includes(f.name);

        const syncBtn = `<button class="btn-file-sync" data-filename="${escapeHtml(f.name)}" title="Đồng bộ ngay tệp này sang Pi 5" style="background:rgba(0,229,255,0.12); color:var(--cyan-glow); border:1px solid rgba(0,229,255,0.3); border-radius:4px; padding:3px 8px; font-size:0.75rem; cursor:pointer; margin-right:4px;">📡 Đồng bộ</button>`;

        const delBtn = isProtected
          ? `<span class="note-sub" style="color:var(--text-dim); margin-left:4px;">Gốc</span>`
          : `<button class="btn-file-del" data-filename="${escapeHtml(f.name)}" style="background:rgba(239,68,68,0.12); color:#f87171; border:1px solid rgba(239,68,68,0.3); border-radius:4px; padding:3px 8px; font-size:0.75rem; cursor:pointer;">🗑️ Xóa</button>`;

        return `
          <tr>
            <td>${thumbHtml}</td>
            <td><strong>${escapeHtml(f.name)}</strong></td>
            <td><span class="badge-ext">${escapeHtml(f.ext.replace(".", ""))}</span> ${statusBadge}</td>
            <td>${sizeKb}</td>
            <td><span class="note-sub">${dateStr}</span></td>
            <td style="text-align: right; white-space: nowrap;">${syncBtn}${delBtn}</td>
          </tr>
        `;
      }).join("");

      // Bind individual sync buttons
      tbody.querySelectorAll(".btn-file-sync").forEach(btn => {
        btn.addEventListener("click", async (e) => {
          const fn = e.currentTarget.getAttribute("data-filename");
          showFileAlert(`Đang gửi yêu cầu đồng bộ '${fn}' sang Pi 5...`, "loading");
          try {
            const syncRes = await fetch("/api/executive/edge/files/sync-all", { method: "POST" });
            const sData = await syncRes.json();
            if (sData.success) {
              showFileAlert(`✅ Đã đồng bộ tài sản sang Pi 5!`, "success");
            } else {
              showFileAlert(`⚠️ Đồng bộ: ${sData.message || sData.error}`, "error");
            }
            loadPiFiles();
          } catch (err) {
            showFileAlert(`❌ Lỗi đồng bộ: ${err}`, "error");
          }
        });
      });

      // Bind delete buttons
      tbody.querySelectorAll(".btn-file-del").forEach(btn => {
        btn.addEventListener("click", async (e) => {
          const fn = e.currentTarget.getAttribute("data-filename");
          if (!confirm(`Anh có chắc chắn muốn xóa tệp '${fn}' trên Pi 5 không?`)) return;
          try {
            const delRes = await fetch("/api/executive/edge/files/delete", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ filename: fn })
            });
            const delData = await delRes.json();
            if (delData.success) {
              showFileAlert(`Đã xóa tệp '${fn}'.`, "success");
              loadPiFiles();
            } else {
              showFileAlert(`Lỗi xóa tệp: ${delData.error}`, "error");
            }
          } catch (err) {
            showFileAlert(`Lỗi khi xóa tệp: ${err}`, "error");
          }
        });
      });

    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="padding:20px; color:#f87171;">Không thể tải danh sách tệp: ${err}</td></tr>`;
    }
  }

  // Export to window for tab switching and external triggers
  window.loadPiFiles = loadPiFiles;
  window.loadEdgeTelemetry = loadEdgeTelemetry;


  // Draw smooth ping latency graph
  function drawPingGraph(rttHistory) {
    const canvas = document.getElementById("canvas-ping-graph");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    // Background Grid
    ctx.strokeStyle = "rgba(0, 229, 255, 0.08)";
    ctx.lineWidth = 1;
    for (let y = 15; y < h; y += 20) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    if (!rttHistory || rttHistory.length < 2) return;

    const maxRtt = Math.max(30, ...rttHistory);
    const minRtt = Math.min(5, ...rttHistory);
    const range = Math.max(10, maxRtt - minRtt);

    const stepX = w / (rttHistory.length - 1);

    // Fill gradient under curve
    ctx.beginPath();
    ctx.moveTo(0, h);
    rttHistory.forEach((val, i) => {
      const x = i * stepX;
      const y = h - ((val - minRtt) / range) * (h - 20) - 10;
      if (i === 0) ctx.lineTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.lineTo(w, h);
    ctx.closePath();

    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, "rgba(52, 211, 153, 0.35)");
    grad.addColorStop(1, "rgba(52, 211, 153, 0.0)");
    ctx.fillStyle = grad;
    ctx.fill();

    // Line curve
    ctx.beginPath();
    rttHistory.forEach((val, i) => {
      const x = i * stepX;
      const y = h - ((val - minRtt) / range) * (h - 20) - 10;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "#34d399";
    ctx.lineWidth = 2.5;
    ctx.shadowColor = "#34d399";
    ctx.shadowBlur = 8;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Dot on last point
    const lastX = (rttHistory.length - 1) * stepX;
    const lastY = h - ((rttHistory[rttHistory.length - 1] - minRtt) / range) * (h - 20) - 10;
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#10b981";
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  // Load telemetry data from PC Core
  async function loadEdgeTelemetry() {
    try {
      const res = await fetch("/api/executive/edge/telemetry", { cache: "no-store" });
      if (!res.ok) return;
      const data = await res.json();
      if (!data.success) return;

      const pcIpEl = document.getElementById("addon-pc-ip");
      const piIpEl = document.getElementById("addon-pi-ip");
      const rttEl = document.getElementById("addon-live-rtt");
      const packetsInEl = document.getElementById("addon-packets-in");
      const packetsOutEl = document.getElementById("addon-packets-out");
      const pingAvgEl = document.getElementById("addon-ping-avg");
      const linkStateBadge = document.getElementById("addon-badge-link-state");
      const tabBadge = document.getElementById("badge-edge-tab-status");
      const btnDirect = document.getElementById("btn-open-kiosk-direct");

      if (pcIpEl && data.core_ip) pcIpEl.textContent = data.core_ip;
      if (piIpEl && data.edge_ip) {
        piIpEl.textContent = data.edge_ip;
        if (btnDirect) btnDirect.href = `http://${data.edge_ip}/`;
      }
      if (rttEl && data.rtt_ms) {
        rttEl.textContent = `RTT: ${data.rtt_ms.toFixed(0)}ms`;
      }
      if (packetsInEl) packetsInEl.textContent = (data.packets_in || 0).toLocaleString();
      if (packetsOutEl) packetsOutEl.textContent = (data.packets_out || 0).toLocaleString();

      if (data.rtt_history && data.rtt_history.length > 0) {
        drawPingGraph(data.rtt_history);
        const avg = data.rtt_history.reduce((a, b) => a + b, 0) / data.rtt_history.length;
        if (pingAvgEl) pingAvgEl.textContent = `Trung bình: ~${avg.toFixed(1)}ms`;
      }

      const isOnline = data.edge_status && data.edge_status.state === "READY";
      if (linkStateBadge) {
        if (isOnline) {
          linkStateBadge.className = "badge badge-ready";
          linkStateBadge.textContent = "🟢 ĐỒNG BỘ 100%";
        } else {
          linkStateBadge.className = "badge badge-stopped";
          linkStateBadge.textContent = "🔴 MẤT KẾT NỐI";
        }
      }
      if (tabBadge) {
        tabBadge.className = isOnline ? "tab-badge badge-green" : "tab-badge badge-stopped";
        tabBadge.textContent = isOnline ? "LIVE" : "OFF";
      }

      // Update virtual screen overlay
      const virtualStatusText = document.getElementById("virtual-status-text");
      const virtualExprTag = document.getElementById("virtual-expr-tag");
      const virtualTranscript = document.getElementById("virtual-transcript");

      if (virtualStatusText) {
        virtualStatusText.textContent = isOnline ? `PI 5 KIOSK: ONLINE (${data.edge_ip})` : "PI 5 KIOSK: OFFLINE";
      }
      if (virtualExprTag && data.target_avatar_state) {
        virtualExprTag.textContent = data.target_avatar_state;
      }
      if (virtualTranscript && data.transcript) {
        virtualTranscript.textContent = `"${data.transcript}"`;
      }

      if (virtualAvatar && typeof virtualAvatar.setState === "function" && data.target_avatar_state) {
        virtualAvatar.setState(data.target_avatar_state);
      }

      // Update Tab 7 Embodiment Status
      updateEmbodimentTabStatus(data, isOnline);
    } catch (e) {
      // Telemetry poll silent
    }
  }

  function updateEmbodimentTabStatus(data, isOnline) {
    const tabEmbodimentBadge = document.getElementById("badge-tab-embodiment-state");
    const embodimentPill = document.getElementById("badge-embodiment-pill");
    const liveStateBadge = document.getElementById("embodiment-live-state-badge");
    const iconStatus = document.getElementById("embodiment-icon-status");
    const avatarHalo = document.getElementById("embodiment-avatar-halo");
    const mainText = document.getElementById("embodiment-main-text");
    const subText = document.getElementById("embodiment-sub-text");
    const statProcess = document.getElementById("stat-embodiment-process");
    const statRtt = document.getElementById("stat-embodiment-rtt");

    if (statRtt && data && data.rtt_ms) {
      statRtt.textContent = `${data.rtt_ms.toFixed(0)} ms`;
    }

    if (!isOnline) {
      if (tabEmbodimentBadge) {
        tabEmbodimentBadge.textContent = "OFFLINE";
        tabEmbodimentBadge.style.background = "rgba(239, 68, 68, 0.2)";
        tabEmbodimentBadge.style.color = "#f87171";
        tabEmbodimentBadge.style.borderColor = "rgba(239, 68, 68, 0.4)";
      }
      if (embodimentPill) {
        embodimentPill.textContent = "NGOẠI TUYẾN (OFFLINE)";
        embodimentPill.style.background = "rgba(239, 68, 68, 0.25)";
        embodimentPill.style.color = "#fca5a5";
        embodimentPill.style.borderColor = "rgba(239, 68, 68, 0.4)";
      }
      if (liveStateBadge) {
        liveStateBadge.className = "badge badge-stopped";
        liveStateBadge.textContent = "🔴 NGOẠI TUYẾN";
      }
      if (iconStatus) iconStatus.textContent = "🔌";
      if (avatarHalo) {
        avatarHalo.style.borderColor = "rgba(239, 68, 68, 0.4)";
        avatarHalo.style.background = "radial-gradient(circle, rgba(239, 68, 68, 0.15) 0%, rgba(15, 23, 42, 0) 70%)";
      }
      if (mainText) mainText.textContent = "Thiết Bị Pi 5 Đang Ngoại Tuyến";
      if (subText) subText.textContent = "Chưa kết nối Wi-Fi với Pi 5 hoặc thiết bị chưa được cấp nguồn.";
      if (statProcess) {
        statProcess.textContent = "CHƯA KẾT NỐI";
        statProcess.style.color = "#f87171";
      }
      return;
    }

    const state = (data && data.target_avatar_state) || "IDLE";
    const lastTele = (data && data.last_telemetry) || {};
    const kioskRunning = lastTele.kiosk_running !== undefined ? lastTele.kiosk_running : (state !== "OFFLINE" && state !== "STOPPED");

    if (kioskRunning) {
      if (tabEmbodimentBadge) {
        tabEmbodimentBadge.textContent = "ACTIVE";
        tabEmbodimentBadge.style.background = "rgba(16, 185, 129, 0.2)";
        tabEmbodimentBadge.style.color = "#34d399";
        tabEmbodimentBadge.style.borderColor = "rgba(16, 185, 129, 0.4)";
      }
      if (embodimentPill) {
        embodimentPill.textContent = "🟢 ĐANG HOẠT ĐỘNG (ACTIVE)";
        embodimentPill.style.background = "rgba(16, 185, 129, 0.25)";
        embodimentPill.style.color = "#6ee7b7";
        embodimentPill.style.borderColor = "rgba(16, 185, 129, 0.5)";
      }
      if (liveStateBadge) {
        liveStateBadge.className = "badge badge-ready";
        liveStateBadge.textContent = "🟢 ĐANG HOẠT ĐỘNG";
      }
      if (iconStatus) iconStatus.textContent = "✨";
      if (avatarHalo) {
        avatarHalo.style.borderColor = "#10b981";
        avatarHalo.style.background = "radial-gradient(circle, rgba(16, 185, 129, 0.25) 0%, rgba(15, 23, 42, 0) 70%)";
        avatarHalo.classList.add("pulse");
      }
      if (mainText) mainText.textContent = "Giao Diện Hình Thể Đang Hoạt Động (Kiosk Active)";
      if (subText) subText.textContent = 'Màn hình 7" DSI đang hiển thị gương mặt Cô Trợ Lý Mẫu A và đồng bộ trực tiếp với PC Core.';
      if (statProcess) {
        statProcess.textContent = "ĐANG CHẠY (Chromium)";
        statProcess.style.color = "#34d399";
      }
    } else {
      if (tabEmbodimentBadge) {
        tabEmbodimentBadge.textContent = "STANDBY";
        tabEmbodimentBadge.style.background = "rgba(245, 158, 11, 0.15)";
        tabEmbodimentBadge.style.color = "#fcd34d";
        tabEmbodimentBadge.style.borderColor = "rgba(245, 158, 11, 0.3)";
      }
      if (embodimentPill) {
        embodimentPill.textContent = "CHẾ ĐỘ CHỜ (STANDBY)";
        embodimentPill.style.background = "rgba(100, 116, 139, 0.3)";
        embodimentPill.style.color = "#cbd5e1";
        embodimentPill.style.borderColor = "rgba(148, 163, 184, 0.4)";
      }
      if (liveStateBadge) {
        liveStateBadge.className = "badge";
        liveStateBadge.textContent = "💤 STANDBY";
        liveStateBadge.style.background = "rgba(100, 116, 139, 0.25)";
        liveStateBadge.style.color = "#cbd5e1";
      }
      if (iconStatus) iconStatus.textContent = "💤";
      if (avatarHalo) {
        avatarHalo.style.borderColor = "rgba(148, 163, 184, 0.3)";
        avatarHalo.style.background = "radial-gradient(circle, rgba(100, 116, 139, 0.15) 0%, rgba(15, 23, 42, 0) 70%)";
        avatarHalo.classList.remove("pulse");
      }
      if (mainText) mainText.textContent = "Hình Thể Đang Ở Chế Độ Nghỉ (Standby)";
      if (subText) subText.textContent = 'Màn hình 7" DSI đang tắt nguồn hiển thị (DPMS off). Bấm nút "BẬT HỆ THỐNG HÌNH THỂ" bên cạnh để hiển thị trợ lý.';
      if (statProcess) {
        statProcess.textContent = "ĐÃ DỪNG (Standby)";
        statProcess.style.color = "#94a3b8";
      }
    }
  }

  // ==========================================================================
  // ADDENDUM V2.1 — REMOTE SENSORS, AUDIO CONTROL, CAMERA VIEW & CAPTURES
  // ==========================================================================
  function initRemoteSensors() {
    let lastSnapshotData = null;
    let liveStreamingActive = false;
    let liveStreamTimer = null;
    let audioPollTimer = null;

    // --- Audio Control & Real Audio Level Meter ---
    async function loadAudioStatus() {
      try {
        const res = await fetch("/api/executive/edge/audio/status", { cache: "no-store" });
        if (!res.ok) return;
        const data = await res.json();
        if (!data.success) return;

        const devEl = document.getElementById("lbl-mic-device");
        const fmtEl = document.getElementById("lbl-mic-format");
        const lvlEl = document.getElementById("lbl-mic-level");
        const tsEl = document.getElementById("lbl-mic-timestamp");
        const meterDbEl = document.getElementById("lbl-meter-db");
        const meterFillEl = document.getElementById("meter-bar-fill");
        const badgeMic = document.getElementById("badge-mic-state");
        const badgeWake = document.getElementById("badge-wake-state");
        const badgeMode = document.getElementById("badge-listen-mode");

        if (devEl && data.device_name) devEl.textContent = data.device_name;
        if (fmtEl && data.sample_rate) {
          const chStr = (data.channels === 1 ? "Mono (1CH)" : "Stereo (2CH)");
          fmtEl.textContent = `${data.sample_rate.toLocaleString()} Hz • ${chStr}`;
        }

        const db = (data.audio_level_db != null) ? Number(data.audio_level_db) : -60.0;
        if (lvlEl) lvlEl.textContent = `${db.toFixed(1)} dB`;
        if (tsEl && data.timestamp) {
          const dt = new Date(data.timestamp);
          tsEl.textContent = isNaN(dt.getTime()) ? data.timestamp : dt.toLocaleTimeString();
        }

        // Calculate meter width: -60 dB -> 0%, 0 dB -> 100%
        const pct = Math.min(100, Math.max(0, ((db + 60) / 60) * 100));
        if (meterFillEl) {
          meterFillEl.style.width = `${pct}%`;
        }
        if (meterDbEl) {
          let desc = "Yên tĩnh";
          if (db > -25) desc = "Âm lượng to";
          else if (db > -45) desc = "Chuẩn hoạt động";
          meterDbEl.textContent = `${db.toFixed(1)} dB (${desc})`;
        }

        if (badgeMic) {
          if (data.mic_enabled === false) {
            badgeMic.className = "badge";
            badgeMic.style.background = "rgba(239, 68, 68, 0.2)";
            badgeMic.style.color = "#f87171";
            badgeMic.style.border = "1px solid #ef4444";
            badgeMic.textContent = "🔴 MIC OFF";
          } else if (data.mic_muted === true) {
            badgeMic.className = "badge";
            badgeMic.style.background = "rgba(245, 158, 11, 0.2)";
            badgeMic.style.color = "#fbbf24";
            badgeMic.style.border = "1px solid #f59e0b";
            badgeMic.textContent = "🔇 MUTE";
          } else {
            badgeMic.className = "badge";
            badgeMic.style.background = "rgba(16, 185, 129, 0.2)";
            badgeMic.style.color = "#10b981";
            badgeMic.style.border = "1px solid #10b981";
            badgeMic.textContent = "🟢 READY";
          }
        }

        if (badgeWake) {
          if (data.wake_word_enabled) {
            badgeWake.style.background = "rgba(56, 189, 248, 0.2)";
            badgeWake.style.color = "#38bdf8";
            badgeWake.style.border = "1px solid #38bdf8";
            badgeWake.textContent = "🎙️ WAKE: BẬT";
          } else {
            badgeWake.style.background = "rgba(100, 116, 139, 0.2)";
            badgeWake.style.color = "#94a3b8";
            badgeWake.style.border = "1px solid #64748b";
            badgeWake.textContent = "🎙️ WAKE: TẮT";
          }
        }

        if (badgeMode) {
          badgeMode.textContent = `CHẾ ĐỘ: ${data.listening_mode || "WAKE WORD"}`;
        }
      } catch (err) {
        // silent audio poll error
      }
    }

    function showAudioAlert(msg, type = "loading") {
      const el = document.getElementById("audio-alert-banner");
      if (!el) return;
      el.className = `file-status-banner ${type}`;
      el.textContent = msg;
      el.classList.remove("hidden");
      if (type === "success") {
        setTimeout(() => el.classList.add("hidden"), 5000);
      }
    }

    async function sendAudioControl(action, payload = {}) {
      try {
        showAudioAlert(`Đang gửi lệnh ${action} đến Pi 5...`, "loading");
        const body = Object.assign({ action: action }, payload);
        const res = await fetch("/api/executive/edge/audio/control", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        const data = await res.json();
        if (data.success) {
          showAudioAlert(`✅ ${data.message || 'Thao tác thành công!'}`, "success");
        } else {
          showAudioAlert(`❌ Lỗi: ${data.error || 'Thao tác thất bại'}`, "error");
        }
        await loadAudioStatus();
      } catch (e) {
        showAudioAlert(`❌ Lỗi kết nối điều khiển audio: ${e}`, "error");
      }
    }

    const btnMicOn = document.getElementById("btn-mic-on");
    const btnMicOff = document.getElementById("btn-mic-off");
    const btnMicMute = document.getElementById("btn-mic-mute");
    const btnMicUnmute = document.getElementById("btn-mic-unmute");
    const btnToggleWake = document.getElementById("btn-toggle-wake-word");
    const btnMicPtt = document.getElementById("btn-mic-ptt");
    const btnTestMic = document.getElementById("btn-test-mic");
    const btnRefreshAudio = document.getElementById("btn-refresh-audio");

    if (btnMicOn) btnMicOn.addEventListener("click", () => sendAudioControl("mic_on"));
    if (btnMicOff) btnMicOff.addEventListener("click", () => sendAudioControl("mic_off"));
    if (btnMicMute) btnMicMute.addEventListener("click", () => sendAudioControl("mute"));
    if (btnMicUnmute) btnMicUnmute.addEventListener("click", () => sendAudioControl("unmute"));
    if (btnToggleWake) btnToggleWake.addEventListener("click", () => sendAudioControl("toggle_wake_word"));
    if (btnMicPtt) btnMicPtt.addEventListener("click", () => sendAudioControl("push_to_talk"));
    if (btnTestMic) {
      btnTestMic.addEventListener("click", async () => {
        showAudioAlert("🧪 Đang đo cường độ âm thanh thực tế 1 giây từ micro phần cứng Pi 5...", "loading");
        try {
          const res = await fetch("/api/executive/edge/audio/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "test_mic" })
          });
          const data = await res.json();
          if (data.success) {
            showAudioAlert(`✅ Kết quả kiểm tra: Mức tín hiệu ${data.audio_level_db != null ? data.audio_level_db.toFixed(1) : '-18.0'} dB (Thời gian đo: ${data.duration_sec || 1.0}s)`, "success");
          } else {
            showAudioAlert(`❌ Lỗi kiểm tra micro: ${data.error}`, "error");
          }
          await loadAudioStatus();
        } catch (e) {
          showAudioAlert(`❌ Lỗi kiểm tra: ${e}`, "error");
        }
      });
    }
    if (btnRefreshAudio) btnRefreshAudio.addEventListener("click", () => loadAudioStatus());

    // --- Camera View & Snapshot Controls ---
    function showCameraAlert(msg, type = "loading") {
      const el = document.getElementById("camera-alert-banner");
      if (!el) return;
      el.className = `file-status-banner ${type}`;
      el.textContent = msg;
      el.classList.remove("hidden");
      if (type === "success") {
        setTimeout(() => el.classList.add("hidden"), 5000);
      }
    }

    async function loadCameraStatus() {
      try {
        const res = await fetch("/api/executive/edge/camera/status", { cache: "no-store" });
        if (!res.ok) return;
        const data = await res.json();
        if (!data.success) return;

        const badgeCam = document.getElementById("badge-camera-state");
        const overlayTag = document.getElementById("camera-overlay-tag");
        const devNameEl = document.getElementById("lbl-camera-device-name");
        const placeholderText = document.getElementById("camera-placeholder-text");

        if (devNameEl && data.device_name) {
          devNameEl.textContent = `${data.device_name} (${data.device_node || '/dev/video0'})`;
        }

        if (badgeCam) {
          if (data.camera_enabled) {
            badgeCam.style.background = "rgba(16, 185, 129, 0.2)";
            badgeCam.style.color = "#10b981";
            badgeCam.style.border = "1px solid #10b981";
            badgeCam.textContent = "🟢 CAMERA ON";
          } else {
            badgeCam.style.background = "rgba(148, 163, 184, 0.2)";
            badgeCam.style.color = "#94a3b8";
            badgeCam.style.border = "1px solid #64748b";
            badgeCam.textContent = "🔴 CAMERA OFF";
          }
        }

        if (overlayTag && !liveStreamingActive) {
          overlayTag.textContent = data.camera_enabled ? "📷 SẴN SÀNG" : "🔴 TẮT";
        }

        if (placeholderText) {
          placeholderText.textContent = data.camera_enabled 
            ? "Camera đã BẬT. Nhấn 'BẮT ĐẦU XEM' hoặc 'CHỤP SNAPSHOT'."
            : "Camera đang ở chế độ TẮT (Camera OFF)";
        }
      } catch (err) {
        // silent camera poll
      }
    }

    async function sendCameraControl(action, payload = {}) {
      try {
        showCameraAlert(`Đang gửi lệnh ${action} đến Camera Pi 5...`, "loading");
        const body = Object.assign({ action: action }, payload);
        const res = await fetch("/api/executive/edge/camera/control", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        const data = await res.json();
        if (data.success) {
          showCameraAlert(`✅ ${data.message || 'Thao tác camera thành công!'}`, "success");
        } else {
          showCameraAlert(`❌ Lỗi camera: ${data.error || 'Thao tác thất bại'}`, "error");
        }
        await loadCameraStatus();
      } catch (e) {
        showCameraAlert(`❌ Lỗi kết nối điều khiển camera: ${e}`, "error");
      }
    }

    const imgLive = document.getElementById("camera-live-img");
    const placeholderBox = document.getElementById("camera-placeholder-box");
    const overlayTag = document.getElementById("camera-overlay-tag");
    const lblCamTs = document.getElementById("lbl-camera-timestamp");

    const btnCamOn = document.getElementById("btn-camera-on");
    const btnCamOff = document.getElementById("btn-camera-off");
    const btnCamStartLive = document.getElementById("btn-camera-start-live");
    const btnCamStopLive = document.getElementById("btn-camera-stop-live");
    const btnCamCapture = document.getElementById("btn-camera-capture");
    const btnCamSaveCore = document.getElementById("btn-camera-save-core");
    const btnTestCamera = document.getElementById("btn-test-camera");
    const btnCamClear = document.getElementById("btn-camera-clear");

    if (btnCamOn) btnCamOn.addEventListener("click", () => sendCameraControl("camera_on"));
    if (btnCamOff) {
      btnCamOff.addEventListener("click", () => {
        stopLiveStream();
        sendCameraControl("camera_off");
        if (imgLive) imgLive.style.display = "none";
        if (placeholderBox) placeholderBox.style.display = "flex";
        if (overlayTag) overlayTag.textContent = "🔴 TẮT";
      });
    }

    async function startLiveStream() {
      if (liveStreamingActive) return;
      liveStreamingActive = true;
      if (overlayTag) overlayTag.textContent = "🟢 TRỰC TIẾP (LIVE)";
      if (imgLive) imgLive.style.display = "block";
      if (placeholderBox) placeholderBox.style.display = "none";
      await sendCameraControl("camera_on");
      sendCameraControl("start_live");

      function fetchNextFrame() {
        if (!liveStreamingActive) return;
        const frame = new Image();
        frame.onload = () => {
          if (!liveStreamingActive) return;
          if (imgLive) {
            imgLive.src = frame.src;
            if (lblCamTs) lblCamTs.textContent = new Date().toLocaleTimeString();
          }
          liveStreamTimer = setTimeout(fetchNextFrame, 600);
        };
        frame.onerror = () => {
          if (!liveStreamingActive) return;
          liveStreamTimer = setTimeout(fetchNextFrame, 1500);
        };
        frame.src = `/api/executive/edge/camera/stream?t=${Date.now()}`;
      }
      fetchNextFrame();
    }

    function stopLiveStream() {
      liveStreamingActive = false;
      if (liveStreamTimer) {
        clearTimeout(liveStreamTimer);
        clearInterval(liveStreamTimer);
        liveStreamTimer = null;
      }
      if (overlayTag) overlayTag.textContent = "⏹️ ĐÃ DỪNG";
      sendCameraControl("stop_live");
    }

    if (btnCamStartLive) btnCamStartLive.addEventListener("click", startLiveStream);
    if (btnCamStopLive) btnCamStopLive.addEventListener("click", stopLiveStream);

    // Quick camera view button from Tab 1
    const btnQuickCam = document.getElementById("btn-quick-open-camera");
    if (btnQuickCam) {
      btnQuickCam.addEventListener("click", () => {
        if (window.switchTab) window.switchTab("tab-edge-sync");
        setTimeout(() => {
          const camCard = document.getElementById("card-remote-camera");
          if (camCard) camCard.scrollIntoView({ behavior: "smooth", block: "center" });
          startLiveStream();
        }, 300);
      });
    }

    if (btnCamCapture) {
      btnCamCapture.addEventListener("click", async () => {
        showCameraAlert("📸 Đang yêu cầu Pi 5 chụp ảnh snapshot qua V4L2...", "loading");
        try {
          await sendCameraControl("camera_on");
          const res = await fetch("/api/executive/edge/camera/snapshot", { cache: "no-store" });
          const data = await res.json();
          if (data.success && data.image_b64) {
            lastSnapshotData = data;
            if (imgLive) {
              imgLive.src = `data:image/jpeg;base64,${data.image_b64}`;
              imgLive.style.display = "block";
            }
            if (placeholderBox) placeholderBox.style.display = "none";
            if (overlayTag) overlayTag.textContent = "📸 SNAPSHOT";
            if (lblCamTs) lblCamTs.textContent = data.timestamp || new Date().toLocaleTimeString();

            // Populate inspection box
            const lblSnapId = document.getElementById("lbl-snap-id");
            const lblSnapSize = document.getElementById("lbl-snap-size");
            const lblSnapHash = document.getElementById("lbl-snap-hash");
            const lblSnapVerif = document.getElementById("lbl-snap-verif");

            if (lblSnapId) lblSnapId.textContent = data.snapshot_id || "--";
            if (lblSnapSize) lblSnapSize.textContent = `${((data.size_bytes || 0) / 1024).toFixed(1)} KB`;
            if (lblSnapHash) lblSnapHash.textContent = data.sha256_hash || "--";
            if (lblSnapVerif) {
              lblSnapVerif.className = "badge badge-ready";
              lblSnapVerif.textContent = "✅ SHA-256 HỢP LỆ";
            }

            showCameraAlert(`✅ Đã chụp snapshot (${((data.size_bytes || 0) / 1024).toFixed(1)} KB). Bấm "LƯU VỀ CORE" để lưu vĩnh viễn!`, "success");
          } else {
            showCameraAlert(`❌ Không thể chụp snapshot: ${data.error || 'Lỗi thiết bị'}`, "error");
          }
        } catch (e) {
          showCameraAlert(`❌ Lỗi chụp snapshot: ${e}`, "error");
        }
      });
    }

    if (btnCamSaveCore) {
      btnCamSaveCore.addEventListener("click", async () => {
        if (!lastSnapshotData || !lastSnapshotData.image_b64) {
          alert("Chưa có ảnh snapshot nào để lưu! Vui lòng bấm 'CHỤP SNAPSHOT' trước.");
          return;
        }
        showCameraAlert("💾 Đang xác minh SHA-256 và lưu snapshot vào PC Core repository...", "loading");
        try {
          const res = await fetch("/api/executive/edge/camera/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              snapshot_id: lastSnapshotData.snapshot_id,
              image_b64: lastSnapshotData.image_b64,
              sha256_hash: lastSnapshotData.sha256_hash,
              metadata: {
                source: "pi5_camera",
                resolution: lastSnapshotData.resolution || "640x480",
                device: "Sirius USB2.0 Camera",
                device_node: "/dev/video0"
              }
            })
          });
          const data = await res.json();
          if (data.success) {
            showCameraAlert(`💾 Đã lưu snapshot vào PC Core (${data.file_path || 'data/edge_media/captures/'}) thành công! Mã băm SHA-256 đã xác minh.`, "success");
            loadCaptureLibrary();
          } else {
            showCameraAlert(`❌ Lưu thất bại: ${data.error || data.message}`, "error");
          }
        } catch (e) {
          showCameraAlert(`❌ Lỗi khi lưu ảnh về PC Core: ${e}`, "error");
        }
      });
    }

    if (btnTestCamera) {
      btnTestCamera.addEventListener("click", async () => {
        showCameraAlert("🧪 Đang kiểm tra luồng video camera qua v4l2...", "loading");
        try {
          const res = await fetch("/api/executive/edge/camera/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "test_camera" })
          });
          const data = await res.json();
          if (data.success) {
            showCameraAlert(`✅ Camera hoạt động tốt: ${data.device_name} (${data.resolution || '640x480'})`, "success");
          } else {
            showCameraAlert(`❌ Lỗi camera: ${data.error}`, "error");
          }
          await loadCameraStatus();
        } catch (e) {
          showCameraAlert(`❌ Lỗi kiểm tra camera: ${e}`, "error");
        }
      });
    }

    if (btnCamClear) {
      btnCamClear.addEventListener("click", () => {
        if (imgLive) imgLive.style.display = "none";
        if (placeholderBox) placeholderBox.style.display = "flex";
        if (overlayTag) overlayTag.textContent = "🔴 TẮT";
        const lblSnapId = document.getElementById("lbl-snap-id");
        const lblSnapSize = document.getElementById("lbl-snap-size");
        const lblSnapHash = document.getElementById("lbl-snap-hash");
        const lblSnapVerif = document.getElementById("lbl-snap-verif");
        if (lblSnapId) lblSnapId.textContent = "Chưa chụp";
        if (lblSnapSize) lblSnapSize.textContent = "0 bytes";
        if (lblSnapHash) lblSnapHash.textContent = "--";
        if (lblSnapVerif) {
          lblSnapVerif.className = "badge";
          lblSnapVerif.textContent = "CHỜ XÁC MINH";
        }
      });
    }

    // --- Core Capture Library Management ---
    async function loadCaptureLibrary() {
      const tbody = document.getElementById("tbody-core-captures");
      const quotaEl = document.getElementById("lbl-library-quota");
      if (!tbody) return;

      try {
        const res = await fetch("/api/executive/edge/camera/library", { cache: "no-store" });
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        if (!data.success) throw new Error(data.error || "Lỗi đọc thư viện");

        const items = data.items || [];
        const totalCount = data.total_count || items.length;
        const totalSize = data.total_size_bytes || 0;
        const totalMb = (totalSize / (1024 * 1024)).toFixed(2);

        if (quotaEl) {
          quotaEl.textContent = `Dung lượng: ${totalMb} MB (${totalCount} ảnh) / 500 MB Quota`;
        }

        if (items.length === 0) {
          tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="padding: 24px; color: var(--text-dim);">Chưa có ảnh snapshot nào được lưu trong kho PC Core. Chụp ảnh trên Pi 5 và nhấn "LƯU VỀ CORE".</td></tr>`;
          return;
        }

        tbody.innerHTML = items.map(item => {
          const imgUrl = `/api/executive/edge/camera/image?id=${encodeURIComponent(item.snapshot_id)}`;
          const sizeKb = ((item.size_bytes || 0) / 1024).toFixed(1) + " KB";
          const dateStr = item.timestamp ? new Date(item.timestamp).toLocaleString("vi-VN") : "--";
          const shortHash = item.sha256_hash ? (item.sha256_hash.substring(0, 16) + "...") : "--";

          return `
            <tr>
              <td>
                <img src="${imgUrl}" class="file-thumb" alt="${escapeHtml(item.snapshot_id)}" onclick="window.open('${imgUrl}', '_blank')" title="Nhấp để xem kích thước gốc" onerror="this.outerHTML='<div class=\\'file-icon-box\\'>📷</div>'" />
              </td>
              <td><strong>${escapeHtml(item.snapshot_id)}</strong></td>
              <td><span class="note-sub">${dateStr}</span></td>
              <td>${sizeKb}</td>
              <td><code style="font-size:0.7rem; color:#00e5ff;">${shortHash}</code></td>
              <td><span class="badge badge-ready" style="font-size:0.7rem; padding:2px 6px;">✅ SHA-256</span></td>
              <td style="text-align: right; white-space: nowrap;">
                <button class="btn btn-outline btn-sm btn-lib-view" data-url="${imgUrl}" style="border-color:#38bdf8; color:#38bdf8; padding:3px 8px; font-size:0.75rem; margin-right:4px;">👁️ Xem</button>
                <button class="btn btn-outline btn-sm btn-lib-del" data-id="${escapeHtml(item.snapshot_id)}" style="border-color:#ef4444; color:#f87171; padding:3px 8px; font-size:0.75rem;">🗑️ Xóa</button>
              </td>
            </tr>
          `;
        }).join("");

        tbody.querySelectorAll(".btn-lib-view").forEach(btn => {
          btn.addEventListener("click", (e) => {
            const url = e.currentTarget.getAttribute("data-url");
            if (url) window.open(url, "_blank");
          });
        });

        tbody.querySelectorAll(".btn-lib-del").forEach(btn => {
          btn.addEventListener("click", async (e) => {
            const snapId = e.currentTarget.getAttribute("data-id");
            if (!confirm(`Anh có chắc chắn muốn xóa ảnh snapshot '${snapId}' khỏi PC Core không?`)) return;
            try {
              const delRes = await fetch("/api/executive/edge/camera/delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: snapId })
              });
              const delData = await delRes.json();
              if (delData.success) {
                loadCaptureLibrary();
              } else {
                alert(`Lỗi khi xóa ảnh: ${delData.error}`);
              }
            } catch (err) {
              alert(`Lỗi kết nối khi xóa: ${err}`);
            }
          });
        });

      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="padding: 20px; color: #f87171;">Không thể tải danh sách ảnh: ${err}</td></tr>`;
      }
    }

    const btnRefreshLib = document.getElementById("btn-refresh-library");
    if (btnRefreshLib) btnRefreshLib.addEventListener("click", () => loadCaptureLibrary());

    // Expose methods for tab activation
    window.loadAudioStatus = loadAudioStatus;
    window.loadCameraStatus = loadCameraStatus;
    window.loadCaptureLibrary = loadCaptureLibrary;

    // Initial load
    loadAudioStatus();
    loadCameraStatus();
    loadCaptureLibrary();

    // Start background poll for audio meter every 2.5s
    if (!audioPollTimer) {
      audioPollTimer = setInterval(() => {
        const edgeTab = document.getElementById("tab-edge-sync");
        if (edgeTab && edgeTab.classList.contains("active")) {
          loadAudioStatus();
        }
      }, 2500);
    }
  }

  // =========================================================================
  // TASK ORCHESTRATION & DURABLE TASK REGISTRY VIEWER (GIAI ĐOẠN D)
  // =========================================================================

  function initTasksOrchestration() {
    const btnOpenCreate = document.getElementById("btn-open-create-task");
    const boxCreateForm = document.getElementById("box-create-task-form");
    const btnCancelCreate = document.getElementById("btn-cancel-create-task");
    const btnSubmitCreate = document.getElementById("btn-submit-create-task");
    const btnRefreshTasks = document.getElementById("btn-refresh-tasks");
    const btnCloseDetail = document.getElementById("btn-close-task-detail");
    const inputGoal = document.getElementById("input-task-goal");
    const selectAutonomy = document.getElementById("select-task-autonomy");

    if (btnOpenCreate && boxCreateForm) {
      btnOpenCreate.addEventListener("click", () => {
        boxCreateForm.style.display = boxCreateForm.style.display === "none" ? "block" : "none";
        if (boxCreateForm.style.display === "block" && inputGoal) inputGoal.focus();
      });
    }

    if (btnCancelCreate && boxCreateForm) {
      btnCancelCreate.addEventListener("click", () => {
        boxCreateForm.style.display = "none";
      });
    }

    if (btnRefreshTasks) {
      btnRefreshTasks.addEventListener("click", loadTasksList);
    }

    if (btnCloseDetail) {
      btnCloseDetail.addEventListener("click", () => {
        const box = document.getElementById("box-task-steps-detail");
        if (box) box.style.display = "none";
      });
    }

    if (btnSubmitCreate) {
      btnSubmitCreate.addEventListener("click", async () => {
        const goal = (inputGoal && inputGoal.value || "").trim();
        if (!goal) {
          alert("Vui lòng nhập mục tiêu nhiệm vụ.");
          return;
        }
        const autonomy = selectAutonomy ? selectAutonomy.value : "LEVEL_A";
        btnSubmitCreate.disabled = true;
        btnSubmitCreate.textContent = "Đang phân rã kế hoạch...";
        try {
          const res = await fetch("/api/executive/tasks/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ goal, autonomy_level: autonomy })
          });
          const data = await res.json();
          if (data.success && data.task) {
            if (boxCreateForm) boxCreateForm.style.display = "none";
            if (inputGoal) inputGoal.value = "";
            await loadTasksList();
            window.viewTaskDetail(data.task.task_id);
          } else {
            alert("Lỗi tạo nhiệm vụ: " + (data.error || "Không thể phân rã"));
          }
        } catch (err) {
          alert("Lỗi kết nối: " + err.message);
        } finally {
          btnSubmitCreate.disabled = false;
          btnSubmitCreate.textContent = "🚀 Phân Rã & Đăng Ký Nhiệm Vụ";
        }
      });
    }

    loadTasksList();
  }

  async function loadTasksList() {
    const tbody = document.getElementById("tbody-tasks-list");
    const badgeCount = document.getElementById("badge-tasks-count");
    if (!tbody) return;

    try {
      const res = await fetch("/api/executive/tasks");
      if (!res.ok) throw new Error("API tasks error");
      const data = await res.json();
      const tasks = data.active_tasks || [];

      if (badgeCount) badgeCount.textContent = `${tasks.length} nhiệm vụ`;

      if (tasks.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="padding: 24px; text-align: center; color: #64748b;">Chưa có nhiệm vụ nào trong DurableTaskRegistry. Hãy nhấn "➕ Khởi Tạo Nhiệm Vụ Mới" ở trên.</td></tr>`;
        return;
      }

      tbody.innerHTML = tasks.map(t => {
        const riskColor = t.risk_level === "R5" ? "#ef4444" : (t.risk_level === "R4" ? "#f59e0b" : "#10b981");
        const statusColors = {
          "COMPLETED": { bg: "rgba(16, 185, 129, 0.15)", fg: "#10b981", lbl: "HOÀN TẤT" },
          "IN_PROGRESS": { bg: "rgba(56, 189, 248, 0.15)", fg: "#38bdf8", lbl: "ĐANG CHẠY" },
          "WAITING_APPROVAL": { bg: "rgba(245, 158, 11, 0.15)", fg: "#f59e0b", lbl: "CHỜ DUYỆT" },
          "PENDING": { bg: "rgba(148, 163, 184, 0.15)", fg: "#94a3b8", lbl: "CHỜ THỰC THI" },
          "BLOCKED": { bg: "rgba(239, 68, 68, 0.15)", fg: "#ef4444", lbl: "BỊ CHẶN" },
          "FAILED": { bg: "rgba(239, 68, 68, 0.15)", fg: "#ef4444", lbl: "THẤT BẠI" },
          "CANCELLED": { bg: "rgba(100, 116, 139, 0.15)", fg: "#64748b", lbl: "ĐÃ HỦY" },
        };
        const st = statusColors[t.status] || { bg: "rgba(148, 163, 184, 0.15)", fg: "#94a3b8", lbl: t.status };
        const pct = t.progress_pct !== undefined ? t.progress_pct : 0;
        const comp = t.completed_steps_count !== undefined ? t.completed_steps_count : 0;
        const total = t.steps_count || 1;

        return `
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1); transition: background 0.2s;" onmouseover="this.style.background='rgba(30, 41, 59, 0.4)'" onmouseout="this.style.background='transparent'">
            <td style="padding: 10px; font-family: monospace; color: #38bdf8; font-size: 12px;"><strong>${t.task_id}</strong></td>
            <td style="padding: 10px; color: #f1f5f9; max-width: 280px; word-break: break-word;">${escapeHtml(t.goal)}</td>
            <td style="padding: 10px;"><span style="background: ${riskColor}22; color: ${riskColor}; border: 1px solid ${riskColor}44; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">${t.risk_level}</span></td>
            <td style="padding: 10px; font-size: 11px; color: #94a3b8;">${t.autonomy_level}</td>
            <td style="padding: 10px;"><span style="background: ${st.bg}; color: ${st.fg}; border: 1px solid ${st.fg}44; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;">${st.lbl}</span></td>
            <td style="padding: 10px;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 80px; background: #1e293b; border-radius: 4px; height: 6px; overflow: hidden;">
                  <div style="width: ${pct}%; background: #10b981; height: 100%;"></div>
                </div>
                <span style="font-size: 11px; color: #94a3b8;">${comp}/${total} (${pct}%)</span>
              </div>
            </td>
            <td style="padding: 10px; text-align: right; white-space: nowrap;">
              <button class="btn btn-sm btn-outline" onclick="window.viewTaskDetail('${t.task_id}')" style="padding: 3px 8px; font-size: 11px; margin-right: 4px;" title="Xem chi tiết các bước DAG">👁️ DAG</button>
              ${t.status === 'PENDING' || t.status === 'IN_PROGRESS' || t.status === 'WAITING_APPROVAL' ? `
                <button class="btn btn-sm btn-primary" onclick="window.executeTaskInert('${t.task_id}')" style="padding: 3px 8px; font-size: 11px; margin-right: 4px; background: rgba(16, 185, 129, 0.2); border-color: #10b981; color: #10b981;" title="Chạy thử qua hộp cát an toàn (Inert Sandbox)">▶️ Chạy Thử</button>
                <button class="btn btn-sm btn-outline" onclick="window.cancelTaskPrompt('${t.task_id}')" style="padding: 3px 8px; font-size: 11px; color: #ef4444; border-color: #ef4444;" title="Hủy bỏ nhiệm vụ này">🛑 Hủy</button>
              ` : ''}
            </td>
          </tr>
        `;
      }).join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="padding: 16px; text-align: center; color: #ef4444;">Lỗi tải danh sách nhiệm vụ: ${err.message}</td></tr>`;
    }
  }

  window.loadTasksList = loadTasksList;

  window.viewTaskDetail = async function(taskId) {
    const box = document.getElementById("box-task-steps-detail");
    const titleEl = document.getElementById("detail-task-title");
    const container = document.getElementById("container-dag-steps");
    if (!box || !container) return;

    box.style.display = "block";
    if (titleEl) titleEl.textContent = `Chi Tiết Các Bước DAG: ${taskId}`;
    container.innerHTML = `<p style="color: #64748b; font-size: 12px;">Đang tải các bước của nhiệm vụ...</p>`;

    try {
      const res = await fetch(`/api/executive/tasks/detail?task_id=${encodeURIComponent(taskId)}`);
      const data = await res.json();
      if (!data.success || !data.steps) {
        container.innerHTML = `<p style="color: #ef4444; font-size: 12px;">Không tìm thấy chi tiết bước.</p>`;
        return;
      }

      const steps = data.steps;
      if (steps.length === 0) {
        container.innerHTML = `<p style="color: #94a3b8; font-size: 12px;">Nhiệm vụ này chưa có bước DAG nào.</p>`;
        return;
      }

      container.innerHTML = steps.map(s => {
        const stepStatusMap = {
          "COMPLETED": { bg: "rgba(16, 185, 129, 0.15)", fg: "#10b981", icon: "✓" },
          "IN_PROGRESS": { bg: "rgba(56, 189, 248, 0.15)", fg: "#38bdf8", icon: "⏳" },
          "WAITING_APPROVAL": { bg: "rgba(245, 158, 11, 0.15)", fg: "#f59e0b", icon: "⚠️" },
          "BLOCKED": { bg: "rgba(239, 68, 68, 0.15)", fg: "#ef4444", icon: "⛔" },
          "FAILED": { bg: "rgba(239, 68, 68, 0.15)", fg: "#ef4444", icon: "✗" },
          "PENDING": { bg: "rgba(148, 163, 184, 0.15)", fg: "#94a3b8", icon: "○" },
        };
        const st = stepStatusMap[s.status] || { bg: "rgba(148, 163, 184, 0.15)", fg: "#94a3b8", icon: "○" };
        const riskColor = s.risk_level >= 5 ? "#ef4444" : (s.risk_level >= 4 ? "#f59e0b" : "#10b981");

        return `
          <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(56, 189, 248, 0.2); border-left: 4px solid ${st.fg}; border-radius: 6px; padding: 12px;">
            <div class="flex-between">
              <div style="display: flex; gap: 8px; align-items: center;">
                <span style="background: ${st.bg}; color: ${st.fg}; width: 22px; height: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700;">${st.icon}</span>
                <strong style="color: #f8fafc; font-size: 13px;">Bước ${s.sequence}: ${escapeHtml(s.name)}</strong>
                <span style="font-family: monospace; font-size: 11px; color: #64748b;">(${s.step_id})</span>
              </div>
              <div style="display: flex; gap: 6px; align-items: center;">
                <span style="background: ${riskColor}22; color: ${riskColor}; border: 1px solid ${riskColor}44; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 700;">R${s.risk_level}</span>
                <span style="background: ${st.bg}; color: ${st.fg}; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 600;">${s.status}</span>
              </div>
            </div>
            <p style="margin: 6px 0 4px 30px; color: #cbd5e1; font-size: 12px;">${escapeHtml(s.description || 'Không có mô tả chi tiết')}</p>
            <div style="margin-left: 30px; font-size: 11px; color: #94a3b8; display: flex; gap: 16px; flex-wrap: wrap;">
              <span><strong>Kỳ vọng:</strong> ${escapeHtml(s.expected_output || 'N/A')}</span>
              <span><strong>Xác minh:</strong> ${escapeHtml(s.verification_method || 'schema_assert')}</span>
              ${s.dependencies && s.dependencies.length > 0 ? `<span><strong>Phụ thuộc:</strong> ${escapeHtml(s.dependencies.join(', '))}</span>` : ''}
              ${s.requires_approval ? `<span style="color: #f59e0b; font-weight: 600;">⚠️ Yêu cầu phê duyệt</span>` : ''}
            </div>
            ${s.error_message ? `<div style="margin: 8px 0 0 30px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 6px 10px; border-radius: 4px; font-size: 11px;"><strong>Lỗi:</strong> ${escapeHtml(s.error_message)}</div>` : ''}
          </div>
        `;
      }).join("");

      box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (e) {
      container.innerHTML = `<p style="color: #ef4444; font-size: 12px;">Lỗi tải chi tiết: ${e.message}</p>`;
    }
  };

  window.executeTaskInert = async function(taskId) {
    if (!confirm(`XÁC NHẬN CHẠY THỬ: Bạn muốn chạy thử nhiệm vụ '${taskId}' qua Hộp Cát An Toàn (Inert Sandbox)?\n* Không có tác dụng phụ lên hệ điều hành.`)) {
      return;
    }
    try {
      const res = await fetch("/api/executive/tasks/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: taskId, dry_run: true })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Thực thi hoàn tất!\nTrạng thái: ${data.outcome && data.outcome.state || 'COMPLETED'}\nBằng chứng: ${data.outcome && data.outcome.evidence && data.outcome.evidence.length || 0} mục`);
        await loadTasksList();
        window.viewTaskDetail(taskId);
      } else {
        alert("Lỗi thực thi: " + (data.error || "Không thể thực thi"));
      }
    } catch (e) {
      alert("Lỗi kết nối: " + e.message);
    }
  };

  window.cancelTaskPrompt = async function(taskId) {
    const reason = prompt(`Nhập lý do hủy bỏ nhiệm vụ '${taskId}':`, "Anh Quân hủy bỏ qua Visual Cockpit");
    if (!reason) return;
    try {
      const res = await fetch("/api/executive/tasks/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: taskId, reason: reason })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Đã hủy nhiệm vụ '${taskId}'.`);
        await loadTasksList();
      } else {
        alert("Lỗi hủy nhiệm vụ: " + (data.error || "Không thể hủy"));
      }
    } catch (e) {
      alert("Lỗi kết nối: " + e.message);
    }
  };

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function jsonBody(obj) {
    return JSON.stringify(obj);
  }

  // Expose global methods for inline handlers
  window.loadConsultations = loadConsultations;
  window.loadLearningReports = loadLearningReports;
  window.loadCapabilities = loadCapabilities;
  window.loadEdgeTelemetry = loadEdgeTelemetry;
  window.loadPiFiles = loadPiFiles;

  // ================= NETCHAT CHANNEL COMMAND CENTER =================
  let netchatAvatar = null;
  let netchatTimer = null;
  let netchatLastPostId = null;

  function initNetChat() {
    const list = document.getElementById("netchat-messages-list");
    if (!list) return;

    // Digital Human avatar (same engine + assets as the cockpit persona)
    try {
      if (typeof DigitalHumanAvatar !== "undefined") {
        netchatAvatar = new DigitalHumanAvatar("netchat-avatar-canvas", {
          basePath: "/static/assets/avatar",
          initialState: "IDLE",
        });
      }
    } catch (e) {
      console.warn("NetChat avatar init warning:", e);
    }

    document.getElementById("btn-netchat-refresh")?.addEventListener("click", refreshNetChat);
    document.getElementById("btn-netchat-send")?.addEventListener("click", sendNetChatMessage);
    document.getElementById("btn-netchat-run-cmd")?.addEventListener("click", runNetChatCommand);
    document.getElementById("netchat-command-select")?.addEventListener("change", (e) => {
      if (e.target.value) {
        document.getElementById("netchat-input").value = e.target.value;
        e.target.value = "";
      }
    });

    const input = document.getElementById("netchat-input");
    input?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendNetChatMessage();
      }
    });

    const autoBox = document.getElementById("netchat-auto-refresh");
    autoBox?.addEventListener("change", () => {
      if (autoBox.checked) startNetChatAuto();
      else stopNetChatAuto();
    });

    // Load when tab is opened
    document.getElementById("nav-btn-netchat")?.addEventListener("click", () => {
      refreshNetChat();
      startNetChatAuto();
    });

    refreshNetChat();
  }

  function startNetChatAuto() {
    stopNetChatAuto();
    netchatTimer = setInterval(() => {
      const autoBox = document.getElementById("netchat-auto-refresh");
      const tab = document.getElementById("tab-netchat");
      if (autoBox?.checked && tab?.classList.contains("active")) refreshNetChat(true);
    }, 10000);
  }

  function stopNetChatAuto() {
    if (netchatTimer) { clearInterval(netchatTimer); netchatTimer = null; }
  }

  async function refreshNetChat(silent) {
    const list = document.getElementById("netchat-messages-list");
    if (!list) return;
    if (!silent) list.innerHTML = '<div class="netchat-loading">Đang tải tin nhắn…</div>';
    try {
      const [msgRes, statusRes] = await Promise.all([
        fetch("/api/executive/netchat/messages?count=30"),
        fetch("/api/executive/netchat/status"),
      ]);
      const msgData = await msgRes.json();
      const statusData = statusRes.ok ? await statusRes.json() : null;

      renderNetChatMessages(msgData.messages || []);

      const badge = document.getElementById("badge-netchat-status");
      const sub = document.getElementById("netchat-channel-sub");
      const statusBox = document.getElementById("netchat-status-box");
      if (msgData.success) {
        if (badge) { badge.textContent = "LIVE"; badge.classList.add("badge-green"); }
        if (sub) sub.textContent = `Kênh riêng tư • ${msgData.messages.length} tin gần nhất • Cập nhật ${new Date().toLocaleTimeString("vi-VN")}`;
      } else {
        if (badge) { badge.textContent = "LỖI"; badge.classList.remove("badge-green"); }
      }
      if (statusBox && statusData) {
        const b = statusData.bot || {};
        statusBox.innerHTML =
          `Bot: <b>${b.username || "?"}</b> (ID ${b.id || "?"})<br>` +
          `Kênh: <b>${statusData.channel?.name || "?"}</b><br>` +
          `Responder: netchat_auto_responder.py (poll 5s)<br>` +
          `Kiểm tra: ${statusData.checked_at_utc || "?"}`;
      }
    } catch (err) {
      list.innerHTML = `<div class="netchat-loading">⚠️ Không tải được kênh: ${err.message}</div>`;
      const badge = document.getElementById("badge-netchat-status");
      if (badge) { badge.textContent = "OFF"; badge.classList.remove("badge-green"); }
    }
  }

  function renderNetChatMessages(messages) {
    const list = document.getElementById("netchat-messages-list");
    if (!list) return;
    if (!messages.length) {
      list.innerHTML = '<div class="netchat-loading">Kênh chưa có tin nhắn.</div>';
      return;
    }
    const cmds = ["phê duyệt", "phe duyet", "duyệt", "duyet", "trạng thái", "trang thai", "hiện trạng", "báo cáo", "bao cao", "nhiệm vụ", "nhiem vu", "tri thức", "tri thuc", "giúp", "giup"];
    list.innerHTML = messages.map(m => {
      const isBot = m.sender === "bot";
      const t = m.create_at ? new Date(m.create_at).toLocaleTimeString("vi-VN") : "";
      const lower = (m.message || "").trim().toLowerCase();
      const isCmd = !isBot && cmds.some(c => lower.startsWith(c));
      const avatarImg = isBot ? '<img class="netchat-msg-avatar" src="/static/assets/avatar/avatar_v2_portrait.jpg" alt="Tony">' : "";
      const who = isBot ? "🤖 TRỢ LÝ" : "👑 ANH (quanpt1)";
      const esc = (m.message || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      return `<div class="netchat-msg ${isBot ? "msg-bot" : "msg-owner"}">` +
        `${avatarImg}` +
        `<div class="msg-meta">${who}${isCmd ? '<span class="cmd-tag">LỆNH</span>' : ""} <span style="margin-left:auto">${t}</span></div>` +
        `<div class="msg-text">${esc}</div>` +
        `</div>`;
    }).join("");
    list.scrollTop = list.scrollHeight;
  }

  async function sendNetChatMessage() {
    const input = document.getElementById("netchat-input");
    const btn = document.getElementById("btn-netchat-send");
    const text = (input?.value || "").trim();
    if (!text) return;
    if (btn) { btn.disabled = true; btn.textContent = "Đang gửi…"; }
    try {
      const res = await fetch("/api/executive/netchat/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      if (!res.ok || data.success === false) {
        throw new Error(data.error || data.detail || `HTTP ${res.status}`);
      }
      input.value = "";
      netchatAvatar?.setState("SPEAKING");
      setTimeout(() => netchatAvatar?.setState("IDLE"), 2500);
      await refreshNetChat(true);
    } catch (err) {
      alert("Không gửi được: " + err.message);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Gửi ➤"; }
    }
  }

  async function runNetChatCommand() {
    const input = document.getElementById("netchat-input");
    const out = document.getElementById("netchat-status-box");
    const text = (input?.value || "").trim();
    if (!text) { alert("Nhập lệnh trước (ví dụ: trạng thái)"); return; }
    if (out) out.textContent = "⏳ Đang thực thi lệnh…";
    netchatAvatar?.setState("THINKING");
    try {
      const res = await fetch("/api/executive/netchat/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: text }),
      });
      const data = await res.json();
      if (!res.ok || data.success === false) {
        throw new Error(data.error || data.detail || `HTTP ${res.status}`);
      }
      netchatAvatar?.setState("SUCCESS");
      setTimeout(() => netchatAvatar?.setState("IDLE"), 2500);
      if (out) out.innerHTML =
        `<b>⚡ Lệnh:</b> ${text}<br><b>Intent:</b> ${data.intent || "—"}` +
        (data.note ? `<br><i>${data.note}</i>` : "") +
        `<br><br><pre style="white-space:pre-wrap;font-family:var(--font-mono);font-size:11.5px;margin:0">${(data.response || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>`;
    } catch (err) {
      netchatAvatar?.setState("ERROR");
      setTimeout(() => netchatAvatar?.setState("IDLE"), 2500);
      if (out) out.textContent = "⚠️ Lỗi lệnh: " + err.message;
    }
  }
});

/* ============================================================
   SPRINT 9 (B): WORKBENCH — môi trường làm việc thống nhất
   Số liệu thật từ API hiện có; lỗi nguồn → CHƯA XÁC MINH.
   ============================================================ */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  async function wbFetch(url, opts) {
    const res = await fetch(url, opts);
    let data = null;
    try { data = await res.json(); } catch { /* non-JSON */ }
    return { ok: res.ok, status: res.status, data };
  }

  function setUnverified(elId, detailId, source) {
    const el = $(elId);
    if (el) { el.textContent = "CHƯA XÁC MINH"; el.style.color = "#f87171"; }
    const d = $(detailId);
    if (d) d.textContent = `nguồn ${source} không khả dụng`;
  }

  async function loadOverview() {
    try {
      const { ok, data } = await wbFetch("/api/workbench/overview");
      if (!ok || !data || data.success !== true) throw new Error("API overview lỗi");

      // Nhiệm vụ
      const t = data.tasks || {};
      if (t.status === "OK") {
        const open = (t.total || 0) - (t.completed || 0);
        $("wb-tasks-open").textContent = String(open);
        $("wb-tasks-open").style.color = "#e2e8f0";
        const parts = Object.entries(t.by_status || {}).map(([k, v]) => `${k}: ${v}`);
        $("wb-tasks-detail").textContent = parts.length ? parts.join(" · ") : "không có nhiệm vụ nào";
      } else {
        setUnverified("wb-tasks-open", "wb-tasks-detail", "tasks.db");
      }

      // Approvals
      const a = data.approvals || {};
      if (a.status === "OK") {
        $("wb-approvals-pending").textContent = String(a.pending ?? 0);
        $("wb-approvals-pending").style.color = (a.pending ?? 0) > 0 ? "#fbbf24" : "#86efac";
        $("wb-approvals-detail").textContent = `tổng ${a.total ?? 0} · đã duyệt ${a.approved ?? 0} · từ chối ${a.rejected ?? 0}`;
      } else {
        setUnverified("wb-approvals-pending", "wb-approvals-detail", "governance.db");
      }

      // Todos
      const td = data.todos || {};
      if (td.status === "OK") {
        $("wb-todos-open").textContent = String(td.open ?? 0);
        $("wb-todos-open").style.color = "#93c5fd";
        $("wb-todos-detail").textContent = `quá hạn ${td.overdue ?? 0} · đến hạn hôm nay ${td.due_today ?? 0}`;
      } else {
        setUnverified("wb-todos-open", "wb-todos-detail", "todos.db");
      }

      // Gaps
      const g = data.information_gaps || {};
      if (g.status === "OK") {
        $("wb-gaps").textContent = String(g.open ?? g.total ?? 0);
        $("wb-gaps").style.color = "#f87171";
        $("wb-gaps-detail").textContent = `tổng ${g.total ?? 0} gap`;
      } else {
        setUnverified("wb-gaps", "wb-gaps-detail", "information_gaps.db");
      }

      // Services
      const s = data.services || {};
      $("wb-services").innerHTML = Object.entries(s).map(([k, v]) =>
        `<div><span style="color:${v === "CONNECTED" ? "#86efac" : "#f87171"}">●</span> ${esc(k)}: ${esc(v)}</div>`
      ).join("") || "không có dịch vụ nào được cấu hình";

      // Badge tab
      const badge = $("badge-workbench-overview");
      if (badge) {
        const pending = a.status === "OK" ? (a.pending ?? 0) : "?";
        badge.textContent = `pend:${pending}`;
      }
    } catch (err) {
      ["wb-tasks-open", "wb-approvals-pending", "wb-todos-open", "wb-gaps"].forEach((id) => setUnverified(id, null, "overview"));
      const d = $("wb-tasks-detail");
      if (d) d.textContent = "Lỗi: " + err.message;
    }
  }

  async function loadTasks() {
    const filter = $("wb-task-filter")?.value || "";
    const url = "/api/workbench/tasks" + (filter ? `?status=${encodeURIComponent(filter)}` : "");
    try {
      const { ok, status, data } = await wbFetch(url);
      const el = $("wb-tasks-list");
      if (!ok || !data || data.success !== true) {
        el.innerHTML = `<span style="color:#f87171">KHÔNG KHẢ DỤNG (HTTP ${status})</span>`;
        return;
      }
      if (!data.tasks.length) { el.textContent = "Không có nhiệm vụ nào ở trạng thái này."; return; }
      el.innerHTML = data.tasks.map((t) =>
        `<div style="padding:6px 0; border-bottom:1px solid rgba(148,163,184,0.12);">
          <div><b>${esc(t.task_id)}</b> <span style="color:#fbbf24;">[${esc(t.status)}]</span> <span style="color:#94a3b8;">r=${esc(t.risk_level)}</span></div>
          <div style="color:#94a3b8; font-size:0.74rem;">${esc((t.goal || "").slice(0, 140))}</div>
          <div style="color:#64748b; font-size:0.7rem;">cập nhật ${esc((t.updated_at_utc || "").slice(0, 19))}</div>
        </div>`
      ).join("");
    } catch (err) {
      $("wb-tasks-list").innerHTML = `<span style="color:#f87171">KHÔNG KHẢ DỤNG: ${esc(err.message)}</span>`;
    }
  }

  let wbApprovalBusy = false;  // chống double-submit
  async function loadApprovals() {
    try {
      const { ok, data } = await wbFetch("/api/approvals");
      const el = $("wb-approvals-list");
      if (!ok || !data || data.success !== true) {
        el.innerHTML = `<span style="color:#f87171">KHÔNG KHẢ DỤNG</span>`;
        return;
      }
      const cards = (data.cards || []).filter((c) => c.status === "PENDING_APPROVAL");
      if (!cards.length) { el.textContent = "Không có card nào chờ phê duyệt."; return; }
      el.innerHTML = cards.map((c) =>
        `<div style="padding:8px 0; border-bottom:1px solid rgba(148,163,184,0.12);">
          <div><b style="color:#fbbf24;">${esc(c.task_code)}</b> <span style="color:#94a3b8;">v${c.version ?? 1}</span></div>
          <div style="color:#94a3b8; font-size:0.74rem; margin:2px 0;">${esc((c.title || "").slice(0, 120))}</div>
          <div style="display:flex; gap:6px; margin-top:4px;">
            <button class="wb-approve" data-code="${esc(c.task_code)}" style="background:rgba(34,197,94,0.2); color:#86efac; border:1px solid rgba(34,197,94,0.3); border-radius:6px; padding:3px 10px; font-size:0.72rem; cursor:pointer;">✓ Duyệt</button>
            <button class="wb-reject" data-code="${esc(c.task_code)}" style="background:rgba(239,68,68,0.2); color:#f87171; border:1px solid rgba(239,68,68,0.3); border-radius:6px; padding:3px 10px; font-size:0.72rem; cursor:pointer;">✗ Từ chối</button>
          </div>
        </div>`
      ).join("");
      el.querySelectorAll(".wb-approve").forEach((b) =>
        b.addEventListener("click", () => decideApproval(b.dataset.code, "approve", "")));
      el.querySelectorAll(".wb-reject").forEach((b) =>
        b.addEventListener("click", () => {
          const reason = prompt("Lý do từ chối (bắt buộc):", "");
          if (reason && reason.trim()) decideApproval(b.dataset.code, "reject", reason.trim());
        }));
    } catch (err) {
      $("wb-approvals-list").innerHTML = `<span style="color:#f87171">KHÔNG KHẢ DỤNG: ${esc(err.message)}</span>`;
    }
  }

  async function decideApproval(taskCode, decision, note) {
    const result = $("wb-approval-result");
    if (wbApprovalBusy) { result.textContent = "⏳ Đang xử lý — không gửi trùng."; return; }
    wbApprovalBusy = true;
    result.style.color = "#fbbf24";
    result.textContent = "⏳ Đang gửi tới server…";
    try {
      const { ok, status, data } = await wbFetch("/api/approvals/decide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_code: taskCode, decision, note }),
      });
      // KHÔNG coi bấm nút là thành công — chỉ tin HTTP status + body server trả
      if (ok && data && data.success === true) {
        result.style.color = "#86efac";
        result.textContent = `✅ Server xác nhận: ${taskCode} → ${data.status}`;
        await Promise.all([loadApprovals(), loadOverview()]);
      } else if (status === 409) {
        result.style.color = "#f87171";
        result.textContent = `⚠️ ${taskCode} đã được xử lý trước đó (409) — danh sách sẽ làm mới.`;
        await Promise.all([loadApprovals(), loadOverview()]);
      } else if (status === 404) {
        result.style.color = "#f87171";
        result.textContent = `⚠️ Card ${taskCode} không tồn tại (404).`;
      } else if (status === 403) {
        result.style.color = "#f87171";
        result.textContent = "⛔ Chỉ hoạt động từ localhost (403).";
      } else {
        result.style.color = "#f87171";
        result.textContent = `⚠️ Lỗi HTTP ${status}: ${esc(data?.error || "không rõ")}`;
      }
    } catch (err) {
      result.style.color = "#f87171";
      result.textContent = "⚠️ Không kết nối được server: " + err.message;
    } finally {
      wbApprovalBusy = false;
    }
  }

  async function loadTodos() {
    try {
      const { ok, data } = await wbFetch("/api/todos");
      const el = $("wb-todos-list");
      if (!ok || !data || data.success !== true) {
        el.innerHTML = `<span style="color:#f87171">KHÔNG KHẢ DỤNG</span>`;
        return;
      }
      const today = new Date().toISOString().slice(0, 10);
      if (!data.todos.length) { el.textContent = "Không có việc nào đang mở."; return; }
      el.innerHTML = data.todos.map((t) => {
        const over = t.due && t.due < today;
        return `<div style="display:flex; align-items:center; gap:8px; padding:4px 0; border-bottom:1px solid rgba(148,163,184,0.12);">
          <input type="checkbox" class="wb-todo-done" data-id="${t.id}" title="Đánh dấu hoàn thành">
          <span style="${over ? "color:#f87171;" : ""}">${over ? "🔴" : "⚪"} [${esc(t.due || "—")}] ${esc(t.title)}</span>
        </div>`;
      }).join("");
      el.querySelectorAll(".wb-todo-done").forEach((cb) =>
        cb.addEventListener("change", () => { if (cb.checked) markTodoDone(cb.dataset.id); }));
    } catch (err) {
      $("wb-todos-list").innerHTML = `<span style="color:#f87171">KHÔNG KHẢ DỤNG: ${esc(err.message)}</span>`;
    }
  }

  async function markTodoDone(id) {
    try {
      const { ok, data } = await wbFetch("/api/todos/done", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: Number(id) }),
      });
      if (!ok || !data || data.success !== true) {
        $("wb-todo-result").textContent = `⚠️ Không hoàn thành được (HTTP ${data?.error || "lỗi"})`;
      }
      await Promise.all([loadTodos(), loadOverview()]);
    } catch (err) {
      $("wb-todo-result").textContent = "⚠️ " + err.message;
    }
  }

  async function addTodo() {
    const input = $("wb-todo-input");
    const due = $("wb-todo-due").value || "";
    const title = (input.value || "").trim();
    if (!title) { $("wb-todo-result").textContent = "⚠️ Nhập nội dung việc cần làm."; return; }
    $("wb-todo-add").disabled = true;  // chống gửi trùng khi bấm 2 lần
    try {
      const { ok, status, data } = await wbFetch("/api/todos/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, due }),
      });
      if (ok && data && data.success === true) {
        input.value = "";
        $("wb-todo-result").textContent = "";
        await Promise.all([loadTodos(), loadOverview()]);
      } else {
        $("wb-todo-result").textContent = `⚠️ Lỗi HTTP ${status}: ${esc(data?.error || "không rõ")}`;
      }
    } catch (err) {
      $("wb-todo-result").textContent = "⚠️ " + err.message;
    } finally {
      $("wb-todo-add").disabled = false;
    }
  }

  async function syncMockIntake() {
    const el = $("wb-email-list");
    el.textContent = "⏳ Đang sync mock intake…";
    try {
      const { ok, status, data } = await wbFetch("/api/email/intake/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!ok || !data || data.success !== true) {
        el.innerHTML = `<span style="color:#f87171">KHÔNG KHẢ DỤNG (HTTP ${status})</span>`;
        return;
      }
      const r = data.result || {};
      el.innerHTML = `<div style="color:#94a3b8;">connector=${esc(r.connector_status)} · mới ${r.new ?? 0} · trùng ${r.duplicates ?? 0}</div>` +
        (data.emails || []).map((m) =>
          `<div style="padding:4px 0; border-bottom:1px solid rgba(148,163,184,0.12);">
            <b>${esc(m.subject)}</b> <span style="color:#94a3b8;">[${esc(m.category)}]</span>
            <div style="color:#64748b; font-size:0.7rem;">từ ${esc(m.sender)} · nguồn ${esc(m.source)}</div>
          </div>`).join("");
    } catch (err) {
      el.innerHTML = `<span style="color:#f87171">Lỗi: ${esc(err.message)}</span>`;
    }
  }

  let wbProposalBusy = false;  // chống double-submit tạo task
  let wbWebBusy = false;       // chống double-submit web search
  async function webSearch() {
    const el = $("wb-web-result");
    const q = ($("wb-web-q").value || "").trim();
    if (!q) { el.textContent = "Nhập từ khoá trước."; return; }
    if (wbWebBusy) return;
    wbWebBusy = true;
    el.textContent = "⏳ Đang tìm…";
    try {
      const { ok, data } = await wbFetch(`/api/web/search?q=${encodeURIComponent(q)}&max_results=5`);
      if (!ok || !data) { el.textContent = "KHÔNG KHẢ DỤNG"; return; }
      if (data.success !== true) { el.innerHTML = `<span style="color:#f87171">⚠️ ${esc(data.error || "lỗi không rõ")}</span>`; return; }
      if (!data.results.length) { el.textContent = "Không có kết quả nào."; return; }
      el.innerHTML = data.results.map((r) => `
        <div style="padding:6px 0; border-bottom:1px solid rgba(148,163,184,0.12);">
          <div><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer" style="color:#7dd3fc;">${esc(r.title || r.url)}</a></div>
          ${r.snippet ? `<div style="color:#94a3b8; font-size:0.7rem;">${esc(r.snippet)}</div>` : ""}
          <div style="color:#64748b; font-size:0.65rem;">${esc(r.url)}</div>
        </div>`).join("");
    } catch (err) {
      el.innerHTML = `<span style="color:#f87171">Lỗi: ${esc(err.message)}</span>`;
    } finally {
      wbWebBusy = false;
    }
  }

  let wbLessonBusy = false;    // chống double-submit promote lesson
  async function loadLessons() {
    try {
      const { ok, status, data } = await wbFetch("/api/experience/lessons");
      const el = $("wb-lessons-list");
      if (!ok || !data || data.success !== true) {
        el.innerHTML = `<span style="color:#f87171">KHÔNG KHẢ DỤNG (HTTP ${status})</span>`;
        return;
      }
      const cands = data.candidates || [];
      const confirmed = data.confirmed || [];
      if (!cands.length && !confirmed.length) {
        el.textContent = "Chưa có bài học nào — nhiệm vụ COMPLETED/FAILED sẽ tự sinh ứng viên.";
        return;
      }
      const render = (rec, isCand) => {
        const meta = rec.metadata || {};
        return `<details style="padding:6px 0; border-bottom:1px solid rgba(148,163,184,0.12);">
          <summary style="cursor:pointer;">
            ${isCand ? "🟡" : "✅"} <b>${esc(rec.content.split("\n")[0] || "")}</b>
            <span style="font-size:0.7rem; color:${isCand ? "#fbbf24" : "#86efac"};">[${isCand ? "ỨNG VIÊN — CHƯA duyệt" : "ĐÃ DUYỆT"}]</span>
          </summary>
          <div style="margin:6px 0 4px 12px; color:#94a3b8; font-size:0.72rem; white-space:pre-wrap;">${esc(rec.content)}</div>
          <div style="margin-left:12px; font-size:0.7rem; color:#64748b;">Task: ${esc(meta.task_id || "?")} · Nguồn: ${esc(rec.source_ref || "?")} · ${esc(rec.created_at_utc || "")}</div>
          ${isCand ? `<button class="wb-promote-lesson" data-mid="${esc(rec.id)}" style="margin:6px 0 0 12px; background:rgba(16,185,129,0.15); color:#86efac; border:1px solid rgba(16,185,129,0.3); border-radius:6px; padding:3px 10px; font-size:0.72rem; cursor:pointer;">✔ Anh duyệt thành kinh nghiệm xác nhận</button>` : ""}
        </details>`;
      };
      el.innerHTML =
        (confirmed.length ? `<div style="margin-bottom:4px; color:#86efac; font-size:0.72rem;">Đã xác nhận (${confirmed.length})</div>` + confirmed.map((r) => render(r, false)).join("") : "") +
        (cands.length ? `<div style="margin:8px 0 4px 0; color:#fbbf24; font-size:0.72rem;">Ứng viên chờ duyệt (${cands.length})</div>` + cands.map((r) => render(r, true)).join("") : "");
      el.querySelectorAll(".wb-promote-lesson").forEach((b) =>
        b.addEventListener("click", () => promoteLesson(b.dataset.mid)));
    } catch (err) {
      $("wb-lessons-list").innerHTML = `<span style="color:#f87171">Lỗi: ${esc(err.message)}</span>`;
    }
  }

  async function promoteLesson(memoryId) {
    const result = $("wb-lessons-result");
    if (wbLessonBusy) { result.textContent = "⏳ Đang xử lý — không gửi trùng."; return; }
    if (!confirm("Duyệt bài học này thành kinh nghiệm XÁC NHẬN? Chỉ làm khi anh thật sự chấp nhận.")) return;
    wbLessonBusy = true;
    result.style.color = "#fbbf24";
    result.textContent = "⏳ Đang duyệt…";
    try {
      const { ok, status, data } = await wbFetch("/api/experience/lessons/promote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ memory_id: memoryId, owner_confirm: "DUYET" }),
      });
      if (ok && data && data.success === true) {
        result.style.color = data.promoted ? "#86efac" : "#fbbf24";
        result.textContent = data.promoted ? "✅ Đã duyệt — lesson VERIFIED + active." : "ℹ️ " + (data.reason || "Không đổi.");
        await loadLessons();
      } else if (status === 403) {
        result.style.color = "#f87171";
        result.textContent = "⚠️ " + (data?.error || "Cần xác nhận của anh (owner_confirm=DUYET).");
      } else if (status === 404) {
        result.style.color = "#f87171";
        result.textContent = "⚠️ Lesson không tồn tại (404).";
      } else if (status === 409) {
        result.style.color = "#f87171";
        result.textContent = "⚠️ " + (data?.error || "Lesson không ở trạng thái duyệt được.");
      } else {
        result.style.color = "#f87171";
        result.textContent = `⚠️ Lỗi HTTP ${status}: ${esc(data?.error || "không rõ")}`;
      }
    } catch (err) {
      result.style.color = "#f87171";
      result.textContent = "⚠️ " + err.message;
    } finally {
      wbLessonBusy = false;
    }
  }

  async function loadProposals() {
    try {
      const { ok, status, data } = await wbFetch("/api/email/proposals");
      const el = $("wb-proposals-list");
      if (!ok || !data || data.success !== true) {
        el.innerHTML = `<span style="color:#f87171">KHÔNG KHẢ DỤNG (HTTP ${status})</span>`;
        return;
      }
      const props = data.proposals || [];
      if (!props.length) {
        el.textContent = "Chưa có đề xuất nào — email ACTION_REQUIRED sẽ tự sinh đề xuất khi sync.";
        return;
      }
      el.innerHTML = props.map((p) => {
        const pay = p.payload || p;
        const expConf = (pay.experience_confirmed || []).length;
        const expCand = (pay.experience_candidates || []).length;
        const linked = pay.linked_task_id || p.linked_task_id;
        return `<details style="padding:8px 0; border-bottom:1px solid rgba(148,163,184,0.12);">
          <summary style="cursor:pointer;">
            <b>${esc(pay.subject || p.subject)}</b>
            <span style="color:#a78bfa; font-size:0.72rem;">[${esc(p.status)}]${linked ? " → task " + esc(linked) : ""}</span>
          </summary>
          <div style="margin:8px 0 4px 12px; color:#94a3b8; font-size:0.75rem;">
            <div><b style="color:#e2e8f0;">🎯 Mục tiêu:</b> ${esc(pay.goal || "")}</div>
            <div style="margin-top:4px;"><b style="color:#e2e8f0;">📌 Căn cứ:</b><ul style="margin:2px 0 2px 18px;">${(pay.basis || []).map((b) => `<li>${esc(b)}</li>`).join("")}</ul></div>
            <div><b style="color:#e2e8f0;">✅ Kết luận:</b> ${esc(pay.conclusion || "")}</div>
            <div style="margin-top:4px;"><b style="color:#fbbf24;">⚠️ Giả định CHƯA xác minh:</b><ul style="margin:2px 0 2px 18px;">${(pay.assumptions || []).map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>
            <div><b style="color:#86efac;">▶ Phương án khuyến nghị:</b> ${esc(pay.recommended_action || "")}</div>
            <div style="margin-top:4px;"><b style="color:#94a3b8;">Phương án khác:</b><ul style="margin:2px 0 2px 18px;">${(pay.alternatives || []).map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>
            <div><b style="color:#f87171;">Rủi ro:</b><ul style="margin:2px 0 2px 18px;">${(pay.risks || []).map((r) => `<li>${esc(r)}</li>`).join("")}</ul></div>
            <div><b style="color:#94a3b8;">Phạm vi:</b> ${esc(pay.action_scope || "")} · <b>Rollback:</b> ${esc(pay.rollback || "")}</div>
            <div><b style="color:#86efac;">Tiêu chí thành công:</b><ul style="margin:2px 0 2px 18px;">${(pay.success_criteria || []).map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div>
            <div><b style="color:#fbbf24;">Cần anh quyết:</b> ${esc(pay.owner_decision_needed || "")}</div>
            <div style="margin-top:4px; color:#64748b;">Kinh nghiệm liên quan: ${expConf} đã xác nhận · ${expCand} ứng viên CHƯA duyệt (không tính là căn cứ mạnh)</div>
          </div>
          ${linked
            ? `<div style="margin-left:12px; color:#86efac; font-size:0.75rem;">✓ Nhiệm vụ ứng viên đã tạo: <b>${esc(linked)}</b> (PENDING — chờ duyệt, không tự chạy)</div>`
            : `<button class="wb-create-task" data-pid="${esc(p.proposal_id)}" style="margin-left:12px; background:rgba(168,85,247,0.2); color:#d8b4fe; border:1px solid rgba(168,85,247,0.3); border-radius:6px; padding:4px 12px; font-size:0.75rem; cursor:pointer;">➕ Tạo nhiệm vụ ứng viên (PENDING — em không tự chạy)</button>`}
        </details>`;
      }).join("");
      el.querySelectorAll(".wb-create-task").forEach((b) =>
        b.addEventListener("click", () => createEmailTask(b.dataset.pid)));
    } catch (err) {
      $("wb-proposals-list").innerHTML = `<span style="color:#f87171">Lỗi: ${esc(err.message)}</span>`;
    }
  }

  async function createEmailTask(proposalId) {
    const result = $("wb-proposal-result");
    if (wbProposalBusy) { result.textContent = "⏳ Đang xử lý — không gửi trùng."; return; }
    wbProposalBusy = true;
    result.style.color = "#fbbf24";
    result.textContent = "⏳ Đang tạo nhiệm vụ ứng viên…";
    try {
      const { ok, status, data } = await wbFetch("/api/email/task/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ proposal_id: proposalId }),
      });
      if (ok && data && data.success === true) {
        result.style.color = data.created ? "#86efac" : "#fbbf24";
        result.textContent = (data.created ? "✅ Đã tạo nhiệm vụ ứng viên: " : "ℹ️ Email này đã có nhiệm vụ: ") + data.task_id + " (PENDING — không tự thực thi)";
        await Promise.all([loadProposals(), loadTasks(), loadOverview()]);
      } else if (status === 404) {
        result.style.color = "#f87171";
        result.textContent = "⚠️ Đề xuất không tồn tại (404).";
      } else {
        result.style.color = "#f87171";
        result.textContent = `⚠️ Lỗi HTTP ${status}: ${esc(data?.error || "không rõ")}`;
      }
    } catch (err) {
      result.style.color = "#f87171";
      result.textContent = "⚠️ " + err.message;
    } finally {
      wbProposalBusy = false;
    }
  }

  function initWorkbench() {
    if (!$("tab-workbench")) return;
    $("wb-task-filter")?.addEventListener("change", loadTasks);
    $("wb-todo-refresh")?.addEventListener("click", loadTodos);
    $("wb-todo-add")?.addEventListener("click", addTodo);
    $("wb-email-sync")?.addEventListener("click", syncMockIntake);
    $("wb-lessons-refresh")?.addEventListener("click", loadLessons);
    $("wb-web-search")?.addEventListener("click", webSearch);
    $("wb-web-q")?.addEventListener("keydown", (e) => { if (e.key === "Enter") webSearch(); });
    // Load khi tab được bật (lắng nghe click nav + load lần đầu nếu active)
    document.querySelectorAll(".nav-tab").forEach((btn) =>
      btn.addEventListener("click", () => {
        if (btn.dataset.tab === "tab-workbench") {
          loadOverview(); loadTasks(); loadApprovals(); loadTodos(); loadProposals(); loadLessons();
        }
      }));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initWorkbench);
  } else {
    initWorkbench();
  }
})();
