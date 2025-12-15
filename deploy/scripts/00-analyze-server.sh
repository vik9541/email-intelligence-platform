#!/bin/bash
#
# SERVER ANALYSIS SCRIPT
# Project: 97v.ru Email Intelligence Platform
# Date: 15 декабря 2025
# Purpose: Safe read-only analysis of server infrastructure
#
# ⚠️ SAFE MODE: All commands are READ-ONLY, no system modifications
#

set -e

REPORT_FILE="/tmp/server-analysis-$(date +%Y%m%d-%H%M%S).txt"

echo "================================" | tee "$REPORT_FILE"
echo "🔍 SERVER ANALYSIS REPORT" | tee -a "$REPORT_FILE"
echo "Generated: $(date)" | tee -a "$REPORT_FILE"
echo "Server: $(hostname)" | tee -a "$REPORT_FILE"
echo "================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# ============================================
# SYSTEM INFO
# ============================================
echo "### 1. SYSTEM INFORMATION" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "OS:" | tee -a "$REPORT_FILE"
if [ -f /etc/os-release ]; then
    cat /etc/os-release | grep -E "^PRETTY_NAME|^VERSION_ID" | cut -d= -f2 | tr -d '"' | tee -a "$REPORT_FILE"
else
    echo "  Unknown (no /etc/os-release)" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

echo "Kernel:" | tee -a "$REPORT_FILE"
echo "  $(uname -r)" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "Architecture:" | tee -a "$REPORT_FILE"
echo "  $(uname -m)" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "Uptime:" | tee -a "$REPORT_FILE"
uptime | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# ============================================
# HARDWARE
# ============================================
echo "### 2. HARDWARE" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

CPU_CORES=$(grep -c '^processor' /proc/cpuinfo)
CPU_MODEL=$(grep '^model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)

echo "CPU:" | tee -a "$REPORT_FILE"
echo "  Cores: $CPU_CORES" | tee -a "$REPORT_FILE"
echo "  Model: $CPU_MODEL" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "Memory:" | tee -a "$REPORT_FILE"
free -h | grep "^Mem:" | awk '{print "  Total: " $2 ", Used: " $3 " (" $5 "), Free: " $4 ", Available: " $7}' | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "Swap:" | tee -a "$REPORT_FILE"
free -h | grep "^Swap:" | awk '{print "  Total: " $2 ", Used: " $3 ", Free: " $4}' | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "Disk:" | tee -a "$REPORT_FILE"
df -h / /home /var 2>/dev/null | awk 'NR==1 || NR>1 {printf "  %-20s %8s %8s %8s %6s %s\n", $6, $2, $3, $4, $5, $1}' | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# ============================================
# DOCKER
# ============================================
echo "### 3. DOCKER STATUS" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version 2>/dev/null)
    echo "✅ Docker installed: $DOCKER_VERSION" | tee -a "$REPORT_FILE"
    
    # Docker info
    if docker info &> /dev/null; then
        echo "" | tee -a "$REPORT_FILE"
        echo "Docker Info:" | tee -a "$REPORT_FILE"
        docker info 2>/dev/null | grep -E "Server Version|Storage Driver|Logging Driver|Cgroup Driver|Kernel Version" | sed 's/^/  /' | tee -a "$REPORT_FILE"
    fi
else
    echo "❌ Docker NOT installed" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version 2>/dev/null)
    echo "✅ Docker Compose installed: $COMPOSE_VERSION" | tee -a "$REPORT_FILE"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version 2>/dev/null)
    echo "✅ Docker Compose (plugin): $COMPOSE_VERSION" | tee -a "$REPORT_FILE"
else
    echo "⚠️  Docker Compose not available" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

if command -v docker &> /dev/null; then
    RUNNING_CONTAINERS=$(docker ps -q 2>/dev/null | wc -l)
    TOTAL_CONTAINERS=$(docker ps -aq 2>/dev/null | wc -l)
    TOTAL_IMAGES=$(docker images -q 2>/dev/null | wc -l)
    
    echo "Containers:" | tee -a "$REPORT_FILE"
    echo "  Running: $RUNNING_CONTAINERS" | tee -a "$REPORT_FILE"
    echo "  Total: $TOTAL_CONTAINERS" | tee -a "$REPORT_FILE"
    echo "  Images: $TOTAL_IMAGES" | tee -a "$REPORT_FILE"
    echo "" | tee -a "$REPORT_FILE"
    
    if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
        echo "Running containers:" | tee -a "$REPORT_FILE"
        docker ps --format "  {{.Names}}: {{.Image}} ({{.Status}})" 2>/dev/null | tee -a "$REPORT_FILE"
        echo "" | tee -a "$REPORT_FILE"
    fi
    
    # Docker disk usage
    echo "Docker Storage:" | tee -a "$REPORT_FILE"
    docker system df 2>/dev/null | tail -n +2 | awk '{printf "  %-15s %10s %10s %10s\n", $1, $2, $3, $4}' | tee -a "$REPORT_FILE"
    echo "" | tee -a "$REPORT_FILE"
