"""
FDA-238  [SIG-003] Cross-Signal Correlation (MAUDE + Recalls + Enforcement)
============================================================================
Computes Pearson and Spearman correlations between FDA adverse-event signal
time series: MAUDE reports, device recalls, and enforcement actions.

Identifying correlated spikes across signal types strengthens evidence of a
genuine safety issue — a recall wave that follows a MAUDE spike two months
later is far more actionable than either signal alone.

Design
------
``SignalSeries``       — immutable named time series (list of float counts/rates).
``CorrelationResult`` — frozen result of one pairwise correlation.
``CrossSignalAnalyzer``— pairwise correlations, lag analysis, composite scoring.
``correlate_signals`` — convenience one-call function.

Correlation methods
-------------------
``pearson``   — linear correlation (sensitive to outliers; good for rate data).
``spearman``  — rank correlation (robust to outliers; good for count data).
``kendall``   — concordance measure (most robust; slower for long series).

Lag analysis
------------
``lag_correlate(series_a, series_b, max_lag)`` shifts series_b by 0..max_lag
periods and returns correlations at each lag.  For MAUDE→Recall the peak
typically appears at lag=1–3 months.

Usage
-----
    from fda_tools.lib.signal_correlation import CrossSignalAnalyzer, SignalSeries

    maude    = SignalSeries("maude",       [10,12,9,11,35,40,38,12])
    recalls  = SignalSeries("recalls",     [1, 1, 1, 2, 3, 8, 9,  3])
    enforce  = SignalSeries("enforcement", [0, 0, 0, 0, 1, 2, 3,  1])

    analyzer = CrossSignalAnalyzer([maude, recalls, enforce])
    results  = analyzer.correlate_all()          # all pairwise Pearson
    lags     = analyzer.lag_analysis("maude", "recalls", max_lag=3)
    score    = analyzer.composite_risk_score()   # 0–1 cross-signal risk
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


# ── Optional scipy import ─────────────────────────────────────────────────────

try:
    from scipy import stats as _scipy_stats  # type: ignore[import]
    _SCIPY_AVAILABLE = True
except ImportError:
    _scipy_stats = None  # type: ignore[assignment]
    _SCIPY_AVAILABLE = False


# ── Value objects ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SignalSeries:
    """
    A named, immutable time series of signal counts or rates.

    Attributes:
        name:    Identifier for this signal (e.g. ``"maude"``, ``"recalls"``).
        values:  Ordered list of numeric observations (counts or rates).
        unit:    Optional description of the unit (e.g. ``"events/month"``).
    """
    name:   str
    values: Tuple[float, ...]
    unit:   str = ""

    def __init__(self, name: str, values: Sequence[float], unit: str = "") -> None:
        object.__setattr__(self, "name",   name)
        object.__setattr__(self, "values", tuple(float(v) for v in values))
        object.__setattr__(self, "unit",   unit)

    def __len__(self) -> int:
        return len(self.values)

    @property
    def mean(self) -> float:
        return statistics.mean(self.values) if self.values else 0.0

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.values) if len(self.values) >= 2 else 0.0


@dataclass(frozen=True)
class CorrelationResult:
    """
    Result of a pairwise correlation between two signal series.

    Attributes:
        series_a:    Name of the first series.
        series_b:    Name of the second series.
        method:      Correlation method: ``"pearson"``, ``"spearman"``, or ``"kendall"``.
        coefficient: Correlation coefficient (−1 to +1).
        p_value:     Two-tailed p-value for the null hypothesis (ρ = 0).
        lag:         Number of periods *series_b* was shifted (0 = no lag).
        n:           Number of paired observations used.
        significant: True if ``p_value < 0.05``.
    """
    series_a:    str
    series_b:    str
    method:      str
    coefficient: float
    p_value:     float
    lag:         int   = 0
    n:           int   = 0
    significant: bool  = False

    @property
    def strength(self) -> str:
        """Return a human-readable correlation strength label."""
        r = abs(self.coefficient)
        if r >= 0.7:
            return "strong"
        if r >= 0.4:
            return "moderate"
        if r >= 0.2:
            return "weak"
        return "negligible"

    def as_dict(self) -> Dict[str, object]:
        return {
            "series_a":    self.series_a,
            "series_b":    self.series_b,
            "method":      self.method,
            "coefficient": round(self.coefficient, 4),
            "p_value":     round(self.p_value, 6),
            "lag":         self.lag,
            "n":           self.n,
            "significant": self.significant,
            "strength":    self.strength,
        }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _pearson(x: Sequence[float], y: Sequence[float]) -> Tuple[float, float]:
    """Return (r, p_value) for Pearson correlation."""
    if _SCIPY_AVAILABLE and _scipy_stats is not None:
        result = _scipy_stats.pearsonr(x, y)
        # scipy ≥1.9 returns a named object; older versions return a plain tuple;
        # indexing works for both — suppress Pyright's generic-tuple complaint.
        r = float(result[0])  # type: ignore[arg-type]
        p = float(result[1])  # type: ignore[arg-type]
        return r, p
    return _manual_pearson(x, y)


def _spearman(x: Sequence[float], y: Sequence[float]) -> Tuple[float, float]:
    """Return (r, p_value) for Spearman rank correlation."""
    if _SCIPY_AVAILABLE and _scipy_stats is not None:
        result = _scipy_stats.spearmanr(x, y)
        r = float(result[0])  # type: ignore[arg-type]
        p = float(result[1])  # type: ignore[arg-type]
        return r, p
    # Fallback: convert to ranks then use Pearson
    rx = _rank(list(x))
    ry = _rank(list(y))
    return _manual_pearson(rx, ry)


def _kendall(x: Sequence[float], y: Sequence[float]) -> Tuple[float, float]:
    """Return (tau, p_value) for Kendall concordance."""
    if _SCIPY_AVAILABLE and _scipy_stats is not None:
        result = _scipy_stats.kendalltau(x, y)
        r = float(result[0])  # type: ignore[arg-type]
        p = float(result[1])  # type: ignore[arg-type]
        return r, p
    return _manual_kendall(list(x), list(y))


def _rank(values: List[float]) -> List[float]:
    """Convert values to ranks (1-based, average ties)."""
    sorted_vals = sorted(enumerate(values), key=lambda t: t[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(sorted_vals):
        j = i
        while j < len(sorted_vals) - 1 and sorted_vals[j][1] == sorted_vals[j + 1][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[sorted_vals[k][0]] = avg_rank
        i = j + 1
    return ranks


def _manual_pearson(x: Sequence[float], y: Sequence[float]) -> Tuple[float, float]:
    """Pearson r without scipy; p-value approximated via t-distribution."""
    import math
    n = len(x)
    if n < 3:
        return 0.0, 1.0
    mx = sum(x) / n
    my = sum(y) / n
    num   = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if den_x == 0 or den_y == 0:
        return 0.0, 1.0
    r = num / (den_x * den_y)
    r = max(-1.0, min(1.0, r))
    # t-statistic approximation
    if abs(r) >= 1.0:
        p = 0.0
    else:
        t = r * math.sqrt(n - 2) / math.sqrt(1 - r ** 2)
        # Two-tailed p-value approximation (large-n normal approximation)
        p = 2 * (1 - _normal_cdf(abs(t)))
    return r, p


def _manual_kendall(x: List[float], y: List[float]) -> Tuple[float, float]:
    """Kendall tau-b without scipy."""
    import math
    n = len(x)
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx * dy > 0:
                concordant += 1
            elif dx * dy < 0:
                discordant += 1
    total = concordant + discordant
    tau = (concordant - discordant) / total if total else 0.0
    # p-value normal approximation
    var = (2 * (2 * n + 5)) / (9 * n * (n - 1)) if n > 1 else 1.0
    z   = tau / math.sqrt(var) if var > 0 else 0.0
    p   = 2 * (1 - _normal_cdf(abs(z)))
    return tau, p


def _normal_cdf(z: float) -> float:
    """Approximate standard normal CDF using Zelen & Severo (1964) formula."""
    import math
    if z < 0:
        return 1 - _normal_cdf(-z)
    t = 1 / (1 + 0.2316419 * z)
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    return 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly


# ── CrossSignalAnalyzer ───────────────────────────────────────────────────────

class CrossSignalAnalyzer:
    """
    Pairwise correlation and lag analysis across multiple signal series.

    Args:
        signals: List of ``SignalSeries`` objects to analyse together.
    """

    def __init__(self, signals: List[SignalSeries]) -> None:
        if len(signals) < 2:
            raise ValueError("At least 2 signal series required for cross-signal analysis")
        self.signals: Dict[str, SignalSeries] = {s.name: s for s in signals}

    # ── Pairwise correlation ───────────────────────────────────────────────────

    def correlate(
        self,
        name_a:  str,
        name_b:  str,
        method:  str = "pearson",
        lag:     int = 0,
    ) -> CorrelationResult:
        """
        Compute correlation between two named series with optional lag.

        Args:
            name_a:  Name of the first series.
            name_b:  Name of the second series (shifted by *lag* if > 0).
            method:  ``"pearson"``, ``"spearman"``, or ``"kendall"``.
            lag:     Periods to shift *series_b* forward (positive = b lags a).

        Returns:
            A ``CorrelationResult``.

        Raises:
            KeyError: If either series name is not registered.
            ValueError: If fewer than 3 paired observations remain after alignment.
        """
        sa = self.signals[name_a]
        sb = self.signals[name_b]

        xa = list(sa.values)
        xb = list(sb.values)

        if lag > 0:
            xa = xa[lag:]
            xb = xb[:len(xb) - lag] if len(xb) > lag else []

        n = min(len(xa), len(xb))
        xa, xb = xa[:n], xb[:n]

        if n < 3:
            raise ValueError(
                f"Too few paired observations ({n}) after applying lag={lag} "
                f"to correlate '{name_a}' and '{name_b}'. Need ≥ 3."
            )

        _fn = {"pearson": _pearson, "spearman": _spearman, "kendall": _kendall}
        if method not in _fn:
            raise ValueError(f"Unknown method '{method}'; choose from {list(_fn)}")

        r, p = _fn[method](xa, xb)
        return CorrelationResult(
            series_a    = name_a,
            series_b    = name_b,
            method      = method,
            coefficient = r,
            p_value     = p,
            lag         = lag,
            n           = n,
            significant = p < 0.05,
        )

    def correlate_all(
        self,
        method: str = "pearson",
    ) -> List[CorrelationResult]:
        """
        Compute all pairwise correlations (no lag) between registered series.

        Returns:
            List of ``CorrelationResult`` sorted by |coefficient| descending.
        """
        names = list(self.signals.keys())
        results = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                try:
                    results.append(self.correlate(names[i], names[j], method=method))
                except ValueError:
                    pass  # skip pairs with insufficient data
        results.sort(key=lambda r: abs(r.coefficient), reverse=True)
        return results

    # ── Lag analysis ──────────────────────────────────────────────────────────

    def lag_analysis(
        self,
        name_a:   str,
        name_b:   str,
        max_lag:  int    = 6,
        method:   str    = "pearson",
    ) -> List[CorrelationResult]:
        """
        Compute correlations at lag=0, 1, …, *max_lag* between two series.

        Useful for detecting delayed responses (e.g. recalls following MAUDE).

        Args:
            name_a:   Leading signal (e.g. ``"maude"``).
            name_b:   Lagging signal (e.g. ``"recalls"``).
            max_lag:  Maximum lag to test (inclusive).
            method:   Correlation method.

        Returns:
            List of ``CorrelationResult`` at each lag (0..max_lag), sorted by lag.
        """
        results = []
        for lag in range(max_lag + 1):
            try:
                results.append(self.correlate(name_a, name_b, method=method, lag=lag))
            except ValueError:
                break  # not enough data for this lag
        return results

    def peak_lag(
        self,
        name_a:  str,
        name_b:  str,
        max_lag: int = 6,
        method:  str = "pearson",
    ) -> Optional[CorrelationResult]:
        """
        Return the ``CorrelationResult`` at the lag with the highest |coefficient|.

        Returns ``None`` if no valid correlation could be computed.
        """
        results = self.lag_analysis(name_a, name_b, max_lag=max_lag, method=method)
        if not results:
            return None
        return max(results, key=lambda r: abs(r.coefficient))

    # ── Composite risk scoring ────────────────────────────────────────────────

    def composite_risk_score(
        self,
        method:  str   = "pearson",
        weights: Optional[Dict[str, float]] = None,  # reserved for future weighted scoring
    ) -> float:
        """
        Compute a composite cross-signal risk score (0–1).

        Combines:
        - Mean absolute pairwise correlation (signal agreement)
        - Fraction of significant correlations (p < 0.05)

        Args:
            method:  Correlation method.
            weights: Optional ``{signal_name: weight}`` dict.  If provided,
                     weighted mean of each series' average correlation with others.

        Returns:
            Float in [0, 1] — higher means stronger cross-signal agreement.
        """
        results = self.correlate_all(method=method)
        if not results:
            return 0.0

        mean_abs = sum(abs(r.coefficient) for r in results) / len(results)
        sig_frac = sum(1 for r in results if r.significant) / len(results)
        score    = 0.6 * mean_abs + 0.4 * sig_frac
        return min(1.0, max(0.0, score))

    def summary(self, method: str = "pearson") -> str:
        """Return a human-readable correlation summary for debugging."""
        results = self.correlate_all(method=method)
        if not results:
            return "No correlations computed."
        lines = [f"Cross-signal correlation ({method})", "─" * 50]
        for r in results:
            sig = " *" if r.significant else ""
            lines.append(
                f"  {r.series_a} ↔ {r.series_b}: r={r.coefficient:+.3f} "
                f"(p={r.p_value:.4f}){sig}  [{r.strength}]"
            )
        score = self.composite_risk_score(method=method)
        lines.append(f"\nComposite risk score: {score:.3f}")
        return "\n".join(lines)


# ── Convenience function ──────────────────────────────────────────────────────

def correlate_signals(
    series:  List[SignalSeries],
    method:  str = "pearson",
) -> List[CorrelationResult]:
    """
    One-call convenience function for all pairwise correlations.

    Args:
        series: List of at least two ``SignalSeries`` objects.
        method: ``"pearson"``, ``"spearman"``, or ``"kendall"``.

    Returns:
        List of ``CorrelationResult`` sorted by |coefficient| descending.
    """
    return CrossSignalAnalyzer(series).correlate_all(method=method)
