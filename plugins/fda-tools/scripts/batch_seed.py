#!/usr/bin/env python3
"""
batch_seed.py — Seed multiple FDA 510(k) test projects from a suite config.

Creates one project per archetype in a round directory, reusing seed_test_project
functions for FDA API calls and PDF extraction.

Usage:
    python3 batch_seed.py --suite test_suite.json --round-name baseline
    python3 batch_seed.py --product-codes OVE,DQY,QKQ --round-name quick
    python3 batch_seed.py --random 5 --seed 42 --round-name random5
    python3 batch_seed.py --suite test_suite.json --round-name test --dry-run
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from fda_api_client import FDAClient
from seed_test_project import (
    get_classification,
    get_recent_clearance,
    fetch_peer_clearances,
    download_pdf_text,
    parse_device_specs,
    build_device_profile_with_pdf_data,
    build_review_json_with_ifu,
    build_review_json,
    build_query_json,
    pick_random_product_code,
)

DEFAULT_OUTPUT_DIR = os.path.expanduser("~/fda-510k-data/projects")
DEFAULT_SUITE_PATH = os.path.join(SCRIPT_DIR, "test_suite.json")
DEFAULT_MAX_AGE_YEARS = 5


def load_suite(suite_path):
    """Load test suite JSON and return list of archetype dicts."""
    with open(suite_path) as f:
        data = json.load(f)
    return data.get("archetypes", [])


def get_plugin_commit():
    """Get current git commit hash for the plugin, or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=os.path.dirname(SCRIPT_DIR),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"Warning: get_plugin_commit failed: {e}", file=sys.stderr)
    return "unknown"


