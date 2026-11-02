# QPIG_V2_LIVE_DEMO.md — Bằng chứng chạy thật PHASE 1 (02/11/2026)

Phần cứng thật: LAN 192.168.1.0/24 (máy QUANPT, không mock).

## Kết quả 5 bước demo (tool call thật qua QPIG.call())

| # | Tool chuẩn §2 | Kết quả thật |
|---|---|---|
| 1 | DEVICE_DISCOVERY | 8 thiết bị sống @ 192.168.1.0/24 |
| 2 | NETWORK_INSPECTION 192.168.1.2 (Pi5) | REACHABLE, latency 2 ms |
| 3 | DEVICE_IDENTIFICATION Pi5 | Cổng mở: **[]** — SSH 22 ĐÓNG (chờ owner mở), fail-honest không suy diễn |
| 4 | AGENT_STATUS edge_pi5 | REACHABLE (NodeRegistry probe thật) |
| 5 | EVIDENCE_COLLECTION + ACTION_VERIFICATION | evidence #1 lưu brain data + đối chiếu ngược OK, payload SHA-256 |

## Danh mục (§2 — trung thực)

- 25 tool đăng ký = **19 chuẩn QPIG V2.0** + 6 alias UAIIF-S4 v1 (backward-compat)
- Operational: **10** (4 Phase 1 vừa chạy thật + 6 v1 đã chạy sprint trước)
- Chưa E2E: **15** — khai báo `operational=false`, KHÔNG fake kết quả

## Cơ chế an toàn chứng minh bằng test (9/9 tests/test_qpig_v2.py)

- §4 Engine 11 bước: thiếu approval → dừng ở CHECK_APPROVAL, không EXECUTE, không evidence
- §6 Token một-lần: tái sử dụng `ap-001` → refuse "đã dùng"
- §6 Token gắn tool: fingerprint sai mục đích → refuse
- §8 Isolation chỉ TẠO card R4 chờ Quanpt1 — không tự cô lập
- §3 Adapter: payload vượt grant/byte → refuse; 7 adapter có sẵn, 6 giao thức (USB/UART/
  RS485/Bluetooth/BACnet/Modbus) khai báo PENDING — không giả lập

## Card phê duyệt

`appr_de50ca6a6a00` — PENDING | R4 | hết hạn 2026-11-03T11:30:17Z | scope: qpig.py,
registry.py, test_qpig_v2.py, test_uaiif_s4.py
