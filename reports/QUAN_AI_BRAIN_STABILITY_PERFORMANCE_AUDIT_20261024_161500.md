# QUAN AI BRAIN — BÁO CÁO TOÀN DIỆN AUDIT GIAI ĐOẠN A (MASTER PROMPT V7)
## Kiểm toán Độ ổn định, Tốc độ xử lý, Hạ tầng Môi trường & Sơ đồ Năng lực Hệ thống

> **Mã báo cáo:** `AUDIT-V7-20261024-161500`  
> **Thời gian kiểm toán:** 2026-10-24 16:15:00 (Local Time)  
> **Chủ sở hữu phê duyệt:** Anh Quân — Quanpt1  
> **Workspace:** `E:\AI\QUAN AI BRAIN`  
> **Trạng thái:** `AUDIT_COMPLETED — PENDING_OWNER_DIFF_SIGNOFF`  
> **Nguyên tắc bất biến:** Không sửa đổi mã nguồn trước khi anh Quân phê duyệt báo cáo audit và kế hoạch diff chi tiết.

---

## 1. BẢO TOÀN WORKSPACE & HIỆN TRẠNG GIT (A2)

- **Git Branch:** `master`
- **Commit Head:** `9243d12 docs: update handoff report with 17 passed tests and clean git tree`
- **Trạng thái Working Tree:**
  - Tracked modified files (17 files):
    - `bao cao xay dung he thong/README.md`
    - `docs/PROJECT_STATUS.md`
    - `pyproject.toml`
    - `reports/HANDOFF_LATEST.md`
    - `reports/TEST_RUN_LATEST.txt`
    - `src/quan_ai_brain/cli.py`
    - `src/quan_ai_brain/core/__init__.py`
    - `src/quan_ai_brain/core/audit.py`
    - `src/quan_ai_brain/core/redaction.py`
    - `src/quan_ai_brain/governance/__init__.py`
    - `src/quan_ai_brain/governance/policy.py`
    - `src/quan_ai_brain/memory/__init__.py`
    - `src/quan_ai_brain/memory/sqlite_store.py`
    - `src/quan_ai_brain/planning/__init__.py`
    - `src/quan_ai_brain/planning/models.py`
    - `src/quan_ai_brain/tools/__init__.py`
    - `tools/validate_and_report.py`
  - Untracked files: Các báo cáo mới trong `reports/`, công cụ kiểm tra trong `tools/`, mã nguồn nâng cấp trong `src/quan_ai_brain/` và bộ test mở rộng trong `tests/`.
- **Tiến trình đang chạy:**
  - PC Core Executive Server (`task-1611`): Đang chạy nền tại cổng `8766` (`http://127.0.0.1:8766/`), phục vụ Cockpit, API và luồng camera trực tiếp.
  - Pi 5 Edge Daemon: Đang chạy tại `http://192.168.1.21:8768/`, kết nối liên tục với Core qua HMAC-SHA256 authenticated heartbeat.
  - Local Ollama Daemon: Đang chạy tại `http://127.0.0.1:11434/`, 7 model sẵn sàng.
- **Cam kết bảo toàn:** Không reset, không clean, không stash đè, không sửa đổi các project lân cận (`DATA CENTER AI OPERATING SYSTEM`, `BAT-AI-2026-Repo`, `os_kernel`, `SKILL_BAT_AI`, `BATTERY_AI_V4`, `BOT`, VDCIM).

---

## 2. GIẢI QUYẾT SAI KHÁC MÔI TRƯỜNG PYTHON (A3)

### 2.1. Kết quả điều tra thực tế
1. **Python trên PATH mặc định:**
   - Đường dẫn: `C:\Python314\python.exe`
   - Phiên bản: `3.14.7` (tags/v3.14.7:823f032, Aug 5 2026, 10:51:32) [MSC v.1944 64 bit (AMD64)]
   - Gói cài đặt: Môi trường global lớn chứa PyTorch, Transformers, ONNX, OpenCV, Ollama SDK, Pydantic, Uvicorn, v.v.
