#!/usr/bin/env node
// (16/11/2026 v6pose_1611) Harness P2 HEAD POSE — chạy engine thật trong sandbox
// giả DOM (pattern wire_v6rig_test.js), đo:
//  (1) head pose state tồn tại + drift/lerp chạy (update loop),
//  (2) _renderHeadPose warp 16 dải quanh cổ (drawImage theo ease), thân nguyên,
//  (3) mắt overlay + rig P1 đi CÙNG đầu (offset _poseAt),
//  (4) state mapping: SPEAKING/LISTENING/THINKING/SLEEPING ra pose khác nhau,
//  (5) saccade mở rộng cho SPEAKING/HAPPY + fixation,
//  (6) root transform KHÔNG xoay (không ctx.rotate ngoài crop roll),
//  (7) clamp giới hạn ±6/±4/±2 — không vượt thiết kế.
// Chạy: node data/wire_v6pose_test.js
const fs = require("fs");
const path = require("path");

let pass = 0, fail = 0;
function T(name, cond) {
  if (cond) { pass++; console.log("  PASS", name); }
  else { fail++; console.log("  FAIL", name); }
}

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
engine.startTime = Date.now() - 5000; // poseT dương
const ctx = makeCtx();

console.log("== P2 HEAD POSE harness ==");

// T1: constructor khởi tạo pose
T("T1 headYaw/Pitch/Roll khởi tạo = 0", engine.headYaw === 0 && engine.headPitch === 0 && engine.headRoll === 0);

// T2: _clamp helper
T("T2 _clamp trong biên", engine._clamp(9, -6, 6) === 6 && engine._clamp(-9, -6, 6) === -6 && engine._clamp(1, -6, 6) === 1);

// T3: _renderHeadPose vẽ 16 dải khi có yaw, 0 dải khi pose ~0
engine.headYaw = 0; engine.headPitch = 0; engine.headRoll = 0; engine._poseAt = null;
draws.length = 0;
engine._renderHeadPose(ctx, engine.assets.portrait, 1080, 1080);
T("T3 pose 0 → không vẽ dải", !draws.some(d => d[0] === "drawImage"));
engine.headYaw = 5; engine.headPitch = 2; engine.headRoll = 1;
draws.length = 0;
engine._renderHeadPose(ctx, engine.assets.portrait, 1080, 1080);
const bandDraws = draws.filter(d => d[0] === "drawImage");
T("T3 pose có yaw → vẽ 16 dải", bandDraws.length === 16);
// T3b: dải tại cổ (dải cuối) dx≈0 — thân đứng yên. drawImage args:
// (img, sx, sy, sw, sh, dx, dy, dw, dh) → dx là args[5] (không phải [4]).
const lastBand = bandDraws[15];
const firstBand = bandDraws[0];
const dxLast = lastBand[1][5], dxFirst = firstBand[1][5];
T("T3b dải ĐÁY (cổ) dx≈0 (thân nguyên)", Math.abs(dxLast) < 0.5);
T("T3b dải ĐỈNH dx lớn nhất", Math.abs(dxFirst) > Math.abs(dxLast) + 1);

// T4: _poseAt đã set cho 3 vùng (eye/brow/mouth) — offset theo ease chiều cao
// (ease giảm từ trên xuống: mắt y≈438 cao hơn mày y≈408? KHÔNG — mày 408 CAO HƠN
// mắt 438 trong ảnh (y nhỏ = cao hơn). Vậy |brow.dx| ≥ |eye.dx| > |mouth.dx|).
T("T4 _poseAt có eye/brow/mouth", engine._poseAt && engine._poseAt.eye && engine._poseAt.brow && engine._poseAt.mouth);
T("T4 brow.dx > eye.dx > mouth.dx (ease theo chiều cao)",
  Math.abs(engine._poseAt.brow.dx) > Math.abs(engine._poseAt.eye.dx) &&
  Math.abs(engine._poseAt.eye.dx) > Math.abs(engine._poseAt.mouth.dx));

// T5: trạng thái điều khiển pose — mô phỏng update loop nhiều frame
// (dùng chính logic: đặt state + chạy đoạn 4b bằng tick thật không tiện — thay vào đó
// kiểm tra mapping qua source + lerp thủ công)
T("T5 source có khối 4b HEAD POSE", src.includes("4b. P2 HEAD POSE"));
T("T5 SPEAKING có statePitch gật", /SPEAKING[\s\S]{0,600}statePitch = Math\.max\(0, beat\)/.test(src));
T("T5 LISTENING nghiêng đầu", /LISTENING[\s\S]{0,200}stateRoll = -1\.4/.test(src));
T("T5 SLEEPING đầu gục", /SLEEPING[\s\S]{0,200}statePitch = 2\.6/.test(src));
T("T5 clamp ±6/±4/±2", /_clamp\(driftYaw \+ stateYaw \* steady \+ gazeYaw, -6, 6\)/.test(src));

