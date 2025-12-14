#!/bin/bash

# Generate capacity utilization report

echo "📊 CAPACITY UTILIZATION REPORT"
echo "=============================="

# Current usage
echo ""
echo "Current Pod Status:"
kubectl get hpa
kubectl top pods --sort-by=memory | head -10

# Projected needs
echo ""
echo "Projected Needs (7-day average):"
PEAK_LOAD=$(kubectl top nodes | tail -1 | awk '{print $3}')
echo "- Peak CPU: ${PEAK_LOAD}%"
echo "- Peak Memory: $(kubectl top pods | awk '{sum+=$3} END {print sum}') Mi"

# Cost analysis
echo ""
echo "Cost Analysis:"
echo "- Current pods: $(kubectl get deployment email-intelligence -o jsonpath='{.spec.replicas}')"
COST=$(kubectl get deployment email-intelligence -o jsonpath='{.spec.replicas}' | awk '{print $1 * 100}')
echo "- Estimated monthly cost: \$$COST"

# Recommendations
echo ""
echo "Recommendations:"
if [ "$PEAK_LOAD" -gt 70 ]; then
  echo "⚠️  Increase max replicas (current load approaching limit)"
fi
if [ "$PEAK_LOAD" -lt 30 ]; then
  echo "💰 Consider reducing max replicas (over-provisioned)"
fi
