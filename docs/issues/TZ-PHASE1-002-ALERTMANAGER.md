# ТЗ-002: Deploy AlertManager Configuration [Phase 1]

**Статус:** 🔴 Not Started  
**Приоритет:** P0 (Critical - Alert Routing)  
**Оценка времени:** 2h  
**Сложность:** MEDIUM  
**Владелец:** DevOps/SRE  
**Sprint:** Phase 1 - Production Monitoring Stack  

---

## 📋 Context (Контекст)

AlertManager - центральная система для роутинга и эскалации alerts от Prometheus. Файл `prometheus/alertmanager.yml` уже создан и содержит:
- **3 уровня эскалации:** P0 (PagerDuty), P1 (Slack + Email), P2 (Email only)
- **Smart routing:** автоматическое определение severity и route к нужным receivers
- **Inhibit rules:** подавление derivative alerts (например, latency alerts когда service down)
- **Grouping:** объединение похожих alerts для уменьшения noise

Без AlertManager'а все Prometheus alerts будут генерироваться, но никто их не получит.

**Зависимости:**
- ✅ [ТЗ-001: Prometheus SLO Rules deployed](TZ-PHASE1-001-PROMETHEUS-SLO-RULES.md)
- ⏸️ **Требуется:** Slack webhook URL, PagerDuty integration key, SMTP credentials
- ✅ Файл `prometheus/alertmanager.yml` создан (commit 49e37eb)

---

## ✅ Requirements (Требования)

### 1. Создать Kubernetes Secrets для интеграций

```bash
# PagerDuty integration key
kubectl create secret generic pagerduty-key -n monitoring \
  --from-literal=integration_key='YOUR_PAGERDUTY_INTEGRATION_KEY'

# Slack webhook URL
kubectl create secret generic slack-webhook -n monitoring \
  --from-literal=url='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

# SMTP credentials для email alerts
kubectl create secret generic smtp-credentials -n monitoring \
  --from-literal=username='alerts@97v.ru' \
  --from-literal=password='YOUR_SMTP_PASSWORD'
```

### 2. Обновить AlertManager ConfigMap

```bash
# Создать ConfigMap из alertmanager.yml
kubectl create configmap alertmanager-config -n monitoring \
  --from-file=alertmanager.yml=prometheus/alertmanager.yml

# Verify: ConfigMap создан
kubectl get configmap alertmanager-config -n monitoring -o yaml
```

### 3. Deploy/Update AlertManager

```bash
# Если AlertManager еще не установлен:
helm upgrade --install alertmanager prometheus-community/alertmanager \
  --namespace monitoring \
  --set configmapReload.enabled=true \
  --set config.existingConfigMap=alertmanager-config

# Если AlertManager уже установлен:
kubectl rollout restart deployment/alertmanager -n monitoring
```

### 4. Настроить Prometheus → AlertManager связь

Проверить что Prometheus отправляет alerts в AlertManager:

```bash
# Проверить Prometheus config
kubectl get configmap prometheus-config -n monitoring -o yaml | grep alertmanagers -A 10

# Должно содержать:
# alerting:
#   alertmanagers:
#     - static_configs:
#         - targets:
#           - alertmanager:9093
```

Если нет, обновить Prometheus config:

```yaml
# prometheus-config.yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager.monitoring.svc.cluster.local:9093
```

### 5. Создать Slack channels

В Slack workspace создать каналы:
- `#incidents` - для P0 critical alerts
- `#alerts` - для P1/P2 warnings

Добавить Incoming Webhook Integration для каждого канала.

### 6. Настроить PagerDuty

1. Создать Service в PagerDuty: "Email Intelligence Platform - Production"
2. Добавить Integration: "Prometheus" type
3. Скопировать Integration Key → использовать в Secret (шаг 1)

---

## ✅ Acceptance Criteria (Критерии приемки)

- [x] **AC1:** Secrets созданы в namespace `monitoring`:
  - `pagerduty-key`
  - `slack-webhook`
  - `smtp-credentials`
- [x] **AC2:** AlertManager ConfigMap создан из `alertmanager.yml`
- [x] **AC3:** AlertManager pod running и healthy
- [x] **AC4:** Prometheus успешно подключен к AlertManager (видно в Prometheus UI → Status → Runtime & Build Information)
- [x] **AC5:** AlertManager UI доступен: `http://alertmanager.monitoring:9093`
- [x] **AC6:** Test alert успешно отправлен в Slack #incidents
- [x] **AC7:** Inhibit rules работают (подавление duplicate alerts)
- [x] **AC8:** Grouping работает (похожие alerts объединяются в одно notification)

---

## 🧪 How to Test (Как тестировать)

### Test 1: Verify AlertManager Running

