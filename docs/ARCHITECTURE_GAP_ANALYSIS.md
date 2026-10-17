# ARCHITECTURE GAP ANALYSIS: QUAN AI BRAIN
**Document ID:** DOC-QAB-GAP-001  
**Audit Date:** 2026-10-17  
**Auditor / Role:** AI Software Architect & Senior Engineer  
**Target Goal:** Digital Executive Assistant (Trợ lý Điều hành Số Toàn diện)  
**Workspace:** `e:\AI\QUAN AI BRAIN`

---

## 1. Tầm nhìn Kiến trúc Mục tiêu
QUAN AI BRAIN được định vị là một **Trợ lý Điều hành Số (Digital Executive Assistant)** cấp cao dành riêng cho Quanpt1, sở hữu các năng lực then chốt:
1. **Tiếp nhận & Thấu hiểu tự nhiên:** Giao tiếp qua ngôn ngữ tự nhiên, phân tách ngữ cảnh chỉ đạo điều hành.
2. **Trí nhớ dài hạn đa tầng (Multi-tier Long-term Memory):** Lưu trữ và truy xuất tri thức, quyết định, quy tắc nghiệp vụ, lịch sử kinh nghiệm và bài học đã xác minh.
3. **Lập kế hoạch & Thực thi có kiểm soát (Planning & Authorized Execution):** Phân rã mục tiêu thành lộ trình hành động; tự động thực thi các tác vụ trong phạm vi được ủy quyền; dừng lại xin phê duyệt khi gặp rủi ro cao.
4. **Kiểm chứng kết quả độc lập (Outcome Verification & Self-Check):** Kiểm tra tính đúng đắn trước khi bàn giao; tự động kiểm tra hồi quy; chống ngẫu nhiên.
5. **Học tập liên tục từ kinh nghiệm (Cognitive Continuous Learning):** Tích lũy tri thức mới sau mỗi nhiệm vụ thành công hoặc sau khi được con người điều chỉnh, tuân thủ nguyên tắc cách ly an toàn (*Learning != Direct Deployment*).
6. **Vận hành bền bỉ 24/7 (Resilient Background Daemon):** Hoạt động liên tục, tự phục hồi khi có sự cố, không phụ thuộc vào trạng thái mở giao diện của người dùng.

---

## 2. Phân tích Khoảng cách (Gap Analysis) theo Khối Chức năng

