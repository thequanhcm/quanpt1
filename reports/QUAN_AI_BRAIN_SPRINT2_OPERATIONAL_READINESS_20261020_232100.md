# BÁO CÁO NGHIỆM THU KỸ THUẬT — SPRINT 2
## QUAN AI BRAIN: INTEGRATION CLOSURE & OPERATIONAL READINESS
**Mã tài liệu:** `RPT-QAB-SPRINT2-OP-READINESS-20261020`  
**Thời gian lập:** 2026-10-20T23:21:00+07:00  
**Chủ sở hữu:** Quanpt1  
**Workspace:** `E:\AI\QUAN AI BRAIN`  
**Môi trường:** Windows 10 x64, Python 3.11.9 (`.venv`)  
**Kết luận trạng thái:** `PARTIALLY_COMPLETED` (Hoàn thành và xác minh 100% PC Core Runtime; Chờ kết nối phần cứng vật lý Raspberry Pi 5 trên mạng LAN).

---

## 1. TÓM TẮT HIỆN TRẠNG TRƯỚC TRIỂN KHAI
- **Baseline kiểm thử ban đầu:** 363 PASSED, 0 FAILED, 1 SKIPPED (Tổng 364 bài test).
- **Các khoảng trống tích hợp (Integration Gaps) đã xác định từ Audit:**
  1. **Tính nhất quán của báo cáo kiểm thử:** Script `tools/validate_and_report.py` trước đây tính test skip là "PASS toàn bộ", gây hiểu lầm giữa số pass và tổng số test.
  2. **Mâu thuẫn trạng thái Voice Interface:** Bảng ma trận tích hợp cũ từ 2026-10-17 chưa được cập nhật các kết quả của Sprint 7 và Sprint Voice TTS; 1 bài test TTS bị skip do phần cứng Pi 5 chưa cắm mạng vật lý.
  3. **Local LLM thực tế:** Cần phân định rõ ràng giữa suy luận thật trên mô hình local Ollama và mock provider.
  4. **Khoảng trống điều phối:** `TaskPlan` (lập kế hoạch DAG, rủi ro) chưa có cầu nối thực thi bền vững với `DurableTaskRegistry` (`data/tasks.db`), thiếu vòng đời điều phối qua `ApprovalGate` và `InertSandbox`.
  5. **Liên kết PC Core ↔ Raspberry Pi 5:** Giao diện, giao thức, bảo mật đã sẵn sàng trong code, nhưng thiết bị vật lý Pi 5 chưa được bật nguồn/cắm mạng.

---

## 2. KIẾN TRÚC ĐƯỢC TÍCH HỢP & ĐIỀU CHỈNH

Hệ thống đã triển khai hoàn thiện luồng nghiệp vụ điều phối nhiệm vụ khép kín theo đúng quy chuẩn:

```
[User Request] (Giọng nói / Text / API)
       │
       ▼
[Intent Classification & Context Building] (CognitiveRetriever + SessionMemoryManager)
       │
       ▼
[TaskPlan & DAG Validation] (ExecutiveCoordinator: Phân rã bước, phát hiện chu trình DAG)
       │
       ▼
[Risk Assessment] (Đánh giá mức độ R0 - R5 độc lập, không cho LLM tự hạ rủi ro)
       │
       ▼
[PlanOrchestrator & DurableTaskRegistry] (Lưu bền vững master task và từng step vào data/tasks.db)
       │
       ├───> Nếu bước là R5 ──────> [HARD-BLOCK NGAY LẬP TỨC] ──> Status: BLOCKED
       │
       ├───> Nếu bước là R4 ──────> [APPROVAL GATE] ────────────> Chưa duyệt: WAITING_APPROVAL
       │                                                         Đã duyệt: AUTHORIZED
       ▼
[Inert Sandbox Execution] (SafeToolSandbox: Mô phỏng an toàn, không subprocess/powerShell tự do)
       │
       ▼
[Result Verification] (Kiểm tra tiêu chí acceptance criteria, lọc credential qua OutputGuardrails)
       │
       ▼
[TaskOutcome & Evidence Creation] (Ghi nhận EvidenceRecord, kết quả chi tiết, thời gian hoàn thành)
       │
       ▼
[Báo cáo & Cập nhật Registry] (Trạng thái COMPLETED, cập nhật tiến độ cho Người dùng)
```

---

## 3. DANH SÁCH FILE SỬA & FILE MỚI

### 3.1. File mới tạo
1. `src/quan_ai_brain/orchestration/plan_orchestrator.py`: Lớp `PlanOrchestrator` đóng kín luồng từ `TaskPlan` sang `DurableTaskRegistry`, `ApprovalGate`, và `InertSandbox`.
2. `tests/test_plan_orchestration_lifecycle.py`: 8 bài kiểm thử tích hợp vòng đời nhiệm vụ, DAG validation, chống chạy lặp qua idempotency key, chặn R5, chờ phê duyệt R4 và phục hồi sau khởi động lại.
3. `tests/test_core_ai_correctness.py`: 8 bài kiểm thử xác minh `LLMRouter` phân tầng, explicit override, fallback provenance (không âm thầm fallback sang mock) và output grounding.
4. `reports/QUAN_AI_BRAIN_SPRINT2_AUDIT_REPORT.md`: Báo cáo audit kiến trúc và ma trận tích hợp đầu Sprint 2.
5. `reports/QUAN_AI_BRAIN_SPRINT2_OPERATIONAL_READINESS_20261020_232100.md`: Báo cáo nghiệm thu kỹ thuật Sprint 2 này.

