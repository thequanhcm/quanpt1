# Watchdog Root Cause Analysis — 12/11/2026

## Triệu chứng
- Watchdog restart liên tục mỗi 1-2 phút
- Log: "No module named 'quan_ai_brain'" warning liên tục
- watchdog_stderr.log: "can't open file 'D:\\AI\\AI'" (path cũ từ máy khác)

## Điều tra
1. **8 pythonw.exe chạy song song** (4 loại × 2: .venv + Python311 global)
2. **Python311 global** = `C:\Users\DELL\AppData\Local\Programs\Python\Python311\pythonw.exe`
3. **.venv pythonw.exe** = launcher (249KB) → exec Python311 global (101KB)
4. **Đây là behavior BÌNH THƯỜNG** của Python venv trên Windows: launcher + actual Python = 2 process

## Root cause
- **KHÔNG phải watchdog crash** — watchdog chạy bình thường khi foreground
- **KHÔNG phải "No module named"** — đó là warning từ Python311 global process (không có site-packages .venv)
- **THẬT SỰ LÀ**: Khi kill all pythonw (bằng taskkill), watchdog bị kill → restart
- watchdog_stderr.log "D:\\AI\\AI" là từ session CŨ (máy quocd), không phải hiện tại

## Fix đã áp dụng
1. **tools/spawn_detached.py** — spawn process detached (workaround Windows CMD `start` quirk)
2. **KHOI_DONG_24_7.bat** — dùng spawn_detached.py thay vì `start "" /B`
3. **Watchdog KHÔNG cần fix** — nó hoạt động đúng, chỉ bị kill bởi external

## Khuyến nghị
- KHÔNG kill all pythonw khi watchdog đang chạy (sẽ trigger restart loop)
- Nếu cần restart: kill chỉ process cụ thể, hoặc dùng Task Scheduler trigger lại
- Python311 global process là BÌNH THƯỜNG — không cần loại bỏ
