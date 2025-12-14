# ТЗ-003: Create Grafana SLO Dashboard [Phase 1]

**Статус:** 🔴 Not Started  
**Приоритет:** P1 (High - Observability)  
**Оценка времени:** 2h  
**Сложность:** MEDIUM  
**Владелец:** DevOps/SRE  
**Sprint:** Phase 1 - Production Monitoring Stack  

---

## 📋 Context (Контекст)

Grafana dashboard для real-time мониторинга SLO метрик. Файл `grafana/dashboards/slo-dashboard.json` уже создан и содержит **13 панелей**:

1. SLO Status gauge (99.9% target)
2. Latency P95 gauge (<800ms target)
3. Error Budget gauge (30-day window)
4. Active Alerts counter
5. Availability Trend (7 days)
6. Latency Percentiles (P50/P95/P99)
7. Throughput (total/success/error RPS)
8. Classification Accuracy
9. ERP Actions Success Rate
10. Kafka Consumer Lag
11. PostgreSQL Connections
12. Error Budget Burn Rate
13. Pod Health table

Dashboard будет использоваться:
- **Дежурными инженерами** - для мониторинга production 24/7
- **CTO/VP Engineering** - для weekly reviews
- **Incident response** - при разборе P0/P1 инцидентов

**Зависимости:**
- ✅ [ТЗ-001: Prometheus SLO Rules deployed](TZ-PHASE1-001-PROMETHEUS-SLO-RULES.md)
- ✅ Grafana установлен в namespace `monitoring`
- ✅ Файл `grafana/dashboards/slo-dashboard.json` создан (commit 49e37eb)

---

## ✅ Requirements (Требования)

### 1. Настроить Prometheus Datasource в Grafana

```bash
# Port-forward Grafana для доступа
kubectl port-forward -n monitoring svc/grafana 3000:80

# Открыть в браузере: http://localhost:3000
# Default credentials: admin/admin (изменить при первом входе)

# Добавить Prometheus datasource:
# 1. Перейти: Configuration → Data Sources → Add data source
# 2. Выбрать: Prometheus
# 3. URL: http://prometheus.monitoring.svc.cluster.local:9090
# 4. Access: Server (default)
# 5. Click: Save & Test
```

### 2. Импортировать SLO Dashboard

**Способ 1: Через Grafana UI (рекомендуется для тестирования)**

```bash
# 1. Перейти: Dashboards → Import
# 2. Нажать: Upload JSON file
# 3. Выбрать: grafana/dashboards/slo-dashboard.json
# 4. Select datasource: Prometheus (созданный в шаге 1)
# 5. Click: Import
```

**Способ 2: Через Grafana API (для automation)**

```bash
# Получить API key
# Grafana UI → Configuration → API Keys → Add API key
# Name: "Dashboard Provisioning"
# Role: Admin
# Скопировать API key

# Импортировать dashboard через API
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @grafana/dashboards/slo-dashboard.json
```

**Способ 3: Через ConfigMap provisioning (best practice для production)**

```bash
# Создать ConfigMap с dashboard
kubectl create configmap grafana-dashboard-slo -n monitoring \
  --from-file=slo-dashboard.json=grafana/dashboards/slo-dashboard.json

# Обновить Grafana deployment для auto-provisioning
kubectl edit deployment grafana -n monitoring

# Добавить volume mount:
# volumes:
#   - name: dashboard-slo
#     configMap:
#       name: grafana-dashboard-slo
#
# volumeMounts:
#   - name: dashboard-slo
#     mountPath: /etc/grafana/provisioning/dashboards/slo-dashboard.json
#     subPath: slo-dashboard.json

# Перезапустить Grafana
kubectl rollout restart deployment/grafana -n monitoring
```

### 3. Настроить Variables

Dashboard использует 2 переменные:
- `$datasource` - выбор Prometheus datasource
- `$namespace` - filter по namespace (default: production)

Проверить что variables работают:
```
Grafana UI → Dashboard Settings → Variables
- datasource: type=datasource, query=prometheus
- namespace: type=query, query=label_values(up, namespace)
```

### 4. Настроить Auto-Refresh

```
Dashboard Settings → Time & Refresh intervals
- Refresh: 30s (default)
- Available intervals: 10s, 30s, 1m, 5m, 15m
- Enable: Auto refresh when dashboard opened
```

### 5. Настроить Annotations

Dashboard должен показывать deployments как vertical lines:

```
Dashboard Settings → Annotations
- Name: Deployments
- Data source: Prometheus
- Query: kube_deployment_status_replicas_updated{namespace="production"}
- Color: Green
- Tags: deployment
```

---

## ✅ Acceptance Criteria (Критерии приемки)

