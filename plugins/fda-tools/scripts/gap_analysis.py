#!/usr/bin/env python3
"""
gap_analysis.py — Identify missing K-numbers in 510k_output.csv

Cross-references FDA PMN database files with existing CSV and PDF directories
to produce a download manifest of what needs to be fetched and extracted.

Usage:
    python gap_analysis.py                                    # All recent (K23-K26, DEN)
    python gap_analysis.py --years 2024,2025                  # Specific years
    python gap_analysis.py --years 2020-2025                  # Year range
    python gap_analysis.py --product-codes KGN,DXY            # Specific product codes
    python gap_analysis.py --prefixes K24,K25                 # Custom K-number prefixes
    python gap_analysis.py --baseline /path/to/output.csv     # Custom baseline CSV
    python gap_analysis.py --pdf-dir /path/to/pdfs            # Custom PDF directory
"""

import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ============================================================
# Security: Path Validation (FDA-171 / SEC-004 / CWE-22)
# ============================================================

def _sanitize_path(path_input):
    """
    Sanitize file path to prevent path traversal attacks.

    Args:
        path_input: User-supplied path string

    Returns:
        Sanitized path string

    Raises:
        ValueError: If path contains traversal sequences or null bytes

    Security: FDA-171 (SEC-004) - CWE-22 Path Traversal Prevention
    """
    if not path_input:
        raise ValueError("Path cannot be empty")

    path_str = str(path_input).strip()

    # Reject null bytes (can bypass security checks)
    if '\x00' in path_str:
        raise ValueError(f"Path contains null bytes: '{path_str}'")

    # Reject explicit traversal sequences
    if '..' in path_str:
        raise ValueError(f"Path contains directory traversal sequence (..) File: {path_str}")

    # Reject absolute paths to prevent escaping project directory
    if os.path.isabs(path_str):
        # Allow absolute paths but validate them later in _validate_path_safety
        pass

    return path_str


def _validate_path_safety(path_input, allowed_base_dirs=None):
    """
    Validate that a file path is safe and doesn't escape allowed directories.

    Args:
        path_input: Path to validate (string or Path object)
        allowed_base_dirs: List of allowed base directories (defaults to project root)

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path escapes allowed directories

    Security: FDA-171 (SEC-004) - CWE-22 Path Traversal Prevention
    """
    # Sanitize first
    sanitized = _sanitize_path(path_input)

    # Resolve to absolute canonical path
    try:
        resolved_path = Path(sanitized).resolve(strict=False)
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Cannot resolve path: {sanitized}") from e

    # If no allowed directories specified, allow anything (backwards compat)
    if allowed_base_dirs is None:
        return resolved_path

    # Ensure allowed_base_dirs are all resolved absolute paths
    allowed_resolved = []
    for base_dir in allowed_base_dirs:
        try:
            base_resolved = Path(base_dir).resolve(strict=False)
            allowed_resolved.append(base_resolved)
        except (OSError, RuntimeError):
            continue

    # Check if resolved path is within any allowed directory
    for allowed_dir in allowed_resolved:
        try:
            # Check if resolved_path is relative to allowed_dir
            resolved_path.relative_to(allowed_dir)
            return resolved_path  # Path is safe
        except ValueError:
            # Not relative to this allowed_dir, try next
            continue

    # Path escapes all allowed directories
    raise ValueError(
        f"Security violation: Path escapes allowed directories\n"
        f"  Requested: {path_input}\n"
        f"  Resolved: {resolved_path}\n"
        f"  Allowed: {', '.join(str(d) for d in allowed_resolved)}"
    )


# --- Defaults ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PMN_FILES = [
    os.path.join(SCRIPT_DIR, "pmn96cur.txt"),
    os.path.join(SCRIPT_DIR, "pmnlstmn.txt"),
]
DEFAULT_BASELINE_CSV = os.path.join(SCRIPT_DIR, "..", "download", "510k", "510k_output.csv")
DEFAULT_PDF_BASE_DIR = os.path.join(SCRIPT_DIR, "..", "download", "510k")
DEFAULT_OUTPUT_MANIFEST = os.path.join(SCRIPT_DIR, "gap_manifest.csv")

