#!/usr/bin/env python3
"""
PMA SSED Batch Downloader -- Downloads and validates SSED PDFs from FDA servers.

Extends the URL construction patterns from pma_prototype.py with robust batch
download orchestration, rate limiting, error recovery, progress tracking,
and resume capability.

Key features:
    - TICKET-002 validated URL patterns (single-digit folders for 2000s PMAs)
    - Case-variation fallback (uppercase B, lowercase b, all lowercase)
    - User-Agent header required by FDA servers
    - 500ms rate limiting between requests (2 req/sec)
    - Automatic retry with exponential backoff (3 attempts)
    - Resume capability (skips already downloaded)
    - PDF validation (%PDF magic bytes)
    - Progress tracking with ETA

Usage:
    from pma_ssed_cache import SSEDDownloader

    downloader = SSEDDownloader(store)
    result = downloader.download_ssed("P170019")
    results = downloader.download_batch(["P170019", "P200024", "P070004"])

    # CLI usage:
    python3 pma_ssed_cache.py --pma P170019
    python3 pma_ssed_cache.py --list P170019,P200024,P070004
    python3 pma_ssed_cache.py --product-code NMH --year 2024
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pma_data_store import PMADataStore


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


class SSEDDownloader:
    """SSED PDF batch downloader with progress tracking and error recovery.

    Downloads Summary of Safety and Effectiveness Data (SSED) PDFs from
    FDA servers with rate limiting, retry logic, and resume capability.
    """

    def __init__(self, store: Optional[PMADataStore] = None,
                 rate_limit: float = DEFAULT_RATE_LIMIT):
        """Initialize SSED downloader.

        Args:
            store: PMADataStore for caching and manifest updates.
            rate_limit: Seconds between requests (default 0.5 = 2 req/sec).
        """
        self.store = store or PMADataStore()
        self.rate_limit = rate_limit
        self._stats = {
            "attempted": 0,
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "total_bytes": 0,
            "start_time": None,
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

        for attempt in range(MAX_RETRIES):
            result["attempts"] += 1
            try:
                req = urllib.request.Request(url, headers=HTTP_HEADERS)
                with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
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
            Dictionary with attempted, downloaded, skipped, failed counts.
        """
        elapsed = 0
        if self._stats["start_time"]:
            elapsed = time.time() - self._stats["start_time"]

        return {
            "attempted": self._stats["attempted"],
            "downloaded": self._stats["downloaded"],
            "skipped": self._stats["skipped"],
            "failed": self._stats["failed"],
            "total_bytes": self._stats["total_bytes"],
            "total_mb": round(self._stats["total_bytes"] / (1024 * 1024), 2),
            "elapsed_seconds": round(elapsed, 1),
            "download_rate_mbps": round(
                (self._stats["total_bytes"] / (1024 * 1024)) / elapsed, 3
            ) if elapsed > 0 else 0,
        }

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
        print(f"  Total size: {stats['total_mb']} MB")
        print(f"  Elapsed:    {stats['elapsed_seconds']}s")
        if stats["download_rate_mbps"] > 0:
            print(f"  Rate:       {stats['download_rate_mbps']} MB/s")
        success_rate = (
            (stats["downloaded"] + stats["skipped"]) / stats["attempted"] * 100
            if stats["attempted"] > 0 else 0
        )
        print(f"  Success:    {success_rate:.1f}%")
        print("=" * 60)


# ------------------------------------------------------------------
# CLI interface
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PMA SSED Batch Downloader"
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

    args = parser.parse_args()
    store = PMADataStore()
    downloader = SSEDDownloader(store, rate_limit=args.rate_limit)

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
        results = downloader.download_batch(pma_numbers, force=args.force)
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
        results = downloader.download_batch(pma_numbers, force=args.force)
        downloader.print_summary()

    else:
        parser.error("Specify --pma, --list, or --product-code")


if __name__ == "__main__":
    main()
