#!/usr/bin/env python3
"""
FDA Data Update Manager — Batch Update Orchestrator.

Scans all projects for stale cached data and provides batch update functionality.
Integrates with existing fda_data_store.py TTL logic and API client.

Usage:
    python3 update_manager.py --scan-all                    # Scan all projects for stale data
    python3 update_manager.py --project NAME --update       # Update stale data for one project
    python3 update_manager.py --update-all                  # Update all stale data across projects
    python3 update_manager.py --clean-cache                 # Remove expired API cache files
    python3 update_manager.py --dry-run --update-all        # Preview updates without executing
    python3 update_manager.py --smart --project NAME        # Smart detection: find new clearances
    python3 update_manager.py --smart --project NAME --dry-run  # Preview smart detection changes

Features:
    - Batch freshness checking across multiple projects
    - Rate-limited batch updates (500ms throttle = 2 req/sec)
    - Dry-run mode for preview without execution
    - Integration with existing is_expired() and TTL_TIERS
    - System cache cleanup for expired API responses
    - Smart change detection: compare live API against fingerprints
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Import existing modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fda_data_store import (
    get_projects_dir,
    load_manifest,
    save_manifest,
    is_expired,
    TTL_TIERS,
    _fetch_from_api,
    _extract_summary,
)
from fda_api_client import FDAClient
from change_detector import detect_changes, trigger_pipeline


# Rate limiting configuration
RATE_LIMIT_DELAY = 0.5  # 500ms = 2 requests/second


def find_all_projects():
    """Find all project directories with data_manifest.json files.

    Returns:
        List of tuples: (project_name, project_dir, manifest_path)
    """
    projects_dir = Path(get_projects_dir())
    if not projects_dir.exists():
        return []

    projects = []
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        manifest_path = project_dir / "data_manifest.json"
        if manifest_path.exists():
            projects.append((
                project_dir.name,
                str(project_dir),
                str(manifest_path)
            ))

    return sorted(projects)


def scan_all_projects(verbose=False):
    """Scan all projects and identify stale queries.

    Args:
        verbose: If True, print detailed progress

    Returns:
        Dictionary with scan results:
        {
            "total_projects": int,
            "total_queries": int,
            "stale_queries": int,
            "fresh_queries": int,
            "projects": {
                "project_name": {
                    "total_queries": int,
                    "stale_queries": int,
                    "fresh_queries": int,
                    "stale_details": [{"key": str, "age_hours": float, "ttl_hours": int}, ...]
                }
            }
        }
    """
    projects = find_all_projects()

    if verbose:
        print(f"🔍 Scanning {len(projects)} projects for stale data...")

    results = {
        "total_projects": len(projects),
        "total_queries": 0,
        "stale_queries": 0,
        "fresh_queries": 0,
        "projects": {}
    }

    for project_name, project_dir, manifest_path in projects:
        manifest = load_manifest(project_dir)
        queries = manifest.get("queries", {})

        project_stats = {
            "total_queries": len(queries),
            "stale_queries": 0,
            "fresh_queries": 0,
            "stale_details": []
        }

        for key, entry in queries.items():
            results["total_queries"] += 1

            if is_expired(entry):
                project_stats["stale_queries"] += 1
                results["stale_queries"] += 1

                # Calculate age
                fetched_at = entry.get("fetched_at", "")
                age_hours = 0
                if fetched_at:
                    try:
                        ft = datetime.fromisoformat(fetched_at)
                        if ft.tzinfo is None:
                            ft = ft.replace(tzinfo=timezone.utc)
                        age_hours = (datetime.now(timezone.utc) - ft).total_seconds() / 3600
                    except (ValueError, TypeError):
                        age_hours = 999999  # Unknown age

                project_stats["stale_details"].append({
                    "key": key,
                    "age_hours": round(age_hours, 1),
                    "ttl_hours": entry.get("ttl_hours", 24)
                })
            else:
                project_stats["fresh_queries"] += 1
                results["fresh_queries"] += 1

        if project_stats["total_queries"] > 0:
            results["projects"][project_name] = project_stats

        if verbose and project_stats["total_queries"] > 0:
            stale = project_stats["stale_queries"]
            total = project_stats["total_queries"]
            status = "⚠️ " if stale > 0 else "✅"
            print(f"  {status} {project_name}: {stale}/{total} stale")

    return results


def find_stale_queries(project_name):
    """Find all stale queries for a specific project.

    Args:
        project_name: Name of the project

    Returns:
        List of dictionaries with stale query details:
        [{"key": str, "entry": dict, "age_hours": float}, ...]
    """
    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, project_name)

    if not os.path.exists(project_dir):
        return []

    manifest = load_manifest(project_dir)
    queries = manifest.get("queries", {})

    stale = []
    for key, entry in queries.items():
        if is_expired(entry):
            # Calculate age
            fetched_at = entry.get("fetched_at", "")
            age_hours = 0
            if fetched_at:
                try:
                    ft = datetime.fromisoformat(fetched_at)
                    if ft.tzinfo is None:
                        ft = ft.replace(tzinfo=timezone.utc)
                    age_hours = (datetime.now(timezone.utc) - ft).total_seconds() / 3600
                except (ValueError, TypeError):
                    age_hours = 999999

            stale.append({
                "key": key,
                "entry": entry,
                "age_hours": age_hours
            })

    return stale


def batch_update(project_name, dry_run=False, verbose=True):
    """Update all stale queries for a project.

    Args:
        project_name: Name of the project to update
        dry_run: If True, preview updates without executing
        verbose: If True, print progress

    Returns:
        Dictionary with update results:
        {
            "project": str,
            "stale_count": int,
            "updated": int,
            "failed": int,
            "skipped": int,
            "updates": [{"key": str, "status": str, "error": str}, ...]
        }
    """
    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, project_name)

    if not os.path.exists(project_dir):
        return {
            "project": project_name,
            "error": "Project directory not found",
            "stale_count": 0,
            "updated": 0,
            "failed": 0,
            "skipped": 0,
            "updates": []
        }

    stale_queries = find_stale_queries(project_name)

    if dry_run:
        if verbose:
            print(f"🔍 DRY RUN: Would update {len(stale_queries)} stale queries for {project_name}")
            for item in stale_queries:
                age_days = item["age_hours"] / 24
                print(f"  - {item['key']} (age: {age_days:.1f} days)")

        return {
            "project": project_name,
            "stale_count": len(stale_queries),
            "updated": 0,
            "failed": 0,
            "skipped": len(stale_queries),
            "updates": [{"key": item["key"], "status": "skipped_dry_run"} for item in stale_queries]
        }

    # Execute updates
    if verbose:
        print(f"🔄 Updating {len(stale_queries)} stale queries for {project_name}...")

    manifest = load_manifest(project_dir)
    client = FDAClient()

    results = {
        "project": project_name,
        "stale_count": len(stale_queries),
        "updated": 0,
        "failed": 0,
        "skipped": 0,
        "updates": []
    }

    for idx, item in enumerate(stale_queries, 1):
        key = item["key"]

        if verbose:
            print(f"  [{idx}/{len(stale_queries)}] Updating {key}...", end=" ")

        # Parse query key to determine query type and parameters
        parts = key.split(":")
        query_type = parts[0]

        # Extract parameters from key
        product_code = None
        k_number = None
        k_numbers = None
        count_field = None

        if query_type in ("classification", "recalls", "events", "enforcement"):
            product_code = parts[1] if len(parts) > 1 else None
        elif query_type == "510k":
            k_number = parts[1] if len(parts) > 1 else None
        elif query_type in ("510k-batch", "510k_batch"):
            k_numbers = parts[1].split(",") if len(parts) > 1 else None
            query_type = "510k-batch"  # Normalize

        if "count:" in key:
            count_field = key.split("count:")[-1]

        # Fetch from API
        result = _fetch_from_api(client, query_type, product_code, k_number, k_numbers, count_field)

        if result.get("degraded") or result.get("error"):
            results["failed"] += 1
            error_msg = result.get("error", "API unavailable")
            results["updates"].append({
                "key": key,
                "status": "failed",
                "error": error_msg
            })
            if verbose:
                print(f"❌ FAILED: {error_msg}")
        else:
            # Extract summary
            summary = _extract_summary(query_type, result, count_field)

            # Update manifest
            now = datetime.now(timezone.utc).isoformat()
            total = result.get("meta", {}).get("results", {}).get("total", 0)

            manifest["queries"][key] = {
                "fetched_at": now,
                "ttl_hours": TTL_TIERS.get(query_type, 24),
                "source": "openFDA",
                "total_matches": total,
                "summary": summary,
                "api_cache_key": item["entry"].get("api_cache_key", "")
            }

            results["updated"] += 1
            results["updates"].append({
                "key": key,
                "status": "updated"
            })
            if verbose:
                print("✅ SUCCESS")

        # Rate limiting
        if idx < len(stale_queries):  # Don't sleep after last item
            time.sleep(RATE_LIMIT_DELAY)

    # Save updated manifest
    save_manifest(project_dir, manifest)

    if verbose:
        print(f"\n✅ Update complete: {results['updated']} updated, {results['failed']} failed")

    return results


def update_all_projects(dry_run=False, verbose=True):
    """Update stale data across all projects.

    Args:
        dry_run: If True, preview updates without executing
        verbose: If True, print progress

    Returns:
        Dictionary with overall results:
        {
            "total_projects": int,
            "updated_projects": int,
            "total_updated": int,
            "total_failed": int,
            "projects": {project_name: update_results, ...}
        }
    """
    scan_results = scan_all_projects(verbose=False)

    projects_with_stale = {
        name: stats
        for name, stats in scan_results["projects"].items()
        if stats["stale_queries"] > 0
    }

    if not projects_with_stale:
        if verbose:
            print("✅ No stale data found across all projects!")
        return {
            "total_projects": 0,
            "updated_projects": 0,
            "total_updated": 0,
            "total_failed": 0,
            "projects": {}
        }

    if verbose:
        print(f"🔍 Found {len(projects_with_stale)} projects with stale data")
        print(f"📊 Total stale queries: {scan_results['stale_queries']}")
        print()

    overall_results = {
        "total_projects": len(projects_with_stale),
        "updated_projects": 0,
        "total_updated": 0,
        "total_failed": 0,
        "projects": {}
    }

    for idx, (project_name, stats) in enumerate(projects_with_stale.items(), 1):
        if verbose:
            print(f"[{idx}/{len(projects_with_stale)}] Project: {project_name} ({stats['stale_queries']} stale)")

        result = batch_update(project_name, dry_run=dry_run, verbose=verbose)
        overall_results["projects"][project_name] = result

        if result.get("updated", 0) > 0:
            overall_results["updated_projects"] += 1

        overall_results["total_updated"] += result.get("updated", 0)
        overall_results["total_failed"] += result.get("failed", 0)

        if verbose:
            print()

    if verbose:
        print("=" * 60)
        print(f"🎯 Overall Summary:")
        print(f"  Projects updated: {overall_results['updated_projects']}/{overall_results['total_projects']}")
        print(f"  Queries updated: {overall_results['total_updated']}")
        print(f"  Queries failed: {overall_results['total_failed']}")

    return overall_results


def clean_system_cache(verbose=True):
    """Remove expired files from system API cache.

    Args:
        verbose: If True, print progress

    Returns:
        Dictionary with cleanup results:
        {
            "cache_dir": str,
            "total_files": int,
            "expired_files": int,
            "bytes_freed": int
        }
    """
    client = FDAClient()
    cache_dir = client.cache_dir

    if verbose:
        print(f"🗑️  Cleaning expired files from {cache_dir}...")

    cache_files = list(cache_dir.glob("*.json"))
    expired_count = 0
    bytes_freed = 0

    for cache_file in cache_files:
        try:
            with open(cache_file) as f:
                data = json.load(f)

            # Check if expired (7-day TTL)
            cached_at = data.get("_cached_at", 0)
            if time.time() - cached_at > (7 * 24 * 60 * 60):
                file_size = cache_file.stat().st_size
                cache_file.unlink()
                expired_count += 1
                bytes_freed += file_size
        except (json.JSONDecodeError, OSError):
            # Invalid cache file, remove it
            try:
                file_size = cache_file.stat().st_size
                cache_file.unlink()
                expired_count += 1
                bytes_freed += file_size
            except OSError as e:
                logger.warning("Failed to remove expired cache file: %s", e)

    results = {
        "cache_dir": str(cache_dir),
        "total_files": len(cache_files),
        "expired_files": expired_count,
        "bytes_freed": bytes_freed
    }

    if verbose:
        mb_freed = bytes_freed / (1024 * 1024)
        print(f"✅ Removed {expired_count} expired files ({mb_freed:.2f} MB freed)")

    return results


def print_scan_summary(scan_results):
    """Print a formatted summary of scan results."""
    print("=" * 60)
    print("📊 FDA Data Freshness Scan Summary")
    print("=" * 60)
    print(f"Total projects: {scan_results['total_projects']}")
    print(f"Total queries: {scan_results['total_queries']}")
    print(f"Fresh queries: {scan_results['fresh_queries']}")
    print(f"Stale queries: {scan_results['stale_queries']}")

    if scan_results['stale_queries'] > 0:
        stale_pct = (scan_results['stale_queries'] / scan_results['total_queries']) * 100
        print(f"Stale percentage: {stale_pct:.1f}%")

    print()

    projects_with_stale = {
        name: stats
        for name, stats in scan_results["projects"].items()
        if stats["stale_queries"] > 0
    }

    if projects_with_stale:
        print("Projects with stale data:")
        print()
        for project_name, stats in sorted(projects_with_stale.items()):
            print(f"  📁 {project_name}")
            print(f"     Stale: {stats['stale_queries']}/{stats['total_queries']} queries")

            # Show top 5 stale queries
            stale_details = sorted(stats['stale_details'], key=lambda x: x['age_hours'], reverse=True)
            for detail in stale_details[:5]:
                age_days = detail['age_hours'] / 24
                ttl_days = detail['ttl_hours'] / 24
                print(f"       - {detail['key']}")
                print(f"         Age: {age_days:.1f} days (TTL: {ttl_days:.1f} days)")

            if len(stale_details) > 5:
                print(f"       ... and {len(stale_details) - 5} more")
            print()
    else:
        print("✅ All data is fresh!")

    print("=" * 60)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FDA Data Update Manager — Batch Update Orchestrator"
    )
    parser.add_argument("--scan-all", action="store_true", dest="scan_all",
                        help="Scan all projects for stale data")
    parser.add_argument("--project", help="Project name for single-project operations")
    parser.add_argument("--update", action="store_true",
                        help="Update stale data (use with --project or --update-all)")
    parser.add_argument("--update-all", action="store_true", dest="update_all",
                        help="Update stale data across all projects")
    parser.add_argument("--clean-cache", action="store_true", dest="clean_cache",
                        help="Remove expired files from system API cache")
    parser.add_argument("--smart", action="store_true",
                        help="Smart change detection: compare live API against fingerprints")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Preview updates without executing")
    parser.add_argument("--quiet", action="store_true",
                        help="Minimal output (for scripting)")

    args = parser.parse_args()
    verbose = not args.quiet

    if args.scan_all:
        results = scan_all_projects(verbose=verbose)
        if verbose:
            print_scan_summary(results)
        else:
            # JSON output for scripting
            print(json.dumps(results, indent=2))

    elif args.update and args.project:
        results = batch_update(args.project, dry_run=args.dry_run, verbose=verbose)
        if not verbose:
            print(json.dumps(results, indent=2))

    elif args.update_all:
        results = update_all_projects(dry_run=args.dry_run, verbose=verbose)
        if not verbose:
            print(json.dumps(results, indent=2))

    elif args.clean_cache:
        results = clean_system_cache(verbose=verbose)
        if not verbose:
            print(json.dumps(results, indent=2))

    elif args.smart:
        # Smart change detection mode
        if not args.project:
            # Smart mode on all projects
            projects = find_all_projects()
            if not projects:
                if verbose:
                    print("No projects found. Create a project first with /fda-tools:extract.")
                sys.exit(0)

            all_results = {}
            total_new = 0
            client = FDAClient()

            for project_name, project_dir, manifest_path in projects:
                result = detect_changes(project_name, client=client, verbose=verbose)
                all_results[project_name] = result
                total_new += result.get("total_new_clearances", 0)

            if verbose:
                print()
                print("=" * 60)
                print(f"Smart Detection Summary: {total_new} new clearance(s) across {len(projects)} project(s)")
                print("=" * 60)

                if total_new > 0 and not args.dry_run:
                    print()
                    print("To trigger pipeline for new clearances, re-run with --smart --project NAME")
                    print("or use change_detector.py --project NAME --trigger")
            else:
                print(json.dumps(all_results, indent=2))
        else:
            # Smart mode on a specific project
            client = FDAClient()
            result = detect_changes(args.project, client=client, verbose=verbose)

            if not verbose:
                print(json.dumps(result, indent=2))
            else:
                changes = result.get("changes", [])
                total_new = result.get("total_new_clearances", 0)

                print()
                print("=" * 60)
                print(f"Smart Detection: {args.project}")
                print("=" * 60)
                print(f"Product codes checked: {result.get('product_codes_checked', 0)}")
                print(f"New clearances: {total_new}")
                print(f"New recalls: {result.get('total_new_recalls', 0)}")

                if total_new > 0:
                    print()
                    # Show change details
                    for change in changes:
                        if change.get("change_type") == "new_clearances":
                            pc = change.get("product_code", "")
                            print(f"  {pc}: {change.get('count', 0)} new clearance(s)")
                            for item in change.get("new_items", [])[:5]:
                                k = item.get("k_number", "")
                                name = item.get("device_name", "")[:50]
                                print(f"    - {k}: {name}")
                            if len(change.get("new_items", [])) > 5:
                                print(f"    ... and {len(change['new_items']) - 5} more")

                    if not args.dry_run:
                        print()
                        print("Trigger pipeline for new clearances? (Use --smart --project NAME in change_detector.py --trigger)")
                    else:
                        print()
                        print("DRY RUN: No pipeline triggered. Remove --dry-run to execute.")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
