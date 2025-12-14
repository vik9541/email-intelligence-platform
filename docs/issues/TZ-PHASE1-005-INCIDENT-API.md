# ТЗ-005: Deploy Incident Response API [Phase 1]

**Статус:** 🔴 Not Started  
**Приоритет:** P1 (High - Incident Management)  
**Оценка времени:** 2.5h  
**Сложность:** MEDIUM  
**Владелец:** Backend  
**Sprint:** Phase 1 - Production Monitoring Stack  

---

## 📋 Context (Контекст)

Incident Response API - автоматическая система управления инцидентами. Интегрируется с AlertManager через webhook для:

- **Auto-создания инцидентов** из P0/P1 alerts
- **Диагностики проблем** (проверка подов, метрик, зависимостей)
- **Автоматических исправлений** (restart, scale, cleanup)
- **Эскалации в PagerDuty/Slack** для critical incidents

Файл `app/api/incident_response.py` уже создан и содержит:
- 5 REST endpoints для управления инцидентами
- Auto-remediation логику
- Интеграцию с Prometheus для diagnostics
- PagerDuty/Slack escalation

**Зависимости:**
- ✅ Файл `app/api/incident_response.py` создан (commit 49e37eb)
- ✅ Kubernetes manifest `k8s/incident-api.yaml` создан
- ⏸️ **Требуется:** PostgreSQL database для incident storage
- ⏸️ **Требуется:** Slack webhook URL, PagerDuty API key

---

## ✅ Requirements (Требования)

### 1. Миграция с in-memory storage на PostgreSQL

Текущий код использует `incidents: Dict[str, Incident] = {}`. Нужно заменить на PostgreSQL:

**A. Создать Alembic migration**

```bash
# Создать новую миграцию
alembic revision -m "add_incidents_table"
```

**B. Создать таблицу incidents**

```python
# alembic/versions/xxx_add_incidents_table.py

def upgrade():
    op.create_table(
        'incidents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('alert_name', sa.String(100), nullable=False),
        sa.Column('priority', sa.Enum('P0', 'P1', 'P2', name='incident_priority')),
        sa.Column('status', sa.Enum('open', 'investigating', 'resolved', 'closed', name='incident_status')),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.Column('summary', sa.Text),
        sa.Column('description', sa.Text),
        sa.Column('diagnostics', sa.JSON),
        sa.Column('remediation_actions', sa.JSON),
        sa.Index('idx_incidents_status', 'status'),
        sa.Index('idx_incidents_priority', 'priority'),
        sa.Index('idx_incidents_created_at', 'created_at')
    )
```

**C. Обновить код для работы с PostgreSQL**

```python
# app/api/incident_response.py

from sqlalchemy import select, update
from app.database import get_db
from app.models.incident import Incident as IncidentModel

@router.post("/webhook/alert")
async def alertmanager_webhook(
    alert_payload: dict,
    db: AsyncSession = Depends(get_db)
):
    # Создать инцидент в БД вместо in-memory dict
    incident = IncidentModel(
        id=str(uuid.uuid4()),
        alert_name=alert_payload['labels']['alertname'],
        priority=determine_priority(alert_payload),
        status='open',
        summary=alert_payload['annotations'].get('summary', ''),
        description=alert_payload['annotations'].get('description', ''),
        diagnostics={},
        remediation_actions=[]
    )
    
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    
    # Background task для diagnostics
    background_tasks.add_task(run_diagnostics, incident.id, db)
    
    return {"incident_id": incident.id}
```

### 2. Настроить Secrets для Slack и PagerDuty

```bash
# Slack webhook
kubectl create secret generic slack-webhook -n production \
  --from-literal=url='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

# PagerDuty API key
kubectl create secret generic pagerduty-key -n production \
  --from-literal=api_key='YOUR_PAGERDUTY_API_KEY'

# API token для authentication
kubectl create secret generic incident-api-token -n production \
  --from-literal=token='$(openssl rand -hex 32)'
```

### 3. Deploy Incident Response API

```bash
# Применить Kubernetes manifest
kubectl apply -f k8s/incident-api.yaml -n production

# Verify: Pods running
kubectl get pods -n production -l app=incident-api

# Expected output:
# NAME                            READY   STATUS    RESTARTS   AGE
# incident-api-abc123            1/1     Running   0          30s
# incident-api-def456            1/1     Running   0          30s
```

### 4. Настроить AlertManager webhook

Обновить `prometheus/alertmanager.yml` для отправки alerts в Incident API:

```yaml
receivers:
  - name: 'incident-webhook'
    webhook_configs:
      - url: 'http://incident-api.production.svc.cluster.local:8080/webhook/alert'
        send_resolved: true
        http_config:
          bearer_token_file: /etc/alertmanager/secrets/incident-api-token/token
```

```bash
# Применить обновленную конфигурацию
kubectl apply -f prometheus/alertmanager.yml -n monitoring

# Перезапустить AlertManager
kubectl rollout restart deployment/alertmanager -n monitoring
```

### 5. Создать Service для доступа к API

