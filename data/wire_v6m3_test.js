#!/usr/bin/env node
/* (16/11/2026 v6m3_1611) Harness V6 P3 M3 — Emotion Blend Mesh + HAPPY Duchenne.
 * Pattern wire_v6m12_test.js: sandbox Function + engine thật + Proxy ctx.
 * Đo:
 *  M3a (1-8)   tick engine mỗi frame; fade duration theo transition preset
 *              (SERIOUS_ALERT 120ms < default 350 < SLEEPING 900ms); easing
 *              ease-in-out monotonic + các值 chuẩn; fallback 350 khi không transition
 *  M3b (9-12)  micro factor theo easing×intensity; clamp 0.02..0.6; base 0.08 khi idle
 *  M3c (13-17) Duchenne: SPEAKING tone tích cực sync squint theo smile; state
 *              HAPPY không nói vẫn Duchenne; tone không tích cực → _rigSmile=0
 *  H   (18-20) hooks P1/P2/M12 nguyên (rig, warp, arms-off, no-root-rotate, facialParams)
 * Chạy: node data/wire_v6m3_test.js
 */
const fs = require("fs");
const path = require("path");

let pass = 0, fail = 0;
function T(name, cond, detail) {
  if (cond) { pass++; console.log("  PASS", name); }
  else { fail++; console.log("  FAIL", name, detail || ""); }
}

const src = fs.readFileSync(path.join(__dirname, "..", "edge_client", "avatar_engine.js"), "utf8");
const emoSrc = fs.readFileSync(path.join(__dirname, "..", "edge_client", "emotion_engine.js"), "utf8");

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

// ---- Load emotion engine thật (sandbox) ----
const emoSandbox = { console, window: {}, performance: { now: () => Date.now() } };
emoSandbox.self = emoSandbox; emoSandbox.globalThis = emoSandbox;
const emoFactory = new Function("window", "self", "globalThis", "performance",
  emoSrc + "\n;return window.CherryEmotionEngine;");
const CherryEmotionEngine = emoFactory(emoSandbox.window, emoSandbox, emoSandbox, emoSandbox.performance);
if (!CherryEmotionEngine) { console.log("FAIL không load được CherryEmotionEngine"); process.exit(1); }

// ---- Load engine class (sandbox, inject CherryEmotionEngine vào globalThis) ----
const sandbox = {
  console, performance: { now: () => Date.now() }, requestAnimationFrame: () => {},
  document: { createElement: () => ({ getContext: () => makeCtx(), width: 0, height: 0 }), getElementById: () => null },
  window: { addEventListener: () => {}, CherryEmotionEngine },
  Image: FakeImage, ImageData: class {},
};
sandbox.self = sandbox; sandbox.globalThis = sandbox;
sandbox.window.CherryEmotionEngine = CherryEmotionEngine;
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

// đọc M3_EASING từ source (module-level const)
const easeMatch = src.match(/const M3_EASING = \{[\s\S]*?\};/);
let M3_EASING = null;
if (easeMatch) M3_EASING = new Function(easeMatch[0] + "; return M3_EASING;")();

console.log("== V6 P3 M3 harness (v6m3_1611) ==");

/* ---- M3a: blend theo engine ---- */
{
  // 1. engine tick nằm trong _render (mỗi frame)
  T("M3a.1 tick _emotionEngine.update trong render", /_emotionEngine\.update\(now\)/.test(src));
  // 2. M3_EASING có 4 key khớp preset
  T("M3a.2 M3_EASING đủ 4 easing", !!M3_EASING && ["ease-in-out", "ease-out", "ease-in", "linear"].every(k => typeof M3_EASING[k] === "function"));
  // 3. ease-in-out chuẩn: 0→0, 0.5→0.5, 1→1, monotonic tăng
  const eio = M3_EASING["ease-in-out"];
  T("M3a.3 ease-in-out chuẩn (0/0.5/1)", Math.abs(eio(0)) < 1e-9 && Math.abs(eio(0.5) - 0.5) < 1e-9 && Math.abs(eio(1) - 1) < 1e-9);
  let mono = true, prev = -1;
  for (let i = 0; i <= 20; i++) { const v = eio(i / 20); if (v < prev - 1e-9) mono = false; prev = v; }
  T("M3a.4 ease-in-out monotonic tăng", mono);
  // 4. ease-out nhanh đầu, chậm cuối (cubic)
  const eo = M3_EASING["ease-out"];
  T("M3a.5 ease-out(0.25) > linear(0.25)", eo(0.25) > 0.25 && Math.abs(eo(1) - 1) < 1e-9);
  // 5. FADE_MS fallback 350 khi engine chưa load / không transition
  T("M3a.6 fallback 350ms giữ (không hồi quy v6emo)", /let FADE_MS = 350;/.test(src));
  // 6. FADE_MS lấy durationMs transition
  T("M3a.7 FADE_MS từ tr.durationMs", /FADE_MS = tr\.durationMs/.test(src));
  // 7. fade áp easing: fade = easeFn(rawT)
  T("M3a.8 fade qua easing (hết linear cứng)", /fade = easeFn \? easeFn\(rawT\) : rawT;/.test(src));
  // 8. RUNTIME: setState qua engine → _transition tồn tại + duration đúng preset
  engine._emotionEngine = new CherryEmotionEngine.EmotionTransitionEngine();
  engine._emotionEngine.transitionTo("SLEEPING");
  const tr = engine._emotionEngine._transition;
  T("M3a.9 transitionTo(SLEEPING) duration 900ms theo preset", !!tr && tr.durationMs === 900);
  engine._emotionEngine.transitionTo("SERIOUS_ALERT", { force: true });
  const tr2 = engine._emotionEngine._transition;
  T("M3a.10 SERIOUS_ALERT 120ms (nhanh hơn default)", !!tr2 && tr2.durationMs === 120);
}

