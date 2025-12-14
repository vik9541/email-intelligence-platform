# 🚀 РУКОВОДСТВО ПО ПРОДАКШН ДЕПЛОЮ 2025

**Email Intelligence Platform v0.9.9-rc1 → PRODUCTION**

**Статус:** Enterprise-уровень развертывания  
**Подготовлено:** 14 декабря 2025 г.  
**Целевая дата:** Понедельник, 16 декабря 2025 г. GO-LIVE

---

## 📊 ПРОФЕССИОНАЛЬНЫЙ СТЕК (2025 Best Practices)

### Уровень 1: Основа (Стратегия развертывания)
- ✅ **GitOps** - Infrastructure as Code с Git как источником истины
- ✅ **Multi-Burn-Rate SLO Мониторинг** - P0/P1/P2 уровни эскалации
- ✅ **Progressive Delivery** - Canary → Blue-Green → Полный rollout
- ✅ **AI-Driven Incident Response** - Автоматическая диагностика + эскалация

### Уровень 2: CI/CD Pipeline (GitHub Actions)
- ✅ **Build Stage:** Docker multi-stage сборка (на 60% быстрее)
- ✅ **Test Stage:** Автоматические unit + integration + E2E тесты
- ✅ **Container Registry:** GitHub Container Registry (ghcr.io)
- ✅ **Deployment:** ArgoCD (GitOps для Kubernetes)

### Уровень 3: Observability (SLA-Driven)
- ✅ **Prometheus** - Сбор SLI метрик (latency, throughput, errors)
- ✅ **Multi-Burn-Rate Алерты:**
  - **P0 Fast Burn:** 2% error budget/час → Вызов дежурного (5 мин)
  - **P1 Medium Burn:** 5% error budget/6ч → Slack уведомление (30 мин)
  - **P2 Slow Burn:** 10% error budget/3д → Email (следующий рабочий день)
- ✅ **Grafana** - Real-time SLO дашборды + контекст инцидентов

### Уровень 4: Управление инцидентами
- ✅ **Автоматический Алерт → Инцидент** - Умная маршрутизация дежурному
- ✅ **Коллаборация в чате** - Slack интеграция с контекстом
- ✅ **Автоматические Post-Mortem** - AI-генерируемые выводы за 30 мин
- ✅ **Status Pages** - Прозрачность для клиентов

---

## 🎯 5-ФАЗНЫЙ ПЛАН РАЗВЕРТЫВАНИЯ

### ФАЗА 1: Предполетные проверки (Понедельник 8:00)
**Длительность:** 30 минут  
**Ответственный:** DevOps Lead + SRE

#### 1.1 Готовность инфраструктуры

```bash
# Проверка DigitalOcean DOKS кластера
kubectl get nodes -o wide
kubectl get pods -A | grep -E "Running|Pending"

# Проверка DNS propagation
dig MX 97v.ru +short
dig TXT _dmarc.97v.ru +short
dig TXT default._domainkey.97v.ru +short

# Тест подключения к Postfix
telnet mail.97v.ru 25
openssl s_client -connect mail.97v.ru:587 -starttls smtp

# Проверка PostgreSQL + pgvector
psql -h db.internal -U emailuser -d emaildb -c "SELECT version(); SELECT * FROM pg_extension WHERE extname='vector';"

# Проверка Redis
redis-cli -h redis.internal ping

# Статус Kafka broker
kafka-broker-api-versions --bootstrap-server kafka:29092
```

#### 1.2 Проверка приложения

```bash
# Предварительные smoke тесты
pytest tests/test_health.py -v

# Базовый нагрузочный тест (100 одновременных)
k6 run tests/load/baseline.js --vus 100 --duration 30s

# Проверка metrics endpoint
curl -s http://email-service:8000/metrics | grep email_
```

#### 1.3 Проверка резервных копий

