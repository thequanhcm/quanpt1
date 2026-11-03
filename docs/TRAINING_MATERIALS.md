# QUAN AI BRAIN - Training Materials
**Version:** V22.0  
**Last Updated:** 2024-10-28

---

## Table of Contents
1. [User Training](#1-user-training)
2. [Administrator Training](#2-administrator-training)
3. [Developer Training](#3-developer-training)
4. [Quick Start Guides](#4-quick-start-guides)
5. [FAQ](#5-faq)
6. [Resources](#6-resources)

---

## 1. User Training

### 1.1 Overview
**Target Audience:** End users, business analysts, content managers  
**Duration:** 2 hours  
**Prerequisites:** None

### 1.2 What is QUAN AI BRAIN?
QUAN AI BRAIN là hệ thống trí nhớ AI với các khả năng:
- **Lưu trữ tri thức**: Ghi nhớ thông tin, sự kiện, kinh nghiệm
- **Tìm kiếm ngữ cảnh**: Tìm thông tin liên quan tự động
- **Suy luận**: Phát hiện mối quan hệ, mâu thuẫn, nguyên nhân
- **Học hỏi**: Cải thiện theo thời gian dựa trên phản hồi
- **Đa modal**: Kết hợp văn bản, code, tài liệu, cuộc họp

### 1.3 Core Features

#### Feature 1: Tìm kiếm Tri thức
**Cách sử dụng:**
```bash
# Tìm kiếm đơn giản
GET /v1/memory/search?q=production+deployment

# Tìm theo phạm vi
GET /v1/memory/search?scope=production&limit=20

# Tìm theo loại
GET /v1/memory/search?knowledge_type=FACT&status=VERIFIED
```

**Ví dụ thực tế:**
- "Tìm các kinh nghiệm triển khai production"
- "Tìm các lỗi đã gặp trong dự án X"
- "Tìm các best practices về security"

#### Feature 2: Thêm Tri thức Mới
**Cách sử dụng:**
```bash
POST /v1/memory/write
{
  "knowledge_type": "FACT",
  "subject": "Production",
  "predicate": "requires",
  "object": "testing",
  "statement": "Production deployment requires thorough testing"
}
```

**Khi nào thêm tri thức:**
- Kinh nghiệm mới học được
- Bài học từ sự cố
- Best practices mới
- Quy trình mới

#### Feature 3: Tìm kiếm theo Ngữ cảnh
**Cách sử dụng:**
```bash
# Đặt ngữ cảnh
POST /v1/memory/context/set
{
  "project": "QUAN-AI",
  "task": "deployment",
  "user": "quanpt1"
}

# Tìm theo ngữ cảnh hiện tại
GET /v1/memory/retrieve/contextual
```

**Lợi ích:**
- Tự động tìm thông tin liên quan đến công việc hiện tại
- Giảm thời gian tìm kiếm
- Tăng độ chính xác

#### Feature 4: Xem Lịch sử & Timeline
**Cách sử dụng:**
```bash
# Xem timeline tri thức
GET /v1/memory/temporal/timeline?days=30

# Xem tri thức mới nhất
GET /v1/memory/temporal/recent?limit=10

# Xem tri thức cũ cần review
GET /v1/memory/temporal/stale?days=90
```

### 1.4 Best Practices

#### Khi thêm tri thức:
1. **Rõ ràng**: Statement phải dễ hiểu
2. **Đầy đủ**: Bao gồm context cần thiết
3. **Chính xác**: Kiểm tra thông tin trước khi lưu
4. **Có cấu trúc**: Sử dụng đúng knowledge_type
5. **Có verification**: Đánh dấu VERIFIED khi đã kiểm chứng

#### Khi tìm kiếm:
1. **Sử dụng từ khóa cụ thể**: "production deployment" tốt hơn "deployment"
2. **Lọc theo scope**: Giới hạn phạm vi tìm kiếm
3. **Kiểm tra confidence**: Ưu tiên tri thức có confidence cao
4. **Xem version**: Kiểm tra version của tri thức
5. **Đóng góp phản hồi**: Giúp hệ thống học hỏi

### 1.5 Common Use Cases

#### Use Case 1: Troubleshooting
```
1. Tìm các lỗi tương tự: search?q=error+database+connection
2. Xem các giải pháp đã từng áp dụng: search?q=database+fix
3. Thêm kinh nghiệm mới: write với type=LESSON_LEARNED
```

#### Use Case 2: Onboarding
```
1. Tìm tài liệu dự án: search?scope=project+X&knowledge_type=DOCUMENT
2. Xem quy trình: search?knowledge_type=PROCESS
3. Tìm best practices: search?knowledge_type=BEST_PRACTICE
```

#### Use Case 3: Knowledge Review
```
1. Xem tri thức cũ: temporal/stale?days=90
2. Kiểm tra độ chính xác
3. Cập nhật hoặc đánh dấu obsolete
```

---

## 2. Administrator Training

### 2.1 Overview
**Target Audience:** System administrators, DevOps engineers  
**Duration:** 4 hours  
**Prerequisites:** Linux, Docker, basic networking

### 2.2 System Architecture
```
┌─────────────────────────────────────────────┐
│              Load Balancer                  │
└─────────────────┬───────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼───┐   ┌────▼────┐   ┌───▼───┐
│  App  │   │   App   │   │  App  │
│ Server│   │ Server  │   │ Server│
└───┬───┘   └────┬────┘   └───┬───┘
    │             │             │
    └─────────────┼─────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼───┐   ┌────▼────┐   ┌───▼───┐
│PostgreSQL│  │ Redis  │   │Prometheus│
└────────┘   └────────┘   └─────────┘
```

### 2.3 Installation & Setup

#### Step 1: Prerequisites
```bash
# Check system requirements
docker --version  # 20.10+
docker-compose --version  # 2.0+
free -h  # 8GB+ RAM
df -h  # 50GB+ disk
```

#### Step 2: Clone & Configure
```bash
git clone https://github.com/thequanhcm/quanpt1.git
cd quanpt1

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

#### Step 3: Start Services
```bash
# Development
docker-compose up -d

# Production
APP_ENV=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check status
docker-compose ps
```

### 2.4 Monitoring & Maintenance

#### Daily Tasks
```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs --tail=100 quan-ai-brain

# Check disk space
df -h

# Check memory
docker stats --no-stream
```

#### Weekly Tasks
```bash
# Run database vacuum
docker exec quan-ai-postgres psql -U quanai -c "VACUUM ANALYZE;"

# Check for slow queries
docker exec quan-ai-postgres psql -U quanai -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Review error logs
docker-compose logs quan-ai-brain | grep -i error

# Check backup status
ls -lh /backups/
```

#### Monthly Tasks
```bash
# Run full backup
docker exec quan-ai-postgres pg_dump -U quanai quan_ai_brain | gzip > /backups/full_$(date +%Y%m%d).sql.gz

# Test restore
gunzip < /backups/full_*.sql.gz | docker exec -i quan-ai-postgres psql -U quanai

# Review performance metrics
# Check Grafana dashboard: http://localhost:3000

# Update system packages
docker-compose pull
docker-compose up -d
```

### 2.5 Troubleshooting

#### Issue: Service won't start
```bash
# Check logs
docker-compose logs quan-ai-brain

# Check port conflicts
netstat -tulpn | grep 8080

# Check resource limits
docker stats --no-stream
```

#### Issue: Database connection failed
```bash
# Check database status
docker exec quan-ai-postgres pg_isready -U quanai

# Check connection pool
docker exec quan-ai-postgres psql -U quanai -c "SELECT count(*) FROM pg_stat_activity;"

# Restart database
docker-compose restart postgres
```

#### Issue: High memory usage
```bash
# Check memory usage
docker stats --no-stream

# Identify memory hogs
docker exec quan-ai-brain ps aux --sort=-%mem

# Restart with more memory
# Edit docker-compose.yml
# deploy:
#   resources:
#     limits:
#       memory: 16G
```

### 2.6 Backup & Recovery

#### Backup Strategy
```bash
# Daily incremental backup (cron)
0 2 * * * /path/to/backup.sh

# Weekly full backup (cron)
0 3 * * 0 /path/to/full_backup.sh

# Upload to S3
aws s3 sync /backups s3://your-bucket/backups
```

#### Recovery Procedure
```bash
# Stop services
docker-compose down

# Restore database
gunzip < backup.sql.gz | docker exec -i quan-ai-postgres psql -U quanai

# Restore application data
rsync -av backup/data/ /app/data/

# Start services
docker-compose up -d

# Verify
curl http://localhost:8080/v1/memory/health
```

---

## 3. Developer Training

### 3.1 Overview
**Target Audience:** Developers, engineers  
**Duration:** 6 hours  
**Prerequisites:** Python 3.11+, PostgreSQL, REST APIs

### 3.2 Development Environment Setup

#### Step 1: Clone Repository
```bash
git clone https://github.com/thequanhcm/quanpt1.git
cd quanpt1
git checkout feature/cognitive-state-integration
```

#### Step 2: Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate  # Windows
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### Step 4: Setup Database
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Create database
docker exec quan-ai-postgres psql -U postgres -c "CREATE DATABASE quan_ai_brain;"
docker exec quan-ai-postgres psql -U postgres -c "CREATE USER quanai WITH PASSWORD 'password';"
docker exec quan-ai-postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE quan_ai_brain TO quanai;"

# Run migrations
python -m quan_ai_brain.db.migrate
```

#### Step 5: Run Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_v11_temporal_memory.py -v

# Run with coverage
pytest --cov=quan_ai_brain --cov-report=html
```

### 3.3 API Development

#### Adding New Endpoint
```python
# src/quan_ai_brain/web/server.py
@app.route('/v1/memory/custom-action', methods=['POST'])
@require_auth
@rate_limit(100)
def custom_action():
    data = request.get_json()
    
    # Validate input
    if not validate_input(data):
        return jsonify({'error': 'Invalid input'}), 400
    
    # Process
    result = process_custom_action(data)
    
    return jsonify(result), 200
```

#### Writing Tests
```python
# tests/test_custom_action.py
def test_custom_action():
    # Setup
    response = client.post('/v1/memory/custom-action',
                          json={'key': 'value'},
                          headers={'Authorization': f'Bearer {TEST_TOKEN}'})
    
    # Assert
    assert response.status_code == 200
    assert 'result' in response.json
```

### 3.4 Module Development

#### Creating New Memory Module
```python
# src/quan_ai_brain/memory/new_module.py
from .base import MemoryModule

class NewMemoryModule(MemoryModule):
    def __init__(self, db_connection):
        super().__init__(db_connection)
        self.name = "new_module"
    
    def add(self, data: dict) -> str:
        """Add new memory"""
        # Implementation
        pass
    
    def search(self, query: str) -> list:
        """Search memories"""
        # Implementation
        pass
    
    def update(self, memory_id: str, data: dict) -> bool:
        """Update memory"""
        # Implementation
        pass
    
    def delete(self, memory_id: str) -> bool:
        """Delete memory"""
        # Implementation
        pass
```

### 3.5 Code Quality

#### Linting
```bash
# Run flake8
flake8 src/ tests/

# Run black
black src/ tests/

# Run isort
isort src/ tests/
```

#### Type Checking
```bash
# Run mypy
mypy src/
```

#### Security Scan
```bash
# Run bandit
bandit -r src/

# Run safety
safety check
```

---

## 4. Quick Start Guides

### 4.1 Quick Start for Users (5 minutes)
```bash
# 1. Access the system
curl http://localhost:8080/v1/memory/health

# 2. Add your first knowledge unit
curl -X POST http://localhost:8080/v1/memory/write \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_type": "FACT",
    "subject": "QuickStart",
    "predicate": "is",
    "object": "easy",
    "statement": "QUAN AI BRAIN is easy to use"
  }'

# 3. Search for it
curl "http://localhost:8080/v1/memory/search?q=QUAN+AI+BRAIN"

# 4. Done!
```

### 4.2 Quick Start for Admins (15 minutes)
```bash
# 1. Clone repository
git clone https://github.com/thequanhcm/quanpt1.git
cd quanpt1

# 2. Copy environment file
cp .env.example .env

# 3. Start services
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. Access monitoring
open http://localhost:3000  # Grafana
open http://localhost:9090  # Prometheus

# 6. Done!
```

### 4.3 Quick Start for Developers (30 minutes)
```bash
# 1. Clone and setup
git clone https://github.com/thequanhcm/quanpt1.git
cd quanpt1
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Start services
docker-compose up -d postgres redis

# 3. Run migrations
python -m quan_ai_brain.db.migrate

# 4. Run tests
pytest

# 5. Start development server
python -m quan_ai_brain.web.server

# 6. Done!
```

---

## 5. FAQ

### General Questions

**Q: What is QUAN AI BRAIN?**  
A: QUAN AI BRAIN is an AI-powered memory system that helps you store, retrieve, and learn from your knowledge and experiences.

**Q: How is it different from a regular database?**  
A: It understands context, finds relationships, learns from feedback, and provides intelligent retrieval based on your current needs.

**Q: Is my data secure?**  
A: Yes, all data is encrypted at rest and in transit. Access is controlled via authentication and authorization.

### Technical Questions

**Q: What databases does it use?**  
A: PostgreSQL for structured data, Redis for caching, and optional vector databases for semantic search.

**Q: Can I run it on-premise?**  
A: Yes, it's designed to run on-premise or in your own cloud infrastructure.

**Q: How do I backup my data?**  
A: Use the built-in backup scripts or the Docker volume backup method. See docs/BACKUP_RECOVERY.md.

**Q: Can I integrate with other systems?**  
A: Yes, it provides REST APIs and webhooks for integration. See docs/API_REFERENCE.md.

### Troubleshooting

**Q: Why is the system slow?**  
A: Check cache hit rate, database indexes, and resource usage. See docs/PERFORMANCE_TUNING.md.

**Q: How do I reset the system?**  
A: Stop all services, drop the database, and restart. WARNING: This will delete all data.

**Q: Where are the logs?**  
A: Logs are in `/app/logs/` or use `docker-compose logs`.

---

## 6. Resources

### Documentation
- **User Guide**: docs/USER_GUIDE.md
- **Admin Guide**: docs/ADMIN_GUIDE.md
- **API Reference**: docs/openapi_spec.yaml
- **Deployment Guide**: docs/DEPLOYMENT_GUIDE.md
- **Performance Tuning**: docs/PERFORMANCE_TUNING.md

### Training Videos
- [Introduction to QUAN AI BRAIN](https://training.quan-ai-brain.vn/intro)
- [User Training](https://training.quan-ai-brain.vn/user)
- [Admin Training](https://training.quan-ai-brain.vn/admin)
- [Developer Training](https://training.quan-ai-brain.vn/developer)

### Support
- **Email**: quanpt1@viettel.com.vn
- **Slack**: #quan-ai-brain
- **Issue Tracker**: https://github.com/thequanhcm/quanpt1/issues
- **Documentation**: https://docs.quan-ai-brain.vn

### Community
- **GitHub**: https://github.com/thequanhcm/quanpt1
- **Discussions**: https://github.com/thequanhcm/quanpt1/discussions
- **Roadmap**: https://github.com/thequanhcm/quanpt1/projects

---

**Document Version:** V22.0  
**Last Updated:** 2024-10-28  
**Next Update:** 2025-01-28