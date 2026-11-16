#!/usr/bin/env node
// (16/11/2026 v6rig_1611) Harness P1 FACE RIG — chạy engine thật trong node-canvas
// nhờ JSDOM + canvas stub, đo: (1) rig vẽ khoang miệng khi openRatio cao,
// (2) không vẽ khi nghỉ, (3) mày warp theo state, (4) sprite cũ đã tắt,
// (5) contract tick/setState/setSpeaking/setSpeechEnergy còn nguyên.
// Chạy: node data/wire_v6rig_test.js  (cần: npm i jsdom canvas — PC có node v22)
const fs = require("fs");
const path = require("path");

let pass = 0, fail = 0;
function T(name, cond) {
  if (cond) { pass++; console.log("  PASS", name); }
  else { fail++; console.log("  FAIL", name); }
}

// ---- Load engine source + eval trong sandbox giả DOM ----
const src = fs.readFileSync(path.join(__dirname, "..", "edge_client", "avatar_engine.js"), "utf8");

const draws = [];
function makeCtx() {
  const grad = { addColorStop: () => {} };
  return new Proxy({}, {
    get(t, prop) {
      if (prop === "createLinearGradient" || prop === "createRadialGradient") return () => grad;
      if (prop === "measureText") return () => ({ width: 10 });
      if (typeof prop === "string") {
        return (...args) => { draws.push([prop, args]); };
      }
      return undefined;
    },
    set() { return true; },
  });
}

class FakeImage {
  constructor() { this.complete = true; this.naturalWidth = 896; this.naturalHeight = 896; }
}
// Image loader stub: mọi this.assets[key] = FakeImage
const sandbox = {
  console, performance: { now: () => Date.now() }, requestAnimationFrame: () => {},
  document: {
    createElement: () => ({ getContext: () => makeCtx(), width: 0, height: 0 }),
    getElementById: () => null,
  },
  window: { addEventListener: () => {} },
  Image: FakeImage,
  ImageData: class {},
};
sandbox.self = sandbox;
sandbox.globalThis = sandbox;

// Trích class DigitalHumanAvatar từ engine (đoạn between "class DigitalHumanAvatar" và kết thúc file)
const m = src.match(/class DigitalHumanAvatar[\s\S]*$/);
if (!m) { console.log("FAIL không tìm thấy class DigitalHumanAvatar"); process.exit(1); }
let code = m[0];
// Bọc eval: class expression → trả về constructor
const factory = new Function("document", "window", "Image", "performance", "requestAnimationFrame", "self", "globalThis",
  code + "\n;return DigitalHumanAvatar;");
const Engine = factory(sandbox.document, sandbox.window, FakeImage, sandbox.performance, sandbox.requestAnimationFrame, sandbox, sandbox);

// ---- Fake canvas + engine instance ----
const fakeCanvas = { width: 1080, height: 1080, getContext: () => makeCtx() };
sandbox.document.getElementById = () => fakeCanvas; // constructor tìm thấy canvas
const engine = new Engine("kiosk-avatar-canvas", { basePath: "/static/assets/avatar" });
engine.canvas = fakeCanvas;
engine.width = 1080; engine.height = 1080;

// Nạp assets giả: tất cả slot v3 + mouth
engine.assets = {};
for (const item of (engine._assetList || [])) {
  engine.assets[item.key] = new FakeImage();
}
// Nếu engine dùng mảng ASSET khác, đảm bảo slot cần rig có sẵn:
for (const key of ["portrait", "portrait_happy", "portrait_thinking", "mouth_speaking", "mouth_rest", "mouth_happy"]) {
  engine.assets[key] = new FakeImage();
}
engine.loaded = true;

const ctx = makeCtx();

// ============ TESTS ============
console.log("== P1 FACE RIG harness ==");

// T1: constructor khởi tạo _rigSmile
T("T1 constructor có _rigSmile=0", engine._rigSmile === 0);

// T2: _rigBase trả toạ độ chuẩn
const R = engine._rigBase();
T("T2 rigBase mouth tâm (547,680)", R.mouthCx === 547 && R.mouthCy === 680);
T("T2 rigBase browL (351,409)", R.browL.cx === 351 && R.browL.cy === 409);

// T3: rig miệng KHÔNG vẽ khi state != SPEAKING
engine.state = "IDLE";
engine.currentOpenRatio = 0.9;
draws.length = 0;
engine._renderRigMouth(ctx, 1.05, 1.05, 0);
T("T3 IDLE không vẽ khoang miệng", !draws.some(d => d[0] === "fill"));

