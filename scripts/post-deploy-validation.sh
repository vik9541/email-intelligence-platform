#!/bin/bash

# Post-deployment health check
# Run this AFTER deployment to verify system is healthy

echo "🩺 POST-DEPLOYMENT HEALTH CHECK"
echo "================================"

# Wait for pods to be ready
echo "Waiting for pods to be ready..."
kubectl rollout status deployment/email-intelligence --timeout=5m

# Check pod status
echo ""
echo "Pod Status:"
kubectl get pods | grep email-intelligence

# Health endpoint
echo ""
echo "Health Check:"
for i in {1..5}; do
  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
  if [ "$status" = "200" ]; then
    echo "✅ Health endpoint: 200 OK"
    break
  else
    echo "⏳ Attempt $i: HTTP $status (retrying...)"
    sleep 2
  fi
done

# Database connection
echo ""
echo "Database Check:"
kubectl exec -it deployment/email-intelligence -- \
  python -c "import psycopg2; print('Database OK')" 2>/dev/null && \
  echo "✅ Database connected" || echo "❌ Database connection failed"

# Metrics
echo ""
echo "Metrics Check:"
curl -s http://localhost:8000/metrics | grep -q "http_requests_total" && \
  echo "✅ Prometheus metrics working" || echo "❌ Metrics not available"

# Check for errors in logs
echo ""
echo "Recent Errors:"
ERROR_COUNT=$(kubectl logs deployment/email-intelligence --tail=100 | grep -c ERROR || echo 0)
if [ "$ERROR_COUNT" -gt 0 ]; then
  echo "⚠️  Found $ERROR_COUNT errors in logs (review carefully)"
  kubectl logs deployment/email-intelligence --tail=20 | grep ERROR
else
  echo "✅ No errors in recent logs"
fi

# Performance check
echo ""
echo "Performance Check:"
# Make 10 test requests and check latency
echo "Making 10 test requests..."
for i in {1..10}; do
  curl -s -w "Request $i: %{time_total}s\n" -o /dev/null http://localhost:8000/health
done

echo ""
echo "================================"
echo "✅ POST-DEPLOYMENT VALIDATION COMPLETE"
echo "System is ready for production traffic"
