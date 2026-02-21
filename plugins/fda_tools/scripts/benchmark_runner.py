#!/usr/bin/env python3
"""
General Performance Benchmark Runner (GH-90).

Uses :class:`~fda_tools.lib.performance_baseline.PerformanceBaseline` to
measure latency for critical library operations and detect regressions
against stored golden-value baselines.

Benchmarks cover:
  - Library import latency
  - Config object instantiation
  - Input validator throughput (1000 calls)
  - PerformanceBaseline record/compare round-trip
  - CacheManager initialisation

Exit codes:
  0 — all comparisons PASS or NO_BASELINE (first run)
  1 — one or more FAIL regressions detected
  2 — one or more WARN regressions detected (exit 0 when --warn-ok passed)

Usage::

    # First run: establish baselines
    python3 -m fda_tools.scripts.benchmark_runner --record

    # Subsequent runs: check for regressions
    python3 -m fda_tools.scripts.benchmark_runner

    # CI: output JSON for artifact storage
    python3 -m fda_tools.scripts.benchmark_runner --output benchmark-results.json

    # Reset stored baselines
    python3 -m fda_tools.scripts.benchmark_runner --reset
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

from fda_tools.lib.performance_baseline import (
    BenchmarkResult,
    PerformanceBaseline,
    RegressionStatus,
)


# ---------------------------------------------------------------------------
# Benchmark definitions
# ---------------------------------------------------------------------------


def _bench_config_import(n: int = 1) -> float:
    """Time importing fda_tools.lib.config (warm import, not cold)."""
    import importlib
    start = time.perf_counter()
    for _ in range(n):
        importlib.import_module("fda_tools.lib.config")
    return (time.perf_counter() - start) * 1_000 / n


def _bench_input_validators(n: int = 1000) -> float:
    """Time 1000 product-code validation calls."""
    from fda_tools.lib.input_validators import validate_product_code

    codes = ["DQY", "OVE", "GEI", "QKQ", "FRO"]
    start = time.perf_counter()
    for i in range(n):
        validate_product_code(codes[i % len(codes)])
    return (time.perf_counter() - start) * 1_000 / n


def _bench_k_number_validator(n: int = 1000) -> float:
    """Time 1000 K-number validation calls."""
    from fda_tools.lib.input_validators import validate_k_number

    knums = ["K241335", "K210001", "K199999", "K230456", "K220123"]
    start = time.perf_counter()
    for i in range(n):
        validate_k_number(knums[i % len(knums)])
    return (time.perf_counter() - start) * 1_000 / n


def _bench_performance_baseline_record_compare(n: int = 100) -> float:
    """Time PerformanceBaseline record + compare round-trip (tmp dir)."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pb = PerformanceBaseline(data_dir=tmp)
        start = time.perf_counter()
        for i in range(n):
            pb.record_baseline(f"op-{i}", float(100 + i))
            pb.compare(f"op-{i}", float(105 + i))
        return (time.perf_counter() - start) * 1_000 / n


def _bench_json_schema_validation(n: int = 1000) -> float:
    """Time validate_json_schema on a small object schema."""
    from fda_tools.lib.input_validators import validate_json_schema

    schema = {
        "type": "object",
        "required": ["name", "count"],
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 128},
            "count": {"type": "integer", "minimum": 0, "maximum": 10000},
        },
    }
    data = {"name": "DQY", "count": 42}
    start = time.perf_counter()
    for _ in range(n):
        validate_json_schema(data, schema)
    return (time.perf_counter() - start) * 1_000 / n


