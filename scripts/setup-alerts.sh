#!/bin/bash

# Setup Prometheus alerts
kubectl apply -f k8s/prometheus-alerts.yaml

# Setup AlertManager
kubectl apply -f k8s/alertmanager-config.yaml

# Verify
kubectl get configmap | grep -E "prometheus|alertmanager"

echo "✅ Alerts configured"
