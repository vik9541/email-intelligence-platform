# Grafana Monitoring Dashboard

Документация по использованию Grafana Dashboard для мониторинга Email Analysis API.

## Быстрый старт

### Доступ к Grafana

- **URL**: http://localhost:3000
- **Логин**: `admin`
- **Пароль**: `admin` (при первом входе предложит сменить)

### Открыть Dashboard

После входа перейдите по прямой ссылке:

```
http://localhost:3000/d/analysis-api
```

Или через меню: **Dashboards** → **Email Service** → **Email Analysis API Monitoring**

---

## Описание панелей

Dashboard содержит 9 панелей для полного обзора состояния системы:

### Ряд 1: Латентность

| # | Панель | Описание | Метрики |
|---|--------|----------|---------|
| 1 | **Email Processing Latency (P95, P99)** | Латентность единичных запросов | Красная линия на 200ms — SLA threshold |
| 2 | **Batch Processing Latency** | Латентность batch-запросов | Красная линия на 1000ms — SLA threshold |

### Ряд 2: Throughput и Error Rate

| # | Панель | Описание | Пороги |
|---|--------|----------|--------|
| 3 | **Request Throughput (RPS)** | Запросов/сек по статусу | 🟢 Success, 🔴 Error |
| 4 | **Error Rate (%)** | Процент ошибок | 🟢 < 1%, 🟡 1-5%, 🔴 > 5% |
| 5 | **SLA Compliance** | Соответствие SLO | 🟢 > 99%, 🟡 95-99%, 🔴 < 95% |

### Ряд 3: Аналитика

| # | Панель | Описание |
|---|--------|----------|
| 6 | **Analysis by Category** | Pie chart распределения писем по категориям |
| 7 | **Automated vs Manual** | Сравнение автоматических и ручных обработок |
| 8 | **Database Query Performance** | Heatmap латентности запросов к PostgreSQL |

### Ряд 4: Детали

| # | Панель | Описание |
|---|--------|----------|
| 9 | **Top 5 Slow Endpoints** | Таблица самых медленных endpoints (сортировка по P99) |

---

## Настройки Dashboard

### Обновление данных

- **Auto-refresh**: каждые 30 секунд
- **Time range**: последние 6 часов (по умолчанию)

Можно изменить в правом верхнем углу Grafana.

### Временные диапазоны

Доступные пресеты:
- Last 5 minutes
- Last 15 minutes
- Last 1 hour
- Last 6 hours (default)
- Last 24 hours
- Last 7 days

---

## Интерпретация данных

### Когда бить тревогу

| Индикатор | Норма | Внимание | Критично |
|-----------|-------|----------|----------|
| **P95 Latency** | < 150ms | 150-200ms | > 200ms |
| **P99 Latency (batch)** | < 800ms | 800-1000ms | > 1000ms |
| **Error Rate** | < 1% | 1-5% | > 5% |
| **SLA Compliance** | > 99% | 95-99% | < 95% |

### Типичные проблемы

1. **Высокая латентность** → Проверить нагрузку на БД (Panel 8)
2. **Рост ошибок** → Проверить логи сервиса и ERP интеграцию
3. **Падение SLA** → Анализировать Top 5 Slow Endpoints (Panel 9)

---

## Добавление новых метрик

### 1. Добавить метрику в код

```python
from prometheus_client import Counter, Histogram

# Пример: новая метрика
my_metric = Counter(
    'my_custom_metric_total',
    'Description',
    ['label1', 'label2']
)
```

### 2. Создать панель в Grafana

1. Открыть Dashboard → **Edit**
2. **Add** → **Visualization**
3. Выбрать тип (Graph, Gauge, Table, etc.)
4. В Query ввести PromQL:
   ```promql
   rate(my_custom_metric_total[5m])
   ```
5. **Save dashboard**

### 3. Экспортировать JSON

1. **Dashboard settings** (⚙️) → **JSON Model**
2. Скопировать JSON
3. Сохранить в `dashboards/analysis-api-monitoring.json`

---

## Docker Compose интеграция

Dashboard автоматически загружается при запуске. Убедитесь, что в `docker-compose.yml`:

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    container_name: email-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./dashboards/provisioning.yaml:/etc/grafana/provisioning/dashboards/provisioning.yaml
      - ./dashboards/datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yaml
      - ./dashboards:/var/lib/grafana/dashboards
    depends_on:
      - prometheus

  prometheus:
    image: prom/prometheus:latest
    container_name: email-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
```

---

## Проверка работы

### 1. Запустить стек

```bash
docker-compose up -d prometheus grafana
```

### 2. Подождать инициализации

```bash
sleep 60
```

### 3. Проверить доступность

```bash
# Grafana
curl -s http://localhost:3000/api/health

# Dashboard загружен
curl -s -u admin:admin http://localhost:3000/api/dashboards/uid/analysis-api | jq .meta.slug
```

### 4. Сгенерировать нагрузку

```bash
# 100 запросов для генерации метрик
for i in $(seq 1 100); do
  curl -s "http://localhost:8000/api/v1/analysis/test-$i" > /dev/null &
done
wait
```

### 5. Открыть в браузере

```
http://localhost:3000/d/analysis-api
```

---

## Troubleshooting

### Dashboard не отображается

1. Проверить provisioning volumes в docker-compose
2. Перезапустить Grafana: `docker-compose restart grafana`
3. Проверить логи: `docker-compose logs grafana`

### Нет данных на панелях

1. Проверить, что Prometheus скрейпит метрики:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```
2. Проверить, что сервис экспортирует метрики:
   ```bash
   curl http://localhost:8000/metrics
   ```

### Ошибка "No data"

- Возможно, метрики ещё не накопились (подождите 1-2 минуты)
- Проверьте правильность названий метрик в PromQL

---

## Полезные ссылки

- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