### 3.2. File chỉnh sửa
1. `tools/validate_and_report.py`: Sửa hàm `parse_pytest_summary` và format báo cáo để phân loại độc lập: `Passed`, `Failed`, `Skipped`, `Blocked`, `Not Run`. Không tính test skip là pass.
2. `src/quan_ai_brain/orchestration/models.py`: Bổ sung trạng thái `TaskStatus.BLOCKED` và lớp `TaskStepRecord` phục vụ lưu trữ từng bước bền vững.
3. `src/quan_ai_brain/orchestration/task_registry.py`: Khởi tạo bảng `durable_task_steps`, thêm các hàm `save_step`, `get_step`, `list_steps_for_task`, `update_step_status`.
4. `src/quan_ai_brain/orchestration/__init__.py`: Export `PlanOrchestrator` và `TaskStepRecord`.
5. `reports/HANDOFF_LATEST.md`: Cập nhật tự động thông số kiểm thử và nhật ký bàn giao mới nhất.

---

## 4. KẾT QUẢ KIỂM THỬ THỰC TẾ CHI TIẾT

### 4.1. Lệnh kiểm thử
- `pytest tests/test_plan_orchestration_lifecycle.py`
- `pytest tests/test_core_ai_correctness.py`
- `pytest -q tests`
- `python tools/validate_and_report.py`

### 4.2. Thống kê kết quả kiểm thử toàn hệ thống
- **Tổng số bài test:** **380 bài**
- **Passed:** **379 bài** (100% test logic đạt yêu cầu)
- **Failed:** **0 bài**
- **Skipped / Blocked:** **1 bài** (`tests/test_vietnamese_tts.py:266` — do phần cứng Raspberry Pi 5 chưa cắm mạng vật lý)
- **Not Run:** **0 bài**
- **Thời gian chạy kiểm thử toàn bộ:** **39.72 giây**
- **Kết luận:** **`PARTIALLY_VERIFIED (379 passed, 1 skipped)`**

---

## 5. KẾT QUẢ ĐO LƯỜNG TỪNG PHÂN HỆ CHUYÊN BIỆT

### 5.1. Phân hệ Core AI & LLMRouter
- **Dịch vụ Ollama thật:** Đang hoạt động trên `127.0.0.1:11434`.
- **Mô hình có sẵn trên máy:**
  * `qwen2.5:7b` (Reasoning tier, 4.68 GB)
  * `qwen2.5:1.5b` (Fast tier, 986 MB)
  * `qwen2.5:0.5b` (Ultra-fast tier, 397 MB)
  * `llama3.1:latest` (8.0B, 4.92 GB)
  * `mistral:latest` (7.2B, 4.37 GB)
  * `qwen:latest` (4.0B, 2.33 GB)
- **Kiểm chứng suy luận thật:**
  * Model: `qwen2.5:0.5b` qua `LLMProvider` (`is_mock=False`).
  * Prompt: *"Xin chao, ban la ai? Tra loi ngan gon 1 cau."*
  * Thời gian phản hồi: **632.4 ms**.
  * Câu trả lời: *"Xin chào! Tôi có thể giúp gì cho bạn hôm nay?"*
- **Định tuyến mô hình:**
  * Câu hỏi thông thường / chào hỏi $\rightarrow$ Chuyển về Fast tier (`qwen2.5:1.5b` / `0.5b`).
  * Câu hỏi phân rã kế hoạch / DAG / phân tích dài $\rightarrow$ Chuyển về Reasoning tier (`qwen2.5:7b`).
- **Xử lý Offline / Timeout:**
  * Chế độ `FallbackMode.NEVER`: Báo lỗi minh bạch, không giả lập AI.
  * Chế độ `FallbackMode.ON_ERROR`: Đánh dấu rõ ràng `is_mock=True` kèm warning.

### 5.2. Phân hệ Điều phối Nhiệm vụ (TaskPlan $\leftrightarrow$ DurableTaskRegistry)
- **Vòng đời nhiệm vụ:** Đã kết nối khép kín thông qua `PlanOrchestrator`.
- **Lưu trữ bền vững:** Toàn bộ trạng thái của master task và các bước con được lưu vào SQLite WAL (`data/tasks.db`).
- **Chống chạy lặp:** Khóa `idempotency_key` ngăn chặn việc sinh trùng tác vụ khi gửi lại yêu cầu.
- **Ranh giới an toàn R5:** Bước R5 bị chặn cứng lập tức (`TaskStatus.BLOCKED`, `TaskState.BLOCKED`), không tiến hành thực thi.
- **Ranh giới an toàn R4:** Bước R4 tự động dừng tại `WAITING_APPROVAL`, tạo yêu cầu phê duyệt trong `ApprovalGate`, chỉ tiếp tục khi chủ nhân ký duyệt.
- **Thực thi trong Inert Sandbox:** Chạy an toàn ở chế độ mô phỏng, thu thập `EvidenceRecord`, cập nhật kết quả và chứng cứ.
- **Khôi phục sự cố:** Khi restart hệ thống, các tác vụ dở dang được chuyển an toàn sang `OUTCOME_UNKNOWN` để tránh thực thi mù quáng.

