"""
Cache Manager — FDA-135
=======================

Centralised expiration-policy enforcement for all fda-510k-data cache
directories.  Each cache type has its own TTL drawn from config:

    openfda      ~/fda-510k-data/api_cache/          30 days
    literature   ~/fda-510k-data/pma_cache/external/pubmed/   90 days
    safety       ~/fda-510k-data/safety_cache/        7 days
    pma_ssed     ~/fda-510k-data/pma_ssed_cache/ (*/ dirs)    60 days
    clinicaltrials ~/fda-510k-data/pma_cache/external/clinicaltrials/  1 day

Usage
-----
    from fda_tools.lib.cache_manager import CacheManager

    mgr = CacheManager()
    stats = mgr.get_stats()
    stale = mgr.purge_stale()
    mgr.purge_all()

CLI entry point is ``fda_tools.scripts.cache_cli``.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CacheEntryInfo:
    """Metadata about a single cache file."""
    path: Path
    cache_type: str
    size_bytes: int
    cached_at: Optional[datetime]
    age_seconds: float
    ttl_seconds: int

    @property
    def is_stale(self) -> bool:
        return self.age_seconds > self.ttl_seconds

    @property
    def age_human(self) -> str:
        if self.age_seconds < 3600:
            return f"{int(self.age_seconds / 60)}m"
        if self.age_seconds < 86400:
            return f"{int(self.age_seconds / 3600)}h"
        return f"{int(self.age_seconds / 86400)}d"


@dataclass
class CacheTypeStats:
    """Aggregate statistics for one cache type."""
    cache_type: str
    ttl_seconds: int
    total_files: int = 0
    stale_files: int = 0
    total_size_bytes: int = 0
    stale_size_bytes: int = 0

    @property
    def ttl_human(self) -> str:
        s = self.ttl_seconds
        if s >= 86400:
            return f"{s // 86400}d"
        if s >= 3600:
            return f"{s // 3600}h"
        return f"{s}s"

    @property
    def total_size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)

    @property
    def stale_size_mb(self) -> float:
        return self.stale_size_bytes / (1024 * 1024)


@dataclass
class PurgeResult:
    """Result of a purge operation."""
    files_removed: int = 0
    bytes_freed: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def mb_freed(self) -> float:
        return self.bytes_freed / (1024 * 1024)


# ---------------------------------------------------------------------------
# Default TTLs (seconds) — overridden by config when available
# ---------------------------------------------------------------------------

_DEFAULT_TTLS: Dict[str, int] = {
    "openfda": 2592000,      # 30 days
    "literature": 7776000,   # 90 days
    "safety": 604800,        # 7 days
    "pma_ssed": 5184000,     # 60 days
    "clinicaltrials": 86400, # 1 day
}


# ---------------------------------------------------------------------------
# CacheManager
# ---------------------------------------------------------------------------


class CacheManager:
    """Enforce TTL-based expiration across all fda-510k-data cache locations.

    Args:
        base_dir: Base data directory. Default: ``~/fda-510k-data``.
        ttl_overrides: Per-type TTL overrides in seconds.  Keys must be one
            of ``openfda``, ``literature``, ``safety``, ``pma_ssed``,
            ``clinicaltrials``.
    """

    def __init__(
        self,
        base_dir: Optional[str] = None,
        ttl_overrides: Optional[Dict[str, int]] = None,
    ) -> None:
        self.base_dir = Path(base_dir or os.path.expanduser("~/fda-510k-data"))

        # Load per-type TTLs from config (best-effort)
        self._ttls: Dict[str, int] = dict(_DEFAULT_TTLS)
        try:
            from fda_tools.lib.config import get_config  # type: ignore
            cfg = get_config()
            mapping = {
                "openfda": "cache.ttl_openfda",
                "literature": "cache.ttl_literature",
                "safety": "cache.ttl_safety",
                "pma_ssed": "cache.ttl_pma_ssed",
                "clinicaltrials": "cache.ttl_clinicaltrials",
            }
            for cache_type, config_key in mapping.items():
                try:
                    val = cfg.get_int(config_key)
                    if val > 0:
                        self._ttls[cache_type] = val
                except Exception:
                    pass
        except Exception:
            pass

        # Apply caller overrides last
        if ttl_overrides:
            for k, v in ttl_overrides.items():
                if k in self._ttls:
                    self._ttls[k] = v

        # Map cache type → directory path(s)
        self._dirs: Dict[str, List[Path]] = {
            "openfda": [self.base_dir / "api_cache"],
            "literature": [self.base_dir / "pma_cache" / "external" / "pubmed"],
            "safety": [self.base_dir / "safety_cache"],
            "pma_ssed": [self.base_dir / "pma_ssed_cache"],
            "clinicaltrials": [
                self.base_dir / "pma_cache" / "external" / "clinicaltrials"
            ],
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, CacheTypeStats]:
        """Return per-type statistics across all cache directories.

        Returns:
            Dict mapping cache type name to :class:`CacheTypeStats`.
        """
        stats: Dict[str, CacheTypeStats] = {}
        for cache_type, dirs in self._dirs.items():
            ttl = self._ttls[cache_type]
            s = CacheTypeStats(cache_type=cache_type, ttl_seconds=ttl)
            for d in dirs:
                if not d.exists():
                    continue
                for entry in self._iter_json_files(d):
                    s.total_files += 1
                    s.total_size_bytes += entry.size_bytes
                    if entry.is_stale:
                        s.stale_files += 1
                        s.stale_size_bytes += entry.size_bytes
            stats[cache_type] = s
        return stats

    def purge_stale(self) -> PurgeResult:
        """Remove cache files whose age exceeds their type-specific TTL.

        Returns:
            :class:`PurgeResult` with counts and bytes freed.
        """
        result = PurgeResult()
        for cache_type, dirs in self._dirs.items():
            for d in dirs:
                if not d.exists():
                    continue
                for entry in self._iter_json_files(d):
                    if entry.is_stale:
                        try:
                            entry.path.unlink()
                            result.files_removed += 1
                            result.bytes_freed += entry.size_bytes
                        except OSError as e:
                            result.errors.append(f"{entry.path}: {e}")
        return result

    def purge_all(self) -> PurgeResult:
        """Remove ALL cache files regardless of age.

        Returns:
            :class:`PurgeResult` with counts and bytes freed.
        """
        result = PurgeResult()
        for cache_type, dirs in self._dirs.items():
            for d in dirs:
                if not d.exists():
                    continue
                for entry in self._iter_json_files(d):
                    try:
                        entry.path.unlink()
                        result.files_removed += 1
                        result.bytes_freed += entry.size_bytes
                    except OSError as e:
                        result.errors.append(f"{entry.path}: {e}")
        return result

    def get_ttls(self) -> Dict[str, int]:
        """Return a copy of the active TTL map (seconds per cache type)."""
        return dict(self._ttls)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_json_files(self, directory: Path):
        """Yield :class:`CacheEntryInfo` for every .json file under *directory*."""
        now = time.time()
        cache_type = self._dir_to_type(directory)
        ttl = self._ttls.get(cache_type, _DEFAULT_TTLS.get(cache_type, 604800))

        for json_file in directory.rglob("*.json"):
            if not json_file.is_file():
                continue
            size = json_file.stat().st_size
            cached_at: Optional[datetime] = None
            age = float("inf")

            try:
                with open(json_file) as f:
                    data = json.load(f)
                ts_str = data.get("_cached_at") or data.get("cached_at")
                if ts_str:
                    cached_at = datetime.fromisoformat(ts_str)
                    if cached_at.tzinfo is None:
                        cached_at = cached_at.replace(tzinfo=timezone.utc)
                    age = now - cached_at.timestamp()
            except (json.JSONDecodeError, OSError, ValueError):
                # Unreadable or malformed → treat as infinitely old
                pass

            yield CacheEntryInfo(
                path=json_file,
                cache_type=cache_type,
                size_bytes=size,
                cached_at=cached_at,
                age_seconds=age,
                ttl_seconds=ttl,
            )

    def _dir_to_type(self, directory: Path) -> str:
        """Map a directory path back to its cache type string."""
        for cache_type, dirs in self._dirs.items():
            if directory in dirs:
                return cache_type
        # Best-effort guess from directory name
        name = directory.name.lower()
        for cache_type in self._ttls:
            if cache_type in name:
                return cache_type
        return "openfda"
