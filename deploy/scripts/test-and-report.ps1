# Automated Server Test and Report Generator
# PowerShell version for Windows
# Usage: .\test-and-report.ps1

$ErrorActionPreference = "Stop"

$TIMESTAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$REPORT_FILE = "server-test-report-$TIMESTAMP.md"

Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  AUTOMATED SERVER TEST & REPORT GENERATOR  ║" -ForegroundColor Cyan
Write-Host "║     97v.ru Email Intelligence Platform     ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ============================================
# STEP 1: CHECK CREDENTIALS
# ============================================
Write-Host "[1/7] Checking credentials..." -ForegroundColor Blue

if (-not $env:DO_SSH_HOST) {
    Write-Host "❌ Error: Environment variables not set" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please set:"
    Write-Host '  $env:DO_SSH_HOST = "your-server-ip"'
    Write-Host '  $env:DO_SSH_USER = "root"'
    Write-Host ""
    Write-Host "Get values from GitHub Secrets:"
    Write-Host "  GitHub → Settings → Secrets → Actions"
    Write-Host "  - DO_SSH_HOST"
    Write-Host "  - DO_SSH_USER"
    Write-Host "  - DO_SSH_PRIVATE_KEY (save to $HOME\.ssh\digitalocean_key)"
    exit 1
}

$SSH_USER = if ($env:DO_SSH_USER) { $env:DO_SSH_USER } else { "root" }
$SSH_PORT = if ($env:DO_SSH_PORT) { $env:DO_SSH_PORT } else { "22" }
$SSH_KEY = if ($env:DO_SSH_KEY_PATH) { $env:DO_SSH_KEY_PATH } else { "$HOME\.ssh\digitalocean_key" }

Write-Host "✅ Credentials found" -ForegroundColor Green
Write-Host "   Host: $env:DO_SSH_HOST"
Write-Host "   User: $SSH_USER"
Write-Host ""

# ============================================
# STEP 2: CHECK SSH KEY
# ============================================
Write-Host "[2/7] Checking SSH key..." -ForegroundColor Blue

if (-not (Test-Path $SSH_KEY)) {
    Write-Host "❌ SSH key not found: $SSH_KEY" -ForegroundColor Red
    Write-Host ""
    Write-Host "Create it:"
    Write-Host "  1. Get DO_SSH_PRIVATE_KEY from GitHub Secrets"
    Write-Host "  2. Open: notepad $SSH_KEY"
    Write-Host "  3. Paste key content and save"
    exit 1
}

Write-Host "✅ SSH key ready" -ForegroundColor Green
Write-Host ""

# ============================================
# STEP 3: TEST CONNECTION
# ============================================
Write-Host "[3/7] Testing connection..." -ForegroundColor Blue

$testCmd = "ssh -i `"$SSH_KEY`" -p $SSH_PORT -o ConnectTimeout=10 -o BatchMode=yes $SSH_USER@$env:DO_SSH_HOST 'echo Connection OK' 2>&1"
$testResult = Invoke-Expression $testCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Cannot connect to server" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:"
    Write-Host "  1. Check server: ping $env:DO_SSH_HOST"
    Write-Host "  2. Check SSH key path: $SSH_KEY"
    Write-Host "  3. Try: ssh -v -i `"$SSH_KEY`" $SSH_USER@$env:DO_SSH_HOST"
    exit 1
}

Write-Host "✅ Connection successful" -ForegroundColor Green
Write-Host ""

# ============================================
# STEP 4: RUN QUICK CHECK
# ============================================
Write-Host "[4/7] Running quick server check..." -ForegroundColor Blue
Write-Host ""

