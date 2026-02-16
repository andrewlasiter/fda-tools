#!/usr/bin/env python3
"""
FDA 510(k) Section Comparison Tool

Compares specific sections (clinical, biocompatibility, etc.) across all 510(k)
summaries for a product code. Provides regulatory intelligence through coverage
analysis, standards frequency detection, and outlier identification.

Usage:
    python3 compare_sections.py --product-code DQY --sections clinical,biocompatibility
    python3 compare_sections.py --product-code OVE --sections all --years 2020-2025
    python3 compare_sections.py --product-code DQY --sections performance --limit 30 --output report.md

Features:
    - Multi-device section extraction from structured cache
    - Coverage matrix (which devices have which sections)
    - FDA standards frequency analysis (ISO/IEC/ASTM citations)
    - Statistical outlier detection (Z-score analysis)
    - Markdown report + CSV export for regulatory review
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import section patterns from build_structured_cache
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_structured_cache import SECTION_PATTERNS


# Section type mapping for user-friendly names
SECTION_ALIASES = {
    'clinical': 'clinical_testing',
    'biocompat': 'biocompatibility',
    'biocompatibility': 'biocompatibility',
    'performance': 'performance_testing',
    'predicate': 'predicate_se',
    'se': 'predicate_se',
    'substantial_equivalence': 'predicate_se',
    'device_desc': 'device_description',
    'description': 'device_description',
    'indications': 'indications_for_use',
    'ifu': 'indications_for_use',
    'sterilization': 'sterilization',
    'shelf_life': 'shelf_life',
    'software': 'software',
    'electrical': 'electrical_safety',
    'human_factors': 'human_factors',
    'hf': 'human_factors',
    'risk': 'risk_management',
    'labeling': 'labeling',
    'regulatory': 'regulatory_history',
    'reprocessing': 'reprocessing',
    'packaging': 'packaging',
    'materials': 'materials',
    'environmental': 'environmental_testing',
    'mechanical': 'mechanical_testing',
    'functional': 'functional_testing',
    'aging': 'accelerated_aging',
    'antimicrobial': 'antimicrobial',
    'emc': 'emc_detailed',
    'mri': 'mri_safety',
    'animal': 'animal_testing',
    'literature': 'literature_review',
    'manufacturing': 'manufacturing',
    'all': 'all'  # Special case for all sections
}


def get_structured_cache_dir():
    """Get the structured cache directory."""
    return Path(os.path.expanduser("~/fda-510k-data/extraction/structured_text_cache"))


def load_structured_cache():
    """Load all structured cache files.

    Returns:
        Dict[str, dict]: K-number -> structured data mapping
    """
    cache_dir = get_structured_cache_dir()
    if not cache_dir.exists():
        return {}

    cache = {}
    for cache_file in cache_dir.glob("*.json"):
        try:
            with open(cache_file) as f:
                data = json.load(f)
                k_number = data.get("k_number", cache_file.stem)
                cache[k_number] = data
        except (json.JSONDecodeError, OSError):
            pass

    return cache


def filter_by_product_code(structured_cache: Dict, product_code: str) -> Dict:
    """Filter structured cache by product code.

    Args:
        structured_cache: Full cache dict
        product_code: Product code to filter by

    Returns:
        Filtered cache dict with only matching product codes
    """
    filtered = {}
    for k_number, data in structured_cache.items():
        # Product code is stored in metadata dict
        device_product_code = data.get("metadata", {}).get("product_code", "")
        if device_product_code.upper() == product_code.upper():
            filtered[k_number] = data

    return filtered


def filter_by_year_range(structured_cache: Dict, year_start: Optional[int],
                         year_end: Optional[int]) -> Dict:
    """Filter structured cache by decision date year range.

    Args:
        structured_cache: Cache dict
        year_start: Start year (inclusive) or None
        year_end: End year (inclusive) or None

    Returns:
        Filtered cache dict
    """
    if not year_start and not year_end:
        return structured_cache

    filtered = {}
    for k_number, data in structured_cache.items():
        decision_date = data.get("decision_date", "")
        if decision_date:
            try:
                year = int(decision_date[:4])
                if year_start and year < year_start:
                    continue
                if year_end and year > year_end:
                    continue
                filtered[k_number] = data
            except (ValueError, IndexError):
                pass

    return filtered


def extract_sections_batch(structured_cache: Dict, section_types: List[str]) -> Dict:
    """Extract specified sections from all devices in cache.

    Args:
        structured_cache: K-number -> structured data mapping
        section_types: List of section types to extract (e.g., ['clinical_testing', 'biocompatibility'])

    Returns:
        Dict with structure:
        {
            k_number: {
                'sections': {
                    section_type: {
                        'text': str,
                        'word_count': int,
                        'standards': [str]  # ISO/IEC/ASTM citations
                    }
                },
                'device_name': str,
                'decision_date': str,
                'product_code': str
            }
        }
    """
    results = {}

    for k_number, data in structured_cache.items():
        device_sections = {}

        # Get metadata
        device_name = data.get("device_name", "Unknown")
        decision_date = data.get("decision_date", "")
        product_code = data.get("product_code", "")

        # Extract requested sections
        sections_data = data.get("sections", {})
        for section_type in section_types:
            if section_type in sections_data:
                section_text = sections_data[section_type].get("text", "")

                # Extract standards citations
                standards = extract_standards_from_text(section_text)

                device_sections[section_type] = {
                    'text': section_text,
                    'word_count': len(section_text.split()),
                    'standards': standards
                }

        if device_sections:  # Only include if at least one section found
            results[k_number] = {
                'sections': device_sections,
                'device_name': device_name,
                'decision_date': decision_date,
                'product_code': product_code
            }

    return results


def extract_standards_from_text(text: str) -> List[str]:
    """Extract FDA standards citations (ISO/IEC/ASTM) from text.

    Args:
        text: Section text

    Returns:
        List of unique standard citations found
    """
    standards = set()

    # Patterns for common standards
    patterns = [
        # ISO standards: ISO 10993-1, ISO-10993-1, ISO10993-1
        r'\bISO[\s-]?(\d{4,5})(?:[\s-](\d{1,2}))?\b',
        # IEC standards: IEC 60601-1-2, IEC-60601-1-2
        r'\bIEC[\s-]?(\d{4,5})(?:[\s-](\d{1,2}))?(?:[\s-](\d{1,2}))?\b',
        # ASTM standards: ASTM F1717, ASTM-F1717
        r'\bASTM[\s-]?([A-Z]\d{3,5})\b',
        # ANSI standards
        r'\bANSI[\s-]?([A-Z0-9\s-]+?)\b',
        # FDA recognized standards (often referenced by number alone in context)
        r'\b(ANSI/AAMI\s+[A-Z0-9:\s-]+?)\b'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Reconstruct standard citation
            if isinstance(match, tuple):
                # Handle multi-group matches (like ISO with parts)
                parts = [p for p in match if p]
                if len(parts) == 1:
                    std = parts[0]
                else:
                    std = '-'.join(parts)
            else:
                std = match

            # Normalize formatting
            std = std.replace(' ', '').replace('_', '-').upper()
            standards.add(std)

    return sorted(list(standards))


def generate_coverage_matrix(section_data: Dict, section_types: List[str]) -> Dict:
    """Generate coverage matrix showing which devices have which sections.

    Args:
        section_data: Output from extract_sections_batch()
        section_types: Section types being analyzed

    Returns:
        Dict with coverage statistics:
        {
            'total_devices': int,
            'section_coverage': {
                section_type: {
                    'count': int,
                    'percentage': float,
                    'devices': [k_numbers]
                }
            }
        }
    """
    total_devices = len(section_data)
    section_coverage = {}

    for section_type in section_types:
        devices_with_section = []
        for k_number, device in section_data.items():
            if section_type in device['sections']:
                devices_with_section.append(k_number)

        count = len(devices_with_section)
        percentage = (count / total_devices * 100) if total_devices > 0 else 0

        section_coverage[section_type] = {
            'count': count,
            'percentage': percentage,
            'devices': devices_with_section
        }

    return {
        'total_devices': total_devices,
        'section_coverage': section_coverage
    }


def analyze_standards_frequency(section_data: Dict) -> Dict:
    """Analyze frequency of standards citations across all sections.

    Args:
        section_data: Output from extract_sections_batch()

    Returns:
        Dict with standards analysis:
        {
            'total_devices': int,
            'standards_by_section': {
                section_type: {
                    standard: {
                        'count': int,
                        'percentage': float,
                        'devices': [k_numbers]
                    }
                }
            },
            'overall_standards': Counter of all standards
        }
    """
    total_devices = len(section_data)
    standards_by_section = defaultdict(lambda: defaultdict(list))
    overall_standards = Counter()

    for k_number, device in section_data.items():
        for section_type, section in device['sections'].items():
            for standard in section['standards']:
                standards_by_section[section_type][standard].append(k_number)
                overall_standards[standard] += 1

    # Convert to percentage format
    analysis = {
        'total_devices': total_devices,
        'standards_by_section': {},
        'overall_standards': overall_standards
    }

    for section_type, standards in standards_by_section.items():
        analysis['standards_by_section'][section_type] = {}
        for standard, devices in standards.items():
            count = len(devices)
            percentage = (count / total_devices * 100) if total_devices > 0 else 0
            analysis['standards_by_section'][section_type][standard] = {
                'count': count,
                'percentage': percentage,
                'devices': devices
            }

    return analysis


def detect_outliers(section_data: Dict, section_types: List[str]) -> List[Dict]:
    """Detect statistical outliers in section content (word count analysis).

    Uses Z-score analysis to flag unusual section lengths.

    Args:
        section_data: Output from extract_sections_batch()
        section_types: Section types being analyzed

    Returns:
        List of outlier findings:
        [
            {
                'k_number': str,
                'section_type': str,
                'finding': str,
                'word_count': int,
                'z_score': float,
                'explanation': str
            }
        ]
    """
    import statistics

    outliers = []

    for section_type in section_types:
        # Collect word counts for this section type
        word_counts = []
        device_word_counts = {}

        for k_number, device in section_data.items():
            if section_type in device['sections']:
                wc = device['sections'][section_type]['word_count']
                word_counts.append(wc)
                device_word_counts[k_number] = wc

        if len(word_counts) < 3:  # Need at least 3 data points for statistics
            continue

        # Calculate mean and std deviation
        mean_wc = statistics.mean(word_counts)
        try:
            stdev_wc = statistics.stdev(word_counts)
        except statistics.StatisticsError:
            continue  # All values are the same

        if stdev_wc == 0:
            continue

        # Calculate Z-scores and flag outliers (|Z| > 2)
        for k_number, wc in device_word_counts.items():
            z_score = (wc - mean_wc) / stdev_wc

            if abs(z_score) > 2:
                if z_score > 0:
                    finding = "Unusually long section"
                    explanation = f"{wc} words vs mean {mean_wc:.0f} words ({z_score:.1f}σ above mean)"
                else:
                    finding = "Unusually short section"
                    explanation = f"{wc} words vs mean {mean_wc:.0f} words ({abs(z_score):.1f}σ below mean)"

                outliers.append({
                    'k_number': k_number,
                    'device_name': section_data[k_number]['device_name'],
                    'section_type': section_type,
                    'finding': finding,
                    'word_count': wc,
                    'z_score': z_score,
                    'explanation': explanation
                })

    return sorted(outliers, key=lambda x: abs(x['z_score']), reverse=True)


def generate_markdown_report(product_code: str, section_types: List[str],
                             section_data: Dict, coverage: Dict,
                             standards_analysis: Dict, outliers: List[Dict],
                             output_path: str):
    """Generate comprehensive markdown report.

    Args:
        product_code: Product code analyzed
        section_types: Section types analyzed
        section_data: Extracted section data
        coverage: Coverage matrix
        standards_analysis: Standards frequency analysis
        outliers: Outlier detections
        output_path: Path to write markdown report
    """
    with open(output_path, 'w') as f:
        # Header
        f.write(f"# FDA 510(k) Section Comparison Report\n\n")
        f.write(f"**Product Code:** {product_code}\n\n")
        f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Devices Analyzed:** {coverage['total_devices']}\n\n")
        f.write(f"**Sections Analyzed:** {', '.join(section_types)}\n\n")

        f.write("---\n\n")

        # Section 1: Coverage Matrix
        f.write("## 1. Section Coverage Matrix\n\n")
        f.write("Percentage of devices containing each section type:\n\n")
        f.write("| Section Type | Devices | Coverage % |\n")
        f.write("|-------------|---------|------------|\n")

        for section_type in sorted(section_types):
            cov = coverage['section_coverage'].get(section_type, {})
            count = cov.get('count', 0)
            pct = cov.get('percentage', 0)
            f.write(f"| {section_type} | {count}/{coverage['total_devices']} | {pct:.1f}% |\n")

        f.write("\n")

        # Section 2: Standards Analysis
        f.write("## 2. FDA Standards Frequency Analysis\n\n")
        f.write("Most commonly cited FDA-recognized standards across all sections:\n\n")

        top_standards = standards_analysis['overall_standards'].most_common(20)
        if top_standards:
            f.write("| Standard | Citations | Percentage |\n")
            f.write("|----------|-----------|------------|\n")
            for standard, count in top_standards:
                pct = (count / coverage['total_devices'] * 100) if coverage['total_devices'] > 0 else 0
                f.write(f"| {standard} | {count} | {pct:.1f}% |\n")
        else:
            f.write("*No standards citations detected*\n")

        f.write("\n")

        # Standards by section
        f.write("### Standards by Section Type\n\n")
        for section_type in section_types:
            section_standards = standards_analysis['standards_by_section'].get(section_type, {})
            if not section_standards:
                continue

            f.write(f"#### {section_type}\n\n")
            f.write("| Standard | Devices | Coverage % |\n")
            f.write("|----------|---------|------------|\n")

            # Sort by percentage descending
            sorted_standards = sorted(section_standards.items(),
                                     key=lambda x: x[1]['percentage'], reverse=True)
            for standard, data in sorted_standards[:10]:  # Top 10
                f.write(f"| {standard} | {data['count']}/{coverage['total_devices']} | {data['percentage']:.1f}% |\n")

            f.write("\n")

        # Section 3: Key Findings
        f.write("## 3. Key Findings\n\n")

        # Identify sections with low coverage
        low_coverage = []
        for section_type, cov in coverage['section_coverage'].items():
            if cov['percentage'] < 50:
                low_coverage.append((section_type, cov['percentage']))

        if low_coverage:
            f.write("### Sections with Low Coverage (<50%)\n\n")
            for section_type, pct in sorted(low_coverage, key=lambda x: x[1]):
                f.write(f"- **{section_type}**: {pct:.1f}% coverage\n")
            f.write("\n")

        # Identify ubiquitous standards
        ubiquitous = [(std, count) for std, count in top_standards if count / coverage['total_devices'] > 0.95]
        if ubiquitous:
            f.write("### Ubiquitous Standards (>95% of devices)\n\n")
            for std, count in ubiquitous:
                pct = (count / coverage['total_devices'] * 100)
                f.write(f"- **{std}**: {pct:.1f}% of devices\n")
            f.write("\n")

        # Section 4: Outliers
        f.write("## 4. Statistical Outliers\n\n")
        if outliers:
            f.write("Devices with unusual section lengths (|Z-score| > 2):\n\n")
            f.write("| K-Number | Device Name | Section | Finding | Z-Score |\n")
            f.write("|----------|-------------|---------|---------|----------|\n")
            for outlier in outliers[:20]:  # Top 20
                f.write(f"| {outlier['k_number']} | {outlier['device_name'][:40]} | {outlier['section_type']} | {outlier['finding']} | {outlier['z_score']:.2f} |\n")

            if len(outliers) > 20:
                f.write(f"\n*...and {len(outliers) - 20} more outliers*\n")
        else:
            f.write("*No statistical outliers detected*\n")

        f.write("\n")

        # Footer
        f.write("---\n\n")
        f.write("**Generated by:** FDA Tools Plugin v5.24.0\n\n")
        f.write(f"**Report Type:** Section Comparison Analysis\n\n")
        f.write("**Note:** This analysis is for regulatory intelligence only. Always verify standards applicability with current FDA guidance.\n")


def generate_csv_export(product_code: str, section_types: List[str],
                       section_data: Dict, output_path: str):
    """Generate CSV export for structured data analysis.

    Args:
        product_code: Product code analyzed
        section_types: Section types analyzed
        section_data: Extracted section data
        output_path: Path to write CSV file
    """
    import csv

    with open(output_path, 'w', newline='') as f:
        # Build column headers
        headers = ['k_number', 'device_name', 'decision_date', 'product_code']

        # Add section presence flags
        for section_type in section_types:
            headers.append(f'has_{section_type}')

        # Add word count columns
        for section_type in section_types:
            headers.append(f'{section_type}_words')

        # Add standards columns
        for section_type in section_types:
            headers.append(f'{section_type}_standards')

        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        # Write rows
        for k_number, device in sorted(section_data.items()):
            row = {
                'k_number': k_number,
                'device_name': device['device_name'],
                'decision_date': device['decision_date'],
                'product_code': device['product_code']
            }

            # Section presence flags
            for section_type in section_types:
                row[f'has_{section_type}'] = 1 if section_type in device['sections'] else 0

            # Word counts
            for section_type in section_types:
                if section_type in device['sections']:
                    row[f'{section_type}_words'] = device['sections'][section_type]['word_count']
                else:
                    row[f'{section_type}_words'] = 0

            # Standards
            for section_type in section_types:
                if section_type in device['sections']:
                    standards = device['sections'][section_type]['standards']
                    row[f'{section_type}_standards'] = '; '.join(standards) if standards else ''
                else:
                    row[f'{section_type}_standards'] = ''

            writer.writerow(row)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FDA 510(k) Section Comparison Tool"
    )
    parser.add_argument("--product-code", required=True,
                        help="FDA product code (e.g., DQY, OVE)")
    parser.add_argument("--sections", required=True,
                        help="Comma-separated section types or 'all' (e.g., clinical,biocompat,performance)")
    parser.add_argument("--years",
                        help="Year range filter (e.g., 2020-2025)")
    parser.add_argument("--limit", type=int,
                        help="Limit number of devices analyzed")
    parser.add_argument("--output",
                        help="Output file path (defaults to product_code_comparison_TIMESTAMP.md)")
    parser.add_argument("--csv", action="store_true",
                        help="Also generate CSV export")
    parser.add_argument("--quiet", action="store_true",
                        help="Minimal output (for scripting)")

    args = parser.parse_args()
    verbose = not args.quiet

    # Parse sections
    if args.sections.lower() == 'all':
        section_types = list(SECTION_PATTERNS.keys())
    else:
        requested_sections = [s.strip() for s in args.sections.split(',')]
        section_types = []
        for s in requested_sections:
            canonical = SECTION_ALIASES.get(s.lower(), s)
            if canonical in SECTION_PATTERNS:
                section_types.append(canonical)
            else:
                print(f"⚠️  Warning: Unknown section type '{s}', skipping")

        if not section_types:
            print("❌ Error: No valid section types specified")
            sys.exit(1)

    # Parse year range
    year_start, year_end = None, None
    if args.years:
        try:
            if '-' in args.years:
                start_str, end_str = args.years.split('-')
                year_start = int(start_str.strip())
                year_end = int(end_str.strip())
            else:
                year_start = year_end = int(args.years.strip())
        except ValueError:
            print(f"❌ Error: Invalid year format '{args.years}'. Use YYYY or YYYY-YYYY")
            sys.exit(1)

    # Load structured cache
    if verbose:
        print("📂 Loading structured cache...")

    cache = load_structured_cache()
    if not cache:
        print("❌ Error: No structured cache found. Run build_structured_cache.py first.")
        sys.exit(1)

    # Filter by product code
    if verbose:
        print(f"🔍 Filtering by product code: {args.product_code}")

    cache = filter_by_product_code(cache, args.product_code)
    if not cache:
        print(f"❌ Error: No devices found for product code {args.product_code}")
        sys.exit(1)

    # Filter by year range
    if year_start or year_end:
        if verbose:
            year_range = f"{year_start}-{year_end}" if year_start != year_end else str(year_start)
            print(f"📅 Filtering by year range: {year_range}")
        cache = filter_by_year_range(cache, year_start, year_end)

    # Apply limit
    if args.limit and len(cache) > args.limit:
        if verbose:
            print(f"⚠️  Limiting to {args.limit} devices (from {len(cache)} available)")
        # Sort by decision date descending and take limit
        sorted_cache = sorted(cache.items(), key=lambda x: x[1].get('decision_date', ''), reverse=True)
        cache = dict(sorted_cache[:args.limit])

    if verbose:
        print(f"✅ Processing {len(cache)} devices...")
        print(f"📝 Analyzing {len(section_types)} section types...")

    # Extract sections
    section_data = extract_sections_batch(cache, section_types)

    if not section_data:
        print("❌ Error: No devices found with requested sections")
        sys.exit(1)

    # Generate analysis
    if verbose:
        print("📊 Generating coverage matrix...")
    coverage = generate_coverage_matrix(section_data, section_types)

    if verbose:
        print("🔬 Analyzing standards frequency...")
    standards_analysis = analyze_standards_frequency(section_data)

    if verbose:
        print("🎯 Detecting outliers...")
    outliers = detect_outliers(section_data, section_types)

    # Generate output path
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(os.path.expanduser(f"~/fda-510k-data/projects/section_comparison_{args.product_code}_{timestamp}"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{args.product_code}_comparison.md"
    else:
        output_path = Path(args.output)
        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

    # Generate markdown report
    if verbose:
        print(f"📄 Writing markdown report to {output_path}...")
    generate_markdown_report(
        args.product_code,
        section_types,
        section_data,
        coverage,
        standards_analysis,
        outliers,
        str(output_path)
    )

    # Generate CSV if requested
    csv_path = None
    if args.csv:
        csv_path = output_path.with_suffix('.csv')
        if verbose:
            print(f"💾 Writing CSV export to {csv_path}...")
        generate_csv_export(args.product_code, section_types, section_data, str(csv_path))

    # Print summary
    if verbose:
        print("\n" + "=" * 60)
        print("✅ Analysis Complete!")
        print("=" * 60)
        print(f"Devices analyzed: {len(section_data)}")
        print(f"Sections analyzed: {len(section_types)}")
        print(f"Standards identified: {len(standards_analysis['overall_standards'])}")
        print(f"Outliers detected: {len(outliers)}")
        print(f"\nReport: {output_path}")
        if csv_path:
            print(f"CSV: {csv_path}")
    else:
        # JSON output for scripting
        result = {
            'devices_analyzed': len(section_data),
            'sections_analyzed': len(section_types),
            'standards_identified': len(standards_analysis['overall_standards']),
            'outliers_detected': len(outliers),
            'report_path': str(output_path)
        }
        if csv_path:
            result['csv_path'] = str(csv_path)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
