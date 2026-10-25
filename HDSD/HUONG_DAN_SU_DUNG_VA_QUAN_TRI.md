# QUAN AI BRAIN — HƯỚNG DẪN SỬ DỤNG VÀ QUẢN TRỊ TOÀN DIỆN
> **Dành cho Chủ nhân:** `Quanpt1`  
> **Phiên bản:** `0.2.0` — Foundation Evolution & Web UI Integration  
> **Môi trường:** Windows 10/11 x64, Python 3.11.9, Local Ollama  
> **Tài liệu lưu tại:** `E:\AI\QUAN AI BRAIN\HDSD\HUONG_DAN_SU_DUNG_VA_QUAN_TRI.md`

---

## MỤC LỤC
1. [TỔNG QUAN HỆ THỐNG](#1-tổng-quan-hệ-thống)
2. [CÁC CÁCH KHỞI ĐỘNG HỆ THỐNG (3 CÁCH NHANH)](#2-các-cách-khởi-động-hệ-thống-3-cách-nhanh)
3. [HƯỚNG DẪN SỬ DỤNG GIAO DIỆN WEB CHAT & GIỌNG NÓI (WEB UI)](#3-hướng-dẫn-sử-dụng-giao-diện-web-chat--giọng-nói-web-ui)
4. [HƯỚNG DẪN SỬ DỤNG BẢNG ĐIỀU KHIỂN CONSOLE (MENU NỘI BỘ)](#4-hướng-dẫn-sử-dụng-bảng-điều-khiển-console-menu-nội-bộ)
5. [HƯỚNG DẪN SỬ DỤNG DÒNG LỆNH CLI (DÀNH CHO CHUYÊN GIA)](#5-hướng-dẫn-sử-dụng-dòng-lệnh-cli-dành-cho-chuyên-gia)
6. [HƯỚNG DẪN QUẢN TRỊ AN TOÀN & HIẾN PHÁP R0 - R5](#6-hướng-dẫn-quản-trị-an-toàn--hiến-pháp-r0---r5)
7. [QUẢN TRỊ TRÍ NHỚ VÀ DỮ LIỆU CỐT LÕI](#7-quản-trị-trí-nhớ-và-dữ-liệu-cốt-lõi)
8. [QUẢN TRỊ ĐỘNG CƠ TỰ HỌC VÀ PHÊ DUYỆT BẢN VÁ](#8-quản-trị-động-cơ-tự-học-và-phê-duyệt-bản-vá)
9. [XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)](#9-xử-lý-sự-cố-thường-gặp-troubleshooting)
10. [PHÒNG ĐIỀU HÀNH & THAM VẤN CHỦ NHÂN (PORT :8766)](#10-phòng-điều-hành--tham-vấn-chủ-nhân-port-8766)
11. [TÍNH NĂNG ĐÁNH THỨC RẢNH TAY BẰNG GIỌNG NÓI TỰ NHIÊN (WAKE WORD ACTIVATION V1)](#11-tính-năng-đánh-thức-rảnh-tay-bằng-giọng-nói-tự-nhiên-wake-word-activation-v1)
12. [LỆNH TỰ ĐỘNG KHỞI ĐỘNG LẠI HỆ THỐNG SAU KHI CẬP NHẬT TÍNH NĂNG (AUTO-RESTART)](#12-lệnh-tự-động-khởi-động-lại-hệ-thống-sau-khi-cập-nhật-tính-năng-auto-restart)

---

## 1. TỔNG QUAN HỆ THỐNG

**QUAN AI BRAIN** là Trợ lý Điều hành Số cá nhân cao cấp (Digital Executive Assistant) được xây dựng riêng cho Chủ nhân **Quanpt1**, hoạt động theo nguyên tắc:
- **An toàn tuyệt đối (Safety-First):** Tuân thủ nghiêm ngặt Hiến pháp kiểm soát rủi ro R0 – R5. R5 luôn bị chặn cứng; R4 yêu cầu phê duyệt có xác thực của Chủ nhân.
- **Bảo mật cục bộ (Local-First):** Chạy 100% trên máy tính cá nhân (`127.0.0.1`), không gửi dữ liệu ra bên ngoài, không mở cổng công khai.
- **Trí nhớ bền vững (Persistent Long-Term Memory):** Ghi nhớ sự kiện, sở thích, quyết định và quy tắc vào cơ sở dữ liệu SQLite WAL độc lập.
- **Động cơ Tự học có kiểm soát (Self-Learning Engine):** Tự phát hiện lỗ hổng, tự nghiên cứu tài liệu, tự tạo bản vá và cách ly kiến thức mới cho đến khi được Chủ nhân phê duyệt.
- **Đa phương thức giao tiếp (Multimodal Interface):** Hỗ trợ tương tác bằng Văn bản, Giọng nói hai chiều (Voice STT/TTS), Web UI đồ họa và Console CLI.

---

## 2. CÁC CÁCH KHỞI ĐỘNG HỆ THỐNG (3 CÁCH NHANH)

Hệ thống được thiết lập sẵn các biểu tượng lối tắt (Shortcuts) ngay trên **Màn hình nền (Desktop)** của Anh:

```
[Màn hình Desktop]
 ├── 🌐 KHOI_DONG_WEB_UI - Shortcut       <-- Khuyến nghị sử dụng hàng ngày
 ├── 💻 KHOI_DONG_QUAN_AI_BRAIN - Shortcut <-- Bảng điều khiển Console Menu
 └── ⚙️ KHOI_DONG_OLLAMA - Shortcut        <-- Khởi động riêng dịch vụ mô hình
```

### Cách 1: Khởi động Giao diện Web Chat Đồ họa & Voice (Khuyến nghị)
1. Nhấp đúp chuột vào biểu tượng **`KHOI_DONG_WEB_UI - Shortcut`** trên Desktop (hoặc chạy tệp `KHOI_DONG_WEB_UI.bat` tại thư mục `E:\AI\QUAN AI BRAIN`).
2. Hệ thống sẽ tự động:
   - Kiểm tra và bật dịch vụ Ollama cục bộ nếu chưa chạy.
   - Khởi động máy chủ Web UI nội bộ tại địa chỉ: `http://127.0.0.1:8765`.
   - **Tự động mở trình duyệt Web (Edge hoặc Chrome)** đưa Anh vào thẳng Cửa sổ Chat.

### Cách 2: Khởi động Bảng điều khiển Console Menu (Dạng văn bản)
1. Nhấp đúp chuột vào biểu tượng **`KHOI_DONG_QUAN_AI_BRAIN - Shortcut`** trên Desktop (hoặc tệp `KHOI_DONG_QUAN_AI_BRAIN.bat`).
2. Cửa sổ dòng lệnh mở ra hiển thị menu 10 lựa chọn (0 đến 9), Anh chỉ cần gõ số tương ứng để làm việc.

### Cách 3: Khởi động riêng dịch vụ Mô hình Ollama
- Nhấp đúp vào **`KHOI_DONG_OLLAMA - Shortcut`** khi Anh chỉ muốn kiểm tra trạng thái cổng `11434` hoặc xem danh sách mô hình AI đã tải trên máy (`qwen2.5:7b`, `qwen2.5:1.5b`, `llama3.1`, v.v.).

---

## 3. HƯỚNG DẪN SỬ DỤNG GIAO DIỆN WEB CHAT & GIỌNG NÓI (WEB UI)

Địa chỉ truy cập: **`http://127.0.0.1:8765`**

Giao diện được thiết kế theo phong cách **Dark Glassmorphism** (kính mờ tối) hiện đại gồm thanh điều hướng bên trái và vùng làm việc bên phải với 4 Tab chính:

### 💬 Tab 1: Hội Thoại Nhận Thức (Cognitive Chat & Voice)
Đây là màn hình làm việc chính để trò chuyện, hỏi đáp và ra chỉ thị cho Trợ lý:
- **Gõ câu hỏi bằng bàn phím:** Nhập nội dung vào khung nhập liệu phía dưới và nhấn phím **Enter** (hoặc nút Gửi mũi tên).
- **Giao tiếp bằng Giọng nói (Voice Input):**
  1. Nhấp vào nút **Microphone 🎙️** bên cạnh khung nhập liệu.
  2. Màn hình sẽ hiện thanh thông báo đỏ *"Đang lắng nghe giọng nói của Anh..."*.
  3. Anh nói câu hỏi bằng tiếng Việt tự nhiên vào micro máy tính.
  4. Trình duyệt tự động chuyển giọng nói thành văn bản. Anh chỉ việc bấm **Gửi**.
- **Tính năng Trợ lý Đọc to Câu trả lời (Voice Output - TTS):**
  - Ở góc trên bên phải có nút gạt **"Giọng đọc TTS"**.
  - Khi bật (màu xanh): Mỗi khi Trợ lý trả lời xong, câu trả lời sẽ được tự động phát âm bằng giọng đọc tiếng Việt truyền cảm.
  - Khi tắt: Trợ lý chỉ hiển thị văn bản im lặng.
- **Chọn Mô hình AI (Model Selector):**
  - `qwen2.5:7b` (Khuyến nghị): Trí tuệ sâu sắc, lập luận chặt chẽ, tối ưu tiếng Việt.
  - `qwen2.5:1.5b`: Phản hồi siêu tốc, thích hợp cho các câu hỏi ngắn, tra cứu nhanh.
- **Thẻ trích dẫn Trí nhớ (Memory Citations):**
  - Dưới mỗi câu trả lời của Trợ lý có hiển thị thẻ thời gian xử lý (`elapsed_ms`) và số lượng mẩu trí nhớ đã được Não bộ truy xuất từ SQLite để làm căn cứ trả lời, chống việc AI bịa đặt thông tin.

### 🧠 Tab 2: Trí Nhớ Dài Hạn (Long-Term Memories)
Nơi Chủ nhân trực tiếp quản lý kho tri thức của Não bộ:
- **Xem kho trí nhớ:** Hiển thị toàn bộ các mẩu thông tin, sự kiện, sở thích hoặc quy tắc đã được lưu trữ trong cơ sở dữ liệu `data/brain.db`.
- **Thêm ghi nhớ mới (+ Ghi nhớ mới):**
  1. Bấm nút **"+ Ghi nhớ mới"** màu xanh.
  2. Nhập nội dung cần ghi nhớ (Ví dụ: *"Chủ nhân thích báo cáo ngắn gọn, tập trung vào kết quả"* hoặc *"Dự án Bot cá nhân ưu tiên bảo mật"*).
  3. Chọn phân loại: Tác vụ (`task`), Sở thích (`preference`), Quy tắc (`rule`), hay Sự kiện (`fact`).
  4. Bấm **"Lưu vào Não bộ"**. Trí nhớ này sẽ được lưu vĩnh viễn và Não bộ sẽ tự động sử dụng trong các cuộc hội thoại tiếp theo.

### 🛡️ Tab 3: Kế Hoạch An Toàn (DAG Task Planning)
Giúp phân tích mục tiêu phức tạp thành các bước hành động có kiểm soát:
1. Nhập mục tiêu công việc (Ví dụ: *"Kiểm tra toàn diện kho tài liệu và sao lưu mã nguồn"*).
2. Bấm nút **"Lập Kế Hoạch"**.
3. Não bộ sẽ tự động:
   - Phân tích mục tiêu thành các bước hành động cụ thể (`step-1`, `step-2`...).
   - Đánh giá cấp độ rủi ro cho từng bước từ **R0** đến **R5**.
   - Gắn cờ chính sách: Bước an toàn (`allow`), bước yêu cầu phê duyệt (`pending_approval`), hoặc bước bị cấm (`deny`/`blocked`).
4. **Lưu ý Quản trị:** Bản kế hoạch này chỉ phục vụ Chủ nhân xem xét đánh giá; hệ thống kiên quyết không tự tiện thực thi các tác vụ gây thay đổi máy tính.

### ⚡ Tab 4: Động Cơ Tự Học (Self-Learning Engine)
Nơi theo dõi năng lực tự tiến hóa của QUAN AI BRAIN:
- Bấm nút **"⚡ Chạy Một Chu Kỳ Tự Học Mẫu (Supervised Dry-Run)"**.
- Hệ thống sẽ minh họa chu trình tự học 5 bước:
  1. Phát hiện lỗ hổng năng lực (Learning Gap).
  2. Tự tra cứu các tài liệu thiết kế và đặc tả mã nguồn được cấp phép.
  3. Tạo hồ sơ tri thức ứng viên và **đưa vào khu vực cách ly (QUARANTINED)**.
  4. Sinh bản đề xuất nâng cấp phần mềm gồm: Mã lỗi, Giải pháp, Mã nguồn sửa đổi (Unified Diff), Phân tích Ưu/Nhược điểm và Độ tự tin.
  5. Dừng lại chờ Chủ nhân xem xét. Không một dòng mã nào được tự ý đưa vào vận hành nếu chưa có lệnh của Chủ nhân.

---

## 4. HƯỚNG DẪN SỬ DỤNG BẢNG ĐIỀU KHIỂN CONSOLE (MENU NỘI BỘ)

Khi sử dụng qua [`KHOI_DONG_QUAN_AI_BRAIN.bat`](file:///e:/AI/QUAN%20AI%20BRAIN/KHOI_DONG_QUAN_AI_BRAIN.bat), giao diện dòng lệnh sẽ hiển thị:

```text
======================================================================
          QUAN AI BRAIN - TRO LY DIEU HANH SO (QUANPT1)
======================================================================
 [1] Hoi dap Nhan thuc (Cognitive Ask - Tri nho + LLM)
 [2] Hoi dap Nhanh voi Mo hinh Local (LLM Ask)
 [3] Lap Ke hoach Nhiem vu An toan (Task Planning R0-R5)
 [4] Kich hoat Chu ky Tu hoc va De xuat Nang cap (Self-Learning)
 [5] Xem Danh sach Tri nho Dai han (Memory List)
 [6] Ghi nho Thong tin moi vao Nao bo (Memory Add)
 [7] Kiem tra Ket noi Ollama va Danh sach Models (LLM Health)
 [8] Kiem tra Suc khoe Toan he thong (Self-Check)
 [9] Mo Giao Dien Web Chat Truc Quan (Web UI Dashboard)
 [0] Thoat
======================================================================
Nhap lua chon cua Anh (0-9):
```

### Hướng dẫn từng mục chọn:
- **Phím `1` — Hỏi đáp Nhận thức:** Hỏi đáp chuyên sâu kết hợp tìm kiếm bộ nhớ và Hiến pháp R0-R5. *(Có thể bấm `Windows + H` để đọc câu hỏi bằng giọng nói).*
- **Phím `2` — Hỏi đáp Nhanh:** Gửi truy vấn trực tiếp tới mô hình LLM.
- **Phím `3` — Lập Kế hoạch An toàn:** Nhập mục tiêu nhiệm vụ để sinh bảng kế hoạch phân rã và đánh giá mức rủi ro.
- **Phím `4` — Chu kỳ Tự học:** Chạy chu kỳ tự học có giám sát để tạo hồ sơ đề xuất nâng cấp.
- **Phím `5` — Danh sách Trí nhớ:** Xem 10 mẩu trí nhớ gần nhất dạng JSON.
- **Phím `6` — Ghi nhớ Thông tin mới:** Nhập câu tóm tắt để lưu ngay sự kiện vào Não bộ.
- **Phím `7` — Kiểm tra Ollama:** Xem tình trạng cổng 11434, model đang chạy và độ trễ phản hồi.
- **Phím `8` — Nhịp tim Hệ thống:** Kiểm tra phiên bản Python, PID tiến trình và trạng thái sức khỏe nền tảng.
- **Phím `9` — Mở Web UI:** Tự động khởi động máy chủ Web và mở trình duyệt.
- **Phím `0` — Thoát:** Đóng cửa sổ an toàn.

---

## 5. HƯỚNG DẪN SỬ DỤNG DÒNG LỆNH CLI (DÀNH CHO CHUYÊN GIA)

Anh hoặc các kỹ sư có thể tương tác trực tiếp với QUAN AI BRAIN từ cửa sổ PowerShell hoặc Terminal thông qua module `quan_ai_brain.cli`:

```powershell
# Chuyển vào thư mục dự án
cd "E:\AI\QUAN AI BRAIN"

# 1. Kiểm tra nhịp tim cơ bản
.venv\Scripts\python.exe -m quan_ai_brain.cli self-check

# 2. Kiểm tra sức khỏe kết nối LLM (<1ms với socket probe)
.venv\Scripts\python.exe -m quan_ai_brain.cli llm-health

# 3. Liệt kê các model Ollama đang có trên máy
.venv\Scripts\python.exe -m quan_ai_brain.cli llm-models

# 4. Gửi câu hỏi nhanh tới mô hình
.venv\Scripts\python.exe -m quan_ai_brain.cli llm-ask --prompt "Xin chào bạn là ai?" --timeout 120

# 5. Hỏi đáp nhận thức (Truy xuất bộ nhớ + Tạo ngữ cảnh an toàn)
.venv\Scripts\python.exe -m quan_ai_brain.cli cognitive-ask --query "Tóm tắt các nguyên tắc an toàn" --timeout 120

# 6. Dựng ngữ cảnh Prompt theo chuẩn phân tầng (Context Builder)
.venv\Scripts\python.exe -m quan_ai_brain.cli context-build --query "chính sách quản trị"

# 7. Lập kế hoạch nhiệm vụ có phân cấp rủi ro R0-R5
.venv\Scripts\python.exe -m quan_ai_brain.cli plan-create --goal "Kiểm tra hệ thống" --format text

# 8. Xem danh sách trí nhớ dài hạn gần đây
.venv\Scripts\python.exe -m quan_ai_brain.cli memory-list --limit 20

# 9. Thêm một bản ghi trí nhớ mới
.venv\Scripts\python.exe -m quan_ai_brain.cli memory-add --summary "Đã cấu hình Web UI cổng 8765" --kind "task"

# 10. Liệt kê các công cụ an toàn đã đăng ký trong Sandbox
.venv\Scripts\python.exe -m quan_ai_brain.cli tool-list

# 11. Chạy thử một công cụ trong chế độ giả lập (Dry-Run)
.venv\Scripts\python.exe -m quan_ai_brain.cli tool-run --tool "system_health" --dry-run

# 12. Chạy chu kỳ tự học có giám sát (Self-Learning Cycle)
.venv\Scripts\python.exe -m quan_ai_brain.cli learning-cycle-dryrun --format text
```

---

## 6. HƯỚNG DẪN QUẢN TRỊ AN TOÀN & HIẾN PHÁP R0 - R5

Hệ thống hoạt động dưới sự giám sát độc lập của bộ máy chính sách (`PolicyEngine`), phân loại mọi hành động theo 6 cấp độ rủi ro:

| Cấp độ | Tên gọi | Định nghĩa | Chính sách Thực thi |
| :---: | :--- | :--- | :--- |
| **R0** | **Read-Only** | Đọc tệp nội bộ, kiểm tra trạng thái, đọc bộ nhớ | **Cho phép (Allow)** trong phạm vi Sandbox |
| **R1** | **Analyze** | Phân tích cú pháp, kiểm tra linter, sinh báo cáo | **Cho phép (Allow)** không có tác dụng phụ |
| **R2** | **Workspace Write** | Tạo tệp mới trong thư mục dự án (cấm ghi đè) | **Yêu cầu phê duyệt cơ bản** của Chủ nhân |
| **R3** | **External Low Impact** | Gọi API bên ngoài ở chế độ đọc, gửi thông báo | **Cần cấp quyền đại biểu (Delegation Grant)** |
| **R4** | **Significant Action** | Thay đổi cấu hình lớn, cài đặt gói, cập nhật mã | **BẮT BUỘC Phê duyệt Chủ nhân (Dual-Factor)** |
| **R5** | **Prohibited** | Xóa dữ liệu, sửa file bí mật (`.env`), ghi đè nhân | **CHẶN CỨNG VĨNH VIỄN (Hard-Blocked)** |

### Các Quy tắc Quản trị Bất khả xâm phạm:
1. **Không tự trao quyền (Anti-Self-Authorization):** Mô hình LLM không có quyền tự đánh giá hạ mức rủi ro của tác vụ hay tự cấp quyền cho chính mình.
2. **Chống phát lại Token (Anti-Replay Protection):** Mỗi mã phê duyệt (`approval_id`) hoặc Nonce chỉ được tiêu thụ đúng 1 lần duy nhất trong kho trạng thái bền vững (`GovernanceStateStore`).
3. **Cơ chế dừng khẩn cấp (Emergency STOP & FREEZE):** Khi hệ thống rơi vào trạng thái `STOP` hoặc `FREEZE`, mọi công cụ và đề xuất nâng cấp đều bị khóa cứng ngay lập tức.
4. **Không nạp mã động ngoài tầm kiểm soát:** Tuyệt đối cấm chạy PowerShell tùy ý hoặc nạp thư viện ngoài danh mục cho phép.

---

## 7. QUẢN TRỊ TRÍ NHỚ VÀ DỮ LIỆU CỐT LÕI

Toàn bộ dữ liệu của QUAN AI BRAIN được bảo vệ nghiêm ngặt trong thư mục `data/` và `logs/`:

### Cấu trúc lưu trữ:
- **`data/brain.db`:** Cơ sở dữ liệu SQLite chính ở chế độ WAL (Write-Ahead Logging). Lưu trữ các bảng:
  - `memories`: Lưu 6 loại trí nhớ (`EPISODIC`, `SEMANTIC`, `PROCEDURAL`, `DECISION`, `PREFERENCE`, `CANDIDATE`).
  - `episodes`: Bản ghi lịch sử tương tác ban đầu.
- **`data/governance_state.db`:** Lưu trữ bền vững trạng thái `STOP/FREEZE`, mã Nonce chống tấn công phát lại, danh sách phê duyệt đã dùng.
- **`data/learning_sandbox.db`:** Cơ sở dữ liệu cách ly riêng biệt dành cho Động cơ tự học, lưu các lỗ hổng phát hiện và tri thức ứng viên.
- **`logs/audit.jsonl`:** Sổ cái kiểm toán an toàn (Append-only). Mọi câu hỏi, câu trả lời, công cụ được gọi hay từ chối đều được ghi lại với thời gian UTC và các giá trị nhạy cảm đã được bôi đen tự động (Redacted).

### Hướng dẫn sao lưu (Backup):
Chủ nhân có thể sao lưu định kỳ bằng cách copy thư mục `data/` ra vị trí an toàn khi hệ thống đang không thực hiện ghi dữ liệu.

---

## 8. QUẢN TRỊ ĐỘNG CƠ TỰ HỌC VÀ PHÊ DUYỆT BẢN VÁ

Khi Trợ lý phát hiện một tác vụ bị lỗi (ví dụ: Ollama bị ngắt kết nối đột ngột hoặc timeout):
1. **Quan sát (Observe):** Trích xuất mã định danh lỗ hổng (`gap_id`).
2. **Nghiên cứu (Research):** Tìm kiếm giải pháp trong các tài liệu nội bộ đã được cấp phép (`docs/SYSTEM_BASELINE.md`, mã nguồn hiện hành, Python standard library).
3. **Cách ly (Quarantine):** Lưu tri thức mới dưới trạng thái `CANDIDATE` (Cách ly). Tri thức này bị cấm xuất hiện trong câu trả lời hàng ngày để chống nhiễm độc trí nhớ (Data Poisoning).
4. **Đề xuất (Proposal):** Não bộ sinh mã hồ sơ đề xuất (Ví dụ: `prop_34405581`) gồm mã thay đổi Unified Diff và mức độ tự tin.
5. **Quyết định của Chủ nhân:**
   - Trạng thái mặc định luôn là `pending_review`.
   - Chỉ khi Chủ nhân cung cấp mã ủy quyền hợp lệ dạng `owner_approved:<proposal_id>:<secret>`, bản vá mới được phép áp dụng vào mã nguồn.

---

## 9. XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

### Sự cố 1: Khởi động Web UI báo `Local Ollama: Chưa kết nối` (Đèn đỏ)
- **Nguyên nhân:** Dịch vụ Ollama chưa chạy ngầm trên máy.
- **Cách khắc phục:** 
  1. Nhấp đúp vào **`KHOI_DONG_OLLAMA - Shortcut`** ngoài Desktop.
  2. Đợi 5 giây và tải lại trang Web (`F5`), đèn sẽ chuyển sang **Xanh (Online)**.

### Sự cố 2: Nhấn Micro nhưng không nhận giọng nói
- **Nguyên nhân:** Trình duyệt chưa cấp quyền sử dụng Micro hoặc đang dùng trình duyệt không hỗ trợ Web Speech API.
- **Cách khắc phục:**
  1. Khuyến nghị mở Web UI bằng trình duyệt **Google Chrome** hoặc **Microsoft Edge**.
  2. Bấm vào biểu tượng ổ khóa/cài đặt trên thanh địa chỉ trình duyệt -> Chọn **Cho phép Micro (Allow Microphone)**.
  3. Hoặc nhấn tổ hợp phím **`Windows + H`** để dùng tính năng nhận diện giọng nói gốc của Windows.

### Sự cố 3: Trợ lý trả lời lâu hoặc bị báo lỗi `Timeout`
- **Nguyên nhân:** Mô hình lớn `qwen2.5:7b` sinh câu trả lời tiếng Việt quá dài trên phần cứng máy tính.
- **Cách khắc phục:**
  1. Ở góc trên trang Web, chuyển sang mô hình **`qwen2.5:1.5b (Siêu tốc)`**. Mô hình này có tốc độ phản hồi nhanh hơn gấp 4 đến 5 lần.
  2. Thời gian chờ (Timeout) mặc định đã được nâng lên **120 giây**, đảm bảo đủ thời gian cho các câu trả lời phức tạp.

### Sự cố 4: Cổng mạng `8765` bị chiếm dụng
- **Cơ chế tự bảo vệ:** Máy chủ `run_web_ui.py` có cơ chế tự động dò tìm cổng tiếp theo (`8766`, `8767`...) nếu cổng 8765 đang bận, đảm bảo không bao giờ bị xung đột cổng.

---

## 10. PHÒNG ĐIỀU HÀNH & THAM VẤN CHỦ NHÂN (PORT :8766)

Nhằm đáp ứng yêu cầu nâng tầm QUAN AI BRAIN thành **Nhân sự số — Bản sao điều hành của Quanpt1**, hệ thống cung cấp một giao diện phòng điều hành độc lập tại:
👉 **URL:** `http://127.0.0.1:8766/`  
👉 **Khởi động một chạm:** Nhấp đúp vào tệp `KHOI_DONG_PHONG_DIEU_HANH_8766.bat` hoặc lối tắt Desktop **`QUAN AI BRAIN - Phong Dieu Hanh 8766.lnk`**.

Giao diện được thiết kế chuyên biệt theo từng mục (Tabs):

### Mục 1: Nhân Sự Số — Bản Sao Điều Hành
- **Hồ sơ bản sao:** Định hình tác phong kỷ luật, xưng "Em" gọi "Anh", quyết đoán, trung thực và phản ánh tư duy điều hành của Quanpt1.
- **5 Điều lệ cốt lõi (DIR-01 đến DIR-05):** Ranh giới minh bạch, trung thực tuyệt đối, không suy đoán vô căn cứ.
- **Ma trận năng lực hệ thống (Ground-Truth):** Phân định rạch ròi giữa Năng lực đang hoạt động (Active), Chế độ bất hoạt an toàn (Staging), và Hệ sinh thái vệ tinh được bảo tồn (Planned).

### Mục 2: Hộp Thư Tham Vấn & Phê Duyệt Ý Kiến (Consultation Inbox)
- Nơi Brain **chủ động gửi các câu hỏi, đề xuất nâng cấp mã nguồn (R4) hoặc quyết sách chiến lược** để xin ý kiến tham khảo của Anh.
- Chủ nhân có thể tương tác trực tiếp:
  - Bấm **`[Đồng Ý & Phê Duyệt Ngay]`** (Approve).
  - Bấm **`[Từ Chối Áp Dụng]`** (Reject).
  - Hoặc nhập chỉ đạo riêng vào ô văn bản và bấm **`[Gửi Chỉ Đạo]`** (Direct).
- Toàn bộ quyết định được lưu vết vào cơ sở dữ liệu quản trị bền vững.

### Mục 3: Báo Cáo Tự Học Định Kỳ & Nâng Cấp Hệ Thống
- Danh sách các **Kỳ báo cáo tự học** (Cycle Reports) ghi nhận tiến trình học hỏi liên tục.
- Xem chi tiết: Lỗ hổng tri thức đã phân tích, tri thức mới trong vùng cách ly (`QUARANTINED`), đề xuất nâng cấp phần mềm kèm mã diff.
- Nút bấm **`[🚀 Kích Hoạt Chu Kỳ Tự Học Ngay]`**: Cho phép Anh chủ động kích hoạt một chu kỳ tự học có giám sát từ giao diện.

### Mục 4: Điều Hành Kế Hoạch DAG & Ranh Giới An Toàn R0-R5
- Xem đồ thị phân rã công việc (DAG Planning), bảng kiểm toán phân cấp rủi ro từ R0 đến R5.
- Trạng thái các hệ sinh thái vệ tinh (`DC-COMMAND`, `SKILL_BAT_AI`, `BATTERY_AI_V4`) luôn ở chế độ bảo tồn read-only.

### Mục 5: Bàn Hội Thoại Trực Tiếp Với Bản Sao
- Kênh giao tiếp điều hành cấp cao bằng văn bản hoặc giọng nói (Micro Web Speech API).
- Bản sao suy luận dựa trên bằng chứng, tiếp nhận chỉ đạo và tự động tổng hợp phương án thực thi.

---

## 11. TÍNH NĂNG ĐÁNH THỨC RẢNH TAY BẰNG GIỌNG NÓI TỰ NHIÊN (WAKE WORD ACTIVATION V1)

Nhằm mang lại trải nghiệm rảnh tay (Hands-Free) cao cấp như một trợ lý điều hành thực thụ, QUAN AI BRAIN hỗ trợ tính năng **Đánh thức bằng từ khóa giọng nói tự nhiên (Wake Word V1)**, cho phép Anh trò chuyện liên tục mà không cần nhấn chuột vào nút Micro ở mỗi lượt.

### 11.1. Danh Sách Từ Khóa Đánh Thức Chuẩn (10 Từ Khóa)
Hệ thống nhận dạng cả Tiếng Việt và Tiếng Anh với tên gọi mặc định **TONY — QUAN AI BRAIN Voice Assistant**:
1. **“Hi TONY”** / **“Hey Tony”**
2. **“Tony ơi”** (Từ khóa thân mật, tự nhiên nhất)
3. **“Chào trợ lý”** / **“Hi trợ lý”** / **“Xin chào trợ lý”**
4. **“Hello assistant”** / **“Hi assistant”**
5. **“QUAN AI”** / **“Quan AI Brain”**

> 💡 **Khả năng tách lệnh thông minh (Zero-Loss Payload Extraction):**  
> Anh có thể gọi từ khóa và nói luôn yêu cầu trong cùng một hơi, ví dụ:  
> *“Tony ơi hãy tóm tắt danh sách công việc hôm nay”*  
> Trợ lý sẽ tự động nhận diện từ khóa `"Tony ơi"`, phát chuông xác nhận và chuyển ngay câu lệnh *“hãy tóm tắt danh sách công việc hôm nay”* cho AI xử lý mà không bị mất chữ.

---

### 11.2. Cách Kích Hoạt Trên Giao Diện (Port :8766)
1. Truy cập **`http://127.0.0.1:8766/`** trên Google Chrome hoặc Microsoft Edge.
2. Trên góc phải thanh tiêu đề (Executive Header), tìm ô **`Đánh Thức:`** và bấm nút **`[OFF]`** để chuyển sang **`[ON]`** (Nút sáng xanh).
3. Trình duyệt sẽ hỏi quyền truy cập Micro (lần đầu tiên) -> Bấm **Cho phép (Allow)**.
4. Đèn tín hiệu chuyển sang màu xanh dương nhịp thở nhẹ (**SẴN SÀNG / STANDBY**). Bây giờ Anh chỉ cần nói: **“Tony ơi”**!

---

### 11.3. Chu Trình 9 Trạng Thái Hoạt Động (Executive State Machine)
| Trạng thái | Đèn báo | Ý nghĩa & Hành vi |
| :--- | :---: | :--- |
| **DISABLED** | Xám | Chế độ rảnh tay đang tắt. |
| **STANDBY** | Xanh dương thở | Chờ từ khóa đánh thức ngầm với mức tiêu thụ CPU < 2%. |
| **WAKE_DETECTED**| Vàng kim | Đã nhận diện từ khóa! Phát chuông **Executive Chime** 2 âm thanh (440Hz -> 880Hz) xác nhận. |
| **LISTENING** | Xanh dương chớp | Đang lắng nghe lời nói của Anh. |
| **TRANSCRIBING**| Xanh dương đậm| Chuyển giọng nói thành văn bản. |
| **THINKING** | Tím xoay | Gửi câu hỏi đến Local Ollama và bộ nhớ để suy luận. |
| **SPEAKING** | Xanh lá sóng | Đang đọc phản hồi thành tiếng qua loa (TTS tiếng Việt). |
| **FOLLOW-UP** | Xanh dương | **Cửa sổ nối tiếp 20 giây**: Sau khi đọc xong, trợ lý tiếp tục lắng nghe 20 giây để Anh có thể ra lệnh tiếp mà không cần gọi lại từ khóa. |
| **ERROR** | Đỏ | Trình duyệt chưa cấp quyền Micro hoặc lỗi mic. |

---

### 11.4. Khẩu Lệnh Điều Khiển Trợ Lý Bằng Giọng Nói (Voice Control Commands)
Anh có thể ra lệnh trực tiếp bằng giọng nói bất cứ lúc nào:
- **“Ngủ đi”** / **“Tạm ngủ”** / **“Go to sleep”**: Yêu cầu trợ lý ngừng nghe và quay về chế độ STANDBY ngay lập tức.
- **“Dừng đọc”** / **“Dừng nói”** / **“Stop speaking”**: Ngắt ngay giọng đọc TTS nếu câu trả lời quá dài.
- **“Dừng nghe”** / **“Stop listening”**: Đóng cửa sổ lắng nghe hiện tại.
- **“Tắt trợ lý”** / **“Tắt đánh thức”**: Tắt hoàn toàn chế độ Hands-Free về trạng thái DISABLED.

---

### 11.5. Chống Tự Kích Hoạt Vòng Lặp (Acoustic Echo Cancellation - AEC)
Hệ thống tích hợp cơ chế khử tiếng vọng phần mềm: Khi trợ lý đang đọc phản hồi qua loa máy tính (`SPEAKING`), micro nhận dạng sẽ tự động tạm ngắt để Brain không nghe thấy chính giọng nói của mình, loại bỏ hoàn toàn hiện tượng tự kích hoạt lặp vô tận.

---

## 12. LỆNH TỰ ĐỘNG KHỞI ĐỘNG LẠI HỆ THỐNG SAU KHI CẬP NHẬT TÍNH NĂNG (AUTO-RESTART)

Sau mỗi lần cập nhật thêm tính năng mới, bổ sung mã nguồn hoặc vá lỗi, máy chủ Python đang chạy cần được khởi động lại để nạp toàn bộ mã nguồn mới nhất. QUAN AI BRAIN cung cấp lệnh tự động hóa hoàn toàn thao tác này một cách an toàn và nhanh chóng.

### 12.1. Ba Cách Thực Hiện Nhanh

#### Cách 1: Nhấp Đúp Chuột Một Chạm Ngoài Desktop (Tiện lợi nhất)
- Ngay trên Màn hình nền (Desktop), nhấp đúp vào lối tắt:  
  👉 **`QUAN AI BRAIN - Tu Dong Khoi Dong Lai.lnk`**  
  *(Hoặc nhấp đúp tệp `TU_DONG_KHOI_DONG_LAI_HE_THONG.bat` / `RESTART_SYSTEM.bat` tại thư mục gốc `E:\AI\QUAN AI BRAIN`)*.

#### Cách 2: Chạy Qua Dòng Lệnh CLI Tiêu Chuẩn
Tại cửa sổ dòng lệnh PowerShell / CMD:
```powershell
.venv\Scripts\python.exe -m quan_ai_brain.cli restart
```

#### Cách 3: Tự Động Kiểm Thử Nghiệm Thu, Lập Báo Cáo Rồi Mới Khởi Động (Khuyến nghị cho Kỹ sư)
Lệnh này sẽ chạy toàn bộ bộ kiểm thử tự động, cập nhật tài liệu bàn giao `HANDOFF_LATEST.md`. Nếu toàn bộ bài test vượt qua, hệ thống mới tiến hành khởi động lại:
```powershell
.venv\Scripts\python.exe tools/restart_system.py --validate
```

---

### 12.2. Quy Trình Khởi Động Lại Tự Động 6 Bước (Fail-Closed Safety)
1. **Kiểm tra mã nguồn trước khi khởi động (Pre-flight Import Check):**  
   Hệ thống kiểm tra cú pháp và khả năng nạp các module cốt lõi. Nếu phát hiện lỗi lập trình làm hỏng server, lệnh sẽ **dừng lại ngay lập tức** và báo lỗi, không bao giờ để hệ thống rơi vào trạng thái chết server.
2. **Quét cổng và dừng tiến trình cũ:**  
   Tự động phát hiện các tiến trình đang chiếm cổng `8766` và `8765`, dừng chúng nhẹ nhàng và đợi cổng được giải phóng hoàn toàn.
3. **Bảo đảm dịch vụ AI Ollama trực tuyến:**  
   Kiểm tra cổng `11434`. Nếu Ollama chưa bật, hệ thống sẽ tự động gọi Ollama chạy ngầm.
4. **Khởi chạy tiến trình mới độc lập trong nền:**  
   Khởi động lại Phòng Điều Hành (`run_executive_desk.py`) và Giao diện Chat (`run_web_ui.py`).
5. **Thăm dò sức khỏe dịch vụ (HTTP Polling):**  
   Liên tục kiểm tra endpoint nội bộ cho đến khi nhận được phản hồi HTTP 200 (Online).
6. **Mở trình duyệt:**  
   Tự động bật trình duyệt Web đưa Anh vào thẳng Phòng Điều Hành `http://127.0.0.1:8766/`.

---

> **TỔNG KẾT:**  
> Hệ thống QUAN AI BRAIN hiện tại đã đạt độ hoàn thiện cao, vận hành song song cả Cổng Chat Cục Bộ (:8765) và Phòng Điều Hành & Tham Vấn (:8766), tích hợp đánh thức rảnh tay bằng giọng nói tự nhiên V1, hỗ trợ công cụ tự động khởi động lại an toàn sau mỗi lần nâng cấp, bảo đảm năng lực bản sao nhân sự số kỷ luật, tự học liên tục và luôn đặt quyền quyết định của Chủ nhân **Quanpt1** ở vị trí tối cao.
