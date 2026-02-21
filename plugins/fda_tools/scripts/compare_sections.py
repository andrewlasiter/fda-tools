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
    python3 compare_sections.py --product-codes DQY,OVE --sections clinical --similarity --trends

Features:
    - Multi-device section extraction from structured cache
    - Coverage matrix (which devices have which sections)
    - FDA standards frequency analysis (ISO/IEC/ASTM citations)
    - Statistical outlier detection (Z-score analysis)
    - Markdown report + CSV export for regulatory review
    - Cross-product-code comparison (--product-codes with multiple codes)
    - Text similarity analysis (--similarity)
    - Temporal trend analysis (--trends)
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import section patterns from build_structured_cache
from build_structured_cache import SECTION_PATTERNS
from section_analytics import (
    compute_similarity,
    pairwise_similarity_matrix,
    analyze_temporal_trends,
    cross_product_compare,
)
from fda_tools.lib.subprocess_helpers import run_subprocess  # type: ignore
from trend_visualization import (  # type: ignore
    generate_ascii_chart,
    generate_svg_chart,
    format_trend_table,
)

# Import similarity cache stats for reporting
from fda_tools.lib.import_helpers import safe_import
_cache_stats_result = safe_import('fda_tools.scripts.similarity_cache', 'get_cache_stats')
CACHE_STATS_AVAILABLE = _cache_stats_result.success
get_cache_stats = _cache_stats_result.module if CACHE_STATS_AVAILABLE else None


# ---------------------------------------------------------------------------
# Progress Bar for Long-Running Operations
# ---------------------------------------------------------------------------

class ProgressBar:
    """Simple CLI progress bar for long-running computations.

    Displays a progress bar with percentage, current/total counts, and ETA.
    Updates in-place using ANSI escape codes.

    Example output:
        Computing similarity matrix...
        [████████████░░░░] 75% (3712/4950 pairs) ETA: 15s
    """

    def __init__(self, total: int, description: str = "", width: int = 20):
        """Initialize progress bar.

        Args:
            total: Total number of iterations expected.
            description: Description to display above the bar.
            width: Width of the progress bar in characters.
        """
        self.total = total
        self.description = description
        self.width = width
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_current = 0

        if description:
            print(description)

    def update(self, current: int, message: str = ""):
        """Update the progress bar.

        Args:
            current: Current iteration count (1-based or 0-based, as long as consistent).
            message: Optional additional message to display.
        """
        if self.total == 0:
            return

        # Calculate percentage
        pct = min(100, int((current / self.total) * 100))

        # Calculate ETA
        elapsed = time.time() - self.start_time
        if current > 0 and elapsed > 0:
            rate = current / elapsed
            remaining = (self.total - current) / rate if rate > 0 else 0
            eta_str = f"ETA: {int(remaining)}s"
        else:
            eta_str = "ETA: calculating..."

        # Build progress bar
        filled = int(self.width * current / self.total)
        bar = "█" * filled + "░" * (self.width - filled)

        # Display progress
        msg_suffix = f" {message}" if message else ""
        print(f"\r[{bar}] {pct}% ({current}/{self.total} pairs) {eta_str}{msg_suffix}", end="", flush=True)

    def finish(self):
        """Complete the progress bar and move to next line."""
        print()


