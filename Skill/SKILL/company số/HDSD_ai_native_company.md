# 🏢 HƯỚNG DẪN SỬ DỤNG: AI NATIVE COMPANY (Mô hình Công ty Số)

**AI Native Company** là một bộ giải pháp toàn diện giúp chuyển đổi cách vận hành doanh nghiệp: từ việc 1 người làm tất cả (hoặc quản lý đội ngũ nhân sự đắt đỏ) sang mô hình **1 người vận hành + đội ngũ Nhân sự AI (AI Workforce)**.

Dự án này đặc biệt tối ưu cho Solopreneur (Doanh nghiệp 1 người) và SMEs (Doanh nghiệp vừa và nhỏ), giúp giảm 97% chi phí vận hành mà vẫn đảm bảo chất lượng đầu ra thông qua 2 Skill cốt lõi.

---

## 🚀 1. TỔNG QUAN VỀ 2 SKILL CHÍNH

Bạn sẽ sử dụng kết hợp 2 Skill theo đúng thứ tự để xây dựng công ty số của mình:

### 🎯 Skill 1: `vibe-company-orchestrator` (Thiết kế Bộ máy Công ty)
- **Nhiệm vụ:** Thiết kế cấu trúc tổng thể của công ty từ một thư mục trống.
- **Đầu ra:** Sơ đồ phòng ban, chức năng, mục tiêu (OKR), quy trình chuẩn (SOP), RACI (Phân quyền trách nhiệm) và tiêu chuẩn chất lượng.
- **Lưu ý:** Skill này chỉ cần chạy **1 lần** khi bạn mới bắt đầu setup công ty.

### 🤖 Skill 2: `vibe-aiworkforce` (Tuyển dụng & Phân bổ Nhân sự AI)
- **Nhiệm vụ:** Sau khi đã có các phòng ban và quy trình (từ Skill 1), bạn dùng Skill này để "tạo ra" các nhân sự AI chuyên biệt đảm nhận từng quy trình đó.
- **Đầu ra:** File cấu trúc nhân sự, thiết lập vai trò, luật lệ (Rules), hệ thống kiểm thử (Tests) và các luồng công việc (State Machine).

---

## 🛠 2. HƯỚNG DẪN CÀI ĐẶT
Bộ công cụ này đã được đóng gói sẵn trong thư mục `ai_native_company-main`. Để AI (như Claude Code, Antigravity) nhận diện được 2 Skill này, bạn cần cài đặt chúng.

### Cài đặt nhanh (Khuyên dùng):
Mở Terminal/PowerShell tại thư mục `ai_native_company-main\community_version` và chạy lệnh:

**Với Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File src\install.ps1
```

**Với macOS/Linux:**
```bash
bash src/install.sh
```
Hệ thống sẽ hỏi bạn đang dùng ứng dụng AI nào (Claude Code, Antigravity, v.v.) để copy Skill vào đúng chỗ. Khởi động lại ứng dụng AI để hoàn tất.

---

## 🎯 3. QUY TRÌNH SỬ DỤNG THỰC TẾ (3 BƯỚC)

### Bước 1: Khởi tạo Công ty (Dùng `vibe-company-orchestrator`)
1. Tạo một thư mục trống trên máy tính của bạn (VD: `D:\Cong_Ty_Cua_Toi`).
2. Mở ứng dụng AI (Claude/Antigravity) tại thư mục đó và gõ lệnh:
   > `/vibe-company-orchestrator`
3. Cung cấp thông tin theo yêu cầu của AI:
   - Ngành nghề kinh doanh là gì?
   - Tầm nhìn, mục tiêu công ty (OKR) là gì?
   - Sơ đồ tổ chức mong muốn (vd: Cần phòng Sales, phòng Marketing, phòng Kế toán).
4. **Kết quả:** AI sẽ tự động tạo ra một loạt các thư mục phòng ban và các file `README.md`, `SOP` chuẩn hóa cực kỳ chuyên nghiệp.

### Bước 2: "Tuyển dụng" Nhân sự số (Dùng `vibe-aiworkforce`)
Sau khi đã có khung công ty, bạn bắt đầu gán việc cho AI xử lý từng phòng ban.
1. Vẫn trong ứng dụng AI, gõ lệnh:
   > `/vibe-aiworkforce`
2. Cung cấp thông tin:
   - Chỉ định `COMPANY_ROOT` (Chính là đường dẫn thư mục `D:\Cong_Ty_Cua_Toi`).
   - Yêu cầu: *"Hãy xây dựng đội ngũ nhân sự số cho phòng Marketing dựa trên các SOP đã tạo."*
3. **Kết quả:** AI sẽ tạo ra cấu trúc **KWSR** (Knowledge - Workflow - Skills - Rules) để biến các AI này thành những "nhân viên" biết tuân thủ luật lệ và quy trình.

### Bước 3: Vận hành & Giám sát hàng ngày
Giờ đây, công ty số của bạn đã hoạt động theo cơ chế **State Machine**:
- **Giao việc:** Bạn thả dữ liệu cần làm vào thư mục `input/` của quy trình tương ứng.
- **Xử lý:** Nhân sự AI tự động vào nhận việc ở `processing/`.
- **Kết quả:** Sản phẩm hoàn thiện nằm ở `output/`.
- **Giám sát:** Bạn chỉ cần ngồi xem Log và duyệt kết quả cuối cùng ở các điểm mù (Human in the loop - HITL).

---

## 💡 BÍ QUYẾT THÀNH CÔNG VỚI MÔ HÌNH NÀY
- **Đừng coi AI là ChatGPT:** Đừng bắt AI làm tất cả trong 1 file prompt. Hãy chia nhỏ công ty thành các Phòng ban $\rightarrow$ Chia phòng ban thành Quy trình (SOP) $\rightarrow$ Giao 1 AI đảm nhận đúng 1 Quy trình.
- **Trần sao âm vậy:** Hãy thiết kế công ty số giống y hệt công ty thực tế. Có Giám đốc, có Nhân viên, có KPI, có Nội quy (Rules).
- **Rules không thể đàm phán:** Nội quy sinh ra là để AI tuân thủ 100%. Mọi hành động của AI đều bị kiểm tra bởi các bài Test tự động nhằm chống hiện tượng "ảo giác" (hallucination).