def seed_one_project(client, rng, product_code, archetype_id, round_dir,
                     max_age_years, dry_run=False):
    """Seed a single project. Returns a manifest entry dict.

    Args:
        client: FDAClient instance
        rng: random.Random for reproducibility
        product_code: e.g. "GEI"
        archetype_id: e.g. "simple_powered"
        round_dir: Path to round directory
        max_age_years: recency filter
        dry_run: if True, don't write files

    Returns:
        dict with project metadata for manifest, or None on failure
    """
    project_name = f"batch_{product_code}_{archetype_id}"
    project_dir = round_dir / project_name
    entry = {
        "project_name": project_name,
        "archetype_id": archetype_id,
        "product_code": product_code,
        "panel": "",
        "device_name": "",
        "predicate_k": "",
        "data_source_k": "",
        "seed_status": "pending",
        "pdf_text_chars": 0,
        "extracted_sections": [],
        "materials_count": 0,
        "sterilization_method": "",
        "standards_count": 0,
        "pipeline_results": {},
    }

    # 1. Classification
    print(f"\n{'='*60}")
    print(f"  Seeding: {product_code} ({archetype_id})")
    print(f"{'='*60}")

    print(f"  Fetching classification for {product_code}...")
    classification = get_classification(client, product_code)
    if classification:
        entry["panel"] = classification.get("review_panel", "")
        entry["device_name"] = classification.get("device_name", "")
    else:
        print(f"  WARNING: No classification found for {product_code}")

    # 2. Recent clearance (predicate)
    print(f"  Fetching recent clearance...")
    clearance = get_recent_clearance(client, product_code, max_age_years)
    if not clearance:
        print(f"  ERROR: No clearance found for {product_code} in {max_age_years} years")
        entry["seed_status"] = "no_clearance"
        return entry

    predicate_k = clearance.get("k_number", "")
    entry["predicate_k"] = predicate_k
    print(f"  Predicate: {predicate_k} ({clearance.get('device_name', '?')})")

    # 3. Peer clearances
    print(f"  Fetching peers (excluding {predicate_k})...")
    peers = fetch_peer_clearances(client, product_code, predicate_k,
                                  max_age_years, limit=10)
    print(f"  Found {len(peers)} peer clearances")

    # 4. Pick a peer for data sourcing
    data_k = None
    pdf_text = None
    pdf_specs = None

    if peers:
        data_peer = rng.choice(peers)
        data_k = data_peer.get("k_number", "")
        entry["data_source_k"] = data_k
        print(f"  Data source peer: {data_k} ({data_peer.get('device_name', '?')})")

        # Check extraction cache first
        cache_dir = Path(os.path.expanduser("~/fda-510k-data/extraction/cache"))
        cache_index = cache_dir / "index.json"
        if cache_index.exists():
            try:
                with open(cache_index) as f:
                    idx = json.load(f)
                if data_k in idx:
                    cached_path = Path(os.path.expanduser("~/fda-510k-data/extraction")) / idx[data_k]["file_path"]
                    if cached_path.exists():
                        with open(cached_path) as f:
                            cached_data = json.load(f)
                        pdf_text = cached_data.get("text", "")
                        if pdf_text and len(pdf_text.strip()) > 200:
                            print(f"  Using cached extraction ({len(pdf_text)} chars)")
            except Exception as e:
                print(f"Warning: Failed to read cached extraction: {e}", file=sys.stderr)

        if not pdf_text or len(pdf_text.strip()) < 200:
            print(f"  Downloading PDF for {data_k}...")
            pdf_text = download_pdf_text(data_k)

        if pdf_text and len(pdf_text.strip()) > 200:
            entry["pdf_text_chars"] = len(pdf_text)
            print(f"  Parsing device specs from PDF ({len(pdf_text)} chars)...")
            pdf_specs = parse_device_specs(pdf_text, data_k, classification)
            sections = list(pdf_specs.get("extracted_sections", {}).keys())
            entry["extracted_sections"] = sections
            entry["materials_count"] = len(pdf_specs.get("materials", []))
            entry["sterilization_method"] = pdf_specs.get("sterilization_method", "")
            entry["standards_count"] = len(pdf_specs.get("standards_referenced", []))
            print(f"  Sections: {', '.join(sections) or 'none'}")
            print(f"  Materials: {entry['materials_count']}, Standards: {entry['standards_count']}")
        else:
            print(f"  WARNING: No PDF text for {data_k}")
    else:
        print(f"  WARNING: No peers found — seeding without PDF data")

    # 5. Build project files
    device_name = entry["device_name"] or clearance.get("device_name", "Unknown")
    intended_use = ""
    if pdf_specs and pdf_specs.get("intended_use"):
        intended_use = pdf_specs["intended_use"]

    query = build_query_json(project_name, product_code, device_name, max_age_years)
    if intended_use:
        query["intended_use"] = intended_use

    if pdf_specs:
        review = build_review_json_with_ifu(
            project_name, product_code, device_name, clearance,
            intended_use=intended_use,
        )
        device_profile = build_device_profile_with_pdf_data(
            pdf_specs, clearance, classification, peers,
            data_source_mode="peer",
        )
    else:
        review = build_review_json(project_name, product_code, device_name, clearance)
        device_profile = None

    # 6. Write files
    if dry_run:
        print(f"  DRY RUN — would create {project_dir}")
        entry["seed_status"] = "dry_run"
    else:
        project_dir.mkdir(parents=True, exist_ok=True)

        with open(project_dir / "query.json", "w") as f:
            json.dump(query, f, indent=2)
            f.write("\n")
        with open(project_dir / "review.json", "w") as f:
            json.dump(review, f, indent=2)
            f.write("\n")

        files_written = ["query.json", "review.json"]

        if device_profile:
            with open(project_dir / "device_profile.json", "w") as f:
                json.dump(device_profile, f, indent=2)
                f.write("\n")
            files_written.append("device_profile.json")

        if pdf_text:
            raw_path = project_dir / f"source_device_text_{data_k}.txt"
            with open(raw_path, "w") as f:
                f.write(f"# Source: {data_k} 510(k) summary PDF\n")
                f.write(f"# Extracted: {datetime.now(timezone.utc).isoformat()}\n")
                f.write(f"# Mode: peer (batch_seed)\n\n")
                f.write(pdf_text)
            files_written.append(raw_path.name)

        print(f"  Created: {', '.join(files_written)}")
        entry["seed_status"] = "success"

    return entry