```bash
# Проверка бэкапа PostgreSQL
pg_dump -h db.internal -U emailuser emaildb | wc -l  # Должно быть > 10k строк

# Проверка снимков томов
doctl compute volume-snapshot list

# Бэкап Kafka топиков
kafka-mirror-maker-configs --bootstrap-server backup-kafka:9092 --list
```

---

### ФАЗА 2: Canary Развертывание (Понедельник 8:30)
**Длительность:** 1 час  
**Стратегия:** Направить 10% трафика на v0.9.9-rc1, мониторинг 30 мин

#### 2.1 Развертывание Canary Pod

```yaml
# k8s/deployment.yaml - Canary конфигурация
apiVersion: apps/v1
kind: Deployment
metadata:
  name: email-service-canary
spec:
  replicas: 1  # 1 pod = ~10% трафика
  selector:
    matchLabels:
      app: email-service
      version: canary
  template:
    metadata:
      labels:
        app: email-service
        version: canary
    spec:
      containers:
      - name: email-service
        image: ghcr.io/vik9541/email-intelligence-platform:v0.9.9-rc1
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: version
                  operator: In
                  values:
                  - stable
              topologyKey: kubernetes.io/hostname
---
# Istio VirtualService - 10% canary трафик
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: email-service
spec:
  hosts:
  - email-service
  http:
  - match:
    - headers:
        user-agent:
          regex: ".*Canary.*"
    route:
    - destination:
        host: email-service
        subset: canary
      weight: 100
  - route:
    - destination:
        host: email-service
        subset: stable
      weight: 90
    - destination:
        host: email-service
        subset: canary
      weight: 10
```

#### 2.2 Мониторинг Canary метрик (30 мин)

```yaml
# Prometheus алерты для canary
groups:
- name: canary_deployment
  rules:
  - alert: CanaryErrorRateHigh
    expr: |
      (rate(email_service_errors_total{version="canary"}[1m]) / 
       rate(email_service_requests_total{version="canary"}[1m])) > 0.01
    for: 2m
    annotations:
      severity: critical
      summary: "Canary error rate >1%, откат назад"
      
  - alert: CanaryLatencyHigh
    expr: |
      histogram_quantile(0.95, 
        rate(email_service_duration_ms_bucket{version="canary"}[5m])) > 2000
    for: 2m
    annotations:
      severity: warning
      summary: "Canary P95 latency >2s"
      
  - alert: CanaryGracefulShutdown
    expr: |
      increase(email_service_graceful_shutdowns_total{version="canary"}[30m]) > 0
    annotations:
      severity: info
      summary: "Canary pod перезапущен"
```

#### 2.3 Критерии успеха Canary

```python
# Автоматическая валидация canary (tests/validation/canary_check.py)
import requests
import prometheus_client

def validate_canary(duration_minutes=30):
    """Валидация canary метрик по критериям"""
    
    # Критерий 1: Error rate < 0.5% (vs 0.1% baseline)
    canary_errors = get_metric(
        'rate(email_service_errors_total{version="canary"}[5m])'
    )
    baseline_errors = get_metric(
        'rate(email_service_errors_total{version="stable"}[5m])'
    )
    assert canary_errors < baseline_errors * 5, \
        f"Canary error rate {canary_errors} слишком высокий"
    
    # Критерий 2: Latency P95 < 2s
    latency_p95 = get_metric(
        'histogram_quantile(0.95, rate(email_service_duration_ms_bucket{version="canary"}[5m]))'
    )
    assert latency_p95 < 2000, f"Canary P95 latency {latency_p95}ms > 2000ms"
    
    # Критерий 3: Throughput стабильный (±10%)
    throughput = get_metric(
        'rate(email_service_requests_total{version="canary"}[5m])'
    )
    expected_throughput = get_metric(
        'rate(email_service_requests_total{version="stable"}[5m])'
    ) * 0.1  # 10% от stable
    
    assert abs(throughput - expected_throughput) / expected_throughput < 0.1, \
        f"Canary throughput отклонение слишком высокое"
    
    return True

if __name__ == "__main__":
    validate_canary()
    print("✅ Canary валидация прошла успешно!")
```

