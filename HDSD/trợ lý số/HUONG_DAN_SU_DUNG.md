# 🤖 TRỢ LÝ SỐ QUAN AI BRAIN

## Giới thiệu sản phẩm

**QUAN AI BRAIN** là trợ lý AI cá nhân thông minh, được phát triển bởi **Phạm Thế Quân** (quanpt1@viettel.com.vn) - chuyên gia AI tại Viettel Networks.

### 🎯 Mục tiêu

Trợ lý số QUAN AI BRAIN giúp bạn:
- **Quản lý công việc** hàng ngày với trí nhớ dài hạn
- **Phân tích dữ liệu** kỹ thuật, tài chính, UPS
- **Tự động hóa** tác vụ lặp đi lặp lại
- **Học hỏi liên tục** từ tương tác với bạn
- **Bảo mật tuyệt đối** với cơ chế phân quyền R0-R5

### ✨ Tính năng nổi bật

#### 1. **Trí nhớ thông minh 3 tầng**
- **Ngắn hạn:** Lịch sử chat, ngữ cảnh phiên làm việc
- **Dài hạn:** Vector database với 53+ chunks tri thức
- **Đã xác minh:** Kiến thức bạn dạy, ưu tiên cao nhất
- **Cách ly:** Kiến thức tự học chờ duyệt (quarantine)

#### 2. **Giọng nói tự nhiên**
- **Tiếng Việt chuẩn** miền Bắc (giọng vi-VN-HoaiMyNeural)
- **Barge-in:** Ngắt lời tự nhiên khi bạn nói chồng
- **Turn control:** Quản lý lượt nói thông minh
- **Latency:** ~1.1s (dưới 7s yêu cầu)

#### 3. **Bảo mật đa lớp**
- **R0-R2:** Tự động thực thi (lệnh thông thường)
- **R3-R4:** Chờ phê duyệt qua NetChat
- **R5:** Chặn cứng (hành động nguy hiểm)
- **STOP/FREEZE:** Dừng khẩn cấp mọi tác vụ

#### 4. **Tích hợp NetChat**
- **Chat 24/7** qua NetChat
- **Commands:** "trạng thái", "stop", "freeze", "báo cáo"
- **Auto-responder:** Tự động phản hồi
- **File sharing:** Gửi/nhận file qua chat

#### 5. **Dashboard real-time**
- **Giám sát:** Trạng thái tất cả services
- **Metrics:** Độ trễ, success rate, issues
- **Knowledge:** 3 tab (Anh dạy, Chờ duyệt, Đã duyệt)
- **Biểu đồ:** Tăng trưởng tri thức theo thời gian

#### 6. **Windows Service**
- **Auto-start:** Tự động chạy khi khởi động Windows
- **Auto-restart:** Tự khởi động lại khi lỗi
- **Centralized logging:** Log tập trung, rotation 10MB
- **Health check:** Giám sát sức khỏe hệ thống

---

## 📦 Cài đặt

### Yêu cầu hệ thống

- **OS:** Windows 10/11
- **RAM:** 8GB+
- **Disk:** 50GB free
- **Python:** 3.11+
- **GPU:** NVIDIA 4GB+ (tùy chọn, cho voice)

### Cài đặt nhanh (1 click)

1. **Download:**
   ```bash
   git clone https://github.com/thequanhcm/quanpt1.git "E:\AI\QUAN AI BRAIN"
   ```

2. **Chạy installer:**
   - Right-click `INSTALL_ONE_CLICK.bat`
   - Chọn "Run as administrator"
   - Chờ 2-3 phút

3. **Khởi động lại máy**

4. **Verify:**
   ```cmd
   cd "E:\AI\QUAN AI BRAIN"
   python tools\health_check.py
   ```

**Chi tiết:** Xem `INSTALLATION_GUIDE.md`

---

## 🚀 Hướng dẫn sử dụng

### Khởi động hệ thống

#### Cách 1: Auto-start (sau khi setup)
- Services tự động chạy khi Windows khởi động
- Kiểm tra: `python tools\health_check.py`

#### Cách 2: Manual start
```cmd
cd "E:\AI\QUAN AI BRAIN"
tools\start_services.bat
```

### Sử dụng qua NetChat

#### Kết nối NetChat
1. Mở NetChat
2. Tìm channel: "TONY"
3. Bắt đầu chat

#### Commands cơ bản

| Command | Mô tả | Ví dụ |
|---------|-------|-------|
| **trạng thái** | Kiểm tra sức khỏe hệ thống | "Em kiểm tra trạng thái" |
| **stop** | Dừng tác vụ không quan trọng | "Dừng tất cả" |
| **freeze** | Đóng băng hệ thống | "Freeze hệ thống" |
| **báo cáo** | Tạo báo cáo tuần | "Tạo báo cáo tuần" |
| **kiểm tra** | Kiểm tra thiết bị | "Kiểm tra UPS" |

#### Ví dụ tương tác

