# 🚀 PRODUCTION DEPLOYMENT RUNBOOK

**Version**: 1.0.0  
**Last Updated**: 2025-12-14  
**Estimated Time**: 30-35 minutes  
**Owner**: DevOps Team

---

## PRE-DEPLOYMENT CHECKLIST

- [ ] All team members notified
- [ ] Maintenance window scheduled
- [ ] Rollback plan reviewed
- [ ] Backup completed and verified
- [ ] Monitoring dashboards open

---

## STEP 0: Pre-Flight Check (5 min)

### 0.1 Verify Repository Status
```bash
cd C:\Projects\email-service
git status  # must be clean
git log --oneline -5  # latest commits
```
**Expected**: No uncommitted changes, all ТЗ commits visible

### 0.2 Verify GitHub Actions
```bash
# Check latest workflow run
gh run list --limit 5
# Or visit: https://github.com/vik9541/email-intelligence-platform/actions
```
**Expected**: All checks ✅ PASSED (test-python, lint, test-docker, security, all-checks)

### 0.3 Verify Kubernetes Cluster
```bash
kubectl cluster-info
kubectl get nodes
kubectl get pods --all-namespaces
```
**Expected**: 
- Cluster responding
- All nodes in `Ready` state
- No pods in `CrashLoopBackOff`

### 0.4 Verify Secrets
```bash
kubectl get secrets -n default
```
**Expected secrets**:
- `docker-credentials`
- `postgres-secret`
- `grafana-secret`
- `aws-credentials` (for backups)

---

## STEP 1: Build & Push Docker Image (5 min)

### 1.1 Build locally (smoke test)
```bash
docker build -t email-service:test .
docker images | grep email-service
```
**Expected**: Image built successfully, size < 500MB

### 1.2 Test image locally
```bash
docker run -d -p 8001:8000 --name email-test email-service:test
sleep 5
curl http://localhost:8000/health
docker stop email-test && docker rm email-test
```
**Expected**: `{"status": "ok", "timestamp": "..."}`

### 1.3 Trigger production build
```bash
# Option A: Push to main (triggers automatic build)
git push origin main

# Option B: Manual workflow dispatch
gh workflow run deploy.yml
```

### 1.4 Monitor build
```bash
# Watch GitHub Actions
gh run watch
```
**Expected**: Deploy workflow completes successfully, Docker image pushed to GHCR

---

## STEP 2: Deploy Infrastructure (5 min)

### 2.1 Deploy database (if not exists)
```bash
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl rollout status deployment/postgres
```

### 2.2 Deploy monitoring stack
```bash
kubectl apply -f k8s/prometheus-config.yaml
kubectl apply -f k8s/grafana-deployment.yaml
kubectl apply -f k8s/elasticsearch-deployment.yaml
kubectl apply -f k8s/kibana-deployment.yaml
```

### 2.3 Verify infrastructure pods
```bash
kubectl get pods
```
**Expected**: All infrastructure pods `Running`

---

## STEP 3: Deploy Application (5 min)

### 3.1 Validate manifests
```bash
kubectl apply -f k8s/deployment.yaml --dry-run=client
kubectl apply -f k8s/service.yaml --dry-run=client
kubectl apply -f k8s/configmap.yaml --dry-run=client
```
**Expected**: No validation errors

### 3.2 Deploy application
```bash
kubectl apply -f k8s/
```

### 3.3 Watch rollout
```bash
kubectl rollout status deployment/email-service
kubectl get pods -w
```
**Expected**: 
- Rollout completes successfully
- New pods in `Running` state
- Old pods terminated gracefully

### 3.4 Verify deployment
```bash
kubectl get deployment email-service
kubectl describe deployment email-service
```
**Expected**: 
- `READY: 1/1` (or 3/3 if replicas=3)
- `AVAILABLE: 1`

---

## STEP 4: Health Checks (5 min)

