#!/usr/bin/env python3
"""
FDA Project Data Store — Context-Surviving API Cache.

Wraps fda_api_client.py with a project-level manifest (data_manifest.json)
so that commands can check "has this been fetched?" and reuse cached results
without re-querying after context compaction.

Usage:
    python3 fda_data_store.py --project NAME --query classification --product-code OVE
    python3 fda_data_store.py --project NAME --query recalls --product-code OVE
    python3 fda_data_store.py --project NAME --query events --product-code OVE [--count event_type.exact]
    python3 fda_data_store.py --project NAME --query 510k --k-number K241335
    python3 fda_data_store.py --project NAME --query 510k-batch --k-numbers K241335,K200123
    python3 fda_data_store.py --project NAME --query enforcement --product-code OVE
    python3 fda_data_store.py --project NAME --show-manifest
    python3 fda_data_store.py --project NAME --query classification --product-code OVE --refresh
"""

import argparse
import json
import logging
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone

# Import FDAClient from sibling module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fda_api_client import FDAClient

# Import manifest validator
LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB_DIR)
try:
    from manifest_validator import (  # type: ignore
        validate_manifest,
        add_schema_version,
        ValidationError,
        CURRENT_SCHEMA_VERSION,
    )
    _VALIDATOR_AVAILABLE = True
except ImportError:
    _VALIDATOR_AVAILABLE = False

# TTL tiers in hours
TTL_TIERS = {
    "classification": 168,   # 7 days — rarely changes
    "510k": 168,             # 7 days — historical data
    "510k-batch": 168,       # 7 days — historical data
    "pma": 168,              # 7 days — historical data
    "recalls": 24,           # 24 hours — safety-critical
    "events": 24,            # 24 hours — new events filed daily
    "enforcement": 24,       # 24 hours — active enforcement changes
    "udi": 168,              # 7 days — device identifiers stable
}


def get_projects_dir():
    """Determine the projects directory from settings or default."""
    settings_path = os.path.expanduser("~/.claude/fda-tools.local.md")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            m = re.search(r"projects_dir:\s*(.+)", f.read())
            if m:
                return os.path.expanduser(m.group(1).strip())
    return os.path.expanduser("~/fda-510k-data/projects")


logger = logging.getLogger(__name__)


