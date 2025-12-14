# SLA Dashboard & Monitoring

**Last Updated**: 2025-12-14  
**Review Frequency**: Weekly (Friday 4 PM UTC)  
**Owner**: DevOps Team

---

## 📊 Key Service Level Indicators (SLIs)

### 1. Availability

**Target**: 99.9% uptime  
**Allowable Downtime**: 43.2 minutes/month  

**Current Status**: 🟢 99.95%

**Measurement**:
```promql
(1 - (increase(kube_pod_container_status_restarts_total[30d]) / (30 * 24 * 60))) * 100
```

**Alert Threshold**: < 99.5% triggers critical alert

---

### 2. Latency

**P50 Target**: < 200ms  
**P95 Target**: < 500ms  
**P99 Target**: < 1000ms  

**Current Status**:
- P50: 🟢 150ms
- P95: 🟢 420ms
- P99: 🟡 880ms

**Measurement**:
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) * 1000
```

**Alert Threshold**: P95 > 1000ms for 5 minutes

---

### 3. Error Rate

**Target**: < 0.5%  
**Critical Threshold**: < 1%  

**Current Status**: 🟢 0.12%

**Measurement**:
```promql
(sum(rate(errors_total[5m])) / sum(rate(http_requests_total[5m]))) * 100
```

**Alert Threshold**: > 1% triggers critical alert

---

### 4. Throughput

**Baseline**: 50 emails/second  
**Peak Capacity**: 500 emails/second  
**Target**: > 10 emails/second sustained  

**Current Status**: 🟢 75 emails/sec

**Measurement**:
```promql
rate(emails_processed_total[1m])
```

**Alert Threshold**: < 5 emails/sec for 10 minutes

---

## 🔧 System Reliability Metrics

### Database Performance

**Query Latency Target**: P95 < 50ms  
**Current**: 🟢 35ms

**Connection Pool**:
- Target Utilization: < 80%
- Current: 🟢 45%
- Alert: > 90% utilization

**Replication Lag** (Multi-region):
- Target: < 100ms
- Current: 🟢 65ms
- Alert: > 500ms

---

### Pod Health

**Restart Rate**: < 2 restarts/24h  
**Current**: 🟢 0 restarts

**Memory Usage**: < 80% of limit  
**Current**: 🟢 58%

**CPU Usage**: < 70% sustained  
**Current**: 🟢 42%

---

### Storage

**Disk Usage**: < 80%  
**Current**: 🟢 45%

**Backup Status**:
- Last Backup: ✅ 2025-12-14 02:00 UTC
- Backup Size: 2.3 GB
- Retention: 7 days (hot), 30 days (cold)

---

## 📈 Business Metrics

### Email Processing

**Daily Volume**: ~500K emails  
**Success Rate**: 99.88%  
**Average Processing Time**: 180ms  

**Top Sender Domains** (24h):
1. gmail.com (35%)
2. outlook.com (25%)
3. company.com (15%)
4. yahoo.com (10%)
5. other (15%)

---

### Peak Hours

**Busiest Hours** (UTC):
- 09:00-11:00 (30% of traffic)
- 14:00-16:00 (25% of traffic)
- 19:00-21:00 (20% of traffic)

**Quietest Hours**:
- 00:00-06:00 (5% of traffic)

---

## 🚨 Alert Summary

### Active Alerts

| Severity | Count | Latest Alert |
|----------|-------|--------------|
| Critical | 0 | - |
| Warning | 1 | High CPU on pod-3 |
| Info | 2 | Disk usage 75%, Backup completed |

### Alert Response Times

**Target**: 
- Critical: < 15 minutes
- Warning: < 1 hour
- Info: < 4 hours

**Current Average**:
- Critical: N/A (no recent incidents)
- Warning: 🟢 25 minutes
- Info: 🟢 2 hours

---

## 📅 SLA Compliance Tracking

### Monthly Overview (December 2025)

| Week | Availability | Avg Latency | Error Rate | Status |
|------|-------------|-------------|------------|--------|
| W1 (Dec 1-7) | 99.95% | 420ms | 0.15% | ✅ Pass |
| W2 (Dec 8-14) | 99.98% | 380ms | 0.12% | ✅ Pass |
| W3 (Dec 15-21) | - | - | - | Pending |
| W4 (Dec 22-31) | - | - | - | Pending |

**Monthly Target**: All SLIs within thresholds  
**Current Status**: ✅ **ON TRACK**

---

## 🎯 Error Budget

**Monthly Error Budget**: 0.1% (43.2 minutes downtime)  
**Consumed This Month**: 0.02% (8.6 minutes)  
**Remaining**: 0.08% (34.6 minutes)  

**Burn Rate**: 🟢 Low (0.5%/day)

**Error Budget Policy**:
- < 25% consumed: All deployments allowed
- 25-50% consumed: Review required for major changes
- 50-75% consumed: Only critical fixes
- > 75% consumed: Freeze deployments, focus on reliability

---

## 📊 Dashboard Links

### Grafana Dashboards
- [Production Overview](http://grafana:3000/d/email-intelligence-prod)
- [Database Metrics](http://grafana:3000/d/database-metrics)
- [Infrastructure Health](http://grafana:3000/d/infra-health)
- [Business Analytics](http://grafana:3000/d/business-analytics)

### Prometheus Queries
- [Email Processing Rate](http://prometheus:9090/graph?g0.expr=rate(emails_processed_total[5m]))
- [Error Rate](http://prometheus:9090/graph?g0.expr=rate(errors_total[5m]))
- [Latency Distribution](http://prometheus:9090/graph?g0.expr=http_request_duration_seconds_bucket)

### Kibana Logs
- [Application Logs](http://kibana:5601/app/discover#/email-logs)
- [Error Logs](http://kibana:5601/app/discover#/error-logs)

---

## 🔄 Weekly Review Process

**Schedule**: Every Friday at 4 PM UTC

**Participants**:
- DevOps Lead
- Engineering Lead
- Product Owner
- On-Call Engineer

**Agenda**:
1. Review weekly SLA compliance (10 min)
2. Analyze error budget consumption (5 min)
3. Discuss incident post-mortems (15 min)
4. Review upcoming changes impact (10 min)
5. Action items and next steps (10 min)

**Outcomes**:
- Weekly SLA report published
- Action items assigned
- Next week priorities set

---

## 📝 Incident Response

### Severity Definitions

**P0 - Critical**:
- Complete service outage
- Data loss risk
- Security breach
- Response: < 15 minutes
- Resolution: < 2 hours

**P1 - High**:
- Major feature unavailable
- Performance degradation > 50%
- High error rate (> 5%)
- Response: < 1 hour
- Resolution: < 4 hours

**P2 - Medium**:
- Minor feature issues
- Performance degradation < 50%
- Elevated error rate (1-5%)
- Response: < 4 hours
- Resolution: < 24 hours

**P3 - Low**:
- Cosmetic issues
- Documentation errors
- Response: < 24 hours
- Resolution: Best effort

---

## 📞 Escalation Contacts

**DevOps Lead**: @devops-lead  
**Engineering Lead**: @eng-lead  
**On-Call Engineer**: @on-call  
**Product Owner**: @product  

**Slack Channels**:
- #email-service-alerts (automated)
- #incidents (manual escalation)
- #sla-reports (weekly reports)

**PagerDuty**: +1-xxx-xxx-xxxx

---

## 🎓 Post-Incident Review

After each P0/P1 incident, conduct post-mortem within 48 hours:

1. Timeline of events
2. Root cause analysis
3. Impact assessment
4. Resolution steps taken
5. Preventive measures
6. Action items with owners

**Template**: [Post-Mortem Template](docs/POST_MORTEM_TEMPLATE.md)

---

**Last Review**: 2025-12-14  
**Next Review**: 2025-12-20  
**Status**: 🟢 All SLAs on track
