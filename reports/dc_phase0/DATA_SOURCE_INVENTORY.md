# DATA_SOURCE_INVENTORY — CHERRY DC PHASE 0 (07/11/2026)
Nguồn dữ liệu THẬT đang nối vào QUAN AI BRAIN / CHERRY (audit chỉ-đọc, mode=ro):

| Nguồn | Loại | Trạng thái | Ghi chú |
|---|---|---|---|
| NetChat DM bot_tony | Tin nhắn 2 chiều | LIVE | kênh DM duy nhất |
| Pi5 edge mesh 100.100.83.59 | Edge telemetry + camera + actuator | LIVE | kiosk/camera/wake/UDC-1 |
| LLM NetMind Cloud GLM-5.3-Flash | LLM + Vision | LIVE | base64 ảnh |
| 30 SQLite DB runtime (brain.db 97MB…) | Nội bộ | LIVE | health/tasks/governance/sentinel/learning |
| BMS/DCIM/SCADA/EMS/EPMS | Protocol feed | **KHÔNG CÓ** | R-01 — cấm tuyên bố realtime DC |
| UPS/Battery feed | Telemetry | **KHÔNG CÓ** | R-02 Battery AI không có trên máy |
| kho_tai_lieu PDL (1.500 file) | Tài liệu DC tĩnh | CÓ, CHƯA ingest | SLD/BMS/enteliWEB/UPS/PCCC |
| document_index.db | Index tài liệu | 6 chunks | chỉ phần test ban đầu |

Kết luận: đủ dữ liệu cho PHASE 1 (kiến thức); PHASE 2+ cần feed thật do owner cấp.
