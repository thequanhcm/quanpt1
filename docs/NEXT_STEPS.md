# NEXT STEPS ROADMAP: QUAN AI BRAIN
**Document ID:** DOC-QAB-PLAN-001  
**Audit Date:** 2026-10-17  
**Auditor / Role:** AI Software Architect & Senior Engineer  
**Workspace:** `e:\AI\QUAN AI BRAIN`

---

## 1. Nguyên tắc Chỉ đạo Thực hiện
Mọi bước đi trong quá trình xây dựng QUAN AI BRAIN đều phải tuân thủ nghiêm ngặt các nguyên tắc sau:
1. **Tiến trình Nhỏ nhất, An toàn nhất và Đo lường được (Smallest Safe Testable Slice):** Không phát triển dàn trải; mỗi bước đều phải có bài test tự động xác nhận tính đúng đắn.
2. **Bảo tồn Nguyên vẹn Hệ sinh thái Hiện hữu:** Không sửa đổi, di chuyển hay xóa mã nguồn của `os_kernel`, `SKILL_BAT_AI`, `BATTERY_AI_V4` hay `DC-COMMAND`. Chỉ tham chiếu và tái sử dụng dưới dạng thư viện độc lập hoặc mô phỏng kiến trúc.
3. **Mọi thay đổi mã nguồn phải có Diff rõ ràng:** Người dùng (Quanpt1) luôn có toàn quyền kiểm soát và phê duyệt trước khi mã nguồn được áp dụng.
4. **Không lưu trữ bí mật (Secrets):** Sử dụng biến môi trường hệ thống hoặc nhắc người dùng nhập khi cần, không hardcode API key hay token vào repository.

---

## 2. Lộ trình Triển khai Tổng thể (Phased Roadmap)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Giai đoạn 1: Thiết lập Khung nền tảng (Foundation & Git Scaffolding)        │
│ [Xác lập venv, Git repository, cấu trúc thư mục module, test runner]        │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│ Giai đoạn 2: Lõi Quản trị An toàn & Bộ nhớ Đa tầng (Governance & Memory)    │
│ [Engine R0-R5, Phân quyền Authz, SQLite Memory: Episodic, Semantic, KEDB]    │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│ Giai đoạn 3: Bộ điều hợp LLM & Vòng lặp Kế hoạch (LLM & Planning Loop)     │
│ [Adapter Local Qwen2.5:7b + Fallback, Phân rã mục tiêu, Tool Sandbox]       │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│ Giai đoạn 4: Động cơ Bảo chứng Nhận thức CLAE (Outcome Verification & CLAE) │
│ [Kiểm chứng kết quả, Chống ngẫu nhiên, Vùng cách ly tri thức mới]           │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│ Giai đoạn 5: Vận hành Ngầm 24/7 Bền bỉ (Resilient Background Daemon)        │
│ [Scheduler, Self-Healing Watchdog từ Kernel L3, Báo cáo tiến độ tự động]    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Bước Tiếp theo Nhỏ nhất, An toàn nhất và Có thể Kiểm thử (Sprint 1: The Walking Skeleton)

Bước kế tiếp ngay sau khi bản báo cáo này được phê duyệt là xây dựng **Bộ xương di động (Walking Skeleton)** tối thiểu cho `QUAN AI BRAIN` ngay trong workspace `e:\AI\QUAN AI BRAIN`:

### 3.1. Nhiệm vụ cụ thể của Sprint 1:
1. **Khởi tạo Quản lý Phiên bản (Git Init):**
   - Chạy `git init` trong `e:\AI\QUAN AI BRAIN`.
   - Tạo `.gitignore` chuẩn cho Python (bỏ qua `.venv/`, `__pycache__/`, `*.db`, `.env`, log files, crash dumps).
2. **Cấu trúc Thư mục Module Dự án:**
   ```
   QUAN AI BRAIN/
   ├── docs/                     # Tài liệu thiết kế & báo cáo kiểm toán
   ├── config/                   # Cấu hình hệ thống (không chứa secret)
   ├── src/
   │   ├── __init__.py
   │   ├── core/                 # Lõi điều phối Kernel & Quản trị R0-R5
   │   ├── memory/               # Lõi trí nhớ (SQLite Episodic & Semantic)
   │   ├── planning/             # Bộ lập kế hoạch tác vụ
   │   ├── tools/                # Hộp cát công cụ an toàn
   │   ├── clae/                 # Động cơ bảo chứng học tập
   │   └── daemon/               # Tiến trình chạy ngầm & watchdog
   ├── tests/                    # Bài kiểm thử tự động (pytest)
   │   ├── __init__.py
   │   └── test_smoke.py         # Kiểm tra tính toàn vẹn hệ thống ban đầu
   ├── pyproject.toml            # Khai báo dependency tối thiểu
   └── README.md                 # Giới thiệu tổng quan và hướng dẫn chạy
   ```
3. **Môi trường Thực thi Cô lập:**
   - Tạo virtual environment cục bộ `.venv` sử dụng Python 3.11/3.14 sẵn có trên máy.
   - Cài đặt `pytest` để hỗ trợ kiểm thử tự động.
4. **Smoke Test Đầu tiên (`tests/test_smoke.py`):**
   - Viết bài kiểm thử đầu tiên kiểm chứng:
     - Môi trường chạy đúng phiên bản Python.
     - Module `src` được import bình thường.
     - Kiểm tra cơ chế tạo/đọc SQLite Memory tạm thời.
     - Kiểm tra bộ lọc Redaction không cho phép hiển thị mật khẩu giả định.

---

## 4. Tiêu chí Đạt (Definition of Done - DoD) cho Sprint 1
- [ ] Lệnh `git status` trong workspace thể hiện cây thư mục sạch sẽ, đúng quy ước `.gitignore`.
- [ ] Lệnh `pytest tests/` chạy hoàn tất với 100% test case pass.
- [ ] Không có bất kỳ tệp tin nào bị ghi đè hay sửa đổi bên ngoài `e:\AI\QUAN AI BRAIN`.
- [ ] Không có secret hay token nào bị đưa vào Git hay log tệp tin.

---

## 5. Đề xuất Quyết định Cần Quanpt1 Duyệt
Trước khi bắt đầu Sprint 1, xin đề xuất người dùng phê duyệt:
1. **Phiên bản Python ưu tiên:** Sử dụng Python 3.11 hay Python 3.14 cho môi trường `.venv` của QUAN AI BRAIN? *(Khuyến nghị: Python 3.11 vì độ tương thích cao và ổn định với các thư viện AI hiện hữu).*
2. **Khởi tạo Git Repository:** Cho phép chạy `git init` và tạo `.gitignore` ngay trong workspace `e:\AI\QUAN AI BRAIN`.
