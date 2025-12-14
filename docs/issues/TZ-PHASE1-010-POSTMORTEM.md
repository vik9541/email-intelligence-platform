# ТЗ-010: Implement Post-Mortem Process [Phase 1]

**Статус:** 🔴 Not Started  
**Приоритет:** P1 (High - Learning Culture)  
**Оценка времени:** 2h  
**Сложность:** LOW  
**Владелец:** DevOps/Engineering Manager  
**Sprint:** Phase 1 - Production Monitoring Stack  

---

## 📋 Context (Контекст)

Post-Mortem Process - структурированный процесс разбора инцидентов для continuous improvement. Включает:

- **Шаблон post-mortem документа** (Markdown)
- **Timeline инцидента** (когда что произошло)
- **Root cause analysis** (5 Whys method)
- **Action items** с owners и deadlines
- **Lessons learned** для предотвращения повторения

Post-mortems проводятся для:
- **Все P0 incidents** (обязательно в течение 48 часов)
- **P1 incidents** если impact >30 минут или повторяющиеся
- **Interesting P2** если обнаружен новый failure mode

**Цель:** 
- Создать culture of learning (не blame culture)
- Reduce incident recurrence rate до <10%
- Build knowledge base для новых team members

**Зависимости:**
- ✅ [ТЗ-005: Incident Response API](TZ-PHASE1-005-INCIDENT-API.md) (для incident data)
- ⏸️ **Требуется:** Google Docs или Confluence для collaborative editing

---

## ✅ Requirements (Требования)

### 1. Создать Post-Mortem Template

```markdown
# docs/templates/POST_MORTEM_TEMPLATE.md

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

5. **Why没有 alerting?**  
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
```

### 2. Создать Post-Mortem Process Documentation

```markdown
# docs/processes/POST_MORTEM_PROCESS.md

# Post-Mortem Process - Email Intelligence Platform

## When to Conduct Post-Mortem

**Required:**
- All P0 incidents (within 48 hours)
- P1 incidents with >30 minutes impact
- Incidents causing SLA breach
- Incidents with customer complaints

**Optional but Recommended:**
- P2 incidents revealing new failure modes
- Near-miss incidents (almost became P0)
- Interesting technical problems

## Process Timeline

### Day 0 (Incident Day)
- Resolve incident
- Collect initial notes in PagerDuty incident
- Schedule post-mortem meeting (within 48h)

### Day 1-2 (Within 48 hours)
- Author creates post-mortem doc from template
- Fill in Timeline, Root Cause, Impact
- Share draft в Slack #incidents for feedback

### Day 3-5 (Review Period)
- Team reviews and comments
- Author incorporates feedback
- Finalize action items with owners

### Day 7 (Post-Mortem Meeting)
- 60-minute meeting with:
  - On-call engineer (presenter)
  - Tech Lead (reviewer)
  - Affected team members
  - Optional: CTO for P0

### Day 10 (Follow-up)
- Check action items progress
- Update tracking spreadsheet

### Day 30 (Retrospective)
- Review if action items prevented recurrence
- Close post-mortem or escalate blockers

## Roles & Responsibilities

**Author (On-call Engineer):**
- Write post-mortem within 48 hours
- Present in meeting
- Track action items until completion

**Reviewers (Tech Lead + Manager):**
- Validate technical accuracy
- Ensure action items are actionable
- Sign off before publishing

**Action Item Owners:**
- Complete assigned tasks by deadline
- Report blockers immediately
- Update status weekly

## Facilitation Guidelines

**Blameless Culture:**
- No blaming individuals
- Focus on systems and processes
- "What failed" not "Who failed"

**Constructive Feedback:**
- Specific, actionable suggestions
- "Add monitoring" ✅ better than "Should have had monitoring" ❌

**Time-boxing:**
- Meeting: 60 minutes max
- Document writing: 2-4 hours max

## Tracking & Metrics

**Metrics to Track:**
- Post-mortem completion rate (target: 100% for P0)
- Average time to publish (target: <48 hours)
- Action items completion rate (target: >90%)
- Incident recurrence rate (target: <10%)

**Tools:**
- Google Sheets: "Post-Mortem Tracker"
- Columns: Incident ID, Date, Author, Status, Action Items Completed
```

### 3. Создать Shared Post-Mortem Tracker

```markdown
# Google Sheets Template: "Post-Mortem Tracker"

Columns:
- Incident ID (P0-XXX)
- Date
- Service Affected
- Duration (minutes)
- Impact (users/revenue)
- Author
- Status (Draft/Review/Published)
- Action Items (count)
- Action Items Completed (%)
- Published Date
- Link to Document

Public URL: https://docs.google.com/spreadsheets/d/XXXXX
```

---

## ✅ Acceptance Criteria (Критерии приемки)

- [x] **AC1:** Post-mortem template создан в `docs/templates/POST_MORTEM_TEMPLATE.md`
- [x] **AC2:** Process documentation создана в `docs/processes/POST_MORTEM_PROCESS.md`
- [x] **AC3:** Template содержит все required sections:
  - Executive Summary
  - Timeline
  - 5 Whys Root Cause Analysis
  - Impact Assessment
  - Action Items с owners
  - Lessons Learned
