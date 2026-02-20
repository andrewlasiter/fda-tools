#!/usr/bin/env python3
"""
Data Completeness Scorer - Focused module for gap analysis confidence scoring.

Extracted from gap_analyzer.py as part of FDA-116 refactoring.
Calculates confidence scores and data completeness metrics.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def calculate_gap_analysis_confidence(
    gap_results: Dict[str, Any],
    project_dir: str
) -> Dict[str, Any]:
    """
    Calculate confidence scores for gap analysis results.

    Scores are based on:
    - Data availability (device_profile.json, review.json, etc.)
    - Gap detection completeness (all 4 categories analyzed)
    - Data freshness (recent vs stale data)

    Args:
        gap_results: Dict from analyze_all_gaps() with gap lists
        project_dir: Path to project directory

    Returns:
        Dict with confidence scores:
        {
            'overall_confidence': int (0-100),
            'data_availability_score': int (0-100),
            'detection_completeness_score': int (0-100),
            'data_freshness_score': int (0-100),
            'interpretation': str
        }
    """
    from pathlib import Path
    import json

    project_path = Path(project_dir)
    scores = {
        'data_availability_score': 0,
        'detection_completeness_score': 0,
        'data_freshness_score': 0,
    }

    # Score 1: Data Availability (40 points max)
    required_files = {
        'device_profile.json': 15,
        'review.json': 10,
        'standards_lookup.json': 10,
        'se_comparison.md': 5,
    }

    for filename, points in required_files.items():
        if (project_path / filename).exists():
            scores['data_availability_score'] += points

    # Score 2: Detection Completeness (40 points max)
    gap_categories = [
        'missing_device_data',
        'weak_predicates',
        'testing_gaps',
        'standards_gaps'
    ]

    for category in gap_categories:
        if category in gap_results and gap_results[category] is not None:
            scores['detection_completeness_score'] += 10

    # Score 3: Data Freshness (20 points max)
    # Check if device_profile has recent modification time
    device_profile_path = project_path / 'device_profile.json'
    if device_profile_path.exists():
        import time
        mtime = device_profile_path.stat().st_mtime
        age_days = (time.time() - mtime) / (60 * 60 * 24)

        if age_days < 7:
            scores['data_freshness_score'] = 20  # Fresh data
        elif age_days < 30:
            scores['data_freshness_score'] = 15  # Recent data
        elif age_days < 90:
            scores['data_freshness_score'] = 10  # Moderately stale
        else:
            scores['data_freshness_score'] = 5   # Stale data

    # Calculate overall confidence (0-100)
    overall_confidence = sum(scores.values())

    # Interpret confidence level
    interpretation = _interpret_confidence(
        level='overall',
        score=overall_confidence
    )

    return {
        **scores,
        'overall_confidence': overall_confidence,
        'interpretation': interpretation,
    }


def _interpret_confidence(level: str, score: int) -> str:
    """
    Interpret confidence score into human-readable assessment.

    Args:
        level: Type of score ('overall', 'data', 'detection', 'freshness')
        score: Numeric score (0-100)

    Returns:
        Human-readable interpretation string
    """
    if score >= 90:
        return "Very High - All required data present and analysis complete"
    elif score >= 75:
        return "High - Most data present, reliable gap detection"
    elif score >= 60:
        return "Medium - Some data gaps may affect completeness"
    elif score >= 40:
        return "Low - Significant data gaps, results may be incomplete"
    else:
        return "Very Low - Critical data missing, results unreliable"
