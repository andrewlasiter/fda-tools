#!/usr/bin/env python3
"""
General-Purpose Performance Baseline Tracker (FDA-134).

Records execution-time baselines for named operations and detects
performance regressions by comparing new measurements to saved baselines.

Distinct from ``scripts/performance_benchmark.py`` (FDA-197), which runs
PostgreSQL-specific micro-benchmarks.  This module is a general-purpose
regression guard for any named operation:

* CLI commands (batchfetch, search, extract, …)
* Library functions (cache lookups, PDF parsing, API calls)
* Any code path where latency matters

Workflow::

    from fda_tools.lib.performance_baseline import PerformanceBaseline

    pb = PerformanceBaseline()

    # --- First run: establish baselines ---
    with pb.measure("batchfetch") as r:
        run_batchfetch()

    pb.record_baseline(r.name, r.duration_ms)   # save as the golden value

    # --- Subsequent runs: detect regressions ---
    with pb.measure("batchfetch") as r:
        run_batchfetch()

    comparison = pb.compare(r.name, r.duration_ms)
    if comparison.status == RegressionStatus.FAIL:
        print(f"REGRESSION: {comparison.regression_pct:.0%} slower than baseline")

Baselines are stored in ``~/fda-510k-data/.performance/baselines.json``.
Each measurement is also appended to a history JSONL file so trends can
be analysed over time.

Regression thresholds (configurable):

* PASS    — current ≤ baseline × (1 + warn_threshold)   default: ≤ 120%
* WARN    — baseline × warn ≤ current ≤ baseline × fail  default: 120-150%
* FAIL    — current > baseline × (1 + fail_threshold)   default: > 150%
"""

from __future__ import annotations

import contextlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Generator, List, Optional
import os

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DATA_DIR = os.path.expanduser("~/fda-510k-data/.performance")
BASELINES_FILE = "baselines.json"
HISTORY_FILE = "history.jsonl"

# Default regression thresholds (fraction above baseline)
DEFAULT_WARN_THRESHOLD = 0.20   # 20% slower → WARN
DEFAULT_FAIL_THRESHOLD = 0.50   # 50% slower → FAIL


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class RegressionStatus(str, Enum):
    """Result of a baseline comparison."""

    PASS = "PASS"    # within acceptable range
    WARN = "WARN"    # noticeably slower, but not critical
    FAIL = "FAIL"    # significant regression
    NO_BASELINE = "NO_BASELINE"  # no saved baseline to compare against


@dataclass
class BenchmarkResult:
    """A single timing measurement.

    Attributes:
        name: Identifier for the operation (e.g. ``"batchfetch"``).
        duration_ms: Wall-clock time in milliseconds.
        timestamp: ISO-8601 UTC timestamp.
    """

    name: str
    duration_ms: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def as_dict(self) -> Dict:
        return {
            "name": self.name,
            "duration_ms": round(self.duration_ms, 3),
            "timestamp": self.timestamp,
        }