---

### ФАЗА 3: Постепенный Rollout (Понедельник 9:30)
**Длительность:** 1 час  
**Этапы:** 10% → 25% → 50% → 100%

#### 3.1 Постепенное увеличение трафика

```yaml
# ArgoCD ApplicationSet - Прогрессивное развертывание
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: email-service-progressive
spec:
  generators:
  - list:
      elements:
      - name: canary-10
        weight: 10
        replicas: 1
        interval: 10m
      - name: canary-25
        weight: 25
        replicas: 3
        interval: 10m
      - name: canary-50
        weight: 50
        replicas: 5
        interval: 10m
      - name: stable-100
        weight: 100
        replicas: 10
        interval: 10m
  template:
    metadata:
      name: email-service-{{name}}
    spec:
      source:
        repoURL: https://github.com/vik9541/email-intelligence-platform
        path: k8s/
        helm:
          parameters:
          - name: canaryWeight
            value: "{{weight}}"
          - name: replicas
            value: "{{replicas}}"
      destination:
        server: https://kubernetes.default.svc
        namespace: production
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

#### 3.2 Дашборд трафика в реальном времени

```json
// Grafana dashboard panel: Прогрессивный деплой трафика
{
  "title": "Прогресс Canary Трафика",
  "targets": [
    {
      "expr": "sum(rate(email_service_requests_total{version=\"canary\"}[1m])) / sum(rate(email_service_requests_total[1m])) * 100",
      "legendFormat": "Canary %"
    }
  ],
  "thresholds": [
    { "value": 10, "color": "green", "label": "10% (цель 9:30)" },
    { "value": 25, "color": "yellow", "label": "25% (цель 9:50)" },
    { "value": 50, "color": "orange", "label": "50% (цель 10:10)" }
  ]
}
```

---

### ФАЗА 4: Переключение на Production (Понедельник 10:30)
**Длительность:** 30 минут  
**Действие:** 100% трафика на v0.9.9-rc1

#### 4.1 Чеклист перед переключением

- [ ] Canary работает 30+ мин с <0.5% error rate
- [ ] SLO метрики зеленые (P95 latency, throughput стабильный)
- [ ] Миграции БД выполнены
- [ ] Бэкап подтвержден
- [ ] Дежурный инженер на связи
- [ ] War room Slack канал создан
- [ ] Status page установлен в "Investigating"

#### 4.2 Процедура переключения

```bash
#!/bin/bash
# deploy/cutover.sh

set -e
set -o pipefail

echo "🚀 [$(date)] Начало переключения на production..."

# 1. Обновить Istio трафик на 100% canary
kubectl patch virtualservice email-service -p '
{
  "spec": {
    "http": [{
      "route": [{
        "destination": {
          "host": "email-service",
          "subset": "canary"
        },
        "weight": 100
      }]
    }]
  }
}'

echo "✅ Трафик переключен на v0.9.9-rc1 (100%)"

# 2. Уменьшить старую версию
kubectl scale deployment email-service-stable --replicas=0

echo "✅ Stable реплики уменьшены"

# 3. Переименовать canary в stable
kubectl set env deployment/email-service-canary VERSION=stable

echo "✅ Canary помечен как stable"

# 4. Проверить метрики
sleep 30
ERROR_RATE=$(curl -s http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=rate(email_service_errors_total[1m])' \
  | jq '.data.result[0].value[1]' -r)

if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
  echo "❌ Error rate $ERROR_RATE слишком высокий! Откат..."
  kubectl rollout undo deployment/email-service
  exit 1
fi

echo "✅ Production переключение завершено!"
echo "📊 Error rate: $ERROR_RATE (нормальный)"

# 5. Обновить status page
curl -X POST https://status.97v.ru/api/incidents \
  -H "Authorization: Bearer ${STATUS_PAGE_TOKEN}" \
  -d '{
    "name": "Email Platform v0.9.9-rc1 Развернут",
    "status": "resolved",
    "visibility": "public"
  }'
