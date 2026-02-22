"""
FDA-237  [SIG-002] CUSUM Spike Detector
========================================
Implements Page's two-sided CUSUM (Cumulative Sum) control chart for
detecting statistically significant spikes in MAUDE adverse event time
series data.

Algorithm
---------
Page's test uses two running sums that accumulate deviations from an
expected mean:

    C+[i] = max(0, C+[i-1] + (x[i] - mu) / sigma - k)
    C-[i] = max(0, C-[i-1] - (x[i] - mu) / sigma - k)

An alert fires when C+[i] > h or C-[i] > h.

Parameters
----------
k : float  — allowance (slack). Controls sensitivity.
             Typically 0.5 for "detect 1-sigma shifts quickly".
h : float  — decision threshold. Larger h = fewer false positives.
             Typically 5.0 for 1/500 ARL under H0.

Reference
---------
Page, E.S. (1954). Continuous inspection schemes. Biometrika 41, 100–115.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Sequence


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class CUSUMAlert:
    index:       int          # position in the input series
    date:        Optional[str]  # ISO date string (if dates provided)
    value:       float        # observed count at alert point
    cusum_plus:  float        # C+ accumulator value at alert
    cusum_minus: float        # C- accumulator value at alert
    direction:   str          # "UPPER" (spike up) or "LOWER" (drop)
    severity:    str          # CRITICAL / HIGH / MEDIUM


@dataclass
class CUSUMResult:
    n:          int
    k:          float
    h:          float
    mu:         float
    sigma:      float
    alerts:     List[CUSUMAlert]    = field(default_factory=list)
    cusum_plus:  List[float]        = field(default_factory=list)
    cusum_minus: List[float]        = field(default_factory=list)
    insufficient_data: bool         = False


# ── CUSUM detector ────────────────────────────────────────────────────────────


class CUSUMDetector:
    """
    Two-sided Page's CUSUM detector for adverse event time series.

    Usage
    -----
    detector = CUSUMDetector(k=0.5, h=5.0)
    result   = detector.detect(counts, dates=date_strings)

    Or with explicit baseline fitting::

        detector.fit(baseline_series)
        result = detector.detect(new_series)
    """

    def __init__(self, k: float = 0.5, h: float = 5.0) -> None:
        """
        Parameters
        ----------
        k : allowance / reference value (half of detectable shift in sigma)
        h : decision threshold (C > h triggers alert)
        """
        self.k       = k
        self.h       = h
        self._mu:    Optional[float] = None
        self._sigma: Optional[float] = None

    # ------------------------------------------------------------------
    # fit / detect API
    # ------------------------------------------------------------------

    def fit(self, baseline_series: Sequence[float]) -> "CUSUMDetector":
        """
        Estimate mean and standard deviation from *baseline_series*.

        Call before ``detect()`` when fitting on a separate historical
        window. If not called, ``detect()`` fits internally from the
        first half of the input series.
        """
        values = [float(v) for v in baseline_series]
        self._mu, self._sigma = _compute_mu_sigma(values)
        return self

    def detect(
        self,
        series: Sequence[float],
        dates:  Optional[Sequence[str]] = None,
    ) -> CUSUMResult:
        """
        Run two-sided CUSUM on *series*, returning detected alerts.

        Parameters
        ----------
        series : sequence of daily event counts (floats / ints)
        dates  : optional ISO date strings aligned with *series*
        """
        values = _interpolate_missing([float(v) for v in series])
        n      = len(values)

        # Need at least 5 data points for meaningful CUSUM
        if n < 5:
            return CUSUMResult(
                n=n, k=self.k, h=self.h,
                mu=0.0, sigma=0.0,
                insufficient_data=True,
            )

        # Use pre-fitted params or derive from first half of series
        if self._mu is not None and self._sigma is not None:
            mu, sigma = self._mu, self._sigma
        else:
            split     = max(2, n // 2)
            mu, sigma = _compute_mu_sigma(values[:split])

        # Run Page's two-sided CUSUM
        cusum_plus:  List[float] = []
        cusum_minus: List[float] = []
        c_plus  = 0.0
        c_minus = 0.0
        alerts: List[CUSUMAlert] = []

        for i, x in enumerate(values):
            z = (x - mu) / sigma if sigma > 0 else 0.0

            c_plus  = max(0.0, c_plus  + z - self.k)
            c_minus = max(0.0, c_minus - z - self.k)

            cusum_plus.append(round(c_plus, 4))
            cusum_minus.append(round(c_minus, 4))

            if c_plus > self.h:
                alerts.append(CUSUMAlert(
                    index       = i,
                    date        = dates[i] if dates and i < len(dates) else None,
                    value       = x,
                    cusum_plus  = round(c_plus, 3),
                    cusum_minus = round(c_minus, 3),
                    direction   = "UPPER",
                    severity    = _severity(c_plus, self.h),
                ))
                c_plus = 0.0   # reset after alert

            elif c_minus > self.h:
                alerts.append(CUSUMAlert(
                    index       = i,
                    date        = dates[i] if dates and i < len(dates) else None,
                    value       = x,
                    cusum_plus  = round(c_plus, 3),
                    cusum_minus = round(c_minus, 3),
                    direction   = "LOWER",
                    severity    = _severity(c_minus, self.h),
                ))
                c_minus = 0.0  # reset after alert

        return CUSUMResult(
            n           = n,
            k           = self.k,
            h           = self.h,
            mu          = round(mu, 4),
            sigma       = round(sigma, 4),
            alerts      = alerts,
            cusum_plus  = cusum_plus,
            cusum_minus = cusum_minus,
        )


# ── Private helpers ───────────────────────────────────────────────────────────


def _compute_mu_sigma(values: List[float]) -> tuple:
    """Return (mean, stdev) — stdev defaults to 1.0 for constant series."""
    if len(values) < 2:
        return float(values[0]) if values else 0.0, 1.0
    mu    = statistics.mean(values)
    sigma = statistics.stdev(values)
    return mu, (sigma if sigma > 0 else 1.0)


def _interpolate_missing(values: List[float]) -> List[float]:
    """
    Linear interpolation for any NaN / negative counts.

    Negative values are treated as missing data (openFDA sometimes
    returns -1 for suppressed counts).
    """
    out: List[float] = list(values)
    for i, v in enumerate(out):
        if math.isnan(v) or v < 0:
            # Find nearest valid neighbours
            prev_i = next((j for j in range(i - 1, -1, -1)
                           if not math.isnan(out[j]) and out[j] >= 0), None)
            next_i = next((j for j in range(i + 1, len(out))
                           if not math.isnan(out[j]) and out[j] >= 0), None)
            if prev_i is not None and next_i is not None:
                out[i] = out[prev_i] + (out[next_i] - out[prev_i]) * (
                    (i - prev_i) / (next_i - prev_i)
                )
            elif prev_i is not None:
                out[i] = out[prev_i]
            elif next_i is not None:
                out[i] = out[next_i]
            else:
                out[i] = 0.0
    return out


def _severity(c_value: float, h: float) -> str:
    """Map CUSUM accumulator ratio to severity label."""
    ratio = c_value / h
    if ratio >= 3.0:
        return "CRITICAL"
    if ratio >= 2.0:
        return "HIGH"
    return "MEDIUM"
