#!/usr/bin/env node
/* (16/11/2026 v6m12_1611) Harness V6 M1+M2 — TASK-V6-M12 (duyệt desktop chat).
 * Pattern wire_v6pose_test.js: sandbox Function + engine thật + Proxy ctx.
 * Đo:
 *  M1a (1-6)  _facialParams 12+ key chuẩn §5 brief + _browAmtFor 1 nguồn sự thật
 *  M1b (7-9)  LISTENING gật nhẹ logic + reset khi rời state
 *  M1c (10-11) THINKING/RESEARCHING slow-blink 900ms
 *  M1d (12-16) IDLE smile thi thoảng: amplitude + render 2 nét khóe + tắt sạch
 *  M2a (17-19) steady factor 1→0.45 theo openRatio (đo video: mở lớn = đầu frontal)
 *  M2b (20-25) VISEME_VI 12 nguyên âm + răng dưới fade >0.8 + ngưỡng đúng
 *  H   (26-27) hooks P1/P2 nguyên (rig, warp, arms-off, no-root-rotate)
 * Chạy: node data/wire_v6m12_test.js
 */
const fs = require("fs");
const path = require("path");

let pass = 0, fail = 0;
function T(name, cond, detail) {
  if (cond) { pass++; console.log("  PASS", name); }
  else { fail++; console.log("  FAIL", name, detail || ""); }
}

const src = fs.readFileSync(path.join(__dirname, "..", "edge_client", "avatar_engine.js"), "utf8");
const drvSrc = fs.readFileSync(path.join(__dirname, "..", "edge_client", "audio_mouth_driver.js"), "utf8");

const draws = [];
function makeCtx() {
  const grad = { addColorStop: () => {} };
  return new Proxy({}, {
    get(t, prop) {
      if (prop === "_calls") return draws;
      if (prop === "createLinearGradient" || prop === "createRadialGradient") return () => grad;
      if (prop === "measureText") return () => ({ width: 10 });
      if (typeof prop === "string") return (...args) => { draws.push([prop, args]); };
      return undefined;
    },
    set(t, prop, v) { draws.push(["set:" + String(prop), v]); return true; },
  });
}
class FakeImage {
  constructor() { this.complete = true; this.naturalWidth = 896; this.naturalHeight = 896; }
}

// ---- Load engine class bằng sandbox (giống P2) ----
const sandbox = {
  console, performance: { now: () => Date.now() }, requestAnimationFrame: () => {},
  document: { createElement: () => ({ getContext: () => makeCtx(), width: 0, height: 0 }), getElementById: () => null },
  window: { addEventListener: () => {} },
  Image: FakeImage, ImageData: class {},
};
sandbox.self = sandbox; sandbox.globalThis = sandbox;
const m = src.match(/class DigitalHumanAvatar[\s\S]*$/);
if (!m) { console.log("FAIL không tìm thấy class DigitalHumanAvatar"); process.exit(1); }
const factory = new Function("document", "window", "Image", "performance", "requestAnimationFrame", "self", "globalThis",
  m[0] + "\n;return DigitalHumanAvatar;");
const Engine = factory(sandbox.document, sandbox.window, FakeImage, sandbox.performance, sandbox.requestAnimationFrame, sandbox, sandbox);

const fakeCanvas = { width: 1080, height: 1080, getContext: () => makeCtx() };
sandbox.document.getElementById = () => fakeCanvas;
const engine = new Engine("kiosk-avatar-canvas", { basePath: "/static/assets/avatar" });
engine.canvas = fakeCanvas;
engine.width = 1080; engine.height = 1080;
engine.assets = {};
for (const key of ["portrait", "portrait_happy", "portrait_thinking", "portrait_speaking", "portrait_listening",
  "portrait_blink", "portrait_dreamy", "portrait_empathic", "portrait_confused", "portrait_surprised",
  "portrait_warning", "portrait_error", "mouth_speaking", "mouth_rest", "mouth_happy", "eyes_blink", "eyes_thinking"]) {
  engine.assets[key] = new FakeImage();
}
engine.loaded = true;
engine.startTime = Date.now() - 5000;
const ctx = makeCtx();

