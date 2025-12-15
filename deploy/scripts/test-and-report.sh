#!/bin/bash
#
# AUTOMATED SERVER TEST & REPORT GENERATOR
# Connects to DigitalOcean server, runs tests, generates report
#
# Usage: ./test-and-report.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="server-test-report-${TIMESTAMP}.md"

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  AUTOMATED SERVER TEST & REPORT GENERATOR  ║${NC}"
echo -e "${CYAN}║     97v.ru Email Intelligence Platform     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ============================================
# STEP 1: CHECK CREDENTIALS
# ============================================
echo -e "${BLUE}[1/7]${NC} Checking credentials..."

if [ -z "$DO_SSH_HOST" ]; then
    echo -e "${RED}❌ Error: Environment variables not set${NC}"
    echo ""
    echo "Please set:"
    echo "  export DO_SSH_HOST='your-server-ip'"
    echo "  export DO_SSH_USER='root'"
    echo ""
    echo "Get values from GitHub Secrets:"
    echo "  GitHub → Settings → Secrets → Actions"
    echo "  - DO_SSH_HOST"
    echo "  - DO_SSH_USER"
    echo "  - DO_SSH_PRIVATE_KEY (save to ~/.ssh/digitalocean_key)"
    echo ""
    exit 1
fi

SSH_USER="${DO_SSH_USER:-root}"
SSH_PORT="${DO_SSH_PORT:-22}"
SSH_KEY="${DO_SSH_KEY_PATH:-$HOME/.ssh/digitalocean_key}"

echo -e "${GREEN}✅ Credentials found${NC}"
echo "   Host: $DO_SSH_HOST"
echo "   User: $SSH_USER"
echo ""

# ============================================
# STEP 2: CHECK SSH KEY
# ============================================
echo -e "${BLUE}[2/7]${NC} Checking SSH key..."

if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ SSH key not found: $SSH_KEY${NC}"
    echo ""
    echo "Create it:"
    echo "  1. Get DO_SSH_PRIVATE_KEY from GitHub Secrets"
    echo "  2. Save: cat > $SSH_KEY << 'EOF'"
    echo "     [paste key]"
    echo "     EOF"
    echo "  3. Fix permissions: chmod 600 $SSH_KEY"
    exit 1
fi

chmod 600 "$SSH_KEY" 2>/dev/null || true
echo -e "${GREEN}✅ SSH key ready${NC}"
echo ""

# ============================================
# STEP 3: TEST CONNECTION
# ============================================
echo -e "${BLUE}[3/7]${NC} Testing connection..."

if ! ssh -i "$SSH_KEY" -p "$SSH_PORT" -o ConnectTimeout=10 -o BatchMode=yes "$SSH_USER@$DO_SSH_HOST" "echo 'Connection OK'" &>/dev/null; then
    echo -e "${RED}❌ Cannot connect to server${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check server is running: ping $DO_SSH_HOST"
    echo "  2. Check SSH port: nmap -p $SSH_PORT $DO_SSH_HOST"
    echo "  3. Check key permissions: ls -la $SSH_KEY"
    echo "  4. Try verbose mode: ssh -v -i $SSH_KEY $SSH_USER@$DO_SSH_HOST"
    exit 1
fi

echo -e "${GREEN}✅ Connection successful${NC}"
echo ""

# ============================================
# STEP 4: RUN QUICK CHECK
# ============================================
echo -e "${BLUE}[4/7]${NC} Running quick server check..."
echo ""

QUICK_CHECK=$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" << 'ENDSSH'
#!/bin/bash

# Find project directory
PROJECT_DIR=""
for dir in /opt/email-service ~/email-service /var/www/email-service; do
    if [ -d "$dir" ]; then
        PROJECT_DIR="$dir"
        break
    fi
done

if [ -z "$PROJECT_DIR" ]; then
    echo "PROJECT_NOT_FOUND"
    exit 0
fi

