"""Root Cause Analysis Engine — phân biệt FACT / POSSIBLE / CONFIRMED (M1.8).

Đầu vào: snapshot hợp nhất từ aggregator. Đầu ra: danh sách nhận định mỗi
nhận định gắn nhãn rõ ràng:
- OBSERVED_FACT: dữ liệu đo thấy trực tiếp.
- POSSIBLE_CAUSE: giả thuyết nguyên nhân có căn cứ (CHƯA xác nhận).
- CONFIRMED_CAUSE: nguyên nhân có bằng chứng xác nhận (hiện tại hầu như
  không bao giờ gán nếu thiếu bằng chứng chuyên sâu — fail-honest).
- INSUFFICIENT_EVIDENCE: không đủ dữ kiện để kết luận.

KHÔNG tự chuyển POSSIBLE_CAUSE thành CONFIRMED_CAUSE (quy tắc master prompt).
"""
from __future__ import annotations

from typing import Any

FACT = "OBSERVED_FACT"
POSSIBLE = "POSSIBLE_CAUSE"
CONFIRMED = "CONFIRMED_CAUSE"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"


def build_rca(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Sinh nhận định RCA từ snapshot. Thuần suy luận từ số liệu có mặt —
    không đoán dữ liệu không có."""
    out: list[dict[str, Any]] = []
    checks = {
        "pc": snapshot.get("pc", {}).get("checks", {}),
        "pi5": snapshot.get("pi5", {}).get("checks", {}),
        "network": snapshot.get("network", {}).get("checks", {}),
        "services": snapshot.get("services", {}).get("checks", {}),
        "databases": snapshot.get("databases", {}).get("checks", {}),
        "voice": snapshot.get("voice", {}).get("checks", {}),
    }

    def add(severity_label: str, kind: str, component: str, statement: str,
            evidence: str, suggested_action: str = "") -> None:
        out.append({
            "label": severity_label,
            "kind": kind,
            "component": component,
            "statement": statement,
            "evidence": evidence,
            "suggested_action": suggested_action,
        })

    # ---- FACT: mọi chỉ số WARNING/CRITICAL là dữ kiện đo thấy ----
    for comp, comp_checks in checks.items():
        for check_id, info in comp_checks.items():
            sev = info.get("severity")
            if sev in ("WARNING", "CRITICAL"):
                add(sev, FACT, comp,
                    f"{check_id} = {info.get('value')} ({sev})",
                    f"measured_at={info.get('measured_at')}")

    # ---- UNKNOWN: thiếu dữ liệu ----
    for comp, comp_checks in checks.items():
        for check_id, info in comp_checks.items():
            if info.get("severity") == "UNKNOWN":
                add("UNKNOWN", INSUFFICIENT, comp,
                    f"{check_id}: không đo được",
                    f"reason={info.get('reason')}")

    # ---- POSSIBLE CAUSE: suy luận có căn cứ, KHÔNG khẳng định ----
    pi5 = checks.get("pi5", {})
    if pi5.get("soc_temp_c", {}).get("value") is not None:
        temp = pi5["soc_temp_c"]["value"]
        if isinstance(temp, (int, float)) and temp >= 65:
            add("INFO", POSSIBLE, "pi5",
                f"Nhiệt độ SoC {temp}°C cao dần — có thể do tải hoặc tản nhiệt kém",
                f"temp={temp}; cần theo dõi xu hướng history để xác nhận")

    throttled = (pi5.get("throttled") or {}).get("value")
    if throttled and throttled not in ("0x0", "0x0."):
        add("WARNING", POSSIBLE, "pi5",
            f"Throttled flag {throttled} — dấu hiệu thiếu nguồn/quá nhiệt hiện tại",
            f"vcgencmd get_throttled={throttled}; bit nghiêm trọng cần decode; "
            "chưa kết luận nguyên nhân gốc (nguồn 5V vs nhiệt)")

    net = checks.get("network", {})
    rtt = (net.get("pc_to_pi5_rtt_ms") or {}).get("value")
    if isinstance(rtt, (int, float)) and rtt >= 150:
        add("WARNING", POSSIBLE, "network",
            f"RTT PC→Pi5 {rtt}ms cao hơn nền (thường ~30ms) — có thể do Tailscale "
            "đi relay DERP thay vì direct, hoặc mạng Wi-Fi tải nặng",
            f"rtt_ms={rtt}; cần 'tailscale status' để xác nhận direct/relay")

    db = checks.get("databases", {})
    brain = db.get("brain.db") or {}
    val = brain.get("value") or {}
    if isinstance(val, dict) and val.get("wal_mb", 0) and val["wal_mb"] > 50:
        add("INFO", POSSIBLE, "databases",
            f"WAL brain.db lớn ({val['wal_mb']}MB) — checkpoint chưa chạy đều",
            f"wal_mb={val['wal_mb']}; quan sát thêm trước khi đề xuất hành động")

    svc = checks.get("services", {})
    lh = (svc.get("learning_daemon_heartbeat") or {})
    if lh.get("severity") == "WARNING":
        add("WARNING", POSSIBLE, "services",
            "Learning daemon log mới nhất cũ hơn 150s — daemon có thể pause "
            "tạm thời (cycle dài) hoặc treo",
            f"log_age_sec={lh.get('value')}; cần xem learning_daemon.py.log để xác nhận")

    return out
