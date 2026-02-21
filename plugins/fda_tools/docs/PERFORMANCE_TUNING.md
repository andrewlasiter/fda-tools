# PostgreSQL Performance Tuning Guide

**FDA-197** — PostgreSQL Performance Benchmarking and Optimization
**Applies to:** `PostgreSQLDatabase` in `lib/postgres_database.py`, `UpdateCoordinator` in `scripts/update_coordinator.py`

---

## Benchmark Results (as of 2026-02-21)

Run the benchmark suite to get current numbers:

```bash
# Fast unit tests (always):
pytest plugins/fda_tools/tests/bench_postgres_performance.py -m "not benchmark and not slow"

# Full benchmark scenarios (slow, requires ~3s):
pytest plugins/fda_tools/tests/bench_postgres_performance.py -v -m "benchmark and slow" -s
```

### Scenario 1 — Query Performance

| Metric | Value | Target |
|--------|-------|--------|
| PG primary-key lookup p99 | ~1.5ms | < 5ms ✅ |
| PG GIN-indexed JSONB scan p50 | ~9ms | < 50ms ✅ |
| JSON full-directory disk scan p50 | ~8ms (200 files) | N/A |
| Speedup at 10K records (projected) | ~10–50x | 50–200x at scale |

**Note:** At 200 records, JSON disk scan and PG GIN scan have similar latency (both ~8–11ms). The PG advantage scales super-linearly: at 10K records, JSON disk scan = ~400ms while PG GIN scan stays ~10ms (40x speedup). At 100K records the gap is ~200x.

### Scenario 2 — Concurrent Access (24 agents)

| Metric | Value | Target |
|--------|-------|--------|
| p50 latency | ~1.0ms | < 5ms ✅ |
| p95 latency | ~1.8ms | < 8ms ✅ |
| p99 latency | ~2.3ms | < 10ms ✅ |
| Lock errors (24 threads) | 0 | 0 ✅ |

The `ThreadedConnectionPool` (psycopg2) handles 24 concurrent agents without lock contention. Pool size of 20 is sufficient; do not exceed 50 without increasing `max_connections` in PostgreSQL.

### Scenario 3 — Bulk Import

| Method | Rate | Time (1K records) | Speedup |
|--------|------|-------------------|---------|
| Individual INSERTs | ~600 rec/s | ~1.7s | 1x |
| PostgreSQL COPY | ~38K rec/s | ~0.026s | ~63x |

Always use `COPY` for initial data loads and large batch updates.

### Scenario 4 — Storage Efficiency

| Metric | Value | Target |
|--------|-------|--------|
| Average raw JSON size | ~1,579 bytes/record | N/A |
| Average JSONB TOAST compressed | ~575 bytes/record | N/A |
| Compression ratio | 2.75x | > 2x ✅ |
| Reduction percentage | 63.6% | 40–60% ✅ |
| GIN index overhead | ~20% | < 30% ✅ |
| Net storage savings | ~43.6% | > 20% ✅ |

---

## Connection Pool Tuning

### Current Configuration

```python
# postgres_database.py default
PostgreSQLDatabase(
    port=6432,       # PgBouncer (not direct PG port 5432)
    pool_size=20,    # Connections in the Python-side pool
    ssl_mode="prefer"
)
```

### Pool Size Guidelines

| Scenario | Recommended `pool_size` | Notes |
|----------|------------------------|-------|
| Dev / single agent | 5 | Minimal resource usage |
| Production / 20 agents | 20 | Default; sufficient for 167-agent orchestrator with queuing |
| High-throughput / 50+ agents | 30–40 | Increase PgBouncer `max_client_conn` to match |
| Peak load testing | 50 | Maximum; beyond this, increase PG `max_connections` |

### PgBouncer Configuration

PgBouncer sits in front of PostgreSQL on port 6432. Key settings in `pgbouncer.ini`:

```ini
[pgbouncer]
pool_mode = transaction        # Most efficient for short queries
max_client_conn = 200          # Max clients to PgBouncer (≥ Python pool_size × agents)
default_pool_size = 20         # Server-side connections to PostgreSQL
min_pool_size = 5              # Idle connections kept warm
reserve_pool_size = 5          # Emergency overflow pool
reserve_pool_timeout = 5       # Seconds before using reserve pool
server_idle_timeout = 300      # Reclaim idle server connections after 5 min
```

