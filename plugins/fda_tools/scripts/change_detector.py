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
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import sibling modules
from fda_api_client import FDAClient
from fda_data_store import get_projects_dir, load_manifest, save_manifest
from fda_tools.lib.subprocess_helpers import run_subprocess  # type: ignore

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


# ------------------------------------------------------------------
# SQLite fingerprint storage (FDA-40)
# ------------------------------------------------------------------


def _get_sqlite_path(project_dir: str) -> str:
    """Return the path to the SQLite fingerprint database.

    Args:
        project_dir: Absolute path to the project directory.

    Returns:
        Absolute path to fingerprints.db.
    """
    return os.path.join(project_dir, "fingerprints.db")


def _init_sqlite_db(db_path: str) -> sqlite3.Connection:
    """Initialize the SQLite fingerprint database.

    Creates the key-value table if it does not exist.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        sqlite3.Connection instance.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            product_code TEXT PRIMARY KEY,
            data         JSON NOT NULL,
            updated_at   TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS migration_meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def _migrate_json_to_sqlite(project_dir: str) -> int:
    """Migrate existing JSON fingerprints to SQLite on first use.

    Reads fingerprints from data_manifest.json and inserts them into
    fingerprints.db. Existing SQLite entries are preserved (INSERT OR IGNORE).
    Records migration timestamp in migration_meta table.

    Args:
        project_dir: Absolute path to the project directory.

    Returns:
        Number of fingerprints migrated.
    """
    db_path = _get_sqlite_path(project_dir)
    conn = _init_sqlite_db(db_path)

    try:
        # Check if already migrated
        row = conn.execute(
            "SELECT value FROM migration_meta WHERE key = 'migrated_from_json'"
        ).fetchone()
        if row is not None:
            conn.close()
            return 0

        # Load JSON fingerprints
        manifest = load_manifest(project_dir)
        fingerprints = manifest.get("fingerprints", {})

        migrated = 0
        now = datetime.now(timezone.utc).isoformat()

        for product_code, fp_data in fingerprints.items():
            conn.execute(
                """INSERT OR IGNORE INTO fingerprints
                   (product_code, data, updated_at) VALUES (?, ?, ?)""",
                (product_code.upper(), json.dumps(fp_data), now),
            )
            migrated += 1

        # Record migration
        conn.execute(
            """INSERT OR REPLACE INTO migration_meta (key, value) VALUES (?, ?)""",
            ("migrated_from_json", now),
        )
        conn.execute(
            """INSERT OR REPLACE INTO migration_meta (key, value) VALUES (?, ?)""",
            ("migrated_count", str(migrated)),
        )
        conn.commit()
        logger.info(
            "Migrated %d fingerprint(s) from JSON to SQLite at %s",
            migrated, db_path,
        )
        return migrated
    finally:
        conn.close()


def _load_fingerprint_sqlite(
    project_dir: str, product_code: str
) -> Optional[Dict[str, Any]]:
    """Load a fingerprint from the SQLite database.

    Args:
        project_dir: Absolute path to the project directory.
        product_code: FDA product code (e.g., 'DQY').

    Returns:
        Fingerprint dictionary or None if not found.
    """
    db_path = _get_sqlite_path(project_dir)
    if not os.path.exists(db_path):
        return None

    conn = _init_sqlite_db(db_path)
    try:
        row = conn.execute(
            "SELECT data FROM fingerprints WHERE product_code = ?",
            (product_code.upper(),),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])
    except (sqlite3.Error, json.JSONDecodeError) as e:
        logger.warning("Error loading fingerprint from SQLite: %s", e)
        return None
    finally:
        conn.close()


def _save_fingerprint_sqlite(
    project_dir: str, product_code: str, fingerprint: Dict[str, Any]
) -> None:
    """Save a fingerprint to the SQLite database.

    Uses INSERT OR REPLACE for upsert semantics.

    Args:
        project_dir: Absolute path to the project directory.
        product_code: FDA product code (e.g., 'DQY').
        fingerprint: Fingerprint dictionary to store.
    """
    db_path = _get_sqlite_path(project_dir)
    conn = _init_sqlite_db(db_path)
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT OR REPLACE INTO fingerprints
               (product_code, data, updated_at) VALUES (?, ?, ?)""",
            (product_code.upper(), json.dumps(fingerprint), now),
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error("Error saving fingerprint to SQLite: %s", e)
    finally:
        conn.close()