### 4.1 Application health
```bash
kubectl port-forward svc/email-service 8000:8000
```
In another terminal:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```
**Expected**: 
- Health: `{"status": "ok", "timestamp": "..."}`
- Metrics: Prometheus format output

### 4.2 Database connection
```bash
kubectl exec -it deployment/email-service -- python -c "
from app.db import engine
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('✅ Database connected')
"
```
**Expected**: `✅ Database connected`

### 4.3 Check application logs
```bash
kubectl logs -f deployment/email-service --tail=50
```
**Expected**: 
- No `ERROR` or `CRITICAL` messages
- INFO level startup messages
- No connection errors

---

## STEP 5: Monitoring Setup (3 min)

### 5.1 Verify Prometheus
```bash
kubectl port-forward svc/prometheus 9090:9090
```
Open: http://localhost:9090
- Navigate to **Status → Targets**
- Verify `email-service` target is **UP**

### 5.2 Verify Grafana
```bash
kubectl port-forward svc/grafana 3000:3000
```
Open: http://localhost:3000
- Login: `admin` / [password from secret]
- Check dashboard shows live data
- All panels populated

### 5.3 Verify Kibana (logs)
```bash
kubectl port-forward svc/kibana 5601:5601
```
Open: http://localhost:5601
- Create index pattern: `filebeat-*`
- Verify logs appearing

---

## STEP 6: Smoke Tests (5 min)

### 6.1 Test email processing endpoint
```bash
curl -X POST http://localhost:8000/api/observations/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "email_id": "test-001",
    "sender": "test@example.com",
    "subject": "Production test",
    "body": "Testing production deployment"
  }'
```
**Expected**: `{"status": "success", "analysis": {...}}`

### 6.2 Database write verification
```bash
kubectl exec -it deployment/email-service -- python -c "
from app.models import Observation
from app.db import SessionLocal
db = SessionLocal()
count = db.query(Observation).count()
print(f'✅ Database has {count} observations')
db.close()
"
```

### 6.3 Check error rates
```bash
curl http://localhost:8000/metrics | grep errors_total
```
**Expected**: Low or zero error count

---

## STEP 7: Load Test (Optional, 5 min)

### 7.1 Run baseline load test
```bash
pip install locust
bash scripts/load-test.sh
```

### 7.2 Monitor during load
Open Grafana dashboard and watch:
- **CPU usage**: Should stay < 70%
- **Memory**: Should be stable
- **Latency**: P95 < 1 second
- **Error rate**: < 0.5%

---

## STEP 8: Verification & Sign-Off (5 min)

### 8.1 Final checklist
```bash
# Quick verification script
kubectl get pods | grep email-service  # Running
curl http://localhost:8000/health  # OK
kubectl logs deployment/email-service --tail=20 | grep ERROR  # None
kubectl get hpa  # If autoscaling configured
```

### 8.2 Complete checklist
- [ ] All pods `Running`
- [ ] Health endpoint responding ✅
- [ ] Database connected ✅
- [ ] Prometheus scraping ✅
- [ ] Grafana showing data ✅
- [ ] Email processing working ✅
- [ ] No errors in logs ✅
- [ ] Load test passed (if run) ✅

### 8.3 Team notification
```bash
# Post to Slack (if configured)
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-type: application/json' \
  --data '{
    "text": "✅ Production deployment completed successfully!",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Production Status:* ✅ ALL SYSTEMS OPERATIONAL\n*Version:* v1.0.0\n*Deployed:* '$(date)'\n*Health:* https://email-service/health"
        }
      }
    ]
  }'
```

---

## TROUBLESHOOTING

### Issue: Pods not starting

**Symptoms**: Pods in `Pending` or `CrashLoopBackOff`

**Diagnosis**:
```bash
kubectl describe pod [pod-name]
kubectl logs [pod-name]
kubectl get events --sort-by='.lastTimestamp'
```

**Common causes**:
1. **Image pull error**: Check GHCR credentials
   ```bash
   kubectl get secret docker-credentials -o yaml
   ```
2. **Resource limits**: Check node resources
   ```bash
   kubectl top nodes
   ```
3. **Config errors**: Check ConfigMap/Secrets
   ```bash
   kubectl get configmap
   kubectl get secrets
   ```

### Issue: Database connection failed

**Symptoms**: Application logs show connection errors

**Diagnosis**:
```bash
kubectl exec -it deployment/postgres -- psql -U postgres -c "SELECT 1"
kubectl get svc postgres
```

**Fix**:
```bash
# Check service DNS
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup postgres

# Test direct connection
kubectl port-forward svc/postgres 5432:5432
psql -h localhost -U postgres -d email_db
```

### Issue: High latency

**Symptoms**: Requests taking > 2 seconds

**Diagnosis**:
```bash
kubectl top pods
kubectl get hpa
kubectl describe deployment email-service
```

**Fix**:
```bash
# Scale up immediately
kubectl scale deployment email-service --replicas=3

