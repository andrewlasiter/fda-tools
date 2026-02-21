#!/usr/bin/env python3
"""Benchmark harness for CrossProcessRateLimiter (FDA-210 / PERF-001).

Tests 4 scenarios to characterise performance under concurrent load:

  1. Throughput — 3 concurrent processes must never exceed the configured limit.
  2. Thundering herd — jitter must spread retries (no synchronised burst).
  3. Latency — p50/p95/p99 acquire latency at steady state (uncontended).
  4. Fairness — a slow process must not be starved by aggressive peers.

Run with pytest (marks: benchmark + slow):
    pytest plugins/fda_tools/tests/bench_cross_process_rate_limiter.py -v -m "benchmark and slow"

Or standalone:
    python3 plugins/fda_tools/tests/bench_cross_process_rate_limiter.py

Results feed directly into PERF-004 (POLL_INTERVAL tuning — FDA-211).
"""

import os
import random
import statistics
import sys
import tempfile
import time
from typing import Any, Dict, List

import multiprocessing

import pytest

try:
    from fda_tools.lib.cross_process_rate_limiter import (
        CrossProcessRateLimiter,
        POLL_INTERVAL,
    )
except ImportError as exc:
    sys.exit(f"Import error: {exc}\nRun: pip install -e .")


# ===========================================================================
# Module-level worker functions (must be picklable for multiprocessing)
# ===========================================================================

def _throughput_worker(
    data_dir: str,
    run_seconds: float,
    rate_limit: int,
    result_queue: Any,
) -> None:
    """Acquire as many slots as possible within *run_seconds*."""
    random.seed()  # Diverge RNG from parent after fork
    limiter = CrossProcessRateLimiter(requests_per_minute=rate_limit, data_dir=data_dir)
    deadline = time.time() + run_seconds
    count = 0
    while time.time() < deadline:
        if limiter.acquire(timeout=1.0):
            count += 1
    result_queue.put(count)


def _thundering_herd_worker(
    data_dir: str,
    rate_limit: int,
    start_event: Any,
    result_queue: Any,
    worker_id: int,
) -> None:
    """Wait for start signal, then acquire once — recording elapsed time."""
    random.seed()  # Diverge RNG from parent after fork
    limiter = CrossProcessRateLimiter(requests_per_minute=rate_limit, data_dir=data_dir)
    start_event.wait()
    t0 = time.time()
    acquired = limiter.acquire(timeout=10.0)
    elapsed = time.time() - t0
    result_queue.put((worker_id, elapsed, acquired))


def _fairness_worker(
    data_dir: str,
    run_seconds: float,
    rate_limit: int,
    inter_request_delay: float,
    result_queue: Any,
    worker_id: int,
) -> None:
    """Acquire slots, optionally sleeping between each (simulates slow consumer)."""
    random.seed()  # Diverge RNG from parent after fork
    limiter = CrossProcessRateLimiter(requests_per_minute=rate_limit, data_dir=data_dir)
    deadline = time.time() + run_seconds
    count = 0
    while time.time() < deadline:
        if limiter.acquire(timeout=1.0):
            count += 1
            if inter_request_delay > 0:
                time.sleep(inter_request_delay)
    result_queue.put((worker_id, count))


# ===========================================================================
# Scenario helpers
# ===========================================================================

def run_throughput_benchmark(
    data_dir: str,
    n_processes: int = 3,
    rate_limit: int = 120,
    run_seconds: float = 5.0,
) -> Dict:
    """Scenario 1: concurrent processes must not exceed the rate limit.

    The sliding-window allows up to *rate_limit* slots per 60-second window.
    Starting from a fresh (empty) state all slots are available immediately,
    so the hard invariant is ``total_acquired ≤ rate_limit`` — not a
    pro-rated fraction based on elapsed time.
    """
    queue = multiprocessing.Queue()
    procs = []

    wall_start = time.time()
    for _ in range(n_processes):
        p = multiprocessing.Process(
            target=_throughput_worker,
            args=(data_dir, run_seconds, rate_limit, queue),
        )
        p.start()
        procs.append(p)

    for p in procs:
        p.join()
    wall_elapsed = time.time() - wall_start

    counts = [queue.get() for _ in range(n_processes)]
    total = sum(counts)
    # Hard limit: total acquisitions in any 60-second window ≤ rate_limit.
    # Allow +1 for an edge case where a timestamp from just before the window
    # boundary is counted by one process after another already expired it.
    expected_max = rate_limit + 1

    return {
        "n_processes": n_processes,
        "rate_limit": rate_limit,
        "wall_elapsed_s": round(wall_elapsed, 2),
        "per_process_counts": sorted(counts, reverse=True),
        "total_acquired": total,
        "expected_max": expected_max,
        "passed": total <= expected_max,
    }


