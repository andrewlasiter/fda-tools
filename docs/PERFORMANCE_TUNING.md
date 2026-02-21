# Performance Tuning — CrossProcessRateLimiter

*FDA-210 (PERF-001) — Benchmark harness baseline*
*PERF-004 (FDA-211) — POLL_INTERVAL tuning (next step)*

---

## Architecture Overview

`CrossProcessRateLimiter` enforces openFDA's sliding-window rate limits
**across OS processes** (not just threads) using two primitives:

| Primitive | Purpose |
|-----------|---------|
| `fcntl.flock(LOCK_EX \| LOCK_NB)` | Mutual exclusion for state-file reads/writes |
| JSON state file (`~/.fda-510k-data/.rate_limit_state.json`) | Shared request-timestamp log across processes |

### Acquisition flow

```
acquire()
  ├─ open lock file
  ├─ flock(LOCK_NB)
  │    ├─ success → read state, check count < limit
  │    │    ├─ under limit → append timestamp, write state, release lock → DONE
  │    │    └─ at limit    → release lock, sleep POLL_INTERVAL → retry
  │    └─ BlockingIOError  → sleep jitter, retry
  └─ timeout → return False
```

### Thundering-herd mitigation

When `flock(LOCK_NB)` fails, the process sleeps a random **jitter**:

```python
jitter = POLL_INTERVAL * (0.5 + 0.5 * random.random())
# Range: [POLL_INTERVAL * 0.5, POLL_INTERVAL * 1.0]
# Default: [0.125s, 0.25s]
```

This desynchronises concurrent waiters so they don't all retry at the
same instant.

---

## Key Constants

| Constant | Default | Location | Effect |
|----------|---------|----------|--------|
| `POLL_INTERVAL` | `0.25s` | `cross_process_rate_limiter.py:65` | Base retry interval; controls jitter range and wait-at-limit sleep |
| `WINDOW_SIZE_SECONDS` | `60s` | `:59` | Sliding window width (matches openFDA window) |
| `MAX_WAIT_SECONDS` | `120s` | `:62` | Hard timeout for `acquire()` |
| `RATE_LIMIT_WITH_KEY` | `240/min` | `:55` | openFDA limit with API key |
| `RATE_LIMIT_WITHOUT_KEY` | `40/min` | `:56` | openFDA limit without API key |

---

## Benchmark Scenarios (FDA-210)

Run the full suite:

```bash
# With pytest (preferred — integrates with CI)
pytest plugins/fda_tools/tests/bench_cross_process_rate_limiter.py -v -m "benchmark and slow"

# Standalone
python3 plugins/fda_tools/tests/bench_cross_process_rate_limiter.py
```

### Scenario 1 — Throughput under concurrent load

| Parameter | Value |
|-----------|-------|
| Processes | 3 |
| Rate limit | 120 req/min |
| Duration | 5 seconds |
| Assertion | `total_acquired ≤ int(120 * elapsed / 60) + 2` |

**What it tests:** The file-based coordination actually prevents aggregate
throughput from exceeding the configured limit when multiple processes
run simultaneously.

**Expected result:** ≤ 12 total acquisitions in 5 seconds (10 at steady
state + 2 boundary buffer).

---

### Scenario 2 — Thundering herd jitter validation

| Parameter | Value |
|-----------|-------|
| Workers | 8 |
| Rate limit | 10 000/min (no rate blocking) |
| Contention source | File lock serialises LOCK_NB attempts |
| Assertion | `time_spread > POLL_INTERVAL × 0.4 = 0.1s` |

**What it tests:** When 8 processes simultaneously try to acquire the
file lock, the jitter formula distributes their retries over time rather
than synchronising them.

**Expected result:** Spread between first and last successful acquisition
> 0.1 s. Near-zero spread indicates broken jitter.

> **Note on fork(2) and RNG state:** After `fork`, all child processes
> inherit the parent's `random` state. Each worker calls `random.seed()`
> (no argument = `os.urandom()`) to diverge their sequences. In
> production, each process is spawned independently and has a unique
> RNG state automatically.

---

### Scenario 3 — Latency distribution (uncontended)

| Parameter | Value |
|-----------|-------|
| Samples | 200 sequential acquires |
| Rate limit | 10 000/min (no blocking) |
| Assertion | `p99 < 100ms` |

**What it tests:** Raw overhead of the acquire path — file open, flock,
JSON read/write, timestamp append, atomic rename. No rate blocking
occurs; this is pure I/O cost.

**Baseline results (WSL2, tmpfs temp dir):**

| Metric | Observed |
|--------|----------|
| p50 | ~0.5 ms |
| p95 | ~1.0–2.0 ms |
| p99 | ~1.5–8.0 ms |
| max | ~1.5–10 ms |

