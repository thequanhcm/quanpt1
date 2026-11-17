#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V6 M5 — Benchmark Pi5 60 phút (PROFILE A) + PC RTT.

Plan: docs/CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md §4 M5:
  "Tối ưu Pi5 (PROFILE A): đo FPS thật, giảm chi phí khi CPU cao; PROFILE B PC giữ full;
   benchmark 60min"

Đo qua API đã có (không thêm engine):
- Pi5 Edge Agent V41: /api/kiosk/agent/status → CPU/nhiệt/throttle/load mỗi 30s
- PC core: /api/executive/edge/telemetry → RTT LAN + avatar_state
- (nếu --use-ssh và ssh BatchMode OK) tổng CPU các process chromium trên Pi5 qua `ps`

Chạy:
  python tools/v6_m5_benchmark_pi5.py                       # 60 phút chuẩn M5
  python tools/v6_m5_benchmark_pi5.py --duration-min 2      # smoke 2 phút
Output:
  reports/V6_M5_BENCHMARK_<timestamp>.json + .md (bảng nghiệm thu)
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
REPORTS = WORKSPACE / "reports"
PI5_STATUS = "http://192.168.1.21:8768/api/kiosk/agent/status"
PC_TELEMETRY = "http://127.0.0.1:8766/api/executive/edge/telemetry"
SAMPLE_INTERVAL_SEC = 30.0

# Ngưỡng cảnh báo M5 (Pi 5 4GB, kiosk chromium SwiftShader):
CPU_WARN_PCT = 60.0     # >60% 3 mẫu liên tiếp → WARN (budget headroom thấp)
CPU_CRIT_PCT = 85.0     # >85% 1 mẫu → CRIT
TEMP_WARN_C = 68.0      # >68°C cảnh báo (Pi5 throttling bắt đầu ~80°C)
TEMP_CRIT_C = 78.0
RTT_WARN_MS = 150.0     # LAN WiFi bình thường <50ms


def _get_json(url: str, timeout: float = 8.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def sample_pi5_chromium_cpu() -> float | None:
    """Tổng CPU % các process chromium trên Pi5 (qua ssh BatchMode)."""
    try:
        out = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
             "quanpt1@192.168.1.21",
             "ps -eo comm,pcpu | awk '$1 ~ /chromium/ {s+=$2} END {print s}'"],
            capture_output=True, text=True, timeout=12)
        line = [l for l in out.stdout.strip().splitlines() if l.strip()][-1]
        return float(line)
    except Exception:
        return None


