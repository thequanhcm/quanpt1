# QUAN AI BRAIN — Sprint 1 Starter

Bộ khung kỹ thuật ban đầu cho QUAN AI BRAIN. Gói này được tạo độc lập để anh kiểm tra trước khi hợp nhất vào workspace Windows `E:\AI\QUAN AI BRAIN`.

## Phạm vi đã triển khai trong gói

- Policy engine tối thiểu cho mức rủi ro R0–R5; R5 bị chặn cứng trong bản nền.
- SQLite Memory Store với episodic memory và candidate knowledge quarantine.
- Audit JSONL có redaction cơ bản.
- Guard bảo vệ đường dẫn, từ chối đường dẫn thoát khỏi workspace.
- Health check cơ bản.
- CLI cho self-check và memory thử nghiệm.
- Script chạy test rồi tự tạo báo cáo bàn giao tại `reports/HANDOFF_LATEST.md` và một bản có timestamp.

## Trạng thái quan trọng

Đây là **starter kit**, chưa phải bản triển khai trên máy Dell của anh, chưa kết nối Ollama, Kernel L3, DC-COMMAND, SKILL_BAT_AI hoặc Battery AI V4, và chưa phải daemon 24/7. Không được tuyên bố các kết nối đó đã hoạt động khi chưa có kiểm thử tích hợp.

## Thiết lập trên Windows PowerShell

1. Tải ZIP và giải nén thành thư mục staging riêng, ví dụ `E:\AI\QUAN_AI_BRAIN_SPRINT1_STAGING` (đặt ngang hàng, không đặt bên trong workspace thật).
2. Kiểm tra bộ khung trong staging trước. Sao lưu workspace thật `E:\AI\QUAN AI BRAIN` trước khi hợp nhất.
3. Trong PowerShell, chạy xem trước; lệnh này mặc định không ghi tệp:

```powershell
Set-Location 'E:\AI\QUAN_AI_BRAIN_SPRINT1_STAGING'
py -3.11 tools\merge_starter_safely.py --source . --target 'E:\AI\QUAN AI BRAIN'
```

4. Đọc toàn bộ kế hoạch. Script chỉ sao chép tệp còn thiếu, bỏ qua tệp trùng tên và không ghi đè tệp hiện hữu. Chỉ sau khi kiểm tra đúng thư mục đích và chấp nhận danh sách mới chạy:

```powershell
py -3.11 tools\merge_starter_safely.py --source . --target 'E:\AI\QUAN AI BRAIN' --apply
```

5. Nếu có xung đột như `.gitignore`, `AGENTS.md` hoặc `pyproject.toml`, không ghi đè; hợp nhất thủ công sau khi xem diff.
6. Mở Antigravity với workspace thật `E:\AI\QUAN AI BRAIN` (không mở toàn bộ `E:\AI`) và yêu cầu Agent kiểm tra các tệp đã hợp nhất.
7. Trong workspace thực tế, ưu tiên Python 3.11 x64:

```powershell
py -3.11 --version
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

4. Chạy kiểm thử và sinh báo cáo bàn giao:

```powershell
.\.venv\Scripts\python.exe tools\validate_and_report.py
```

5. Mở và gửi lại tệp `reports\HANDOFF_LATEST.md` trong cuộc trò chuyện. Nếu lệnh test trả mã lỗi khác 0, vẫn gửi báo cáo vì báo cáo cũng ghi lại tình trạng thất bại.

## Chạy thử thủ công

```powershell
.\.venv\Scripts\python.exe -m quan_ai_brain.cli self-check
.\.venv\Scripts\python.exe -m quan_ai_brain.cli memory-add --summary "Kiểm tra bộ nhớ khởi tạo" --source "manual-test"
.\.venv\Scripts\python.exe -m quan_ai_brain.cli memory-list
```

Lệnh CLI dùng `data\brain.db` bên trong workspace hiện hành. Chỉ chạy sau khi đã chọn đúng thư mục dự án. Không dùng dữ liệu sản xuất cho bài kiểm thử ban đầu.

## Giới hạn bảo mật của bản Sprint 1

- Không có tool chạy PowerShell tùy ý, gọi API ghi hoặc điều khiển thiết bị.
- Không có cơ chế đọc tệp bên ngoài workspace.
- Candidate knowledge không được tự kích hoạt thành tri thức chính thức nếu thiếu phê duyệt và kết quả kiểm thử hồi quy.
- R5 luôn bị chặn; không đưa secret phê duyệt vào mã nguồn.
- Script báo cáo chỉ kiểm kê tên và kích thước tệp an toàn trong workspace, trạng thái Git và kết quả test. Nó không đọc `.env`, private key, token, cơ sở dữ liệu hay toàn bộ ổ đĩa.

## Tiêu chí nghiệm thu Sprint 1

- `pytest tests/` chạy thành công trên máy đích.
- Các test redaction, policy R0–R5, SQLite memory, quarantine, audit và path guard đều PASS.
- Không sửa hệ thống ở ngoài workspace.
- Sau mỗi vòng triển khai, chạy `tools\validate_and_report.py` và gửi `reports\HANDOFF_LATEST.md` để phiên ChatGPT tiếp theo đọc được trạng thái mới nhất.
