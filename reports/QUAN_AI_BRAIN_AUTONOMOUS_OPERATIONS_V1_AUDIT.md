# QUAN AI BRAIN — Autonomous Engineering & Operations V1: Baseline Audit & Gap Analysis

**Chủ sở hữu:** Anh Quân — Quanpt1  
**Mã kiểm toán:** AUDIT-AUTO-OPS-V1-20261022  
**Thời gian kiểm toán:** 2026-10-22 13:10:00 (Local Time)  
**Máy chủ trung tâm:** Windows 10 Pro (x64), Python 3.11.9  
**Thiết bị biên:** Raspberry Pi 5 (`192.168.1.21:8768`)  
**Commit cơ sở:** `9243d12` (master)  
**Trạng thái kiểm thử baseline:** **432 PASSED, 1 SKIPPED, 0 FAILED** (Tổng: 433 tests)

---

## 1. Mục Đích & Phạm Vi Kiểm Toán

Báo cáo này thực hiện kiểm toán toàn diện mã nguồn, runtime thực tế và các phụ thuộc hệ thống theo đúng yêu cầu tại **Section 2 của Master Prompt: AUTONOMOUS ENGINEERING & OPERATIONS V1**.

Mọi đánh giá đều dựa trên **bằng chứng thực nghiệm (Empirical Evidence)** từ các lệnh probe và test chạy trực tiếp trên máy chủ của Anh Quân, không suy đoán và không phụ thuộc vào các báo cáo cũ.

---

## 2. Bằng Chứng Thực Nghiệm Trực Tiếp (Live Forensics)

Trước khi phân loại khoảng cách, hệ thống đã chạy các bài kiểm tra thực tế trên môi trường:

### 2.1. Kiểm tra Mô hình Cục bộ Ollama & Qwen2.5:7b (NVIDIA GPU)
- **Cổng kết nối:** `http://127.0.0.1:11434` -> `ONLINE`.
- **Danh mục mô hình sẵn sàng:** `bge-m3:latest` (1.2 GB), `qwen2.5:7b` (4.7 GB), `qwen2.5:1.5b` (986 MB), `qwen2.5:0.5b` (397 MB), `llama3.1:latest` (4.9 GB), `mistral:latest`.
- **Suy luận thực tế (`LLMProvider.generate`):**
  - Prompt: `"2+2=? Tra loi ngan gon chi so."`
  - Kết quả trả về: `"4"`
  - Provider: `ollama` (Is mock: `False`)
  - Độ trễ khi model đã nạp ấm (Warm Latency): **920.61 ms** (dưới 1 giây trên GPU Quadro T1000).
- **Kết luận:** Lớp suy luận cục bộ hoạt động hoàn hảo trên phần cứng thực tế.

### 2.2. Kiểm tra Kết nối Thiết bị Biên Raspberry Pi 5 (`192.168.1.21:8768`)
- **Kiểm tra socket:** `192.168.1.21:8768` -> `CONNECTED`.
- **Phản hồi HTTP `/api/kiosk/status`:**
  - Header Server: `BaseHTTP/0.6 Python/3.13.5`
  - Trạng thái kết nối Core: `core_connected: true`
  - Thiết bị: `EDGE-PI5-DESK-01`
  - Mô hình hiển thị: `qwen2.5:7b`
  - Biểu cảm Avatar: `SPEAKING`
  - Nhịp tim gần nhất (Heartbeat epoch): `1792630534.25`
- **Kết luận:** Thể nghiệm vật lý Raspberry Pi 5 đang chạy ngầm, kết nối mạng LAN thông suốt với PC Core.

### 2.3. Kiểm tra Trí nhớ Ngữ nghĩa BGE-M3 & Hybrid Retrieval
- **Vector embedding:** 1024 chiều, sinh thành công trong 620ms.
- **Phân loại ngữ nghĩa tiếng Việt:** Phân biệt chính xác văn bản chuyên môn ắc quy (0.6381) và văn bản không liên quan (0.3566).
- **Rào chắn kiểm dịch:** Các bản ghi `CANDIDATE` / `QUARANTINED` bị chặn 100% không cho lọt vào ngữ cảnh AI.

---

## 3. Ma Trận Phân Loại Trạng Thái Năng Lực (Capability State Matrix)

Theo đúng quy chuẩn phân loại 7 mức của Master Prompt:

