# ТЗ-009: Create On-Call Quick Reference Card [Phase 1]

**Статус:** 🔴 Not Started  
**Приоритет:** P1 (High - On-Call Support)  
**Оценка времени:** 1.5h  
**Сложность:** LOW  
**Владелец:** DevOps/SRE  
**Sprint:** Phase 1 - Production Monitoring Stack  

---

## 📋 Context (Контекст)

On-Call Quick Reference Card - компактная "шпаргалка" для дежурных инженеров. Формат: **1-страница PDF/PNG** с самой критичной информацией:

- **Emergency Contacts** - кого звонить при P0
- **Quick Diagnostics** - 5 команд для первичной диагностики
- **Common Fixes** - top 5 проблем и их решения
- **Escalation Tree** - flowchart когда эскалировать
- **Important Links** - Grafana, Runbook, PagerDuty

Используется:
- **Дежурными инженерами** - распечатан рядом с компьютером или на втором мониторе
- **Новые members команды** - onboarding материал
- **Incident response** - quick reference во время stress ситуаций

**Цель:** Сократить время первичной диагностики с 5 минут до <2 минут.

**Зависимости:**
- ✅ [ТЗ-007: P0 Runbook создан](TZ-PHASE1-007-P0-RUNBOOK.md) (для извлечения common commands)
- ✅ [ТЗ-006: Monitor script создан](TZ-PHASE1-006-MONITOR-SCRIPT.md) (для quick status check)

---

## ✅ Requirements (Требования)

### 1. Создать Markdown источник

```markdown
# docs/ONCALL_QUICK_REFERENCE.md

# 🚨 On-Call Quick Reference Card
Email Intelligence Platform - Production

## ⚡ Emergency Contacts

| Role | Contact | When to Call |
|------|---------|--------------|
| **Primary On-Call** | PagerDuty Auto-Page | All P0 incidents |
| **Tech Lead Viktor** | +7-XXX-XXX-XXXX | P0 unresolved >15min |
| **CTO** | +7-XXX-XXX-XXXX | P0 >30min or data loss |
| **Cloud Support** | support@digitalocean.com | Infrastructure issues |

## 🔍 Quick Diagnostics (30 seconds)

```bash
# 1. Service Health
kubectl get pods -n production -l app=email-service

# 2. Current SLO Status
./scripts/monitor-production.sh

# 3. Active Alerts
curl http://prometheus.monitoring:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing") | .labels.alertname'

# 4. Recent Deployments
kubectl rollout history deployment/email-service -n production

# 5. System Dependencies
kubectl get pods -n production -l app=postgres,app=kafka,app=redis
```

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
kubectl exec -n production postgres-0 -- psql -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle' AND state_change < now() - interval '10 minutes'"
```

### 5. Disk Full → Cleanup Logs (1min)
```bash
kubectl exec -n production deployment/email-service -- \
  find /var/log -name "*.log" -mtime +7 -delete
```

## 📊 SLO Targets

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Availability | 99.9% | <99% (P0) |
| Latency P95 | <800ms | >800ms (P1) |
| Latency P99 | <1000ms | >5000ms (P0) |
| Error Budget | >20% remaining | <10% (P2) |

## 🔗 Important Links

- **Grafana Dashboard:** http://grafana.monitoring/d/slo-dashboard
- **Prometheus Alerts:** http://prometheus.monitoring:9090/alerts
- **P0 Runbook:** [docs/P0_RUNBOOK_RU.md](P0_RUNBOOK_RU.md)
- **PagerDuty:** https://yourcompany.pagerduty.com/incidents
- **Slack #incidents:** https://slack.com/app_redirect?channel=incidents

## 🚀 Escalation Flowchart

```
P0 Alert Fired
    ↓
Run Quick Diagnostics (30s)
    ↓
Attempt Common Fix (1-2min)
    ↓
Fixed? → YES → Close incident in PagerDuty
    ↓ NO
Call Tech Lead (if >15min)
    ↓
Still Not Fixed?
    ↓
Call CTO + Create War Room (if >30min)
```

## 📝 Notes

- **Always check recent deployments first** (80% of incidents are from new releases)
- **Rollback is safe** - can always re-deploy after fixing issue
- **Don't be hero** - escalate early if unsure
- **Document everything** - add comments in PagerDuty incident

---
Generated: 14 декабря 2025  
Version: 1.0
```

### 2. Создать PDF версию

```bash
# Install pandoc (если нет)
brew install pandoc wkhtmltopdf  # macOS
# или
sudo apt-get install pandoc wkhtmltopdf  # Linux

# Generate PDF from Markdown
pandoc docs/ONCALL_QUICK_REFERENCE.md \
  -o docs/ONCALL_QUICK_REFERENCE.pdf \
  --pdf-engine=wkhtmltopdf \
  -V geometry:margin=1cm \
  -V fontsize=10pt

# Verify PDF generated
ls -lh docs/ONCALL_QUICK_REFERENCE.pdf
```

### 3. Создать PNG/Image версию (для slack pin)

```bash
# Convert PDF to PNG (high resolution for printing)
convert -density 300 docs/ONCALL_QUICK_REFERENCE.pdf \
  -quality 100 \
  docs/ONCALL_QUICK_REFERENCE.png