@dataclass
class BaselineComparison:
    """Comparison of a measurement against a saved baseline.

    Attributes:
        name: Operation identifier.
        current_ms: Duration of the new measurement.
        baseline_ms: Saved golden-value duration.
        regression_pct: How much slower the new measurement is
            (0.0 = same as baseline; 0.5 = 50% slower; negative = faster).
        status: PASS / WARN / FAIL / NO_BASELINE.
        message: Human-readable summary.
    """

    name: str
    current_ms: float
    baseline_ms: float
    regression_pct: float
    status: RegressionStatus
    message: str

    def is_regression(self) -> bool:
        """Return True if status is WARN or FAIL."""
        return self.status in (RegressionStatus.WARN, RegressionStatus.FAIL)

    def as_dict(self) -> Dict:
        return {
            "name": self.name,
            "current_ms": round(self.current_ms, 3),
            "baseline_ms": round(self.baseline_ms, 3),
            "regression_pct": round(self.regression_pct * 100, 1),
            "status": self.status.value,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# PerformanceBaseline
# ---------------------------------------------------------------------------


class PerformanceBaseline:
    """Baseline recorder and regression detector.

    Args:
        data_dir: Directory for baselines and history files.
        warn_threshold: Fraction above baseline that triggers WARN (default: 0.20).
        fail_threshold: Fraction above baseline that triggers FAIL (default: 0.50).
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        warn_threshold: float = DEFAULT_WARN_THRESHOLD,
        fail_threshold: float = DEFAULT_FAIL_THRESHOLD,
    ) -> None:
        self._dir = Path(data_dir or DEFAULT_DATA_DIR)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._baselines_path = self._dir / BASELINES_FILE
        self._history_path = self._dir / HISTORY_FILE
        self.warn_threshold = warn_threshold
        self.fail_threshold = fail_threshold

    # ------------------------------------------------------------------
    # Measuring
    # ------------------------------------------------------------------

    @contextlib.contextmanager
    def measure(self, name: str) -> Generator[BenchmarkResult, None, None]:
        """Context manager that times the enclosed block.

        The :class:`BenchmarkResult` is populated **after** the block exits.
        Append the measurement to history by calling :meth:`append_history`
        or save it as the new baseline with :meth:`record_baseline`.

        Example::

            with pb.measure("my_operation") as r:
                do_work()
            # r.duration_ms is now populated
            pb.append_history(r)

        Yields:
            BenchmarkResult with name and a placeholder duration (0.0).
            After the block exits, ``duration_ms`` and ``timestamp`` are set.
        """
        result = BenchmarkResult(name=name, duration_ms=0.0)
        start = time.perf_counter()
        try:
            yield result
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1_000
            result.duration_ms = elapsed_ms
            result.timestamp = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Baselines
    # ------------------------------------------------------------------

    def record_baseline(self, name: str, duration_ms: float) -> None:
        """Save *duration_ms* as the golden-value baseline for *name*.

        Overwrites any previously saved baseline for this name.
        """
        baselines = self._load_baselines()
        baselines[name] = round(duration_ms, 3)
        self._save_baselines(baselines)

    def get_baseline(self, name: str) -> Optional[float]:
        """Return the saved baseline for *name*, or None if absent."""
        return self._load_baselines().get(name)

    def get_all_baselines(self) -> Dict[str, float]:
        """Return all saved baselines as a name → ms dict."""
        return dict(self._load_baselines())

    def delete_baseline(self, name: str) -> bool:
        """Delete the saved baseline for *name*. Return True if found."""
        baselines = self._load_baselines()
        if name in baselines:
            del baselines[name]
            self._save_baselines(baselines)
            return True
        return False

    # ------------------------------------------------------------------
    # Regression detection
    # ------------------------------------------------------------------

    def compare(self, name: str, duration_ms: float) -> BaselineComparison:
        """Compare *duration_ms* against the saved baseline for *name*.

        Returns:
            :class:`BaselineComparison` with status and message.
        """
        baseline = self.get_baseline(name)
        if baseline is None:
            return BaselineComparison(
                name=name,
                current_ms=duration_ms,
                baseline_ms=0.0,
                regression_pct=0.0,
                status=RegressionStatus.NO_BASELINE,
                message=f"No baseline recorded for '{name}'.",
            )

        if baseline <= 0:
            regression_pct = 0.0
        else:
            regression_pct = (duration_ms - baseline) / baseline

        if regression_pct > self.fail_threshold:
            status = RegressionStatus.FAIL
            msg = (
                f"FAIL: '{name}' is {regression_pct * 100:.0f}% slower than baseline "
                f"({duration_ms:.0f} ms vs {baseline:.0f} ms baseline)."
            )
        elif regression_pct > self.warn_threshold:
            status = RegressionStatus.WARN
            msg = (
                f"WARN: '{name}' is {regression_pct * 100:.0f}% slower than baseline "
                f"({duration_ms:.0f} ms vs {baseline:.0f} ms baseline)."
            )
        else:
            status = RegressionStatus.PASS
            pct_str = (
                f"{abs(regression_pct) * 100:.0f}% faster"
                if regression_pct < 0
                else f"{regression_pct * 100:.0f}% slower"
            )
            msg = (
                f"PASS: '{name}' within threshold ({pct_str} than baseline "
                f"{baseline:.0f} ms)."
            )

        return BaselineComparison(
            name=name,
            current_ms=duration_ms,
            baseline_ms=baseline,
            regression_pct=regression_pct,
            status=status,
            message=msg,
        )

    def regression_report(
        self, results: List[BenchmarkResult]
    ) -> List[BaselineComparison]:
        """Compare a list of measurements against their baselines.

        Args:
            results: Measurements to check.

        Returns:
            Comparisons sorted by severity (FAIL first, then WARN, then PASS).
        """
        comparisons = [self.compare(r.name, r.duration_ms) for r in results]
        order = {
            RegressionStatus.FAIL: 0,
            RegressionStatus.WARN: 1,
            RegressionStatus.NO_BASELINE: 2,
            RegressionStatus.PASS: 3,
        }
        return sorted(comparisons, key=lambda c: order[c.status])

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def append_history(self, result: BenchmarkResult) -> None:
        """Append *result* to the measurement history JSONL file."""
        with open(self._history_path, "a") as f:
            f.write(json.dumps(result.as_dict()) + "\n")

    def load_history(self, name: Optional[str] = None) -> List[BenchmarkResult]:
        """Load measurement history, optionally filtered to *name*.

        Returns:
            List of :class:`BenchmarkResult` in recorded order.
        """
        if not self._history_path.exists():
            return []
        results: List[BenchmarkResult] = []
        try:
            with open(self._history_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        if name is None or d.get("name") == name:
                            results.append(
                                BenchmarkResult(
                                    name=d["name"],
                                    duration_ms=d["duration_ms"],
                                    timestamp=d.get("timestamp", ""),
                                )
                            )
                    except (json.JSONDecodeError, KeyError):
                        continue
        except OSError:
            pass
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_baselines(self) -> Dict[str, float]:
        if not self._baselines_path.exists():
            return {}
        try:
            with open(self._baselines_path, "r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_baselines(self, baselines: Dict[str, float]) -> None:
        tmp = self._baselines_path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump(baselines, f, indent=2)
            tmp.replace(self._baselines_path)
        except OSError:
            tmp.unlink(missing_ok=True)