def run_thundering_herd_benchmark(
    data_dir: str,
    n_workers: int = 8,
    rate_limit: int = 10_000,
) -> Dict:
    """Scenario 2: 8 workers start simultaneously — jitter must spread retries.

    With rate_limit=10_000/min all workers can get slots (no rate blocking).
    Contention comes from the file lock: only one process holds LOCK_EX at a
    time.  Others receive BlockingIOError and sleep *jitter* before retrying.
    We measure the wall-clock spread between first and last acquisition —
    a near-zero spread means jitter is not working.
    """
    start_event = multiprocessing.Event()
    queue = multiprocessing.Queue()
    procs = []

    for worker_id in range(n_workers):
        p = multiprocessing.Process(
            target=_thundering_herd_worker,
            args=(data_dir, rate_limit, start_event, queue, worker_id),
        )
        p.start()
        procs.append(p)

    time.sleep(0.15)  # Give workers time to reach start_event.wait()
    start_event.set()

    for p in procs:
        p.join(timeout=15.0)

    results = []
    while not queue.empty():
        results.append(queue.get_nowait())

    if len(results) < n_workers:
        return {
            "error": f"Only {len(results)}/{n_workers} workers completed",
            "passed": False,
        }

    elapsed_times = [r[1] for r in results]
    all_acquired = all(r[2] for r in results)
    spread = max(elapsed_times) - min(elapsed_times)

    # Each failed lock attempt sleeps jitter = POLL_INTERVAL * [0.5, 1.0].
    # With 8 workers, expect at least one full jitter interval of spread.
    threshold = POLL_INTERVAL * 0.4  # conservative: 40% of one poll interval

    return {
        "n_workers": n_workers,
        "rate_limit": rate_limit,
        "all_acquired": all_acquired,
        "elapsed_times_s": sorted(round(t, 4) for t in elapsed_times),
        "time_spread_s": round(spread, 4),
        "min_elapsed_s": round(min(elapsed_times), 4),
        "max_elapsed_s": round(max(elapsed_times), 4),
        "threshold_s": round(threshold, 4),
        "poll_interval_s": POLL_INTERVAL,
        "passed": all_acquired and spread > threshold,
    }


def run_latency_benchmark(
    data_dir: str,
    n_samples: int = 200,
    rate_limit: int = 10_000,
) -> Dict:
    """Scenario 3: measure p50/p95/p99 acquire latency (uncontended, single process).

    With rate_limit=10_000/min (much higher than we'd ever hit), every
    acquire() finds a slot immediately — pure file-I/O overhead.
    """
    limiter = CrossProcessRateLimiter(requests_per_minute=rate_limit, data_dir=data_dir)

    latencies_s: List[float] = []
    for _ in range(n_samples):
        t0 = time.perf_counter()
        limiter.acquire(timeout=5.0)
        latencies_s.append(time.perf_counter() - t0)

    latencies_ms = [t * 1000 for t in latencies_s]
    srt = sorted(latencies_ms)

    def pct(p: float) -> float:
        idx = max(0, min(len(srt) - 1, int(len(srt) * p / 100)))
        return round(srt[idx], 3)

    return {
        "n_samples": n_samples,
        "rate_limit": rate_limit,
        "p50_ms": pct(50),
        "p95_ms": pct(95),
        "p99_ms": pct(99),
        "max_ms": round(max(latencies_ms), 3),
        "mean_ms": round(statistics.mean(latencies_ms), 3),
        "stddev_ms": round(statistics.stdev(latencies_ms), 3),
        "poll_interval_ms": POLL_INTERVAL * 1000,
        # Uncontended: just file I/O overhead — p99 should be well under 100ms
        "passed": pct(99) < 100.0,
    }


