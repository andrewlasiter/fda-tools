"""
FDA-238  [SIG-003] Cross-Signal Correlation
============================================
Computes Pearson correlation between MAUDE adverse event counts and
device recall counts for a given product code, with optional lead-lag
analysis to surface whether recalls tend to follow (or precede) spikes
in adverse event reports.

Output schema
-------------
{
  "product_code": "DQY",
  "window_days": 90,
  "maude_points": 45,
  "recall_points": 45,
  "pearson_r": 0.72,
  "p_value": 0.001,
  "lag_days": 14,
  "lag_r": 0.81,
  "interpretation": "Strong positive correlation...",
  "insufficient_data": false
}

Graceful degradation
--------------------
- Returns ``insufficient_data=True`` when either series has < 5 points
- Returns ``pearson_r=None`` when variance is zero (constant series)
- All network calls degrade to empty data on failure
"""

from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum data points required for meaningful correlation
MIN_DATA_POINTS = 5

# Lead-lag window to test (days)
MAX_LAG_DAYS = 30


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class CorrelationReport:
    product_code:      str
    window_days:       int
    maude_points:      int
    recall_points:     int
    pearson_r:         Optional[float]
    p_value:           Optional[float]
    lag_days:          int               # lag with highest |r|; 0 = same-day
    lag_r:             Optional[float]   # r at optimal lag
    interpretation:    str
    insufficient_data: bool = False
    error:             Optional[str] = None


# ── Public entry point ────────────────────────────────────────────────────────


