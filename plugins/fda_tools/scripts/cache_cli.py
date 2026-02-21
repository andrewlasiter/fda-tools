#!/usr/bin/env python3
"""
Cache Management CLI — FDA-135
================================

Provides ``/fda-tools:cache`` sub-commands for inspecting and purging
stale data across all fda-510k-data cache directories.

Usage
-----
    python3 -m fda_tools.scripts.cache_cli --stats
    python3 -m fda_tools.scripts.cache_cli --purge-stale
    python3 -m fda_tools.scripts.cache_cli --purge-all
    python3 -m fda_tools.scripts.cache_cli --list-ttls

Exit codes: 0 = success, 1 = error
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from fda_tools.lib.cache_manager import CacheManager


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cache_cli",
        description="FDA plugin cache management (FDA-135)",
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--stats",
        action="store_true",
        help="Print cache statistics (file counts, sizes, stale counts)",
    )
    group.add_argument(
        "--purge-stale",
        action="store_true",
        help="Delete cache files that have exceeded their TTL",
    )
    group.add_argument(
        "--purge-all",
        action="store_true",
        help="Delete ALL cache files regardless of age",
    )
    group.add_argument(
        "--list-ttls",
        action="store_true",
        help="Print the TTL (seconds) for each cache type",
    )
    p.add_argument(
        "--base-dir",
        default=None,
        help="Override base data directory (default: ~/fda-510k-data)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON instead of human-readable text",
    )
    return p


def cmd_stats(mgr: CacheManager, output_json: bool) -> None:
    stats = mgr.get_stats()
    if output_json:
        out = {
            ct: {
                "ttl_seconds": s.ttl_seconds,
                "ttl_human": s.ttl_human,
                "total_files": s.total_files,
                "stale_files": s.stale_files,
                "total_size_mb": round(s.total_size_mb, 2),
                "stale_size_mb": round(s.stale_size_mb, 2),
            }
            for ct, s in stats.items()
        }
        print(json.dumps(out, indent=2))
        return

    # Human-readable table
    header = f"{'Cache Type':<18} {'TTL':>6}  {'Files':>6}  {'Stale':>6}  {'Size MB':>8}  {'Stale MB':>9}"
    print(header)
    print("-" * len(header))
    total_files = total_stale = 0
    total_mb = stale_mb = 0.0
    for ct, s in sorted(stats.items()):
        print(
            f"{ct:<18} {s.ttl_human:>6}  {s.total_files:>6}  {s.stale_files:>6}"
            f"  {s.total_size_mb:>8.2f}  {s.stale_size_mb:>9.2f}"
        )
        total_files += s.total_files
        total_stale += s.stale_files
        total_mb += s.total_size_mb
        stale_mb += s.stale_size_mb
    print("-" * len(header))
    print(
        f"{'TOTAL':<18} {'':>6}  {total_files:>6}  {total_stale:>6}"
        f"  {total_mb:>8.2f}  {stale_mb:>9.2f}"
    )


def cmd_purge_stale(mgr: CacheManager, output_json: bool) -> None:
    result = mgr.purge_stale()
    if output_json:
        print(json.dumps({
            "files_removed": result.files_removed,
            "mb_freed": round(result.mb_freed, 2),
            "errors": result.errors,
        }, indent=2))
        return
    print(f"Removed {result.files_removed} stale cache files "
          f"({result.mb_freed:.2f} MB freed)")
    if result.errors:
        print(f"Errors ({len(result.errors)}):", file=sys.stderr)
        for e in result.errors:
            print(f"  {e}", file=sys.stderr)


def cmd_purge_all(mgr: CacheManager, output_json: bool) -> None:
    result = mgr.purge_all()
    if output_json:
        print(json.dumps({
            "files_removed": result.files_removed,
            "mb_freed": round(result.mb_freed, 2),
            "errors": result.errors,
        }, indent=2))
        return
    print(f"Removed {result.files_removed} cache files "
          f"({result.mb_freed:.2f} MB freed)")
    if result.errors:
        print(f"Errors ({len(result.errors)}):", file=sys.stderr)
        for e in result.errors:
            print(f"  {e}", file=sys.stderr)


def cmd_list_ttls(mgr: CacheManager, output_json: bool) -> None:
    ttls = mgr.get_ttls()
    if output_json:
        print(json.dumps(ttls, indent=2))
        return
    print(f"{'Cache Type':<18} {'TTL (seconds)':>14}  {'TTL (human)':>12}")
    print("-" * 48)
    for ct, seconds in sorted(ttls.items()):
        if seconds >= 86400:
            human = f"{seconds // 86400}d"
        elif seconds >= 3600:
            human = f"{seconds // 3600}h"
        else:
            human = f"{seconds}s"
        print(f"{ct:<18} {seconds:>14}  {human:>12}")


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        mgr = CacheManager(base_dir=args.base_dir)
    except Exception as e:
        if args.output_json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error initialising CacheManager: {e}", file=sys.stderr)
        return 1

    try:
        if args.stats:
            cmd_stats(mgr, args.output_json)
        elif args.purge_stale:
            cmd_purge_stale(mgr, args.output_json)
        elif args.purge_all:
            cmd_purge_all(mgr, args.output_json)
        elif args.list_ttls:
            cmd_list_ttls(mgr, args.output_json)
    except Exception as e:
        if args.output_json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
