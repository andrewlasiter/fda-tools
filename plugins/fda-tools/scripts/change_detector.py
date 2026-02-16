#!/usr/bin/env python3
"""
FDA Smart Change Detector -- Detect new 510(k) clearances and data changes.

Compares live FDA API data against stored fingerprints in data_manifest.json
to identify new clearances, recalls, and other changes for a product code.
Optionally triggers the batchfetch + extraction pipeline for new devices.

Fingerprints are stored in the project's data_manifest.json under the
"fingerprints" key, enabling persistent tracking across sessions.

Usage:
    from change_detector import detect_changes, find_new_clearances, trigger_pipeline

    changes = detect_changes("my_project", client, verbose=True)
    new_k = find_new_clearances("DQY", known_k_numbers, client, max_fetch=100)
    trigger_pipeline("my_project", new_k, "DQY", dry_run=False, verbose=True)

    # CLI usage:
    python3 change_detector.py --project my_project
    python3 change_detector.py --project my_project --dry-run
    python3 change_detector.py --project my_project --product-code DQY --max-fetch 200
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fda_api_client import FDAClient
from fda_data_store import get_projects_dir, load_manifest, save_manifest


def _run_subprocess(
    cmd: List[str],
    step_name: str,
    timeout_seconds: int,
    cwd: str,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Run a subprocess with standardized error handling and user-friendly messages.

    Centralizes the try/except pattern for subprocess calls used by the
    pipeline trigger functions, providing consistent timeout messages,
    error reporting, and verbose output.

    Args:
        cmd: Command and arguments to execute.
        step_name: Human-readable name for the step (e.g., 'batchfetch').
        timeout_seconds: Maximum seconds before killing the process.
        cwd: Working directory for the subprocess.
        verbose: If True, print progress information.

    Returns:
        Dictionary with step result:
        {
            "step": str,
            "status": "success" | "error" | "timeout",
            "returncode": int (only on success/error),
            "output": str,
            "error": str (only on failure),
        }
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=cwd,
        )
        step_result = {
            "step": step_name,
            "status": "success" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "output": result.stdout[-500:] if result.stdout else "",
            "error": result.stderr[-500:] if result.stderr else "",
        }
        if verbose:
            status = "success" if result.returncode == 0 else "error"
            print(f"    {step_name}: {status}")
        return step_result
    except subprocess.TimeoutExpired:
        timeout_minutes = timeout_seconds / 60
        message = (
            f"Process timed out after {timeout_seconds} seconds. "
            f"Possible causes: (1) FDA API may be slow or unreachable -- "
            f"check your internet connection; (2) Large dataset requires "
            f"more time -- consider increasing the timeout; (3) The API "
            f"server may be under maintenance -- try again later."
        )
        step_result = {
            "step": step_name,
            "status": "timeout",
            "output": message,
        }
        if verbose:
            print(f"    {step_name}: TIMEOUT ({timeout_minutes:.0f}min)")
            print(f"      Suggestion: Check API connectivity or retry later.")
        return step_result
    except OSError as e:
        step_result = {
            "step": step_name,
            "status": "error",
            "output": str(e),
        }
        if verbose:
            print(f"    {step_name}: ERROR ({e})")
        return step_result


def _load_fingerprint(
    project_dir: str, product_code: str
) -> Optional[Dict[str, Any]]:
    """Load a stored fingerprint for a product code from the project manifest.

    Fingerprints are stored in the project's data_manifest.json under the
    "fingerprints" key. Each product code has its own fingerprint entry.

    Args:
        project_dir: Absolute path to the project directory.
        product_code: FDA product code (e.g., 'DQY').

    Returns:
        Fingerprint dictionary or None if no fingerprint exists.
        Fingerprint structure:
        {
            "last_checked": "2026-02-16T10:00:00+00:00",
            "clearance_count": 147,
            "latest_k_number": "K251234",
            "latest_decision_date": "20260115",
            "recall_count": 3,
            "known_k_numbers": ["K251234", "K250987", ...]
        }
    """
    manifest = load_manifest(project_dir)
    fingerprints = manifest.get("fingerprints", {})
    return fingerprints.get(product_code.upper())


def _save_fingerprint(
    project_dir: str, product_code: str, fingerprint: Dict[str, Any]
) -> None:
    """Save a fingerprint for a product code to the project manifest.

    Fingerprints are persisted in data_manifest.json as a nested dict keyed
    by product code. This JSON-based approach works well for the current
    scale of up to ~50 product codes per project.

    Args:
        project_dir: Absolute path to the project directory.
        product_code: FDA product code (e.g., 'DQY').
        fingerprint: Fingerprint dictionary to store.

    .. note::
        TODO (Scalability): If fingerprint storage grows beyond ~100 product
        codes per project, consider migrating to SQLite for better
        read/write performance and concurrent access. The current JSON
        approach requires full file read/write on each update, which
        becomes a bottleneck at scale. A migration path would involve:
        1. Creating a fingerprints.db alongside data_manifest.json
        2. Using a simple key-value table (product_code TEXT PK, data JSON)
        3. Keeping data_manifest.json as the authoritative source for
           non-fingerprint data (queries, product_codes, etc.)
    """
    manifest = load_manifest(project_dir)
    if "fingerprints" not in manifest:
        manifest["fingerprints"] = {}
    manifest["fingerprints"][product_code.upper()] = fingerprint
    save_manifest(project_dir, manifest)


def find_new_clearances(
    product_code: str,
    known_k_numbers: List[str],
    client: Optional[FDAClient] = None,
    max_fetch: int = 100,
) -> List[Dict[str, Any]]:
    """Query the FDA API and return clearances not in the known set.

    Args:
        product_code: FDA product code (e.g., 'DQY').
        known_k_numbers: List of K-numbers already tracked.
        client: FDAClient instance (created if None).
        max_fetch: Maximum number of clearances to fetch from API.

    Returns:
        List of new clearance records (dicts with k_number, device_name,
        applicant, decision_date, decision_code, clearance_type).
    """
    if client is None:
        client = FDAClient()

    known_set = {k.upper() for k in known_k_numbers}

    result = client.get_clearances(product_code, limit=max_fetch, sort="decision_date:desc")

    if result.get("degraded") or result.get("error"):
        return []

    new_clearances = []
    for item in result.get("results", []):
        k_number = item.get("k_number", "").upper()
        if k_number and k_number not in known_set:
            new_clearances.append({
                "k_number": k_number,
                "device_name": item.get("device_name", ""),
                "applicant": item.get("applicant", ""),
                "decision_date": item.get("decision_date", ""),
                "decision_code": item.get("decision_code", ""),
                "clearance_type": item.get("clearance_type", ""),
                "product_code": item.get("product_code", product_code),
            })

    return new_clearances


def detect_changes(
    project_name: str,
    client: Optional[FDAClient] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Compare live FDA API data against stored fingerprints for a project.

    Checks all product codes associated with the project and detects:
    - New 510(k) clearances
    - Changes in total clearance count
    - New recall events
    - Changes in recall count

    Args:
        project_name: Name of the project directory.
        client: FDAClient instance (created if None).
        verbose: If True, print progress information.

    Returns:
        Dictionary with change detection results:
        {
            "project": str,
            "status": "completed" | "error" | "no_fingerprints",
            "checked_at": str (ISO timestamp),
            "product_codes_checked": int,
            "changes": [
                {
                    "product_code": str,
                    "change_type": "new_clearances" | "new_recalls" | "count_change",
                    "details": {...},
                    "new_items": [...],
                }
            ],
            "total_new_clearances": int,
            "total_new_recalls": int,
        }
    """
    if client is None:
        client = FDAClient()

    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, project_name)

    if not os.path.exists(project_dir):
        return {
            "project": project_name,
            "status": "error",
            "error": f"Project directory not found: {project_dir}",
            "changes": [],
        }

    manifest = load_manifest(project_dir)
    product_codes = manifest.get("product_codes", [])
    fingerprints = manifest.get("fingerprints", {})

    # If no product codes and no fingerprints, nothing to check
    if not product_codes and not fingerprints:
        return {
            "project": project_name,
            "status": "no_fingerprints",
            "message": "No product codes or fingerprints found. Run batchfetch first.",
            "changes": [],
            "total_new_clearances": 0,
            "total_new_recalls": 0,
        }

    # Merge product_codes from both sources
    codes_to_check = set(pc.upper() for pc in product_codes)
    codes_to_check.update(fingerprints.keys())

    if verbose:
        print(f"Checking {len(codes_to_check)} product code(s) for project '{project_name}'...")

    all_changes = []
    total_new_clearances = 0
    total_new_recalls = 0
    now = datetime.now(timezone.utc).isoformat()

    for idx, product_code in enumerate(sorted(codes_to_check), 1):
        if verbose:
            print(f"  [{idx}/{len(codes_to_check)}] Checking {product_code}...", end=" ")

        fp = fingerprints.get(product_code, {})
        known_k_numbers = fp.get("known_k_numbers", [])
        prev_clearance_count = fp.get("clearance_count", 0)
        prev_recall_count = fp.get("recall_count", 0)

        # -- Check clearances --
        clearance_result = client.get_clearances(
            product_code, limit=100, sort="decision_date:desc"
        )
        if clearance_result.get("degraded") or clearance_result.get("error"):
            if verbose:
                print(f"API error: {clearance_result.get('error', 'unavailable')}")
            continue

        current_total = clearance_result.get("meta", {}).get("results", {}).get("total", 0)
        current_results = clearance_result.get("results", [])

        # Find new clearances
        known_set = {k.upper() for k in known_k_numbers}
        new_clearances = []
        all_current_k_numbers = list(known_set)  # Start with existing

        for item in current_results:
            k_num = item.get("k_number", "").upper()
            if k_num:
                if k_num not in known_set:
                    new_clearances.append({
                        "k_number": k_num,
                        "device_name": item.get("device_name", ""),
                        "applicant": item.get("applicant", ""),
                        "decision_date": item.get("decision_date", ""),
                    })
                if k_num not in all_current_k_numbers:
                    all_current_k_numbers.append(k_num)

        if new_clearances:
            all_changes.append({
                "product_code": product_code,
                "change_type": "new_clearances",
                "count": len(new_clearances),
                "details": {
                    "previous_total": prev_clearance_count,
                    "current_total": current_total,
                },
                "new_items": new_clearances,
            })
            total_new_clearances += len(new_clearances)

        # -- Check recalls --
        recall_result = client.get_recalls(product_code, limit=10)
        current_recall_count = 0
        if not recall_result.get("degraded") and not recall_result.get("error"):
            current_recall_count = recall_result.get("meta", {}).get("results", {}).get("total", 0)

            if current_recall_count > prev_recall_count:
                new_recall_count = current_recall_count - prev_recall_count
                all_changes.append({
                    "product_code": product_code,
                    "change_type": "new_recalls",
                    "count": new_recall_count,
                    "details": {
                        "previous_count": prev_recall_count,
                        "current_count": current_recall_count,
                    },
                    "new_items": [],
                })
                total_new_recalls += new_recall_count

        # -- Update fingerprint --
        latest_k = ""
        latest_date = ""
        if current_results:
            latest_k = current_results[0].get("k_number", "")
            latest_date = current_results[0].get("decision_date", "")

        new_fingerprint = {
            "last_checked": now,
            "clearance_count": current_total,
            "latest_k_number": latest_k,
            "latest_decision_date": latest_date,
            "recall_count": current_recall_count,
            "known_k_numbers": sorted(set(all_current_k_numbers)),
        }
        _save_fingerprint(project_dir, product_code, new_fingerprint)

        if verbose:
            if new_clearances:
                print(f"{len(new_clearances)} new clearance(s) found")
            else:
                print("no changes")

        # Rate limiting between product codes
        if idx < len(codes_to_check):
            time.sleep(0.5)

    return {
        "project": project_name,
        "status": "completed",
        "checked_at": now,
        "product_codes_checked": len(codes_to_check),
        "changes": all_changes,
        "total_new_clearances": total_new_clearances,
        "total_new_recalls": total_new_recalls,
    }