```bash
# Проверить pod status
kubectl get pods -n monitoring -l app=alertmanager

# Expected output:
# NAME                           READY   STATUS    RESTARTS   AGE
# alertmanager-0                 1/1     Running   0          5m

# Проверить logs
kubectl logs -n monitoring alertmanager-0 --tail=50

# Должно содержать:
# "msg"="Completed loading of configuration file"
```

### Test 2: Verify Prometheus → AlertManager Connection

```bash
# Открыть Prometheus UI
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Перейти в браузере: http://localhost:9090/status
# Section: "Alertmanagers" должен показывать:
# - Endpoint: alertmanager.monitoring.svc.cluster.local:9093
# - State: UP
# - Last Error: (empty)
```

### Test 3: Send Test Alert to Slack

```bash
# Отправить тестовый alert в AlertManager API
curl -XPOST http://alertmanager.monitoring:9093/api/v1/alerts -d '[
  {
    "labels": {
      "alertname": "TestAlert",
      "severity": "critical",
      "service": "email"
    },
    "annotations": {
      "summary": "Test critical alert - ignore",
      "description": "This is a test alert from ТЗ-002 verification"
    },
    "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "endsAt": "'$(date -u -d '+5 minutes' +%Y-%m-%dT%H:%M:%SZ)'"
  }
]'

# Expected:
# - Через 5 секунд alert появится в Slack #incidents
# - PagerDuty создаст incident (проверить PagerDuty UI)
# - Email отправлен на oncall engineer
```

**Проверка в Slack:**
- Сообщение должно содержать:
  - 🚨 **FIRING** - TestAlert
  - Severity: critical
  - Service: email
  - Summary: Test critical alert - ignore
  - Кнопка "View in AlertManager"

### Test 4: Verify Grouping

```bash
# Отправить 3 похожих alerts одновременно
for i in {1..3}; do
  curl -XPOST http://alertmanager.monitoring:9093/api/v1/alerts -d "[
    {
      \"labels\": {
        \"alertname\": \"HighMemory\",
        \"severity\": \"warning\",
        \"pod\": \"email-service-$i\"
      },
      \"annotations\": {
        \"summary\": \"High memory on pod $i\"
      }
    }
  ]"
done

# Expected:
# - AlertManager объединит 3 alerts в ОДНО notification
# - Slack получит 1 сообщение с текстом: "3 alerts grouped: HighMemory"
```

### Test 5: Verify Inhibit Rules

```bash
# Шаг 1: Отправить EmailServiceDown (P0)
curl -XPOST http://alertmanager.monitoring:9093/api/v1/alerts -d '[
  {
    "labels": {
      "alertname": "EmailServiceDown",
      "severity": "critical",
      "service": "email"
    },
    "annotations": {
      "summary": "Service is completely down"
    }
  }
]'

# Шаг 2: Отправить SLOLatencyP99Critical (derivative alert)
curl -XPOST http://alertmanager.monitoring:9093/api/v1/alerts -d '[
  {
    "labels": {
      "alertname": "SLOLatencyP99Critical",
      "severity": "critical",
      "service": "email"
    },
    "annotations": {
      "summary": "Latency is high"
    }
  }
]'

# Expected:
# - Slack получит только 1 notification: EmailServiceDown
# - SLOLatencyP99Critical подавлен (inhibited), т.к. service down
#
# Rationale: Если сервис упал, latency alerts не имеют смысла
```

### Test 6: Verify Email Escalation (P1)

```bash
# Отправить P1 alert
curl -XPOST http://alertmanager.monitoring:9093/api/v1/alerts -d '[
  {
    "labels": {
      "alertname": "SLOAvailabilityWarning",
      "severity": "warning",
      "service": "email"
    },
    "annotations": {
      "summary": "Availability dropped to 99.5%"
    }
  }
]'

# Expected:
# - Slack #alerts получит notification (НЕ #incidents!)
# - Email отправлен на oncall@97v.ru
# - PagerDuty НЕ создает incident (только для critical)
```

---

## 📊 Monitoring After Deployment

После deployment проверить метрики AlertManager:

```bash
# Количество активных alerts
curl -s http://alertmanager.monitoring:9093/api/v1/alerts | jq '.data | length'

# Статистика notifications
curl -s http://alertmanager.monitoring:9093/metrics | grep alertmanager_notifications_total

# Expected output:
# alertmanager_notifications_total{integration="slack-critical"} 5
# alertmanager_notifications_total{integration="pagerduty-critical"} 2
# alertmanager_notifications_total{integration="email-oncall"} 8
```

---

## 🔧 Troubleshooting

### Problem: Slack notifications не приходят