2. **Python chuẩn ảo hóa (.venv):**
   - Đường dẫn: `E:\AI\QUAN AI BRAIN\.venv\Scripts\python.exe`
   - Phiên bản gốc: `Python 3.11.9` (`C:\Users\DELL\AppData\Local\Programs\Python\Python311\python.exe`)
   - Cấu hình: `include-system-site-packages = false`
   - Gói cài đặt: Môi trường tinh gọn, chuẩn hóa riêng cho QUAN AI BRAIN (`aiohttp`, `edge-tts`, `paramiko`, `pillow`, `pytest`, `quan-ai-brain` editable, `cryptography`, `bcrypt`, `tabulate`).
3. **Kết quả kiểm thử trên cả hai môi trường:**
   - Chạy trên `.venv` (Python 3.11.9): **483 PASSED, 0 FAILED, 1 SKIPPED** (74.18s).
   - Chạy trên `C:\Python314` (Python 3.14.7): **483 PASSED, 0 FAILED, 1 SKIPPED** (69.80s).
   - Cả hai interpreter đều chạy thành công 100% các bài test của hệ thống.

### 2.2. Đề xuất phương án Runtime chuẩn (Trình anh Quân phê duyệt)
- **Phương án đề xuất (Recommended):** Chuẩn hóa sử dụng môi trường ảo `.venv` (`Python 3.11.9`).
  - *Lý do:* Python 3.11.9 là phiên bản ổn định (LTS standard) trong toàn bộ tài liệu kiến trúc ban đầu (`docs/NEXT_STEPS.md`, `pyvenv.cfg`), có tính tương thích 100% với các thư viện native C-extension, âm thanh ALSA/PipeWire, OpenCV, và tránh xung đột với các gói toàn cục ngoài workspace.
  - *Cấu hình launcher:* Cập nhật các batch script và launcher (`run_executive_desk.py`, `tools/validate_and_report.py`) để tự động ưu tiên interpreter trong `.venv` nếu tồn tại, fallback sang `sys.executable`.
  - *Không xóa hoặc ghi đè:* Giữ nguyên cả hai môi trường, không xóa thư mục hay cài lại dependency gây xáo trộn.

---

## 3. BẢNG PHÂN LOẠI NĂNG LỰC 18 THÀNH PHẦN TRỌNG YẾU (A4)

