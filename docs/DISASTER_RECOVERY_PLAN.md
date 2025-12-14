# Disaster Recovery Plan

## RTO (Recovery Time Objective): 30 minutes
## RPO (Recovery Point Objective): 24 hours

### Backup Strategy
- Daily full backups at 2 AM UTC
- 7-day retention (automatic cleanup)
- Stored in S3 with versioning
- Backup size: ~50-100 MB per day

### Recovery Procedure
1. Identify issue (data corruption, accidental delete)
2. List available backups: `aws s3 ls s3://email-backups/`
3. Execute recovery: `bash scripts/restore-database.sh backup-*.sql.gz`
4. Verify data integrity
5. Run health checks
6. Monitor application for 1 hour

### Testing
Recovery procedure should be tested:
- Monthly dry-run
- After each major deployment
- Team should practice recovery steps

## Backup Retention Policy

### Storage Tiers
- **Hot Storage** (7 days): Immediate access
- **Cold Storage** (30 days): Glacier storage
- **Archive** (90 days): Deep Archive

### Automated Cleanup
```bash
# Cleanup script runs daily after backup
aws s3 ls s3://email-backups/ | awk '{print $4}' | \
  while read file; do
    age=$((($(date +%s) - $(date -d "$(echo $file | cut -d- -f2)" +%s)) / 86400))
    if [ $age -gt 7 ]; then
      aws s3 mv s3://email-backups/$file s3://email-backups-archive/$file --storage-class GLACIER
    fi
  done
```

## Disaster Scenarios

### Scenario 1: Data Corruption
**Symptoms**: Invalid data in database, application errors  
**Response**:
1. Stop application immediately
2. Identify last known good backup
3. Execute restore procedure
4. Validate data integrity
5. Resume operations

**Time Estimate**: 20-30 minutes

### Scenario 2: Accidental Deletion
**Symptoms**: Missing records, user reports  
**Response**:
1. Identify deletion timestamp
2. Find backup before deletion
3. Restore specific tables (partial restore)
4. Merge with current data if needed

**Time Estimate**: 30-45 minutes

### Scenario 3: Database Server Failure
**Symptoms**: Connection errors, timeout  
**Response**:
1. Spin up new PostgreSQL instance
2. Restore latest backup
3. Update connection strings
4. Redeploy application

**Time Estimate**: 45-60 minutes

## Contact Information

**Database Administrator**: @db-admin  
**DevOps Lead**: @devops-lead  
**Escalation**: #incident-response (Slack)

## Post-Recovery Checklist

- [ ] All services restored
- [ ] Data integrity verified
- [ ] Application health checks passing
- [ ] Monitoring alerts cleared
- [ ] Incident report documented
- [ ] Root cause analysis scheduled
- [ ] Recovery procedure reviewed and updated

## Recovery Verification Commands

```bash
# Check database size
psql -h postgres -U postgres -d email_db -c "SELECT pg_size_pretty(pg_database_size('email_db'));"

# Check table counts
psql -h postgres -U postgres -d email_db -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"

# Check recent records
psql -h postgres -U postgres -d email_db -c "SELECT COUNT(*), MAX(created_at) FROM observations;"

# Application health
curl http://localhost:8000/health

# Database connections
psql -h postgres -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

## Lessons Learned

After each recovery incident, document:
1. What went wrong?
2. How was it detected?
3. How long did recovery take?
4. What can be improved?
5. Training needs identified?

**Last Updated**: 2025-12-14  
**Next Review Date**: 2026-01-14