**Choosing `pool_mode`:**
- `transaction`: Best for short OLTP queries (our use case). Each query releases the connection immediately.
- `session`: Required for prepared statements and `SET LOCAL`. Use if `upsert_record()` triggers deadlocks.
- `statement`: Highest throughput but incompatible with multi-statement transactions.

---

## Index Strategy

### Existing GIN Indexes

All OpenFDA JSONB columns have GIN indexes for containment queries (`@>`):

```sql
-- Verify indexes exist
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename LIKE 'fda_%'
ORDER BY tablename, indexname;
```

Expected indexes per table:

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| `fda_510k` | `idx_510k_k_number` | btree | Primary key lookup |
| `fda_510k` | `idx_510k_product_code` | btree | Filter by product code |
| `fda_510k` | `idx_510k_openfda_gin` | GIN | JSONB containment queries |
| `fda_510k` | `idx_510k_decision_date` | btree | Date range queries |
| `fda_maude_events` | `idx_maude_product_code` | btree | Safety lookups |
| `fda_maude_events` | `idx_maude_openfda_gin` | GIN | JSONB containment |
| `fda_recalls` | `idx_recalls_product_code` | btree | Recall lookups |

### Trigram Indexes for Full-Text Search

For `device_name` or `decision_description` free-text searches, add `pg_trgm` indexes:

```sql
-- Enable extension (run once as superuser)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Add trigram index for device name search
CREATE INDEX CONCURRENTLY idx_510k_device_name_trgm
    ON fda_510k USING GIN (device_name gin_trgm_ops);

-- Query usage
SELECT k_number, device_name FROM fda_510k
WHERE device_name % 'titanium catheter'  -- similarity search
ORDER BY similarity(device_name, 'titanium catheter') DESC
LIMIT 20;
```

### BRIN Indexes for Time-Series Data

For `decision_date` range queries on large tables (MAUDE has millions of rows), BRIN is more space-efficient than B-tree:

```sql
-- Replace existing btree date index with BRIN for tables > 10M rows
DROP INDEX IF EXISTS idx_maude_date_received;
CREATE INDEX CONCURRENTLY idx_maude_date_received_brin
    ON fda_maude_events USING BRIN (date_received)
    WITH (pages_per_range = 128);
```

**When to use BRIN vs B-tree:**
- B-tree: Random inserts (510k, classification) — BRIN performs poorly
- BRIN: Time-ordered inserts (MAUDE events, enforcement actions) — 10–100x smaller index

---

## Query Optimization

### Enable `pg_stat_statements`

Profile slow queries in production:

```sql
-- Enable in postgresql.conf
-- shared_preload_libraries = 'pg_stat_statements'
-- Then reload:
SELECT pg_reload_conf();

-- Find slowest queries
SELECT query, calls, total_exec_time / calls AS avg_ms,
       rows / calls AS avg_rows, stddev_exec_time
FROM pg_stat_statements
WHERE calls > 10
ORDER BY total_exec_time DESC
LIMIT 20;
```

### Using `EXPLAIN ANALYZE`

For any query taking > 100ms:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT k_number, device_name, openfda_json
FROM fda_510k
WHERE openfda_json @> '{"product_code": ["DQY"]}'::jsonb
  AND decision_date >= '2020-01-01'
ORDER BY decision_date DESC
LIMIT 100;
```

**Key indicators to look for:**
- `Index Only Scan`: Best — data served entirely from index
- `Bitmap Index Scan`: Good — index used, heap fetched for matches only
- `Seq Scan` on large table: Investigate — missing index or poor selectivity
- `Buffers: hit=X miss=Y`: High `miss` values indicate OS page cache pressure

### Common Slow Query Patterns

#### 1. JSONB Containment Without GIN

```sql
-- SLOW (no GIN index hit):
SELECT * FROM fda_510k WHERE openfda_json->'openfda'->>'regulation_number' = '870.3610';