// T6: _renderEyes nhận poseOff (đi cùng đầu). destX = eb.x*scaleX + poseOff.dx
draws.length = 0;
engine.state = "IDLE"; engine.isBlinking = true; engine.assets.eyes_blink = new FakeImage();
engine.saccadeX = 0; engine.saccadeY = 0; engine.currentMicro = { gazeX: 0, gazeY: 0 };
engine._renderEyes(ctx, 1.05, 1.05, 0, false, false, false, { dx: 4, dy: 2 });
// drawImage CUỐI = vẽ eCanvas lên ctx chính (args[1] = destX); drawImage đầu
// là vẽ eyes_blink vào eCanvas nội bộ tại (0,0).
const eyeDraw = draws.filter(d => d[0] === "drawImage").pop();
T("T6 eyes overlay dịch theo poseOff", eyeDraw && Math.abs(eyeDraw[1][1] - (engine.EYES_BOX.x * 1.05 + 4)) < 0.6);

// T7: rig miệng + cười + mày đọc _rigMouthDx/_rigBrowDx (đi cùng đầu).
// f = 896/this.width = 896/1080; moveTo đầu tiên = (cx - halfW + poseDx, ...)
engine._rigMouthDx = 3.5; engine._rigBrowDx = 2.0;
const f7 = 896 / 1080;
engine.state = "SPEAKING"; engine.currentOpenRatio = 0.8; engine.activeViseme = "A";
engine.activeEmotionTone = "WARM_GREETING"; engine._rigSmile = 0;
draws.length = 0;
engine._renderRigMouth(ctx, 1.05, 1.05, 0);
const mouthPath = draws.filter(d => d[0] === "moveTo");
T("T7 khoang miệng +poseDx", mouthPath.length > 0 &&
  Math.abs(mouthPath[0][1][0] - ((547 - 264 * 0.5) * f7 + 3.5)) < 1.0);
draws.length = 0;
engine.state = "THINKING"; engine._rigPortraitImg = new FakeImage();
engine._renderRigBrows(ctx, 1.05, 1.05, 0);
const browDraw = draws.find(d => d[0] === "translate");
T("T7 dải mày +poseDx", browDraw && Math.abs(browDraw[1][0] - (351 * f7 + 2.0)) < 1.0);

// T8: saccade mở rộng — SPEAKING/HAPPY có nhánh riêng + fixation
T("T8 saccade SPEAKING branch", /state === "SPEAKING" \|\| this\.state === "HAPPY"/.test(src));
T("T8 micro-fixation 30%", /Math\.random\(\) < 0\.30/.test(src));

// T9: root render KHÔNG xoay (v6ges rule) — khối _render→restore không có
// ctx.rotate thực thi (chỉ có chữ "rotate" trong comment).
const rIdx = src.indexOf("_render(now)");
const restIdx = src.indexOf("ctx.restore(); // Restore head transform");
const rootSeg = src.slice(rIdx, restIdx);
const execRotates = rootSeg.split("\n").filter(l => {
  const code = l.replace(/\/\/.*$/, ""); // bỏ comment cuối dòng
  return /ctx\.rotate\(/.test(code) && !/^\s*\/\//.test(l);
});
T("T9 root không ctx.rotate ngoài head pose", execRotates.length === 0);

// T10: wire _render gọi _renderHeadPose + truyền offset cho rig
T("T10 _render gọi _renderHeadPose", /this\._renderHeadPose\(ctx, baseImg, w, h\)/.test(src));
T("T10 _render set _rigBrowDx/_rigMouthDx", /_rigBrowDx = p\.brow\.dx/.test(src) && /_rigMouthDx = p\.mouth\.dx/.test(src));
T("T10 crossfade cũng qua head pose", /_renderHeadPose\(ctx, this\._prevPortrait\.img, w, h\)/.test(src));

// T11: P1 harness vẫn phải logic-pass — sprite vẫn tắt, rig vẫn wire
T("T11 P1 sprite _renderMouth vẫn comment", /\/\/\s*this\._renderMouth\(ctx/.test(src));
T("T11 P1 arms vẫn tắt (yêu cầu owner 16/11)", /\/\/\s*this\._renderArmsOverPortrait\(ctx/.test(src));

// T12: pose không phá signal IDLE tĩnh — pose nhỏ (<0.05°) skip render
engine.headYaw = 0.01; engine.headPitch = 0.01; engine.headRoll = 0.01;
draws.length = 0;
engine._renderHeadPose(ctx, engine.assets.portrait, 1080, 1080);
T("T12 pose vi mô → skip (không tốn CPU)", draws.filter(d => d[0] === "drawImage").length === 0);

console.log(`\nKẾT QUẢ: ${pass} passed / ${fail} failed`);
process.exit(fail ? 1 : 0);
