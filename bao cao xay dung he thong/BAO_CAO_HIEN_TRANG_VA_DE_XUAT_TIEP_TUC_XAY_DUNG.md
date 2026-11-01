# BÁO CÁO CHI TIẾT HIỆN TRẠNG & ĐỀ XUẤT HỆ THỐNG QUAN AI BRAIN
## TÀI LIỆU BÀN GIAO KỸ THUẬT CHO CHATGPT TIẾP TỤC PHÁT TRIỂN

**Dự án:** QUAN AI BRAIN — Digital Executive Assistant  
**Mã tài liệu:** BC-QAB-STATUS-PROPOSAL-SPRINT2A  
**Ngày lập báo cáo:** 2026-10-17  
**Chủ nhiệm hệ thống / Người thụ hưởng:** Quanpt1  
**Đơn vị thực hiện:** AI Software Architect & Senior Engineering Pair (Antigravity)  
**Workspace:** `E:\AI\QUAN AI BRAIN`  
**Trạng thái kiểm thử:** **34/34 bài test PASS** (100% thành công)  
**Tài liệu tham chiếu:** [BAO_CAO_XAY_DUNG_HE_THONG_QUAN_AI_BRAIN.md](file:///e:/AI/QUAN%20AI%20BRAIN/bao%20cao%20xay%20dung%20he%20thong/BAO_CAO_XAY_DUNG_HE_THONG_QUAN_AI_BRAIN.md) | [HANDOFF_LATEST.md](file:///e:/AI/QUAN%20AI%20BRAIN/reports/HANDOFF_LATEST.md) | [PROJECT_STATUS.md](file:///e:/AI/QUAN%20AI%20BRAIN/docs/PROJECT_STATUS.md) | [AGENTS.md](file:///e:/AI/QUAN%20AI%20BRAIN/AGENTS.md)

---

## MỤC LỤC
1. [TỔNG QUAN HIỆN TRẠNG & BẰNG CHỨNG KIỂM THỬ THỰC TẾ](#1-tổng-quan-hiện-trạng--bằng-chứng-kiểm-thử-thực-tế)
2. [CHI TIẾT MÃ NGUỒN & CÁC PHÂN HỆ ĐÃ HOÀN THÀNH](#2-chi-tiết-mã-nguồn--các-phân-hệ-đã-hoàn-thành)
3. [MA TRẬN ĐỐI CHIẾU HỆ THỐNG NGOẠI VI & BẢO TỒN NGUYÊN TRẠNG](#3-ma-trận-đối-chiếu-hệ-thống-ngoại-vi--bảo-tồn-nguyên-trạng)
4. [PHÂN TÍCH KHOẢNG TRỐNG KIẾN TRÚC (GAP ANALYSIS) SAU SPRINT 2A](#4-phân-tích-khoảng-trống-kiến-trúc-gap-analysis-sau-sprint-2a)
5. [ĐỀ XUẤT HỆ THỐNG & KẾ HOẠCH HÀNH ĐỘNG CHO CHATGPT (SPRINT 2B - SPRINT 4)](#5-đề-xuất-hệ-thống--kế-hoạch-hành-động-cho-chatgpt-sprint-2b---sprint-4)
6. [CÁC QUY TẮC AN TOÀN BẤT BIẾN DÀNH CHO KỸ SƯ KẾ NHIỆM](#6-các-quy-tắc-an-toàn-bất-biến-dành-cho-kỹ-sư-kế-nhiệm)
7. [BẢN TIN BÀN GIAO TIẾP NỐI CHO PHIÊN CHATGPT TIẾP THEO (HANDOFF PAYLOAD)](#7-bản-tin-bàn-giao-tiếp-nối-cho-phiên-chatgpt-tiếp-theo-handoff-payload)

---

## 1. TỔNG QUAN HIỆN TRẠNG & BẰNG CHỨNG KIỂM THỬ THỰC TẾ

### 1.1. Môi trường Thực thi Máy chủ
- **Thiết bị:** Dell Precision 7550, CPU Intel Core i7 / Xeon, RAM 32GB+.
- **Hệ điều hành:** Windows 10 Pro x64 (Build 10.0.19045).
- **Python Runtime:** Python 3.11.9 (64-bit), môi trường ảo chuyên biệt tại `E:\AI\QUAN AI BRAIN\.venv`.
- **Hệ thống Quản lý Phiên bản (VCS):** Git đã được khởi tạo (`git init`), cấu hình tác giả nội bộ `Quanpt1 <quanpt1@local>`, commit khởi tạo Sprint 1 (`47f0bad`, `9243d12`).
- **Phạm vi an toàn:** Toàn bộ quá trình cài đặt, chạy test và tạo tệp được giam giữ 100% bên trong workspace `E:\AI\QUAN AI BRAIN`.

### 1.2. Bằng chứng Kiểm thử (Verified Ground Truth)
Khác với các tài liệu giả định, hệ thống hiện đã có bộ test hồi quy tự động hoàn chỉnh và được kiểm chứng trực tiếp trên máy thật:
- **Lệnh thực thi:** `.\.venv\Scripts\python.exe -m pytest -v`
- **Kết quả:** **34/34 bài test PASS** (Thời gian chạy: `0.96 giây`).
  - `tests/test_long_term_memory.py`: **11/11 bài test PASS** (Lưu trữ và truy xuất 6 loại trí nhớ, duy trì dữ liệu qua các lần đóng/mở CSDL, tìm kiếm tiếng Việt có dấu, lọc theo trạng thái xác minh, cách ly tri thức ứng viên, quản lý phiên bản versioning v1 -> v2 và truy vết nguồn gốc dòng giống `trace_source`, ghi nhận kết quả tác vụ, chống SQL injection, từ chối dữ liệu rỗng/sai lệch, tự động che giấu credential).
  - `tests/test_validate_and_report.py`: **6/6 bài test PASS** (Phát hiện và loại trừ tệp nhạy cảm `.env*`/`.key`/`.db`, phân tích chính xác kết quả pytest, kiểm tra cấu trúc 9 phần của báo cáo, kiểm thử tình huống test failure, kiểm tra an toàn danh mục tệp, kiểm tra tính chịu lỗi của module Git).
  - `tests/test_policy.py`: **3/3 bài test PASS** (Ma trận rủi ro R0 - R5; R5 chặn cứng tuyệt đối, R4 yêu cầu phê duyệt có chữ ký, R2 kiểm tra đường dẫn workspace).
  - `tests/test_quarantine.py`: **3/3 bài test PASS** (Cơ chế cách ly tri thức ứng viên, chặn thăng cấp khi chưa có regression pass và xác minh người sở hữu).
  - `tests/test_memory.py`: **4/4 bài test PASS** (Episodic SQLite, bảo vệ đường dẫn DB không thoát workspace, từ chối episode rỗng, kiểm tra Unicode tiếng Việt).
  - `tests/test_path_and_audit.py`: **2/2 bài test PASS** (PathGuard chặn path traversal escape, AuditLogger JSONL append-only có redaction).
  - `tests/test_planning_and_health.py`: **3/3 bài test PASS** (Kiểm tra mô hình kế hoạch tác vụ TaskPlan, cảnh báo rủi ro cao, health snapshot).
  - `tests/test_redaction.py`: **2/2 bài test PASS** (Che giấu regex Bearer, password, api_key, access_token, client_secret).

---

## 2. CHI TIẾT MÃ NGUỒN & CÁC PHÂN HỆ ĐÃ HOÀN THÀNH

Toàn bộ mã nguồn hiện tại được tổ chức chuẩn mực theo cấu trúc package Python tại [`src/quan_ai_brain/`](file:///e:/AI/QUAN%20AI%20BRAIN/src/quan_ai_brain):

```
E:\AI\QUAN AI BRAIN\
├── .gitignore                          # Cấu hình bỏ qua .venv, DB, logs, cache, secrets
├── AGENTS.md                           # Bộ quy tắc kỹ thuật bất biến của dự án
├── pyproject.toml                      # Cấu hình đóng gói package & pytest options
├── README_SPRINT1.md                   # Hướng dẫn khởi tạo Sprint 1
├── src\quan_ai_brain\
│   ├── __init__.py                     # Package entry point
│   ├── cli.py                          # Giao diện dòng lệnh (self-check, memory-add, memory-list) có UTF-8 Windows
│   ├── clae\
│   │   ├── __init__.py
│   │   └── quarantine.py               # Cổng cách ly tri thức ứng viên (Cognitive Quarantine)
│   ├── core\
│   │   ├── __init__.py
│   │   ├── audit.py                    # Ghi nhật ký kiểm toán JSONL append-only
│   │   └── redaction.py                # Bộ lọc che giấu thông tin nhạy cảm trước khi lưu
│   ├── daemon\
│   │   ├── __init__.py
│   │   └── health.py                   # Báo cáo sức khỏe tiến trình cục bộ (Health-only skeleton)
│   ├── governance\
│   │   ├── __init__.py
│   │   └── policy.py                   # Cổng phân cấp rủi ro R0 - R5 (Policy Engine)
│   ├── memory\
│   │   ├── __init__.py
│   │   ├── models.py                   # Enums (MemoryType, VerificationStatus, LifecycleStatus) & MemoryRecord
│   │   └── sqlite_store.py             # Bộ nhớ SQLite đa tầng, thread-safe, versioning, search tiếng Việt
│   ├── planning\
│   │   ├── __init__.py
│   │   └── models.py                   # Mô hình kế hoạch tác vụ (TaskPlan, TaskStep, TaskStatus)
│   └── tools\
│       ├── __init__.py
│       └── path_guard.py               # Người gác cổng ranh giới workspace (PathGuard)
├── tests\                              # 34 bài kiểm thử tự động
│   ├── test_long_term_memory.py        # 11 tests: Bộ nhớ dài hạn V1
│   ├── test_memory.py                  # 4 tests: Episodic memory cơ bản
│   ├── test_path_and_audit.py          # 2 tests: PathGuard & Audit
│   ├── test_planning_and_health.py     # 3 tests: TaskPlan & Health
│   ├── test_policy.py                  # 3 tests: R0 - R5 Policy
│   ├── test_quarantine.py              # 3 tests: CLAE Quarantine
│   ├── test_redaction.py               # 2 tests: Redaction regex
│   └── test_validate_and_report.py     # 6 tests: Handoff report generator
├── tools\
│   ├── merge_starter_safely.py         # Kịch bản sao chép an toàn không ghi đè
│   └── validate_and_report.py          # Công cụ sinh báo cáo bàn giao chuẩn 9 phần cho ChatGPT
└── reports\
    ├── HANDOFF_LATEST.md               # Báo cáo bàn giao mới nhất (chứa Continuation Context cho ChatGPT)
    ├── HANDOFF_YYYYMMDD_HHMMSS.md      # Các bản lưu lịch sử theo mốc thời gian
    └── TEST_RUN_LATEST.txt             # Chi tiết đầu ra pytest mới nhất
```

### 2.1. Phân hệ Bộ nhớ Dài hạn (Long-Term Memory Engine V1)
Đã chuyển hóa từ kho lưu trữ sự kiện đơn giản thành Động cơ Trí nhớ Dài hạn có cấu trúc:
1. **6 Loại trí nhớ (`MemoryType`):**
   - `EPISODIC`: Sự kiện, cuộc trao đổi, nhiệm vụ điều hành và kết quả đạt được.
   - `SEMANTIC`: Kiến thức chuyên môn, dữ kiện khoa học, thực thể và mối quan hệ.
   - `PROCEDURAL`: Quy trình vận hành chuẩn (SOP), hướng dẫn kỹ thuật đã kiểm chứng.
   - `DECISION`: Các quyết định điều hành, lựa chọn được cân nhắc, lý do, giả định và kết quả.
   - `PREFERENCE`: Ưu tiên làm việc, thói quen và chỉ đạo đã được Quanpt1 xác nhận.
   - `CANDIDATE`: Tri thức ứng viên mới học được, bắt buộc ở trạng thái chờ xác minh.
2. **6 Trạng thái xác minh (`VerificationStatus`):**
   - `USER_PROVIDED`: Do chính Quanpt1 cung cấp trực tiếp.
   - `OBSERVED`: Hệ thống quan sát trực tiếp từ đầu ra công cụ hoặc cảm biến.
   - `VERIFIED`: Đã được kiểm chứng thực tế bằng bài kiểm tra hoặc bằng chứng xác thực.
   - `INFERRED`: Suy luận logic của AI, không phải dữ kiện chắc chắn.
   - `UNVERIFIED`: Thông tin tiếp nhận từ bên ngoài nhưng chưa được đối soát.
   - `CANDIDATE`: Tri thức ứng viên đang bị cách ly.
3. **Quản lý Phiên bản & Bảo toàn Lịch sử (Zero Data Loss):**
   - Hàm `supersede_memory()`: Khi có tham số vận hành mới, bản ghi cũ tự động chuyển sang `lifecycle_status = "superseded"` và trỏ `superseded_by` sang bản ghi mới; bản ghi mới được sinh ra với version tăng dần (`v1 -> v2`). Không bao giờ xóa đè dữ liệu cũ.
   - Hàm `trace_source()`: Truy vết ngược dòng thời gian, liệt kê toàn bộ chuỗi tiền nhiệm (predecessors) để giải trình nguồn gốc quyết định.
4. **Tìm kiếm Tiếng Việt có dấu & Chống SQL Injection:**
   - Hàm `search_memories()` hỗ trợ tìm kiếm chuỗi tiếng Việt có dấu, lọc kết hợp theo loại trí nhớ, trạng thái xác minh, nhãn (`tag`) và phạm vi dự án (`project_scope`).
   - Sử dụng 100% truy vấn tham số hóa (`?`), vô hiệu hóa mọi nguy cơ chèn mã SQL độc hại.

### 2.2. Phân hệ Quản trị An toàn & Phân cấp Rủi ro (Governance R0 - R5)
- **R0 (Read-only):** Truy vấn đọc dữ liệu, phân tích không thay đổi trạng thái -> `ALLOW`.
- **R1 (Compute in-memory):** Xử lý tính toán, lập kế hoạch trong bộ nhớ -> `ALLOW`.
- **R2 (Workspace write):** Ghi tệp bên trong workspace -> `ALLOW` (bắt buộc kiểm tra qua `PathGuard`).
- **R3 (Low-impact external action):** Hành động đọc ra ngoài -> `ALLOW_WITH_NOTICE`.
- **R4 (Significant system change):** Thay đổi cấu hình, can thiệp hệ thống -> `APPROVAL_REQUIRED` (yêu cầu phê duyệt từ Quanpt1; hiện chưa có executor tự động).
- **R5 (Prohibited / High Danger):** Các hành vi phá hủy, ghi đè hạ tầng, xóa dữ liệu lớn -> **CHẶN CỨNG (`BLOCKED`)**. Không có bất kỳ bí mật hay cửa hậu nào trong mã nguồn để vượt qua mức R5.

### 2.3. Phân hệ Bảo chứng Nhận thức & Cách ly Tri thức (CLAE Quarantine)
- Tuân thủ nguyên lý nền tảng của DC-COMMAND V6.7: **Học tập không đồng nghĩa với Triển khai (Learning is not Deployment)**.
- Tri thức mới từ AI tự động đưa vào `candidate_knowledge` và bảng `memories` với nhãn `quarantined`.
- Cấm tuyệt đối việc tự động kích hoạt tri thức ứng viên thành quy tắc chính thức nếu thiếu bài kiểm thử hồi quy (`regression_passed == True`) và chữ ký phê duyệt có xác thực từ Quanpt1 (`approval_verified == True`).

### 2.4. Phân hệ Báo cáo Bàn giao Tự động (Automated Engineering Handoff)
- Kịch bản [`tools/validate_and_report.py`](file:///e:/AI/QUAN AI BRAIN/tools/validate_and_report.py) tự động thực thi sau mỗi phiên làm việc, kiểm tra kết quả test thực tế và xuất báo cáo chuẩn hóa 9 phần ra [`reports/HANDOFF_LATEST.md`](file:///e:/AI/QUAN%20AI%20BRAIN/reports/HANDOFF_LATEST.md).
- Báo cáo tích hợp sẵn khối **`CONTINUATION CONTEXT FOR CHATGPT`** giúp ChatGPT ở phiên sau có thể đọc độc lập và tiếp tục công việc ngay lập tức.

---

## 3. MA TRẬN ĐỐI CHIẾU HỆ THỐNG NGOẠI VI & BẢO TỒN NGUYÊN TRẠNG

Để bảo đảm tuyệt đối tính an toàn cho hệ sinh thái của Quanpt1, bảng ma trận dưới đây phân định rõ trạng thái kết nối thực tế:

| Hệ sinh thái | Vị trí vật lý trên máy Dell | Trạng thái tích hợp | Ranh giới kỹ thuật & Cam kết an toàn |
| :--- | :--- | :--- | :--- |
| **QUAN AI BRAIN (Lõi)** | `E:\AI\QUAN AI BRAIN` | `TESTED / IMPLEMENTED` | 34/34 bài test đạt; CSDL SQLite cục bộ `data/brain.db`. |
| **Ollama / Qwen2.5:7b** | `E:\AI\Ollama` | `NOT_VERIFIED` | Các model 7B, 1.5B đã có sẵn trên ổ đĩa; **chưa kết nối runtime** trong Sprint 2A (quy hoạch Sprint 2B). |
| **Kernel L3** | `BAT-AI-2026-Repo\...\os_kernel` | `NOT_IMPLEMENTED` | Tham khảo kiến trúc EventBus & SafetyGuard; **tuyệt đối không sửa trực tiếp**. |
| **DC-COMMAND / CLAE** | `DATA CENTER AI OPERATING SYSTEM` | `PARTIALLY_IMPLEMENTED` | Đã mô phỏng cơ chế Quarantine tri thức; **chưa nối pipeline 30 bước**. |
| **SKILL_BAT_AI** | `E:\AI\Skill\SKILL_BAT_AI` | `NOT_IMPLEMENTED` | Kế thừa mô hình phân cấp rủi ro R0-R5; **giữ nguyên mã nguồn gốc**. |
| **BATTERY_AI_V4** | `E:\AI\battery-ai-\BATTERY_AI_V4` | `NOT_IMPLEMENTED` | Bảo tồn nguyên trạng CSDL `battery_data.db` và tệp `.env`; **không mở hoặc đọc secret**. |
| **VDCIM / NetChat** | Sibling projects | `NOT_IMPLEMENTED` | Chưa kết nối giao tiếp ngoại vi. |
| **Background Daemon 24/7** | N/A | `NOT_IMPLEMENTED` | Mới có skeleton `health.py`; chưa chạy dịch vụ Windows nền. |
| **Voice Interface** | N/A | `NOT_IMPLEMENTED` | Chưa tích hợp bộ nhận diện giọng nói. |

---

## 4. PHÂN TÍCH KHOẢNG TRỐNG KIẾN TRÚC (GAP ANALYSIS) SAU SPRINT 2A

Mặc dù Sprint 2A đã hoàn thiện xuất sắc lớp Trí nhớ Dài hạn và Khung An toàn, hệ thống vẫn còn các khoảng trống cần ChatGPT tiếp tục xây dựng ở các Sprint tiếp theo:

1. **Khoảng trống 1 — Khả năng Suy luận Ngôn ngữ Cục bộ (Local LLM Inference):**
   - Hiện tại hệ thống chưa có khả năng "hiểu" yêu cầu ngôn ngữ tự nhiên phức tạp hoặc sinh câu trả lời bằng AI.
   - Cần xây dựng adapter kết nối an toàn với máy chủ Ollama cục bộ (`http://127.0.0.1:11434`) để khai thác mô hình `qwen2.5:7b` sẵn có.
2. **Khoảng trống 2 — Cầu nối Trí nhớ & Ngữ cảnh Suy luận (Memory-Augmented Generation - MAG):**
   - Động cơ trí nhớ đã có API tìm kiếm, nhưng chưa có lớp tự động trích xuất các SOP, quyết định cũ, sở thích của Quanpt1 để nhúng vào Prompt của LLM trước khi suy luận.
3. **Khoảng trống 3 — Hộp cát Thực thi Công cụ An toàn (Tool Execution Sandbox):**
   - Policy Engine đã có ma trận R0 - R5 nhưng chưa có các bộ thực thi công cụ (Tool Executors) an toàn cho mức R0 - R2 (ví dụ: công cụ đọc tài liệu, công cụ kiểm tra trạng thái Git, công cụ phân tích log).
4. **Khoảng trống 4 — Cơ chế Xác thực Phê duyệt Chủ sở hữu (Authenticated Approval Verifier):**
   - Các tác vụ R4 và việc thăng cấp tri thức ứng viên hiện đang bị chặn an toàn vì chưa có cơ chế tiếp nhận và xác thực mã bí mật (`QUANPT1_APPROVAL_SECRET`) từ Quanpt1.
5. **Khoảng trống 5 — Giám sát Tiến trình Nền 24/7 (Always-on Daemon):**
   - Hệ thống mới chỉ chạy theo yêu cầu dòng lệnh (CLI), chưa có tiến trình nền theo dõi sức khỏe và tự phục hồi (*self-healing*) như thiết kế trong Kernel L3.

---

## 5. ĐỀ XUẤT HỆ THỐNG & KẾ HOẠCH HÀNH ĐỘNG CHO CHATGPT (SPRINT 2B - SPRINT 4)

Dưới đây là kế hoạch chi tiết, khả thi và an toàn nhất để ChatGPT có thể tiếp quản và tiếp tục xây dựng từng bước nhỏ có kiểm thử:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        QUAN AI BRAIN ROADMAP                           │
├──────────────────────────┬─────────────────────────────────────────────┤
│ SPRINT 1 (Hoàn thành)    │ Walking Skeleton + Policy R0-R5 + SQLite    │
│ SPRINT 2A (Hoàn thành)   │ Long-Term Memory V1 + 9-Section Handoff     │
├──────────────────────────┼─────────────────────────────────────────────┤
│ SPRINT 2B (Ưu tiên số 1) │ Local Ollama Provider + Mock Fallback       │
│ SPRINT 2C                │ Memory Context Augmentation (Prompt Router) │
│ SPRINT 3A                │ Safe Tool Sandbox (R0 - R2 Read/Audit)      │
│ SPRINT 3B                │ Escalation & Approval Verifier (R4)         │
│ SPRINT 4                 │ 24/7 Always-On Daemon + Self-Healing        │
└──────────────────────────┴─────────────────────────────────────────────┘
```

### 5.1. ƯU TIÊN SỐ 1: SPRINT 2B — Local Ollama LLM Provider + Health Check + Mock Fallback
- **Mục tiêu:** Cho phép QUAN AI BRAIN giao tiếp với mô hình ngôn ngữ lớn chạy offline trên máy Dell mà không cần kết nối Internet và không tốn chi phí API đám mây.
- **Thiết kế module đề xuất:**
  - Tạo thư mục: `src/quan_ai_brain/llm/`
  - Tệp `models.py`: Định nghĩa cấu trúc `LLMRequest`, `LLMResponse`, `ModelInfo`.
  - Tệp `client.py`: Class `OllamaClient` sử dụng thư viện chuẩn của Python (`urllib.request` / `json`), kết nối tới `http://127.0.0.1:11434`.
    - Phương thức `ping() -> bool`: Kiểm tra dịch vụ Ollama có đang chạy hay không.
    - Phương thức `list_models() -> list[str]`: Liệt kê các model cục bộ (`qwen2.5:7b`, `llama3.1`, ...).
    - Phương thức `generate(prompt: str, model: str = "qwen2.5:7b", temperature: float = 0.2) -> LLMResponse`.
  - Tệp `mock_provider.py`: Class `MockLLMProvider` giả lập phản hồi định sẵn khi Ollama daemon đang tắt. Điều này bảo đảm test suite luôn PASS 100% trong môi trường CI/CD hoặc khi máy chưa bật Ollama.
  - Tệp `provider.py`: Facade tự động phát hiện: Nếu Ollama online thì dùng `OllamaClient`, nếu offline thì fallback sang `MockLLMProvider` kèm cảnh báo.
- **Yêu cầu kiểm thử:**
  - Viết `tests/test_ollama_provider.py`:
    - Test mock generate với các kịch bản phản hồi khác nhau.
    - Test fallback an toàn khi mất kết nối mạng cục bộ.
    - Test timeout và bắt lỗi kết nối không làm sập ứng dụng.
- **Ranh giới an toàn:** Không cấp quyền cho LLM tự ý gọi lệnh thực thi công cụ ở Sprint này; chỉ xử lý text-in / text-out.

### 5.2. SPRINT 2C — Cognitive Memory Retriever & Prompt Augmentation
- **Mục tiêu:** Tự động truy xuất trí nhớ dài hạn (quy trình SOP, sở thích của Quanpt1, quyết định quá khứ) để nhúng vào ngữ cảnh suy luận của LLM.
- **Thiết kế đề xuất:**
  - Module: `src/quan_ai_brain/cognition/context_builder.py`.
  - Thuật toán trích xuất: Khi người dùng đưa ra chỉ thị, hệ thống phân tích từ khóa -> gọi `MemoryStore.search_memories()` lấy top 3 SOP (`PROCEDURAL`) và top 3 dữ kiện đã duyệt (`SEMANTIC`) -> định dạng thành khối System Prompt chuẩn hóa.
  - Phân định minh bạch trong Prompt:
    ```
    [NGỮ CẢNH HỆ THỐNG - ĐÃ DUYỆT]
    - Dữ kiện xác minh: ...
    - Quy trình chuẩn (SOP): ...
    [LƯU Ý AN TOÀN]
    - R5 bị chặn cứng; không thực hiện hành vi can thiệp trái phép.
    ```

### 5.3. SPRINT 3A — Safe Tool Sandbox (R0 - R2 Read/Audit)
- **Mục tiêu:** Xây dựng các công cụ an toàn trong hộp cát được Policy Engine kiểm duyệt:
  - `Tool_ReadFile`: Đọc tệp văn bản trong workspace (được bảo vệ bởi `PathGuard`).
  - `Tool_GitStatus`: Kiểm tra trạng thái kho Git nội bộ.
  - `Tool_InspectMemory`: Truy vấn cơ sở tri thức.
- **Nguyên tắc:** Mỗi khi công cụ được yêu cầu, phải chuyển qua `PolicyEngine.authorize()`. Nếu vi phạm (ví dụ đòi đọc tệp `.env` hoặc thoát workspace), hệ thống từ chối ngay lập tức.

### 5.4. SPRINT 3B — Escalation Engine & Approval Verifier (R4)
- **Mục tiêu:** Xây dựng cơ chế tiếp nhận mã phê duyệt khẩn cấp từ Quanpt1 cho các tác vụ cấp R4.
- **Thiết kế đề xuất:**
  - Cơ chế băm an toàn (`hmac` + `sha256`) đối soát mã phê duyệt thay vì lưu secret dạng plain text trong mã nguồn.
  - Khi phê duyệt thành công, ghi nhận vào `AuditLogger` và cho phép thực thi tác vụ trong phiên làm việc đó.

### 5.5. SPRINT 4 — Always-on Background Daemon & Health Supervision
- **Mục tiêu:** Nâng cấp `quan_ai_brain.daemon` thành một tiến trình nền chạy 24/7 trên Windows:
  - Tự động chạy heartbeat kiểm tra định kỳ (15 phút/lần).
  - Tự kiểm tra tính toàn vẹn CSDL và tiến trình Ollama.
  - Cơ chế tự phục hồi (*Self-Healing*) kế thừa từ kiến trúc Kernel L3.

---

## 6. CÁC QUY TẮC AN TOÀN BẤT BIẾN DÀNH CHO KỸ SƯ KẾ NHIỆM

Khi ChatGPT hoặc bất kỳ AI Engineer nào tiếp tục phát triển codebase này, phải tuyệt đối tuân thủ 10 điều lệnh sau:

1. **Workspace Confinement:** Chỉ được tạo hoặc chỉnh sửa tệp trong thư mục `E:\AI\QUAN AI BRAIN`. Tuyệt đối không can thiệp, di chuyển hoặc ghi đè vào các thư mục lân cận (`os_kernel`, `SKILL_BAT_AI`, `BATTERY_AI_V4`, `DC-COMMAND`, `BOT`).
2. **Zero Hard-Coded Credentials:** Tuyệt đối không thêm secret, private key, token, API key hoặc mật khẩu vào mã nguồn. R5 luôn là hard-blocked.
3. **No Secret Ingestion:** Không đọc nội dung các tệp `.env`, certificates, credential stores hay biến môi trường máy chủ để đưa vào báo cáo hay mã nguồn.
4. **Learning is Not Deployment:** Mọi tri thức mới AI học được phải lưu ở dạng `CANDIDATE` và bị cách ly (`quarantined`). Không được thăng cấp nếu chưa có regression test pass và xác minh người sở hữu.
5. **No Blind git init / commit:** Không tự ý chạy `git init` nếu repo đã tồn tại; không tự ý commit nếu chưa có yêu cầu từ người dùng.
6. **Code Diff First:** Trình bày rõ diff và danh sách tệp dự kiến thay đổi trước khi sửa các tệp hiện hữu.
7. **Test-Driven Progression:** Sau mỗi thay đổi, phải chạy `pytest tests/` và chỉ nghiệm thu khi toàn bộ test suite đạt kết quả PASS.
8. **Automated Handoff Maintenance:** Sau khi hoàn thành một bước làm việc, bắt buộc chạy `python tools/validate_and_report.py` để làm mới tệp `reports/HANDOFF_LATEST.md`.
9. **Truthful Documentation:** Không tuyên bố một tính năng đã hoàn thành chỉ vì tệp hoặc thư mục tồn tại. Phải phân định rạch ròi giữa `IMPLEMENTED & TESTED`, `PARTIALLY_IMPLEMENTED` và `NOT_IMPLEMENTED`.
10. **Preserve Backward Compatibility:** Mọi nâng cấp về CSDL hay API bộ nhớ phải bảo đảm tương thích ngược với các bài kiểm thử và dữ liệu đã lưu từ các Sprint trước.

---

## 7. BẢN TIN BÀN GIAO TIẾP NỐI CHO PHIÊN CHATGPT TIẾP THEO (HANDOFF PAYLOAD)

> 💡 **HƯỚNG DẪN DÀNH CHO QUANPT1:**  
> Khi bắt đầu phiên làm việc mới trên ChatGPT, anh chỉ cần **sao chép toàn bộ khung lệnh dưới đây** và gửi vào ChatGPT. ChatGPT sẽ nhận diện toàn bộ hiện trạng kỹ thuật và tiếp tục xây dựng Sprint 2B một cách chính xác tuyệt đối.

```markdown
# NHIỆM VỤ TIẾP QUẢN: QUAN AI BRAIN — SPRINT 2B
## LOCAL OLLAMA LLM PROVIDER + HEALTH CHECK + MOCK FALLBACK

Chào ChatGPT, bạn đang tiếp quản vai trò AI Software Architect & Senior Python Engineer để tiếp tục phát triển hệ thống QUAN AI BRAIN cho Quanpt1 tại workspace:
`E:\AI\QUAN AI BRAIN`

### 1. Bối cảnh & Hiện trạng Kỹ thuật Thực tế (Đã hoàn thành Sprint 1 & Sprint 2A)
- Môi trường: Dell Precision 7550, Windows 10 Pro x64, Python 3.11.9 (.venv), Git repo đã khởi tạo.
- Toàn bộ 34/34 bài test hiện đang PASS 100%:
  - Long-Term Memory Engine V1 hoàn chỉnh: 6 loại trí nhớ (EPISODIC, SEMANTIC, PROCEDURAL, DECISION, PREFERENCE, CANDIDATE), 6 trạng thái xác minh, CSDL SQLite memories, quản lý phiên bản (v1 -> v2) không mất lịch sử cũ, truy vết dòng giống trace_source(), tìm kiếm tiếng Việt có dấu, tham số hóa chống SQL injection, cách ly tri thức ứng viên (CLAE Quarantine).
  - Khung quản trị R0 - R5 (R5 chặn cứng; R4 yêu cầu duyệt; R2 giới hạn workspace).
  - PathGuard bảo vệ ranh giới workspace; AuditLogger JSONL; Redaction regex che giấu secret.
  - Công cụ tạo báo cáo tự động tools/validate_and_report.py cập nhật đầy đủ 9 phần tại reports/HANDOFF_LATEST.md.
- Các hệ thống ngoại vi được bảo toàn tuyệt đối không can thiệp:
  `E:\AI\DATA CENTER AI OPERATING SYSTEM` (DC-COMMAND V6.7 / CLAE)
  `E:\AI\BAT-AI-2026-Repo\battery-ai-\os_kernel` (Kernel L3)
  `E:\AI\Skill\SKILL_BAT_AI` (Autonomous Workforce OS)
  `E:\AI\battery-ai-\BATTERY_AI_V4` (Battery Intelligence Brain)
  `E:\AI\BOT` (Production Bots)
  `E:\AI\Ollama` (Local models: qwen2.5:7b có sẵn trên đĩa)

### 2. Nhiệm vụ của Bạn trong Phiên này: SPRINT 2B
Hãy triển khai phân hệ Local Ollama LLM Provider cho QUAN AI BRAIN:
1. Tạo package `src/quan_ai_brain/llm/`:
   - `models.py`: Dataclass typed cho yêu cầu/phản hồi LLM (LLMRequest, LLMResponse, ModelInfo).
   - `client.py`: Class `OllamaClient` dùng thư viện chuẩn Python (urllib.request/json), kết nối tới endpoint cục bộ `http://127.0.0.1:11434`. Cung cấp các hàm `ping()`, `list_models()`, `generate(prompt, model="qwen2.5:7b", temperature=0.2)`.
   - `mock_provider.py`: Class `MockLLMProvider` phục vụ chạy test offline khi tiến trình Ollama daemon đang tắt.
   - `provider.py`: Class `LLMProvider` facade tự động kiểm tra: nếu Ollama online thì gọi OllamaClient, nếu offline thì fallback sang MockLLMProvider an toàn.
2. Viết bộ kiểm thử toàn diện `tests/test_llm_provider.py`:
   - Test MockLLMProvider sinh phản hồi đúng cấu trúc.
   - Test OllamaClient xử lý lỗi kết nối và timeout (ConnectionRefusedError / TimeoutError) êm ái mà không làm crash ứng dụng.
   - Test cơ chế tự động fallback sang Mock khi offline.
   - Test tự động che giấu credential nếu người dùng vô tình đưa token vào prompt (tích hợp `redact_text`).
3. Đảm bảo toàn bộ 34 bài test cũ + các bài test mới đều PASS (Tổng cộng >= 38 tests).
4. Cập nhật `docs/PROJECT_STATUS.md` và chạy `tools/validate_and_report.py` để sinh báo cáo mới nhất.

### 3. Nguyên tắc Kỹ thuật Bắt buộc
- Chỉ làm việc trong `E:\AI\QUAN AI BRAIN`. Không chỉnh sửa các thư mục bên ngoài.
- Dùng standard library Python (urllib, json, dataclasses, enum). Không tự ý cài thêm dependency nặng nếu chưa cần thiết.
- Không cấp quyền thực thi công cụ nguy hiểm cho LLM ở giai đoạn này (chỉ xử lý text-in / text-out).
- Luôn trình bày kế hoạch nhỏ và diff mã nguồn trước khi áp dụng.

Hãy bắt đầu bằng việc xác nhận bạn đã hiểu bối cảnh hiện trạng và trình bày kế hoạch triển khai chi tiết cho Sprint 2B!
```

---

*Báo cáo được lập và lưu trữ an toàn tại:*  
📁 [`e:\AI\QUAN AI BRAIN\bao cao xay dung he thong\BAO_CAO_HIEN_TRANG_VA_DE_XUAT_TIEP_TUC_XAY_DUNG.md`](file:///e:/AI/QUAN%20AI%20BRAIN/bao%20cao%20xay%20dung%20he%20thong/BAO_CAO_HIEN_TRANG_VA_DE_XUAT_TIEP_TUC_XAY_DUNG.md)
