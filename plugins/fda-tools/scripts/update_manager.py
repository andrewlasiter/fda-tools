#!/usr/bin/env python3
"""
FDA Data Update Manager — Batch Update Orchestrator.

Scans all projects for stale cached data and provides batch update functionality.
Integrates with existing fda_data_store.py TTL logic and API client.

Usage:
    python3 update_manager.py --scan-all                    # Scan all projects for stale data
    python3 update_manager.py --project NAME --update       # Update stale data for one project
    python3 update_manager.py --update-all                  # Update all stale data across projects
    python3 update_manager.py --update-all --backup         # Backup before updating all projects
    python3 update_manager.py --clean-cache                 # Remove expired API cache files
    python3 update_manager.py --dry-run --update-all        # Preview updates without executing
    python3 update_manager.py --smart --project NAME        # Smart detection: find new clearances
    python3 update_manager.py --smart --project NAME --dry-run  # Preview smart detection changes
    python3 update_manager.py --smart --all-projects        # Smart detection across ALL projects (FDA-38)
    python3 update_manager.py --smart --all-projects --dry-run  # Preview all-projects smart detection

Features:
    - Batch freshness checking across multiple projects
    - Rate-limited batch updates (500ms throttle = 2 req/sec)
    - Dry-run mode for preview without execution
    - Integration with existing is_expired() and TTL_TIERS
    - System cache cleanup for expired API responses
    - Smart change detection: compare live API against fingerprints
    - Automatic backup before updates (optional --backup flag)
    - Consolidated --smart --all-projects mode with global rate limiting (FDA-38)
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
from change_detector import detect_changes

# Import backup functionality
try:
    from backup_project import backup_all_projects
    BACKUP_AVAILABLE = True
except ImportError:
    BACKUP_AVAILABLE = False
    logger.warning("Backup functionality not available (backup_project.py not found)")


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

    for project_name, project_dir, _manifest_path in projects:
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


def update_all_projects(dry_run=False, verbose=True, backup_first=False):
    """Update stale data across all projects.

    Args:
        dry_run: If True, preview updates without executing
        verbose: If True, print progress
        backup_first: If True, create backup before updating

    Returns:
        Dictionary with overall results:
        {
            "total_projects": int,
            "updated_projects": int,
            "total_updated": int,
            "total_failed": int,
            "backup_info": dict | None,
            "projects": {project_name: update_results, ...}
        }
    """
    # Create backup if requested
    backup_info = None
    if backup_first and not dry_run:
        if not BACKUP_AVAILABLE:
            logger.error("❌ Backup requested but backup_project.py not available")
            return {
                "total_projects": 0,
                "updated_projects": 0,
                "total_updated": 0,
                "total_failed": 0,
                "backup_info": {"status": "failed", "message": "Backup module not available"},
                "projects": {}
            }

        if verbose:
            print("📦 Creating backup before updates...")

        # Type guard for Pyright (backup_all_projects is only defined if BACKUP_AVAILABLE)
        if BACKUP_AVAILABLE:
            try:
                backup_result = backup_all_projects(output_dir=None, verify=True)
                backup_info = {
                    "status": "success",
                    "backup_file": backup_result["backup_file"],
                    "timestamp": backup_result["timestamp"]
                }
                if verbose:
                    print(f"✅ Backup created: {backup_result['backup_file']}")
                    print()
            except Exception as e:
                logger.error(f"❌ Backup failed: {e}")
                backup_info = {"status": "failed", "message": str(e)}
                if verbose:
                    print(f"⚠️  Continuing without backup (use Ctrl+C to abort)")
                    time.sleep(2)

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
            "backup_info": backup_info,
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
        "backup_info": backup_info,
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
        if backup_info and backup_info.get("status") == "success":
            print(f"  Backup: {backup_info['backup_file']}")

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


def smart_detect_all_projects(
    dry_run=False,
    verbose=True,
    backup_first=False,
    global_rate_limit=True,
):
    """Run smart change detection across ALL projects with consolidated reporting.

    Unlike the simple --smart loop in main(), this function:
    1. Aggregates changes across all projects into a single consolidated report
    2. Applies a global rate limit budget shared across projects (not per-project)
    3. Generates a consolidated change summary report as markdown
    4. Optionally backs up before running detection

    Args:
        dry_run: If True, preview changes without triggering pipelines.
        verbose: If True, print progress.
        backup_first: If True, create backup before detection.
        global_rate_limit: If True, apply a single global rate limit across
            all projects (default). When False, each project manages its own
            rate limiting (legacy behavior).

    Returns:
        Dictionary with consolidated results:
        {
            "total_projects": int,
            "projects_with_changes": int,
            "total_new_clearances": int,
            "total_new_recalls": int,
            "total_field_changes": int,
            "total_product_codes_checked": int,
            "total_api_calls": int,
            "projects": {project_name: detect_changes_result, ...},
            "consolidated_changes": [
                {
                    "project": str,
                    "product_code": str,
                    "change_type": str,
                    "count": int,
                    "new_items": [...],
                }
            ],
            "report_path": str | None,
            "backup_info": dict | None,
        }
    """
    # Create backup if requested
    backup_info = None
    if backup_first and not dry_run:
        if not BACKUP_AVAILABLE:
            logger.error("Backup requested but backup_project.py not available")
            return {
                "total_projects": 0,
                "projects_with_changes": 0,
                "total_new_clearances": 0,
                "total_new_recalls": 0,
                "total_field_changes": 0,
                "total_product_codes_checked": 0,
                "total_api_calls": 0,
                "projects": {},
                "consolidated_changes": [],
                "report_path": None,
                "backup_info": {"status": "failed", "message": "Backup module not available"},
            }

        if verbose:
            print("Creating backup before smart detection...")

        # Type guard for Pyright (backup_all_projects is only defined if BACKUP_AVAILABLE)
        if BACKUP_AVAILABLE:
            try:
                backup_result = backup_all_projects(output_dir=None, verify=True)
                backup_info = {
                    "status": "success",
                    "backup_file": backup_result["backup_file"],
                    "timestamp": backup_result["timestamp"],
                }
                if verbose:
                    print(f"Backup created: {backup_result['backup_file']}")
                    print()
            except Exception as e:
                logger.error("Backup failed: %s", e)
                backup_info = {"status": "failed", "message": str(e)}
                if verbose:
                    print("Warning: Continuing without backup (use Ctrl+C to abort)")
                    time.sleep(2)

    # Discover projects
    projects = find_all_projects()
    if not projects:
        if verbose:
            print("No projects found. Create a project first with /fda-tools:extract.")
        return {
            "total_projects": 0,
            "projects_with_changes": 0,
            "total_new_clearances": 0,
            "total_new_recalls": 0,
            "total_field_changes": 0,
            "total_product_codes_checked": 0,
            "total_api_calls": 0,
            "projects": {},
            "consolidated_changes": [],
            "report_path": None,
            "backup_info": backup_info,
        }

    if verbose:
        print(f"Smart detection across {len(projects)} project(s)...")
        if global_rate_limit:
            print("  Global rate limiting: ON (shared budget across all projects)")
        print()

    # Single shared FDAClient for global rate limiting across projects
    client = FDAClient()

    # Aggregate results
    all_project_results = {}
    consolidated_changes = []
    total_new_clearances = 0
    total_new_recalls = 0
    total_field_changes = 0
    total_product_codes_checked = 0
    projects_with_changes = 0
    api_call_count = 0

    for idx, (project_name, _project_dir, _manifest_path) in enumerate(projects, 1):
        if verbose:
            print(f"[{idx}/{len(projects)}] Project: {project_name}")

        result = detect_changes(
            project_name,
            client=client,
            verbose=verbose,
        )
        all_project_results[project_name] = result

        project_new = result.get("total_new_clearances", 0)
        project_recalls = result.get("total_new_recalls", 0)
        project_field = result.get("total_field_changes", 0)
        project_codes = result.get("product_codes_checked", 0)

        total_new_clearances += project_new
        total_new_recalls += project_recalls
        total_field_changes += project_field
        total_product_codes_checked += project_codes

        # Each product code triggers ~2 API calls (clearances + recalls)
        api_call_count += project_codes * 2

        if project_new > 0 or project_recalls > 0 or project_field > 0:
            projects_with_changes += 1

        # Flatten changes into consolidated list
        for change in result.get("changes", []):
            consolidated_changes.append({
                "project": project_name,
                "product_code": change.get("product_code", ""),
                "change_type": change.get("change_type", ""),
                "count": change.get("count", 0),
                "new_items": change.get("new_items", []),
                "details": change.get("details", {}),
            })

        if verbose:
            if project_new > 0 or project_recalls > 0:
                print(f"  -> {project_new} new clearance(s), {project_recalls} new recall(s)")
            else:
                print("  -> No changes")
            print()

        # Global rate limit: pause between projects (not within detect_changes,
        # which already pauses between product codes)
        if global_rate_limit and idx < len(projects):
            time.sleep(RATE_LIMIT_DELAY)

    # Generate consolidated report
    report_path = _generate_consolidated_smart_report(
        all_project_results,
        consolidated_changes,
        total_new_clearances,
        total_new_recalls,
        total_field_changes,
        total_product_codes_checked,
        api_call_count,
        dry_run=dry_run,
    )

    overall_results = {
        "total_projects": len(projects),
        "projects_with_changes": projects_with_changes,
        "total_new_clearances": total_new_clearances,
        "total_new_recalls": total_new_recalls,
        "total_field_changes": total_field_changes,
        "total_product_codes_checked": total_product_codes_checked,
        "total_api_calls": api_call_count,
        "projects": all_project_results,
        "consolidated_changes": consolidated_changes,
        "report_path": report_path,
        "backup_info": backup_info,
    }

    if verbose:
        _print_consolidated_smart_summary(overall_results)

    return overall_results


def _generate_consolidated_smart_report(
    project_results,
    consolidated_changes,
    total_new_clearances,
    total_new_recalls,
    total_field_changes,
    total_product_codes_checked,
    api_call_count,
    dry_run=False,
):
    """Generate a consolidated markdown report for --smart --all-projects.

    Writes the report to ~/fda-510k-data/reports/smart_detection_report.md.

    Returns:
        str: Path to the generated report, or None if writing failed.
    """
    now = datetime.now(timezone.utc).isoformat()
    report_dir = Path(os.path.expanduser("~/fda-510k-data/reports"))

    try:
        report_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.warning("Could not create reports directory: %s", e)
        return None

    report_path = report_dir / "smart_detection_report.md"

    lines = [
        "# FDA Smart Detection -- Consolidated Report",
        "",
        f"**Generated:** {now}",
        f"**Mode:** {'DRY RUN' if dry_run else 'LIVE'}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Projects scanned | {len(project_results)} |",
        f"| Product codes checked | {total_product_codes_checked} |",
        f"| API calls made | {api_call_count} |",
        f"| New clearances | {total_new_clearances} |",
        f"| New recalls | {total_new_recalls} |",
        f"| Field changes | {total_field_changes} |",
        "",
    ]

    # Group changes by project
    changes_by_project = {}
    for change in consolidated_changes:
        proj = change["project"]
        if proj not in changes_by_project:
            changes_by_project[proj] = []
        changes_by_project[proj].append(change)

    if changes_by_project:
        lines.append("## Changes by Project")
        lines.append("")

        for project_name in sorted(changes_by_project.keys()):
            changes = changes_by_project[project_name]
            lines.append(f"### {project_name}")
            lines.append("")

            for change in changes:
                ct = change["change_type"]
                pc = change["product_code"]
                count = change["count"]
                lines.append(f"- **{pc}**: {ct} ({count})")

                if ct == "new_clearances":
                    for item in change.get("new_items", [])[:5]:
                        k = item.get("k_number", "")
                        name = item.get("device_name", "")[:60]
                        date = item.get("decision_date", "")
                        lines.append(f"  - {k}: {name} ({date})")
                    remaining = len(change.get("new_items", [])) - 5
                    if remaining > 0:
                        lines.append(f"  - ... and {remaining} more")

            lines.append("")

        # Cross-project product code summary
        lines.append("## Cross-Project Product Code Summary")
        lines.append("")
        lines.append("| Product Code | Projects | New Clearances | New Recalls |")
        lines.append("|-------------|----------|----------------|-------------|")

        pc_summary = {}
        for change in consolidated_changes:
            pc = change["product_code"]
            proj = change["project"]
            if pc not in pc_summary:
                pc_summary[pc] = {"projects": set(), "clearances": 0, "recalls": 0}
            pc_summary[pc]["projects"].add(proj)
            if change["change_type"] == "new_clearances":
                pc_summary[pc]["clearances"] += change["count"]
            elif change["change_type"] == "new_recalls":
                pc_summary[pc]["recalls"] += change["count"]

        for pc in sorted(pc_summary.keys()):
            info = pc_summary[pc]
            proj_list = ", ".join(sorted(info["projects"]))
            lines.append(
                f"| {pc} | {proj_list} | {info['clearances']} | {info['recalls']} |"
            )
        lines.append("")

    else:
        lines.append("## Changes")
        lines.append("")
        lines.append("No changes detected across any project. All data is up to date.")
        lines.append("")

    # Project status table
    lines.append("## Project Status")
    lines.append("")
    lines.append("| Project | Status | Product Codes | New Clearances | New Recalls |")
    lines.append("|---------|--------|--------------|----------------|-------------|")

    for project_name in sorted(project_results.keys()):
        result = project_results[project_name]
        status = result.get("status", "unknown")
        codes = result.get("product_codes_checked", 0)
        nc = result.get("total_new_clearances", 0)
        nr = result.get("total_new_recalls", 0)
        lines.append(f"| {project_name} | {status} | {codes} | {nc} | {nr} |")

    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by FDA Smart Detection (update_manager.py --smart --all-projects) on {now}*")
    lines.append("")

    report_text = "\n".join(lines)

    try:
        with open(report_path, "w") as f:
            f.write(report_text)
        return str(report_path)
    except OSError as e:
        logger.warning("Could not write consolidated report: %s", e)
        return None


def _print_consolidated_smart_summary(results):
    """Print a formatted summary of --smart --all-projects results."""
    print()
    print("=" * 60)
    print("FDA Smart Detection -- Consolidated Summary")
    print("=" * 60)
    print(f"  Projects scanned:       {results['total_projects']}")
    print(f"  Projects with changes:  {results['projects_with_changes']}")
    print(f"  Product codes checked:  {results['total_product_codes_checked']}")
    print(f"  API calls made:         {results['total_api_calls']}")
    print(f"  New clearances:         {results['total_new_clearances']}")
    print(f"  New recalls:            {results['total_new_recalls']}")
    print(f"  Field changes:          {results['total_field_changes']}")

    if results.get("report_path"):
        print(f"  Report:                 {results['report_path']}")

    if results.get("backup_info") and results["backup_info"].get("status") == "success":
        print(f"  Backup:                 {results['backup_info']['backup_file']}")

    # Show per-project breakdown
    projects_with_changes = {
        name: res
        for name, res in results["projects"].items()
        if res.get("total_new_clearances", 0) > 0
        or res.get("total_new_recalls", 0) > 0
        or res.get("total_field_changes", 0) > 0
    }

    if projects_with_changes:
        print()
        print("Projects with changes:")
        for name in sorted(projects_with_changes.keys()):
            res = projects_with_changes[name]
            nc = res.get("total_new_clearances", 0)
            nr = res.get("total_new_recalls", 0)
            nf = res.get("total_field_changes", 0)
            parts = []
            if nc > 0:
                parts.append(f"{nc} clearances")
            if nr > 0:
                parts.append(f"{nr} recalls")
            if nf > 0:
                parts.append(f"{nf} field changes")
            print(f"  {name}: {', '.join(parts)}")
    else:
        print()
        print("No changes detected across any project.")

    print("=" * 60)


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
    parser.add_argument("--backup", action="store_true",
                        help="Create backup before updating (use with --update-all)")
    parser.add_argument("--clean-cache", action="store_true", dest="clean_cache",
                        help="Remove expired files from system API cache")
    parser.add_argument("--smart", action="store_true",
                        help="Smart change detection: compare live API against fingerprints")
    parser.add_argument("--all-projects", action="store_true", dest="all_projects",
                        help="Run smart detection across ALL projects with consolidated "
                             "reporting and global rate limiting (FDA-38)")
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
        results = update_all_projects(dry_run=args.dry_run, verbose=verbose, backup_first=args.backup)
        if not verbose:
            print(json.dumps(results, indent=2))

    elif args.clean_cache:
        results = clean_system_cache(verbose=verbose)
        if not verbose:
            print(json.dumps(results, indent=2))

    elif args.smart:
        # Smart change detection mode
        if args.all_projects:
            # FDA-38: Smart detection across ALL projects with consolidated reporting
            results = smart_detect_all_projects(
                dry_run=args.dry_run,
                verbose=verbose,
                backup_first=args.backup,
                global_rate_limit=True,
            )
            if not verbose:
                # Strip non-serializable items for JSON output
                json_results = {
                    k: v for k, v in results.items()
                    if k != "report_path" or v is not None
                }
                print(json.dumps(json_results, indent=2))

        elif not args.project:
            # Legacy: Smart mode on all projects (basic loop, no consolidated report)
            projects = find_all_projects()
            if not projects:
                if verbose:
                    print("No projects found. Create a project first with /fda-tools:extract.")
                sys.exit(0)

            all_results = {}
            total_new = 0
            client = FDAClient()

            for project_name, _project_dir, _manifest_path in projects:
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
                print()
                print("TIP: Use --smart --all-projects for consolidated reporting (FDA-38)")
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
