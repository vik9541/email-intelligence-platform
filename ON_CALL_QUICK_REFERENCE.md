# 🚨 ON-CALL QUICK REFERENCE

## STEP 1: TRIAGE (< 1 min)

Is it a real incident or false alarm?

```bash
# Check system status
curl http://email-intelligence:8000/health

# Check if Grafana shows data
open http://localhost:3000
```

**If health = 200**: Not P1, can wait until morning
**If health = timeout**: P1 INCIDENT

---

## STEP 2: ASSESS SEVERITY (< 2 min)

| Symptom | Severity | What to do |
|---------|----------|-----------|
| /health returns 500 | P1 | Go to STEP 4 |
| Error rate > 50% | P1 | Go to STEP 4 |
| Pods restarting | P2 | Go to STEP 5 |
| High latency (> 2s) | P2 | Go to STEP 6 |
| Memory leak | P2 | Restart pods |

---

## STEP 3: DECLARE INCIDENT (< 30 sec)

```bash
# Post to Slack
curl -X POST $SLACK_WEBHOOK_URL -H 'Content-type: application/json' \
  --data '{"text": "🚨 INCIDENT START: [what you observed]"}'

# Start timer
date +%s > /tmp/incident_start.txt
```

---

## STEP 4: QUICK FIXES (in order, try each)

### Fix 1: Restart pods (30 sec)
```bash
kubectl rollout restart deployment/email-intelligence
kubectl rollout status deployment/email-intelligence
curl http://email-intelligence:8000/health
```
✅ If works → DONE (goes to POST-INCIDENT)

### Fix 2: Rollback last deployment (1 min)
```bash
kubectl rollout undo deployment/email-intelligence
kubectl rollout status deployment/email-intelligence
curl http://email-intelligence:8000/health
```
✅ If works → DONE

### Fix 3: Scale up database connections (30 sec)
```bash
# If error = "too many connections"
kubectl set env deployment/email-intelligence \
  DB_POOL_SIZE=100 \
  --record
sleep 30
curl http://email-intelligence:8000/health
```
✅ If works → DONE

### Fix 4: Restore from backup (5 min)
```bash
# If database corrupted
kubectl scale deployment email-intelligence --replicas=0
bash scripts/restore-database.sh backup-latest.sql.gz
kubectl scale deployment email-intelligence --replicas=3
curl http://email-intelligence:8000/health
```

---

## STEP 5: IF NOTHING WORKS

```bash
# Get incident commander (escalate)
# Check phone list at: /root/.on-call-phone.txt

# Open war room call
# Slack: /call start

# Provide context:
# - kubectl describe pod [pod-name]
# - kubectl logs [pod-name] --tail=100
# - curl http://prometheus:9090/api/v1/query?query=errors_total
```

---

## STEP 6: POST-INCIDENT (after recovery)

```bash
# Calculate incident time
start=$(cat /tmp/incident_start.txt)
end=$(date +%s)
duration=$((end - start))
minutes=$((duration / 60))

# Post summary
curl -X POST $SLACK_WEBHOOK_URL -H 'Content-type: application/json' \
  --data "{
    \"text\": \"✅ INCIDENT RESOLVED\",
    \"blocks\": [{
      \"type\": \"section\",
      \"text\": {\"type\": \"mrkdwn\", \"text\": \"Duration: ${minutes} minutes\"}
    }]
  }"

# Create issue for post-mortem
gh issue create --title "Post-mortem: [incident title]" \
  --body "Duration: ${minutes} min\nAction items:\n- [ ] "
```

---

## USEFUL COMMANDS

```bash
# Check pods
kubectl get pods
kubectl describe pod [pod-name]
kubectl logs [pod-name] --tail=100 -f

# Check resources
kubectl top pods
kubectl describe nodes

# Check database
kubectl exec -it pod/postgres -- psql -U postgres -c "SELECT count(*) FROM observations;"

# Check errors
curl 'http://elasticsearch:9200/_search?q=level:ERROR&size=10'

# Restart all
kubectl rollout restart deployment/email-intelligence

# Scale pods
kubectl scale deployment email-intelligence --replicas=5

# Update image
kubectl set image deployment/email-intelligence \
  app=ghcr.io/vik9541/email-intelligence:vX.Y.Z

# Check HPA
kubectl get hpa
```

---

## EMERGENCY CONTACTS

- **Incident Commander**: $INCIDENT_COMMANDER_PHONE
- **Engineering Lead**: $LEAD_PHONE
- **Database Admin**: $DBA_PHONE

---

## KEY RESOURCES

- Grafana dashboard: http://localhost:3000
- Prometheus queries: http://localhost:9090
- Kibana logs: http://localhost:5601
- GitHub Actions: https://github.com/vik9541/email-intelligence-platform/actions

---

**REMEMBER**: Faster recovery > perfect solution
Try quick fixes first, escalate if stuck > 5 min
