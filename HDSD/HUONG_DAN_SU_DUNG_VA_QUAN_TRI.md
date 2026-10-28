# QUAN AI BRAIN — HƯỚNG DẪN SỬ DỤNG VÀ QUẢN TRỊ TOÀN DIỆN
> **Dành cho Chủ nhân:** `Quanpt1`  
> **Phiên bản:** `V30.0-Production` — Enterprise AI Platform  
> **Môi trường:** Windows 10/11 x64, Python 3.10+, Local Ollama/NetMind Cloud  
> **Tài liệu lưu tại:** `E:\AI\QUAN AI BRAIN\HDSD\HUONG_DAN_SU_DUNG_VA_QUAN_TRI.md`

---

## MỤC LỤC
1. [TỔNG QUAN HỆ THỐNG V30](#1-tổng-quan-hệ-thống-v30)
2. [CÁC CÁCH KHỞI ĐỘNG HỆ THỐNG](#2-các-cách-khởi-động-hệ-thống)
3. [HƯỚNG DẪN SỬ DỤNG GIAO DIỆN WEB CHAT & VOICE](#3-hướng-dẫn-sử-dụng-giao-diện-web-chat--voice)
4. [HƯỚNG DẪN SỬ DỤNG CONSOLE MENU](#4-hướng-dẫn-sử-dụng-console-menu)
5. [HƯỚNG DẪN CLI & API](#5-hướng-dẫn-cli--api)
6. [QUẢN TRỊ AN TOÀN & HIẾN PHÁP R0-R5](#6-quản-trị-an-toàn--hiến-pháp-r0-r5)
7. [QUẢN TRỊ TRÍ NHỚ (MEMORY MANAGEMENT)](#7-quản-trị-trí-nhớ-memory-management)
8. [QUẢN TRỊ ĐỘNG CƠ TỰ HỌC](#8-quản-trị-động-cơ-tự-học)
9. [XỬ LÝ SỰ CỐ (TROUBLESHOOTING)](#9-xử-lý-sự-cố-troubleshooting)
10. [MONITORING & ANALYTICS](#10-monitoring--analytics)
11. [BACKUP & DISASTER RECOVERY](#11-backup--disaster-recovery)
12. [ENTERPRISE INTEGRATION](#12-enterprise-integration)
13. [MOBILE APP USAGE](#13-mobile-app-usage)
14. [SECURITY BEST PRACTICES](#14-security-best-practices)

---

## 1. TỔNG QUAN HỆ THỐNG V30

**QUAN AI BRAIN V30.0** là **Enterprise-grade AI Platform** hoàn chỉnh, được phát triển qua **30 sprints** với:

### 🎯 Tính năng chính
- **60+ modules** AI/ML chuyên sâu
- **258,000+ dòng code** production-ready
- **1,455+ tests** automated (100% pass)
- **300KB+ documentation** hoàn chỉnh
- **100+ API endpoints** enterprise-grade

### 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                    NGINX Load Balancer                      │
│                  HTTPS (SSL/TLS) Enabled                    │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   API        │ │  Responder   │ │   Learning   │
│   Server     │ │   (Bot)      │ │   Daemon     │
│   (8216)     │ │   (18036)    │ │   (7724)     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Redis     │  │  PostgreSQL │  │  Watchdog   │
│  (Cache)    │  │   (DB)      │  │  (Monitor)  │
└─────────────┘  └─────────────┘  └─────────────┘
```

### 📦 Các module chính

#### Core Memory System (V11-V21)
- **Deep Memory Store**: Persistent knowledge base với semantic search
- **Knowledge Graph**: Relationship mapping & graph traversal
- **Temporal Memory**: Time-aware memory với automatic aging
- **Emotional Memory**: Sentiment tracking & emotion-based search
- **Counterfactual Memory**: What-if scenarios & alternative outcomes

#### Cognitive Engine (V23)
- **Causal Reasoning**: Chain discovery, intervention planning
- **Federated Learning**: Privacy-preserving distributed training
- **Collaboration**: Real-time shared state với CRDT
- **Performance Optimizer**: Auto-tuning & bottleneck detection
- **Security Hardening**: Configuration scanning & risk assessment

#### Mobile & NLP (V24)
- **NLP Query Engine**: Natural language understanding
- **Voice Interface**: STT/TTS với multi-language support
- **Offline Sync**: Conflict resolution & checkpoint/resume
- **Notifications**: Priority queue & quiet hours

#### Analytics & Insights (V25)
- **Analytics Dashboard**: Real-time metrics & visualizations
- **AI Insights Engine**: Pattern detection & anomaly detection
- **Report Generator**: Automated reports (PDF/Excel/HTML)
- **Graph Visualization**: Force-directed layout & centrality
- **Recommendation System**: Content-based & collaborative filtering

#### Auto-Optimization (V26)
- **Auto-Tuner**: Performance optimization & parameter tuning
- **Self-Learning Engine**: Continuous improvement từ feedback
- **Adaptive Algorithms**: Dynamic thresholds & cooldown
- **Improvement Loop**: Measure→Analyze→Propose→Apply
- **Intelligent Cache**: LRU + adaptive capacity & prefetch

#### Security & Compliance (V27)
- **Authentication**: OAuth 2.0, OIDC, MFA (TOTP/SMS/WebAuthn), SSO
- **RBAC/ABAC**: Fine-grained access control với 10+ roles
- **Audit Logging**: Immutable hash-chained logs, GDPR compliance
- **Data Protection**: Encryption at rest & in transit, masking
- **Security Monitoring**: Intrusion detection & threat analysis

#### Enterprise Integration (V28)
- **API Gateway**: Routing, rate limiting, caching, authentication
- **Enterprise Connectors**: Salesforce, M365, Slack, SAP, Oracle
- **Message Queue**: Pub/sub, consumer groups, DLQ (Kafka/RabbitMQ)
- **Webhooks**: Event-driven integrations với HMAC signing
- **API Versioning**: Deprecation management & migration paths

#### Advanced AI (V29)
- **Neural Symbolic AI**: Hybrid neural + symbolic reasoning
- **Common Sense Reasoning**: 10K+ concepts & inference paths
- **Explainable AI (XAI)**: Feature attribution & counterfactuals
- **Transfer Learning**: Few-shot learning & model distillation
- **Multi-Agent Collaboration**: BDI agents & FIPA-ACL messaging

#### Scalability & Performance (V30)
- **Horizontal Scaling**: Auto-scaling, load balancing, circuit breakers
- **Performance Optimizer**: Query optimization & index recommendations
- **Disaster Recovery**: Backup/restore, RTO < 15min, RPO < 5min
- **Monitoring**: Distributed tracing, SLO/SLI, error budgets
- **Business Intelligence**: Time-series aggregation & KPI dashboards

---

## 2. CÁC CÁCH KHỞI ĐỘNG HỆ THỐNG

### Cách 1: 1-Click Production Deploy (Khuyến nghị)

```powershell
# Chạy với Administrator
cd "E:\AI\QUAN AI BRAIN"
.\deploy\production_deploy.ps1
```

**Tự động thực hiện:**
- ✅ Pre-flight checks (Python, Git, Redis, PostgreSQL)
- ✅ Backup database & configuration
- ✅ Stop services (nếu đang chạy)
- ✅ Pull code mới nhất từ Git
- ✅ Install dependencies
- ✅ Run database migrations
- ✅ Start all services
- ✅ Verify health checks
- ✅ Rollback tự động nếu lỗi

### Cách 2: Manual Deploy (5 phút)

```bash
# 1. Install dependencies
pip install -r requirements-prod.txt

# 2. Configure environment
cp .env.production .env
# Edit .env với thông tin của bạn

# 3. Run migrations
python tools\run_migrations.py

# 4. Start services
.\tools\start_production.bat

# 5. Verify deployment
python tools\verify_production.py
```

### Cách 3: Start Services Individually

```bash
# Start API Server (port 8216)
.\.venv\Scripts\python.exe tools\server.py --env=production

# Start Responder (port 18036)
.\.venv\Scripts\python.exe tools\netchat_auto_responder.py --env=production

# Start Learning Daemon (port 7724)
.\.venv\Scripts\python.exe tools\learning_daemon.py --env=production

# Start Watchdog (port 17236)
.\.venv\Scripts\python.exe tools\watchdog.py --env=production

# Start Dashboard (port 8765)
.\.venv\Scripts\python.exe tools\dashboard.py --env=production
```

### Cách 4: Docker Deployment (Optional)

```bash
# Build Docker image
docker build -t quan-ai-brain:v30 .

# Run with docker-compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

---

## 3. HƯỚNG DẪN SỬ DỤNG GIAO DIỆN WEB CHAT & VOICE

### Truy cập Dashboard

**Địa chỉ:** `http://localhost:8765`

### Các Tab chính

#### 💬 Tab 1: Cognitive Chat & Voice

**Chat với AI:**
1. Gõ câu hỏi vào khung nhập liệu
2. Nhấn **Enter** hoặc click nút **Gửi**
3. AI sẽ trả lời dựa trên kiến thức từ memory

**Voice Input (STT):**
1. Click nút **Microphone 🎙️**
2. Nói câu hỏi bằng tiếng Việt
3. Hệ thống chuyển giọng nói → văn bản
4. Click **Gửi** để send

**Voice Output (TTS):**
1. Bật nút **TTS** ở góc phải
2. AI sẽ đọc to câu trả lời

**Chọn Model:**
- `qwen2.5:7b`: Chất lượng cao, tiếng Việt tốt
- `qwen2.5:1.5b`: Tốc độ nhanh
- `glm-5.3-flash`: NetMind Cloud (nếu configured)

#### 🧠 Tab 2: Memory Management

**Xem trí nhớ:**
- Hiển thị tất cả knowledge units
- Lọc theo type, status, scope
- Tìm kiếm semantic

**Thêm trí nhớ mới:**
1. Click **"+ Add Memory"**
2. Nhập nội dung
3. Chọn type: `fact`, `concept`, `procedure`, `rule`, `example`
4. Chọn scope: `general`, `domain-specific`, `personal`
5. Click **Save**

**Sửa/Xóa trí nhớ:**
- Click vào memory unit
- Edit nội dung hoặc click **Delete**

#### 📊 Tab 3: Analytics Dashboard

**Metrics hiển thị:**
- Total Knowledge Units
- Quality Score (avg confidence)
- Freshness (avg age)
- Activity (creates/updates/deletes)
- Search metrics (queries, CTR)

**Charts:**
- Growth trend (line chart)
- Distribution by type (pie chart)
- Activity heatmap
- Performance metrics

**Export:**
- Click **Export Report**
- Chọn format: PDF, Excel, HTML
- Download file

#### 🛡️ Tab 4: Security & Audit

**View audit logs:**
- Filter by user, action, time range
- Export logs (GDPR compliance)
- Verify integrity (hash chain)

**Manage users:**
- Add/remove users
- Assign roles
- Reset passwords

**Security alerts:**
- View recent alerts
- Acknowledge alerts
- Configure alert rules

#### ⚙️ Tab 5: System Settings

**Configuration:**
- Database settings
- Redis settings
- LLM model selection
- Rate limiting
- Feature flags

**Monitoring:**
- System health status
- Resource usage (CPU, memory, disk)
- Active connections
- Cache hit rate

**Backup & Restore:**
- Create backup
- Restore from backup
- Schedule automated backups

---

## 4. HƯỚNG DẪN SỬ DỤNG CONSOLE MENU

### Khởi động Console

```bash
.\tools\KHOI_DONG_QUAN_AI_BRAIN.bat
```

### Menu chính (10 lựa chọn)

```
╔════════════════════════════════════════╗
║   QUAN AI BRAIN - Console Menu        ║
╠════════════════════════════════════════╣
║  0. Exit                               ║
║  1. Start/Stop Services                ║
║  2. View System Status                 ║
║  3. Manage Memory                      ║
║  4. Run Diagnostics                    ║
║  5. Backup & Restore                   ║
║  6. View Logs                          ║
║  7. Configure System                   ║
║  8. Security Management                ║
║  9. Advanced Tools                     ║
╚════════════════════════════════════════╝
```

### Các lệnh phổ biến

**1. Start/Stop Services:**
```
Chọn 1 → Chọn action:
  1. Start All Services
  2. Stop All Services
  3. Restart All Services
  4. Check Service Status
```

**2. View System Status:**
```
Chọn 2 → Hiển thị:
  - CPU usage
  - Memory usage
  - Disk space
  - Active processes
  - Network ports
```

**3. Manage Memory:**
```
Chọn 3 → Chọn action:
  1. View all memories
  2. Add new memory
  3. Search memories
  4. Delete memory
  5. Review & approve pending memories
```

**4. Run Diagnostics:**
```
Chọn 4 → Chạy tests:
  1. Quick health check
  2. Full system test
  3. Database integrity check
  4. Cache performance test
```

**5. Backup & Restore:**
```
Chọn 5 → Chọn action:
  1. Create backup
  2. Restore from backup
  3. List backups
  4. Schedule automated backup
```

---

## 5. HƯỚNG DẪN CLI & API

### CLI Commands

```bash
# Kiểm tra trạng thái hệ thống
python tools\cli.py status

# Quản lý memory
python tools\cli.py memory add "Nội dung ghi nhớ" --type=fact
python tools\cli.py memory search "keyword"
python tools\cli.py memory list --limit=20

# Chạy diagnostics
python tools\cli.py diagnostics run

# Backup database
python tools\cli.py backup create

# View logs
python tools\cli.py logs tail --lines=50
```

### API Endpoints

#### Memory API

```http
# Create knowledge unit
POST /api/memory/knowledge-units
Content-Type: application/json
Authorization: Bearer <token>

{
  "content": "Python is a programming language",
  "type": "fact",
  "scope": "general",
  "confidence": 0.95
}

# Search knowledge
GET /api/memory/knowledge-units/search?q=python&limit=10

# Get knowledge unit
GET /api/memory/knowledge-units/{id}
```

#### Analytics API

```http
# Get metrics
GET /api/analytics/metrics

# Get trends
GET /api/analytics/trends?metric=knowledge_count&period=7d

# Generate report
POST /api/analytics/reports/generate
{
  "type": "daily_summary",
  "date": "2026-10-28",
  "format": "pdf"
}
```

#### Security API

```http
# Login
POST /api/auth/login
{
  "username": "admin",
  "password": "password"
}

# Enable MFA
POST /api/auth/mfa/enable
{
  "method": "totp"
}

# Verify MFA
POST /api/auth/mfa/verify
{
  "code": "123456"
}
```

---

## 6. QUẢN TRỊ AN TOÀN & HIẾN PHÁP R0-R5

### Hiến pháp Kiểm soát Rủi ro

**R0 - Không thể thay đổi:**
- Không được phép làm hại con người
- Không được vi phạm quyền riêng tư
- Không được truy cập dữ liệu nhạy cảm

**R1 - Chỉ đọc:**
- Chỉ đọc dữ liệu, không ghi
- Không thay đổi hệ thống

**R2 - Giới hạn phạm vi:**
- Chỉ làm việc trong workspace được cấp phép
- Không truy cập hệ thống khác

**R3 - Không tự động:**
- Không tự động thực hiện hành động
- Phải có xác nhận của chủ nhân

**R4 - Phê duyệt yêu cầu:**
- Yêu cầu phê duyệt rõ ràng
- Xác thực chủ nhân bắt buộc

**R5 - Chặn cứng:**
- KHÔNG BAO GIỜ được thực thi
- Hard-block ở code level

### Cách áp dụng

**Khi thực hiện hành động:**
1. Hệ thống tự động kiểm tra level R
2. Nếu R4/R5 → Chặn và yêu cầu phê duyệt
3. Chủ nhân xác thực → Cho phép thực hiện
4. Ghi log audit trail

**Ví dụ:**
```
User: "Xóa toàn bộ database"
System: [R5 BLOCKED] Hành động này bị chặn vĩnh viễn
User: "Xem logs"
System: [R1 OK] Hiển thị logs (chỉ đọc)
```

---

## 7. QUẢN TRỊ TRÍ NHỚ (MEMORY MANAGEMENT)

### Thêm trí nhớ mới

**Cách 1: Qua Web UI**
1. Vào Tab "Memory"
2. Click "+ Add Memory"
3. Nhập nội dung
4. Chọn type & scope
5. Click Save

**Cách 2: Qua API**
```python
import requests

response = requests.post(
    'http://localhost:8216/api/memory/knowledge-units',
    json={
        "content": "User prefers concise responses",
        "type": "preference",
        "scope": "personal",
        "confidence": 1.0
    }
)
```

**Cách 3: Qua Console**
```bash
python tools\cli.py memory add "User prefers concise responses" --type=preference
```

### Tìm kiếm trí nhớ

**Semantic search:**
```python
results = requests.get(
    'http://localhost:8216/api/memory/knowledge-units/search',
    params={"q": "user preferences", "limit": 10}
)
```

**Filter by type:**
```python
results = requests.get(
    'http://localhost:8216/api/memory/knowledge-units/search',
    params={"type": "fact", "status": "VERIFIED"}
)
```

### Review & Approve

**Quy trình:**
1. Memory mới → Status: `PENDING`
2. System tạo review session
3. Chủ nhân review findings
4. Approve → Status: `VERIFIED`
5. Reject → Status: `REJECTED`

**Via Web UI:**
1. Vào Tab "Review"
2. Xem pending memories
3. Click "Approve" hoặc "Reject"
4. Add comment (optional)

---

## 8. QUẢN TRỊ ĐỘNG CƠ TỰ HỌC

### Self-Learning Engine

**Cơ chế hoạt động:**
1. **Monitor**: Theo dõi feedback & usage patterns
2. **Extract**: Trích xuất patterns từ data
3. **Propose**: Đề xuất cải tiến
4. **Validate**: Test trong sandbox
5. **Apply**: Áp dụng nếu pass
6. **Verify**: Monitor impact

### Phê duyệt bản vá

**Quy trình:**
```
1. System phát hiện issue
2. Tự động tạo patch proposal
3. Chạy tests trong sandbox
4. Tạo báo cáo impact
5. Gửi yêu cầu phê duyệt đến chủ nhân
6. Chủ nhân review & approve/reject
7. Nếu approve → Deploy production
8. Monitor & rollback nếu cần
```

**Via Web UI:**
1. Vào Tab "Learning"
2. Xem pending patches
3. Review changes & test results
4. Click "Approve" hoặc "Reject"
5. Add comment

---

## 9. XỬ LÝ SỰ CỐ (TROUBLESHOOTING)

### Sự cố thường gặp

#### 1. Services không start

**Triệu chứng:**
```
Error: Port 8216 already in use
```

**Giải pháp:**
```bash
# Check process using port
netstat -ano | findstr :8216

# Kill process
taskkill /F /PID <process_id>

# Restart services
.\tools\start_production.bat
```

#### 2. Database connection failed

**Triệu chứng:**
```
Error: Cannot connect to database
```

**Giải pháp:**
```bash
# Check PostgreSQL service
net status postgresql

# Start service
net start postgresql-x64-14

# Verify connection
python tools\cli.py db test-connection
```

#### 3. Redis not responding

**Triệu chứng:**
```
Error: Redis connection refused
```

**Giải pháp:**
```bash
# Check Redis service
net status redis

# Start Redis
net start redis

# Test connection
redis-cli ping
# Should return: PONG
```

#### 4. High memory usage

**Triệu chứng:**
```
Warning: Memory usage > 80%
```

**Giải pháp:**
```bash
# Check memory usage
python tools\cli.py diagnostics memory

# Restart services
.\tools\stop_services.bat
.\tools\start_production.bat

# Enable memory profiling
python -m memory_profiler tools\server.py
```

#### 5. Slow API responses

**Triệu chứng:**
```
P95 latency > 1s
```

**Giải pháp:**
```bash
# Check slow queries
python tools\cli.py db query-slow

# Add indexes
python tools\cli.py db optimize

# Enable caching
python tools\cli.py cache warm-up

# Check system resources
python tools\cli.py status
```

### Log files

**Vị trí log:**
- Application: `logs\app.log`
- Access: `logs\access.log`
- Error: `logs\error.log`
- Database: `logs\db.log`
- Security: `logs\security.log`

**Xem logs:**
```bash
# Tail logs
tail -f logs\app.log

# Search errors
grep -i "error" logs\app.log

# View last 100 lines
type logs\app.log | more
```

---

## 10. MONITORING & ANALYTICS

### Dashboard Metrics

**Real-time metrics:**
- API response time (P50, P95, P99)
- Request rate (req/s)
- Error rate (%)
- Database query time
- Cache hit rate
- Memory usage
- CPU usage
- Active connections

**Access Dashboard:**
```
http://localhost:8765/analytics
```

### Prometheus Metrics

**Endpoint:** `http://localhost:8216/metrics`

**Key metrics:**
```
quanai_requests_total{method,endpoint,status}
quanai_request_duration_seconds{endpoint}
quanai_active_connections
quanai_memory_usage_bytes
quanai_database_queries_total
```

### Grafana Dashboards

**Access:** `http://localhost:3000`

**Default dashboards:**
- System Overview
- API Performance
- Database Health
- Cache Performance
- Security Alerts

### Alert Rules

**Config:** `config\alert_rules.yml`

**Example rules:**
```yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status="500"}[5m]) > 0.01
  for: 5m
  severity: critical

- alert: HighLatency
  expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 1
  for: 10m
  severity: warning

- alert: ServiceDown
  expr: up{job="quanai"} == 0
  for: 1m
  severity: critical
```

---

## 11. BACKUP & DISASTER RECOVERY

### Automated Backup

**Schedule:** Daily at 2:00 AM

**Backup includes:**
- Database (brain.db)
- Configuration files
- Logs (optional)
- Uploads (optional)

**Create manual backup:**
```bash
python tools\cli.py backup create --name=manual_backup_20261028
```

**Backup location:**
```
E:\AI\QUAN AI BRAIN\backups\
├── 20261028_020000/
│   ├── database.sql.gz
│   ├── config.zip
│   └── manifest.json
└── 20261029_020000/
    └── ...
```

### Restore from backup

**Via CLI:**
```bash
python tools\cli.py backup restore --backup=20261028_020000
```

**Via Web UI:**
1. Vào Tab "Settings"
2. Scroll to "Backup & Restore"
3. Chọn backup từ danh sách
4. Click "Restore"
5. Confirm

### Disaster Recovery Plan

**RTO (Recovery Time Objective):** < 15 minutes  
**RPO (Recovery Point Objective):** < 5 minutes

**Steps:**
1. Stop services
2. Restore database from latest backup
3. Restore configuration
4. Start services
5. Verify health checks
6. Monitor for 1 hour

---

## 12. ENTERPRISE INTEGRATION

### API Gateway

**Configuration:** `config\gateway.yml`

**Features:**
- Rate limiting (1000 req/hour per user)
- Response caching (TTL 300s)
- Authentication proxy
- Request transformation
- Circuit breakers

**Example config:**
```yaml
routes:
  - path: /api/v1/*
    upstream: http://backend:8216
    rate_limit: 1000/hour
    cache:
      enabled: true
      ttl: 300
    auth:
      type: jwt
      required: true
```

### Enterprise Connectors

**Supported connectors:**
- Salesforce
- Microsoft 365
- Slack
- Teams
- SAP
- Oracle

**Configure connector:**
```bash
python tools\cli.py connector connect salesforce \
  --client-id=xxx \
  --client-secret=xxx \
  --callback-url=https://quanai.company.com/callback
```

**Sync data:**
```bash
python tools\cli.py connector sync salesforce \
  --objects=Account,Contact,Opportunity \
  --mode=incremental
```

### Webhooks

**Register webhook:**
```python
import requests

webhook = requests.post(
    'http://localhost:8216/api/webhooks',
    json={
        "url": "https://partner.com/webhook",
        "events": ["knowledge.created", "knowledge.updated"],
        "secret": "webhook-secret-key"
    }
)
```

**Webhook payload:**
```json
{
  "event": "knowledge.created",
  "timestamp": "2026-10-28T10:00:00Z",
  "data": {"id": "uuid", "type": "fact", ...},
  "signature": "hmac-sha256-signature"
}
```

---

## 13. MOBILE APP USAGE

### Installation

**iOS:**
1. Open App Store
2. Search "QUAN AI BRAIN"
3. Download & install
4. Open app

**Android:**
1. Open Google Play
2. Search "QUAN AI BRAIN"
3. Download & install
4. Open app

### First-time setup

1. **Login:**
   - Enter username/email
   - Enter password
   - Complete MFA (if enabled)

2. **Configure sync:**
   - Enable auto-sync
   - Set sync interval (5min default)
   - Choose sync mode (Wi-Fi only / Any network)

3. **Customize notifications:**
   - Enable/disable notifications
   - Set quiet hours
   - Choose notification sound

### Features

**Knowledge Browser:**
- Search knowledge units
- Filter by type, status, scope
- View details & metadata
- Bookmark favorites

**Voice Commands:**
- Hold microphone button
- Speak command
- Release to send

**Offline Mode:**
- Access cached knowledge
- Queue operations
- Auto-sync when online

**Real-time Updates:**
- Live search results
- Push notifications
- Sync status indicator

---

## 14. SECURITY BEST PRACTICES

### Password Policy

**Requirements:**
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character

**Change password:**
```bash
python tools\cli.py auth change-password
```

### MFA Setup

**TOTP (Google Authenticator):**
1. Vào Settings → Security
2. Click "Enable MFA"
3. Chọn "TOTP"
4. Scan QR code với app
5. Enter 6-digit code để verify

**SMS:**
1. Vào Settings → Security
2. Click "Enable MFA"
3. Chọn "SMS"
4. Enter phone number
5. Enter verification code

### Session Management

**View active sessions:**
```
Settings → Security → Active Sessions
```

**Revoke session:**
1. Chọn session
2. Click "Revoke"
3. Confirm

**Session timeout:**
- Default: 24 hours
- Configurable in `.env`: `SESSION_TIMEOUT=86400`

### Audit Log

**View audit logs:**
```
Settings → Security → Audit Logs
```

**Filter logs:**
- By user
- By action
- By date range
- By severity

**Export logs:**
```bash
python tools\cli.py audit export --format=csv --output=audit_report.csv
```

### Security Checklist

**Daily:**
- [ ] Check security alerts
- [ ] Review failed login attempts
- [ ] Monitor unusual activity

**Weekly:**
- [ ] Review user access
- [ ] Check audit logs
- [ ] Update passwords (if needed)

**Monthly:**
- [ ] Security audit
- [ ] Review permissions
- [ ] Update dependencies
- [ ] Test backup restore

---

## PHỤ LỤC A: LỆNH CLI THAM KHẢO

### System Management
```bash
python tools\cli.py status
python tools\cli.py restart
python tools\cli.py diagnostics run
```

### Memory Management
```bash
python tools\cli.py memory add "content" --type=fact
python tools\cli.py memory search "keyword"
python tools\cli.py memory list --limit=20
python tools\cli.py memory delete <id>
```

### Backup & Restore
```bash
python tools\cli.py backup create --name=backup_20261028
python tools\cli.py backup restore --backup=backup_20261028
python tools\cli.py backup list
```

### Security
```bash
python tools\cli.py auth change-password
python tools\cli.py audit export --format=csv
python tools\cli.py security scan
```

---

## PHỤ LỤC B: TÀI NGUYÊN HỖ TRỢ

### Documentation
- **Functional Specifications:** `docs\FUNCTIONAL_SPECIFICATIONS.md`
- **Production Deployment:** `docs\PRODUCTION_DEPLOYMENT.md`
- **API Reference:** `docs\OPENAPI_SPEC.yaml`

### Support Channels
- **Email:** quanpt1@viettel.com.vn
- **Slack:** #quanai-support
- **GitHub:** https://github.com/thequanhcm/quanpt1/issues

### Emergency Contacts
- **DevOps Lead:** Quân PT
- **Security Lead:** [TBD]
- **On-Call:** [TBD]

---

**Document Version:** V30.0  
**Last Updated:** 2026-10-28  
**Maintained By:** QUAN AI BRAIN Team  
**Classification:** Internal Use Only