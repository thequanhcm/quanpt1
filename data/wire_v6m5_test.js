
// V6 M5 harness (duyệt card TASK-V6-M5 16/11) — wire test 5 phần:
//   M5a FPS meter + M5b PROFILE A engine + M5b agent suggest + M5c daemon perf wire + M5d kiosk wire
// Chạy: node data/wire_v6m5_test.js  → exit 0 khi tất cả PASS.
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const ROOT = 'E:/BRAIN';
let ok = 0, fail = 0;
const check = (n, c) => { if (c) { ok++; console.log('PASS ' + n); } else { fail++; console.log('FAIL ' + n); } };

// ===== M5a+M5b: avatar_engine FPS meter + setPerfProfile =====
const engSrc = fs.readFileSync(path.join(ROOT, 'edge_client/avatar_engine.js'), 'utf8');
const sandbox = {
  window: { addEventListener: () => {}, devicePixelRatio: 1, location: { search: '' } },
  document: { getElementById: () => null, createElement: () => ({ style: {} }), addEventListener: () => {}, querySelectorAll: () => [] },
  Image: class {}, performance: { now: () => Date.now() }, requestAnimationFrame: () => 0, console,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(engSrc, sandbox);
const K = vm.runInContext('DigitalHumanAvatar', sandbox);
check('M5a class DigitalHumanAvatar parse', typeof K === 'function');
check('M5a getPerfStats tồn tại', typeof K.prototype.getPerfStats === 'function');
check('M5b setPerfProfile tồn tại', typeof K.prototype.setPerfProfile === 'function');
const inst = Object.create(K.prototype);
inst._perfProfile = undefined; inst.state = 'IDLE';
inst.setPerfProfile('LOW');
check('M5b LOW IDLE 125ms (~8 FPS)', inst._frameIntervalMs() === 125);
inst.state = 'SPEAKING';
check('M5b LOW SPEAKING 66ms (~15 FPS)', inst._frameIntervalMs() === 66);
inst.state = 'LISTENING';
check('M5b LOW LISTENING 100ms (~10 FPS)', inst._frameIntervalMs() === 100);
inst.state = 'SPEAKING';
inst.setPerfProfile('NORMAL');
check('M5b NORMAL SPEAKING 42ms (~24 FPS)', inst._frameIntervalMs() === 42);
inst.state = 'LISTENING';
check('M5b NORMAL LISTENING 56ms (~18 FPS)', inst._frameIntervalMs() === 56);
inst.state = 'IDLE';
check('M5b NORMAL IDLE 83ms (~12 FPS)', inst._frameIntervalMs() === 83);
inst._lastMeasuredFps = 11.8; inst._lastAvgRenderMs = 4.2;
const s = inst.getPerfStats();
check('M5a getPerfStats đủ trường', s.fps_measured === 11.8 && s.render_ms_avg === 4.2 && s.perf_profile === 'NORMAL' && s.fps_target === 12);
check('M5b setPerfProfile(garbage) → NORMAL', inst.setPerfProfile('TURBO') === 'NORMAL');

// ===== M5b: edge_agent.suggest_perf_profile =====
try {
  const eaSrc = fs.readFileSync(path.join(ROOT, 'edge_client/edge_agent.py'), 'utf8');
  check('M5b agent suggest_perf_profile có hàm', eaSrc.includes('def suggest_perf_profile'));
  check('M5b agent fail-honest thiếu dữ liệu', eaSrc.includes('if len(hist) < 4:'));
  check('M5b agent ngưỡng CPU 70', eaSrc.includes('c >= 70.0'));
  check('M5b agent ngưỡng nhiệt 70C', eaSrc.includes('t >= 70.0'));
  check('M5b agent hysteresis phục hồi', eaSrc.includes('c <= 45.0'));
} catch (e) { check('M5b agent đọc file (' + e.message.slice(0, 60) + ')', false); }

// ===== M5c: daemon perf wire =====
try {
  const dSrc = fs.readFileSync(path.join(ROOT, 'edge_client/client_daemon.py'), 'utf8');
  check('M5c route /api/kiosk/perf', dSrc.includes('"/api/kiosk/perf"'));
  check('M5c kiosk_perf field init', dSrc.includes('self.kiosk_perf'));
  check('M5c kiosk_perf expose agent/status', dSrc.includes('"kiosk_perf": kiosk_perf'));
  check('M5c perf_profile đẩy kiosk status', dSrc.includes('"perf_profile":'));
  check('M5c daemon gọi suggest_perf_profile', dSrc.includes('suggest_perf_profile()'));
  // chạy python py_compile
} catch (e) { check('M5c daemon đọc file (' + e.message.slice(0, 60) + ')', false); }

// ===== M5d: kiosk.js wire =====
try {
  const kSrc = fs.readFileSync(path.join(ROOT, 'edge_client/kiosk.js'), 'utf8');
  check('M5d kiosk đọc data.perf_profile', kSrc.includes('data.perf_profile'));
  check('M5d kiosk gọi digitalHuman.setPerfProfile', kSrc.includes('window.digitalHuman.setPerfProfile'));
  check('M5d kiosk POST /api/kiosk/perf', kSrc.includes('"/api/kiosk/perf"'));
  check('M5d kiosk đẩy fps_measured', kSrc.includes('fps_measured'));
  check('M5d kiosk bỏ lượt khi chưa có số', kSrc.includes('s.fps_measured == null'));
  try { new Function(kSrc); check('M5d kiosk.js parse OK', true); }
  catch (e) { check('M5d kiosk.js parse (' + e.message.slice(0, 60) + ')', false); }
} catch (e) { check('M5d kiosk đọc file (' + e.message.slice(0, 60) + ')', false); }


// ===== Python syntax: py_compile 3 file =====
const { execSync } = require('child_process');
try {
  execSync('python -m py_compile edge_client/edge_agent.py edge_client/client_daemon.py tools/v6_m5_benchmark_pi5.py', { cwd: ROOT, stdio: 'pipe' });
  check('M5 py_compile 3 file OK', true);
} catch (e) { check('M5 py_compile (' + String(e.stderr).slice(0, 60) + ')', false); }

console.log('=== V6 M5 WIRE HARNESS: ' + ok + ' pass / ' + fail + ' fail ===');
process.exit(fail > 0 ? 1 : 0);
