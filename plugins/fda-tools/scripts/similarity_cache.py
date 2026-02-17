#!/usr/bin/env python3
"""
Similarity Score Cache Module for FDA 510(k) Section Analytics

Implements disk-based caching for pairwise similarity matrices to achieve
30x speedup on repeated section comparisons. Addresses FE-005 from FDA-62.

Features:
  - Deterministic cache key generation (section_type + method + device_set_hash)
  - 7-day TTL with auto-expiration
  - Leverages cache_integrity.py for atomic writes and checksums
  - Cache hit/miss statistics
  - CLI flag --no-cache to bypass cache

Performance Target:
  - Cached queries: <2 seconds (30x speedup from ~60s baseline)
  - Cache miss: Acceptable at baseline speed (~60s for 100 devices)

Usage:
    from similarity_cache import (
        get_cached_similarity_matrix,
        save_similarity_matrix,
        generate_cache_key,
        get_cache_stats,
    )

    # Generate cache key
    cache_key = generate_cache_key(device_keys, section_type, method)

    # Try to retrieve cached result
    cached = get_cached_similarity_matrix(cache_key)
    if cached:
        return cached

    # Compute and cache result
    result = compute_expensive_similarity_matrix(...)
    save_similarity_matrix(cache_key, result)
"""

import hashlib
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Import cache integrity infrastructure
try:
    from cache_integrity import integrity_read, integrity_write  # type: ignore
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cache_integrity import integrity_read, integrity_write  # type: ignore


# Cache configuration
DEFAULT_CACHE_DIR = Path(os.path.expanduser("~/fda-510k-data/extraction/similarity_cache"))
DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days


# Global cache statistics (in-memory for the session)
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "writes": 0,
    "invalidations": 0,
    "errors": 0,
}


def _get_cache_dir() -> Path:
    """Get the similarity cache directory, creating it if needed."""
    cache_dir = DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def generate_cache_key(
    device_keys: List[str],
    section_type: str,
    method: str = "cosine",
) -> str:
    """Generate a deterministic cache key for a similarity matrix query.

    Cache key formula: sha256(sorted_device_keys + section_type + method)

    This ensures:
      - Same device set + section + method = same cache key
      - Different device order = same cache key (sorted first)
      - Different device set = different cache key

    Args:
        device_keys: List of K-numbers (device identifiers).
        section_type: Section type (e.g., 'clinical_testing').
        method: Similarity method ('sequence', 'jaccard', 'cosine').

    Returns:
        Hexadecimal cache key string (64 chars).

    Example:
        >>> generate_cache_key(['K123456', 'K789012'], 'clinical_testing', 'cosine')
        'a3f2e1d...'
    """
    # Sort device keys for deterministic ordering
    sorted_devices = sorted(device_keys)

    # Create canonical string representation
    key_parts = [
        f"devices:{','.join(sorted_devices)}",
        f"section:{section_type}",
        f"method:{method}",
    ]
    key_string = "|".join(key_parts)

    # Hash for compact key
    key_hash = hashlib.sha256(key_string.encode("utf-8")).hexdigest()

    return key_hash


def _get_cache_file_path(cache_key: str) -> Path:
    """Get the file path for a cache key.

    Args:
        cache_key: Hexadecimal cache key.

    Returns:
        Path to cache file.
    """
    cache_dir = _get_cache_dir()
    return cache_dir / f"{cache_key}.json"