fi

# ============================================
# PORTS
# ============================================
echo "### 4. LISTENING PORTS" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

if command -v ss &> /dev/null; then
    echo "Open ports:" | tee -a "$REPORT_FILE"
    if [ "$EUID" -eq 0 ]; then
        sudo ss -tlnp 2>/dev/null | grep LISTEN | awk 'NR>0 {split($4,a,":"); printf "  Port %-6s %s\n", a[length(a)], $7}' | sort -u | tee -a "$REPORT_FILE"
    else
        ss -tln 2>/dev/null | grep LISTEN | awk 'NR>0 {split($4,a,":"); print "  Port " a[length(a)]}' | sort -u | tee -a "$REPORT_FILE"
        echo "  (Run with sudo for process info)" | tee -a "$REPORT_FILE"
    fi
elif command -v netstat &> /dev/null; then
    echo "Open ports:" | tee -a "$REPORT_FILE"
    netstat -tln 2>/dev/null | grep LISTEN | awk '{split($4,a,":"); print "  Port " a[length(a)]}' | sort -u | tee -a "$REPORT_FILE"
else
    echo "  (ss/netstat not available)" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# Critical ports check
echo "Critical ports status:" | tee -a "$REPORT_FILE"
for port in 22 80 443 5432 3306 6379 9090 8000 8080; do
    if ss -tln 2>/dev/null | grep -q ":$port " || netstat -tln 2>/dev/null | grep -q ":$port "; then
        echo "  ✅ Port $port: OPEN" | tee -a "$REPORT_FILE"
    else
        echo "  ❌ Port $port: CLOSED" | tee -a "$REPORT_FILE"
    fi
done
echo "" | tee -a "$REPORT_FILE"

# ============================================
# DATABASES
# ============================================
echo "### 5. DATABASE SERVICES" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# PostgreSQL
if docker ps 2>/dev/null | grep -q postgres; then
    PG_CONTAINER=$(docker ps --filter "ancestor=postgres" --format "{{.Names}}" | head -1)
    echo "✅ PostgreSQL (Docker): running in container '$PG_CONTAINER'" | tee -a "$REPORT_FILE"
elif systemctl is-active --quiet postgresql 2>/dev/null; then
    PG_VERSION=$(psql --version 2>/dev/null | cut -d' ' -f3)
    echo "✅ PostgreSQL (system): running (version $PG_VERSION)" | tee -a "$REPORT_FILE"
elif command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL: installed but not running" | tee -a "$REPORT_FILE"
else
    echo "❌ PostgreSQL: not installed" | tee -a "$REPORT_FILE"
fi

# MySQL/MariaDB
if docker ps 2>/dev/null | grep -q mysql; then
    MYSQL_CONTAINER=$(docker ps --filter "ancestor=mysql" --format "{{.Names}}" | head -1)
    echo "✅ MySQL (Docker): running in container '$MYSQL_CONTAINER'" | tee -a "$REPORT_FILE"
elif systemctl is-active --quiet mysql 2>/dev/null || systemctl is-active --quiet mariadb 2>/dev/null; then
    MYSQL_VERSION=$(mysql --version 2>/dev/null | cut -d' ' -f6)
    echo "✅ MySQL (system): running (version $MYSQL_VERSION)" | tee -a "$REPORT_FILE"
elif command -v mysql &> /dev/null; then
    echo "⚠️  MySQL: installed but not running" | tee -a "$REPORT_FILE"
else
    echo "❌ MySQL: not installed" | tee -a "$REPORT_FILE"
fi

# Redis
if docker ps 2>/dev/null | grep -q redis; then
    REDIS_CONTAINER=$(docker ps --filter "ancestor=redis" --format "{{.Names}}" | head -1)
    echo "✅ Redis (Docker): running in container '$REDIS_CONTAINER'" | tee -a "$REPORT_FILE"
