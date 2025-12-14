# ТЗ-006: Create Monitoring Dashboard Script [Phase 1]

**Статус:** 🔴 Not Started  
**Приоритет:** P2 (Medium - Convenience Tool)  
**Оценка времени:** 1.5h  
**Сложность:** LOW  
**Владелец:** DevOps  
**Sprint:** Phase 1 - Production Monitoring Stack  

---

## 📋 Context (Контекст)

Bash script для real-time мониторинга production через terminal. Файл `scripts/monitor-production.sh` уже создан и показывает:

- **SLO Metrics:** availability, latency P95/P99, error budget
- **Pods Status:** с цветовой индикацией (green=Running, red=Failed)
- **Active Alerts:** список firing alerts из Prometheus
- **Kafka Consumer Lag:** для каждого топика
- **PostgreSQL Connections:** текущее использование vs max
- **Throughput:** total/success/error RPS
- **Important Links:** Grafana, Prometheus, GitHub, Runbook

Используется:
- **Дежурными инженерами** - для quick status check без открытия Grafana
- **Incident response** - для диагностики во время P0/P1
- **Deployments** - для мониторинга canary rollout

**Зависимости:**
- ✅ Файл `scripts/monitor-production.sh` создан (commit 49e37eb)
- ⏸️ **Требуется:** jq, curl установлены на машине пользователя
- ⏸️ **Требуется:** kubectl настроен с доступом к production cluster

---

## ✅ Requirements (Требования)

### 1. Сделать script executable

```bash
chmod +x scripts/monitor-production.sh
```

### 2. Добавить dependencies check

Добавить в начало скрипта проверку зависимостей:

```bash
#!/bin/bash

# Dependency check
for cmd in kubectl curl jq; do
  if ! command -v $cmd &> /dev/null; then
    echo "❌ Error: $cmd is not installed"
    echo "Install: brew install $cmd (macOS) or apt-get install $cmd (Linux)"
    exit 1
  fi
done

# Verify kubectl context
current_context=$(kubectl config current-context)
if [[ ! "$current_context" =~ production ]]; then
  echo "⚠️  Warning: Current kubectl context is '$current_context'"
  echo "Expected context containing 'production'"
  read -p "Continue anyway? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi
```

### 3. Добавить configuration variables

```bash
# Configuration
PROMETHEUS_URL=${PROMETHEUS_URL:-"http://prometheus.monitoring:9090"}
NAMESPACE=${NAMESPACE:-"production"}
REFRESH_INTERVAL=${REFRESH_INTERVAL:-30}  # seconds

# Allow override via environment variables
# Example: PROMETHEUS_URL=http://localhost:9090 ./monitor-production.sh
```

### 4. Добавить watch mode

```bash
# Add command-line argument for watch mode
if [[ "$1" == "--watch" || "$1" == "-w" ]]; then
  while true; do
    clear
    bash "$0"  # Re-run script
    echo ""
    echo "Refreshing in $REFRESH_INTERVAL seconds... (Ctrl+C to exit)"
    sleep $REFRESH_INTERVAL
  done
fi
```

### 5. Улучшить error handling

```bash
query_prometheus() {
  local query="$1"
  local result
  
  result=$(curl -s --max-time 5 "${PROMETHEUS_URL}/api/v1/query?query=${query}" | jq -r '.data.result[0].value[1] // "N/A"' 2>/dev/null)
  
  if [[ $? -ne 0 || "$result" == "N/A" ]]; then
    echo "N/A"
  else
    echo "$result"
  fi
}

# Usage
availability=$(query_prometheus "slo:email_service:availability:ratio_rate5m")
```

### 6. Добавить colored output

```bash
# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_green() {
  echo -e "${GREEN}$1${NC}"
}

print_red() {
  echo -e "${RED}$1${NC}"
}

print_yellow() {
  echo -e "${YELLOW}$1${NC}"
}

# Example usage
if (( $(echo "$availability > 99.9" | bc -l) )); then
  print_green "✅ Availability: ${availability}%"
else
  print_red "❌ Availability: ${availability}%"
fi
```

---

## ✅ Acceptance Criteria (Критерии приемки)