def get_cached_similarity_matrix(
    cache_key: str,
    ttl_seconds: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve a cached similarity matrix if available and valid.

    Checks:
      1. File exists
      2. Integrity checksum valid (via cache_integrity)
      3. TTL not expired (default: 7 days)

    Args:
        cache_key: Cache key from generate_cache_key().
        ttl_seconds: Time-to-live in seconds. Defaults to 7 days.

    Returns:
        Cached similarity matrix dict, or None if cache miss/invalid/expired.
    """
    global _cache_stats

    if ttl_seconds is None:
        ttl_seconds = DEFAULT_TTL_SECONDS

    cache_file = _get_cache_file_path(cache_key)

    try:
        # Use cache_integrity for validated read with TTL
        data = integrity_read(
            cache_file,
            ttl_seconds=ttl_seconds,
            auto_invalidate=True,
        )

        if data is not None:
            _cache_stats["hits"] += 1
            return data
        else:
            _cache_stats["misses"] += 1
            return None

    except Exception:
        _cache_stats["errors"] += 1
        _cache_stats["misses"] += 1
        return None


def save_similarity_matrix(
    cache_key: str,
    similarity_data: Dict[str, Any],
) -> bool:
    """Save a similarity matrix to disk cache.

    Uses cache_integrity for:
      - SHA-256 checksum of data
      - Atomic write (temp file + os.replace)
      - Timestamp metadata

    Args:
        cache_key: Cache key from generate_cache_key().
        similarity_data: Similarity matrix dict to cache.

    Returns:
        True if write succeeded, False otherwise.
    """
    global _cache_stats

    cache_file = _get_cache_file_path(cache_key)

    try:
        # Use cache_integrity for atomic write with checksum
        success = integrity_write(
            cache_file,
            similarity_data,
            cached_at=time.time(),
        )

        if success:
            _cache_stats["writes"] += 1
        else:
            _cache_stats["errors"] += 1

        return success

    except Exception:
        _cache_stats["errors"] += 1
        return False


def invalidate_cache(cache_key: str) -> bool:
    """Invalidate (delete) a cached similarity matrix.

    Args:
        cache_key: Cache key to invalidate.

    Returns:
        True if file was deleted, False otherwise.
    """
    global _cache_stats

    cache_file = _get_cache_file_path(cache_key)

    try:
        if cache_file.exists():
            cache_file.unlink()
            _cache_stats["invalidations"] += 1
            return True
        return False
    except OSError:
        return False


def get_cache_stats() -> Dict[str, Union[int, float]]:
    """Get cache statistics for the current session.

    Returns:
        Dict with hit/miss/write/error counts:
        {
            'hits': int,
            'misses': int,
            'writes': int,
            'invalidations': int,
            'errors': int,
            'total_queries': int,
            'hit_rate': float (0.0-1.0),
        }
    """
    global _cache_stats

    total = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = _cache_stats["hits"] / total if total > 0 else 0.0

    return {
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "writes": _cache_stats["writes"],
        "invalidations": _cache_stats["invalidations"],
        "errors": _cache_stats["errors"],
        "total_queries": total,
        "hit_rate": hit_rate,
    }


def reset_cache_stats() -> None:
    """Reset cache statistics (useful for testing)."""
    global _cache_stats
    _cache_stats = {
        "hits": 0,
        "misses": 0,
        "writes": 0,
        "invalidations": 0,
        "errors": 0,
    }


def clear_all_cache(max_age_days: Optional[int] = None) -> Tuple[int, int]:
    """Clear all similarity cache files.

    Args:
        max_age_days: If provided, only delete files older than this many days.
                     If None, delete all cache files.

    Returns:
        Tuple of (files_deleted, errors_encountered).
    """
    cache_dir = _get_cache_dir()
    deleted = 0
    errors = 0

    if not cache_dir.exists():
        return 0, 0

    cutoff_time = None
    if max_age_days is not None:
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)

    for cache_file in cache_dir.glob("*.json"):
        try:
            # Check age if max_age_days specified
            if cutoff_time is not None:
                file_mtime = cache_file.stat().st_mtime
                if file_mtime > cutoff_time:
                    continue  # Skip newer files

            cache_file.unlink()
            deleted += 1
        except OSError:
            errors += 1

    return deleted, errors


def get_cache_size_info() -> Dict[str, Any]:
    """Get information about cache disk usage.

    Returns:
        Dict with cache size statistics:
        {
            'file_count': int,
            'total_bytes': int,
            'total_mb': float,
            'oldest_file': str (ISO timestamp),
            'newest_file': str (ISO timestamp),
        }
    """
    cache_dir = _get_cache_dir()

    if not cache_dir.exists():
        return {
            "file_count": 0,
            "total_bytes": 0,
            "total_mb": 0.0,
            "oldest_file": None,
            "newest_file": None,
        }

    files = list(cache_dir.glob("*.json"))
    total_bytes = sum(f.stat().st_size for f in files)

    mtimes = [f.stat().st_mtime for f in files] if files else []
    oldest = min(mtimes) if mtimes else None
    newest = max(mtimes) if mtimes else None

    return {
        "file_count": len(files),
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
        "oldest_file": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(oldest)) if oldest else None,
        "newest_file": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(newest)) if newest else None,
    }


# CLI for cache management
def main():
    """CLI entry point for cache management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Similarity Cache Management Tool"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show current session cache statistics"
    )
    parser.add_argument(
        "--info", action="store_true",
        help="Show cache size and disk usage info"
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Clear all cache files"
    )
    parser.add_argument(
        "--clear-old", type=int, metavar="DAYS",
        help="Clear cache files older than N days"
    )

    args = parser.parse_args()

    if args.stats:
        stats = get_cache_stats()
        print("Cache Statistics (Current Session)")
        print("=" * 50)
        print(f"Hits:          {stats['hits']}")
        print(f"Misses:        {stats['misses']}")
        print(f"Writes:        {stats['writes']}")
        print(f"Invalidations: {stats['invalidations']}")
        print(f"Errors:        {stats['errors']}")
        print(f"Total Queries: {stats['total_queries']}")
        print(f"Hit Rate:      {stats['hit_rate']:.1%}")

    elif args.info:
        info = get_cache_size_info()
        print("Cache Disk Usage")
        print("=" * 50)
        print(f"Files:        {info['file_count']}")
        print(f"Total Size:   {info['total_mb']} MB ({info['total_bytes']:,} bytes)")
        print(f"Oldest File:  {info['oldest_file']}")
        print(f"Newest File:  {info['newest_file']}")
        print(f"Cache Dir:    {_get_cache_dir()}")

    elif args.clear:
        deleted, errors = clear_all_cache()
        print(f"Cleared cache: {deleted} files deleted, {errors} errors")

    elif args.clear_old:
        deleted, errors = clear_all_cache(max_age_days=args.clear_old)
        print(f"Cleared cache files older than {args.clear_old} days:")
        print(f"  {deleted} files deleted, {errors} errors")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