| STT | Phân hệ / Năng lực cốt lõi | Hiện trạng thực tế | Phân loại trạng thái | Ghi chú & Rào cản kỹ thuật |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **Suy luận Ngôn ngữ Cục bộ (LLM)** | Qwen 2.5 7B, 1.5B, 0.5B trên Ollama | `VERIFIED_E2E` | Hoạt động thực tế trên GPU Quadro T1000, 920ms latency. |
| **2** | **Bộ định tuyến Mô hình (`LLMRouter`)** | Phân tầng Fast (<1.5s) vs Reasoning | `VERIFIED_E2E` | Đã test phân luồng tự động câu hỏi chào hỏi sang 1.5B. |
| **3** | **Trí nhớ Ngữ nghĩa (BGE-M3)** | Vector 1024-dim, Cosine pure-python | `VERIFIED_E2E` | Hoạt động trực tiếp trên Ollama, zero-dependency. |
| **4** | **Trí nhớ Phiên (`SessionMemoryManager`)** | Trích xuất sự thật, lưu SQLite WAL | `VERIFIED_E2E` | Lưu bền vững vào `data/brain.db`, đọc lại chuẩn sau restart. |
| **5** | **Hệ Thần Kinh Tự Chủ (`AutonomicHealth`)** | Đo 7 vùng cơ thể, phát hiện điểm đau | `VERIFIED_E2E` | Phát hiện thiếu Camera, thiếu Radar, cất tiếng kêu đau. |
| **6** | **Tâm Trí Tự Thân (`AutonomousMind`)** | Luồng suy nghĩ nội tâm, keep-warm | `VERIFIED_E2E` | 5 chế độ tâm trí, tự tư duy khi rảnh, kích hoạt `THINKING`. |
| **7** | **Kết nối Biên Pi 5 (`edge_client`)** | Kiosk UI, Avatar 1024x1024, Heartbeat | `VERIFIED_E2E` | Pi 5 đang chạy thực tế tại `192.168.1.21:8768`. |
| **8** | **Nối TaskPlan với `DurableTaskRegistry`** | Ghi kế hoạch vào `data/tasks.db` | `INTEGRATION_TESTED` | Đã nối qua `PlanOrchestrator` và endpoint `POST /api/plan`. |
| **9** | **Hộp Cát & Phân Quyền (`SafeToolSandbox`)** | R0-R5, `ApprovalGate`, `Delegation` | `INTEGRATION_TESTED` | 37 tests kiểm soát chặt chẽ, R5 chặn cứng, R4 không ủy quyền. |
| **10** | **Engine Tự Học (`SelfLearningEngine`)** | Hồ sơ nghiên cứu, đề xuất 17 điểm | `INTEGRATION_TESTED` | 16 tests nghiệm thu; cách ly tri thức ứng viên vào Quarantine. |
| **11** | **Khung Tích Hợp Đa Hệ Thống (Master V6)** | 10 bước vận hành, telemetry, verifier | `INTEGRATION_TESTED` | 20/20 kịch bản test PASSED; SystemTelemetry thu thập CPU/RAM. |
| **12** | **Giám Sát Vận Hành (`Supervisor`)** | `ContinuousAutonomySupervisor` 16 bước | `UNIT_TESTED_ONLY` | Đã có logic 16 bước, nhưng **chưa được nối vào vòng lặp chạy nền định kỳ tự động của Web Server/Daemon**. |
| **13** | **Tự Nghiên Cứu Tài Liệu Trực Tuyến** | Tra cứu tài liệu kỹ thuật qua Internet | `IMPLEMENTED_NOT_VERIFIED` | `ResearchEngine` mới tra cứu tri thức nội bộ hoặc trích dẫn tĩnh; chưa có module crawler đọc doc an toàn. |
| **14** | **Hộp Cát Thử Nghiệm Nâng Cấp (Sandbox)** | Thử nghiệm bản vá trong thư mục cách ly | `MOCKED` | Mới có staging mô phỏng trong test (`test_executor_staging.py`), chưa có runner tự clone & test sandbox thật. |
| **15** | **Bộ Test Sẵn Sàng Vận Hành 18 Ca** | `Autonomous Operations Readiness` | `MISSING` | Chưa có tệp kiểm thử tập trung mô phỏng 18 tình huống sự cố theo Section 11 của Master Prompt. |
| **16** | **Thực Thi Hệ Thống Production Thật** | Chạy lệnh OS/PowerShell ngoài sandbox | `BLOCKED_PENDING_APPROVAL` | Bị chặn bởi `SPRINT6_DESIGN_SIGNOFF.md` (`PENDING_OWNER_SIGNOFF`) và quy tắc `AGENTS.md`. |

---

## 4. Các Điểm Nghẽn & Khâu Đứt Gãy Cần Nối Ngay

