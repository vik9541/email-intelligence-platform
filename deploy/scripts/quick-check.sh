#!/bin/bash
#
# QUICK SERVER CHECK
# Fast diagnostic script for Email Intelligence Platform
#

echo "================================"
echo "⚡ QUICK SERVER CHECK"
echo "================================"
echo ""

echo "=== SYSTEM ==="
echo "OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '"' || echo 'Unknown')"
echo "Kernel: $(uname -r)"
echo "Uptime: $(uptime -p 2>/dev/null || uptime | cut -d',' -f1)"
echo ""

echo "=== CPU ==="
echo "Cores: $(grep -c '^processor' /proc/cpuinfo)"
echo "Load: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

echo "=== MEMORY ==="
free -h | grep "^Mem:" | awk '{print "Total: " $2 ", Used: " $3 " (" $5 "), Available: " $7}'
echo ""

echo "=== DISK ==="
df -h / | awk 'NR==2 {print "Total: " $2 ", Used: " $3 " (" $5 "), Free: " $4}'
echo ""

echo "=== DOCKER ==="
if command -v docker &> /dev/null; then
    echo "✅ Installed: $(docker --version)"
    RUNNING=$(docker ps -q 2>/dev/null | wc -l)
    TOTAL=$(docker ps -aq 2>/dev/null | wc -l)
    echo "Containers: $RUNNING running / $TOTAL total"
    
    if [ "$RUNNING" -gt 0 ]; then
        echo ""
        echo "Running:"
        docker ps --format "  {{.Names}}: {{.Image}}" 2>/dev/null
    fi
else
    echo "❌ Docker NOT installed"
fi
echo ""

echo "=== DOCKER COMPOSE ==="
if command -v docker-compose &> /dev/null; then
    echo "✅ $(docker-compose --version)"
elif docker compose version &> /dev/null 2>&1; then
    echo "✅ $(docker compose version)"
else
    echo "❌ Docker Compose NOT installed"
fi
echo ""

echo "=== LISTENING PORTS ==="
if command -v ss &> /dev/null; then
    ss -tln 2>/dev/null | grep LISTEN | awk '{split($4,a,":"); print a[length(a)]}' | sort -un | head -10 | xargs
elif command -v netstat &> /dev/null; then
    netstat -tln 2>/dev/null | grep LISTEN | awk '{split($4,a,":"); print a[length(a)]}' | sort -un | head -10 | xargs
else
    echo "(ss/netstat not available)"
fi
echo ""

echo "=== CRITICAL SERVICES ==="
for service in ssh nginx apache2 postgresql mysql redis; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        echo "✅ $service: running"
    elif docker ps 2>/dev/null | grep -q "$service"; then
        echo "✅ $service: running (Docker)"
    fi
done
echo ""

echo "=== NETWORK ==="
echo "Hostname: $(hostname)"
echo "IP: $(hostname -I | awk '{print $1}')"

if ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
    echo "✅ Internet: OK"
else
    echo "❌ Internet: FAILED"
fi

if nslookup google.com &> /dev/null 2>&1; then
    echo "✅ DNS: OK"
else
    echo "❌ DNS: FAILED"
fi
echo ""

echo "=== TOP PROCESSES (by memory) ==="
ps aux --sort=-%mem | head -4 | tail -3 | awk '{printf "  %-10s %5s%% %8s  %s\n", $1, $4, $6, $11}'
echo ""

echo "=== HEALTH STATUS ==="
DISK=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
MEM=$(free | awk 'NR==2 {printf "%.0f", ($3/$2)*100}')
LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d, -f1 | xargs)
CORES=$(grep -c '^processor' /proc/cpuinfo)

if [ "$DISK" -gt 80 ]; then
    echo "⚠️  Disk: $DISK% (high)"
else
    echo "✅ Disk: $DISK%"
fi

if [ "$MEM" -gt 80 ]; then
    echo "⚠️  Memory: $MEM% (high)"
else
    echo "✅ Memory: $MEM%"
fi

LOAD_THRESHOLD=$(echo "$CORES * 1.5" | bc)
if (( $(echo "$LOAD > $LOAD_THRESHOLD" | bc -l) )); then
    echo "⚠️  Load: $LOAD avg (high for $CORES cores)"
else
    echo "✅ Load: $LOAD avg ($CORES cores)"
fi

echo ""
echo "================================"
echo "$(date)"
echo "================================"
