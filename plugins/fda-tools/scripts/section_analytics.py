#!/usr/bin/env python3
"""
FDA 510(k) Section Analytics -- Advanced section comparison and trend analysis.

Provides text similarity computation, pairwise similarity matrices, temporal
trend analysis, and cross-product-code comparison for structured 510(k) section
data. Uses only Python standard library (no scikit-learn or numpy required).

Core functions:
    compute_similarity(text_a, text_b, method) -> float (0.0-1.0)
    pairwise_similarity_matrix(section_data, section_type, method, sample_size) -> dict
    analyze_temporal_trends(section_data, section_types) -> dict
    cross_product_compare(product_codes, section_types, structured_cache) -> dict

Usage:
    from section_analytics import (
        compute_similarity,
        pairwise_similarity_matrix,
        analyze_temporal_trends,
        cross_product_compare,
    )

    # Compare two text sections
    score = compute_similarity(text_a, text_b, method='sequence')

    # Build a similarity matrix for a section type
    matrix = pairwise_similarity_matrix(section_data, 'clinical_testing')

    # Analyze trends over time
    trends = analyze_temporal_trends(section_data, ['clinical_testing', 'biocompatibility'])

    # Cross-product comparison
    comparison = cross_product_compare(['DQY', 'OVE'], ['clinical_testing'], cache)
"""

import argparse
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional, Tuple

# Import sibling modules for cache loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import similarity cache module
try:
    from similarity_cache import (  # type: ignore
        generate_cache_key,
        get_cached_similarity_matrix,
        save_similarity_matrix,
        get_cache_stats,
    )
    SIMILARITY_CACHE_AVAILABLE = True
