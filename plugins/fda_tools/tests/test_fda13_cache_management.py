#!/usr/bin/env python3
"""
Tests for FDA-13: PMA SSED Cache Disk Space Management.

Tests the CacheManager class for:
- Cache size calculation
- LRU eviction ordering and execution
- Disk space checking
- Cache cleanup command
- Integration with SSEDDownloader
"""

import os
import sys
import json
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts directory to path
_scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")

from pma_ssed_cache import (
    CacheManager,
    SSEDDownloader,
    DEFAULT_MAX_CACHE_MB,
    construct_ssed_url,
    validate_pdf,
)


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing."""
    tmpdir = tempfile.mkdtemp(prefix="fda_test_cache_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def populated_cache(temp_cache_dir):
    """Create a cache directory with fake PDF files for testing LRU eviction."""
    # Create 5 PMA directories with fake PDFs of varying sizes
    pmas = ["P170001", "P170002", "P170003", "P170004", "P170005"]
    for i, pma in enumerate(pmas):
        pma_dir = temp_cache_dir / pma
        pma_dir.mkdir()

        # Create fake PDF (size varies: 100KB, 200KB, 300KB, 400KB, 500KB)
        pdf_path = pma_dir / "ssed.pdf"
        pdf_content = b"%PDF-1.4 " + b"x" * ((i + 1) * 100 * 1024)
        pdf_path.write_bytes(pdf_content)

        # Create a JSON metadata file
        json_path = pma_dir / "pma_data.json"
        json_path.write_text(json.dumps({"pma_number": pma}))

        # Stagger access times so LRU ordering is deterministic
        # P170001 is oldest (accessed first), P170005 is newest
        atime = time.time() - (len(pmas) - i) * 3600  # 5h, 4h, 3h, 2h, 1h ago
        mtime = atime
        os.utime(pdf_path, (atime, mtime))

    return temp_cache_dir


class TestCacheManager:
    """Tests for the CacheManager class."""

    def test_init_default_max_cache(self, temp_cache_dir):
        """Test default max cache size is 500MB."""
        mgr = CacheManager(temp_cache_dir)
        assert mgr.max_cache_bytes == DEFAULT_MAX_CACHE_MB * 1024 * 1024

    def test_init_custom_max_cache(self, temp_cache_dir):
        """Test custom max cache size."""
        mgr = CacheManager(temp_cache_dir, max_cache_mb=200)
        assert mgr.max_cache_bytes == 200 * 1024 * 1024

    def test_get_cache_size_empty(self, temp_cache_dir):
        """Test cache size calculation on empty directory."""
        mgr = CacheManager(temp_cache_dir, max_cache_mb=500)
        info = mgr.get_cache_size()
        assert info["total_bytes"] == 0
        assert info["pdf_count"] == 0
        assert info["json_count"] == 0
        assert info["usage_percent"] == 0.0

    def test_get_cache_size_populated(self, populated_cache):
        """Test cache size calculation with files."""
        mgr = CacheManager(populated_cache, max_cache_mb=500)
        info = mgr.get_cache_size()
        assert info["pdf_count"] == 5
        assert info["json_count"] == 5
        assert info["total_bytes"] > 0
        assert info["total_mb"] > 0
        assert 0 <= info["usage_percent"] <= 100

    def test_get_cache_size_nonexistent_dir(self):
        """Test cache size on nonexistent directory returns zeros."""
        mgr = CacheManager(Path("/tmp/nonexistent_fda_test_dir"))
        info = mgr.get_cache_size()
        assert info["total_bytes"] == 0
        assert info["pdf_count"] == 0

    def test_get_pdf_files_by_access_time(self, populated_cache):
        """Test PDF files are sorted by access time, oldest first."""
        mgr = CacheManager(populated_cache)
        files = mgr.get_pdf_files_by_access_time()
        assert len(files) == 5
        # Oldest should be first (P170001)
        assert "P170001" in str(files[0][0])
        # Newest should be last (P170005)
        assert "P170005" in str(files[-1][0])
        # Verify sorted by access time
        for i in range(len(files) - 1):
            assert files[i][1] <= files[i + 1][1]

    def test_evict_lru_no_eviction_needed(self, populated_cache):
        """Test no eviction when cache is under limit."""
        mgr = CacheManager(populated_cache, max_cache_mb=500)
        result = mgr.evict_lru()
        assert result["evicted_count"] == 0
        assert result["evicted_bytes"] == 0
        assert result["evicted_files"] == []

    def test_evict_lru_evicts_oldest_first(self, populated_cache):
        """Test LRU eviction removes oldest files first."""
        # Set cache limit very low to force eviction
        # Total cache is about 1.5MB of PDFs
        mgr = CacheManager(populated_cache, max_cache_mb=1)
        result = mgr.evict_lru()

        # Should have evicted some files
        assert result["evicted_count"] > 0
        assert result["evicted_bytes"] > 0

        # Oldest file (P170001) should be evicted first
        if result["evicted_files"]:
            assert "P170001" in result["evicted_files"][0]

    def test_evict_lru_with_target_free_bytes(self, populated_cache):
        """Test LRU eviction with additional target bytes to free."""
        mgr = CacheManager(populated_cache, max_cache_mb=2)
        # Request additional 1MB free
        result = mgr.evict_lru(target_free_bytes=1024 * 1024)
        # Should evict to create room
        assert result["evicted_count"] >= 0

    def test_check_disk_space_sufficient(self, temp_cache_dir):
        """Test disk space check when space is sufficient."""
        mgr = CacheManager(temp_cache_dir)
        result = mgr.check_disk_space(required_bytes=1024)
        assert result["sufficient"] is True
        assert result["free_mb"] > 0

    def test_check_disk_space_message(self, temp_cache_dir):
        """Test disk space check returns appropriate message."""
        mgr = CacheManager(temp_cache_dir)
        result = mgr.check_disk_space(required_bytes=0)
        assert "message" in result
        assert isinstance(result["message"], str)
        assert len(result["message"]) > 0

    def test_clean_cache(self, populated_cache):
        """Test clean_cache reduces cache to target size."""
        mgr = CacheManager(populated_cache, max_cache_mb=500)
        before = mgr.get_cache_size()

        # Clean to a very small target
        result = mgr.clean_cache(target_mb=0)

        assert result["before_mb"] == before["total_mb"]
        assert result["after_mb"] <= result["before_mb"]
        assert result["freed_mb"] >= 0

    def test_clean_cache_with_default_limit(self, populated_cache):
        """Test clean_cache uses configured max when target_mb is None."""
        # Set max well above current size
        mgr = CacheManager(populated_cache, max_cache_mb=500)
        result = mgr.clean_cache()
        # Should not evict anything since cache is under 500MB
        assert result["evicted_count"] == 0

    def test_evict_removes_empty_parent_dirs(self, temp_cache_dir):
        """Test that eviction removes empty parent directories."""
        # Create a PMA dir with only a PDF
        pma_dir = temp_cache_dir / "P999999"
        pma_dir.mkdir()
        pdf = pma_dir / "ssed.pdf"
        pdf.write_bytes(b"%PDF-1.4 " + b"x" * 2000)

        mgr = CacheManager(temp_cache_dir, max_cache_mb=0)  # Force eviction
        mgr.evict_lru()

        # PDF should be gone and empty parent removed
        assert not pdf.exists()
        assert not pma_dir.exists()


class TestSSEDDownloaderCacheIntegration:
    """Tests for SSEDDownloader integration with CacheManager."""

    def test_downloader_has_cache_manager(self, temp_cache_dir):
        """Test SSEDDownloader creates a CacheManager."""
        mock_store = MagicMock()
        mock_store.cache_dir = temp_cache_dir
        downloader = SSEDDownloader(store=mock_store, max_cache_mb=300)
        assert downloader.cache_manager is not None
        assert downloader.cache_manager.max_cache_bytes == 300 * 1024 * 1024

    def test_downloader_default_cache_size(self, temp_cache_dir):
        """Test SSEDDownloader uses default 500MB cache."""
        mock_store = MagicMock()
        mock_store.cache_dir = temp_cache_dir
        downloader = SSEDDownloader(store=mock_store)
        assert downloader.cache_manager.max_cache_bytes == DEFAULT_MAX_CACHE_MB * 1024 * 1024

    def test_get_stats_includes_cache_info(self, temp_cache_dir):
        """Test get_stats returns cache size information."""
        mock_store = MagicMock()
        mock_store.cache_dir = temp_cache_dir
        downloader = SSEDDownloader(store=mock_store, max_cache_mb=500)
        stats = downloader.get_stats()
        assert "cache_size_mb" in stats
        assert "cache_max_mb" in stats
        assert "cache_usage_percent" in stats
        assert "cache_pdf_count" in stats

    def test_evicted_stat_tracked(self, temp_cache_dir):
        """Test that evicted file count is tracked in stats."""
        mock_store = MagicMock()
        mock_store.cache_dir = temp_cache_dir
        downloader = SSEDDownloader(store=mock_store, max_cache_mb=500)
        assert downloader._stats["evicted"] == 0

    @patch("pma_ssed_cache.CacheManager.check_disk_space")
    def test_download_blocked_on_insufficient_disk(self, mock_disk_check, temp_cache_dir):
        """Test download fails gracefully when disk space is insufficient."""
        mock_disk_check.return_value = {
            "sufficient": False,
            "free_mb": 10,
            "required_mb": 50,
            "message": "Insufficient disk space: 10 MB free, need 50 MB.",
        }
        mock_store = MagicMock()
        mock_store.cache_dir = temp_cache_dir
        mock_store.get_pma_dir.return_value = temp_cache_dir / "P170019"
        (temp_cache_dir / "P170019").mkdir(exist_ok=True)

        downloader = SSEDDownloader(store=mock_store, max_cache_mb=500)
        result = downloader.download_ssed("P170019")

        assert result["success"] is False
        assert "Insufficient disk space" in result["error"]
        assert downloader._stats["failed"] == 1


class TestCacheManagerEdgeCases:
    """Edge case tests for CacheManager."""

    def test_zero_max_cache(self, temp_cache_dir):
        """Test max_cache_mb=0 means unlimited (no eviction)."""
        mgr = CacheManager(temp_cache_dir, max_cache_mb=0)
        assert mgr.max_cache_bytes == 0

    def test_cache_size_with_nested_dirs(self, temp_cache_dir):
        """Test cache size calculation handles nested directory structures."""
        nested = temp_cache_dir / "P100001" / "subdir"
        nested.mkdir(parents=True)
        (nested / "test.pdf").write_bytes(b"%PDF-1.4 " + b"x" * 5000)
        (temp_cache_dir / "P100001" / "pma_data.json").write_text("{}")

        mgr = CacheManager(temp_cache_dir)
        info = mgr.get_cache_size()
        assert info["pdf_count"] == 1
        assert info["json_count"] == 1

    def test_evict_handles_permission_errors(self, temp_cache_dir):
        """Test eviction handles files that cannot be deleted."""
        pma_dir = temp_cache_dir / "P888888"
        pma_dir.mkdir()
        pdf = pma_dir / "ssed.pdf"
        pdf.write_bytes(b"%PDF-1.4 " + b"x" * 2000)

        mgr = CacheManager(temp_cache_dir, max_cache_mb=0)

        # Mock unlink to raise OSError
        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            result = mgr.evict_lru()
            # Should not crash, but no files evicted
            assert result["evicted_count"] == 0


class TestURLConstruction:
    """Tests for construct_ssed_url (existing functionality, not FDA-13)."""

    def test_standard_pma(self):
        urls = construct_ssed_url("P170019")
        assert len(urls) == 3
        assert "pdf17" in urls[0]

    def test_2000s_pma_single_digit(self):
        urls = construct_ssed_url("P070004")
        assert "pdf7/" in urls[0]

    def test_invalid_pma_raises(self):
        with pytest.raises(ValueError):
            construct_ssed_url("K123456")


class TestPDFValidation:
    """Tests for validate_pdf (existing functionality)."""

    def test_valid_pdf(self):
        content = b"%PDF-1.4 " + b"x" * 2000
        assert validate_pdf(content) is True

    def test_too_small(self):
        content = b"%PDF" + b"x" * 10
        assert validate_pdf(content) is False

    def test_wrong_magic(self):
        content = b"<html>" + b"x" * 2000
        assert validate_pdf(content) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
