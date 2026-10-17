# SYSTEM BASELINE: QUAN AI BRAIN
**Document ID:** DOC-QAB-BASE-001  
**Audit Date:** 2026-10-17  
**Auditor / Role:** AI Software Architect & Senior Engineer  
**Workspace Path:** `e:\AI\QUAN AI BRAIN`  
**Classification:** Baseline Audit & Environmental Verification

---

## 1. Mục đích tài liệu
Tài liệu này xác lập đường cơ sở kỹ thuật (System Baseline) cho dự án **QUAN AI BRAIN** tại thời điểm khởi tạo, phân định rõ ràng giữa:
- **Đã xác minh (Verified):** Dữ liệu thu thập trực tiếp bằng kiểm tra hệ thống thực tế.
- **Suy luận kỹ thuật (Inferred):** Suy đoán logic dựa trên tài liệu kiến trúc hiện hữu.
- **Chưa biết (Unknown):** Thông tin thiếu bằng chứng thực nghiệm hoặc chưa được cấp quyền kiểm tra.

---

## 2. Kiểm toán Workspace Hiện tại (`e:\AI\QUAN AI BRAIN`)

| Thuộc tính | Trạng thái xác minh | Chi tiết kỹ thuật |
| :--- | :--- | :--- |
| **Cấu trúc thư mục** | Đã xác minh | Thư mục trống (0 tệp, 0 thư mục con trước khi khởi tạo docs). |
| **Hệ thống Git VCS** | Đã xác minh | Chưa khởi tạo kho chứa Git (`fatal: not a git repository`). |
| **Điểm khởi chạy (Entry points)** | Đã xác minh | Chưa có bất kỳ tệp thực thi, main script hay batch file nào. |
| **Tệp cấu hình & Môi trường** | Đã xác minh | Chưa có `.env`, `pyproject.toml`, `requirements.txt` hay config file. |
| **Mã nguồn & Test Suite** | Đã xác minh | Chưa có mã nguồn nghiệp vụ hoặc bài kiểm thử nội bộ. |
| **Tài liệu kiến trúc nội tại** | Đã xác minh | Chưa có tài liệu nội bộ trong workspace trước lần kiểm toán này. |

---

## 3. Kiểm toán Đối chiếu Hệ thống Ngoại vi (Theo chấp thuận của người dùng)

Để bảo đảm tính tương thích và bảo tồn các hệ sinh thái sẵn có của Quanpt1, kiểm toán chỉ đọc (read-only audit) đã rà soát các hệ thống liên quan:

### 3.1. DC-COMMAND V6.7 / CLAE (Cognitive Learning Assurance Engine)
- **Vị trí vật lý xác minh:** `E:\AI\DATA CENTER AI OPERATING SYSTEM` (và bản mirror tại `E:\AI\BAT-AI-2026-Repo\DATA CENTER AI OPERATING SYSTEM`).
- **Thành phần cốt lõi:**
  - `core/clae.py`: Engine học tập bảo đảm nhận thức (CLAE) gồm 30 bước xử lý.
  - `communication/notify_v67_clae.py`: Module thông báo điều hành.
  - `tests/test_v67_clae.py`: Bộ kiểm thử golden benchmarks.
  - `data build/DC_COMMAND_V67_CLAE_ARCHITECTURE.md`: Tài liệu kiến trúc chuẩn mực.
- **Nguyên lý bảo đảm:**
  - Tách bạch giữa **Học hỏi (Learning)** và **Triển khai (Deployment)**.
  - Kiểm tra chống ngẫu nhiên (*Luck vs Learning*).
  - Không suy thoái (*Zero Regression*).
  - Yêu cầu phê duyệt từ Quanpt1 trước khi tích hợp tri thức vào sản xuất.

### 3.2. Kernel L3 (Battery OS Kernel)
- **Vị trí vật lý xác minh:** `E:\AI\BAT-AI-2026-Repo\battery-ai-\os_kernel`. *(Lưu ý: Không nằm ở `E:\AI\battery-ai-\os_kernel` như giả định ban đầu mà nằm trong nhánh repo phân tán).*
- **Thành phần cốt lõi:**
  - `kernel.py`: Lớp Facade tích hợp 10 hệ thống con.
  - 10 Subsystems: `api` (Gateway), `audit` (AuditTrail), `bus` (EventBus), `capability` (CapabilityManager), `health` (HealthMonitor), `logs`, `policy` (PolicyEngine), `registry` (ModuleRegistry), `safety` (SafetyGuard), `scheduler` (TaskScheduler), `state` (StateManager), cùng engine tự phục hồi `self_healing.py`.
  - `self_test.py`: Kịch bản tự kiểm tra toàn vẹn hệ thống kernel.
- **Đánh giá trạng thái:** Kiến trúc hướng sự kiện, mô đun hóa cao, cung cấp cơ chế an toàn và giám sát vòng đời.

### 3.3. SKILL_BAT_AI (Autonomous AI Workforce OS)
- **Vị trí vật lý xác minh:** `E:\AI\Skill\SKILL_BAT_AI`.
- **Thành phần cốt lõi:**
  - Core Engine 6 khối: `TaskEngine`, `RiskEngine` (Ma trận rủi ro R0 - R5), `AuthzEngine`, `ExecutionEngine` (tự retry, tự validate), `EscalationEngine` (Ticket khẩn), `LearningEngine`.
  - Cơ sở dữ liệu: `ai_workforce.db` (SQLite).
  - Vận hành: Mô hình Zero-Touch chạy ngầm (Daemon) với cơ chế Escalate qua secret key (`QUANPT1_APPROVAL_SECRET`).
  - Tài liệu: `READ_ME_FIRST.md` và `SKILL.md`.