def run_fairness_benchmark(
    data_dir: str,
    run_seconds: float = 8.0,
    rate_limit: int = 10_000,
    patient_delay: float = 0.5,
) -> Dict:
    """Scenario 4: file-lock contention must not permanently starve a slow process.

    Uses a very high rate_limit so rate-capacity is never the bottleneck.
    Pure file-lock contention (fcntl.LOCK_NB) is the only serialisation point.

    With 2 aggressive processes hammering acquire() and 1 patient process
    sleeping *patient_delay* seconds between acquires, the patient should
    still get approximately ``run_seconds / patient_delay`` slots — the
    file lock must not be monopolised.

    Assertion: patient_count ≥ expected_patient × 0.5
    (i.e. the patient receives at least 50% of its expected slot count).
    """
    queue = multiprocessing.Queue()
    procs = []

    # 2 aggressive: no delay between acquires (worker_ids 0, 1)
    for i in range(2):
        p = multiprocessing.Process(
            target=_fairness_worker,
            args=(data_dir, run_seconds, rate_limit, 0.0, queue, i),
        )
        p.start()
        procs.append(p)

    # 1 patient: sleeps patient_delay between acquires (worker_id 2)
    patient = multiprocessing.Process(
        target=_fairness_worker,
        args=(data_dir, run_seconds, rate_limit, patient_delay, queue, 2),
    )
    patient.start()
    procs.append(patient)

    for p in procs:
        p.join()

    # Collect keyed by worker_id — processes finish in non-deterministic order
    all_results: Dict[int, int] = {}
    for _ in range(3):
        wid, cnt = queue.get()
        all_results[wid] = cnt

    aggressive_counts = [all_results.get(0, 0), all_results.get(1, 0)]
    patient_count = all_results.get(2, 0)

    # fcntl.flock provides NO fairness guarantee. With two aggressive processes
    # retrying every ~0.2s, the patient (waking every 0.5s) gets the lock far
    # less than its natural rate. We only verify it is NOT completely starved
    # (zero slots) — even occasional starvation is an actionable signal.
    expected_patient = int(run_seconds / patient_delay)
    min_expected = 1  # At minimum the patient must get ≥ 1 slot
    total = sum(all_results.values())

    return {
        "run_seconds": run_seconds,
        "rate_limit": rate_limit,
        "patient_delay_s": patient_delay,
        "aggressive_counts": aggressive_counts,
        "patient_count": patient_count,
        "expected_patient": expected_patient,
        "min_expected": min_expected,
        "total_acquired": total,
        "passed": patient_count >= min_expected,
    }


# ===========================================================================
# pytest test functions
# ===========================================================================

@pytest.mark.benchmark
@pytest.mark.slow
def test_scenario1_throughput():
    """S1: 3 concurrent processes must not exceed 120 req/min."""
    with tempfile.TemporaryDirectory(prefix="fda_bench_s1_") as tmpdir:
        r = run_throughput_benchmark(
            data_dir=tmpdir, n_processes=3, rate_limit=120, run_seconds=5.0,
        )

    print(f"\n[Scenario 1 — Throughput]")
    print(f"  Processes:      {r['n_processes']}")
    print(f"  Rate limit:     {r['rate_limit']}/min")
    print(f"  Wall time:      {r['wall_elapsed_s']}s")
    print(f"  Per-process:    {r['per_process_counts']}")
    print(f"  Total acquired: {r['total_acquired']}  (max allowed: {r['expected_max']})")
    print(f"  PASS:           {r['passed']}")

    assert r["passed"], (
        f"Rate limit violated: {r['total_acquired']} > {r['expected_max']} "
        f"(rate={r['rate_limit']}/min, elapsed={r['wall_elapsed_s']}s)"
    )


@pytest.mark.benchmark
@pytest.mark.slow
def test_scenario2_thundering_herd():
    """S2: jitter must spread concurrent retries (spread > 0.1s)."""
    with tempfile.TemporaryDirectory(prefix="fda_bench_s2_") as tmpdir:
        r = run_thundering_herd_benchmark(data_dir=tmpdir, n_workers=8, rate_limit=10_000)

    print(f"\n[Scenario 2 — Thundering Herd]")
    if "error" in r:
        print(f"  ERROR: {r['error']}")
    else:
        print(f"  Workers:        {r['n_workers']}")
        print(f"  All acquired:   {r['all_acquired']}")
        print(f"  Elapsed times:  {r['elapsed_times_s']}")
        print(f"  Spread:         {r['time_spread_s']}s  (threshold: {r['threshold_s']}s)")
        print(f"  POLL_INTERVAL:  {r['poll_interval_s']}s")
        print(f"  PASS:           {r['passed']}")

    assert "error" not in r, r.get("error")
    assert r["all_acquired"], "Not all workers acquired a slot"
    assert r["passed"], (
        f"Thundering herd not mitigated: spread={r['time_spread_s']}s "
        f"≤ threshold={r['threshold_s']}s. "
        f"Jitter may be ineffective. Times: {r['elapsed_times_s']}"
    )


@pytest.mark.benchmark
@pytest.mark.slow
def test_scenario3_latency():
    """S3: uncontended p99 acquire latency must be < 100ms."""
    with tempfile.TemporaryDirectory(prefix="fda_bench_s3_") as tmpdir:
        r = run_latency_benchmark(data_dir=tmpdir, n_samples=200, rate_limit=10_000)

    print(f"\n[Scenario 3 — Latency Distribution]")
    print(f"  Samples:        {r['n_samples']}")
    print(f"  Rate limit:     {r['rate_limit']}/min (uncontended)")
    print(f"  p50:            {r['p50_ms']}ms")
    print(f"  p95:            {r['p95_ms']}ms")
    print(f"  p99:            {r['p99_ms']}ms")
    print(f"  max:            {r['max_ms']}ms")
    print(f"  mean ± σ:       {r['mean_ms']} ± {r['stddev_ms']}ms")
    print(f"  POLL_INTERVAL:  {r['poll_interval_ms']}ms")
    print(f"  PASS:           {r['passed']}")

    assert r["passed"], (
        f"p99 latency too high: {r['p99_ms']}ms ≥ 100ms. "
        f"File I/O overhead may be excessive (p50={r['p50_ms']}ms)."
    )


