# Legacy Admin Operations Runbook

This runbook provides comprehensive guidance for operating, monitoring, and troubleshooting the Legacy Admin system in production.

## On-Call Procedures

### On-Call Roster

| Week | Primary | Secondary | Escalation |
|------|---------|-----------|------------|
| Week 1 | [Primary Name] | [Secondary Name] | [Manager Name] |
| Week 2 | [Primary Name] | [Secondary Name] | [Manager Name] |
| Week 3 | [Primary Name] | [Secondary Name] | [Manager Name] |
| Week 4 | [Primary Name] | [Secondary Name] | [Manager Name] |

### Escalation Procedure

1. Alerts are sent to the primary on-call engineer
2. If no response within 15 minutes, alerts are escalated to the secondary
3. If no response within 30 minutes, alerts are escalated to the manager
4. If the issue affects critical business functions, immediately escalate to the manager

### On-Call Handoff

Perform the following during on-call handoff:

1. Review any open incidents
2. Discuss known issues and potential problems
3. Transfer any knowledge about recent deployments
4. Update PagerDuty/on-call system with new contact details

## Common Operations

### Deployment

#### Standard Deployment

```bash
# Deploy to staging
git push origin develop

# Deploy to production (after staging verification)
git push origin main
```

#### Manual Deployment

```bash
# Deploy specific commit to staging
kubectl set image deployment/legacyadmin-web legacyadmin-web=ghcr.io/yourusername/legacyadmin:commit-sha-web
kubectl set image deployment/legacyadmin-celery legacyadmin-celery=ghcr.io/yourusername/legacyadmin:commit-sha-celery

# Verify deployment
kubectl rollout status deployment/legacyadmin-web
kubectl rollout status deployment/legacyadmin-celery
```

#### Rollback Procedure

```bash
# Get deployment history
kubectl rollout history deployment/legacyadmin-web

# Rollback to previous version
kubectl rollout undo deployment/legacyadmin-web
kubectl rollout undo deployment/legacyadmin-celery
```

### Database Operations

#### Backup

```bash
# Create a manual backup
kubectl exec -it deployment/legacyadmin-web -- ./scripts/backup_database.sh

# List available backups
kubectl exec -it deployment/legacyadmin-web -- ./scripts/restore_database.sh --list-only --from-s3
```

#### Restore

```bash
# Restore from backup
kubectl exec -it deployment/legacyadmin-web -- ./scripts/restore_database.sh legacyadmin_backup_YYYY-MM-DD_HH-MM-SS.sql.gz --from-s3
```

#### Database Migrations

```bash
# Run migrations
kubectl exec -it deployment/legacyadmin-web -- python manage.py migrate

# Show migration status
kubectl exec -it deployment/legacyadmin-web -- python manage.py showmigrations
```

### Scaling

#### Horizontal Scaling

```bash
# Scale web servers
kubectl scale deployment legacyadmin-web --replicas=5

# Scale Celery workers
kubectl scale deployment legacyadmin-celery --replicas=3
```

#### Vertical Scaling

```bash
# Update resource requests/limits in kubernetes/web-deployment.yaml and apply
kubectl apply -f kubernetes/web-deployment.yaml
```

### Cache Management

```bash
# Clear all caches
kubectl exec -it deployment/legacyadmin-web -- python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Clear specific cache
kubectl exec -it deployment/legacyadmin-web -- python manage.py shell -c "from django.core.cache import cache; cache.delete_pattern('underwriters:*')"
```

## Monitoring & Alerting

### Dashboards

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| Main | https://grafana.example.com/d/legacyadmin-main | Overall system health |
| Performance | https://grafana.example.com/d/legacyadmin-performance | Application performance |
| Database | https://grafana.example.com/d/legacyadmin-database | Database metrics |
| Errors | https://grafana.example.com/d/legacyadmin-errors | Error tracking |

### Key Metrics to Watch

#### System Health
- CPU and memory usage
- Disk space
- Pod restarts
- Error rates

#### Application Performance
- Request latency (p95 < 500ms)
- Request throughput
- Database query time
- Cache hit rate (target > 80%)

#### Business Metrics
- Daily active users
- Policy creation rate
- Underwriter usage distribution

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Error Rate | > 1% | > 5% | Check Sentry, logs |
| Response Time | > 500ms | > 1s | Check DB, cache |
| CPU Usage | > 70% | > 85% | Consider scaling |
| Memory Usage | > 80% | > 90% | Check for leaks |
| Disk Space | < 20% | < 10% | Clean or expand |

## Troubleshooting

### Common Issues and Solutions

#### High Response Times

1. **Check database performance**
   ```bash
   kubectl exec -it deployment/legacyadmin-web -- python manage.py dbstats
   ```

2. **Check cache hit rates**
   ```bash
   kubectl exec -it deployment/legacyadmin-web -- python manage.py shell -c "from django.core.cache import cache; print(cache.get_stats())"
   ```

3. **Check for slow queries**
   ```bash
   # Look at slow query log
   kubectl exec -it statefulset/postgres-0 -- cat /var/log/postgresql/postgresql-slow.log
   ```

#### High Error Rates

1. **Check application logs**
   ```bash
   kubectl logs -f deployment/legacyadmin-web --tail=100
   ```

2. **Check Sentry for detailed error reports**
   Visit https://sentry.io/organizations/your-org/issues/

3. **Verify recent deployments**
   ```bash
   kubectl rollout history deployment/legacyadmin-web
   ```

