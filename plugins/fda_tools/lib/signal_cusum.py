"""
FDA-229  [SIG-002] CUSUM Algorithm for MAUDE Adverse Event Spike Detection
===========================================================================
Implements the two-sided CUSUM (Cumulative Sum Control Chart) for detecting
sustained shifts in FDA MAUDE adverse event report counts.

Background
----------
The CUSUM chart (Page, 1954) is a sequential change-detection algorithm that
accumulates deviations from a target mean (μ₀) and raises an alarm when the
cumulative sum exceeds a decision threshold *h*.  Unlike Shewhart control
charts — which only examine individual observations — CUSUM catches sustained
*shifts* even when no single observation is extreme.

For MAUDE monitoring this matters: a device whose adverse event rate slowly
doubles over 6 months is more dangerous than a one-month spike, and CUSUM
flags it before a clinician would notice.

Algorithm (two-sided, tabular CUSUM)
-------------------------------------
    S⁺ₙ = max(0, S⁺ₙ₋₁ + (xₙ - μ₀ - k))      ← detects upward shift
    S⁻ₙ = max(0, S⁻ₙ₋₁ - (xₙ - μ₀ + k))      ← detects downward shift

    alarm when S⁺ₙ ≥ h  or  S⁻ₙ ≥ h

Parameters
----------
    μ₀   — target (in-control) mean  (``target``)
    k    — allowance / slack          (``allowance`` ≈ half the shift to detect)
    h    — decision threshold         (``threshold`` ≈ 4–5× σ for ARL ≈ 500)

Design
------
``CusumPoint``    — immutable value object for one time-step result.
``CusumDetector`` — stateful detector; call ``update(x)`` or ``run(series)``.
``run_cusum``     — stateless convenience function for batch analysis.
``CusumSummary``  — aggregate statistics over a full run.
``auto_target``   — helper to estimate μ₀ and k from a warm-up series.

Usage
-----
    from fda_tools.lib.signal_cusum import CusumDetector, run_cusum

    # Streaming (one point at a time)
    det = CusumDetector(target=10.0, allowance=2.5, threshold=20.0)
    for count in monthly_maude_counts:
        point = det.update(count)
        if point.alarm:
            print(f"Month {point.index}: ALARM — cusum={point.cusum_high:.1f}")

    # Batch
    results = run_cusum(series=[8,9,11,10,22,25,30], target=10.0)
    alarms  = [r for r in results if r.alarm]
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


# ── Value objects ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CusumPoint:
    """
    Result of one CUSUM update step.

    Attributes:
        index:       Zero-based time index.
        value:       Observed value at this step.
        cusum_high:  Upward cumulative sum S⁺ₙ.
        cusum_low:   Downward cumulative sum S⁻ₙ.
        alarm:       True if either cusum exceeds the threshold.
        alarm_direction: ``"high"`` | ``"low"`` | ``"both"`` | ``""``
    """
    index:           int
    value:           float
    cusum_high:      float
    cusum_low:       float
    alarm:           bool
    alarm_direction: str  = ""


@dataclass
class CusumSummary:
    """
    Aggregate statistics over a complete CUSUM run.

    Attributes:
        n_points:     Total number of observations processed.
        n_alarms:     Number of alarm points.
        first_alarm:  Index of the first alarm, or ``None``.
        max_cusum_high: Maximum S⁺ value seen.
        max_cusum_low:  Maximum S⁻ value seen.
        points:       Full list of ``CusumPoint`` objects.
    """
    n_points:       int
    n_alarms:       int
    first_alarm:    Optional[int]
    max_cusum_high: float
    max_cusum_low:  float
    points:         List[CusumPoint] = field(default_factory=list)

    @property
    def alarm_rate(self) -> float:
        """Fraction of points that triggered an alarm."""
        return self.n_alarms / self.n_points if self.n_points else 0.0

    @property
    def has_alarm(self) -> bool:
        """True if any alarm was raised."""
        return self.n_alarms > 0


# ── CusumDetector ─────────────────────────────────────────────────────────────

class CusumDetector:
    """
    Stateful two-sided tabular CUSUM detector.

    Maintains running S⁺ and S⁻ accumulators.  Optionally resets after an
    alarm to start fresh detection (``reset_on_alarm=True``).

    Args:
        target:         In-control mean μ₀.
        allowance:      Slack parameter k (typically half the detectable shift).
                        Default: ``0.5 * sigma_estimate`` if not provided.
        threshold:      Decision threshold h.  Alarm fires when S⁺ ≥ h or S⁻ ≥ h.
                        Rule of thumb: ``h ≈ 5 * sigma_estimate`` for ARL ≈ 500.
        reset_on_alarm: If True, reset S⁺ and S⁻ to 0 immediately after an alarm.
    """

    def __init__(
        self,
        target:         float,
        allowance:      float,
        threshold:      float,
        reset_on_alarm: bool = False,
    ) -> None:
        if allowance <= 0:
            raise ValueError(f"allowance must be > 0, got {allowance}")
        if threshold <= 0:
            raise ValueError(f"threshold must be > 0, got {threshold}")

        self.target         = target
        self.allowance      = allowance
        self.threshold      = threshold
        self.reset_on_alarm = reset_on_alarm

        self._cusum_high: float = 0.0
        self._cusum_low:  float = 0.0
        self._index:      int   = 0

    # ── Streaming API ─────────────────────────────────────────────────────────

    def update(self, value: float) -> CusumPoint:
        """
        Ingest one observation and return the updated ``CusumPoint``.

        Args:
            value: The observed count / rate for this time period.

        Returns:
            A ``CusumPoint`` with the current CUSUM statistics and alarm status.
        """
        # Tabular CUSUM update
        self._cusum_high = max(
            0.0,
            self._cusum_high + (value - self.target - self.allowance),
        )
        self._cusum_low = max(
            0.0,
            self._cusum_low - (value - self.target + self.allowance),
        )

        alarm_high = self._cusum_high >= self.threshold
        alarm_low  = self._cusum_low  >= self.threshold
        alarm      = alarm_high or alarm_low

        direction = ""
        if alarm_high and alarm_low:
            direction = "both"
        elif alarm_high:
            direction = "high"
        elif alarm_low:
            direction = "low"

        point = CusumPoint(
            index           = self._index,
            value           = value,
            cusum_high      = self._cusum_high,
            cusum_low       = self._cusum_low,
            alarm           = alarm,
            alarm_direction = direction,
        )

        if alarm and self.reset_on_alarm:
            self._cusum_high = 0.0
            self._cusum_low  = 0.0

        self._index += 1
        return point

    # ── Batch API ─────────────────────────────────────────────────────────────

    def run(self, series: Sequence[float]) -> CusumSummary:
        """
        Process an entire time series and return a ``CusumSummary``.

        Resets the detector state before processing.

        Args:
            series: Sequence of observations (counts or rates).

        Returns:
            A ``CusumSummary`` with all points and aggregate statistics.
        """
        self.reset()
        points = [self.update(v) for v in series]
        return _summarise(points)

    # ── State management ──────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset all accumulated state (S⁺, S⁻, index)."""
        self._cusum_high = 0.0
        self._cusum_low  = 0.0
        self._index      = 0

    @property
    def cusum_high(self) -> float:
        """Current upward CUSUM accumulator value."""
        return self._cusum_high

    @property
    def cusum_low(self) -> float:
        """Current downward CUSUM accumulator value."""
        return self._cusum_low


