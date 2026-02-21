"""
Performance Baseline Tests (FDA-134).
=======================================

Verifies that PerformanceBaseline accurately records baselines, detects
regressions, and tracks measurement history.

Tests cover:
  - BenchmarkResult.as_dict() serialisation
  - BaselineComparison.is_regression() helper
  - RegressionStatus enum string values
  - PerformanceBaseline.measure() context manager times the block
  - record_baseline() persists a value; get_baseline() reads it back
  - get_all_baselines() returns all saved entries
  - delete_baseline() removes an entry; returns False for unknown name
  - compare() returns PASS when within warn threshold
  - compare() returns WARN when between warn and fail thresholds
  - compare() returns FAIL when above fail threshold
  - compare() returns NO_BASELINE when no saved value exists
  - Faster-than-baseline comparison still returns PASS
  - regression_report() sorts FAIL before WARN before PASS
  - append_history() and load_history() round-trip
  - load_history(name) filters to a single operation
  - Corrupt baselines file falls back to empty dict (no crash)

Test count: 20
Target: pytest plugins/fda_tools/tests/test_fda134_performance_baseline.py -v
"""

from __future__ import annotations

import time
from pathlib import Path

from fda_tools.lib.performance_baseline import (
    BaselineComparison,
    BenchmarkResult,
    PerformanceBaseline,
    RegressionStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pb(tmp_path: Path, warn: float = 0.20, fail: float = 0.50) -> PerformanceBaseline:
    """Return a PerformanceBaseline backed by a tmp directory."""
    return PerformanceBaseline(
        data_dir=str(tmp_path / ".perf"),
        warn_threshold=warn,
        fail_threshold=fail,
    )


# ---------------------------------------------------------------------------
# TestRegressionStatusEnum
# ---------------------------------------------------------------------------


class TestRegressionStatusEnum:
    def test_pass_value(self):
        assert RegressionStatus.PASS == "PASS"

    def test_warn_value(self):
        assert RegressionStatus.WARN == "WARN"

    def test_fail_value(self):
        assert RegressionStatus.FAIL == "FAIL"

    def test_no_baseline_value(self):
        assert RegressionStatus.NO_BASELINE == "NO_BASELINE"


# ---------------------------------------------------------------------------
# TestBenchmarkResultDataclass
# ---------------------------------------------------------------------------


class TestBenchmarkResultDataclass:
    def test_as_dict_contains_required_keys(self):
        r = BenchmarkResult(name="cmd", duration_ms=123.456)
        d = r.as_dict()
        assert d["name"] == "cmd"
        assert d["duration_ms"] == 123.456
        assert "timestamp" in d

    def test_duration_rounded_to_three_places(self):
        r = BenchmarkResult(name="cmd", duration_ms=123.456789)
        assert r.as_dict()["duration_ms"] == 123.457


# ---------------------------------------------------------------------------
# TestBaselineComparisonDataclass
# ---------------------------------------------------------------------------


class TestBaselineComparisonDataclass:
    def test_is_regression_false_for_pass(self):
        c = BaselineComparison(
            name="cmd",
            current_ms=100,
            baseline_ms=100,
            regression_pct=0.0,
            status=RegressionStatus.PASS,
            message="ok",
        )
        assert c.is_regression() is False

    def test_is_regression_true_for_warn(self):
        c = BaselineComparison(
            name="cmd",
            current_ms=130,
            baseline_ms=100,
            regression_pct=0.30,
            status=RegressionStatus.WARN,
            message="warn",
        )
        assert c.is_regression() is True

    def test_is_regression_true_for_fail(self):
        c = BaselineComparison(
            name="cmd",
            current_ms=200,
            baseline_ms=100,
            regression_pct=1.0,
            status=RegressionStatus.FAIL,
            message="fail",
        )
        assert c.is_regression() is True


# ---------------------------------------------------------------------------
# TestMeasureContextManager
# ---------------------------------------------------------------------------


class TestMeasureContextManager:
    def test_measure_populates_duration(self, tmp_path):
        pb = _pb(tmp_path)
        with pb.measure("op") as r:
            time.sleep(0.01)
        assert r.duration_ms > 5  # at least 5 ms

    def test_measure_sets_name(self, tmp_path):
        pb = _pb(tmp_path)
        with pb.measure("my-op") as r:
            pass
        assert r.name == "my-op"

    def test_measure_sets_timestamp(self, tmp_path):
        pb = _pb(tmp_path)
        with pb.measure("op") as r:
            pass
        assert r.timestamp  # non-empty ISO string


# ---------------------------------------------------------------------------
# TestRecordAndGetBaseline
# ---------------------------------------------------------------------------


class TestRecordAndGetBaseline:
    def test_record_then_get_returns_value(self, tmp_path):
        pb = _pb(tmp_path)
        pb.record_baseline("batchfetch", 500.0)
        assert pb.get_baseline("batchfetch") == 500.0

    def test_get_unknown_returns_none(self, tmp_path):
        pb = _pb(tmp_path)
        assert pb.get_baseline("nonexistent") is None

    def test_get_all_baselines(self, tmp_path):
        pb = _pb(tmp_path)
        pb.record_baseline("cmd-a", 100.0)
        pb.record_baseline("cmd-b", 200.0)
        all_b = pb.get_all_baselines()
        assert all_b["cmd-a"] == 100.0
        assert all_b["cmd-b"] == 200.0

    def test_delete_baseline_returns_true(self, tmp_path):
        pb = _pb(tmp_path)
        pb.record_baseline("cmd", 100.0)
        assert pb.delete_baseline("cmd") is True
        assert pb.get_baseline("cmd") is None

    def test_delete_unknown_returns_false(self, tmp_path):
        pb = _pb(tmp_path)
        assert pb.delete_baseline("ghost") is False


# ---------------------------------------------------------------------------
# TestCompare
# ---------------------------------------------------------------------------


class TestCompare:
    def test_no_baseline_status(self, tmp_path):
        pb = _pb(tmp_path)
        result = pb.compare("unseen-op", 100.0)
        assert result.status == RegressionStatus.NO_BASELINE

    def test_pass_within_threshold(self, tmp_path):
        pb = _pb(tmp_path, warn=0.20)
        pb.record_baseline("op", 100.0)
        result = pb.compare("op", 115.0)  # 15% slower → PASS
        assert result.status == RegressionStatus.PASS

    def test_warn_between_thresholds(self, tmp_path):
        pb = _pb(tmp_path, warn=0.20, fail=0.50)
        pb.record_baseline("op", 100.0)
        result = pb.compare("op", 130.0)  # 30% slower → WARN
        assert result.status == RegressionStatus.WARN

    def test_fail_above_fail_threshold(self, tmp_path):
        pb = _pb(tmp_path, warn=0.20, fail=0.50)
        pb.record_baseline("op", 100.0)
        result = pb.compare("op", 200.0)  # 100% slower → FAIL
        assert result.status == RegressionStatus.FAIL

    def test_faster_than_baseline_is_pass(self, tmp_path):
        pb = _pb(tmp_path)
        pb.record_baseline("op", 200.0)
        result = pb.compare("op", 100.0)  # 50% faster
        assert result.status == RegressionStatus.PASS
        assert result.regression_pct < 0

    def test_compare_regression_pct_computed(self, tmp_path):
        pb = _pb(tmp_path)
        pb.record_baseline("op", 100.0)
        result = pb.compare("op", 130.0)
        assert abs(result.regression_pct - 0.30) < 0.01


# ---------------------------------------------------------------------------
# TestRegressionReport
# ---------------------------------------------------------------------------


class TestRegressionReport:
    def test_regression_report_sorted_fail_first(self, tmp_path):
        pb = _pb(tmp_path, warn=0.20, fail=0.50)
        pb.record_baseline("pass-op", 100.0)
        pb.record_baseline("warn-op", 100.0)
        pb.record_baseline("fail-op", 100.0)

        results = [
            BenchmarkResult("pass-op", 110.0),   # 10% → PASS
            BenchmarkResult("warn-op", 135.0),   # 35% → WARN
            BenchmarkResult("fail-op", 200.0),   # 100% → FAIL
        ]
        report = pb.regression_report(results)
        assert report[0].status == RegressionStatus.FAIL
        assert report[1].status == RegressionStatus.WARN
        assert report[2].status == RegressionStatus.PASS


# ---------------------------------------------------------------------------
# TestHistory
# ---------------------------------------------------------------------------


class TestHistory:
    def test_append_and_load_history(self, tmp_path):
        pb = _pb(tmp_path)
        r = BenchmarkResult("batchfetch", 250.0)
        pb.append_history(r)
        history = pb.load_history()
        assert len(history) == 1
        assert history[0].name == "batchfetch"
        assert history[0].duration_ms == 250.0

    def test_load_history_filtered_by_name(self, tmp_path):
        pb = _pb(tmp_path)
        pb.append_history(BenchmarkResult("cmd-a", 100.0))
        pb.append_history(BenchmarkResult("cmd-b", 200.0))
        only_a = pb.load_history(name="cmd-a")
        assert len(only_a) == 1
        assert only_a[0].name == "cmd-a"

    def test_corrupt_baselines_falls_back_to_empty(self, tmp_path):
        pb = _pb(tmp_path)
        baselines_file = tmp_path / ".perf" / "baselines.json"
        baselines_file.parent.mkdir(parents=True, exist_ok=True)
        baselines_file.write_text("NOT JSON {{{{")
        # Should not raise
        assert pb.get_all_baselines() == {}