```
                     MỤC TIÊU: QUAN AI BRAIN (EXECUTIVE ASSISTANT)
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             Executive Gateway & API                              │
├─────────────────────┬──────────────────────┬─────────────────────────────────────┤
│  1. Memory Engine   │ 2. Planning & Authz  │ 3. Execution & Tool Sandbox         │
│  - Episodic Memory  │ - Goal Decomposition │ - Tool Registry                     │
│  - Semantic Store   │ - Risk Matrix R0-R5  │ - Pre/Post Execution Validation     │
│  - Experience DB    │ - Approval Escalation│ - Idempotent Actions                │
├─────────────────────┴──────────────────────┴─────────────────────────────────────┤
│                        4. Cognitive Learning Engine                              │
│         - CLAE 30-Step Assurance Pipeline (Evidence Provenance, Zero Regression) │
├──────────────────────────────────────────────────────────────────────────────────┤
│                        5. Background Daemon & Kernel                             │
│         - Event Bus, Task Scheduler, Health Monitor, Self-Healing Watchdog       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Bảng Đối chiếu: Hiện trạng vs Khoảng cách vs Giải pháp Tận dụng Hệ thống Có sẵn

| Khối Chức năng | Hiện trạng Workspace `QUAN AI BRAIN` | Tài nguyên Hệ thống Hiện hữu Liên quan | Khoảng cách Kỹ thuật (Gap) | Giải pháp Kiến trúc Kế thừa |
| :--- | :--- | :--- | :--- | :--- |
| **1. Tiếp nhận Ngôn ngữ & Suy luận** | Chưa có | Ollama đã cài đặt tại `E:\AI\Ollama` với model `qwen2.5:7b` sẵn có trên đĩa. | Thiếu client adapter kết nối với Ollama; thiếu fallback xử lý khi model bận hoặc offline. | Xây dựng `LLMProvider` hỗ trợ cả Local Ollama (Qwen2.5:7b) và Cloud API (nếu cần), có fallback và timeout an toàn. |
| **2. Trí nhớ Dài hạn (Memory Engine)** | Chưa có | - `BATTERY_AI_V4` có cấu trúc KEDB & SQLite.<br>- `SKILL_BAT_AI` có `ai_workforce.db`.<br>- CLAE có 7-Layer Extended Memory. | Chưa có lược đồ cơ sở dữ liệu (schema) chuẩn cho Executive Memory (ghi nhớ quyết định điều hành, tri thức của Quanpt1). | Thiết kế SQLite/DuckDB + Vector Index cục bộ cho 3 tầng nhớ: Episodic (nhật ký việc làm), Semantic (tri thức), Procedural (quy tắc điều hành). |
| **3. Lập kế hoạch & Đánh giá Rủi ro** | Chưa có | `SKILL_BAT_AI` đã có sẵn ma trận rủi ro `RiskEngine` (R0-R5) và hàng rào phân quyền `AuthzEngine`. | Các rule hiện tại của SKILL_BAT_AI đang gắn liền với nghiệp vụ pin/hạ tầng, chưa tổng quát hóa cho Trợ lý Điều hành. | Kế thừa nguyên lý R0-R5 của `RiskEngine` và cơ chế bí mật `QUANPT1_APPROVAL_SECRET`, trừu tượng hóa thành `BrainGovernanceEngine`. |
| **4. Thực thi & Hộp cát Công cụ (Tool Sandbox)** | Chưa có | `Kernel L3` (`os_kernel`) có `SafetyGuard`, `CapabilityManager`. | Chưa có Tool Registry trong Brain để đăng ký công cụ an toàn, chưa có cơ chế sandbox bảo vệ tệp tin và môi trường. | Xây dựng `ToolRegistry` theo mô hình Capability-based Security của Kernel L3: mọi thao tác tệp, lệnh hệ thống đều phải qua kiểm duyệt an toàn. |
| **5. Kiểm chứng Kết quả & Tự học** | Chưa có | `DC-COMMAND V6.7 / CLAE` đã định nghĩa quy chuẩn 30 bước bảo chứng học tập, *Luck vs Learning*, *Zero Regression*. | Chưa có module nào trong Brain hiện thực hóa CLAE cho tác vụ trợ lý chung (văn bản, báo cáo, phân tích dữ liệu, tự động hóa). | Chắt lọc các bước cốt lõi của CLAE: Xác minh bằng chứng (Evidence Provenance), Kiểm tra hồi quy (Regression Test), và Cách ly tri thức mới (Quarantine Sandbox). |
| **6. Vận hành Ngầm 24/7 (Daemon)** | Chưa có | - `Kernel L3` có `TaskScheduler`, `HealthMonitor`, `SelfHealingEngine`.<br>- `SKILL_BAT_AI` có daemon Zero-Touch. | Chưa có process supervisor hoặc Windows Service daemon cho `QUAN AI BRAIN`. | Tái cấu trúc mô hình micro-kernel nhẹ từ Kernel L3 thành `BrainDaemonRunner` chạy dịch vụ ngầm có watchdog và ghi log độc lập. |

---

## 3. Phân tích Rủi ro Chính (Principal Risks)

### R1. Rủi ro Phá vỡ Quy tắc An toàn Hệ thống (Safety Violation Risk)
- **Mô tả:** Trợ lý AI thực thi các lệnh hệ thống hoặc can thiệp tệp tin ngoài ý muốn gây ảnh hưởng đến dữ liệu sản xuất hoặc các hệ thống pin/trung tâm dữ liệu lân cận.
- **Biện pháp giảm thiểu:**
  - Áp dụng nguyên tắc Zero-Trust nội bộ.
  - Phân loại lệnh thành R0-R5: R0-R2 tự động thực thi; R3 yêu cầu log xác nhận; R4-R5 bắt buộc dừng lại và xin mã phê duyệt của Quanpt1.
  - Đảm bảo Workspace Sandbox: Không ghi ra ngoài workspace nếu không có chỉ thị rõ ràng.

### R2. Rủi ro Ảo giác và Học sai Tri thức (Hallucination & Faulty Learning)
- **Mô tả:** AI ghi nhận thông tin sai lệch vào bộ nhớ dài hạn, dẫn đến các quyết định điều hành sai lệch về sau.
- **Biện pháp giảm thiểu:**
  - Áp dụng nguyên lý CLAE: Mọi tri thức học được từ tương tác phải qua vùng đệm cách ly (Candidate Knowledge Quarantine).
  - Chỉ khi kết quả được xác minh thực tế (Ground Truth Verification) hoặc Quanpt1 bấm duyệt thì mới đưa vào Production Memory.

### R3. Rủi ro Gián đoạn Vận hành Tiến trình Nền (Daemon Crash & Drift)
- **Mô tả:** Script chạy ngầm bị crash do rò rỉ bộ nhớ, nghẽn tài nguyên CPU/GPU hoặc lỗi không bắt được ngoại lệ (unhandled exception).
- **Biện pháp giảm thiểu:**
  - Tích hợp Heartbeat và Self-Healing Engine kế thừa từ Kernel L3.
  - Thiết kế tiến trình theo trạng thái phi trạng thái từng phần (Checkpointed State) trong SQLite để khi khởi động lại có thể tiếp tục ngay tác vụ đang dang dở.

### R4. Rủi ro Lộ Bí mật & Thông tin Nhạy cảm (Secret Leakage)
- **Mô tả:** Trợ lý quét trúng tệp cấu hình chứa API key, mật khẩu từ các project cũ (`.env`, config tokens) và xuất vào log hoặc báo cáo.
- **Biện pháp giảm thiểu:**
  - Bộ lọc Redaction Filter chủ động quét và loại bỏ mọi chuỗi dạng API Key, Secret Token, Bearer, Password trước khi ghi log hoặc gửi phản hồi.
  - Cấm hoàn toàn việc mở hoặc đọc nội dung các tệp có đuôi `.env`, `.pem`, `.key` trong toàn bộ quy trình.

---

## 4. Các Phụ thuộc Cốt lõi (Core Dependencies)
1. **Python 3.11 / 3.14:** Môi trường thực thi tiêu chuẩn trên máy chủ.
2. **Local Ollama Daemon:** Cần có script/lệnh khởi động và quản lý trạng thái Ollama tự động khi cần suy luận cục bộ bằng `qwen2.5:7b`.
3. **SQLite3:** Lưu trữ nhẹ, tin cậy cao, tích hợp sẵn trong Python standard library, không đòi hỏi cài đặt database server phức tạp.
4. **Git Version Control:** Cần được khởi tạo trong workspace `e:\AI\QUAN AI BRAIN` để kiểm soát mọi diff và lịch sử thay đổi mã nguồn.

---

## 5. Kết luận Gap Analysis
Để hiện thực hóa QUAN AI BRAIN, chúng ta **không cần viết lại từ đầu bằng cách thử nghiệm mò mẫm**, mà sẽ **tích hợp và nâng cấp các khối kiến trúc tinh hoa đã được kiểm nghiệm thực tế từ Quanpt1**:
- Tư duy bảo đảm học tập và chống thoái biến của **CLAE**.
- Lớp vỏ điều phối, tự phục hồi và bảo vệ hệ thống của **Kernel L3**.
- Khung phân cấp rủi ro, phân quyền và tự hành Zero-Touch của **SKILL_BAT_AI**.
- Khả năng xử lý ngôn ngữ bảo mật cục bộ của **Ollama / Qwen2.5:7b**.
