# ТЗ-004: Implement Self-Healing Automaton [Phase 1]

**Статус:** 🔴 Not Started  
**Приоритет:** P1 (High - Automation)  
**Оценка времени:** 3h  
**Сложность:** HIGH  
**Владелец:** Backend/DevOps  
**Sprint:** Phase 1 - Production Monitoring Stack  

---

## 📋 Context (Контекст)

Self-Healing Automaton - автономная система для автоматического устранения типовых проблем production окружения. Файл `app/services/self_healing_automaton.py` уже создан и содержит логику для:

- **Kafka consumer lag >15k** → Auto-scale consumers
- **PostgreSQL connections >85%** → Cleanup idle connections
- **Pod OOMKilled/CrashLoop** → Increase memory limits
- **Disk space >85%** → Cleanup old logs
- **Pod restart loops** → Restart deployment

**Цель:** Снизить MTTR (Mean Time To Recover) с 15 минут до <5 минут для типовых P2 инцидентов.

**Зависимости:**
- ✅ Файл `app/services/self_healing_automaton.py` создан (commit 49e37eb)
- ✅ Kubernetes manifest `k8s/self-healing-automaton.yaml` создан
- ⏸️ **Требуется:** Kubernetes RBAC permissions для automaton
- ⏸️ **Требуется:** Python dependencies: kubernetes, psycopg2, kafka-python

---

## ✅ Requirements (Требования)

### 1. Завершить stub implementations

Текущий код содержит TODO комментарии. Нужно реализовать:

**A. `check_kafka_lag()` - реальная интеграция с Kafka**

```python
# app/services/self_healing_automaton.py

async def check_kafka_lag(self):
    """Check Kafka consumer lag and scale if needed."""
    from kafka import KafkaAdminClient, KafkaConsumer
    
    admin_client = KafkaAdminClient(
        bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    )
    
    # Get consumer group info
    consumer_groups = admin_client.list_consumer_groups()
    
    for group_id, _ in consumer_groups:
        if group_id == 'email-service-group':
            # Get lag for each partition
            consumer = KafkaConsumer(
                bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
                group_id=group_id,
                enable_auto_commit=False
            )
            
            lag = consumer.end_offsets(consumer.assignment()) - consumer.position()
            total_lag = sum(lag.values())
            
            if total_lag > 15000:
                logger.warning(f"High Kafka lag detected: {total_lag}")
                await self.scale_deployment('email-service', replicas=6)
                self.healing_actions_total.labels(
                    action='scale_kafka_consumers',
                    success='true'
                ).inc()
```

**B. `cleanup_postgres_connections()` - SQL execution**

```python
async def cleanup_postgres_connections(self):
    """Terminate idle PostgreSQL connections."""
    import psycopg2
    
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        database=os.getenv('POSTGRES_DB', 'email_db'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD')
    )
    
    cur = conn.cursor()
    
    # Terminate idle connections >10 minutes
    cur.execute("""
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE state = 'idle' 
          AND state_change < now() - interval '10 minutes'
          AND pid != pg_backend_pid()
    """)
    
    terminated = cur.rowcount
    logger.info(f"Terminated {terminated} idle PostgreSQL connections")
    
    cur.close()
    conn.close()
    
    self.healing_actions_total.labels(
        action='cleanup_postgres_connections',
        success='true'
    ).inc()
```

**C. `cleanup_old_logs()` - kubectl exec implementation**

```python
async def cleanup_old_logs(self):
    """Delete old application logs from pods."""
    from kubernetes import client, config
    
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    
    pods = v1.list_namespaced_pod(
        namespace='production',
        label_selector='app=email-service'
    )
    
    for pod in pods.items:
        # Execute cleanup command in pod
        exec_command = [
            '/bin/sh',
            '-c',
            'find /var/log -name "*.log" -mtime +7 -delete'
        ]
        
        resp = stream(
            v1.connect_get_namespaced_pod_exec,
            pod.metadata.name,
            'production',
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        
        logger.info(f"Cleaned up logs on pod {pod.metadata.name}: {resp}")
```

### 2. Deploy Self-Healing Automaton to Production

```bash
# Применить RBAC permissions
kubectl apply -f k8s/self-healing-automaton.yaml -n production

# Verify: Pod running
kubectl get pods -n production -l app=self-healing-automaton

# Expected output:
# NAME                                     READY   STATUS    RESTARTS   AGE
# self-healing-automaton-abc123           1/1     Running   0          30s
```

### 3. Настроить мониторинг automaton

```bash
# Проверить что Prometheus scrapes metrics
curl -s http://self-healing-automaton.production:8000/metrics | grep healing_actions_total

# Expected output:
# healing_actions_total{action="scale_kafka_consumers",success="true"} 5
# healing_actions_total{action="cleanup_postgres_connections",success="true"} 12
```