**Diagnosis:**
```bash
# Проверить logs AlertManager
kubectl logs -n monitoring alertmanager-0 | grep slack

# Искать ошибки:
# - "failed to notify slack" → неверный webhook URL
# - "context deadline exceeded" → Slack недоступен
# - "invalid_payload" → проблема с форматом сообщения
```

**Fix:**
```bash
# Проверить Secret
kubectl get secret slack-webhook -n monitoring -o yaml

# Если URL неверный - пересоздать:
kubectl delete secret slack-webhook -n monitoring
kubectl create secret generic slack-webhook -n monitoring \
  --from-literal=url='https://hooks.slack.com/services/CORRECT/URL'

# Перезапустить AlertManager
kubectl rollout restart deployment/alertmanager -n monitoring
```

### Problem: PagerDuty incidents не создаются

**Diagnosis:**
```bash
# Проверить integration key в PagerDuty UI
# Services → Email Intelligence Platform → Integrations → Prometheus

# Проверить logs
kubectl logs -n monitoring alertmanager-0 | grep pagerduty
```

**Fix:**
```bash
# Verify integration key format (32 символа hex)
kubectl get secret pagerduty-key -n monitoring -o jsonpath='{.data.integration_key}' | base64 -d

# Если неверный:
kubectl delete secret pagerduty-key -n monitoring
kubectl create secret generic pagerduty-key -n monitoring \
  --from-literal=integration_key='CORRECT_32_CHAR_HEX_KEY'
```

### Problem: Emails не отправляются

**Diagnosis:**
```bash
# Проверить SMTP credentials
kubectl get secret smtp-credentials -n monitoring -o yaml

# Тест SMTP connection
kubectl run smtp-test --rm -it --restart=Never --image=alpine -- \
  sh -c "apk add --no-cache curl && curl -v smtp://smtp.gmail.com:587"
```

**Fix:**
```bash
# Если Gmail - требуется App Password, не обычный пароль
# 1. Перейти: https://myaccount.google.com/apppasswords
# 2. Создать App Password для "Mail"
# 3. Обновить Secret:

kubectl delete secret smtp-credentials -n monitoring
kubectl create secret generic smtp-credentials -n monitoring \
  --from-literal=username='alerts@97v.ru' \
  --from-literal=password='NEW_APP_PASSWORD_16_CHARS'
```

---

## 📋 Checklist перед закрытием задачи

- [ ] Все 3 Secrets созданы и валидны
- [ ] AlertManager pod в статусе Running >5 минут без restarts
- [ ] Test alert успешно доставлен в:
  - [ ] Slack #incidents (P0)
  - [ ] Slack #alerts (P1)
  - [ ] PagerDuty (P0)
  - [ ] Email oncall (P1)
- [ ] Grouping работает (несколько alerts → одно notification)
- [ ] Inhibit rules работают (derivative alerts подавляются)
- [ ] AlertManager metrics экспортируются в Prometheus
- [ ] Создана документация: "How to add new receiver" в wiki

---

## 🔗 Related Tasks

- **Previous:** [ТЗ-001: Deploy Prometheus SLO Rules](TZ-PHASE1-001-PROMETHEUS-SLO-RULES.md)
- **Next:** [ТЗ-003: Create Grafana SLO Dashboard](TZ-PHASE1-003-GRAFANA-DASHBOARD.md)
- **Dependency:** Prometheus должен отправлять alerts (проверить ТЗ-001)

---

## 📝 Notes

### AlertManager Routing Logic

```yaml
route:
  group_by: ['alertname', 'cluster']
  group_wait: 10s        # Ждать 10s перед отправкой (для grouping)
  group_interval: 10s    # Если новый alert в той же группе - подождать 10s
  repeat_interval: 12h   # Повторять notification каждые 12 часов если alert still firing
  
  routes:
    # P0: PagerDuty + Slack + Incident Webhook
    - match:
        severity: critical
      receiver: pagerduty-critical
      group_wait: 5s       # Критично - отправить быстрее
      continue: true       # Продолжить к следующим routes
    
    # P1: Slack + Email
    - match:
        severity: warning
      receiver: slack-high
      continue: true
    
    # P2: Email only
    - match:
        severity: info
      receiver: email-team
```

### Inhibit Rules Explained

```yaml
# Если EmailServiceDown firing, подавить все остальные email service alerts
inhibit_rules:
  - source_match:
      alertname: EmailServiceDown
    target_match_re:
      alertname: SLO.*|Kafka.*|Postgres.*
    equal: ['service']

# Rationale: Когда весь сервис упал, не нужны алерты про latency, throughput, etc.
```

---

**Создано:** 14 декабря 2025  
**Автор:** DevOps Team  
**Версия:** 1.0