> Values vary across runs due to OS scheduling jitter. The wide p99/max range
> is normal on WSL2 where the host OS can preempt the process during the
> file-lock acquisition.  Re-run on target hardware to establish a stable baseline.

---

### Scenario 4 — Starvation / Fairness

| Parameter | Value |
|-----------|-------|
| Aggressive processes | 2 (no delay between acquires) |
| Patient process | 1 (0.5 s sleep between acquires) |
| Rate limit | 120 req/min |
| Duration | 8 seconds |
| Assertion | `patient_count ≥ 1` |

**What it tests:** The sliding-window mechanism does not permanently
starve a slow consumer. Since rate slots expire after 60 seconds,
newly available capacity is shared fairly among all waiters.

---

## Tuning Guide (PERF-004 / FDA-211 — Completed)

### Empirical Comparison (FDA-211, 2026-02-21)

All 4 candidates were benchmarked on WSL2/tmpfs (6 workers for S2, 100 samples for S3):

| POLL_INTERVAL | Jitter range | S3 p50 | S3 p99 | S2 spread | S2 pass | **Verdict** |
|---------------|-------------|--------|--------|-----------|---------|-------------|
| `0.05s` | 0.025–0.05s | 0.40ms | 2.10ms | 0.094s | ❌ FAIL | Too small — jitter bunches retries |
| `0.10s` | 0.05–0.10s | 0.52ms | 2.25ms | 0.079s | ❌ FAIL | Too small — jitter bunches retries |
| **`0.25s`** ✓ | **0.125–0.25s** | **0.32ms** | **1.90ms** | **0.248s** | **✓ PASS** | **Optimal — passes all scenarios** |
| `0.50s` | 0.25–0.50s | 0.39ms | 1.39ms | 0.507s | ✓ PASS | Passes, but slower rate-limit recovery |

**Decision:** Keep `POLL_INTERVAL = 0.25s`.

- Values below 0.25s **fail** the thundering-herd test because the jitter range
  `[POLL_INTERVAL×0.5, POLL_INTERVAL×1.0]` is too narrow — processes cluster.
- `0.25s` provides adequate spread (≥ 0.1s) with the best p50 of all passing candidates.
- `0.50s` passes but adds 250ms latency when a rate-limit slot opens (unacceptable
  at 240 req/min = 4 req/sec).

### When to revisit POLL_INTERVAL

Re-benchmark if:
- Production process count increases beyond 8 concurrent workers.
- Filesystem changes (NFS, DrvFs) slow lock acquisition significantly.
- Rate limit changes substantially (e.g., openFDA revises limits).

### How to apply a change

1. Edit `POLL_INTERVAL` in `plugins/fda_tools/lib/cross_process_rate_limiter.py:65`.
2. Re-run all 4 benchmark scenarios.
3. Verify S2 spread > `POLL_INTERVAL × 0.4` (the S2 threshold scales with the value).
4. Document results in this file under "Benchmark History" below.

---

## Benchmark History

| Date | Branch | POLL_INTERVAL | S1 total | S2 spread | S3 p99 | S4 patient |
|------|--------|---------------|----------|-----------|--------|------------|
| 2026-02-20 | `master` (FDA-210) | 0.25s | 120/121 ✓ | 0.24–0.40s ✓ | 1.3–7.8ms ✓ | ≥2/16 ✓ |
| 2026-02-21 | `master` (FDA-211) | 0.05s | — | 0.094s ❌ | — | — |
| 2026-02-21 | `master` (FDA-211) | 0.10s | — | 0.079s ❌ | — | — |
| 2026-02-21 | `master` (FDA-211) | **0.25s ✓** | — | **0.248s ✓** | **1.90ms ✓** | — |
| 2026-02-21 | `master` (FDA-211) | 0.50s | — | 0.507s ✓ | 1.39ms ✓ | — |

> S1 = total slots acquired vs window capacity (120/min).
> S2 = time spread of 8 concurrent processes' first acquisitions.
> S3 = p99 acquire latency (uncontended, tmpfs).
> S4 = patient process slots vs natural rate (rate_limit=10_000, 0.5s delay).

> Track this table across PERF-004 tuning iterations (FDA-211).
> Re-run on target hardware (production filesystem) to establish stable baseline.

---

## Related Issues

| Issue | Title | Status |
|-------|-------|--------|
| FDA-200 | Consolidate rate limiters | Done |
| FDA-209 | Remove `_FallbackRateLimiter` dead code | Done |
| FDA-210 | Benchmark CrossProcessRateLimiter (PERF-001) | Done |
| **FDA-211** | **Tune POLL_INTERVAL (PERF-004)** | **In Progress** |