cd "$PROJECT_DIR"
chmod +x deploy/scripts/*.sh 2>/dev/null || true

if [ -f "deploy/scripts/quick-check.sh" ]; then
    ./deploy/scripts/quick-check.sh
else
    echo "SCRIPT_NOT_FOUND"
fi
ENDSSH
)

if echo "$QUICK_CHECK" | grep -q "PROJECT_NOT_FOUND"; then
    echo -e "${YELLOW}⚠️  Project not found on server${NC}"
    echo ""
    echo "Clone it first:"
    echo "  ssh $SSH_USER@$DO_SSH_HOST"
    echo "  cd /opt"
    echo "  git clone https://github.com/[username]/email-service.git"
    exit 1
elif echo "$QUICK_CHECK" | grep -q "SCRIPT_NOT_FOUND"; then
    echo -e "${YELLOW}⚠️  Scripts not found${NC}"
    QUICK_CHECK="Scripts not deployed yet"
else
    echo "$QUICK_CHECK"
fi

echo ""

# ============================================
# STEP 5: RUN FULL ANALYSIS
# ============================================
echo -e "${BLUE}[5/7]${NC} Running full server analysis..."
echo ""

FULL_ANALYSIS=$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" << 'ENDSSH'
#!/bin/bash

PROJECT_DIR=""
for dir in /opt/email-service ~/email-service /var/www/email-service; do
    if [ -d "$dir" ]; then
        PROJECT_DIR="$dir"
        break
    fi
done

if [ -z "$PROJECT_DIR" ]; then
    echo "PROJECT_NOT_FOUND"
    exit 0
fi

cd "$PROJECT_DIR"

if [ -f "deploy/scripts/00-analyze-server.sh" ]; then
    ./deploy/scripts/00-analyze-server.sh
    # Return path to report
    ls -1t /tmp/server-analysis-*.txt 2>/dev/null | head -1
else
    echo ""
fi
ENDSSH
)

if echo "$FULL_ANALYSIS" | grep -q "PROJECT_NOT_FOUND"; then
    echo -e "${YELLOW}⚠️  Skipping full analysis (project not found)${NC}"
    REMOTE_REPORT=""
else
    REMOTE_REPORT=$(echo "$FULL_ANALYSIS" | tail -1)
    if [ -f "$REMOTE_REPORT" ] || [[ "$REMOTE_REPORT" == /tmp/server-analysis-* ]]; then
        echo -e "${GREEN}✅ Analysis complete${NC}"
        echo "   Report: $REMOTE_REPORT"
    fi
fi

echo ""

# ============================================
# STEP 6: COLLECT DOCKER INFO
# ============================================
echo -e "${BLUE}[6/7]${NC} Collecting Docker information..."

DOCKER_INFO=$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" << 'ENDSSH'
#!/bin/bash

echo "=== DOCKER VERSION ==="
docker --version 2>/dev/null || echo "Docker not installed"

echo ""
echo "=== DOCKER COMPOSE VERSION ==="
docker-compose --version 2>/dev/null || docker compose version 2>/dev/null || echo "Docker Compose not installed"

echo ""
echo "=== RUNNING CONTAINERS ==="
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No containers"

echo ""
echo "=== DOCKER IMAGES ==="
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>/dev/null | head -10 || echo "No images"

echo ""
echo "=== DOCKER DISK USAGE ==="
docker system df 2>/dev/null || echo "Docker not available"
ENDSSH
)

echo "$DOCKER_INFO"
echo ""

# ============================================
# STEP 7: GENERATE REPORT
# ============================================
echo -e "${BLUE}[7/7]${NC} Generating report..."

cat > "$REPORT_FILE" << EOF
# Server Test Report

**Date:** $(date '+%Y-%m-%d %H:%M:%S')  
**Server:** $DO_SSH_HOST  
**User:** $SSH_USER  
**Report ID:** $TIMESTAMP  

---

## 📋 Executive Summary

$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" << 'ENDSSH'
#!/bin/bash

# System info
OS=$(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')
KERNEL=$(uname -r)
UPTIME=$(uptime -p 2>/dev/null || uptime | cut -d',' -f1)

# Resources
CORES=$(grep -c '^processor' /proc/cpuinfo)
LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d, -f1 | xargs)
MEM_TOTAL=$(free -h | grep "^Mem:" | awk '{print $2}')
MEM_USED=$(free -h | grep "^Mem:" | awk '{print $3}')
MEM_PERCENT=$(free | awk 'NR==2 {printf "%.0f", ($3/$2)*100}')
DISK_TOTAL=$(df -h / | awk 'NR==2 {print $2}')
DISK_USED=$(df -h / | awk 'NR==2 {print $3}')
DISK_PERCENT=$(df / | awk 'NR==2 {print $5}')

# Docker
DOCKER_RUNNING=$(docker ps -q 2>/dev/null | wc -l)
DOCKER_TOTAL=$(docker ps -aq 2>/dev/null | wc -l)

echo "- **OS:** $OS"
echo "- **Kernel:** $KERNEL"
echo "- **Uptime:** $UPTIME"
echo "- **CPU:** $CORES cores, Load: $LOAD"
echo "- **Memory:** $MEM_USED / $MEM_TOTAL ($MEM_PERCENT%)"
echo "- **Disk:** $DISK_USED / $DISK_TOTAL ($DISK_PERCENT)"
echo "- **Docker:** $DOCKER_RUNNING running / $DOCKER_TOTAL total containers"

# Health status
DISK_NUM=$(echo $DISK_PERCENT | sed 's/%//')
if [ "$DISK_NUM" -gt 80 ]; then
    echo "- **Health:** ⚠️ WARNING - Disk usage high"
elif [ "$MEM_PERCENT" -gt 80 ]; then
    echo "- **Health:** ⚠️ WARNING - Memory usage high"
else
    echo "- **Health:** ✅ All systems operational"
fi
ENDSSH
)

---

## 🖥️ Quick Check Results

\`\`\`
$QUICK_CHECK
\`\`\`

---

## 🐳 Docker Environment

\`\`\`
$DOCKER_INFO
\`\`\`

---

## 📊 Detailed Analysis

$(if [ -n "$REMOTE_REPORT" ]; then
    echo "Full analysis report available at:"
    echo "\`$REMOTE_REPORT\`"
    echo ""
    echo "Download with:"
    echo "\`\`\`bash"
    echo "scp -i $SSH_KEY $SSH_USER@$DO_SSH_HOST:$REMOTE_REPORT ./"
    echo "\`\`\`"
else
    echo "Full analysis not available (run deploy/scripts/00-analyze-server.sh on server)"
fi)

---

## 🔍 System Details

### Operating System
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "cat /etc/os-release 2>/dev/null" | sed 's/^/    /')

### Kernel
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "uname -a")

### CPU
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "lscpu | grep -E 'Model name|CPU\(s\)|Thread' | head -3" | sed 's/^/    /')

### Memory
\`\`\`
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "free -h")
\`\`\`

### Disk
\`\`\`
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "df -h")
\`\`\`

---

## 🌐 Network & Services

### Listening Ports
\`\`\`
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "ss -tln 2>/dev/null | grep LISTEN | awk '{split(\$4,a,\":\"); print a[length(a)]}' | sort -un | head -20" | xargs)
\`\`\`

### Critical Services
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" << 'ENDSSH'
for service in ssh nginx postgresql mysql redis docker; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        echo "- ✅ **$service:** running (system)"
    elif docker ps 2>/dev/null | grep -q "$service"; then
        echo "- ✅ **$service:** running (Docker)"
    fi
done
ENDSSH
)

### Connectivity Tests
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" << 'ENDSSH'
if ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
    echo "- ✅ Internet: OK"
else
    echo "- ❌ Internet: FAILED"
fi

if nslookup google.com &>/dev/null; then
    echo "- ✅ DNS: OK"
else
    echo "- ❌ DNS: FAILED"
fi
ENDSSH
)

---

## 🔐 Security Status

### SSH Configuration
\`\`\`
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "grep -E '^Port|^PermitRootLogin|^PasswordAuthentication' /etc/ssh/sshd_config 2>/dev/null || echo 'Default SSH config'")
\`\`\`

### Firewall
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" << 'ENDSSH'
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(ufw status 2>/dev/null | grep "Status:" | awk '{print $2}')
    echo "- UFW Firewall: $UFW_STATUS"
else
    echo "- UFW: not installed"
fi
ENDSSH
)

---

## 📈 Resource Usage

### Top Processes (by memory)
\`\`\`
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "ps aux --sort=-%mem | head -6")
\`\`\`

### Top Processes (by CPU)
\`\`\`
$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" "ps aux --sort=-%cpu | head -6")
\`\`\`

---

## ✅ Recommendations

$(ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST" << 'ENDSSH'
#!/bin/bash

DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", ($3/$2)*100}')
CORES=$(grep -c '^processor' /proc/cpuinfo)
LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d, -f1 | xargs)

RECOMMENDATIONS=""

if [ "$DISK_USAGE" -gt 90 ]; then
    echo "- 🔴 **CRITICAL:** Disk usage very high ($DISK_USAGE%) - Free up space immediately"
elif [ "$DISK_USAGE" -gt 80 ]; then
    echo "- ⚠️ **WARNING:** Disk usage high ($DISK_USAGE%) - Consider cleanup"
    echo "  - Run: \`docker system prune -af\`"
    echo "  - Clean logs: \`sudo journalctl --vacuum-time=7d\`"
fi

if [ "$MEM_USAGE" -gt 90 ]; then
    echo "- 🔴 **CRITICAL:** Memory usage very high ($MEM_USAGE%) - Check for memory leaks"
elif [ "$MEM_USAGE" -gt 80 ]; then
    echo "- ⚠️ **WARNING:** Memory usage high ($MEM_USAGE%) - Monitor processes"
fi

LOAD_THRESHOLD=$(echo "$CORES * 1.5" | bc)
if (( $(echo "$LOAD > $LOAD_THRESHOLD" | bc -l) )); then
    echo "- ⚠️ **WARNING:** High system load ($LOAD for $CORES cores) - Check CPU usage"
fi

if [ -z "$RECOMMENDATIONS" ]; then
    echo "- ✅ All systems operating within normal parameters"
    echo "- ✅ Continue regular monitoring"
fi
ENDSSH
)

---

## 📞 Next Steps

1. **Review this report** for any warnings or critical issues
2. **Download full analysis** if needed (see Detailed Analysis section)
3. **Monitor resources** regularly with quick-check script
4. **Address recommendations** listed above
5. **Schedule next check** in 7 days

---

**Report Generated:** $(date)  
**Generated By:** Automated Server Test Script  
**Version:** 1.0  
EOF

echo -e "${GREEN}✅ Report generated: $REPORT_FILE${NC}"
echo ""

# ============================================
# DOWNLOAD REMOTE REPORT (if available)
# ============================================
if [ -n "$REMOTE_REPORT" ] && [[ "$REMOTE_REPORT" == /tmp/server-analysis-* ]]; then
    echo -e "${YELLOW}Downloading full analysis report...${NC}"
    LOCAL_FULL_REPORT="full-analysis-${TIMESTAMP}.txt"
    
    if scp -i "$SSH_KEY" -P "$SSH_PORT" "$SSH_USER@$DO_SSH_HOST:$REMOTE_REPORT" "./$LOCAL_FULL_REPORT" &>/dev/null; then
        echo -e "${GREEN}✅ Downloaded: $LOCAL_FULL_REPORT${NC}"
        echo ""
    fi
fi

# ============================================
# SUMMARY
# ============================================
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           TEST COMPLETE                     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}📄 Report saved to:${NC} $REPORT_FILE"
if [ -f "$LOCAL_FULL_REPORT" ]; then
    echo -e "${GREEN}📄 Full analysis:${NC} $LOCAL_FULL_REPORT"
fi
echo ""
echo "View report:"
echo "  cat $REPORT_FILE"
echo "  # or"
echo "  less $REPORT_FILE"
echo ""
echo "Open in browser:"
if command -v pandoc &>/dev/null; then
    echo "  pandoc $REPORT_FILE -o ${REPORT_FILE%.md}.html"
    echo "  xdg-open ${REPORT_FILE%.md}.html  # Linux"
    echo "  open ${REPORT_FILE%.md}.html      # Mac"
else
    echo "  # Install pandoc first: sudo apt install pandoc"
fi
echo ""
