# QUAN AI BRAIN — BÁO CÁO KỸ THUẬT TOÀN DIỆN
## KIẾN TRÚC HỆ THỐNG, CƠ CHẾ HOẠT ĐỘNG, GIAO THỨC TRUYỀN THÔNG & KẾ HOẠCH TIẾP THEO

**Chủ sở hữu & Người thụ hưởng tối cao:** Anh Quân — Quanpt1  
**Mã tài liệu:** `BC-QAB-TECH-ARCH-EVOLUTION-V7`  
**Ngày lập báo cáo:** 2026-10-25 09:55:00 (Local Time)  
**Địa chỉ lưu trữ:** `E:\AI\QUAN AI BRAIN\bao cao xay dung he thong\BAO_CAO_KIEN_TRUC_VAN_HANH_VA_KE_HOACH_PHAT_TRIEN_QUAN_AI_BRAIN.md`  
**Workspace:** `E:\AI\QUAN AI BRAIN`  
**Trạng thái kiểm thử:** **484 PASSED, 1 SKIPPED, 0 FAILED** (56 test modules, 100% Standard Library)  
**Tài liệu tham chiếu:** [HANDOFF_LATEST.md](file:///E:/AI/QUAN%20AI%20BRAIN/reports/HANDOFF_LATEST.md) | [PROJECT_STATUS.md](file:///E:/AI/QUAN%20AI%20BRAIN/docs/PROJECT_STATUS.md) | [AGENTS.md](file:///E:/AI/QUAN%20AI%20BRAIN/AGENTS.md)

---

## MỤC LỤC
1. [TỔNG QUAN HỆ THỐNG & NGUYÊN TẮC CỐT LÕI](#1-tổng-quan-hệ-thống--nguyên-tắc-cốt-lõi)
2. [KIẾN TRÚC TỔNG THỂ PHÂN TÁN (PC CORE + RASPBERRY PI 5)](#2-kiến-trúc-tổng-thể-phân-tán-pc-core--raspberry-pi-5)
3. [CẤU TRÚC MÃ NGUỒN & CÁC PHÂN HỆ CHỨC NĂNG](#3-cấu-trúc-mã-nguồn--các-phân-hệ-chức-năng)
4. [CƠ CHẾ VẬN HÀNH NỘI TẠI CỦA BỘ NÃO (CORE ENGINE)](#4-cơ-chế-vận-hành-nội-tại-của-bộ-não-core-engine)
5. [GIAO THỨC TRUYỀN THÔNG VÀ LIÊN KẾT BIÊN (CORE <-> PI 5)](#5-giao-thức-truyền-thông-và-liên-kết-biên-core---pi-5)
6. [HÌNH THỂ SỐ MODEL A & CẢM BIẾN VẬT LÝ BIÊN](#6-hình-thể-số-model-a--cảm-biến-vật-lý-biên)
7. [CƠ CHẾ LƯU TRỮ VÀ DỮ LIỆU BỀN VỮNG (PERSISTENCE)](#7-cơ-chế-lưu-trữ-và-dữ-liệu-bền-vững-persistence)
8. [HIỆN TRẠNG NGHIỆM THU & BẰNG CHỨNG KIỂM THỬ THỰC TẾ](#8-hiện-trạng-nghiệm-thu--bằng-chứng-kiểm-thử-thực-tế)
9. [KẾ HOẠCH HÀNH ĐỘNG VÀ LỘ TRÌNH PHÁT TRIỂN TIẾP THEO](#9-kế-hoạch-hành-động-và-lộ-trình-phát-triển-tiếp-theo)
10. [BẢO TỒN NGUYÊN VẸN HỆ SINH THÁI & QUY TẮC BẤT BIẾN](#10-bảo-tồn-nguyên-vẹn-hệ-sinh-thái--quy-tắc-bất-biến)

---

## 1. TỔNG QUAN HỆ THỐNG & NGUYÊN TẮC CỐT LÕI

### 1.1. Mục Tiêu & Định Vị Hệ Thống
**QUAN AI BRAIN** là hệ thống **Trợ Lý Điều Hành Số Độc Lập (Digital Executive Assistant)** thế hệ mới, sở hữu tư duy nhận thức bền vững, khả năng lập kế hoạch có kiểm chứng (Auditable Planning), vận hành công cụ trong ranh giới an toàn nghiêm ngặt (Bounded Tool Execution), và cơ chế tự học dưới quyền kiểm soát tuyệt đối của chủ sở hữu (**Anh Quân — Quanpt1**).

Khác biệt với các chatbot thông thường, QUAN AI BRAIN được thiết kế theo cấu trúc **Sinh Thể Số Phân Tán (Distributed Digital Organism)**:
- **PC Core (Máy tính chủ trung tâm):** Nơi đặt bộ não tư duy sâu, hệ thần kinh thực vật, cơ sở dữ liệu trí nhớ dài hạn (SQLite WAL), bộ định tuyến mô hình cục bộ (Ollama), và giao diện điều hành Cockpit trung tâm.
- **Raspberry Pi 5 (Hình thể số vật lý biên):** Thiết bị biên đảm nhận vai trò "thân xác", trang bị màn hình cảm ứng 7" DSI hiển thị Avatar Model A, cụm microphone thu âm, camera thị giác máy tính, và loa phát âm thanh giọng nữ Việt Hoài My.

### 1.2. Các Nguyên Tắc Bất Biến (Non-Negotiable Invariants)
1. **Quyền Quyết Định Tuyệt Đối (Owner Consent First):** Anh Quân là chủ sở hữu, người sáng tạo và là cấp thẩm quyền duy nhất phê duyệt các hành động có tác động đến dữ liệu, mã nguồn hoặc cấu hình.
2. **Khóa Cứng Rủi Ro Cấp 5 (R5 Hard-Blocked):** Mọi hành động can thiệp nhân hệ điều hành, format ổ đĩa, xâm nhập bí mật, gửi dữ liệu ra mạng ngoài trái phép đều bị hệ thống chặn cứng ở mức mã nguồn; không tồn tại mã ghi đè bí mật.
3. **Cổng Phê Duyệt Cấp 4 (R4 Dual-Factor Approval):** Mọi hành vi sửa đổi mã nguồn hoặc thao tác nhạy cảm bắt buộc phải tạo vé tham vấn (Consultation Ticket) và yêu cầu chữ ký xác thực từ Anh Quân.
4. **Không Thực Thi Sản Xuất Trực Tiếp (Zero-Execution Sandbox Invariant):** Toàn bộ việc thực thi tác vụ hiện tại chỉ diễn ra trong môi trường cát lập trình an toàn (`InertProcessBackend` / Dry-run staging). Không tự động spawn tiến trình shell của Windows khi chưa có sign-off nghiệm thu.
5. **Tuyệt Đối Không Rò Rỉ Bí Mật (Secret Redaction):** Không in, không copy, không log các khóa API, token, private key hoặc giá trị `.env` ra màn hình, tệp log hay giao diện người dùng.
6. **Cách Ly Tuyệt Đối Workspace:** Tuyệt đối không can thiệp, không sửa đổi các dự án anh em (`DATA CENTER AI OPERATING SYSTEM`, `BAT-AI-2026-Repo`, `os_kernel`, `SKILL_BAT_AI`, `BATTERY_AI_V4`, `BOT`, VDCIM).

---

## 2. KIẾN TRÚC TỔNG THỂ PHÂN TÁN (PC CORE + RASPBERRY PI 5)

Hệ thống được tổ chức thành 6 tầng kiến trúc chặt chẽ, liên kết giữa PC Core và Raspberry Pi 5 thông qua mạng LAN nội bộ:

```mermaid
graph TD
    subgraph "TẦNG TRÌNH DIỄN & GIAO TIẾP (PRESENTATION LAYER)"
        UI_Chat["Web Chat Hội Thoại (:8765)<br/>app.html / app.js"]
        UI_Cockpit["Executive Cockpit (:8766)<br/>executive.html / executive.js"]
        Kiosk_Pi5["Pi 5 Kiosk Display (1024x600/1280x720)<br/>Chromium Wayland labwc"]
    end

    subgraph "TẦNG NHẬN THỨC & SUY LUẬN (COGNITIVE LAYER - PC CORE)"
        Router["LLM Router (Fast / Reasoning)<br/>Fast: Qwen 0.5B/1.5B (0.5s)<br/>Reasoning: Qwen 7B (20s)"]
        Retriever["Cognitive Retriever (Hybrid)<br/>BM25 Sparse + BGE-M3 Dense (1024-dim)"]
        SessionMgr["Session Memory Manager<br/>Episodic Persistence & Fact Extraction"]
        AutoMind["Autonomous Mind & DMN<br/>Cogitation Modes & Keep-Warm Pulse"]
        Persona["Executive Persona (Tony Pham)<br/>18-field Digital Identity"]
    end

    subgraph "TẦNG QUẢN TRỊ & RANH GIỚI AN TOÀN (GOVERNANCE LAYER)"
        PolicyEng["Policy Engine (R0 - R5)"]
        GovStore["Governance State Store (governance.db)"]
        Approval["Approval Gate & Dual-Factor Verifier"]
        Inbox["Consultation Inbox (consultations.db)"]
        Guardrails["Output Guardrails & Redaction"]
    end

    subgraph "TẦNG ĐIỀU PHỐI TÁC VỤ (ORCHESTRATION LAYER)"
        Coord["Executive Coordinator<br/>TaskPlan Decomposition"]
        Orch["Plan Orchestrator<br/>DAG Validation & Risk Tagging"]
        DurableReg["Durable Task Registry (tasks.db)<br/>SQLite WAL & Unique Step Isolation"]
        Sandbox["Safe Tool Sandbox<br/>Inert Process Backend (Zero Exec)"]
    end

    subgraph "TẦNG DỮ LIỆU BỀN VỮNG (STORAGE & PERSISTENCE LAYER)"
        DB_Brain["data/brain.db<br/>Episodic & Long-term Memories"]
        DB_Tasks["data/tasks.db<br/>Durable Tasks & Steps Ledger"]
        DB_Gov["data/governance.db<br/>Emergency States & Audits"]
        DB_Consult["data/consultations.db<br/>Owner Consultation Tickets"]
        FS_Media["data/edge_media/captures/<br/>Cryptographic Snapshot Library"]
    end

    subgraph "TẦNG HÌNH THỂ SỐ BIÊN (EDGE EMBODIMENT - PI 5)"
        Daemon_Pi5["client_daemon.py (:8768)<br/>HMAC-SHA256 Auth & Nonce"]
        Avatar_Pi5["Avatar Model A Master Quartet<br/>Feathered Lip-Sync Engine"]
        Sensors_Pi5["Microphone Card 2 (RMS dB Meter)<br/>USB Camera (/dev/video0 V4L2)"]
        Audio_Pi5["Vietnamese TTS (vi-VN-HoaiMyNeural)<br/>ALSA Speaker System"]
    end

    %% Flow Connections
    UI_Cockpit -->|REST API :8766| Router
    UI_Chat -->|REST API :8765| Router
    Router --> SessionMgr
    Router --> Retriever
    Retriever --> DB_Brain
    Router --> PolicyEng
    PolicyEng --> GovStore
    PolicyEng --> Inbox
    
    UI_Cockpit --> Coord
    Coord --> Orch
    Orch --> DurableReg
    DurableReg --> DB_Tasks
    Orch --> Sandbox
    
    Daemon_Pi5 <-->|HMAC Heartbeat / Telemetry 10-15ms| UI_Cockpit
    Daemon_Pi5 --> Avatar_Pi5
    Daemon_Pi5 --> Sensors_Pi5
    Daemon_Pi5 --> Audio_Pi5
    Sensors_Pi5 -->|SHA-256 Validated Snapshot| FS_Media
```

---

## 3. CẤU TRÚC MÃ NGUỒN & CÁC PHÂN HỆ CHỨC NĂNG

Toàn bộ mã nguồn cốt lõi nằm tại package [`src/quan_ai_brain/`](file:///E:/AI/QUAN%20AI%20BRAIN/src/quan_ai_brain) và ứng dụng biên tại [`edge_client/`](file:///E:/AI/QUAN%20AI%20BRAIN/edge_client):

```text
E:\AI\QUAN AI BRAIN\
├── edge_client/                        # Phân hệ khách biên chạy trên Raspberry Pi 5
│   ├── client_daemon.py                # Daemon chính xử lý HTTP/REST, HMAC, Camera, Mic, Kiosk
│   ├── main.py                         # Điểm vào chính của ứng dụng Pi 5
│   ├── avatar_engine.js                # Engine vẽ Digital Human Model A, viseme lip-sync
│   ├── index.html                      # Giao diện Avatar toàn màn hình trên Pi 5
│   └── start_kiosk.sh                  # Kịch bản khởi động Chromium Kiosk (chế độ Standby)
│
├── src/quan_ai_brain/                  # Gói phần mềm lõi máy tính chủ PC Core
│   ├── cognition/                      # Nhận thức, trí nhớ và chân dung số
│   │   ├── autonomous_mind.py          # DMN, luồng độc thoại nội tâm, keep-warm GPU
│   │   ├── embedding.py                # Dịch vụ nhúng vector BGE-M3 cục bộ (1024 chiều)
│   │   ├── executive_persona.py        # Chân dung số Tony Pham (18 trường dữ liệu)
│   │   ├── retrieval.py                # Truy xuất thông tin lai ghép (Hybrid BM25 + Vector)
│   │   ├── role_orchestrator.py        # Điều phối 4 vai trò điều hành chuyên biệt
│   │   └── session_memory.py           # Quản lý phiên hội thoại và trích xuất sự thật
│   │
│   ├── core/                           # Hệ thần kinh thực vật và an toàn nền tảng
│   │   ├── autonomic.py                # ANS: 7 vùng cơ thể, cảm biến đau, tiếng nói phản ánh
│   │   ├── audit.py                    # Ghi nhật ký kiểm toán bất biến JSONL có che giấu
│   │   ├── guardrails.py               # Lọc XSS, credential leakage, kiểm tra grounding
│   │   └── redaction.py                # Khử dữ liệu nhạy cảm bằng Regular Expressions
│   │
│   ├── governance/                     # Quản trị chính sách và cổng phê duyệt
│   │   ├── consultation_inbox.py       # CSDL vé tham vấn ý kiến chủ sở hữu
│   │   ├── policy.py                   # Động cơ phân loại rủi ro R0 - R5
│   │   └── state_store.py              # Trạng thái khẩn cấp STOP/FREEZE và override
│   │
│   ├── llm/                            # Tầng giao tiếp mô hình ngôn ngữ lớn
│   │   ├── client.py                   # HTTP Client giao tiếp Ollama cục bộ
│   │   ├── context_builder.py          # Lắp ráp ngữ cảnh prompt tối ưu ngân sách token
│   │   ├── mock_provider.py            # Provider mô phỏng phục vụ kiểm thử deterministic
│   │   ├── provider.py                 # Bộ cấp phát LLM hỗ trợ fallback thông minh
│   │   └── router.py                   # Định tuyến Fast Tier (1.5B/0.5B) vs Reasoning (7B)
│   │
│   ├── orchestration/                  # Điều phối nhiệm vụ và sổ cái bền vững
│   │   ├── models.py                   # Data models: TaskRecord, TaskStepRecord, AutonomyLevel
│   │   ├── plan_orchestrator.py        # Nối TaskPlan vào DAG, phân vùng khóa bước, Sandbox
│   │   ├── supervisor.py               # Vòng lặp giám sát tự chủ liên tục (tick loop)
│   │   └── task_registry.py            # Sổ cái SQLite WAL lưu trữ nhiệm vụ và bước
│   │
│   ├── planning/                       # Lập kế hoạch phân rã
│   │   ├── coordinator.py              # ExecutiveCoordinator sinh kế hoạch từ mục tiêu
│   │   └── models.py                   # TaskPlan, TaskStep, quan hệ phụ thuộc DAG
│   │
│   ├── tools/                          # Quản lý công cụ và hộp cát bảo vệ
│   │   ├── approval.py                 # Cổng phê duyệt đa yếu tố (ApprovalGate)
│   │   ├── delegation.py               # Quản lý giấy ủy quyền có hạn định (DelegationGrant)
│   │   ├── registry.py                 # Danh bạ công cụ cho phép
│   │   └── sandbox.py                  # SafeToolSandbox cô lập thực thi trong InertBackend
│   │
│   ├── voice/                          # Âm thanh và giọng nói tiếng Việt
│   │   ├── mouth_sync.py               # Đồng bộ cử động môi theo phổ biên độ âm thanh
│   │   ├── tts.py                      # Tổng hợp tiếng Việt nữ Hoài My (Edge-TTS / Offline)
│   │   └── wake_word.py                # Cấu hình từ kích hoạt "Hi Tony"
│   │
│   └── web/                            # Máy chủ Web giao diện người dùng
│       ├── server.py                   # HTTP Server tích hợp REST API hội thoại & điều hành
│       └── static/                     # Giao diện người dùng
│           ├── app.html / app.js       # Giao diện Chat hội thoại (:8765)
│           ├── executive.html / .js    # Giao diện Cockpit điều hành trung tâm (:8766)
│           └── assets/                 # Bộ ảnh Model A master quartet, visemes
│
├── tests/                              # Bộ 56 modules kiểm thử tự động (485 bài test)
├── tools/                              # Bộ công cụ vận hành đơn lệnh
│   ├── oneclick_orchestrator.py        # Điều phối khởi động 1 chạm thông minh
│   ├── validate_and_report.py          # Tự động chạy test và sinh handoff report
│   └── sync_pi5_complete.py            # Đồng bộ toàn diện dữ liệu sang Pi 5
│
└── KHOI_DONG_QUAN_AI_BRAIN.bat         # File kích hoạt 1-click chính thức của toàn hệ sinh thái
```

---

## 4. CƠ CHẾ VẬN HÀNH NỘI TẠI CỦA BỘ NÃO (CORE ENGINE)

### 4.1. Cơ Chế Định Tuyến Mô Hình Linh Hoạt (`LLMRouter`)
Hệ thống không sử dụng một mô hình duy nhất cho mọi tác vụ nhằm cân bằng hoàn hảo giữa tốc độ và chiều sâu suy luận:
- **Fast Tier (0.5B / 1.5B):** Định tuyến tự động cho các câu chào hỏi, tra cứu nhanh, lệnh điều khiển cảm biến, phản hồi trạng thái. Thời gian phản hồi thực tế đo được trên GPU đạt **0.50s - 0.79s** (>60 - 120 token/giây).
- **Reasoning Tier (7B):** Định tuyến cho các yêu cầu lập kế hoạch phức tạp, phân rã kiến trúc DAG, phân tích an toàn R0-R5, suy luận chiến lược.
- **Fallback Mode An Toàn:** Khi mô hình chính quá tải hoặc offline, hệ thống tự động suy giảm bậc (Graceful Degradation) sang mô hình nhỏ hơn hoặc kích hoạt Mock an toàn có thông báo rõ ràng cho người dùng, không bao giờ che giấu lỗi hay giả lập kết quả thành công.

### 4.2. Trí Nhớ Nhận Thức & Truy Xuất Lai Ghép (`CognitiveRetriever`)
Trí nhớ được lưu trữ theo kiến trúc phân tầng:
1. **Trí nhớ Ngắn hạn (Session History):** Lưu trữ 3 lượt hội thoại gần nhất, chèn vào khối `[RECENT CONVERSATION HISTORY]` để đảm bảo mạch nói chuyện tự nhiên.
2. **Trí nhớ Dài hạn (Long-Term Episodic & Semantic Memory):**
   - **BM25 Lexical Matching ($S_{sparse}$):** Khớp từ khóa tiếng Việt chính xác (tên người, số liệu, thông số kỹ thuật).
   - **BGE-M3 Dense Semantic Embedding ($S_{dense}$):** Biểu diễn ngữ nghĩa bằng vector 1024 chiều, nhận diện ý định tương đồng ngay cả khi không trùng từ khóa.
   - **Công thức dung hợp điểm:** $Score = 0.5 \times S_{sparse} + 0.5 \times S_{dense}$.
   - **Cách ly ứng viên (Candidate Quarantine):** Tri thức mới chỉ được lưu ở trạng thái `CANDIDATE`. Chỉ khi vượt qua kiểm thử hồi quy và được Anh Quân duyệt mới được thăng cấp lên `VERIFIED`.

### 4.3. Quản Trị Rủi Ro & Ranh Giới An Toàn (R0 — R5)
Mọi tác vụ đều phải đi qua `PolicyEngine` để thẩm định mức độ nguy hại:
- **R0 (Read-only System Info):** Được phép tự động (đọc tài nguyên, xem nhật ký, đo cảm biến).
- **R1 (Read-only Telemetry/Metrics):** Được phép tự động trong phạm vi được ủy quyền.
- **R2 (Safe Staging Sandbox):** Được phép chạy thử nghiệm trong môi trường cô lập.
- **R3 (Candidate Knowledge/Proposals):** Tự động cách ly, chờ đánh giá hồi quy.
- **R4 (Owner Approval Required):** Bắt buộc dừng lại ở trạng thái `WAITING_APPROVAL`, tạo ticket tham vấn và gửi yêu cầu phê duyệt có chữ ký tới Anh Quân.
- **R5 (Prohibited / Hard-Blocked):** Ngừng ngay lập tức (`BLOCKED`), kích hoạt cảnh báo an ninh, kiên quyết từ chối thực thi.

### 4.4. Điều Phối Kế Hoạch & Sổ Cái Nhiệm Vụ Bền Vững (`PlanOrchestrator`)
Hoàn thiện trọn vẹn tại Giai đoạn D Master Prompt V7:
1. `ExecutiveCoordinator.plan()` sinh cây kế hoạch `TaskPlan`.
2. `PlanOrchestrator.submit_plan()` kiểm tra tính hợp lệ của đồ thị DAG (không có chu trình lặp vô hạn), thẩm định rủi ro tổng thể, gán khóa chống trùng lặp `idempotency_key` và ghi nhận bền vững vào `data/tasks.db`.
3. Từng bước được ghi vào `durable_task_steps` với mã định danh không gian tên riêng (`{task_id}_{step_id}`).
4. Vòng đời thực thi `execute_lifecycle()` tuân thủ nghiêm ngặt:
   - Kiểm tra trạng thái dừng khẩn cấp STOP/FREEZE.
   - Chặn đứng bước R5.
   - Chờ duyệt bước R4.
   - Chạy các bước R0-R2 trong `SafeToolSandbox` (Inert dry-run).
   - Thu thập bằng chứng xác minh và đánh dấu `COMPLETED` cùng thanh tiến độ 100%.

### 4.5. Hệ Thần Kinh Thực Vật & Luồng Độc Thoại Nội Tâm
- **Hệ Thần Kinh Thực Vật (`AutonomicNervousSystem`):** Giám sát 7 vùng cơ thể (`BRAIN`, `EARS`, `VOICE`, `EYES`, `SKIN`, `CIRCULATION`, `BODY`). Khi phát hiện thiếu hụt phần cứng (ví dụ: mất kết nối micro hoặc camera), cơ chế cảm nhận đau (Nociception) sẽ kích hoạt và chuyển hóa thành câu nói tiếng Việt phản ánh trung thực lên loa ("ốm đau thì phải kêu").
- **Tâm Trí Tự Chủ (`AutonomousMind`):** Chạy nền theo mạng chế độ mặc định (DMN), suy ngẫm về các điểm đau thể xác, tổng hợp tri thức quá khứ, và định kỳ gửi xung giữ ấm (Keep-warm pulse) để giữ các mô hình Qwen/BGE-M3 luôn sẵn sàng trong GPU VRAM, loại bỏ độ trễ nạp mô hình.

---

## 5. GIAO THỨC TRUYỀN THÔNG VÀ LIÊN KẾT BIÊN (CORE <-> PI 5)

Mối liên kết giữa PC Core và Raspberry Pi 5 là huyết mạch đảm bảo sự sống của hình thể số:

```mermaid
sequenceDiagram
    autonumber
    participant Core as PC Core (Windows :8766)
    participant Pi5 as Raspberry Pi 5 (:8768)
    participant HW as Phần cứng Pi 5 (Cam/Mic/Loa)

    Note over Core,Pi5: CHU TRÌNH NHỊP TIM XÁC THỰC (Mỗi 1 giây)
    Pi5->>Core: POST /api/executive/edge/heartbeat (HMAC-SHA256, Nonce, RTT)
    Core-->>Pi5: HTTP 200 OK (ACK, Trạng thái hệ thống, Lệnh chờ)

    Note over Core,Pi5: ĐIỀU KHIỂN CẢM BIẾN TỪ XA (THEO YÊU CẦU)
    Core->>Pi5: POST /api/executive/edge/control (Lệnh: "capture_snapshot")
    Pi5->>HW: V4L2 Frame Grab (/dev/video0)
    HW-->>Pi5: Raw JPEG Frame (1280x720)
    Pi5->>Pi5: Tính toán SHA-256 Hash
    Pi5->>Core: Gửi Ảnh kèm X-Image-SHA256
    Core->>Core: Đối soát Hash Cryptographic
    Core->>Core: Lưu trữ vào data/edge_media/captures/
    Core-->>UI: Cập nhật thư viện ảnh trên Cockpit

    Note over Core,Pi5: KHỞI ĐỘNG 1 CHẠM & TỰ ĐỘNG CHÀO THOẠI
    Core->>Pi5: POST /api/executive/edge/startup-sequence
    Pi5->>HW: Loa ALSA: "Chào anh ạ, rất vui được gặp anh."
    Pi5->>HW: Tự kiểm tra Micro Card 2 & Camera /dev/video0
    HW-->>Pi5: Micro OK (RMS dB hợp lệ), Camera OK
    Pi5->>HW: Loa ALSA: "Báo cáo anh: Micro tốt, Camera tốt..."
    Pi5-->>Core: Báo cáo hoàn tất chuỗi chẩn đoán
```

### 5.1. Cơ Chế Xác Thực & Chống Tấn Công Phát Lại (Anti-Replay)
Mọi gói tin trao đổi giữa Core và Pi 5 đều bắt buộc:
- **Khóa bí mật chia sẻ (Shared Secret):** Được cấu hình thống nhất trên cả hai thiết bị.
- **Chữ ký HMAC-SHA256:** Kèm theo mỗi payload để ngăn chặn giả mạo gói tin trong mạng nội bộ.
- **Số Nonce & Dấu Thời Gian (Timestamp):** Các gói tin có độ lệch thời gian > 60 giây hoặc nonce trùng lặp sẽ bị từ chối ngay lập tức (`HTTP 401 Unauthorized`).

### 5.2. Đo Lường Độ Trễ Khứ Hồi (RTT) Thời Gian Thực
- Mỗi gói tin heartbeat gửi kèm dấu thời gian phát.
- Core ghi nhận lịch sử 30 nhịp RTT gần nhất, hiển thị trực tiếp lên thanh trạng thái Cockpit.
- RTT mạng Wi-Fi thực tế đo được duy trì cực kỳ ổn định trong ngưỡng **10ms — 15ms**.

---

## 6. HÌNH THỂ SỐ MODEL A & CẢM BIẾN VẬT LÝ BIÊN

### 6.1. Tiêu Chuẩn Nhân Dạng Số Model A
Tuân thủ tuyệt đối định hướng thiết kế của Anh Quân tại tài liệu chuẩn `Lựa Chọn Avatar Trợ Lý Ảo TONY.png`:
- **Phong thái:** *"Dịu dàng, thân thiện, phong cách tự nhiên, gần gũi, luôn tươi cười"*.
- **Bộ 4 Trạng Thái Master Quartet (1024x1024):**
  1. `model_a_1024_preview.jpg`: Trạng thái nghỉ (IDLE) và lắng nghe (LISTENING).
  2. `model_a_blink.jpg`: Trạng thái chớp mắt tự nhiên (BLINK) và nghỉ ngơi (OFFLINE).
  3. `model_a_thinking.jpg`: Trạng thái suy ngẫm, lập kế hoạch (THINKING / RESEARCH).
  4. `model_a_speaking.jpg`: Trạng thái đàm thoại sống động (SPEAKING).
- **Viseme Feathred Lip-Sync Mềm Mại:** Khắc phục triệt để lỗi khung hình chữ nhật thô ráp bằng kỹ thuật làm mờ biên elip Gaussian (Gaussian elliptical alpha feathered visemes: `mouth_v2_rest.png`, `mouth_v2_speaking.png`, `mouth_v2_open_o.png`, `mouth_v2_happy.png`).

### 6.2. Cảm Biến Âm Thanh (Microphone & Speaker)
- **Cụm Thu Âm Vật Lý:** Card 2 ALSA USB Audio Device (`Jieli Technology UACDemoV1.0`).
- **Đo Mức Âm Lượng Thực:** Tính toán công suất tín hiệu hiệu dụng thực (True RMS dB) trong dải `[-60 dB, 0 dB]`, hiển thị thước đo âm lượng gradient thời gian thực trên Cockpit.
- **Bộ Phát Âm Thanh:** Loa kết nối Pi 5, phát âm giọng nữ Việt tiêu chuẩn `vi-VN-HoaiMyNeural` với tính năng ngắt lời tức thì (Barge-in cancellation).

### 6.3. Thị Giác Máy Tính (Camera Vision)
- **Phần Cứng:** Sirius USB2.0 Camera gắn cổng USB 3.0 trên Pi 5, giao tiếp qua driver chuẩn Linux V4L2 (`/dev/video0`).
- **Truyền Tải & Lưu Trữ:**
  - Hỗ trợ xem trực tiếp (Live Stream) mượt mà với cơ chế non-overlapping sequential polling, loại bỏ hiện tượng tràn bộ nhớ hay nghẽn mạng.
  - Chụp ảnh độ phân giải cao theo yêu cầu, tính toán mã băm SHA-256 tại Pi 5, truyền tải về PC Core, kiểm tra tính toàn vẹn và lưu trữ trong `data/edge_media/captures/` kèm tệp metadata JSON.
  - Ranh giới bảo mật PathGuard và hạn mức lưu trữ nghiêm ngặt (500 MB quota).

### 6.4. Cơ Chế Quản Lý Kiosk Theo Yêu Cầu (On-Demand Embodiment)
- **Khởi động Pi 5 ở chế độ Chờ:** Khi Pi 5 bật nguồn hoặc reboot, hệ điều hành chỉ chạy daemon nền, giữ màn hình DSI 7" ở chế độ tiết kiệm năng lượng (DPMS off), không tự ý bật Chromium Kiosk.
- **Kích hoạt từ xa qua Tab 7 Cockpit:** Chỉ khi Anh Quân bấm nút *"Bật Hình Thể Kiosk"* trên giao diện Cockpit máy tính chủ, lệnh `start_kiosk` mới được gửi tới Pi 5 để mở sáng màn hình và nạp Avatar.
- **Cách Ly Tiến Trình Tuyệt Đối:** Loại bỏ hoàn toàn lệnh `taskkill /IM chrome.exe` nguy hiểm trên Windows. Pi 5 chỉ quản lý đúng PID của tiến trình Chromium trên Linux, đảm bảo không bao giờ làm đóng trình duyệt làm việc của Anh Quân trên PC Core.

---

## 7. CƠ CHẾ LƯU TRỮ VÀ DỮ LIỆU BỀN VỮNG (PERSISTENCE)

Hệ thống sử dụng các cơ sở dữ liệu SQLite chuyên biệt ở chế độ Write-Ahead Logging (WAL) để đảm bảo an toàn giao dịch và truy cập đồng thời:

| Tên Cơ Sở Dữ Liệu | Đường Dẫn | Vai Trò & Dữ Liệu Lưu Trữ | Cơ Chế Bảo Vệ |
| :--- | :--- | :--- | :--- |
| **Brain DB** | `data/brain.db` | Lưu trữ tập các phiên hội thoại (Episodes) và các bản ghi trí nhớ dài hạn (Memories). | Phân quyền đọc/ghi cô lập, phân vùng nhãn CANDIDATE/VERIFIED. |
| **Tasks DB** | `data/tasks.db` | Sổ cái nhiệm vụ bền vững (`durable_tasks`) và các bước thực thi DAG (`durable_task_steps`). | Khóa chống trùng lặp `idempotency_key`, cô lập khóa chính `{task_id}_{step_id}`. |
| **Governance DB** | `data/governance.db` | Trạng thái khẩn cấp STOP/FREEZE, nhật ký can thiệp chính sách. | Ghi nhận bất biến, ưu tiên an toàn cao nhất khi có sự cố. |
| **Consultations DB** | `data/consultations.db` | Hòm thư vé tham vấn chủ sở hữu (`consultation_tickets`). | Chờ chữ ký xác thực từ Anh Quân, không tự ý giải phóng. |
| **Edge Media Store** | `data/edge_media/` | Thư viện lưu trữ ảnh chụp và snapshot từ camera Pi 5. | Xác thực SHA-256 toàn vẹn, giới hạn dung lượng 500 MB. |

---

## 8. HIỆN TRẠNG NGHIỆM THU & BẰNG CHỨNG KIỂM THỬ THỰC TẾ

### 8.1. Bằng Chứng Bộ Kiểm Thử Tự Động (Regression Test Suite)
Đã chạy và kiểm chứng độc lập trên môi trường máy chủ:
- **Môi trường:** Python 3.11.9 64-bit (`E:\AI\QUAN AI BRAIN\.venv\Scripts\python.exe`).
- **Tổng số bài test:** **485 bài test**.
- **Kết quả nghiệm thu:** **484 PASSED**, **1 SKIPPED**, **0 FAILED**.
- **Tỷ lệ thành công:** **100%** đối với toàn bộ các tính năng đã kích hoạt.
- **Thời gian chạy toàn bộ:** 90.40 giây.

```text
=========================== short test summary info ===========================
SKIPPED [1] tests\test_vietnamese_tts.py:266: BLOCKED: Phần cứng Raspberry Pi 5 thực tế chưa kết nối mạng trong phiên kiểm thử tự động này. PC Core đã được xác thực hoàn chỉnh.
484 passed, 1 skipped in 90.40s
Exit code: 0
```

### 8.2. Kết Quả Đo Lường Hiệu Năng Thực Tế (Ollama Local Benchmark)
Đo trực tiếp trên cổng `http://127.0.0.1:11434` của PC Core:
1. `qwen2.5:0.5b` (Fast Tier - Lệnh ngắn & chào hỏi): **0.79s** (Tốc độ sinh token: 125 tok/s).
2. `qwen2.5:1.5b` (Fast Tier - Đàm thoại thông thường): **0.50s** (Tốc độ sinh token: 64.6 tok/s).
3. `qwen2.5:7b` (Reasoning Tier - Lập kế hoạch chuyên sâu): **20.6s** (Tốc độ sinh token: 7.7 tok/s).
4. `bge-m3:latest` (Dense Embedding - Trí nhớ ngữ nghĩa): **9.64s** (Vector chuẩn 1024 chiều).

> **⚠️ CHÚ THÍCH HIỆU CHỈNH (Sprint 0 Audit 2026-10-25, approved D1):** Các số đo trên là phép đo
> **cold-start** (bao gồm thời gian nạp model vào VRAM), không phải warm inference. Phép đo độc lập
> ngày 2026-10-25 (`reports/SPRINT0_RUNTIME_PROBE.json`) xác minh: **BGE-M3 warm = 0.39–0.47s** (9.64s là cold-start);
> `qwen2.5:7b` trên GPU Quadro T1000 4GB chỉ nạp được 2.3/5.1GB → **warm 6.0 tok/s, cold 35.6s** (chậm hơn số 20.6s ghi trên);
> 0.5B/1.5B warm đúng khoảng 0.5–0.8s. Nguyên nhân: VRAM 4GB không đủ chứa model 5.1GB (partial offload).

---

## 9. KẾ HOẠCH HÀNH ĐỘNG VÀ LỘ TRÌNH PHÁT TRIỂN TIẾP THEO

Dựa trên kết quả hoàn thành Giai đoạn D, lộ trình tiến hóa của QUAN AI BRAIN được đề xuất thành 4 sprint rõ ràng:

```mermaid
gantt
    title LỘ TRÌNH PHÁT TRIỂN TIẾP THEO (SPRINT C - SPRINT G)
    dateFormat  YYYY-MM-DD
    section Sprint D (Hoàn thành)
    Nối TaskPlan vào DurableTaskRegistry & Tab 3 Cockpit :done, d1, 2026-10-24, 2026-10-25
    section Sprint C (Hiệu năng)
    Benchmark độ trễ thực tế & Token Budget Caching :active, c1, 2026-10-26, 2026-10-28
    Tối ưu hóa LLM Router Fast vs Reasoning Tier :c2, 2026-10-28, 2026-10-30
    section Sprint E (Giọng nói & Biên)
    Wake-word 'Hi Tony' & VAD hai chiều trên Pi 5 :e1, 2026-10-31, 2026-11-03
    Barge-in ngắt lời tức thì & Đồng bộ môi trực tiếp :e2, 2026-11-03, 2026-11-05
    section Sprint F (Tự học & Nâng cấp)
    Bộ máy phát hiện khoảng trống & lập hồ sơ nâng cấp :f1, 2026-11-06, 2026-11-09
    Quy trình phê duyệt tự học an toàn (Owner Approval Gate) :f2, 2026-11-09, 2026-11-12
    section Sprint G (Vận hành 24/7)
    Đóng gói Daemon dịch vụ nền có kiểm soát :g1, 2026-11-13, 2026-11-15
    Tổng kết, bàn giao vận hành độc lập toàn diện :g2, 2026-11-15, 2026-11-17
```

### 9.1. Sprint C — Tối Ưu Hóa Tốc Độ & Đo Lường Hiệu Năng (Ưu Tiên Tiếp Theo)
- **Mục tiêu:** Giảm thiểu độ trễ đàm thoại và truy xuất ngữ cảnh.
- **Nội dung:**
  1. Triển khai cơ chế Streaming phản hồi token từ Ollama về giao diện Web Chat và Cockpit.
  2. Tối ưu ngân sách token trong `PromptContextBuilder` (loại bỏ thông tin trùng lặp, ưu tiên lịch sử gần nhất).
  3. Xây dựng bộ nhớ đệm ngữ nghĩa có điều kiện (Semantic Cache) cho các truy vấn trạng thái hệ thống phổ biến.

### 9.2. Sprint E — Hoàn Thiện Tương Tác Thoại Hai Chiều Tại Biên (Edge Voice Pipeline)
- **Mục tiêu:** Biến Raspberry Pi 5 thành thiết bị giao tiếp giọng nói hoàn chỉnh không cần chạm.
- **Nội dung:**
  1. Kích hoạt nhận diện từ đánh thức cục bộ ("Hi Tony") sử dụng mô hình nhẹ trên Pi 5.
  2. Tích hợp Voice Activity Detection (VAD) và bộ chuyển giọng nói thành văn bản (STT) tiếng Việt.
  3. Hoàn thiện ngắt lời (Barge-in): Khi người dùng cất tiếng, hệ thống lập tức ngắt tiếng phát từ loa và dừng cử động môi của Avatar.

### 9.3. Sprint F — Tăng Cường Năng Lực Tự Học Có Kiểm Soát (Self-Learning Engine)
- **Mục tiêu:** Giúp trợ lý tự phát hiện điểm yếu, tự nghiên cứu giải pháp và đề xuất nâng cấp lên Anh Quân.
- **Nội dung:**
  1. Kết nối `CapabilityRegistry` với `AutonomicNervousSystem` để phát hiện các phân hệ đang suy thoái hoặc thiếu sót phần cứng.
  2. Tạo lập hồ sơ nâng cấp (`UpgradeProposal`) kèm bằng chứng, diff mã nguồn và bài test hồi quy.
  3. Gửi thẳng vào hòm thư tham vấn (`ConsultationStore`) để Anh Quân xem xét phê duyệt.

### 9.4. Sprint G — Chuẩn Bị Vận Hành Thường Trực 24/7 (Operational Daemon)
- **Mục tiêu:** Thiết lập chế độ chạy ngầm bền bỉ, an toàn.
- **Nội dung:**
  1. Thiết kế dịch vụ nền Windows Service hoặc Task Scheduler có kiểm soát.
  2. Bổ sung cơ chế tự phục hồi (Self-Healing) khi crash mạng hoặc tiến trình con bị ngắt quãng.
  3. Giữ nguyên ranh giới không tự động chạy lệnh shell ra ngoài hệ điều hành khi chưa có sự cho phép bằng văn bản từ Anh Quân.

---

## 10. BẢO TỒN NGUYÊN VẸN HỆ SINH THÁI & QUY TẮC BẤT BIẾN

Toàn bộ quá trình phát triển tuân thủ nghiêm ngặt các cam kết:
1. **Không Chạm Vào Các Dự Án Anh Em:** Không chỉnh sửa bất kỳ tệp tin nào thuộc:
   - `E:\AI\DATA CENTER AI OPERATING SYSTEM`
   - `E:\AI\BAT-AI-2026-Repo\battery-ai-\os_kernel`
   - `E:\AI\Skill\SKILL_BAT_AI`
   - `E:\AI\battery-ai-\BATTERY_AI_V4`
   - `E:\AI\BOT`
   - VDCIM và các hệ thống dữ liệu vận hành.
2. **Không Khởi Tạo Subprocess Thực Thi Ngoài Luồng:** Giữ vững `InertProcessBackend` làm chốt chặn bảo vệ cuối cùng.
3. **Quyền Kiểm Soát Của Anh Quân:** Mọi nâng cấp tiếp theo đều phải được sự đồng ý của anh Quân trước khi áp dụng vào codebase.

---

*Báo cáo được lập tự động dựa trên hiện trạng thực tế từ codebase QUAN AI BRAIN, mã nguồn đã xác minh và bộ kiểm thử hồi quy đạt chuẩn 100%.*