- [x] **AC1:** Script executable (`chmod +x`)
- [x] **AC2:** Dependencies check работает (kubectl, curl, jq)
- [x] **AC3:** Configuration через environment variables
- [x] **AC4:** Watch mode работает (`--watch` flag)
- [x] **AC5:** Error handling для failed Prometheus queries
- [x] **AC6:** Colored output (зеленый=healthy, красный=critical, желтый=warning)
- [x] **AC7:** Script выполняется <5 секунд
- [x] **AC8:** Help message доступен (`--help` flag)

---

## 🧪 How to Test (Как тестировать)

### Test 1: Verify Dependencies Check

```bash
# Test когда dependency отсутствует
# Временно переименовать jq
sudo mv /usr/local/bin/jq /usr/local/bin/jq.bak

# Запустить script
./scripts/monitor-production.sh

# Expected output:
# ❌ Error: jq is not installed
# Install: brew install jq (macOS) or apt-get install jq (Linux)

# Restore jq
sudo mv /usr/local/bin/jq.bak /usr/local/bin/jq
```

### Test 2: Verify Colored Output

```bash
./scripts/monitor-production.sh

# Expected:
# - SLO metrics в цвете (green если >target, red если <target)
# - Pod status: green "Running", red "CrashLoopBackOff"
# - Alerts: red if firing, green if no alerts
```

### Test 3: Verify Watch Mode

```bash
./scripts/monitor-production.sh --watch

# Expected:
# - Dashboard обновляется каждые 30 секунд
# - Clear screen перед каждым обновлением
# - "Refreshing in 30 seconds..." внизу
# - Ctrl+C выходит из watch mode
```

### Test 4: Verify Configuration Override

```bash
# Test с custom Prometheus URL
PROMETHEUS_URL=http://localhost:9090 ./scripts/monitor-production.sh

# Test с custom namespace
NAMESPACE=staging ./scripts/monitor-production.sh

# Test с custom refresh interval
REFRESH_INTERVAL=10 ./scripts/monitor-production.sh --watch
```

### Test 5: Verify Error Handling (Prometheus Down)

```bash
# Stop port-forward для Prometheus (симулировать downtime)
pkill -f "port-forward.*prometheus"

# Запустить script
./scripts/monitor-production.sh

# Expected:
# - "N/A" вместо metrics
# - Script НЕ должен крашиться
# - Warning message: "⚠️  Failed to query Prometheus"
```

### Test 6: Verify Help Message

```bash
./scripts/monitor-production.sh --help

# Expected output:
# Usage: monitor-production.sh [OPTIONS]
# 
# Real-time production monitoring dashboard
# 
# Options:
#   -w, --watch      Watch mode (refresh every 30s)
#   -h, --help       Show this help message
# 
# Environment Variables:
#   PROMETHEUS_URL   Prometheus API URL (default: http://prometheus.monitoring:9090)
#   NAMESPACE        Kubernetes namespace (default: production)
#   REFRESH_INTERVAL Watch mode refresh interval in seconds (default: 30)
# 
# Examples:
#   ./monitor-production.sh
#   ./monitor-production.sh --watch
#   NAMESPACE=staging ./monitor-production.sh
```

---

## 📊 Expected Output Example

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║       📊 PRODUCTION MONITORING DASHBOARD                 ║
║       Email Intelligence Platform                        ║
║       Updated: 2025-12-14 15:30:45 MSK                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

━━━ SLO Metrics ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Availability:       99.92% (target: 99.9%)
✅ Latency P95:        450ms (target: <800ms)
✅ Latency P99:        780ms (target: <1000ms)
✅ Error Budget:       85% remaining (30-day window)

━━━ Pods Status ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

email-service-abc123        ✅ Running      CPU: 45%   MEM: 512Mi
email-service-def456        ✅ Running      CPU: 52%   MEM: 487Mi
email-service-ghi789        ✅ Running      CPU: 48%   MEM: 501Mi

━━━ Active Alerts ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ No firing alerts

━━━ Kafka Consumer Lag ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

email.received             Lag: 1,234 messages   ✅ OK
email.processed            Lag: 56 messages      ✅ OK

━━━ PostgreSQL Connections ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current: 45 / Max: 100     ✅ 45% usage

━━━ Throughput ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total:   125 req/s
Success: 123 req/s (98.4%)
Errors:  2 req/s (1.6%)

━━━ Important Links ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Grafana:    http://grafana.monitoring/d/slo-dashboard
  Prometheus: http://prometheus.monitoring:9090
  GitHub:     https://github.com/vik9541/email-intelligence-platform
  Runbook:    docs/P0_RUNBOOK_RU.md