# ---------------------------------------------------------------------------
# Section type mapping for user-friendly names
# ---------------------------------------------------------------------------

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
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Failed to load cache file {cache_file}: {e}", file=sys.stderr)

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
            except (ValueError, IndexError) as e:
                print(f"Warning: Could not parse year from decision_date: {e}", file=sys.stderr)

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
                             _section_data: Dict, coverage: Dict,
                             standards_analysis: Dict, outliers: List[Dict],
                             output_path: str):
    """Generate comprehensive markdown report.

    Args:
        product_code: Product code analyzed
        section_types: Section types analyzed
        _section_data: Extracted section data (unused - coverage/standards/outliers
            are pre-computed from section_data before calling this function)
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
        # Use dynamic version from plugin.json via version.py
        try:
            from version import PLUGIN_VERSION
        except ImportError:
            PLUGIN_VERSION = "5.27.0"
        f.write(f"**Generated by:** FDA Tools Plugin v{PLUGIN_VERSION}\n\n")
        f.write(f"**Report Type:** Section Comparison Analysis\n\n")
        f.write("**Note:** This analysis is for regulatory intelligence only. Always verify standards applicability with current FDA guidance.\n")


def append_similarity_section(output_path: str, similarity_results: Dict):
    """Append similarity analysis section to the markdown report.

    Args:
        output_path: Path to existing markdown report.
        similarity_results: Output from pairwise_similarity_matrix().
    """
    with open(output_path, 'a') as f:
        f.write("\n---\n\n")
        f.write("## 5. Text Similarity Analysis\n\n")

        section_type = similarity_results.get("section_type", "")
        method = similarity_results.get("method", "")
        stats = similarity_results.get("statistics", {})
        n_devices = similarity_results.get("devices_compared", 0)
        n_pairs = similarity_results.get("pairs_computed", 0)

        f.write(f"**Section:** {section_type}\n\n")
        f.write(f"**Method:** {method}\n\n")
        f.write(f"**Devices compared:** {n_devices} ({n_pairs} pairs)\n\n")

        if n_pairs > 0:
            f.write("### Similarity Statistics\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Mean | {stats.get('mean', 0):.4f} |\n")
            f.write(f"| Median | {stats.get('median', 0):.4f} |\n")
            f.write(f"| Min | {stats.get('min', 0):.4f} |\n")
            f.write(f"| Max | {stats.get('max', 0):.4f} |\n")
            f.write(f"| Std Dev | {stats.get('stdev', 0):.4f} |\n")
            f.write("\n")

            most = similarity_results.get("most_similar_pair")
            least = similarity_results.get("least_similar_pair")

            if most:
                f.write(f"**Most similar pair:** {most['devices'][0]} & {most['devices'][1]} ")
                f.write(f"(score: {most['score']:.4f})\n\n")
            if least:
                f.write(f"**Least similar pair:** {least['devices'][0]} & {least['devices'][1]} ")
                f.write(f"(score: {least['score']:.4f})\n\n")

            # Interpret results
            mean_val = stats.get("mean", 0)
            f.write("### Interpretation\n\n")
            if mean_val > 0.8:
                f.write("- **High similarity** across devices. Sections follow a consistent structure.\n")
                f.write("- Strategy: Follow established patterns closely.\n")
            elif mean_val > 0.5:
                f.write("- **Moderate similarity** across devices. Some variation in approach.\n")
                f.write("- Strategy: Align with common patterns while differentiating where appropriate.\n")
            else:
                f.write("- **Low similarity** across devices. High variation in section content.\n")
                f.write("- Strategy: Review multiple approaches and choose the most thorough.\n")
            f.write("\n")
        else:
            f.write("*Insufficient data for similarity analysis (need at least 2 devices)*\n\n")


def append_trends_section(output_path: str, trends_results: Dict):
    """Append temporal trends section to the markdown report.

    Enhanced with ASCII trend charts and detailed change analysis.

    Args:
        output_path: Path to existing markdown report.
        trends_results: Output from analyze_temporal_trends().
    """
    with open(output_path, 'a') as f:
        f.write("\n---\n\n")
        f.write("## 6. Temporal Trend Analysis\n\n")

        year_range = trends_results.get("year_range", {})
        f.write(f"**Year range:** {year_range.get('start', '?')} - {year_range.get('end', '?')}\n\n")
        f.write(f"**Total devices:** {trends_results.get('total_devices', 0)}\n\n")

        trends = trends_results.get("trends", {})
        if not trends:
            f.write("*No temporal data available*\n\n")
            return

        for section_type, section_trends in trends.items():
            f.write(f"### {section_type}\n\n")

            # Coverage trend
            coverage = section_trends.get("coverage_trend", {})
            direction = coverage.get("direction", "unknown")
            r_sq = coverage.get("r_squared", 0)
            f.write(f"**Coverage trend:** {direction}")
            if direction not in ("insufficient_data",):
                f.write(f" (R²={r_sq:.3f}, slope={coverage.get('slope', 0):.2f})")
            f.write("\n\n")

            # Length trend
            length = section_trends.get("length_trend", {})
            l_direction = length.get("direction", "unknown")
            f.write(f"**Section length trend:** {l_direction}")
            if l_direction not in ("insufficient_data",):
                f.write(f" (R²={length.get('r_squared', 0):.3f})")
            f.write("\n\n")

            # Generate ASCII trend chart
            try:
                ascii_chart = generate_ascii_chart(trends_results, section_type)
                f.write(ascii_chart)
                f.write("\n")
            except (ValueError, KeyError) as e:
                f.write(f"*Unable to generate chart: {e}*\n\n")

            # Year-by-year table with change indicators
            by_year = section_trends.get("by_year", {})
            if by_year:
                f.write("#### Detailed Year-by-Year Data\n\n")
                trend_table = format_trend_table(trends_results, section_type)
                f.write(trend_table)
                f.write("\n")


def append_cross_product_section(output_path: str, cross_results: Dict):
    """Append cross-product comparison section to the markdown report.

    Args:
        output_path: Path to existing markdown report.
        cross_results: Output from cross_product_compare().
    """
    with open(output_path, 'a') as f:
        f.write("\n---\n\n")
        f.write("## 7. Cross-Product Code Comparison\n\n")

        product_codes = cross_results.get("product_codes", [])
        f.write(f"**Product codes compared:** {', '.join(product_codes)}\n\n")

        comparison = cross_results.get("comparison", {})
        if not comparison:
            f.write("*No cross-product comparison data available*\n\n")
            return

        for section_type, by_code in comparison.items():
            f.write(f"### {section_type}\n\n")
            f.write("| Product Code | Devices | Coverage % | Avg Words | Top Standard |\n")
            f.write("|-------------|---------|------------|-----------|-------------|\n")

            for pc, data in sorted(by_code.items()):
                top_std = ""
                top_stds = data.get("top_standards", [])
                if top_stds:
                    top_std = f"{top_stds[0][0]} ({top_stds[0][1]})"

                f.write(
                    f"| {pc} "
                    f"| {data.get('device_count', 0)} "
                    f"| {data.get('coverage_pct', 0):.1f}% "
                    f"| {data.get('avg_word_count', 0):.0f} "
                    f"| {top_std} |\n"
                )
            f.write("\n")

        # Summary
        summary = cross_results.get("summary", {})
        highest = summary.get("highest_coverage", {})
        longest = summary.get("longest_sections", {})

        if highest:
            f.write("### Summary\n\n")
            f.write("**Highest coverage by section:**\n\n")
            for section_type, pc in highest.items():
                f.write(f"- {section_type}: **{pc}**\n")
            f.write("\n")

        if longest:
            f.write("**Longest sections by section:**\n\n")
            for section_type, pc in longest.items():
                f.write(f"- {section_type}: **{pc}**\n")
            f.write("\n")


def generate_csv_export(_product_code: str, section_types: List[str],
                       section_data: Dict, output_path: str):
    """Generate CSV export for structured data analysis.

    Args:
        _product_code: Product code analyzed (unused - each device row uses its
            own product_code from section_data)
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