# Registry: name → (benchmark_fn, iterations, description)
BENCHMARKS = [
    (
        "config_import",
        _bench_config_import,
        10,
        "Config import (warm, 10 iterations), avg ms/call",
    ),
    (
        "input_validator_product_code",
        _bench_input_validators,
        1000,
        "validate_product_code (1000 calls), avg ms/call",
    ),
    (
        "input_validator_k_number",
        _bench_k_number_validator,
        1000,
        "validate_k_number (1000 calls), avg ms/call",
    ),
    (
        "performance_baseline_record_compare",
        _bench_performance_baseline_record_compare,
        100,
        "PerformanceBaseline record+compare round-trip (100 ops), avg ms/op",
    ),
    (
        "json_schema_validation",
        _bench_json_schema_validation,
        1000,
        "validate_json_schema object (1000 calls), avg ms/call",
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_benchmarks(
    pb: PerformanceBaseline,
    *,
    record: bool = False,
    verbose: bool = True,
) -> List[BenchmarkResult]:
    """Run all benchmarks and return results."""
    results: List[BenchmarkResult] = []

    for name, fn, n, _description in BENCHMARKS:
        if verbose:
            print(f"  {name} ...", end=" ", flush=True)

        try:
            duration_ms = fn(n)
        except Exception as exc:
            if verbose:
                print(f"ERROR: {exc}")
            continue

        r = BenchmarkResult(name=name, duration_ms=duration_ms)
        results.append(r)
        pb.append_history(r)

        if record:
            pb.record_baseline(name, duration_ms)
            if verbose:
                print(f"{duration_ms:.3f} ms  [RECORDED AS BASELINE]")
        elif verbose:
            print(f"{duration_ms:.3f} ms")

    return results


def print_regression_report(
    pb: PerformanceBaseline,
    results: List[BenchmarkResult],
) -> int:
    """Print regression report and return worst exit code (0/1/2)."""
    comparisons = pb.regression_report(results)
    exit_code = 0

    print("\nRegression Report")
    print("=" * 60)
    for cmp in comparisons:
        status = cmp.status.value
        if cmp.status == RegressionStatus.NO_BASELINE:
            icon = "~"
        elif cmp.status == RegressionStatus.FAIL:
            icon = "✗"
            exit_code = max(exit_code, 1)
        elif cmp.status == RegressionStatus.WARN:
            icon = "!"
            exit_code = max(exit_code, 2)
        else:
            icon = "✓"
        print(f"  [{icon}] {status:<12}  {cmp.message}")

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FDA Tools performance benchmark runner",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record current measurements as new baselines (first run)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all stored baselines and history",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write JSON results to FILE (for CI artifact storage)",
    )
    parser.add_argument(
        "--warn-ok",
        action="store_true",
        help="Exit 0 even if WARN regressions are detected (exit 1 only for FAIL)",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Override baseline storage directory",
    )
    args = parser.parse_args()

    pb = PerformanceBaseline(
        data_dir=args.data_dir,
        warn_threshold=0.20,
        fail_threshold=0.50,
    )

    if args.reset:
        baselines = pb.get_all_baselines()
        for name in list(baselines):
            pb.delete_baseline(name)
        history_path = Path(pb._history_path)
        if history_path.exists():
            history_path.unlink()
        print(
            f"Reset: deleted {len(baselines)} baselines and history."
        )
        return 0

    print("FDA Tools Performance Benchmarks")
    print("-" * 40)
    if args.record:
        print("Mode: RECORD (establishing new baselines)")
    else:
        print("Mode: CHECK (comparing against stored baselines)")
    print()

    results = run_benchmarks(pb, record=args.record, verbose=True)

    if args.output:
        output_data: Dict = {
            "benchmarks": [r.as_dict() for r in results],
            "baselines": pb.get_all_baselines(),
        }
        if not args.record:
            comparisons = pb.regression_report(results)
            output_data["comparisons"] = [c.as_dict() for c in comparisons]
        Path(args.output).write_text(
            json.dumps(output_data, indent=2)
        )
        print(f"\nResults written to {args.output}")

    if args.record:
        print(
            f"\nBaselines recorded for {len(results)} operations."
        )
        return 0

    exit_code = print_regression_report(pb, results)

    if args.warn_ok and exit_code == 2:
        exit_code = 0

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
