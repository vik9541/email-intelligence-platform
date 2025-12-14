# Incident Response Playbook

## Severity Levels

| Severity | Impact | Response Time | Owner |
|----------|--------|----------------|-------|
| P1 | Full outage | < 5 min | On-call |
| P2 | Degraded (> 50% errors) | < 15 min | Team lead |
| P3 | Minor issues (< 5% errors) | < 1 hour | Developer |
| P4 | Non-critical | < 24 hours | Backlog |

---

## P1: Complete System Outage

### Detection
- Grafana: All metrics = 0
- Health check returns 500
- No requests processed for 5 min

### Immediate Actions (< 2 min)
1. **Declare incident**
   - Post to #incidents Slack channel
   - Start incident timer
   - Assign incident commander

2. **Check status**
   ```bash
   kubectl get pods
   kubectl get nodes
   kubectl get services
   ```

3. **Check recent deployments**
   ```bash
   kubectl rollout history deployment/email-intelligence
   kubectl describe deployment email-intelligence
   ```

### Diagnosis (2-5 min)
1. **Pod status**
   ```bash
   kubectl describe pod [failing-pod]
   kubectl logs [failing-pod] --tail=50
   ```

2. **Database connection**
   ```bash
   kubectl exec -it [pod] -- python -c "from src.db import test_connection; test_connection()"
   ```

3. **Recent errors**
   ```bash
   # Elasticsearch
   curl http://elasticsearch:9200/_all/_search?q=severity:error&size=10
   ```

### Recovery

**Scenario A: Bad deployment**
```bash
# Rollback
kubectl rollout undo deployment/email-intelligence
kubectl rollout status deployment/email-intelligence

# Verify
curl http://localhost:8000/health
```

**Scenario B: Database down**
```bash
# Check PostgreSQL
kubectl logs pod/postgres

# If corrupted:
# 1. Scale down app
kubectl scale deployment email-intelligence --replicas=0

# 2. Restore backup
bash scripts/restore-database.sh backup-latest.sql.gz

# 3. Scale up
kubectl scale deployment email-intelligence --replicas=3

# 4. Verify
curl http://localhost:8000/health
```

**Scenario C: Resource exhaustion**
```bash
# Check resources
kubectl top pods
kubectl describe nodes

# If OOM: increase limits
kubectl set resources deployment email-intelligence \
  --limits=memory=2Gi,cpu=2000m \
  --requests=memory=1Gi,cpu=1000m

# Or scale out
kubectl scale deployment email-intelligence --replicas=5
```

### Post-Incident (after recovery)
1. Create GitHub issue with timeline
2. Schedule post-mortem (24 hours)
3. Identify root cause
4. Create prevention task

---

## P2: High Error Rate (> 50% errors)

### Detection Alert
```
🚨 ERROR_RATE_HIGH: 55% errors in last 5 min
```

### Response (< 15 min)

1. **Check what changed**
   ```bash
   git log --oneline -10
   kubectl rollout history deployment/email-intelligence
   ```

2. **Identify error pattern**
   ```bash
   # Kibana search
   POST /_search
   {
     "query": { "match": { "level": "ERROR" } },
     "aggs": { "errors": { "terms": { "field": "error_type" } } }
   }
   ```

3. **Common causes:**
   - Database connection pool exhausted → Scale DB connections
   - External API rate limited → Add backoff/retry
   - Configuration issue → Check environment variables
   - Memory leak → Restart pods

4. **Quick fix options:**
   - Disable non-critical feature (feature flags)
   - Reduce load (scale down consumers)
   - Rollback if recently deployed

### Monitoring During Recovery
```bash
# Watch error rate in real-time
kubectl logs -f deployment/email-intelligence | grep ERROR
```

---

## P3: Elevated Latency (P95 > 2s)

### Check bottleneck
```bash
# Database slow query log
kubectl exec -it pod/postgres -- \
  tail -100 /var/log/postgresql/postgresql.log | grep "duration"

# Application profiling
curl http://localhost:8000/debug/profile?duration=10s
```

### Solutions
- Add database indexes
- Increase replica count
- Enable caching
- Optimize slow queries

---

## Escalation Matrix

| Level | Response Time | Owner | Escalate To |
|-------|----------------|-------|------------|
| 1st response | < 5 min | On-call | Team lead |
| 2nd response | < 15 min | Team lead | Engineering manager |
| 3rd response | < 1 hour | Manager | VP Engineering |

---

## Tools & Access

- **Kubernetes**: kubectl configured locally
- **Logs**: Kibana (localhost:5601)
- **Metrics**: Prometheus (localhost:9090)
- **Database**: psql credentials in secrets
- **On-call**: PagerDuty / Slack

---

## Post-Mortem Template

```markdown
# Incident: [Title]

**Date**: YYYY-MM-DD
**Duration**: HH:MM
**Severity**: P1/P2/P3
**Incident Commander**: @name

## Timeline
- 09:00 - Alert triggered
- 09:02 - Diagnosis started
- 09:05 - Root cause identified
- 09:10 - Fix deployed
- 09:15 - System recovered

## Root Cause
[What actually happened]

## Contributing Factors
[Why it wasn't caught earlier]

## Action Items
- [ ] Fix issue
- [ ] Add monitoring
- [ ] Update runbook
- [ ] Team training
```