def generate_html_report(
    product_code: str,
    section_types: List[str],
    coverage: Dict,
    standards_analysis: Dict,
    trends_results: Optional[Dict],
    output_path: str
):
    """Generate HTML report with SVG charts.

    Args:
        product_code: Product code analyzed.
        section_types: Section types analyzed.
        coverage: Coverage matrix data.
        standards_analysis: Standards frequency analysis.
        trends_results: Temporal trends analysis (optional).
        output_path: Path to write HTML file.
    """
    with open(output_path, 'w') as f:
        # HTML header
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FDA 510(k) Section Comparison Report - {product_code}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #0066cc;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #0066cc;
            margin-top: 30px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        h3 {{
            color: #444;
            margin-top: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f5f5f5;
            font-weight: 600;
            color: #555;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        .chart-container {{
            margin: 20px 0;
            padding: 15px;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metadata {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .metadata p {{
            margin: 5px 0;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ddd;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <h1>FDA 510(k) Section Comparison Report</h1>
    <div class="metadata">
        <p><strong>Product Code:</strong> {product_code}</p>
        <p><strong>Analysis Date:</strong> {timestamp}</p>
        <p><strong>Devices Analyzed:</strong> {device_count}</p>
        <p><strong>Sections Analyzed:</strong> {sections}</p>
    </div>
""".format(
            product_code=product_code,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M'),
            device_count=coverage['total_devices'],
            sections=', '.join(section_types)
        ))

        # Coverage matrix
        f.write("<h2>Section Coverage Matrix</h2>\n")
        f.write("<table>\n")
        f.write("<thead><tr><th>Section Type</th><th>Devices</th><th>Coverage %</th></tr></thead>\n")
        f.write("<tbody>\n")
        for section_type in sorted(section_types):
            cov = coverage['section_coverage'].get(section_type, {})
            count = cov.get('count', 0)
            pct = cov.get('percentage', 0)
            f.write(
                f"<tr><td>{section_type}</td>"
                f"<td>{count}/{coverage['total_devices']}</td>"
                f"<td>{pct:.1f}%</td></tr>\n"
            )
        f.write("</tbody></table>\n")

        # Standards analysis
        f.write("<h2>FDA Standards Frequency Analysis</h2>\n")
        top_standards = standards_analysis['overall_standards'].most_common(20)
        if top_standards:
            f.write("<table>\n")
            f.write("<thead><tr><th>Standard</th><th>Citations</th><th>Percentage</th></tr></thead>\n")
            f.write("<tbody>\n")
            for standard, count in top_standards:
                pct = (count / coverage['total_devices'] * 100) if coverage['total_devices'] > 0 else 0
                f.write(f"<tr><td>{standard}</td><td>{count}</td><td>{pct:.1f}%</td></tr>\n")
            f.write("</tbody></table>\n")
        else:
            f.write("<p><em>No standards citations detected</em></p>\n")

        # Temporal trends with SVG charts
        if trends_results:
            f.write("<h2>Temporal Trend Analysis</h2>\n")
            year_range = trends_results.get("year_range", {})
            f.write(f"<p><strong>Year range:</strong> {year_range.get('start', '?')} - {year_range.get('end', '?')}</p>\n")

            trends = trends_results.get("trends", {})
            for section_type in section_types:
                if section_type in trends:
                    f.write(f"<h3>{section_type.replace('_', ' ').title()}</h3>\n")

                    section_trends = trends[section_type]
                    coverage_trend = section_trends.get("coverage_trend", {})
                    length_trend = section_trends.get("length_trend", {})

                    f.write(f"<p><strong>Coverage trend:</strong> {coverage_trend.get('direction', 'unknown')}")
                    if coverage_trend.get("direction") not in ("insufficient_data",):
                        f.write(f" (R²={coverage_trend.get('r_squared', 0):.3f}, slope={coverage_trend.get('slope', 0):.2f})")
                    f.write("</p>\n")

                    f.write(f"<p><strong>Section length trend:</strong> {length_trend.get('direction', 'unknown')}")
                    if length_trend.get("direction") not in ("insufficient_data",):
                        f.write(f" (R²={length_trend.get('r_squared', 0):.3f})")
                    f.write("</p>\n")

                    # Generate SVG chart
                    try:
                        f.write('<div class="chart-container">\n')
                        svg_chart = generate_svg_chart(trends_results, section_type)
                        f.write(svg_chart)
                        f.write('\n</div>\n')
                    except (ValueError, KeyError) as e:
                        f.write(f"<p><em>Unable to generate chart: {e}</em></p>\n")

        # Footer
        try:
            from version import PLUGIN_VERSION
        except ImportError:
            PLUGIN_VERSION = "5.27.0"

        f.write(f"""
    <div class="footer">
        <p><strong>Generated by:</strong> FDA Tools Plugin v{PLUGIN_VERSION}</p>
        <p><strong>Report Type:</strong> Section Comparison Analysis (HTML)</p>
        <p><strong>Note:</strong> This analysis is for regulatory intelligence only. Always verify standards applicability with current FDA guidance.</p>
    </div>
</body>
</html>
""")



def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FDA 510(k) Section Comparison Tool"
    )
    parser.add_argument("--product-code",
                        help="FDA product code (e.g., DQY, OVE)")
    parser.add_argument("--product-codes", dest="product_codes",
                        help="Multiple product codes for cross-comparison (e.g., DQY,OVE,GEI)")
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
    parser.add_argument("--html", action="store_true",
                        help="Also generate HTML report with SVG charts")
    parser.add_argument("--similarity", action="store_true",
                        help="Compute pairwise text similarity for each section type")
    parser.add_argument("--similarity-method", dest="similarity_method",
                        default="cosine", choices=["sequence", "jaccard", "cosine", "auto"],
                        help="Similarity method (default: cosine). Use 'auto' for heuristic selection based on text characteristics (FDA-39).")
    parser.add_argument("--similarity-sample", dest="similarity_sample", type=int,
                        default=30,
                        help="Max devices for similarity matrix (default: 30, for performance)")
    parser.add_argument("--trends", action="store_true",
                        help="Analyze year-over-year temporal trends")
    parser.add_argument("--no-cache", dest="no_cache", action="store_true",
                        help="Bypass similarity score cache (force recomputation)")
    parser.add_argument("--quiet", action="store_true",
                        help="Minimal output (for scripting)")

    args = parser.parse_args()
    verbose = not args.quiet

    # Validate: need at least one of --product-code or --product-codes
    if not args.product_code and not args.product_codes:
        parser.error("--product-code or --product-codes is required")

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

    # Determine product codes to process
    multi_code_mode = bool(args.product_codes)
    if multi_code_mode:
        all_product_codes = [pc.strip().upper() for pc in args.product_codes.split(",") if pc.strip()]
        primary_product_code = all_product_codes[0]  # Use first for single-code operations
    else:
        primary_product_code = args.product_code.upper()
        all_product_codes = [primary_product_code]

    # Load structured cache (with auto-build if empty)
    if verbose:
        print("Loading structured cache...")

    cache = load_structured_cache()
    if not cache:
        # Attempt auto-build
        build_script = Path(__file__).resolve().parent / "build_structured_cache.py"
        cache_dir = Path(os.path.expanduser("~/fda-510k-data/extraction/cache"))
        if build_script.exists() and cache_dir.exists():
            if verbose:
                print("No structured cache found. Auto-building from extraction cache...")

            cmd = [sys.executable, str(build_script), "--cache-dir", str(cache_dir)]
            result = run_command(
                cmd=cmd,                timeout=300,
                cwd=str(build_script.parent),
                verbose=verbose
            )

            if result["status"] == "success":
                cache = load_structured_cache()
            elif result["status"] == "timeout" and verbose:
                print("  Suggestion: Check that extraction cache files exist in "
                      f"{cache_dir} and try running build_structured_cache.py manually.")

        if not cache:
            print("Error: No structured cache found. Run build_structured_cache.py first.")
            sys.exit(1)

    # Store full cache for cross-product comparison if needed
    full_cache = cache if multi_code_mode else None

    # Filter by product code (use primary for single-code analysis)
    if verbose:
        print(f"Filtering by product code: {primary_product_code}")

    cache = filter_by_product_code(cache, primary_product_code)
    if not cache:
        print(f"Error: No devices found for product code {primary_product_code}")
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
    _code_label = ",".join(all_product_codes) if multi_code_mode else primary_product_code
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(os.path.expanduser(f"~/fda-510k-data/projects/section_comparison_{primary_product_code}_{timestamp}"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{primary_product_code}_comparison.md"
    else:
        output_path = Path(args.output)
        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

    # Generate markdown report (base report)
    if verbose:
        print(f"Writing markdown report to {output_path}...")
    generate_markdown_report(
        primary_product_code,
        section_types,
        section_data,
        coverage,
        standards_analysis,
        outliers,
        str(output_path)
    )

    # --- Extended analytics ---

    # Similarity analysis
    similarity_results = {}
    if args.similarity:
        use_cache = not args.no_cache
        if verbose:
            cache_status = "disabled" if args.no_cache else "enabled"
            print(f"Computing text similarity (method: {args.similarity_method}, "
                  f"sample: {args.similarity_sample}, cache: {cache_status})...")

        for section_type in section_types:
            # Create progress callback if verbose mode
            progress_bar = None
            progress_callback = None

            if verbose:
                # Count devices with this section for progress bar initialization
                devices_with_section = sum(
                    1 for device in section_data.values()
                    if section_type in device.get("sections", {})
                )
                # Limit by sample_size if provided
                if args.similarity_sample:
                    devices_with_section = min(devices_with_section, args.similarity_sample)

                if devices_with_section >= 2:
                    total_pairs = (devices_with_section * (devices_with_section - 1)) // 2
                    progress_bar = ProgressBar(
                        total_pairs,
                        description=f"  Computing similarity for {section_type}..."
                    )

                    def progress_callback(current: int, _total: int, message: str):
                        if progress_bar:
                            progress_bar.update(current, message)

            sim_result = pairwise_similarity_matrix(
                section_data,
                section_type,
                method=args.similarity_method,
                sample_size=args.similarity_sample,
                use_cache=use_cache,
                progress_callback=progress_callback,
            )
            similarity_results[section_type] = sim_result

            # Finish progress bar if it was created
            if progress_bar:
                progress_bar.finish()

            if sim_result.get("pairs_computed", 0) > 0:
                append_similarity_section(str(output_path), sim_result)
                if verbose:
                    stats = sim_result.get("statistics", {})
                    cache_indicator = "CACHE HIT" if sim_result.get("cache_hit") else "computed"
                    comp_time = sim_result.get("computation_time", 0)
                    print(f"  {section_type}: mean={stats.get('mean', 0):.3f}, "
                          f"stdev={stats.get('stdev', 0):.3f}, "
                          f"pairs={sim_result.get('pairs_computed', 0)}, "
                          f"{cache_indicator} ({comp_time:.2f}s)")

    # Temporal trends
    trends_results = {}
    if args.trends:
        if verbose:
            print("Analyzing temporal trends...")
        trends_results = analyze_temporal_trends(section_data, section_types)
        append_trends_section(str(output_path), trends_results)

        if verbose:
            for section_type, st in trends_results.get("trends", {}).items():
                cov = st.get("coverage_trend", {})
                print(f"  {section_type}: coverage {cov.get('direction', '?')} "
                      f"(R2={cov.get('r_squared', 0):.3f})")

    # Cross-product comparison
    cross_results = {}
    if multi_code_mode and full_cache:
        if verbose:
            print(f"Running cross-product comparison: {', '.join(all_product_codes)}...")
        cross_results = cross_product_compare(
            all_product_codes, section_types, full_cache
        )
        append_cross_product_section(str(output_path), cross_results)

        if verbose:
            for section_type, by_code in cross_results.get("comparison", {}).items():
                parts = []
                for pc, data in by_code.items():
                    parts.append(f"{pc}={data.get('coverage_pct', 0):.0f}%")
                print(f"  {section_type}: {', '.join(parts)}")

    # Generate CSV if requested
    csv_path = None
    if args.csv:
        csv_path = output_path.with_suffix('.csv')
        if verbose:
            print(f"Writing CSV export to {csv_path}...")
        generate_csv_export(primary_product_code, section_types, section_data, str(csv_path))

    # Generate HTML if requested
    html_path = None
    if args.html:
        html_path = output_path.with_suffix('.html')
        if verbose:
            print(f"Writing HTML report with SVG charts to {html_path}...")
        generate_html_report(
            primary_product_code,
            section_types,
            coverage,
            standards_analysis,
            trends_results if args.trends else None,
            str(html_path)
        )

    # Print summary
    if verbose:
        print("\n" + "=" * 60)
        print("Analysis Complete!")
        print("=" * 60)
        print(f"Devices analyzed: {len(section_data)}")
        print(f"Sections analyzed: {len(section_types)}")
        print(f"Standards identified: {len(standards_analysis['overall_standards'])}")
        print(f"Outliers detected: {len(outliers)}")
        if args.similarity:
            print(f"Similarity computed: {sum(r.get('pairs_computed', 0) for r in similarity_results.values())} pairs")

            # Display cache statistics
            if CACHE_STATS_AVAILABLE and not args.no_cache:
                cache_stats = get_cache_stats()
                if cache_stats['total_queries'] > 0:
                    print(f"\nCache Performance:")
                    print(f"  Hits: {cache_stats['hits']}, Misses: {cache_stats['misses']}")
                    print(f"  Hit Rate: {cache_stats['hit_rate']:.1%}")
                    if cache_stats['hits'] > 0:
                        print(f"  Speedup: ~30x on cached queries")

        if args.trends:
            print(f"Trend analysis: {len(trends_results.get('trends', {}))} section(s)")
        if multi_code_mode:
            print(f"Cross-product codes: {', '.join(all_product_codes)}")
        print(f"\nReport: {output_path}")
        if csv_path:
            print(f"CSV: {csv_path}")
        if html_path:
            print(f"HTML: {html_path}")
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
        if html_path:
            result['html_path'] = str(html_path)
        if args.similarity:
            result['similarity'] = {
                st: {
                    'mean': r.get('statistics', {}).get('mean', 0),
                    'stdev': r.get('statistics', {}).get('stdev', 0),
                    'pairs': r.get('pairs_computed', 0),
                }
                for st, r in similarity_results.items()
            }
        if args.trends:
            result['trends'] = {
                st: t.get('coverage_trend', {}).get('direction', 'unknown')
                for st, t in trends_results.get('trends', {}).items()
            }
        if multi_code_mode:
            result['cross_product_codes'] = all_product_codes
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