- [x] **AC1:** Grafana доступен на `http://grafana.monitoring` (внутри кластера)
- [x] **AC2:** Prometheus datasource настроен и показывает "Data source is working"
- [x] **AC3:** SLO Dashboard импортирован и доступен по ссылке `/d/slo-dashboard`
- [x] **AC4:** Все 13 панелей отображают данные (не "No data")
- [x] **AC5:** Variables `$datasource` и `$namespace` работают
- [x] **AC6:** Auto-refresh 30s включен
- [x] **AC7:** Annotations показывают deployments как вертикальные линии на графиках
- [x] **AC8:** Dashboard имеет правильные thresholds:
  - Availability gauge: Red <99%, Yellow 99-99.9%, Green >99.9%
  - Latency P95 gauge: Red >800ms, Yellow 600-800ms, Green <600ms
  - Error Budget: Red <20%, Yellow 20-50%, Green >50%

---

## 🧪 How to Test (Как тестировать)

### Test 1: Verify All Panels Load Data

```bash
# Открыть dashboard
# URL: http://localhost:3000/d/slo-dashboard

# Проверить каждую панель:
# Panel 1: SLO Status - должна показывать процент availability (например, 99.92%)
# Panel 2: Latency P95 - должна показывать миллисекунды (например, 450ms)
# Panel 3: Error Budget - должна показывать процент remaining (например, 85%)
# Panel 4: Active Alerts - должна показывать число (например, 0 или 2)
# Panel 5: Availability Trend - график за 7 дней с линией 99.9% threshold
# ...и так далее для всех 13 панелей

# Если панель показывает "No data":
# 1. Click: Panel title → Edit
# 2. Query Inspector → Refresh
# 3. Проверить PromQL query в Query tab
# 4. Выполнить query в Prometheus UI для debug
```

### Test 2: Verify Variables Work

```bash
# В верхней части dashboard должны быть dropdowns:
# - datasource: [Prometheus]
# - namespace: [production] [staging] [monitoring]

# Тест:
# 1. Изменить namespace с "production" на "staging"
# 2. Все панели должны обновиться и показать данные для staging
# 3. Вернуть namespace обратно на "production"
```

### Test 3: Verify Thresholds and Colors

```bash
# Panel 1: SLO Status Gauge
# - Если availability >99.9% → фон зеленый, значение зеленое
# - Если 99-99.9% → фон желтый, значение желтое
# - Если <99% → фон красный, значение красное

# Симулировать low availability для теста:
# 1. Остановить 2 из 3 email-service replicas
kubectl scale deployment email-service -n production --replicas=1

# 2. Подождать 2 минуты (Prometheus scrape interval)
sleep 120

# 3. Обновить Grafana dashboard (F5)
# 4. SLO Status gauge должен стать красным (availability упал <99%)

# 5. Восстановить replicas
kubectl scale deployment email-service -n production --replicas=3
```

### Test 4: Verify Auto-Refresh

```bash
# 1. Открыть dashboard
# 2. В правом верхнем углу должна быть иконка refresh с "30s"
# 3. Наблюдать за Panel 7 (Throughput) - график должен обновляться каждые 30 секунд
# 4. Новые точки данных должны появляться на правом краю графика

# Проверка через Network tab в Chrome DevTools:
# - Должны быть XHR requests к /api/datasources/proxy/*/api/v1/query_range каждые 30 секунд
```

### Test 5: Verify Annotations (Deployments)

```bash
# 1. Сделать новый deployment
kubectl set image deployment/email-service -n production \
  email-service=ghcr.io/vik9541/email-service:v0.9.9

# 2. Подождать 1 минуту
sleep 60

# 3. Обновить Grafana dashboard (F5)
# 4. На графике "Availability Trend" должна появиться зеленая вертикальная линия
# 5. При наведении на линию - tooltip: "Deployment: email-service updated"
```

### Test 6: Verify Drill-Down Links

```bash
# Panel 4: Active Alerts
# Кликнуть на число (например, "2 active alerts")
# → Должен открыться AlertManager UI с filtered view: только firing alerts

# Panel 13: Pod Health Table
# Кликнуть на pod name (например, "email-service-abc123")
# → Должен открыться Kubernetes Dashboard или Lens для этого pod
```

---

## 📊 Panel Descriptions

### Panel 1: SLO Status Gauge
```
Query: slo:email_service:availability:ratio_rate5m * 100
Unit: Percent (0-100)
Thresholds: 
  - Red: 0-99
  - Yellow: 99-99.9
  - Green: 99.9-100
Min/Max: 98% - 100%
```

### Panel 2: Latency P95 Gauge
```
Query: slo:email_service:latency:p95
Unit: Milliseconds
Thresholds:
  - Red: >800
  - Yellow: 600-800
  - Green: <600
Min/Max: 0 - 1000ms
```

### Panel 3: Error Budget Gauge
```
Query: slo:email_service:error_budget_remaining * 100
Unit: Percent (0-100)
Thresholds:
  - Red: <20%
  - Yellow: 20-50%
  - Green: >50%
Min/Max: 0 - 100%
```

