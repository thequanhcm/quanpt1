# HƯỚNG DẪN CHUYỂN MÁY — ONE-CLICK (dành cho anh Quân)

## Cách dùng trên máy tính mới (3 bước)

1. **Cắm ổ F:** (hoặc chép nguyên thư mục `F:\BRAIN` sang ổ bất kỳ của máy mới — ví dụ `D:\BRAIN`)
2. **Double-click** `ONECLICK_SETUP_NEW_PC.bat` trong thư mục BRAIN
3. Chờ 5–15 phút (tải Python + thư viện lần đầu). Đọc kết quả PASS/WARN/FAIL trên màn hình.

## Script tự làm gì (8 bước, có log `reports\ONECLICK_SETUP_LOG.txt`)

| Bước | Việc | Nếu thiếu |
|---|---|---|
| 1 | Tìm Python ≥ 3.11 | Tự cài qua winget |
| 2 | Tạo `.venv` (venv cũ không dùng được giữa các máy) | Tự tạo, venv cũ giữ lại `.venv_maycu` |
| 3 | Cài dependencies (`pip install -e .`) | FAIL nếu không có internet |
| 4 | Kiểm `.env` có `NETMIND_API_KEY` | WARN — anh tự dán key (không bao giờ in giá trị) |
| 5 | Kiểm SSH key Pi5 (`%USERPROFILE%\.ssh\id_ed25519`) | WARN — anh chép 2 file key từ máy cũ |
| 6 | Kiểm Ollama + models fallback (qwen2.5:7b/1.5b/0.5b) | WARN — hướng dẫn `winget install Ollama.Ollama` + `ollama pull` |
| 7 | Chạy 37+ test nhanh của hệ thống | FAIL nếu code hỏng |
| 8 | Kiểm `TONY_START.bat` / `TONY_STOP.bat` | WARN nếu thiếu |

## Những gì KHÔNG tự chuyển (bắt anh làm 1 lần — đúng nguyên tắc không tự ghi secret)

- **NETMIND_API_KEY**: mirror có sẵn trong `F:\BRAIN\.env` (đã kiểm — có key). Nếu WARN → mở `.env`, dán dòng `NETMIND_API_KEY=...` (lấy từ máy cũ: `reg query HKCU\Environment /v NETMIND_API_KEY`)
- **SSH key Pi5**: chép `C:\Users\quocd\.ssh\id_ed25519` + `.pub` sang `%USERPROFILE%\.ssh\` máy mới
- **Tailscale**: đăng nhập app Tailscale trên máy mới (cùng tài khoản thequan.hcm@gmail.com)

## Sau khi ONECLICK xong

```
TONY_START.bat          ← khởi động toàn hệ thống (servers 8765+8766, watchdog, responder)
```
- Kiểm: mở `http://127.0.0.1:8766/health` → phải hiện JSON trạng thái
- Tắt máy cũ: **TONY_STOP.bat** trước khi đóng

## Nếu muốn re-mirror ngược (máy mới → ổ F)

Chạy `python tools\mirror_workspace_to_f.py` — script đã fix nhận diện rc=9 (extras) là hành vi bình thường của /MIR.

---
*Cập nhật: 01/11/2026 ~24:00. E2E test: 7 PASS / 1 WARN (thiếu .env trong folder giả) / 0 FAIL.*