# FDA TYPE field mapping to directory names (matches 510BAtchFetch26.py behavior)
TYPE_MAP = {
    "Traditional": "Traditional",
    "Special": "Special",
    "Abbreviated": "Abbreviated",
    "Post-NSE": "Post-NSE",
    "Dual": "Dual",
    "Direct": "Direct",
    "Tracking": "Tracking",
    "": "Unknown",
}


def parse_years(years_str):
    """Parse year argument into a set of year integers.

    Accepts: '2024', '2024,2025', '2020-2025', '2020-2022,2024,2025'
    """
    years = set()
    for part in years_str.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            years.update(range(int(lo), int(hi) + 1))
        else:
            years.add(int(part))
    return years


def prefixes_from_years(years):
    """Convert a set of years to K-number prefixes.

    2023 → K23, 2024 → K24, etc. Also includes DEN for all.
    """
    prefixes = set()
    for y in years:
        suffix = str(y)[-2:]  # last 2 digits
        prefixes.add(f"K{suffix}")
    prefixes.add("DEN")
    return tuple(sorted(prefixes))


def sanitize_applicant(applicant):
    """Remove non-word characters from applicant name (matches 510BAtchFetch26.py)."""
    return re.sub(r'\W+', '', str(applicant))


def build_pdf_url(knumber, date_received):
    """Construct FDA download URL for a K-number."""
    if not date_received or '/' not in date_received:
        return ""
    try:
        year = int(date_received.split('/')[-1])
    except (ValueError, IndexError):
        return ""

    if year >= 2002:
        folder = f"pdf{year - 2000}"
    else:
        folder = "pdf"

    return f"https://www.accessdata.fda.gov/cdrh_docs/{folder}/{knumber}.pdf"


def build_pdf_path(knumber, year, applicant, productcode, fda_type, pdf_base_dir):
    """Construct expected local PDF path matching existing directory structure."""
    sanitized = sanitize_applicant(applicant)
    type_name = TYPE_MAP.get(fda_type, fda_type if fda_type else "Unknown")
    return os.path.join(
        pdf_base_dir, str(year), sanitized, productcode, type_name, f"{knumber}.pdf"
    )


def load_pmn_records(pmn_files, target_prefixes, product_codes=None, year_set=None):
    """Load all records from PMN database files, filtered by prefixes and optional filters."""
    records = {}
    for filepath in pmn_files:
        if not os.path.exists(filepath):
            print(f"  WARNING: PMN file not found: {filepath}")
            continue
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f, delimiter='|')
            header = next(reader, None)
            if not header:
                continue
            col_idx = {name.strip(): i for i, name in enumerate(header)}
            for row in reader:
                if len(row) < 15:
                    continue
                knumber = row[col_idx.get('KNUMBER', 0)].strip()
                if not any(knumber.startswith(p) for p in target_prefixes):
                    continue
                if knumber in records:
                    continue
                date_received = row[col_idx.get('DATERECEIVED', 10)].strip()
                try:
                    year = int(date_received.split('/')[-1]) if date_received else 0
                except (ValueError, IndexError):
                    year = 0

                # Year filter
                if year_set and year not in year_set:
                    continue

                productcode = row[col_idx.get('PRODUCTCODE', 14)].strip()

                # Product code filter
                if product_codes and productcode not in product_codes:
                    continue

                records[knumber] = {
                    'applicant': row[col_idx.get('APPLICANT', 1)].strip(),
                    'productcode': productcode,
                    'datereceived': date_received,
                    'type': row[col_idx.get('TYPE', 18)].strip(),
                    'devicename': row[col_idx.get('DEVICENAME', 21)].strip() if len(row) > 21 else '',
                    'year': year,
                }
    return records


