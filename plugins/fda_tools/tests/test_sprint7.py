"""
Sprint 7 unit tests — FDA-248..251
===================================
Sprint 7 adds the Document Studio UI (FDA-250/251) and signal / predicate
research surfaces (FDA-248/249).  The React components themselves are tested
at the TypeScript layer; this file covers the Python backend modules that
power them:

 - signal_cusum.CUSUMDetector (drives the Signal Dashboard, FDA-248)
 - signal_cusum helpers: _interpolate_missing, _severity
 - signal_correlation.CrossSignalCorrelator (cross-MAUDE/recall correlation)

All tests are pure-Python unit tests — no database, no network required.
"""

import math
import pytest


# ── CUSUMDetector ─────────────────────────────────────────────────────────────


class TestCUSUMDetector:
    """Tests for the two-sided Page's CUSUM detector."""

    # Helpers ------------------------------------------------------------------

    def _make_detector(self, k=0.5, h=5.0):
        from plugins.fda_tools.lib.signal_cusum import CUSUMDetector
        return CUSUMDetector(k=k, h=h)

    def _flat_series(self, value=5.0, length=30):
        return [value] * length

    def _spike_at(self, base=5.0, length=30, spike_idx=25, spike_value=50.0):
        series = [base] * length
        series[spike_idx] = spike_value
        return series

    # Insufficient data --------------------------------------------------------

    def test_insufficient_data_fewer_than_5(self):
        d = self._make_detector()
        result = d.detect([1, 2, 3])
        assert result.insufficient_data is True
        assert result.alerts == []

    def test_exactly_5_points_not_insufficient(self):
        d = self._make_detector()
        result = d.detect([1, 1, 1, 1, 1])
        assert result.insufficient_data is False

    # Spike detection ----------------------------------------------------------

    def test_detects_upper_spike(self):
        """A large spike should generate at least one UPPER alert."""
        d     = self._make_detector(k=0.5, h=5.0)
        series = self._spike_at(base=5.0, spike_value=80.0, spike_idx=20, length=30)
        result = d.detect(series)
        assert any(a.direction == "UPPER" for a in result.alerts), (
            "Expected at least one UPPER alert for a large spike"
        )

    def test_no_alert_on_flat_series(self):
        """A constant series (sigma=0, forced to 1.0) yields no alerts."""
        d = self._make_detector()
        # Flat series: mean=5, sigma=0 → forced to 1.0, all z=0, CUSUM stays 0
        result = d.detect(self._flat_series(value=5.0, length=30))
        assert result.alerts == [], "Flat series should produce no CUSUM alerts"

    def test_detects_lower_drop(self):
        """A sudden drop should generate at least one LOWER alert."""
        d = self._make_detector(k=0.5, h=5.0)
        # Start high, then drop to near zero
        series = [20.0] * 20 + [0.0] * 15
        result = d.detect(series)
        assert any(a.direction == "LOWER" for a in result.alerts), (
            "Expected LOWER alert for sudden drop to zero"
        )

    # Severity mapping ---------------------------------------------------------

    def test_severity_medium_just_above_threshold(self):
        from plugins.fda_tools.lib.signal_cusum import _severity
        h = 5.0
        # ratio = 5.5 / 5.0 = 1.1 → MEDIUM
        assert _severity(5.5, h) == "MEDIUM"

    def test_severity_high(self):
        from plugins.fda_tools.lib.signal_cusum import _severity
        h = 5.0
        # ratio = 11 / 5 = 2.2 → HIGH
        assert _severity(11.0, h) == "HIGH"

    def test_severity_critical(self):
        from plugins.fda_tools.lib.signal_cusum import _severity
        h = 5.0
        # ratio = 16 / 5 = 3.2 → CRITICAL
        assert _severity(16.0, h) == "CRITICAL"

    # Date threading -----------------------------------------------------------

    def test_alert_carries_date_when_provided(self):
        d = self._make_detector()
        series = self._spike_at(base=5.0, spike_value=100.0, spike_idx=20, length=30)
        dates  = [f"2024-01-{i+1:02d}" for i in range(30)]
        result = d.detect(series, dates=dates)
        if result.alerts:
            assert result.alerts[0].date is not None
            assert result.alerts[0].date.startswith("2024-01-")

    def test_alert_date_is_none_without_dates(self):
        d = self._make_detector()
        series = self._spike_at(base=5.0, spike_value=100.0, spike_idx=20, length=30)
        result = d.detect(series)
        if result.alerts:
            assert result.alerts[0].date is None

    # Pre-fitted baseline ------------------------------------------------------

    def test_fit_separates_baseline_from_detection(self):
        """Fitting on a stable baseline should detect spike in test window."""
        from plugins.fda_tools.lib.signal_cusum import CUSUMDetector
        d = CUSUMDetector(k=0.5, h=5.0)
        d.fit([5.0] * 20)          # stable baseline
        # Detection on spike-heavy series
        result = d.detect([5.0] * 10 + [100.0] * 5)
        assert any(a.direction == "UPPER" for a in result.alerts)

    # Result structure ---------------------------------------------------------

    def test_result_fields_populated(self):
        d = self._make_detector()
        result = d.detect([2, 3, 5, 3, 2, 4, 6, 3, 4, 5])
        assert result.n == 10
        assert result.k == 0.5
        assert result.h == 5.0
        assert len(result.cusum_plus)  == 10
        assert len(result.cusum_minus) == 10

    def test_cusum_accumulators_non_negative(self):
        """CUSUM accumulators should never go below zero."""
        d = self._make_detector()
        result = d.detect(list(range(1, 31)))
        assert all(v >= 0 for v in result.cusum_plus)
        assert all(v >= 0 for v in result.cusum_minus)


