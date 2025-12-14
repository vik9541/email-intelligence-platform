# ТЗ-001: Deploy Prometheus SLO Rules [Phase 1]

**Статус:** 🔴 Not Started  
**Приоритет:** P0 (Critical - Production Monitoring)  
**Оценка времени:** 1.5h  
**Сложность:** MEDIUM  
**Владелец:** DevOps/SRE  
**Sprint:** Phase 1 - Production Monitoring Stack  

---

## 📋 Context (Контекст)

Нужно активировать систему мониторинга SLO для production окружения. Файл `prometheus/slo-rules.yaml` уже создан и содержит:
- 5 recording rules для расчета SLI (availability, latency, error budget)
- 12 alert rules с multi-burn-rate подходом (P0/P1/P2)
- Интеграция с AlertManager для эскалации

Без этих правил Prometheus не сможет отслеживать SLO метрики и генерировать критические алерты при деградации сервиса.

**Зависимости:**
- ✅ Prometheus установлен в namespace `monitoring`
- ✅ Email service деплойнут в namespace `production`
- ✅ Файл `prometheus/slo-rules.yaml` создан (commit 49e37eb)

---

## ✅ Requirements (Требования)

### 1. Deploy SLO Rules в Prometheus

```bash
# Применить правила к production Prometheus
kubectl apply -f prometheus/slo-rules.yaml -n monitoring

# Verify: правила загружены
kubectl logs -n monitoring prometheus-0 | grep "Loading configuration file"
```

### 2. Проверить валидность правил

```bash
# Проверить синтаксис YAML
promtool check rules prometheus/slo-rules.yaml

# Verify: должно вывести "SUCCESS"
```

### 3. Verify recording rules работают

```bash
# Подождать 1 минуту для первых расчетов
sleep 60

# Проверить что recording rules создают метрики
curl -s http://prometheus.monitoring:9090/api/v1/query?query=slo:email_service:availability:ratio_rate5m | jq

# Expected output:
# {
#   "data": {
#     "result": [{
#       "metric": {"service": "email"},
#       "value": [timestamp, "0.999"] # должно быть >0.99
#     }]
#   }
# }
```

### 4. Verify alert rules загружены

```bash
# Проверить список активных alert rules
curl -s http://prometheus.monitoring:9090/api/v1/rules | jq '.data.groups[] | select(.name == "slo_fast_burn") | .rules[].name'

# Expected output (12 alerts):
# - EmailServiceDown
# - SLOAvailabilityBudgetBurn
# - SLOAvailabilityCritical
# - SLOLatencyP99Critical
# - SLOErrorRateCritical
# - SLOAvailabilityWarning
# - SLOLatencyP95High
# - KafkaConsumerLagHigh
# - SLOErrorBudgetLow
# - DiskSpaceLow
# - MemoryUsageHigh
# - PodRestartingFrequently
```

### 5. Test alert triggering (dry-run)

```bash
# Временно установить низкий порог для теста
kubectl patch configmap prometheus-config -n monitoring --type merge -p '
data:
  slo-rules.yaml: |
    # ... (изменить threshold для SLOAvailabilityCritical с 0.99 на 1.01 - impossible)
'

# Подождать 2 минуты и проверить что alert firing
curl -s http://prometheus.monitoring:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname == "SLOAvailabilityCritical")'

# Откатить изменение
kubectl apply -f prometheus/slo-rules.yaml -n monitoring
```

---

## ✅ Acceptance Criteria (Критерии приемки)

- [x] **AC1:** Файл `prometheus/slo-rules.yaml` применен через `kubectl apply`
- [x] **AC2:** `promtool check rules` показывает SUCCESS без ошибок
- [x] **AC3:** Все 5 SLO recording rules активны и генерируют метрики:
  - `slo:email_service:availability:ratio_rate5m`
  - `slo:email_service:latency:p95`
  - `slo:email_service:latency:p99`
  - `slo:email_service:error_budget_remaining`
  - `slo:email_service:error_rate`
- [x] **AC4:** Все 12 alert rules загружены в Prometheus
- [x] **AC5:** Recording rules обновляются каждые 30 секунд (видно в Prometheus UI)
- [x] **AC6:** Alert rules имеют корректные labels:
  - `severity: critical` для P0
  - `severity: warning` для P1
  - `severity: info` для P2
- [x] **AC7:** Runbook ссылки в alerts ведут на `docs/P0_RUNBOOK_RU.md`

---

## 🧪 How to Test (Как тестировать)

### Test 1: Recording Rules Generate Metrics

```bash
# Запросить каждую recording rule и проверить что есть данные
for metric in \
  "slo:email_service:availability:ratio_rate5m" \
  "slo:email_service:latency:p95" \
  "slo:email_service:latency:p99" \
  "slo:email_service:error_budget_remaining" \
  "slo:email_service:error_rate"
do
  echo "Testing $metric..."
  result=$(curl -s "http://prometheus.monitoring:9090/api/v1/query?query=$metric" | jq -r '.data.result | length')
  
  if [ "$result" -gt 0 ]; then
    echo "✅ $metric: OK ($result series)"
  else
    echo "❌ $metric: FAIL (no data)"
  fi
done
```

