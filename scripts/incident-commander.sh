#!/bin/bash

# Incident commander dashboard

echo "🚨 INCIDENT COMMANDER DASHBOARD"
echo "=================================="

# Check critical metrics
echo "📊 System Status:"
echo "- Pods: $(kubectl get pods | grep Running | wc -l) running"
echo "- Error rate: $(curl -s http://localhost:9090/api/v1/query?query=errors_total | grep -o '"value":\["[^"]*"' | cut -d'"' -f4)"
echo "- P95 latency: $(curl -s http://localhost:9090/api/v1/query?query=http_request_duration | tail -1)"

echo ""
echo "Recent errors:"
curl -s http://elasticsearch:9200/_all/_search?q=severity:error&size=5 | grep -o '"message":"[^"]*"' | head -5

echo ""
echo "Useful commands:"
echo "- kubectl logs -f deployment/email-intelligence"
echo "- kubectl exec -it [pod] /bin/bash"
echo "- kubectl rollout undo deployment/email-intelligence"