# Or use online tool: https://www.pdf2png.com/
```

### 4. Создать Notion/Confluence версию

```
Скопировать Markdown content в:
- Confluence page: "On-Call Quick Reference"
- Notion page: share в team workspace
- Slack canvas: pin в #incidents channel
```

---

## ✅ Acceptance Criteria (Критерии приемки)

- [x] **AC1:** Markdown файл `docs/ONCALL_QUICK_REFERENCE.md` создан
- [x] **AC2:** Файл содержит все 6 секций:
  - Emergency Contacts
  - Quick Diagnostics (5 commands)
  - Common Fixes (Top 5)
  - SLO Targets table
  - Important Links
  - Escalation Flowchart
- [x] **AC3:** PDF версия сгенерирована
- [x] **AC4:** PNG версия создана (для printing)
- [x] **AC5:** Все bash команды валидны
- [x] **AC6:** Document помещается на 1 страницу (A4/Letter)
- [x] **AC7:** Fonts читаются без zoom (минимум 10pt)
- [x] **AC8:** Распространен команде:
  - Printed copies для on-call engineers
  - Pinned в Slack #incidents
  - Added to team wiki

---

## 🧪 How to Test (Как тестировать)

### Test 1: Verify Markdown Content

```bash
# Check file exists
ls -lh docs/ONCALL_QUICK_REFERENCE.md

# Count sections
grep "^##" docs/ONCALL_QUICK_REFERENCE.md | wc -l
# Expected: 6 sections

# Validate bash commands
grep -A 10 '```bash' docs/ONCALL_QUICK_REFERENCE.md | shellcheck -
```

### Test 2: Generate and Verify PDF

```bash
# Generate PDF
pandoc docs/ONCALL_QUICK_REFERENCE.md -o /tmp/test.pdf

# Check PDF page count
pdfinfo /tmp/test.pdf | grep Pages
# Expected: Pages: 1

# Open PDF and verify:
# - All text visible (no overflow)
# - Tables formatted correctly
# - Code blocks readable
# - Links clickable
```

### Test 3: Print Test

```bash
# Print to PDF printer (check margins)
# или
# Print на реальный принтер

# Проверить:
# - Весь текст помещается на 1 страницу
# - Fonts минимум 10pt (читаемо на расстоянии 50cm)
# - Таблицы не обрезаны
# - QR code (если добавлен) сканируется
```

### Test 4: Usability Test

**Попросить нового team member:**
1. Получить quick reference card
2. Симулировать P0 incident
3. Использовать ТОЛЬКО quick reference (без runbook)
4. Засечь время первичной диагностики

**Target:** <2 минуты от alert до diagnosis

### Test 5: Command Validation

```bash
# Execute каждую команду из "Quick Diagnostics"
# на staging environment

# Expected: Все команды выполняются без ошибок
```

---

## 📊 Usage Metrics

После deployment собирать метрики:

```bash
# Survey on-call engineers monthly:
# 1. Использовали ли quick reference во время incidents?
# 2. Какая секция наиболее useful?
# 3. Что добавить/убрать?

# Metrics to track:
# - Time to diagnosis (before/after quick ref)
# - % incidents resolved with "Common Fixes"
# - Escalation rate (should decrease)
```

---

## 🔧 Maintenance

### Monthly Updates

- [ ] Review "Common Fixes" based на actual incident frequency
- [ ] Update contacts если team changes
- [ ] Add new diagnostics commands если discovered

### After Each P0 Incident

- [ ] Check if quick reference был helpful
- [ ] Add missing command если потребовался
- [ ] Clarify confusing section

### Version History

```
v1.0 - 14 Dec 2025 - Initial creation
v1.1 - [Future]    - Added QR codes for links
v1.2 - [Future]    - Translated to English for international team
```

---

## 📋 Checklist перед закрытием задачи

- [ ] Markdown file created in docs/
- [ ] All 6 sections complete
- [ ] PDF generated (1 page, readable)
- [ ] PNG generated (high-res for printing)
- [ ] Bash commands validated on staging
- [ ] Printed copies distributed to on-call engineers
- [ ] Pinned в Slack #incidents channel
- [ ] Added to team wiki homepage
- [ ] Onboarding checklist updated: "Review On-Call Quick Reference"
- [ ] Feedback collected from 3+ team members

---

## 🔗 Related Tasks

- **Previous:** [ТЗ-008: Setup SLO Report Generation](TZ-PHASE1-008-SLO-REPORT.md)
- **Next:** [ТЗ-010: Implement Post-Mortem Process](TZ-PHASE1-010-POSTMORTEM.md)
- **Source Material:** ТЗ-007 (P0 Runbook), ТЗ-006 (Monitor Script)

---

## 📝 Notes

### Design Tips

**Layout:**
- Use 2-column layout для максимизации space
- Color-code sections (красный=emergency, желтый=warning, зеленый=links)
- Bold для critical information
- Monospace font для commands

**Content Prioritization:**
1. **Most Important** (top half): Emergency contacts, Quick diagnostics
2. **Secondary** (middle): Common fixes, SLO targets
3. **Reference** (bottom): Links, escalation flowchart

### Optional Enhancements

**QR Codes для links:**
```bash
# Generate QR codes for important links
qrencode -o grafana-qr.png "http://grafana.monitoring/d/slo-dashboard"
qrencode -o runbook-qr.png "https://github.com/.../P0_RUNBOOK_RU.md"

# Include в PDF
```

**Laminated Card:**
- Print на водостойкой бумаге
- Laminate для durability
- Credit-card size версия для wallet

**Mobile Version:**
- Responsive HTML version
- PWA (Progressive Web App) для offline access
- Push к home screen на телефоне

---

**Создано:** 14 декабря 2025  
**Автор:** DevOps Team  
**Версия:** 1.0
