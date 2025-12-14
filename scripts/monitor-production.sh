#!/bin/bash
# 🔍 PRODUCTION MONITORING DASHBOARD
# Email Intelligence Platform - Real-Time Monitoring

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROMETHEUS_URL="${PROMETHEUS_URL:-http://prometheus.monitoring.svc.cluster.local:9090}"
NAMESPACE="${NAMESPACE:-production}"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  📊 EMAIL PLATFORM PRODUCTION MONITORING                 ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Функция запроса к Prometheus
query_prometheus() {
    local query=$1
    curl -s "${PROMETHEUS_URL}/api/v1/query" \
        --data-urlencode "query=${query}" \
        | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A"
}

# ========================================
# 1. SLO МЕТРИКИ
# ========================================
echo -e "${CYAN}🎯 SLO Metrics (30 days)${NC}"
echo "────────────────────────────────────────"

AVAILABILITY=$(query_prometheus "slo:email_service:availability:ratio_rate5m")
LATENCY_P95=$(query_prometheus "slo:email_service:latency:p95")
LATENCY_P99=$(query_prometheus "slo:email_service:latency:p99")
ERROR_BUDGET=$(query_prometheus "slo:email_service:error_budget_remaining")

# Availability
if [ "$AVAILABILITY" != "N/A" ]; then
    AVAIL_PCT=$(echo "$AVAILABILITY * 100" | bc -l | xargs printf "%.3f")
    
    if (( $(echo "$AVAILABILITY >= 0.999" | bc -l) )); then
        echo -e "  ✅ Availability: ${GREEN}${AVAIL_PCT}%${NC} (Target: 99.9%)"
    else
        echo -e "  ⚠️  Availability: ${RED}${AVAIL_PCT}%${NC} (Target: 99.9%)"
    fi
else
    echo -e "  ⚠️  Availability: ${YELLOW}N/A${NC}"
fi

# Latency P95
if [ "$LATENCY_P95" != "N/A" ]; then
    if (( $(echo "$LATENCY_P95 <= 800" | bc -l) )); then
        echo -e "  ✅ Latency P95: ${GREEN}${LATENCY_P95}ms${NC} (Target: <800ms)"
    else
        echo -e "  ⚠️  Latency P95: ${RED}${LATENCY_P95}ms${NC} (Target: <800ms)"
    fi
else
    echo -e "  ⚠️  Latency P95: ${YELLOW}N/A${NC}"
fi

# Latency P99
if [ "$LATENCY_P99" != "N/A" ]; then
    if (( $(echo "$LATENCY_P99 <= 2000" | bc -l) )); then
        echo -e "  ✅ Latency P99: ${GREEN}${LATENCY_P99}ms${NC} (Target: <2000ms)"
    else
        echo -e "  ⚠️  Latency P99: ${RED}${LATENCY_P99}ms${NC} (Target: <2000ms)"
    fi
else
    echo -e "  ⚠️  Latency P99: ${YELLOW}N/A${NC}"
fi

# Error Budget
if [ "$ERROR_BUDGET" != "N/A" ]; then
    BUDGET_PCT=$(echo "$ERROR_BUDGET * 100" | bc -l | xargs printf "%.1f")
    
    if (( $(echo "$ERROR_BUDGET >= 0.5" | bc -l) )); then
        echo -e "  ✅ Error Budget: ${GREEN}${BUDGET_PCT}%${NC}"
    elif (( $(echo "$ERROR_BUDGET >= 0.25" | bc -l) )); then
        echo -e "  ⚠️  Error Budget: ${YELLOW}${BUDGET_PCT}%${NC}"
    else
        echo -e "  🚨 Error Budget: ${RED}${BUDGET_PCT}%${NC}"
    fi
else
    echo -e "  ⚠️  Error Budget: ${YELLOW}N/A${NC}"
fi

echo ""

# ========================================
# 2. PODS STATUS
# ========================================
echo -e "${CYAN}🚀 Pods Status${NC}"
echo "────────────────────────────────────────"

kubectl get pods -n $NAMESPACE \
    -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,RESTARTS:.status.containerStatuses[0].restartCount,AGE:.metadata.creationTimestamp \
    --sort-by=.metadata.creationTimestamp \
    | while read line; do
        if echo "$line" | grep -q "Running"; then
            echo -e "  ${GREEN}$line${NC}"
        elif echo "$line" | grep -q "Pending\|CrashLoopBackOff\|Error"; then
            echo -e "  ${RED}$line${NC}"
        else
            echo "  $line"
        fi
    done

