/* ============================================================
   CHERRY INTELLIGENCE MATURITY DASHBOARD — Tab (Phase 3, 12/11)
   File RIÊNG — không đụng executive.js (R2 của Phase 0 report).
   READ-ONLY: chỉ GET 3 API, 0 POST, không tự đánh giá.
   Nguyên tắc: N/A-insufficient, không điểm tổng, RED FLAG >5%,
   BLOCKED khi thiếu — INCONCLUSIVE không tự thành PASS.
   ============================================================ */
(function () {
  "use strict";

  var API = {
    scorecard: "/api/intelligence/scorecard",
    audit: "/api/intelligence/audit-status",
    errors: "/api/intelligence/errors?status=OPEN",
  };

  function el(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function fmtVal(kpi) {
    if (kpi.status === "MEASURED" && kpi.value != null) {
      if (kpi.unit === "ratio" && kpi.value <= 1.0001) {
        return Math.round(kpi.value * 1000) / 10 + "%";
      }
      return String(Math.round(kpi.value * 1000) / 1000);
    }
    if (kpi.status === "BLOCKED") return "BLOCKED";
    return "NOT EVALUATED";
  }

  function badgeHtml(kpi) {
    if (kpi.red_flag) return '<span class="intel-badge intel-badge-redflag">RED FLAG ▼</span>';
    switch (kpi.status) {
      case "MEASURED": return '<span class="intel-badge intel-badge-measured">MEASURED</span>';
      case "BLOCKED": return '<span class="intel-badge intel-badge-blocked">BLOCKED</span>';
      case "AUDIT_REQUIRED": return '<span class="intel-badge intel-badge-auditreq">AUDIT REQUIRED</span>';
      default: return '<span class="intel-badge intel-badge-noteval">NOT EVALUATED</span>';
    }
  }

  function sparkline(points) {
    if (!points || points.length < 2) return "";
    var vals = points.map(function (p) { return p.value; });
    var min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
    var span = (max - min) || 1;
    var w = 90, h = 22;
    var coords = points.map(function (p, i) {
      var x = (i / (points.length - 1)) * (w - 4) + 2;
      var y = h - 3 - ((p.value - min) / span) * (h - 6);
      return x.toFixed(1) + "," + y.toFixed(1);
    });
    var hasFlag = points.some(function (p) { return p.red_flag; });
    return '<svg class="intel-spark' + (hasFlag ? " intel-spark-red" : "") +
      '" viewBox="0 0 ' + w + " " + h + '" width="' + w + '" height="' + h + '">' +
      '<polyline fill="none" stroke="currentColor" stroke-width="1.5" points="' +
      coords.join(" ") + '"/></svg>';
  }

  function renderKpis(data) {
    var grid = el("intel-kpi-grid");
    if (!grid) return;
    var html = "";
    data.kpis.forEach(function (kpi) {
      var trend = (data.trend && data.trend[String(kpi.kpi_id)]) || null;
      html += '<div class="intel-kpi' + (kpi.red_flag ? " intel-kpi-redflag" : "") + '">' +
        '<div class="intel-kpi-head">' +
        '<span class="intel-kpi-name">' + kpi.kpi_id + " · " + esc(kpi.kpi_name) + "</span>" +
        badgeHtml(kpi) + "</div>" +
        '<div class="intel-kpi-value' +
        (kpi.status === "MEASURED" ? " intel-val-measured" : " intel-val-na") + '">' +
        esc(fmtVal(kpi)) + "</div>" +
        '<div class="intel-kpi-meta">' +
        (kpi.sample_size != null ? "n=" + esc(kpi.sample_size) : "") +
        (kpi.confidence ? " · CI [" + kpi.confidence[0] + "–" + kpi.confidence[1] + "]" : "") +
        (kpi.status === "MEASURED" ? "" : " · thiếu dataset/benchmark") +
        "</div>" +
        (trend ? '<div class="intel-kpi-trend">' + sparkline(trend) + "</div>" : "") +
        "</div>";
    });
    grid.innerHTML = html;
  }

  function loadScorecard() {
    fetch(API.scorecard)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.success) throw new Error(data.error || "scorecard fail");
        var cov = data.coverage || { measured: 0, total: 12 };
        var stateEl = el("intel-eval-state");
        if (stateEl) stateEl.textContent = (data.eval_state || "UNKNOWN").replace(/_/g, " ");
        var covEl = el("intel-coverage");
        if (covEl) covEl.textContent = "Coverage đo được: " + cov.measured + "/" + cov.total + " KPI";
        var lastEl = el("intel-last-eval");
        if (lastEl) lastEl.textContent = data.last_eval_utc
          ? "Đánh giá gần nhất: " + data.last_eval_utc.replace("T", " ").slice(0, 16) + " UTC"
          : "Chưa có benchmark chính thức nào";
        renderKpis(data);
      })
      .catch(function (e) {
        var grid = el("intel-kpi-grid");
        if (grid) grid.innerHTML = '<div class="intel-error">Lỗi tải scorecard: ' + esc(e.message) + "</div>";
      });
  }

  function loadAudit() {
    fetch(API.audit)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var elx = el("intel-audit-state");
        if (elx) {
          elx.textContent = (data.audit_state || "UNKNOWN").replace(/_/g, " ");
          elx.className = "intel-badge intel-badge-noteval";
        }
        var d = el("intel-audit-detail");
        if (d) d.textContent = data.detail || "";
      })
      .catch(function () {});
  }

  function loadErrors() {
    fetch(API.errors)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var box = el("intel-errors-list");
        if (!box) return;
        if (!data.errors || !data.errors.length) {
          box.innerHTML = '<div class="intel-empty">Không có lỗi OPEN.</div>';
          return;
        }
        box.innerHTML = data.errors.map(function (e) {
          return '<div class="intel-err' + (e.severity === "HIGH" ? " intel-err-high" : "") + '">' +
            '<div class="intel-err-title">' + esc(e.error_id) + " — " + esc(e.title) + "</div>" +
            '<div class="intel-err-meta">' + esc(e.source) + " · chu trình: " +
            esc(e.cycle_state) + " · severity: " + esc(e.severity) + "</div></div>";
        }).join("");
      })
      .catch(function () {});
  }

  // API công khai cho switchTab hook (executive.html gọi window.loadIntelligence)
  window.loadIntelligence = function () {
    loadScorecard();
    loadAudit();
    loadErrors();
  };

  // Tự load nếu tab đang active lúc trang mở (deep-link ?tab=tab-intelligence)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      if (location.search.indexOf("tab-intelligence") >= 0 && window.loadIntelligence) window.loadIntelligence();
    });
  } else if (location.search.indexOf("tab-intelligence") >= 0) {
    window.loadIntelligence();
  }
})();