def load_manifest(project_dir):
    """Load or create a project manifest.

    Attempts to load data_manifest.json from the project directory. If the
    primary file is corrupted or missing, falls back to the .bak copy
    (created by save_manifest on each write). If both are unavailable,
    returns a fresh empty manifest.

    Args:
        project_dir: Absolute path to the project directory.

    Returns:
        dict: The manifest data.
    """
    manifest_path = os.path.join(project_dir, "data_manifest.json")
    backup_path = manifest_path + ".bak"

    # Try primary manifest first
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)

            # Validate and add schema_version if missing
            if _VALIDATOR_AVAILABLE:
                if "schema_version" not in manifest:
                    manifest = add_schema_version(manifest)
                    logger.info("Added schema_version to manifest at %s", manifest_path)

                # Validate manifest (non-strict, just log warnings)
                try:
                    is_valid, errors = validate_manifest(manifest, strict=False)
                    if not is_valid:
                        logger.warning(
                            "Manifest validation warnings for %s: %s",
                            manifest_path, "; ".join(errors[:3])
                        )
                except Exception as e:
                    logger.debug("Manifest validation skipped: %s", e)

            return manifest
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Primary manifest corrupted at %s: %s. Trying backup.",
                manifest_path, exc,
            )

    # Fall back to backup if primary is missing or corrupted
    if os.path.exists(backup_path):
        try:
            with open(backup_path) as f:
                data = json.load(f)
            logger.info("Recovered manifest from backup: %s", backup_path)
            # Restore backup as primary
            try:
                shutil.copy2(backup_path, manifest_path)
            except OSError as e:
                logger.warning("Could not restore backup to primary manifest: %s", e)
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Backup manifest also corrupted: %s", exc)

    # Create new manifest with schema version
    new_manifest = {
        "schema_version": CURRENT_SCHEMA_VERSION if _VALIDATOR_AVAILABLE else "1.0.0",
        "project": os.path.basename(project_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "product_codes": [],
        "queries": {},
    }
    return new_manifest


def save_manifest(project_dir, manifest):
    """Save the project manifest atomically with backup.

    Uses a write-to-temp-then-rename strategy to prevent data corruption
    if the process crashes during write. Before overwriting, the current
    manifest is preserved as data_manifest.json.bak.

    Per 21 CFR 820.70(i), data integrity during automated processing
    must be ensured. Atomic writes guarantee that the manifest is always
    in a consistent state on disk.

    Args:
        project_dir: Absolute path to the project directory.
        manifest: The manifest dict to persist.

    Raises:
        OSError: If the project directory cannot be created or the
            atomic rename fails (e.g., cross-device move).
    """
    manifest["last_updated"] = datetime.now(timezone.utc).isoformat()
    manifest_path = os.path.join(project_dir, "data_manifest.json")
    backup_path = manifest_path + ".bak"
    os.makedirs(project_dir, exist_ok=True)

    # Create backup of existing manifest before overwriting
    if os.path.exists(manifest_path):
        try:
            shutil.copy2(manifest_path, backup_path)
        except OSError as exc:
            logger.warning("Could not create manifest backup: %s", exc)

    # Atomic write: write to temp file in same directory, then rename.
    # os.replace() is atomic on POSIX when source and dest are on the
    # same filesystem. Using the same directory guarantees this.
    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=project_dir, prefix=".data_manifest_", suffix=".tmp"
        )
        with os.fdopen(fd, "w") as f:
            fd = None  # os.fdopen takes ownership of the fd
            json.dump(manifest, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, manifest_path)
        tmp_path = None  # successfully moved, nothing to clean up
    except Exception:
        # Clean up temp file on failure
        if fd is not None:
            try:
                os.close(fd)
            except OSError as e:
                logger.warning("Failed to close temp file descriptor: %s", e)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError as e:
                logger.warning("Failed to remove temp file %s: %s", tmp_path, e)
        raise


def is_expired(entry):
    """Check if a manifest entry has expired based on its TTL."""
    fetched_at = entry.get("fetched_at", "")
    ttl_hours = entry.get("ttl_hours", 24)
    if not fetched_at:
        return True
    try:
        fetched_time = datetime.fromisoformat(fetched_at)
        if fetched_time.tzinfo is None:
            fetched_time = fetched_time.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - fetched_time).total_seconds() / 3600
        return elapsed > ttl_hours
    except (ValueError, TypeError):
        return True


def make_query_key(query_type, **kwargs):
    """Generate a canonical query key from arguments."""
    parts = [query_type]
    if kwargs.get("product_code"):
        parts.append(kwargs["product_code"])
    if kwargs.get("k_number"):
        parts.append(kwargs["k_number"])
    if kwargs.get("k_numbers"):
        parts.append(",".join(sorted(kwargs["k_numbers"])))
    if kwargs.get("count_field"):
        parts.append("count:" + kwargs["count_field"])
    return ":".join(parts)


def extract_classification_summary(result):
    """Extract summary fields from a classification API response."""
    if not result.get("results"):
        return {"error": "No results found"}
    r = result["results"][0]
    return {
        "device_name": r.get("device_name", "N/A"),
        "device_class": r.get("device_class", "N/A"),
        "regulation_number": r.get("regulation_number", "N/A"),
        "review_panel": r.get("medical_specialty_description", r.get("review_panel", "N/A")),
        "definition": r.get("definition", "N/A"),
        "gmp_exempt": r.get("gmp_exempt_flag", "N/A"),
        "third_party_flag": r.get("third_party_flag", "N/A"),
        "implant_flag": r.get("implant_flag", "N"),
        "life_sustain_support_flag": r.get("life_sustain_support_flag", "N"),
    }


