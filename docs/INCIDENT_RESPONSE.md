# QUAN AI BRAIN - Incident Response Runbooks
**Version:** V22.0  
**Last Updated:** 2024-10-28  
**Emergency Contact:** quanpt1@viettel.com.vn

---

## Table of Contents
1. [Incident Classification](#1-incident-classification)
2. [Response Procedures](#2-response-procedures)
3. [Common Incidents](#3-common-incidents)
4. [Escalation Matrix](#4-escalation-matrix)
5. [Post-Incident Review](#5-post-incident-review)
6. [Contact List](#6-contact-list)

---

## 1. Incident Classification

### Severity Levels

| Level | Description | Response Time | Example |
|---|---|---|---|
| **P1 - Critical** | System down, data loss, security breach | < 15 min | Database corruption, DDoS attack |
| **P2 - High** | Major functionality broken, performance degradation | < 1 hour | API 500 errors, slow queries |
| **P3 - Medium** | Minor functionality affected, workaround available | < 4 hours | Cache issues, non-critical errors |
| **P4 - Low** | Cosmetic issues, feature requests | < 24 hours | UI glitches, documentation errors |

### Impact Assessment
- **Users Affected**: How many users impacted?
- **Data Impact**: Is data at risk?
- **Business Impact**: Revenue, reputation, compliance?
- **Duration**: How long has this been happening?

---

## 2. Response Procedures

### 2.1 Initial Response (All Incidents)

**Step 1: Acknowledge**
```bash
# Check monitoring alerts
curl http://localhost:9090/api/v1/alerts

# Check application logs
docker-compose logs --tail=100 quan-ai-brain

# Verify service status
docker-compose ps
```

**Step 2: Assess**
- What is the symptom?
- When did it start?
- What changed recently?
- How many users affected?

**Step 3: Communicate**
- Notify stakeholders via Slack/Email
- Create incident ticket
- Update status page (if public)

**Step 4: Contain**
- Implement immediate workaround if possible
- Isolate affected components
- Enable maintenance mode if needed

### 2.2 Investigation

**Step 5: Diagnose**
```bash
# Check database health
docker exec quan-ai-postgres pg_isready -U quanai

# Check Redis health
docker exec quan-ai-redis redis-cli ping

# Check application metrics
curl http://localhost:8080/v1/memory/health

# Analyze slow queries
docker exec quan-ai-postgres psql -U quanai -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 5;"
```

**Step 6: Root Cause Analysis**
- Review recent deployments
- Check error logs
- Analyze metrics trends
- Reproduce the issue

### 2.3 Resolution

**Step 7: Fix**
- Apply hotfix if available
- Rollback if fix not ready
- Restart affected services
- Clear caches if needed

**Step 8: Verify**
```bash
# Run health checks
curl http://localhost:8080/v1/memory/health

# Run smoke tests
pytest tests/smoke_test.py -v

# Monitor metrics for 15 minutes
watch -n 5 'curl -s http://localhost:8080/metrics | grep request_count'
```

**Step 9: Close**
- Update incident ticket
- Notify stakeholders
- Document lessons learned
- Schedule post-incident review

---

## 3. Common Incidents

### Incident 1: Database Connection Pool Exhausted

**Symptoms:**
- 503 Service Unavailable errors
- "Connection pool exhausted" in logs
- High database connection count

**Immediate Action:**
```bash
# Check current connections
docker exec quan-ai-postgres psql -U quanai -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
docker exec quan-ai-postgres psql -U quanai -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';"

# Restart application to reset pool
docker-compose restart quan-ai-brain
```

**Root Cause:**
- Connection leak in application
- Too many concurrent requests
- Pool size too small

**Prevention:**
- Increase pool size in config
- Add connection timeout
- Implement connection monitoring
- Fix connection leak in code

---

### Incident 2: High Memory Usage

**Symptoms:**
- Memory usage > 90%
- OOM killer activated
- Application crashes

**Immediate Action:**
```bash
# Check memory usage
docker stats --no-stream

# Identify memory hogs
docker exec quan-ai-brain ps aux --sort=-%mem | head -10

# Restart affected container
docker-compose restart quan-ai-brain

# Check for memory leaks
docker exec quan-ai-brain python -m memory_profiler app.py
```

**Root Cause:**
- Memory leak in application
- Cache too large
- Insufficient memory allocation

**Prevention:**
- Increase memory limit
- Implement memory monitoring
- Fix memory leak
- Add memory limits to queries

---

### Incident 3: Slow Query Performance

**Symptoms:**
- P95 latency > 500ms
- Timeout errors
- High CPU usage

**Immediate Action:**
```bash
# Find slow queries
docker exec quan-ai-postgres psql -U quanai -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Kill long-running queries
docker exec quan-ai-postgres psql -U quanai -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < NOW() - INTERVAL '5 minutes';"

# Analyze query plan
docker exec quan-ai-postgres psql -U quanai -c "EXPLAIN ANALYZE <problematic_query>;"

# Add missing index
docker exec quan-ai-postgres psql -U quanai -c "CREATE INDEX CONCURRENTLY idx_name ON table(column);"
```

**Root Cause:**
- Missing indexes
- Inefficient query
- Table bloat
- Insufficient resources

**Prevention:**
- Regular query optimization
- Index maintenance
- Query caching
- Performance monitoring

---

### Incident 4: Cache Failure

**Symptoms:**
- Cache miss rate > 50%
- Redis connection errors
- High latency on all requests

**Immediate Action:**
```bash
# Check Redis status
docker exec quan-ai-redis redis-cli ping
docker exec quan-ai-redis redis-cli INFO stats

# Check memory usage
docker exec quan-ai-redis redis-cli INFO memory

# Restart Redis if needed
docker-compose restart quan-ai-redis

# Clear cache if corrupted
docker exec quan-ai-redis redis-cli FLUSHDB
```

**Root Cause:**
- Redis out of memory
- Network partition
- Cache key collision
- Configuration error

**Prevention:**
- Monitor Redis memory
- Set appropriate TTL
- Implement cache fallback
- Add Redis clustering

---

### Incident 5: API Rate Limit Exceeded

**Symptoms:**
- 429 Too Many Requests errors
- Users unable to access API
- High request rate

**Immediate Action:**
```bash
# Check current rate
curl -I http://localhost:8080/v1/memory/health

# Temporarily increase limit (if safe)
# Edit .env file
RATE_LIMIT_PER_MINUTE=200

# Restart application
docker-compose restart quan-ai-brain

# Identify abusive clients
docker exec quan-ai-brain python -c "from quan_ai_brain.core.rate_limiter import get_top_clients; print(get_top_clients(10))"
```

**Root Cause:**
- DDoS attack
- Misconfigured client
- Legitimate traffic spike

**Prevention:**
- Implement rate limiting per client
- Add CAPTCHA for suspicious traffic
- Scale horizontally
- Use CDN for static content

---

### Incident 6: Authentication Failure

**Symptoms:**
- 401 Unauthorized errors
- Users unable to login
- Token validation failures

**Immediate Action:**
```bash
# Check JWT secret
docker exec quan-ai-brain python -c "import os; print(os.getenv('JWT_SECRET_KEY')[:10])"

# Verify token
curl -H "Authorization: Bearer <token>" http://localhost:8080/v1/memory/health

# Check authentication logs
docker-compose logs quan-ai-brain | grep -i "auth\|token\|jwt"

# Regenerate secret if compromised
openssl rand -base64 64 > .env.secret
docker-compose restart quan-ai-brain
```

**Root Cause:**
- Expired tokens
- Invalid JWT secret
- Authentication service down
- Token revocation list issue

**Prevention:**
- Monitor token expiry
- Implement token refresh
- Use secure secret management
- Add authentication monitoring

---

### Incident 7: Data Corruption

**Symptoms:**
- Invalid data in database
- Integrity constraint violations
- Inconsistent state

**Immediate Action:**
```bash
# Stop writes to prevent further corruption
docker-compose stop quan-ai-brain

# Backup current state
docker exec quan-ai-postgres pg_dump -U quanai quan_ai_brain > /backups/corruption_$(date +%Y%m%d_%H%M%S).sql

# Identify corrupted records
docker exec quan-ai-postgres psql -U quanai -c "SELECT * FROM knowledge_units WHERE statement IS NULL OR statement = '';"

# Restore from backup if severe
docker exec -i quan-ai-postgres psql -U quanai < /backups/backup_20241028.sql

# Verify data integrity
docker exec quan-ai-postgres psql -U quanai -c "ANALYZE VERBOSE;"
```

**Root Cause:**
- Bug in data processing
- Concurrent write conflict
- Hardware failure
- Human error

**Prevention:**
- Implement data validation
- Add database constraints
- Regular backups
- Use transactions

---

### Incident 8: Security Breach

**Symptoms:**
- Unauthorized access detected
- Suspicious activity in logs
- Data exfiltration attempts

**Immediate Action:**
```bash
# Isolate affected systems
docker-compose stop quan-ai-brain

# Block suspicious IPs
iptables -A INPUT -s <suspicious-ip> -j DROP

# Rotate all secrets
openssl rand -base64 64 > .env.secret
# Update all API keys, database passwords, etc.

# Audit access logs
docker-compose logs quan-ai-brain | grep -i "unauthorized\|forbidden\|error"

# Notify security team
# Email: security@viettel.com.vn
# Phone: +84-xxx-xxx-xxxx
```

**Root Cause:**
- Vulnerability exploitation
- Credential compromise
- Insider threat
- Third-party breach

**Prevention:**
- Regular security audits
- Penetration testing
- Security training
- Incident response plan

---

## 4. Escalation Matrix

### Escalation Path

| Level | Who | When | Contact |
|---|---|---|---|
| **L1** | On-call Engineer | Initial response | Slack #incidents |
| **L2** | Senior Engineer | After 30 min unresolved | Phone: +84-xxx-xxx-xxx |
| **L3** | Tech Lead | After 1 hour unresolved | Phone: +84-xxx-xxx-xxx |
| **L4** | CTO | P1 incidents only | Phone: +84-xxx-xxx-xxx |

### Escalation Triggers
- **P1**: Escalate to L2 immediately, L3 after 15 min
- **P2**: Escalate to L2 after 30 min, L3 after 1 hour
- **P3**: Escalate to L2 after 2 hours
- **P4**: No escalation needed

### Communication Template
```
INCIDENT UPDATE - [SEVERITY] - [INCIDENT_ID]

Status: [Investigating/Identified/Monitoring/Resolved]
Impact: [Description of impact]
Affected Systems: [List of systems]
Users Affected: [Number/Percentage]
Current Action: [What we're doing]
Next Update: [Time]

Contact: [Name] - [Phone]
```

---

## 5. Post-Incident Review

### 5.1 Review Meeting (Within 48 hours)

**Attendees:**
- Incident responder
- Tech lead
- Affected team members
- Stakeholders (if P1/P2)

**Agenda:**
1. Timeline of events
2. Root cause analysis
3. What went well
4. What went wrong
5. Action items

### 5.2 Incident Report Template

```markdown
# Incident Report: [INCIDENT_ID]

## Summary
[Brief description of incident]

## Timeline
- [Time] - Incident detected
- [Time] - Response initiated
- [Time] - Root cause identified
- [Time] - Fix applied
- [Time] - Service restored

## Impact
- Duration: [X hours/minutes]
- Users affected: [Number]
- Revenue impact: [If applicable]
- Data loss: [Yes/No]

## Root Cause
[Detailed explanation]

## Action Items
| ID | Action | Owner | Due Date | Status |
|---|---|---|---|---|
| 1 | [Action] | [Name] | [Date] | [Open/Done] |
| 2 | [Action] | [Name] | [Date] | [Open/Done] |

## Lessons Learned
1. [Lesson]
2. [Lesson]
3. [Lesson]

## Prevention Measures
1. [Measure]
2. [Measure]
3. [Measure]
```

### 5.3 Follow-up
- Track action items to completion
- Update runbooks based on lessons learned
- Conduct training if needed
- Review and update monitoring/alerting

---

## 6. Contact List

### Internal Team
| Role | Name | Phone | Email | Slack |
|---|---|---|---|---|
| Tech Lead | Quân PT | +84-xxx-xxx-xxx | quanpt1@viettel.com.vn | @quanpt1 |
| DevOps | [Name] | +84-xxx-xxx-xxx | [email] | @[slack] |
| Security | [Name] | +84-xxx-xxx-xxx | [email] | @[slack] |

### External Support
| Service | Contact | Phone | Email |
|---|---|---|---|
| Cloud Provider | AWS Support | +1-xxx-xxx-xxx | support@aws.amazon.com |
| Database | PostgreSQL | - | support@postgresql.org |
| Security | Viettel Security | +84-xxx-xxx-xxx | security@viettel.com.vn |

### Emergency Contacts
- **Fire**: 114
- **Police**: 113
- **Medical**: 115
- **IT Emergency**: +84-xxx-xxx-xxx

---

## Appendix: Quick Reference Commands

```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f quan-ai-brain

# Restart service
docker-compose restart quan-ai-brain

# Check database
docker exec quan-ai-postgres psql -U quanai -c "SELECT version();"

# Check Redis
docker exec quan-ai-redis redis-cli ping

# Check metrics
curl http://localhost:9090/api/v1/query?query=up

# Rollback
docker-compose down
docker-compose pull previous
docker-compose up -d

# Backup database
docker exec quan-ai-postgres pg_dump -U quanai quan_ai_brain > backup.sql

# Restore database
docker exec -i quan-ai-postgres psql -U quanai < backup.sql
```

---

**Document Version:** V22.0  
**Last Updated:** 2024-10-28  
**Next Review:** 2025-01-28