- [x] **AC4:** Process определяет timelines (48h для P0)
- [x] **AC5:** Blameless culture guidelines документированы
- [x] **AC6:** Post-Mortem Tracker spreadsheet создан
- [x] **AC7:** Process добавлен в team onboarding checklist
- [x] **AC8:** Conducted первый post-mortem (даже если simulated incident)

---

## 🧪 How to Test (Как тестировать)

### Test 1: Verify Template Completeness

```bash
# Check all required sections present
grep "^##" docs/templates/POST_MORTEM_TEMPLATE.md

# Expected sections:
# - Executive Summary
# - Incident Details
# - Timeline
# - Root Cause Analysis
# - Impact Assessment
# - Resolution
# - Action Items
# - Lessons Learned
# - Prevention
# - References
# - Review & Sign-off
```

### Test 2: Conduct Dry-Run Post-Mortem

```bash
# Simulate P0 incident (from Test 3 in ТЗ-004)
# Use Self-Healing Automaton test scenario

# Create post-mortem doc
cp docs/templates/POST_MORTEM_TEMPLATE.md /tmp/P0-TEST-POSTMORTEM.md

# Fill in with simulated incident data
# Present to team (15 minute dry-run meeting)

# Collect feedback:
# - Is template easy to fill?
# - Are sections clear?
# - What's missing?
```

### Test 3: Validate Process Timeline

```bash
# Create test incident
# Follow process day-by-day:

# Day 0: Incident resolved
# Day 1: Author starts writing (2 hours)
# Day 2: Share draft, collect feedback (30 min)
# Day 5: Finalize action items (1 hour)
# Day 7: Conduct meeting (60 minutes)

# Total time investment: ~4 hours per P0
# Acceptable overhead: Yes (для learning)
```

### Test 4: Action Items Tracking

```bash
# Create 3 action items from dry-run
# Assign owners and due dates
# Track в Google Sheets

# Weekly check:
# - How many completed?
# - Any blockers?

# Target: >90% completion rate
```

---

## 📊 Success Metrics

**Process Health:**
- Post-mortem completion rate: 100% for P0 (target)
- Average time to publish: <48 hours (target)
- Team attendance at meetings: >80% (target)

**Learning Impact:**
- Incident recurrence rate: <10% (target)
- Action items completion: >90% (target)
- New monitoring/alerts added: 2-3 per post-mortem (average)

**Cultural:**
- Team satisfaction with process: >4/5 (quarterly survey)
- Blameless culture score: >4/5 (anonymous feedback)

---

## 📋 Checklist перед закрытием задачи

- [ ] POST_MORTEM_TEMPLATE.md created
- [ ] POST_MORTEM_PROCESS.md created
- [ ] Google Sheets tracker created and shared with team
- [ ] Process added to team wiki
- [ ] Process added to onboarding checklist
- [ ] Dry-run post-mortem conducted (simulated incident)
- [ ] Feedback collected from 3+ team members
- [ ] Process approved by Engineering Manager
- [ ] Scheduled recurring reminder: "Check post-mortem action items" (weekly)

---

## 🔗 Related Tasks

- **Previous:** [ТЗ-009: Create On-Call Quick Reference Card](TZ-PHASE1-009-ONCALL-CARD.md)
- **Completes:** Phase 1 - Production Monitoring Stack
- **Enables:** Continuous improvement culture

---

## 📝 Notes

### Best Practices

**DO:**
- Start writing post-mortem immediately (memory fresh)
- Include specific timestamps in timeline
- Make action items SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
- Share broadly (engineering, product, support teams)
- Celebrate what went well (not just problems)

**DON'T:**
- Blame individuals ("Engineer X made a mistake")
- Use vague action items ("Improve monitoring")
- Skip post-mortem for "small" P0 incidents
- Let action items linger >30 days without completion

### Example Good vs Bad Action Items

**Bad:** "Improve monitoring"  
**Good:** "Add alert for DB connection pool >80% usage (Owner: @devops, Due: Dec 21)"

**Bad:** "Fix database performance"  
**Good:** "Add index on emails.received_at column, validate query <500ms P95 (Owner: @backend, Due: Dec 21)"

**Bad:** "Better testing"  
**Good:** "Add load test scenario: 300 req/s sustained for 10 minutes (Owner: @qa, Due: Jan 15)"

### Integration with Other Systems

**Jira:**
- Auto-create Jira tickets from action items
- Link back to post-mortem document

**Slack:**
- Post executive summary в #engineering after publishing
- Weekly reminder: "3 post-mortem action items due this week"

**Confluence:**
- Archive all post-mortems в "Incident Archive" space
- Build searchable knowledge base

---

**Создано:** 14 декабря 2025  
**Автор:** Engineering Manager + DevOps Team  
**Версия:** 1.0