### 4. Создать ConfigMap для configuration

```yaml
# k8s/self-healing-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: self-healing-config
  namespace: production
data:
  # Thresholds
  KAFKA_LAG_THRESHOLD: "15000"
  POSTGRES_CONN_THRESHOLD: "85"  # percent
  DISK_SPACE_THRESHOLD: "85"     # percent
  MEMORY_THRESHOLD: "85"          # percent
  
  # Scaling limits
  MIN_REPLICAS: "1"
  MAX_REPLICAS: "10"
  
  # Check intervals
  CHECK_INTERVAL: "60"  # seconds
```

```bash
kubectl apply -f k8s/self-healing-config.yaml -n production
```

---

## ✅ Acceptance Criteria (Критерии приемки)

- [x] **AC1:** Все TODO комментарии в `self_healing_automaton.py` удалены и заменены рабочим кодом
- [x] **AC2:** Python dependencies установлены: `kubernetes`, `psycopg2-binary`, `kafka-python`
- [x] **AC3:** Self-Healing Automaton pod running в production namespace
- [x] **AC4:** RBAC permissions настроены (ServiceAccount может читать pods, scale deployments)
- [x] **AC5:** Prometheus scrapes метрики с automaton:
  - `healing_actions_total`
  - `healing_latency_seconds`
- [x] **AC6:** ConfigMap `self-healing-config` создан и используется automaton
- [x] **AC7:** Automaton успешно выполнил хотя бы одно healing action за последние 24 часа
- [x] **AC8:** Логи automaton доступны через `kubectl logs`

---

## 🧪 How to Test (Как тестировать)

### Test 1: Simulate High Kafka Lag → Auto-Scaling

```bash
# Шаг 1: Остановить consumers (создать backlog)
kubectl scale deployment email-service -n production --replicas=0

# Шаг 2: Сгенерировать 20k messages в Kafka
for i in {1..20000}; do
  echo '{"test": "message '$i'"}' | \
  kubectl exec -n production kafka-0 -- kafka-console-producer.sh \
    --bootstrap-server kafka:9092 \
    --topic email.received
done

# Шаг 3: Проверить lag
kubectl exec -n production kafka-0 -- kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --group email-service-group \
  --describe

# Expected: LAG ~20000

# Шаг 4: Запустить email-service обратно (1 replica)
kubectl scale deployment email-service -n production --replicas=1

# Шаг 5: Дождаться auto-healing (60 секунд)
sleep 60

# Шаг 6: Проверить что automaton увеличил replicas
kubectl get deployment email-service -n production

# Expected: READY 6/6 (auto-scaled from 1 to 6)

# Шаг 7: Проверить Prometheus metric
curl -s http://self-healing-automaton.production:8000/metrics | \
  grep 'healing_actions_total{action="scale_kafka_consumers"}'

# Expected: healing_actions_total{action="scale_kafka_consumers",success="true"} 1
```

### Test 2: Simulate High PostgreSQL Connections → Cleanup

```bash
# Шаг 1: Создать 100 idle connections
for i in {1..100}; do
  kubectl exec -n production postgres-0 -- psql -U postgres -c "SELECT pg_sleep(3600)" &
done

# Шаг 2: Проверить количество connections
kubectl exec -n production postgres-0 -- psql -U postgres -c \
  "SELECT count(*) FROM pg_stat_activity"

# Expected: >100

# Шаг 3: Дождаться automaton cleanup (60 секунд)
sleep 60

# Шаг 4: Проверить что connections упали
kubectl exec -n production postgres-0 -- psql -U postgres -c \
  "SELECT count(*) FROM pg_stat_activity WHERE state='idle'"

# Expected: <10 (idle connections terminated)

# Шаг 5: Проверить logs automaton
kubectl logs -n production -l app=self-healing-automaton --tail=20

# Expected: "Terminated XX idle PostgreSQL connections"
```

### Test 3: Simulate OOMKilled Pod → Memory Increase

```bash
# Шаг 1: Создать memory leak в email-service (для теста)
kubectl exec -n production deployment/email-service -- \
  python -c "x = [0] * 10**9"  # Allocate 8GB RAM

# Шаг 2: Pod будет OOMKilled
kubectl get pods -n production -l app=email-service

# Expected: STATUS=OOMKilled

# Шаг 3: Дождаться automaton healing (60 секунд)
sleep 60

# Шаг 4: Проверить что memory limits увеличены
kubectl get deployment email-service -n production -o yaml | grep -A 5 resources

# Expected:
# limits:
#   memory: 2Gi  # (было 1Gi)
# requests:
#   memory: 1Gi  # (было 512Mi)

# Шаг 5: Проверить metric
curl -s http://self-healing-automaton.production:8000/metrics | \
  grep 'healing_actions_total{action="increase_pod_memory"}'
```