def write_manifest(round_dir, round_name, entries, dry_run=False):
    """Write round_manifest.json with metadata for all projects."""
    manifest = {
        "round_id": round_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plugin_commit": get_plugin_commit(),
        "dry_run": dry_run,
        "project_count": len(entries),
        "success_count": sum(1 for e in entries if e["seed_status"] == "success"),
        "projects": entries,
    }
    manifest_path = round_dir / "round_manifest.json"
    if not dry_run:
        round_dir.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        print(f"\nManifest: {manifest_path}")
    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Batch-seed FDA 510(k) test projects from a suite config.",
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--suite",
        metavar="PATH",
        help="Path to test_suite.json (default: scripts/test_suite.json)",
    )
    source.add_argument(
        "--product-codes",
        metavar="CSV",
        help="Comma-separated product codes (e.g., OVE,DQY,QKQ)",
    )
    source.add_argument(
        "--random",
        metavar="N",
        type=int,
        help="Seed N random product codes",
    )

    parser.add_argument("--round-name", default=None,
                        help="Round name (default: timestamp-based)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="Base output directory")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--max-age-years", type=int, default=DEFAULT_MAX_AGE_YEARS,
                        help=f"Predicate recency filter (default: {DEFAULT_MAX_AGE_YEARS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without writing files")

    args = parser.parse_args()
    rng = random.Random(args.seed)
    client = FDAClient()

    # Determine round name and directory
    round_name = args.round_name or datetime.now().strftime("%Y%m%d_%H%M%S")
    round_dir = Path(args.output_dir) / f"rounds/round_{round_name}"

    # Build work items: list of (product_code, archetype_id)
    work_items = []

    if args.suite:
        suite_path = args.suite
        if not os.path.isabs(suite_path):
            # Try relative to script dir first, then CWD
            candidate = os.path.join(SCRIPT_DIR, suite_path)
            if os.path.exists(candidate):
                suite_path = candidate
        archetypes = load_suite(suite_path)
        for arch in archetypes:
            work_items.append((arch["product_code"], arch["id"]))

    elif args.product_codes:
        codes = [c.strip().upper() for c in args.product_codes.split(",")]
        for code in codes:
            work_items.append((code, f"manual_{code.lower()}"))

    elif args.random:
        print(f"Picking {args.random} random product codes...")
        for i in range(args.random):
            code = pick_random_product_code(client, rng, args.max_age_years)
            if code:
                work_items.append((code, f"random_{i+1}"))
                print(f"  #{i+1}: {code}")
            else:
                print(f"  #{i+1}: FAILED to pick random code")

    if not work_items:
        print("ERROR: No work items to process.", file=sys.stderr)
        sys.exit(1)

    # Print plan
    print(f"\n{'='*60}")
    print(f"  Batch Seed: {len(work_items)} projects")
    print(f"  Round: {round_name}")
    print(f"  Output: {round_dir}")
    print(f"  Commit: {get_plugin_commit()}")
    if args.dry_run:
        print(f"  Mode: DRY RUN")
    print(f"{'='*60}")
    for code, arch_id in work_items:
        print(f"  - {code} ({arch_id})")

    # Seed each project
    entries = []
    t0 = time.time()

    for i, (code, arch_id) in enumerate(work_items):
        print(f"\n[{i+1}/{len(work_items)}] ", end="")
        try:
            entry = seed_one_project(
                client, rng, code, arch_id, round_dir,
                args.max_age_years, dry_run=args.dry_run,
            )
            if entry:
                entries.append(entry)
        except Exception as e:
            print(f"  ERROR seeding {code}: {e}")
            entries.append({
                "project_name": f"batch_{code}_{arch_id}",
                "archetype_id": arch_id,
                "product_code": code,
                "seed_status": "error",
                "error": str(e),
            })

        # Brief pause between API calls
        if i < len(work_items) - 1:
            time.sleep(0.5)

    elapsed = time.time() - t0

    # Write manifest
    manifest = write_manifest(round_dir, round_name, entries, dry_run=args.dry_run)

    # Summary
    success = sum(1 for e in entries if e.get("seed_status") == "success")
    failed = sum(1 for e in entries if e.get("seed_status") in ("error", "no_clearance"))
    dry = sum(1 for e in entries if e.get("seed_status") == "dry_run")

    print(f"\n{'='*60}")
    print(f"  BATCH SEED COMPLETE")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Success: {success}, Failed: {failed}", end="")
    if dry:
        print(f", Dry run: {dry}", end="")
    print()

    # Quick stats table
    print(f"\n  {'Code':<6} {'Archetype':<25} {'Status':<12} {'PDF':<8} {'Sections':<10}")
    print(f"  {'-'*5:<6} {'-'*24:<25} {'-'*11:<12} {'-'*7:<8} {'-'*9:<10}")
    for e in entries:
        code = e.get("product_code", "?")
        arch = e.get("archetype_id", "?")[:24]
        status = e.get("seed_status", "?")
        pdf = f"{e.get('pdf_text_chars', 0):,}" if e.get("pdf_text_chars") else "-"
        sects = ", ".join(e.get("extracted_sections", [])[:3])
        if len(e.get("extracted_sections", [])) > 3:
            sects += "..."
        print(f"  {code:<6} {arch:<25} {status:<12} {pdf:<8} {sects}")

    print(f"\n  Next steps:")
    if not args.dry_run:
        print(f"  1. Run drafting agents on each project")
        print(f"  2. Run pre-check on each project")
        print(f"  3. Analyze: python3 {SCRIPT_DIR}/batch_analyze.py --round {round_dir}")
    print()


if __name__ == "__main__":
    main()