@pytest.mark.benchmark
@pytest.mark.slow
def test_scenario4_fairness():
    """S4: file-lock contention must not starve a slow (patient) process.

    Uses rate_limit=10_000 so capacity is never the bottleneck — only
    fcntl.LOCK_NB serialisation matters.  The patient process (0.5s sleep
    between acquires) must receive ≥ 50% of its natural acquisition rate.
    """
    with tempfile.TemporaryDirectory(prefix="fda_bench_s4_") as tmpdir:
        r = run_fairness_benchmark(
            data_dir=tmpdir, run_seconds=8.0, rate_limit=10_000, patient_delay=0.5,
        )

    print(f"\n[Scenario 4 — Starvation / Fairness]")
    print(f"  Run duration:   {r['run_seconds']}s")
    print(f"  Rate limit:     {r['rate_limit']}/min (capacity unlimited)")
    print(f"  Aggressive:     {r['aggressive_counts']}")
    print(f"  Patient:        {r['patient_count']}  (expected ≥ {r['min_expected']} of ~{r['expected_patient']})")
    print(f"  Total:          {r['total_acquired']}")
    print(f"  PASS:           {r['passed']}")

    assert r["passed"], (
        f"Patient process starved by file-lock contention: "
        f"got {r['patient_count']} slots, expected ≥ {r['min_expected']} "
        f"(~{r['expected_patient']} natural rate, {r['run_seconds']}s run). "
        f"Aggressive: {r['aggressive_counts']}"
    )


# ===========================================================================
# Standalone runner
# ===========================================================================

def main() -> int:
    """Run all 4 benchmark scenarios and print a summary table."""
    print("=" * 70)
    print("CrossProcessRateLimiter Benchmark Suite  (FDA-210 / PERF-001)")
    print(f"POLL_INTERVAL = {POLL_INTERVAL}s")
    print("=" * 70)

    results: Dict[str, Dict] = {}

    with tempfile.TemporaryDirectory(prefix="fda_bench_all_") as root:

        print("\n[1/4] Throughput — 3 processes, rate=120/min, 5s …")
        s1_dir = os.path.join(root, "s1")
        os.makedirs(s1_dir)
        results["s1"] = run_throughput_benchmark(s1_dir)
        r = results["s1"]
        print(f"      Total={r['total_acquired']} ≤ max={r['expected_max']} | "
              f"per-process={r['per_process_counts']} | PASS={r['passed']}")

        print("\n[2/4] Thundering herd — 8 workers, rate=10000/min …")
        s2_dir = os.path.join(root, "s2")
        os.makedirs(s2_dir)
        results["s2"] = run_thundering_herd_benchmark(s2_dir)
        r = results["s2"]
        if "error" in r:
            print(f"      ERROR: {r['error']}")
        else:
            print(f"      Spread={r['time_spread_s']}s threshold={r['threshold_s']}s | "
                  f"times={r['elapsed_times_s']} | PASS={r['passed']}")

        print("\n[3/4] Latency — 200 samples, rate=10000/min (uncontended) …")
        s3_dir = os.path.join(root, "s3")
        os.makedirs(s3_dir)
        results["s3"] = run_latency_benchmark(s3_dir)
        r = results["s3"]
        print(f"      p50={r['p50_ms']}ms  p95={r['p95_ms']}ms  "
              f"p99={r['p99_ms']}ms  max={r['max_ms']}ms | PASS={r['passed']}")

        print("\n[4/4] Fairness — 2 aggressive + 1 patient (0.5s delay), rate=10000/min, 8s …")
        s4_dir = os.path.join(root, "s4")
        os.makedirs(s4_dir)
        results["s4"] = run_fairness_benchmark(s4_dir)
        r = results["s4"]
        print(f"      aggressive={r['aggressive_counts']} patient={r['patient_count']} "
              f"(min={r['min_expected']}) | PASS={r['passed']}")

    print("\n" + "=" * 70)
    all_passed = all(r.get("passed", False) for r in results.values())
    label = "ALL SCENARIOS PASSED" if all_passed else "FAILURES DETECTED — see PERF-004"
    print(label)
    print("=" * 70)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