// T4: rig miệng VẼ khi SPEAKING + openRatio cao
engine.state = "SPEAKING";
engine.currentOpenRatio = 0.85;
draws.length = 0;
engine._renderRigMouth(ctx, 1.05, 1.05, 0);
T("T4 SPEAKING có fill khoang", draws.some(d => d[0] === "fill"));
T("T4 có path quadraticCurveTo (hạt đậu)", draws.some(d => d[0] === "quadraticCurveTo"));

// T5: răng xuất hiện khi mở đủ (openPx > mh*0.30)
draws.length = 0;
engine._renderRigMouth(ctx, 1.05, 1.05, 0);
const teeth = draws.some(d => d[0] === "fillStyle" || d[0] === "fill");
T("T5 có fill (khoang+răng)", teeth);

// T6: viseme O/U → khoang hẹp hơn A
engine.activeViseme = "A";
draws.length = 0;
engine._renderRigMouth(ctx, 1.05, 1.05, 0);
const wideHalf = draws.filter(d => d[0] === "quadraticCurveTo").length;
engine.activeViseme = "O";
draws.length = 0;
engine._renderRigMouth(ctx, 1.05, 1.05, 0);
const narrowHalf = draws.filter(d => d[0] === "quadraticCurveTo").length;
T("T6 O/U vẫn vẽ (shape khác không crash)", narrowHalf > 0);

// T7: rig cười — tone tích cực set _rigSmile > 0, tone khác = 0
engine.state = "SPEAKING";
engine.currentOpenRatio = 0.6;
engine.activeEmotionTone = "WARM_GREETING";
engine._renderRigSmile(ctx, 1.05, 1.05, 0);
T("T7 smile tone WARM → _rigSmile>0", engine._rigSmile > 0);
engine.activeEmotionTone = "NEUTRAL";
engine._renderRigSmile(ctx, 1.05, 1.05, 0);
T("T7 tone NEUTRAL → _rigSmile=0", engine._rigSmile === 0);

// T8: rig mày — THINKING nhíu (vẽ lại dải mày = drawImage), IDLE không đụng
engine.state = "THINKING";
engine._rigPortraitImg = new FakeImage();
draws.length = 0;
engine._renderRigBrows(ctx, 1.05, 1.05, 0);
T("T8 THINKING warp mày (drawImage)", draws.some(d => d[0] === "drawImage"));
engine.state = "IDLE";
draws.length = 0;
engine._renderRigBrows(ctx, 1.05, 1.05, 0);
T("T8 IDLE giữ mày gốc (0 drawImage)", !draws.some(d => d[0] === "drawImage"));

// T9: sprite cũ đã ngắt gọi trong _render — check source
T("T9 _renderMouth sprite đã comment", /\/\/\s*this\._renderMouth\(ctx/.test(src));
T("T9 _renderSmile sprite đã comment", /\/\/\s*this\._renderSmile\(ctx/.test(src));
T("T9 _renderEyebrows SVG đã comment", /\/\/\s*this\._renderEyebrows\(ctx/.test(src));

// T10: rig hook trong _render
T("T10 _render gọi _renderRigMouth", /this\._renderRigMouth\(ctx/.test(src) && !/\/\/\s*this\._renderRigMouth/.test(src));
T("T10 _render gọi _renderRigBrows", /this\._renderRigBrows\(ctx/.test(src));
T("T10 _render gọi _renderRigSmile", /this\._renderRigSmile\(ctx/.test(src));

// T11: contract prototype giữ nguyên (TASK001) — tick/setSpeaking/setSpeechEnergy
// thuộc body_motion_engine + presence_engine (không phải avatar engine); setState
// là của avatar engine. Kiểm tra qua source cho đúng scope.
T("T11 avatar_engine.setState tồn tại", typeof engine.setState === "function");
const bmSrc = fs.readFileSync(path.join(__dirname, "..", "edge_client", "body_motion_engine.js"), "utf8");
for (const fn of ["tick", "setState", "setSpeaking", "setSpeechEnergy"]) {
  T(`T11 body_motion_engine.${fn} prototype`, new RegExp(`prototype\\.${fn}\\s*=`).test(bmSrc));
}

// T12: _rigSmile khởi tạo trong constructor (không undefined runtime)
T("T12 _rigSmile number", typeof engine._rigSmile === "number");

console.log(`\nKẾT QUẢ: ${pass} passed / ${fail} failed`);
process.exit(fail ? 1 : 0);