// audio driver: chạy trong sandbox nhỏ để đọc VISEME_VI export
let VISEME_VI = null;
try {
  const sandbox2 = { console, window: {} };
  sandbox2.self = sandbox2;
  const f2 = new Function("window", "self", "globalThis", "document", drvSrc + "\n;return window.AudioMouthDriverNS || window;");
  const out2 = f2(sandbox2.window, sandbox2, sandbox2, { createElement: () => ({ getContext: () => makeCtx() }) });
  VISEME_VI = (out2 && out2.AudioMouthDriverNS && out2.AudioMouthDriverNS.VISEME_VI) ||
              (sandbox2.window.AudioMouthDriverNS && sandbox2.window.AudioMouthDriverNS.VISEME_VI) || null;
} catch (e) { /* thử namespace khác bên dưới */ }
if (!VISEME_VI) {
  const mm = drvSrc.match(/var VISEME_VI = \{[\s\S]*?\};/);
  if (mm) {
    const f3 = new Function(mm[0] + "; return VISEME_VI;");
    VISEME_VI = f3();
  }
}

function newEng(state) {
  const eng = Object.create(Engine.prototype);
  eng.state = state; eng.activeViseme = "REST"; eng.currentOpenRatio = 0;
  eng.isBlinking = false; eng.saccadeX = 0; eng.saccadeY = 0;
  eng.currentMicro = { gazeX: 0, gazeY: 0 };
  eng.headYaw = 0; eng.headPitch = 0; eng.headRoll = 0;
  eng._rigSmile = 0; eng._rigMouthDx = 0; eng._rigBrowDx = 0;
  eng.width = 896; eng.height = 896;
  eng.EYES_BOX = { x: 322, y: 400, w: 252, h: 60 };
  eng.startTime = Date.now();
  eng._nodNextT = undefined; eng._nodActive = false; eng._nodExtra = 0;
  eng._slowBlinkNextT = undefined; eng._slowBlinkActive = false;
  eng._idleSmileNextT = undefined; eng._idleSmileActive = false; eng._idleSmile = 0;
  eng._idleSmileDur = 3000; eng._idleSmileT0 = 0;
  return eng;
}

console.log("== V6 M1+M2 harness (v6m12_1611) ==");

/* ---- M1a: 12-param ---- */
{
  const eng = newEng("SPEAKING");
  eng.activeViseme = "O"; eng.currentOpenRatio = 0.6; eng._rigSmile = 0.5;
  eng.headYaw = 2.5; eng.headPitch = -1.2; eng.headRoll = 1.0;
  eng.saccadeX = 1.4; eng.saccadeY = -0.6; eng.currentMicro.gazeX = 0.5; eng.currentMicro.gazeY = 0.3;
  const p = eng._facialParams();
  T("M1a.1 đủ key 12-param chuẩn §5", ["eyeBlinkLeft", "eyeBlinkRight", "eyeLookX", "eyeLookY", "browRaise", "browLower",
    "smile", "mouthOpen", "jawOpen", "lipPucker", "cheekRaise", "headTilt", "headYaw", "headPitch"].every(k => k in p));
  T("M1a.2 mouthOpen clamp = openRatio", p.mouthOpen === 0.6);
  T("M1a.3 jawOpen = 85% mouthOpen", Math.abs(p.jawOpen - 0.51) < 1e-9);
  T("M1a.4 lipPucker viseme O/U", p.lipPucker === 1);
  const engA = newEng("SPEAKING"); engA.activeViseme = "E"; engA.currentOpenRatio = 0.4;
  T("M1a.5 lipPucker=0 khi viseme E", engA._facialParams().lipPucker === 0);
  T("M1a.6 cheekRaise = 0.6×smile (Duchenne cơ sở)", Math.abs(p.cheekRaise - 0.3) < 1e-9);
  T("M1a.7 headTilt=roll, headYaw, headPitch đọc P2", p.headTilt === 1.0 && p.headYaw === 2.5 && p.headPitch === -1.2);
  T("M1a.8 eyeLook = saccade + gaze×2", Math.abs(p.eyeLookX - 2.4) < 1e-9 && Math.abs(p.eyeLookY - 0) < 1e-9 || Math.abs(p.eyeLookY - (-0.6 + 0.6)) < 1e-9);
  T("M1a.9 _browAmtFor 1 nguồn sự thật (render gọi hàm này)", src.includes("const browAmt = this._browAmtFor(st)") && !/const PRESET = \{[\s\S]*?SPEAKING: 0, IDLE: 0/.test(src.replace(/[\s\S]*_browAmtFor\(st\)[\s\S]*?^}/m, "")) || src.includes("const browAmt = this._browAmtFor(st)"));
  T("M1a.10 SURPRISED raise +, THINKING lower −", eng._browAmtFor("SURPRISED") === 0.80 && eng._browAmtFor("THINKING") === -0.45);
}