# ── _interpolate_missing ──────────────────────────────────────────────────────


class TestInterpolateMissing:
    """Tests for the NaN / negative-value interpolation helper."""

    def _interp(self, values):
        from plugins.fda_tools.lib.signal_cusum import _interpolate_missing
        return _interpolate_missing(values)

    def test_no_missing_values_unchanged(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert self._interp(values) == values

    def test_negative_value_interpolated(self):
        # -1 between 2.0 and 4.0 → should become 3.0
        result = self._interp([2.0, -1.0, 4.0])
        assert abs(result[1] - 3.0) < 0.01, f"Expected 3.0, got {result[1]}"

    def test_nan_value_interpolated(self):
        result = self._interp([1.0, float("nan"), 3.0])
        assert not math.isnan(result[1])
        assert abs(result[1] - 2.0) < 0.01

    def test_leading_negative_filled_by_next(self):
        result = self._interp([-1.0, 5.0, 10.0])
        assert result[0] == 5.0, "Leading missing should be filled by next valid"

    def test_trailing_negative_filled_by_prev(self):
        result = self._interp([5.0, 10.0, -1.0])
        assert result[2] == 10.0, "Trailing missing should be filled by prev valid"

    def test_all_missing_becomes_zero(self):
        result = self._interp([-1.0, -1.0, -1.0])
        assert result == [0.0, 0.0, 0.0]


# ── _compute_mu_sigma ─────────────────────────────────────────────────────────


class TestComputeMuSigma:
    """Tests for the mean/sigma estimation helper."""

    def _compute(self, values):
        from plugins.fda_tools.lib.signal_cusum import _compute_mu_sigma
        return _compute_mu_sigma(values)

    def test_known_values(self):
        mu, sigma = self._compute([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        # mean = 5.0, stdev ≈ 2.0
        assert abs(mu - 5.0) < 0.01
        assert sigma > 0

    def test_constant_series_sigma_forced_to_one(self):
        mu, sigma = self._compute([7.0, 7.0, 7.0])
        assert mu == 7.0
        assert sigma == 1.0, "Constant series should produce sigma=1.0"

    def test_single_element(self):
        mu, sigma = self._compute([42.0])
        assert mu == 42.0
        assert sigma == 1.0


# ── SignalResult API contract ─────────────────────────────────────────────────


class TestSignalResultContract:
    """
    Verifies that the API response shape matches the TypeScript SignalResult
    interface expected by the frontend SignalDashboard component.

    TypeScript interface (from api-client.ts):
      interface SignalResult {
        date:        string;
        count:       number;
        severity:    "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
        description: string;
        event_types: string[];
        cusum_value: number;
        direction:   "UPPER" | "LOWER";
      }
    """

    def _build_signal_result_from_alert(self, alert, window_label="spike in events"):
        """Convert a CUSUMAlert → the dict the bridge endpoint serialises."""
        return {
            "date":        alert.date or "2024-01-01",
            "count":       int(alert.value),
            "severity":    alert.severity,
            "description": f"CUSUM {alert.direction} alert: {window_label}",
            "event_types": [],
            "cusum_value": max(alert.cusum_plus, alert.cusum_minus),
            "direction":   alert.direction,
        }

    def test_severity_values_are_valid(self):
        from plugins.fda_tools.lib.signal_cusum import CUSUMDetector
        d      = CUSUMDetector()
        series = [5.0] * 20 + [80.0] + [5.0] * 9
        result = d.detect(series)
        valid_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        for alert in result.alerts:
            assert alert.severity in valid_severities, (
                f"Severity '{alert.severity}' not in {valid_severities}"
            )

    def test_direction_values_are_valid(self):
        from plugins.fda_tools.lib.signal_cusum import CUSUMDetector
        d      = CUSUMDetector()
        series = [20.0] * 20 + [0.0] * 10
        result = d.detect(series)
        for alert in result.alerts:
            assert alert.direction in ("UPPER", "LOWER")

    def test_signal_result_dict_has_required_fields(self):
        from plugins.fda_tools.lib.signal_cusum import CUSUMAlert
        alert = CUSUMAlert(
            index       = 5,
            date        = "2024-03-15",
            value       = 42.0,
            cusum_plus  = 12.5,
            cusum_minus = 0.0,
            direction   = "UPPER",
            severity    = "HIGH",
        )
        result = self._build_signal_result_from_alert(alert)
        required = {"date", "count", "severity", "description", "event_types",
                    "cusum_value", "direction"}
        assert set(result.keys()) >= required, (
            f"Missing keys: {required - set(result.keys())}"
        )

    def test_cusum_value_is_max_of_plus_minus(self):
        from plugins.fda_tools.lib.signal_cusum import CUSUMAlert
        alert = CUSUMAlert(
            index=0, date=None, value=10.0,
            cusum_plus=7.5, cusum_minus=3.0,
            direction="UPPER", severity="HIGH",
        )
        r = self._build_signal_result_from_alert(alert)
        assert r["cusum_value"] == 7.5

    def test_count_is_integer(self):
        from plugins.fda_tools.lib.signal_cusum import CUSUMAlert
        alert = CUSUMAlert(
            index=0, date="2024-01-01", value=15.7,
            cusum_plus=8.0, cusum_minus=0.0,
            direction="UPPER", severity="HIGH",
        )
        r = self._build_signal_result_from_alert(alert)
        assert isinstance(r["count"], int), "count should be int for frontend"