def extract_recalls_summary(result):
    """Extract summary fields from a recalls API response."""
    results = result.get("results", [])
    total = result.get("meta", {}).get("results", {}).get("total", 0)
    active = sum(1 for r in results if r.get("recall_status", "").lower() in ("ongoing", "on-going"))
    class_counts = {"Class I": 0, "Class II": 0, "Class III": 0}
    for r in results:
        cls = r.get("classification", "")
        if cls in class_counts:
            class_counts[cls] += 1
    latest = ""
    for r in results:
        d = r.get("event_date_initiated", "")
        if d and d > latest:
            latest = d
    return {
        "total_recalls": total,
        "returned": len(results),
        "active_recalls": active,
        "class_i": class_counts["Class I"],
        "class_ii": class_counts["Class II"],
        "class_iii": class_counts["Class III"],
        "latest_recall_date": latest or "N/A",
    }


def extract_events_summary(result, count_field=None):
    """Extract summary fields from a MAUDE events API response."""
    if count_field:
        results = result.get("results", [])
        total = sum(r.get("count", 0) for r in results)
        breakdown = {}
        for r in results:
            breakdown[r.get("term", "unknown")] = r.get("count", 0)
        return {
            "total_events": total,
            "deaths": breakdown.get("Death", 0),
            "injuries": breakdown.get("Injury", 0),
            "malfunctions": breakdown.get("Malfunction", 0),
            "breakdown": breakdown,
        }
    else:
        total = result.get("meta", {}).get("results", {}).get("total", 0)
        returned = len(result.get("results", []))
        return {
            "total_events": total,
            "returned": returned,
        }


def extract_510k_summary(result):
    """Extract summary fields from a single 510(k) lookup."""
    if not result.get("results"):
        return {"error": "No results found"}
    r = result["results"][0]
    return {
        "k_number": r.get("k_number", "N/A"),
        "applicant": r.get("applicant", "N/A"),
        "device_name": r.get("device_name", "N/A"),
        "product_code": r.get("product_code", "N/A"),
        "decision_date": r.get("decision_date", "N/A"),
        "decision_code": r.get("decision_code", "N/A"),
        "clearance_type": r.get("clearance_type", "N/A"),
        "statement_or_summary": r.get("statement_or_summary", "N/A"),
        "third_party_flag": r.get("third_party_flag", "N/A"),
    }


def extract_510k_batch_summary(result):
    """Extract summary fields from a batch 510(k) lookup."""
    devices = {}
    for r in result.get("results", []):
        kn = r.get("k_number", "")
        devices[kn] = {
            "applicant": r.get("applicant", "N/A"),
            "device_name": r.get("device_name", "N/A"),
            "product_code": r.get("product_code", "N/A"),
            "decision_date": r.get("decision_date", "N/A"),
            "decision_code": r.get("decision_code", "N/A"),
            "clearance_type": r.get("clearance_type", "N/A"),
            "statement_or_summary": r.get("statement_or_summary", "N/A"),
        }
    return {
        "total_matches": result.get("meta", {}).get("results", {}).get("total", 0),
        "returned": len(result.get("results", [])),
        "devices": devices,
    }


def extract_enforcement_summary(result):
    """Extract summary fields from an enforcement API response."""
    results = result.get("results", [])
    total = result.get("meta", {}).get("results", {}).get("total", 0)
    ongoing = sum(1 for r in results if r.get("status", "").lower() == "ongoing")
    return {
        "total_actions": total,
        "returned": len(results),
        "ongoing": ongoing,
    }


def print_classification(summary, cache_status, fetched_at):
    """Print classification results in structured KEY:VALUE format."""
    print(f"CACHE_STATUS:{cache_status}")
    print(f"FETCHED_AT:{fetched_at}")
    if summary.get("error"):
        print(f"ERROR:{summary['error']}")
        return
    print(f"CLASSIFICATION_MATCHES:1")
    print(f"DEVICE_NAME:{summary.get('device_name', 'N/A')}")
    print(f"DEVICE_CLASS:{summary.get('device_class', 'N/A')}")
    print(f"REGULATION:{summary.get('regulation_number', 'N/A')}")
    print(f"PANEL:{summary.get('review_panel', 'N/A')}")
    print(f"DEFINITION:{summary.get('definition', 'N/A')}")
    print(f"GMP_EXEMPT:{summary.get('gmp_exempt', 'N/A')}")
    print(f"THIRD_PARTY_FLAG:{summary.get('third_party_flag', 'N/A')}")
    print(f"IMPLANT_FLAG:{summary.get('implant_flag', 'N')}")
    print(f"LIFE_SUSTAIN:{summary.get('life_sustain_support_flag', 'N')}")
    source = "openFDA API (cached)" if cache_status == "HIT" else "openFDA API"
    print(f"SOURCE:{source}")


