/*
 * CHERRY AVATAR PROTOCOL — Sprint 1: Unified Emotion Protocol (14/11/2026)
 * =========================================================================
 * Nguồn sự thật DUY NHẤT cho state/emotion giữa PC dashboard (8765/8766) và
 * Pi5 kiosk (8768). Cả 2 nền tảng nạp FILE NÀY (cùng md5) TRƯỚC
 * avatar_engine.js. Bản copy local trong engine chỉ là fallback khẩn cấp.
 *
 * Card: TASK-EMBODIMENT-S1 (APPROVED, auth owner_desktop_chat_directive).
 * Canonical = giá trị PC dashboard 13/11 (owner đã duyệt giao diện PC).
 */
(function (root) {
  "use strict";

  var PROTOCOL_VERSION = "s1_1411";

  // ===== 22 STATE_CONFIGS (canonical — khớp PC dashboard 13/11) =====
  var STATE_CONFIGS = {
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
    SURPRISED: { name: "SURPRISED (NGẠC NHIÊN)", auraColor: "#38bdf8", haloSpeed: 0.09, eyes: "open", smile: "natural", symbol: "😮", defaultTone: "SURPRISED" },
    CURIOUS: { name: "CURIOUS (TÒ MÒ)", auraColor: "#22d3ee", haloSpeed: 0.055, eyes: "thinking", smile: "natural", symbol: "🤔", defaultTone: "CURIOUS" },
    APOLOGETIC: { name: "APOLOGETIC (XIN LỖI)", auraColor: "#f472b6", haloSpeed: 0.03, eyes: "open", smile: "closed", symbol: "🙏", defaultTone: "APOLOGETIC" },
    PROUD: { name: "PROUD (TỰ HÀO)", auraColor: "#facc15", haloSpeed: 0.07, eyes: "open", smile: "happy", symbol: "🌟", defaultTone: "PROUD" },
  };

  // ===== 11 EMOTION_PRESETS (canonical — khớp PC dashboard 13/11) =====
  var EMOTION_PRESETS = {
    NEUTRAL: { browLift: 0.0, browTilt: 0.0, browInward: 0.0, browAsymmetric: 0.0, eyeSquint: 0.05, gazeX: 0.0, gazeY: 0.0, glintPulse: 1.0, smileBoost: 0.08 },
    WARM_GREETING: { browLift: 3.5, browTilt: 2.2, browInward: 0.0, browAsymmetric: 0.0, eyeSquint: 0.38, gazeX: 0.0, gazeY: 0.0, glintPulse: 1.35, smileBoost: 0.40 },
    ANALYTICAL_THINKING: { browLift: -2.5, browTilt: -3.2, browInward: 2.5, browAsymmetric: 1.2, eyeSquint: 0.20, gazeX: 1.8, gazeY: -1.4, glintPulse: 1.05, smileBoost: 0.05 },
    SERIOUS_ALERT: { browLift: -4.5, browTilt: -4.8, browInward: 3.5, browAsymmetric: 0.0, eyeSquint: 0.0, gazeX: 0.0, gazeY: 0.5, glintPulse: 0.85, smileBoost: -0.30 },
    CONFIDENT_SUCCESS: { browLift: 4.2, browTilt: 1.5, browInward: 0.0, browAsymmetric: 0.0, eyeSquint: 0.42, gazeX: 0.0, gazeY: 0.0, glintPulse: 1.50, smileBoost: 0.45 },
    CONSULTATIVE_INQUIRING: { browLift: 2.2, browTilt: 2.8, browInward: 0.5, browAsymmetric: 2.8, eyeSquint: 0.22, gazeX: 0.0, gazeY: -0.6, glintPulse: 1.25, smileBoost: 0.22 },
    CURIOUS: { browLift: 4.8, browTilt: 3.6, browInward: 0.0, browAsymmetric: 3.4, eyeSquint: 0.12, gazeX: 1.2, gazeY: 0.8, glintPulse: 1.45, smileBoost: 0.18 },
    APOLOGETIC: { browLift: -1.8, browTilt: 2.6, browInward: 2.2, browAsymmetric: 1.6, eyeSquint: 0.30, gazeX: 0.0, gazeY: 1.2, glintPulse: 0.90, smileBoost: -0.10 },
    PATIENT_WAITING: { browLift: 1.2, browTilt: 1.0, browInward: 0.0, browAsymmetric: 0.0, eyeSquint: 0.25, gazeX: 0.0, gazeY: 0.3, glintPulse: 1.10, smileBoost: 0.12 },
    PROUD: { browLift: 3.0, browTilt: 0.8, browInward: 0.0, browAsymmetric: 0.0, eyeSquint: 0.45, gazeX: 0.0, gazeY: -0.4, glintPulse: 1.55, smileBoost: 0.38 },
    SURPRISED: { browLift: 7.5, browTilt: 0.0, browInward: 0.0, browAsymmetric: 0.0, eyeSquint: 0.0, gazeX: 0.0, gazeY: 0.0, glintPulse: 1.70, smileBoost: 0.05 },
  };

  // Alias state cũ/khác → state canonical 22.
  var STATE_ALIASES = {
    ONLINE: "IDLE",
    READY: "IDLE",
    STANDBY: "IDLE",
    SPEAK: "SPEAKING",
    TALKING: "SPEAKING",
    LISTEN: "LISTENING",
    HEARING: "LISTENING",
    WAIT: "WAITING_FOR_OWNER",
    WAITING: "WAITING_FOR_OWNER",
    PENDING: "WAITING_FOR_OWNER",
    FAIL: "ERROR",
    CRITICAL: "BLOCKED",
    BOOTING: "RECONNECTING",
    CONNECTING: "RECONNECTING",
  };

  function normalizeState(state) {
    var s = String(state || "").trim().toUpperCase();
    if (!s) return "IDLE";
    if (STATE_CONFIGS[s]) return s;
    if (STATE_ALIASES[s]) return STATE_ALIASES[s];
    return "IDLE";
  }

  /*
   * Extractor cảm xúc tiếng Việt HỢP NHẤT (PC + Pi5):
   * - Chạy regex CÓ dấu trên text gốc (PC) VÀ regex KHÔNG dấu trên text đã
   *   strip dấu (Pi5, chuẩn hóa NFD + đ→d — xử lý text TTS/telemetry không dấu).
   * - Thứ tự category theo PC (APOLOGETIC ưu tiên trước SERIOUS_ALERT).
   * - Fix "chuy" (typo Pi5 không bao giờ khớp "chu y") → dùng đúng "chu y".
   */
  function extractVietnameseEmotion(text) {
    if (!text || typeof text !== "string") return "NEUTRAL";
    var raw = text.toLowerCase();
    var stripped = raw;
    try {
      stripped = raw.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d");
    } catch (_) { /* giữ raw nếu môi trường không có normalize */ }
    function has(reRaw, reStripped) {
      if (reRaw && reRaw.test(raw)) return true;
      if (reStripped && reStripped.test(stripped)) return true;
      return false;
    }
    // 0. Apology trước alert: "xin lỗi anh, em gặp sự cố" là xin lỗi (13/11)
    if (has(/xin lỗi|chia buồn|rất tiếc|đáng tiếc|gây phiền|thừa nhận|mất thời gian|tạm biệt|không may/,
            /xin loi|chia buon|rat tiec|dang tiec|gay phien|thua nhan|mat thoi gian|tam biet|khong may/)) return "APOLOGETIC";
    // 1. Alert / Warning / Safety Block
    if (has(/cảnh báo|chú ý|lưu ý|nguy hiểm|rủi ro|không được|chặn|thất bại|lỗi|bất thường|sự cố|dừng|khẩn cấp|nghiêm cấm/,
            /canh bao|chu y|luu y|nguy hiem|rui ro|khong duoc|chan|that bai|loi |bi loi|bat thuong|su co|dung |khan cap|nghiem cam/)) return "SERIOUS_ALERT";
    // 2. Success
    if (has(/hoàn thành|thành công|chính xác|đạt chuẩn|vượt qua|tốt đẹp|100%|xuất sắc|hoàn hảo|thắng lợi/,
            /hoan thanh|thanh cong|chinh xac|dat chuan|vuot qua|tot dep|100%|xuat sac|hoan hao|thang loi/)) return "CONFIDENT_SUCCESS";
    // 3. Analytical
    if (has(/phân tích|dữ liệu|kết quả|nghiên cứu|thuật toán|kiến trúc|thông số|đo lường|logic|thống kê|chi tiết|báo cáo|kiểm tra|xác nhận|chỉ số/,
            /phan tich|du lieu|ket qua|nghien cuu|thuat toan|kien truc|thong so|do luong|logic|thong ke|chi tiet|bao cao|kiem tra|xac nhan|chi so/)) return "ANALYTICAL_THINKING";
    // 4. Consultative
    if (has(/kính trình|đề xuất|chờ anh|xin ý kiến|phê duyệt|chỉ đạo|chờ xác nhận|tham vấn/,
            /inh trinh|de xuat|cho anh|xin kien|phe duyet|chi dao|cho xac nhan|tham van/)) return "CONSULTATIVE_INQUIRING";
    // 5. Warm greeting
    if (has(/chào|xin chào|dạ|vâng|rất vui|hân hạnh|sẵn sàng|chúc|em đây|vâng ạ|em nghe|tuyệt vời|cảm ơn/,
            /chao|xin chao|da |vang |rat vui|han hanh|san sang|chuc|em day|em nghe|tuyet voi|cam on/)) return "WARM_GREETING";
    // 6. Surprise (hợp nhất PC 6 + Pi5 1b)
    if (has(/bất ngờ|ngạc nhiên|ọe|trời ơi|ổn quá|wow|hoàn toàn mới|lần đầu tiên|khám phá/,
            /bat ngo|ngac nhien|dang le|khong mong doi|khan|dot xuat|mau than|choang|on ao/)) return "SURPRISED";
    // 7. Curious
    if (has(/tại sao|như thế nào|thế nào|làm sao|giải thích|cho em hỏi|thắc mắc|tò mò|muốn biết|hỏi anh|câu hỏi/,
            /tai sao|nhu the nao|the nao|lam sao|giai thich|cho em hoi|thac mac|to mo|muon biet|hoi anh|cau hoi/)) return "CURIOUS";
    // 8. Proud
    if (has(/tự hào|cải thiện|tiến bộ|tối ưu|nâng cấp|hoàn thiện|phát triển|nhất quán|ổn định|học được|nắm bắt/,
            /tu hao|cai thien|tien bo|toi uu|nang cap|hoan thien|phat trien|nhat quan|on dinh|hoc duoc|nam bat/)) return "PROUD";
    return "NEUTRAL";
  }

  /*
   * IPC envelope validator — Sprint 1 (MASTER PROMPT V4.0 §3.7).
   * Rules: timestamp skew ≤ maxSkewMs; expiry không quá hạn; event_id không
   * trùng (duplicate suppression); sequence tăng monotonic theo platform
   * (lệch lùi = OUT_OF_ORDER, tiến ≤ tolerance coi như mất gói chấp nhận).
   * ctx: { seen: Object<string,true>, lastSeq: Object<string,number>,
   *        nowMs, maxSkewMs (default 30000), seqTolerance (default 0) }
   * Mutates ctx (seen/lastSeq) CHỈ khi hợp lệ.
   */
  function validateEnvelope(ev, ctx) {
    if (!ev || typeof ev !== "object") return { ok: false, reason: "MISSING_ENVELOPE" };
    ctx = ctx || {};
    var nowMs = ctx.nowMs != null ? ctx.nowMs : Date.now();
    var maxSkewMs = ctx.maxSkewMs != null ? ctx.maxSkewMs : 30000;
    var seqTolerance = ctx.seqTolerance != null ? ctx.seqTolerance : 0;
    var seen = ctx.seen || (ctx.seen = {});
    var lastSeq = ctx.lastSeq || (ctx.lastSeq = {});

    var eventId = ev.event_id;
    if (!eventId) return { ok: false, reason: "MISSING_FIELD:event_id" };
    if (seen[eventId]) return { ok: false, reason: "DUPLICATE" };

    var ts = Number(ev.timestamp);
    if (!isFinite(ts) || ts <= 0) return { ok: false, reason: "MISSING_FIELD:timestamp" };
    if (Math.abs(nowMs - ts) > maxSkewMs) return { ok: false, reason: "STALE" };

    if (ev.expiry != null) {
      var exp = Number(ev.expiry);
      if (isFinite(exp) && exp > 0 && nowMs > exp) return { ok: false, reason: "EXPIRED" };
    }

    var platform = ev.platform || "UNKNOWN";
    if (ev.sequence != null) {
      var seq = Number(ev.sequence);
      if (!isFinite(seq)) return { ok: false, reason: "MISSING_FIELD:sequence" };
      var prev = lastSeq[platform];
      if (prev != null && seq <= prev - seqTolerance) {
        return { ok: false, reason: "OUT_OF_ORDER" };
      }
    }

    // Hợp lệ → ghi nhận (duplicate + sequence tracking).
    seen[eventId] = true;
    var kept = 0;
    for (var k in seen) {
      if (++kept > 512) delete seen[k];
    }
    if (ev.sequence != null && isFinite(Number(ev.sequence))) {
      var s = Number(ev.sequence);
      if (lastSeq[platform] == null || s > lastSeq[platform]) lastSeq[platform] = s;
    }
    return { ok: true, reason: "OK" };
  }

  var api = {
    version: PROTOCOL_VERSION,
    STATE_CONFIGS: STATE_CONFIGS,
    EMOTION_PRESETS: EMOTION_PRESETS,
    STATE_ALIASES: STATE_ALIASES,
    normalizeState: normalizeState,
    extractVietnameseEmotion: extractVietnameseEmotion,
    validateEnvelope: validateEnvelope,
  };

  root.CHERRY_AVATAR_PROTOCOL = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api; // node (test)
  }
})(typeof window !== "undefined" ? window : globalThis);