# ── Helpers ───────────────────────────────────────────────────────────────────

def _summarise(points: List[CusumPoint]) -> CusumSummary:
    alarms = [p for p in points if p.alarm]
    return CusumSummary(
        n_points       = len(points),
        n_alarms       = len(alarms),
        first_alarm    = alarms[0].index if alarms else None,
        max_cusum_high = max((p.cusum_high for p in points), default=0.0),
        max_cusum_low  = max((p.cusum_low  for p in points), default=0.0),
        points         = points,
    )


def auto_target(
    warmup: Sequence[float],
    k_sigma: float = 0.5,
) -> Tuple[float, float]:
    """
    Estimate CUSUM parameters from a warm-up (in-control) series.

    Args:
        warmup:  In-control observations (e.g. first 12 months of baseline data).
        k_sigma: Multiplier for allowance = ``k_sigma * sigma``.
                 Default 0.5 means the CUSUM detects a 1-sigma shift.

    Returns:
        ``(target, allowance)`` — μ₀ and k estimated from *warmup*.

    Raises:
        ValueError: If *warmup* has fewer than 2 observations.
    """
    if len(warmup) < 2:
        raise ValueError("warmup must contain at least 2 observations")
    mu    = statistics.mean(warmup)
    sigma = statistics.stdev(warmup)
    k     = k_sigma * sigma if sigma > 0 else 1.0
    return mu, k


def threshold_for_arl(
    sigma: float,
    target_arl: float = 500.0,
) -> float:
    """
    Approximate CUSUM threshold h for a desired in-control Average Run Length.

    Uses the Siegmund (1985) approximation valid for Gaussian observations.

    Args:
        sigma:      Standard deviation of the in-control process.
        target_arl: Desired in-control ARL (default 500 = false alarm every 500 periods).

    Returns:
        Recommended threshold h.
    """
    # Approximate: h ≈ sigma * sqrt(2 * ln(target_arl))
    return sigma * math.sqrt(2.0 * math.log(max(target_arl, 1.0)))


# ── Convenience function ──────────────────────────────────────────────────────

def run_cusum(
    series:         Sequence[float],
    target:         float,
    allowance:      Optional[float] = None,
    threshold:      Optional[float] = None,
    reset_on_alarm: bool            = False,
) -> CusumSummary:
    """
    Stateless batch CUSUM analysis.

    If *allowance* is not provided, it defaults to ``0.5 * stdev(series)``.
    If *threshold* is not provided, it defaults to ``threshold_for_arl(stdev, 500)``.

    Args:
        series:         Sequence of observed counts / rates.
        target:         In-control mean μ₀.
        allowance:      Slack k (default: half the series stdev).
        threshold:      Decision threshold h (default: ARL-500 approximation).
        reset_on_alarm: Reset accumulators after each alarm.

    Returns:
        A ``CusumSummary`` over the full series.

    Raises:
        ValueError: If *series* is empty.
    """
    if not series:
        raise ValueError("series must not be empty")

    sigma = statistics.stdev(series) if len(series) > 1 else 1.0
    k = allowance if allowance is not None else 0.5 * max(sigma, 1e-9)
    h = threshold if threshold is not None else threshold_for_arl(sigma)

    det = CusumDetector(
        target         = target,
        allowance      = k,
        threshold      = h,
        reset_on_alarm = reset_on_alarm,
    )
    return det.run(series)
