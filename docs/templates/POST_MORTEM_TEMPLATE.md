# Post-Mortem: [Incident Title]

**Incident ID:** [P0-XXX]  
**Date:** [YYYY-MM-DD]  
**Author:** [Your Name]  
**Reviewers:** [Tech Lead, CTO, affected team members]  
**Status:** 🟡 Draft / ✅ Reviewed / 📝 Published

---

## Executive Summary

**Incident:** [1-2 sentence description]  
**Impact:** [X users affected, $Y revenue loss, Z minutes downtime]  
**Root Cause:** [1 sentence - what actually broke]  
**Resolution:** [1 sentence - how we fixed it]  
**Prevention:** [1 sentence - how we'll prevent recurrence]

---

## Incident Details

### Severity Classification
- **Priority:** P0 / P1 / P2
- **Service Affected:** email-service / postgres / kafka / other
- **Customer Impact:** [Number of affected users/requests]
- **Revenue Impact:** [$XXX estimated loss]
- **Duration:** [XX minutes from detection to resolution]

### Detection
- **Alert Fired:** [YYYY-MM-DD HH:MM:SS]
- **Alert Name:** [EmailServiceDown / SLOAvailabilityCritical / etc.]
- **Detection Method:** Automated alert / Customer report / Manual discovery
- **Time to Detection (TTD):** [X minutes from incident start to alert]

---

## Timeline

**All times in MSK (UTC+3)**

| Time | Event | Actor |
|------|-------|-------|
| 10:00:00 | 🔴 Incident Start: Service started throwing 500 errors | System |
| 10:02:15 | 🚨 Alert Fired: EmailServiceDown | Prometheus |
| 10:02:30 | 👤 On-call engineer paged | PagerDuty |
| 10:03:00 | 🔍 Engineer acknowledged, started investigation | @engineer |
| 10:05:00 | 🐛 Identified root cause: Database connection pool exhausted | @engineer |
| 10:06:30 | 🔧 Applied fix: Increased pool size from 10 to 50 | @engineer |
| 10:07:00 | 🔄 Restarted email-service pods | @engineer |
| 10:09:00 | ✅ Service recovered, availability >99% | System |
| 10:12:00 | ✅ Incident resolved, alert cleared | Prometheus |

**Total Duration:** 12 minutes (TTD: 2m 15s, MTTR: 9m 45s)

---

## Root Cause Analysis

### What Happened?
[Detailed technical description of what went wrong]

Example:
```
Email service ran out of database connections due to connection pool exhaustion.
The pool was configured with max_size=10, but during peak traffic (125 req/s),
we needed ~35 concurrent connections. When pool was exhausted, new requests
failed with "TimeoutError: Could not acquire connection from pool within 30s".
```

### 5 Whys Analysis

1. **Why did the service fail?**  
   → Database connections were exhausted

2. **Why were connections exhausted?**  
   → Connection pool max_size=10 was too small for peak traffic

3. **Why was pool size set to 10?**  
   → Default configuration from initial setup, never adjusted

4. **Why wasn't this detected earlier?**  
   → No alerting on connection pool usage metrics

5. **Why was there no alerting?**  
   → PostgreSQL connection pool metrics were not exported to Prometheus

**Root Cause:** Insufficient connection pool size + lack of monitoring on pool usage

### Contributing Factors
- Traffic spike during peak hours (10 AM MSK) - 2x normal volume
- Long-running queries holding connections longer than expected
- No auto-scaling configured for database connection pool

---

## Impact Assessment

### User Impact
- **Affected Users:** ~500 users (25% of total user base)
- **Failed Requests:** ~1,200 requests over 12 minutes
- **User Experience:** Users saw "Service Temporarily Unavailable" error

### Business Impact
- **Revenue Loss:** $150 estimated (based on $0.125/failed request)
- **SLA Breach:** Yes - availability 98.5% for 12 minutes (target: 99.9%)
- **Customer Complaints:** 3 support tickets filed

### SLO Impact
- **Availability:** Dropped to 98.5% for 12 minutes
- **Error Budget Used:** 0.5% of monthly budget (12 min / 43.2 min total)
- **Error Budget Remaining:** 72% (good - not in danger zone)

---

## Resolution

### Immediate Fix (Applied during incident)
```bash
# Increased connection pool size
kubectl set env deployment/email-service -n production \
  DB_POOL_SIZE=50

# Restarted pods to apply change
kubectl rollout restart deployment/email-service -n production
```

### Validation
```bash
# Verified service recovered
kubectl get pods -n production -l app=email-service
# All pods Running

# Verified SLO metrics recovered
curl http://prometheus:9090/api/v1/query?query=slo:email_service:availability:ratio_rate5m
# Result: 0.999 (99.9%)
```

---

## Action Items

**High Priority (Complete within 1 week):**

- [ ] **AI-1:** Add Prometheus metrics for connection pool usage
  - Owner: @backend-engineer
  - Due Date: 2025-12-21
  - Success Criteria: `db_pool_connections_active`, `db_pool_connections_idle` metrics exported

- [ ] **AI-2:** Create alert for high connection pool usage (>80%)
  - Owner: @devops-engineer  
  - Due Date: 2025-12-21
  - Success Criteria: Alert fires when pool >80% utilized

- [ ] **AI-3:** Implement auto-scaling for connection pool based on traffic
  - Owner: @backend-engineer
  - Due Date: 2025-12-28
  - Success Criteria: Pool size adjusts automatically between 10-100

**Medium Priority (Complete within 1 month):**

- [ ] **AI-4:** Review and optimize long-running queries
  - Owner: @backend-engineer
  - Due Date: 2026-01-15
  - Success Criteria: All queries <500ms P95

- [ ] **AI-5:** Add connection pool monitoring to Grafana dashboard
  - Owner: @devops-engineer
  - Due Date: 2026-01-15
  - Success Criteria: Panel showing pool usage trends

**Low Priority (Complete within 3 months):**

- [ ] **AI-6:** Conduct load testing to validate new pool size
  - Owner: @qa-engineer
  - Due Date: 2026-03-01
  - Success Criteria: System handles 3x peak traffic without issues

---

## Lessons Learned

### What Went Well ✅
- Alert fired quickly (2m 15s TTD)
- On-call engineer responded promptly
- Root cause identified quickly (5 minutes)
- Fix applied and validated within 12 minutes total

### What Didn't Go Well ❌
- No monitoring on database connection pool usage
- Default configuration never reviewed after initial setup
- No load testing under peak traffic scenarios

### Surprising Findings 🤔
- Traffic spike was 2x normal but not unprecedented (happens monthly)
- Long-running queries were caused by missing index on `emails.received_at` column

---

## Prevention

### Immediate (Already Implemented)
- ✅ Increased DB pool size to 50
- ✅ Restarted service with new config

### Short-term (This Sprint)
- Add connection pool monitoring
- Create alerting on high pool usage
- Review all database indexes

### Long-term (Next Quarter)
- Implement auto-scaling for connection pool
- Conduct regular load testing
- Build automated capacity planning based on traffic trends

---

## References

- **Incident:** http://pagerduty.com/incidents/P0-XXX
- **Grafana Dashboard:** http://grafana.monitoring/d/slo-dashboard?from=1702540800000&to=1702541520000
- **Prometheus Alerts:** http://prometheus.monitoring:9090/alerts?search=EmailServiceDown
- **Related Incidents:** P0-012 (similar connection pool issue 6 months ago)

---

## Review & Sign-off

**Reviewed by:**
- [ ] Tech Lead (@tech-lead) - Technical accuracy
- [ ] Engineering Manager (@eng-manager) - Action items ownership
- [ ] CTO (@cto) - Business impact assessment

**Published:** [YYYY-MM-DD]  
**Distribution:** Engineering team, Product team, Support team

---

**Template Version:** 1.0  
**Last Updated:** 14 декабря 2025
