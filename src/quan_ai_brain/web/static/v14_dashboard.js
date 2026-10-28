/* ================= V14 — UI INTEGRATION & VISUALIZATION DASHBOARD ================= */
/* Temporal Memory, Cross-Modal Linking, Quality & Maintenance UI */

(function initV14UI() {
  "use strict";
  
  const $ = (id) => document.getElementById(id);
  const esc = (s) => {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&")
      .replace(/</g, "<")
      .replace(/>/g, ">")
      .replace(/"/g, """)
      .replace(/'/g, "'");
  };

  // ============================================================================
  // TEMPORAL MEMORY UI
  // ============================================================================
  
  async function loadTemporalStats() {
    const container = $("temporal-stats");
    if (!container) return;
    
    try {
      const res = await fetch("/api/memory/temporal/stats");
      const data = await res.json();
      
      container.innerHTML = `
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:10px; margin-bottom:15px;">
          <div style="background:#1e293b; padding:12px; border-radius:8px; border:1px solid #334155;">
            <div style="font-size:0.7rem; color:#94a3b8;">Total KU</div>
            <div style="font-size:1.5rem; font-weight:700; color:#93c5fd;">${esc(data.total_kus || 0)}</div>
          </div>
          <div style="background:#1e293b; padding:12px; border-radius:8px; border:1px solid #334155;">
            <div style="font-size:0.7rem; color:#94a3b8;">Avg Freshness</div>
            <div style="font-size:1.5rem; font-weight:700; color:#4ade80;">${esc((data.avg_freshness * 100).toFixed(1) || 0)}%</div>
          </div>
          <div style="background:#1e293b; padding:12px; border-radius:8px; border:1px solid #334155;">
            <div style="font-size:0.7rem; color:#94a3b8;">Avg Confidence</div>
            <div style="font-size:1.5rem; font-weight:700; color:#fbbf24;">${esc((data.avg_confidence * 100).toFixed(1) || 0)}%</div>
          </div>
          <div style="background:#1e293b; padding:12px; border-radius:8px; border:1px solid #334155;">
            <div style="font-size:0.7rem; color:#94a3b8;">Expired</div>
            <div style="font-size:1.5rem; font-weight:700; color:#f87171;">${esc(data.expired_count || 0)}</div>
          </div>
        </div>
      `;
    } catch (err) {
      container.innerHTML = `<div style="color:#f87171; font-size:0.8rem;">Lỗi tải: ${esc(err.message)}</div>`;
    }
  }

  async function renderFreshnessHeatmap() {
    const container = $("temporal-heatmap");
    if (!container) return;
    
    try {
      const res = await fetch("/api/memory/temporal/scores?limit=50");
      const data = await res.json();
      
      const scores = data.scores || [];
      if (scores.length === 0) {
        container.innerHTML = `<div style="color:#64748b; font-size:0.8rem;">Không có dữ liệu</div>`;
        return;
      }
      
      const heatmap = scores.map(s => {
        const color = s.freshness_score >= 0.7 ? "#4ade80" : 
                      s.freshness_score >= 0.4 ? "#fbbf24" : "#f87171";
        return `
          <div style="display:flex; align-items:center; gap:8px; padding:6px 8px; margin-bottom:4px; background:#1e293b; border-radius:6px;">
            <div style="width:12px; height:12px; border-radius:50%; background:${color};"></div>
            <div style="flex:1; font-size:0.72rem; color:#e2e8f0;">${esc(s.statement || "")}</div>
            <div style="font-size:0.7rem; color:#94a3b8; min-width:50px; text-align:right;">${esc((s.freshness_score * 100).toFixed(0))}%</div>
          </div>
        `;
      }).join("");
      
      container.innerHTML = heatmap;
    } catch (err) {
      container.innerHTML = `<div style="color:#f87171; font-size:0.8rem;">Lỗi: ${esc(err.message)}</div>`;
    }
  }

  // ============================================================================
  // CROSS-MODAL LINKING UI
  // ============================================================================
  
  let currentContext = null;
  
  async function loadContext() {
    const panel = $("context-panel");
    if (!panel) return;
    
    try {
      const res = await fetch("/api/memory/context/current");
      const data = await res.json();
      currentContext = data.context;
      
      panel.innerHTML = `
        <div style="display:flex; gap:8px; margin-bottom:10px; flex-wrap:wrap;">
          <input id="context-project" placeholder="Project" value="${esc(currentContext?.project || "")}" 
                 style="flex:1; min-width:120px; background:#1e293b; color:#e2e8f0; border:1px solid #334155; border-radius:6px; padding:6px 10px; font-size:0.75rem;">
          <input id="context-task" placeholder="Task" value="${esc(currentContext?.task || "")}"
                 style="flex:1; min-width:120px; background:#1e293b; color:#e2e8f0; border:1px solid #334155; border-radius:6px; padding:6px 10px; font-size:0.75rem;">
          <input id="context-user" placeholder="User" value="${esc(currentContext?.user || "")}"
                 style="flex:1; min-width:120px; background:#1e293b; color:#e2e8f0; border:1px solid #334155; border-radius:6px; padding:6px 10px; font-size:0.75rem;">
          <button id="btn-set-context" style="background:#2563eb; color:#fff; border:none; border-radius:6px; padding:6px 12px; font-size:0.75rem; cursor:pointer;">Set Context</button>
          <button id="btn-clear-context" style="background:#475569; color:#fff; border:none; border-radius:6px; padding:6px 12px; font-size:0.75rem; cursor:pointer;">Clear</button>
        </div>
        <div style="font-size:0.7rem; color:#94a3b8;">
          <b>Current:</b> ${currentContext ? 
            `project=${esc(currentContext.project || "—")}, task=${esc(currentContext.task || "—")}, user=${esc(currentContext.user || "—")}` : 
            "None"}
        </div>
      `;
      
      // Wire buttons
      $("btn-set-context")?.addEventListener("click", async () => {
        const project = $("context-project").value.trim();
        const task = $("context-task").value.trim();
        const user = $("context-user").value.trim();
        
        await fetch("/api/memory/context/set", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project, task, user })
        });
        await loadContext();
      });
      
      $("btn-clear-context")?.addEventListener("click", async () => {
        await fetch("/api/memory/context/clear", { method: "POST" });
        await loadContext();
      });
    } catch (err) {
      panel.innerHTML = `<div style="color:#f87171; font-size:0.8rem;">Lỗi: ${esc(err.message)}</div>`;
    }
  }

  async function performContextualSearch() {
    const query = $("contextual-search-input")?.value.trim();
    if (!query) return;
    
    const resultsContainer = $("contextual-search-results");
    if (!resultsContainer) return;
    
    resultsContainer.innerHTML = `<div style="color:#94a3b8; font-size:0.75rem;">Đang tìm...</div>`;
    
    try {
      const res = await fetch(`/api/memory/retrieve/contextual?query=${encodeURIComponent(query)}&top_k=10`);
      const data = await res.json();
      const results = data.results || [];
      
      if (results.length === 0) {
        resultsContainer.innerHTML = `<div style="color:#64748b; font-size:0.75rem;">Không tìm thấy kết quả</div>`;
        return;
      }
      
      const html = results.map(r => {
        const relevanceColor = r.relevance_score >= 0.7 ? "#4ade80" : 
                               r.relevance_score >= 0.4 ? "#fbbf24" : "#f87171";
        const contextColor = r.context_match_score >= 0.7 ? "#4ade80" : 
                             r.context_match_score >= 0.4 ? "#fbbf24" : "#f87171";
        
        return `
          <div style="border:1px solid #334155; border-radius:8px; padding:10px; margin-bottom:8px; background:#0f172a;">
            <div style="font-size:0.75rem; color:#e2e8f0; margin-bottom:6px;">${esc(r.statement || "")}</div>
            <div style="display:flex; gap:12px; font-size:0.68rem; color:#94a3b8;">
              <span style="color:${relevanceColor};">Relevance: ${esc((r.relevance_score * 100).toFixed(0))}%</span>
              <span style="color:${contextColor};">Context: ${esc((r.context_match_score * 100).toFixed(0))}%</span>
              <span>Combined: ${esc((r.combined_score * 100).toFixed(0))}%</span>
            </div>
            <div style="font-size:0.68rem; color:#64748b; margin-top:4px;">${esc(r.explanation || "")}</div>
          </div>
        `;
      }).join("");
      
      resultsContainer.innerHTML = html;
    } catch (err) {
      resultsContainer.innerHTML = `<div style="color:#f87171; font-size:0.75rem;">Lỗi: ${esc(err.message)}</div>`;
    }
  }

  // ============================================================================
  // QUALITY & MAINTENANCE UI
  // ============================================================================
  
  async function loadQualityDashboard() {
    const container = $("quality-dashboard");
    if (!container) return;
    
    try {
      const res = await fetch("/api/memory/quality/metrics");
      const data = await res.json();
      const metrics = data.metrics || {};
      
      const total = metrics.total_kus || 0;
      const high = metrics.high_quality_count || 0;
      const medium = metrics.medium_quality_count || 0;
      const low = metrics.low_quality_count || 0;
      
      // Simple pie chart using CSS conic-gradient
      const highPct = total > 0 ? (high / total * 100) : 0;
      const mediumPct = total > 0 ? (medium / total * 100) : 0;
      const lowPct = total > 0 ? (low / total * 100) : 0;
      
      container.innerHTML = `
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:15px;">
          <div style="background:#1e293b; padding:14px; border-radius:8px; border:1px solid #334155;">
            <h4 style="margin:0 0 10px 0; font-size:0.8rem; color:#94a3b8;">Quality Distribution</h4>
            <div style="display:flex; align-items:center; gap:15px;">
              <div style="width:80px; height:80px; border-radius:50%; background:conic-gradient(
                #4ade80 0 ${highPct}%,
                #fbbf24 ${highPct}% ${highPct + mediumPct}%,
                #f87171 ${highPct + mediumPct}% 100%
              );"></div>
              <div style="font-size:0.7rem;">
                <div style="color:#4ade80;">● High: ${esc(high)} (${esc(highPct.toFixed(1))}%)</div>
                <div style="color:#fbbf24;">● Medium: ${esc(medium)} (${esc(mediumPct.toFixed(1))}%)</div>
                <div style="color:#f87171;">● Low: ${esc(low)} (${esc(lowPct.toFixed(1))}%)</div>
              </div>
            </div>
          </div>
          
          <div style="background:#1e293b; padding:14px; border-radius:8px; border:1px solid #334155;">
            <h4 style="margin:0 0 10px 0; font-size:0.8rem; color:#94a3b8;">Averages</h4>
            <div style="font-size:0.72rem; color:#e2e8f0;">
              <div>Quality: <b style="color:#93c5fd;">${esc((metrics.average_quality * 100).toFixed(1) || 0)}%</b></div>
              <div>Confidence: <b style="color:#fbbf24;">${esc((metrics.average_confidence * 100).toFixed(1) || 0)}%</b></div>
              <div>Freshness: <b style="color:#4ade80;">${esc((metrics.average_freshness * 100).toFixed(1) || 0)}%</b></div>
              <div>Verification: <b style="color:#a78bfa;">${esc((metrics.average_verification * 100).toFixed(1) || 0)}%</b></div>
            </div>
          </div>
        </div>
      `;
    } catch (err) {
      container.innerHTML = `<div style="color:#f87171; font-size:0.8rem;">Lỗi: ${esc(err.message)}</div>`;
    }
  }

  async function loadLowQualityList() {
    const container = $("low-quality-list");
    if (!container) return;
    
    try {
      const res = await fetch("/api/memory/quality/low-quality?threshold=0.4&limit=20");
      const data = await res.json();
      const kus = data.kus || [];
      
      if (kus.length === 0) {
        container.innerHTML = `<div style="color:#4ade80; font-size:0.75rem;">Tất cả KU đều có chất lượng tốt!</div>`;
        return;
      }
      
      const html = kus.map(k => `
        <div style="border:1px solid #334155; border-radius:6px; padding:8px; margin-bottom:6px; background:#1e293b;">
          <div style="font-size:0.72rem; color:#e2e8f0;">${esc(k.statement || "")}</div>
          <div style="display:flex; gap:12px; font-size:0.68rem; color:#94a3b8; margin-top:4px;">
            <span>Overall: <b style="color:#f87171;">${esc((k.overall * 100).toFixed(0))}%</b></span>
            <span>Conf: ${esc((k.confidence * 100).toFixed(0))}%</span>
            <span>Fresh: ${esc((k.freshness * 100).toFixed(0))}%</span>
            <span>Verif: ${esc((k.verification * 100).toFixed(0))}%</span>
          </div>
        </div>
      `).join("");
      
      container.innerHTML = html;
    } catch (err) {
      container.innerHTML = `<div style="color:#f87171; font-size:0.75rem;">Lỗi: ${esc(err.message)}</div>`;
    }
  }

  async function runMaintenance() {
    const btn = $("btn-run-maintenance");
    if (!btn) return;
    
    btn.disabled = true;
    btn.textContent = "⏳ Đang chạy...";
    
    try {
      const res = await fetch("/api/memory/maintenance/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      const data = await res.json();
      
      if (data.success) {
        const result = data.result || {};
        btn.textContent = `✅ Done: Archived ${result.archived_count || 0}, Decayed ${result.decayed_count || 0}`;
        await loadQualityDashboard();
        await loadLowQualityList();
      } else {
        btn.textContent = "❌ Lỗi";
      }
    } catch (err) {
      btn.textContent = "❌ Lỗi";
    }
    
    setTimeout(() => { btn.disabled = false; btn.textContent = "🔄 Run Maintenance"; }, 3000);
  }

  // ============================================================================
  // INIT
  // ============================================================================
  
  function wireEvents() {
    $("btn-run-maintenance")?.addEventListener("click", runMaintenance);
    $("contextual-search-btn")?.addEventListener("click", performContextualSearch);
    
    // Enter key for search
    $("contextual-search-input")?.addEventListener("keypress", (e) => {
      if (e.key === "Enter") performContextualSearch();
    });
  }

  async function loadAll() {
    await Promise.all([
      loadTemporalStats(),
      renderFreshnessHeatmap(),
      loadContext(),
      loadQualityDashboard(),
      loadLowQualityList()
    ]);
  }

  // Initialize
  wireEvents();
  loadAll();
  
  // Reload on tab switch
  document.querySelectorAll(".nav-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.tab === "tab-v14-dashboard") {
        setTimeout(loadAll, 150);
      }
    });
  });
  
  if (document.querySelector(".nav-tab.active")?.dataset.tab === "tab-v14-dashboard") {
    setTimeout(loadAll, 150);
  }
})();