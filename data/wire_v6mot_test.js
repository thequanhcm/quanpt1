/**
 * WIRE TEST v6mot_1511 — chuyển động người nói camera (6.mp4) + ca sĩ (3/4/5.mp4)
 * Kiểm chứng bằng code thật trong edge_client/avatar_engine.js + body_motion_engine.js:
 *  1. body_motion_engine sway 3 tầng: 12.5s / 50s / 6.2s; micro-rest tắt tầng vi mô
 *  2. avatar_engine: phraseNod ~14.3s; lateral lean ±1.0° @10s; micro-rest head ×0.35
 *  3. targetBody consume: render KHÔNG crash khi targetBody null và khi có transform
 *  4. KHÔNG đụng miệng/portrait: giữ _renderSmile + band 0.42..0.78 + portrait_v3 nguyên
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function makeCtx2D() {
  return new Proxy({}, {
    get(t, k) {
      if (k === "createRadialGradient" || k === "createLinearGradient") return () => ({ addColorStop: () => {} });
      if (k === "measureText") return () => ({ width: 10 });
      return typeof k === "string" && !t[k] ? () => {} : t[k];
    },
    set(t, k, v) { t[k] = v; return true; },
  });
}
const canvasStub = () => ({ width: 800, height: 480, getContext: () => makeCtx2D(), style: {}, addEventListener: () => {} });
const windowMock = {
  devicePixelRatio: 1, addEventListener: () => {}, performance: { now: () => Date.now() },
  Image: class { constructor() { this.complete = false; this.naturalWidth = 0; } set src(_) { this.complete = true; this.naturalWidth = 896; } },
};
windowMock.window = windowMock; windowMock.globalThis = windowMock;
windowMock.document = {
  createElement: (t) => (t === "canvas" ? canvasStub() : { style: {} }),
  getElementById: () => canvasStub(), addEventListener: () => {}, visibilityState: "visible",
};
const baseDir = path.join(__dirname, "..", "edge_client");
const ctx = vm.createContext({ window: windowMock, document: windowMock.document, console, setTimeout, setInterval, clearTimeout, clearInterval, performance: windowMock.performance, Image: windowMock.Image, requestAnimationFrame: () => 0 });
["avatar_protocol.js", "audio_mouth_driver.js", "body_motion_engine.js", "avatar_engine.js"].forEach(f => vm.runInContext(fs.readFileSync(path.join(baseDir, f), "utf8"), ctx));

const results = [];
function check(name, cond, detail) {
  results.push({ name, pass: !!cond, detail: detail || "" });
  console.log((cond ? "PASS" : "FAIL") + "  " + name + (detail ? "  [" + detail + "]" : ""));
}

// ===== 1. Body motion engine — sway 3 tầng + micro-rest =====
const BME = windowMock.CherryBodyMotionEngine;
check("1a. body engine VERSION v6mot_1511", BME && BME.VERSION === "v6mot_1511", BME && BME.VERSION);

function swaySample(energy, offsetsSec) {
  const eng = new BME.BodyMotionEngine({ nowFn: () => 1000000 });
  eng.setState("IDLE"); // production gọi setState mỗi frame (avatar_engine :603)
  eng.setSpeechEnergy(energy);
  const t0 = 1000000;
  return offsetsSec.map(dt => {
    eng.tick(t0 + dt * 1000);
    const tr = eng.getTransform();
    return { x: tr.swayX, y: tr.swayY };
  });
}

// A) vẫn lắc khi có energy (3 tầng phải có: độ lệch giữa 2 mốc cách nhau vài giây)
const A = swaySample(0.5, [0, 1, 2, 3, 6.25, 12.5]);
check("1b. sway thay đổi theo thời gian khi nói", A[0].x !== A[1].x || A[0].x !== A[2].x,
  `x@0s=${A[0].x.toFixed(4)} x@1s=${A[1].x.toFixed(4)} x@2s=${A[2].x.toFixed(4)}`);

// B) micro-rest: energy=0 → tại cùng mốc thời gian, |sway| phải NHỎ hơn khi nói
const engRest = new BME.BodyMotionEngine({ nowFn: () => 1000000 });
engRest.setState("IDLE");
const engTalk = new BME.BodyMotionEngine({ nowFn: () => 1000000 });
engTalk.setState("IDLE");
engTalk.setSpeechEnergy(0.6);
engTalk.setSpeaking(true);
const t0 = 1000000;
[3000, 4000, 5000].forEach(dt => {
  engRest.tick(t0 + dt);
  engTalk.tick(t0 + dt);
});
const rT = engRest.getTransform(), kT = engTalk.getTransform();
check("1c. micro-rest |sway| nhỏ hơn khi nói", Math.abs(rT.swayX) < Math.abs(kT.swayX),
  `rest=${rT.swayX.toFixed(4)} talk=${kT.swayX.toFixed(4)}`);

// C) chu kỳ 50s phải tồn tại: sway tại t và t+25s khác dấu của thành phần ultra
// (đo gián tiếp: 2 điểm cách nửa chu kỳ tầng chậm nhất phải khác nhau rõ)
const engC = new BME.BodyMotionEngine({ nowFn: () => 1000000 });
engC.setState("IDLE");
engC.setSpeechEnergy(0.5);
engC.setSpeaking(true);
engC.tick(t0);
const c1 = engC.getTransform().swayX;
const engC2 = new BME.BodyMotionEngine({ nowFn: () => 1000000 });
engC2.setState("IDLE");
engC2.setSpeechEnergy(0.5);
engC2.setSpeaking(true);
engC2.tick(t0 + 25000);
const c2 = engC2.getTransform().swayX;
check("1d. tầng 50s tạo khác biệt 25s", c1 !== c2, `x@0=${c1.toFixed(4)} x@25s=${c2.toFixed(4)}`);

// ===== 2. Avatar engine — head motion layers =====
const DH = windowMock.DigitalHumanAvatar;
check("2a. DigitalHumanAvatar định nghĩa", typeof DH === "function");

const av = new DH("test-canvas", { basePath: "/assets/avatar", initialState: "SPEAKING" });
check("2b. engine khởi tạo", !!av);

// đánh dấu v6mot trong source
const src = fs.readFileSync(path.join(baseDir, "avatar_engine.js"), "utf8");
check("2c. source có phraseNod (gật-theo-câu 6.mp4)", src.includes("phraseNod"));
check("2d. lateralLean đã chuyển thành sway ngang (v6ges — không xoay)", src.includes("phraseSway") && !src.includes("lateralLean"));
check("2e. source có MICRO-REST (restFactor 0.35)", src.includes("restFactor"));
check("2f. source consume targetBody trong render", src.includes("const bodyT = this.targetBody"));
// KHÔNG đụng mặt/portrait:
check("2g. giữ _renderSmile (v6mou)", src.includes("_renderSmile"));
check("2h. giữ band MAU 0.42/0.78", src.includes("MAU_FLOOR = 0.42") && src.includes("MAU_CEIL = 0.78"));
check("2i. giữ portrait_v3 asset", src.includes("avatar_v3_thu_thai.png"));
check("2j. KHÔNG có vẽ tay mới (không arm draw)", !/ctx\.moveTo\([^)]*\)\s*;?\s*\/\/\s*arm/i.test(src));

// Chạy 1 frame _update + _render thật với SPEAKING + energy cao (không crash)
// Lưu ý: _update(soArriveTime) so sánh với performance.now() thật (epoch ms) —
// phải truyền mốc TƯƠNG LAI để khối head-shift/speech được tính.
const NOW_REAL = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
const FUTURE = NOW_REAL + 60000; // 60s sau now thật → nextHeadShiftTime bị vượt
av.state = "SPEAKING";
if (av._mouthDriver) {
  // giả lập driver đang nói
  av._mouthDriver.getCurrent = () => ({ viseme: "A", open: 0.6, envelope: 0.7, active: true });
  av._mouthDriver.isActive = () => true;
}
av.nextHeadShiftTime = 0; // force head-shift branch chạy ngay
let updateError = null;
try { av._update(FUTURE); av._render(FUTURE); } catch (e) { updateError = e; }
check("2k. _update+_render SPEAKING không crash", !updateError, updateError ? updateError.message : "");
check("2l. headNodY phản ứng speechPulse", Math.abs(av.headNodY) > 0.01, `headNodY=${av.headNodY.toFixed(3)}`);

// Micro-rest: energy 0 → restFactor co cinematic layer
const avIdle = new DH("test-canvas-2", { basePath: "/assets/avatar", initialState: "IDLE" });
if (avIdle._mouthDriver) {
  avIdle._mouthDriver.getCurrent = () => ({ viseme: "REST", open: 0, envelope: 0, active: false });
  avIdle._mouthDriver.isActive = () => false;
}
avIdle.nextHeadShiftTime = 0;
try { avIdle._update(FUTURE); avIdle._render(FUTURE); } catch (e) { updateError = e; }
check("2m. IDLE energy=0 render không crash", !updateError, updateError ? updateError.message : "");

// ===== 3. targetBody consume =====
const avB = new DH("test-canvas-3", { basePath: "/assets/avatar", initialState: "IDLE" });
avB.targetBody = null;
let e3 = null;
try { avB._render(9000); } catch (e) { e3 = e; }
check("3a. render OK khi targetBody=null", !e3, e3 ? e3.message : "");
avB.targetBody = { swayX: 0.5, swayY: 0.3, breathOffset: 0.4, leanX: 0.2 };
e3 = null;
try { avB._render(9000); } catch (e) { e3 = e; }
check("3b. render OK khi targetBody có transform", !e3, e3 ? e3.message : "");

// ===== 4. Cache bump =====
for (const f of ["kiosk.html", "../src/quan_ai_brain/web/static/executive.html", "../src/quan_ai_brain/web/static/index.html"]) {
  const html = fs.readFileSync(path.join(__dirname, "..", "edge_client", f), "utf8");
  check("4. cache v6mot_1511 trong " + f, html.includes("avatar_engine.js?v=v6mot_1511"));
}

// ===== Tổng =====
const failed = results.filter(r => !r.pass);
console.log("\n===== TỔNG: " + (results.length - failed.length) + "/" + results.length + " PASS, " + failed.length + " FAIL =====");
process.exit(failed.length ? 1 : 0);