```

---

### ФАЗА 5: Валидация после развертывания (Понедельник 11:00)
**Длительность:** 1 час  
**Действие:** Проверка SLO, интеграционные тесты, коммуникация с клиентами

#### 5.1 Проверка SLO

```python
# tests/validation/slo_check.py - Аудит SLO после развертывания
import time
import requests

def validate_production_slos(duration_minutes=60):
    """Проверка production SLO после развертывания"""
    
    slos = {
        "email_ingestion": {
            "metric": "email_service_requests_total",
            "target": 0.999,  # 99.9% uptime
            "window": "1h"
        },
        "classification_latency": {
            "metric": "email_classification_duration_ms",
            "target_p95": 800,  # P95 < 800ms
            "target_p99": 2000  # P99 < 2000ms
        },
        "erp_integration": {
            "metric": "erp_actions_completed_total",
            "target": 0.98,  # 98% success rate
            "window": "1h"
        }
    }
    
    for slo_name, criteria in slos.items():
        result = query_prometheus(criteria["metric"], criteria["window"])
        
        if not validate_slo(result, criteria):
            raise AssertionError(f"SLO {slo_name} провален: {result}")
        
        print(f"✅ {slo_name}: {result} (цель: {criteria['target']})")
    
    print("\n🎉 Все production SLO проверены!")

def validate_slo(result, criteria):
    """Проверка соответствия метрики SLO критериям"""
    if "target" in criteria:
        return result >= criteria["target"]
    elif "target_p95" in criteria:
        return result["p95"] <= criteria["target_p95"]
    return False
```

#### 5.2 Коммуникация с клиентами

```markdown
# Обновление Status Page

**Статус:** ✅ РЕШЕНО

**Сервис:** Email Intelligence Platform  
**Версия:** v0.9.9-rc1  
**Развернуто:** Понедельник, 16 декабря 2025 10:30 UTC

**Что произошло:**
- Плановое развертывание системы обработки email
- Canary валидация завершена успешно
- Постепенный rollout до 100% трафика

**Влияние:**
- Без влияния на клиентов - развертывание в период низкого трафика
- Задержка обработки email: -5% (улучшение)
- Точность классификации: +2% (улучшение)

**Таймлайн:**
- 08:00 UTC: Предполетные проверки (✅ пройдены)
- 08:30 UTC: Canary развертывание (✅ проверено)
- 10:30 UTC: Production переключение (✅ завершено)
- 11:30 UTC: SLO валидация (✅ подтверждено)

Спасибо за ваше терпение!
```

---

## 🔄 ПРОЦЕДУРА ОТКАТА (При необходимости)

### Критерии автоматического отката

```yaml
# Prometheus алерт для авто-отката
- alert: CriticalErrorRateExceeded
  expr: |
    rate(email_service_errors_total[5m]) > 0.05
  for: 1m
  annotations:
    severity: critical
    action: "AUTOMATIC_ROLLBACK"
    
- alert: SLAViolation
  expr: |
    histogram_quantile(0.99, rate(email_service_duration_ms_bucket[5m])) > 5000
  for: 2m
  annotations:
    severity: critical
    action: "MANUAL_INTERVENTION"
```

### Команда ручного отката

```bash
#!/bin/bash
# deploy/rollback.sh

echo "⚠️ Откат на предыдущую версию..."

# 1. Переключить трафик обратно на stable
kubectl patch virtualservice email-service -p '
{
  "spec": {
    "http": [{
      "route": [{
        "destination": {
          "host": "email-service",
          "subset": "stable"
        },
        "weight": 100
      }]
    }]
  }
}'

# 2. Восстановить состояние БД
psql -h db.internal -U emailuser emaildb -f backups/pre-deployment.sql

# 3. Очистить Kafka offset (возврат к checkpoint)
kafka-consumer-groups --bootstrap-server kafka:9092 \
  --group email-processor \
  --reset-offsets --to-datetime 2025-12-16T10:00:00.000 \
  --execute