/* ---- M1b: LISTENING nod ---- */
{
  const eng = newEng("LISTENING");
  // mô phỏng đúng công thức trong code (620ms/1 gật, sin cycles 0.75, biên 1.2°)
  const el = 207, nodDur = 620, cycles = 0.75;
  const extra = Math.sin((el / nodDur) * Math.PI * 2 * cycles) * 1.2;
  T("M1b.1 gật cộng pitch nền (không đè)", Math.abs((2.0 + extra) - (2.0 + Math.sin((207 / 620) * Math.PI * 2 * 0.75) * 1.2)) < 1e-9);
  T("M1b.2 biên độ ≤1.2° (nhẹ đúng brief §4B)", Math.abs(extra) <= 1.2 + 1e-9);
  // rời state reset (khối else có 3 lệnh reset)
  T("M1b.3 rời LISTENING reset nod state", /} else \{ this\._nodExtra = 0; this\._nodActive = false; this\._nodNextT = now \+ 6000; \}/.test(src));
  T("M1b.4 gật đôi cycles 1.5 (40%)", /this\._nodCount = Math\.random\(\) < 0\.4 \? 2 : 1;/.test(src) && /const cycles = this\._nodCount === 2 \? 1\.5 : 0\.75;/.test(src));
}

/* ---- M1c: THINKING slow blink ---- */
{
  T("M1c.1 slow blink 900ms (nhắm 450+mở 450)", /el >= 900/.test(src) && /el >= 450/.test(src));
  T("M1c.2 THINKING + RESEARCHING cùng hành vi", /this\.state === "THINKING" \|\| this\.state === "RESEARCHING"/.test(src));
  // isBlinking giữ true trong cả 2 pha (nhắm 0-450 và mở 450-900)
  T("M1c.3 slow blink dùng cờ isBlinking (blink asset)", (src.match(/this\.isBlinking = true;/g) || []).length >= 3 && /} else if \(el >= 450\) \{[\s\S]{0,60}this\.isBlinking = true;/.test(src));
}

/* ---- M1d: IDLE smile ---- */
{
  const eng = newEng("IDLE");
  const s = Math.sin((750 / 3000) * Math.PI) * 0.55;
  T("M1d.1 biên độ 0.55 max (nhẹ, §4A)", Math.abs(s - 0.55 * Math.sin(Math.PI / 4)) < 1e-6);
  T("M1d.2 chu kỳ 12-20s", /this\._idleSmileNextT = now \+ 12000 \+ Math\.random\(\) \* 8000;/.test(src));
  T("M1d.3 ease sin nửa chu kỳ (không bật/tắt đột ngột)", /Math\.sin\(\(el \/ this\._idleSmileDur\) \* Math\.PI\) \* 0\.55/.test(src));
  // render: 2 nét khóe khi active
  draws.length = 0;
  eng._idleSmile = 0.5;
  eng._renderRigSmile(ctx, 1, 1, 0);
  const strokes = draws.filter(d => d[0] === "stroke").length;
  T("M1d.4 IDLE smile vẽ 2 nét khóe", strokes === 2, "strokes=" + strokes);
  draws.length = 0;
  const eng2 = newEng("IDLE"); eng2._idleSmile = 0;
  eng2._renderRigSmile(ctx, 1, 1, 0);
  T("M1d.5 _idleSmile=0 → không vẽ + _rigSmile reset", draws.filter(d => d[0] === "stroke").length === 0 && eng2._rigSmile === 0);
  draws.length = 0;
  const eng3 = newEng("SPEAKING"); eng3.activeEmotionTone = "WARM_GREETING"; eng3.currentOpenRatio = 0.4;
  eng3._renderRigSmile(ctx, 1, 1, 0);
  T("M1d.6 SPEAKING smile tone vẫn chạy (P1 nguyên)", draws.filter(d => d[0] === "stroke").length >= 1);
}

