# QUAN AI BRAIN - PRODUCTION DEPLOYMENT PACKAGE
**Version:** V30.0-Production  
**Date:** 2026-10-28  
**Status:** READY FOR DEPLOYMENT

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Architecture Overview](#architecture-overview)
4. [Deployment Steps](#deployment-steps)
5. [Configuration](#configuration)
6. [Monitoring & Health Checks](#monitoring--health-checks)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedures](#rollback-procedures)
10. [Performance Tuning](#performance-tuning)

---

## Quick Start

### 1-Click Production Deploy (Windows)

```powershell
# Run as Administrator
.\deploy\production_deploy.ps1
```

### Manual Deploy (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/thequanhcm/quanpt1.git
cd quanpt1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Run database migrations
python tools/run_migrations.py

# 5. Start services
.\tools\start_production.bat

# 6. Verify deployment
curl http://localhost:8216/api/health
```

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk | 50 GB SSD | 100+ GB NVMe |
| Network | 100 Mbps | 1 Gbps |
| OS | Windows 10 / Server 2019 | Windows Server 2022 |

### Software Dependencies

- **Python:** 3.10+
- **PostgreSQL:** 14+ (or SQLite for small scale)
- **Redis:** 7+ (caching & sessions)
- **NGINX:** 1.20+ (reverse proxy)
- **Docker:** 20+ (optional, for containerized deploy)

### Network Ports

| Service | Port | Protocol |
|---------|------|----------|
| API Server | 8216 | HTTP/HTTPS |
| Responder | 18036 | HTTP |
| Watchdog | 17236 | HTTP |
| Learning Daemon | 7724 | HTTP |
| Dashboard | 8765 | HTTP |
| Core | 8766 | HTTP |
| Redis | 6379 | TCP |
| PostgreSQL | 5432 | TCP |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     LOAD BALANCER (NGINX)                    │
│                    Port 80/443 (HTTPS)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Server     │ │  Responder   │ │   Learning   │
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
│  (Cache)    │  │   (DB)      │  │  (17236)    │
└─────────────┘  └─────────────┘  └─────────────┘
```

### Component Descriptions

| Component | Purpose | Scale |
|-----------|---------|-------|
| **Server** | Main API, business logic | 2-10 instances |
| **Responder** | NetChat bot, real-time replies | 1-3 instances |
| **Learning** | Background learning, updates | 1-2 instances |
| **Watchdog** | Health monitoring, auto-restart | 1 instance |
| **Dashboard** | Admin UI, monitoring | 1 instance |
| **Redis** | Caching, sessions, queues | 1-3 nodes |
| **PostgreSQL** | Primary database | 1 primary + replicas |

---

## Deployment Steps

### Step 1: Prepare Production Server

```powershell
# Windows Server - Run as Administrator

# 1. Install Python 3.10+
winget install Python.Python.3.10

# 2. Install Git
winget install Git.Git

# 3. Install Redis
# Download from: https://github.com/microsoftarchive/redis/releases
# Or use Docker: docker run -d -p 6379:6379 redis:7

# 4. Install PostgreSQL
winget install PostgreSQL.PostgreSQL.14

# 5. Create deployment user
net user quanai P@ssw0rd123 /add /y
net localgroup Administrators quanai /add
```

### Step 2: Clone & Setup

```bash
# Login as quanai
cd C:\
git clone https://github.com/thequanhcm/quanpt1.git
cd quanpt1

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-prod.txt
```

### Step 3: Configure Environment

```bash
# Copy environment template
copy .env.example .env

# Edit .env with production values
# Key settings:
# - DATABASE_URL=postgresql://user:pass@localhost:5432/quanai
# - REDIS_URL=redis://localhost:6379/0
# - SECRET_KEY=<generate-random-32-char>
# - DEBUG=false
# - LOG_LEVEL=INFO
# - API_RATE_LIMIT=1000
```

### Step 4: Database Setup

```bash
# Run migrations
python tools/run_migrations.py

# Initialize database
python tools/init_production_db.py

# Create admin user
python tools/create_admin.py --username admin --email admin@company.com
```

### Step 5: Start Services

```bash
# Option 1: Use batch script (recommended)
.\tools\start_production.bat

# Option 2: Start individually
start /b .\.venv\Scripts\python.exe tools/server.py
start /b .\.venv\Scripts\python.exe tools/netchat_auto_responder.py
start /b .\.venv\Scripts\python.exe tools/learning_daemon.py
start /b .\.venv\Scripts\python.exe tools/watchdog.py

# Option 3: Use Windows Service (advanced)
.\deploy\install_as_service.ps1
```

### Step 6: Configure NGINX

```nginx
# /etc/nginx/sites-available/quanai
upstream quanai_backend {
    server 127.0.0.1:8216;
    server 127.0.0.1:8217;  # if multiple instances
    keepalive 32;
}

server {
    listen 80;
    server_name quanai.company.com;
    
    location / {
        proxy_pass http://quanai_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files
    location /static {
        alias C:/quanai/web/static;
        expires 30d;
    }
}
```

### Step 7: SSL/TLS Setup

```bash
# Using Let's Encrypt (certbot)
certbot --nginx -d quanai.company.com

# Or manual certificate
# Place cert.pem and key.pem in C:/quanai/certs/
```

### Step 8: Verify Deployment

```bash
# Health checks
curl http://localhost:8216/api/health
curl http://localhost:8765/api/health
curl http://localhost:18036/api/health

# Check all services
python tools/verify_production.py

# Run smoke tests
pytest tests/smoke_tests/ -v
```

---

## Configuration

### Environment Variables (.env)

```bash
# === DATABASE ===
DATABASE_URL=postgresql://quanai:secure_password@localhost:5432/quanai
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# === REDIS ===
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# === SECURITY ===
SECRET_KEY=your-32-character-random-secret-key-here
JWT_SECRET=another-random-secret-for-jwt-tokens
ENCRYPTION_KEY=32-byte-encryption-key-base64

# === API ===
API_RATE_LIMIT=1000
API_MAX_REQUEST_SIZE=10485760
CORS_ORIGINS=https://quanai.company.com

# === LOGGING ===
LOG_LEVEL=INFO
LOG_FILE=/var/log/quanai/app.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5

# === OLLAMA/LLM ===
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b
EMBEDDING_MODEL=bge-m3

# === NETCHAT ===
NETCHAT_API_URL=https://api.netchat.company.com
NETCHAT_CHANNEL_ID=your-channel-id
NETCHAT_BOT_TOKEN=your-bot-token

# === MONITORING ===
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
SENTRY_DSN=https://your-sentry-dsn

# === FEATURE FLAGS ===
ENABLE_FEDERATED_LEARNING=true
ENABLE_AUTO_TUNING=true
ENABLE_ANALYTICS=true
```

### Production Settings (config.py)

```python
# config/production.py

class ProductionConfig:
    # Environment
    ENV = "production"
    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_POOL_SIZE = 20
    SQLALCHEMY_MAX_OVERFLOW = 10
    SQLALCHEMY_POOL_RECYCLE = 3600
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL")
    CACHE_TYPE = "redis"
    CACHE_DEFAULT_TIMEOUT = 3600
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET")
    SECURITY_PASSWORD_SALT = os.getenv("SECURITY_SALT")
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "1000/hour"
    RATELIMIT_STORAGE_URL = "redis://localhost:6379/1"
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "/var/log/quanai/app.log"
    
    # Monitoring
    PROMETHEUS_ENABLED = True
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    
    # Features
    ENABLE_ANALYTICS = True
    ENABLE_AUTO_TUNING = True
    ENABLE_FEDERATED_LEARNING = True
```

---

## Monitoring & Health Checks

### Health Check Endpoints

```bash
# Main API health
GET /api/health
Response: {"status": "healthy", "version": "30.0", "uptime": 86400}

# Database health
GET /api/health/db
Response: {"status": "healthy", "latency_ms": 5}

# Redis health
GET /api/health/redis
Response: {"status": "healthy", "connected_clients": 10}

# Full system health
GET /api/health/full
Response: {
    "status": "healthy",
    "components": {
        "api": "healthy",
        "database": "healthy",
        "redis": "healthy",
        "responder": "healthy",
        "learning": "healthy"
    }
}
```

### Monitoring Dashboard

Access: http://localhost:8765

**Metrics Tracked:**
- API response time (P50, P95, P99)
- Request rate (req/s)
- Error rate (%)
- Database query time
- Cache hit rate
- Memory usage
- CPU usage
- Active connections

### Prometheus Metrics

```bash
# Export metrics endpoint
GET /metrics

# Key metrics:
# - quanai_requests_total{method,endpoint,status}
# - quanai_request_duration_seconds{endpoint}
# - quanai_active_connections
# - quanai_memory_usage_bytes
# - quanai_database_queries_total
```

### Alert Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: quanai
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status="500"}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected (P95 > 1s)"
          
      - alert: ServiceDown
        expr: up{job="quanai"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
```

---

## Backup & Recovery

### Automated Backup Script

```bash
# deploy/backup.sh
#!/bin/bash

# Configuration
BACKUP_DIR="/backup/quanai"
DB_NAME="quanai"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U quanai $DB_NAME | gzip > $BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql.gz

# File backup
tar -czf $BACKUP_DIR/files_$(date +%Y%m%d_%H%M%S).tar.gz /var/lib/quanai

# Cleanup old backups
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete

# Log
echo "$(date): Backup completed" >> /var/log/quanai/backup.log
```

### Restore Procedure

```bash
# 1. Stop services
.\tools\stop_services.bat

# 2. Restore database
gunzip < db_backup.sql.gz | psql -U quanai quanai

# 3. Restore files
tar -xzf files_backup.tar.gz -C /var/lib/quanai

# 4. Start services
.\tools\start_production.bat

# 5. Verify
curl http://localhost:8216/api/health
```

### Disaster Recovery Plan

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Single server failure | 5 min | 0 | Failover to replica |
| Database failure | 15 min | 5 min | Restore from backup |
| Complete datacenter loss | 1 hour | 15 min | DR site activation |
| Ransomware attack | 4 hours | 24 hours | Full restore from backup |

---

## Troubleshooting

### Common Issues

#### 1. High Memory Usage

```bash
# Check memory
python tools/check_memory.py

# Restart service
taskkill /F /PID <process_id>
start .\.venv\Scripts\python.exe tools/server.py

# Enable memory profiling
python -m memory_profiler tools/server.py
```

#### 2. Database Connection Pool Exhausted

```python
# Increase pool size in config
DATABASE_POOL_SIZE = 50
DATABASE_MAX_OVERFLOW = 25

# Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'quanai';
```

#### 3. Slow API Responses

```bash
# Enable query logging
LOG_QUERIES = True

# Check slow queries
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

# Add indexes
CREATE INDEX CONCURRENTLY ON knowledge_units(created_at);
```

#### 4. Redis Connection Failed

```bash
# Check Redis status
redis-cli ping
# Should return: PONG

# Restart Redis
net stop Redis
net start Redis

# Check Redis config
redis-cli CONFIG GET maxmemory
```

### Log Files

| Log | Location | Purpose |
|-----|----------|---------|
| Application | C:/quanai/logs/app.log | Main application logs |
| Access | C:/quanai/logs/access.log | HTTP access logs |
| Error | C:/quanai/logs/error.log | Error logs |
| Database | C:/quanai/logs/db.log | Database queries |
| Security | C:/quanai/logs/security.log | Auth & security events |

### Debug Mode

```bash
# Enable debug mode
set DEBUG=true
set LOG_LEVEL=DEBUG

# Restart services
.\tools\restart_services.bat

# Check debug endpoint
curl http://localhost:8216/api/debug/status
```

---

## Rollback Procedures

### Quick Rollback (Last Version)

```bash
# 1. Stop services
.\tools\stop_services.bat

# 2. Revert git
git reset --hard HEAD~1
git pull origin master

# 3. Restore database (if needed)
.\deploy\restore_backup.bat latest

# 4. Restart services
.\tools\start_production.bat

# 5. Verify
curl http://localhost:8216/api/health
```

### Full Rollback (Specific Version)

```bash
# 1. Stop services
.\tools\stop_services.bat

# 2. Checkout version
git checkout v29.0.0

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations (rollback)
python tools/run_migrations.py --rollback

# 5. Restore database
.\deploy\restore_backup.bat v29.0.0

# 6. Restart services
.\tools\start_production.bat
```

### Rollback Checklist

- [ ] Stop all services
- [ ] Backup current version
- [ ] Revert code to previous version
- [ ] Rollback database migrations
- [ ] Restore database from backup
- [ ] Restart services
- [ ] Verify health checks
- [ ] Run smoke tests
- [ ] Monitor for 1 hour
- [ ] Document rollback reason

---

## Performance Tuning

### Database Optimization

```sql
-- Create indexes
CREATE INDEX CONCURRENTLY idx_ku_status ON knowledge_units(status);
CREATE INDEX CONCURRENTLY idx_ku_type ON knowledge_units(type);
CREATE INDEX CONCURRENTLY idx_ku_created ON knowledge_units(created_at);

-- Analyze tables
ANALYZE knowledge_units;
ANALYZE relations;

-- Vacuum
VACUUM ANALYZE;

-- Check query plan
EXPLAIN ANALYZE SELECT * FROM knowledge_units WHERE status = 'VERIFIED';
```

### Redis Caching

```python
# Cache configuration
CACHE_CONFIG = {
    'knowledge_units': {'ttl': 3600, 'prefix': 'ku_'},
    'search_results': {'ttl': 300, 'prefix': 'sr_'},
    'user_sessions': {'ttl': 86400, 'prefix': 'sess_'},
    'api_responses': {'ttl': 60, 'prefix': 'api_'}
}

# Cache warm-up
python tools/warm_cache.py
```

### API Optimization

```python
# Enable compression
app.config['COMPRESS_ENABLED'] = True
app.config['COMPRESS_LEVEL'] = 6

# Enable response caching
@app.route('/api/knowledge', methods=['GET'])
@cache.cached(timeout=60)
def get_knowledge():
    ...

# Connection pooling
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 20,
    'max_overflow': 10,
    'pool_recycle': 3600
}
```

### Load Testing

```bash
# Run load test
locust -f tests/load_test.py --host=http://localhost:8216

# Target: 1000 users, 10000 requests
# Expected: P95 < 200ms, error rate < 0.1%
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (pytest tests/)
- [ ] Code review approved
- [ ] Security audit complete
- [ ] Database backup created
- [ ] Rollback plan documented
- [ ] Stakeholders notified
- [ ] Maintenance window scheduled

### During Deployment

- [ ] Stop services
- [ ] Backup current version
- [ ] Deploy new code
- [ ] Run migrations
- [ ] Start services
- [ ] Verify health checks
- [ ] Run smoke tests

### Post-Deployment

- [ ] Monitor error logs (1 hour)
- [ ] Check performance metrics
- [ ] Verify all features work
- [ ] Test critical user flows
- [ ] Update documentation
- [ ] Notify stakeholders
- [ ] Close deployment ticket

---

## Support & Contact

### Emergency Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| DevOps Lead | Quân PT | +84 xxx | quanpt1@viettel.com.vn |
| Security Lead | [Name] | +84 xxx | [email] |
| On-Call Engineer | [Name] | +84 xxx | [email] |

### Support Channels

- **Slack:** #quanai-production
- **Email:** quanai-support@company.com
- **PagerDuty:** quanai-production
- **GitHub Issues:** https://github.com/thequanhcm/quanpt1/issues

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| V30.0 | 2026-10-28 | Production release, all features |
| V29.0 | 2026-10-27 | Advanced AI capabilities |
| V28.0 | 2026-10-26 | Enterprise integration |
| V27.0 | 2026-10-25 | Security hardening |

---

**Document Version:** 30.0  
**Last Updated:** 2026-10-28  
**Maintained By:** QUAN AI BRAIN Team  
**Classification:** Internal Use Only