def print_recalls(summary, cache_status, fetched_at):
    """Print recalls results in structured KEY:VALUE format."""
    print(f"CACHE_STATUS:{cache_status}")
    print(f"FETCHED_AT:{fetched_at}")
    print(f"TOTAL_RECALLS:{summary.get('total_recalls', 0)}")
    print(f"ACTIVE_RECALLS:{summary.get('active_recalls', 0)}")
    print(f"CLASS_I:{summary.get('class_i', 0)}")
    print(f"CLASS_II:{summary.get('class_ii', 0)}")
    print(f"CLASS_III:{summary.get('class_iii', 0)}")
    print(f"LATEST_RECALL_DATE:{summary.get('latest_recall_date', 'N/A')}")
    source = "openFDA API (cached)" if cache_status == "HIT" else "openFDA API"
    print(f"SOURCE:{source}")


def print_events(summary, cache_status, fetched_at):
    """Print events results in structured KEY:VALUE format."""
    print(f"CACHE_STATUS:{cache_status}")
    print(f"FETCHED_AT:{fetched_at}")
    print(f"TOTAL_EVENTS:{summary.get('total_events', 0)}")
    if "deaths" in summary:
        print(f"DEATHS:{summary.get('deaths', 0)}")
        print(f"INJURIES:{summary.get('injuries', 0)}")
        print(f"MALFUNCTIONS:{summary.get('malfunctions', 0)}")
        for term, count in summary.get("breakdown", {}).items():
            if term not in ("Death", "Injury", "Malfunction"):
                print(f"EVENT_TYPE:{term}:{count}")
    else:
        print(f"RETURNED:{summary.get('returned', 0)}")
    source = "openFDA API (cached)" if cache_status == "HIT" else "openFDA API"
    print(f"SOURCE:{source}")


def print_510k(summary, cache_status, fetched_at):
    """Print single 510(k) results."""
    print(f"CACHE_STATUS:{cache_status}")
    print(f"FETCHED_AT:{fetched_at}")
    if summary.get("error"):
        print(f"ERROR:{summary['error']}")
        return
    print(f"K_NUMBER:{summary.get('k_number', 'N/A')}")
    print(f"APPLICANT:{summary.get('applicant', 'N/A')}")
    print(f"DEVICE_NAME:{summary.get('device_name', 'N/A')}")
    print(f"PRODUCT_CODE:{summary.get('product_code', 'N/A')}")
    print(f"DECISION_DATE:{summary.get('decision_date', 'N/A')}")
    print(f"DECISION_CODE:{summary.get('decision_code', 'N/A')}")
    print(f"CLEARANCE_TYPE:{summary.get('clearance_type', 'N/A')}")
    print(f"STATEMENT_OR_SUMMARY:{summary.get('statement_or_summary', 'N/A')}")
    source = "openFDA API (cached)" if cache_status == "HIT" else "openFDA API"
    print(f"SOURCE:{source}")


def print_510k_batch(summary, cache_status, fetched_at):
    """Print batch 510(k) results."""
    print(f"CACHE_STATUS:{cache_status}")
    print(f"FETCHED_AT:{fetched_at}")
    print(f"TOTAL_MATCHES:{summary.get('total_matches', 0)}")
    print(f"RETURNED:{summary.get('returned', 0)}")
    for kn, info in summary.get("devices", {}).items():
        print(f"DEVICE:{kn}|{info.get('applicant', 'N/A')}|{info.get('device_name', 'N/A')}|{info.get('product_code', 'N/A')}|{info.get('decision_date', 'N/A')}|{info.get('decision_code', 'N/A')}|{info.get('clearance_type', 'N/A')}|{info.get('statement_or_summary', 'N/A')}")
    source = "openFDA API (cached)" if cache_status == "HIT" else "openFDA API"
    print(f"SOURCE:{source}")