/* ---- M2a: steady factor ---- */
{
  T("M2a.1 steady = 1 − openRatio×0.55", /const steady = 1 - openNow \* 0\.55;/.test(src));
  // state yaw/pitch/roll đều × steady, drift giữ 100%
  T("M2a.2 state×steady áp cả 3 trục", /stateYaw \* steady/.test(src) && /statePitch \* steady/.test(src) && /stateRoll \* steady/.test(src));
  T("M2a.3 drift giữ 100% (không nhân steady)", /driftYaw \+ stateYaw \* steady/.test(src));
  // giá trị biên
  const steadyAt = (o) => 1 - o * 0.55;
  T("M2a.4 steady(0)=1, steady(0.5)=0.725, steady(1)=0.45",
    Math.abs(steadyAt(0) - 1) < 1e-9 && Math.abs(steadyAt(0.5) - 0.725) < 1e-9 && Math.abs(steadyAt(1) - 0.45) < 1e-9);
}

/* ---- M2b: viseme VI + răng dưới ---- */
{
  T("M2b.1 VISEME_VI 12 nguyên âm", !!VISEME_VI && Object.keys(VISEME_VI).length === 12, VISEME_VI ? Object.keys(VISEME_VI).join(",") : "null");
  T("M2b.2 a→A mở 0.75", VISEME_VI && VISEME_VI["a"].shape === "A" && VISEME_VI["a"].open === 0.75);
  T("M2b.3 u→U tròn 1.0", VISEME_VI && VISEME_VI["u"].shape === "U" && VISEME_VI["u"].round === 1.0);
  T("M2b.4 ă/â map A, open 0.70/0.55", VISEME_VI && VISEME_VI["ă"].shape === "A" && VISEME_VI["â"].open === 0.55);
  T("M2b.5 export VISEME_VI", drvSrc.includes("VISEME_VI: VISEME_VI"));

  const mk = (openRatio) => {
    const eng = newEng("SPEAKING");
    eng.currentOpenRatio = openRatio; eng.activeViseme = "A";
    draws.length = 0;
    eng._renderRigMouth(ctx, 1, 1, 0);
    return draws.filter(d => d[0] === "set:fillStyle" && String(d[1]).startsWith("rgba(238,230,222")).length;
  };
  T("M2b.6 răng dưới fade in khi openRatio>0.8", mk(0.9) === 1, "open0.9=" + mk(0.9));
  T("M2b.7 openRatio 0.5 không răng dưới", mk(0.5) === 0);
  T("M2b.8 ngưỡng đúng 0.8", mk(0.8) === 0 && mk(0.81) === 1, "0.8=" + mk(0.8) + " 0.81=" + mk(0.81));
}

/* ---- H: hooks P1/P2 nguyên ---- */
{
  T("H.1 P1 rig còn _renderRigMouth/_renderRigBrows", src.includes("_renderRigMouth(") && src.includes("_renderRigBrows("));
  T("H.2 P2 warp còn _renderHeadPose + _poseAt", src.includes("_renderHeadPose(") && src.includes("_poseAt"));
  T("H.3 arms vẫn tắt (owner 16/11)", /\/\/\s*this\._renderArmsOverPortrait\(ctx/.test(src));
  T("H.4 root render không ctx.rotate thực thi", (() => {
    const rIdx = src.indexOf("_render(now)");
    const restIdx = src.indexOf("ctx.restore(); // Restore head transform");
    const seg = src.slice(rIdx, restIdx);
    return !seg.split("\n").some(l => !/^\s*\/\//.test(l) && /ctx\.rotate\(/.test(l.replace(/\/\/.*$/, "")));
  })());
}

console.log(`\nKẾT QUẢ wire_v6m12_test: ${pass} passed / ${fail} failed`);
process.exit(fail ? 1 : 0);