def _list_fingerprints_sqlite(project_dir: str) -> Dict[str, Dict[str, Any]]:
    """List all fingerprints from the SQLite database.

    Args:
        project_dir: Absolute path to the project directory.

    Returns:
        Dict mapping product_code to fingerprint data.
    """
    db_path = _get_sqlite_path(project_dir)
    if not os.path.exists(db_path):
        return {}

    conn = _init_sqlite_db(db_path)
    try:
        rows = conn.execute(
            "SELECT product_code, data FROM fingerprints ORDER BY product_code"
        ).fetchall()
        result = {}
        for pc, data_json in rows:
            try:
                result[pc] = json.loads(data_json)
            except json.JSONDecodeError:
                logger.warning("Corrupted fingerprint for %s in SQLite", pc)
        return result
    except sqlite3.Error as e:
        logger.warning("Error listing fingerprints from SQLite: %s", e)
        return {}
    finally:
        conn.close()


def _delete_fingerprint_sqlite(project_dir: str, product_code: str) -> bool:
    """Delete a fingerprint from the SQLite database.

    Args:
        project_dir: Absolute path to the project directory.
        product_code: FDA product code.

    Returns:
        True if a row was deleted.
    """
    db_path = _get_sqlite_path(project_dir)
    if not os.path.exists(db_path):
        return False

    conn = _init_sqlite_db(db_path)
    try:
        cursor = conn.execute(
            "DELETE FROM fingerprints WHERE product_code = ?",
            (product_code.upper(),),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.warning("Error deleting fingerprint from SQLite: %s", e)
        return False
    finally:
        conn.close()


# ------------------------------------------------------------------
# Unified fingerprint access (respects --use-sqlite flag)
# ------------------------------------------------------------------

# Module-level flag; set via CLI --use-sqlite or programmatic call
_USE_SQLITE: bool = False


def set_use_sqlite(enabled: bool) -> None:
    """Enable or disable SQLite fingerprint storage globally.

    When enabled, fingerprint reads and writes use fingerprints.db.
    When disabled (default), fingerprint reads and writes use
    data_manifest.json (original behavior).

    On first SQLite use, existing JSON fingerprints are automatically
    migrated to SQLite.

    Args:
        enabled: True to use SQLite, False for JSON.
    """
    global _USE_SQLITE
    _USE_SQLITE = enabled


def load_fingerprint(
    project_dir: str, product_code: str
) -> Optional[Dict[str, Any]]:
    """Load a fingerprint using the active storage backend.

    Delegates to SQLite or JSON based on the _USE_SQLITE flag.

    Args:
        project_dir: Absolute path to the project directory.
        product_code: FDA product code (e.g., 'DQY').

    Returns:
        Fingerprint dictionary or None if not found.
    """
    if _USE_SQLITE:
        # Ensure migration on first use
        _migrate_json_to_sqlite(project_dir)
        return _load_fingerprint_sqlite(project_dir, product_code)
    return _load_fingerprint(project_dir, product_code)


def save_fingerprint(
    project_dir: str, product_code: str, fingerprint: Dict[str, Any]
) -> None:
    """Save a fingerprint using the active storage backend.

    When SQLite is active, writes to both SQLite and JSON for backward
    compatibility. When JSON-only, writes to JSON as before.

    Args:
        project_dir: Absolute path to the project directory.
        product_code: FDA product code (e.g., 'DQY').
        fingerprint: Fingerprint dictionary to store.
    """
    if _USE_SQLITE:
        _save_fingerprint_sqlite(project_dir, product_code, fingerprint)
        # Also write to JSON for backward compatibility
        _save_fingerprint(project_dir, product_code, fingerprint)
    else:
        _save_fingerprint(project_dir, product_code, fingerprint)


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


def _detect_field_changes(
    stored_devices: Dict[str, Dict[str, Any]],
    current_devices: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Detect field-level changes in existing K-numbers.

    Compares stored device data against current API data to identify
    fields that have changed values (e.g., decision_date corrections,
    applicant name changes due to acquisitions).

    Args:
        stored_devices: Dict mapping K-number to stored device data.
        current_devices: List of current device records from API.

    Returns:
        List of field change records:
        [
            {
                "k_number": str,
                "field": str,
                "before": Any,
                "after": Any,
            }
        ]
    """
    changes = []

    # Fields to monitor for changes
    monitored_fields = [
        "device_name",
        "applicant",
        "decision_date",
        "decision_code",
        "clearance_type",
        "product_code",
    ]

    for current in current_devices:
        k_number = current.get("k_number", "").upper()
        if not k_number or k_number not in stored_devices:
            continue

        stored = stored_devices[k_number]

        for field in monitored_fields:
            current_value = current.get(field, "")
            stored_value = stored.get(field, "")

            # Normalize for comparison
            if isinstance(current_value, str):
                current_value = current_value.strip()
            if isinstance(stored_value, str):
                stored_value = stored_value.strip()

            if current_value != stored_value:
                changes.append({
                    "k_number": k_number,
                    "field": field,
                    "before": stored_value,
                    "after": current_value,
                })

    return changes


def _generate_diff_report(
    diff_changes: List[Dict[str, Any]],
    product_code: str,
    timestamp: str,
    output_path: Optional[str] = None,
) -> str:
    """Generate markdown diff report for field-level changes.

    Args:
        diff_changes: List of field change records.
        product_code: FDA product code.
        timestamp: ISO timestamp of detection.
        output_path: Optional path to write report file.

    Returns:
        Markdown report as string.
    """
    report_lines = [
        "# FDA Field-Level Change Report",
        "",
        f"**Product Code:** {product_code}",
        f"**Detection Time:** {timestamp}",
        f"**Changes Detected:** {len(diff_changes)}",
        "",
        "## Summary",
        "",
    ]

    if not diff_changes:
        report_lines.extend([
            "No field-level changes detected in existing clearances.",
            "",
        ])
    else:
        # Group changes by K-number
        by_k_number = {}
        for change in diff_changes:
            k_num = change["k_number"]
            if k_num not in by_k_number:
                by_k_number[k_num] = []
            by_k_number[k_num].append(change)

        report_lines.append(
            f"Field changes detected across {len(by_k_number)} device(s)."
        )
        report_lines.append("")

        # Field change frequency
        field_counts = {}
        for change in diff_changes:
            field = change["field"]
            field_counts[field] = field_counts.get(field, 0) + 1

        report_lines.append("### Changes by Field Type")
        report_lines.append("")
        for field, count in sorted(field_counts.items(), key=lambda x: -x[1]):
            report_lines.append(f"- **{field}**: {count} change(s)")
        report_lines.append("")

        # Detailed changes
        report_lines.append("## Detailed Changes")
        report_lines.append("")

        for k_num in sorted(by_k_number.keys()):
            report_lines.append(f"### {k_num}")
            report_lines.append("")
            report_lines.append("| Field | Before | After |")
            report_lines.append("|-------|--------|-------|")

            for change in by_k_number[k_num]:
                field = change["field"]
                before = change["before"] or "(empty)"
                after = change["after"] or "(empty)"
                # Escape pipe characters in values
                before = str(before).replace("|", "\\|")
                after = str(after).replace("|", "\\|")
                report_lines.append(f"| {field} | {before} | {after} |")

            report_lines.append("")

    report_lines.extend([
        "## Notes",
        "",
        "- **Decision Date Changes**: May indicate FDA backdating corrections",
        "- **Applicant Changes**: Often due to company acquisitions or mergers",
        "- **Device Name Changes**: May reflect FDA database corrections",
        "- **Decision Code/Clearance Type**: Rare but can indicate reclassification",
        "",
        "---",
        f"*Generated by FDA Smart Change Detector on {timestamp}*",
        "",
    ])

    report_text = "\n".join(report_lines)

    if output_path:
        with open(output_path, "w") as f:
            f.write(report_text)

    return report_text


def detect_changes(
    project_name: str,
    client: Optional[FDAClient] = None,
    verbose: bool = False,
    detect_field_diffs: bool = False,
) -> Dict[str, Any]:
    """Compare live FDA API data against stored fingerprints for a project.

    Checks all product codes associated with the project and detects:
    - New 510(k) clearances
    - Changes in total clearance count
    - New recall events
    - Changes in recall count
    - Field-level changes in existing clearances (if detect_field_diffs=True)

    Args:
        project_name: Name of the project directory.
        client: FDAClient instance (created if None).
        verbose: If True, print progress information.
        detect_field_diffs: If True, detect field-level changes in existing devices.

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
                    "change_type": "new_clearances" | "new_recalls" | "field_changes",
                    "details": {...},
                    "new_items": [...],
                }
            ],
            "total_new_clearances": int,
            "total_new_recalls": int,
            "total_field_changes": int,
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

    # When using SQLite, also include fingerprints from the database
    if _USE_SQLITE:
        sqlite_fps = _list_fingerprints_sqlite(project_dir)
        # SQLite fingerprints take precedence (they may be newer)
        merged_fps = {**fingerprints, **sqlite_fps}
    else:
        merged_fps = fingerprints

    # If no product codes and no fingerprints, nothing to check
    if not product_codes and not merged_fps:
        return {
            "project": project_name,
            "status": "no_fingerprints",
            "message": "No product codes or fingerprints found. Run batchfetch first.",
            "changes": [],
            "total_new_clearances": 0,
            "total_new_recalls": 0,
            "total_field_changes": 0,
        }

    # Merge product_codes from both sources
    codes_to_check = set(pc.upper() for pc in product_codes)
    codes_to_check.update(merged_fps.keys())

    if verbose:
        backend = "SQLite" if _USE_SQLITE else "JSON"
        print(f"Checking {len(codes_to_check)} product code(s) for project "
              f"'{project_name}' (storage: {backend})...")

    all_changes = []
    total_new_clearances = 0
    total_new_recalls = 0
    total_field_changes = 0
    now = datetime.now(timezone.utc).isoformat()

    for idx, product_code in enumerate(sorted(codes_to_check), 1):
        if verbose:
            print(f"  [{idx}/{len(codes_to_check)}] Checking {product_code}...", end=" ")

        fp = load_fingerprint(project_dir, product_code) or {}
        known_k_numbers = fp.get("known_k_numbers", [])
        prev_clearance_count = fp.get("clearance_count", 0)
        prev_recall_count = fp.get("recall_count", 0)
        stored_device_data = fp.get("device_data", {})

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
        updated_device_data = {}

        for item in current_results:
            k_num = item.get("k_number", "").upper()
            if k_num:
                # Store device data for field diff detection
                device_record = {
                    "k_number": k_num,
                    "device_name": item.get("device_name", ""),
                    "applicant": item.get("applicant", ""),
                    "decision_date": item.get("decision_date", ""),
                    "decision_code": item.get("decision_code", ""),
                    "clearance_type": item.get("clearance_type", ""),
                    "product_code": item.get("product_code", product_code),
                }
                updated_device_data[k_num] = device_record

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

        # -- Detect field-level changes --
        if detect_field_diffs and stored_device_data:
            field_changes = _detect_field_changes(stored_device_data, current_results)
            if field_changes:
                all_changes.append({
                    "product_code": product_code,
                    "change_type": "field_changes",
                    "count": len(field_changes),
                    "details": {
                        "devices_affected": len(set(c["k_number"] for c in field_changes)),
                    },
                    "new_items": field_changes,
                })
                total_field_changes += len(field_changes)

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
            "device_data": updated_device_data,
        }
        save_fingerprint(project_dir, product_code, new_fingerprint)

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
        "total_field_changes": total_field_changes,
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

        step_result = run_command(
            cmd, "batchfetch", timeout=300,
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

        step_result = run_command(
            cmd, "build_structured_cache", timeout=600,
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
    parser.add_argument(
        "--diff-report", action="store_true", dest="diff_report",
        help="Generate markdown diff report for field-level changes"
    )
    parser.add_argument(
        "--use-sqlite", action="store_true", dest="use_sqlite",
        help="Use SQLite database (fingerprints.db) for fingerprint storage "
             "instead of JSON (data_manifest.json). On first use, existing "
             "JSON fingerprints are automatically migrated to SQLite. "
             "Recommended for projects with 100+ product codes."
    )

    args = parser.parse_args()
    verbose = not args.quiet

    # Enable SQLite storage if requested
    if args.use_sqlite:
        set_use_sqlite(True)
        if verbose:
            print("SQLite fingerprint storage enabled.")

    client = FDAClient()

    # Detect changes
    result = detect_changes(
        project_name=args.project,
        client=client,
        verbose=verbose,
        detect_field_diffs=args.diff_report,
    )

    if result.get("status") == "error":
        if args.json or args.quiet:
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    # Generate diff report if requested
    diff_report_path = None
    if args.diff_report:
        projects_dir = get_projects_dir()
        project_dir = os.path.join(projects_dir, args.project)
        diff_report_path = os.path.join(project_dir, "field_changes_report.md")

        # Collect all field changes across product codes
        all_field_changes = []
        for change in result.get("changes", []):
            if change.get("change_type") == "field_changes":
                all_field_changes.extend(change.get("new_items", []))

        if all_field_changes:
            # Generate report for all product codes
            product_codes = sorted(set(
                change.get("product_code", "")
                for change in result.get("changes", [])
            ))
            product_code_str = ", ".join(product_codes)

            _generate_diff_report(
                all_field_changes,
                product_code_str,
                result.get("checked_at", ""),
                output_path=diff_report_path,
            )
            if verbose:
                print(f"\nDiff report written to: {diff_report_path}")

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
        if args.diff_report:
            print(f"Field changes detected: {result.get('total_field_changes', 0)}")
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
                elif ct == "field_changes":
                    devices_affected = change.get("details", {}).get("devices_affected", 0)
                    print(f"    Devices affected: {devices_affected}")
                    # Show first few field changes
                    for item in change.get("new_items", [])[:3]:
                        k = item.get("k_number", "")
                        field = item.get("field", "")
                        before = item.get("before", "")[:30]
                        after = item.get("after", "")[:30]
                        print(f"    - {k}: {field} changed")
                        print(f"      '{before}' -> '{after}'")
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