**User:** "Trạng thái của em thế nào?"  
**Bot:** "✅ Hệ thống hoạt động bình thường\n- Server: ONLINE (port 8765)\n- Watchdog: ONLINE\n- Learning: ONLINE\n- Responder: ONLINE\n- Dashboard: ONLINE (port 8766)\n\nEm là **TONY**, trợ lý số của anh!"

**User:** "Dừng tất cả"  
**Bot:** "🛑 Đã dừng các tác vụ không quan trọng\nServices cốt lõi vẫn hoạt động"

**User:** "Tạo báo cáo tuần"  
**Bot:** "📊 Báo cáo tuần đã tạo\n- 5 sessions\n- 10 interactions\n- 80% success rate\n- 1.14s avg latency\n- 2 issues (non-critical)"

### Sử dụng Dashboard

#### Truy cập
- URL: http://127.0.0.1:8766/
- Mở browser, nhập URL

#### Các tab

**Tab 1: Tổng quan**
- Số liệu tổng: 150 KUs, 53 chunks
- Biểu đồ tăng trưởng
- Status tất cả services

**Tab 2: Anh dạy**
- Kiến thức bạn dạy (USER_PROVIDED)
- Ngày lưu, nguồn chat
- Priority cao nhất

**Tab 3: Chờ duyệt**
- Kiến thức tự học (quarantine)
- Tóm tắt + nguồn
- Nút Duyệt/Từ chối

**Tab 4: Đã duyệt**
- Kiến thức đã phê duyệt
- Đã nhập vào vector DB
- Có thể search

### Quản lý kiến thức

#### Dạy kiến thức mới
1. Chat với bot: "Em nhớ rằng..."
2. Bot lưu vào quarantine
3. Bạn duyệt trên Dashboard
4. Bot nhập vào verified memory

#### Xem kiến thức
- Dashboard → Tab "Anh dạy"
- Search theo từ khóa
- Lọc theo ngày, nguồn

#### Sửa/Xóa kiến thức
- Dashboard → Tìm kiến thức
- Click "Sửa" hoặc "Xóa"
- Xác nhận

### Logs & Monitoring

#### Xem logs
```cmd
# Server log:
type logs\server.log

# Watchdog log:
type logs\watchdog.log

# Learning log:
type logs\learning.log

# Responder log:
type logs\responder.log

# Dashboard log:
type logs\dashboard.log

# Audit log:
type logs\audit.log
```

#### Health check
```cmd
python tools\health_check.py
```

**Kết quả:**
```
============================================================
QUAN AI BRAIN — Health Check
============================================================

📊 SERVICE STATUS
------------------------------------------------------------
server          ✅ ONLINE (port 8765 listening)
watchdog        ✅ ONLINE (port 17236 listening)
learning        ✅ ONLINE (port 7724 listening)
responder       ✅ ONLINE
dashboard       ✅ ONLINE (port 8766 listening)

📅 TASK SCHEDULER STATUS
------------------------------------------------------------
QUAN-AI-BRAIN-Server      ✅ Task configured
QUAN-AI-BRAIN-Watchdog    ✅ Task configured
QUAN-AI-BRAIN-Learning    ✅ Task configured
QUAN-AI-BRAIN-Responder   ✅ Task configured
QUAN-AI-BRAIN-Dashboard   ✅ Task configured

============================================================
SUMMARY
============================================================
Services running: 5/5
Tasks configured: 5/5
Overall status: ✅ ALL ONLINE
```

---

## 🔧 Bảo trì

### Backup dữ liệu

```cmd
# Backup brain.db:
copy data\brain.db data\backup\brain_YYYY-MM-DD.db

# Backup vector_db:
xcopy data\vector_db data\backup\vector_db_YYYY-MM-DD /E /I

# Backup quarantine:
copy data\quarantine.db data\backup\quarantine_YYYY-MM-DD.db
```

### Restore dữ liệu

```cmd
# Restore brain.db:
copy data\backup\brain_YYYY-MM-DD.db data\brain.db

# Restart services:
tools\stop_services.bat
tools\start_services.bat
```

### Clean logs

```cmd
# Xóa logs cũ 30 ngày:
forfiles /p logs /s /m *.log /d -30 /c "cmd /c del @path"
```

### Update hệ thống

```cmd
cd "E:\AI\QUAN AI BRAIN"
git pull origin feature/cognitive-state-integration
pip install -e ".[all]"
tools\stop_services.bat
tools\start_services.bat
```

---

## 🐛 Xử lý sự cố

### Services không khởi động

**Triệu chứng:** `❌ OFFLINE` trong health check

**Giải pháp:**
```cmd
# Check Task Scheduler:
schtasks /Query /TN "QUAN-AI-BRAIN-Server" /V

# Check logs:
type logs\server.log

# Re-run setup as Admin:
tools\setup_windows_services.bat
```

### Port đã được sử dụng

**Triệu chứng:** `Address already in use`

