# 🚨 P0 INCIDENT RESPONSE RUNBOOK
**Email Intelligence Platform - Критические инциденты**

**Время реагирования:** 5 минут  
**Приоритет:** КРИТИЧЕСКИЙ  
**Эскалация:** Немедленная (PagerDuty + Slack)

---

## 📋 БЫСТРЫЕ ДЕЙСТВИЯ (Первые 5 минут)

### 1. Acknowledge инцидента
```bash
# Подтвердить получение алерта в PagerDuty
# Написать в #incidents канал Slack: "Acknowledged, investigating"
```

### 2. Быстрая диагностика (2 минуты)
```bash
# Проверить статус сервисов
kubectl get pods -n production

# Проверить логи
kubectl logs -f deployment/email-service -n production --tail=100

# Проверить Grafana dashboard
# https://grafana.97v.ru/d/email-platform-slo
```

### 3. Определить тип проблемы
- [ ] Email service down
- [ ] Availability <99%
- [ ] Latency P99 >5s
- [ ] Error rate >5%
- [ ] PostgreSQL down
- [ ] Kafka down

---

## 🔥 P0 СЦЕНАРИИ И РЕШЕНИЯ

### Сценарий 1: Email Service Down

**Симптомы:**
- `up{job="email-service"} == 0`
- Pods в статусе CrashLoopBackOff или Pending

**Диагностика:**
```bash
# Проверить статус pods
kubectl get pods -n production -l app=email-service

# Проверить events
kubectl get events -n production --sort-by='.lastTimestamp'

# Описание проблемного pod
kubectl describe pod <pod-name> -n production

# Логи pod
kubectl logs <pod-name> -n production --previous
```

**Причины и решения:**

#### 1.1 OOMKilled (Out of Memory)
```bash
# Проверить memory usage
kubectl top pods -n production

# БЫСТРОЕ РЕШЕНИЕ: Увеличить memory limits
kubectl set resources deployment email-service \
  --limits=memory=4Gi \
  -n production

# Мониторить restart
kubectl rollout status deployment/email-service -n production
```

#### 1.2 ImagePullBackOff (Проблема с Docker образом)
```bash
# Проверить образ
kubectl describe pod <pod-name> -n production | grep Image

# БЫСТРОЕ РЕШЕНИЕ: Откатиться на предыдущую версию
kubectl rollout undo deployment/email-service -n production

# Проверить rollback
kubectl rollout status deployment/email-service -n production
```

#### 1.3 CrashLoopBackOff (Приложение падает)
```bash
# Проверить логи запуска
kubectl logs <pod-name> -n production

# Частые причины:
# - Database connection failed
# - Missing environment variables
# - Port already in use

# БЫСТРОЕ РЕШЕНИЕ: Проверить connectivity
kubectl exec -it <pod-name> -n production -- ping postgres.production.svc.cluster.local

# Если БД недоступна - перейти к Сценарию 4
```

---

### Сценарий 2: Availability <99% (High Error Rate)

**Симптомы:**
- `slo:email_service:availability:ratio_rate5m < 0.99`
- Большое количество ошибок в логах

**Диагностика:**
```bash
# Проверить error rate
kubectl logs -f deployment/email-service -n production | grep ERROR

# Проверить metrics
curl -s http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query \
  --data-urlencode 'query=rate(email_service_errors_total[5m])'
```

**Причины и решения:**

#### 2.1 Database Connection Pool Exhausted
```bash
# Проверить PostgreSQL connections
kubectl exec -it postgres-0 -n production -- \
  psql -U emailuser -d emaildb -c "SELECT count(*) FROM pg_stat_activity;"

# БЫСТРОЕ РЕШЕНИЕ: Restart email-service pods (освобождает connections)
kubectl rollout restart deployment/email-service -n production

# Долгосрочное решение: Увеличить connection pool
# В app/database.py изменить max_overflow
```

#### 2.2 Kafka Consumer Lag Too High
```bash
# Проверить Kafka lag
kafka-consumer-groups --bootstrap-server kafka:9092 \
  --group email-processor \
  --describe

# БЫСТРОЕ РЕШЕНИЕ: Scale up consumers
kubectl scale deployment email-consumer --replicas=5 -n production

# Мониторить lag
watch -n 5 'kafka-consumer-groups --bootstrap-server kafka:9092 \
  --group email-processor --describe'
```

#### 2.3 Недавний Deployment (Bad Release)
```bash
# Проверить когда был последний deploy
kubectl rollout history deployment/email-service -n production

# БЫСТРОЕ РЕШЕНИЕ: Откат на стабильную версию
kubectl rollout undo deployment/email-service -n production

# Проверить recovery
watch -n 2 'kubectl get pods -n production'
```

---

### Сценарий 3: Latency P99 >5s (Critical Slowness)

**Симптомы:**
- `slo:email_service:latency:p99 > 5000`
- Пользователи испытывают тайм-ауты

**Диагностика:**
```bash
# Проверить latency distribution
# В Grafana: "Latency Percentiles" panel

# Проверить slow queries в PostgreSQL
kubectl exec -it postgres-0 -n production -- \
  psql -U emailuser -d emaildb -c \
  "SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5;"
```

**Причины и решения:**

#### 3.1 PostgreSQL Slow Queries
```bash
# БЫСТРОЕ РЕШЕНИЕ: Restart PostgreSQL (освобождает locks)
kubectl delete pod postgres-0 -n production

# Мониторить восстановление
kubectl get pods -n production -w

# После восстановления: проверить индексы
kubectl exec -it postgres-0 -n production -- \
  psql -U emailuser -d emaildb -c \
  "SELECT schemaname, tablename, indexname FROM pg_indexes WHERE tablename='emails';"
```