### Test 4: Verify RBAC Permissions

```bash
# Проверить ServiceAccount permissions
kubectl auth can-i get pods --as=system:serviceaccount:production:self-healing-sa -n production

# Expected: yes

kubectl auth can-i patch deployments --as=system:serviceaccount:production:self-healing-sa -n production

# Expected: yes

kubectl auth can-i delete pods --as=system:serviceaccount:production:self-healing-sa -n production

# Expected: no (should NOT have delete permissions)
```

---

## 📊 Monitoring After Deployment

```bash
# Dashboard для мониторинга automaton
watch -n 30 '
  echo "=== Self-Healing Actions (last 24h) ==="
  curl -s http://prometheus.monitoring:9090/api/v1/query?query=increase(healing_actions_total[24h]) | \
    jq -r ".data.result[] | \"\(.metric.action): \(.value[1])\""
  
  echo ""
  echo "=== Automaton Health ==="
  kubectl get pods -n production -l app=self-healing-automaton
  
  echo ""
  echo "=== Recent Logs ==="
  kubectl logs -n production -l app=self-healing-automaton --tail=5
'
```

---

## 🔧 Troubleshooting

### Problem: Automaton pod CrashLoopBackOff

**Diagnosis:**
```bash
kubectl logs -n production -l app=self-healing-automaton --previous

# Искать ошибки:
# - "Forbidden" → RBAC permissions issue
# - "Unable to connect to Kafka" → Kafka URL неверный
# - "psycopg2.OperationalError" → PostgreSQL credentials issue
```

**Fix:**
```bash
# Fix RBAC
kubectl apply -f k8s/self-healing-automaton.yaml

# Fix environment variables
kubectl edit deployment self-healing-automaton -n production
# Проверить:
# - KAFKA_BOOTSTRAP_SERVERS
# - POSTGRES_HOST, POSTGRES_PASSWORD
# - CHECK_INTERVAL
```

### Problem: Automaton не выполняет healing actions

**Diagnosis:**
```bash
# Проверить что check interval корректный
kubectl logs -n production -l app=self-healing-automaton | grep "Running healing checks"

# Должно появляться каждые 60 секунд

# Проверить метрики
curl -s http://self-healing-automaton.production:8000/metrics | grep healing_checks_total

# Если =0 → automaton не запускается
```

**Fix:**
```bash
# Проверить main loop
kubectl logs -n production -l app=self-healing-automaton -f

# Должно показывать:
# "Starting Self-Healing Automaton..."
# "Running healing checks iteration 1"
# "Running healing checks iteration 2"
# ...
```

---

## 📋 Checklist перед закрытием задачи

- [ ] Все TODO в `self_healing_automaton.py` реализованы
- [ ] Dependencies установлены в Docker image
- [ ] RBAC permissions настроены и протестированы
- [ ] Automaton pod running >10 минут без restarts
- [ ] Prometheus scrapes metrics успешно
- [ ] Протестировано хотя бы 3 healing scenarios:
  - [ ] Kafka lag → auto-scaling
  - [ ] PostgreSQL connections → cleanup
  - [ ] OOMKilled → memory increase
- [ ] ConfigMap создан и используется
- [ ] Logs показывают healing actions
- [ ] Создана документация: "How Self-Healing Works" в wiki

---

## 🔗 Related Tasks

- **Previous:** [ТЗ-003: Create Grafana SLO Dashboard](TZ-PHASE1-003-GRAFANA-DASHBOARD.md)
- **Next:** [ТЗ-005: Deploy Incident Response API](TZ-PHASE1-005-INCIDENT-API.md)
- **Blocker for:** ТЗ-009 (On-Call Quick Reference зависит от automaton capabilities)

---

## 📝 Notes

### Healing Action Priority

1. **Critical (immediate):** OOMKilled, CrashLoopBackOff
2. **High (5 min delay):** Kafka lag >20k, PostgreSQL >90%
3. **Medium (15 min delay):** Disk space >85%, Memory >85%
4. **Low (1 hour delay):** Pod restarting occasionally

### Safety Limits

Automaton НЕ ДОЛЖЕН:
- Удалять pods (только restart через rollout)
- Менять production database schema
- Scale выше MAX_REPLICAS (10)
- Выполнять healing action чаще чем раз в 5 минут для одной и той же проблемы

### Future Enhancements

- Интеграция с ML для prediction (например, предсказывать Kafka lag spikes)
- Automatic rollback при деградации metrics после healing action
- Integration с Incident Response API для создания tickets

---

**Создано:** 14 декабря 2025  
**Автор:** Backend/DevOps Team  
**Версия:** 1.0