def print_enforcement(summary, cache_status, fetched_at):
    """Print enforcement results."""
    print(f"CACHE_STATUS:{cache_status}")
    print(f"FETCHED_AT:{fetched_at}")
    print(f"TOTAL_ACTIONS:{summary.get('total_actions', 0)}")
    print(f"ONGOING:{summary.get('ongoing', 0)}")
    source = "openFDA API (cached)" if cache_status == "HIT" else "openFDA API"
    print(f"SOURCE:{source}")


def handle_query(args):
    """Handle a data store query — check manifest, fetch if needed, update manifest."""
    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, args.project)
    os.makedirs(project_dir, exist_ok=True)

    manifest = load_manifest(project_dir)
    client = FDAClient()

    query_type = args.query
    product_code = getattr(args, "product_code", None)
    k_number = getattr(args, "k_number", None)
    k_numbers = getattr(args, "k_numbers", None)
    count_field = getattr(args, "count", None)
    refresh = getattr(args, "refresh", False)

    if k_numbers:
        k_numbers = [k.strip().upper() for k in k_numbers.split(",") if k.strip()]

    # Build query key
    key = make_query_key(
        query_type,
        product_code=product_code,
        k_number=k_number,
        k_numbers=k_numbers,
        count_field=count_field,
    )

    # Check manifest for cached entry
    entry = manifest["queries"].get(key)
    if entry and not refresh and not is_expired(entry):
        summary = entry.get("summary", {})
        fetched_at = entry.get("fetched_at", "unknown")
        _print_result(query_type, summary, "HIT", fetched_at, count_field)
        return

    # Cache miss — fetch from API
    result = _fetch_from_api(client, query_type, product_code, k_number, k_numbers, count_field)

    if result.get("degraded") or result.get("error"):
        # API error — check if we have a stale cache entry
        if entry:
            summary = entry.get("summary", {})
            fetched_at = entry.get("fetched_at", "unknown")
            logger.warning("API_ERROR -- using stale cached data")
            _print_result(query_type, summary, "STALE", fetched_at, count_field)
            return
        print(f"CACHE_STATUS:MISS")
        print(f"ERROR:{result.get('error', 'API unavailable')}")
        return

    # Extract summary
    summary = _extract_summary(query_type, result, count_field)

    # Get cache key from the client's internal cache
    cache_key = client._cache_key(
        _get_endpoint(query_type),
        _get_params(query_type, product_code, k_number, k_numbers, count_field),
    )

    # Update manifest
    now = datetime.now(timezone.utc).isoformat()
    total = result.get("meta", {}).get("results", {}).get("total", 0)
    manifest["queries"][key] = {
        "fetched_at": now,
        "ttl_hours": TTL_TIERS.get(query_type, 24),
        "source": "openFDA",
        "total_matches": total,
        "summary": summary,
        "api_cache_key": cache_key,
    }

    # Track product codes
    if product_code and product_code not in manifest.get("product_codes", []):
        manifest.setdefault("product_codes", []).append(product_code)

    save_manifest(project_dir, manifest)
    _print_result(query_type, summary, "MISS", now, count_field)


def _fetch_from_api(client, query_type, product_code, k_number, k_numbers, count_field):
    """Fetch data from the API based on query type."""
    if query_type == "classification":
        return client.get_classification(product_code)
    elif query_type == "recalls":
        return client.get_recalls(product_code, limit=100)
    elif query_type == "events":
        if count_field:
            return client.get_events(product_code, count=count_field)
        return client.get_events(product_code)
    elif query_type == "510k":
        return client.get_510k(k_number)
    elif query_type == "510k-batch":
        return client.batch_510k(k_numbers)
    elif query_type == "enforcement":
        return client._request("enforcement", {
            "search": f'product_code:"{product_code}"',
            "limit": "100",
        })
    else:
        return {"error": f"Unknown query type: {query_type}", "degraded": True}