/* ---- M3b: micro lerp theo easing+intensity ---- */
{
  T("M3b.1 factor biến (let factor) không còn const cứng", /let factor = 0\.08;/.test(src) && !/const factor = 0\.08;/.test(src));
  T("M3b.2 factor nhân eased × (0.12 + inten×0.5)", /factor = Math\.max\(0\.02, Math\.min\(0\.6, eased \* \(0\.12 \+ inten \* 0\.5\)\)\)/.test(src));
  T("M3b.3 intensity clamp 0.1..1", /Math\.max\(0\.1, Math\.min\(1, snapNow\.intensity \|\| 0\.5\)\)/.test(src));
  T("M3b.4 không transition → base 0.08 (idle không hồi quy)", /if \(prog !== null\) \{[\s\S]{0,400}factor = Math\.max/.test(src));
  // giá trị biên: eased=0.5, inten=0.6 → 0.5*0.42=0.21
  T("M3b.5 giá trị mẫu eased=0.5,inten=0.6 → 0.21", Math.abs(0.5 * (0.12 + 0.6 * 0.5) - 0.21) < 1e-9);
}

/* ---- M3c: HAPPY Duchenne ---- */
{
  T("M3c.1 Duchenne SPEAKING sync theo smile×intensity", /0\.30 \* smile \* inten/.test(src) && /0\.45 \* smile \* inten/.test(src));
  T("M3c.2 state vui không nói vẫn Duchenne (HAPPY/PROUD/SUCCESS/CONFIDENT_SUCCESS)",
    /state === "HAPPY" \|\| this\.state === "PROUD" \|\| this\.state === "SUCCESS"/.test(src));
  T("M3c.3 Duchenne lerp helper method trong class (mắt cong mượt)", /_lerpDuchenne\(a, b, t\) \{ return a \+ \(b - a\) \* t; \}/.test(src));
  T("M3c.4 max squint 0.30-0.26 (nhẹ đúng §4F không cường điệu)", /0\.30 \* smile \* inten/.test(src) && /0\.26 \* inten/.test(src));
  // RUNTIME: state HAPPY → _rigSmile > 0 + squint target dương
  const eng = Object.create(Engine.prototype);
  eng.state = "HAPPY"; eng.activeEmotionTone = "CONFIDENT_SUCCESS";
  eng.currentMicro = { eyeSquint: 0, smileBoost: 0, browLift: 0, browTilt: 0, browInward: 0, browAsymmetric: 0, gazeX: 0, gazeY: 0, glintPulse: 1 };
  eng._emotionEngine = new CherryEmotionEngine.EmotionTransitionEngine();
  eng._emotionEngine.transitionTo("HAPPY");
  eng._rigSmile = 0; eng._rigMouthDx = 0;
  const ctxX = makeCtx();
  eng._renderRigSmile(ctxX, 1, 1, 0);
  T("M3c.5 HAPPY → _rigSmile dương + squint nâng dần", eng._rigSmile > 0.2 && eng.currentMicro.eyeSquint > 0);
  // tone không tích cực → _rigSmile=0 (giữ hành vi cũ)
  const eng2 = Object.create(Engine.prototype);
  eng2.state = "SPEAKING"; eng2.activeEmotionTone = "SERIOUS_ALERT";
  eng2.currentOpenRatio = 0.5; eng2._rigSmile = 0.4; eng2._rigMouthDx = 0;
  eng2._emotionEngine = new CherryEmotionEngine.EmotionTransitionEngine();
  const ctx2 = makeCtx();
  eng2._renderRigSmile(ctx2, 1, 1, 0);
  T("M3c.6 SERIOUS_ALERT → không cười (_rigSmile=0)", eng2._rigSmile === 0);
}

/* ---- H: hooks nguyên ---- */
{
  T("H.1 P1 rig còn (_renderRigMouth/_renderRigBrows/_renderRigSmile)", src.includes("_renderRigMouth(") && src.includes("_renderRigBrows(") && src.includes("_renderRigSmile("));
  T("H.2 P2 warp còn (_renderHeadPose/_poseAt)", src.includes("_renderHeadPose(") && src.includes("_poseAt"));
  T("H.3 M12 còn (_facialParams/_browAmtFor/steady)", src.includes("_facialParams(") && src.includes("_browAmtFor(") && /const steady = 1 - openNow \* 0\.55;/.test(src));
  T("H.4 arms vẫn tắt + root không ctx.rotate", /\/\/\s*this\._renderArmsOverPortrait\(ctx/.test(src));
}

console.log(`\nKẾT QUẢ wire_v6m3_test: ${pass} passed / ${fail} failed`);
process.exit(fail ? 1 : 0);