def load_existing_csv_knumbers(baseline_csv):
    """Load set of K-numbers already in the baseline CSV."""
    knumbers = set()
    if not os.path.exists(baseline_csv):
        print(f"  WARNING: Baseline CSV not found: {baseline_csv}")
        return knumbers
    with open(baseline_csv, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if row:
                knumbers.add(row[0].strip())
    return knumbers


def check_pdf_exists(knumber, meta, pdf_base_dir):
    """Check if a PDF exists at its expected path."""
    pdf_path = build_pdf_path(
        knumber, meta['year'], meta['applicant'],
        meta['productcode'], meta['type'], pdf_base_dir
    )
    return os.path.exists(pdf_path), pdf_path


def main():
    parser = argparse.ArgumentParser(
        description="Identify missing K-numbers and generate a download manifest"
    )
    parser.add_argument("--years", type=str, default=None,
                        help="Years to analyze (e.g. 2024,2025 or 2020-2025)")
    parser.add_argument("--prefixes", type=str, default=None,
                        help="K-number prefixes (e.g. K23,K24,DEN). "
                             "Overrides --years for prefix selection.")
    parser.add_argument("--product-codes", type=str, default=None,
                        help="Filter to specific product codes (e.g. KGN,DXY)")
    parser.add_argument("--baseline", type=str, default=DEFAULT_BASELINE_CSV,
                        help=f"Baseline CSV path (default: {DEFAULT_BASELINE_CSV})")
    parser.add_argument("--pdf-dir", type=str, default=DEFAULT_PDF_BASE_DIR,
                        help=f"PDF base directory (default: {DEFAULT_PDF_BASE_DIR})")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_MANIFEST,
                        help=f"Output manifest path (default: {DEFAULT_OUTPUT_MANIFEST})")
    parser.add_argument("--pmn-files", type=str, default=None,
                        help="Comma-separated PMN database files (default: pmn96cur.txt,pmnlstmn.txt)")
    args = parser.parse_args()

    # Security: Validate all file paths (FDA-171 / SEC-004 / CWE-22)
    try:
        # Define allowed base directories for path validation
        # Allow access to scripts dir, download dir, and current working directory
        project_root = Path(SCRIPT_DIR).parent.resolve()
        allowed_dirs = [
            project_root,  # Plugin root directory
            Path.cwd(),    # Current working directory
        ]

        # Validate baseline CSV path
        args.baseline = str(_validate_path_safety(args.baseline, allowed_dirs))

        # Validate PDF base directory
        args.pdf_dir = str(_validate_path_safety(args.pdf_dir, allowed_dirs))

        # Validate output manifest path
        args.output = str(_validate_path_safety(args.output, allowed_dirs))

        # Validate PMN files if provided
        if args.pmn_files:
            validated_pmn_files = []
            for pmn_path in [p.strip() for p in args.pmn_files.split(",")]:
                validated = str(_validate_path_safety(pmn_path, allowed_dirs))
                validated_pmn_files.append(validated)
            args.pmn_files = ','.join(validated_pmn_files)

    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve filters
    year_set = None
    if args.years:
        year_set = parse_years(args.years)

    if args.prefixes:
        target_prefixes = tuple(p.strip() for p in args.prefixes.split(","))
    elif year_set:
        target_prefixes = prefixes_from_years(year_set)
    else:
        # Default: recent years
        target_prefixes = ("K23", "K24", "K25", "K26", "DEN")

    product_codes = None
    if args.product_codes:
        product_codes = set(p.strip().upper() for p in args.product_codes.split(","))

    pmn_files = DEFAULT_PMN_FILES
    if args.pmn_files:
        # args.pmn_files is already validated as comma-separated string
        pmn_files = args.pmn_files.split(",")

    print("=" * 60)
    print("510(k) Gap Analysis")
    print("=" * 60)
    print(f"  Prefixes: {', '.join(target_prefixes)}")
    if year_set:
        print(f"  Years: {', '.join(str(y) for y in sorted(year_set))}")
    if product_codes:
        print(f"  Product codes: {', '.join(sorted(product_codes))}")

    # Step 1: Load PMN records
    print("\n[1/3] Loading PMN database records...")
    pmn_records = load_pmn_records(pmn_files, target_prefixes, product_codes, year_set)
    print(f"  Found {len(pmn_records)} records matching filters")

    # Breakdown by prefix
    prefix_counts = defaultdict(int)
    for k in pmn_records:
        for p in target_prefixes:
            if k.startswith(p):
                prefix_counts[p] += 1
                break
    for p in sorted(prefix_counts):
        print(f"    {p}: {prefix_counts[p]}")

    # Step 2: Load existing CSV K-numbers
    print("\n[2/3] Loading existing baseline CSV...")
    csv_knumbers = load_existing_csv_knumbers(args.baseline)
    print(f"  Found {len(csv_knumbers)} K-numbers in {os.path.basename(args.baseline)}")

    # Step 3: Check each target K-number
    print("\n[3/3] Checking PDF existence and generating manifest...")

    have_pdf_no_csv = []
    need_download = []
    already_done = []
    checked = 0

    for knumber, meta in sorted(pmn_records.items()):
        if knumber in csv_knumbers:
            already_done.append(knumber)
            continue

        url = build_pdf_url(knumber, meta['datereceived'])
        has_pdf, pdf_path = check_pdf_exists(knumber, meta, args.pdf_dir)

        entry = {
            'knumber': knumber,
            'status': 'have_pdf_no_csv' if has_pdf else 'need_download',
            'pdf_path': pdf_path,
            'download_url': url,
            **meta,
        }
        if has_pdf:
            have_pdf_no_csv.append(entry)
        else:
            need_download.append(entry)

        checked += 1
        if checked % 1000 == 0:
            print(f"  Checked {checked} K-numbers...")

    # Write manifest CSV
    all_rows = have_pdf_no_csv + need_download
    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'KNUMBER', 'STATUS', 'PDF_PATH', 'DOWNLOAD_URL',
            'APPLICANT', 'PRODUCTCODE', 'TYPE', 'DATERECEIVED',
            'DEVICENAME', 'YEAR'
        ])
        for row in all_rows:
            writer.writerow([
                row['knumber'], row['status'], row['pdf_path'],
                row['download_url'], row['applicant'], row['productcode'],
                row['type'], row['datereceived'], row['devicename'],
                row['year'],
            ])

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"  PMN records in target range:  {len(pmn_records)}")
    print(f"  Already in CSV (skip):        {len(already_done)}")
    print(f"  Have PDF, need extraction:    {len(have_pdf_no_csv)}")
    print(f"  Need download + extraction:   {len(need_download)}")
    print(f"  Total to process:             {len(have_pdf_no_csv) + len(need_download)}")
    print()

    for label, group in [("Have PDF, need extraction", have_pdf_no_csv),
                          ("Need download", need_download)]:
        if group:
            pc = defaultdict(int)
            for r in group:
                for p in target_prefixes:
                    if r['knumber'].startswith(p):
                        pc[p] += 1
                        break
            print(f"  {label}:")
            for p in sorted(pc):
                print(f"    {p}: {pc[p]}")

            # Product code breakdown
            if product_codes:
                by_code = defaultdict(int)
                for r in group:
                    by_code[r['productcode']] += 1
                print(f"    By product code:")
                for code in sorted(by_code):
                    print(f"      {code}: {by_code[code]}")
            print()

    est_hours = len(need_download) * 10 / 3600
    print(f"  Estimated download time: {est_hours:.1f} hours ({len(need_download)} files @ 10s each)")
    print(f"\n  Manifest written to: {args.output}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