def _extract_summary(query_type, result, count_field=None):
    """Extract a summary from an API result based on query type."""
    if query_type == "classification":
        return extract_classification_summary(result)
    elif query_type == "recalls":
        return extract_recalls_summary(result)
    elif query_type == "events":
        return extract_events_summary(result, count_field)
    elif query_type == "510k":
        return extract_510k_summary(result)
    elif query_type == "510k-batch":
        return extract_510k_batch_summary(result)
    elif query_type == "enforcement":
        return extract_enforcement_summary(result)
    return {}


def _get_endpoint(query_type):
    """Map query type to API endpoint."""
    return {
        "classification": "classification",
        "recalls": "recall",
        "events": "event",
        "510k": "510k",
        "510k-batch": "510k",
        "enforcement": "enforcement",
    }.get(query_type, query_type)


def _get_params(query_type, product_code, k_number, k_numbers, count_field):
    """Build API params for cache key generation."""
    if query_type == "classification":
        return {"search": f'product_code:"{product_code}"', "limit": "1"}
    elif query_type == "recalls":
        return {"search": f'product_code:"{product_code}"', "limit": "100"}
    elif query_type == "events":
        params = {"search": f'device.device_report_product_code:"{product_code}"', "limit": "100"}
        if count_field:
            params["count"] = count_field
            del params["limit"]
        return params
    elif query_type == "510k":
        return {"search": f'k_number:"{k_number}"', "limit": "1"}
    elif query_type == "510k-batch":
        search = "+OR+".join(f'k_number:"{k}"' for k in (k_numbers or []))
        return {"search": search, "limit": str(len(k_numbers or []))}
    elif query_type == "enforcement":
        return {"search": f'product_code:"{product_code}"', "limit": "100"}
    return {}


def _print_result(query_type, summary, cache_status, fetched_at, _count_field=None):
    """Route to the appropriate printer."""
    if query_type == "classification":
        print_classification(summary, cache_status, fetched_at)
    elif query_type == "recalls":
        print_recalls(summary, cache_status, fetched_at)
    elif query_type == "events":
        print_events(summary, cache_status, fetched_at)
    elif query_type == "510k":
        print_510k(summary, cache_status, fetched_at)
    elif query_type == "510k-batch":
        print_510k_batch(summary, cache_status, fetched_at)
    elif query_type == "enforcement":
        print_enforcement(summary, cache_status, fetched_at)


def handle_show_manifest(args):
    """Show the project manifest summary."""
    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, args.project)
    manifest = load_manifest(project_dir)

    print(f"PROJECT:{manifest.get('project', args.project)}")
    print(f"LAST_UPDATED:{manifest.get('last_updated', 'never')}")
    print(f"PRODUCT_CODES:{','.join(manifest.get('product_codes', [])) or 'none'}")
    print("---")

    cached_count = 0
    stale_count = 0
    for key, entry in manifest.get("queries", {}).items():
        expired = is_expired(entry)
        summary = entry.get("summary", {})
        fetched_at = entry.get("fetched_at", "")

        # Calculate time ago
        time_ago = "unknown"
        if fetched_at:
            try:
                ft = datetime.fromisoformat(fetched_at)
                if ft.tzinfo is None:
                    ft = ft.replace(tzinfo=timezone.utc)
                hours = (datetime.now(timezone.utc) - ft).total_seconds() / 3600
                if hours < 1:
                    time_ago = f"{int(hours * 60)}m ago"
                elif hours < 24:
                    time_ago = f"{int(hours)}h ago"
                else:
                    time_ago = f"{int(hours / 24)}d ago"
            except (ValueError, TypeError) as e:
                logger.warning("Could not parse fetched_at timestamp: %s", e)

        # Build compact summary string
        compact = _compact_summary(key, summary)
        status = "STALE" if expired else "CACHED"

        if expired:
            stale_count += 1
            print(f"{status}:{key} | {compact} | {time_ago} [EXPIRED]")
        else:
            cached_count += 1
            print(f"{status}:{key} | {compact} | {time_ago}")

    print("---")
    print(f"TOTAL_CACHED:{cached_count}")
    print(f"TOTAL_STALE:{stale_count}")


