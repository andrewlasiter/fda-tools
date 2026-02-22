"""
FDA-236  [SIG-001] Signal Detector — Legacy Port
=================================================
Port of the original Windows-path signal analysis code into a clean, cross-platform
``pathlib.Path``-based script.  Detects anomalous MAUDE adverse event signals for
a given FDA product code using statistical and rule-based methods.

Usage
-----
python3 signal_detector.py --product-code DQY [OPTIONS]

  --product-code PC   FDA product code (required)
  --days N            Lookback window in days (default: 90)
  --threshold F       Z-score threshold to flag a signal (default: 2.0)
  --output PATH       Write JSON output to file (default: stdout)
  --cache-dir PATH    Directory for MAUDE cache (default: $FDA_DATA_DIR or ~/.fda-data)
  --no-cache          Bypass local cache, always fetch fresh data

Output JSON schema
------------------
{
  "product_code": "DQY",
  "window_days":  90,
  "generated_at": "2026-02-21T12:00:00Z",
  "total_events": 145,
  "signals": [
    {
      "date":        "2026-01-15",
      "count":       23,
      "severity":    "HIGH",
      "description": "Spike above 2.0σ threshold (baseline=4.2, z=3.8)",
      "event_types": ["MALFUNCTION", "INJURY"]
    }
  ],
  "baseline_stats": {
    "mean":   4.2,
    "std":    2.1,
    "median": 4.0,
    "n_days": 90
  }
}

Signal severity mapping
-----------------------
- CRITICAL: z-score >= 3.0 or absolute count >= 50 in single day
- HIGH:     z-score >= 2.0
- MEDIUM:   z-score >= 1.5
- LOW:      z-score >= 1.0

This is the SIG-001 foundation; CUSUM (FDA-237) and correlation (FDA-238)
build on top of this module.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_LOOKBACK_DAYS = 90
DEFAULT_Z_THRESHOLD   = 2.0
OPEN_FDA_MAUDE_URL    = "https://api.fda.gov/device/event.json"
REQUEST_TIMEOUT       = 30  # seconds

SEVERITY_THRESHOLDS = {
    "CRITICAL": 3.0,
    "HIGH":     2.0,
    "MEDIUM":   1.5,
    "LOW":      1.0,
}


# ── Data structures ────────────────────────────────────────────────────────────

from dataclasses import dataclass, field

@dataclass
class Signal:
    date:        str          # ISO date string
    count:       int
    severity:    str          # CRITICAL / HIGH / MEDIUM / LOW
    description: str
    event_types: list[str] = field(default_factory=list)
    z_score:     float = 0.0


@dataclass
class BaselineStats:
    mean:   float
    std:    float
    median: float
    n_days: int


# ── MAUDE data fetcher ─────────────────────────────────────────────────────────

def _cache_path(cache_dir: Path, product_code: str, days: int) -> Path:
    """Return the cache file path for this query."""
    return cache_dir / f"maude_{product_code.upper()}_{days}d.json"


def _fetch_maude_events(
    product_code: str,
    days:         int,
    cache_dir:    Path,
    use_cache:    bool = True,
) -> list[dict]:
    """
    Fetch MAUDE adverse event records from openFDA or local cache.

    Returns a list of raw event dicts from the openFDA API.
    Falls back to empty list on network failure (graceful degradation).
    """
    cache_file = _cache_path(cache_dir, product_code, days)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Cache hit
    if use_cache and cache_file.exists():
        age_hours = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 3600
        if age_hours < 24:
            logger.info("Cache hit: %s (%.1fh old)", cache_file.name, age_hours)
            data = json.loads(cache_file.read_text())
            return data.get("results", [])

    # Build date filter
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y%m%d")
    today  = date.today().strftime("%Y%m%d")

    logger.info("Fetching MAUDE events: product_code=%s, days=%d", product_code, days)

    try:
        from fda_tools.scripts.fda_http import create_session as _cs
        session = _cs(purpose="api")
        search_params = {
            "search": (
                f"device.openfda.device_name:{product_code.upper()}"
                f"+AND+date_received:[{cutoff}+TO+{today}]"
            ),
            "limit": "1000",
            "count": "date_received",   # count by day for efficient signal detection
        }
        resp = session.get(OPEN_FDA_MAUDE_URL, params=search_params, timeout=REQUEST_TIMEOUT)
        raw  = resp.json() if resp.status_code == 200 else {}

        events = raw.get("results", []) if isinstance(raw, dict) else []
        logger.info("Fetched %d event records", len(events))

        # Cache result
        import datetime as _dt
        cache_file.write_text(json.dumps({"results": events, "fetched_at": _dt.datetime.now(tz=_dt.timezone.utc).isoformat()}))
        return events

    except Exception as exc:
        logger.warning("MAUDE fetch failed (%s); using empty dataset", exc)
        return []


# ── Signal analysis ────────────────────────────────────────────────────────────

def _count_events_by_day(
    events: list[dict],
    days:   int,
) -> dict[str, int]:
    """
    Build a date → count mapping from MAUDE event records.

    Handles two openFDA response shapes:
    1. Individual event records with date_received
    2. Count-by-date aggregation (time: "YYYYMMDD", count: N)
    """
    counts: dict[str, int] = {}
    cutoff = date.today() - timedelta(days=days)

    for event in events:
        # Shape 1: aggregated count-by-date
        if "time" in event and "count" in event:
            try:
                raw = str(event["time"])
                d   = date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
                if d >= cutoff:
                    counts[d.isoformat()] = counts.get(d.isoformat(), 0) + int(event["count"])
            except (ValueError, TypeError, KeyError):
                pass
            continue

        # Shape 2: raw event record
        for date_field in ("date_received", "date_of_event", "date_report"):
            raw = event.get(date_field, "")
            if raw and len(raw) >= 8:
                try:
                    d = date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
                    if d >= cutoff:
                        counts[d.isoformat()] = counts.get(d.isoformat(), 0) + 1
                    break
                except (ValueError, TypeError):
                    pass

    return counts


def _extract_event_types(events: list[dict]) -> Counter:
    """Count event type categories (MALFUNCTION, INJURY, DEATH, OTHER)."""
    counter: Counter = Counter()
    for event in events:
        raw = event.get("event_type", event.get("adverse_event_flag", "OTHER"))
        counter[str(raw).upper()] += 1
    return counter


def _compute_baseline(counts: dict[str, int]) -> BaselineStats:
    """Compute mean/std/median from daily counts."""
    values = list(counts.values()) if counts else [0]
    if len(values) < 2:
        return BaselineStats(mean=float(values[0]), std=0.0, median=float(values[0]), n_days=len(values))
    return BaselineStats(
        mean   = statistics.mean(values),
        std    = statistics.stdev(values),
        median = statistics.median(values),
        n_days = len(values),
    )


def _z_score(value: float, mean: float, std: float) -> float:
    """Return z-score; returns 0.0 if std == 0."""
    return (value - mean) / std if std > 0 else 0.0


def _severity(z: float, abs_count: int) -> Optional[str]:
    """Return severity label or None if below LOW threshold."""
    if z >= SEVERITY_THRESHOLDS["CRITICAL"] or abs_count >= 50:
        return "CRITICAL"
    if z >= SEVERITY_THRESHOLDS["HIGH"]:
        return "HIGH"
    if z >= SEVERITY_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    if z >= SEVERITY_THRESHOLDS["LOW"]:
        return "LOW"
    return None


def detect_signals(
    product_code: str,
    days:         int           = DEFAULT_LOOKBACK_DAYS,
    threshold:    float         = DEFAULT_Z_THRESHOLD,
    cache_dir:    Optional[Path]= None,
    use_cache:    bool          = True,
) -> dict:
    """
    Run full signal detection pipeline for a product code.

    Returns the output JSON dict described in the module docstring.
    """
    if cache_dir is None:
        default_data_dir = os.getenv("FDA_DATA_DIR", str(Path.home() / ".fda-data"))
        cache_dir = Path(default_data_dir) / "maude_cache"

    events     = _fetch_maude_events(product_code, days, cache_dir, use_cache)
    day_counts = _count_events_by_day(events, days)
    event_types = _extract_event_types(events)
    baseline   = _compute_baseline(day_counts)
    top_types  = [t for t, _ in event_types.most_common(5)]

    raw_signals: list[Signal] = []

    for iso_date, count in sorted(day_counts.items()):
        z   = _z_score(float(count), baseline.mean, baseline.std)
        sev = _severity(z, count)

        if sev is None or z < threshold:
            continue

        desc = (
            f"Spike above {threshold}σ threshold "
            f"(baseline mean={baseline.mean:.1f}, z={z:.2f})"
        )
        raw_signals.append(Signal(
            date        = iso_date,
            count       = count,
            severity    = sev,
            description = desc,
            event_types = top_types[:3],
            z_score     = round(z, 3),
        ))

    now_utc = datetime.now(tz=__import__("datetime").timezone.utc)

    return {
        "product_code":  product_code.upper(),
        "window_days":   days,
        "generated_at":  now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_events":  sum(day_counts.values()),
        "signals": [
            {
                "date":        s.date,
                "count":       s.count,
                "severity":    s.severity,
                "description": s.description,
                "event_types": s.event_types,
                "z_score":     s.z_score,
            }
            for s in raw_signals
        ],
        "baseline_stats": {
            "mean":   round(baseline.mean, 3),
            "std":    round(baseline.std, 3),
            "median": float(baseline.median),
            "n_days": baseline.n_days,
        },
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="FDA MAUDE Signal Detector (FDA-236)"
    )
    parser.add_argument(
        "--product-code", required=True, type=str,
        help="FDA product code to analyze (e.g. DQY)"
    )
    parser.add_argument(
        "--days", type=int, default=DEFAULT_LOOKBACK_DAYS,
        help=f"Lookback window in days (default: {DEFAULT_LOOKBACK_DAYS})"
    )
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_Z_THRESHOLD,
        help=f"Z-score threshold to flag signal (default: {DEFAULT_Z_THRESHOLD})"
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write JSON output to file (default: stdout)"
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=None,
        help="MAUDE cache directory (default: ~/.fda-data/maude_cache)"
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Bypass cache; always fetch fresh data"
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    result = detect_signals(
        product_code = args.product_code,
        days         = args.days,
        threshold    = args.threshold,
        cache_dir    = args.cache_dir,
        use_cache    = not args.no_cache,
    )

    output_str = json.dumps(result, indent=2)

    if args.output:
        args.output.write_text(output_str)
        logger.info("Output written to %s", args.output)
    else:
        print(output_str)


if __name__ == "__main__":
    _cli()
