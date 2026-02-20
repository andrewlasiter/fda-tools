#!/usr/bin/env python3
"""
PMA SSED Batch Downloader -- Downloads and validates SSED PDFs from FDA servers.

Extends the URL construction patterns from pma_prototype.py with robust batch
download orchestration, rate limiting, error recovery, progress tracking,
resume capability, and disk space management.

Key features:
    - TICKET-002 validated URL patterns (single-digit folders for 2000s PMAs)
    - Case-variation fallback (uppercase B, lowercase b, all lowercase)
    - User-Agent header required by FDA servers
    - 500ms rate limiting between requests (2 req/sec)
    - Automatic retry with exponential backoff (3 attempts)
    - Resume capability (skips already downloaded)
    - PDF validation (%PDF magic bytes)
    - Progress tracking with ETA
    - Configurable max cache size with LRU eviction (FDA-13)
    - Disk space check before PDF download (FDA-13)
    - Cache cleanup command (FDA-13)

Usage:
    from pma_ssed_cache import SSEDDownloader

    downloader = SSEDDownloader(store, max_cache_mb=500)
    result = downloader.download_ssed("P170019")
    results = downloader.download_batch(["P170019", "P200024", "P070004"])

    # CLI usage:
    python3 pma_ssed_cache.py --pma P170019
    python3 pma_ssed_cache.py --list P170019,P200024,P070004
    python3 pma_ssed_cache.py --product-code NMH --year 2024
    python3 pma_ssed_cache.py --clean-cache
    python3 pma_ssed_cache.py --clean-cache --max-cache-mb 200
    python3 pma_ssed_cache.py --show-manifest
"""

import argparse
import logging
import os
import shutil
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Import sibling modules
from pma_data_store import PMADataStore

# Module logger
logger = logging.getLogger(__name__)

# HTTP headers required for FDA server access
# FDA servers block requests without a proper User-Agent header.
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Default rate limit: 500ms between requests (2 req/sec)
DEFAULT_RATE_LIMIT = 0.5

# Max retries per download
MAX_RETRIES = 3

# Base backoff in seconds for retry
BASE_BACKOFF = 1.0

# Minimum valid PDF size in bytes (reject tiny error pages)
MIN_PDF_SIZE = 1000

# PDF magic bytes
PDF_MAGIC = b"%PDF"

# HTTP timeout in seconds
HTTP_TIMEOUT = 30

# Default max cache size in MB (FDA-13)
DEFAULT_MAX_CACHE_MB = 500

# Minimum free disk space required before download in MB (FDA-13)
MIN_FREE_DISK_MB = 50


def construct_ssed_url(pma_number: str) -> List[str]:
    """Construct candidate SSED PDF URLs from a PMA number.

    TICKET-002 validated: 2000s PMAs (P0X####) use single-digit folder names
    (pdf7 not pdf07). Pre-2000 PMAs are not digitized.

    Args:
        pma_number: PMA number (e.g., 'P170019', 'P070004', 'P170019S029')

    Returns:
        List of candidate URLs to try, ordered by likelihood:
            1. {PMA}B.pdf (uppercase B) - most common
            2. {PMA}b.pdf (lowercase b)
            3. {pma_lower}b.pdf (all lowercase)

    Raises:
        ValueError: If pma_number doesn't start with 'P'.
    """
    pma = pma_number.upper()
    if not pma.startswith("P"):
        raise ValueError(f"Invalid PMA number format: {pma_number} (must start with 'P')")

    year = pma[1:3]

    # TICKET-002 critical fix: Remove leading zero for 2000s PMAs.
    # FDA uses single-digit folder names: pdf7, pdf5, pdf3 (not pdf07, pdf05, pdf03)
    if year.startswith("0") and len(year) == 2:
        year = year[1]  # "07" -> "7", "05" -> "5", "03" -> "3"

    base_url = f"https://www.accessdata.fda.gov/cdrh_docs/pdf{year}/"

    return [
        f"{base_url}{pma}B.pdf",              # Standard uppercase B
        f"{base_url}{pma}b.pdf",              # Lowercase b
        f"{base_url}{pma.lower()}b.pdf",      # All lowercase
    ]