# Check resource limits
kubectl edit deployment email-service
# Increase CPU/memory limits
```

### Issue: Monitoring not working

**Symptoms**: Grafana showing no data

**Diagnosis**:
```bash
kubectl logs deployment/prometheus
kubectl port-forward svc/prometheus 9090:9090
# Check http://localhost:9090/targets
```

**Fix**:
```bash
# Recreate Prometheus config
kubectl delete configmap prometheus-config
kubectl apply -f k8s/prometheus-config.yaml
kubectl rollout restart deployment/prometheus
```

---

## ROLLBACK PROCEDURE

### When to rollback
- Critical bugs in production
- Performance degradation > 50%
- Error rate > 5%
- Database corruption detected

### Rollback steps

#### Option 1: Kubernetes rollback
```bash
# View deployment history
kubectl rollout history deployment/email-service

# Rollback to previous version
kubectl rollout undo deployment/email-service

# Rollback to specific revision
kubectl rollout undo deployment/email-service --to-revision=2

# Verify rollback
kubectl rollout status deployment/email-service
```

#### Option 2: Git revert + redeploy
```bash
# Identify problematic commit
git log --oneline -10

# Revert commit
git revert [commit-hash]
git push origin main

# Wait for GitHub Actions to build and deploy
gh run watch
```

#### Option 3: Manual image rollback
```bash
# Update deployment with previous image
kubectl set image deployment/email-service \
  email-service=ghcr.io/vik9541/email-intelligence-platform:v0.9.0

# Verify
kubectl rollout status deployment/email-service
```

### Post-rollback
1. Verify all services operational
2. Check metrics and logs
3. Create incident report
4. Schedule post-mortem
5. Document root cause

---

## POST-DEPLOYMENT MONITORING

### First 30 minutes
```bash
# Watch logs continuously
kubectl logs -f deployment/email-service

# Monitor metrics
watch kubectl top pods

# Check error rates every 5 minutes
watch -n 300 'curl http://localhost:8000/metrics | grep errors_total'
```

### First 24 hours
- [ ] Check Grafana dashboard every 2 hours
- [ ] Review error logs every 4 hours
- [ ] Monitor database connection pool
- [ ] Check disk space usage
- [ ] Review backup job execution

### First week
- [ ] Daily health check review
- [ ] Performance trending analysis
- [ ] User feedback collection
- [ ] Load test comparison
- [ ] Cost analysis (cloud resources)

---

## SUCCESS CRITERIA

✅ **Deployment is successful if**:
1. All pods running for > 30 minutes
2. No critical errors in logs
3. Health endpoint returning 200 OK
4. P95 latency < 1 second
5. Error rate < 0.5%
6. Database queries executing normally
7. Monitoring dashboards showing data
8. No user-reported issues

---

## CONTACTS

**DevOps Lead**: @devops-lead  
**Database Admin**: @db-admin  
**Tech Lead**: @tech-lead  
**On-Call Engineer**: @on-call  
**Slack Channel**: #email-service-deployment  
**Incident Channel**: #incidents

---

## APPENDIX: Quick Reference Commands

```bash
# Status checks
kubectl get all
kubectl get pods -o wide
kubectl get svc
kubectl get configmap
kubectl get secrets

# Logs
kubectl logs -f deployment/email-service
kubectl logs deployment/email-service --previous  # Previous container
kubectl logs -l app=email-service --all-containers=true

# Debugging
kubectl exec -it deployment/email-service -- /bin/bash
kubectl describe pod [pod-name]
kubectl get events --sort-by='.lastTimestamp'

# Scaling
kubectl scale deployment email-service --replicas=3
kubectl autoscale deployment email-service --min=2 --max=10 --cpu-percent=70

# Updates
kubectl set image deployment/email-service email-service=image:tag
kubectl rollout restart deployment/email-service
kubectl rollout status deployment/email-service
kubectl rollout undo deployment/email-service

# Port forwarding
kubectl port-forward svc/email-service 8000:8000
kubectl port-forward svc/grafana 3000:3000
kubectl port-forward svc/prometheus 9090:9090
```

---

**END OF RUNBOOK**

✅ **Deployment Time**: 30-35 minutes  
🎯 **Next Steps**: Monitor for 24 hours, then schedule go-live for Friday
