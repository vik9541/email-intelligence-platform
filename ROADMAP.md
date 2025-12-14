# Roadmap v1.0.0 - Email Intelligence Pipeline

**Release Target:** v1.0.0  
**Estimated Effort:** 12 hours  
**Dependencies:** v0.9.9-rc1 (current release)

---

## 🎯 Milestone: Email Pipeline MVP

### ТЗ-001: DNS + MX Records Setup ⚙️
**Status:** 🔴 Not Started  
**Priority:** P0 (Critical - Infrastructure)  
**Estimate:** 1.5h | Complexity: MEDIUM  

**Deliverables:**
- [ ] Configure MX records for info@97v.ru
- [ ] Setup Postfix on VPS (45.129.141.198)
- [ ] Let's Encrypt SSL for mail.97v.ru
- [ ] SPF: `v=spf1 include:mail.97v.ru ~all`
- [ ] DKIM key generation & DNS publishing
- [ ] DMARC policy: `p=quarantine; rua=mailto:dmarc-reports@97v.ru`
- [ ] Test: `dig MX 97v.ru`, `postfix status`

**Files:**
- Infrastructure: `/etc/postfix/main.cf` (VPS)
- DNS: DigitalOcean DNS console

---

### ТЗ-002: IMAP Listener + Kafka Producer 📧
**Status:** 🔴 Not Started  
**Priority:** P0 (Critical - Email Intake)  
**Estimate:** 2h | Complexity: MEDIUM  

**Deliverables:**
- [ ] `app/services/imap_listener.py` - IMAPListenerService
- [ ] IMAP IDLE protocol for real-time listening
- [ ] Kafka producer for `email.received` topic
- [ ] Email parser with MIME support (attachments)
- [ ] Retry logic for Kafka failures
- [ ] Tests: `tests/test_imap_listener.py`

**Files:**
- `app/services/imap_listener.py` (new)
- `app/schemas/email_events.py` (new)
- `tests/test_imap_listener.py` (new)

**Dependencies:**
- aioimaplib
- kafka-python
- ТЗ-001 (DNS/MX setup)

---

### ТЗ-003: Email Classification Pipeline (Rules + LLM) 🤖
**Status:** 🔴 Not Started  
**Priority:** P1 (High - Core Feature)  
**Estimate:** 3h | Complexity: HIGH  

**Deliverables:**
- [ ] `app/services/email_classifier.py` - 2-stage classifier
- [ ] Stage 1: Rules engine (70% accuracy, <100ms)
- [ ] Stage 2: Mistral 7B LLM (95% accuracy, <800ms)
- [ ] pgvector similarity search for few-shot learning
- [ ] Categories: Invoice, PO, Support, Sales, HR, Custom
- [ ] Confidence threshold: 0.85
- [ ] Tests: 100+ test emails, measure accuracy & latency

**Files:**
- `app/services/email_classifier.py` (new)
- `app/ml/rules_engine.py` (new)
- `app/ml/llm_classifier.py` (new)
- `tests/test_classifier.py` (new)

**Dependencies:**
- Ollama + Mistral 7B model
- pgvector extension
- ТЗ-002 (email intake)

---

### ТЗ-004: ERP Action Executor (Create Orders) 🏭
**Status:** 🔴 Not Started  
**Priority:** P1 (High - Business Logic)  
**Estimate:** 2.5h | Complexity: HIGH  

**Deliverables:**
- [ ] `app/services/erp_action_executor.py` - ERPActionExecutor
- [ ] Parse order items from email (text, Excel, PDF)
- [ ] Create orders via `POST /api/orders/create`
- [ ] Update invoices via `POST /api/invoices/update`
- [ ] Create tickets via `POST /api/tickets/create`
- [ ] Retry: Exponential backoff (max 3 attempts)
- [ ] Failed actions queue: Redis
- [ ] Tests: `tests/test_erp_executor.py`

**Files:**
- `app/services/erp_action_executor.py` (enhance existing)
- `app/parsers/order_parser.py` (new)
- `tests/test_erp_executor.py` (enhance)

**Dependencies:**
- 97k-backend API
- Redis for queue
- ТЗ-003 (classification)

---

