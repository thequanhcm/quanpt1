# KIỂM TRA TOÀN BỘ TAB DASHBOARD QUAN AI BRAIN — 06/11/2026 20:15

## A. 4 tab Chrome (ảnh 19:03)
| Tab | Trang | Trạng thái |
|---|---|---|
| TONY - Viettel Networks VTNet | (không xác định được — favicon đỏ tròn) | UNKNOWN — cần anh mở tab đó nói em biết URL |
| Phòng Điều Khiển = **Phòng Điều Hành & Tham Vấn Chủ Nhân** | 127.0.0.1:8766 | ✅ LIVE |
| Trợ Lý Điều Khiển = **Trợ Lý Điều Hành Số** | 127.0.0.1:8765 | ✅ LIVE |
| Hoangology English | (bookmark cá nhân) | ngoài phạm vi TONY |

## B. 10 tab trong dashboard 8766 (executive) — kết quả gọi API thật từng tab
| # | Tab | Endpoint chính | Kết quả |
|---|---|---|---|
| 1 | Nhân Sự Số | persona / roles / capabilities | ✅ OK — persona "TONY PHAM" đầy đủ |
| 2 | Tham Vấn & Duyệt | consultations / approvals | ✅ OK |
| 3 | Báo Cáo Tự Học | learning/reports / improvement/report / experience/lessons | ✅ OK — có báo cáo kỳ 4 (27/10) |
| 4 | Điều Hành & An Toàn | supervisor / tasks / status | ✅ OK — supervisor READY |
| 5 | Hội Thoại Trực Tiếp | todos / voice/wake-config | ✅ OK |
| 6 | Kênh NetChat | netchat/status + messages | ✅ OK — kênh "Trợ lý Tony Pham" |
| 7 | Đồng Bộ Pi 5 | edge/telemetry + edge/files | ✅ OK — heartbeat 1.36s, RTT 160ms, files list OK |
| 8 | Hình Thể Pi 5 | edge/audio/status + edge/camera/status + library | ✅ OK — Jieli UACDemoV1.0, IMX708, 6 ảnh lưu |
| 9 | Workbench | workbench/overview + tasks | ✅ OK — 50 tasks (1 verified, 2 completed, 47 cancelled) |
| 10 | Trí Nhớ Sâu V9 | /api/memory/deep/* + /api/memory/review/* | ❌ **404 — SERVER CHƯA CÓ ROUTE** |

## C. 2 điểm mâu thuẫn trong ảnh — GIẢI THÍCH + TRẠNG THÁI GIỜ
1. **Audio "Chưa kiểm tra/-60dB" vs banner "-18.2dB"**: banner là kết quả test cũ trong phiên; ô thông số chỉ cập nhật khi bấm "KIỂM TRA MICRO" hoặc poll. **GIỜ API trả: mic_enabled=true, wake_word=TRUE, level -18.0dB, READY** — state đã đồng bộ, wake word đang BẬT (khác ảnh vì sau đó có thao tác bật).
2. **Camera badge OFF nhưng frame "LIVE"**: frame trong khung là **ảnh cuối cùng lưu trong bộ đệm** (last_timestamp 13:09), badge OFF = đúng camera_enabled=false GIỜ (privacy) — fail-honest, không phải lỗi. **KHUYẾN NGHỊ**: khi camera OFF, khung preview nên hiện "CAMERA OFF — hiển thị frame cuối 13:09" thay vì nhãn "TRỰC TIẾP (LIVE)" gây hiểu nhầm.
3. **Alert "LỖI THIẾT BỊ CAMERA PI 5" (ALERT_H_CAMERA_FAULT)**: cảnh báo từ lần snapshot khi camera chưa warm-up (20:09) — camera hoạt động bình thường sau đó (58.550B OK). Cần nút xóa alert/stale.
4. **Kiosk Pi (8768)**: core_connected=True nhưng avatar **SLEEPING / STANDBY** — đúng (màn Pi đang nghỉ, kiosk chờ tương tác).

## D. Lỗi cần sửa (chờ anh duyệt)
1. **Tab 10 Trí Nhớ Sâu V9 chết**: JS gọi 6 endpoint `/api/memory/deep/*` + `/api/memory/review/*` nhưng server.py chưa implement → tab trắng/404. Cần: implement route (đọc data/knowledge_db) HOẶC ẩn tab (fail-honest).
2. Nhãn "TRỰC TIẾP (LIVE)" khi camera OFF → đổi "FRAME CUỐI (hh:mm)".
3. Alert H camera fault stale → tự xóa khi camera status OK lại.


## E. Cập nhật 06/11 tối: UI báo ĐÚNG hiện trạng mô hình (lệnh owner "update đúng hiện trạng mô hình netmind đang sử dụng")

Hiện trạng thật (verify qua /api/status):
- Runtime CHÍNH = **NetMind Cloud** (`stream-netmind.viettel.vn/aigw`) — model **zai-org/GLM-5.3-Flash** (status READY, catalog_reachable)
- **Ollama ĐÃ GỎ** khỏi máy (ollama_online=false — tcp_probe 11434 timeout) → chấm đỏ "Local Ollama — Chưa kết nối" là gây hiểu nhầm
- available_models của NetMind: MiniMax-M3, Qwen3.6-35B, Qwen3.5-122B, GLM-5.3-Flash
- Chat E2E: POST /api/chat → provider=netmind, model=GLM-5.3-Flash, is_mock=false, trả lời "OK" 3.7s ✓

Đã sửa (3 file, chưa commit):
1. **index.html**: widget "Local Ollama" → **"Suy luận (LLM)"**; default hiển thị zai-org/GLM-5.3-Flash; subtitle bỏ "(Ollama local khi khả dụng)"; dropdown 4 model NetMind Cloud (bỏ 2 model qwen local đã gỡ)
2. **app.js updateSystemStatus**: hiển thị PROVIDER ĐANG PHỤC VỤ (NetMind Cloud — xanh) thay vì trạng thái Ollama; dropdown nạp models từ `data.llm.netmind.available_models` (fallback ollama list); label "— NetMind Cloud" / "Không có runtime (cần Cloud hoặc cài lại Ollama)" khi cả 2 chết
3. node --check app.js OK; static serve từ disk — trình duyệt chỉ cần refresh (Ctrl+F5)

Trạng thái sau sửa (trên 8765):
- Widget: 🟢 Suy luận (LLM) — **NetMind Cloud (GLM-5.3-Flash)** — Model active: zai-org/GLM-5.3-Flash — NetMind Cloud
