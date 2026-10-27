# QUAN AI BRAIN - Production Deployment Guide
**Version:** V22.0  
**Last Updated:** 2024-10-28  
**Author:** QUAN AI BRAIN Team

---

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Environment Setup](#2-environment-setup)
3. [Database Migration](#3-database-migration)
4. [Docker Deployment](#4-docker-deployment)
5. [Kubernetes Deployment](#5-kubernetes-deployment)
6. [Configuration](#6-configuration)
7. [Health Checks](#7-health-checks)
8. [Monitoring Setup](#8-monitoring-setup)
9. [Backup & Recovery](#9-backup--recovery)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

### 1.1 System Requirements
- **CPU**: 4+ cores (8+ recommended for production)
- **RAM**: 8GB minimum (16GB recommended)
- **Disk**: 50GB+ SSD (100GB+ recommended)
- **Network**: 1Gbps+ connection
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)

### 1.2 Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Kubernetes 1.24+ (if using K8s)
- Python 3.11+ (for local tools)
- Git 2.30+

### 1.3 Network Requirements
- Port 8080: Application API
- Port 6379: Redis (internal only)
- Port 5432: PostgreSQL (internal only)
- Port 9090: Prometheus (monitoring)
- Port 3000: Grafana (monitoring)
- Port 443: HTTPS (nginx reverse proxy)

### 1.4 Security Requirements
- SSL/TLS certificates for HTTPS
- Firewall rules to restrict access
- Secrets management (Vault, AWS Secrets Manager, etc.)
- Regular security updates

---

## 2. Environment Setup

### 2.1 Clone Repository
```bash
git clone https://github.com/thequanhcm/quanpt1.git
cd quanpt1
git checkout main
```

### 2.2 Environment Variables
Create `.env` file in project root:

```bash
# Application
APP_ENV=production
APP_PORT=8080
APP_SECRET_KEY=<generate-random-32-char-string>
APP_LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://quanai:password@postgres:5432/quan_ai_brain
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=5

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_MAX_CONNECTIONS=50

# Security
JWT_SECRET_KEY=<generate-random-64-char-string>
CORS_ORIGINS=https://api.quan-ai-brain.vn
RATE_LIMIT_PER_MINUTE=100

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<secure-password>

# Backup
BACKUP_RETENTION_DAYS=30
BACKUP_BUCKET=s3://your-backup-bucket
```

### 2.3 Generate Secrets
```bash
# Generate secure random strings
openssl rand -base64 32  # For APP_SECRET_KEY
openssl rand -base64 64  # For JWT_SECRET_KEY

# Or use Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.4 SSL/TLS Certificates
```bash
# Option 1: Let's Encrypt (recommended for production)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.quan-ai-brain.vn

# Option 2: Self-signed (for testing)
mkdir -p monitoring/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout monitoring/nginx/ssl/server.key \
  -out monitoring/nginx/ssl/server.crt \
  -subj "/CN=api.quan-ai-brain.vn"
```

---

## 3. Database Migration

### 3.1 PostgreSQL Setup
```bash
# Create database and user
docker exec -it quan-ai-postgres psql -U postgres

CREATE DATABASE quan_ai_brain;
CREATE USER quanai WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE quan_ai_brain TO quanai;
\q
```

### 3.2 Run Migrations
```bash
# Initialize database schema
docker-compose run --rm quan-ai-brain python -m quan_ai_brain.db.migrate

# Verify migration
docker-compose run --rm quan-ai-brain python -m quan_ai_brain.db.check
```

### 3.3 Initial Data
```bash
# Load initial knowledge units (optional)
docker-compose run --rm quan-ai-brain python tools/load_initial_data.py

# Create admin user
docker-compose run --rm quan-ai-brain python tools/create_admin.py --username admin --email admin@quan-ai-brain.vn
```

---

## 4. Docker Deployment

### 4.1 Quick Start (Development)
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f quan-ai-brain
```

### 4.2 Production Deployment
```bash
# Use production profile
APP_ENV=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Build optimized images
docker-compose build --no-cache --pull

# Start services
docker-compose up -d
```

### 4.3 Zero-Downtime Deployment
```bash
# Pull new image
docker-compose pull

# Rollout with health checks
docker-compose up -d --no-recreate

# Wait for health check
until curl -f http://localhost:8080/v1/memory/health; do
  echo "Waiting for service to be healthy..."
  sleep 5
done

# Remove old containers
docker-compose down
```

### 4.4 Rollback
```bash
# Rollback to previous version
docker-compose pull previous
docker-compose up -d

# Or use specific tag
docker tag ghcr.io/thequanhcm/quanpt1:v21.0 ghcr.io/thequanhcm/quanpt1:current
docker-compose up -d
```

---

## 5. Kubernetes Deployment

### 5.1 Prerequisites
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### 5.2 Deploy to Kubernetes
```bash
# Create namespace
kubectl create namespace quan-ai-brain

# Apply manifests
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/ingress.yaml

# Verify deployment
kubectl get all -n quan-ai-brain
kubectl get pods -n quan-ai-brain -w
```

### 5.3 Horizontal Pod Autoscaler
```bash
# Apply HPA
kubectl apply -f kubernetes/hpa.yaml

# Check HPA status
kubectl get hpa -n quan-ai-brain
```

### 5.4 Rolling Update
```bash
# Update image
kubectl set image deployment/quan-ai-brain quan-ai-brain=ghcr.io/thequanhcm/quanpt1:v22.0 -n quan-ai-brain

# Monitor rollout
kubectl rollout status deployment/quan-ai-brain -n quan-ai-brain

# Rollback if needed
kubectl rollout undo deployment/quan-ai-brain -n quan-ai-brain
```

---

## 6. Configuration

### 6.1 Application Configuration
Edit `config/production.yaml`:

```yaml
application:
  name: QUAN AI BRAIN
  version: 22.0.0
  environment: production
  
database:
  pool_size: 20
  max_overflow: 5
  pool_timeout: 30
  pool_recycle: 3600
  
cache:
  enabled: true
  ttl: 300
  max_size: 10000
  
security:
  jwt_expiry: 3600
  rate_limit: 100
  cors_origins:
    - https://api.quan-ai-brain.vn
  
logging:
  level: INFO
  format: json
  output: /app/logs/app.log
```

### 6.2 Resource Limits
```yaml
# docker-compose.prod.yml
services:
  quan-ai-brain:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

### 6.3 Environment-Specific Settings
```bash
# Development
APP_ENV=development
APP_LOG_LEVEL=DEBUG
CACHE_ENABLED=false

# Staging
APP_ENV=staging
APP_LOG_LEVEL=INFO
CACHE_ENABLED=true

# Production
APP_ENV=production
APP_LOG_LEVEL=WARNING
CACHE_ENABLED=true
```

---

## 7. Health Checks

### 7.1 Application Health
```bash
# Check API health
curl http://localhost:8080/v1/memory/health

# Expected response:
{
  "overall_status": "healthy",
  "modules": {
    "temporal": "healthy",
    "cross_modal": "healthy",
    "quality": "healthy",
    ...
  },
  "timestamp": "2024-10-28T10:00:00Z"
}
```

### 7.2 Database Health
```bash
# Check PostgreSQL
docker exec quan-ai-postgres pg_isready -U quanai

# Check Redis
docker exec quan-ai-redis redis-cli ping
```

### 7.3 Docker Health
```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' quan-ai-brain

# Check all containers
docker-compose ps
```

### 7.4 Kubernetes Health
```bash
# Check pod status
kubectl get pods -n quan-ai-brain

# Check deployment
kubectl rollout status deployment/quan-ai-brain -n quan-ai-brain

# Check services
kubectl get svc -n quan-ai-brain
```

---

## 8. Monitoring Setup

### 8.1 Prometheus Configuration
Edit `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'quan-ai-brain'
    static_configs:
      - targets: ['quan-ai-brain:8080']
    metrics_path: /metrics

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:9187']
```

### 8.2 Grafana Dashboards
Import dashboards from `monitoring/grafana/dashboards/`:
- `system-overview.json` - System metrics overview
- `memory-performance.json` - Memory performance metrics
- `api-latency.json` - API latency percentiles
- `error-tracking.json` - Error rate tracking

### 8.3 Alert Rules
Edit `monitoring/prometheus/alerts.yml`:

```yaml
groups:
  - name: quan-ai-brain
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status="500"}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: HighLatencies
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High API latencies detected"
```

### 8.4 Log Aggregation
```bash
# Check ELK stack
curl http://localhost:9200
curl http://localhost:5601/api/status

# View logs in Kibana
# Navigate to Discover > quan-ai-brain-*
```

---

## 9. Backup & Recovery

### 9.1 Database Backup
```bash
# Create backup
docker exec quan-ai-postgres pg_dump -U quanai quan_ai_brain > backup_$(date +%Y%m%d).sql

# Compress backup
gzip backup_$(date +%Y%m%d).sql

# Upload to S3
aws s3 cp backup_$(date +%Y%m%d).sql.gz s3://your-backup-bucket/quan-ai-brain/

# Schedule daily backup (cron)
0 2 * * * /path/to/backup.sh
```

### 9.2 Backup Script
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup
docker exec quan-ai-postgres pg_dump -U quanai quan_ai_brain | gzip > \
  ${BACKUP_DIR}/backup_${DATE}.sql.gz

# Upload to S3
aws s3 cp ${BACKUP_DIR}/backup_${DATE}.sql.gz \
  s3://your-backup-bucket/quan-ai-brain/

# Cleanup old backups
find ${BACKUP_DIR} -name "backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# Log
echo "Backup completed: backup_${DATE}.sql.gz"
```

### 9.3 Recovery Procedure
```bash
# Download backup
aws s3 cp s3://your-backup-bucket/quan-ai-brain/backup_20241028.sql.gz .

# Decompress
gunzip backup_20241028.sql.gz

# Restore database
docker exec -i quan-ai-postgres psql -U quanai quan_ai_brain < backup_20241028.sql

# Verify restoration
docker exec quan-ai-postgres psql -U quanai -c "SELECT COUNT(*) FROM knowledge_units;"
```

### 9.4 Disaster Recovery
```bash
# Full system recovery
1. Stop all services: docker-compose down
2. Restore database: (see 9.3)
3. Restore application data: rsync -av backup/data/ /app/data/
4. Start services: docker-compose up -d
5. Verify health: curl http://localhost:8080/v1/memory/health
```

---

## 10. Troubleshooting

### 10.1 Common Issues

#### Issue: Application won't start
```bash
# Check logs
docker-compose logs quan-ai-brain

# Common causes:
# - Database connection failed → Check DATABASE_URL
# - Redis connection failed → Check REDIS_URL
# - Port already in use → Change APP_PORT
# - Missing environment variables → Check .env file
```

#### Issue: High memory usage
```bash
# Check memory usage
docker stats quan-ai-brain

# Solutions:
# - Increase memory limit in docker-compose.yml
# - Enable caching
# - Optimize queries
# - Scale horizontally
```

#### Issue: Slow queries
```bash
# Enable query logging
docker-compose exec postgres psql -U quanai -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"

# Check slow queries
docker-compose exec postgres psql -U quanai -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Solutions:
# - Add indexes
# - Optimize queries
# - Increase cache size
```

#### Issue: Connection pool exhausted
```bash
# Check pool status
docker-compose exec postgres psql -U quanai -c "SELECT count(*) FROM pg_stat_activity;"

# Solutions:
# - Increase DATABASE_POOL_SIZE
# - Optimize connection usage
# - Add connection pooling (PgBouncer)
```

### 10.2 Performance Tuning

#### Database Optimization
```sql
-- Add indexes
CREATE INDEX idx_knowledge_scope ON knowledge_units(scope);
CREATE INDEX idx_knowledge_status ON knowledge_units(status);
CREATE INDEX idx_knowledge_created ON knowledge_units(created_at_utc);

-- Analyze tables
ANALYZE knowledge_units;
ANALYZE relations;

-- Vacuum database
VACUUM ANALYZE;
```

#### Redis Optimization
```bash
# Increase maxmemory
docker exec quan-ai-redis redis-cli CONFIG SET maxmemory 2gb
docker exec quan-ai-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Check Redis stats
docker exec quan-ai-redis redis-cli INFO stats
```

#### Application Optimization
```python
# Enable query caching
# config/production.yaml
cache:
  enabled: true
  ttl: 300
  max_size: 10000

# Enable connection pooling
database:
  pool_size: 20
  max_overflow: 5
```

### 10.3 Security Issues

#### Issue: Unauthorized access
```bash
# Check authentication
curl -H "Authorization: Bearer <token>" http://localhost:8080/v1/memory/health

# Regenerate secrets if compromised
openssl rand -base64 64 > .env.secret
```

#### Issue: Rate limiting triggered
```bash
# Check rate limit config
curl http://localhost:8080/v1/memory/health | jq .rate_limit

# Increase limit if needed
# .env
RATE_LIMIT_PER_MINUTE=200
```

### 10.4 Support & Resources

- **Documentation**: `docs/` directory
- **API Reference**: `docs/openapi_spec.yaml`
- **Issue Tracker**: GitHub Issues
- **Email**: quanpt1@viettel.com.vn
- **Emergency**: +84-xxx-xxx-xxxx

---

## Appendix A: Command Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Execute command in container
docker-compose exec quan-ai-brain bash

# Backup database
docker exec quan-ai-postgres pg_dump -U quanai quan_ai_brain > backup.sql

# Restore database
docker exec -i quan-ai-postgres psql -U quanai < backup.sql

# Update application
docker-compose pull
docker-compose up -d

# Rollback
docker-compose down
docker-compose pull previous
docker-compose up -d
```

---

## Appendix B: Checklist

### Pre-Deployment
- [ ] System requirements met
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database created and migrated
- [ ] Secrets generated and stored securely
- [ ] Firewall rules configured
- [ ] Monitoring configured
- [ ] Backup strategy in place

### Post-Deployment
- [ ] Health checks passing
- [ ] All services running
- [ ] API endpoints responding
- [ ] Monitoring dashboards visible
- [ ] Logs being collected
- [ ] Backup jobs scheduled
- [ ] Security scan passed
- [ ] Performance benchmarks met

### Ongoing
- [ ] Daily backups verified
- [ ] Weekly security updates
- [ ] Monthly performance review
- [ ] Quarterly disaster recovery test
- [ ] Annual security audit

---

**Document Version:** V22.0  
**Last Reviewed:** 2024-10-28  
**Next Review:** 2025-01-28