def trigger_pipeline(
    project_name: str,
    new_k_numbers: List[str],
    product_code: str,
    dry_run: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Trigger batchfetch + extraction pipeline for newly detected K-numbers.

    Uses subprocess to invoke the existing batchfetch and extraction scripts
    for the new devices. This ensures the structured cache is updated with
    the new 510(k) summaries.

    Args:
        project_name: Name of the project.
        new_k_numbers: List of new K-numbers to process.
        product_code: FDA product code for context.
        dry_run: If True, show what would be done without executing.
        verbose: If True, print progress information.

    Returns:
        Dictionary with pipeline results:
        {
            "project": str,
            "product_code": str,
            "k_numbers_processed": int,
            "status": "completed" | "dry_run" | "error" | "skipped",
            "steps": [{"step": str, "status": str, "output": str}],
        }
    """
    if not new_k_numbers:
        return {
            "project": project_name,
            "product_code": product_code,
            "k_numbers_processed": 0,
            "status": "skipped",
            "message": "No new K-numbers to process.",
            "steps": [],
        }

    scripts_dir = Path(__file__).resolve().parent
    steps = []

    if dry_run:
        if verbose:
            print(f"DRY RUN: Would process {len(new_k_numbers)} new K-numbers for {product_code}:")
            for k in new_k_numbers[:10]:
                print(f"  - {k}")
            if len(new_k_numbers) > 10:
                print(f"  ... and {len(new_k_numbers) - 10} more")
        return {
            "project": project_name,
            "product_code": product_code,
            "k_numbers_processed": len(new_k_numbers),
            "status": "dry_run",
            "k_numbers": new_k_numbers,
            "steps": [{"step": "dry_run", "status": "preview", "output": f"Would process {len(new_k_numbers)} K-numbers"}],
        }

    if verbose:
        print(f"Triggering pipeline for {len(new_k_numbers)} new K-numbers ({product_code})...")

    # Step 1: Fetch new device data via batchfetch
    batchfetch_script = scripts_dir / "batchfetch.py"
    if batchfetch_script.exists():
        cmd = [
            sys.executable,
            str(batchfetch_script),
            "--product-codes", product_code,
            "--years", "2020-2026",
            "--date-range", "pmn96cur",
        ]

        if verbose:
            print(f"  Step 1: Running batchfetch for {product_code}...")

        step_result = _run_subprocess(
            cmd, "batchfetch", timeout_seconds=300,
            cwd=str(scripts_dir), verbose=verbose,
        )
        steps.append(step_result)
    else:
        steps.append({
            "step": "batchfetch",
            "status": "skipped",
            "output": f"Script not found: {batchfetch_script}",
        })

    # Step 2: Build structured cache for new entries
    build_cache_script = scripts_dir / "build_structured_cache.py"
    if build_cache_script.exists():
        cache_dir = Path(os.path.expanduser("~/fda-510k-data/extraction/cache"))
        cmd = [
            sys.executable,
            str(build_cache_script),
            "--cache-dir", str(cache_dir),
        ]

        if verbose:
            print("  Step 2: Building structured cache...")

        step_result = _run_subprocess(
            cmd, "build_structured_cache", timeout_seconds=600,
            cwd=str(scripts_dir), verbose=verbose,
        )
        steps.append(step_result)
    else:
        steps.append({
            "step": "build_structured_cache",
            "status": "skipped",
            "output": f"Script not found: {build_cache_script}",
        })

    # Determine overall status
    step_statuses = [s.get("status") for s in steps]
    if all(s == "success" for s in step_statuses):
        overall_status = "completed"
    elif any(s == "success" for s in step_statuses):
        overall_status = "partial"
    else:
        overall_status = "error"

    if verbose:
        print(f"  Pipeline result: {overall_status}")

    return {
        "project": project_name,
        "product_code": product_code,
        "k_numbers_processed": len(new_k_numbers),
        "status": overall_status,
        "steps": steps,
    }


def main():
    """CLI entry point for smart change detection."""
    parser = argparse.ArgumentParser(
        description="FDA Smart Change Detector -- Detect new clearances and data changes"
    )
    parser.add_argument(
        "--project", required=True,
        help="Project name to check for changes"
    )
    parser.add_argument(
        "--product-code", dest="product_code",
        help="Specific product code to check (default: all project codes)"
    )
    parser.add_argument(
        "--max-fetch", type=int, default=100, dest="max_fetch",
        help="Maximum clearances to fetch per product code (default: 100)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="Preview changes without triggering pipeline"
    )
    parser.add_argument(
        "--trigger", action="store_true",
        help="Automatically trigger pipeline for new clearances"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Minimal output (JSON only)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()
    verbose = not args.quiet

    client = FDAClient()

    # Detect changes
    result = detect_changes(
        project_name=args.project,
        client=client,
        verbose=verbose,
    )

    if result.get("status") == "error":
        if args.json or args.quiet:
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    # Display results
    if args.json or args.quiet:
        print(json.dumps(result, indent=2))
    else:
        print()
        print("=" * 60)
        print("Smart Change Detection Results")
        print("=" * 60)
        print(f"Project: {result.get('project')}")
        print(f"Product codes checked: {result.get('product_codes_checked', 0)}")
        print(f"New clearances found: {result.get('total_new_clearances', 0)}")
        print(f"New recalls found: {result.get('total_new_recalls', 0)}")
        print()

        changes = result.get("changes", [])
        if changes:
            print("Changes Detected:")
            print("-" * 40)
            for change in changes:
                pc = change.get("product_code", "")
                ct = change.get("change_type", "")
                count = change.get("count", 0)
                print(f"  {pc}: {ct} ({count} new)")

                if ct == "new_clearances":
                    for item in change.get("new_items", [])[:5]:
                        k = item.get("k_number", "")
                        name = item.get("device_name", "")[:50]
                        date = item.get("decision_date", "")
                        print(f"    - {k}: {name} ({date})")
                    remaining = len(change.get("new_items", [])) - 5
                    if remaining > 0:
                        print(f"    ... and {remaining} more")
            print()
        else:
            print("No changes detected. All data is up to date.")
            print()

    # Optionally trigger pipeline
    if args.trigger and result.get("total_new_clearances", 0) > 0:
        for change in result.get("changes", []):
            if change.get("change_type") == "new_clearances":
                new_k = [item["k_number"] for item in change.get("new_items", [])]
                pc = change.get("product_code", "")
                pipeline_result = trigger_pipeline(
                    args.project, new_k, pc,
                    dry_run=args.dry_run, verbose=verbose,
                )
                if args.json or args.quiet:
                    print(json.dumps(pipeline_result, indent=2))


if __name__ == "__main__":
    main()
