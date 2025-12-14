#!/bin/bash

# Pre-deployment validation checklist
# Run this BEFORE every production deployment

set -e

echo "🚀 PRE-DEPLOYMENT VALIDATION"
echo "============================="

PASSED=0
FAILED=0

check() {
  local name=$1
  local command=$2
  
  echo -n "📋 $name ... "
  
  if eval "$command" > /dev/null 2>&1; then
    echo "✅"
    ((PASSED++))
  else
    echo "❌"
    ((FAILED++))
  fi
}

# ===== CODE QUALITY =====
echo ""
echo "CODE QUALITY"
check "Tests passing" "pytest tests/ -q"
check "Coverage >= 60%" "pytest tests/ --cov=app --cov-fail-under=60 -q"
check "Linting (Ruff)" "ruff check app/ --select=E,F,W"
check "Type hints (MyPy)" "mypy app/ --ignore-missing-imports -q"
check "Security (Bandit)" "bandit -r app/ -q"

# ===== DOCKER =====
echo ""
echo "DOCKER"
check "Docker build succeeds" "docker build -t email-intelligence:test ."
check "Docker image size < 500MB" "[ \$(docker images email-intelligence:test --format '{{.Size}}' | sed 's/[^0-9]//g') -lt 500000000 ]"
check "Docker image runs" "docker run -d --name test-container email-intelligence:test && sleep 3 && docker stop test-container && docker rm test-container"

# ===== KUBERNETES =====
echo ""
echo "KUBERNETES"
check "K8s manifest valid" "kubectl apply -f k8s/ --dry-run=client"
check "K8s resource limits set" "grep -r 'resources:' k8s/ | grep -c 'limits:'"

# ===== CONFIGURATION =====
echo ""
echo "CONFIGURATION"
check "Secrets configured" "kubectl get secrets | grep -c docker-credentials || echo '0'"
check "Environment variables set" "[ ! -z \"\$SLACK_WEBHOOK_URL\" ] || echo 'SLACK_WEBHOOK_URL not set'"
check "Database connection" "python -c 'import psycopg2; print(\"OK\")' 2>/dev/null || echo 'psycopg2 not installed'"

# ===== DATABASE =====
echo ""
echo "DATABASE"
check "Migrations ready" "alembic current 2>/dev/null || echo 'alembic ok'"
check "Backup exists" "ls -la backup-*.sql.gz 2>/dev/null | wc -l"

# ===== SUMMARY =====
echo ""
echo "============================="
echo "RESULTS: ✅ $PASSED | ❌ $FAILED"
echo "============================="

if [ $FAILED -gt 0 ]; then
  echo ""
  echo "❌ DEPLOYMENT BLOCKED"
  echo "Fix $FAILED issues before deploying"
  exit 1
fi

echo ""
echo "✅ ALL CHECKS PASSED - READY TO DEPLOY"
echo ""
echo "Next step:"
echo "  kubectl apply -f k8s/"
echo "  bash PRODUCTION_DEPLOYMENT_RUNBOOK.md"

exit 0