def correlate(
    product_code: str,
    window_days:  int = 90,
    maude_series: Optional[Dict[str, int]] = None,
    recall_series: Optional[Dict[str, int]] = None,
) -> CorrelationReport:
    """
    Compute Pearson correlation between MAUDE events and recalls for
    *product_code* over the last *window_days* days.

    Parameters
    ----------
    product_code  : FDA product code (e.g. "DQY")
    window_days   : look-back window
    maude_series  : pre-fetched ``{ISO-date: count}`` dict (testing hook)
    recall_series : pre-fetched ``{ISO-date: count}`` dict (testing hook)

    Returns
    -------
    :class:`CorrelationReport`
    """
    if maude_series is None:
        maude_series = _fetch_maude_monthly(product_code, window_days)
    if recall_series is None:
        recall_series = _fetch_recall_monthly(product_code, window_days)

    dates  = _date_range_months(window_days)
    x_vals = [float(maude_series.get(d, 0)) for d in dates]
    y_vals = [float(recall_series.get(d, 0)) for d in dates]

    n = len(dates)
    if n < MIN_DATA_POINTS:
        return CorrelationReport(
            product_code=product_code.upper(),
            window_days=window_days,
            maude_points=sum(1 for v in x_vals if v > 0),
            recall_points=sum(1 for v in y_vals if v > 0),
            pearson_r=None,
            p_value=None,
            lag_days=0,
            lag_r=None,
            interpretation="Insufficient data for correlation analysis.",
            insufficient_data=True,
        )

    r_same, p_same = _pearson(x_vals, y_vals)

    # Lead-lag: test shifts of -MAX_LAG to +MAX_LAG months
    best_lag, best_r = _best_lag(x_vals, y_vals, max_lag=min(MAX_LAG_DAYS // 30, n - 2))

    return CorrelationReport(
        product_code  = product_code.upper(),
        window_days   = window_days,
        maude_points  = sum(1 for v in x_vals if v > 0),
        recall_points = sum(1 for v in y_vals if v > 0),
        pearson_r     = r_same,
        p_value       = p_same,
        lag_days      = best_lag * 30,  # convert months to approx days
        lag_r         = best_r,
        interpretation = _interpret(r_same, best_lag, best_r),
        insufficient_data = False,
    )


# ── Statistics ────────────────────────────────────────────────────────────────


def _pearson(x: List[float], y: List[float]) -> Tuple[Optional[float], Optional[float]]:
    """
    Compute Pearson r and approximate two-tailed p-value.

    Returns (None, None) if either series is constant (zero variance).
    """
    n = len(x)
    if n < 2:
        return None, None

    mx, my = statistics.mean(x), statistics.mean(y)
    sx_sq  = sum((xi - mx) ** 2 for xi in x)
    sy_sq  = sum((yi - my) ** 2 for yi in y)

    if sx_sq == 0 or sy_sq == 0:
        return None, None   # constant series — r is undefined

    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    r   = sxy / math.sqrt(sx_sq * sy_sq)
    r   = max(-1.0, min(1.0, r))   # clamp floating point errors

    # Approximate p-value using t-distribution with n-2 df
    if abs(r) >= 1.0:
        p = 0.0
    else:
        t   = r * math.sqrt((n - 2) / (1 - r ** 2))
        p   = _t_pvalue(t, n - 2)

    return round(r, 4), round(p, 6)


def _best_lag(
    x: List[float],
    y: List[float],
    max_lag: int = 3,
) -> Tuple[int, Optional[float]]:
    """
    Test lags from -max_lag to +max_lag months.

    Positive lag means MAUDE leads recalls (events come first).
    Returns (lag, r) with highest absolute r.
    """
    best_lag = 0
    best_r, _ = _pearson(x, y)

    for lag in range(-max_lag, max_lag + 1):
        if lag == 0:
            continue
        if lag > 0:
            xi, yi = x[lag:], y[:len(y) - lag]
        else:
            xi, yi = x[:len(x) + lag], y[-lag:]
        if len(xi) < MIN_DATA_POINTS:
            continue
        r, _ = _pearson(xi, yi)
        if r is not None and (best_r is None or abs(r) > abs(best_r)):
            best_r, best_lag = r, lag

    return best_lag, best_r


def _t_pvalue(t: float, df: int) -> float:
    """
    Approximate two-tailed p-value for t-statistic with *df* degrees of
    freedom using the Cornish-Fisher approximation. Good enough for
    regulatory signal flagging (no scipy dependency).
    """
    # Normalise t to z-score via a simple df correction
    z = t * (1 - 1 / (4 * df))
    p_one_tail = _normal_sf(abs(z))
    return min(1.0, 2 * p_one_tail)


def _normal_sf(z: float) -> float:
    """Survival function P(Z > z) for standard normal, using erfc."""
    return 0.5 * math.erfc(z / math.sqrt(2))


# ── Data fetchers ─────────────────────────────────────────────────────────────


def _fetch_maude_monthly(product_code: str, window_days: int) -> Dict[str, int]:
    """
    Fetch MAUDE adverse event counts aggregated by month.
    Returns {YYYY-MM: count}.  Empty dict on failure.
    """
    try:
        from fda_tools.scripts.fda_http import create_session as _cs
        cutoff = (date.today() - timedelta(days=window_days)).strftime("%Y%m%d")
        today  = date.today().strftime("%Y%m%d")
        session = _cs(purpose="api")
        resp = session.get(
            "https://api.fda.gov/device/event.json",
            params={
                "search": (
                    f"device.openfda.device_name:{product_code.upper()}"
                    f"+AND+date_received:[{cutoff}+TO+{today}]"
                ),
                "count": "date_received",
                "limit": "1000",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return {}
        raw = resp.json().get("results", [])
        return _aggregate_monthly(raw, "time")
    except Exception as exc:
        logger.warning("MAUDE fetch failed for correlation: %s", exc)
        return {}


def _fetch_recall_monthly(product_code: str, window_days: int) -> Dict[str, int]:
    """
    Fetch device recall counts aggregated by month.
    Returns {YYYY-MM: count}.  Empty dict on failure.
    """
    try:
        from fda_tools.scripts.fda_http import create_session as _cs
        cutoff = (date.today() - timedelta(days=window_days)).strftime("%Y-%m-%d")
        today  = date.today().strftime("%Y-%m-%d")
        session = _cs(purpose="api")
        resp = session.get(
            "https://api.fda.gov/device/recall.json",
            params={
                "search": (
                    f"product_code:{product_code.upper()}"
                    f"+AND+event_date_initiated:[{cutoff}+TO+{today}]"
                ),
                "count": "event_date_initiated",
                "limit": "1000",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return {}
        raw = resp.json().get("results", [])
        return _aggregate_monthly(raw, "time")
    except Exception as exc:
        logger.warning("Recall fetch failed for correlation: %s", exc)
        return {}


def _aggregate_monthly(records: list, date_field: str) -> Dict[str, int]:
    """Sum count-by-date records into monthly buckets."""
    monthly: Dict[str, int] = {}
    for rec in records:
        raw = str(rec.get(date_field, ""))
        if len(raw) >= 6:
            month_key = f"{raw[:4]}-{raw[4:6]}"
            monthly[month_key] = monthly.get(month_key, 0) + int(rec.get("count", 1))
    return monthly


def _date_range_months(window_days: int) -> List[str]:
    """Return list of YYYY-MM keys for the past window_days (monthly buckets)."""
    n_months  = max(1, window_days // 30)
    today     = date.today()
    result    = []
    for i in range(n_months - 1, -1, -1):
        d = today - timedelta(days=i * 30)
        result.append(f"{d.year:04d}-{d.month:02d}")
    # Deduplicate while preserving order
    seen = set()
    dedup = []
    for m in result:
        if m not in seen:
            seen.add(m)
            dedup.append(m)
    return dedup


# ── Interpretation helper ─────────────────────────────────────────────────────


def _interpret(
    r:        Optional[float],
    lag:      int,
    lag_r:    Optional[float],
) -> str:
    if r is None:
        return "Correlation could not be computed (constant series or insufficient variance)."

    strength = (
        "strong"   if abs(r) >= 0.7 else
        "moderate" if abs(r) >= 0.4 else
        "weak"
    )
    direction = "positive" if r >= 0 else "negative"

    base = f"{strength.capitalize()} {direction} correlation (r={r:.2f}) between MAUDE events and recalls."

    if lag != 0 and lag_r is not None and abs(lag_r) > abs(r):
        lead = "MAUDE leads recalls" if lag > 0 else "Recalls lead MAUDE"
        base += (
            f" Stronger correlation at {abs(lag)} month lag "
            f"(r={lag_r:.2f}); {lead}."
        )
    return base