| STT | Thành phần (Subsystem) | Trạng thái thực tế | Bằng chứng xác minh & Chi tiết kiểm toán |
| :--- | :--- | :--- | :--- |
| **1** | `LLMRouter` & Ollama Client | `VERIFIED_E2E` | Ollama chạy cổng 11434 với 7 models. Đo lường thực tế: `0.5b` warm 0.79s (125 tok/s), `1.5b` warm 0.50s (64.6 tok/s), `7b` 20.6s (7.7 tok/s). `test_llm_provider.py` PASS. |
| **2** | `SessionMemoryManager` | `VERIFIED_E2E` | Lưu trữ bền vững hội thoại đa lượt vào SQLite WAL `data/brain.db`. API `/api/memories` hiển thị 289 mục nhớ. 5 bài test E2E `test_end_to_end_chat.py` PASS. |
| **3** | `CognitiveRetriever` & BGE-M3 | `INTEGRATION_TESTED` | Hybrid sparse/dense retrieval; cosine similarity thuần Python. BGE-M3 sinh 1024-dim vector trong 9.64s. 12 test trong `test_memory_retrieval.py` & `test_bge_m3_embedding.py` PASS. |
| **4** | `PromptContextBuilder` | `INTEGRATION_TESTED` | Tổng hợp Persona, Directives của anh Quân, Capabilities, lịch sử hội thoại gần nhất và ký ức trích xuất. `test_context_builder.py` PASS. |
| **5** | `TaskPlan` & DAG Validation | `INTEGRATION_TESTED` | Kiểm tra chu trình (Cycle detection), thứ tự tô-pô, đánh giá rủi ro R0-R5 của từng bước. 15 test `test_planning.py` PASS. |
| **6** | `DurableTaskRegistry` | `INTEGRATION_TESTED` | Lưu trữ nhiệm vụ và các bước bền vững vào SQLite WAL `data/tasks.db`, khóa chống trùng lặp (idempotency key), khôi phục trạng thái sau restart. 14 test `test_durable_task_registry.py` PASS. |
| **7** | `ExecutiveCoordinator` | `UNIT_TESTED_ONLY` | Phân tách mục tiêu người dùng thành TaskPlan. Hiện chỉ được nối với mock LLM trong test; chưa kết nối trực tiếp vào luồng xử lý `POST /api/chat` để kích hoạt tự động. |
| **8** | `ToolRegistry` | `INTEGRATION_TESTED` | Đăng ký công cụ theo capability, xác thực schema tham số, phân loại rủi ro R0-R5. 14 test `test_tool_sandbox.py` PASS. |
| **9** | `ApprovalGate` & Signature Verifier | `INTEGRATION_TESTED` | Kiểm soát phê duyệt của chủ sở hữu, chữ ký HMAC, chống replay nonce một lần, xác thực Dual-Factor cho R4. `test_approval_gate.py` & `test_owner_signature_verifier.py` PASS. |
| **10** | `DelegationRegistry` | `INTEGRATION_TESTED` | Ủy quyền có thời hạn và ngân số lần gọi; giới hạn cứng ở R0-R2 (cấm tuyệt đối ủy quyền R4/R5). 11 test `test_delegation.py` PASS. |
| **11** | `SafeToolSandbox` | `INTEGRATION_TESTED` | Giữ chặt thao tác trong thư mục `E:\AI\QUAN AI BRAIN` qua `PathGuard`, che giấu thông tin nhạy cảm. 14 test `test_tool_sandbox.py` PASS. |
| **12** | `InertProcessBackend` | `BLOCKED_PENDING_APPROVAL` | Mô phỏng thực thi có kiểm soát (Staging only). Chặn cứng việc tạo subprocess hoặc chạy lệnh sản xuất khi chưa có sign-off. `test_process_containment.py` PASS. |
| **13** | `ContinuousEvaluationHarness` | `INTEGRATION_TESTED` | Đo lường tỷ lệ pass, phát hiện hồi quy, cách ly tri thức mới, tạo 17-point UpgradeProposal. `test_evaluation_harness.py` & `test_self_learning_engine.py` PASS. |
| **14** | `Executive Desk` API & Frontend | `VERIFIED_E2E` | Server chạy cổng 8766 (`task-1611`), 7 tabs điều hành, telemetry trực tiếp, duyệt đề xuất, stream camera thật, điều khiển âm thanh. `test_web_executive_endpoints.py` PASS. |
| **15** | Voice Pipeline & Vietnamese TTS | `INTEGRATION_TESTED` | Edge-TTS giọng nữ `vi-VN-HoaiMyNeural`, bộ nhớ đệm âm thanh, cơ chế ngắt lời (barge-in), mouth-sync viseme. 10 test `test_vietnamese_tts.py` & `test_voice_first_pipeline.py` PASS. |
| **16** | Edge Client (Raspberry Pi 5) | `VERIFIED_E2E` | Kết nối vật lý 24/7 với Pi 5 (`192.168.1.21:8768`), RTT 10-15ms, stream JPEG camera USB thật (21KB color frame), loa/micro PipeWire ALSA hoạt động. `test_edge_client.py` PASS. |
| **17** | Health Monitoring & Autonomic | `INTEGRATION_TESTED` | Thu thập chỉ số CPU, RAM, disk, trạng thái SQLite, nhịp tim subsystem. Expose endpoint `/api/status`. `test_autonomic_nervous_system.py` PASS. |
| **18** | GovernanceStateStore | `INTEGRATION_TESTED` | Cơ sở dữ liệu SQLite WAL `data/governance.db` lưu trạng thái khẩn cấp STOP/FREEZE bền bỉ qua reboot, token phê duyệt 1 lần. `test_governance_state_store.py` PASS. |

---

## 4. CÁC ĐIỂM NGHẼN (BOTTLENECK) VÀ KẾT NỐI CÒN THIẾU ĐÃ XÁC MINH (A4 - C)

