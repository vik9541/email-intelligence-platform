# Capacity Planning & Scaling Strategy

## Current Baseline (Single Pod)
- CPU: 200m request, 500m limit
- Memory: 512Mi request, 1Gi limit
- Throughput: ~100 emails/sec
- Latency P95: < 200ms

## Scaling Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU | > 70% | Add pod (target 50%) |
| Memory | > 80% | Add pod (target 60%) |
| Requests/sec | > 5000 | Add pod |
| Database conn | > 80 | Increase pool size |
| P95 latency | > 1000ms | Add pod or optimize |

## Daily Load Pattern

```
Peak Hours (9 AM - 5 PM UTC):
├─ 09:00-12:00: 500-700 req/sec (Scale: 5-7 pods)
├─ 12:00-14:00: 800-1000 req/sec (Scale: 8-10 pods)
├─ 14:00-17:00: 600-800 req/sec (Scale: 6-8 pods)

Off-peak (5 PM - 9 AM UTC):
├─ 17:00-22:00: 100-200 req/sec (Scale: 2-3 pods)
├─ 22:00-06:00: 20-50 req/sec (Scale: 2 pods minimum)
├─ 06:00-09:00: 50-200 req/sec (Scale: 2-3 pods)
```

## Cost Optimization

| Config | Cost/Month | Pros | Cons |
|--------|-----------|------|------|
| Static 3 pods | $300 | Simple, predictable | Wastes off-peak |
| Auto 2-10 pods | $200 | ~33% savings | Variable latency |
| Auto 2-20 pods | $280 | High availability | ~33% more cost |
| Spot instances | $100 | Cheapest | 2min interruption |

**Recommendation**: Auto 2-10 pods for 80/20 optimal balance

## Testing Auto-Scaling

### Simulate peak load
```bash
# Scale up test
bash scripts/load-test.sh --duration=10m --users=1000

# Watch pods scale
kubectl get hpa -w
kubectl get pods -w
```

### Verify scale-down
```bash
# Wait for 5+ minutes with no load
# Check that pods scale down to 2

kubectl get hpa
# Should show: 2 current, 2 min
```

## Database Scaling

PostgreSQL connection pool should scale with app:
- 2 pods: 20 connections
- 5 pods: 50 connections
- 10 pods: 100 connections

Adjust in `.env`:
```
DB_POOL_SIZE=10 * NUM_PODS
```