#### 3.2 Email Classifier Slow (LLM Inference)
```bash
# Проверить classifier latency
curl -s http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query \
  --data-urlencode 'query=rate(email_classification_duration_ms_bucket[5m])'

# БЫСТРОЕ РЕШЕНИЕ: Scale up classifier service
kubectl scale deployment email-classifier --replicas=5 -n production

# Проверить queue depth
# В Grafana: "Email Pipeline" dashboard
```

#### 3.3 Redis Cache Down
```bash
# Проверить Redis
kubectl get pods -n production | grep redis

# БЫСТРОЕ РЕШЕНИЕ: Restart Redis
kubectl delete pod redis-0 -n production

# Приложение должно работать без кэша (degraded mode)
```

---

### Сценарий 4: PostgreSQL Down

**Симптомы:**
- `up{job="postgresql"} == 0`
- Email service не может подключиться к БД

**Диагностика:**
```bash
# Проверить статус PostgreSQL pod
kubectl get pods -n production | grep postgres

# Логи PostgreSQL
kubectl logs postgres-0 -n production

# Проверить PVC (Persistent Volume)
kubectl get pvc -n production
```

**Причины и решения:**

#### 4.1 PostgreSQL Pod Crashed
```bash
# БЫСТРОЕ РЕШЕНИЕ: Restart PostgreSQL
kubectl delete pod postgres-0 -n production

# StatefulSet автоматически пересоздаст pod
# Мониторить восстановление
kubectl get pods -n production -w

# Проверить data integrity после восстановления
kubectl exec -it postgres-0 -n production -- \
  psql -U emailuser -d emaildb -c "SELECT count(*) FROM emails;"
```

#### 4.2 Disk Full (PVC заполнен)
```bash
# Проверить disk usage
kubectl exec -it postgres-0 -n production -- df -h

# БЫСТРОЕ РЕШЕНИЕ: Увеличить PVC размер
kubectl edit pvc postgres-data -n production
# Изменить spec.resources.requests.storage

# Или очистить старые данные
kubectl exec -it postgres-0 -n production -- \
  psql -U emailuser -d emaildb -c \
  "DELETE FROM emails WHERE created_at < NOW() - INTERVAL '90 days';"
```

---

### Сценарий 5: Kafka Down

**Симптомы:**
- `up{job="kafka"} == 0`
- Email pipeline остановлен

**Диагностика:**
```bash
# Проверить Kafka broker
kubectl get pods -n production | grep kafka

# Логи Kafka
kubectl logs kafka-0 -n production

# Проверить zookeeper
kubectl get pods -n production | grep zookeeper
```

**Причины и решения:**

#### 5.1 Kafka Broker Crashed
```bash
# БЫСТРОЕ РЕШЕНИЕ: Restart Kafka
kubectl delete pod kafka-0 -n production

# Мониторить восстановление
kubectl get pods -n production -w

# Проверить топики после восстановления
kubectl exec -it kafka-0 -n production -- \
  kafka-topics --bootstrap-server localhost:9092 --list
```

#### 5.2 Zookeeper Down
```bash
# Restart Zookeeper
kubectl delete pod zookeeper-0 -n production

# Kafka автоматически переподключится
```

---

## 🔄 УНИВЕРСАЛЬНАЯ ПРОЦЕДУРА ОТКАТА

Если не можете быстро определить проблему:

```bash
# 1. Откат на предыдущую версию
kubectl rollout undo deployment/email-service -n production

# 2. Проверить восстановление availability
watch -n 5 'curl -s http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query \
  --data-urlencode "query=slo:email_service:availability:ratio_rate5m"'

# 3. Если availability восстановилась - проблема в новом deploy
# Создать post-mortem и запланировать исправление

# 4. Если availability НЕ восстановилась - проблема в инфраструктуре
# Проверить все зависимости: PostgreSQL, Kafka, Redis
```

---

## 📊 МОНИТОРИНГ ВОССТАНОВЛЕНИЯ

После применения fix:

```bash
# 1. Проверить availability каждые 30 секунд
watch -n 30 'curl -s http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query \
  --data-urlencode "query=slo:email_service:availability:ratio_rate5m"'

# 2. Проверить latency
watch -n 30 'curl -s http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query \
  --data-urlencode "query=slo:email_service:latency:p99"'

# 3. Проверить error rate
watch -n 30 'kubectl logs -f deployment/email-service -n production | grep ERROR | wc -l'

# 4. Когда SLO восстановлены:
# - Обновить инцидент в #incidents канале
# - Написать в PagerDuty "Resolved"
# - Начать post-mortem анализ
```

---

## 📞 ЭСКАЛАЦИЯ

Если не можете решить за 15 минут:

1. **Технический Lead:** @tech-lead в Slack
2. **CTO:** Телефон +7-XXX-XXX-XXXX
3. **Внешняя поддержка:** support@vendor.com

---

## 📝 POST-MORTEM

После решения P0 инцидента ОБЯЗАТЕЛЬНО:

1. Создать post-mortem документ
2. Указать:
   - Root cause
   - Timeline
   - Impact (сколько пользователей затронуто)
   - Решение
   - Action items для предотвращения
3. Провести post-mortem meeting (в течение 24ч)

**Шаблон:** `docs/POST_MORTEM_TEMPLATE.md`

---

**Последнее обновление:** 14 декабря 2025 г.  
**Версия:** 1.0  
**Автор:** DevOps Team
