# THƯ MỤC: HƯỚNG DẪN SỬ DỤNG VÀ QUẢN TRỊ (HDSD)

Thư mục này chứa tài liệu hướng dẫn vận hành chi tiết dành cho Chủ nhân **Quanpt1** và các quản trị viên hệ thống **QUAN AI BRAIN V30.0**:

## 📚 Tài liệu chính

- 📖 **[HUONG_DAN_SU_DUNG_VA_QUAN_TRI.md](./HUONG_DAN_SU_DUNG_VA_QUAN_TRI.md)** - Hướng dẫn sử dụng toàn diện (27KB, 450+ dòng)
  - Tổng quan hệ thống V30
  - Khởi động hệ thống (4 cách)
  - Web UI & Voice interface
  - Console Menu & CLI
  - Quản trị an toàn R0-R5
  - Memory management
  - Self-learning & approval
  - Troubleshooting
  - Monitoring & Analytics
  - Backup & Disaster Recovery
  - Enterprise Integration
  - Mobile App usage
  - Security best practices

## 🚀 Quick Start

### 1. Đọc tài liệu
Mở file `HUONG_DAN_SU_DUNG_VA_QUAN_TRI.md` để xem hướng dẫn chi tiết.

### 2. Khởi động hệ thống

**Cách 1: 1-Click Deploy (Khuyến nghị)**
```powershell
.\deploy\production_deploy.ps1
```

**Cách 2: Manual Deploy**
```bash
pip install -r requirements-prod.txt
copy .env.production .env
python tools\run_migrations.py
.\tools\start_production.bat
```

**Cách 3: Desktop Shortcuts**
- 🌐 `KHOI_DONG_WEB_UI - Shortcut` - Web Chat & Voice
- 💻 `KHOI_DONG_QUAN_AI_BRAIN - Shortcut` - Console Menu
- ⚙️ `KHOI_DONG_OLLAMA - Shortcut` - Ollama service

### 3. Truy cập hệ thống

- **Web Dashboard:** http://localhost:8765
- **API Server:** http://localhost:8216
- **Health Check:** http://localhost:8216/api/health

## 📖 Nội dung chính

### Phần 1: Giới thiệu
- Tổng quan hệ thống V30
- Kiến trúc & modules
- Tính năng chính

### Phần 2: Sử dụng
- Web UI (Chat, Voice, Analytics)
- Console Menu
- CLI commands
- Mobile App

### Phần 3: Quản trị
- Security & R0-R5
- Memory management
- Self-learning approval
- Backup & Recovery
- Monitoring & Alerts

### Phần 4: Enterprise
- API Gateway
- Enterprise Connectors
- Message Queue
- Webhooks
- API Versioning

### Phần 5: Troubleshooting
- Sự cố thường gặp
- Log files
- Diagnostics
- Performance tuning

## 🔗 Tài liệu liên quan

- `docs\FUNCTIONAL_SPECIFICATIONS.md` - Chi tiết API & modules
- `docs\PRODUCTION_DEPLOYMENT.md` - Hướng dẫn deploy production
- `docs\DEPLOYMENT_GUIDE.md` - Deployment guide
- `reports\PRODUCTION_READY_REPORT.md` - Production readiness

## 📞 Hỗ trợ

- **Email:** quanpt1@viettel.com.vn
- **GitHub:** https://github.com/thequanhcm/quanpt1/issues
- **Slack:** #quanai-support

---

**Version:** V30.0-Production  
**Last Updated:** 2026-10-28  
**Maintained By:** QUAN AI BRAIN Team