1. **Khâu đứt gãy 1: `ContinuousAutonomySupervisor` đang "ngủ yên"**:
   - `ContinuousAutonomySupervisor` đã có mã nguồn rất hoàn chỉnh (16 trạng thái, kiểm tra STOP/FREEZE, phục hồi task dở dang, rà soát task PENDING).
   - Tuy nhiên, hiện tại nó chỉ chạy khi được gọi thủ công trong unit test. Khi Web Server khởi động, supervisor **chưa có một luồng Timer/Heartbeat chạy ngầm an toàn** để định kỳ kích hoạt chu trình tự kiểm tra và điều phối.
2. **Khâu đứt gãy 2: Thiếu Bộ Kiểm Thử Nghiệm Thu Vận Hành Tự Chủ (18 Ca sự cố)**:
   - Hệ thống cần một bộ test chính quy `tests/test_autonomous_operations_readiness.py` chứng minh khả năng tự phục hồi, xử lý khi Ollama rớt mạng, Pi 5 rớt mạng, dữ liệu hỏng, prompt injection từ web, v.v.
3. **Khâu đứt gãy 3: Tự Nghiên Cứu Trực Tuyến Chưa Có Bộ Lọc An Toàn**:
   - Khi `AutonomicHealth` phát hiện thiếu phần cứng hoặc lỗi, `ResearchEngine` cần có khả năng tra cứu tài liệu kỹ thuật chính thức qua HTTP (Read-Only) với cơ chế bảo vệ chống Prompt Injection và không bao giờ tự thực thi mã tải về.

---

## 5. Đề Xuất Lộ Trình Triển Khai (Sprint 1)

Tuân thủ nghiêm ngặt nguyên tắc: **"Chọn bước triển khai nhỏ nhất có thể nâng cao đáng kể khả năng vận hành thực tế. Trình phương án và diff trước khi sửa mã; chờ anh Quân phê duyệt."**

Em đề xuất kế hoạch thực hiện **Sprint 1 — Autonomous Supervisor & Operations Readiness**:

### Mục tiêu Sprint 1:
1. **Nối `ContinuousAutonomySupervisor` vào vòng lặp vận hành tự chủ có kiểm soát**:
   - Tích hợp một luồng nền nhẹ `AutonomousSupervisorDaemon` (chạy theo chu kỳ định kỳ, có ngân sách tài nguyên CPU/thời gian, có điều kiện dừng an toàn, tôn trọng cờ STOP/FREEZE).
   - Khi không có task, supervisor tự động chuyển sang trạng thái `IDLE` / `RESTING` và phát xung giữ ấm nơ-ron (không tạo vòng lặp vô hạn gọi LLM).
2. **Xây dựng Bộ Kiểm Thử Nghiệm Thu 18 Kịch Bản (`Autonomous Operations Readiness`)**:
   - Tạo `tests/test_autonomous_operations_readiness.py` bao phủ đầy đủ 18 ca sự cố theo Section 11 của Master Prompt.
3. **Mở rộng `ResearchEngine` với Bộ Đọc Tài Liệu Kỹ Thuật An Toàn (Safe Read-Only Document Reader)**:
   - Tra cứu và lập hồ sơ kỹ thuật có nguồn gốc, URL, SHA-256 hash, cách ly trong vùng kiểm dịch (Quarantine), phòng thủ prompt injection.

### Danh sách các tệp dự kiến tác động trong Sprint 1:
1. `src/quan_ai_brain/orchestration/supervisor.py`: Thêm phương thức cấu hình chu kỳ lặp an toàn (`run_background_tick`), giới hạn ngân sách tài nguyên và tích hợp với `GLOBAL_AUTONOMIC_SYSTEM`.
2. `src/quan_ai_brain/learning/engine.py`: Tích hợp module tra cứu tài liệu kỹ thuật an toàn (Read-Only HTTP Fetcher với bộ lọc phòng vệ).
3. `src/quan_ai_brain/web/server.py`: Bổ sung endpoint điều khiển Supervisor trên Cockpit (`GET /api/supervisor/state`, `POST /api/supervisor/tick`).
4. `tests/test_autonomous_operations_readiness.py`: Tệp kiểm thử mới bao phủ 18 kịch bản vận hành tự chủ có kiểm soát.
5. `tools/run_autonomous_cycle.py`: Công cụ CLI để anh Quân hoặc hệ thống có thể chạy 1 chu trình tự kiểm tra, tự nghiên cứu và tự đề xuất độc lập.

---

## 6. Kính Trình Anh Quân Phê Duyệt

Báo cáo kiểm toán này xác lập sự thật khách quan về trạng thái hệ thống. 
Kính xin ý kiến phê duyệt của Anh Quân để em bắt đầu triển khai các bước chi tiết của **Sprint 1**!