def validate_pdf(content: bytes) -> bool:
    """Validate that downloaded content is a valid PDF.

    Args:
        content: Downloaded file content as bytes.

    Returns:
        True if content appears to be a valid PDF.
    """
    if len(content) < MIN_PDF_SIZE:
        return False
    if not content[:4] == PDF_MAGIC:
        return False
    return True


class CacheManager:
    """Manages SSED PDF cache disk space with LRU eviction (FDA-13).

    Tracks cache size, enforces configurable limits, and provides LRU
    eviction when the cache exceeds the configured maximum size.

    The LRU ordering is determined by file access time (atime) or, if
    unavailable, modification time (mtime).
    """

    def __init__(self, cache_dir: Path, max_cache_mb: int = DEFAULT_MAX_CACHE_MB):
        """Initialize cache manager.

        Args:
            cache_dir: Root directory of the PMA cache.
            max_cache_mb: Maximum cache size in megabytes (default: 500).
        """
        self.cache_dir = cache_dir
        self.max_cache_bytes = max_cache_mb * 1024 * 1024

    def get_cache_size(self) -> Dict[str, Any]:
        """Calculate current cache size and file inventory.

        Returns:
            Dictionary with:
                - total_bytes: Total cache size in bytes
                - total_mb: Total cache size in MB (rounded)
                - pdf_count: Number of PDF files
                - pdf_bytes: Total size of PDF files
                - json_count: Number of JSON files
                - json_bytes: Total size of JSON files
                - other_count: Number of other files
                - other_bytes: Total size of other files
                - max_cache_mb: Configured max cache size
                - usage_percent: Percentage of max cache used
        """
        total_bytes = 0
        pdf_count = 0
        pdf_bytes = 0
        json_count = 0
        json_bytes = 0
        other_count = 0
        other_bytes = 0

        if not self.cache_dir.exists():
            return {
                "total_bytes": 0, "total_mb": 0.0,
                "pdf_count": 0, "pdf_bytes": 0,
                "json_count": 0, "json_bytes": 0,
                "other_count": 0, "other_bytes": 0,
                "max_cache_mb": self.max_cache_bytes // (1024 * 1024),
                "usage_percent": 0.0,
            }

        for dirpath, _dirnames, filenames in os.walk(self.cache_dir):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    fsize = os.path.getsize(fpath)
                except OSError:
                    continue
                total_bytes += fsize
                if fname.endswith(".pdf"):
                    pdf_count += 1
                    pdf_bytes += fsize
                elif fname.endswith(".json"):
                    json_count += 1
                    json_bytes += fsize
                else:
                    other_count += 1
                    other_bytes += fsize

        max_mb = self.max_cache_bytes / (1024 * 1024)
        total_mb = total_bytes / (1024 * 1024)
        usage_pct = (total_bytes / self.max_cache_bytes * 100) if self.max_cache_bytes > 0 else 0.0

        return {
            "total_bytes": total_bytes,
            "total_mb": round(total_mb, 2),
            "pdf_count": pdf_count,
            "pdf_bytes": pdf_bytes,
            "json_count": json_count,
            "json_bytes": json_bytes,
            "other_count": other_count,
            "other_bytes": other_bytes,
            "max_cache_mb": round(max_mb, 2),
            "usage_percent": round(usage_pct, 1),
        }

    def get_pdf_files_by_access_time(self) -> List[Tuple[Path, float, int]]:
        """Get all cached PDF files sorted by last access time (oldest first).

        Returns:
            List of (path, access_time, size_bytes) tuples sorted by access_time ascending.
        """
        pdf_files = []
        if not self.cache_dir.exists():
            return pdf_files

        for pdf_path in self.cache_dir.rglob("*.pdf"):
            try:
                stat = pdf_path.stat()
                # Prefer atime; fall back to mtime if atime is not meaningful
                access_time = stat.st_atime if stat.st_atime > 0 else stat.st_mtime
                pdf_files.append((pdf_path, access_time, stat.st_size))
            except OSError:
                continue

        # Sort by access time, oldest first (LRU candidates first)
        pdf_files.sort(key=lambda x: x[1])
        return pdf_files

    def evict_lru(self, target_free_bytes: int = 0) -> Dict[str, Any]:
        """Evict least-recently-used PDF files until cache is within limits.

        If target_free_bytes is specified, evict enough to free that many bytes
        in addition to getting under the max cache limit.

        Args:
            target_free_bytes: Additional bytes to free beyond the limit (e.g.,
                for an upcoming download). Default: 0.

        Returns:
            Dictionary with eviction results:
                - evicted_count: Number of files evicted
                - evicted_bytes: Total bytes freed
                - evicted_files: List of evicted file paths
        """
        cache_info = self.get_cache_size()
        current_bytes = cache_info["total_bytes"]
        threshold = self.max_cache_bytes - target_free_bytes

        result = {
            "evicted_count": 0,
            "evicted_bytes": 0,
            "evicted_files": [],
        }

        if current_bytes <= threshold:
            return result

        bytes_to_free = current_bytes - threshold
        pdf_files = self.get_pdf_files_by_access_time()

        freed = 0
        for pdf_path, _atime, size in pdf_files:
            if freed >= bytes_to_free:
                break

            try:
                pdf_path.unlink()
                freed += size
                result["evicted_count"] += 1
                result["evicted_bytes"] += size
                result["evicted_files"].append(str(pdf_path))
                logger.info("LRU evicted: %s (%d KB)", pdf_path.name, size // 1024)

                # Also remove parent directory if it is now empty
                parent = pdf_path.parent
                if parent != self.cache_dir and parent.exists():
                    remaining = list(parent.iterdir())
                    if not remaining:
                        parent.rmdir()
            except OSError as e:
                logger.warning("Failed to evict %s: %s", pdf_path, e)

        logger.info(
            "LRU eviction complete: evicted %d files, freed %.2f MB",
            result["evicted_count"],
            result["evicted_bytes"] / (1024 * 1024),
        )
        return result

    def check_disk_space(self, required_bytes: int = 0) -> Dict[str, Any]:
        """Check available disk space before a download.

        Args:
            required_bytes: Estimated bytes needed for the download.

        Returns:
            Dictionary with:
                - sufficient: True if enough space is available
                - free_mb: Free disk space in MB
                - required_mb: Required space in MB
                - message: Human-readable status message
        """
        try:
            stat = shutil.disk_usage(self.cache_dir)
            free_bytes = stat.free
        except OSError:
            # Cannot determine disk space; assume sufficient
            return {
                "sufficient": True,
                "free_mb": -1,
                "required_mb": round(required_bytes / (1024 * 1024), 2),
                "message": "Could not determine disk space; proceeding with download.",
            }

        free_mb = free_bytes / (1024 * 1024)
        required_mb = required_bytes / (1024 * 1024)
        min_needed = max(required_mb, MIN_FREE_DISK_MB)
        sufficient = free_mb >= min_needed

        if sufficient:
            msg = f"Disk space OK: {free_mb:.1f} MB free (need {min_needed:.1f} MB)"
        else:
            msg = (
                f"Insufficient disk space: {free_mb:.1f} MB free, "
                f"need at least {min_needed:.1f} MB. "
                f"Run --clean-cache to free space."
            )

        return {
            "sufficient": sufficient,
            "free_mb": round(free_mb, 2),
            "required_mb": round(required_mb, 2),
            "message": msg,
        }

    def clean_cache(self, target_mb: Optional[int] = None) -> Dict[str, Any]:
        """Clean the cache by evicting LRU files to reach a target size.

        If target_mb is None, evicts down to the configured max_cache_mb.
        If target_mb is specified, evicts down to that size.

        Args:
            target_mb: Target cache size in MB. None uses configured max.

        Returns:
            Dictionary with cleanup results including before/after sizes.
        """
        before = self.get_cache_size()

        if target_mb is not None:
            original_max = self.max_cache_bytes
            self.max_cache_bytes = target_mb * 1024 * 1024
            eviction = self.evict_lru()
            self.max_cache_bytes = original_max
        else:
            eviction = self.evict_lru()

        after = self.get_cache_size()

        return {
            "before_mb": before["total_mb"],
            "after_mb": after["total_mb"],
            "freed_mb": round(before["total_mb"] - after["total_mb"], 2),
            "evicted_count": eviction["evicted_count"],
            "evicted_files": eviction["evicted_files"],
            "max_cache_mb": self.max_cache_bytes / (1024 * 1024),
        }


class SSEDDownloader:
    """SSED PDF batch downloader with progress tracking and error recovery.

    Downloads Summary of Safety and Effectiveness Data (SSED) PDFs from
    FDA servers with rate limiting, retry logic, resume capability, and
    disk space management (FDA-13).
    """

    def __init__(self, store: Optional[PMADataStore] = None,
                 rate_limit: float = DEFAULT_RATE_LIMIT,
                 max_cache_mb: int = DEFAULT_MAX_CACHE_MB):
        """Initialize SSED downloader.

        Args:
            store: PMADataStore for caching and manifest updates.
            rate_limit: Seconds between requests (default 0.5 = 2 req/sec).
            max_cache_mb: Maximum cache size in MB (default 500). Set to 0 for unlimited.
        """
        self.store = store or PMADataStore()
        self.rate_limit = rate_limit
        self.cache_manager = CacheManager(self.store.cache_dir, max_cache_mb=max_cache_mb)
        self._stats = {
            "attempted": 0,
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "total_bytes": 0,
            "start_time": None,
            "evicted": 0,
        }

    def download_ssed(self, pma_number: str, force: bool = False) -> Dict:
        """Download SSED PDF for a single PMA number.

        Tries multiple URL patterns with case-variation fallback.
        Validates downloaded content as a real PDF (not error page).

        Args:
            pma_number: PMA number (e.g., 'P170019')
            force: Re-download even if already cached.

        Returns:
            Dict with download result:
                {
                    "pma_number": "P170019",
                    "success": True,
                    "filepath": "/path/to/ssed.pdf",
                    "url": "https://...",
                    "file_size_kb": 1234,
                    "error": None,
                    "attempts": 1,
                    "skipped": False
                }
        """
        pma_key = pma_number.upper()
        result = {
            "pma_number": pma_key,
            "success": False,
            "filepath": None,
            "url": None,
            "file_size_kb": 0,
            "error": None,
            "attempts": 0,
            "skipped": False,
        }

        self._stats["attempted"] += 1

        # Check if already downloaded (skip unless force)
        pma_dir = self.store.get_pma_dir(pma_key)
        pdf_path = pma_dir / "ssed.pdf"

        if not force and pdf_path.exists() and pdf_path.stat().st_size > MIN_PDF_SIZE:
            result["success"] = True
            result["filepath"] = str(pdf_path)
            result["file_size_kb"] = pdf_path.stat().st_size // 1024
            result["skipped"] = True
            self._stats["skipped"] += 1
            return result

        # FDA-13: Check disk space before download
        disk_check = self.cache_manager.check_disk_space(required_bytes=5 * 1024 * 1024)  # Assume ~5MB per PDF
        if not disk_check["sufficient"]:
            result["error"] = disk_check["message"]
            self._stats["failed"] += 1
            logger.warning("Skipping %s: %s", pma_key, disk_check["message"])
            return result

        # FDA-13: Enforce cache size limit with LRU eviction
        if self.cache_manager.max_cache_bytes > 0:
            eviction = self.cache_manager.evict_lru(target_free_bytes=5 * 1024 * 1024)
            if eviction["evicted_count"] > 0:
                self._stats["evicted"] += eviction["evicted_count"]
                logger.info(
                    "Evicted %d LRU files (%.2f MB) to make room for %s",
                    eviction["evicted_count"],
                    eviction["evicted_bytes"] / (1024 * 1024),
                    pma_key,
                )

        # Get candidate URLs
        try:
            candidate_urls = construct_ssed_url(pma_key)
        except ValueError as e:
            result["error"] = str(e)
            self._stats["failed"] += 1
            return result

        # Try each URL pattern with retry logic
        for url in candidate_urls:
            download_result = self._try_download(url)
            result["attempts"] += download_result["attempts"]
            result["url"] = url

            if download_result["success"]:
                # Save PDF to cache
                try:
                    with open(pdf_path, "wb") as f:
                        f.write(download_result["content"])

                    result["success"] = True
                    result["filepath"] = str(pdf_path)
                    result["file_size_kb"] = len(download_result["content"]) // 1024

                    # Update data store manifest
                    self.store.mark_ssed_downloaded(
                        pma_key,
                        filepath=str(pdf_path),
                        file_size_kb=result["file_size_kb"],
                        url=url,
                    )

                    self._stats["downloaded"] += 1
                    self._stats["total_bytes"] += len(download_result["content"])
                    return result
                except OSError as e:
                    result["error"] = f"File write error: {e}"
                    self._stats["failed"] += 1
                    return result

            # Rate limiting between URL attempts
            time.sleep(self.rate_limit)

        # All patterns exhausted
        if result["error"] is None:
            result["error"] = f"HTTP 404 on all {len(candidate_urls)} URL patterns"
        self._stats["failed"] += 1
        return result

    def _try_download(self, url: str) -> Dict:
        """Attempt to download from a URL with retry and exponential backoff.

        Args:
            url: URL to download from.

        Returns:
            Dict with success, content, attempts, error.
        """
        result = {"success": False, "content": None, "attempts": 0, "error": None}

        # FDA-107: Create SSL context with certificate verification enabled
        ssl_context = ssl.create_default_context()

        for attempt in range(MAX_RETRIES):
            result["attempts"] += 1
            try:
                req = urllib.request.Request(url, headers=HTTP_HEADERS)
                with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT, context=ssl_context) as resp:
                    content = resp.read()

                if validate_pdf(content):
                    result["success"] = True
                    result["content"] = content
                    return result
                else:
                    result["error"] = f"Invalid PDF content from {url} ({len(content)} bytes)"
                    return result  # Don't retry invalid content

            except urllib.error.HTTPError as e:
                if e.code == 404:
                    result["error"] = f"HTTP 404: {url}"
                    return result  # Don't retry 404s
                elif e.code == 429:
                    wait = BASE_BACKOFF * (2 ** attempt) * 2
                    time.sleep(wait)
                    result["error"] = f"HTTP 429 (rate limited)"
                elif e.code >= 500:
                    wait = BASE_BACKOFF * (2 ** attempt)
                    time.sleep(wait)
                    result["error"] = f"HTTP {e.code}"
                else:
                    result["error"] = f"HTTP {e.code}: {e.reason}"
                    return result  # Don't retry client errors

            except urllib.error.URLError as e:
                wait = BASE_BACKOFF * (2 ** attempt)
                time.sleep(wait)
                result["error"] = f"URL error: {e.reason}"

            except Exception as e:
                wait = BASE_BACKOFF * (2 ** attempt)
                time.sleep(wait)
                result["error"] = f"Download error: {e}"

        return result

    def download_batch(self, pma_numbers: List[str], force: bool = False,
                       progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Download SSEDs for multiple PMA numbers with progress tracking.

        Args:
            pma_numbers: List of PMA numbers to download.
            force: Re-download even if already cached.
            progress_callback: Optional callback(current, total, result_dict).

        Returns:
            List of download result dicts (one per PMA).
        """
        self._stats["start_time"] = time.time()
        total = len(pma_numbers)
        results = []

        for i, pma_number in enumerate(pma_numbers):
            result = self.download_ssed(pma_number, force=force)
            results.append(result)

            # Progress callback
            if progress_callback:
                progress_callback(i + 1, total, result)
            else:
                self._print_progress(i + 1, total, result)

            # Rate limiting between PMAs (in addition to per-attempt limiting)
            if i < total - 1:
                time.sleep(self.rate_limit)

        return results

    def _print_progress(self, current: int, total: int, result: Dict) -> None:
        """Print default progress output.

        Args:
            current: Current item number.
            total: Total items.
            result: Download result dict.
        """
        pma = result["pma_number"]
        if result["skipped"]:
            status = f"SKIP ({result['file_size_kb']} KB cached)"
        elif result["success"]:
            status = f"OK ({result['file_size_kb']} KB, {result['attempts']} attempt(s))"
        else:
            status = f"FAIL ({result['error']})"

        elapsed = time.time() - (self._stats["start_time"] or time.time())
        if current > 0 and elapsed > 0:
            rate = current / elapsed
            remaining = (total - current) / rate if rate > 0 else 0
            eta = f"ETA {int(remaining)}s"
        else:
            eta = ""

        print(f"[{current}/{total}] {pma}: {status} {eta}")

    def get_stats(self) -> Dict:
        """Get download session statistics.

        Returns:
            Dictionary with attempted, downloaded, skipped, failed, evicted counts
            and cache size information.
        """
        elapsed = 0
        if self._stats["start_time"]:
            elapsed = time.time() - self._stats["start_time"]

        stats = {
            "attempted": self._stats["attempted"],
            "downloaded": self._stats["downloaded"],
            "skipped": self._stats["skipped"],
            "failed": self._stats["failed"],
            "evicted": self._stats["evicted"],
            "total_bytes": self._stats["total_bytes"],
            "total_mb": round(self._stats["total_bytes"] / (1024 * 1024), 2),
            "elapsed_seconds": round(elapsed, 1),
            "download_rate_mbps": round(
                (self._stats["total_bytes"] / (1024 * 1024)) / elapsed, 3
            ) if elapsed > 0 else 0,
        }

        # FDA-13: Include cache size info
        cache_info = self.cache_manager.get_cache_size()
        stats["cache_size_mb"] = cache_info["total_mb"]
        stats["cache_max_mb"] = cache_info["max_cache_mb"]
        stats["cache_usage_percent"] = cache_info["usage_percent"]
        stats["cache_pdf_count"] = cache_info["pdf_count"]

        return stats

    def print_summary(self) -> None:
        """Print download session summary."""
        stats = self.get_stats()
        print()
        print("=" * 60)
        print("SSED Download Summary")
        print("=" * 60)
        print(f"  Attempted:  {stats['attempted']}")
        print(f"  Downloaded: {stats['downloaded']}")
        print(f"  Skipped:    {stats['skipped']} (already cached)")
        print(f"  Failed:     {stats['failed']}")
        if stats["evicted"] > 0:
            print(f"  Evicted:    {stats['evicted']} (LRU cache management)")
        print(f"  Total size: {stats['total_mb']} MB")
        print(f"  Elapsed:    {stats['elapsed_seconds']}s")
        if stats["download_rate_mbps"] > 0:
            print(f"  Rate:       {stats['download_rate_mbps']} MB/s")
        success_rate = (
            (stats["downloaded"] + stats["skipped"]) / stats["attempted"] * 100
            if stats["attempted"] > 0 else 0
        )
        print(f"  Success:    {success_rate:.1f}%")
        print("-" * 60)
        print(f"  Cache:      {stats['cache_size_mb']} MB / {stats['cache_max_mb']} MB "
              f"({stats['cache_usage_percent']}% used, {stats['cache_pdf_count']} PDFs)")
        print("=" * 60)


# ------------------------------------------------------------------
# CLI interface
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PMA SSED Batch Downloader with Cache Management (FDA-13)"
    )
    parser.add_argument("--pma", help="Single PMA number to download")
    parser.add_argument("--list", dest="pma_list",
                        help="Comma-separated PMA numbers to download")
    parser.add_argument("--product-code", dest="product_code",
                        help="Download SSEDs for all PMAs with this product code")
    parser.add_argument("--year", type=int, help="Filter by approval year (with --product-code)")
    parser.add_argument("--force", action="store_true",
                        help="Re-download even if already cached")
    parser.add_argument("--rate-limit", type=float, default=DEFAULT_RATE_LIMIT,
                        dest="rate_limit", help=f"Seconds between requests (default: {DEFAULT_RATE_LIMIT})")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Show URLs without downloading")
    # FDA-13: Cache management options
    parser.add_argument("--max-cache-mb", type=int, default=DEFAULT_MAX_CACHE_MB,
                        dest="max_cache_mb",
                        help=f"Maximum cache size in MB (default: {DEFAULT_MAX_CACHE_MB}). Set to 0 for unlimited.")
    parser.add_argument("--clean-cache", action="store_true", dest="clean_cache",
                        help="Clean cache by evicting LRU files to fit within --max-cache-mb limit")
    parser.add_argument("--show-manifest", action="store_true", dest="show_manifest",
                        help="Show cache manifest with size information")

    args = parser.parse_args()
    store = PMADataStore()

    # FDA-13: Handle --clean-cache command
    if args.clean_cache:
        cache_mgr = CacheManager(store.cache_dir, max_cache_mb=args.max_cache_mb)
        print(f"Cleaning SSED cache (target: {args.max_cache_mb} MB max)...")
        before = cache_mgr.get_cache_size()
        print(f"  Current cache: {before['total_mb']} MB ({before['pdf_count']} PDFs)")

        result = cache_mgr.clean_cache(target_mb=args.max_cache_mb)
        print(f"  After cleanup: {result['after_mb']} MB")
        print(f"  Freed: {result['freed_mb']} MB ({result['evicted_count']} files evicted)")
        if result['evicted_files']:
            for f in result['evicted_files'][:10]:
                print(f"    - {os.path.basename(os.path.dirname(f))}/{os.path.basename(f)}")
            if len(result['evicted_files']) > 10:
                print(f"    ... and {len(result['evicted_files']) - 10} more")
        return

    # FDA-13: Handle --show-manifest command
    if args.show_manifest:
        cache_mgr = CacheManager(store.cache_dir, max_cache_mb=args.max_cache_mb)
        cache_info = cache_mgr.get_cache_size()
        stats = store.get_stats()

        print("=" * 60)
        print("PMA SSED Cache Manifest")
        print("=" * 60)
        print(f"  Cache directory:  {store.cache_dir}")
        print(f"  Total PMAs:       {stats['total_pmas']}")
        print(f"  SSEDs downloaded: {stats['total_sseds_downloaded']}")
        print(f"  Sections extracted: {stats['total_sections_extracted']}")
        print("-" * 60)
        print(f"  Cache size:       {cache_info['total_mb']} MB / {cache_info['max_cache_mb']} MB "
              f"({cache_info['usage_percent']}%)")
        print(f"  PDF files:        {cache_info['pdf_count']} ({round(cache_info['pdf_bytes'] / (1024*1024), 2)} MB)")
        print(f"  JSON files:       {cache_info['json_count']} ({round(cache_info['json_bytes'] / (1024*1024), 2)} MB)")
        print(f"  Other files:      {cache_info['other_count']} ({round(cache_info['other_bytes'] / (1024*1024), 2)} MB)")

        # Disk space check
        disk_info = cache_mgr.check_disk_space()
        print(f"  Free disk space:  {disk_info['free_mb']} MB")
        print(f"  Last updated:     {stats['last_updated']}")
        print("=" * 60)

        # List cached PMAs
        pmas = store.list_cached_pmas()
        if pmas:
            print(f"\nCached PMAs ({len(pmas)}):")
            for p in pmas[:20]:
                ssed = "SSED" if p["ssed_downloaded"] else "no-SSED"
                sections = f"{p['section_count']}sec" if p["sections_extracted"] else "no-sections"
                print(f"  {p['pma_number']} | {p['device_name'][:40]:40s} | {ssed} | {sections}")
            if len(pmas) > 20:
                print(f"  ... and {len(pmas) - 20} more")
        return

    downloader = SSEDDownloader(store, rate_limit=args.rate_limit,
                                max_cache_mb=args.max_cache_mb)

    if args.dry_run:
        pma_numbers = []
        if args.pma:
            pma_numbers = [args.pma]
        elif args.pma_list:
            pma_numbers = [p.strip() for p in args.pma_list.split(",") if p.strip()]

        for pma in pma_numbers:
            urls = construct_ssed_url(pma)
            print(f"{pma}:")
            for url in urls:
                print(f"  {url}")
        return

    if args.pma:
        result = downloader.download_ssed(args.pma, force=args.force)
        if result["success"]:
            print(f"SUCCESS:{result['pma_number']}|{result['filepath']}|{result['file_size_kb']}KB")
        else:
            print(f"FAILED:{result['pma_number']}|{result['error']}")

    elif args.pma_list:
        pma_numbers = [p.strip().upper() for p in args.pma_list.split(",") if p.strip()]
        print(f"Downloading SSEDs for {len(pma_numbers)} PMAs...")
        _results = downloader.download_batch(pma_numbers, force=args.force)
        downloader.print_summary()

    elif args.product_code:
        # Search for PMAs with product code, then download SSEDs
        result = store.client.search_pma(
            product_code=args.product_code,
            year_start=args.year,
            year_end=args.year,
            limit=50,
        )
        if result.get("degraded"):
            print(f"ERROR:{result.get('error')}")
            return

        pma_numbers = []
        for r in result.get("results", []):
            pn = r.get("pma_number", "")
            if pn:
                pma_numbers.append(pn)

        if not pma_numbers:
            print(f"No PMAs found for product code {args.product_code}")
            return

        print(f"Found {len(pma_numbers)} PMAs for {args.product_code}, downloading SSEDs...")
        _results = downloader.download_batch(pma_numbers, force=args.force)
        downloader.print_summary()

    else:
        parser.error("Specify --pma, --list, --product-code, --clean-cache, or --show-manifest")


if __name__ == "__main__":
    main()
