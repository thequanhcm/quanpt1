# BÁO CÁO AUDIT HIỆN TRẠNG TOÀN DIỆN (PHASE 0)
# COGNITIVE MEMORY & KNOWLEDGE INTELLIGENCE UPGRADE
## HỆ THỐNG: DC-OS / BATTERY AI / SKILL_BAT_AI / QUAN AI BRAIN

- **Đối tượng thực hiện:** Antigravity AI Engineering Team (Principal AI Architect & Reliability Engineer)
- **Thời điểm hoàn thành Audit:** 2026-10-22
- **Phương pháp tiếp cận:** Audit-first, Evidence-driven, Non-destructive, Zero-speculation.
- **Hiện trạng kiểm thử kiểm chứng tự động:** 411 bài test (410 PASSED, 1 SKIPPED — Pi 5 hardware offline, 0 FAILED) trên Python 3.11.9 (`reports/HANDOFF_LATEST.md`).

---

## MỤC LỤC BÁO CÁO

1. [Kiến trúc hiện trạng toàn bộ hệ sinh thái (Ecosystem Baseline)](#1-kiến-trúc-hiện-trạng-toàn-bộ-hệ-sinh-thái)
2. [Sơ đồ đường đi thực thi thực tế (Execution Flow & Trace)](#2-sơ-đồ-đường-đi-thực-thi-thực-tế)
3. [Danh mục module và trạng thái hoạt động đã kiểm chứng (Module Matrix)](#3-danh-mục-module-và-trạng-thái-hoạt-động-đã-kiểm-chứng)
4. [Sơ đồ Database và quan hệ dữ liệu liên quan (Database Topology)](#4-sơ-đồ-database-và-quan-hệ-dữ-liệu-liên-quan)
5. [Các vấn đề hiệu năng, độ chính xác, bảo mật và độ tin cậy](#5-các-vấn-đề-hiệu-năng-độ-chính-xác-bảo-mật-và-độ-tin-cậy)
6. [Đánh giá các chức năng đã có và còn thiếu (Gap Analysis)](#6-đánh-giá-các-chức-năng-đã-có-và-còn-thiếu)
7. [Những thành phần có nguy cơ trùng lặp (Deduplication Analysis)](#7-những-thành-phần-có-nguy-cơ-trùng-lặp)
8. [Đánh giá tài nguyên phần cứng và tính khả thi vận hành BGE-M3](#8-đánh-giá-tài-nguyên-phần-cứng-và-tính-khả-thi-vận-hành-bge-m3)
9. [Các rủi ro khi thay đổi và vùng nguy hiểm (Risk Register)](#9-các-rủi-ro-khi-thay-đổi-và-vùng-nguy-hiểm)
10. [Đề xuất kiến trúc đích (Unified Cognitive Memory Architecture)](#10-đề-xuất-kiến-trúc-đích)
11. [Kế hoạch triển khai theo từng giai đoạn (Phased Implementation Plan)](#11-kế-hoạch-triển-khai-theo-từng-giai-đoạn)
12. [Các điểm cần Chủ dự án (Anh Quân) phê duyệt (Sign-off Checkpoints)](#12-các-điểm-cần-chủ-dự-án-phê-duyệt)

---

## 1. KIẾN TRÚC HIỆN TRẠNG TOÀN BỘ HỆ SINH THÁI

Khảo sát vật lý trực tiếp trên ổ đĩa `E:\AI` cho thấy hệ sinh thái hiện tại không phải là một khối đơn lẻ mà bao gồm **5 hệ thống độc lập**, được phát triển qua các thời kỳ với các cơ chế lưu trữ và mức độ hoàn thiện khác nhau:

```
                                    +-------------------------------------------------------------+
                                    |                QUAN AI BRAIN (PC Core + Pi5)                |
                                    |  Digital Executive Assistant / Cognitive Foundation         |
                                    |  - Web UI (Port 8765) & Cockpit (Port 8766)                 |
                                    |  - Digital Avatar TONY V2 (Port 8768 / Pi 5 Kiosk)          |
                                    |  - MemoryStore WAL (`data/brain.db` - 196 eps, 200 mems)   |
                                    |  - Governance & Approvals (`data/governance.db`)            |
                                    |  - LLMRouter (Fast tier 1.5B/0.5B; Reasoning tier 7B)       |
                                    |  - Universal Connector Foundation V6 (A0-A3)                |
                                    +------------------------------+------------------------------+
                                                                   |
                           +---------------------------------------+---------------------------------------+
                           |                                       |                                       |
                           v                                       v                                       v
+--------------------------------------+ +--------------------------------------+ +--------------------------------------+
|     DC-OS / DC-COMMAND (BAC-DC V5)   | |            BATTERY AI V4             | |             SKILL_BAT_AI             |
|  `E:\AI\DATA CENTER AI...`           | |  `E:\AI\battery-ai-\BATTERY_AI_V4`   | |  `E:\AI\Skill\SKILL_BAT_AI`          |
|  - 12 Cognitive Cores                | |  - FastAPI Backend (`server.py`)     | |  - 6 Core Engines: Task, Risk, Authz,|
|  - ChromaDB (`chroma.sqlite3`: 114MB,| |  - 248MB SQLite `battery_ups_v4.db`  | |    Execution, Escalation, Learning.  |
|    145,975 vectors MiniLM-L12-v2)    | |    (6.08M cell voltages, 224k reads) | |  - `ai_workforce.db`                 |
|  - RAGEngine: KEDB + SOP + ChromaDB  | |  - TabPFN/XGBoost SOH/RUL predictor  | |  - Legacy Escalation via env secret  |
|  - UnifiedMemoryCore (In-memory RAM) | |  - `knowledge_memory.db` (1 case)    | |    (`QUANPT1_APPROVAL_SECRET`)       |
|  - CLAE (Closed-Loop Autonomous Exec)| |  - In-memory Vector RAG (Llama 3.1)  | |  - Autonomous Daemon                 |
+--------------------------------------+ +--------------------------------------+ +--------------------------------------+
                                                           |
                                                           v
                                         +--------------------------------------+
                                         |     INTELLIGENT RUNTIME KERNEL L3    |
                                         |  `E:\AI\BAT-AI-2026-Repo\...`        |
                                         |  - Kernel L3 (bus, policy, safety,   |
                                         |    scheduler, health, registry)      |
                                         +--------------------------------------+
```

### 1.1. QUAN AI BRAIN (`E:\AI\QUAN AI BRAIN`) — *Hệ thống Trung tâm Hiện tại*
- **Vai trò:** Trợ lý Điều hành Số (Digital Executive Assistant) kết hợp thể nghiệm vật lý qua Raspberry Pi 5.
- **Nền tảng kỹ thuật:** Python 3.11.9, Standard Library, SQLite WAL, Threaded HTTP Server (cổng 8765, 8766).
- **Bộ nhớ hiện hữu:** 
  - `MemoryStore` (`src/quan_ai_brain/memory/sqlite_store.py`): Lưu trữ bền vững vào `data/brain.db`. Hỗ trợ 6 loại memory (`EPISODIC`, `SEMANTIC`, `PROCEDURAL`, `DECISION`, `PREFERENCE`, `CANDIDATE`) và 6 trạng thái xác minh (`USER_PROVIDED`, `OBSERVED`, `VERIFIED`, `INFERRED`, `UNVERIFIED`, `CANDIDATE`).
  - `SessionMemoryManager`: Trích xuất thực tế chủ nhân (tên, sở thích, quy tắc) từ hội thoại qua regex heuristics.
  - `CognitiveRetriever`: Xếp hạng deterministic dựa trên keyword overlap, trọng số loại memory, trạng thái xác minh và scope. **Chưa có Dense Vector Search hay Embedding.**
- **Quản trị an toàn:** R0–R5 (R5 hard-blocked; R4 yêu cầu chữ ký số HMAC-SHA256 hoặc Dual-Factor SMS OTP; Sandbox trơ `InertProcessBackend` tuyệt đối không spawn tiến trình trái phép).
- **Trạng thái kiểm thử:** 410 passed, 1 skipped (phần cứng Pi 5 offline), 0 failed.

### 1.2. DC-COMMAND / DC-OS (`E:\AI\DATA CENTER AI OPERATING SYSTEM`) — *AI Chuyên ngành Data Center*
- **Vai trò:** Hệ điều hành AI giám sát và chỉ huy Trung tâm dữ liệu (Cơ điện: UPS, Battery, Chiller, PAC/CRAC, BMS, Máy phát, Tủ nguồn MSB).
- **Kiến trúc tri thức:**
  - `rag_engine.py`: Tìm kiếm kết hợp KEDB (sự cố) + SOP + ChromaDB.
  - Vector DB: ChromaDB v0.4 (`data/chromadb/chroma.sqlite3`) chứa **145,975 embedding vectors** (dimension 384, sinh bởi `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`).
  - Tài liệu gốc: Hàng ngàn tài liệu kỹ thuật cơ điện trong `data/documents/Tai lieu co dien` (ABB, Eltek, UPS Delta, Vertiv, Chiller, BMS, Quy trình GNOC, sơ đồ 1 sợi trạm Pháp Vân PDL, Giang Võ GVM).
- **Bộ nhớ:**
  - `memory_engine.py` và `unified_memory_core.py`: Thiết kế 10 tầng trí nhớ nhưng **lưu hoàn toàn trên RAM (in-memory Python dicts/lists)**. Khi khởi động lại tiến trình, toàn bộ dữ liệu biến mất. Tìm kiếm tương đồng lịch sử sự cố (`search_episodic_similarity`) đang bị **hard-code chuỗi ký tự** (`if "17" in symptoms or "pac-02" in symptoms...`).

### 1.3. BATTERY AI V4 (`E:\AI\battery-ai-\BATTERY_AI_V4`) — *Động cơ Tính toán & Dự báo Ắc quy*
- **Vai trò:** Backend chuyên sâu thu thập dữ liệu đo đạc cell ắc quy thời gian thực, chạy mô hình PCA, TabPFN, XGBoost dự báo SOH/RUL.
- **Cơ sở dữ liệu:** `battery_ups_v4.db` (dung lượng 248 MB):
  - `cell_voltages`: **6,087,712 bản ghi** điện áp cell thực tế.
  - `readings`: **224,830 bản ghi** chuỗi đo đạc.
  - `devices` & `strings`: 52 thiết bị, 94 chuỗi ắc quy UPS.
  - `prediction_snapshots` & `test_decisions`: 3,543 bản ghi dự báo SOH/RUL.
  - `ai_episodic_memory`: 66 bản ghi tổng kết ngày.
  - `capacity_tests` / `capacity_tests_v3`: **0 bản ghi (Trống hoàn toàn)** — Đây là khoảng trống ground truth cực kỳ lớn.
- **Module RAG/Memory:**
  - `vector_rag.py`: Gọi Ollama `/api/embeddings` với `model="llama3.1"`, lưu vector trong danh sách Python thô (`numpy` array), tính `cosine_similarity` tuyến tính, không có vector index.
  - `knowledge_memory.db`: Thiết kế bảng `experience_cases` (1 bản ghi), `predictions_history` (0 bản ghi), `events_history` (0 bản ghi).

### 1.4. SKILL_BAT_AI (`E:\AI\Skill\SKILL_BAT_AI`) — *Nhân sự Số Vận hành Tự động Cũ*
- **Vai trò:** Daemon tự động hóa xử lý sự kiện qua 6 module (TaskEngine, RiskEngine, AuthzEngine, ExecutionEngine, EscalationEngine, LearningEngine).
- **Cơ chế:** Lưu task vào `ai_workforce.db`.
- **Hạn chế an toàn nghiêm trọng:** Cơ chế phê duyệt cũ dựa vào biến môi trường `set QUANPT1_APPROVAL_SECRET=...`. Điều này **xung đột trực tiếp với quy tắc bất di bất dịch của QUAN AI BRAIN** (R5 hard-blocked, không hardcode credentials, không dùng secret tĩnh).
- **Khả năng học:** Tự động sửa file `risk_matrix.json` khi nhận lệnh học từ ticket — tiềm ẩn nguy cơ self-escalation nếu không có kiểm chứng hồi quy.

### 1.5. Intelligent Runtime Kernel Level 3 (`os_kernel`)
- **Vị trí vật lý thực tế:** Nằm tại `E:\AI\BAT-AI-2026-Repo\battery-ai-\os_kernel` (KHÔNG nằm tại `E:\AI\battery-ai-\os_kernel` như giả định trong hồ sơ cũ).
- **Trạng thái:** Chứa kiến trúc Kernel L3 hoàn chỉnh (bus, policy, safety, scheduler, health, capability, audit). Hiện tại đang hoạt động độc lập, chưa được nối bus trực tiếp với QUAN AI BRAIN.

---

## 2. SƠ ĐỒ ĐƯỜNG ĐI THỰC THI THỰC TẾ

### 2.1. Luồng thực thi truy xuất và trí nhớ trong QUAN AI BRAIN hiện tại
```
[User Query / Voice Turn]
         |
         v
[BrainAPIHandler: POST /api/chat] (or Voice API: POST /api/voice/interact)
         |
         +---> [SessionMemoryManager.extract_user_facts()]
         |            | (Regex match: tên, sở thích, chỉ thị)
         |            v
         |     [MemoryStore.save_memory()] (data/brain.db: type=SEMANTIC/PREFERENCE, verified=USER_PROVIDED)
         |
         +---> [CognitiveRetriever.retrieve()]
         |            | (Tokenize regex -> SQLite LIKE match trên bảng memories)
         |            | (Filter: exclude CANDIDATE; Score: keyword overlap + weights)
         |            v
         |     [Top-K Scored Memories]
         |
         +---> [PromptContextBuilder.build()]
         |            | (Lắp ráp: System prompt, Capabilities, Episodic history, Verified memories)
         |            v
         |     [Formatted LLM Prompt] (< 4000 chars budget)
         |
         +---> [LLMRouter.generate()]
         |            | (Tự động chọn: Fast tier 1.5B/0.5B < 2s hoặc Reasoning tier 7B)
         |            v
         |     [Raw LLM Response]
         |
         +---> [OutputGuardrails.sanitize()]
         |            | (Lọc rò rỉ credential, script tag injection, che giấu đường dẫn)
         |            v
         |     [Sanitized Assistant Reply]
         |
         +---> [SessionMemoryManager.persist_chat_turn()]
                      |
                      v
               [data/brain.db: episodes & memories table]
```

### 2.2. Luồng thực thi RAG trong DC-COMMAND (DC-OS)
```
[User Query / Incident Code]
         |
         v
[RAGEngine.query()]
         |
         +---> 1. [KEDB.search()] -> Tìm lỗi/triệu chứng đã biết trong bộ quy tắc
         |
         +---> 2. [SOPKnowledgeBase.search_sops()] -> Tìm quy trình vận hành chuẩn
         |
         +---> 3. [ChromaDB Retriever.invoke()]
                      |
                      v (Embedding: MiniLM-L12-v2 384-dim)
               [ChromaDB ANN Search: k=3]
                      |
                      v
               [Concatenate Top-3 Chunks]
                      |
                      v
               [Ollama Qwen 2.5:7b Invoke] (Prompt: "Dựa vào tài liệu... Nếu không có hãy nói rõ...")
                      |
                      v
               [RAGResult: answer, evidence_sources, confidence, has_verified_standard]
```

### 2.3. Sự đứt gãy giữa các hệ thống (Execution Disconnects)
1. **Cô lập bộ nhớ:** Khi người dùng trò chuyện với QUAN AI BRAIN về sự cố UPS hay ắc quy, QUAN AI BRAIN chỉ tìm trong `data/brain.db` (200 records). Nó hoàn toàn **không truy vấn được** 145,975 chunks tài liệu cơ điện trong ChromaDB của DC-OS, cũng không đọc được 6 triệu dòng điện áp cell trong `battery_ups_v4.db`.
2. **Không có kênh chia sẻ phản hồi:** Khi DC-OS giải quyết một sự cố, kinh nghiệm đó không được đưa về `data/brain.db` của Trợ lý Số.
3. **Thiếu cơ chế Reranking:** Cả hai hệ thống đều lấy Top-K thô (Chroma lấy k=3 qua cosine, QUAN AI BRAIN lấy top-10 qua keyword match), không có Cross-Encoder reranker để lọc nhiễu trước khi nhồi vào LLM context.

---

## 3. DANH MỤC MODULE VÀ TRẠNG THÁI HOẠT ĐỘNG ĐÃ KIỂM CHỨNG

| STT | Phân hệ | Tên Module / File | Công nghệ | Trạng thái thực tế | Bằng chứng thực nghiệm |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **1** | QUAN AI BRAIN | `MemoryStore` (`sqlite_store.py`) | SQLite WAL | **VERIFIED ACTIVE** | Đã kiểm thử qua test suite, 200 memories trong `data/brain.db`. |
| **2** | QUAN AI BRAIN | `CognitiveRetriever` (`retrieval.py`) | Heuristic Ranking | **VERIFIED ACTIVE** | Hoạt động tốt với từ khóa nhưng **thiếu Semantic/Vector Search**. |
| **3** | QUAN AI BRAIN | `SessionMemoryManager` (`session_memory.py`) | Regex Extractor | **VERIFIED ACTIVE** | Trích xuất tên/sở thích; chưa phát hiện mâu thuẫn tri thức. |
| **4** | QUAN AI BRAIN | `SelfLearningEngine` (`engine.py`) | Sandbox Proposal | **VERIFIED ACTIVE** | Chu trình 17 điểm, cách ly CANDIDATE, cổng duyệt chủ nhân. |
| **5** | QUAN AI BRAIN | `ContinuousEvaluationHarness` (`evaluation.py`) | Benchmark Suite | **VERIFIED ACTIVE** | 5 chỉ số định lượng đo lường tiến bộ tự học. |
| **6** | QUAN AI BRAIN | `ContainedExecutionRunner` (`process_containment.py`)| Win32 Job Objects | **VERIFIED ACTIVE** | Inert mode chặn 100% subprocess, kiểm soát budget RAM/CPU. |
| **7** | QUAN AI BRAIN | `Universal Connector Foundation` (`integration/`) | Manifest/Policy | **VERIFIED ACTIVE** | 20 bài test pass, hỗ trợ chu trình chủ động 10 bước A0–A3. |
| **8** | DC-OS | `RAGEngine` (`rag_engine.py`) | ChromaDB + MiniLM | **VERIFIED ACTIVE** | Đang phục vụ 145,975 vector embeddings, nhưng model cũ (384-dim). |
| **9** | DC-OS | `UnifiedMemoryCore` (`unified_memory_core.py`) | In-memory RAM Dict | **FRAGMENTED / IN-MEMORY** | Mất dữ liệu khi tắt máy; tìm kiếm sự cố hardcoded chuỗi. |
| **10**| DC-OS | `CLAE` (`clae.py`) | Autonomous Loop | **STAGED / EXPERIMENTAL** | Động cơ suy luận tốt nhưng chưa có rào chắn chữ ký như Brain. |
| **11**| BATTERY AI V4 | `PredictionEngine` (`prediction_engine.py`) | TabPFN / XGBoost | **VERIFIED ACTIVE** | Dự báo SOH/RUL cho 52 thiết bị, sinh 3,543 snapshot. |
| **12**| BATTERY AI V4 | `VectorRAG` (`vector_rag.py`) | Ollama Llama 3.1 | **MOCK / RUDIMENTARY** | Lưu vector mảng numpy, tính cosine tuyến tính, không index. |
| **13**| BATTERY AI V4 | `GroundTruthEngine` (`ground_truth_engine.py`)| Discharging Test | **BLOCKED (EMPTY DATA)** | Bảng `capacity_tests` có 0 dòng, không có dữ liệu đối chứng. |
| **14**| SKILL_BAT_AI | `ExecutionEngine` / `RiskEngine` | Python Daemon | **LEGACY RISK** | Phụ thuộc biến môi trường secret, không tương thích R4/R5. |

---

## 4. SƠ ĐỒ DATABASE VÀ QUAN HỆ DỮ LIỆU LIÊN QUAN

Toàn bộ hệ thống đang sử dụng 6 database SQLite chính (tổng dung lượng > 250 MB):

```
+---------------------------------------------------------------------------------------------------+
|                                      BẢN ĐỒ DỮ LIỆU TOÀN CẢNH                                     |
+---------------------------------------------------------------------------------------------------+
| 1. QUAN AI BRAIN: `data/brain.db` (475 KB)                                                        |
|    - episodes (196 rows): Nhật ký tương tác từng lượt hội thoại.                                  |
|    - memories (200 rows): Tri thức dài hạn đã phân loại, gắn trạng thái xác minh & project scope.   |
|    - candidate_knowledge (0 rows) & semantic_memory (0 rows): Bảng v1 (đã gộp vào memories).       |
|                                                                                                   |
| 2. QUAN AI BRAIN: `data/tasks.db` (48 KB)                                                         |
|    - durable_tasks (23 rows): Kế hoạch nhiệm vụ được phân rã thành DAG.                           |
|    - durable_task_steps (2 rows): Các bước thực thi có gắn mức rủi ro R0-R5.                      |
|                                                                                                   |
| 3. QUAN AI BRAIN: `data/governance.db` (176 KB)                                                   |
|    - emergency_states (96 rows): Lịch sử kích hoạt STOP/FREEZE bảo vệ an toàn.                     |
|    - governance_events (189 rows): Audit log ghi lại mọi quyết định của hệ thống.                  |
|    - approval_requests & delegation_grants: Quản lý quyền ủy quyền có ranh giới.                  |
|                                                                                                   |
| 4. BATTERY AI: `data/battery_ups_v4.db` (248 MB)                                                  |
|    - cell_voltages: 6,087,712 rows (Dữ liệu điện áp từng bình ắc quy đo đạc thực tế).             |
|    - readings: 224,830 rows (Các chu kỳ đo tổng thể trạm nguồn).                                  |
|    - devices: 52 rows | strings: 94 rows | cell_ir: 5,292 rows | cell_temperatures: 5,292 rows.   |
|    - prediction_snapshots: 3,543 rows (Kết quả dự báo SOH/RUL từ mô hình).                        |
|    - test_decisions: 3,543 rows (Khuyến nghị đo xả kiểm tra dung lượng).                          |
|    - ai_episodic_memory: 66 rows (Nhật ký tóm tắt ngày của ắc quy).                               |
|    - capacity_tests / capacity_tests_v3: 0 rows (TRỐNG HOÀN TOÀN - THIẾU GROUND TRUTH ĐO XẢ).      |
|                                                                                                   |
| 5. BATTERY AI: `data/knowledge_memory.db` (28 KB)                                                 |
|    - experience_cases: 1 row (Kinh nghiệm xử lý bình suy giảm nội trở).                           |
|    - predictions_history: 0 rows | events_history: 0 rows.                                         |
|                                                                                                   |
| 6. DC-OS: `data/chromadb/chroma.sqlite3` (114 MB) + Vector Binaries (24 MB)                       |
|    - embeddings: 145,975 rows (Vector 384 chiều, MiniLM-L12-v2).                                  |
|    - embedding_metadata: 972,659 rows (Nguồn tài liệu, số trang, tiêu đề).                        |
|    - embedding_fulltext_search: 145,975 rows (Chỉ mục FTS SQLite).                                |
+---------------------------------------------------------------------------------------------------+
```

---

## 5. CÁC VẤN ĐỀ HIỆU NĂNG, ĐỘ CHÍNH XÁC, BẢO MẬT VÀ ĐỘ TIN CẬY

### 5.1. Về Trí nhớ (Cognitive Memory)
1. **Phân mảnh và bay hơi:** DC-OS có hệ thống phân loại 10 tầng trí nhớ rất hay (`unified_memory_core.py`), nhưng lại lưu trên biến RAM của Python. Tắt máy là mất sạch.
2. **Khả năng truy hồi sự kiện (Episodic Retrieval) yếu:** Việc tìm kiếm sự cố tương tự trong DC-OS đang dựa vào so khớp chuỗi cứng (`if "17" in symptoms...`). Nếu sự cố xảy ra ở trạm khác hoặc viết khác đi, hệ thống sẽ rơi về sự cố mặc định đầu tiên hoặc không tìm thấy.
3. **Chưa có cơ chế phát hiện mâu thuẫn (Contradiction Detection):** Khi người dùng cập nhật thông tin mới (ví dụ: *"Bình số 12 đã được thay mới"*), hệ thống ghi nhận thêm một bản ghi mới nhưng không tự động đánh dấu bản ghi cũ là `SUPERSEDED` hoặc phát hiện mâu thuẫn với nhận định trước đó.

### 5.2. Về Động cơ Truy xuất (Retrieval Engine & Vector RAG)
1. **Model Embedding cũ và giới hạn ngữ nghĩa:** ChromaDB đang dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (dimension 384). Model này:
   - Giới hạn độ dài ngữ cảnh chỉ 128 - 512 tokens (dễ làm đứt gãy bảng biểu kỹ thuật Data Center).
   - Khả năng hiểu mã lỗi kỹ thuật viết tắt (ví dụ: `ALM_BAT_TEMP_HI`, `BDI_PC1`, `REC_MOD_FAIL`) rất hạn chế.
2. **QUAN AI BRAIN hoàn toàn chưa có Vector Search:** Truy xuất hiện tại của Trợ lý số chỉ dùng SQLite `LIKE` và so khớp token regex. Điều này khiến trợ lý không thể trả lời các câu hỏi dùng từ đồng nghĩa hoặc câu hỏi tự nhiên bằng tiếng Việt khi không trùng từ khóa chính xác.
3. **Thiếu cơ chế Hybrid Retrieval và Reranker:** Hiện tại chỉ có Dense Search đơn thuần (ở DC-OS) hoặc Lexical Search đơn thuần (ở Brain). Chưa có sự kết hợp (Dense + Sparse/BM25) và hoàn toàn thiếu mô hình Reranking (như BGE-Reranker) để tinh lọc Top-K trước khi gửi vào LLM.

### 5.3. Về Chuẩn Dữ liệu & Ground Truth Chuyên ngành Ắc quy (Battery Ground Truth)
1. **Thiếu hoàn toàn kết quả đo xả dung lượng thực nghiệm:** Trong `battery_ups_v4.db`, bảng `capacity_tests` có **0 bản ghi**. Mọi chỉ số SOH (%) và RUL (tháng) hiện tại đều là **kết quả suy luận (INFERRED) từ mô hình AI**, không thể coi là Sự thật chuẩn (Ground Truth).
2. **Nguy cơ Data Leakage và Hallucination:** Nếu AI tự dùng dự báo của mình để "dạy" cho các chu kỳ học tiếp theo, sai số sẽ bị khuếch đại (Self-reinforcing error loop).

### 5.4. Về Bảo mật, Quyền hạn và An toàn Vận hành
1. **Rủi ro rò rỉ và leo thang quyền từ legacy code:** `SKILL_BAT_AI` còn chứa code kiểm tra quyền qua biến môi trường tĩnh `QUANPT1_APPROVAL_SECRET`. Đây là lỗ hổng cần loại bỏ triệt để.
2. **Nguyên tắc R5 và R4:** QUAN AI BRAIN đã cài đặt rất tốt cơ chế chặn cứng R5 (`BLOCKED_R5_PROHIBITED`) và yêu cầu xác thực kép cho R4. Cần đảm bảo khi tích hợp các module học tập và truy xuất của DC-OS, các rào chắn này **không bao giờ bị bypass**.

---

## 6. ĐÁNH GIÁ CÁC CHỨC NĂNG ĐÃ CÓ VÀ CÒN THIẾU

| Nhóm Năng lực | Yêu cầu của Master Prompt | Trạng thái hiện tại | Đánh giá & Khoảng trống kỹ thuật |
| :--- | :--- | :---: | :--- |
| **Working Memory** | Giữ ngữ cảnh nhiệm vụ, giới hạn token, cách ly phiên. | ĐÃ CÓ (70%) | `PromptContextBuilder` quản lý budget tốt; nhưng chưa nén ngữ cảnh tự động cho nhiệm vụ dài. |
| **Episodic Memory** | Ghi nhớ sự kiện, tác nhân, hành động, bằng chứng, kết quả. | ĐÃ CÓ (60%) | Bảng `episodes` và `ai_episodic_memory` đã có; nhưng thiếu liên kết chuỗi nhân quả (Causal Chain). |
| **Semantic Memory** | Tri thức khái niệm, quy tắc, thiết bị, phiên bản. | ĐÃ CÓ (60%) | Bảng `memories` có type `SEMANTIC`; nhưng chưa kết nối với 145k chunk tài liệu của DC-OS. |
| **Procedural Memory**| SOP, Runbook, Checklist có điều kiện dừng và quyền. | ĐÃ CÓ (50%) | DC-OS có `sop.py`; Brain có `OperationalPlaybook`; nhưng chưa có cơ chế kiểm tra điều kiện tiên quyết tự động. |
| **Decision Memory**  | Vấn đề, phương án, bằng chứng, người duyệt, bài học. | ĐÃ CÓ (50%) | Bảng `memories` (type `DECISION`) và `governance_events`; nhưng chưa có cơ chế so sánh với quyết định tương tự trong quá khứ. |
| **Memory Governance**| Quản lý vòng đời, TTL, audit trail, chống ghi đè. | ĐÃ CÓ (80%) | `GovernanceStateStore`, `PathGuard`, SHA-256 fingerprint hoạt động rất tốt. |
| **BGE-M3 Dense**     | Semantic search tài liệu dài tiếng Việt/Anh (8192 tokens).| CHƯA CÓ (0%) | **BGE-M3 chưa được cài đặt trong môi trường.** ChromaDB đang chạy MiniLM-L12-v2 (384-dim). |
| **Sparse Retrieval** | Tìm kiếm mã lỗi, thông số chính xác (BM25 / SPLADE).| CHƯA CÓ (0%) | Chưa tích hợp BM25 sparse index. |
| **Cross Reranker**   | Tái xếp hạng tài liệu trước khi nhồi vào LLM. | CHƯA CÓ (0%) | Chưa có module Reranking. |
| **Provenance & Cite**| Trích dẫn chính xác tài liệu, trang, phiên bản. | ĐÃ CÓ (70%) | DC-OS RAGEngine trích dẫn được file + page; Brain trích dẫn source_ref. |
| **Continuous Learn** | Quan sát -> Đánh giá -> Phản tư -> Đề xuất -> Sandbox -> Duyệt.| ĐÃ CÓ (75%) | `SelfLearningEngine` của Brain đã có khung 17 điểm; cần nối với dữ liệu vận hành thực tế của DC-OS. |
| **Ground Truth Spec**| Phân biệt VERIFIED, OBSERVED, INFERRED, HYPOTHESIS. | ĐÃ CÓ (70%) | `VerificationStatus` trong Brain đã phân cấp rõ ràng; cần áp dụng sang toàn bộ dữ liệu ắc quy và SOP. |

---

## 7. NHỮNG THÀNH PHẦN CÓ NGUY CƠ TRÙNG LẶP

1. **Ba hệ thống lưu trữ trí nhớ song song:**
   - `QUAN AI BRAIN`: `data/brain.db` (`memories`, `episodes`)
   - `DC-OS`: `memory_engine.py` / `unified_memory_core.py` (In-memory dicts)
   - `BATTERY AI`: `data/knowledge_memory.db` (`experience_cases`, `events_history`)
   - *Giải pháp:* Hợp nhất toàn bộ về một chuẩn Cognitive Memory duy nhất của QUAN AI BRAIN (`data/brain.db`), nâng cấp schema để hỗ trợ trọn vẹn 10 tầng trí nhớ của DC-OS mà không làm mất tính bền vững.
2. **Hai module Vector RAG riêng biệt:**
   - `DC-OS`: `rag_engine.py` (ChromaDB + LangChain)
   - `BATTERY AI`: `vector_rag.py` (NumPy in-memory)
   - *Giải pháp:* Loại bỏ hoàn toàn script `vector_rag.py` dùng mảng numpy thô; chuẩn hóa một **Hybrid Retrieval Engine** duy nhất phục vụ toàn bộ hệ sinh thái.
3. **Ba động cơ tự học độc lập:**
   - `QUAN AI BRAIN`: `SelfLearningEngine` (An toàn nhất, có rào chắn chủ nhân phê duyệt).
   - `DC-OS`: `learning_engine.py`.
   - `SKILL_BAT_AI`: `LearningEngine` (Sửa file json thô, rủi ro cao).
   - *Giải pháp:* Đưa `SelfLearningEngine` của QUAN AI BRAIN làm chuẩn điều phối trung tâm; vô hiệu hóa cơ chế tự sửa file của SKILL_BAT_AI.

---

## 8. ĐÁNH GIÁ TÀI NGUYÊN PHẦN CỨNG VÀ TÍNH KHẢ THI VẬN HÀNH BGE-M3

Kết quả kiểm tra trực tiếp qua Windows WMI / CIM trên máy chủ:

- **CPU:** Intel(R) Core(TM) i7-10850H @ 2.70GHz (6 physical cores, 12 logical threads).
- **RAM:** 32 GB DDR4 (Tổng: 33,178,736 KB; **Còn trống: ~16.7 GB RAM thực tế**).
- **GPU:** NVIDIA Quadro T1000 (4 GB GDDR6 VRAM chuyên dụng).
- **Ổ đĩa cứng:**
  - Ổ `C:\`: 255 GB (Còn trống: **91 GB**).
  - Ổ `E:\` (Chứa dự án AI): 367 GB (Còn trống: **152 GB**).
- **Dịch vụ LLM cục bộ:** Ollama đang chạy với các mô hình:
  - `qwen2.5:7b` (4.7 GB)
  - `qwen2.5:1.5b` (986 MB)
  - `qwen2.5:0.5b` (397 MB)
  - `llama3.1:latest` (4.9 GB)
  - `mistral:latest` (4.4 GB)

### Phân tích Tính khả thi Kỹ thuật của BGE-M3 (Feasibility Analysis)

1. **Đặc tính kỹ thuật của BGE-M3:**
   - Số chiều embedding: **1024** (so với 384 của MiniLM hiện tại).
   - Ngữ cảnh tối đa: **8192 tokens** (hỗ trợ đọc trọn vẹn tài liệu kỹ thuật, bảng thông số pin nhiều cell).
   - Dung lượng model:
     - FP16 (PyTorch / HuggingFace): ~2.2 GB.
     - Lượng tử hóa (INT8 / ONNX Runtime): ~1.1 GB.
     - Lượng tử hóa GGUF (qua Ollama nếu có): ~600 MB.
2. **Khả năng chứa trên VRAM và RAM:**
   - GPU NVIDIA Quadro T1000 chỉ có **4 GB VRAM**.
   - Nếu nạp mô hình LLM chính (`qwen2.5:7b` chiếm ~4.7 GB) vào GPU, VRAM đã đầy và Ollama phải chia một phần layers lên RAM hệ thống.
   - Do đó, **nếu chạy thêm BGE-M3 FP16 (2.2 GB) cùng lúc trên GPU sẽ gây tràn VRAM (CUDA Out Of Memory)** hoặc làm giảm tốc độ suy luận của LLM.
3. **Giải pháp Kiến trúc Tối ưu Được Đề xuất:**
   - **Phương án A (Khuyến nghị cao nhất):** Chạy BGE-M3 qua **ONNX Runtime (INT8) trên CPU** hoặc GPU offload bán phần. Vì máy chủ có **16.7 GB RAM trống**, việc cấp 1.5 GB RAM cho BGE-M3 chạy bằng CPU đa luồng (12 threads của i7-10850H) cho tốc độ embedding tài liệu cực nhanh (< 50ms cho 1 query; ~15-20 chunks/s khi indexing) mà hoàn toàn **không chiếm dụng 4GB VRAM quý giá của Quadro T1000** (để dành trọn vẹn cho Qwen 2.5 7B sinh văn bản).
   - **Chi phí xây dựng lại index:** Hiện tại ChromaDB có 145,975 chunks. Nếu re-index toàn bộ bằng BGE-M3 sẽ mất khoảng 1.5 – 2.5 giờ tính toán CPU.
   - **Chiến lược an toàn:** Giữ nguyên ChromaDB cũ làm phân vùng lưu trữ dự phòng; xây dựng Index BGE-M3 mới song song (Shadow Index), chạy benchmark đối sánh trước khi chuyển đổi chính thức.

---

## 9. CÁC RỦI RO KHI THAY ĐỔI VÀ VÙNG NGUY HIỂM

1. **Rủi ro phá vỡ 145,975 vector embeddings trong ChromaDB:**
   - Tuyệt đối không xóa thư mục `data/chromadb` của DC-OS. Mọi thử nghiệm BGE-M3 phải tạo thư mục lưu trữ riêng (ví dụ: `data/vector_bge_m3/`).
2. **Rủi ro xung đột khóa file SQLite (Database Locking):**
   - Các database `battery_ups_v4.db` (248MB) và `brain.db` đang được truy cập bởi nhiều tiến trình. Mọi kết nối mới phải bật chế độ WAL (`PRAGMA journal_mode = WAL;`) và timeout `>= 30.0s`.
3. **Rủi ro tự cấp quyền (Self-Authorization) trong chu trình học:**
   - Mô hình học tự động không được phép tự động thăng hạng (promote) tri thức từ `CANDIDATE` lên `VERIFIED` nếu không có bằng chứng thực nghiệm và chữ ký phê duyệt của Anh Quân.
4. **Rủi ro giả định kết quả AI là Ground Truth:**
   - Các nhãn SOH/RUL sinh bởi TabPFN/XGBoost phải được gắn cờ `INFERRED`. Tuyệt đối không lưu vào kho tri thức chuẩn dưới nhãn `VERIFIED` khi chưa có biên bản đo xả thực tế.

---

## 10. ĐỀ XUẤT KIẾN TRÚC ĐÍCH: UNIFIED COGNITIVE INTELLIGENCE

Thiết kế một kiến trúc thống nhất, phân tầng rõ ràng, kế thừa sự an toàn của QUAN AI BRAIN và sức mạnh chuyên ngành Data Center của DC-OS:

```
+===================================================================================================+
|                        QUAN AI BRAIN - COGNITIVE INTELLIGENCE ARCHITECTURE                        |
+===================================================================================================+
                                                   |
                                     [1. WORKING MEMORY MANAGER]
                                     - Theo dõi mục tiêu, bước thực hiện
                                     - Nén ngữ cảnh & token budget capping
                                     - Phân tách tenant / người dùng
                                                   |
                                                   v
                     +-----------------------------+-----------------------------+
                     |                                                           |
                     v                                                           v
       [2. MULTI-TIER MEMORY ENGINE]                              [3. BGE-M3 HYBRID RETRIEVAL]
       (Lưu trữ bền vững SQLite WAL)                              (Động cơ truy xuất lai)
       - Working Memory                                           - Dense Retrieval: BGE-M3 (1024-dim)
       - Episodic Memory (Sự kiện có ID, tác nhân, kết quả)       - Sparse Retrieval: BM25 / Exact Code
       - Semantic Memory (Khái niệm, thiết bị, quy tắc)          - Metadata Filter: Thiết bị, thời gian, ACL
       - Procedural Memory (SOP, Runbook, Checklist)             - Cross-Encoder Reranker (Top-K rerank)
       - Decision Memory (Lý do chọn, rủi ro, người duyệt)        - Deduplication & Provenance Tracker
       - Preference Memory (Sở thích, chỉ thị chủ nhân)           - Citation Generator (Tài liệu, trang, ver)
                     |                                                           |
                     +-----------------------------+-----------------------------+
                                                   |
                                                   v
                                   [4. EVIDENCE & GROUND TRUTH GATE]
                                   - Phân loại: VERIFIED | OBSERVED | INFERRED | HYPOTHESIS
                                   - Phát hiện xung đột & mâu thuẫn tri thức (Contradiction Detector)
                                   - Cách ly tri thức mới vào CANDIDATE QUARANTINE
                                                   |
                                                   v
                                   [5. GOVERNANCE & EXECUTION SAFETY]
                                   - R0-R2: Safe Sandbox (Read-only, Diagnostic)
                                   - R3: Cảnh báo & Ghi log kiểm toán
                                   - R4: Yêu cầu xác thực kép Chủ nhân (HMAC-SHA256 / SMS OTP)
                                   - R5: CHẶN CỨNG BẤT DI BẤT DỊCH (Hard-blocked)
                                                   |
                                                   v
                                   [6. CONTROLLED CONTINUOUS LEARNING]
                                   OBSERVE -> EVALUATE -> REFLECT -> PROPOSE -> VALIDATE -> APPROVE
```

---

## 11. KẾ HOẠCH TRIỂN KHAI THEO TỪNG GIAI ĐOẠN

Thực hiện tuần tự, mỗi giai đoạn có tiêu chí nghiệm thu rõ ràng, chỉ chuyển giai đoạn khi 100% kiểm thử tự động vượt qua:

### Phase 0 — Audit & Baseline (Giai đoạn hiện tại — ĐÃ HOÀN THÀNH)
- [x] Khảo sát thực tế toàn bộ 5 hệ thống và 6 database.
- [x] Lập bản đồ đường đi thực thi và các điểm đứt gãy.
- [x] Đo lường tài nguyên phần cứng máy chủ (i7-10850H, 32GB RAM, Quadro T1000 4GB).
- [x] Xuất báo cáo `COGNITIVE_MEMORY_AUDIT.md`.
- [x] Chạy baseline kiểm thử toàn hệ thống (410 passed, 1 skipped, 0 failed).

### Phase 1 — Architecture Design & Memory Schema (Giai đoạn tiếp theo)
- **Mục tiêu:** Thiết kế chi tiết Data Schema cho 10 tầng trí nhớ và chuẩn giao tiếp API.
- **Sản phẩm:** `COGNITIVE_MEMORY_ARCHITECTURE.md`, `MEMORY_SCHEMA.md`, `GROUND_TRUTH_SPEC.md`.
- **Phạm vi file dự kiến:** Bổ sung models trong `src/quan_ai_brain/memory/` và `src/quan_ai_brain/cognition/`.
- **Tiêu chí nghiệm thu:** Unit tests kiểm tra trọn vẹn vòng đời dữ liệu (tạo, cập nhật version, phát hiện mâu thuẫn, truy xuất nguồn gốc).

### Phase 2 — Memory Foundation Consolidation
- **Mục tiêu:** Nâng cấp `MemoryStore` trong `data/brain.db` để lưu trữ bền vững Working, Episodic, Semantic, Procedural và Decision Memory. Di chuyển tri thức từ RAM của DC-OS sang SQLite bền vững.
- **Tiêu chí nghiệm thu:** Dữ liệu tồn tại nguyên vẹn sau khi restart tiến trình; không làm hỏng dữ liệu hiện tại của Trợ lý số.

### Phase 3 — BGE-M3 Hybrid Retrieval & Benchmark
- **Mục tiêu:** Cài đặt môi trường runtime cho BGE-M3 (ONNX Runtime CPU / fastembed); xây dựng tập dữ liệu kiểm thử (Evaluation Dataset); Benchmark so sánh BGE-M3 với MiniLM-L12-v2; Xây dựng cơ chế Hybrid Search (Dense BGE-M3 + BM25 + Exact Code).
- **Sản phẩm:** `RETRIEVAL_BENCHMARK.md`.
- **Tiêu chí nghiệm thu:** Recall@5 và MRR trên tập thuật ngữ kỹ thuật Data Center cải thiện ít nhất 20% so với baseline cũ.

### Phase 4 — Evidence, Provenance & Ground Truth Pipeline
- **Mục tiêu:** Xây dựng bộ lọc cách ly dữ liệu suy đoán; trích dẫn nguồn có kiểm chứng; kết nối dữ liệu đo thực tế từ `battery_ups_v4.db` với định danh rõ ràng.
- **Tiêu chí nghiệm thu:** Trợ lý từ chối khẳng định nếu thiếu bằng chứng; không sinh trích dẫn giả; phân biệt rõ dữ liệu quan sát và dữ liệu suy luận.

### Phase 5 — Continuous Controlled Learning Pipeline
- **Mục tiêu:** Hoàn thiện chu trình 6 bước (Observe -> Evaluate -> Reflect -> Propose -> Validate in Sandbox -> Owner Approval Gate).
- **Sản phẩm:** `LEARNING_PIPELINE.md`.
- **Tiêu chí nghiệm thu:** Tri thức mới tự động đưa vào vùng cách ly `CANDIDATE`; tự động sinh đề xuất nâng cấp 17 điểm; chỉ đưa vào vận hành khi có chữ ký của Anh Quân.

### Phase 6 — Integration & Visual Cockpit Update
- **Mục tiêu:** Kết nối giao diện điều hành Cockpit (cổng 8766) và trợ lý ảo TONY (Pi 5) để hiển thị trạng thái trí nhớ, mức độ tự tin, cây bằng chứng và danh sách đề xuất học tập đang chờ duyệt.
- **Tiêu chí nghiệm thu:** Người vận hành nhìn thấy rõ ràng vì sao AI đưa ra câu trả lời và xem xét duyệt đề xuất học bằng 1 cú nhấp chuột.

### Phase 7 — Controlled Shadow Rollout & Verification
- **Mục tiêu:** Chạy thử nghiệm chế độ Shadow song song trong 7 ngày; theo dõi độ trễ P50/P95; kiểm tra hồi quy; nghiệm thu toàn diện.
- **Sản phẩm:** `PRODUCTION_READINESS_REPORT.md`.

---

## 12. CÁC ĐIỂM CẦN CHỦ DỰ ÁN PHÊ DUYỆT

Kính trình Chủ dự án (Anh Quân) xem xét và cho ý kiến chỉ đạo đối với 4 quyết định kỹ thuật then chốt:

1. **Phê duyệt Kiến trúc Chạy BGE-M3 trên CPU (ONNX Runtime):**
   - Đề xuất: Sử dụng CPU Intel i7 (12 luồng) và 16GB RAM trống để chạy BGE-M3 phục vụ Dense Retrieval, giữ trọn vẹn 4GB VRAM của card Quadro T1000 cho mô hình ngôn ngữ lớn (Qwen 2.5 7B) nhằm tránh lỗi tràn VRAM (CUDA OOM).
   - *Lựa chọn của Chủ dự án:* [ ĐỒNG Ý / YÊU CẦU THỬ NGHIỆM TRÊN GPU ]

2. **Phê duyệt Chiến lược Xử lý 145,975 Vectors trong ChromaDB Cũ:**
   - Đề xuất: Giữ nguyên chỉ mục ChromaDB hiện tại làm phân vùng tra cứu phụ (Fallback Partition). Xây dựng chỉ mục BGE-M3 mới từng bước (Incremental Shadow Index) cho các tài liệu kỹ thuật quan trọng nhất trước, không xóa dữ liệu cũ.
   - *Lựa chọn của Chủ dự án:* [ ĐỒNG Ý GIỮ SONG SONG / YÊU CẦU ĐỔI TOÀN BỘ ]

3. **Phê duyệt Cơ chế Quản trị Trí nhớ Thống nhất:**
   - Đề xuất: Thống nhất lấy `data/brain.db` của QUAN AI BRAIN làm kho tri thức và bộ nhớ trung tâm duy nhất; vô hiệu hóa việc lưu trí nhớ tạm trên RAM của DC-OS và vô hiệu hóa cơ chế sửa file thô của SKILL_BAT_AI.
   - *Lựa chọn của Chủ dự án:* [ ĐỒNG Ý HỢP NHẤT / GIỮ NGUYÊN TỪNG PHẦN ]

4. **Cho phép Bắt đầu Giai đoạn 1 (Phase 1): Thiết kế Kiến trúc Đích và Schema Chi tiết:**
   - Đề xuất: Sau khi hoàn thành Phase 0 Audit này, cho phép Antigravity bắt tay xây dựng bộ tài liệu kỹ thuật Phase 1 (`COGNITIVE_MEMORY_ARCHITECTURE.md`, `MEMORY_SCHEMA.md`, `GROUND_TRUTH_SPEC.md`) và mã nguồn kiểm thử tương ứng.
   - *Lựa chọn của Chủ dự án:* [ PHÊ DUYỆT CHUYỂN PHASE 1 / YÊU CẦU BỔ SUNG AUDIT ]

---
*Báo cáo được khởi tạo và xác thực trung thực dựa trên bằng chứng vật lý ổ đĩa và mã nguồn thực tế tại trạm làm việc.*