except ImportError:
    SIMILARITY_CACHE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Text Similarity Functions
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words, removing punctuation.

    Args:
        text: Input text string.

    Returns:
        List of lowercase word tokens.
    """
    return re.findall(r'[a-z0-9]+', text.lower())


def _cosine_similarity_stdlib(text_a: str, text_b: str) -> float:
    """Compute cosine similarity between two texts using stdlib only.

    Uses term-frequency vectors (bag-of-words) without external libraries.

    Args:
        text_a: First text.
        text_b: Second text.

    Returns:
        Cosine similarity score (0.0 to 1.0).
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    freq_a = Counter(tokens_a)
    freq_b = Counter(tokens_b)

    # All unique terms
    all_terms = set(freq_a.keys()) | set(freq_b.keys())

    # Dot product
    dot_product = sum(freq_a.get(t, 0) * freq_b.get(t, 0) for t in all_terms)

    # Magnitudes
    mag_a = math.sqrt(sum(v * v for v in freq_a.values()))
    mag_b = math.sqrt(sum(v * v for v in freq_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot_product / (mag_a * mag_b)


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity between two texts.

    Uses unique word sets (not frequencies).

    Args:
        text_a: First text.
        text_b: Second text.

    Returns:
        Jaccard similarity score (0.0 to 1.0).
    """
    set_a = set(_tokenize(text_a))
    set_b = set(_tokenize(text_b))

    if not set_a and not set_b:
        return 0.0

    intersection = set_a & set_b
    union = set_a | set_b

    if not union:
        return 0.0

    return len(intersection) / len(union)


def compute_similarity(
    text_a: str, text_b: str, method: str = "sequence"
) -> float:
    """Compute text similarity between two strings.

    Args:
        text_a: First text string.
        text_b: Second text string.
        method: Similarity method. One of:
            - 'sequence': SequenceMatcher ratio (difflib). Good for structural
              similarity. Default.
            - 'jaccard': Jaccard index on word sets. Good for vocabulary overlap.
            - 'cosine': Cosine similarity on term-frequency vectors. Good for
              content similarity regardless of length.

    Returns:
        Similarity score between 0.0 (completely different) and 1.0 (identical).

    Raises:
        ValueError: If method is not one of 'sequence', 'jaccard', 'cosine'.
    """
    if not text_a or not text_b:
        return 0.0

    method = method.lower()

    if method == "sequence":
        return SequenceMatcher(None, text_a, text_b).ratio()
    elif method == "jaccard":
        return _jaccard_similarity(text_a, text_b)
    elif method == "cosine":
        return _cosine_similarity_stdlib(text_a, text_b)
    else:
        raise ValueError(
            f"Unknown similarity method '{method}'. "
            f"Use 'sequence', 'jaccard', or 'cosine'."
        )


# ---------------------------------------------------------------------------
# Pairwise Similarity Matrix
# ---------------------------------------------------------------------------

def pairwise_similarity_matrix(
    section_data: Dict[str, Dict],
    section_type: str,
    method: str = "sequence",
    sample_size: Optional[int] = None,
    use_cache: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """Compute pairwise similarity matrix for a given section type.

    For each pair of devices that have the specified section, computes the
    similarity score and returns statistical summaries.

    **Performance Enhancement (FE-005):**
    Implements disk-based caching for 30x speedup on repeated queries.
    Cache key: sha256(sorted_device_keys + section_type + method)
    TTL: 7 days

    Args:
        section_data: Output from compare_sections.extract_sections_batch().
            Structure: {k_number: {'sections': {section_type: {'text': str}}}}
        section_type: Section type to compare (e.g., 'clinical_testing').
        method: Similarity method ('sequence', 'jaccard', 'cosine').
        sample_size: If provided, randomly sample this many devices
            (for performance with large datasets).
        use_cache: If True, use disk cache for similarity matrices. Default: True.
            Set to False to bypass cache (--no-cache flag).
        progress_callback: Optional callback for progress reporting.
            Signature: callback(current: int, total: int, message: str)
            Called periodically during computation with pairs completed so far.

    Returns:
        Dictionary with similarity analysis:
        {
            'section_type': str,
            'method': str,
            'devices_compared': int,
            'pairs_computed': int,
            'cache_hit': bool,  # NEW: indicates if result was cached
            'computation_time': float,  # NEW: time in seconds
            'statistics': {
                'mean': float,
                'median': float,
                'min': float,
                'max': float,
                'stdev': float,
            },
            'most_similar_pair': {
                'devices': (str, str),
                'score': float,
            },
            'least_similar_pair': {
                'devices': (str, str),
                'score': float,
            },
            'scores': [(k1, k2, score), ...]  # All pairwise scores
        }
    """
    start_time = time.time()

    # Collect devices with the specified section
    devices_with_section = {}
    for k_number, data in section_data.items():
        sections = data.get("sections", {})
        if section_type in sections:
            text = sections[section_type].get("text", "")
            if text.strip():
                devices_with_section[k_number] = text

    # Apply sample_size limit
    device_keys = sorted(devices_with_section.keys())
    if sample_size and len(device_keys) > sample_size:
        # Take most recent (sorted K-numbers are roughly chronological)
        device_keys = device_keys[-sample_size:]

    n = len(device_keys)
    if n < 2:
        return {
            "section_type": section_type,
            "method": method,
            "devices_compared": n,
            "pairs_computed": 0,
            "cache_hit": False,
            "computation_time": time.time() - start_time,
            "statistics": {
                "mean": 0.0, "median": 0.0, "min": 0.0,
                "max": 0.0, "stdev": 0.0,
            },
            "most_similar_pair": None,
            "least_similar_pair": None,
            "scores": [],
        }

    # Try cache if enabled
    cache_hit = False
    cached_result = None

    if use_cache and SIMILARITY_CACHE_AVAILABLE:
        cache_key = generate_cache_key(device_keys, section_type, method)
        cached_result = get_cached_similarity_matrix(cache_key)

        if cached_result is not None:
            # Cache hit - return cached result with updated timing
            cache_hit = True
            cached_result["cache_hit"] = True
            cached_result["computation_time"] = time.time() - start_time
            return cached_result

    # Cache miss or cache disabled - compute similarity matrix
    scores = []
    total_pairs = (n * (n - 1)) // 2
    last_update = 0
    update_interval = max(1, total_pairs // 100)  # Update every 1%

    for i in range(n):
        for j in range(i + 1, n):
            k1 = device_keys[i]
            k2 = device_keys[j]
            score = compute_similarity(
                devices_with_section[k1],
                devices_with_section[k2],
                method=method,
            )
            scores.append((k1, k2, round(score, 4)))

            # Progress callback
            if progress_callback and (len(scores) - last_update >= update_interval or len(scores) == total_pairs):
                progress_callback(len(scores), total_pairs, f"Computing similarity")
                last_update = len(scores)

    # Compute statistics
    score_values = [s[2] for s in scores]

    mean_score = sum(score_values) / len(score_values)
    sorted_scores = sorted(score_values)
    mid = len(sorted_scores) // 2
    if len(sorted_scores) % 2 == 0:
        median_score = (sorted_scores[mid - 1] + sorted_scores[mid]) / 2
    else:
        median_score = sorted_scores[mid]

    min_score = min(score_values)
    max_score = max(score_values)

    # Standard deviation
    if len(score_values) > 1:
        variance = sum((s - mean_score) ** 2 for s in score_values) / (len(score_values) - 1)
        stdev_score = math.sqrt(variance)
    else:
        stdev_score = 0.0

    # Find extremes
    most_similar = max(scores, key=lambda x: x[2])
    least_similar = min(scores, key=lambda x: x[2])

    computation_time = time.time() - start_time

    result = {
        "section_type": section_type,
        "method": method,
        "devices_compared": n,
        "pairs_computed": len(scores),
        "cache_hit": cache_hit,
        "computation_time": computation_time,
        "statistics": {
            "mean": round(mean_score, 4),
            "median": round(median_score, 4),
            "min": round(min_score, 4),
            "max": round(max_score, 4),
            "stdev": round(stdev_score, 4),
        },
        "most_similar_pair": {
            "devices": (most_similar[0], most_similar[1]),
            "score": most_similar[2],
        },
        "least_similar_pair": {
            "devices": (least_similar[0], least_similar[1]),
            "score": least_similar[2],
        },
        "scores": scores,
    }

    # Save to cache if enabled and available
    if use_cache and SIMILARITY_CACHE_AVAILABLE:
        cache_key = generate_cache_key(device_keys, section_type, method)
        save_similarity_matrix(cache_key, result)

    return result


# ---------------------------------------------------------------------------
# Temporal Trend Analysis
# ---------------------------------------------------------------------------

def _detect_trend_direction(year_values: List[Tuple[int, float]]) -> Dict[str, Any]:
    """Detect trend direction using simple linear regression (stdlib).

    Computes slope, intercept, and R-squared using ordinary least squares.

    Args:
        year_values: List of (year, value) tuples, sorted by year.

    Returns:
        Dictionary with trend information:
        {
            'direction': 'increasing' | 'decreasing' | 'stable' | 'insufficient_data',
            'slope': float,
            'r_squared': float,
            'start_year': int,
            'end_year': int,
            'start_value': float,
            'end_value': float,
        }
    """
    if len(year_values) < 2:
        return {
            "direction": "insufficient_data",
            "slope": 0.0,
            "r_squared": 0.0,
        }

    n = len(year_values)
    xs = [float(yv[0]) for yv in year_values]
    ys = [float(yv[1]) for yv in year_values]

    # Linear regression: y = slope * x + intercept
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    ss_yy = sum((y - mean_y) ** 2 for y in ys)

    if ss_xx == 0:
        return {
            "direction": "stable",
            "slope": 0.0,
            "r_squared": 0.0,
            "start_year": int(xs[0]),
            "end_year": int(xs[-1]),
            "start_value": ys[0],
            "end_value": ys[-1],
        }

    slope = ss_xy / ss_xx

    # R-squared
    if ss_yy == 0:
        r_squared = 1.0 if ss_xy == 0 else 0.0
    else:
        r_squared = (ss_xy ** 2) / (ss_xx * ss_yy)

    # Determine direction
    # Use slope magnitude relative to mean to judge significance
    if mean_y == 0:
        relative_slope = abs(slope)
    else:
        relative_slope = abs(slope) / abs(mean_y)

    if relative_slope < 0.02:  # Less than 2% change per year
        direction = "stable"
    elif slope > 0:
        direction = "increasing"
    else:
        direction = "decreasing"

    return {
        "direction": direction,
        "slope": round(slope, 4),
        "r_squared": round(r_squared, 4),
        "start_year": int(xs[0]),
        "end_year": int(xs[-1]),
        "start_value": round(ys[0], 2),
        "end_value": round(ys[-1], 2),
    }


def analyze_temporal_trends(
    section_data: Dict[str, Dict],
    section_types: List[str],
) -> Dict[str, Any]:
    """Analyze year-over-year trends for section types.

    Groups devices by decision year and tracks changes in:
    - Section inclusion rate (coverage percentage)
    - Average section length (word count)
    - Standards citation frequency

    Args:
        section_data: Output from compare_sections.extract_sections_batch().
        section_types: List of section types to analyze.

    Returns:
        Dictionary with temporal analysis:
        {
            'total_devices': int,
            'year_range': {'start': int, 'end': int},
            'trends': {
                section_type: {
                    'coverage_trend': {direction, slope, r_squared, ...},
                    'length_trend': {direction, slope, r_squared, ...},
                    'by_year': {
                        year: {
                            'device_count': int,
                            'coverage_pct': float,
                            'avg_word_count': float,
                            'standards_count': int,
                        }
                    }
                }
            }
        }
    """
    # Group devices by year
    devices_by_year: Dict[int, List[str]] = defaultdict(list)
    for k_number, data in section_data.items():
        decision_date = data.get("decision_date", "")
        if not decision_date:
            continue
        try:
            year = int(decision_date[:4])
            if 1976 <= year <= 2030:
                devices_by_year[year].append(k_number)
        except (ValueError, IndexError):
            continue

    if not devices_by_year:
        return {
            "total_devices": len(section_data),
            "year_range": {"start": 0, "end": 0},
            "trends": {},
        }

    years = sorted(devices_by_year.keys())
    year_start = years[0]
    year_end = years[-1]

    trends = {}
    for section_type in section_types:
        yearly_stats: Dict[int, Dict[str, Any]] = {}
        coverage_points = []
        length_points = []

        for year in years:
            year_devices = devices_by_year[year]
            total_in_year = len(year_devices)

            # Count devices with this section
            devices_with_section = 0
            word_counts = []
            standards_count = 0

            for k_number in year_devices:
                device_data = section_data.get(k_number, {})
                sections = device_data.get("sections", {})

                if section_type in sections:
                    devices_with_section += 1
                    section_info = sections[section_type]
                    wc = section_info.get("word_count", 0)
                    word_counts.append(wc)
                    standards_count += len(section_info.get("standards", []))

            coverage_pct = (
                (devices_with_section / total_in_year * 100)
                if total_in_year > 0 else 0.0
            )
            avg_wc = (
                sum(word_counts) / len(word_counts)
                if word_counts else 0.0
            )

            yearly_stats[year] = {
                "device_count": total_in_year,
                "devices_with_section": devices_with_section,
                "coverage_pct": round(coverage_pct, 1),
                "avg_word_count": round(avg_wc, 1),
                "standards_count": standards_count,
            }

            coverage_points.append((year, coverage_pct))
            if avg_wc > 0:
                length_points.append((year, avg_wc))

        trends[section_type] = {
            "coverage_trend": _detect_trend_direction(coverage_points),
            "length_trend": _detect_trend_direction(length_points),
            "by_year": yearly_stats,
        }

    return {
        "total_devices": len(section_data),
        "year_range": {"start": year_start, "end": year_end},
        "trends": trends,
    }


# ---------------------------------------------------------------------------
# Cross-Product-Code Comparison
# ---------------------------------------------------------------------------

def cross_product_compare(
    product_codes: List[str],
    section_types: List[str],
    structured_cache: Dict[str, Dict],
) -> Dict[str, Any]:
    """Compare section characteristics across multiple product codes.

    For each product code, computes section coverage rates, average word
    counts, and standards frequencies, enabling cross-code benchmarking.

    Args:
        product_codes: List of FDA product codes to compare (e.g., ['DQY', 'OVE']).
        section_types: List of section types to analyze.
        structured_cache: Full structured cache dict (k_number -> device data).
            Each device needs metadata.product_code or product_code field.

    Returns:
        Dictionary with cross-product comparison:
        {
            'product_codes': [str],
            'section_types': [str],
            'comparison': {
                section_type: {
                    product_code: {
                        'device_count': int,
                        'coverage_pct': float,
                        'avg_word_count': float,
                        'top_standards': [(standard, count), ...],
                    }
                }
            },
            'summary': {
                'highest_coverage': {section_type: product_code, ...},
                'longest_sections': {section_type: product_code, ...},
            }
        }
    """
    # Group cache by product code
    by_product_code: Dict[str, Dict[str, Dict]] = defaultdict(dict)
    for k_number, data in structured_cache.items():
        pc = data.get("metadata", {}).get("product_code", "")
        if not pc:
            pc = data.get("product_code", "")
        if pc:
            pc = pc.upper()
            if pc in [p.upper() for p in product_codes]:
                by_product_code[pc][k_number] = data

    comparison = {}
    summary_highest_coverage = {}
    summary_longest_sections = {}

    for section_type in section_types:
        section_comparison = {}
        best_coverage = ("", 0.0)
        best_length = ("", 0.0)

        for product_code in product_codes:
            pc = product_code.upper()
            pc_devices = by_product_code.get(pc, {})
            total_devices = len(pc_devices)

            if total_devices == 0:
                section_comparison[pc] = {
                    "device_count": 0,
                    "coverage_pct": 0.0,
                    "avg_word_count": 0.0,
                    "top_standards": [],
                }
                continue

            devices_with_section = 0
            word_counts = []
            standards_counter: Counter = Counter()

            for k_number, data in pc_devices.items():
                sections = data.get("sections", {})
                if section_type in sections:
                    devices_with_section += 1
                    section_info = sections[section_type]
                    text = section_info.get("text", "")
                    wc = section_info.get("word_count", len(text.split()))
                    word_counts.append(wc)

                    # Extract standards (reuse pattern from text)
                    for std in section_info.get("standards", []):
                        standards_counter[std] += 1

            coverage_pct = (
                (devices_with_section / total_devices * 100)
                if total_devices > 0 else 0.0
            )
            avg_wc = (
                sum(word_counts) / len(word_counts)
                if word_counts else 0.0
            )

            section_comparison[pc] = {
                "device_count": total_devices,
                "devices_with_section": devices_with_section,
                "coverage_pct": round(coverage_pct, 1),
                "avg_word_count": round(avg_wc, 1),
                "top_standards": standards_counter.most_common(10),
            }

            if coverage_pct > best_coverage[1]:
                best_coverage = (pc, coverage_pct)
            if avg_wc > best_length[1]:
                best_length = (pc, avg_wc)

        comparison[section_type] = section_comparison

        if best_coverage[0]:
            summary_highest_coverage[section_type] = best_coverage[0]
        if best_length[0]:
            summary_longest_sections[section_type] = best_length[0]

    return {
        "product_codes": [pc.upper() for pc in product_codes],
        "section_types": section_types,
        "comparison": comparison,
        "summary": {
            "highest_coverage": summary_highest_coverage,
            "longest_sections": summary_longest_sections,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """CLI entry point for section analytics."""
    parser = argparse.ArgumentParser(
        description="FDA 510(k) Section Analytics -- Similarity, trends, and cross-product comparison"
    )
    parser.add_argument(
        "--similarity-demo", action="store_true", dest="similarity_demo",
        help="Run a similarity computation demo"
    )
    parser.add_argument(
        "--method", default="sequence",
        choices=["sequence", "jaccard", "cosine"],
        help="Similarity method (default: sequence)"
    )

    args = parser.parse_args()

    if args.similarity_demo:
        text_a = (
            "The device is a cardiovascular catheter intended for use in "
            "percutaneous transluminal coronary angioplasty procedures."
        )
        text_b = (
            "This cardiovascular catheter device is indicated for "
            "percutaneous coronary interventions including angioplasty."
        )
        text_c = (
            "An orthopedic spinal implant system consisting of pedicle "
            "screws, rods, and connectors for posterior spinal fixation."
        )

        print("Section Analytics -- Similarity Demo")
        print("=" * 50)
        print()

        for method in ["sequence", "jaccard", "cosine"]:
            s_ab = compute_similarity(text_a, text_b, method=method)
            s_ac = compute_similarity(text_a, text_c, method=method)
            s_bc = compute_similarity(text_b, text_c, method=method)
            print(f"Method: {method}")
            print(f"  Catheter A vs Catheter B: {s_ab:.4f}  (similar devices)")
            print(f"  Catheter A vs Implant C:  {s_ac:.4f}  (different devices)")
            print(f"  Catheter B vs Implant C:  {s_bc:.4f}  (different devices)")
            print()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