### 4.1. Điểm nghẽn 1: Polling lặp quá mức giữa Pi 5 và Core PC (Mạng & CPU)
- **Hiện tượng thực tế:** Trong nhật ký server Core (`task-1611`), cứ mỗi 1 giây Pi 5 gửi **4 request HTTP riêng biệt**:
  1. `GET /api/executive/supervisor`
  2. `POST /api/executive/edge/heartbeat`
  3. `GET /api/executive/tasks`
  4. `GET /api/executive/consultations?status=PENDING_REVIEW`
- **Ảnh hưởng:** 240 requests/phút qua mạng Wi-Fi; gây lãng phí CPU trên Pi 5, tạo hàng trăm socket kết nối ngắn hạn.
- **Giải pháp tối ưu:** Tích hợp dữ liệu `active_tasks` và `pending_consultations_count` trực tiếp vào phản hồi của `POST /api/executive/edge/heartbeat`. Giãn nhịp tim lên 2.5 - 3.0 giây.
- **Hiệu quả dự kiến:** Giảm 75% lưu lượng mạng giữa Core và Pi 5, giảm độ trễ phản hồi, tiết kiệm tài nguyên CPU.

### 4.2. Điểm nghẽn 2: Đứt gãy luồng TaskPlan -> DurableTaskRegistry trong Hội thoại
- **Hiện tượng thực tế:** Module `PlanOrchestrator` (`src/quan_ai_brain/orchestration/plan_orchestrator.py`) đã có đầy đủ logic kết nối `TaskPlan` vào `DurableTaskRegistry`, nhưng chưa được gắn vào API xử lý hội thoại chính `POST /api/chat` trên `server.py`.
- **Ảnh hưởng:** Khi anh Quân yêu cầu một nhiệm vụ phức tạp nhiều bước trên giao diện Web, hệ thống chỉ phản hồi văn bản thông qua LLM mà không ghi nhận nhiệm vụ bền vững vào bảng điều phối `data/tasks.db` và không hiển thị tiến trình trên Tab 3.
- **Giải pháp:** Kết nối `ExecutiveCoordinator` và `PlanOrchestrator` vào endpoint `POST /api/chat`. Khi phát hiện yêu cầu dạng `planning`/nhiệm vụ, tự động đăng ký `TaskRecord` và các `TaskStepRecord` vào `DurableTaskRegistry` với Idempotency Key an toàn.

### 4.3. Điểm nghẽn 3: Quản lý Timeout phân tầng LLM (Tier-Aware Timeout)
- **Hiện tượng thực tế:** Model `qwen2.5:7b` (Reasoning Tier) trên phần cứng PC tiêu tốn ~20s cho suy luận phức tạp. Nếu client sử dụng timeout cố định 15s như model nhẹ (`0.5b`/`1.5b`), request 7B sẽ bị `timed out`.
- **Giải pháp:** Cấu hình timeout động theo phân tầng: Fast Tier (`0.5b`/`1.5b`) = 10s; Reasoning Tier (`7b`) = 60s; Embedding (`bge-m3`) = 20s.

### 4.4. Điểm nghẽn 4: Chuẩn hóa SQLite Connection và WAL Mode
- **Hiện tượng thực tế:** Các cơ sở dữ liệu (`brain.db`, `tasks.db`, `governance.db`, `consultations.db`) được mở rải rác. Cần đảm bảo 100% kết nối đều thiết lập `PRAGMA busy_timeout = 5000` và `PRAGMA synchronous = NORMAL` để ngăn ngừa triệt để lỗi `database is locked` khi giao diện web và các luồng nền truy cập đồng thời.

---

## 5. KẾ HOẠCH DIFF VÀ CÁC FILE SẼ ĐƯỢC CHỈNH SỬA (TRÌNH DUYỆT)

Để giải quyết triệt để các vấn đề trên mà không làm xáo trộn kiến trúc, các file dự kiến can thiệp có phạm vi kiểm soát chặt chẽ như sau:

| File cần tác động | Mục đích thay đổi | Rủi ro & Biện pháp kiểm soát |
| :--- | :--- | :--- |
| `src/quan_ai_brain/web/server.py` | 1. Tích hợp `active_tasks` và `proposals_pending` vào heartbeat response của Edge.<br>2. Nối `POST /api/chat` với `PlanOrchestrator` khi có yêu cầu lập kế hoạch nhiệm vụ.<br>3. Chuẩn hóa `busy_timeout = 5000` cho mọi kết nối SQLite. | Thấp. Toàn bộ endpoints hiện tại giữ nguyên tương thích ngược. Chạy lại 100% test web sau khi sửa. |
| `edge_client/client_daemon.py` | 1. Tối ưu nhịp tim: Nhận thông tin task/consultation từ heartbeat response thay vì gọi 3 request polling riêng.<br>2. Đặt `poll_interval_sec = 2.5` để giảm tải Wi-Fi. | Thấp. Có fallback: Nếu heartbeat không trả về task data, vẫn duy trì cơ chế cũ. |
| `src/quan_ai_brain/llm/client.py` & `router.py` | Cấu hình timeout phân tầng theo tier (Fast: 10s, Reasoning: 60s). | Rất thấp. Giúp model 7B suy luận trọn vẹn mà không bị ngắt quãng. |
| `src/quan_ai_brain/orchestration/plan_orchestrator.py` | Đảm bảo tính nhất quán trạng thái giữa `TaskRecord` trong DB và kết quả trả về giao diện. | Thấp. Code đã có sẵn 14 test pass, chỉ hoàn thiện kết nối. |

---

## 6. TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA) & PHƯƠNG ÁN ROLLBACK

### 6.1. Tiêu chí nghiệm thu (DoD):
1. **Kiểm thử tự động:** 100% bộ test (ít nhất 483 tests) tiếp tục PASS trên môi trường chuẩn `.venv` (Python 3.11.9).
2. **Tối ưu mạng Pi 5:** Số request từ Pi 5 sang Core giảm từ 4 req/giây xuống còn 1 req mỗi 2.5 giây (giảm ~75% lưu lượng), camera stream và audio vẫn hoạt động tức thời.
3. **Nhiệm vụ bền vững:** Gửi chỉ thị lập kế hoạch qua `/api/chat` sinh ra `TaskRecord` thực sự trong `data/tasks.db`, hiển thị trên Cockpit Tab 3 mà không lỗi.
4. **Không lỗi SQLite Lock:** Chạy đồng thời đàm thoại, streaming camera và heartbeat không ghi nhận bất kỳ lỗi `database is locked`.
5. **Giữ nguyên Zero-Execution:** Không kích hoạt subprocess runner ngoài đời thực; duy trì chế độ an toàn `InertProcessBackend` đúng theo Sprint 6 Sign-Off.

### 6.2. Phương án Rollback:
- Mỗi file trước khi chỉnh sửa đều được lưu bản backup cục bộ.
- Nếu sau khi sửa có bất kỳ bài test nào FAIL hoặc Pi 5 mất kết nối, revert ngay lập tức về trạng thái commit `9243d12` thông qua `git checkout`.
- Không có bất kỳ thay đổi schema mang tính phá hủy dữ liệu nào đối với các cơ sở dữ liệu SQLite hiện hữu.

---

## 7. ĐỀ XUẤT PHÊ DUYỆT CỦA ANH QUÂN (Quanpt1)

Xin trân trọng báo cáo và kính đề xuất anh Quân xem xét, cho ý kiến chỉ đạo đối với 2 quyết định trước khi tiến hành chỉnh sửa mã nguồn:

1. **Phê duyệt Runtime chuẩn:** Xác nhận sử dụng môi trường ảo `.venv` (`Python 3.11.9`) làm runtime chuẩn mực cho mọi tác vụ vận hành và kiểm thử tự động của QUAN AI BRAIN.
2. **Phê duyệt Triển khai Sprint B & D:** Cho phép thực hiện gói chỉnh sửa tối ưu hóa:
   - Gói B: Giảm 75% polling lặp của Pi 5, tích hợp phản hồi heartbeat gộp, chuẩn hóa timeout LLM.
   - Gói D: Nối luồng `TaskPlan` từ hội thoại vào `DurableTaskRegistry` để hiển thị nhiệm vụ sống trên Cockpit.
