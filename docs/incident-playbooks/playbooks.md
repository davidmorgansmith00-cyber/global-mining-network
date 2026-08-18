# Incident Playbooks — Global Mining Network

> **Audience:** On-call engineers and operations team.  
> **Purpose:** Step-by-step procedures for common production incidents.  
> **Update policy:** Update after every incident post-mortem.

---

## Playbook 1 — High Error Rate

### Symptoms
- Error rate > 5% sustained for > 5 minutes (WARNING alert)
- Error rate > 10% sustained for > 2 minutes (CRITICAL — page on-call)

### Diagnosis Steps
1. Check `GET /api/v1/monitoring/errors` for the top fingerprinted errors.
2. Check `GET /api/v1/monitoring/metrics` for per-endpoint breakdown.
3. Look at application logs for the time window in question (Kibana / CloudWatch).
4. Determine whether errors are isolated to one endpoint or global.

### Mitigation
- **If DB-related:** See Playbook 4 (Database Down).
- **If code bug introduced by recent deploy:** Roll back the last deployment.
- **If external dependency:** Check dependency status page; enable circuit breaker if available.
- **If rate spike:** Enable rate limiting or scale horizontally.

### Resolution
- Confirm error rate drops below 1%.
- Document root cause in post-mortem.

---

## Playbook 2 — Slow Block Finalization

### Symptoms
- Block finalization latency > 10s (normal < 2s).
- Players report blocks not finalising.

### Diagnosis Steps
1. Check DB query performance dashboard for `blockchain` tables.
2. Check mining worker logs for exceptions or slowdowns.
3. Check system CPU and memory usage.
4. Check network latency between API and DB.

### Mitigation
- **DB overloaded:** Reduce mining worker concurrency; add read replica if available.
- **High CPU:** Restart mining workers in batches; scale out if autoscaling is available.
- **Code regression:** Roll back last deployment.

### Resolution
- Confirm block finalization latency returns to < 2s.
- Update MTTR in incident tracker.

---

## Playbook 3 — High API Latency

### Symptoms
- P99 latency > 1000ms (WARNING alert).
- Players report slow UI responses.

### Diagnosis Steps
1. Check `GET /api/v1/monitoring/metrics` for high-latency endpoints.
2. Check DB connection pool usage.
3. Check Redis cache hit rate.
4. Check for GC pauses in application logs.

### Mitigation
- **DB slow queries:** Add missing index or cache frequently queried data.
- **Connection pool exhausted:** Increase pool size or add connection pooler (PgBouncer).
- **Cache cold:** Pre-warm cache on deploy.
- **Horizontal scale needed:** Scale out API instances.

### Resolution
- Confirm P99 latency returns below 500ms.
- Document optimisation applied.

---

## Playbook 4 — Database Down

### Symptoms
- `GET /health/ready` returns `"database": "error"`.
- All API endpoints returning 503.

### Diagnosis Steps
1. Attempt `psql $DATABASE_URL` from app host. Note specific error.
2. Check DB host health: disk space, CPU, connections.
3. Check DB replication lag (if HA setup).
4. Review DB error logs.

### Mitigation
1. **If primary is down:** Initiate failover to replica.
   ```bash
   # Promote replica (adapt to your RDS/Postgres HA setup)
   pg_ctl promote -D /var/lib/postgresql/data
   ```
2. Update `DATABASE_URL` in environment to point to promoted replica.
3. Restart API pods.
4. If no replica: restore from most recent backup.
   ```bash
   pg_restore -d $DATABASE_URL latest_backup.dump
   ```

### Resolution
- Confirm `GET /health/ready` returns `"ready": true`.
- Verify all pending transactions are consistent.
- Run migration reconciliation if needed.

---

## Playbook 5 — Memory Leak

### Symptoms
- Memory usage increasing monotonically over hours.
- P99 latency rising slowly over time.
- OOM kills in application logs.

### Diagnosis Steps
1. Generate heap/memory profile for suspicious worker.
2. Compare memory usage at T=0, T=6h, T=12h.
3. Identify service with the steepest growth.

### Mitigation
1. **Immediate:** Restart affected service instances on a rolling basis (zero-downtime).
2. **Medium-term:** Profile with memory profiler, identify root cause.
3. **Patch:** Fix the leak and deploy.

### Resolution
- Confirm memory is stable after warm-up period (< 5% growth over 1h).

---

## Appendix

| Alert | Severity | Target SLA |
|-------|----------|------------|
| Error rate > 5% for 5min | WARNING | Acknowledged in 15min |
| Error rate > 10% for 2min | CRITICAL | Page on-call; response in 5min |
| P99 latency > 1000ms for 10min | WARNING | Acknowledged in 30min |
| Database connection pool exhausted | CRITICAL | Page on-call; response in 5min |
| Health check red | CRITICAL | Page on-call; response in 5min |
