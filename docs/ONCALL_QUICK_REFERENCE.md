# 🚨 On-Call Quick Reference Card
**Email Intelligence Platform - Production**

## ⚡ Emergency Contacts

| Role | Contact | When to Call |
|------|---------|--------------|
| **Primary On-Call** | PagerDuty Auto-Page | All P0 incidents |
| **Tech Lead Viktor** | +7-XXX-XXX-XXXX | P0 unresolved >15min |
| **CTO** | +7-XXX-XXX-XXXX | P0 >30min or data loss |
| **Cloud Support** | support@digitalocean.com | Infrastructure issues |

---

## 🔍 Quick Diagnostics (30 seconds)

```bash
# 1. Service Health
kubectl get pods -n production -l app=email-service

# 2. Current SLO Status  
./scripts/monitor-production.sh

# 3. Active Alerts
curl -s http://prometheus.monitoring:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing") | .labels.alertname'

# 4. Recent Deployments
kubectl rollout history deployment/email-service -n production

# 5. System Dependencies
kubectl get pods -n production -l 'app in (postgres,kafka,redis)'
```

---

## 🔧 Common Fixes (Top 5)

### 1. Service Down → Rollback (30sec)
```bash
kubectl rollout undo deployment/email-service -n production
```

### 2. High Memory → Restart Pods (1min)
```bash
kubectl rollout restart deployment/email-service -n production
```

### 3. Kafka Lag → Scale Consumers (30sec)
```bash
kubectl scale deployment/email-service -n production --replicas=6
```

### 4. Database Connections → Cleanup (2min)
```bash
kubectl exec -n production postgres-0 -- psql -U postgres -d email_db -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle' AND state_change < now() - interval '10 minutes'"
```

### 5. Disk Full → Cleanup Logs (1min)
```bash
kubectl exec -n production deployment/email-service -- \
  find /var/log -name "*.log" -mtime +7 -delete
```

---

## 📊 SLO Targets

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Availability | 99.9% | <99% (P0) |
| Latency P95 | <800ms | >800ms (P1) |
| Latency P99 | <1000ms | >5000ms (P0) |
| Error Budget | >20% remaining | <10% (P2) |

---

## 🔗 Important Links

- **Grafana Dashboard:** http://grafana.monitoring/d/slo-dashboard
- **Prometheus Alerts:** http://prometheus.monitoring:9090/alerts
- **P0 Runbook:** [docs/P0_RUNBOOK_RU.md](P0_RUNBOOK_RU.md)
- **PagerDuty:** https://yourcompany.pagerduty.com/incidents
- **Slack #incidents:** https://yourworkspace.slack.com/app_redirect?channel=incidents

---

## 🚀 Escalation Flowchart

```
P0 Alert Fired
    ↓
Run Quick Diagnostics (30s)
    ↓
Attempt Common Fix (1-2min)
    ↓
Fixed? → YES → Close incident in PagerDuty
    |
    NO
    ↓
Call Tech Lead (if >15min)
    ↓
Still Not Fixed?
    ↓
Call CTO + Create War Room (if >30min)
```

---

## 📝 Critical Notes

- **Always check recent deployments first** (80% of incidents are from new releases)
- **Rollback is safe** - can always re-deploy after fixing issue
- **Don't be hero** - escalate early if unsure
- **Document everything** - add comments in PagerDuty incident

---

**Generated:** 14 декабря 2025  
**Version:** 1.0  
**Print this and keep by your desk!**
