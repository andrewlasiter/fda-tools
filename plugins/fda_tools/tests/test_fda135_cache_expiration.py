"""
Cache Expiration Policy Tests (FDA-135)
========================================

Verifies that CacheManager correctly:

  - Reports per-type statistics (file counts, sizes, stale counts)
  - Identifies stale entries according to per-type TTLs
  - Purges stale-only entries (purge_stale)
  - Purges all entries regardless of age (purge_all)
  - Handles missing/empty cache directories gracefully
  - Returns TTL configuration (get_ttls)
  - CLI flags --stats, --purge-stale, --purge-all, --list-ttls exit 0

Test count: 15
Target: pytest plugins/fda_tools/tests/test_fda135_cache_expiration.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from fda_tools.lib.cache_manager import CacheManager, CacheTypeStats, PurgeResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_cache_file(directory: Path, name: str, age_seconds: float) -> Path:
    """Write a JSON cache file whose _cached_at timestamp is age_seconds old."""
    directory.mkdir(parents=True, exist_ok=True)
    cached_at = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    path = directory / f"{name}.json"
    path.write_text(json.dumps({
        "_cached_at": cached_at.isoformat(),
        "source": "test",
        "data": {"key": "value"},
    }))
    return path


def _make_manager(tmp_path: Path, ttl_overrides: dict | None = None) -> CacheManager:
    """Create a CacheManager pointing at a temp base dir."""
    return CacheManager(base_dir=str(tmp_path), ttl_overrides=ttl_overrides)


# ---------------------------------------------------------------------------
# TestCacheManagerStats
# ---------------------------------------------------------------------------


class TestCacheManagerStats:
    """Tests for CacheManager.get_stats()."""

    def test_empty_cache_dirs_produce_zero_stats(self, tmp_path):
        mgr = _make_manager(tmp_path)
        stats = mgr.get_stats()
        for ct, s in stats.items():
            assert s.total_files == 0
            assert s.stale_files == 0
            assert s.total_size_bytes == 0

    def test_fresh_file_not_counted_as_stale(self, tmp_path):
        mgr = _make_manager(tmp_path, ttl_overrides={"openfda": 3600})
        api_dir = tmp_path / "api_cache"
        _write_cache_file(api_dir, "recent", age_seconds=60)  # 1 minute old

        stats = mgr.get_stats()
        s = stats["openfda"]
        assert s.total_files == 1
        assert s.stale_files == 0

    def test_expired_file_counted_as_stale(self, tmp_path):
        mgr = _make_manager(tmp_path, ttl_overrides={"openfda": 3600})
        api_dir = tmp_path / "api_cache"
        _write_cache_file(api_dir, "old", age_seconds=7200)  # 2 hours old > 1h TTL

        stats = mgr.get_stats()
        s = stats["openfda"]
        assert s.total_files == 1
        assert s.stale_files == 1

    def test_mixed_fresh_and_stale_counted_correctly(self, tmp_path):
        ttl = 3600  # 1 hour
        mgr = _make_manager(tmp_path, ttl_overrides={"openfda": ttl})
        api_dir = tmp_path / "api_cache"
        _write_cache_file(api_dir, "fresh1", age_seconds=1800)  # 30 min — fresh
        _write_cache_file(api_dir, "fresh2", age_seconds=3000)  # 50 min — fresh
        _write_cache_file(api_dir, "stale1", age_seconds=7200)  # 2 h — stale
        _write_cache_file(api_dir, "stale2", age_seconds=86400) # 1 day — stale

        s = mgr.get_stats()["openfda"]
        assert s.total_files == 4
        assert s.stale_files == 2

    def test_stats_include_all_cache_types(self, tmp_path):
        mgr = _make_manager(tmp_path)
        stats = mgr.get_stats()
        expected_types = {"openfda", "literature", "safety", "pma_ssed", "clinicaltrials"}
        assert set(stats.keys()) == expected_types

    def test_stats_ttl_matches_override(self, tmp_path):
        mgr = _make_manager(tmp_path, ttl_overrides={"safety": 900})
        assert mgr.get_stats()["safety"].ttl_seconds == 900


# ---------------------------------------------------------------------------
# TestPurgeStale
# ---------------------------------------------------------------------------


class TestPurgeStale:
    """Tests for CacheManager.purge_stale()."""

    def test_purge_stale_removes_expired_files(self, tmp_path):
        mgr = _make_manager(tmp_path, ttl_overrides={"openfda": 3600})
        api_dir = tmp_path / "api_cache"
        stale = _write_cache_file(api_dir, "stale", age_seconds=7200)
        fresh = _write_cache_file(api_dir, "fresh", age_seconds=60)

        result = mgr.purge_stale()
        assert result.files_removed == 1
        assert result.bytes_freed > 0
        assert not stale.exists()
        assert fresh.exists()

    def test_purge_stale_no_errors_on_empty_dir(self, tmp_path):
        mgr = _make_manager(tmp_path)
        result = mgr.purge_stale()
        assert result.files_removed == 0
        assert result.errors == []

    def test_purge_stale_returns_bytes_freed(self, tmp_path):
        mgr = _make_manager(tmp_path, ttl_overrides={"openfda": 3600})
        api_dir = tmp_path / "api_cache"
        stale = _write_cache_file(api_dir, "stale", age_seconds=7200)
        expected_size = stale.stat().st_size

        result = mgr.purge_stale()
        assert result.bytes_freed == expected_size


# ---------------------------------------------------------------------------
# TestPurgeAll
# ---------------------------------------------------------------------------


class TestPurgeAll:
    """Tests for CacheManager.purge_all()."""

    def test_purge_all_removes_fresh_and_stale(self, tmp_path):
        mgr = _make_manager(tmp_path, ttl_overrides={"openfda": 3600})
        api_dir = tmp_path / "api_cache"
        fresh = _write_cache_file(api_dir, "fresh", age_seconds=60)
        stale = _write_cache_file(api_dir, "stale", age_seconds=7200)

        result = mgr.purge_all()
        assert result.files_removed == 2
        assert not fresh.exists()
        assert not stale.exists()

    def test_purge_all_no_errors_on_empty(self, tmp_path):
        mgr = _make_manager(tmp_path)
        result = mgr.purge_all()
        assert result.files_removed == 0
        assert result.errors == []


# ---------------------------------------------------------------------------
# TestDefaultTTLs
# ---------------------------------------------------------------------------


class TestDefaultTTLs:
    """Tests for TTL configuration."""

    def test_get_ttls_returns_all_types(self, tmp_path):
        mgr = _make_manager(tmp_path)
        ttls = mgr.get_ttls()
        expected = {"openfda", "literature", "safety", "pma_ssed", "clinicaltrials"}
        assert set(ttls.keys()) == expected

    def test_default_openfda_ttl_is_30_days(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.get_ttls()["openfda"] == 30 * 24 * 3600

    def test_default_literature_ttl_is_90_days(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.get_ttls()["literature"] == 90 * 24 * 3600

    def test_default_safety_ttl_is_7_days(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.get_ttls()["safety"] == 7 * 24 * 3600


# ---------------------------------------------------------------------------
# TestCacheCLI
# ---------------------------------------------------------------------------


class TestCacheCLI:
    """Tests for the cache_cli CLI entry point."""

    def _run(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "fda_tools.scripts.cache_cli", *args],
            capture_output=True,
            text=True,
        )

    def test_stats_exits_zero(self, tmp_path):
        proc = self._run("--stats", "--base-dir", str(tmp_path))
        assert proc.returncode == 0

    def test_stats_json_output_parseable(self, tmp_path):
        proc = self._run("--stats", "--base-dir", str(tmp_path), "--json")
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert isinstance(data, dict)
        assert "openfda" in data

    def test_purge_stale_exits_zero(self, tmp_path):
        proc = self._run("--purge-stale", "--base-dir", str(tmp_path))
        assert proc.returncode == 0

    def test_purge_all_exits_zero(self, tmp_path):
        proc = self._run("--purge-all", "--base-dir", str(tmp_path))
        assert proc.returncode == 0

    def test_list_ttls_json_has_all_types(self, tmp_path):
        proc = self._run("--list-ttls", "--base-dir", str(tmp_path), "--json")
        assert proc.returncode == 0
        ttls = json.loads(proc.stdout)
        assert set(ttls.keys()) == {
            "openfda", "literature", "safety", "pma_ssed", "clinicaltrials"
        }