```

---

## 🔧 Troubleshooting

### Problem: Script выполняется очень медленно (>20 секунд)

**Diagnosis:**
```bash
# Добавить timing для каждой секции
time query_prometheus "slo:email_service:availability:ratio_rate5m"

# Если Prometheus query медленный:
# - Проверить latency: curl -w "%{time_total}\n" -o /dev/null http://prometheus.monitoring:9090/api/v1/query?query=up
# - Если >1s → Prometheus перегружен или сеть медленная
```

**Fix:**
```bash
# Добавить timeout для всех curl requests
curl -s --max-time 2 "${PROMETHEUS_URL}/api/v1/query?query=${query}"

# Parallel queries вместо sequential
{
  availability=$(query_prometheus "slo:email_service:availability:ratio_rate5m") &
  latency_p95=$(query_prometheus "slo:email_service:latency:p95") &
  wait
}

# Скорость должна увеличиться с 15s → 3s
```

### Problem: Colored output не работает на Windows

**Diagnosis:**
```bash
# Windows Terminal не поддерживает ANSI color codes в старых версиях

# Check terminal type
echo $TERM

# Если "dumb" или пусто → colors не поддерживаются
```

**Fix:**
```bash
# Detect terminal capabilities
if [[ -t 1 && "$TERM" != "dumb" ]]; then
  USE_COLORS=true
else
  USE_COLORS=false
fi

# Conditional coloring
if $USE_COLORS; then
  print_green "✅ OK"
else
  echo "[OK]"
fi
```

### Problem: kubectl queries возвращают permission denied

**Diagnosis:**
```bash
# Test kubectl permissions
kubectl auth can-i get pods -n production

# Если "no" → RBAC issue
```

**Fix:**
```bash
# Request permissions from cluster admin
# Or use service account with proper RBAC

kubectl create sa monitoring-reader -n production
kubectl create clusterrole monitoring-reader --verb=get,list,watch --resource=pods,deployments
kubectl create clusterrolebinding monitoring-reader --clusterrole=monitoring-reader --serviceaccount=production:monitoring-reader
```

---

## 📋 Checklist перед закрытием задачи

- [ ] Script executable
- [ ] Dependencies check работает
- [ ] Configuration variables работают
- [ ] Watch mode работает
- [ ] Error handling для всех external calls
- [ ] Colored output работает (и отключается на non-TTY)
- [ ] Help message добавлен
- [ ] Performance <5 секунд
- [ ] Tested на macOS и Linux
- [ ] Добавлен в team wiki: "Quick Production Monitoring"
- [ ] Добавлен alias в team .bashrc:
  ```bash
  alias prod-mon="~/email-service/scripts/monitor-production.sh --watch"
  ```

---

## 🔗 Related Tasks

- **Previous:** [ТЗ-005: Deploy Incident Response API](TZ-PHASE1-005-INCIDENT-API.md)
- **Next:** [ТЗ-007: Write P0 Incident Runbook](TZ-PHASE1-007-P0-RUNBOOK.md)
- **Used by:** Дежурные инженеры, incident response team

---

## 📝 Notes

### Additional Features (Optional)

**1. Export to JSON**
```bash
./monitor-production.sh --json > status.json

# Output:
# {
#   "timestamp": "2025-12-14T15:30:45Z",
#   "slo": {
#     "availability": 99.92,
#     "latency_p95": 450,
#     "error_budget": 85
#   },
#   "pods": [...],
#   "alerts": [...]
# }
```

**2. Slack Integration**
```bash
# Post status to Slack channel
./monitor-production.sh --slack-webhook https://hooks.slack.com/...

# Or scheduled with cron:
# 0 9 * * * /path/to/monitor-production.sh --slack-webhook $WEBHOOK_URL
```

**3. Diff Mode**
```bash
# Compare with previous run
./monitor-production.sh --diff

# Output:
# Availability:  99.92% (↑ +0.05% from 5 minutes ago)
# Latency P95:   450ms  (↓ -50ms from 5 minutes ago)
```

### Integration with Other Tools

- **tmux/screen:** Запустить в отдельной панели для постоянного мониторинга
- **Jenkins:** Use в CI/CD для post-deployment verification
- **Runbook:** Референсится в P0_RUNBOOK_RU.md для quick diagnostics

---

**Создано:** 14 декабря 2025  
**Автор:** DevOps Team  
**Версия:** 1.0
