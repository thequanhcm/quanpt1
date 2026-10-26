# 📖 HƯỚNG DẪN SỬ DỤNG SKILL: VIBE-AIWORKFORCE

**Vibe AI Workforce** là một Skill chuyên biệt dành cho hệ thống AI đóng vai trò như một **Workforce Architect** (Kiến trúc sư Tổ chức Số). Skill này giúp chuyển hóa bất kỳ một quy trình/nhiệm vụ thủ công nào của doanh nghiệp thành một **đội ngũ nhân sự AI tự động hóa hoàn chỉnh**.

## 1. Khi nào nên gọi Skill này?
Hãy kích hoạt skill này khi gặp các trường hợp sau:
- Có một quy trình nghiệp vụ phức tạp (vd: Quy trình Marketing từ A-Z, Quy trình Sales, v.v.) và muốn AI tự động hóa nó.
- Muốn chia nhỏ công việc cho nhiều "nhân viên AI" khác nhau (mỗi AI đảm nhận 1 chuyên môn).
- Muốn thiết kế một bộ tiêu chuẩn SOPs (Standard Operating Procedures), luật lệ (Rules), và bài test cho AI.

## 2. Cách ra lệnh (Prompting)
Để AI hiểu và bắt đầu làm việc, bạn cần cung cấp 1 prompt (lời nhắc) rõ ràng bao gồm các thông tin:
- **Đường dẫn thư mục công ty (COMPANY_ROOT)**: Bắt buộc phải có để AI biết lưu file vào đâu.
- **Mô tả nhiệm vụ**: Quy trình hiện tại đang chạy như thế nào?
- **Nỗi đau (Pain point)**: Khâu nào đang mất thời gian nhất và cần AI giải quyết?

**Ví dụ câu lệnh chuẩn:**
> *"Hãy dùng skill `vibe-aiworkforce` để xây dựng đội ngũ nhân sự số cho Quy trình Content Marketing của tôi. Hiện tại team tôi phải lên ý tưởng, viết bài, và đăng bài thủ công tốn rất nhiều thời gian. Hãy thiết kế các nhân sự AI chuyên biệt để giải quyết việc này. Thư mục gốc của công ty tôi nằm ở: `E:\Cong_Ty_X\02-Marketing`"*

## 3. Skill này sẽ làm ra những gì?
Thay vì chỉ sinh ra một file code vô hồn, Skill này sẽ cấu trúc lại toàn bộ thư mục phòng ban của bạn theo **Mô hình KWSR** cực kỳ khoa học:

- 🧠 **K (Knowledge) - `_knowledge/`**: Chứa các file `README.md` lưu trữ mục tiêu (KPI, OKR), tầm nhìn, và kiến thức chuyên ngành mà AI cần phải "học thuộc".
- 🔄 **W (Workflow) - `_workflow/`**: Chứa toàn bộ luồng công việc SOPs (Đầu vào là gì, quy trình xử lý ra sao, đầu ra như thế nào).
- 🤖 **S (Skills-Agents) - `_skills-agents/`**: Danh sách hồ sơ các "nhân viên AI" (AI Worker Profile) và phân quyền ai làm việc gì.
- ⚖️ **R (Rules) - `_rules/`**: Chính sách công ty, những giới hạn quyền hạn mà AI **tuyệt đối không được vượt qua** (Ví dụ: Không được tự ý chốt giá nếu chưa hỏi Giám đốc).

## 4. Nguyên tắc cốt lõi cần nhớ
- **Mỗi Skill là 1 con người số**: Đừng gộp mọi thứ vào 1 con AI. Hãy chia nhỏ ra (VD: 1 AI chuyên viết bài, 1 AI chuyên duyệt bài).
- **Phải lưu trong thư mục công ty**: Các file sinh ra phải nằm cùng với folder của phòng ban để dễ quản lý, dễ share và dễ update. Không lưu rải rác.
- **Rules là Quân lệnh**: AI không được quyền đàm phán với file Rules. Nó giống như nội quy công ty.