-- FAST (GIN index):
SELECT * FROM fda_510k WHERE openfda_json @> '{"openfda": {"regulation_number": ["870.3610"]}}';
```

#### 2. OR Conditions That Prevent Index Use

```sql
-- SLOW:
SELECT * FROM fda_510k WHERE product_code = 'DQY' OR product_code = 'GEI';

-- FAST:
SELECT * FROM fda_510k WHERE product_code = ANY(ARRAY['DQY', 'GEI']);
```

#### 3. Implicit Type Casts

```sql
-- SLOW (cast prevents index):
SELECT * FROM fda_510k WHERE decision_date::text LIKE '2024%';

-- FAST:
SELECT * FROM fda_510k WHERE decision_date >= '2024-01-01' AND decision_date < '2025-01-01';
```

---

## Bulk Import Best Practices

### Use COPY for Initial Loads

```python
import psycopg2
from psycopg2.extras import execute_values

# Fastest method: execute_values with large page_size
with db.get_connection() as conn:
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO fda_510k (k_number, product_code, device_name,
                                  applicant, decision_date, openfda_json,
                                  cached_at, checksum)
            VALUES %s
            ON CONFLICT (k_number) DO UPDATE SET
                openfda_json = EXCLUDED.openfda_json,
                cached_at = EXCLUDED.cached_at,
                updated_at = NOW()
            """,
            [(r['k_number'], r['product_code'], r['device_name'],
              r['applicant'], r['decision_date'], Json(r),
              datetime.now(), compute_checksum(r))
             for r in records],
            page_size=1000,  # Insert 1000 rows per round-trip
        )
```

### Optimal Batch Sizes

| Dataset Size | Batch Size | Expected Rate |
|-------------|------------|---------------|
| < 1K records | 100–500 | ~600 rec/s (individual) |
| 1K–10K | 1,000 | ~5,000 rec/s |
| 10K–100K | 5,000 | ~15,000 rec/s |
| > 100K | 10,000 | ~25,000–40,000 rec/s |

### Pre-Import Optimization

For very large initial loads (full FDA database):

```sql
-- 1. Drop indexes before import
DROP INDEX idx_510k_openfda_gin;
DROP INDEX idx_510k_product_code;

-- 2. Import with COPY
COPY fda_510k FROM '/tmp/510k_data.csv' WITH (FORMAT CSV, HEADER);

-- 3. Rebuild indexes (CONCURRENTLY = no table lock)
CREATE INDEX CONCURRENTLY idx_510k_openfda_gin ON fda_510k USING GIN (openfda_json);
CREATE INDEX CONCURRENTLY idx_510k_product_code ON fda_510k (product_code);

-- 4. Update table statistics
ANALYZE fda_510k;
```

---

## Blue-Green Deployment Performance

The `UpdateCoordinator` uses blue-green deployment for zero-downtime updates. Performance targets:

| Operation | Target | Notes |
|-----------|--------|-------|
| Prepare GREEN (full replication) | < 5 minutes | Logical replication lag |
| Delta detection (FDA API diff) | < 30 seconds | ~1,000 changed records/day typical |
| Apply deltas to GREEN | < 2 minutes | Batch upserts |
| Integrity verification | < 10 seconds | Row count + checksum sample |
| PgBouncer switch (SIGHUP) | < 10 seconds | RTO target |
| Rollback to BLUE | < 5 seconds | PgBouncer config revert |

### Monitoring Replication Lag

```sql
-- Check replication lag between BLUE and GREEN
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       (sent_lsn - replay_lsn) AS replication_lag_bytes
FROM pg_stat_replication;

-- Alert if lag > 100MB
SELECT CASE
    WHEN pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) > 104857600
    THEN 'LAG EXCEEDS 100MB — SWITCH BLOCKED'
    ELSE 'OK'
END AS status
FROM pg_stat_replication
WHERE application_name = 'green';
```

---

## Storage Management

### VACUUM and AUTOVACUUM

OpenFDA data has frequent upserts (ON CONFLICT DO UPDATE). Dead tuples accumulate without regular VACUUM:

```sql
-- Check table bloat
SELECT relname, n_live_tup, n_dead_tup,
       round(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 1) AS dead_pct,
       last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables
WHERE relname LIKE 'fda_%'
ORDER BY n_dead_tup DESC;

-- Manual VACUUM if dead_pct > 20%
VACUUM ANALYZE fda_510k;
```

### Recommended Autovacuum Settings (per-table)

```sql
ALTER TABLE fda_510k SET (
    autovacuum_vacuum_scale_factor = 0.01,   -- vacuum at 1% dead tuples (default 20%)
    autovacuum_analyze_scale_factor = 0.005, -- analyze at 0.5% changed rows
    autovacuum_vacuum_cost_delay = 2         -- reduce I/O throttling for fast tables
);
```

### TOAST Configuration

OpenFDA JSONB fields are automatically TOASTed (compressed + out-of-line) for records > 2KB. Verify compression is active:

```sql
SELECT relname, reltoastrelid::regclass AS toast_table,
       pg_size_pretty(pg_total_relation_size(reltoastrelid)) AS toast_size
FROM pg_class
WHERE relname LIKE 'fda_%' AND reltoastrelid > 0;
```

Expected: each `fda_*` table has an associated `pg_toast_*` table using ~40–60% of raw JSONB size.

---

## 21 CFR Part 11 Audit Trail Performance

The `upsert_record()` function sets `SET LOCAL app.user_id` for each transaction to enable audit triggers. This adds ~0.1–0.2ms per write operation. At 600 writes/sec (individual insert rate), the audit overhead is negligible (<0.1% of total write time).

For read-heavy workloads, audit triggers do not fire — no read overhead.

---

## Capacity Planning

### Storage Estimates

| Endpoint | Records (typical) | Raw JSON | JSONB TOAST | With Indexes |
|----------|------------------|----------|-------------|--------------|
| 510k | 580,000 | ~900 MB | ~330 MB | ~430 MB |
| classification | 7,000 | ~11 MB | ~4 MB | ~6 MB |
| maude | 20M+ | ~30 GB | ~11 GB | ~14 GB |
| recalls | 50,000 | ~75 MB | ~27 MB | ~35 MB |
| pma | 50,000 | ~75 MB | ~27 MB | ~35 MB |
| udi | 2M | ~3 GB | ~1.1 GB | ~1.4 GB |
| enforcement | 20,000 | ~30 MB | ~11 MB | ~14 MB |
| **Total** | | **~34 GB** | **~12.5 GB** | **~16 GB** |

**Recommended disk allocation:** 50 GB minimum (BLUE), 50 GB (GREEN) = 100 GB total with room for WAL/temp files.

### Connection Scaling

With 167 agents each needing up to 2 concurrent queries:

- Python-side pool: 20 connections (agents queue internally)
- PgBouncer max_client_conn: 500 (accommodates all agents + overhead)
- PostgreSQL max_connections: 50 (5 Python pools × 2 DB instances + admin)

---

## Troubleshooting

### "Too many connections" Error

1. Check PgBouncer is running: `docker ps | grep pgbouncer`
2. Verify `PGBOUNCER_PORT=6432` is set in environment
3. Reduce `pool_size` in `PostgreSQLDatabase.__init__()` to 10
4. Check `PgBouncer admin: SHOW POOLS;` for pool exhaustion

### Slow Queries After Data Import

1. Run `ANALYZE fda_510k;` — statistics may be stale
2. Run `VACUUM fda_510k;` — page bloat from import
3. Check `pg_stat_activity` for blocking locks
4. Verify GIN indexes exist: `\d fda_510k` in psql

### High Memory Usage

1. Lower `work_mem` (default 4MB is usually fine):
   ```sql
   SET work_mem = '8MB';  -- Only for sort-heavy sessions
   ```
2. Check `shared_buffers` (should be 25% of RAM, max 8GB)
3. Monitor TOAST access: large JSONB decompression can spike memory

### Replication Lag During Blue-Green Switch

1. Check write rate: `SELECT * FROM pg_stat_bgwriter;`
2. Increase `wal_sender_timeout` if network is slow
3. Reduce batch size in `apply_updates()` to give replication time to catch up
4. Monitor: `pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)` < 1MB before switch
