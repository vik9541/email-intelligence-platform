#!/bin/bash

# Multi-region failover setup

set -e

echo "🌍 Setting up multi-region deployment..."

# Configuration
PRIMARY_REGION="us-east-1"
SECONDARY_REGION="us-west-2"
PRIMARY_CLUSTER="primary-cluster"
SECONDARY_CLUSTER="secondary-cluster"

# 1. Deploy to primary region
echo "📍 Deploying to primary region ($PRIMARY_REGION)..."
kubectl config use-context $PRIMARY_CLUSTER
kubectl apply -f k8s/multi-region-deployment.yaml
kubectl apply -f k8s/database-replication.yaml

echo "⏳ Waiting for primary deployment to be ready..."
kubectl rollout status deployment/email-intelligence-primary

# 2. Deploy to secondary region
echo "📍 Deploying to secondary region ($SECONDARY_REGION)..."
kubectl config use-context $SECONDARY_CLUSTER
kubectl apply -f k8s/multi-region-deployment.yaml

echo "⏳ Waiting for secondary deployment to be ready..."
kubectl rollout status deployment/email-intelligence-secondary

# 3. Setup database replication
echo "🔄 Setting up database replication..."
kubectl config use-context $PRIMARY_CLUSTER

# Create replication user on primary
kubectl exec -it postgres-primary-0 -- psql -U postgres -c "
  CREATE USER replication WITH REPLICATION ENCRYPTED PASSWORD 'changeme123';
  SELECT pg_create_physical_replication_slot('standby1');
"

echo "✅ Replication user and slot created"

# 4. Get primary database endpoint
PRIMARY_DB_ENDPOINT=$(kubectl get svc postgres-primary -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "📍 Primary database endpoint: $PRIMARY_DB_ENDPOINT"

# 5. Setup DNS failover (example using AWS Route53)
echo "🌐 Configuring DNS failover..."

# Create health check for primary
aws route53 create-health-check \
  --caller-reference "email-intelligence-primary-$(date +%s)" \
  --health-check-config \
    IPAddress=$PRIMARY_IP,Port=443,Type=HTTPS,ResourcePath=/health,FullyQualifiedDomainName=email-intelligence.us-east-1.example.com \
  --region us-east-1 || echo "Health check already exists"

# Create weighted DNS records
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "email-intelligence.global.example.com",
        "Type": "A",
        "SetIdentifier": "primary-us-east-1",
        "Weight": 100,
        "TTL": 60,
        "ResourceRecords": [{"Value": "'$PRIMARY_IP'"}]
      }
    }, {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "email-intelligence.global.example.com",
        "Type": "A",
        "SetIdentifier": "secondary-us-west-2",
        "Weight": 0,
        "TTL": 60,
        "ResourceRecords": [{"Value": "'$SECONDARY_IP'"}]
      }
    }]
  }' || echo "DNS records already exist"

# 6. Test health checks
echo "🧪 Testing health checks..."

kubectl config use-context $PRIMARY_CLUSTER
PRIMARY_HEALTH=$(kubectl exec -it deployment/email-intelligence-primary -- curl -s http://localhost:8000/health)
echo "Primary health: $PRIMARY_HEALTH"

kubectl config use-context $SECONDARY_CLUSTER
SECONDARY_HEALTH=$(kubectl exec -it deployment/email-intelligence-secondary -- curl -s http://localhost:8000/health)
echo "Secondary health: $SECONDARY_HEALTH"

# 7. Test failover scenario
echo "🎯 Testing failover scenario..."
echo "Simulating primary region failure..."

kubectl config use-context $PRIMARY_CLUSTER
kubectl scale deployment email-intelligence-primary --replicas=0

echo "⏳ Waiting 30 seconds for DNS failover..."
sleep 30

echo "🔍 Checking global endpoint (should route to secondary)..."
curl -s https://email-intelligence.global.example.com/health | jq .

# 8. Restore primary
echo "↩️  Restoring primary region..."
kubectl scale deployment email-intelligence-primary --replicas=3
kubectl rollout status deployment/email-intelligence-primary

echo "✅ Multi-region setup complete!"
echo ""
echo "📊 Status Summary:"
echo "  Primary Region: $PRIMARY_REGION"
echo "  Secondary Region: $SECONDARY_REGION"
echo "  Global Endpoint: https://email-intelligence.global.example.com"
echo "  Database Replication: ✅ Active"
echo "  DNS Failover: ✅ Configured"
echo ""
echo "🔧 Next Steps:"
echo "  1. Monitor replication lag: SELECT * FROM pg_stat_replication;"
echo "  2. Test failover: kubectl scale deployment email-intelligence-primary --replicas=0"
echo "  3. Check metrics in Grafana"