**Giải pháp:**
```cmd
# Tìm process:
netstat -ano | findstr :8765

# Kill process:
taskkill /F /PID <PID>
```

### Ollama không phản hồi

**Triệu chứng:** `Connection refused`

**Giải pháp:**
```bash
# Check Ollama:
ollama list

# Start Ollama:
ollama serve

# Pull model:
ollama pull bge-m3
```

### Memory không lưu

**Triệu chứng:** Kiến thức không xuất hiện trên Dashboard

**Giải pháp:**
1. Check quarantine: `data/quarantine.db`
2. Check logs: `logs/learning.log`
3. Duyệt trên Dashboard
4. Re-ingest: `python tools/ingest_brain_db.py`

---

## 📊 Hiệu năng

### Metrics

| Metric | Giá trị | Mục tiêu | Trạng thái |
|--------|---------|----------|------------|
| **Voice latency** | 1.14s | <7s | ✅ PASS |
| **Success rate** | 80% | >85% | ⚠️ |
| **Memory retrieval** | <500ms | <1s | ✅ PASS |
| **Uptime** | 24/7 | 99.9% | ✅ PASS |
| **Auto-start** | Working | Required | ✅ PASS |

### Benchmark

- **150 knowledge units** trong brain.db
- **53 chunks** trong vector DB
- **158+ tests** passing (100%)
- **2,000+ lines** code
- **5,000+ lines** documentation

---

## 🔐 Bảo mật

### Phân quyền R0-R5

| Level | Mô tả | Ví dụ |
|-------|-------|-------|
| **R0** | Public info | "Thời tiết thế nào?" |
| **R1** | Read-only | "Kiểm tra UPS" |
| **R2** | Safe write | "Tạo báo cáo" |
| **R3** | Param approval | "Thay đổi config X" |
| **R4** | Full approval | "Deploy production" |
| **R5** | Hard-block | "Xóa database" |

### Audit log

Mọi hành động được log vào `logs/audit.log`:
- Timestamp
- User
- Action
- Result
- Evidence

### Data protection

- **No hardcoded credentials**
- **Secrets qua git credential fill**
- **No logging sensitive data**
- **Encrypted storage** (planned)

---

## 📞 Hỗ trợ

### Contact

- **Developer:** Phạm Thế Quân
- **Email:** quanpt1@viettel.com.vn
- **NetChat:** "TONY" channel
- **Repository:** https://github.com/thequanhcm/quanpt1

### Documentation

- **Installation:** `INSTALLATION_GUIDE.md`
- **Deployment:** `DEPLOYMENT_GUIDE.md`
- **Handoff:** `reports/FINAL_HANDOFF_REPORT.md`
- **This guide:** `HDSD/trợ lý số/HUONG_DAN_SU_DUNG.md`

### Logs

- **Location:** `logs/`
- **Format:** Rotating files (10MB, 5 backups)
- **Files:** server.log, watchdog.log, learning.log, responder.log, dashboard.log, audit.log

### UAT Logs

- **Location:** `data/uat_logs/`
- **Format:** JSON (daily files)
- **Example:** `uat_2026-10-28.json`

---

## 🎓 Học thêm

### Tài liệu phát triển

- **Architecture:** `docs/roadmap/MASTER_ROADMAP.md`
- **V31 Design:** `docs/roadmap/V31_MEMORY_INTELLIGENCE_DESIGN.md`
- **V36 Voice:** `docs/roadmap/v36/V36_PRE_IMPLEMENTATION_AUDIT.md`
- **V37 Skills:** `docs/V37/V37_PRE_IMPLEMENTATION_AUDIT.md`

### Source code

- **Memory:** `src/quan_ai_brain/memory/`
- **Voice:** `src/quan_ai_brain/voice/`
- **Cognition:** `src/quan_ai_brain/cognition/`
- **Dashboard:** `src/quan_ai_brain/dashboard/`

### Tests

- **Unit tests:** `tests/`
- **Integration:** `tests/test_v37_integration.py`
- **UAT:** `tools/uat_runner.py`

---

## 📜 License

**Proprietary** - Copyright © 2026 Phạm Thế Quân

Không được sao chép, phân phối hoặc sửa đổi mà không có sự cho phép bằng văn bản.

---

## 🙏 Lời cảm ơn

Cảm ơn bạn đã sử dụng **QUAN AI BRAIN**!

Hệ thống này là kết quả của **8 tuần phát triển**, **158+ tests**, **2,000+ dòng code**, và **nhiều đêm không ngủ** để mang lại cho bạn trải nghiệm tốt nhất.

**Mục tiêu tiếp theo:**
- Voice barge-in hoàn chỉnh
- Multi-agent coordination
- Self-improvement engine
- Enterprise integration

**Mọi ý kiến đóng góp đều được trân trọng!**

---

**Version:** 1.0  
**Last updated:** 2026-10-28  
**Status:** Production Ready ✅

---

*Trợ lý số QUAN AI BRAIN - Thông minh hơn mỗi ngày*