```yaml
# k8s/incident-api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: incident-api
  namespace: production
spec:
  type: ClusterIP
  selector:
    app: incident-api
  ports:
    - port: 8080
      targetPort: 8080
      protocol: TCP
```

```bash
kubectl apply -f k8s/incident-api-service.yaml -n production
```

---

## ✅ Acceptance Criteria (Критерии приемки)

- [x] **AC1:** PostgreSQL migration применена и таблица `incidents` создана
- [x] **AC2:** In-memory storage заменен на PostgreSQL в коде
- [x] **AC3:** Secrets созданы для Slack, PagerDuty, API token
- [x] **AC4:** Incident API pods running (2 replicas) в production namespace
- [x] **AC5:** Service `incident-api` создан и доступен по ClusterIP
- [x] **AC6:** AlertManager успешно отправляет webhooks в Incident API
- [x] **AC7:** Test alert создает инцидент в БД
- [x] **AC8:** P0 incidents автоматически эскалируются в PagerDuty
- [x] **AC9:** Diagnostics выполняются в background и сохраняются в БД

---

## 🧪 How to Test (Как тестировать)

### Test 1: Verify API Health

```bash
# Проверить health endpoint
kubectl run curl-test --rm -it --restart=Never --image=curlimages/curl -- \
  curl http://incident-api.production.svc.cluster.local:8080/health

# Expected output:
# {"status": "healthy", "database": "connected"}
```

### Test 2: Create Incident via Webhook

```bash
# Отправить тестовый alert через AlertManager
curl -XPOST http://alertmanager.monitoring:9093/api/v1/alerts -d '[
  {
    "labels": {
      "alertname": "TestIncident",
      "severity": "critical",
      "service": "email"
    },
    "annotations": {
      "summary": "Test incident creation",
      "description": "This is a test"
    }
  }
]'

# Подождать 5 секунд (webhook delay)
sleep 5

# Проверить что инцидент создан
kubectl run psql-test --rm -it --restart=Never --image=postgres:14 -- \
  psql -h postgres.production -U postgres -d email_db -c \
  "SELECT id, alert_name, priority, status FROM incidents WHERE alert_name='TestIncident'"

# Expected output:
#             id           | alert_name   | priority | status
# ------------------------+-------------+----------+--------
#  uuid-here              | TestIncident | P0       | open
```

### Test 3: Verify Diagnostics Run

```bash
# Создать инцидент (см. Test 2)

# Подождать 30 секунд для background task
sleep 30

# Проверить что diagnostics заполнены
curl http://incident-api.production:8080/incidents/{incident_id} | jq .diagnostics

# Expected output:
# {
#   "pods": {
#     "email-service": {
#       "ready": "3/3",
#       "status": "Running"
#     }
#   },
#   "metrics": {
#     "availability": 0.999,
#     "latency_p95": 450
#   },
#   "dependencies": {
#     "kafka": "up",
#     "postgres": "up"
#   }
# }
```

### Test 4: Verify Auto-Remediation

```bash
# Создать инцидент с высоким Kafka lag
# (Incident API должен автоматически увеличить replicas)

# Шаг 1: Создать Kafka lag
kubectl scale deployment email-service -n production --replicas=0
# (генерируем backlog как в ТЗ-004)

# Шаг 2: Создать alert
curl -XPOST http://alertmanager.monitoring:9093/api/v1/alerts -d '[
  {
    "labels": {
      "alertname": "KafkaConsumerLagHigh",
      "severity": "warning"
    },
    "annotations": {
      "summary": "Kafka lag >15000"
    }
  }
]'

# Шаг 3: Подождать remediation
sleep 60

# Шаг 4: Проверить что replicas увеличились
kubectl get deployment email-service -n production

# Expected: READY 6/6 (auto-scaled)

# Шаг 5: Проверить remediation_actions в БД
curl http://incident-api.production:8080/incidents/{incident_id} | jq .remediation_actions

# Expected:
# [
#   {
#     "action": "scale_deployment",
#     "target": "email-service",
#     "from": 1,
#     "to": 6,
#     "timestamp": "2025-12-14T10:30:00Z",
#     "success": true
#   }
# ]
```

### Test 5: Verify PagerDuty Escalation

```bash
# Создать P0 incident
curl -XPOST http://alertmanager.monitoring:9093/api/v1/alerts -d '[
  {
    "labels": {
      "alertname": "EmailServiceDown",
      "severity": "critical"
    },
    "annotations": {
      "summary": "Service completely down"
    }
  }
]'

# Проверить PagerDuty UI
# Должен быть создан новый incident:
# - Title: "EmailServiceDown - Service completely down"
# - Urgency: High
# - Assigned to: Current on-call engineer
```

### Test 6: List and Filter Incidents

```bash
# Получить все открытые инциденты
curl http://incident-api.production:8080/incidents?status=open | jq

# Получить только P0 инциденты
curl http://incident-api.production:8080/incidents?priority=P0 | jq

# Получить инциденты за последние 24 часа
curl "http://incident-api.production:8080/incidents?since=$(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%SZ)" | jq
```

---

## 📊 Monitoring After Deployment