### 3.4. Battery AI V4
- **Vị trí vật lý xác minh:** `E:\AI\battery-ai-\BATTERY_AI_V4`.
- **Thành phần cốt lõi:**
  - Master Prompts và tài liệu: `BATTERY AI V4 - MASTER PROMPT_ Knowledge & Experience Learning Engine.md`, `BATTERY AI V4-V5 - MASTER PROMPT_ Autonomous Battery Intelligence Brain.md`.
  - Lưu trữ dữ liệu: `battery_data.db`, `battery_ups_v4.db`.
  - Tệp nhạy cảm `.env`: Đã ghi nhận sự tồn tại, tuân thủ nguyên tắc an toàn tuyệt đối **không mở hoặc đọc nội dung**.
  - Scripts: Bộ điều khiển chạy ngầm `run_autonomous_daemon.bat`, `setup_autonomous_task.bat`, các bài test kiểm soát admin và concurrency.

### 3.5. Ollama & Mô hình Cục bộ (Local LLM)
- **Vị trí cài đặt xác minh:** `E:\AI\Ollama`.
- **Mô hình sẵn có trong đĩa:**
  - `qwen2.5:7b` (Đã tải: `E:\AI\Ollama\models\manifests\registry.ollama.ai\library\qwen2.5\7b`).
  - Mô hình phụ trợ: `llama3.1:latest`, `mistral:latest`, `qwen:latest`, `qwen2.5:0.5b`, `qwen2.5:1.5b`.
- **Trạng thái dịch vụ runtime:** Tiến trình nền của Ollama daemon chưa kích hoạt hoặc chưa lắng nghe cổng mặc định tại thời điểm kiểm toán.

### 3.6. Môi trường Hệ thống & Runtime Máy chủ
- **Hệ điều hành:** Windows 10 Pro (x64) Build 10.0.19045.
- **Python Runtimes:**
  - Python 3.14.7 (Active mặc định trên PATH).
  - Python 3.11 (64-bit có sẵn trên máy qua `py -0`).
- **Môi trường ảo (Virtual Environments):**
  - Có các venv hiện hữu ở `E:\AI\BOT\.venv` và `E:\AI\battery-ai-\BATTERY_AI_TABPFN\venv`.
  - Workspace `QUAN AI BRAIN` hiện chưa có venv riêng.

---

## 4. Bảng Phân Định: Xác minh vs Suy luận vs Chưa biết

| Thành phần | Đã xác minh (Verified) | Suy luận (Inferred) | Chưa biết (Unknown) |
| :--- | :--- | :--- | :--- |
| **Workspace QUAN AI BRAIN** | Thư mục mới hoàn toàn, trống 100%, chưa có git. | Cần được tổ chức theo cấu trúc module độc lập, kế thừa tinh hoa từ CLAE, Kernel L3 và SKILL_BAT_AI. | Quy ước đóng gói của Quanpt1 cho project mới (ví dụ: Poetry, Pipenv hay chuẩn venv). |
| **Kernel L3** | Nằm tại `BAT-AI-2026-Repo\battery-ai-\os_kernel`, cấu trúc 10 component đầy đủ. | Đóng vai trò lớp nền tảng bảo vệ phần cứng và điều phối bus sự kiện. | Mức độ phụ thuộc chéo vào các module telemetry cụ thể của battery-ai. |
| **SKILL_BAT_AI** | Đã sẵn sàng các engine rủi ro R0-R5 và daemon Zero-Touch. | Là khung quy trình lý tưởng cho lớp thực thi tác vụ (Task/Execution Layer) của Trợ lý Điều hành. | Cấu hình webhook thực tế và các kênh thông báo ngoại vi đang kết nối. |
| **CLAE (DC-COMMAND)** | Quy trình 30 bước bảo chứng tri thức, pipeline chống ngẫu nhiên. | Là lõi thuật toán cho tính năng "học từ kinh nghiệm và kết quả đã xác minh" của Brain. | Dữ liệu Ground Truth và Golden Baselines được nạp định kỳ từ nguồn nào. |
| **Ollama / Qwen2.5:7b** | Model 7B đã nằm sẵn trong thư mục models của Ollama. | Sẽ là Local LLM chính để xử lý suy luận offline, bảo mật dữ liệu nội bộ. | Cấu hình GPU VRAM và hiệu năng tải đồng thời khi chạy ngầm. |
| **Bảo mật & Credentials** | Tồn tại `.env` ở các thư mục cũ (không chạm vào). | Cần xây dựng cơ chế credential an toàn riêng biệt cho QUAN AI BRAIN không ghi đè hay rò rỉ. | Các API key cần thiết cho Brain kết nối ra ngoài (Telegram, Zalo, Webhook nội bộ). |

---

## 5. Kết luận Baseline
Workspace `e:\AI\QUAN AI BRAIN` đang ở trạng thái **Nền tảng Tinh khiết (Clean Slate)**, không có nợ kỹ thuật (technical debt) trực tiếp trong thư mục, đồng thời được bao bọc bởi một hệ sinh thái tài nguyên và kiến trúc sẵn có rất mạnh mẽ (CLAE, Kernel L3, SKILL_BAT_AI, Local Qwen2.5:7b). Điều này cho phép thiết kế một kiến trúc Trợ lý Điều hành chuẩn mực ngay từ ngày đầu tiên mà không phá vỡ bất kỳ thành phần nào đang vận hành.