def _compact_summary(key, summary):
    """Generate a compact one-line summary for manifest display."""
    if key.startswith("classification:"):
        cls = summary.get("device_class", "?")
        reg = summary.get("regulation_number", "?")
        return f"Class {cls} | {reg}"
    elif key.startswith("recalls:"):
        total = summary.get("total_recalls", 0)
        active = summary.get("active_recalls", 0)
        return f"{total} total ({active} active)"
    elif "events:" in key and "count:" in key:
        total = summary.get("total_events", 0)
        deaths = summary.get("deaths", 0)
        return f"{total} total ({deaths} deaths)"
    elif key.startswith("events:"):
        total = summary.get("total_events", 0)
        returned = summary.get("returned", 0)
        return f"{total} total ({returned} returned)"
    elif key.startswith("510k_batch:") or key.startswith("510k-batch:"):
        count = len(summary.get("devices", {}))
        return f"{count} devices"
    elif key.startswith("510k:"):
        name = summary.get("device_name", "N/A")
        return name[:50]
    elif key.startswith("enforcement:"):
        total = summary.get("total_actions", 0)
        ongoing = summary.get("ongoing", 0)
        return f"{total} total ({ongoing} ongoing)"
    return str(summary)[:60]


def handle_clear(args):
    """Clear all cached data for a project."""
    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, args.project)
    manifest_path = os.path.join(project_dir, "data_manifest.json")
    if os.path.exists(manifest_path):
        os.remove(manifest_path)
        print(f"CLEARED:data_manifest.json for project {args.project}")
    else:
        print(f"NO_MANIFEST:no data_manifest.json found for project {args.project}")


def handle_refresh_all(args):
    """Mark all manifest entries as stale by setting fetched_at to epoch."""
    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, args.project)
    manifest = load_manifest(project_dir)
    count = 0
    for key in manifest.get("queries", {}):
        manifest["queries"][key]["fetched_at"] = "1970-01-01T00:00:00+00:00"
        count += 1
    save_manifest(project_dir, manifest)
    print(f"REFRESHED:{count} entries marked as stale for project {args.project}")


def main():
    parser = argparse.ArgumentParser(
        description="FDA Project Data Store — Context-Surviving API Cache"
    )
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument(
        "--query",
        choices=["classification", "recalls", "events", "510k", "510k-batch", "enforcement"],
        help="Query type",
    )
    parser.add_argument("--product-code", dest="product_code", help="FDA product code")
    parser.add_argument("--k-number", dest="k_number", help="Single K-number for 510k lookup")
    parser.add_argument("--k-numbers", dest="k_numbers", help="Comma-separated K-numbers for batch lookup")
    parser.add_argument("--count", help="Count field for events query (e.g., event_type.exact)")
    parser.add_argument("--refresh", action="store_true", help="Force refresh (ignore manifest cache)")
    parser.add_argument("--show-manifest", action="store_true", dest="show_manifest", help="Show manifest summary")
    parser.add_argument("--clear", action="store_true", help="Clear all cached data for project")
    parser.add_argument("--refresh-all", action="store_true", dest="refresh_all", help="Mark all entries as stale")

    args = parser.parse_args()

    if args.clear:
        handle_clear(args)
    elif args.refresh_all:
        handle_refresh_all(args)
    elif args.show_manifest:
        handle_show_manifest(args)
    elif args.query:
        # Validate required arguments per query type
        if args.query in ("classification", "recalls", "events", "enforcement"):
            if not args.product_code:
                parser.error(f"--product-code is required for --query {args.query}")
        elif args.query == "510k":
            if not args.k_number:
                parser.error("--k-number is required for --query 510k")
        elif args.query == "510k-batch":
            if not args.k_numbers:
                parser.error("--k-numbers is required for --query 510k-batch")
        handle_query(args)
    else:
        parser.error("Specify --query, --show-manifest, --clear, or --refresh-all")


if __name__ == "__main__":
    main()