elif systemctl is-active --quiet redis 2>/dev/null || systemctl is-active --quiet redis-server 2>/dev/null; then
    echo "✅ Redis (system): running" | tee -a "$REPORT_FILE"
else
    echo "❌ Redis: not running" | tee -a "$REPORT_FILE"
fi

echo "" | tee -a "$REPORT_FILE"

# ============================================
# WEB SERVERS
# ============================================
echo "### 6. WEB SERVERS" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Nginx
if docker ps 2>/dev/null | grep -q nginx; then
    NGINX_CONTAINER=$(docker ps --filter "ancestor=nginx" --format "{{.Names}}" | head -1)
    echo "✅ Nginx (Docker): running in container '$NGINX_CONTAINER'" | tee -a "$REPORT_FILE"
elif systemctl is-active --quiet nginx 2>/dev/null; then
    NGINX_VERSION=$(nginx -v 2>&1 | cut -d'/' -f2)
    echo "✅ Nginx (system): running (version $NGINX_VERSION)" | tee -a "$REPORT_FILE"
elif command -v nginx &> /dev/null; then
    echo "⚠️  Nginx: installed but not running" | tee -a "$REPORT_FILE"
else
    echo "❌ Nginx: not installed" | tee -a "$REPORT_FILE"
fi

# Apache
if docker ps 2>/dev/null | grep -q "httpd\|apache"; then
    APACHE_CONTAINER=$(docker ps --filter "ancestor=httpd" --format "{{.Names}}" | head -1)
    echo "✅ Apache (Docker): running in container '$APACHE_CONTAINER'" | tee -a "$REPORT_FILE"
elif systemctl is-active --quiet apache2 2>/dev/null || systemctl is-active --quiet httpd 2>/dev/null; then
    echo "✅ Apache (system): running" | tee -a "$REPORT_FILE"
elif command -v apache2 &> /dev/null || command -v httpd &> /dev/null; then
    echo "⚠️  Apache: installed but not running" | tee -a "$REPORT_FILE"
else
    echo "❌ Apache: not installed" | tee -a "$REPORT_FILE"
fi

echo "" | tee -a "$REPORT_FILE"

# ============================================
# DISK USAGE
# ============================================
echo "### 7. DISK USAGE (Top 10 directories)" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