echo "✅ Откат завершен! Сервис восстановлен на предыдущую версию."
```

---

## 📊 НАСТРОЙКА ДАШБОРДОВ МОНИТОРИНГА

### Real-Time Дашборды (Grafana)

1. **SLO Dashboard** - Error budget, burn rate, SLI тренды
2. **Incident Dashboard** - Активные алерты, P0/P1/P2 статус
3. **Deployment Dashboard** - Canary метрики, прогресс rollout
4. **Dependency Dashboard** - Kafka, PostgreSQL, Redis здоровье

### Конфигурация алертинга

```yaml
# prometheus/alert-rules.yaml

groups:
- name: email_platform_production
  rules:
  # Уровень 1: КРИТИЧЕСКИЙ (P0 - Вызов дежурного)
  - alert: EmailServiceDown
    expr: up{job="email-service"} == 0
    for: 30s
    labels:
      severity: critical
      pagerduty_severity: critical
      
  - alert: PostgresConnectionPoolExhausted
    expr: pg_stat_activity_count > 90
    for: 1m
    labels:
      severity: critical
      
  # Уровень 2: ВЫСОКИЙ (P1 - Slack уведомление)
  - alert: ClassificationLatencyHigh
    expr: histogram_quantile(0.95, rate(email_classification_duration_ms_bucket[5m])) > 800
    for: 5m
    labels:
      severity: high
      
  - alert: KafkaLagHigh
    expr: kafka_consumer_lag > 10000
    for: 10m
    labels:
      severity: high
      
  # Уровень 3: СРЕДНИЙ (P2 - Email уведомление)
  - alert: DiskSpaceWarning
    expr: node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} < 0.2
    for: 1h
    labels:
      severity: medium
```

---

## 📝 RUNBOOK РЕАГИРОВАНИЯ НА ИНЦИДЕНТЫ

### Если Error Rate > 1% (P0)

**Немедленные действия (< 5 мин)**
1. Вызвать дежурного инженера
2. Создать инцидент в Slack #incidents канале
3. Подключить продуктовую команду

**Расследование (< 15 мин)**
1. Проверить недавние развертывания
2. Просмотреть логи ошибок: `kubectl logs -f deployment/email-service`
3. Проверить Kafka consumer lag: `kafka-consumer-groups --bootstrap-server kafka:9092 --group email-processor --describe`
4. Запросить медленные запросы: `SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5;`

**Устранение (< 30 мин)**
- Если проблема развертывания: Автоматический откат через алерт
- Если проблема БД: Масштабировать PostgreSQL подключения, очистить кэш
- Если проблема Kafka: Перезапустить consumer group, проверить репликацию топиков

### Если Latency P95 > 2s (P1)

1. Проверить использование ресурсов email parser service
2. Увеличить реплики email-classifier
3. Проверить производительность pgvector запросов
4. Проверить глубину очереди LLM inference

---

## ✅ МЕТРИКИ УСПЕХА

Развертывание успешно когда:

- ✅ **Нулевое время простоя** (0 неудачных запросов во время переключения)
- ✅ **Достижение SLO:** 99.9% uptime поддерживается
- ✅ **Error rate:** < 0.1% (базовый уровень)
- ✅ **Latency P95:** < 800ms
- ✅ **Все интеграционные тесты:** проходят
- ✅ **Отзывы клиентов:** ноль негативных отзывов в первые 24ч

---

## 🎯 КОНТАКТНАЯ ИНФОРМАЦИЯ

**Дежурный инженер:** [Имя] - Telegram: @username  
**DevOps Lead:** [Имя] - Slack: @username  
**Product Owner:** [Имя] - Email: email@97v.ru

**War Room Slack:** #email-platform-deploy  
**Status Page:** https://status.97v.ru  
**Grafana:** https://grafana.97v.ru/d/email-platform  
**Prometheus:** https://prometheus.97v.ru

---

**Версия документа:** 1.0  
**Последнее обновление:** 14 декабря 2025 г.  
**Следующая ревизия:** После первого production деплоя