$quickCheckScript = @'
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
chmod +x deploy/scripts/*.sh 2>/dev/null || true

if [ -f "deploy/scripts/quick-check.sh" ]; then
    ./deploy/scripts/quick-check.sh
else
    echo "SCRIPT_NOT_FOUND"
fi
'@

$QUICK_CHECK = ssh -i "$SSH_KEY" -p $SSH_PORT "$SSH_USER@$env:DO_SSH_HOST" $quickCheckScript

if ($QUICK_CHECK -match "PROJECT_NOT_FOUND") {
    Write-Host "⚠️  Project not found on server" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Clone it first:"
    Write-Host "  ssh $SSH_USER@$env:DO_SSH_HOST"
    Write-Host "  cd /opt"
    Write-Host "  git clone https://github.com/[username]/email-service.git"
    $QUICK_CHECK = "Project not deployed yet"
} elseif ($QUICK_CHECK -match "SCRIPT_NOT_FOUND") {
    Write-Host "⚠️  Scripts not found" -ForegroundColor Yellow
    $QUICK_CHECK = "Scripts not deployed yet"
} else {
    Write-Host $QUICK_CHECK
}

Write-Host ""

# ============================================
# STEP 5: RUN DOCKER INFO
# ============================================
Write-Host "[5/7] Collecting Docker information..." -ForegroundColor Blue

$dockerScript = @'
#!/bin/bash
echo "=== DOCKER VERSION ==="
docker --version 2>/dev/null || echo "Docker not installed"

echo ""
echo "=== RUNNING CONTAINERS ==="
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null | head -10 || echo "No containers"

echo ""
echo "=== DOCKER DISK USAGE ==="
docker system df 2>/dev/null || echo "Docker not available"
'@

$DOCKER_INFO = ssh -i "$SSH_KEY" -p $SSH_PORT "$SSH_USER@$env:DO_SSH_HOST" $dockerScript
Write-Host $DOCKER_INFO
Write-Host ""

# ============================================
# STEP 6: COLLECT SYSTEM INFO
# ============================================
Write-Host "[6/7] Collecting system information..." -ForegroundColor Blue

$systemScript = @'
#!/bin/bash
OS=$(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')
KERNEL=$(uname -r)
UPTIME=$(uptime -p 2>/dev/null || uptime)
CORES=$(grep -c '^processor' /proc/cpuinfo)
LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d, -f1 | xargs)
MEM_TOTAL=$(free -h | grep "^Mem:" | awk '{print $2}')
MEM_USED=$(free -h | grep "^Mem:" | awk '{print $3}')
MEM_PERCENT=$(free | awk 'NR==2 {printf "%.0f", ($3/$2)*100}')
DISK_TOTAL=$(df -h / | awk 'NR==2 {print $2}')
DISK_USED=$(df -h / | awk 'NR==2 {print $3}')
DISK_PERCENT=$(df / | awk 'NR==2 {print $5}')
DOCKER_RUNNING=$(docker ps -q 2>/dev/null | wc -l)

echo "OS=$OS"
echo "KERNEL=$KERNEL"
echo "UPTIME=$UPTIME"
echo "CORES=$CORES"
echo "LOAD=$LOAD"
echo "MEM_TOTAL=$MEM_TOTAL"
echo "MEM_USED=$MEM_USED"
echo "MEM_PERCENT=$MEM_PERCENT"
echo "DISK_TOTAL=$DISK_TOTAL"
echo "DISK_USED=$DISK_USED"
echo "DISK_PERCENT=$DISK_PERCENT"
echo "DOCKER_RUNNING=$DOCKER_RUNNING"
'@

$SYSTEM_INFO = ssh -i "$SSH_KEY" -p $SSH_PORT "$SSH_USER@$env:DO_SSH_HOST" $systemScript
$sysInfo = @{}
$SYSTEM_INFO -split "`n" | ForEach-Object {
    if ($_ -match '(.+)=(.+)') {
        $sysInfo[$matches[1]] = $matches[2]
    }
}

Write-Host "✅ System info collected" -ForegroundColor Green
Write-Host ""

# ============================================
# STEP 7: GENERATE REPORT
# ============================================
Write-Host "[7/7] Generating report..." -ForegroundColor Blue

$reportContent = @"
# Server Test Report

**Date:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  
**Server:** $env:DO_SSH_HOST  
**User:** $SSH_USER  
**Report ID:** $TIMESTAMP  

---

## 📋 Executive Summary

- **OS:** $($sysInfo['OS'])
- **Kernel:** $($sysInfo['KERNEL'])
- **Uptime:** $($sysInfo['UPTIME'])
- **CPU:** $($sysInfo['CORES']) cores, Load: $($sysInfo['LOAD'])
- **Memory:** $($sysInfo['MEM_USED']) / $($sysInfo['MEM_TOTAL']) ($($sysInfo['MEM_PERCENT'])%)
- **Disk:** $($sysInfo['DISK_USED']) / $($sysInfo['DISK_TOTAL']) ($($sysInfo['DISK_PERCENT']))
- **Docker:** $($sysInfo['DOCKER_RUNNING']) running containers

$(
    $diskNum = [int]($sysInfo['DISK_PERCENT'] -replace '%','')
    $memNum = [int]$sysInfo['MEM_PERCENT']
    
    if ($diskNum -gt 80) {
        "- **Health:** ⚠️ WARNING - Disk usage high"
    } elseif ($memNum -gt 80) {
        "- **Health:** ⚠️ WARNING - Memory usage high"
    } else {
        "- **Health:** ✅ All systems operational"
    }
)

---

## 🖥️ Quick Check Results

``````
$QUICK_CHECK
``````

---

## 🐳 Docker Environment

``````
$DOCKER_INFO
``````

---

## ✅ Recommendations

$(
    $diskNum = [int]($sysInfo['DISK_PERCENT'] -replace '%','')
    $memNum = [int]$sysInfo['MEM_PERCENT']
    
    if ($diskNum -gt 90) {
        "- 🔴 **CRITICAL:** Disk usage very high ($diskNum%) - Free up space immediately"
        "  - Run: ``docker system prune -af``"
    } elseif ($diskNum -gt 80) {
        "- ⚠️ **WARNING:** Disk usage high ($diskNum%) - Consider cleanup"
    }
    
    if ($memNum -gt 90) {
        "- 🔴 **CRITICAL:** Memory usage very high ($memNum%) - Check for memory leaks"
    } elseif ($memNum -gt 80) {
        "- ⚠️ **WARNING:** Memory usage high ($memNum%) - Monitor processes"
    }
    
    if ($diskNum -le 80 -and $memNum -le 80) {
        "- ✅ All systems operating within normal parameters"
        "- ✅ Continue regular monitoring"
    }
)

---

## 📞 Next Steps

1. **Review this report** for any warnings or critical issues
2. **Monitor resources** regularly
3. **Address recommendations** listed above
4. **Schedule next check** in 7 days

---

**Report Generated:** $(Get-Date)  
**Generated By:** Automated Server Test Script (PowerShell)  
**Version:** 1.0  
"@

$reportContent | Out-File -FilePath $REPORT_FILE -Encoding UTF8

Write-Host "✅ Report generated: $REPORT_FILE" -ForegroundColor Green
Write-Host ""

# ============================================
# SUMMARY
# ============================================
Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           TEST COMPLETE                     ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "📄 Report saved to: " -ForegroundColor Green -NoNewline
Write-Host $REPORT_FILE
Write-Host ""
Write-Host "View report:"
Write-Host "  cat $REPORT_FILE"
Write-Host "  # or"
Write-Host "  notepad $REPORT_FILE"
Write-Host ""
Write-Host "Open in browser:"
Write-Host "  Start-Process $REPORT_FILE"
Write-Host ""