if [ "$EUID" -eq 0 ]; then
    du -sh /* 2>/dev/null | sort -rh | head -10 | awk '{printf "  %8s  %s\n", $1, $2}' | tee -a "$REPORT_FILE"
else
    echo "  (Run with sudo for full system analysis)" | tee -a "$REPORT_FILE"
    du -sh ~/* 2>/dev/null | sort -rh | head -10 | awk '{printf "  %8s  %s\n", $1, $2}' | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# Docker volumes
if command -v docker &> /dev/null; then
    DOCKER_DIR_SIZE=$(du -sh /var/lib/docker 2>/dev/null | cut -f1)
    if [ -n "$DOCKER_DIR_SIZE" ]; then
        echo "Docker storage: $DOCKER_DIR_SIZE" | tee -a "$REPORT_FILE"
        echo "" | tee -a "$REPORT_FILE"
    fi
fi

# ============================================
# NETWORK
# ============================================
echo "### 8. NETWORK" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "Hostname: $(hostname)" | tee -a "$REPORT_FILE"
echo "FQDN: $(hostname -f 2>/dev/null || echo 'Not set')" | tee -a "$REPORT_FILE"

IP_ADDRESSES=$(hostname -I 2>/dev/null | xargs)
echo "IP Addresses: $IP_ADDRESSES" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Internet connectivity
if ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
    echo "✅ Internet connectivity: OK" | tee -a "$REPORT_FILE"
else
    echo "❌ Internet connectivity: FAILED" | tee -a "$REPORT_FILE"
fi

# DNS
if nslookup google.com &> /dev/null; then
    echo "✅ DNS resolution: OK" | tee -a "$REPORT_FILE"
else
    echo "❌ DNS resolution: FAILED" | tee -a "$REPORT_FILE"
fi

echo "" | tee -a "$REPORT_FILE"

# DNS servers
echo "DNS servers:" | tee -a "$REPORT_FILE"
if [ -f /etc/resolv.conf ]; then
    grep "^nameserver" /etc/resolv.conf | awk '{print "  " $2}' | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# ============================================
# SECURITY
# ============================================
echo "### 9. SECURITY" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# SSH
if systemctl is-active --quiet ssh 2>/dev/null || systemctl is-active --quiet sshd 2>/dev/null; then
    echo "✅ SSH: running" | tee -a "$REPORT_FILE"
    SSH_PORT=$(grep "^Port" /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}')
    if [ -n "$SSH_PORT" ]; then
        echo "  Port: $SSH_PORT" | tee -a "$REPORT_FILE"
    else
        echo "  Port: 22 (default)" | tee -a "$REPORT_FILE"
    fi
else
    echo "❌ SSH: not running" | tee -a "$REPORT_FILE"
fi

# Firewall
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null | grep "Status:" | awk '{print $2}')
    echo "Firewall (UFW): $UFW_STATUS" | tee -a "$REPORT_FILE"
elif command -v firewalld &> /dev/null; then
    echo "Firewall (firewalld): installed" | tee -a "$REPORT_FILE"
else
    echo "Firewall: not detected" | tee -a "$REPORT_FILE"
fi

echo "" | tee -a "$REPORT_FILE"

# ============================================
# RUNNING PROCESSES
# ============================================
echo "### 10. TOP PROCESSES" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "By Memory (Top 5):" | tee -a "$REPORT_FILE"
ps aux --sort=-%mem | head -6 | awk 'NR==1 || NR>1 {printf "  %-10s %5s %5s %8s  %s\n", $1, $3, $4, $6, $11}' | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "By CPU (Top 5):" | tee -a "$REPORT_FILE"
ps aux --sort=-%cpu | head -6 | awk 'NR==1 || NR>1 {printf "  %-10s %5s %5s %8s  %s\n", $1, $3, $4, $6, $11}' | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# ============================================
# SYSTEMD SERVICES
# ============================================
echo "### 11. SYSTEMD SERVICES" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

FAILED_SERVICES=$(systemctl list-units --type=service --state=failed --no-pager --no-legend 2>/dev/null | wc -l)
if [ "$FAILED_SERVICES" -gt 0 ]; then
    echo "⚠️  Failed services: $FAILED_SERVICES" | tee -a "$REPORT_FILE"
    systemctl list-units --type=service --state=failed --no-pager --no-legend 2>/dev/null | awk '{print "  " $1}' | tee -a "$REPORT_FILE"
else
    echo "✅ All services running normally" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# ============================================
# SUMMARY & RECOMMENDATIONS
# ============================================
echo "### 12. HEALTH CHECK & RECOMMENDATIONS" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Disk usage warning
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "🔴 CRITICAL: Disk usage is very high ($DISK_USAGE%)" | tee -a "$REPORT_FILE"
elif [ "$DISK_USAGE" -gt 80 ]; then
    echo "⚠️  WARNING: Disk usage is high ($DISK_USAGE%)" | tee -a "$REPORT_FILE"
else
    echo "✅ Disk usage: OK ($DISK_USAGE%)" | tee -a "$REPORT_FILE"
fi

# Load average warning
LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d, -f1 | xargs)
LOAD_THRESHOLD=$(echo "$CPU_CORES * 1.5" | bc)
if (( $(echo "$LOAD > $LOAD_THRESHOLD" | bc -l) )); then
    echo "⚠️  WARNING: System load is high ($LOAD avg, $CPU_CORES cores)" | tee -a "$REPORT_FILE"
else
    echo "✅ System load: OK ($LOAD avg, $CPU_CORES cores)" | tee -a "$REPORT_FILE"
fi

# Memory usage warning
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", ($3/$2)*100}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "🔴 CRITICAL: Memory usage is very high ($MEM_USAGE%)" | tee -a "$REPORT_FILE"
elif [ "$MEM_USAGE" -gt 80 ]; then
    echo "⚠️  WARNING: Memory usage is high ($MEM_USAGE%)" | tee -a "$REPORT_FILE"
else
    echo "✅ Memory usage: OK ($MEM_USAGE%)" | tee -a "$REPORT_FILE"
fi

echo "" | tee -a "$REPORT_FILE"

# ============================================
# FOOTER
# ============================================
echo "================================" | tee -a "$REPORT_FILE"
echo "Report saved to: $REPORT_FILE" | tee -a "$REPORT_FILE"
echo "Generated at: $(date)" | tee -a "$REPORT_FILE"
echo "================================" | tee -a "$REPORT_FILE"

echo ""
echo "✅ Analysis complete!"
echo "📄 Full report: $REPORT_FILE"