```bash
# Dashboard для мониторинга Incident API
watch -n 30 '
  echo "=== Active Incidents ==="
  curl -s http://incident-api.production:8080/incidents?status=open | jq "length"
  
  echo ""
  echo "=== Incidents by Priority (last 24h) ==="
  curl -s http://prometheus.monitoring:9090/api/v1/query?query=incidents_total | jq
  
  echo ""
  echo "=== Auto-Remediation Success Rate ==="
  curl -s http://incident-api.production:8080/metrics | grep remediation_success_rate
  
  echo ""
  echo "=== API Health ==="
  kubectl get pods -n production -l app=incident-api
'
```

---

## 🔧 Troubleshooting

### Problem: Webhooks не создают incidents

**Diagnosis:**
```bash
# Проверить logs Incident API
kubectl logs -n production -l app=incident-api --tail=50

# Искать:
# - "Received webhook" → webhook пришел
# - "Error creating incident" → проблема с БД
# - "Unauthorized" → неверный API token
```

**Fix:**
```bash
# Проверить AlertManager config
kubectl get configmap alertmanager-config -n monitoring -o yaml | grep incident-api

# Должен быть:
# - url: http://incident-api.production:8080/webhook/alert
# - bearer_token_file: /etc/alertmanager/secrets/incident-api-token/token

# Если неверно - исправить и перезапустить AlertManager
```

### Problem: Diagnostics не заполняются

**Diagnosis:**
```bash
# Проверить background tasks
kubectl logs -n production -l app=incident-api | grep "Running diagnostics"

# Если нет логов → background tasks не запускаются
```

**Fix:**
```python
# Проверить что FastAPI BackgroundTasks используется правильно
# app/api/incident_response.py

@router.post("/webhook/alert")
async def alertmanager_webhook(
    alert_payload: dict,
    background_tasks: BackgroundTasks  # ← ВАЖНО: это параметр функции
):
    # ...
    background_tasks.add_task(run_diagnostics, incident_id)
```

### Problem: PagerDuty incidents не создаются

**Diagnosis:**
```bash
# Проверить Secret
kubectl get secret pagerduty-key -n production -o jsonpath='{.data.api_key}' | base64 -d

# Проверить logs
kubectl logs -n production -l app=incident-api | grep pagerduty
```

**Fix:**
```bash
# Verify PagerDuty API key format
# Должен быть: длинный hex string (64+ символов)

# Test PagerDuty API manually
curl -X POST https://api.pagerduty.com/incidents \
  -H "Authorization: Token token=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "incident": {
      "type": "incident",
      "title": "Test incident",
      "service": {
        "id": "SERVICE_ID",
        "type": "service_reference"
      }
    }
  }'
```

---

## 📋 Checklist перед закрытием задачи

- [ ] PostgreSQL migration применена
- [ ] In-memory storage полностью заменен на PostgreSQL
- [ ] Secrets созданы для Slack, PagerDuty, API token
- [ ] Incident API pods running (2 replicas)
- [ ] Service создан и доступен
- [ ] AlertManager webhook настроен и работает
- [ ] Test incidents создаются в БД
- [ ] Diagnostics заполняются автоматически
- [ ] Auto-remediation работает (хотя бы 1 успешный случай)
- [ ] PagerDuty escalation работает для P0
- [ ] Slack notifications приходят
- [ ] Создана документация: "Incident Management Process" в wiki

---

## 🔗 Related Tasks

- **Previous:** [ТЗ-004: Implement Self-Healing Automaton](TZ-PHASE1-004-SELF-HEALING.md)
- **Next:** [ТЗ-006: Create Monitoring Dashboard Script](TZ-PHASE1-006-MONITOR-SCRIPT.md)
- **Integration with:** ТЗ-004 (Self-Healing автоматически создает incidents через этот API)

---

## 📝 Notes

### Incident Lifecycle

```
Alert Fired → Incident Created (open)
              ↓
          Diagnostics Running (investigating)
              ↓
          Auto-Remediation Attempted
              ↓
          ├→ Success → Incident Resolved (resolved)
              ↓
          └→ Failure → Escalate to PagerDuty (investigating)
              ↓
          Manual Resolution → Incident Closed (closed)
```

### Auto-Remediation Logic

```python
# app/api/incident_response.py

async def attempt_remediation(incident_id: str):
    if incident.alert_name == "KafkaConsumerLagHigh":
        await scale_deployment("email-service", replicas=6)
    
    elif incident.alert_name == "PostgreSQLConnectionsHigh":
        await cleanup_postgres_connections()
    
    elif incident.alert_name == "DiskSpaceLow":
        await cleanup_old_logs()
    
    # ... более 10 remediation scenarios
```

### Integration Points

- **AlertManager** → Incident API (webhook)
- **Incident API** → PagerDuty (escalation)
- **Incident API** → Slack (notifications)
- **Incident API** → Prometheus (diagnostics queries)
- **Incident API** → Kubernetes (remediation actions)
- **Self-Healing Automaton** → Incident API (create incidents for healing actions)

---

**Создано:** 14 декабря 2025  
**Автор:** Backend Team  
**Версия:** 1.0