**Expected output:**
```
Testing slo:email_service:availability:ratio_rate5m...
✅ slo:email_service:availability:ratio_rate5m: OK (1 series)

Testing slo:email_service:latency:p95...
✅ slo:email_service:latency:p95: OK (1 series)

...
```

### Test 2: Alert Rules Evaluate Correctly

```bash
# Проверить evaluation time для всех alerts
curl -s http://prometheus.monitoring:9090/api/v1/rules | \
  jq -r '.data.groups[] | select(.name | startswith("slo_")) | .rules[] | "\(.name): \(.evaluationTime)s"'
```

**Expected output:**
```
EmailServiceDown: 0.005s
SLOAvailabilityBudgetBurn: 0.012s
SLOAvailabilityCritical: 0.008s
...
```

**Evaluation time должно быть <100ms для всех alerts.**

### Test 3: Simulate Critical Alert

```bash
# Временно остановить email-service
kubectl scale deployment email-service -n production --replicas=0

# Подождать 2 минуты (alert evaluation interval)
sleep 120

# Проверить что EmailServiceDown firing
curl -s http://prometheus.monitoring:9090/api/v1/alerts | \
  jq '.data.alerts[] | select(.labels.alertname == "EmailServiceDown" and .state == "firing")'

# Expected output:
# {
#   "labels": {
#     "alertname": "EmailServiceDown",
#     "severity": "critical",
#     "service": "email"
#   },
#   "state": "firing",
#   "annotations": {
#     "summary": "Email service has been down for 2 minutes",
#     "runbook": "docs/P0_RUNBOOK_RU.md#scenario-1-email-service-down"
#   }
# }

# Restore service
kubectl scale deployment email-service -n production --replicas=3
```

### Test 4: Verify Error Budget Calculation

```bash
# Проверить формулу error budget
# Formula: (1 - target_slo) * time_window
# Example: (1 - 0.999) * 30 days = 0.001 * 43200 minutes = 43.2 minutes

# Запросить текущий error budget
curl -s http://prometheus.monitoring:9090/api/v1/query?query=slo:email_service:error_budget_remaining | \
  jq -r '.data.result[0].value[1]'

# Expected: число между 0 и 1 (например, 0.85 = 85% remaining)
```

---

## 📊 Monitoring After Deployment

После успешного deployment мониторить в течение 24 часов:

```bash
# Dashboard для проверки SLO метрик
watch -n 30 '
  echo "=== SLO Metrics ==="
  echo "Availability: $(curl -s "http://prometheus.monitoring:9090/api/v1/query?query=slo:email_service:availability:ratio_rate5m" | jq -r .data.result[0].value[1])%"
  echo "Latency P95: $(curl -s "http://prometheus.monitoring:9090/api/v1/query?query=slo:email_service:latency:p95" | jq -r .data.result[0].value[1])s"
  echo "Error Budget: $(curl -s "http://prometheus.monitoring:9090/api/v1/query?query=slo:email_service:error_budget_remaining" | jq -r .data.result[0].value[1])%"
  echo ""
  echo "=== Active Alerts ==="
  curl -s http://prometheus.monitoring:9090/api/v1/alerts | jq -r ".data.alerts[] | select(.state == \"firing\") | .labels.alertname"
'
```

---

## 🔗 Related Tasks

- **Next Task:** [ТЗ-002: Deploy AlertManager Configuration](TZ-PHASE1-002-ALERTMANAGER.md)
- **Dependency:** Email service должен быть deployed в production
- **Blocker:** Без этих правил AlertManager не будет получать alerts

---

## 📝 Notes

### Prometheus Rule Groups

Файл содержит 4 группы правил:

1. **slo_recording_rules** (interval: 30s)
   - Recording rules для SLI метрик
   - Используются другими alerts и Grafana dashboards

2. **slo_fast_burn** (interval: 30s)
   - P0 alerts: критические SLO нарушения
   - Firing time: <2 минуты

3. **slo_slow_burn** (interval: 5m)
   - P1/P2 alerts: предупреждения и долгосрочные тренды
   - Firing time: 5-15 минут

4. **infrastructure_alerts** (interval: 1m)
   - Infrastructure health: disk, memory, pods
   - Firing time: 1-5 минут

### Multi-Burn-Rate Approach

Используем Google SRE best practices:
- **Fast burn (2% in 1h):** Page immediately (P0)
- **Medium burn (5% in 6h):** Alert oncall (P1)
- **Slow burn (10% in 3d):** Create ticket (P2)

Это минимизирует false positives и фокусирует команду на реальных проблемах.

---

**Создано:** 14 декабря 2025  
**Автор:** DevOps Team  
**Версия:** 1.0