def classify(cpu: float, temp: float, rtt: float, throttle_bits: int) -> str:
    if cpu >= CPU_CRIT_PCT or temp >= TEMP_CRIT_C:
        return "CRIT"
    if (cpu >= CPU_WARN_PCT or temp >= TEMP_WARN_C
            or rtt >= RTT_WARN_MS or throttle_bits != 0):
        return "WARN"
    return "OK"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration-min", type=float, default=60.0)
    ap.add_argument("--interval-sec", type=float, default=SAMPLE_INTERVAL_SEC)
    ap.add_argument("--use-ssh", action="store_true", help="thêm mẫu CPU chromium qua ssh")
    args = ap.parse_args()

    REPORTS.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    duration_sec = args.duration_min * 60.0

    ssh_ok = False
    if args.use_ssh:
        try:
            r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                                "quanpt1@192.168.1.21", "echo ok"],
                               capture_output=True, text=True, timeout=10)
            ssh_ok = r.returncode == 0
        except Exception:
            ssh_ok = False

    samples: list[dict] = []
    print(f"M5 BENCHMARK: duration={args.duration_min}min interval={args.interval_sec}s ssh={ssh_ok}")
    t0 = time.time()
    n = 0
    while (time.time() - t0) < duration_sec:
        n += 1
        s: dict = {"i": n, "t_sec": round(time.time() - t0, 1)}
        # Pi5 agent
        try:
            d = _get_json(PI5_STATUS)
            m = d.get("agent", {}).get("metrics", {})
            s["cpu_pct"] = m.get("cpu_percent")
            s["temp_c"] = m.get("temp_c")
            s["throttle_bits"] = m.get("throttled_bits")
            s["load1"] = (m.get("load_avg") or [None])[0]
            s["mem_avail_mb"] = m.get("mem_available_mb")
            # M5c: FPS THẬT browser đẩy về (fail-honest: None nếu chưa có/stale)
            kp = d.get("kiosk_perf") or {}
            s["fps_measured"] = kp.get("fps_measured")
            s["render_ms_avg"] = kp.get("render_ms_avg")
            s["perf_profile"] = kp.get("perf_profile")
            kp_age = time.time() - (kp.get("epoch") or 0.0)
            if kp_age > 60:  # dữ liệu perf stale > 60s → coi như không có
                s["fps_measured"] = None
        except Exception as e:
            s["pi5_err"] = str(e)[:120]
        # PC telemetry
        try:
            d2 = _get_json(PC_TELEMETRY)
            s["rtt_ms"] = round(d2.get("rtt_ms") or -1, 1)
            s["edge_state"] = (d2.get("edge_status") or {}).get("state")
        except Exception as e:
            s["pc_err"] = str(e)[:120]
        # chromium CPU (optional)
        if ssh_ok:
            c = sample_pi5_chromium_cpu()
            if c is not None:
                s["chromium_cpu_pct"] = round(c, 1)
        s["verdict"] = classify(
            s.get("cpu_pct") or 0, s.get("temp_c") or 0,
            s.get("rtt_ms") or 0, s.get("throttle_bits") or 0)
        samples.append(s)
        print(f"[{n:3d}] t={s['t_sec']:6.0f}s cpu={s.get('cpu_pct')}% temp={s.get('temp_c')}C "
              f"rtt={s.get('rtt_ms')}ms verdict={s['verdict']}")
        time.sleep(max(1.0, args.interval_sec))

    # ===== TỔNG HỢP =====
    cpus = [s["cpu_pct"] for s in samples if isinstance(s.get("cpu_pct"), (int, float))]
    temps = [s["temp_c"] for s in samples if isinstance(s.get("temp_c"), (int, float))]
    rtts = [s["rtt_ms"] for s in samples if isinstance(s.get("rtt_ms"), (int, float)) and s["rtt_ms"] >= 0]
    chroms = [s["chromium_cpu_pct"] for s in samples if isinstance(s.get("chromium_cpu_pct"), (int, float))]

    def stats(v):
        if not v:
            return None
        return {
            "n": len(v), "min": round(min(v), 1), "avg": round(statistics.mean(v), 1),
            "p95": round(sorted(v)[int(len(v) * 0.95) - 1] if len(v) > 1 else v[0], 1),
            "max": round(max(v), 1),
        }

    cpu3_consec_warn = any(
        all((samples[i + k].get("cpu_pct") or 0) >= CPU_WARN_PCT for k in range(3))
        for i in range(len(samples) - 2))
    verdicts = [s["verdict"] for s in samples]
    final = "FAIL" if "CRIT" in verdicts else ("WARN" if ("WARN" in verdicts or cpu3_consec_warn) else "PASS")

    summary = {
        "timestamp": ts,
        "duration_min": args.duration_min,
        "samples": len(samples),
        "cpu_pct": stats(cpus),
        "chromium_cpu_pct": stats(chroms),
        "temp_c": stats(temps),
        "rtt_ms": stats(rtts),
        "warn_3consec_cpu": cpu3_consec_warn,
        "verdict_counts": {v: verdicts.count(v) for v in ("OK", "WARN", "CRIT")},
        "FINAL": final,
        "thresholds": {"cpu_warn": CPU_WARN_PCT, "cpu_crit": CPU_CRIT_PCT,
                       "temp_warn": TEMP_WARN_C, "temp_crit": TEMP_CRIT_C,
                       "rtt_warn": RTT_WARN_MS},
    }
    out_json = REPORTS / f"V6_M5_BENCHMARK_{ts}.json"
    out_json.write_text(json.dumps({"summary": summary, "samples": samples}, indent=1),
                        encoding="utf-8")

    lines = [
        f"# V6 M5 — BENCHMARK PI5 {args.duration_min:g} PHÚT ({ts})",
        "",
        f"**Kết luận: {final}** — {len(samples)} mẫu, interval {args.interval_sec:g}s",
        "",
        "| Chỉ số | n | min | avg | p95 | max | Ngưỡng |",
        "|---|---|---|---|---|---|---|",
    ]
    for label, st, thr in [
        ("CPU Pi5 %", summary["cpu_pct"], f"WARN>{CPU_WARN_PCT:g} CRIT>{CPU_CRIT_PCT:g}"),
        ("CPU chromium %", summary["chromium_cpu_pct"], "-"),
        ("Nhiệt °C", summary["temp_c"], f"WARN>{TEMP_WARN_C:g} CRIT>{TEMP_CRIT_C:g}"),
        ("RTT LAN ms", summary["rtt_ms"], f"WARN>{RTT_WARN_MS:g}"),
    ]:
        if st:
            lines.append(
                f"| {label} | {st['n']} | {st['min']} | {st['avg']} | {st['p95']} | {st['max']} | {thr} |")
    # M5c: FPS THẬT (browser đẩy về) — chỉ báo nếu có dữ liệu
    fpss = [s["fps_measured"] for s in samples if isinstance(s.get("fps_measured"), (int, float))]
    if fpss:
        fst = stats(fpss)
        lines.append(f"| FPS measured (browser) | {fst['n']} | {fst['min']} | {fst['avg']} | "
                     f"{fst['p95']} | {fst['max']} | target 12-24 theo state |")
    lines += [
        "",
        f"- WARN 3 mẫu liên tiếp CPU≥{CPU_WARN_PCT:g}%: {'CÓ' if cpu3_consec_warn else 'KHÔNG'}",
        f"- Verdict mẫu: {summary['verdict_counts']}",
        f"- Throttle bits luôn 0: {'CÓ' if all((s.get('throttle_bits') or 0) == 0 for s in samples) else 'KHÔNG'}",
        "",
        f"Chi tiết: `{out_json.name}`",
    ]
    out_md = REPORTS / f"V6_M5_BENCHMARK_{ts}.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=1))
    print(f"Report: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