### Panel 5: Availability Trend (Graph)
```
Query 1 (Actual): slo:email_service:availability:ratio_rate5m * 100
Query 2 (Target): 99.9 (constant line)
Time range: Last 7 days
Legend: "Actual Availability", "Target 99.9%"
Y-axis: 98% - 100% (fixed range to highlight small changes)
```

### Panel 7: Throughput (Graph)
```
Query 1 (Total): sum(rate(http_requests_total{service="email"}[5m]))
Query 2 (Success): sum(rate(http_requests_total{service="email",status=~"2.."}[5m]))
Query 3 (Error): sum(rate(http_requests_total{service="email",status=~"5.."}[5m]))
Unit: Requests per second
Stacking: None (separate lines)
```

---

## 🔧 Troubleshooting

### Problem: "No data" на всех панелях

**Diagnosis:**
```bash
# 1. Проверить Prometheus datasource
Grafana UI → Configuration → Data Sources → Prometheus → Test

# Если "Error reading Prometheus":
# - Проверить URL: http://prometheus.monitoring.svc.cluster.local:9090
# - Проверить Prometheus running: kubectl get pods -n monitoring -l app=prometheus
```

**Fix:**
```bash
# Если Prometheus URL неверный, исправить:
Grafana UI → Data Sources → Prometheus → Edit
URL: http://prometheus.monitoring.svc.cluster.local:9090
Access: Server (default)
Save & Test
```

### Problem: "No data" только на некоторых панелях

**Diagnosis:**
```bash
# Проверить PromQL query в Prometheus UI
# 1. kubectl port-forward -n monitoring svc/prometheus 9090:9090
# 2. Открыть: http://localhost:9090/graph
# 3. Вставить query из панели (например, slo:email_service:availability:ratio_rate5m)
# 4. Click: Execute

# Если "Empty query result":
# - Recording rule не активна → проверить ТЗ-001
# - Метрика не экспортируется → проверить email-service metrics endpoint
```

### Problem: Dashboard медленно загружается (>10 секунд)

**Diagnosis:**
```bash
# Проверить query performance
# Grafana → Panel → Edit → Query Inspector → Stats
# 
# Slow queries (>1s):
# - Обычно это range queries за большой период (например, 30 days)
# - Решение: использовать recording rules вместо raw queries
```

**Fix:**
```json
// Плохо (медленно):
{
  "expr": "rate(http_requests_total[30d])"
}

// Хорошо (быстро):
{
  "expr": "slo:email_service:availability:ratio_rate5m"  // Already pre-aggregated
}
```

---

## 📋 Checklist перед закрытием задачи

- [ ] Grafana доступен и credentials изменены с дефолтных
- [ ] Prometheus datasource настроен и тестируется успешно
- [ ] SLO Dashboard импортирован
- [ ] Все 13 панелей отображают данные
- [ ] Variables (datasource, namespace) работают
- [ ] Auto-refresh 30s включен
- [ ] Thresholds настроены правильно (цвета меняются при изменении метрик)
- [ ] Annotations показывают deployments
- [ ] Dashboard добавлен в Starred dashboards для быстрого доступа
- [ ] Создан Snapshot для демонстрации stakeholders
- [ ] URL dashboard добавлен в:
  - [ ] P0 Runbook
  - [ ] Production Deployment Playbook
  - [ ] Team wiki

---

## 🔗 Related Tasks

- **Previous:** [ТЗ-002: Deploy AlertManager Configuration](TZ-PHASE1-002-ALERTMANAGER.md)
- **Next:** [ТЗ-004: Implement Self-Healing Automaton](TZ-PHASE1-004-SELF-HEALING.md)
- **Dependency:** Prometheus recording rules (ТЗ-001)

---

## 📝 Notes

### Dashboard Sharing

**Public Snapshot для stakeholders:**
```bash
# Создать snapshot (read-only, с ограниченным временем жизни)
Grafana UI → Dashboard → Share → Snapshot
- Snapshot name: "SLO Dashboard - Week 50 2025"
- Expire: 30 days
- Publish to snapshots.raintank.io: Yes

# Скопировать URL и отправить в Slack/Email
```

**Embedding в external apps:**
```html
<!-- Встроить панель в wiki или admin panel -->
<iframe src="http://grafana.monitoring/d-solo/slo-dashboard?panelId=1&orgId=1" 
        width="450" height="200" frameborder="0"></iframe>
```

### Alerts на Dashboard Панелях

Некоторые панели могут иметь свои alerts (дублируют Prometheus alerts для visibility):

```
Panel 3: Error Budget
- Alert: "Error Budget Low"
- Condition: Error Budget <20%
- Notification: Slack #alerts
- Frequency: Every 1 hour
```

**Не рекомендуется** использовать Grafana alerts вместо Prometheus - только для дублирования критических метрик.

---

**Создано:** 14 декабря 2025  
**Автор:** DevOps Team  
**Версия:** 1.0