### ТЗ-005: End-to-End Email Pipeline + Monitoring 📊
**Status:** 🔴 Not Started  
**Priority:** P0 (Critical - Integration)  
**Estimate:** 3h | Complexity: HIGH  

**Deliverables:**
- [ ] `app/api/email_pipelines.py` - EmailPipelineService
- [ ] `app/consumers/email_consumer.py` - Kafka consumer
- [ ] E2E flow: IMAP → Kafka → Classify → ERP → Response → Analytics
- [ ] SLA: P95 < 1s, P99 < 2s
- [ ] Prometheus metrics: latency, throughput, error_rate, accuracy
- [ ] Grafana dashboard with real-time SLA tracking
- [ ] 10,000+ emails/day throughput
- [ ] 99.9% uptime (max 22 min/month downtime)

**Files:**
- `app/api/email_pipelines.py` (new)
- `app/consumers/email_consumer.py` (new)
- `dashboards/email_pipeline_sla.json` (Grafana)
- `tests/integration/test_email_e2e.py` (new)

**Dependencies:**
- All previous TZ (001-004)
- Prometheus + Grafana
- Kubernetes

---

## 📅 Timeline

```
Week 1: Infrastructure + Intake (TZ-001, TZ-002)
├─ Day 1: DNS/MX setup, Postfix config
├─ Day 2: IMAP listener, Kafka integration
└─ Day 3: Testing & validation

Week 2: Intelligence + Actions (TZ-003, TZ-004)
├─ Day 4-5: Email classification (Rules + LLM)
├─ Day 6: ERP action executor
└─ Day 7: Integration testing

Week 3: E2E Pipeline + Launch (TZ-005)
├─ Day 8-9: E2E pipeline, Kafka consumer
├─ Day 10: Monitoring, Grafana dashboards
└─ Day 11-12: Load testing, prod deployment
```

---

## 🎯 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Email Processing Latency (P95) | < 1s | Prometheus histogram |
| Email Processing Latency (P99) | < 2s | Prometheus histogram |
| Classification Accuracy | > 90% | Test suite + prod monitoring |
| Throughput | 10,000 emails/day | Kafka metrics |
| Uptime SLA | 99.9% | Kubernetes pod metrics |
| Order Creation Success Rate | > 95% | ERP API logs |

---

## 🚀 Launch Readiness Checklist

### Infrastructure
- [ ] DNS MX records propagated (TZ-001)
- [ ] Postfix running, TLS enabled (TZ-001)
- [ ] DKIM/SPF/DMARC configured (TZ-001)
- [ ] Dovecot IMAP operational (TZ-002)

### Services
- [ ] IMAP listener consuming emails (TZ-002)
- [ ] Kafka topic `email.received` active (TZ-002)
- [ ] Email classifier achieving 90%+ accuracy (TZ-003)
- [ ] ERP executor creating orders (TZ-004)
- [ ] E2E pipeline processing emails (TZ-005)

### Monitoring
- [ ] Prometheus scraping metrics (TZ-005)
- [ ] Grafana dashboard deployed (TZ-005)
- [ ] Alerts configured (uptime, latency, errors)

### Testing
- [ ] Unit tests passing (100%)
- [ ] Integration tests passing (E2E flow)
- [ ] Load tests: 10k emails/day sustained

---

## 📦 Release Plan

**v1.0.0-rc1** (After TZ-001 to TZ-003)
- Email intake + classification ready
- Manual ERP actions

**v1.0.0-rc2** (After TZ-004)
- Automated ERP actions
- Beta testing with real emails

**v1.0.0** (After TZ-005)
- Full E2E pipeline
- Production-ready monitoring
- Public launch

---

## 🔗 Related Documents

- [GO_LIVE_PACKAGE.md](./GO_LIVE_PACKAGE.md) - Production deployment guide
- [PRODUCTION_DEPLOYMENT_RUNBOOK.md](./PRODUCTION_DEPLOYMENT_RUNBOOK.md) - Deployment runbook
- [ON_CALL_QUICK_REFERENCE.md](./ON_CALL_QUICK_REFERENCE.md) - On-call guide
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) - Infrastructure setup

---

**Last Updated:** 2025-12-14  
**Version:** v1.0.0-roadmap  
**Status:** 🔴 Planning → 🟡 In Progress → 🟢 Complete