#### Database Connection Issues

1. **Check database connectivity**
   ```bash
   kubectl exec -it deployment/legacyadmin-web -- python -c "from django.db import connections; connections['default'].ensure_connection(); print('Connected successfully')"
   ```

2. **Check connection pool stats**
   ```bash
   kubectl exec -it deployment/legacyadmin-web -- python manage.py shell -c "from django.db import connections; print(connections['default'].pool.status())"
   ```

#### Celery Task Failures

1. **Check Celery worker logs**
   ```bash
   kubectl logs -f deployment/legacyadmin-celery --tail=100
   ```

2. **Check task queue status**
   ```bash
   kubectl exec -it deployment/legacyadmin-web -- python manage.py celery_inspect active
   ```

3. **View failed tasks**
   ```bash
   kubectl exec -it deployment/legacyadmin-web -- python manage.py celery_inspect revoked
   ```

### Diagnostic Commands

#### System Diagnostics

```bash
# Check system health
kubectl exec -it deployment/legacyadmin-web -- python manage.py check --deploy

# Check database connectivity
kubectl exec -it deployment/legacyadmin-web -- python manage.py dbcheck

# Run self-diagnostics
kubectl exec -it deployment/legacyadmin-web -- python manage.py diagnose
```

#### Performance Diagnostics

```bash
# Profile a request
kubectl exec -it deployment/legacyadmin-web -- python -m pyinstrument -m django.core.wsgi

# Analyze memory usage
kubectl exec -it deployment/legacyadmin-web -- python -m memory_profiler manage.py memory_usage
```

## Emergency Procedures

### Service Outage

1. **Verify the outage**
   - Check external monitoring (Pingdom, UptimeRobot)
   - Try accessing the application from different networks
   - Check cloud provider status page

2. **Assess the scope**
   - Is it affecting all users or a subset?
   - Is it a complete outage or degraded service?
   - Are all features affected or only specific ones?

3. **Check critical components**
   ```bash
   # Check web servers
   kubectl get pods -l app=legacyadmin-web
   
   # Check database
   kubectl exec -it statefulset/postgres-0 -- pg_isready
   
   # Check Redis
   kubectl exec -it deployment/legacyadmin-web -- redis-cli -h redis ping
   ```

4. **Implement immediate mitigation**
   - For deployment issues: rollback to last known good version
   - For resource issues: scale up affected services
   - For database issues: check for blocking queries, terminate if necessary

5. **Communication**
   - Update status page
   - Notify stakeholders through established channels
   - Provide regular updates (every 30 minutes)

6. **Post-mortem**
   - Document the incident
   - Identify root cause
   - Implement preventative measures

### Data Breach

1. **Contain the breach**
   - Identify affected systems
   - Isolate compromised components
   - Revoke any compromised credentials

2. **Assess the impact**
   - What data was potentially exposed?
   - How many users are affected?
   - What is the sensitivity of the exposed data?

3. **Engage security team**
   - Follow the established security incident response plan
   - Involve legal team for compliance requirements
   - Document all actions taken

4. **Notification and reporting**
   - Notify affected users as required by law
   - Report to relevant authorities if required
   - Provide guidance on protective actions for affected users

## Maintenance Procedures

### Scheduled Maintenance

1. **Preparation**
   - Plan maintenance window during low-traffic periods
   - Communicate maintenance window to stakeholders at least 48 hours in advance
   - Prepare rollback plan

2. **Execution**
   - Announce start of maintenance
   - Implement changes according to plan
   - Test functionality after changes
   - Document all actions taken

3. **Completion**
   - Verify system health after maintenance
   - Announce completion of maintenance
   - Monitor system closely for 24 hours after maintenance

### Database Maintenance

#### Vacuum and Analyze

```bash
# Regular maintenance (run weekly)
kubectl exec -it statefulset/postgres-0 -- psql -U postgres -c "VACUUM ANALYZE;"

# Full vacuum (run monthly)
kubectl exec -it statefulset/postgres-0 -- psql -U postgres -c "VACUUM FULL ANALYZE;"
```

#### Index Maintenance

```bash
# Rebuild indexes (run monthly)
kubectl exec -it statefulset/postgres-0 -- psql -U postgres -c "REINDEX DATABASE legacyadmin;"
```

## Compliance and Audit

### Security Scanning

```bash
# Run security scan
./scripts/security_scan.sh https://app.example.com
```

### Audit Log Review

```bash
# Export audit logs for review
kubectl exec -it deployment/legacyadmin-web -- python manage.py export_audit_logs --start-date=YYYY-MM-DD --end-date=YYYY-MM-DD --output=audit.csv
```

### Compliance Verification

```bash
# Run POPIA compliance check
kubectl exec -it deployment/legacyadmin-web -- python manage.py compliance_check
```

## Contact Information

### Team Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| Lead Developer | [Name] | [Email] | [Phone] |
| DevOps Engineer | [Name] | [Email] | [Phone] |
| Database Admin | [Name] | [Email] | [Phone] |
| Security Officer | [Name] | [Email] | [Phone] |

### External Contacts

| Service | Provider | Support Contact | Account ID |
|---------|----------|-----------------|------------|
| Cloud Hosting | [Provider] | [Contact] | [ID] |
| Database | [Provider] | [Contact] | [ID] |
| DNS | [Provider] | [Contact] | [ID] |
| SSL Certificates | [Provider] | [Contact] | [ID] |