echo ""

# ========================================
# 3. АКТИВНЫЕ АЛЕРТЫ
# ========================================
echo -e "${CYAN}🚨 Active Alerts${NC}"
echo "────────────────────────────────────────"

FIRING_ALERTS=$(curl -s "${PROMETHEUS_URL}/api/v1/alerts" | jq -r '.data.alerts[] | select(.state=="firing") | .labels.alertname' 2>/dev/null)

if [ -z "$FIRING_ALERTS" ]; then
    echo -e "  ${GREEN}✅ No active alerts${NC}"
else
    echo "$FIRING_ALERTS" | while read alert; do
        echo -e "  ${RED}⚠️  $alert${NC}"
    done
fi

echo ""

# ========================================
# 4. KAFKA CONSUMER LAG
# ========================================
echo -e "${CYAN}📧 Kafka Consumer Lag${NC}"
echo "────────────────────────────────────────"

KAFKA_LAG=$(query_prometheus 'kafka_consumer_lag{topic="email.received"}')

if [ "$KAFKA_LAG" != "N/A" ]; then
    if (( $(echo "$KAFKA_LAG < 10000" | bc -l) )); then
        echo -e "  ✅ email.received: ${GREEN}${KAFKA_LAG}${NC} messages"
    else
        echo -e "  ⚠️  email.received: ${RED}${KAFKA_LAG}${NC} messages (HIGH!)"
    fi
else
    echo -e "  ⚠️  email.received: ${YELLOW}N/A${NC}"
fi

echo ""

# ========================================
# 5. POSTGRESQL
# ========================================
echo -e "${CYAN}💾 PostgreSQL Status${NC}"
echo "────────────────────────────────────────"

PG_CONNECTIONS=$(query_prometheus 'pg_stat_activity_count')

if [ "$PG_CONNECTIONS" != "N/A" ]; then
    if (( $(echo "$PG_CONNECTIONS < 80" | bc -l) )); then
        echo -e "  ✅ Connections: ${GREEN}${PG_CONNECTIONS}/100${NC}"
    else
        echo -e "  ⚠️  Connections: ${RED}${PG_CONNECTIONS}/100${NC} (HIGH!)"
    fi
else
    echo -e "  ⚠️  Connections: ${YELLOW}N/A${NC}"
fi

echo ""

# ========================================
# 6. THROUGHPUT
# ========================================
echo -e "${CYAN}📊 Throughput (last 5m)${NC}"
echo "────────────────────────────────────────"

TOTAL_RPS=$(query_prometheus 'sum(rate(email_service_requests_total[5m]))')
SUCCESS_RPS=$(query_prometheus 'sum(rate(email_service_requests_total{status="success"}[5m]))')
ERROR_RPS=$(query_prometheus 'sum(rate(email_service_requests_total{status="error"}[5m]))')

if [ "$TOTAL_RPS" != "N/A" ]; then
    TOTAL_RPS_FMT=$(printf "%.2f" $TOTAL_RPS)
    echo -e "  Total: ${CYAN}${TOTAL_RPS_FMT}${NC} req/sec"
fi

if [ "$SUCCESS_RPS" != "N/A" ]; then
    SUCCESS_RPS_FMT=$(printf "%.2f" $SUCCESS_RPS)
    echo -e "  Success: ${GREEN}${SUCCESS_RPS_FMT}${NC} req/sec"
fi

if [ "$ERROR_RPS" != "N/A" ]; then
    ERROR_RPS_FMT=$(printf "%.2f" $ERROR_RPS)
    
    if (( $(echo "$ERROR_RPS < 0.01" | bc -l) )); then
        echo -e "  Errors: ${GREEN}${ERROR_RPS_FMT}${NC} req/sec"
    else
        echo -e "  Errors: ${RED}${ERROR_RPS_FMT}${NC} req/sec"
    fi
fi

echo ""

# ========================================
# 7. LINKS
# ========================================
echo -e "${CYAN}🔗 Important Links${NC}"
echo "────────────────────────────────────────"
echo "  Grafana: https://grafana.97v.ru/d/email-platform-slo"
echo "  Prometheus: https://prometheus.97v.ru"
echo "  GitHub: https://github.com/vik9541/email-intelligence-platform"
echo "  Runbook: docs/P0_RUNBOOK_RU.md"
echo ""

echo -e "${GREEN}✨ Dashboard updated: $(date)${NC}"
echo ""