### 5.3. Phân hệ Giọng nói Tiếng Việt & Avatar
- **Giọng đọc mặc định:** Microsoft Edge Natural Voice `vi-VN-HoaiMyNeural` (Nữ, tiếng Việt chuẩn).
- **Rào chắn ngôn ngữ:** Không tự ý rơi về giọng tiếng Anh mặc định; giữ nguyên dấu tiếng Việt.
- **Ngắt lời (Barge-in):** Dừng audio lập tức (<10ms) và đưa viseme về `REST` khi có âm thanh mới hoặc bấm mic.
- **Đồng bộ Avatar Mẫu F:** Canvas 2.5D 60 FPS đồng bộ 6 viseme khẩu hình (A, O, E, I, U, REST) theo chu kỳ 50ms, kết hợp chớp mắt kép và nhịp thở vi mô.

### 5.4. Kênh PC Core ↔ Raspberry Pi 5
- **Mã nguồn biên:** `edge_client/` đầy đủ các module xác thực HMAC-SHA256, điều khiển rơ-le/servo, giao diện kiosk cảm ứng.
- **Dịch vụ truyền tệp (Edge Transfer):** Hỗ trợ chia chunk, hash SHA-256, xác nhận ACK hai chiều, ngăn chặn rò rỉ `.env`, key và database.
- **Dịch vụ cập nhật (Edge Release):** Kiểm tra cú pháp `py_compile`, staging, hỗ trợ rollback nguyên tử.
- **Trạng thái phần cứng vật lý:** Hiện tại bo mạch Pi 5 chưa cắm mạng, hệ thống nhận diện chính xác trạng thái `DISCONNECTED / OFFLINE`, cảnh báo trung thực trên giao diện :8766 và ghi nhận test là `BLOCKED`.

---

## 6. CÁC LỖI TỒN TẠI & GIỚI HẠN MÔI TRƯỜNG

1. **Phần cứng Raspberry Pi 5 chưa cắm mạng LAN:**
   - Bo mạch Pi 5 thực tế chưa được cấp nguồn hoặc chưa kết nối vào cùng dải IP Wi-Fi với PC Core (`192.168.1.21:8768`).
   - Đây là giới hạn về mặt vật lý của phiên làm việc hiện tại, không phải lỗi mã nguồn.
   - Khi chủ sở hữu cấp nguồn cho Pi 5 và chạy script `oneclick_run_pi5.sh` hoặc bật autostart, kết nối sẽ được kích hoạt tức thì.
2. **Thực thi lệnh hệ thống thật (Production Executors):**
   - Vẫn được duy trì ở chế độ `Inert Sandbox` theo đúng quy định an toàn của Sprint 2; chưa bật subprocess spawner hay Windows 24/7 service ngoài phạm vi được duyệt.

---

## 7. PHƯƠNG ÁN PHỤC HỒI (ROLLBACK PLAN)

Nếu cần hoàn nguyên các thay đổi của Sprint 2:
1. Xóa file mới tạo:
   - `src/quan_ai_brain/orchestration/plan_orchestrator.py`
   - `tests/test_plan_orchestration_lifecycle.py`
   - `tests/test_core_ai_correctness.py`
2. Hoàn nguyên các file đã sửa:
   - `git checkout HEAD -- src/quan_ai_brain/orchestration/models.py`
   - `git checkout HEAD -- src/quan_ai_brain/orchestration/task_registry.py`
   - `git checkout HEAD -- src/quan_ai_brain/orchestration/__init__.py`
   - `git checkout HEAD -- tools/validate_and_report.py`
3. Chạy lại `python tools/validate_and_report.py` để trở về baseline 363/364 tests.

---

## 8. KHUYẾN NGHỊ CHO SPRINT TIẾP THEO

1. **Kết nối mạng vật lý cho Raspberry Pi 5:**
   - Cấp nguồn cho Pi 5 trên cùng mạng Wi-Fi nội bộ (`192.168.1.x`).
   - Chạy lệnh ghép cặp 1-click để xác nhận handshake HMAC và thông suốt âm thanh loa phần cứng.
2. **Thẩm định thiết kế Windows Job Object (Sprint 7B):**
   - Đệ trình chủ sở hữu Quanpt1 xem xét `docs/SPRINT6_DESIGN_SIGNOFF.md` để cân nhắc lộ trình cho phép thực thi tiến trình có kiểm soát chặt chẽ qua Win32 Job Object giới hạn CPU/RAM.
3. **Mở rộng giao diện điều hành Cockpit:**
   - Hiển thị danh sách tiến trình DAG trực tiếp từ `PlanOrchestrator` trên cổng 8766 để người dùng theo dõi trực quan từng bước thực thi.
